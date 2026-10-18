"""File manually downloaded documents into the corpus.

Drop PDFs (or saved .html pages) into data/corpus/_inbox/ named
    <TICKER>_<kind>_<period>.pdf        e.g. BMY_slides_2026Q2.pdf, AMGN_transcript_2025Q3.pdf,
                                             LLY_presentation_2026-01-jpm.pdf, BOEHRINGER_report_annual-2025.pdf
kind: transcript | slides | presentation | report | press
Optional source tag before the extension: BMY_transcript_2026Q2_bloomberg.pdf (bloomberg, factset, capiq, refinitiv,
company). Anything from those sources is logged as official.

Each file is converted with page markers (same format as the rest of the corpus), the original PDF is kept next to
the text, a row goes into the company's sources.jsonl, and the inbox copy is removed. A transcript that replaces a
third-party copy keeps the old one as <period>_transcript_thirdparty.md.

Usage:  python -m agent.ingest_inbox            # process everything in the inbox
        python -m agent.ingest_inbox --dry-run  # show what would happen
"""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from agent.corpus import COMPANIES, paged_text, render
from agent.ir_fetch import pdf_pages

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
INBOX = CORPUS / "_inbox"
KINDS = {  # kind: (subfolder, rel suffix, doc_type)
    "transcript": ("transcripts", "transcript", "transcript"),
    "slides": ("presentations", "earnings_slides", "earnings_slides"),
    "presentation": ("presentations", "", "investor_presentation"),
    "report": ("reports", "", "annual_report_glossy"),
    "press": ("policy", "press", "press_release"),
}
SOURCES = {"bloomberg", "factset", "capiq", "refinitiv", "company"}
NAME = re.compile(r"^(?P<ticker>[A-Za-z]+)_(?P<kind>[a-z]+)_(?P<period>[A-Za-z0-9\-]+?)(?:_(?P<src>[a-z]+))?$")


def target(ticker, kind, period):
    sub, suffix, doc_type = KINDS[kind]
    if kind in ("transcript", "slides"):
        rel = f"{sub}/{period}_{suffix}.md"
    elif kind == "press":
        rel = f"{sub}/press_{period}.md"
    else:
        rel = f"{sub}/{period}.md"
    return rel, doc_type


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    INBOX.mkdir(parents=True, exist_ok=True)
    files = [p for p in sorted(INBOX.iterdir()) if p.suffix.lower() in (".pdf", ".html", ".htm")]
    if not files:
        print(f"inbox empty: {INBOX}")
        return
    for p in files:
        m = NAME.match(p.stem)
        if not m or m["kind"] not in KINDS or (m["src"] and m["src"] not in SOURCES):
            print(f"SKIP {p.name}: name must be TICKER_kind_period[_source].pdf, kind in {sorted(KINDS)}")
            continue
        ticker, kind, period = m["ticker"].upper(), m["kind"], m["period"]
        group = COMPANIES.get(ticker, "peers")
        folder = CORPUS / group / ticker
        rel, doc_type = target(ticker, kind, period)
        out = folder / rel
        data = p.read_bytes()
        is_pdf = data[:4] == b"%PDF"
        if a.dry_run:
            print(f"{p.name} -> {out.relative_to(ROOT)}{' (replaces existing)' if out.exists() else ''}")
            continue
        pages = pdf_pages(data) if is_pdf else paged_text(data.decode("utf-8", errors="replace"))
        chars = sum(len(t) for _, t in pages)
        if chars < 500:
            print(f"SKIP {p.name}: almost no text extracted (scanned PDF or empty page)")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if kind == "transcript" and out.exists():
            out.rename(out.with_name(out.stem + "_thirdparty.md"))
        src = m["src"] or "manual"
        retrieved = datetime.now(timezone.utc).isoformat()
        header = (f"<!-- source: manual download ({src}), file {p.name}\n     ticker: {ticker}  type: {doc_type}  "
                  f"period: {period}  quality: official\n     retrieved: {retrieved} -->\n")
        body = render(pages, header)
        out.write_text(body, encoding="utf-8")
        if is_pdf:
            out.with_suffix(".pdf").write_bytes(data)
        row = {"doc_id": f"{ticker}:{rel}", "ticker": ticker, "group": group, "doc_type": doc_type, "form": None,
               "filed": None, "period": period, "accession": None, "source_url": f"manual:{src}:{p.name}",
               "retrieved_at": retrieved, "path": str(out.relative_to(ROOT)).replace("\\", "/"),
               "pages": len(pages), "pages_with_folio": len(pages) if is_pdf else 0, "chars": chars,
               "sha256": hashlib.sha256(body.encode()).hexdigest(), "source_quality": "official", "sections": None}
        with (folder / "sources.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        p.unlink()
        print(f"OK   {p.name} -> {row['path']} ({len(pages)} pages)")
    print("\nnext: python -m agent.corpus_check   (refreshes manifest.csv and GAPS.md)")


if __name__ == "__main__":
    main()
