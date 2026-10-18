import pandas as pd

from agent.moat.common import note_gap

o = pd.read_csv("data/moat/tables/open_payments_by_drug.csv")
t = o.groupby("drug").agg(usd=("total_usd", "sum"), n=("n_payments", "sum"), food=("usd_food", "sum"), consult=("usd_consulting", "sum"),
                          speak=("usd_speaking", "sum")).sort_values("usd", ascending=False)
print(t.head(10).round(0))
print(t.loc[["keytruda", "opdivo", "eliquis"]].round(0) if "keytruda" in t.index else "no keytruda")
print(o[o.n_physicians_upper_bound.notna()].shape, o.program_year.unique())
note_gap("rx", "ALL", "open_payments_n_physicians", "distinct-physician counts only for drug-slot pairs finished before the timebox (program year 2024 partly); other rows blank. Resume: PYTHONPATH=. python -m agent.moat.rx_openpay after removing the early return in job_phys")
note_gap("rx", "ALL", "open_payments_physicians_2021_2023", "not queried (30 s table scan per drug-slot-year); set PHYS_FROM=2021 in agent/moat/rx_openpay.py and rerun")
note_gap("rx", "ALL", "partd_state_enrollment", "claims_per_1000 uses CMS Medicare Monthly Enrollment PRSCRPTN_DRUG_TOT_BENES (state, annual row); suppressed states are blank")
note_gap("rx", "IV biologics", "partd_prescribers", "Keytruda, Opdivo, Tecentriq, Imfinzi, Darzalex, Entyvio, Leqvio, Amvuttra, Sarclisa, Rybrevant have only incidental Part D rows; use partb_providers_by_drug.csv")
note_gap("rx", "Cabenuva", "partb", "J0741 returned no provider rows in 2021-2023 (check HCPCS code / J3490 billing)")
note_gap("rx", "ALL", "formulary_rxcui_mapping", "RXCUIs mapped via RxNav SBD plus related SCD; biologics are mostly absent from Part D formularies (shown as not covered)")
