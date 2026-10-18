"""Cache SEC submissions (filing date, form, period, primary doc, description) for the 10 filers."""
import json, os
os.environ.setdefault("SEC_USER_AGENT", "Neeley AI Forward hackathon aidan@justinianhq.com")
import agent.tenk
agent.tenk.MIN_INTERVAL = 0.5
from agent.corpus import filings

CIKS = {"MRK": 310158, "BMY": 14272, "PFE": 78003, "LLY": 59478, "ABBV": 1551152, "JNJ": 200406, "AMGN": 318154,
        "GILD": 882095, "NVO": 353278, "AZN": 901832}
out = {}
for t, cik in CIKS.items():
    _, fs = filings(cik, "2021-01-01")
    for f in fs:
        out[f["accession"]] = dict(f, ticker=t, cik=cik)
json.dump(out, open("data/moat/scratch/f_subs.json", "w"))
print(len(out))
