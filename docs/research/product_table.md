# Product table (agent/product_table.py)

One row per company x brand answering "when does exclusivity end" and "when does pricing change". Works for any tickers or CIKs: the 14 candidates in `agent.gap_data.COMPANIES` use their applicant regexes; any other company gets a regex built from its SEC name (no XBRL revenue unless `agent.gap_data --steps products --ciks <cik>` has run for it).

## Run

```
PYTHONPATH=. python -m agent.product_table --tickers BMY,PFE,JNJ          # writes to R2
PYTHONPATH=. python -m agent.product_table --ciks 14272,78003 --no-upload  # writes to data/derived/product_table/
PRODUCT_TABLE_CACHE=/tmp/ptcache ...                                       # cache R2 inputs on disk (derived/ never cached)
```

In Python: `df, citations, timeline = agent.product_table.build(tickers=["BMY", "PFE", "JNJ"])`.

Outputs in R2: `derived/product_table/<TICKERS>.csv`, `<TICKERS>_citations.jsonl`, `<TICKERS>_timeline.json` (`brands` = sorted dated events per brand, `unmatched_revenue_members` = XBRL members not mapped to a brand, `inputs_present`).

## Rows kept

Brands the company holds (Orange Book Rx NDA or Purple Book 351(a) applicant matches the company) plus brands whose revenue the company books but someone else holds (Pfizer Eliquis, Pfizer Xtandi, J&J Imbruvica, Merck Lynparza). Line extensions with the same ingredient fold into the base brand (Eliquis Sprinkle into Eliquis). Kept when latest FY revenue >= $250M, or IRA selected, or the LOE year falls in 2024-2032 and the brand has revenue or Medicare spend. Sorted by revenue.

## Columns, sources, method

| Columns | Source (R2 key) | Method |
|---|---|---|
| brand, brand_group, ingredient, modality, appl_nos, nda_holder | classes/brand_products.jsonl.gz, public/orange_book.zip, public/purple_book_2026_09.csv | appl_nos = every Rx NDA / 351(a) BLA with that trade name |
| revenue_booker, partner_note | 10-K collaboration notes | `PARTNERED` table in the code. Eliquis: BMS books global sales; Pfizer reports alliance revenue (never add the two). Xarelto: J&J books US only, Bayer ex-US |
| revenue_member, revenue_fy, revenue_latest_fy, revenue_prior_fy, revenue_yoy, revenue_us, revenue_us_share, revenue_scope | xbrl_product/<cik>/<acc>.jsonl.gz from the latest 10-K | annual USD rows, zeros dropped. Total = the row with no geography (max across extra dims such as segment); if none, US + non-US; if only US, total = US and revenue_scope says so. Member to brand: normalized name exact, then prefix, then first word; own brands first, then any brand (partner); a few aliases (Vyndaqel to Vyndamax, Prevnar family to Prevnar 20) |
| company_revenue_fy, pct_of_company_revenue | xbrl/<cik>.json (companyfacts) | Revenues for the same accession and FY |
| loe_orange_book_substance, loe_last_listed_patent, exclusivity_latest_code/date | Orange Book patent.txt, exclusivity.txt | substance = oldest drug-substance patent (the compound patent), using its *PED row if one exists. Last listed = max of all patents |
| pb_ref_exclusivity, pb_orphan_exclusivity, biosimilar_count, interchangeable_flag, biosimilar_first_approval | Purple Book | 351(k) rows whose reference product name is the brand |
| piv_first_submission, piv_anda_count, piv_180day_status, piv_first_generic_marketing, piv_last_qualifying_patent | public/paragraph_iv.xlsx | joined on NDA number. ANDA count = max across strengths |
| generic_anda_holders_count, generic_anda_holders_marketed, generic_first_anda_approval | Orange Book products.txt | ANDAs with the same ingredient and dosage form/route; count includes DISCN (approved, not launched, often held back by settlement) |
| loe_fda_estimate | derived | section 1 rule. Small molecule: max(NCE date, + 30 months if a PIV exists; compound patent; ODE; NP). If none is unexpired, the first-filer marketing date or the first ANDA approval. Biologic: Purple Book reference exclusivity; when that has passed and biosimilars exist, the first biosimilar approval, labeled as a lower bound |
| loe_company_stated, loe_company_basis, loe_company_quote, loe_eu_stated | derived/company_stated_loe.jsonl; fallback derived/loe_curves.json `drugs` | product names normalized before the parenthesis and split on "/"; ranked: has a US date, then settlement, then the company's own row, then the plain (non-footnote) row. If no dated row, the LOE-curve set's verified 10-K LOE year ("10-K: loss of exclusivity in 2023") |
| loe_best_estimate, loe_best_year, loe_basis | derived | company-stated wins, else loe_fda_estimate. Text may be a year ("2028"), a month ("2026-01") or a date |
| partd_spend_2024, partd_spend_per_unit_2024, partd_per_unit_chg_23_24, partd_per_unit_cagr_20_24 | public/partd_spending_dy24.csv | `Overall` rows whose brand words start with the brand and whose generic name contains the ingredient; spend summed, per-unit from the largest row |
| partd_spend_2025, partd_spend_2026q1 | public/partd_quarterly_2025.csv.gz | same match, Overall rows |
| partb_spend_2024, partb_hcpcs, partb_asp_2024, partb_per_unit_chg_23_24 | public/partb_spending_dy24.csv | largest HCPCS row for ASP |
| ira_ipay, ira_selected_date, ira_mfp_30day, ira_mfp_effective, ira_mfp_30day_latest, ira_mfp_latest_effective, ira_deselected, ira_deselect_date, ira_deselect_scope | public/ira_selected_drugs_mfp.zip | exact brand match on Selected Drug Name. Initial MFP = earliest effective row; latest = inflation row. Deselect scope counts NDC-11s. Selection dates are the CMS announcement dates per IPAY |
| atc4, atc4_name, epc_class | classes/ingredient_classes.jsonl.gz | RxClass ATC level 4 (5-character code) and FDA EPC |
| competitors | same + Part D/B spend | other brands, any company, sharing an ATC level-4 class and a different ingredient; top 6 by 2024 Medicare spend; each with holder and LOE (10-K stated if any, else FDA rule) |
| formulary_coverage_share, formulary_tier_median, formulary_prior_auth_share, formulary_step_therapy_share | formulary/rxcui_summary.csv.gz | label RXCUIs (classes/brand_indications.jsonl.gz) joined to the SPUF summary; the RXCUI on the most formularies |
| indication | classes/brand_indications.jsonl.gz | first 300 characters of the openFDA label indication |
| phase3_active_same_molecule, phase3_active_same_area, phase3_area_terms | trials/<cik>.jsonl.gz | the company's active Phase 3 studies (recruiting, active not recruiting, not yet recruiting, by invitation). Same molecule = intervention or title mentions the ingredient or brand. Same area = trial conditions/keywords contain any disease term (fixed list of about 90, `AREA_TERMS`) that appears in the brand's label indication |
| revenue_at_risk_through_2030 | derived/loe_curves.json | median pct-of-peak curve per modality, shaped like `agent.loe_curves.revenue_at_risk` (running minimum, flat after year 4). Sum over FY+1..2030 of latest revenue x (1 - p(year)/p(FY)); LOE in the future means p(FY) = 1, so latest revenue is the pre-LOE run-rate |

