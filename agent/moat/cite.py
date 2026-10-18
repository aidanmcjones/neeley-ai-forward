"""Query the citation index (data/moat/index/citations.sqlite, built by agent.moat.index).

    from agent.moat.cite import search_pages, search_facts, get_page, cite, verify_quote
    search_pages("Genmab royalty", ticker="JNJ", doc_type="annual_report")
    cite("JNJ:10k_FY2025.md", 52)   -> ("Johnson & Johnson 10-K FY2025, p. 50", "https://www.sec.gov/...")

CLI:  python -m agent.moat.cite "Keytruda royalty" --ticker MRK [--facts] [--grade B] [--since 2025-01-01] [-k 10]

Rules baked in: superseded docs are hidden unless include_superseded=True; grade_min applies to transcripts only and
drops ungraded transcripts; Bloomberg pages carry license='bloomberg_licensed' (quote with citation, never copy
their text into a public artifact).
"""

import argparse
import os
import re
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path

from agent.findings import _norm
from agent.needle.pages import DOC_LABELS

# Copied verbatim from data-moat commit 704741d (agent/moat/cite.py) except this DB resolution: the sqlite is
# gitignored, so use env CITATIONS_DB, else the repo-local file, else the gap-data worktree copy.
_LOCAL = Path(__file__).resolve().parents[2] / "data" / "moat" / "index" / "citations.sqlite"
_GAP = Path("/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data/data/moat/index/citations.sqlite")
DB = Path(os.environ["CITATIONS_DB"]) if os.environ.get("CITATIONS_DB") else (_LOCAL if _LOCAL.exists() else _GAP)
GRADE_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4}
TRANSCRIPT_TYPES = ("transcript", "transcript_source")
EXTRA_LABELS = {"current_report_8k": "8-K", "proxy_statement": "proxy (DEF 14A)", "material_agreement": "agreement exhibit",
                "cms_fact_sheet": "CMS fact sheet", "mfp_explanation": "CMS MFP explanation", "gov": "government document",
                "pricing_report": "pricing report", "notes": "verification notes", "note": "verification note",
                "memo": "verification memo"}


@lru_cache(maxsize=1)
def db():
    if not DB.exists():
        raise SystemExit(f"{DB} missing: run python -m agent.moat.index")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def fts_query(q):
    """Plain words become an AND of quoted terms; FTS syntax (quotes, OR, NEAR, *) passes through."""
    if re.search(r'"|\bOR\b|\bNEAR\b|\*', q):
        return q
    toks = re.findall(r"\w+", q)
    return " ".join(f'"{t}"' for t in toks)


def _or(q):
    return " OR ".join(f'"{t}"' for t in re.findall(r"\w+", q))


# ---------------------------------------------------------------- labels

def label(d):
    """'Merck 10-K FY2025', 'AstraZeneca 2026Q1 earnings call (Bloomberg)', 'Humira label'."""
    co = d["company"] or d["ticker"] or ""
    t, period, filed = d["doc_type"], d["period"] or "", d["filed"] or ""
    if t == "annual_report":
        return f"{co} {d['form'] or 'annual report'} FY{(filed or period)[:4] if not period[:4].isdigit() else period[:4]}"
    if t == "quarterly_report":
        return f"{co} 10-Q {period}"
    if t == "transcript":
        q = "Bloomberg" if d["stream"] == "bloomberg" else d["source_quality"]
        return f"{co} {period} earnings call ({q})"
    if t == "transcript_source":
        return f"{co} {period} earnings call (official transcript PDF)"
    if t in ("fda_label", "fda_label_version"):
        name = (d["drug"] or "").replace("_", " ").title()
        ver = re.search(r"label_v(\d+)", d["path"] or "")
        return f"{name} label" + (f" v{ver.group(1)} ({period})" if ver else "")
    if t == "table":
        return f"table {d['path'].split('/moat/', 1)[-1]}"
    name = EXTRA_LABELS.get(t) or DOC_LABELS.get(t) or d["form"] or t.replace("_", " ")
    if t == "sec_comment_letter" and d["form"]:
        name = f"SEC comment letter ({d['form']})"
    when = filed or period
    return " ".join(x for x in [co, name, when] if x)


def where(d, page_no, printed):
    if d["page_scheme"] == "section":
        return f"section {printed}" if printed != "?" else f"section {page_no}"
    if d["page_scheme"] == "pdf_page":
        return f"PDF p. {printed}"
    if not printed or printed == "?":
        return f"file page {page_no} (no printed page number)"
    if printed.startswith("Item "):
        return printed
    return f"p. {printed}"


def _doc(doc_id):
    return db().execute("SELECT * FROM docs WHERE doc_id=?", (doc_id,)).fetchone()


def cite(doc_id, page_no):
    """(citation string, source url). Raises KeyError for an unknown doc or page."""
    d = _doc(doc_id)
    p = db().execute("SELECT printed FROM pages WHERE doc_id=? AND page_no=?", (doc_id, page_no)).fetchone()
    if not d or not p:
        raise KeyError(f"{doc_id}#p{page_no} not in the index")
    return f"{label(d)}, {where(d, page_no, p['printed'])}", d["source_url"]


def get_page(doc_id, page_no):
    r = db().execute("SELECT p.*, d.license, d.quote_grade, d.superseded_by FROM pages p JOIN docs d USING(doc_id) "
                     "WHERE doc_id=? AND page_no=?", (doc_id, page_no)).fetchone()
    return dict(r) if r else None


