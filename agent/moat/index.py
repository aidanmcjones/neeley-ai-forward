"""Build data/moat/index/citations.sqlite: every doc, every page, every verified table row, full-text searchable.

python -m agent.moat.index            # build (about 2 to 4 minutes)
python -m agent.moat.index --upload   # build, then gzip and put to R2 moat/index/citations.sqlite.gz
python -m agent.moat.index --add      # incremental: insert only docs and fact rows not yet indexed (ids stable)

Page ids match NEEDLE (agent/needle/pages.py, agent/findings.py verify()): a page is (doc_id, page_no) where
page_no is the first number in the "[[page N | printed M]]" marker, so "doc_id#pN" is the same source id the
verifier already accepts. Docs without markers get one page per section heading (labels) or per PDF page.
"""

import csv
import gzip
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

from agent.findings import MARKER

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"
MOAT = ROOT / "data" / "moat"
OUT = MOAT / "index" / "citations.sqlite"
BBG = CORPUS / "_inbox" / "bloomberg"
GRADES = MOAT / "verified" / "calls" / "transcript_grades.csv"

csv.field_size_limit(sys.maxsize)

COMPANY = {"MRK": "Merck", "BMY": "Bristol Myers Squibb", "PFE": "Pfizer", "LLY": "Eli Lilly", "NVO": "Novo Nordisk",
           "ABBV": "AbbVie", "JNJ": "Johnson & Johnson", "AZN": "AstraZeneca", "AMGN": "Amgen", "GILD": "Gilead",
           "NVS": "Novartis", "GSK": "GSK", "SNY": "Sanofi", "TAK": "Takeda", "REGN": "Regeneron",
           "ALNY": "Alnylam", "BBIO": "BridgeBio", "ROCHE": "Roche", "BOEHRINGER": "Boehringer Ingelheim"}

# Known bad files (data/corpus/README.md, GAPS.md): doc_id -> (superseded_by, note)
SUPERSEDED = {
    "AZN:transcripts/2026Q1_transcript.md": (
        "AZN:companies/AZN/transcripts/2026Q1_transcript.md",
        "mislabeled: this file is actually the Q2 2026 call (duplicate of AZN:transcripts/2026Q2_transcript.md); "
        "the real Q1 2026 call is the moat copy"),
}

SCHEMA = """
CREATE TABLE docs (doc_id TEXT PRIMARY KEY, ticker TEXT, company TEXT, "group" TEXT, doc_type TEXT, form TEXT,
  period TEXT, filed TEXT, source_quality TEXT, source_url TEXT, path TEXT, stream TEXT, quote_grade TEXT,
  superseded_by TEXT, license TEXT, drug TEXT, n_pages INTEGER, page_scheme TEXT, notes TEXT);
CREATE TABLE pages (id INTEGER PRIMARY KEY, doc_id TEXT, page_no INTEGER, printed TEXT, char_start INTEGER,
  char_end INTEGER, speakers TEXT, text TEXT);
CREATE TABLE turns (doc_id TEXT, page_no INTEGER, turn_no INTEGER, speaker TEXT, char_start INTEGER);
CREATE TABLE facts (id INTEGER PRIMARY KEY, "table" TEXT, doc_id TEXT, row_key TEXT, ticker TEXT, drug TEXT,
  period TEXT, field TEXT, value TEXT, unit TEXT, source TEXT, source_row TEXT, verify_status TEXT,
  row_json TEXT, text TEXT);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE VIRTUAL TABLE pages_fts USING fts5(text, content='pages', content_rowid='id', tokenize='porter unicode61');
CREATE VIRTUAL TABLE facts_fts USING fts5(text, content='facts', content_rowid='id', tokenize='porter unicode61');
"""


def s(v):
    return "" if v is None else str(v).strip()


# ---------------------------------------------------------------- docs