Every non-null value has a citation row `{fact_id, company, brand, field, value, source_name, url_or_key, row_key, accession}`: R2 key plus file row or Orange Book key (`patent.txt N~202155~001~6967208*PED`), or the SEC accession for XBRL and 10-K facts.

## Known limits

- Revenue is the latest 10-K only (FY2025 for all 14). BMS and Pfizer tag no geography in XBRL, so `revenue_us_share` is blank for them. Merged members (Regeneron "EYLEA HD and EYLEA") and secondary members of the same brand (AbbVie Botox Cosmetic next to Botox Therapeutic) end up in `unmatched_revenue_members`, not summed.
- Brands with no product member (Pfizer Premarin, small legacy NDAs) have no revenue; they stay only because of IRA or LOE window plus Medicare spend.
- The Orange Book rule ignores settlements and use-code carve-outs. Xarelto shows 2025-03-03 because that is when the first 2.5 mg generic was approved; other strengths are still protected. Biologic FDA estimates are lower bounds (Humira's first biosimilar approval was 2016; launch was 2023). Company-stated dates fix this where the 10-K gives one.
- Darzalex and other big biologics with blank Purple Book exclusivity rely only on the 10-K date.
- Part D is gross spend before rebates. MFP and Part B ASP are the only near-net prices. NADAC, Drugs@FDA and the openFDA NDC file are in R2 but not used yet (brand-name joins were enough for these companies).
- Formulary coverage is blank when the brand has no openFDA label RXCUI (label pull covered the 14 companies' brands; partner brands match by name only).
- Trial area matching is keyword based. Oncology brands with long labels (Keytruda) match most of the company's oncology Phase 3 studies.
- Revenue at risk uses small-n curves (4 biologics); treat the biologic tail as indicative. Eliquis appears twice (BMS sales and Pfizer alliance revenue), so do not sum revenue at risk across those two rows.
