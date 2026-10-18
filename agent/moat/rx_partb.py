"""Part B providers for the physician-administered case drugs, 2021-2023 (provider x service file filtered by HCPCS)."""
import pandas as pd
import requests

from agent.moat.common import note_gap, store, write

YEARS = {2021: "31dc2c47-f297-4948-bfb4-075e1bec3a02", 2022: "e650987d-01b7-4f09-b75e-b0b075afbf98",
         2023: "0e9f2f2b-7bf9-451a-912c-e02e654dd725"}
CODES = {"keytruda": ["J9271"], "opdivo": ["J9299"], "darzalex": ["J9145", "J9144"], "stelara-iv": ["J3358"],
         "entyvio": ["J3380"], "tecentriq": ["J9022"], "imfinzi": ["J9173"], "sarclisa": ["J9227"],
         "rybrevant": ["J9061"], "leqvio": ["J1306"], "amvuttra": ["J0225"], "cabenuva": ["J0741"],
         "apretude": ["J0739"]}
S = requests.Session()


def fetch(year, code):
    base = f"https://data.cms.gov/data-api/v1/dataset/{YEARS[year]}/data"
    p = {"filter[HCPCS_Cd]": code}
    n = S.get(base + "/stats", params=p, timeout=120).json()["found_rows"]
    rows = []
    for off in range(0, n, 5000):
        rows += S.get(base, params={**p, "size": 5000, "offset": off}, timeout=120).json()
    return rows


def main():
    out = []
    for slug, codes in CODES.items():
        for year in YEARS:
            for code in codes:
                rows = fetch(year, code)
                if not rows:
                    note_gap("rx", slug, f"partb_{year}_{code}", "no provider rows for HCPCS code in Part B provider-service file")
                    continue
                df = pd.DataFrame(rows)
                for c in ("Tot_Benes", "Tot_Srvcs", "Tot_Bene_Day_Srvcs", "Avg_Mdcr_Pymt_Amt"):
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                df["pay"] = df["Avg_Mdcr_Pymt_Amt"] * df["Tot_Srvcs"]
                src = f"https://data.cms.gov/data-api/v1/dataset/{YEARS[year]}/data?filter[HCPCS_Cd]={code}"
                for level, col in (("total", None), ("specialty", "Rndrng_Prvdr_Type"), ("state", "Rndrng_Prvdr_State_Abrvtn")):
                    groups = [("ALL", df)] if col is None else list(df.groupby(col))
                    for key, g in groups:
                        out.append({"drug": slug, "hcpcs": code, "hcpcs_desc": rows[0]["HCPCS_Desc"], "year": year, "level": level,
                                    "key": key, "providers": g["Rndrng_NPI"].nunique(), "services": g["Tot_Srvcs"].sum(),
                                    "beneficiaries_sum_over_providers": g["Tot_Benes"].sum(), "medicare_payment_est_usd": round(g["pay"].sum(), 2),
                                    "source": src, "source_row": f"{year}:{code}:{level}:{key}"})
                print(slug, year, code, len(df), flush=True)
    df = pd.DataFrame(out)
    write("rx", "tables/partb_providers_by_drug.csv", df.to_csv(index=False), group="rx", doc_type="table",
          source_url="https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service")
    t = df[df.level == "total"].sort_values("services", ascending=False)
    print(t[["drug", "year", "providers", "services"]].head(20))


main()