def corpus_rows():
    """manifest.csv, then manifest.jsonl and every sources.jsonl (later rows win, as agent/needle/pages.py does)."""
    rows = {}
    with open(CORPUS / "manifest.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["doc_id"]] = r
    for p in [CORPUS / "manifest.jsonl", *sorted(CORPUS.glob("*/*/sources.jsonl"))]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    rows[r["doc_id"]] = r
    for r in rows.values():
        r["stream"] = "corpus"
    return rows


def moat_rows():
    """Every data/moat/manifests/*.jsonl row; verify_* manifests sort after the collector ones, so they win."""
    rows = {}
    for p in sorted((MOAT / "manifests").glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                r.setdefault("stream", p.stem)
                rows[r["doc_id"]] = r
    return rows


def bloomberg_rows():
    rows = {}
    for pdf in sorted(BBG.glob("*.pdf")):
        m = re.match(r"([A-Z]+)_(\d{4}Q\d)_transcript_bbg", pdf.stem)
        if not m:
            continue
        side = pdf.with_suffix(".json")
        meta = json.loads(side.read_text()) if side.exists() else {}
        rel = pdf.relative_to(ROOT).as_posix()
        rows[f"{m.group(1)}:_inbox/bloomberg/{pdf.name}"] = {
            "ticker": m.group(1), "group": "companies", "doc_type": "transcript", "form": "", "period": m.group(2),
            "filed": "", "source_quality": meta.get("source_quality", "official_bloomberg"),
            "source_url": "Bloomberg Terminal (licensed)", "path": rel, "stream": "bloomberg",
            "title": meta.get("title", "")}
    return rows


def grade_map():
    """path -> grade, from both the graded file and the file quotes are taken from (quote_from)."""
    order = "ABCD"
    out = {}
    with open(GRADES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            g = s(r["grade"]).upper()
            if g not in order:
                continue
            for p in [r.get("path"), r.get("quote_from")]:
                for tok in s(p).split():
                    if tok.startswith("data/") or tok.startswith("src/"):
                        tok = tok if tok.startswith("data/") else "data/moat/verified/calls/" + tok
                        if tok not in out or order.index(g) < order.index(out[tok]):
                            out[tok] = g
    return out


# ---------------------------------------------------------------- pages

HEAD = re.compile(r"^(#{1,4})\s+(.*)$", re.M)
BBG_TAG = re.compile(r"^(?:Q|A) - |\s*\{BIO \d+ <GO>\}")
BBG_PAGE = re.compile(r"Page (\d+) of \d+")
MD_TURN = re.compile(r"^\*\*([^*\n]{2,80}?):?\*\*:?", re.M)
LSEG_TURN = re.compile(r"^([A-Z][A-Za-z.'\- ]{2,60}) - ([^\n]{2,80}?) - [^\n]{2,80}$", re.M)


def marked_pages(text):
    ms = list(MARKER.finditer(text))
    out = []
    for i, m in enumerate(ms):
        a = m.end()
        b = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((int(m.group(1)), m.group(2).strip(), a, b, text[a:b]))
    return out


def section_pages(text):
    """One page per heading; printed = the heading ('1.1 Rheumatoid Arthritis'). Empty sections are dropped."""
    hs = list(HEAD.finditer(text))
    out, n = [], 0
    bounds = [(0, None)] + [(h.start(), h) for h in hs]
    for i, (a, h) in enumerate(bounds):
        b = bounds[i + 1][0] if i + 1 < len(bounds) else len(text)
        body = text[a:b]
        clean = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        if h is not None:
            clean = clean[h.end() - h.start():]
        if not clean.strip():
            continue
        label = " ".join(h.group(2).split()) if h is not None else "?"
        n += 1
        out.append((n, label or "?", a, b, body))
    return out


def pdf_pages(path):
    import pymupdf
    doc = pymupdf.open(path)
    out, pos = [], 0
    for i, pg in enumerate(doc):
        t = pg.get_text()
        m = BBG_PAGE.search(t)
        printed = m.group(1) if m else str(i + 1)
        out.append((i + 1, printed, pos, pos + len(t), t))
        pos += len(t)
    return out


def bbg_participants(first_page):
    """Names listed under Company Participants / Other Participants, before Presentation."""
    m = re.search(r"Company Participants\n(.*?)\n(?:Presentation|Questions And Answers)\n", first_page, re.S)
    if not m:
        return set()
    names = {ln.strip() for ln in m.group(1).splitlines() if ln.strip() and ln.strip() != "Other Participants"}
    head = first_page[:m.start()]
    names |= {ln.split(",")[0].strip() for ln in head.splitlines() if "," in ln and not ln.startswith(",")}
    return {n for n in names if n} | {"Operator"}


def turns_for(pages, kind):
    out = []
    names = bbg_participants(pages[0][4]) if kind == "bloomberg" and pages else set()
    k = 0
    for page_no, _, _, _, t in pages:
        if kind == "bloomberg":
            hits = [(m.start(), BBG_TAG.sub("", m.group(0)).strip()) for m in re.finditer(r"^[^\n]+$", t, re.M)
                    if BBG_TAG.sub("", m.group(0)).strip() in names]
            if page_no == 1:  # skip the participant roster itself
                cut = t.find("\nPresentation\n")
                hits = [h for h in hits if h[0] > cut]
        elif kind == "lseg":
            hits = [(m.start(), m.group(1).strip()) for m in LSEG_TURN.finditer(t)]
        else:
            hits = [(m.start(), m.group(1).strip()) for m in MD_TURN.finditer(t)]
        for pos, sp in hits:
            k += 1
            out.append((page_no, k, sp, pos))
    return out


# ---------------------------------------------------------------- facts

TICKER_COLS = ["ticker", "company"]
DRUG_COLS = ["drug", "product", "product_member", "brand", "drugs", "agreement"]
PERIOD_COLS = ["period", "quarter", "year", "fiscal_period_end", "period_end", "fpedats", "date", "effective_date",
               "statpers", "report_date", "status_date", "staff_letter_date", "wac_effective_date", "pends",
               "anndats", "filed", "agreement_date", "call_date"]
SOURCE_COLS = ["source", "citation", "cite", "staff_quote_cite", "next_filing_cite", "doc", "quote_file", "text_doc",
               "guidance_file", "example_file", "path", "file", "url", "sources", "source_url", "evidence", "traceable_row_ids", "sources_used"]
PAGE_COLS = ["printed_page", "printed_page_or_section", "page", "guidance_page", "pdf_page"]
STATUS_COLS = ["verify_status", "verified", "match", "xbrl_status", "text_status", "ok", "label_correct",
               "recompute_check", "quotable", "check"]
VALUE_COLS = ["value", "value_usd", "value_last_reported_usd", "meanest", "adj_close", "nadac_per_unit",
              "payment_limit", "total_spend", "wac_after_increase", "total_amount_reimbursed", "abn_0_to_1",
              "ira_share_of_total_revenue_pct", "cms_pct_cut", "gap_pct", "avg_net_price_change_pct",
              "partd_spend_per_unit", "meanrec", "weight_pct", "count", "grade", "verdict", "materiality",
              "change_type", "n_indications", "true_head_to_head", "evidence_type", "classification", "rems_active",
              "officer_net_open_mkt_value", "exec_word_agreement_pct", "analyst_turns", "turns_with_topic",
              "share_of_quarters_asked", "flag", "found_in_company_docs", "pct_diff", "class", "issue",
              "label_correct", "term", "metric", "topic", "text"]
KEYISH = set(TICKER_COLS + DRUG_COLS + PERIOD_COLS + SOURCE_COLS + PAGE_COLS + ["source_row", "row_id", "oftic"])
NUM = re.compile(r"^-?\$?[\d,]*\.?\d+%?$")


def fact_tables():
    """(table name, path, default verify_status). Verified copies supersede raw tables of the same name."""
    out = []
    for p in sorted((MOAT / "verified").glob("*/*.csv")):
        # *_dropped.csv lists rows a verifier rejected; they are kept for the report, never cited as facts
        if p.name.endswith("_dropped.csv"):
            continue
        out.append((f"{p.parent.name}/{p.name}", p, "verified"))
    tables = MOAT / "tables"
    for p in sorted(tables.glob("ibes_*.csv")) + [tables / "prices_daily.csv"]:
        out.append((f"tables/{p.name}", p, "no_verified_copy"))
    # Raw pricing tables mix units (wrong Part B codes, MFP averaged across units); the verified pricing copies
    # fix that, so the raw ones are indexed only as a flagged fallback when verified/pricing/ is absent.
    if not list((MOAT / "verified" / "pricing").glob("*.csv")):
        for name in ["gtn_proxy.csv", "company_list_vs_net.csv", "wac_increases.csv", "partb_asp_quarterly.csv",
                     "partd_by_year.csv", "medicaid_sdud.csv", "nadac_history.csv"]:
            if (tables / name).exists():
                out.append((f"tables/{name}", tables / name, "unverified"))
    # Per-entity tables written by agent.moat.onboard_company / onboard_drug: same source / source_row columns,
    # not yet re-verified by a second agent, so they carry their own status.
    for p in sorted((MOAT / "onboard").glob("*/*.csv")):
        out.append((f"onboard/{p.parent.name}/{p.name}", p, "unverified_onboard"))
    return out


def verified_notes():
    """Markdown notes under data/moat/verified/ that no manifest lists yet (e.g. pricing/movements.md)."""
    rows = {}
    for p in sorted((MOAT / "verified").glob("*/*.md")):
        rel = p.relative_to(ROOT).as_posix()
        rows[f"{p.parent.name}:verified/{p.parent.name}/{p.name}"] = {
            "ticker": "", "group": p.parent.name, "doc_type": "notes", "source_quality": "verified",
            "path": rel, "stream": f"verify_{p.parent.name}"}
    return rows


def unit_for(field, row):
    if s(row.get("unit")):
        return s(row["unit"])
    for suf, u in [("_usd_bn", "USD bn"), ("_bn", "USD bn"), ("_usd", "USD"), ("_m", "USD m"), ("_pct", "%"),
                   ("_per_unit", "USD per unit"), ("adj_close", "USD"), ("payment_limit", "USD per HCPCS unit")]:
        if field.endswith(suf):
            return u
    return ""


def first(row, cols):
    for c in cols:
        if s(row.get(c)):
            return c, s(row[c])
    return "", ""


def fact_rows(table, path, default_status, doc_id):
    with open(path, encoding="utf-8", errors="ignore", newline="") as f:
        rd = csv.reader(f)
        header = next(rd, [])
        seen, cols = {}, []
        for h in header:  # label_changes.csv repeats some column names
            h = h.strip()
            seen[h] = seen.get(h, 0) + 1
            cols.append(h if seen[h] == 1 else f"{h}_{seen[h]}")
        for i, vals in enumerate(rd, start=2):
            row = dict(zip(cols, vals))
            if not any(v.strip() for v in vals):
                continue
            tick = s(row.get("ticker")) or s(row.get("company"))
            _, drug = first(row, DRUG_COLS)
            _, period = first(row, PERIOD_COLS)
            _, src = first(row, SOURCE_COLS)
            _, pg = first(row, PAGE_COLS)
            if pg and src and pg not in src:
                src = f"{src}, p. {pg}"
            st_col, status = first(row, STATUS_COLS)
            if "verify_note" in row and not s(row.get("verify_status")) and s(row.get("status")):
                st_col, status = "status", s(row["status"])
            status = status or default_status
            if default_status != "verified" and not st_col:
                status = default_status
            field, value = first(row, VALUE_COLS)
            if not field:
                for c in cols:
                    if c not in KEYISH and NUM.match(s(row.get(c))):
                        field, value = c, s(row[c])
                        break
            key = s(row.get("row_id")) or f"{table}#{i}"
            bits = [f"{c} = {s(v)}" for c, v in row.items() if s(v)]
            text = f"{table}: " + "; ".join(bits)
            yield (table, doc_id, key, tick, drug, period, field, value[:500], unit_for(field, row), src[:1000],
                   s(row.get("source_row")), status, json.dumps(row, ensure_ascii=False), text[:4000])


# ---------------------------------------------------------------- build

def onboard_names():
    """ticker -> registrant name for tickers onboarded by agent.moat.onboard_company (profile.json)."""
    out = {}
    for p in sorted((MOAT / "onboard").glob("*/profile.json")):
        try:
            d = json.loads(p.read_text())
            if d.get("ticker") and d.get("name"):
                out[d["ticker"]] = d["name"]
        except Exception:
            pass
    return out


def all_doc_rows():
    """Every doc row (corpus, moat manifests, Bloomberg, unlisted verified notes) and a path -> doc_id map."""
    allrows = {}
    for src in (corpus_rows(), moat_rows(), bloomberg_rows()):
        allrows.update(src)
    known = {s(r.get("path")) for r in allrows.values()}
    for d, r in verified_notes().items():
        if r["path"] not in known:
            allrows[d] = r
    by_path = {}
    for d, r in allrows.items():
        by_path.setdefault(s(r.get("path")), d)
    return allrows, by_path


def doc_context(allrows):
    ctx = {"grades": grade_map(), "company": {**onboard_names(), **COMPANY}}
    # raw moat tables superseded by the verified copy of the same file name
    ctx["verified_by_name"] = {Path(s(r["path"])).name: d for d, r in allrows.items()
                               if "/verified/" in s(r.get("path")) and s(r.get("path")).endswith(".csv")}
    drug_ticker = {}
    for r in allrows.values():
        m = re.match(r"data/corpus/drugs/([^/]+)/", s(r.get("path")))
        if m and s(r.get("ticker")):
            drug_ticker.setdefault(m.group(1), s(r["ticker"]))
    ctx["drug_ticker"] = drug_ticker
    ctx["bbg_by_call"] = {(r["ticker"], r["period"]): d for d, r in allrows.items() if r.get("stream") == "bloomberg"}
    return ctx


def doc_record(doc_id, r, ctx, stats):
    """(docs row tuple, pages [(n, printed, a, b, text)], turns [(page_no, k, speaker, pos)], speakers by page)."""
    path = s(r.get("path"))
    p = ROOT / path
    notes, scheme, pages, kind = [], "", [], "md"
    sup = ""
    if doc_id in SUPERSEDED:
        sup, note = SUPERSEDED[doc_id]
        notes.append(note)
    elif path.startswith("data/moat/tables/") and Path(path).name in ctx["verified_by_name"]:
        sup = ctx["verified_by_name"][Path(path).name]
        notes.append("raw collector table; the verified copy supersedes it")
    ticker = s(r.get("ticker")) or (doc_id.split(":")[0] if doc_id.split(":")[0].isupper() else "")
    m = re.match(r"data/(?:corpus|moat)/drugs/([^/]+)/", path)
    drug = m.group(1) if m else ""
    if drug and ticker == drug:  # moat label manifests put the drug in the ticker column
        ticker = ctx["drug_ticker"].get(drug, "")
    grade = ctx["grades"].get(path, "")
    if r.get("stream") == "bloomberg":
        grade = "A"
        notes.append("official Bloomberg transcript; licensed: index only, never copy text into a public artifact")
    if s(r.get("doc_type")) == "transcript" and (ticker, s(r.get("period"))) in ctx["bbg_by_call"] \
            and r.get("stream") != "bloomberg":
        notes.append(f"Bloomberg copy of this call: {ctx['bbg_by_call'][(ticker, s(r.get('period')))]}")
    if s(r.get("doc_type")) == "transcript" and not grade and s(r.get("stream")).startswith("onboard_"):
        grade = "C" if s(r.get("source_quality")) != "official" else ""
    if s(r.get("doc_type")) == "transcript" and grade == "C":
        notes.append("grade C: check the quote against Bloomberg before it goes in a findings table")
    if s(r.get("doc_type")) == "transcript" and grade == "D":
        notes.append("grade D: not quotable")
    if not p.exists():
        notes.append("file missing on disk")
    elif p.suffix == ".md":
        text = p.read_text(encoding="utf-8", errors="ignore")
        pages = marked_pages(text)
        scheme = "marker"
        if not pages:
            pages = section_pages(text)
            scheme = "section"
            notes.append("no page markers: one page per section heading, printed = heading (cite by section)")
        if s(r.get("doc_type")) in ("transcript",):
            kind = "md"
    elif p.suffix == ".pdf":
        pages = pdf_pages(p)
        scheme = "pdf_page"
        kind = "bloomberg" if r.get("stream") == "bloomberg" else "lseg"
        notes.append("PDF: one page per PDF page; printed = PDF page number")
    else:
        scheme = "none"
        if p.suffix == ".csv":
            notes.append("table: rows are in facts if verified or listed, no pages")
        else:
            notes.append(f"{p.suffix} file: not page-indexed")
            stats["pages_skipped_docs"].append(doc_id)
    transcriptish = s(r.get("doc_type")) in ("transcript", "transcript_source")
    turns = turns_for(pages, kind) if transcriptish and pages else []
    sp_by_page = {}
    for page_no, _, sp, _ in turns:
        sp_by_page.setdefault(page_no, [])
        if sp not in sp_by_page[page_no]:
            sp_by_page[page_no].append(sp)
    lic = "bloomberg_licensed" if r.get("stream") == "bloomberg" else ""
    doc = (doc_id, ticker, ctx["company"].get(ticker, ticker), s(r.get("group")), s(r.get("doc_type")),
           s(r.get("form")), s(r.get("period")), s(r.get("filed")), s(r.get("source_quality")),
           s(r.get("source_url")), path, s(r.get("stream")), grade, sup, lic, drug, len(pages), scheme,
           "; ".join(notes))
    return doc, pages, turns, sp_by_page


def insert_doc(db, rec):
    doc, pages, turns, sp_by_page = rec
    doc_id = doc[0]
    db.executemany("INSERT INTO pages(doc_id,page_no,printed,char_start,char_end,speakers,text) VALUES (?,?,?,?,?,?,?)",
                   [(doc_id, n, pr, a, b, "; ".join(sp_by_page.get(n, [])), t) for n, pr, a, b, t in pages])
    db.executemany("INSERT INTO turns VALUES (?,?,?,?,?)", [(doc_id, *t) for t in turns])
    db.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", doc)
    return len(pages)


FACT_INSERT = ('INSERT INTO facts("table",doc_id,row_key,ticker,drug,period,field,value,unit,source,'
               'source_row,verify_status,row_json,text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)')


def build(out=OUT):
    t0 = time.time()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    db = sqlite3.connect(tmp)
    db.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;" + SCHEMA)

    allrows, by_path = all_doc_rows()
    ctx = doc_context(allrows)
    stats = {"pages_skipped_docs": []}
    n_pages = 0
    for doc_id, r in allrows.items():
        n_pages += insert_doc(db, doc_record(doc_id, r, ctx, stats))

    n_facts = 0
    tabs = fact_tables()
    for table, path, status in tabs:
        rel = path.relative_to(ROOT).as_posix()
        doc_id = by_path.get(rel, "")
        rows = list(fact_rows(table, path, status, doc_id))
        db.executemany(FACT_INSERT, rows)
        n_facts += len(rows)

    db.execute("CREATE INDEX pages_doc ON pages(doc_id, page_no)")
    db.execute("CREATE INDEX turns_doc ON turns(doc_id, page_no)")
    db.execute('CREATE INDEX facts_tab ON facts("table", ticker)')
    db.execute("CREATE INDEX docs_tick ON docs(ticker, doc_type)")
    db.execute("INSERT INTO pages_fts(pages_fts) VALUES('rebuild')")
    db.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")
    pricing = "verified" if (MOAT / "verified" / "pricing").exists() else "unverified"
    meta = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_docs": len(allrows), "n_pages": n_pages,
            "n_facts": n_facts, "fact_tables": json.dumps([t for t, _, _ in tabs]),
            "pricing_source": pricing, "pages_skipped_docs": json.dumps(stats["pages_skipped_docs"]),
            "page_id_convention": "doc_id#p<page_no>, page_no = first number of the [[page N | printed M]] marker"}
    db.executemany("INSERT INTO meta VALUES (?,?)", [(k, str(v)) for k, v in meta.items()])
    db.commit()
    db.execute("INSERT INTO pages_fts(pages_fts) VALUES('optimize')")
    db.execute("INSERT INTO facts_fts(facts_fts) VALUES('optimize')")
    db.commit()
    db.execute("VACUUM")
    db.close()
    tmp.replace(out)
    meta["seconds"] = round(time.time() - t0, 1)
    meta["mb"] = round(out.stat().st_size / 1e6, 1)
    return meta


def add(out=OUT, only_tables=None):
    """Incremental update: insert docs whose doc_id is not in the index and fact rows whose (table, row_key) is not,
    appending to pages / facts and their FTS tables. Existing rows and ids are never touched, so running it twice
    is a no-op. Falls back to a full build when the index does not exist yet."""
    t0 = time.time()
    if not out.exists():
        meta = build(out)
        meta["mode"] = "full_build (no index yet)"
        return meta
    db = sqlite3.connect(out)
    have_docs = {r[0] for r in db.execute("SELECT doc_id FROM docs")}
    allrows, by_path = all_doc_rows()
    new = {d: r for d, r in allrows.items() if d not in have_docs}
    ctx = doc_context(allrows) if new else None
    stats = {"pages_skipped_docs": []}
    n_pages = 0
    max_page = db.execute("SELECT COALESCE(MAX(id), 0) FROM pages").fetchone()[0]
    for doc_id, r in new.items():
        n_pages += insert_doc(db, doc_record(doc_id, r, ctx, stats))
    db.execute("INSERT INTO pages_fts(rowid, text) SELECT id, text FROM pages WHERE id > ?", (max_page,))

    have_keys = {}
    max_fact = db.execute("SELECT COALESCE(MAX(id), 0) FROM facts").fetchone()[0]
    n_facts = 0
    new_tables = []
    for table, path, status in fact_tables():
        if only_tables and table not in only_tables:
            continue
        if table not in have_keys:
            have_keys[table] = {r[0] for r in db.execute('SELECT row_key FROM facts WHERE "table" = ?', (table,))}
        rel = path.relative_to(ROOT).as_posix()
        rows = [x for x in fact_rows(table, path, status, by_path.get(rel, "")) if x[2] not in have_keys[table]]
        if rows:
            db.executemany(FACT_INSERT, rows)
            n_facts += len(rows)
            if not have_keys[table]:
                new_tables.append(table)
    db.execute("INSERT INTO facts_fts(rowid, text) SELECT id, text FROM facts WHERE id > ?", (max_fact,))
    cur = dict(db.execute("SELECT key, value FROM meta").fetchall())
    tabs = json.loads(cur.get("fact_tables", "[]"))
    tabs += [t for t in new_tables if t not in tabs]
    upd = {"n_docs": db.execute("SELECT COUNT(*) FROM docs").fetchone()[0],
           "n_pages": db.execute("SELECT COUNT(*) FROM pages").fetchone()[0],
           "n_facts": db.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
           "fact_tables": json.dumps(tabs), "last_add_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    db.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", [(k, str(v)) for k, v in upd.items()])
    db.commit()
    db.close()
    return {"mode": "add", "new_docs": len(new), "new_pages": n_pages, "new_facts": n_facts,
            "new_tables": new_tables, "n_docs": upd["n_docs"], "n_pages": upd["n_pages"], "n_facts": upd["n_facts"],
            "seconds": round(time.time() - t0, 1)}


def upload(path=OUT):
    from agent.tenk import Store
    data = gzip.compress(path.read_bytes(), compresslevel=6)
    st = Store()
    st.put("moat/index/citations.sqlite.gz", data, "application/gzip")
    return len(data), st


def main():
    if "--add" in sys.argv:
        print(json.dumps(add(), indent=1))
        return
    meta = build()
    print(json.dumps({k: v for k, v in meta.items() if k not in ("fact_tables",)}, indent=1))
    if "--upload" in sys.argv:
        n, st = upload()
        print("uploaded", n, "bytes to", getattr(st, "bucket", None), "moat/index/citations.sqlite.gz")


if __name__ == "__main__":
    main()
