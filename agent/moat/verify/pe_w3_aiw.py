"""Peers wave 3: append the AI errors found in the wave-3 collector tables to data/moat/verify/ai_wrong.jsonl.
Run once (it appends). Counts come from pe_w3_rev.py / pe_w3_promote.py output.

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_aiw.py
"""
from agent.moat.verify.pe_lib import log_wrong

T = "tables/peer_product_revenue_wave3.csv"
E = [
    dict(stream="peers", table=T, row_key="GSK Q4 releases (2024-01-31, 2025-02-05, 2026-02-04)",
         what_the_ai_wrote="rows from the 'year ended 31 December' tables labelled Q4 and rows from the 'three months ended 31 December' tables labelled FY (e.g. Meningitis 2023Q4 = 1,260)",
         what_the_source_says="Meningitis 1,260 sits under 'Vaccines turnover - year ended 31 December 2023' (line 8346); the Q4 figure is 273 under the three-months table (line 8989)",
         error_type="period_scope_swap", severity="high", how_caught="nearest governing table header re-derived for every row",
         count=163, example_cite="data/moat/companies/GSK/6k/2024-01-31_0001654954-24-001113.md line 8440 (header line 8346)"),
    dict(stream="peers", table=T, row_key="SNY FY / H1 / YTD appendix rows",
         what_the_ai_wrote="48 rows from the FY, H1 or YTD appendix labelled as the quarter (e.g. Aldurazyme 279 as 2023Q4) plus 6 rows from the H1 2024 half-year management report labelled 2024Q2",
         what_the_source_says="rows sit under 'Full year 2023', 'Appendix 1: H1 2025 net sales', 'YTD 2024 (EUR million)'; the half-year report table is six-month data (Total Sanofi 21,209 = H1 2024)",
         error_type="period_scope_mislabel", severity="high", how_caught="governing table header per row", count=54,
         example_cite="data/moat/companies/SNY/6k/2024-02-01_0001121404-24-000003.md line 810 under 'Full year 2023' (line 783)"),
    dict(stream="peers", table=T, row_key="TAK FY<year>Q2/Q3/Q4 rows",
         what_the_ai_wrote="scope=Q2/Q3/Q4 (single quarter), e.g. GATTEX/REVESTIVE FY2023Q3 = JPY 90.0bn",
         what_the_source_says="Takeda releases give cumulative figures: 'Revenue for the nine-month period ended December 31, 2023'; Q2 = six months, Q3 = nine months, Q4 = full fiscal year. Only Q1 rows are a single quarter",
         error_type="period_scope_ytd_as_quarter", severity="high", how_caught="'Summary of Financial Statements for the Nine-month Period' header and revenue sentence",
         count=102, example_cite="data/moat/companies/TAK/6k/2024-02-01_0001395064-24-000011_ex2.md p9 line 486 (line 405)"),
    dict(stream="peers", table=T, row_key="GSK wrapped names",
         what_the_ai_wrote="first line dropped from names that wrap: 'Acting Injectables', 'Respiratory' (for Other Respiratory), 'General Medicines' (for Other General Medicines), 'Vaccines', 'Medicines', 'Varilrix', 'Pediarix', 'FluLaval', 'Immunology and Inflammation'",
         what_the_source_says="'Long-Acting Injectables', 'Other Respiratory', 'Other General Medicines', 'Established Vaccines', 'Specialty Medicines', 'Priorix, Priorix Tetra, Varilrix', 'Infanrix, Pediarix', 'Fluarix, FluLaval', 'Respiratory, Immunology and Inflammation'. 'Respiratory' 146 in 2025Q2 is Other Respiratory, not the Respiratory subtotal",
         error_type="truncated_name", severity="high", how_caught="preceding text-fragment lines joined to the name",
         count=29, example_cite="data/moat/companies/GSK/6k/2026-07-28_0001654954-26-006949.md lines 9304-9305 'Other' / 'Respiratory'"),
    dict(stream="peers", table=T, row_key="GSK and SNY subtotals",
         what_the_ai_wrote="therapeutic-area and segment totals (HIV, Respiratory, Vaccines, Specialty Care, Total Sanofi) and 'Other' buckets mixed with products with no row type",
         what_the_source_says="GSK bold category rows are subtotals of the indented products below; SNY 'Total ...', GBU and franchise lines are totals",
         error_type="subtotal_mixed_with_products", severity="medium", how_caught="name list plus GSK bold/indent layout",
         count=258, example_cite="data/moat/companies/GSK/6k/2024-01-31_0001654954-24-001113.md line 9679 'HIV 6,444'"),
    dict(stream="peers", table=T, row_key="SNY 2024-07-25 000016",
         what_the_ai_wrote="half-year management report (exhibit 99.2) mined as a separate results release",
         what_the_source_says="same H1 2024 figures as the results release 0001121404-24-000018",
         error_type="duplicate_alternate_filing", severity="low", how_caught="value match against the release", count=6,
         example_cite="data/moat/companies/SNY/6k/2024-07-25_0001121404-24-000016.md p13 line 659 Lantus 758"),
]
log_wrong(E)
print(len(E), "entries appended")
