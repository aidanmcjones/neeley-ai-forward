"""Verified gross-to-net proxy: explicit unit columns, NDC-matched MFP ratios, per-mg conversion from label strength.

Writes data/moat/verified/pricing/gtn_proxy.csv (local only here; pv_upload.py uploads)."""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from agent.drug_pack import DRUGS

T = "data/moat/tables/"
OUT = Path("data/moat/verified/pricing")
OUT.mkdir(parents=True, exist_ok=True)

# Correct HCPCS per product (the collector took the first code alphabetically among codes listed for the pack,
# which gave Darzalex IV the Faspro code, Qlex/Qvantig the IV code, Yeztugo the Sunlenca code, Wezlana Stelara's code).
HCPCS = {
    "keytruda": ("J9271", 1, "pembrolizumab IV, 1 mg"), "keytruda-qlex": ("J9277", 1, "pembrolizumab + berahyaluronidase SC, 1 mg"),
    "opdivo": ("J9299", 1, "nivolumab IV, 1 mg"), "opdivo-qvantig": ("J9289", 2, "nivolumab + hyaluronidase SC, 2 mg"),
    "darzalex": ("J9145", 10, "daratumumab IV, 10 mg"), "darzalex-faspro": ("J9144", 10, "daratumumab + hyaluronidase SC, 10 mg"),
    "stelara": ("J3357", 1, "ustekinumab SC, 1 mg (code ends 2025Q1); J3358 IV is a different presentation"),
    "entyvio": ("J3380", 1, "vedolizumab IV, 1 mg (IV vial only; SC pen is Part D)"),
    "tecentriq": ("J9022", 10, "atezolizumab IV, 10 mg"), "imfinzi": ("J9173", 10, "durvalumab IV, 10 mg"),
    "sarclisa": ("J9227", 10, "isatuximab IV, 10 mg"), "rybrevant": ("J9061", 2, "amivantamab IV, 2 mg"),
    "amvuttra": ("J0225", 1, "vutrisiran SC, 1 mg"), "leqvio": ("J1306", 1, "inclisiran SC, 1 mg"),
    "skyrizi": ("J2327", 1, "risankizumab IV, 1 mg (IV induction only; SC is Part D)"),
    "tremfya": ("J1628", 1, "guselkumab IV, 1 mg (IV induction only; SC is Part D)"),
    "cosentyx": ("J3247", 1, "secukinumab IV, 1 mg (IV only; SC is Part D)"),
    "cabenuva": ("J0741", None, "cabotegravir 2 mg + rilpivirine 3 mg per unit (combination unit, no per-mg)"),
    "apretude": ("J0739", 1, "cabotegravir PrEP, 1 mg"), "yeztugo": ("J0738", 1, "lenacapavir PrEP inj, 1 mg (from 2025Q4; J1961 is Sunlenca, not Yeztugo)"),
}


def mg_per_unit(desc, unit):
    d = desc.upper()
    if "STARTER" in d or "CO-PACK" in d or "DAILY DOSE" in d:
        return None
    if unit == "EA":
        m = re.search(r"(?<![-\d.])(\d+(?:\.\d+)?) MG(?:/[\d.]+ ML)? (SYRINGE|KIT|PEN)", d) or \
            re.search(r"PEN (\d+(?:\.\d+)?) MG/[\d.]+ ML$", d)
        if m and not re.search(r"\d-\d", d):
            return float(m.group(1))
        return None
    if unit == "ML":
        m = re.search(r"\((\d+(?:\.\d+)?) MG/(\d+(?:\.\d+)?) ML\)", d) or re.search(r"\((\d+(?:\.\d+)?) MG/(ML)\)", d) \
            or re.search(r"(\d+(?:\.\d+)?) MG/(\d+(?:\.\d+)?) ?ML", d) or re.search(r"(\d+(?:\.\d+)?) MG/(ML)", d)
        if m:
            den = 1.0 if m.group(2) == "ML" else float(m.group(2))
            return float(m.group(1)) / den
    return None


