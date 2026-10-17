"""Per drug and year gross-to-net proxy table from the other pricing tables."""
import pandas as pd
from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap

T = "data/moat/tables/"
pd_ = pd.read_csv(T + "partd_by_year.csv")
asp = pd.read_csv(T + "partb_asp_quarterly.csv")
nad = pd.read_csv(T + "nadac_history.csv", dtype={"ndc": str})
rows = []
for slug in DRUGS:
    r = {}
    # Part D: Overall rows, all brand variants of this drug (sum spend / sum units); annual only
    d = pd_[(pd_.drug == slug) & (pd_.mftr == "Overall") & (pd_.grain == "year")]
    for y, g in d.groupby("period"):
        g = g.dropna(subset=["total_spend", "dosage_units"])
        if len(g) and g.dosage_units.sum() > 0:
            r.setdefault(int(y), {})["partd_spend_per_unit"] = g.total_spend.sum() / g.dosage_units.sum()
            r[int(y)]["partd_total_spend"] = g.total_spend.sum()
            r[int(y)]["partd_src"] = "; ".join(g.source_row.head(3))
    # Part B ASP payment limit: mean over the year's four quarters, for the drug's own HCPCS (first listed code)
    a = asp[asp.drugs.str.split(";").apply(lambda x: slug in x)].copy()
    a["year"] = a.quarter.str[:4].astype(int)
    a = a[a.match_basis == "hcpcs_in_pack"] if (a.match_basis == "hcpcs_in_pack").any() else a
    for (y, h), g in a.groupby(["year", "hcpcs"]):
        e = r.setdefault(y, {})
        if "partb_asp_payment_limit" not in e:
            e["partb_asp_payment_limit"] = g.payment_limit.astype(float).mean()
            e["partb_hcpcs"] = h
            e["partb_asp_dosage"] = g.dosage.iloc[0]
            e["partb_asp_quarters"] = len(g)
            e["partb_src"] = g.source_row.iloc[0]
    # NADAC: mean brand NADAC per unit across NDCs and weeks in the year
    n = nad[(nad.drug == slug) & (nad.match_kind == "brand")].copy()
    n["y"] = pd.to_datetime(n.effective_date, errors="coerce").dt.year
    n["p"] = pd.to_numeric(n.nadac_per_unit, errors="coerce")
    for y, g in n.dropna(subset=["y", "p"]).groupby("y"):
        e = r.setdefault(int(y), {})
        e["nadac_brand_mean_per_unit"] = g.p.mean()
        e["nadac_ndc_count"] = g.ndc.nunique()
        e["nadac_pricing_unit"] = g.pricing_unit.mode().iloc[0]
        e["nadac_src"] = g.source_row.iloc[0]
        gen = pd.to_numeric(g.corresponding_generic_drug_nadac_per_unit, errors="coerce").dropna()
        if len(gen):
            e["nadac_corresponding_generic_per_unit"] = gen.mean()
    # IRA MFP per unit (NDC-9 level, mean of rows with a value), shown for MFP effective year
    try:
        m = pd.read_csv(f"data/corpus/drugs/{slug}/ira_negotiation.csv", dtype=str)
        m["u"] = pd.to_numeric(m["NDC-9 MFP per Unit Price"], errors="coerce")
        m["d"] = pd.to_datetime(m["MFP Effective Date"], errors="coerce")
        m["d30"] = pd.to_numeric(m["Single MFP per 30 DES"], errors="coerce")
        for y, g in m.dropna(subset=["d"]).groupby(m.d.dt.year):
            e = r.setdefault(int(y), {})
            if g.u.notna().any():
                e["ira_mfp_per_unit"] = g.u.mean()
            if g.d30.notna().any():
                e["ira_mfp_per_30day"] = g.d30.mean()
            e["ira_src"] = f"data/corpus/drugs/{slug}/ira_negotiation.csv IPAY={g.IPAY.iloc[0]}"
    except FileNotFoundError:
        pass
    for y, e in sorted(r.items()):
        if 2020 <= y <= 2027:
            rows.append(dict(drug=slug, year=y, **e))
df = pd.DataFrame(rows)
df["partd_vs_nadac_ratio"] = df.partd_spend_per_unit / df.nadac_brand_mean_per_unit
df["partd_gross_vs_mfp_ratio"] = df.partd_spend_per_unit / df.ira_mfp_per_unit
df["nadac_vs_mfp_ratio"] = df.nadac_brand_mean_per_unit / df.ira_mfp_per_unit
df["source"] = "derived from tables/partd_by_year.csv, partb_asp_quarterly.csv, nadac_history.csv and data/corpus/drugs/<drug>/ira_negotiation.csv"
df["source_row"] = df.drug + "|" + df.year.astype(str)
cols = ["drug", "year", "partd_spend_per_unit", "partd_total_spend", "partb_hcpcs", "partb_asp_payment_limit", "partb_asp_dosage", "partb_asp_quarters",
        "nadac_brand_mean_per_unit", "nadac_pricing_unit", "nadac_ndc_count", "nadac_corresponding_generic_per_unit", "ira_mfp_per_unit", "ira_mfp_per_30day",
        "partd_vs_nadac_ratio", "partd_gross_vs_mfp_ratio", "nadac_vs_mfp_ratio", "partd_src", "partb_src", "nadac_src", "ira_src", "source", "source_row"]
df = df[[c for c in cols if c in df.columns]]
write("pricing", "tables/gtn_proxy.csv", df.to_csv(index=False), group="pricing", doc_type="table", source_url="derived")
print(len(df), df.drug.nunique())
for c in ["partd_spend_per_unit", "partb_asp_payment_limit", "nadac_brand_mean_per_unit", "ira_mfp_per_unit"]:
    print(c, df[c].notna().sum(), "rows;", df[df[c].notna()].drug.nunique(), "drugs")
none = [s for s in DRUGS if s not in set(df.drug)]
print("no proxy rows:", none)
for s in none:
    note_gap("pricing", DRUGS[s][3], s, "no Part D, Part B ASP, NADAC or IRA price series available for gtn_proxy")
