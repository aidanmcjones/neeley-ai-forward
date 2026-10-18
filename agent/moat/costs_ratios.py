import csv
from collections import defaultdict
d = defaultdict(dict)
for r in csv.DictReader(open("data/moat/tables/company_cost_structure.csv")):
    m = r["metric"]
    if m == "headcount_text":
        m = "headcount"
    if m == "advertising_text":
        m = "advertising"
    if m in ("revenue", "sga", "rnd", "advertising", "headcount", "cost_of_sales", "capex", "selling_and_marketing"):
        d[(r["ticker"], int(r["fiscal_year"]))][m] = (float(r["value"]), r["unit"])
TEN = "MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD".split()
for tk in TEN:
    out = []
    for fy in range(2021, 2026):
        x = d.get((tk, fy), {})
        rev, sga, rnd, adv, hc = (x.get(k, (None,))[0] for k in ("revenue", "sga", "rnd", "advertising", "headcount"))
        def pct(a):
            return f"{100 * a / rev:.1f}%" if a and rev else "-"
        per = f"{sga / hc / 1e3:.0f}k" if sga and hc and x.get("sga", ("", ""))[1] == "USD" else "-"
        out.append(f"{fy}: rev {rev / 1e9 if rev else 0:.1f}B {x.get('revenue', ('', ''))[1]} SGA {pct(sga)} R&D {pct(rnd)} adv {pct(adv)} SGA/emp {per}")
    print(tk)
    print("  " + "\n  ".join(out))
