"""Page store for every page-marked corpus document, in the exact shape agent.findings.verify expects.

docs(ticker, doc_types=None) -> {doc_id: {"row", "pages": {file_page: (printed, text)}, "flat"}}
Unlike agent.findings.load_docs (filings and calls only), this covers every doc type with page markers:
earnings releases, 6-Ks, policy 8-Ks, slides, glossy reports, distributor filings. Rows come from manifest.jsonl
plus each folder's sources.jsonl, so documents added after manifest.csv was last rebuilt are included.

check(evidence, ticker_docs) runs the shared verifier on one schema.Evidence and fills printed/citation.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from agent.findings import MARKER, _norm, verify

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "data" / "corpus"
FORMS = {"annual_report": "10-K", "quarterly_report": "10-Q"}


@lru_cache(maxsize=1)
def manifest():
    """{doc_id: row} from manifest.jsonl and every sources.jsonl; later rows win, missing files dropped."""
    rows = {}
    for p in [CORPUS / "manifest.jsonl", *sorted(CORPUS.glob("*/*/sources.jsonl"))]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if (ROOT / r["path"]).exists():
                        rows[r["doc_id"]] = r
    return rows


def _row(r):
    """Normalize a manifest row to the string fields agent.findings.label() reads."""
    out = {k: ("" if v is None else v) for k, v in r.items()}
    out["form"] = r.get("form") or FORMS.get(r.get("doc_type"), "")
    out["period"] = str(r.get("period") or r.get("filed") or "")
    out["source_quality"] = r.get("source_quality") or "official"
    return out


def parse(path):
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    parts = MARKER.split(text)
    pages = {int(parts[i]): (parts[i + 1].strip(), parts[i + 2]) for i in range(1, len(parts) - 2, 3)}
    return pages, text


@lru_cache(maxsize=32)
def docs(ticker, doc_types=None):
    out = {}
    for doc_id, r in manifest().items():
        if r["ticker"] != ticker.upper() or (doc_types and r["doc_type"] not in doc_types):
            continue
        if not r["path"].endswith(".md"):
            continue
        pages, text = parse(ROOT / r["path"])
        if pages:
            out[doc_id] = {"row": _row(r), "pages": pages, "flat": _norm(text)}
    return out


def find_page(doc, snippet):
    """File page whose text contains snippet (normalized), else None."""
    q = _norm(snippet)
    for n, (_, t) in doc["pages"].items():
        if q in _norm(t):
            return n
    return None


def check(ev, ticker_docs):
    """Verify one Evidence with the shared verifier. Returns (status, reason); fills ev.printed / ev.citation."""
    status, reason, citation = verify({"source": ev.source(), "quote": ev.quote, "speaker": ev.speaker,
                                       "figures": ev.figures}, ticker_docs)
    doc = ticker_docs.get(ev.doc_id)
    if doc and ev.page in doc["pages"]:
        ev.printed = doc["pages"][ev.page][0]
        row = doc["row"]
        # agent.findings.label() only knows 10-K / 10-Q / calls; name every other doc type correctly
        if citation and row["doc_type"] in DOC_LABELS:
            where = f"p. {ev.printed}" if ev.printed and ev.printed != "?" else f"file page {ev.page}"
            citation = f"{row['ticker']} {DOC_LABELS[row['doc_type']]} {row.get('filed') or row['period']}, {where}"
    ev.citation = citation.replace(", p. Item ", ", Item ") if citation else citation  # Item-sectioned filings
    return status, reason


DOC_LABELS = {"earnings_release": "earnings release (8-K)", "policy_8k": "8-K", "foreign_current_report": "6-K",
              "earnings_slides": "earnings slides", "investor_presentation": "investor presentation",
              "press_release": "press release", "interim_report": "interim report",
              "annual_report_glossy": "annual report", "sales_supplement": "sales supplement"}


def paragraphs(text, min_words=12):
    """Split page text into paragraphs worth comparing (drops headers, table rows, page numbers)."""
    out = []
    for p in re.split(r"\n\s*\n", text):
        p = " ".join(p.split())
        # a paragraph has a sentence in it: drops tables of contents and heading runs (NVO's "45 51 71 132
        # General information Prioritised topics ...")
        if (len(p.split()) >= min_words and sum(c.isalpha() for c in p) > 0.6 * len(p)
                and re.search(r"[a-z][.;:]", p) and not re.match(r"(\d+\s+){3}", p)):
            out.append(p)
    return out
