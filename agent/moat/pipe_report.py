import pandas as pd

a = pd.read_csv("data/moat/tables/pipeline_assets.csv")
t = pd.read_csv("data/moat/tables/pipeline_landscape.csv")
print("trials by phase", t.phase.value_counts().to_dict())
print("trials by primary indication", t.primary_indication.value_counts().to_dict())
rank = {"Phase 3": 3, "Phase 2/3": 2.5, "Phase 2": 2}
a["r"] = a.most_advanced_phase.map(rank)
x = a.assign(ind=a.indications.str.split("; ")).explode("ind").reset_index(drop=True)
print(pd.crosstab(x.ind, x.most_advanced_phase).to_string())
print(a.flag.value_counts().to_dict())
rank = {"Phase 3": 3, "Phase 2/3": 2.5, "Phase 2": 2}
a["r"] = a.most_advanced_phase.map(rank)
no = x[~x.flag.eq("owned by one of the 10")]
groups = {"obesity": ["obesity"], "NSCLC": ["NSCLC"],
          "psoriasis/IBD": ["plaque psoriasis", "psoriatic arthritis", "Crohn's", "ulcerative colitis"]}
for g, inds in groups.items():
    y = no[no.ind.isin(inds)].drop_duplicates("sample_nct")
    y = y[y.most_advanced_phase.isin(["Phase 3", "Phase 2/3"])]
    y = y[y.nearest_primary_completion.notna()]
    y = y[y.nearest_primary_completion.astype(str) >= "2026-06"]
    y = y.sort_values(["r", "nearest_primary_completion"], ascending=[False, True]).head(10)
    print("\n==", g)
    print(y[["sponsor", "asset", "most_advanced_phase", "flag", "nearest_primary_completion", "n_trials"]].to_string(index=False))
