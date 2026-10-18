"""Census of the moat database: what is in citations.sqlite, by kind, stream, company and verification status.

Run:  python -m agent.moat.census [--md]   (writes data/moat/CENSUS.md with --md)
"""
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/moat/index/citations.sqlite"
SHORTLIST = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]


def q(c, sql, *a):
    return c.execute(sql, a).fetchall()


def census():
    c = sqlite3.connect(DB)
    out = {}
    out["totals"] = {t: q(c, f"SELECT COUNT(*) FROM {t}")[0][0] for t in ("docs", "pages", "turns", "facts")}
    out["docs_by_type"] = dict(q(c, "SELECT COALESCE(doc_type,''), COUNT(*) FROM docs GROUP BY 1 ORDER BY 2 DESC"))
    out["docs_by_stream"] = dict(q(c, "SELECT COALESCE(stream,''), COUNT(*) FROM docs GROUP BY 1 ORDER BY 2 DESC"))
    out["docs_by_company"] = dict(q(c, "SELECT COALESCE(ticker,''), COUNT(*) FROM docs GROUP BY 1 ORDER BY 2 DESC"))
    out["pages_by_company"] = dict(q(c, "SELECT COALESCE(d.ticker,''), COUNT(*) FROM pages p JOIN docs d ON d.doc_id=p.doc_id GROUP BY 1 ORDER BY 2 DESC"))
    out["transcripts_by_company"] = dict(q(c, "SELECT ticker, COUNT(*) FROM docs WHERE doc_type='transcript' GROUP BY 1 ORDER BY 2 DESC"))
    out["transcript_grades"] = dict(q(c, "SELECT COALESCE(quote_grade,'ungraded'), COUNT(*) FROM docs WHERE doc_type='transcript' GROUP BY 1"))
    out["licensed_docs"] = q(c, "SELECT COUNT(*) FROM docs WHERE license LIKE '%bloomberg%'")[0][0]
    # facts
    tabs = q(c, 'SELECT "table", COUNT(*) FROM facts GROUP BY 1 ORDER BY 2 DESC')
    out["fact_tables"] = len(tabs)
    by_stream = Counter()
    for t, n in tabs:
        by_stream[t.split("/")[0]] += n
    out["facts_by_stream"] = dict(by_stream.most_common())
    out["facts_by_table"] = dict(tabs)
    checked = ("verified", "corrected", "fixed", "yes", "True", "pass", "recomputed", "filled_verified", "match", "matches page",
               "verified_at_source", "verified_secondary_subject", "verbatim_fragments", "sample:verified")
    st = Counter(dict(q(c, "SELECT COALESCE(verify_status,''), COUNT(*) FROM facts GROUP BY 1")))
    buckets = defaultdict(int)
    for k, n in st.items():
        if k in checked:
            buckets["checked by a verifier"] += n
        elif k == "unverified_onboard":
            buckets["onboarded, awaiting a verifier"] += n
        elif k == "no_verified_copy":
            buckets["machine data (prices, I/B/E/S, CMS)"] += n
        elif k in ("dropped", "no", "False", "drop_publisher_text"):
            buckets["rejected, kept for the report only"] += n
        elif k in ("unchecked", "unverified", "", "none"):
            buckets["collected, not individually checked"] += n
        else:
            buckets["other status values"] += n
    out["facts_by_status"] = dict(buckets)
    out["facts_by_company"] = dict(q(c, "SELECT COALESCE(ticker,''), COUNT(*) FROM facts WHERE ticker IN (%s) GROUP BY 1 ORDER BY 2 DESC" % ",".join("?" * len(SHORTLIST)), *SHORTLIST))
    out["facts_with_drug"] = q(c, "SELECT COUNT(*) FROM facts WHERE drug IS NOT NULL AND drug != ''")[0][0]
    out["distinct_drugs_in_facts"] = q(c, "SELECT COUNT(DISTINCT lower(drug)) FROM facts WHERE drug IS NOT NULL AND drug != ''")[0][0]
    out["locators"] = {
        "document page (doc_id#p<page>)": q(c, "SELECT COUNT(*) FROM facts WHERE locator NOT LIKE 'fact:%' AND locator NOT LIKE 'url:%'")[0][0],
        "dataset or API url": q(c, "SELECT COUNT(*) FROM facts WHERE locator LIKE 'url:%'")[0][0],
        "row key only": q(c, "SELECT COUNT(*) FROM facts WHERE locator LIKE 'fact:%'")[0][0],
    }
    out["meta"] = dict(q(c, "SELECT key, value FROM meta WHERE key IN ('built_at','last_add_at','page_id_convention')"))
    # outside the index
    aw = ROOT / "data/moat/verify/ai_wrong.jsonl"
    out["ai_wrong_entries"] = sum(1 for l in aw.open() if l.strip()) if aw.exists() else 0
    gaps = 0
    for p in (ROOT / "data/moat/gaps").glob("*.jsonl"):
        gaps += sum(1 for l in p.open() if l.strip())
    out["gap_notes"] = gaps
    out["sqlite_mb"] = round(DB.stat().st_size / 1e6)
    verified_files = sorted(p.relative_to(ROOT / "data/moat/verified").as_posix() for p in (ROOT / "data/moat/verified").glob("*/*.csv"))
    out["verified_csv_files"] = len(verified_files)
    return out


