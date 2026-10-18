"""Side-by-side FDA label sections and linked tables for a product against the rivals the case lists for it.

Answers: how do the label (indications, boxed warning, contraindications, warnings, dosing), REMS, label
changes, exclusivity dates, price series and head-to-head trials of a product compare with its listed rivals.

    label_compare(drug, rivals=None, sections=("indications","boxed_warning","contraindications","warnings",
                  "rems","dosing","exclusivity","pricing")) -> list of row dicts

`drug` is a case key (e.g. "keytruda"). `rivals` defaults to the rivals agent.moat.case_sets lists for it
(all shortlist companies' sets are searched); pass rival keys to override. Rows carry kind, ticker, drug, maker,
section, text, citation, url, locator, source_id, quote_grade, license. Label rows cite a label page; table rows
carry verify_status, source, source_row and the facts locator. One kind="matrix" row per section holds
{drug: one-line summary}. Unknown drug returns [].

    python -m agent.moat.case_labels keytruda [--rivals opdivo imfinzi] [--section indications]
"""

import argparse
import csv
import re
import sys

from agent.moat import case_sets as S
from agent.moat import cite as C
from agent.moat.index import MOAT

ALL_SECTIONS = ("indications", "boxed_warning", "contraindications", "warnings", "rems", "dosing", "exclusivity",
                "pricing")
LABEL_SECTIONS = ("indications", "boxed_warning", "contraindications", "warnings", "dosing")
# A label version doc older than this is treated as stale and the current full label (fda_label) is used.
STALE_BEFORE = "2025-01-01"
# Dosing phrases are read from the start of the section only (later subsections name co-administered drugs).
DOSE_SCAN_CHARS = 2500
VER = MOAT / "verified"

# section -> regex on the page heading. Full labels split sections into subsections ("1.1 Melanoma").
HEAD = {
    "indications": r"^1(?:\.\d+)?[ .]",
    "boxed_warning": r"^(BOXED WARNING|WARNING:)",
    "contraindications": r"^4[ .]*CONTRAINDICATIONS",
    "warnings": r"^5(?:\.\d+)?[ .]",
    "dosing": r"^2(?:\.\d+)?[ .]",
}
# Version docs: one page per top-level section ("1 INDICATIONS", "BOXED WARNING", "2 DOSAGE AND ADMINISTRATION").
HEAD_VER = {
    "indications": r"^1 INDICATIONS", "boxed_warning": r"^BOXED WARNING", "contraindications": r"^4 CONTRAINDICATIONS",
    "warnings": r"^5 WARNINGS", "dosing": r"^2 DOSAGE",
}
DOSE_PATTERNS = [
    r"once weekly", r"once daily", r"once monthly", r"once every \d+ (?:weeks|months)", r"twice daily",
    r"twice weekly", r"every \d+ (?:weeks|months|days)", r"orally once daily",
    r"intravenous infusion over \d+ (?:minutes|hours)", r"subcutaneous(?:ly)?", r"intravenous(?:ly)?", r"orally",
    r"by mouth", r"intramuscular(?:ly)?",
]