def load():
    nad = pd.read_csv(T + "nadac_history.csv", dtype={"ndc": str})
    nad = nad[nad.match_kind == "brand"].copy()
    nad["year"] = pd.to_datetime(nad.as_of_date, errors="coerce").dt.year
    nad["p"] = pd.to_numeric(nad.nadac_per_unit, errors="coerce")
    nad = nad.dropna(subset=["year", "p"]).drop_duplicates(["ndc", "as_of_date"])
    sd = pd.read_csv(T + "medicaid_sdud.csv", dtype={"ndc": str})
    sd = sd[sd.drug != "drug"]
    sd["units"] = pd.to_numeric(sd.units_reimbursed, errors="coerce")
    sd["year"] = pd.to_numeric(sd.year, errors="coerce")
    su = sd.groupby(["ndc", "year"]).units.sum()
    pdd = pd.read_csv(T + "partd_by_year.csv")
    asp = pd.read_csv(T + "partb_asp_quarterly.csv")
    asp["year"] = asp.quarter.str[:4].astype(int)
    return nad, su, pdd, asp


def mfp_rows(slug, ndc9s):
    p = Path(f"data/corpus/drugs/{slug}/ira_negotiation.csv")
    if not p.exists():
        return None, None
    m = pd.read_csv(p, dtype=str)
    m["ndc11"] = m["NDC-11"].str.replace("-", "")
    m["ndc9"] = m.ndc11.str[:9]
    m["u"] = pd.to_numeric(m["NDC-9 MFP per Unit Price"], errors="coerce")
    m["d30"] = pd.to_numeric(m["Single MFP per 30 DES"], errors="coerce")
    m["eff"] = pd.to_datetime(m["MFP Effective Date"], errors="coerce").dt.year
    ipay = int(m.IPAY.iloc[0])
    m = m[m.eff == ipay]  # initial MFP year only (drops the next-year inflation rows)
    if ndc9s is not None and len(m) and "; " in m["Selected Drug Name"].iloc[0]:
        m = m[m.ndc9.isin(ndc9s)]  # combined selections (Ozempic; Rybelsus; Wegovy): keep this brand's NDCs only
    return ipay, m


