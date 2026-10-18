"""rx verifier item 3: Part D claims per 1,000 Part D enrollees by state. Recomputes 6 drugs x 10 states for 2023 from
the raw provider-drug pulls and the CMS Medicare Monthly Enrollment annual state rows, confirms the denominator is
PRSCRPTN_DRUG_TOT_BENES (Part D enrollees) not TOT_BENES, and adds all-prescriber state claims from CMS Geography and
Drug for 8 brands (2023, 2024) so the rate is not cut by the 11-claim rule."""
import pandas as pd

from agent.moat.verify.rx_lib import ROOT, classify, cms, out, raw_partd

T = ROOT / "data/moat/tables"
ENR = "d7fabe1e-d19b-4333-9eff-e80e0643f2fd"
DRUGS6 = ["eliquis", "ozempic", "jardiance", "mounjaro", "repatha", "xarelto"]
STATES = ["CA", "TX", "FL", "NY", "PA", "OH", "IL", "MI", "GA", "NC"]
ABBR = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
        "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
        "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
        "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
        "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
        "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND",
        "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
        "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
        "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
        "Puerto Rico": "PR"}


def main():
    col = pd.read_csv(T / "partd_prescribers_by_state.csv")
    enr = {}
    for y in (2023, 2024):
        for x in cms(ENR, {"filter[YEAR]": str(y), "filter[MONTH]": "Year", "filter[BENE_GEO_LVL]": "State"}):
            enr[(y, x["BENE_STATE_ABRVTN"])] = (pd.to_numeric(x["PRSCRPTN_DRUG_TOT_BENES"], errors="coerce"),
                                                pd.to_numeric(x["TOT_BENES"], errors="coerce"))
    raw = raw_partd(2023)
    raw["drug"] = [classify(b) for b in raw.Brnd_Name]
    mine = raw[raw.drug.isin(DRUGS6)].groupby(["drug", "Prscrbr_State_Abrvtn"]).Tot_Clms.sum()
    geo = pd.read_csv("/tmp/rxv/geo.csv")
    gs = geo[geo.Prscrbr_Geo_Lvl == "State"].copy()
    gs["state"] = gs.Prscrbr_Geo_Desc.map(ABBR)
    gs = gs.groupby(["drug", "year", "state"]).Tot_Clms.sum()
    rows = []
    for _, r in col.iterrows():
        o = r.to_dict()
        notes, ok = [], True
        e = enr.get((r.year, r.state))
        if e is not None:
            o["partd_enrollees_cms"], o["total_medicare_benes_cms"] = e
            if not pd.isna(r.partd_enrollees) and abs(e[0] - r.partd_enrollees) > 0.5:
                ok = False
                notes.append(f"denominator {r.partd_enrollees:,.0f} != Part D enrollees {e[0]:,.0f}")
        o["claims_per_1000_partd_enrollees_unrounded"] = (r.claims / r.partd_enrollees * 1000) if r.partd_enrollees else None
        if not pd.isna(o["claims_per_1000_partd_enrollees_unrounded"]) and \
                abs(round(o["claims_per_1000_partd_enrollees_unrounded"], 2) - r.claims_per_1000_partd_enrollees) > 0.011:
            ok = False
            notes.append("rate does not equal claims / enrollees * 1000")
        g = gs.get((r.drug, r.year, r.state))
        if g is not None and not pd.isna(g):
            o["claims_all_prescribers_cms"] = g
            if r.partd_enrollees:
                o["claims_all_prescribers_per_1000_partd_enrollees"] = g / r.partd_enrollees * 1000
        smp = r.drug in DRUGS6 and r.year == 2023 and r.state in STATES
        if smp:
            m = mine.get((r.drug, r.state))
            if m is None or abs(m - r.claims) > 0.5:
                ok = False
                notes.append(f"raw recompute gives {m} claims")
            else:
                notes.append("claims recomputed from raw; denominator is PRSCRPTN_DRUG_TOT_BENES for the same state-year")
        notes.append("numerator is claims by prescribers located in the state (not beneficiaries living there) with 11+ "
                     "claims; rate rounded to 2 decimals in the collector file, use the _unrounded column for small drugs")
        o["in_opus_sample"] = smp
        o["verify_status"] = "verified" if ok else "corrected"
        o["verify_note"] = "; ".join(notes)
        rows.append(o)
    d = pd.DataFrame(rows)
    out("partd_prescribers_by_state.csv", d.round(4), "CMS Part D Prescribers by Provider and Drug + Medicare Monthly Enrollment")
    s = d[d.in_opus_sample]
    print(len(s), d.verify_status.value_counts().to_dict(), s.verify_status.value_counts().to_dict(),
          int((d.claims_per_1000_partd_enrollees == 0).sum()))
    print(s[["drug", "state", "claims", "partd_enrollees", "total_medicare_benes_cms", "claims_per_1000_partd_enrollees",
             "claims_all_prescribers_per_1000_partd_enrollees"]].head(12).round(2).to_string())


if __name__ == "__main__":
    main()
