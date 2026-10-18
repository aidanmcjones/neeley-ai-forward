"""Peers: cleaned manifest (drop rows whose file no longer exists, dedupe by path keeping the last write)."""
import json

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT


def main():
    rows = [json.loads(l) for l in (ROOT / "data/moat/manifests/peers.jsonl").read_text().splitlines() if l.strip()]
    gone = [r for r in rows if not (ROOT / r["path"]).exists()]
    live = [r for r in rows if (ROOT / r["path"]).exists()]
    last = {}
    for r in live:
        last[r["path"]] = r
    clean = list(last.values())
    tiny = [r for r in clean if (r.get("chars") or 0) < 2000 and r.get("doc_type") != "table"]
    print(f"manifest rows {len(rows)}; path missing {len(gone)}; duplicate path rows {len(live) - len(clean)}; "
          f"clean {len(clean)}; remaining docs under 2,000 chars {len(tiny)}")
    for r in tiny[:10]:
        print("  tiny:", r["path"], r.get("chars"))
    write("verify_peers", "verified/peers/manifest_clean.jsonl", "".join(json.dumps(r) + "\n" for r in clean),
          group="manifest", doc_type="manifest", quality="verified", source_url="data/moat/manifests/peers.jsonl")
    return dict(rows=len(rows), missing=len(gone), dup=len(live) - len(clean), clean=len(clean), tiny=len(tiny),
                missing_examples=[r["path"] for r in gone[:5]])


if __name__ == "__main__":
    print(main())
