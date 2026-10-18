"""Peek helper for wave-3 peers verification: print lines a..b of a file (non-blank), optionally grep."""
import sys
from pathlib import Path
p = Path(sys.argv[1]); a = int(sys.argv[2]); b = int(sys.argv[3]); pat = sys.argv[4] if len(sys.argv) > 4 else None
L = p.read_text(errors="replace").split("\n")
print("nlines", len(L))
if pat:
    for i, l in enumerate(L, 1):
        if pat.lower() in l.lower():
            print(i, l[:200])
else:
    for i in range(a, min(b, len(L)) + 1):
        if L[i - 1].strip():
            print(i, L[i - 1][:200])
