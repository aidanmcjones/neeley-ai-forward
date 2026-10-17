"""Stratified re-fetch of pricing rows against the raw sources. Writes data/moat/verified/pricing/sample_checks.csv."""
import csv
import glob
import io
import json
import random
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

T = "data/moat/tables/"
V = Path("data/moat/verified/pricing")
H = {"User-Agent": "Neeley AI Forward hackathon"}
random.seed(17)
out = []


def add(table, key, ours, src, url, tol=0.005):
    try:
        a, b = float(ours), float(src)
        ok = abs(a - b) <= tol * max(1, abs(b))
    except (TypeError, ValueError):
        ok = str(ours).strip() == str(src).strip()
    out.append(dict(table=table, key=key, ours=ours, source=src, match=ok, source_url=url))


def get(url, params=None):
    for i in range(4):
        try:
            r = requests.get(url, params=params, headers=H, timeout=120)
            r.raise_for_status()
            return r
        except Exception:
            time.sleep(3 * (i + 1))
    return None


# ---------------- ASP: fresh CMS zips in /tmp/pvraw/asp
QMAP = {"january": "Q1", "april": "Q2", "july": "Q3", "october": "Q4"}
asp = pd.read_csv(T + "partb_asp_quarterly.csv")
fresh = {}
for f in glob.glob("/tmp/pvraw/asp/*.zip"):
    name = f.split("/")[-1]
    q = name.split("-")[1] + QMAP[name.split("-")[0]]
    z = zipfile.ZipFile(f)
    for n in z.namelist():
        if not n.lower().endswith(".csv") or "crosswalk" in n.lower() or "noc" in n.lower():
            continue
        rows = list(csv.reader(io.TextIOWrapper(z.open(n), encoding="latin-1")))
        hi = next((i for i, r in enumerate(rows) if r and r[0].strip().upper().startswith("HCPCS") and any("payment limit" in c.lower() for c in r)), None)
        if hi is None:
            continue
        pl = next(i for i, c in enumerate(rows[hi]) if "payment limit" in c.lower())
        for r in rows[hi + 1:]:
            if r and r[0].strip():
                fresh.setdefault(q, {})[r[0].strip()] = (r[pl].strip(), f"https://www.cms.gov/files/zip/{name}:{n}")
        break
codes = sorted(asp.hcpcs.unique())
pick = []
for c in codes:  # every HCPCS once, in a quarter we have fresh, then fill to 60
    s = asp[(asp.hcpcs == c) & asp.quarter.isin(fresh)]
    if len(s):
        pick.append(s.sample(1, random_state=1).index[0])
rest = asp[asp.quarter.isin(fresh) & ~asp.index.isin(pick)]
pick += list(rest.sample(min(60 - len(pick), len(rest)), random_state=2).index)
for i in pick:
    r = asp.loc[i]
    v = fresh[r.quarter].get(r.hcpcs)
    add("partb_asp_quarterly", f"{r.hcpcs}|{r.quarter}", r.payment_limit, v[0] if v else "MISSING", v[1] if v else "", tol=0.0005)
missing_codes = [c for c in codes if not any(c in fresh[q] for q in fresh if (asp[(asp.hcpcs == c)].quarter == q).any())]
print("ASP codes with no fresh quarter:", missing_codes)

# ---------------- NADAC via datastore
NADAC = {2020: "c933dc16-7de9-52b6-8971-4b75992673e0", 2021: "d5eaf378-dcef-5779-83de-acdd8347d68e", 2022: "dfa2ab14-06c2-457a-9e36-5cb6d80f8d93",
         2023: "4a00010a-132b-4e4d-a611-543c9521280f", 2024: "99315a95-37ac-4eee-946a-3c523b4c481e", 2025: "f38d0706-1239-442c-a3cc-40ef1b686ac0",
         2026: "fbb83258-11c7-47f5-8b18-5f8e79f7e704"}
BASE = "https://data.medicaid.gov/api/1/datastore/query/{ds}/0"


def ds_query(ds, conds):
    p = {"limit": 50}
    for i, (k, v) in enumerate(conds):
        p[f"conditions[{i}][property]"] = k
        p[f"conditions[{i}][value]"] = v
        p[f"conditions[{i}][operator]"] = "="
    r = get(BASE.format(ds=ds), p)
    return r.json().get("results", []) if r else None


nad = pd.read_csv(T + "nadac_history.csv", dtype={"ndc": str})
ns = nad.sample(frac=1, random_state=3).drop_duplicates(["drug", "year_dataset"]).sample(60, random_state=4)
for _, r in ns.iterrows():
    res = ds_query(NADAC[int(r.year_dataset)], [("ndc", r.ndc), ("as_of_date", r.as_of_date)])
    v = "FETCH_FAIL" if res is None else (res[0]["nadac_per_unit"] if res else "MISSING")
    if res and len(res) > 1:
        v = next((x["nadac_per_unit"] for x in res if x.get("effective_date") == r.effective_date), res[0]["nadac_per_unit"])
    add("nadac_history", f"{r.ndc}|{r.as_of_date}", r.nadac_per_unit, v, f"https://data.medicaid.gov/dataset/{NADAC[int(r.year_dataset)]}", tol=1e-6)
print("nadac done", len(out))

