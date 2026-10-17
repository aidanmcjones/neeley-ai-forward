import re, sys
from agent.moat.secx_lib import *
from agent.moat.secx_agreements import exhibits
t = sys.argv[1]
cik = ciks()[t]
_, fs = filings(cik, "2025-01-01")
f = [x for x in fs if x["form"] in ("10-K", "20-F")][-1]
base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accession'].replace('-', '')}/"
raw = sec_get(base + f["primary_doc"])
for e in exhibits(raw, base, cik):
    print(e["exhibit"], "|", e["title"][:110], "|", e["url"][-60:])