def verify_quote(quote, doc_id, page_no):
    """True when the quote is on that page, using agent.findings.verify() normalization (NFKC, curly quotes,
    dashes, whitespace, case). Unlike verify(), no 20-char minimum and no speaker/figure checks."""
    p = get_page(doc_id, page_no)
    q = _norm(quote)
    return bool(p and q and q in _norm(p["text"]))


# ---------------------------------------------------------------- search

def search_pages(q, ticker=None, doc_type=None, since=None, grade_min=None, k=10, include_superseded=False):
    """Ranked page hits: [{doc_id, page_no, printed, citation, url, snippet, quote_grade, license, score}]."""
    where_sql, args = [], []
    if ticker:
        where_sql.append("d.ticker = ?")
        args.append(ticker.upper())
    if doc_type:
        types = [doc_type] if isinstance(doc_type, str) else list(doc_type)
        where_sql.append(f"d.doc_type IN ({','.join('?' * len(types))})")
        args += types
    if since:
        where_sql.append("COALESCE(NULLIF(d.filed,''), d.period) >= ?")
        args.append(since)
    if grade_min:
        ok = [g for g, n in GRADE_ORDER.items() if n <= GRADE_ORDER[grade_min.upper()]]
        where_sql.append(f"(d.doc_type NOT IN ('transcript','transcript_source') OR d.quote_grade IN "
                         f"({','.join('?' * len(ok))}))")
        args += ok
    if not include_superseded:
        where_sql.append("d.superseded_by = ''")
    extra = (" AND " + " AND ".join(where_sql)) if where_sql else ""
    sql = ("SELECT p.doc_id, p.page_no, p.printed, snippet(pages_fts, 0, '[', ']', ' ... ', 20) AS snip, "
           "bm25(pages_fts) AS score, d.quote_grade, d.license, d.doc_type FROM pages_fts "
           "JOIN pages p ON p.id = pages_fts.rowid JOIN docs d ON d.doc_id = p.doc_id "
           f"WHERE pages_fts MATCH ?{extra} ORDER BY score LIMIT ?")
    rows = db().execute(sql, [fts_query(q), *args, k]).fetchall()
    if not rows and len(re.findall(r"\w+", q)) > 1:
        rows = db().execute(sql, [_or(q), *args, k]).fetchall()
    out = []
    for r in rows:
        c, url = cite(r["doc_id"], r["page_no"])
        out.append({"doc_id": r["doc_id"], "page_no": r["page_no"], "printed": r["printed"], "citation": c,
                    "url": url, "snippet": " ".join(r["snip"].split()), "quote_grade": r["quote_grade"],
                    "license": r["license"], "score": round(r["score"], 3), "source_id": f"{r['doc_id']}#p{r['page_no']}"})
    return out


def search_facts(q, ticker=None, table=None, k=20):
    """Ranked verified-table rows: [{table, row_key, ticker, drug, period, field, value, unit, source, ...}]."""
    where_sql, args = [], []
    if ticker:
        where_sql.append("f.ticker = ?")
        args.append(ticker.upper())
    if table:
        where_sql.append('f."table" LIKE ?')
        args.append(f"%{table}%")
    extra = (" AND " + " AND ".join(where_sql)) if where_sql else ""
    sql = ('SELECT f.*, bm25(facts_fts) AS score FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid '
           f"WHERE facts_fts MATCH ?{extra} ORDER BY score LIMIT ?")
    rows = db().execute(sql, [fts_query(q), *args, k]).fetchall()
    if not rows and len(re.findall(r"\w+", q)) > 1:
        rows = db().execute(sql, [_or(q), *args, k]).fetchall()
    keep = ["table", "doc_id", "row_key", "ticker", "drug", "period", "field", "value", "unit", "source",
            "source_row", "verify_status", "text", "score"]
    # additive: facts.locator = doc_id#p<page_no> when the row names a page, else fact:<table>#<row_key>
    has_loc = rows and "locator" in rows[0].keys()
    return [{**{c: r[c] for c in keep}, "locator": (r["locator"] if has_loc else f"fact:{r['table']}#{r['row_key']}")}
            for r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Search the citation index")
    ap.add_argument("query")
    ap.add_argument("--ticker")
    ap.add_argument("--doc-type")
    ap.add_argument("--since")
    ap.add_argument("--grade", help="minimum transcript grade: A, B, C or D")
    ap.add_argument("--facts", action="store_true", help="search verified table rows instead of pages")
    ap.add_argument("--table")
    ap.add_argument("-k", type=int, default=10)
    a = ap.parse_args(argv)
    if a.facts:
        for h in search_facts(a.query, ticker=a.ticker, table=a.table, k=a.k):
            print(f"{h['table']} {h['row_key']} [{h['verify_status']}] {h['field']}={h['value']} {h['unit']}")
            print(f"    source: {h['source']}  source_row: {h['source_row']}")
            print(f"    {h['text'][:240]}")
        return
    for h in search_pages(a.query, ticker=a.ticker, doc_type=a.doc_type, since=a.since, grade_min=a.grade, k=a.k):
        flag = f" grade {h['quote_grade']}" if h["quote_grade"] else ""
        flag += " LICENSED" if h["license"] else ""
        print(f"{h['citation']}{flag}  <{h['source_id']}>")
        print(f"    {h['url']}")
        print(f"    {h['snippet']}")


if __name__ == "__main__":
    main(sys.argv[1:])
