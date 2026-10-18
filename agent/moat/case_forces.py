"""Policy forces per company: IRA Medicare negotiation, Most Favored Nation (MFN) deal, tariff exposure.

Answers: how exposed is a company to IRA price setting, its MFN deal terms and tariff exposure, with the
company's own words (filing and call sentences) and the verified policy tables behind each number.

Signature: forces(ticker, force="all" | "ira" | "mfn" | "tariff", k=60) -> list of row dicts.
Kinds: summary, exposure_item, ira_drug, mfn_term, tariff_item, manufacturing_site, filing_statement,
call_statement, peer_matrix (one row, all shortlist tickers, cells with facts locators).
Data: data/moat/verified/policy/*.csv (locators come from the facts index) plus sentence search of the two latest
annual reports, latest 10-Q/interim and last four transcripts (grade A or B only).

Example: python -m agent.moat.case_forces NVO ira
"""
import csv
import re
import sys
from pathlib import Path

from agent.moat import cite as C
from agent.moat.case_sets import SHORTLIST

POL = Path(__file__).resolve().parents[2] / "data/moat/verified/policy"
TERMS = ["Inflation Reduction Act", "maximum fair price", "negotiated price", "Most Favored Nation", "MFN", "tariff",
         "Section 232", "manufacturing investment", "TrumpRx", "direct-to-consumer"]
FORCE_OF = {"IRA": "ira", "MFN": "mfn", "tariff": "tariff", "manufacturing": "tariff", "exposure_base": "ira"}
KIND_OF = {"IRA": "ira_drug", "MFN": "mfn_term", "tariff": "tariff_item", "manufacturing": "tariff_item",
           "exposure_base": "exposure_item"}


