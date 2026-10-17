"""Throwaway survey of the corpus for the citation index build."""
import collections
import csv
import json
from pathlib import Path

from agent.findings import MARKER

ROOT = Path(__file__).resolve().parents[2]
rows = {}
src = collections.Counter()
for r in csv.DictReader(open(ROOT / "data/corpus/manifest.csv", encoding="utf-8")):
    rows[r["doc_id"]] = ("csv", r)
for p in [ROOT / "data/corpus/manifest.jsonl", *sorted((ROOT / "data/corpus").glob("*/*/sources.jsonl"))]:
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r["doc_id"] not in rows:
                src["new_from_" + p.name] += 1
            rows[r["doc_id"]] = ("jsonl", r)
moat = {}
for p in sorted((ROOT / "data/moat/manifests").glob("*.jsonl")):
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r["doc_id"] in moat:
                src["moat_dup"] += 1
            moat[r["doc_id"]] = r
print(src, len(rows), len(moat), "overlap", len(set(rows) & set(moat)))
ext = collections.Counter()
nomark = collections.Counter()
missing = 0
examples = {}
for k, (_, r) in list(rows.items()) + [(k, ("m", r)) for k, r in moat.items()]:
    p = ROOT / r["path"]
    e = p.suffix
    ext[(r.get("stream") or "corpus", e)] += 1
    if not p.exists():
        missing += 1
        continue
    if e == ".md":
        t = p.read_text(errors="ignore")
        if not MARKER.search(t):
            nomark[(r.get("stream") or "corpus", r["doc_type"])] += 1
            examples.setdefault(r["doc_type"], r["path"])
print("missing", missing)
for k, v in sorted(ext.items()):
    print(k, v)
print("no markers:")
for k, v in sorted(nomark.items()):
    print(k, v)
print(examples)
dt = collections.Counter((r.get("stream") or "corpus", r["doc_type"]) for r in moat.values())
print(dt)
