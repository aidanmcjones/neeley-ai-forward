"""rx verifier items 1 and 2: Part D prescribers by drug, specialty mix and concentration.

Recomputes every drug-year from the raw provider-and-drug pulls in R2 (rx/raw/partd_prescribers_<year>.csv.gz) with an
independent brand classifier, and cross-checks against CMS's own drug-level totals (Part D Prescribers by Geography and
Drug, national rows, fetched by rx_geo_fetch). Writes verified/rx/partd_prescribers_by_drug.csv,
partd_prescribers_by_specialty.csv and prescriber_concentration.csv."""
import io
import json

import numpy as np
import pandas as pd

from agent.moat.verify.rx_lib import cms, out, PD_GEO, PD_PROV, ROOT, TARGETS, classify, raw_partd

T = ROOT / "data/moat/tables"
GEO_URL = "https://data.cms.gov/data-api/v1/dataset/{}/data?filter[Prscrbr_Geo_Lvl]=National&filter[Brnd_Name]={}"
CAVEAT = ("beneficiaries_reported sums per-prescriber Tot_Benes (blank when under 11) so a patient seen by two "
          "prescribers counts twice; use true_beneficiaries (CMS drug-level distinct count)")
SCOPE = ("prescribers = NPIs with 11+ claims for the drug (CMS drops smaller prescriber-drug rows from the provider "
         "file); prescribers_all_cms is CMS's count of every prescriber")


def csv(df):
    b = io.StringIO()
    df.to_csv(b, index=False)
    return b.getvalue()


def close(a, b, tol=0.005):
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(a - b) <= tol * max(abs(b), 1)


def conc(claims):
    c = np.sort(claims)[::-1]
    tot = c.sum()
    return {p: (c[:max(1, int(np.ceil(len(c) * p / 100)))].sum() / tot if tot else None) for p in (1, 5, 20)}


def conc_all(claims, n_all, tot_all):
    """Top p% of ALL prescribers: suppressed prescribers each have under 11 claims so they sit at the bottom; the top
    k of the full population are the top k of the provider file while k <= its length."""
    c = np.sort(claims)[::-1]
    out = {}
    for p in (1, 5, 20):
        k = max(1, int(np.ceil(n_all * p / 100)))
        out[p] = c[:k].sum() / tot_all if (k <= len(c) and tot_all) else None
    return out


