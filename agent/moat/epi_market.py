"""epi stream steps 3-4: medicare_market.csv and market_sizing_inputs.csv."""
import csv
import io

import pandas as pd

from agent.moat.common import OUT, note_gap, write

CLASS = {
    "mounjaro": "GLP-1/GIP agonist", "zepbound": "GLP-1/GIP agonist", "ozempic": "GLP-1/GIP agonist", "wegovy": "GLP-1/GIP agonist",
    "rybelsus": "GLP-1/GIP agonist", "trulicity": "GLP-1/GIP agonist", "foundayo": "GLP-1/GIP agonist",
    "januvia": "DPP-4 inhibitor", "janumet": "DPP-4 inhibitor",
    "farxiga": "SGLT2 inhibitor", "jardiance": "SGLT2 inhibitor",
    "eliquis": "oral anticoagulant (factor Xa)", "xarelto": "oral anticoagulant (factor Xa)",
    "repatha": "PCSK9 mAb / LDL-lowering injectable", "praluent": "PCSK9 mAb / LDL-lowering injectable",
    "leqvio": "PCSK9 mAb / LDL-lowering injectable", "lipfendra": "PCSK9 mAb / LDL-lowering injectable",
    "humira": "TNF inhibitor / adalimumab", "amjevita": "TNF inhibitor / adalimumab", "enbrel": "TNF inhibitor / adalimumab",
    "stelara": "IL-12/23 and IL-23 inhibitor", "wezlana": "IL-12/23 and IL-23 inhibitor", "skyrizi": "IL-12/23 and IL-23 inhibitor",
    "tremfya": "IL-12/23 and IL-23 inhibitor", "cosentyx": "IL-17 inhibitor", "entyvio": "integrin inhibitor (IBD)",
    "rinvoq": "JAK inhibitor",
    "keytruda": "PD-1/PD-L1 checkpoint inhibitor", "keytruda-qlex": "PD-1/PD-L1 checkpoint inhibitor", "opdivo": "PD-1/PD-L1 checkpoint inhibitor",
    "opdivo-qvantig": "PD-1/PD-L1 checkpoint inhibitor", "imfinzi": "PD-1/PD-L1 checkpoint inhibitor", "tecentriq": "PD-1/PD-L1 checkpoint inhibitor",
    "ibrance": "CDK4/6 inhibitor", "verzenio": "CDK4/6 inhibitor", "kisqali": "CDK4/6 inhibitor",
    "tagrisso": "EGFR-directed NSCLC therapy", "rybrevant": "EGFR-directed NSCLC therapy", "lazcluze": "EGFR-directed NSCLC therapy",
    "darzalex": "anti-CD38 antibody", "darzalex-faspro": "anti-CD38 antibody", "sarclisa": "anti-CD38 antibody",
    "vyndaqel": "ATTR-CM therapy", "vyndamax": "ATTR-CM therapy", "attruby": "ATTR-CM therapy", "amvuttra": "ATTR-CM therapy",
    "biktarvy": "HIV-1 treatment regimen", "dovato": "HIV-1 treatment regimen", "cabenuva": "HIV-1 treatment regimen",
    "apretude": "HIV PrEP", "yeztugo": "HIV PrEP",
}
PD_SRC = "https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug (R2 public/partd_spending_dy24.csv) via data/moat/tables/partd_by_year.csv"


def tocsv(df):
    b = io.StringIO()
    df.to_csv(b, index=False, quoting=csv.QUOTE_MINIMAL)
    return b.getvalue()


