"""List the table headers that govern each wave-3 product revenue row (nearest preceding header line)."""
import re
import sys
from collections import Counter
import pandas as pd
from agent.moat.verify.pe_lib import ROOT

HDR = {"SNY": re.compile(r"(€ million|net sales by GBU|Appendix 1)", re.I),
       "GSK": re.compile(r"turnover\s*[–-]\s*(year|three|six|nine|quarter)", re.I),
       "TAK": re.compile(r"(April|July|October|January)\s*[-–]\s*\w+|Revenue", re.I)}
tk = sys.argv[1]
d = pd.read_csv(ROOT / "data/moat/tables/peer_product_revenue_wave3.csv")
d = d[d.ticker == tk]
c = Counter()
cache = {}
for _, r in d.iterrows():
    L = cache.setdefault(r.source_path, (ROOT / r.source_path).read_text(errors="replace").split("\n"))
    ln = int(re.match(r"line (\d+)", r.source_row).group(1))
    h = next((L[i].strip()[:110] for i in range(ln - 1, -1, -1) if HDR[r.ticker].search(L[i])), None)
    c[(r.fiscal_year, r.doc, h)] += 1
for k, v in sorted(c.items(), key=lambda x: (str(x[0][1]), str(x[0][0]))):
    print(v, k)
