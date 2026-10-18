import json, re
import pandas as pd
from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap

S = "pricing"
W = "/Users/aidanjones/.claude/jobs/9174fb40/tmp/w/"
a = pd.read_csv(W + "ca_wac_all.csv", dtype=str)
def co(*names):
    out = None
    for n in names:
        out = a[n] if out is None else out.fillna(a[n])
    return out
d = pd.DataFrame({
    "manufacturer": co("manufacturer_name", "Manufacturer Name"), "ndc_raw": co("ndc", "NDC Number"),
    "product_desc": co("drug_prod_desc", "Drug Product Description"), "wac_effective_date": co("wac_effective_date", "WAC Effective Date"),
    "wac_increase_amount": co("wac_increase_amount", "WAC Increase Amount"), "wac_after_increase": co("wac_after_increase", "WAC After Increase"),
    "us_unit_sales": co("unit_sales_volume_us", "Unit Sales Volume in US"), "us_gross_sales_usd": co("gross_sales_volume_us_dollars", "Gross Sales (US Dollars)"),
    "cost_increase_factors": co("cost_increase_factors", "Cost Increase Factors"), "source": a["_file"], "_row": a["_row"]})
d["ndc_digits"] = d.ndc_raw.fillna("").str.replace(r"\D", "", regex=True)
ndcmap = json.load(open(W + "pricing_ndc.json"))
ndc9 = {}
for slug, v in ndcmap.items():
    for b in v["brand"]:
        ndc9.setdefault(b["ndc11"], set()).add(slug)
names = sorted(((v[0].upper(), k) for k, v in DRUGS.items()), key=lambda x: -len(x[0]))
def m(r):
    n = r.ndc_digits
    if len(n) == 11 and n in ndc9:
        return sorted(ndc9[n], key=lambda s: -len(DRUGS[s][0]))[0], "ndc11"
    desc = str(r.product_desc).upper()
    for nm, s in names:
        if re.match(re.escape(nm) + r"(?![A-Z])", desc):
            return s, "brand_name_prefix"
    return None, None
res = d.apply(m, axis=1, result_type="expand")
d["drug"], d["match_basis"] = res[0], res[1]
d = d[d.drug.notna()].copy()
d["source_row"] = "row=" + d["_row"].astype(str) + "|ndc=" + d.ndc_raw.astype(str) + "|wac_effective=" + d.wac_effective_date.astype(str)
d = d.drop(columns=["_row", "ndc_digits"])
d["wac_effective_date"] = pd.to_datetime(d.wac_effective_date, errors="coerce").dt.date
d = d.sort_values(["drug", "wac_effective_date"])
write(S, "tables/wac_increases.csv", d.to_csv(index=False), group="pricing", doc_type="table", source_url="https://data.chhs.ca.gov/dataset/prescription-drug-wholesale-acquisition-cost-wac-increases")
print(len(d), d.wac_effective_date.min(), d.wac_effective_date.max(), d.drug.nunique())
miss = [s for s in DRUGS if s not in set(d.drug)]
print("none:", miss)
for s in miss:
    note_gap(S, DRUGS[s][3], s, "no California HCAI WAC-increase report (increase below 16% three-year threshold or not reported)")
print(d.groupby("drug").size().to_string())
