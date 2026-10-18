"""Restore files listed in a moat manifest from R2 (moat/<rel>.gz), checking sha256.

python -m agent.moat.onboard_restore <manifest stem> <path prefix>
e.g. python -m agent.moat.onboard_restore peers data/moat/companies/REGN/
"""
import gzip
import hashlib
import json
import sys

from agent.moat.common import OUT, ROOT, store


def main():
    stem, prefix = sys.argv[1], sys.argv[2]
    rows = {}
    for ln in (OUT / "manifests" / f"{stem}.jsonl").read_text().splitlines():
        if ln.strip():
            r = json.loads(ln)
            if str(r.get("path", "")).startswith(prefix):
                rows[r["path"]] = r  # later rows win
    ok = bad = miss = 0
    for path, r in sorted(rows.items()):
        p = ROOT / path
        rel = path[len("data/moat/"):]
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"]:
            ok += 1
            continue
        key = f"moat/{rel}" if rel.endswith(".gz") else f"moat/{rel}.gz"
        body = store().get(key)
        if body is None:
            miss += 1
            print("MISSING in R2", key)
            continue
        raw = body if rel.endswith(".gz") else gzip.decompress(body)
        if hashlib.sha256(raw).hexdigest() != r["sha256"]:
            bad += 1
            print("SHA MISMATCH", key)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        ok += 1
    print(f"restored/ok {ok}  sha mismatch {bad}  missing {miss}  of {len(rows)}")


if __name__ == "__main__":
    main()
