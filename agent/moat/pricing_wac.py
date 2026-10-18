"""California HCAI WAC increase reports (2019..Sep 2026) filtered to the 52 drugs (brand name or NDC-9 from openFDA map)."""
import io, json, requests
import pandas as pd
from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap

S = "pricing"
PKG = "https://data.chhs.ca.gov/api/3/action/package_show?id=prescription-drug-wholesale-acquisition-cost-wac-increases"
res = requests.get(PKG, timeout=60).json()["result"]["resources"]
ndcmap = json.load(open("/Users/aidanjones/.claude/jobs/9174fb40/tmp/w/pricing_ndc.json"))
ndc9 = {}
for slug, v in ndcmap.items():
    for b in v["brand"]:
        ndc9[b["ndc11"][:9]] = slug
names = sorted(((v[0].upper(), k) for k, v in DRUGS.items()), key=lambda x: -len(x[0]))
frames = []
for r in res:
    n = r["name"]
    if "5 Year" in n or "Dictionary" in n or "Diabetes" in n:
        continue
    if not (n.startswith("Q1-Q4") or (r["format"] == "CSV" and "Monthly" in n)):
        continue
    raw = requests.get(r["url"], timeout=180).content
    df = pd.read_csv(io.BytesIO(raw), dtype=str) if r["format"] == "CSV" else pd.read_excel(io.BytesIO(raw), dtype=str)
    df["_file"] = r["url"]
    df["_row"] = range(2, len(df) + 2)
    print(n, len(df), list(df.columns)[:12], flush=True)
    frames.append(df)
all_ = pd.concat(frames, ignore_index=True)
all_.to_csv("/Users/aidanjones/.claude/jobs/9174fb40/tmp/w/ca_wac_all.csv", index=False)
cols = {c.lower(): c for c in all_.columns}
print(list(all_.columns))
