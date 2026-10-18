"""Summaries of verified vs collector analyst_topics; prints example quotes for a topic if given."""
import csv
import sys
from collections import defaultdict
from agent.moat.verify.m_qa import ROOT

V = list(csv.DictReader(open(ROOT / "data/moat/verified/market/analyst_topics.csv")))
C = list(csv.DictReader(open(ROOT / "data/moat/tables/analyst_topics.csv")))
if len(sys.argv) > 1:
    for r in V:
        if r["topic"] == sys.argv[1] and int(r["turns_with_topic"]) and (len(sys.argv) < 3 or r["ticker"] == sys.argv[2]):
            print(r["ticker"], r["quarter"], r["turns_with_topic"], r["example_speaker"][:25], "|", r["example_quote"][:230])
    sys.exit()
cq = {(r["ticker"], r["quarter"]) for r in C}
same = [r for r in V if (r["ticker"], r["quarter"]) in cq]
print("collector company-quarters", len(cq), "verified", len({(r['ticker'], r['quarter']) for r in V}))
print("collector analyst turns total", sum(int(r["analyst_turns"]) for r in C if r["topic"] == "MFN"),
      "verified same quarters", sum(int(r["analyst_turns"]) for r in same if r["topic"] == "MFN"))
zero_c = [k for k in cq if any(int(r["analyst_turns"]) < 3 for r in C if (r["ticker"], r["quarter"]) == k)]
print("collector calls with <3 analyst turns", sorted(zero_c))
ch = defaultdict(int)
nz = 0
for r in same:
    d = r["delta_vs_collector"]
    if d not in ("", "0"):
        ch[r["topic"]] += 1
    if (int(r["turns_with_topic"]) > 0) != (int(r["collector_turns_with_topic"] or 0) > 0):
        nz += 1
print("cells changed by topic (same quarters):", dict(ch), "total", sum(ch.values()), "of", len(same))
print("cells flipping zero/nonzero:", nz)
agg = defaultdict(lambda: [0, 0, 0])
for r in V:
    a = agg[(r["ticker"], r["topic"])]
    a[0] += 1
    a[1] += int(r["turns_with_topic"]) > 0
    a[2] += int(r["turns_with_topic"])
tks = sorted({r["ticker"] for r in V})
tops = list(dict.fromkeys(r["topic"] for r in V))
print("ticker  " + " ".join(f"{t[:9]:>10}" for t in tops))
for tk in tks:
    print(f"{tk:7} " + " ".join(f"{agg[(tk, t)][1]:>3}/{agg[(tk, t)][0]:<2}({agg[(tk, t)][2]:>3})" for t in tops))
