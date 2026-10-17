import pandas as pd

p = "data/moat/verified/pricing/sample_checks.csv"
d = pd.read_csv(p, dtype=str)
nullish = {"nan", "N/A", "", "None", "MISSING_NULL"}
both_null = d.ours.fillna("nan").isin(nullish) & d.source.fillna("nan").isin(nullish)
d["note"] = ""
d.loc[both_null, "match"] = "True"
d.loc[both_null, "note"] = "both null (SDUD suppressed cell or ASP 'N/A')"
w20 = d.key.str.endswith("cols4-6_raw")
d.loc[w20, "match"] = "False"
d.loc[w20, "note"] = ("HCAI 2020 data rows carry an extra year column: raw = year | increase amount | WAC after. "
                      "Ours stored 2020 as wac_increase_amount and the increase amount as wac_after_increase; true WAC after is the third raw value")
d.to_csv(p, index=False)
d["m"] = d.match == "True"
print(d.groupby("table").m.agg(["sum", "count"]))