def top(d, n=12):
    items = list(d.items())[:n]
    return "\n".join(f"| {k or '(none)'} | {v:,} |" for k, v in items)


def markdown(o):
    t = o["totals"]
    lines = [
        "# Moat database census",
        "",
        f"As of {o['meta'].get('last_add_at') or o['meta'].get('built_at')}. Index file {o['sqlite_mb']} MB. "
        f"Page id convention: {o['meta'].get('page_id_convention')}.",
        "",
        "## Totals",
        "",
        "| What | Count |", "|---|---|",
        f"| Documents | {t['docs']:,} |",
        f"| Pages (full-text searchable) | {t['pages']:,} |",
        f"| Speaker turns (earnings calls) | {t['turns']:,} |",
        f"| Fact rows (full-text searchable) | {t['facts']:,} |",
        f"| Fact tables | {o['fact_tables']:,} |",
        f"| Verified CSV files | {o['verified_csv_files']:,} |",
        f"| Fact rows naming a drug | {o['facts_with_drug']:,} ({o['distinct_drugs_in_facts']:,} distinct drug names) |",
        f"| Licensed (Bloomberg) documents, cite only | {o['licensed_docs']:,} |",
        f"| Verified AI errors logged | {o['ai_wrong_entries']:,} |",
        f"| Gap notes (what could not be sourced, and why) | {o['gap_notes']:,} |",
        "",
        "## Fact rows by verification status", "", "| Status | Rows |", "|---|---|", top(o["facts_by_status"]),
        "",
        "## Fact rows by locator (what a citation can open)", "", "| Locator | Rows |", "|---|---|", top(o["locators"]),
        "",
        "## Documents by type", "", "| Type | Docs |", "|---|---|", top(o["docs_by_type"], 20),
        "",
        "## Documents by stream", "", "| Stream | Docs |", "|---|---|", top(o["docs_by_stream"], 30),
        "",
        "## Documents and pages by company", "", "| Company | Docs | Pages |", "|---|---|---|",
    ]
    for k, v in list(o["docs_by_company"].items())[:30]:
        lines.append(f"| {k or '(none)'} | {v:,} | {o['pages_by_company'].get(k, 0):,} |")
    lines += ["", "## Earnings-call transcripts by company", "", "| Company | Calls |", "|---|---|", top(o["transcripts_by_company"], 30),
              "", f"Transcript quotability grades: {o['transcript_grades']}",
              "", "## Fact rows by stream", "", "| Stream | Rows |", "|---|---|", top(o["facts_by_stream"], 30),
              "", "## Fact rows by shortlist company", "", "| Company | Rows |", "|---|---|", top(o["facts_by_company"], 10),
              "", "## Fact rows by table", "", "| Table | Rows |", "|---|---|", top(o["facts_by_table"], 200)]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    o = census()
    if "--md" in sys.argv:
        (ROOT / "data/moat/CENSUS.md").write_text(markdown(o))
        print("wrote data/moat/CENSUS.md")
    print(json.dumps({k: v for k, v in o.items() if k not in ("facts_by_table",)}, indent=1)[:6000])
