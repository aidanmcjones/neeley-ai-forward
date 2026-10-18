"""Segment and product table changes: revised or reclassified past numbers and products quietly dropped.

Answers: "Which past revenue numbers did this company restate or reclassify, and which products stopped
being broken out?"  Rows come only from verified tables (data/moat/verified/filings/*.csv) plus
verified page quotes from the latest 10-K/10-Qs.

    segment_changes(ticker, kind=None, k=200) -> list of row dicts
    kind in {"restatement", "discontinued_breakout", "series_break", "revenue_check", "table_note"}

Every row has ticker, kind, text, citation, url, locator, source_id, quote_grade, license.
Table rows also carry verify_status and source.

Example:
    python -m agent.moat.case_segments MRK --kind restatement
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from agent.moat import cite

ROOT = Path(__file__).resolve().parents[2]
FIL = ROOT / "data" / "moat" / "verified" / "filings"
KINDS = ("restatement", "discontinued_breakout", "series_break", "revenue_check", "table_note")
NOTE_TERMS = ["reclassified", "recast", "revised", "prior period", "no longer separately",
              "included in other", "other pharmaceutical"]
_CITE_RE = re.compile(r"(data/\S+?\.md)\]?\s+p(\d+)")


def _read(name):
    p = FIL / name
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _doc_by_path(path):
    r = cite.db().execute("SELECT doc_id FROM docs WHERE path=?", (path,)).fetchone()
    return r["doc_id"] if r else None


def _resolve(citation):
    """Turn a CSV citation string into (citation, url, locator, doc_id, page_no); None when unresolvable."""
    m = _CITE_RE.search(citation or "")
    if m:
        doc_id = _doc_by_path(m.group(1))
        if doc_id:
            try:
                c, url = cite.cite(doc_id, int(m.group(2)))
                return c, url, f"{doc_id}#p{m.group(2)}", doc_id, int(m.group(2))
            except KeyError:
                pass
    return None


def _facts(table, ticker):
    out = {}
    for r in cite.db().execute('SELECT row_key, verify_status, source, locator FROM facts '
                               'WHERE "table"=? AND ticker=?', (table, ticker)):
        out[r["row_key"]] = r
    return out


def _row(ticker, kind, text, citation_csv, table, key, fact):
    res = _resolve(citation_csv)
    if res:
        c, url, loc, doc_id, page = res
    else:
        loc = fact["locator"] if fact else f"fact:{table}#{key}"
        src = fact["source"] if fact else ""
        c = f"verified table {table} row {key}" + (f" ({src})" if src else "")
        url, doc_id, page = (src if src.startswith("http") else ""), "", None
    return {"ticker": ticker, "kind": kind, "text": text[:600], "citation": c, "url": url, "locator": loc,
            "source_id": loc, "quote_grade": "", "license": "", "doc_id": doc_id, "page_no": page,
            "table": table, "row_key": key,
            "verify_status": fact["verify_status"] if fact else "", "source": fact["source"] if fact else ""}


def _name(member):
    s = (member or "").split(":")[-1]
    return re.sub(r"Member$", "", s) or s


def _money(v):
    return f"${float(v) / 1e6:,.1f}M"


def _accn_order(a):
    m = re.match(r"\d+-(\d\d)-(\d+)", a)
    return (m.group(1), int(m.group(2))) if m else ("99", 0)


def _restatements(t):
    table = "filings/restatements_triaged.csv"
    facts = _facts(table, t)
    rows = []
    for r in _read("restatements_triaged.csv"):
        if r["ticker"] != t:
            continue
        try:
            vals = json.loads(r["values_by_accession"] or "{}")
        except ValueError:
            vals = {}
        seq = sorted(((a, v) for v, accs in vals.items() for a in accs), key=lambda x: _accn_order(x[0]))
        prod = _name(r["product_member"]) or r["concept"].split(":")[-1]
        geo = r["geography"].split(":")[-1] if r["geography"] else ""
        label = f"{prod} {geo}".strip()
        if len(seq) >= 2:
            first, last = seq[0], seq[-1]
            body = f"reported {_money(first[1])} in {first[0]}, later {_money(last[1])} ({r['pct_diff']}%)"
        else:
            body = f"values {_money(r['min_value'])} to {_money(r['max_value'])} ({r['pct_diff']}%)"
        text = f"{label} {r['period_end']}: {body}; class {r['class']}: {r['explanation']}"
        row = _row(t, "restatement", text, r["citation"], table, r["row_id"], facts.get(r["row_id"]))
        row.update({"period": r["period_end"], "product": prod, "geography": geo, "class": r["class"],
                    "pct_diff": float(r["pct_diff"] or 0), "min_value": r["min_value"], "max_value": r["max_value"]})
        rows.append(row)
    rows.sort(key=lambda x: (x["class"] != "recast_reclassification", -x["pct_diff"]))
    return rows


def _discontinued(t):
    table = "filings/discontinued_breakouts.csv"
    facts = _facts(table, t)
    rows = []
    for i, r in enumerate(_read("discontinued_breakouts.csv"), start=2):
        if r["ticker"] != t:
            continue
        key = f"{table}#{i}"
        val = r["value_last_reported_usd"]
        text = (f"{r['product']} no longer broken out after {r['last_filing']}; last reported "
                f"{_money(val) if val else 'n/a'} ({r['comparative_period']}), folded into {r['folded_into']}: {r['evidence']}")
        row = _row(t, "discontinued_breakout", text, r["citation_last"], table, key, facts.get(key))
        row.update({"product": r["product"], "period": r["comparative_period"], "value": val, "unit": "USD",
                    "citation_without": r["citation_without"], "folded_into": r["folded_into"]})
        rows.append(row)
    return rows


def _checks(t):
    table = "filings/product_revenue_checks.csv"
    facts = _facts(table, t)
    allrows = [(i, r) for i, r in enumerate(_read("product_revenue_checks.csv"), start=2) if r["ticker"] == t]
    checks, breaks = [], []
    for i, r in allrows:
        key = f"{table}#{i}"
        prod = _name(r["product_member"])
        geo = r["geography"].split(":")[-1] if r["geography"] else "total"
        text = (f"{prod} {geo} {r['period_end']}: {_money(r['value_usd'])} in {r['form']} {r['accession']}; "
                f"XBRL {r['xbrl_status']}, text {r['text_status']}")
        row = _row(t, "revenue_check", text, "%s %s" % (r["text_doc"], r["printed_page"]), table, key, facts.get(key))
        row.update({"period": r["period_end"], "product": prod, "value": r["value_usd"], "unit": "USD"})
        checks.append(row)
    groups = defaultdict(list)
    for (i, r), row in zip(allrows, checks):
        groups[(r["product_member"], r["geography"], r["period_start"], r["period_end"])].append((r, row))
    for (pm, geo, ps, pe), items in groups.items():
        per = defaultdict(set)
        for r, _ in items:
            per[r["accession"]].add(round(float(r["value_usd"])))
        if len(per) < 2 or any(len(v) > 1 for v in per.values()):
            continue  # one accession printed several values (other dimensions): not a clean series comparison
        items.sort(key=lambda x: _accn_order(x[0]["accession"]))
        (r1, _), (r2, row2) = items[0], items[-1]
        if round(float(r1["value_usd"])) == round(float(r2["value_usd"])):
            continue
        text = (f"{_name(pm)} {geo.split(':')[-1] or 'total'} {pe}: {_money(r1['value_usd'])} in {r1['accession']}, "
                f"later {_money(r2['value_usd'])} in {r2['accession']}")
        row = dict(row2)
        row.update({"kind": "series_break", "text": text[:600], "prev_value": r1["value_usd"],
                    "value": r2["value_usd"], "delta": float(r2["value_usd"]) - float(r1["value_usd"])})
        breaks.append(row)
    breaks.sort(key=lambda x: -abs(x["delta"]))
    return checks, breaks


def _jnj_notes(t):
    rows = []
    for i, r in enumerate(_read("jnj_fiscal_quarters.csv"), start=2):
        if r["ticker"] != t or r["label_correct"] != "False":
            continue
        doc_id = _doc_by_path(r["file"])
        if not doc_id:
            continue
        try:
            c, url = cite.cite(doc_id, 1)
        except KeyError:
            continue
        loc = f"{doc_id}#p1"
        rows.append({"ticker": t, "kind": "table_note",
                     "text": f"{r['ticker']} file labelled {r['file_label']} is {r['fiscal_quarter']} "
                             f"(period end {r['period_end']}); fiscal calendar differs from calendar quarters",
                     "citation": c, "url": url, "locator": loc, "source_id": loc, "quote_grade": "", "license": "",
                     "doc_id": doc_id, "page_no": 1, "table": "filings/jnj_fiscal_quarters.csv",
                     "row_key": f"filings/jnj_fiscal_quarters.csv#{i}", "verify_status": "verified",
                     "source": r["file"], "period": r["period_end"]})
    return rows


def _sentences(text):
    return re.split(r"(?<=[.;])\s+|\n+", text)


def _table_notes(t, limit=10):
    db = cite.db()
    k10 = db.execute("SELECT doc_id, filed FROM docs WHERE ticker=? AND doc_type='annual_report' AND superseded_by='' "
                     "ORDER BY filed DESC LIMIT 1", (t,)).fetchone()
    if not k10:
        return []
    qs = db.execute("SELECT doc_id FROM docs WHERE ticker=? AND doc_type='quarterly_report' AND superseded_by='' "
                    "AND filed>=? ORDER BY filed DESC LIMIT 2", (t, k10["filed"])).fetchall()
    ids = [k10["doc_id"]] + [q["doc_id"] for q in qs]
    match = " OR ".join('"%s"' % w for w in NOTE_TERMS)
    sql = ("SELECT p.doc_id, p.page_no, p.text, bm25(pages_fts) s FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid "
           f"WHERE pages_fts MATCH ? AND p.doc_id IN ({','.join('?' * len(ids))}) ORDER BY s LIMIT 60")
    out, seen = [], set()
    pat = re.compile("|".join(re.escape(w) for w in NOTE_TERMS), re.I)
    for r in db.execute(sql, [match, *ids]):
        for s in _sentences(r["text"]):
            s = " ".join(s.split())
            if not (40 <= len(s) <= 500) or not pat.search(s) or s in seen:
                continue
            if not cite.verify_quote(s, r["doc_id"], r["page_no"]):
                continue
            seen.add(s)
            c, url = cite.cite(r["doc_id"], r["page_no"])
            loc = f"{r['doc_id']}#p{r['page_no']}"
            out.append({"ticker": t, "kind": "table_note", "text": s, "citation": c, "url": url, "locator": loc,
                        "source_id": loc, "quote_grade": "", "license": "", "doc_id": r["doc_id"],
                        "page_no": r["page_no"]})
            break
        if len(out) >= limit:
            break
    return out


def segment_changes(ticker, kind=None, k=200):
    """Rows about restated/reclassified numbers, products dropped from tables, and table notes for one ticker."""
    t = (ticker or "").upper()
    if kind is not None and kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")

    def want(x):
        return kind in (None, x)

    parts = {}
    if want("restatement"):
        parts["restatement"] = _restatements(t)
    if want("discontinued_breakout"):
        parts["discontinued_breakout"] = _discontinued(t)
    if want("revenue_check") or want("series_break"):
        checks, breaks = _checks(t)
        if want("revenue_check"):
            parts["revenue_check"] = checks
        if want("series_break"):
            parts["series_break"] = breaks
    if want("table_note"):
        parts["table_note"] = _table_notes(t) + _jnj_notes(t)
    if kind:
        return parts[kind][:k]
    share = {"restatement": 0.4, "discontinued_breakout": 0.2, "series_break": 0.15, "revenue_check": 0.1,
             "table_note": 0.15}
    out = []
    for kd, rows in parts.items():
        out += rows[:max(1, int(k * share[kd]))]
    return out[:k]


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if not a:
        print("usage: python -m agent.moat.case_segments TICKER [--kind KIND] [--k N]")
        return 2
    kind = a[a.index("--kind") + 1] if "--kind" in a else None
    k = int(a[a.index("--k") + 1]) if "--k" in a else 20
    for t in [x for x in a if not x.startswith("--") and x not in (kind, str(k))]:
        rows = segment_changes(t, kind, k)
        if not rows:
            print(f"{t}: no segment-change rows in the verified tables")
        for r in rows:
            print(f"[{r['kind']}] {r['text'][:220]} | {r['citation']} | {r['locator']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
