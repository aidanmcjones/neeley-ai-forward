import pandas as pd
g = pd.read_csv("data/moat/tables/gtn_proxy.csv")
p = g.pivot(index="drug", columns="year", values="partd_spend_per_unit")
p["chg"] = p[2024] / p[2020] - 1
print(p[[2020, 2024, "chg"]].dropna().sort_values("chg").round(3).to_string())
n = g.pivot(index="drug", columns="year", values="nadac_brand_mean_per_unit")
print(n.round(2).dropna(how="all").to_string())
print(g[g.ira_mfp_per_unit.notna()][["drug", "year", "partd_spend_per_unit", "nadac_brand_mean_per_unit", "ira_mfp_per_unit", "partd_gross_vs_mfp_ratio"]].round(2).to_string())
a = g.pivot(index="drug", columns="year", values="partb_asp_payment_limit")
print(a.round(2).to_string())