def _csv(name):
    with open(POL / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _facts(table, ticker=None):
    sql = 'SELECT row_key, locator, text FROM facts WHERE "table"=?'
    a = [table]
    if ticker:
        sql += " AND ticker=?"
        a.append(ticker)
    return {r["row_key"]: r for r in C.db().execute(sql, a).fetchall()}


def _cite_loc(loc, fallback_doc, fallback_url):
    """Citation + url for a locator of the form doc_id#p<n>; falls back to the table's doc path and source."""
    m = re.match(r"^(.*)#p(\d+)$", loc or "")
    if m:
        try:
            return C.cite(m.group(1), int(m.group(2)))
        except KeyError:
            pass
    return fallback_doc, fallback_url


def _row(ticker, kind, force, **kw):
    r = {"ticker": ticker, "kind": kind, "force": force, "item": "", "value": "", "unit": "", "effective_date": "",
         "text": "", "citation": "", "url": "", "locator": "", "source_id": "", "verify_status": "", "source": "",
         "quote_grade": "", "license": ""}
    r.update(kw)
    r["source_id"] = r["source_id"] or r["locator"]
    r["text"] = r["text"][:600]
    return r


def _table_rows(t, force):
    fx = _facts("policy/policy_exposure.csv", t)
    out = []
    for r in _csv("policy_exposure.csv"):
        if r["ticker"] != t or r["status"] == "dropped":
            continue
        f = FORCE_OF.get(r["force"], "ira")
        if force != "all" and f != force:
            continue
        loc = fx[r["row_id"]]["locator"] if r["row_id"] in fx else ""
        cit, url = _cite_loc(loc, f'{r["doc"]}, {r["printed_page_or_section"]}', r["source"])
        out.append(_row(t, KIND_OF.get(r["force"], "exposure_item"), f, item=r["item"], value=r["value"], unit=r["unit"],
                        effective_date=r["effective_date"], text=r["quote"], citation=cit, url=url or r["source"],
                        locator=loc or f"fact:policy/policy_exposure.csv#{r['row_id']}", verify_status=r["status"],
                        source=r["source"], row_id=r["row_id"], note=r["note"]))
    return out


def _summary(t, force):
    fx = _facts("policy/force_summary.csv", t)
    out = []
    for i, r in enumerate(_csv("force_summary.csv"), start=2):
        if r["ticker"] != t:
            continue
        loc = next(iter(fx.values()))["locator"] if fx else f"fact:policy/force_summary.csv#{i}"
        keys = {"ira": ["ira_drug_count_ipay2026_2028", "ira_drugs", "ira_drug_fy2025_revenue", "ira_revenue_unit",
                        "fy2025_total_revenue", "ira_share_of_total_revenue_pct", "expected_selection", "expected_share_pct"],
                "mfn": ["mfn_date", "us_investment_pledge_usd_bn", "pledge_horizon", "pledge_scope"],
                "tariff": ["tariff_exempt_until", "mfg_sites_total", "mfg_sites_non_us", "pct_mfg_sites_outside_us",
                           "mfg_sites_confidence", "us_revenue_share_pct"]}
        for f, ks in keys.items():
            if force in ("all", f):
                vals = {k: r[k] for k in ks if r.get(k, "") != ""}
                out.append(_row(t, "summary", f, item=f"{f} summary", value=str(vals), unit="mixed",
                                text="; ".join(f"{k}={v}" for k, v in vals.items()),
                                citation=f"Verified policy force_summary, {t}", locator=loc, verify_status="verified",
                                source="policy/force_summary.csv", traceable_row_ids=r["traceable_row_ids"], fields=vals))
    return out


def _ira_checks(t):
    fx = _facts("policy/ira_cut_check.csv", t)
    out = []
    for i, r in enumerate(_csv("ira_cut_check.csv"), start=2):
        if r["ticker"] != t:
            continue
        f = fx.get(f"policy/ira_cut_check.csv#{i}")
        loc = f["locator"] if f else ""
        cit, url = _cite_loc(loc, r["doc"], "")
        out.append(_row(t, "ira_drug", "ira", item=f'{r["drug"]} IPAY {r["ipay"]} negotiated price vs list (30-day)',
                        value=r["cms_pct_cut"], unit="pct cut", effective_date=f'{r["ipay"]}-01-01',
                        text=r["quote"], citation=cit, url=url, locator=loc or f"fact:policy/ira_cut_check.csv#{i}",
                        verify_status="verified" if r["match"] == "yes" else "check", source="CMS fact sheet",
                        mfp_usd=r["mfp_usd_30day"], list_usd=r["list_usd_30day"], recomputed_pct=r["recomputed_pct_cut"]))
    return out


def _sites(t):
    rows = [r for r in _csv("manufacturing_sites_verified.csv") if r["ticker"] == t]
    if not rows:
        return []
    fx = _facts("policy/manufacturing_sites_verified.csv", t)
    by = {}
    for r in rows:
        by.setdefault(r["country_code"], []).append(r)
    out = []
    for cc, rs in sorted(by.items(), key=lambda x: -len(x[1])):
        first = rs[0]
        loc = next((v["locator"] for v in fx.values() if f'fei_number = {first["fei_number"]};' in (v["text"] or "")), "")
        out.append(_row(t, "manufacturing_site", "tariff", item=f"FDA-registered manufacturing sites, {cc}",
                        value=str(len(rs)), unit="sites",
                        text=f'{len(rs)} sites in {cc}, e.g. {first["firm_name"]} (FEI {first["fei_number"]})',
                        citation="FDA CDER drug establishment registrations (drls_reg.txt)",
                        url="https://www.fda.gov/drugs/drug-approvals-and-databases/drug-establishments-current-registration-site",
                        locator=loc or "fact:policy/manufacturing_sites_verified.csv", verify_status=first["status"],
                        source=first["source_row"], country=cc, in_us=cc in ("USA", "PRI")))
    return out


def _docs(t):
    q = C.db().execute
    ann = q("SELECT doc_id FROM docs WHERE ticker=? AND doc_type='annual_report' AND superseded_by='' "
            "AND doc_id NOT LIKE '%\\_d2%' ESCAPE '\\' ORDER BY period DESC", (t,)).fetchall()
    qtr = q("SELECT doc_id FROM docs WHERE ticker=? AND doc_type IN ('quarterly_report','interim_report') "
            "AND superseded_by='' ORDER BY period DESC LIMIT 1", (t,)).fetchall()
    tr = q("SELECT doc_id, period FROM docs WHERE ticker=? AND doc_type='transcript' AND quote_grade IN ('A','B') "
           "AND superseded_by='' ORDER BY period DESC", (t,)).fetchall()
    seen, trs = set(), []
    for r in tr:
        if r["period"] not in seen and len(seen) < 4:
            seen.add(r["period"])
            trs.append(r["doc_id"])
    return [r["doc_id"] for r in ann[:2]], [r["doc_id"] for r in qtr], trs


def _sentences(text, terms):
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        s = " ".join(s.split())
        if 40 <= len(s) <= 560 and any(re.search(r"\b" + re.escape(x) + r"\b", s, re.I) for x in terms):
            out.append(s)
    return out


def _statements(t, force, per_doc=3):
    terms = {"all": TERMS, "ira": TERMS[:3] + ["Medicare negotiation"],
             "mfn": ["Most Favored Nation", "MFN", "TrumpRx", "direct-to-consumer"],
             "tariff": ["tariff", "Section 232", "manufacturing investment"]}[force]
    ann, qtr, trs = _docs(t)
    db = C.db()
    match = " OR ".join('"%s"' % x for x in terms)
    out = []
    for kind, docs in (("filing_statement", ann + qtr), ("call_statement", trs)):
        for d in docs:
            rows = db.execute("SELECT p.page_no, p.text, bm25(pages_fts) s FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid "
                              "WHERE pages_fts MATCH ? AND p.doc_id=? ORDER BY s LIMIT 12", (match, d)).fetchall()
            n = 0
            for r in rows:
                for s in _sentences(r["text"], terms):
                    if n >= per_doc:
                        break
                    if not C.verify_quote(s, d, r["page_no"]):
                        continue
                    cit, url = C.cite(d, r["page_no"])
                    dd = C._doc(d)
                    f = ("ira" if re.search(r"Inflation Reduction|fair price|negotiat", s, re.I) else
                         "tariff" if re.search(r"tariff|232|manufacturing", s, re.I) else "mfn")
                    out.append(_row(t, kind, f, item=next((x for x in terms if re.search(re.escape(x), s, re.I)), ""),
                                    text=s, citation=cit, url=url, locator=f"{d}#p{r['page_no']}",
                                    quote_grade=dd["quote_grade"] if dd["doc_type"] == "transcript" else "",
                                    license=dd["license"] or "", verify_status="quote_verified", source=d))
                    n += 1
    return out


def peer_matrix():
    fx = {r["ticker"]: r["locator"] for r in C.db().execute(
        'SELECT ticker, locator FROM facts WHERE "table"=?', ("policy/force_summary.csv",)).fetchall()}
    rows = {r["ticker"]: r for r in _csv("force_summary.csv")}
    cols = ["ira_share_of_total_revenue_pct", "mfn_date", "us_investment_pledge_usd_bn", "tariff_exempt_until"]
    value, loc = {}, {}
    for t in SHORTLIST:
        r = rows.get(t)
        if not r:
            continue
        value[t] = {c: r[c] for c in cols}
        loc[t] = {c: fx.get(t, "fact:policy/force_summary.csv") for c in cols}
    return _row("ALL", "peer_matrix", "all", item="peer exposure matrix", value=value, unit="mixed",
                text="; ".join(f"{t}: " + ", ".join(f"{c}={v}" for c, v in d.items()) for t, d in value.items()),
                citation="Verified policy force_summary (10 shortlist companies)", locator="fact:policy/force_summary.csv",
                verify_status="verified", source="policy/force_summary.csv", locators=loc)


def forces(ticker, force="all", k=60):
    t = ticker.upper()
    force = force.lower()
    if force not in ("all", "ira", "mfn", "tariff"):
        raise ValueError("force must be all, ira, mfn or tariff")
    if not any(r["ticker"] == t for r in _csv("force_summary.csv")):
        return []
    rows = _summary(t, force) + _table_rows(t, force)
    if force in ("all", "ira"):
        rows += _ira_checks(t)
    if force in ("all", "tariff"):
        rows += _sites(t)
    rows += _statements(t, force)
    rows = rows[:k]
    rows.append(peer_matrix())
    return rows


def main(argv=None):
    a = argv or sys.argv[1:]
    if not a:
        print("usage: python -m agent.moat.case_forces TICKER [all|ira|mfn|tariff]")
        return
    rs = forces(a[0], a[1] if len(a) > 1 else "all")
    if not rs:
        print(f"no policy data for {a[0]}")
    for r in rs:
        v = "..." if r["kind"] == "peer_matrix" else r["value"]
        print(f'[{r["kind"]}/{r["force"]}] {r["item"]} = {v} | {r["text"][:140]} | {r["citation"]} | {r["locator"]}')


if __name__ == "__main__":
    main()
