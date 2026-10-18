"""Wave 3: apply duplicate merges, sampled-check results and marketed-comparator flags/drops to
verified/pipeline/pipeline_assets.csv. Marketed list: FDA Orange Book products + Purple Book (cached)."""
import io, re, shutil, zipfile
import pandas as pd
from agent.moat.common import write, OUT
from agent.moat.verify.pp_targets_lib import toks

V = OUT / "verified/pipeline"
for n in ("pipeline_assets", "pipeline_assets_dropped"):
    if not (V / f"{n}_wave2.csv").exists():
        shutil.copy(V / f"{n}.csv", V / f"{n}_wave2.csv")
a = pd.read_csv(V / "pipeline_assets_wave2.csv")
drop0 = pd.read_csv(V / "pipeline_assets_dropped_wave2.csv")
r = pd.read_csv(OUT / "tables/pipeline_assets_rechecks.csv")
a["key"] = a.sponsor + "|" + a.asset

# 1. sampled checks (owner, phase, CT.gov phase, sponsor): 80/80 pass
samp = r[r.check.isin(["owner_flag_vs_landscape", "owner_vs_ctgov_lead_sponsor", "phase_vs_ctgov", "phase_vs_landscape"])]
ok = samp.groupby("row_key").result.apply(lambda s: (s == "pass").all())
for k, v in ok.items():
    m = a.key == k.split(":", 1)[1]
    a.loc[m & (a.verify_status == "unverified"), "verify_status"] = "pass" if v else "check"

# 2. merges
def merge(keep, gone, why):
    i, j = a.index[a.key == keep][0], a.index[a.key == gone][0]
    trials = sorted(set(str(a.at[i, "source_row"]).split("; ")) | set(str(a.at[j, "source_row"]).split("; ")))
    al = sorted(set(str(a.at[i, "aliases"]).split("; ")) | set(str(a.at[j, "aliases"]).split("; ")) | {a.at[j, "asset"]})
    inds = sorted(set(str(a.at[i, "indications"]).split("; ")) | set(str(a.at[j, "indications"]).split("; ")))
    a.at[i, "source_row"], a.at[i, "aliases"], a.at[i, "indications"] = "; ".join(trials), "; ".join(al), "; ".join(inds)
    a.at[i, "n_trials"] = len(trials)
    a.at[i, "n_active"] = int(a.at[i, "n_active"]) + int(a.at[j, "n_active"])  # upper bound; trials may overlap
    for c in ("nearest_primary_completion",):
        a.at[i, c] = min(str(a.at[i, c]), str(a.at[j, c]))
    a.at[i, "latest_primary_completion"] = max(str(a.at[i, "latest_primary_completion"]), str(a.at[j, "latest_primary_completion"]))
    a.at[i, "asset_flag"] = f"merged duplicate '{a.at[j, 'asset']}' ({why})"
    return a.drop(index=j)

a = merge("Merck Sharp & Dohme LLC|Mitomycin C (MMC)", "Merck Sharp & Dohme LLC|MMC", "RxNav: both map to mitomycin")
a = merge("Novartis Pharmaceuticals|ALN-PCSSC; KJX839", "Novartis Pharmaceuticals|KJX839", "alias overlap KJX839")

# 3. marketed list
with zipfile.ZipFile(OUT / "verify/pp_cache/orange_book.zip") as z:
    ob = pd.read_csv(io.BytesIO(z.read("products.txt")), sep="~", dtype=str)
pbraw = (OUT / "verify/pp_cache/purple_book.csv").read_text(errors="replace").splitlines()
hdr = next(i for i, l in enumerate(pbraw) if l.startswith("N/R/U,Applicant"))
pb = pd.read_csv(io.StringIO("\n".join(pbraw[hdr:])), dtype=str, on_bad_lines="skip")
holders = {}  # name (lower) -> set of holder token-sets
def add(name, holder):
    for n in re.split(r"[;,]", str(name).lower()):
        n = re.sub(r"\s+", " ", n).strip()
        if len(n) > 3 and n != "nan":
            holders.setdefault(n, set()).add(holder)
for _, x in ob.iterrows():
    add(x.Ingredient, x.Applicant_Full_Name); add(x.Trade_Name, x.Applicant_Full_Name)
for _, x in pb.iterrows():
    add(re.sub(r"-[a-z]{4}$", "", str(x["Proper Name"])), x.Applicant); add(x["Proprietary Name"], x.Applicant)
GROUP = [{"roche", "genentech", "hoffmann", "chugai"}, {"janssen", "johnson", "actelion"}, {"novartis", "sandoz"},
         {"sanofi", "genzyme", "aventis"}, {"pfizer", "wyeth", "hospira", "seagen", "arena"}, {"bristol", "squibb", "celgene", "juno", "mirati"},
         {"abbvie", "allergan", "abbott", "pharmacyclics"}, {"glaxosmithkline", "gsk", "viiv"}, {"astrazeneca", "medimmune", "alexion"},
         {"emd", "serono", "merck kgaa"}, {"takeda", "shire", "millennium"}, {"gilead", "kite"}, {"merck", "msd", "sharp", "dohme"},
         {"lilly"}, {"amgen"}, {"boehringer"}, {"bayer"}, {"novo", "nordisk"}, {"regeneron"}, {"biogen"}]