def _norm_key(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _csv(rel):
    p = VER / rel
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return [{**r, "_row_key": f"{rel}#{i + 2}"} for i, r in enumerate(csv.DictReader(f))]


def _maker_map():
    m = {}
    for t, sets in S.COMPETITIVE_SETS.items():
        for k, rv in sets.items():
            for p in k.split("/"):
                m[p] = t
            for r, mk, _ in rv:
                m.setdefault(r, mk)
    return m


def default_rivals(drug):
    out = []
    for sets in S.COMPETITIVE_SETS.values():
        for k, rv in sets.items():
            if drug in k.split("/"):
                for r, _mk, _ in rv:
                    if r not in out and r != drug:
                        out.append(r)
    return out


def _fact_locator(table, row_key):
    r = C.db().execute('SELECT locator FROM facts WHERE "table"=? AND row_key=? LIMIT 1', (table, row_key)).fetchone()
    return r["locator"] if r else f"fact:{table}#{row_key}"


def _table_cite(rel, row, locator, source):
    num = row["_row_key"].split("#")[1]
    m = re.match(r"^(.+)#p(\d+)$", locator or "")
    if m:
        try:
            c, u = C.cite(m.group(1), int(m.group(2)))
            return f"{c} (table {rel} row {num})", u
        except KeyError:
            pass
    return f"Verified table {rel}, row {num}", (source if str(source).startswith("http") else "")


def _f(v):
    """Compact number text: '2020.0' -> '2020', long floats -> 2 decimals; other text unchanged."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return v
    return str(int(x)) if x == int(x) and abs(x) < 1e6 else f"{x:,.2f}"


def _trim(s, n=600):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 3].rstrip() + "..."


def _base(kind, ticker, drug, maker):
    return {"ticker": ticker, "kind": kind, "drug": drug, "maker": maker, "quote_grade": "", "license": ""}


def _trow(kind, rel, row, drug, ticker, maker, text, source, **extra):
    loc = _fact_locator(rel, row["_row_key"])
    cit, url = _table_cite(rel, row, loc, source)
    d = _base(kind, ticker, drug, maker)
    d.update({"text": _trim(text), "citation": cit, "url": url or "", "locator": loc, "source_id": loc,
              "verify_status": row.get("verify_status", ""), "source": source, "source_row": row.get("source_row", ""),
              "table": rel, "row_key": row["_row_key"]})
    d.update(extra)
    return d


# ---------------------------------------------------------------- label docs

def _label_docs(drug):
    """(latest version doc row or None, full label doc row or None)."""
    db = C.db()
    ver = db.execute("SELECT * FROM docs WHERE drug=? AND doc_type='fda_label_version' "
                     "ORDER BY period DESC, filed DESC LIMIT 1", (drug,)).fetchone()
    full = db.execute("SELECT * FROM docs WHERE drug=? AND doc_type='fda_label' "
                      "ORDER BY (doc_id LIKE 'drug:%') DESC LIMIT 1", (drug,)).fetchone()
    return ver, full


def _pages(doc_id):
    return C.db().execute("SELECT page_no, printed, text FROM pages WHERE doc_id=? ORDER BY page_no",
                          (doc_id,)).fetchall()


def _find_section(drug, section):
    """(doc row, [page rows]) for the section, or (None, [])."""
    ver, full = _label_docs(drug)
    use_ver = ver is not None and (ver["period"] or "") >= STALE_BEFORE
    order = [(ver, HEAD_VER)] if use_ver else []
    if full is not None:
        order.append((full, HEAD))
    if ver is not None and not use_ver:
        order.append((ver, HEAD_VER))
    for doc, heads in order:
        pages = [p for p in _pages(doc["doc_id"]) if re.match(heads[section], p["printed"] or "", re.I)]
        if pages:
            return doc, pages
    return None, []


def _count_indications(pages):
    text = "\n".join(p["text"] for p in pages)
    n = len(re.findall(r"^#+\s*1\.\d+", text, re.M))
    if not n:
        n = sum(1 for p in pages if re.match(r"^1\.\d+", p["printed"] or ""))
    if not n:
        n = len(re.findall(r"^\s*[-•]\s*\S", text, re.M)) or len(re.findall(r"\b(?:is|are) indicated\b", text))
    return n


def _dosing_summary(text):
    t = " ".join(text.split())
    found = []
    for pat in DOSE_PATTERNS:
        for m in re.finditer(pat, t, re.I):
            ph = m.group(0).lower()
            if ph not in found:
                found.append(ph)
    found = [f for f in found if not any(f != g and f in g for g in found)]
    return found[:6]


def _boxed_terms(pages):
    m = re.search(r"^#+\s*(WARNING[^\n]*)", pages[0]["text"], re.M | re.I)
    return _trim(m.group(1) if m else pages[0]["printed"], 200)


def _label_rows(drug, ticker, maker, section):
    doc, pages = _find_section(drug, section)
    if not doc:
        return []
    first = pages[0]
    full_text = "\n".join(p["text"] for p in pages)
    cit, url = C.cite(doc["doc_id"], first["page_no"])
    loc = f"{doc['doc_id']}#p{first['page_no']}"
    r = _base("label_section", ticker, drug, maker)
    r.update({"section": section, "heading": first["printed"], "text": _trim(first["text"]),
              "full_text_chars": len(full_text), "citation": cit, "url": url, "locator": loc, "source_id": loc,
              "label_effective": doc["period"] or "", "label_doc_type": doc["doc_type"],
              "has_boxed_warning": _has_boxed(drug), "pages_in_section": len(pages)})
    if section == "indications":
        r["n_indications"] = _count_indications(pages)
    if section == "boxed_warning":
        r["boxed_warning_terms"] = _boxed_terms(pages)
    if section == "dosing":
        r["dosing_summary"] = _dosing_summary(full_text[:DOSE_SCAN_CHARS])
    return [r]


def _has_boxed(drug):
    return bool(_find_section(drug, "boxed_warning")[1])


# ---------------------------------------------------------------- tables

def _ingredients():
    return {r["drug"]: r["ingredient"].lower() for r in _csv("product/rems.csv")}


def _rems_rows(drug, ticker, maker):
    out = []
    for r in _csv("product/rems.csv"):
        if r["drug"] != drug:
            continue
        t = f"{r['brand']} ({r['ingredient']}): REMS active {r['rems_active']}; elements: {r['elements'] or 'none'}"
        if r["rems_entries"]:
            t += f"; entries: {r['rems_entries']}"
        out.append(_trow("rems", "product/rems.csv", r, drug, ticker, maker, t, r["source"], section="rems",
                         rems_active=r["rems_active"], elements=r["elements"]))
    return out


def _change_rows(drug, ticker, maker, n=5):
    rel = "product/label_changes_key.csv"
    rows = [r for r in _csv(rel) if r["drug"] == drug]
    if not rows:
        rel = "product/label_changes.csv"
        rows = [r for r in _csv(rel) if r["drug"] == drug]
    rows.sort(key=lambda r: r.get("effective_date", ""), reverse=True)
    out = []
    for r in rows[:n]:
        desc = r.get("description") or r.get("new_excerpt") or ""
        t = f"{r['effective_date']} {r['section']} ({r.get('materiality') or r.get('change_type', '')}): {desc}"
        out.append(_trow("label_change", rel, r, drug, ticker, maker, t, r["source"], section="label_changes",
                         effective_date=r["effective_date"], version=r.get("version", ""),
                         materiality=r.get("materiality", "")))
    return out


LOE_KEYS = ["orange_book_last_patent", "exclusivity_latest_date", "purple_book_ref_exclusivity", "company_stated_loe",
            "first_generic_or_biosimilar"]


def _loe_rows(drug, ticker, maker):
    out = []
    for r in _csv("pipeline/loe_calendar.csv"):
        if _norm_key(r["brand"]) != drug:
            continue
        bits = "; ".join(f"{k} {r[k]}" for k in LOE_KEYS if r.get(k))
        t = f"{r['brand']} {r['territory']}: " + (bits or "no exclusivity dates in the table")
        out.append(_trow("exclusivity", "pipeline/loe_calendar.csv", r, drug, ticker, maker, t, r["source"],
                         section="exclusivity", territory=r["territory"], **{k: r.get(k, "") for k in LOE_KEYS}))
    return out


def _pricing_rows(drug, ticker, maker):
    out = []
    for r in _csv("pricing/gtn_exposure.csv"):
        if r["drug"] != drug:
            continue
        parts = []
        if r["list_like_series"]:
            parts.append(f"list-like ({r['list_like_series']}) {_f(r['list_like_from'])}-{_f(r['list_like_to'])}: "
                         f"{_f(r['list_like_start'])} to {_f(r['list_like_end'])} ({r['list_like_pct']}%)")
        if r["net_like_series"]:
            parts.append(f"net-like ({r['net_like_series']}) {_f(r['net_like_from'])}-{_f(r['net_like_to'])}: "
                         f"{_f(r['net_like_start'])} to {_f(r['net_like_end'])} ({r['net_like_pct']}%)")
        for k in ("ira_ipay", "ira_mfp_effective", "ira_mfp_per_30day", "mfp_discount_vs_nadac_pct", "exposure_call"):
            if r.get(k):
                parts.append(f"{k} {r[k]}")
        out.append(_trow("pricing", "pricing/gtn_exposure.csv", r, drug, ticker, maker,
                         f"{drug}: " + ("; ".join(parts) or "no free price series"), r["sources"], section="pricing",
                         **{k: r.get(k, "") for k in ("list_like_pct", "net_like_pct", "ira_mfp_effective",
                                                       "ira_mfp_per_30day", "exposure_call", "confidence")}))
    prox = [r for r in _csv("pricing/gtn_proxy.csv") if r["drug"] == drug]
    if prox:
        r = max(prox, key=lambda x: x["year"])
        keys = ["partd_spend_per_unit", "asp_payment_limit_per_hcpcs_unit", "nadac_weighted_per_unit", "ira_ipay",
                "ira_mfp_effective", "ira_mfp_per_30day", "nadac_vs_mfp_ndc_matched_median"]
        t = f"{drug} {r['year']}: " + "; ".join(f"{k} {_f(r[k])}" for k in keys if r.get(k))
        out.append(_trow("pricing", "pricing/gtn_proxy.csv", r, drug, ticker, maker, t, r["source"], section="pricing",
                         year=r["year"], **{k: r.get(k, "") for k in keys}))
    return out


def _h2h_rows(drug, rival, ing, ticker, maker):
    a, b = ing.get(drug, drug), ing.get(rival, rival)
    out = []
    if a == b:
        return out
    pairs = (f"{a} vs {b}", f"{b} vs {a}")
    for r in _csv("product/h2h_by_pair.csv"):
        if r["pair"] in pairs:
            t = (f"{r['pair']}: {r['n_ctgov_rows_checked']} CT.gov rows checked, {r['n_direct_h2h']} direct "
                 f"head-to-head, {r['n_regimen_h2h']} regimen head-to-head. {r['verdict']}")
            out.append(_trow("head_to_head", "product/h2h_by_pair.csv", r, drug, ticker, maker, t, r["source"],
                             section="head_to_head", rival=rival, pair=r["pair"]))
    for t_ in _csv("product/head_to_head.csv"):
        if t_["drugs"] in pairs and t_["true_head_to_head"] == "y" and t_["h2h_tier"] == "direct":
            out.append(_trow("head_to_head", "product/head_to_head.csv", t_, drug, ticker, maker,
                             f"{t_['nct_id']} {t_['title']} ({t_['phase'] or 'phase n/a'}, {t_['status']}); "
                             f"primary outcome: {t_['primary_outcome']}", t_["source"], section="head_to_head",
                             rival=rival, pair=t_["drugs"], nct_id=t_["nct_id"]))
    return out


# ---------------------------------------------------------------- matrix

def _summary(section, rows):
    if not rows:
        return "no data in the index"
    r = rows[0]
    if section == "indications":
        return f"{r['n_indications']} approved use(s) listed ({r['full_text_chars']} chars)"
    if section == "boxed_warning":
        return f"yes: {r['boxed_warning_terms']}"
    if section == "dosing":
        return "; ".join(r["dosing_summary"]) or "no route/frequency phrase found"
    if section in ("contraindications", "warnings"):
        if r["full_text_chars"] < 150:
            return _trim(r["text"], 110)
        return f"{r['full_text_chars']} chars; begins: {_trim(r['text'], 110)}"
    if section == "rems":
        return f"REMS active {r['rems_active']} ({r['elements'] or 'none'})"
    if section == "exclusivity":
        return "; ".join(f"{x['territory']}: " + (x["company_stated_loe"] or x["exclusivity_latest_date"] or
                                                    x["orange_book_last_patent"] or "n/a") for x in rows)
    return r["text"].split(": ", 1)[-1][:160]


# ---------------------------------------------------------------- public

def label_compare(drug, rivals=None, sections=ALL_SECTIONS):
    drug = _norm_key(drug)
    makers = _maker_map()
    db = C.db()
    if drug not in S.all_drugs() and not db.execute("SELECT 1 FROM docs WHERE drug=? LIMIT 1", (drug,)).fetchone():
        return []
    rival_keys = [_norm_key(r) for r in (rivals if rivals is not None else default_rivals(drug))]
    drugs = [drug] + [r for r in rival_keys if r != drug]
    ing = _ingredients()
    rows, per_drug = [], {}
    for dg in drugs:
        d_row = db.execute("SELECT ticker FROM docs WHERE drug=? LIMIT 1", (dg,)).fetchone()
        maker = makers.get(dg) or (d_row["ticker"] if d_row else "")
        ticker = (d_row["ticker"] if d_row else "") or maker
        mine = []
        for sec in sections:
            if sec in LABEL_SECTIONS:
                mine += _label_rows(dg, ticker, maker, sec)
            elif sec == "rems":
                mine += _rems_rows(dg, ticker, maker) + _change_rows(dg, ticker, maker)
            elif sec == "exclusivity":
                mine += _loe_rows(dg, ticker, maker)
            elif sec == "pricing":
                mine += _pricing_rows(dg, ticker, maker)
        if dg == drug:
            for rv in drugs[1:]:
                mine += _h2h_rows(dg, rv, ing, ticker, maker)
        per_drug[dg] = mine
        rows += mine
    for sec in sections:
        summ, cits, locs, urls = {}, [], [], []
        for dg in drugs:
            sub = [r for r in per_drug[dg] if r.get("section") == sec]
            if sec == "boxed_warning" and not sub:
                summ[dg] = "no" if _label_present(dg) else "no data in the index"
            else:
                summ[dg] = _summary(sec, sub)
            if sub:
                cits.append(sub[0]["citation"])
                locs.append(sub[0]["locator"])
                urls.append(sub[0]["url"])
        if not cits and sec != "boxed_warning":
            continue
        if not cits:  # boxed warning absent everywhere: cite the labels' indications pages as the evidence read
            for dg in drugs:
                doc, pg = _find_section(dg, "indications")
                if doc:
                    c, u = C.cite(doc["doc_id"], pg[0]["page_no"])
                    cits.append(c)
                    locs.append(f"{doc['doc_id']}#p{pg[0]['page_no']}")
                    urls.append(u)
            if not cits:
                continue
        rows.append({"ticker": rows[0]["ticker"], "kind": "matrix", "section": sec, "drug": drug, "matrix": summ,
                     "text": _trim(" | ".join(f"{k}: {v}" for k, v in summ.items())), "citation": " ; ".join(cits),
                     "url": urls[0], "locator": " ; ".join(locs), "source_id": locs[0], "quote_grade": "",
                     "license": ""})
    return rows


def _label_present(drug):
    return any(_find_section(drug, s)[0] for s in ("indications", "dosing"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Side-by-side label sections for a product and its case rivals")
    ap.add_argument("drug")
    ap.add_argument("--rivals", nargs="*", default=None)
    ap.add_argument("--section", nargs="*", default=None, choices=ALL_SECTIONS)
    a = ap.parse_args(argv)
    rows = label_compare(a.drug, a.rivals, tuple(a.section) if a.section else ALL_SECTIONS)
    if not rows:
        print(f"no rows: '{a.drug}' is not a known case drug or has no label data in the index", file=sys.stderr)
        return 1
    for r in rows:
        print(f"[{r['kind']}] {r['drug']} {r.get('section', '')} :: {r['text'][:200]}\n"
              f"    {r['citation']} <{r['locator']}>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
