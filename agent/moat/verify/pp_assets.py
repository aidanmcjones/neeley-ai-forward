"""Pipeline verifier item 2 (partial, timeboxed): flag assets that are trial arms, comparators or another company's
marketed drug, and code-name/INN duplicates within a sponsor that share trials. No full 80-asset trial re-derivation.
Usage: python -m agent.moat.verify.pp_assets [--write]
"""
import re
import sys

import pandas as pd

from agent.moat.common import write

a = pd.read_csv("data/moat/tables/pipeline_assets.csv")
ARM = re.compile(r"^(arm [a-z0-9]|cohort|part [a-z0-9]|prior |platinum|chemotherapy|endocrine therapy|"
                 r"investigator|physician|standard|best |bcg\b|rescue|pd-1 monoclonal)|chemotherapy$|\bplus\b|\+", re.I)
# marketed drugs of OTHER companies that show up as a small sponsor's asset (comparator or backbone arm)
OTHERS = re.compile(r"^(crizotinib|xalkori|valacyclovir|apremilast|otezla|byl719|alpelisib|pembrolizumab|"
                    r"nivolumab|fulvestrant|letrozole|palbociclib|dexamethasone|bevacizumab|cisplatin|carboplatin|"
                    r"paclitaxel|docetaxel|metformin|semaglutide|tirzepatide|dupilumab|ustekinumab|adalimumab|"
                    r"apixaban|rivaroxaban)\b", re.I)
# sponsor's own drug already FDA-approved under a brand (collector shows it as a Phase 2/3 pipeline asset)
MARKETED = {"MGL-3196": "resmetirom (Rezdiffra, approved 2024)", "NVX-CoV2373": "Nuvaxovid (approved 2025)",
            "Setmelanotide": "Imcivree (approved 2020)", "Tebentafusp": "Kimmtrak (approved 2022)",
            "Lifileucel": "Amtagvi (approved 2024)", "Taletrectinib": "Ibtrozi (approved 2025)",
            "KPT-330": "selinexor (Xpovio, approved 2019)", "UGN-102": "Zusduri (approved 2025)",
            "CORT118335": "relacorilant (code name; same drug as Corcept relacorilant)"}
a["asset_flag"] = ""
for i, r in a.iterrows():
    f = []
    nm = str(r.asset)
    if ARM.search(nm):
        f.append("trial arm or regimen label, not a drug asset")
    if OTHERS.search(nm):
        f.append("another company's marketed drug (comparator or backbone arm)")
    if nm in MARKETED:
        f.append("already marketed: " + MARKETED[nm])
    a.at[i, "asset_flag"] = "; ".join(f)
# duplicates: same sponsor, assets whose trial sets overlap (code name vs INN listed separately)
dups = []
for sp, g in a.groupby("sponsor"):
    if len(g) < 2:
        continue
    sets = {i: set(str(x).split("; ")) for i, x in zip(g.index, g.source_row)}
    ids = list(sets)
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            i, j = ids[x], ids[y]
            if sets[i] & sets[j] and not (a.at[i, "asset_flag"] or a.at[j, "asset_flag"]):
                dups.append((sp, a.at[i, "asset"], a.at[j, "asset"], len(sets[i] & sets[j])))
D = pd.DataFrame(dups, columns=["sponsor", "asset_a", "asset_b", "shared_trials"])
# dose-variant splits: "MWN109 1", "MWN109 2" are one drug; merge to the base code name
a["base"] = a.asset.astype(str).str.replace(r"\s+\d+(\.\d+)?$", "", regex=True)
grp = a.groupby(["sponsor", "base"])
merged = 0
for (sp, b), g in grp:
    if len(g) > 1 and (g.asset != b).any():
        i0 = g.index[0]
        a.at[i0, "aliases"] = "; ".join(sorted(set("; ".join(g.aliases.astype(str)).split("; ")) | set(g.asset)))
        a.at[i0, "source_row"] = "; ".join(sorted(set("; ".join(g.source_row.astype(str)).split("; "))))
        a.at[i0, "n_trials"] = len(a.at[i0, "source_row"].split("; "))
        a.at[i0, "asset"] = b
        a.at[i0, "asset_flag"] = (str(a.at[i0, "asset_flag"]) + f"; merged {len(g)} dose-variant rows").strip("; ")
        a.drop(index=g.index[1:], inplace=True)
        merged += len(g) - 1
print("dose-variant rows merged", merged)
a = a.drop(columns="base")
D.to_csv("data/moat/verify/pp_cache/asset_dup_candidates.csv", index=False)
a["verify_status"] = ["rejected_not_asset" if ("arm" in f or "another company" in f) else
                      ("marketed_not_pipeline" if "already marketed" in f else "unverified") for f in a.asset_flag]
print(a.verify_status.value_counts().to_dict())
print(a[a.flag.str.startswith("potential")].verify_status.value_counts().to_dict())
print("shared-trial pairs within sponsor", len(D))
print(D.sort_values("shared_trials", ascending=False).head(20).to_string())
if "--write" in sys.argv:
    keep = a[a.verify_status != "rejected_not_asset"]
    write("verify_pipeline", "verified/pipeline/pipeline_assets.csv", keep.to_csv(index=False), group="pipeline",
          doc_type="table", quality="verified", source_url="https://clinicaltrials.gov/api/v2/studies")
    write("verify_pipeline", "verified/pipeline/pipeline_assets_dropped.csv",
          a[a.verify_status == "rejected_not_asset"].to_csv(index=False), group="pipeline", doc_type="table",
          quality="rejected", source_url="https://clinicaltrials.gov/api/v2/studies")
