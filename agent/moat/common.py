"""Shared writer for the moat dataset: every document and table lands in the same place, format and manifest.

Documents: page-marked markdown like data/corpus ("[[page 47 | printed 39]]" before each page), with a header
comment carrying the source URL and retrieval time. Tables: CSV with a `source` column (URL or R2 key) and a
`source_row` column (row key in that source), so every number can be cited.

Each document is written to data/moat/<rel> (gitignored) and to R2 moat/<rel>. Each workstream appends rows to
its own manifest, data/moat/manifests/<stream>.jsonl, with the same columns as data/corpus/manifest.csv plus
`stream`. agent/moat/index.py merges them.
"""

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.tenk import Store

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "moat"
MANIFEST_COLS = ["doc_id", "ticker", "group", "doc_type", "form", "period", "filed", "source_quality", "pages",
                 "pages_with_folio", "chars", "path", "source_url", "retrieved_at", "sha256", "stream"]
_store = None


def store():
    global _store
    if _store is None:
        _store = Store()
    return _store


def now():
    return datetime.now(timezone.utc).isoformat()


def header(source_url, **meta):
    fields = " ".join(f"{k}={v}" for k, v in meta.items() if v is not None)
    return f"<!-- source: {source_url} | retrieved: {now()} | {fields} -->\n"


def write(stream, rel, data, *, ticker=None, group=None, doc_type=None, form=None, period=None, filed=None,
          source_url=None, quality="official", pages=None, pages_with_folio=None, upload=True):
    """Write one document or table. `rel` is relative to data/moat (e.g. companies/BMY/10q_2024Q2.md)."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    if upload and store().kind == "r2":
        body = raw if rel.endswith(".gz") else gzip.compress(raw)
        key = f"moat/{rel}" if rel.endswith(".gz") else f"moat/{rel}.gz"
        store().put(key, body, "application/gzip")
    row = {"doc_id": f"{ticker or group}:{rel}", "ticker": ticker, "group": group, "doc_type": doc_type,
           "form": form, "period": period, "filed": filed, "source_quality": quality, "pages": pages,
           "pages_with_folio": pages_with_folio, "chars": len(raw), "path": f"data/moat/{rel}",
           "source_url": source_url, "retrieved_at": now(), "sha256": hashlib.sha256(raw).hexdigest(),
           "stream": stream}
    man = OUT / "manifests" / f"{stream}.jsonl"
    man.parent.mkdir(parents=True, exist_ok=True)
    with man.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def note_gap(stream, ticker, item, reason):
    """Record something expected that could not be collected (merged into data/moat/GAPS.md)."""
    gap = OUT / "gaps" / f"{stream}.jsonl"
    gap.parent.mkdir(parents=True, exist_ok=True)
    with gap.open("a") as f:
        f.write(json.dumps({"ticker": ticker, "item": item, "reason": reason, "at": now()}) + "\n")
