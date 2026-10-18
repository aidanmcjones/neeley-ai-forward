from agent.moat.common import note_gap
for t, i, r in [
    ("ROCHE,BOEHRINGER", "company_cost_structure", "no XBRL or 10-K/20-F in corpus (Roche, Boehringer not SEC filers in corpus)"),
    ("NVO", "SG&A / sales and distribution costs", "not tagged in ifrs-full companyfacts; read from 20-F income statement not done"),
    ("ALL", "number of Phase 3 programs and R&D by stage/program", "not extracted; only company-level R&D in table"),
    ("ALL", "sales-force size", "only Novartis states a field-force FTE count (FY2023-FY2025); no US 10-K gives rep counts"),
    ("ALL", "headcount for peers GSK, NVS, SNY, TAK(FY2021-23), BBIO, REGN FY2021-24, ALNY FY2021-24", "partial: XBRL NumberOfEmployees where tagged only"),
    ("ALL", "Open Payments by nature and manufacturer breakdown, PY2025", "per-drug filtered queries take ~30s each and stalled under concurrency; only PY2023-2024 totals collected; royalty/ownership-type natures may inflate some drugs (e.g. Tecentriq)"),
    ("ALL", "new_indication_benchmarks join", "trial-to-supplement match is heuristic (nearest Phase 3 with >=100 enrolled finishing 0-900 days before approval); verify before quoting a single row"),
]:
    note_gap("costs", t, i, r)