def main():
    pd_ = pd.read_csv(OUT / "tables" / "partd_by_year.csv")
    ov = pd_[pd_.mftr == "Overall"].copy()
    ov["class"] = ov.drug.map(CLASS)
    g = ov.groupby(["class", "drug", "period"], dropna=False).agg(
        part_d_claims=("claims", "sum"), part_d_spend=("total_spend", "sum"), part_d_benes_floor=("benes", "max"),
        part_d_benes_sum_presentations=("benes", "sum"), presentations=("brand", "nunique")).reset_index()
    g["spend_per_claim"] = (g.part_d_spend / g.part_d_claims).round(2)

    sd = pd.read_csv(OUT / "tables" / "medicaid_sdud.csv")
    sg = sd.groupby(["drug", "year"]).agg(medicaid_prescriptions=("prescriptions", "sum"), medicaid_reimbursed=("medicaid_amount_reimbursed", "sum"),
                                         quarters=("quarter", "nunique")).reset_index()
    sg["period"] = sg.year.astype(str)
    g = g.merge(sg[["drug", "period", "medicaid_prescriptions", "medicaid_reimbursed", "quarters"]], on=["drug", "period"], how="left")
    g = g.rename(columns={"quarters": "medicaid_quarters_in_period"})
    tot = g[g.period == "2024"].groupby("class").agg(class_claims_2024=("part_d_claims", "sum"), class_spend_2024=("part_d_spend", "sum"),
                                                     class_benes_floor_2024=("part_d_benes_floor", "sum")).reset_index()
    g = g.merge(tot, on="class", how="left")
    g["drug_share_of_class_claims_2024"] = g.apply(lambda r: round(r.part_d_claims / r.class_claims_2024, 4) if r.period == "2024" and r.class_claims_2024 else None, axis=1)
    g["source"] = PD_SRC + "; Medicaid: " + "https://data.medicaid.gov/dataset/cc318bfb-a9b2-55f3-a924-d47376b32ea3 via data/moat/tables/medicaid_sdud.csv"
    g["source_row"] = g.apply(lambda r: f"drug={r.drug}|period={r.period}|mftr=Overall (sum of {r.presentations} brand presentations)", axis=1)
    g["note"] = ("benes_floor = largest single presentation's beneficiary count (a beneficiary can use more than one presentation, so the true unique count lies between floor and sum); "
                 "class benes_floor sums drug floors, so a beneficiary on two drugs in a class is double counted; 2025 period is Q1-Q4 file, 2026 is Q1 only; "
                 "keytruda-qlex and opdivo-qvantig Part D rows are mostly IV parent data per corpus GAPS note")
    g = g.sort_values(["class", "drug", "period"])
    write("epi", "tables/medicare_market.csv", tocsv(g), group="epi", doc_type="epi_table", source_url=PD_SRC)
    print("medicare_market", len(g))

    # sizing inputs
    m = pd.read_csv(OUT / "tables" / "indication_map.csv")
    e = pd.read_csv(OUT / "tables" / "indication_epidemiology.csv").set_index("indication")
    d24 = g[g.period == "2024"].set_index("drug")
    rows = []
    for _, r in m.drop_duplicates(["drug", "indication"]).iterrows():
        dr, ind = r.drug, r.indication
        x = d24.loc[dr] if dr in d24.index else None
        has = ind in e.index
        ep = e.loc[ind] if has else None
        prev = ep.us_prevalence_n if has else None
        diag_n = ep.diagnosed_n if has and pd.notna(ep.diagnosed_n) else None
        floor = float(x.part_d_benes_floor) if x is not None and pd.notna(x.part_d_benes_floor) else None
        cls_floor = float(x.class_benes_floor_2024) if x is not None and pd.notna(x.class_benes_floor_2024) else None
        denom = diag_n if diag_n else prev
        denom_basis = "diagnosed" if diag_n else "prevalent"
        multi = (m[m.drug == dr].indication.nunique() > 1)
        note = []
        if has and pd.notna(prev):
            note.append(f"funnel: prevalence {int(prev):,} ({ep.prevalence_year}); diagnosed {ep.diagnosed_share if pd.notna(ep.diagnosed_share) else 'n/a'}%; treated {ep.treated_share if pd.notna(ep.treated_share) else 'n/a'}%")
        else:
            note.append("no collected epidemiology for this indication (see GAPS)")
        if floor:
            note.append(f"Medicare Part D 2024 beneficiaries on {dr} (floor) {int(floor):,} = {floor/denom*100:.2f}% of {denom_basis} US patients" if denom and pd.notna(denom) else f"Medicare Part D 2024 beneficiaries on {dr} (floor) {int(floor):,}")
        if multi:
            note.append("drug has several indications: Part D beneficiaries are drug-level and cannot be split by indication, so the share overstates this indication")
        if ind in ("NSCLC", "SCLC", "HR+/HER2- breast cancer", "triple-negative breast cancer", "HER2+ breast cancer", "colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H"):
            note.append("cancer prevalence is for the whole site; apply a subtype/stage/line share before use")
        if dr in ("keytruda-qlex", "opdivo-qvantig"):
            note.append("Part D data is the IV parent's")
        rows.append(dict(
            drug=dr, indication=ind, drug_class=CLASS.get(dr, ""), label_section=r.label_section,
            us_prevalence_n=prev if has else "", prevalence_year=ep.prevalence_year if has else "",
            annual_incidence_n=ep.annual_incidence_n if has else "", diagnosed_share_pct=ep.diagnosed_share if has else "",
            diagnosed_n=diag_n or "", class_treated_share_pct=ep.treated_share if has else "",
            share_aged_65plus=ep.share_aged_65plus if has else "",
            medicare_partd_benes_on_drug_2024_floor=floor or "", medicare_partd_class_benes_floor_2024=cls_floor or "",
            medicare_partd_claims_2024=float(x.part_d_claims) if x is not None else "",
            medicare_partd_spend_2024=float(x.part_d_spend) if x is not None else "",
            medicaid_prescriptions_2024=float(x.medicaid_prescriptions) if x is not None and pd.notna(x.medicaid_prescriptions) else "",
            medicare_floor_pct_of_denominator=round(floor / denom * 100, 3) if floor and denom and pd.notna(denom) else "",
            denominator_basis=denom_basis if denom and pd.notna(denom) else "",
            method_note=" | ".join(note),
            source=(ep.source if has else "") + " ; " + PD_SRC, source_row=f"{dr}|{ind}"))
    out = pd.DataFrame(rows)
    write("epi", "tables/market_sizing_inputs.csv", tocsv(out), group="epi", doc_type="epi_table", source_url="derived: indication_map x epidemiology x Part D")
    print("market_sizing_inputs", len(out), "with epi", int((out.us_prevalence_n != "").sum()))
    if d24.shape[0] < 40:
        note_gap("epi", "partd", "2024 coverage", f"only {d24.shape[0]} drugs with 2024 Part D rows")


if __name__ == "__main__":
    main()
