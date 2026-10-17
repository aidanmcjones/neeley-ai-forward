"""Drop moat transcripts that duplicate a good corpus transcript; dedupe the calls manifest and gaps."""
import json

from agent.moat.common import OUT, ROOT

FIX = {("AZN", "2026Q1"), ("AZN", "2025Q3"), ("GILD", "2025Q3"), ("NVO", "2026Q1"), ("AMGN", "2025Q3")}
for p in sorted((OUT / "companies").glob("*/transcripts/*_transcript.md")):
    tk, q = p.parent.parent.name, p.name.split("_")[0]
    c = ROOT / "data" / "corpus" / "companies" / tk / "transcripts" / p.name
    if c.exists() and (tk, q) not in FIX:
        p.unlink()
        print("dropped duplicate", tk, q)
man = OUT / "manifests" / "calls.jsonl"
rows = {}
for l in man.read_text().splitlines():
    r = json.loads(l)
    rows[r["doc_id"]] = r
keep = [r for r in rows.values() if (ROOT / r["path"]).exists()]
man.write_text("".join(json.dumps(r) + "\n" for r in keep))
print("manifest rows", len(keep))
gp = OUT / "gaps" / "calls.jsonl"
g = {}
if gp.exists():
    for l in gp.read_text().splitlines():
        r = json.loads(l)
        g[(r["ticker"], r["item"])] = r
    gp.write_text("")
print("gaps cleared", len(g))
