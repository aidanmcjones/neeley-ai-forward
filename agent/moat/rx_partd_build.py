"""Build the Part D prescriber tables from the raw pulls (scratch) written by rx_partd_fetch."""
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from agent.drug_pack import DRUGS
from agent.moat.common import write
from agent.moat.rx_partd_fetch import YEARS, TMP

ENR = "https://data.cms.gov/data-api/v1/dataset/d7fabe1e-d19b-4333-9eff-e80e0643f2fd/data"
BRANDS = sorted(((v[0].lower(), slug, v[2].lower().split(";")[0].split(",")[0].strip()) for slug, v in DRUGS.items()),
                key=lambda t: -len(t[0]))


def classify(brnd, gnrc, q):
    b = (brnd or "").lower()
    for name, slug, ing in BRANDS:
        if b == name or b.startswith(name + " "):
            return slug
    if b == (gnrc or "").lower() or b.replace("-", " ") == (gnrc or "").lower().replace("-", " "):
        return f"{q} (generic)"
    return None


def enrollment():
    rows = []
    for y in YEARS:
        r = requests.get(ENR, params={"filter[YEAR]": str(y), "filter[MONTH]": "Year", "filter[BENE_GEO_LVL]": "State", "size": 100}, timeout=120).json()
        rows += [{"year": y, "state": x["BENE_STATE_ABRVTN"], "partd_enrollees": pd.to_numeric(x["PRSCRPTN_DRUG_TOT_BENES"], errors="coerce")} for x in r]
    return pd.DataFrame(rows)


def conc(g):
    c = np.sort(g["Tot_Clms"].to_numpy())[::-1]
    tot = c.sum()
    out = {}
    for p in (1, 5, 20):
        k = max(1, int(np.ceil(len(c) * p / 100)))
        out[f"top{p}pct_claim_share"] = round(c[:k].sum() / tot, 4) if tot else None
    return pd.Series(out)


def main():
    frames = []
    for y in YEARS:
        f = TMP / f"partd_{y}.csv.gz"
        if not f.exists():
            continue
        d = pd.read_csv(f, dtype={"Prscrbr_NPI": str})
        d["year"] = y
        frames.append(d)
    df = pd.concat(frames)
    df["drug"] = [classify(b, g, q) for b, g, q in zip(df.Brnd_Name, df.Gnrc_Name, df.query_ingredient)]
    df = df[df.drug.notna()].copy()
    for c in ("Tot_Clms", "Tot_30day_Fills", "Tot_Drug_Cst", "Tot_Benes"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Prscrbr_Type"] = df["Prscrbr_Type"].fillna("Unknown")
    # one row per prescriber-drug-year after collapsing brand/generic name variants
    ds = {y: f"https://data.cms.gov/data-api/v1/dataset/{YEARS[y]}/data" for y in YEARS}
    print(df.groupby(["drug", "year"]).size().unstack().fillna(0).astype(int))

    ing = {slug: v[2].lower().split(";")[0].split(",")[0].strip() for slug, v in DRUGS.items()}
    a = df.groupby(["drug", "year"]).agg(prescribers=("Prscrbr_NPI", "nunique"), total_claims=("Tot_Clms", "sum"),
                                         total_30day_fills=("Tot_30day_Fills", "sum"), total_drug_cost=("Tot_Drug_Cst", "sum"),
                                         beneficiaries_reported=("Tot_Benes", "sum")).reset_index()
    a["ingredient"] = [ing.get(d, d.replace(" (generic)", "")) for d in a.drug]
    a["note"] = "beneficiaries_reported sums per-prescriber counts (rows under 11 are suppressed by CMS), so it double-counts patients seen by several prescribers"
    a["source"] = [ds[y] + f"?filter[Gnrc_Name][operator]=CONTAINS&filter[Gnrc_Name][value]={i}" for y, i in zip(a.year, a.ingredient)]
    a["source_row"] = [f"{y}:{d}:total" for y, d in zip(a.year, a.drug)]
    a = a.round(2)
    write("rx", "tables/partd_prescribers_by_drug.csv", a.to_csv(index=False), group="rx", doc_type="table", source_url="https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug")

    s = df.groupby(["drug", "year", "Prscrbr_Type"]).agg(prescribers=("Prscrbr_NPI", "nunique"), claims=("Tot_Clms", "sum"), drug_cost=("Tot_Drug_Cst", "sum")).reset_index()
    s["claim_share"] = (s.claims / s.groupby(["drug", "year"])["claims"].transform("sum")).round(4)
    s["rank"] = s.groupby(["drug", "year"])["claims"].rank(ascending=False, method="first").astype(int)
    s = s[s["rank"] <= 10].rename(columns={"Prscrbr_Type": "specialty"}).sort_values(["drug", "year", "rank"])
    s["source"] = [ds[y] for y in s.year]
    s["source_row"] = [f"{y}:{d}:specialty:{k}" for y, d, k in zip(s.year, s.drug, s.specialty)]
    write("rx", "tables/partd_prescribers_by_specialty.csv", s.round(2).to_csv(index=False), group="rx", doc_type="table", source_url=ds[2023])

    en = enrollment()
    st = df.groupby(["drug", "year", "Prscrbr_State_Abrvtn"]).agg(prescribers=("Prscrbr_NPI", "nunique"), claims=("Tot_Clms", "sum"), drug_cost=("Tot_Drug_Cst", "sum")).reset_index()
    st = st.rename(columns={"Prscrbr_State_Abrvtn": "state"}).merge(en, on=["year", "state"], how="left")
    st["claims_per_1000_partd_enrollees"] = (st.claims / st.partd_enrollees * 1000).round(3)
    st["source"] = [ds[y] for y in st.year]
    st["source_row"] = [f"{y}:{d}:state:{k}" for y, d, k in zip(st.year, st.drug, st.state)]
    st["enrollment_source"] = ENR + "?filter[BENE_GEO_LVL]=State&filter[MONTH]=Year (PRSCRPTN_DRUG_TOT_BENES)"
    write("rx", "tables/partd_prescribers_by_state.csv", st.round(2).to_csv(index=False), group="rx", doc_type="table", source_url=ENR)

    c = df.groupby(["drug", "year"]).apply(conc, include_groups=False).reset_index()
    c = c.merge(a[["drug", "year", "prescribers", "total_claims"]], on=["drug", "year"])
    c = c.sort_values(["drug", "year"])
    c["prescribers_prev_year"] = c.groupby("drug")["prescribers"].shift(1)
    c["prescriber_growth_yoy"] = (c.prescribers / c.prescribers_prev_year - 1).round(4)
    c["claims_growth_yoy"] = (c.total_claims / c.groupby("drug")["total_claims"].shift(1) - 1).round(4)
    c["source"] = [ds[y] for y in c.year]
    c["source_row"] = [f"{y}:{d}:concentration" for y, d in zip(c.year, c.drug)]
    write("rx", "tables/prescriber_concentration.csv", c.to_csv(index=False), group="rx", doc_type="table", source_url=ds[2023])
    print(len(a), len(s), len(st), len(c))


main()
