"""Upload label version docs and verified product tables to R2 (gzip, same key scheme as common.write)."""
import gzip
import sys
from pathlib import Path

from agent.moat.common import OUT, store


def main():
    s = store()
    if s.kind != "r2":
        print("store is not r2:", s.kind)
        sys.exit(1)
    files = sorted(OUT.glob("drugs/*/label_v*.md")) + sorted(p for p in (OUT / "verified/product").glob("*") if p.is_file())
    n = 0
    for p in files:
        rel = p.relative_to(OUT).as_posix()
        s.put(f"moat/{rel}.gz", gzip.compress(p.read_bytes()), "application/gzip")
        n += 1
        if n % 100 == 0:
            print(n, flush=True)
    print("uploaded", n)
    probe = files[0].relative_to(OUT).as_posix()
    back = s.get(f"moat/{probe}.gz")
    print("roundtrip", probe, back is not None and gzip.decompress(back) == files[0].read_bytes())


main()
