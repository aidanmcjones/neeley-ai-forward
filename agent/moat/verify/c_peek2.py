import csv
from collections import Counter

from agent.moat.common import ROOT

rows = list(csv.DictReader((ROOT / "tables" / "qa_turns.csv").open()))
c = Counter(r["speaker"].strip() for r in rows if r["role"] == "analyst")
names = sorted(c, key=lambda s: (s.split()[-1].lower() if s.split() else "", s))
print(" ; ".join(f"{n}={c[n]}" for n in names if len(n) < 45))
print("LONG:", sum(1 for n in names if len(n) >= 45))
f = Counter(r["firm"].strip() for r in rows if r["role"] == "analyst")
print(" ; ".join(f"{k}={v}" for k, v in sorted(f.items()) if len(k) < 45))
