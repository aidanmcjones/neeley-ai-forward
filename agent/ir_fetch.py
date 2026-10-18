"""Save one investor-relations document (transcript, slides, presentation, press release, annual report) verbatim.

Text is never paraphrased: the raw HTML or PDF is downloaded and converted mechanically, PDFs page by page with
    [[page 12 | printed 12]]
markers, so quotes and page cites can be checked against the source. Each save appends one row to
data/corpus/<group>/<TICKER>/sources.jsonl (merged into manifest.jsonl by agent.corpus_check).

Usage:
  python -m agent.ir_fetch URL --ticker BMY --rel transcripts/2026Q2_transcript.md --type transcript \
      --period 2026Q2 --quality official|third_party [--group companies|peers] [--keep-pdf]
"""

import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

from agent.corpus import COMPANIES, html_to_text, paged_text, render

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "corpus"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
MAX_BYTES = 50 * 1024 * 1024


def pdf_pages(data):
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, p in enumerate(reader.pages, 1):
        try:
            text = p.extract_text() or ""
        except Exception:
            text = ""
        pages.append((str(i), text.strip()))
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--rel", required=True, help="path inside the company folder, ending in .md")
    ap.add_argument("--type", required=True)
    ap.add_argument("--period", default="")
    ap.add_argument("--quality", choices=["official", "third_party"], required=True)
    ap.add_argument("--group")
    ap.add_argument("--keep-pdf", action="store_true", help="also commit the original PDF next to the text")
    a = ap.parse_args()

    group = a.group or COMPANIES.get(a.ticker.upper(), "peers")
    folder = OUT / group / a.ticker.upper()
    r = requests.get(a.url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=120)
    if r.status_code != 200:
        sys.exit(f"HTTP {r.status_code} for {a.url}")
    data = r.content
    if len(data) > MAX_BYTES:
        sys.exit(f"too large ({len(data) / 1e6:.0f} MB), not saved: {a.url}")
    is_pdf = data[:4] == b"%PDF"
    pages = pdf_pages(data) if is_pdf else paged_text(r.text)
    if sum(len(t) for _, t in pages) < 500:
        sys.exit(f"almost no text extracted ({'pdf' if is_pdf else 'html'}); likely a JS page or scanned PDF: {a.url}")

    retrieved = datetime.now(timezone.utc).isoformat()
    header = (f"<!-- source: {a.url}\n     ticker: {a.ticker.upper()}  type: {a.type}  period: {a.period}  "
              f"quality: {a.quality}  format: {'pdf' if is_pdf else 'html'}\n     retrieved: {retrieved}\n"
              f"     verbatim mechanical extraction; verify cited quotes against the source -->\n")
    body = render(pages, header)
    out = folder / a.rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    if is_pdf and a.keep_pdf:
        out.with_suffix(".pdf").write_bytes(data)

    row = {"doc_id": f"{a.ticker.upper()}:{a.rel}", "ticker": a.ticker.upper(), "group": group, "doc_type": a.type,
           "form": None, "filed": None, "period": a.period, "accession": None, "source_url": a.url,
           "retrieved_at": retrieved, "path": str(out.relative_to(ROOT)).replace("\\", "/"), "pages": len(pages),
           "pages_with_folio": len(pages) if is_pdf else sum(1 for f, _ in pages if f),
           "chars": sum(len(t) for _, t in pages), "sha256": hashlib.sha256(body.encode()).hexdigest(),
           "source_quality": a.quality, "sections": None}
    with (folder / "sources.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    print(f"saved {row['path']} ({len(pages)} pages, {row['chars']:,} chars)")


if __name__ == "__main__":
    main()
