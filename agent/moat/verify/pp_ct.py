"""Pipeline verifier item 1: draw a 150-trial sample stratified by indication x phase and re-pull each from CT.gov v2."""
import json
import time
from pathlib import Path

import pandas as pd
import requests

C = Path("data/moat/verify/pp_cache/ct")
C.mkdir(parents=True, exist_ok=True)
d = pd.read_csv("data/moat/tables/pipeline_landscape.csv")
d["stratum"] = d.primary_indication.fillna("none") + " | " + d.phase
# 6 per indication (24 indications = 144) spread over phases, then 6 more from the largest strata
rows = []
for ind, g in d.groupby("primary_indication"):
    per = []
    phases = g.phase.unique().tolist()
    for i in range(6):
        ph = phases[i % len(phases)]
        pool = g[(g.phase == ph) & ~g.nct_id.isin([r for r in per])]
        if pool.empty:
            pool = g[~g.nct_id.isin(per)]
        per.append(pool.sample(1, random_state=17 + i).nct_id.iloc[0])
    rows += per
extra = d[~d.nct_id.isin(rows)].sample(150 - len(rows), random_state=5).nct_id.tolist()
rows += extra
pd.Series(rows, name="nct_id").to_csv("data/moat/verify/pp_cache/ct_sample.csv", index=False)
for n in rows:
    f = C / f"{n}.json"
    if f.exists():
        continue
    for a in range(3):
        try:
            r = requests.get(f"https://clinicaltrials.gov/api/v2/studies/{n}", timeout=30)
            if r.status_code == 200:
                f.write_text(r.text)
                break
        except Exception:
            pass
        time.sleep(1 + a)
    time.sleep(0.25)
print(len(rows), len(list(C.glob("*.json"))))
