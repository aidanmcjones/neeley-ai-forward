import csv
import sys
from collections import Counter, defaultdict

from agent.moat.common import ROOT

rows = list(csv.DictReader((ROOT / "tables" / "qa_turns.csv").open()))
print(len(rows))
by = defaultdict(Counter)
for r in rows:
    by[(r["ticker"], r["role"])][(r["speaker"], r["firm"])] += 1
want = sys.argv[1] if len(sys.argv) > 1 else None
for (t, role), c in sorted(by.items()):
    if want and t != want:
        continue
    print("==", t, role, len(c))
    for (s, f), n in c.most_common():
        print(f"   {n:4d} {s!r} | {f!r}")
