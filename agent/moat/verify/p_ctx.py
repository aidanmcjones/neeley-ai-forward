"""Policy verifier: re-locate each policy_exposure quote on its cited page and dump surrounding context."""
import csv
import sys

from agent.moat.common import ROOT
from agent.moat.policy_build import load, norm

rows = list(csv.DictReader(open(ROOT / "data/moat/tables/policy_exposure.csv")))
out = open(ROOT / "data/moat/verified/policy/_ctx.txt", "w")
force = sys.argv[1] if len(sys.argv) > 1 else None
for r in rows:
    if r["force"] == "manufacturing" and r["doc"].endswith(".csv"):
        continue
    url, pages = load(r["doc"])
    q = norm(r["quote"])
    hit = [(lab, b) for lab, b in pages if lab == r["printed_page_or_section"] and q in b]
    status = "PAGE_OK" if hit else "PAGE_MISS"
    ctx = ""
    if hit:
        b = hit[0][1]
        i = b.index(q)
        ctx = b[max(0, i - 300): i + len(q) + 300]
    out.write(f"=== {r['row_id']} {r['ticker']} {r['force']} | {r['item']} | value={r['value']} {r['unit']} | eff={r['effective_date']} | {status} p={r['printed_page_or_section']} | {r['doc']}\nQ: {r['quote']}\nCTX: {ctx}\n\n")
print("done")