def build():
    nad, su, pdd, asp = load()
    rows = []
    for slug in DRUGS:
        n = nad[nad.drug == slug].copy()
        n["mg"] = [mg_per_unit(a, b) for a, b in zip(n.ndc_description, n.pricing_unit)]
        ndc9s = set(n.ndc.str[:9]) if len(n) else None
        ipay, m = mfp_rows(slug, ndc9s)
        d = pdd[(pdd.drug == slug) & (pdd.mftr == "Overall") & (pdd.grain == "year")].dropna(subset=["total_spend", "dosage_units"])
        hc = HCPCS.get(slug)
        a = asp[asp.hcpcs == hc[0]] if hc else asp.iloc[0:0]
        if slug == "yeztugo":
            a = a[a.quarter >= "2025Q4"]
        years = sorted(set(n.year.astype(int)) | set(d.period.astype(int)) | set(a.year) | ({ipay} if ipay and m is not None and m.u.notna().any() else set()))
        for y in [y for y in years if 2020 <= y <= 2027]:
            r = {"drug": slug, "company": DRUGS[slug][3], "year": y}
            notes = []
            # ---- Part D (list-like, pre-rebate gross)
            g = d[d.period.astype(int) == y]
            if len(g):
                r["partd_spend_per_unit"] = g.total_spend.sum() / g.dosage_units.sum()
                r["partd_spend_per_claim"] = g.total_spend.sum() / g.claims.sum()
                r["partd_units_per_claim"] = g.dosage_units.sum() / g.claims.sum()
                r["partd_unit"] = "Part D dosage unit (NCPDP billing unit: EA tablet/vial or mL), summed over brand rows: " + "; ".join(g.brand)
                r["partd_src"] = "; ".join(g.source_row)
            # ---- NADAC (list-like): simple mean (collector) and Medicaid-units-weighted by NDC
            ny = n[n.year == y]
            if len(ny):
                per = ny.groupby("ndc").agg(p=("p", "mean"), unit=("pricing_unit", "first"), mg=("mg", "first"), desc=("ndc_description", "first"))
                units = sorted(per.unit.unique())
                r["nadac_unit"] = "/".join(units)
                r["nadac_ndc_count"] = len(per)
                r["nadac_simple_mean_per_unit"] = ny.p.mean()
                r["nadac_ndc_price_cv"] = per.p.std() / per.p.mean() if len(per) > 1 else 0.0
                main = per[per.unit == per.unit.mode().iloc[0]].copy()
                w = np.array([su.get((k, y), 0.0) for k in main.index])
                if w.sum() > 0:
                    r["nadac_weighted_per_unit"] = float((main.p * w).sum() / w.sum())
                    r["nadac_weight_basis"] = f"Medicaid SDUD {y} units by NDC, {main.unit.iloc[0]} NDCs only"
                    mm = main.mg.notna() & (w > 0)
                    if mm.all():
                        r["nadac_weighted_per_mg"] = float((main.p * w).sum() / (main.mg * w).sum())
                else:
                    r["nadac_weighted_per_unit"] = float(main.p.mean())
                    r["nadac_weight_basis"] = f"unweighted NDC mean (no SDUD units {y}), {main.unit.iloc[0]} NDCs only"
                    if main.mg.notna().all():
                        r["nadac_weighted_per_mg"] = float((main.p / main.mg).mean())
                if len(units) > 1:
                    notes.append(f"NADAC mixes {'/'.join(units)} NDCs; collector simple mean is not a valid per-unit price, weighted figure uses {main.unit.iloc[0]} NDCs only")
                r["nadac_src"] = f"nadac_history.csv drug={slug} as_of year {y}, NDCs " + ",".join(list(per.index)[:6])
            # ---- Part B ASP payment limit (net-like, ASP+6%)
            ay = a[a.year == y]
            if len(ay):
                r["asp_hcpcs"] = hc[0]
                r["asp_hcpcs_unit"] = hc[2]
                r["asp_payment_limit_per_hcpcs_unit"] = ay.payment_limit.astype(float).mean()
                r["asp_quarters"] = len(ay)
                if hc[1]:
                    r["asp_payment_limit_per_mg"] = r["asp_payment_limit_per_hcpcs_unit"] / hc[1]
                    r["asp_est_per_mg"] = r["asp_payment_limit_per_mg"] / 1.06
                r["partb_src"] = "; ".join(ay.source_row.head(4))
                if len(ay) < 4:
                    notes.append(f"ASP mean of {len(ay)} quarters only")
            # ---- IRA MFP (net-like statutory price), NDC-matched to NADAC
            if ipay and m is not None and y == ipay and m.u.notna().any():
                r["ira_ipay"] = ipay
                r["ira_mfp_effective"] = f"{ipay}-01-01"
                r["ira_mfp_per_30day"] = float(m.d30.dropna().iloc[0])
                mm = m.dropna(subset=["u"]).drop_duplicates("ndc9")
                r["ira_mfp_per_unit_ndc_median"] = float(mm.u.median())
                r["ira_mfp_unit_range"] = f"{mm.u.min():.4g}-{mm.u.max():.4g}"
                # NADAC for the same NDC-9, latest available year <= MFP year
                ny2 = n[n.year == min(y, int(n.year.max()))] if len(n) else n
                if len(ny2):
                    pn = ny2.assign(ndc9=ny2.ndc.str[:9]).groupby("ndc9").agg(p=("p", "mean"), unit=("pricing_unit", "first"))
                    j = mm.set_index("ndc9").join(pn, how="inner")
                    if len(j):
                        j["ratio"] = j.p / j.u
                        j["nadac_30d"] = j.p * (j.d30 / j.u)
                        r["nadac_vs_mfp_ndc_matched_median"] = float(j.ratio.median())
                        r["nadac_vs_mfp_ndc_range"] = f"{j.ratio.min():.2f}-{j.ratio.max():.2f}"
                        r["nadac_vs_mfp_ndc_n"] = len(j)
                        r["nadac_per_30day_median"] = float(j.nadac_30d.median())
                        r["mfp_unit_basis"] = f"NCPDP unit of each NDC-9 ({'/'.join(sorted(j.unit.unique()))}); 30-day units = Single MFP per 30 DES / NDC-9 MFP per unit (CMS columns)"
                        r["nadac_year_for_mfp"] = int(ny2.year.iloc[0])
                r["ira_src"] = f"data/corpus/drugs/{slug}/ira_negotiation.csv IPAY={ipay}, initial-MFP rows"
                if "Deselect" in set(m["Type of Update"]):
                    notes.append("CMS lists all Stelara NDCs as deselected with MFP end date 2026-12-31 (biosimilar entry)")
            # ---- comparisons, only like with like
            if "partd_spend_per_unit" in r and "nadac_weighted_per_unit" in r:
                same_ea = r.get("nadac_unit") == "EA" and r.get("nadac_ndc_price_cv", 1) < 0.10
                if same_ea:
                    r["partd_vs_nadac_ratio"] = r["partd_spend_per_unit"] / r["nadac_weighted_per_unit"]
                    r["partd_vs_nadac_basis"] = "like with like: per tablet/unit, NDC prices within 10% (flat pricing)"
                else:
                    r["partd_vs_nadac_ratio_indicative"] = r["partd_spend_per_unit"] / r["nadac_weighted_per_unit"]
                    r["partd_vs_nadac_basis"] = "mix-sensitive: Part D brand-level units mix strengths/presentations; Medicare and Medicaid mixes differ; indicative only"
            if "asp_payment_limit_per_mg" in r and "nadac_weighted_per_mg" in r:
                if slug == "stelara":
                    r["asp_vs_nadac_per_mg"] = r["asp_est_per_mg"] / r["nadac_weighted_per_mg"]
                    r["asp_vs_nadac_basis"] = "like with like: ustekinumab SC, ASP (payment limit / 1.06) per mg vs SDUD-weighted NADAC per mg from label strength (45 mg/0.5 mL, 90 mg/mL)"
                else:
                    notes.append("ASP is the IV presentation, NADAC is SC; per-mg prices differ by presentation, no ratio")
            r["basis_note"] = basis_note(slug, r, notes)
            rows.append(r)
    df = pd.DataFrame(rows)
    df["source"] = "verified from tables/partd_by_year.csv, nadac_history.csv, medicaid_sdud.csv, partb_asp_quarterly.csv, data/corpus/drugs/<drug>/ira_negotiation.csv"
    df["source_row"] = df.drug + "|" + df.year.astype(str)
    df.to_csv(OUT / "gtn_proxy.csv", index=False)
    return df


