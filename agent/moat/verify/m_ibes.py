"""IBES sanity: tickers per company, currencies, FY1 mapping, latest FY2026 revenue consensus."""
import csv
from collections import defaultdict
from agent.moat.verify.m_qa import ROOT

T = ROOT / "data/moat/tables"
rev = list(csv.DictReader(open(T / "ibes_revenue_consensus.csv")))
eps = list(csv.DictReader(open(T / "ibes_eps_consensus.csv")))
print("rev cols", list(rev[0].keys()))
print("eps cols", list(eps[0].keys()))
by = defaultdict(set)
for r in rev:
    by[r["oftic"]].add((r["ticker"], r["curcode"], r["measure"]))
for k, v in sorted(by.items()):
    print("REV", k, sorted(v))
by = defaultdict(set)
for r in eps:
    by[r["oftic"]].add((r["ticker"], r.get("curcode", "")))
for k, v in sorted(by.items()):
    print("EPS", k, sorted(v)[:6])
# FY1 mapping at latest statpers
last = {}
for r in rev:
    if r["measure"] == "SAL" and r["fpi"] == "1":
        k = (r["oftic"], r["ticker"])
        if k not in last or r["statpers"] > last[k]["statpers"]:
            last[k] = r
for k, r in sorted(last.items()):
    print("SAL FY1 latest", k, r["statpers"], r["fpedats"], r["numest"], r["meanest"], r["medest"], r["lowest"], r["highest"], r["curcode"])
last = {}
for r in eps:
    if r["fpi"] == "1":
        k = (r["oftic"], r["ticker"])
        if k not in last or r["statpers"] > last[k]["statpers"]:
            last[k] = r
for k, r in sorted(last.items()):
    print("EPS FY1 latest", k, r["statpers"], r["fpedats"], r["numest"], r["meanest"], r.get("curcode", ""))