def extra_biktarvy(y):
    """Biktarvy was missed by the collector's ingredient query; pull its provider-drug rows directly."""
    r = pd.DataFrame(cms(PD_PROV[y], {"filter[Brnd_Name]": "Biktarvy"}))
    for c in ("Tot_Clms", "Tot_30day_Fills", "Tot_Drug_Cst", "Tot_Benes"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["year"] = y
    r["query_ingredient"] = "opus:Brnd_Name=Biktarvy"
    return r[["Prscrbr_NPI", "Prscrbr_State_Abrvtn", "Prscrbr_Type", "Brnd_Name", "Gnrc_Name", "Tot_Clms",
              "Tot_30day_Fills", "Tot_Drug_Cst", "Tot_Benes", "year", "query_ingredient"]]


def main():
    raw = pd.concat([raw_partd(y) for y in PD_PROV] + [extra_biktarvy(y) for y in PD_PROV])
    raw["drug"] = [classify(b) for b in raw.Brnd_Name]
    raw = raw[raw.drug.notna()].copy()
    raw["Prscrbr_Type"] = raw["Prscrbr_Type"].fillna("Unknown")
    npi = raw.groupby(["drug", "year", "Prscrbr_NPI"]).agg(claims=("Tot_Clms", "sum")).reset_index()
    mine = raw.groupby(["drug", "year"]).agg(prescribers=("Prscrbr_NPI", "nunique"), total_claims=("Tot_Clms", "sum"),
                                             total_drug_cost=("Tot_Drug_Cst", "sum"),
                                             beneficiaries_reported=("Tot_Benes", "sum"),
                                             brand_rows=("Prscrbr_NPI", "size")).reset_index()
    geo = pd.read_csv("/tmp/rxv/geo.csv")
    nat = geo[geo.Prscrbr_Geo_Lvl == "National"].groupby(["drug", "year"]).agg(
        prescribers_all_cms=("Tot_Prscrbrs", "sum"), claims_all_cms=("Tot_Clms", "sum"),
        drug_cost_all_cms=("Tot_Drug_Cst", "sum"), true_beneficiaries=("Tot_Benes", "sum"),
        cms_brand_rows=("Brnd_Name", "nunique"), cms_brands=("Brnd_Name", lambda s: "|".join(sorted(set(s))))).reset_index()

    # ---------- item 1: by drug ----------
    col = pd.read_csv(T / "partd_prescribers_by_drug.csv")
    col = col[~col.drug.str.contains("generic")]
    m = col.merge(mine, on=["drug", "year"], how="outer", suffixes=("", "_v")).merge(nat, on=["drug", "year"], how="outer")
    rows, errs = [], {"classify": [], "missing": []}
    for _, r in m.iterrows():
        o = r.to_dict()
        tgt = r.drug in TARGETS and r.year in (2023, 2024)
        notes = []
        if pd.isna(r.get("prescribers")):
            if pd.isna(r.prescribers_v):
                # brand absent from the raw pull altogether (ingredient query missed it)
                o.update(prescribers=None, total_claims=None, total_drug_cost=None, beneficiaries_reported=None)
                st = "added_from_cms_geography"
                notes.append("collector's Gnrc_Name CONTAINS query missed this brand (CMS generic string is abbreviated, "
                             "e.g. 'Bictegrav/Emtricit/Tenofov Ala'); totals from CMS Geography and Drug national rows only")
                errs["missing"].append((r.drug, r.year, r.claims_all_cms))
            else:
                o.update(prescribers=r.prescribers_v, total_claims=r.total_claims_v, total_drug_cost=r.total_drug_cost_v,
                         beneficiaries_reported=r.beneficiaries_reported_v)
                st = "added_from_raw"
                if r.drug == "biktarvy":
                    notes.append("collector's Gnrc_Name CONTAINS 'bictegravir' query missed Biktarvy (CMS generic string is "
                                 "'Bictegrav/Emtricit/Tenofov Ala'); Opus pulled Brnd_Name=Biktarvy rows directly")
                else:
                    notes.append("brand present in the raw pull but dropped by the collector's brand classifier "
                             "(pack suffix like '(Cf)' not handled)")
                errs["missing"].append((r.drug, r.year, r.total_claims_v))
            o["source"] = GEO_URL.format(PD_GEO[int(r.year)], str(r.drug).title())
            o["source_row"] = f"{int(r.year)}:{r.drug}:total"
        else:
            ok = all(close(r[a], r[a + "_v"]) for a in ("prescribers", "total_claims", "total_drug_cost"))
            if ok:
                st = "verified"
                notes.append("recomputed from raw provider-drug rows: prescribers, claims and cost match")
            else:
                st = "corrected"
                notes.append(f"recomputed from raw: prescribers {r.prescribers:,.0f}->{r.prescribers_v:,.0f}, "
                             f"claims {r.total_claims:,.0f}->{r.total_claims_v:,.0f} (brand variants such as "
                             f"'Humira(Cf) Pen' were dropped by the collector)")
                errs["classify"].append((r.drug, r.year, r.total_claims, r.total_claims_v))
                o.update(prescribers=r.prescribers_v, total_claims=r.total_claims_v, total_drug_cost=r.total_drug_cost_v,
                         beneficiaries_reported=r.beneficiaries_reported_v)
        if not pd.isna(r.claims_all_cms) and not pd.isna(o.get("total_claims")):
            o["claims_in_provider_file_share"] = round(o["total_claims"] / r.claims_all_cms, 4)
            if o["total_claims"] > r.claims_all_cms * 1.001:
                st = "flag"
                notes.append("provider-file claims exceed CMS national total: check classification")
        if pd.isna(r.claims_all_cms):
            notes.append("no CMS Geography and Drug national row found for this brand-year")
        if r.cms_brand_rows and r.cms_brand_rows > 1:
            notes.append(f"prescribers_all_cms and true_beneficiaries summed over {int(r.cms_brand_rows)} CMS brand "
                         f"rows ({r.cms_brands}): upper bound, a prescriber or patient on two pack forms counts twice")
        o["in_opus_sample"] = tgt
        o["note"] = SCOPE
        o["distinct_beneficiary_caveat"] = CAVEAT
        o["geo_source"] = GEO_URL.format(PD_GEO[int(r.year)], str(r.drug).title())
        o["verify_status"] = st
        o["verify_note"] = "; ".join(notes)
        rows.append(o)
    bd = pd.DataFrame(rows)
    keep = ["drug", "year", "prescribers", "prescribers_all_cms", "total_claims", "claims_all_cms",
            "claims_in_provider_file_share", "total_30day_fills", "total_drug_cost", "drug_cost_all_cms",
            "beneficiaries_reported", "true_beneficiaries", "distinct_beneficiary_caveat", "ingredient", "note",
            "in_opus_sample", "source", "source_row", "geo_source", "verify_status", "verify_note"]
    bd = bd[keep].sort_values(["drug", "year"])
    out("partd_prescribers_by_drug.csv", bd.round(4), "CMS Part D Prescribers by Provider and Drug + by Geography and Drug")
    samp = bd[bd.in_opus_sample]
    print("by_drug", bd.verify_status.value_counts().to_dict(), "sample", samp.verify_status.value_counts().to_dict())
    print(samp[["drug", "year", "prescribers", "prescribers_all_cms", "total_claims", "claims_all_cms",
                "beneficiaries_reported", "true_beneficiaries"]].to_string())

    # ---------- specialty ----------
    s = raw.groupby(["drug", "year", "Prscrbr_Type"]).agg(prescribers=("Prscrbr_NPI", "nunique"), claims=("Tot_Clms", "sum"),
                                                          drug_cost=("Tot_Drug_Cst", "sum")).reset_index()
    s["claim_share"] = (s.claims / s.groupby(["drug", "year"])["claims"].transform("sum")).round(4)
    s["rank"] = s.groupby(["drug", "year"])["claims"].rank(ascending=False, method="first").astype(int)
    s = s[s["rank"] <= 10].rename(columns={"Prscrbr_Type": "specialty"})
    cs = pd.read_csv(T / "partd_prescribers_by_specialty.csv")
    sm = s.merge(cs[["drug", "year", "specialty", "claims", "claim_share", "rank"]], on=["drug", "year", "specialty"],
                 how="outer", suffixes=("", "_collector"))
    st, nt = [], []
    for _, r in sm.iterrows():
        tgt = r.drug in TARGETS and r.year in (2023, 2024)
        if pd.isna(r.claims):
            st.append("dropped"); nt.append("collector row falls out of the top 10 once all brand variants are counted")
        elif pd.isna(r.claims_collector):
            st.append("added"); nt.append("new top-10 row after reclassifying brand variants")
        elif close(r.claim_share, r.claim_share_collector, 0.02) and r["rank"] == r.rank_collector:
            st.append("verified"); nt.append("claims share and rank recomputed from raw")
        else:
            st.append("corrected")
            nt.append(f"share {r.claim_share_collector:.4f}->{r.claim_share:.4f}, rank {int(r.rank_collector)}->{int(r['rank'])}")
        nt[-1] += ("; Opus sample drug-year" if tgt else "") + "; shares are of claims by prescribers with 11+ claims"
    sm["verify_status"], sm["verify_note"] = st, nt
    sm["in_opus_sample"] = sm.drug.isin(TARGETS) & sm.year.isin([2023, 2024])
    sm["source"] = [f"https://data.cms.gov/data-api/v1/dataset/{PD_PROV[int(y)]}/data" for y in sm.year]
    sm["source_row"] = [f"{int(y)}:{d}:specialty:{k}" for y, d, k in zip(sm.year, sm.drug, sm.specialty)]
    drop = sm[sm.verify_status == "dropped"]
    sm = sm[sm.verify_status != "dropped"].sort_values(["drug", "year", "rank"])
    out("partd_prescribers_by_specialty.csv", sm, "CMS Part D Prescribers by Provider and Drug")
    out("partd_prescribers_by_specialty_dropped.csv", drop, "CMS Part D Prescribers by Provider and Drug")
    ss = sm[sm.in_opus_sample]
    print("specialty", sm.verify_status.value_counts().to_dict(), "sample", ss.verify_status.value_counts().to_dict())
    print(ss[(ss["rank"] <= 3) & (ss.year == 2023)][["drug", "specialty", "claim_share", "claim_share_collector"]].to_string())

    # ---------- item 2: concentration ----------
    cc = pd.read_csv(T / "prescriber_concentration.csv")
    cc = cc[~cc.drug.str.contains("generic")]
    nat_i = nat.set_index(["drug", "year"])
    crow = []
    for (d, y), g in npi.groupby(["drug", "year"]):
        a = conc(g.claims.to_numpy())
        o = {"drug": d, "year": y, "prescribers": g.Prscrbr_NPI.nunique(), "total_claims": g.claims.sum(),
             "top1pct_claim_share": a[1], "top5pct_claim_share": a[5], "top20pct_claim_share": a[20]}
        if (d, y) in nat_i.index:
            n = nat_i.loc[(d, y)]
            b = conc_all(g.claims.to_numpy(), n.prescribers_all_cms, n.claims_all_cms)
            o.update(prescribers_all_cms=n.prescribers_all_cms, claims_all_cms=n.claims_all_cms,
                     top1pct_share_all_prescribers=b[1], top5pct_share_all_prescribers=b[5],
                     top20pct_share_all_prescribers=b[20])
        crow.append(o)
    c = pd.DataFrame(crow).sort_values(["drug", "year"])
    for base, pcol, ccol in (("", "prescribers", "total_claims"), ("_all_cms", "prescribers_all_cms", "claims_all_cms")):
        prev = c.groupby("drug")[pcol].shift(1)
        prevy = c.groupby("drug")["year"].shift(1)
        c[f"prescriber_growth_yoy{base}"] = np.where(prevy == c.year - 1, c[pcol] / prev - 1, np.nan)
        c[f"claims_growth_yoy{base}"] = np.where(prevy == c.year - 1, c[ccol] / c.groupby("drug")[ccol].shift(1) - 1, np.nan)
    cm = c.merge(cc[["drug", "year", "top1pct_claim_share", "top5pct_claim_share", "top20pct_claim_share",
                     "prescriber_growth_yoy", "claims_growth_yoy"]], on=["drug", "year"], how="left",
                 suffixes=("", "_collector"))
    st, nt = [], []
    multi = raw.groupby(["drug", "year", "Prscrbr_NPI"]).size().gt(1).groupby(["drug", "year"]).sum()
    for _, r in cm.iterrows():
        diffs = [k for k in ("top1pct_claim_share", "top5pct_claim_share", "top20pct_claim_share",
                             "prescriber_growth_yoy", "claims_growth_yoy")
                 if not close(r[k], r[k + "_collector"], 0.01) and not (pd.isna(r[k]) and pd.isna(r[k + "_collector"]))]
        mm = int(multi.get((r.drug, r.year), 0))
        if pd.isna(r.top1pct_claim_share_collector):
            st.append("added"); nt.append("drug-year absent from collector table")
        elif not diffs:
            st.append("verified"); nt.append("top shares and YoY growth recomputed at NPI level from raw")
        else:
            st.append("corrected")
            nt.append("differs on " + ", ".join(f"{k} {r[k + '_collector']:.4f}->{r[k]:.4f}" for k in diffs if not pd.isna(r[k]) and not pd.isna(r[k + '_collector']))
                      + (f"; {mm} prescribers had several brand-variant rows the collector ranked separately" if mm else "")
                      + ("; brand variants dropped by collector" if r.drug in ("humira", "amjevita") else ""))
        nt[-1] += ("; YoY on 11+-claim prescribers moves with the suppressed share; prefer the _all_cms growth"
                   if not pd.isna(r.get("prescriber_growth_yoy_all_cms")) else "")
    cm["verify_status"], cm["verify_note"] = st, nt
    cm["in_opus_sample"] = cm.drug.isin(TARGETS) & cm.year.isin([2023, 2024])
    cm["suppression_rule"] = "both years: CMS omits prescriber-drug rows with under 11 claims; same rule every year"
    cm["source"] = [f"https://data.cms.gov/data-api/v1/dataset/{PD_PROV[int(y)]}/data" for y in cm.year]
    cm["source_row"] = [f"{int(y)}:{d}:concentration" for y, d in zip(cm.year, cm.drug)]
    out("prescriber_concentration.csv", cm.round(4), "CMS Part D Prescribers by Provider and Drug + by Geography and Drug")
    cs_ = cm[cm.in_opus_sample]
    print("conc", cm.verify_status.value_counts().to_dict(), "sample", cs_.verify_status.value_counts().to_dict())
    print(cs_[["drug", "year", "top1pct_claim_share", "top1pct_claim_share_collector", "top20pct_claim_share",
               "top20pct_claim_share_collector", "top1pct_share_all_prescribers", "prescriber_growth_yoy",
               "prescriber_growth_yoy_all_cms"]].round(3).to_string())
    json.dump({"missing": [list(map(str, x)) for x in errs["missing"]], "classify": [list(map(str, x)) for x in errs["classify"]],
               "by_drug": bd.verify_status.value_counts().to_dict(), "by_drug_sample": samp.verify_status.value_counts().to_dict(),
               "spec": sm.verify_status.value_counts().to_dict(), "spec_sample": ss.verify_status.value_counts().to_dict(),
               "conc": cm.verify_status.value_counts().to_dict(), "conc_sample": cs_.verify_status.value_counts().to_dict(),
               "multi_rows": {f"{d}:{y}": int(v) for (d, y), v in multi.items() if v}},
              open("/tmp/rxv/partd_summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
