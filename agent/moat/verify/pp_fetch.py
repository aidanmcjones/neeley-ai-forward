"""Pipeline verifier: cache SEC companyfacts and submissions for every target_profiles CIK."""
import json
from pathlib import Path

import pandas as pd

from agent.tenk import sec_get

C = Path("data/moat/verify/pp_cache/sec")
C.mkdir(parents=True, exist_ok=True)
t = pd.read_csv("data/moat/tables/target_profiles.csv")
for cik in sorted(set(t.sponsor_cik.dropna().astype(int))):
    for kind, url in [("cf", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"),
                      ("sub", f"https://data.sec.gov/submissions/CIK{cik:010d}.json")]:
        f = C / f"{kind}_{cik}.json"
        if f.exists():
            continue
        try:
            f.write_text(json.dumps(sec_get(url, as_json=True)))
        except Exception as e:
            print(cik, kind, str(e)[:80])
print("done", len(list(C.glob("*.json"))))
