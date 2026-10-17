import sys
import pandas as pd

n = pd.read_csv("data/moat/tables/nadac_history.csv", dtype={"ndc": str})
for d in sys.argv[1:]:
    x = n[(n.drug == d) & (n.match_kind == "brand")].copy()
    x["y"] = x.as_of_date.str[:4]
    g = x.groupby(["ndc", "ndc_description", "pricing_unit", "y"]).agg(p=("nadac_per_unit", "mean"), last=("as_of_date", "max"), k=("as_of_date", "count")).reset_index()
    print(g[g.y >= "2024"].to_string())
