"""Mine earnings-call transcripts for launch-investment, DTC and field-force statements. Output: data/moat/scratch/costs_calls.json"""
import csv
import json
import re

PAGE = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")
TURN = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*)$")
A = re.compile(r"\blaunch(?:es|ing|ed)?\b", re.I)
B = re.compile(r"\binvest(?:ment|ments|ing)?\b|\bspend(?:ing)?\b|\bDTC\b|direct[- ]to[- ]consumer|field force|sales ?force|sales representatives|\breps\b|\bheadcount\b|commercial (?:infrastructure|capacity)", re.I)
C = re.compile(r"\$\s?\d|\b\d+(?:\.\d+)? ?(?:%|percent|billion|million|reps|representatives)|\bdouble|\btriple|\badd(?:ing|ed)?\b.{0,30}\b(?:reps|representatives|sales)", re.I)
out = []
for r in csv.DictReader(open("data/moat/tables/transcripts_index.csv")):
    f = r["path"]
    try:
        txt = open(f, errors="ignore").read()
    except OSError:
        continue
    page, n = "1", 0
    cand = []
    for ln in txt.split("\n"):
        pm = PAGE.match(ln.strip())
        if pm:
            page = pm.group(1)
            continue
        m = TURN.match(ln.strip())
        if not m:
            continue
        spk, body = m.group(1), m.group(2)
        if re.match(r"operator", spk, re.I):
            continue
        for s in re.split(r"(?<=[.?!])\s+(?=[A-Z])", body):
            if (A.search(s) and B.search(s) or re.search(r"\bDTC\b|direct[- ]to[- ]consumer|field force|sales force|sales representatives", s, re.I)) and 60 < len(s) < 800:
                cand.append((0 if C.search(s) else 1, {"ticker": r["ticker"], "quarter": r["quarter"], "call_date": r["call_date"], "speaker": spk, "quote": s.strip(), "file": f, "page": page,
                            "source_url": r["source_url"]}))
    cand.sort(key=lambda x: x[0])
    out += [c[1] for c in cand[:5]]
json.dump(out, open("data/moat/scratch/costs_calls.json", "w"))
print(len(out))
from collections import Counter
print(Counter(o["ticker"] for o in out))
