"""Show, for each of the 24 price-to-revenue rows, the revenue sentence the collector used (re-run of its rule)."""
import re
import pandas as pd
from agent.moat.common import OUT
from agent.moat.deals_lib import amounts, sentences

d = pd.read_csv(OUT / "tables" / "deal_comps.csv")
b = pd.read_csv(OUT / "tables" / "deal_benchmarks.csv")
ids = b[b.metric == "price_to_trailing_revenue_x"].row_ids.iloc[0].split()
for i in ids:
    r = d[d.deal_id == i].iloc[0]
    t = re.sub(r"\s+", " ", (OUT / "deals" / r.source_row.split(" ")[0]).read_text())
    revs = []
    for s in sentences(t):
        if re.search(r"(?:net )?(?:revenue|sales)", s, re.I) and re.search(r"20(?:19|2\d)|trailing|last twelve|annual", s, re.I) and not re.search(r"peak|expected|project|forecast|potential|anticipate", s, re.I):
            for v, _, _ in amounts(s):
                if v >= 1:
                    revs.append((v, s))
    v, s = revs[0] if revs else (None, "")
    print(f"## {i} {r.date} tot={r.total_potential_usd_m} rev={v} x={r.total_potential_usd_m / v if v else None:.2f} | {r.source_row.split()[0]}")
    print("   S:", s[:330])