def basis_note(slug, r, notes):
    parts = []
    if "partd_unit" in r:
        parts.append(f"PartD per {'unit' if r.get('partd_units_per_claim') else '?'} ({r['partd_units_per_claim']:.2f} units/claim)")
    if "nadac_unit" in r:
        parts.append(f"NADAC per {r['nadac_unit']}")
    if "asp_hcpcs" in r:
        parts.append(f"ASP per HCPCS unit {r['asp_hcpcs']} ({HCPCS[slug][2]})")
    if "ira_mfp_per_30day" in r:
        parts.append("MFP per NDC-9 NCPDP unit and per 30-day equivalent supply")
    return "; ".join(parts + notes)


if __name__ == "__main__":
    df = build()
    print(len(df), df.drug.nunique())
    show = ["drug", "year", "partd_spend_per_unit", "partd_units_per_claim", "nadac_unit", "nadac_simple_mean_per_unit", "nadac_weighted_per_unit",
            "nadac_weighted_per_mg", "asp_hcpcs", "asp_payment_limit_per_mg", "ira_mfp_per_unit_ndc_median", "nadac_vs_mfp_ndc_matched_median",
            "nadac_vs_mfp_ndc_range", "partd_vs_nadac_ratio", "asp_vs_nadac_per_mg"]
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 400)
    sel = df[df.drug.isin(["stelara", "januvia", "ozempic", "entyvio", "eliquis", "wegovy", "rybelsus", "enbrel", "farxiga", "xarelto", "jardiance", "janumet", "ibrance", "darzalex"])]
    sel[[c for c in show if c in df.columns]].round(3).to_csv("/tmp/pv_sel.csv", index=False)
