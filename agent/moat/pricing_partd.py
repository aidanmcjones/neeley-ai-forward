import gzip, io
import pandas as pd
from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap, store

S = "pricing"
names = {v[0].upper(): k for k, v in DRUGS.items()}
D = pd.read_csv("data/external/partd_spending_dy24.csv")
D["k"] = D.Brnd_Name.str.upper().str.strip()
import re
def match(k):
    best = None
    if not isinstance(k, str):
        return None
    for n in names:
        if re.match(re.escape(n) + r"(?![A-Z0-9])", k) and (best is None or len(n) > len(best)):
            best = n
    return best
D["m"] = D.k.map(match); D = D[D.m.notna()]
rows = []
for i, r in D.iterrows():
    for y in range(2020, 2025):
        rows.append(dict(drug=names[r.m], brand=r.Brnd_Name, generic=r.Gnrc_Name, mftr=r.Mftr_Name, tot_mftr=r.Tot_Mftr,
            period=str(y), grain="year", total_spend=r[f"Tot_Spndng_{y}"], dosage_units=r[f"Tot_Dsg_Unts_{y}"],
            claims=r[f"Tot_Clms_{y}"], benes=r[f"Tot_Benes_{y}"], spend_per_unit=r[f"Avg_Spnd_Per_Dsg_Unt_Wghtd_{y}"],
            spend_per_claim=r[f"Avg_Spnd_Per_Clm_{y}"], outlier=r[f"Outlier_Flag_{y}"],
            source="https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug (R2 public/partd_spending_dy24.csv)",
            source_row=f"Brnd_Name={r.Brnd_Name}|Mftr_Name={r.Mftr_Name}|DY{y}"))
Q = pd.read_csv(io.BytesIO(gzip.decompress(store().get("public/partd_quarterly_2025.csv.gz"))))
print(Q.columns.tolist(), len(Q)); print(Q.head(3).to_string())
Q["k"] = Q.Brnd_Name.str.upper().str.strip()
Q["m"] = Q.k.map(match); Q = Q[Q.m.notna()]
for i, r in Q.iterrows():
    rows.append(dict(drug=names[r.m], brand=r.Brnd_Name, generic=r.Gnrc_Name, mftr=r.Mftr_Name, tot_mftr=r.Tot_Mftr,
        period=str(r.Year), grain="quarterly_2025_file", total_spend=r.Tot_Spndng, claims=r.Tot_Clms, benes=r.Tot_Benes,
        spend_per_claim=r.Avg_Spnd_Per_Clm, source="https://data.cms.gov/sites/default/files/2026-07/QDD_PTD_RQ2603_P01_V10_DQT2601_20260708.csv (R2 public/partd_quarterly_2025.csv.gz)",
        source_row=f"Brnd_Name={r.Brnd_Name}|Mftr_Name={r.Mftr_Name}|Year={r.Year}"))
df = pd.DataFrame(rows)
write(S, "tables/partd_by_year.csv", df.to_csv(index=False), group="pricing", doc_type="table", source_url="https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug")
got = set(df.drug)
miss = [d for d in DRUGS if d not in got]
print(len(df), "rows; no match:", miss)
for d in miss: note_gap(S, DRUGS[d][3], d, "no Part D brand-name match (injectable Part B, new, or not yet in DY2024)")
