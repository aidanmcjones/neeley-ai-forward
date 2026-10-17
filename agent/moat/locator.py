"""facts.locator: a page-like locator for every fact row, additive to the frozen citation-index contract.

  doc_id#p<page_no>        when the row names a document and a page (same convention as pages, so cite(doc_id, page_no)
                           and get_page() work on it unchanged)
  url:<dataset URL>#<row_key>  when the row's source is a dataset or API URL and no page exists (machine data with a link)
  fact:<table>#<row_key>   otherwise (a synthetic locator that keeps the row addressable)

Run after every build or --add:  python -m agent.moat.locator   (idempotent; fills only empty locators unless --all)
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data/moat/index/citations.sqlite"

PAGE_ID = re.compile(r"([A-Za-z0-9][A-Za-z0-9_\-:./ ]*?#p\d+)")
PAGE_IN_TEXT = re.compile(r"(?:\bp(?:age)?\.?\s*)(\d{1,4})\b", re.I)
DOC_COLS = ["doc_id", "doc", "document", "file", "path", "quote_file", "text_doc", "source_file", "filing", "transcript",
            "source_doc", "tenk_doc", "label_doc"]
PAGE_COLS = ["page_no", "page", "tenk_page", "pdf_page", "printed_page", "guidance_page", "page_cite", "printed_page_or_section",
             "source_row"]


def _s(v):
    return "" if v is None else str(v).strip()


PAGE_COLS = ["page_no", "page", "tenk_page", "pdf_page", "printed_page", "guidance_page", "page_cite", "printed_page_or_section",
             "source_page", "source_copy", "source_row"]
PAGE_EQ = re.compile(r"#page[= ](\d{1,4})\b", re.I)


def _int(v):
    try:
        return int(float(v))
    except Exception:
        return None


def _page(row):
    for c in PAGE_COLS:
        v = _s(row.get(c))
        if not v:
            continue
        n = _int(v)
        if n is not None:
            return n
        m = PAGE_EQ.search(v) or re.search(r"#p(\d+)", v) or PAGE_IN_TEXT.search(v)
        if m:
            return int(m.group(1))
    return None


def _lookup(core, doc_ids, tails, paths):
    core = core.strip()
    if not core:
        return None
    if core in doc_ids:
        return core
    if core in paths:
        return paths[core]
    for tok in [core] + re.split(r"[\s,;|]+", core):
        tok = tok.strip()
        if tok in paths:
            return paths[tok]
        b = os.path.basename(tok)
        if b in tails:
            return tails[b]
        stem = os.path.splitext(b)[0]
        if stem and stem in tails:
            return tails[stem]
    return None


def _doc(row, doc_ids, tails, paths):
    cands = [_s(row.get(c)) for c in DOC_COLS] + [_s(row.get("source_copy")), _s(row.get("source_local")),
                                                   _s(row.get("source_row")), _s(row.get("source"))]
    for v in cands:
        if not v:
            continue
        core = re.split(r"#p|#page|\s+page\s+|,\s*p\.", v)[0]
        d = _lookup(core, doc_ids, tails, paths)
        if d:
            return d
    # a 10-K page column with no doc named means the company's latest annual report
    if any(_s(row.get(c)) for c in ("tenk_page",)) and _s(row.get("ticker")):
        t = _s(row.get("ticker")).upper()
        for cand in (f"{t}:10k_FY2025.md", f"{t}:20f_FY2025.md", f"{t}:companies/{t}/10k_FY2025.md"):
            if cand in doc_ids:
                return cand
    return None


def derive(table, row_key, row, doc_ids, tails, paths):
    for v in row.values():
        v = _s(v)
        m = PAGE_ID.search(v)
        if m and m.group(1).split("#p")[0] in doc_ids:
            return m.group(1)
    d = _doc(row, doc_ids, tails, paths)
    p = _page(row)
    if d and p:
        return f"{d}#p{p}"
    key = row_key[len(table) + 1:] if row_key.startswith(table + "#") else row_key
    # third form: a row whose source is a dataset or API URL (CMS, data.medicaid.gov, SEC companyfacts, CT.gov, WRDS)
    for c in ("source_url", "url", "source", "geo_source", "dataset_url"):
        v = _s(row.get(c))
        m = re.search(r"https?://[^\s|,;\"')]+", v)
        if m:
            return f"url:{m.group(0).rstrip('.')}#{key}"
    return f"fact:{table}#{key}"


def backfill(db_path=OUT, all_rows=False):
    db = sqlite3.connect(db_path)
    cols = [r[1] for r in db.execute("pragma table_info(facts)")]
    if "locator" not in cols:
        db.execute("ALTER TABLE facts ADD COLUMN locator TEXT")
    doc_ids = {r[0] for r in db.execute("SELECT doc_id FROM docs")}
    tails, paths = {}, {}
    for doc_id, path in db.execute("SELECT doc_id, path FROM docs"):
        p = path or ""
        if p:
            paths[p] = doc_id
            paths[p.replace("data/moat/", "", 1)] = doc_id
            paths[p.replace("data/corpus/", "", 1)] = doc_id
        base = os.path.basename(p)
        for key in {base, os.path.splitext(base)[0], doc_id.split(":")[-1], os.path.basename(doc_id.split(":")[-1])}:
            if key:
                tails[key] = doc_id if key not in tails or tails[key] == doc_id else None
    tails = {k: v for k, v in tails.items() if v}
    q = 'SELECT id, "table", row_key, row_json FROM facts' + ("" if all_rows else " WHERE locator IS NULL OR locator = ''")
    todo = db.execute(q).fetchall()
    out = []
    for fid, table, key, rj in todo:
        try:
            row = json.loads(rj) if rj else {}
        except Exception:
            row = {}
        out.append((derive(table, key, row, doc_ids, tails, paths), fid))
    db.executemany("UPDATE facts SET locator = ? WHERE id = ?", out)
    db.commit()
    n_page = db.execute("SELECT COUNT(*) FROM facts WHERE locator LIKE '%#p%' AND locator NOT LIKE 'fact:%'").fetchone()[0]
    n_all = db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    db.close()
    return {"filled": len(out), "page_resolvable": n_page, "facts": n_all}


if __name__ == "__main__":
    print(json.dumps(backfill(all_rows="--all" in sys.argv), indent=1))