# ---------------- SDUD
SDUD = {2020: "cc318bfb-a9b2-55f3-a924-d47376b32ea3", 2021: "eec7fbe6-c4c4-5915-b3d0-be5828ef4e9d", 2022: "200c2cba-e58d-4a95-aa60-14b99736808d",
        2023: "d890d3a9-6b00-43fd-8b31-fcba4c8e2909", 2024: "61729e5a-7aa8-448c-8903-ba3e0cd0ea3c", 2025: "158a1baa-5506-400a-8ec3-97756f0b0536",
        2026: "2957a7f9-9a15-453e-9afd-3bbdcbac8fd3"}
sd = pd.read_csv(T + "medicaid_sdud.csv", dtype={"ndc": str})
sd = sd[sd.drug != "drug"]
ss = sd.sample(40, random_state=5)
for _, r in ss.iterrows():
    res = ds_query(SDUD[int(r.year)], [("ndc", r.ndc), ("state", "XX"), ("quarter", str(int(r.quarter))), ("utilization_type", r.utilization_type)])
    if res is None:
        add("medicaid_sdud", f"{r.ndc}|{r.year}Q{r.quarter}|{r.utilization_type}", r.units_reimbursed, "FETCH_FAIL", "")
        continue
    x = res[0] if res else {}
    url = f"https://data.medicaid.gov/dataset/{SDUD[int(r.year)]}"
    add("medicaid_sdud", f"{r.ndc}|{r.year}Q{r.quarter}|{r.utilization_type}|units", r.units_reimbursed, x.get("units_reimbursed", "MISSING"), url)
    add("medicaid_sdud", f"{r.ndc}|{r.year}Q{r.quarter}|{r.utilization_type}|total_amount", r.total_amount_reimbursed, x.get("total_amount_reimbursed", "MISSING"), url)
print("sdud done", len(out))

# ---------------- Part D (CMS API, DY2024 file with 2020-2024 wide columns): all Overall rows for the 20 highest-spend brands
pdd = pd.read_csv(T + "partd_by_year.csv")
ov = pdd[(pdd.mftr == "Overall") & (pdd.grain == "year")]
top = ov[ov.period.astype(str) == "2024"].sort_values("total_spend", ascending=False).brand.drop_duplicates().head(20)
API = "https://data.cms.gov/data-api/v1/dataset/7e0b4365-fd63-4a29-8f5e-e0ac9f66a81b/data"
outlier_bad = []
for b in top:
    r = get(API, {"filter[Brnd_Name]": b, "size": 50})
    js = [x for x in (r.json() if r else []) if x["Mftr_Name"] == "Overall"]
    src = js[0] if js else {}
    for _, o in ov[ov.brand == b].iterrows():
        y = str(int(o.period))
        for col, f in [("total_spend", "Tot_Spndng_"), ("dosage_units", "Tot_Dsg_Unts_"), ("claims", "Tot_Clms_"), ("spend_per_unit", "Avg_Spnd_Per_Dsg_Unt_Wghtd_")]:
            add("partd_by_year", f"{b}|Overall|{y}|{col}", "" if pd.isna(o[col]) else o[col], src.get(f + y, "MISSING") or "", API + f"?filter[Brnd_Name]={b}")
        flag = src.get("Outlier_Flag_" + y)
        if flag == "1":
            outlier_bad.append((b, y, o.outlier))
print("partd done", len(out), "CMS outlier-flagged rows:", outlier_bad)

# ---------------- WAC: 30 rows against the HCAI 2020 and 2023 files in /tmp/pvraw/wac
wac = pd.read_csv(T + "wac_increases.csv", dtype={"ndc_raw": str})
for yr, f in [("2020", "/tmp/pvraw/wac/w2020.xlsx"), ("2023", "/tmp/pvraw/wac/w2023.xlsx")]:
    x = pd.read_excel(f, header=None, dtype=str)
    hi = x.index[x.apply(lambda r: r.astype(str).str.contains("NDC Number").any(), axis=1)][0]
    raw = x.iloc[hi + 1:].reset_index(drop=True)
    sub = wac[wac.source.str.contains(f"q1-q4-{yr}-")].sample(15, random_state=6)
    for _, r in sub.iterrows():
        m = raw[(raw[1].astype(str).str.replace(r"\D", "", regex=True) == r.ndc_raw) &
                (pd.to_datetime(raw[3], errors="coerce").dt.strftime("%Y-%m-%d") == r.wac_effective_date)]
        if not len(m):
            add("wac_increases", f"{r.ndc_raw}|{r.wac_effective_date}", r.wac_after_increase, "MISSING", r.source)
            continue
        m = m.iloc[0]
        if yr == "2020":  # header says col4 = increase amount, col5 = WAC after, but data rows carry an extra year column
            add("wac_increases", f"{r.ndc_raw}|{r.wac_effective_date}|cols4-6_raw", f"{r.wac_increase_amount}|{r.wac_after_increase}", f"{m[4]}|{m[5]}|{m[6]}", r.source)
        else:
            add("wac_increases", f"{r.ndc_raw}|{r.wac_effective_date}|increase", r.wac_increase_amount, m[4], r.source)
            add("wac_increases", f"{r.ndc_raw}|{r.wac_effective_date}|wac_after", r.wac_after_increase, m[5], r.source)

df = pd.DataFrame(out)
df.to_csv(V / "sample_checks.csv", index=False)
print(df.groupby("table").match.agg(["sum", "count"]))
print(df[~df.match].head(40).to_string())