def fam(s):
    t = toks(s) | {w for w in str(s).lower().split()}
    out = set(t)
    for g in GROUP:
        if t & g:
            out |= g
    return out
COMPARATOR_WORDS = re.compile(r"(?i)\b(conventional|standard of care|soc|physician'?s choice|investigator'?s choice|reference|placebo)\b")
flags = []
for i, x in a.iterrows():
    names = [x.asset] + str(x.aliases).split("; ")
    hit, via_alias = None, False
    for k, n in enumerate(names):
        n0 = re.sub(r"\s+", " ", re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|mg/kg|%)\b.*", "", str(n).lower())).strip(" ,")
        n0 = re.sub(r"^(conventional|generic|reference|commercial|marketed|branded)\s+", "", n0)
        if n0 in holders:
            hit, via_alias = n0, k > 0; break
    if not hit:
        continue
    sp = fam(x.sponsor)
    own = any(fam(h) & sp - {"inc", "llc"} for h in holders[hit])
    nhold = len(holders[hit])
    flags.append({"i": i, "match": ("alias: " if via_alias else "") + hit, "own": own, "n_holders": nhold, "alias": via_alias})
fl = pd.DataFrame(flags).set_index("i")
a["marketed_match"] = fl.match
a["marketed_comparator"] = 0
cm = fl.index[~fl.own]
a.loc[cm, "marketed_comparator"] = 1
a.loc[fl.index[fl.own], "asset_flag"] = a.loc[fl.index[fl.own], "asset_flag"].fillna("").astype(str).str.cat(
    ["sponsor's own marketed drug (Orange/Purple Book holder): " + m for m in fl.loc[fl.own, "match"]], sep="; ").str.strip("; ")
# obvious drops: marketed to another holder AND (multi-source generic, >=3 holders, or comparator wording, or the
# recheck's named comparators); single-holder brands owned by others are flagged, not dropped (could be licensed)
HAND = {"Empros Pharma AB|Conventional orlistat 120 mg,", "Shanghai Institute Of Biological Products|Avastin",
        "Janssen Research & Development, LLC|Tocilizumab", "Regeneron Pharmaceuticals|Apixiban", "AstraZeneca|sunitinib",
        "Hoffmann-La Roche|Midazolam", "Hoffmann-La Roche|Adagrasib", "Palleos Healthcare GmbH|Epirubicin",
        "RemeGen Co., Ltd.|Epirubicin", "Oncotherapeutics|Ixazomib", "Merck Sharp & Dohme LLC|Mitomycin C (MMC)"}
a.loc[a.key.isin(HAND), "marketed_comparator"] = 1
obvious = a.key.isin(HAND) | ((a.marketed_comparator == 1) & (
    a.index.isin(fl.index[(fl.n_holders >= 3) & ~fl.alias]) | a.asset.str.contains(COMPARATOR_WORDS, na=False)))
dropped = a[obvious].copy()
dropped["asset_flag"] = "another company's marketed drug used as comparator, backbone or probe (wave 3): " + dropped.marketed_match.fillna("hand").astype(str)
dropped["verify_status"] = "rejected_not_asset"
keep = a[~obvious].copy()
keep.loc[keep.marketed_comparator == 1, "asset_flag"] = keep.loc[keep.marketed_comparator == 1, "asset_flag"].fillna("").astype(str).str.cat(
    ["marketed by another holder (" + str(m) + "): comparator, backbone or licensed asset, check before use" for m in keep.loc[keep.marketed_comparator == 1, "marketed_match"]], sep="; ").str.strip("; ")
keep = keep.drop(columns=["key"]); dropped = dropped.drop(columns=["key"])
alld = pd.concat([drop0, dropped], ignore_index=True)
print("kept", len(keep), "new drops", len(dropped), "dropped total", len(alld), "flag kept", int((keep.marketed_comparator == 1).sum()),
      "own marketed", int(fl.own.sum()), keep.verify_status.value_counts().to_dict())
print(dropped[["sponsor", "asset", "marketed_match"]].to_string()[:6000])
print(keep[keep.marketed_comparator == 1][["sponsor", "asset", "marketed_match"]].head(15).to_string())
write("verify_pipeline", "verified/pipeline/pipeline_assets.csv", keep.to_csv(index=False), group="pipeline", doc_type="verified_table",
      source_url="CT.gov v2; RxNav; FDA Orange Book products.txt; Purple Book Sept 2026")
write("verify_pipeline", "verified/pipeline/pipeline_assets_dropped.csv", alld.to_csv(index=False), group="pipeline", doc_type="verified_table")
for n in ("pipeline_assets", "pipeline_assets_dropped"):
    write("verify_pipeline", f"verified/pipeline/{n}_wave2.csv", (V / f"{n}_wave2.csv").read_text(), group="pipeline", doc_type="verified_table_prior")
