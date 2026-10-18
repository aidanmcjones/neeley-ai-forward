# Moat database census

As of 2026-10-17T21:40:06. Index file 765 MB. Page id convention: doc_id#p<page_no>, page_no = first number of the [[page N | printed M]] marker.

## Totals

| What | Count |
|---|---|
| Documents | 6,888 |
| Pages (full-text searchable) | 74,841 |
| Speaker turns (earnings calls) | 15,202 |
| Fact rows (full-text searchable) | 116,052 |
| Fact tables | 287 |
| Verified CSV files | 108 |
| Fact rows naming a drug | 44,415 (3,575 distinct drug names) |
| Licensed (Bloomberg) documents, cite only | 5 |
| Verified AI errors logged | 514 |
| Gap notes (what could not be sourced, and why) | 431 |

## Fact rows by verification status

| Status | Rows |
|---|---|
| rejected, kept for the report only | 6,211 |
| checked by a verifier | 36,099 |
| other status values | 5,245 |
| machine data (prices, I/B/E/S, CMS) | 47,754 |
| collected, not individually checked | 3,430 |
| onboarded, awaiting a verifier | 17,313 |

## Fact rows by locator (what a citation can open)

| Locator | Rows |
|---|---|
| document page (doc_id#p<page>) | 11,239 |
| dataset or API url | 44,985 |
| row key only | 59,828 |

## Documents by type

| Type | Docs |
|---|---|
| 8-K+EX99 | 2,902 |
| foreign_current_report | 919 |
| fda_label_version | 710 |
| current_report_8k | 527 |
| table | 318 |
| drug_reference_data | 209 |
| transcript | 184 |
| earnings_release | 167 |
| 10-K asset excerpt | 144 |
| quarterly_report | 133 |
| sec_comment_letter | 113 |
| annual_report | 104 |
| press_release | 71 |
| fda_label | 67 |
| earnings_slides | 34 |
| 8-K own | 32 |
| proxy_statement | 30 |
| epi_source | 26 |
| mfp_explanation | 25 |
| consensus_table | 24 |

## Documents by stream

| Stream | Docs |
|---|---|
| deals | 2,936 |
| secx | 1,196 |
| corpus | 881 |
| product | 717 |
| peers | 170 |
| pipeline | 149 |
| filings | 134 |
| onboard_VRTX | 106 |
| onboard_REGN | 97 |
| calls | 67 |
| policy | 52 |
| epi | 34 |
| onboard_NVS | 32 |
| verify_calls | 17 |
| verify_peers | 15 |
| pricing | 14 |
| onboard_drug_xtandi | 14 |
| onboard_drug_kisqali | 14 |
| verify_pipeline | 13 |
| verify_costs | 13 |
| onboard_drug_cosentyx | 12 |
| verify_rx | 11 |
| verify_epi | 11 |
| onboard_drug_xolair | 11 |
| onboard_drug_kalydeco | 11 |
| onboard_drug_dupixent | 11 |
| onboard_drug_promacta | 10 |
| onboard_drug_kesimpta | 10 |
| onboard_drug_entresto | 10 |
| onboard_drug_libtayo | 9 |

## Documents and pages by company

| Company | Docs | Pages |
|---|---|---|
| (none) | 3,214 | 21,679 |
| AZN | 518 | 3,693 |
| NVO | 410 | 3,897 |
| JNJ | 301 | 3,969 |
| MRK | 249 | 2,972 |
| ABBV | 222 | 2,394 |
| BMY | 201 | 3,300 |
| NVS | 192 | 2,749 |
| REGN | 180 | 2,844 |
| AMGN | 162 | 3,514 |
| PFE | 149 | 3,015 |
| LLY | 148 | 2,353 |
| VRTX | 138 | 2,218 |
| GILD | 136 | 2,449 |
| SNY | 129 | 2,214 |
| GSK | 103 | 1,511 |
| TAK | 89 | 2,334 |
| BBIO | 39 | 1,900 |
| ALNY | 37 | 1,513 |
| Roche | 33 | 200 |
| ROCHE | 24 | 2,981 |
| Boehringer/Lilly | 22 | 139 |
| CAH | 16 | 270 |
| MCK | 14 | 290 |
| COR | 13 | 263 |
| BOEHRINGER | 5 | 174 |
| URGN | 3 | 0 |
| SYRE | 3 | 0 |
| SMMT | 3 | 0 |
| RYTM | 3 | 0 |

## Earnings-call transcripts by company

| Company | Calls |
|---|---|
| AZN | 14 |
| AMGN | 13 |
| GILD | 12 |
| REGN | 12 |
| JNJ | 11 |
| NVO | 11 |
| NVS | 11 |
| VRTX | 11 |
| ABBV | 10 |
| BMY | 10 |
| LLY | 10 |
| MRK | 10 |
| PFE | 10 |
| GSK | 9 |
| ALNY | 8 |
| SNY | 8 |
| TAK | 8 |
| BBIO | 5 |
| ROCHE | 1 |

Transcript quotability grades: {'': 58, 'A': 30, 'B': 7, 'C': 87, 'D': 2}

## Fact rows by stream

| Stream | Rows |
|---|---|
| tables | 47,754 |
| onboard | 17,313 |
| rx | 14,864 |
| product | 7,793 |
| calls | 7,706 |
| pipeline | 7,233 |
| market | 3,015 |
| costs | 2,353 |
| peers | 2,068 |
| deals | 1,978 |
| filings | 1,276 |
| pricing | 1,132 |
| secx | 576 |
| epi | 523 |
| policy | 468 |

## Fact rows by shortlist company

| Company | Rows |
|---|---|
| AZN | 4,571 |
| PFE | 4,347 |
| LLY | 4,163 |
| JNJ | 4,115 |
| MRK | 4,087 |
| BMY | 4,076 |
| ABBV | 4,061 |
| NVO | 3,849 |
| AMGN | 3,818 |
| GILD | 3,728 |

## Fact rows by table

| Table | Rows |
|---|---|
| tables/prices_daily.csv | 39,261 |
| rx/partd_prescribers_by_state.csv | 9,071 |
| calls/qa_turns.csv | 6,556 |
| tables/ibes_revenue_consensus.csv | 5,255 |
| pipeline/pipeline_landscape.csv | 3,383 |
| product/head_to_head.csv | 2,418 |
| pipeline/pipeline_assets.csv | 2,188 |
| rx/partd_prescribers_by_specialty.csv | 1,951 |
| rx/formulary_history.csv | 1,780 |
| deals/deal_comps.csv | 1,611 |
| product/label_changes.csv | 1,602 |
| onboard/NVS/nadac_history.csv | 1,599 |
| onboard/NVS/product_revenue_quarterly.csv | 1,556 |
| product/head_to_head_pubmed.csv | 1,422 |
| product/indication_timeline.csv | 1,343 |
| market/analyst_turns_all.csv | 1,340 |
| tables/ibes_eps_consensus.csv | 1,320 |
| tables/ibes_eps_quarterly.csv | 1,309 |
| onboard/REGN/product_revenue_quarterly.csv | 1,216 |
| peers/peer_product_revenue.csv | 1,033 |
| rx/partb_providers_by_drug.csv | 965 |
| onboard/drug_entresto/nadac_history.csv | 945 |
| calls/cross_source_diffs.csv | 925 |
| pipeline/fda_calendar.csv | 921 |
| market/analyst_topics.csv | 909 |
| peers/rival_product_statements.csv | 839 |
| onboard/REGN/insider_trades.csv | 781 |
| pricing/sample_checks.csv | 645 |
| onboard/drug_cosentyx/nadac_history.csv | 620 |
| filings/restatements_triaged.csv | 616 |
| costs/trial_cost_benchmarks.csv | 607 |
| product/supplement_approvals.csv | 587 |
| costs/company_cost_structure.csv | 579 |
| onboard/REGN/nadac_history.csv | 564 |
| onboard/drug_dupixent/nadac_history.csv | 564 |
| onboard/NVS/ibes_revenue_consensus.csv | 528 |
| onboard/REGN/ibes_revenue_consensus.csv | 528 |
| onboard/VRTX/ibes_revenue_consensus.csv | 528 |
| costs/new_indication_benchmarks.csv | 520 |
| onboard/VRTX/insider_trades.csv | 505 |
| pipeline/loe_calendar.csv | 452 |
| filings/product_revenue_checks.csv | 448 |
| tables/ibes_recommendations.csv | 441 |
| onboard/VRTX/product_revenue_quarterly.csv | 431 |
| onboard/drug_kisqali/nadac_history.csv | 408 |
| market/event_returns.csv | 377 |
| secx/insider_open_market.csv | 356 |
| onboard/drug_trikafta/orange_book_patents.csv | 289 |
| pricing/gtn_proxy.csv | 283 |
| deals/duplicates.csv | 269 |
| costs/launch_and_marketing_benchmarks.csv | 265 |
| policy/policy_exposure.csv | 261 |
| rx/partd_prescribers_by_drug.csv | 229 |
| rx/prescriber_concentration.csv | 223 |
| onboard/drug_orkambi/orange_book_patents.csv | 220 |
| epi/indication_map.csv | 212 |
| pipeline/target_profiles.csv | 199 |
| onboard/drug_dupixent/medicaid_sdud.csv | 186 |
| policy/manufacturing_sites_verified.csv | 181 |
| rx/reconciliation.csv | 179 |
| onboard/drug_kalydeco/orange_book_patents.csv | 175 |
| onboard/drug_entresto/medicaid_sdud.csv | 174 |
| epi/market_sizing_inputs.csv | 173 |
| product/h2h_trials_appendix.csv | 173 |
| onboard/drug_promacta/medicaid_sdud.csv | 172 |
| tables/ibes_actuals.csv | 168 |
| rx/open_payments_by_drug.csv | 162 |
| rx/open_payments_physicians.csv | 162 |
| onboard/drug_eylea/head_to_head.csv | 161 |
| onboard/drug_xtandi/head_to_head.csv | 161 |
| onboard/drug_cosentyx/medicaid_sdud.csv | 157 |
| onboard/drug_xolair/medicaid_sdud.csv | 152 |
| onboard/drug_kisqali/head_to_head.csv | 143 |
| product/label_changes_key.csv | 142 |
| rx/open_payments_research.csv | 142 |
| costs/cost_ratios.csv | 140 |
| onboard/drug_kisqali/medicaid_sdud.csv | 135 |
| filings/doc_checks.csv | 132 |
| onboard/NVS/ibes_eps_consensus.csv | 132 |
| onboard/NVS/ibes_eps_quarterly.csv | 132 |
| onboard/REGN/ibes_eps_consensus.csv | 132 |
| onboard/REGN/ibes_eps_quarterly.csv | 132 |
| onboard/VRTX/ibes_eps_consensus.csv | 132 |
| onboard/VRTX/ibes_eps_quarterly.csv | 132 |
| onboard/drug_kesimpta/nadac_history.csv | 131 |
| onboard/drug_kalydeco/medicaid_sdud.csv | 129 |
| costs/open_payments_by_drug.csv | 120 |
| onboard/drug_orkambi/medicaid_sdud.csv | 120 |
| pricing/new_launch_prices.csv | 116 |
| calls/transcript_grades.csv | 101 |
| market/transcript_choice.csv | 101 |
| market/ibes_ids.csv | 98 |
| calls/roster_check.csv | 92 |
| onboard/drug_trikafta/medicaid_sdud.csv | 92 |
| market/never_asked.csv | 90 |
| market/priced_in_scorecard.csv | 90 |
| onboard/NVS/analyst_topics.csv | 90 |
| onboard/REGN/analyst_topics.csv | 90 |
| onboard/VRTX/analyst_topics.csv | 90 |
| pipeline/pipe_indication_to_epi.csv | 90 |
| onboard/drug_cosentyx/head_to_head_pubmed.csv | 84 |
| onboard/drug_eylea/medicaid_sdud.csv | 83 |
| costs/open_payments_by_nature.csv | 81 |
| onboard/drug_eylea/head_to_head_pubmed.csv | 75 |
| onboard/drug_xolair/head_to_head_pubmed.csv | 75 |
| deals/deal_benchmarks.csv | 74 |
| onboard/drug_kisqali/orange_book_patents.csv | 72 |
| onboard/drug_xtandi/head_to_head_pubmed.csv | 72 |
| onboard/drug_xtandi/medicaid_sdud.csv | 72 |
| peers/peer_product_revenue_xbrl_checks.csv | 72 |
| onboard/NVS/products.csv | 71 |
| onboard/drug_kalydeco/head_to_head.csv | 70 |
| secx/incentive_metrics_foreign.csv | 66 |
| onboard/drug_symdeko/orange_book_patents.csv | 65 |
| filings/discontinued_breakouts.csv | 62 |
| peers/sixk_index.csv | 61 |
| epi/medicare_market_checks.csv | 60 |
| onboard/NVS/ira_selected.csv | 57 |
| onboard/drug_dupixent/head_to_head_pubmed.csv | 57 |
| onboard/drug_kesimpta/head_to_head.csv | 57 |
| epi/indication_epidemiology.csv | 56 |
| onboard/drug_cosentyx/head_to_head.csv | 55 |
| pricing/gtn_exposure.csv | 51 |
| product/rems.csv | 51 |
| secx/incentive_metrics.csv | 51 |
| onboard/VRTX/subsidiaries.csv | 50 |
| onboard/drug_kisqali/head_to_head_pubmed.csv | 50 |
| onboard/drug_dupixent/label_versions.csv | 49 |
| onboard/drug_evkeeza/medicaid_sdud.csv | 48 |
| onboard/drug_kesimpta/head_to_head_pubmed.csv | 48 |
| onboard/drug_xtandi/orange_book_patents.csv | 47 |
| peers/transcript_labels.csv | 47 |
| onboard/drug_symdeko/medicaid_sdud.csv | 46 |
| onboard/NVS/ibes_recommendations.csv | 44 |
| onboard/REGN/ibes_recommendations.csv | 44 |
| onboard/VRTX/ibes_recommendations.csv | 44 |
| onboard/drug_promacta/head_to_head_pubmed.csv | 44 |
| onboard/drug_eylea/label_versions.csv | 38 |
| pricing/company_list_vs_net.csv | 37 |
| product/h2h_by_pair.csv | 37 |
| onboard/drug_promacta/orange_book_patents.csv | 36 |
| onboard/REGN/subsidiaries.csv | 34 |
| onboard/drug_xolair/head_to_head.csv | 34 |
| onboard/drug_entresto/ira_negotiation.csv | 33 |
| onboard/drug_kalydeco/orange_book_exclusivity.csv | 32 |
| secx/agreements_checked.csv | 32 |
| onboard/drug_cosentyx/label_versions.csv | 30 |
| onboard/drug_entresto/orange_book_patents.csv | 30 |
| onboard/drug_promacta/label_versions.csv | 30 |
| onboard/drug_kalydeco/head_to_head_pubmed.csv | 29 |
| onboard/drug_kalydeco/label_versions.csv | 28 |
| onboard/drug_kisqali/label_versions.csv | 28 |
| onboard/drug_promacta/head_to_head.csv | 28 |
| onboard/drug_xtandi/open_payments.csv | 28 |
| costs/pricing_move_benchmarks.csv | 27 |
| onboard/NVS/policy_mentions.csv | 27 |
| onboard/REGN/products.csv | 27 |
| onboard/NVS/partd_spending.csv | 26 |
| onboard/drug_dupixent/open_payments.csv | 26 |
| onboard/drug_xolair/label_versions.csv | 26 |
| secx/comment_letter_findings.csv | 26 |
| onboard/drug_entresto/label_versions.csv | 25 |
| deals/pr_checks.csv | 24 |
| onboard/drug_arcalyst/medicaid_sdud.csv | 24 |
| onboard/drug_kesimpta/medicaid_sdud.csv | 24 |
| onboard/drug_libtayo/medicaid_sdud.csv | 24 |
| onboard/drug_xtandi/label_versions.csv | 24 |
| onboard/drug_orkambi/label_versions.csv | 23 |
| epi/indication_subset_shares.csv | 22 |
| onboard/NVS/manufacturing_sites.csv | 21 |
| onboard/drug_libtayo/label_versions.csv | 21 |
| onboard/drug_trikafta/orange_book_exclusivity.csv | 21 |
| calls/cross_source.csv | 20 |
| onboard/VRTX/exec_comp_metrics.csv | 20 |
| onboard/REGN/exec_comp_metrics.csv | 19 |
| onboard/drug_dupixent/head_to_head.csv | 19 |
| filings/jnj_fiscal_quarters.csv | 18 |
| onboard/drug_trikafta/label_versions.csv | 18 |
| onboard/NVS/ibes_actuals.csv | 17 |
| onboard/REGN/ibes_actuals.csv | 17 |
| onboard/REGN/partd_spending.csv | 17 |
| onboard/VRTX/ibes_actuals.csv | 17 |
| onboard/drug_eylea/purple_book.csv | 16 |
| peers/annual_report_page_checks.csv | 16 |
| policy/ira_cut_check.csv | 16 |
| secx/insider_summary.csv | 16 |
| onboard/drug_symdeko/label_versions.csv | 15 |
| product/recalls.csv | 15 |
| costs/new_indication_timing_summary.csv | 14 |
| onboard/REGN/policy_mentions.csv | 14 |
| onboard/REGN/sec_comment_letters.csv | 14 |
| onboard/VRTX/products.csv | 13 |
| onboard/drug_libtayo/head_to_head.csv | 13 |
| calls/fix_counts.csv | 12 |
| onboard/drug_cosentyx/partd_spending.csv | 12 |
| onboard/drug_orkambi/orange_book_exclusivity.csv | 12 |
| onboard/VRTX/transcripts_index.csv | 11 |
| onboard/drug_cosentyx/policy_mentions.csv | 11 |
| onboard/drug_entresto/policy_mentions.csv | 11 |
| onboard/drug_kesimpta/label_versions.csv | 11 |
