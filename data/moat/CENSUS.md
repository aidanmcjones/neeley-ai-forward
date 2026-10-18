# Moat database census

As of 2026-10-18T00:37:36. Index file 766 MB. Page id convention: doc_id#p<page_no>, page_no = first number of the [[page N | printed M]] marker.

## Totals

| What | Count |
|---|---|
| Documents | 7,003 |
| Pages (full-text searchable) | 78,392 |
| Speaker turns (earnings calls) | 15,463 |
| Fact rows (full-text searchable) | 117,904 |
| Fact tables | 302 |
| Verified CSV files | 123 |
| Fact rows naming a drug | 45,304 (3,628 distinct drug names) |
| Licensed (Bloomberg) documents, cite only | 5 |
| Verified AI errors logged | 516 |
| Gap notes (what could not be sourced, and why) | 431 |

## Fact rows by verification status

| Status | Rows |
|---|---|
| rejected, kept for the report only | 6,211 |
| checked by a verifier | 37,655 |
| other status values | 5,521 |
| machine data (prices, I/B/E/S, CMS) | 47,754 |
| collected, not individually checked | 3,450 |
| onboarded, awaiting a verifier | 17,313 |

## Fact rows by locator (what a citation can open)

| Locator | Rows |
|---|---|
| document page (doc_id#p<page>) | 12,579 |
| dataset or API url | 45,442 |
| row key only | 59,883 |

## Documents by type

| Type | Docs |
|---|---|
| 8-K+EX99 | 2,902 |
| foreign_current_report | 919 |
| fda_label_version | 722 |
| current_report_8k | 527 |
| table | 318 |
| drug_reference_data | 209 |
| transcript | 187 |
| earnings_release | 181 |
| 10-K asset excerpt | 144 |
| quarterly_report | 137 |
| sec_comment_letter | 113 |
| annual_report | 108 |
| press_release | 105 |
| fda_label | 78 |
| earnings_slides | 34 |
| 8-K own | 32 |
| report | 31 |
| proxy_statement | 30 |
| epi_source | 26 |
| mfp_explanation | 25 |

## Documents by stream

| Stream | Docs |
|---|---|
| deals | 2,936 |
| secx | 1,196 |
| corpus | 881 |
| product | 740 |
| peers | 177 |
| pipeline | 151 |
| filings | 134 |
| onboard_VRTX | 106 |
| onboard_REGN | 97 |
| policy | 82 |
| calls | 70 |
| epi | 37 |
| onboard_NVS | 32 |
| deals_p2 | 32 |
| verify_calls | 17 |
| verify_peers | 15 |
| exhibits_p2 | 15 |
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

## Documents and pages by company

| Company | Docs | Pages |
|---|---|---|
| (none) | 3,256 | 23,506 |
| AZN | 519 | 3,696 |
| NVO | 411 | 3,902 |
| JNJ | 304 | 3,982 |
| MRK | 255 | 3,007 |
| ABBV | 224 | 2,414 |
| BMY | 205 | 3,322 |
| NVS | 197 | 2,774 |
| REGN | 183 | 2,860 |
| AMGN | 174 | 3,770 |
| PFE | 152 | 3,103 |
| LLY | 152 | 2,388 |
| VRTX | 139 | 2,224 |
| GILD | 136 | 2,449 |
| SNY | 130 | 2,220 |
| GSK | 103 | 1,511 |
| TAK | 89 | 2,334 |
| ALNY | 47 | 1,701 |
| BBIO | 41 | 1,940 |
| Roche | 33 | 200 |
| ROCHE | 24 | 2,981 |
| Boehringer/Lilly | 23 | 143 |
| CAH | 16 | 270 |
| MCK | 14 | 290 |
| COR | 13 | 263 |
| NTLA | 5 | 215 |
| HALO | 5 | 390 |
| BOEHRINGER | 5 | 174 |
| SMMT | 4 | 7 |
| URGN | 3 | 0 |

## Earnings-call transcripts by company

| Company | Calls |
|---|---|
| AMGN | 14 |
| AZN | 14 |
| GILD | 12 |
| REGN | 12 |
| ABBV | 11 |
| JNJ | 11 |
| LLY | 11 |
| NVO | 11 |
| NVS | 11 |
| VRTX | 11 |
| BMY | 10 |
| MRK | 10 |
| PFE | 10 |
| GSK | 9 |
| ALNY | 8 |
| SNY | 8 |
| TAK | 8 |
| BBIO | 5 |
| ROCHE | 1 |

Transcript quotability grades: {'': 58, 'A': 30, 'B': 21, 'C': 76, 'D': 2}

## Fact rows by stream

| Stream | Rows |
|---|---|
| tables | 47,754 |
| onboard | 17,313 |
| rx | 15,110 |
| product | 8,005 |
| calls | 7,706 |
| pipeline | 7,397 |
| market | 3,015 |
| costs | 2,353 |
| peers | 2,304 |
| deals | 2,054 |
| filings | 2,018 |
| pricing | 1,202 |
| secx | 576 |
| epi | 560 |
| policy | 537 |

## Fact rows by shortlist company

| Company | Rows |
|---|---|
| AZN | 4,666 |
| PFE | 4,439 |
| MRK | 4,184 |
| LLY | 4,164 |
| JNJ | 4,117 |
| BMY | 4,077 |
| ABBV | 4,062 |
| AMGN | 3,998 |
| NVO | 3,898 |
| GILD | 3,729 |

## Fact rows by table

| Table | Rows |
|---|---|
| tables/prices_daily.csv | 39,261 |
| rx/partd_prescribers_by_state.csv | 9,071 |
| calls/qa_turns.csv | 6,556 |
| tables/ibes_revenue_consensus.csv | 5,255 |
| pipeline/pipeline_landscape.csv | 3,383 |
| product/head_to_head.csv | 2,430 |
| pipeline/pipeline_assets.csv | 2,188 |
| rx/partd_prescribers_by_specialty.csv | 1,951 |
| rx/formulary_history.csv | 1,780 |
| deals/deal_comps.csv | 1,645 |
| product/label_changes.csv | 1,602 |
| onboard/NVS/nadac_history.csv | 1,599 |
| onboard/NVS/product_revenue_quarterly.csv | 1,556 |
| product/head_to_head_pubmed.csv | 1,422 |
| product/indication_timeline.csv | 1,343 |
| market/analyst_turns_all.csv | 1,340 |
| tables/ibes_eps_consensus.csv | 1,320 |
| tables/ibes_eps_quarterly.csv | 1,309 |
| onboard/REGN/product_revenue_quarterly.csv | 1,216 |
| peers/rival_product_statements.csv | 1,049 |
| peers/peer_product_revenue.csv | 1,033 |
| rx/partb_providers_by_drug.csv | 965 |
| onboard/drug_entresto/nadac_history.csv | 945 |
| calls/cross_source_diffs.csv | 925 |
| pipeline/fda_calendar.csv | 921 |
| market/analyst_topics.csv | 909 |
| onboard/REGN/insider_trades.csv | 781 |
| pricing/sample_checks.csv | 645 |
| onboard/drug_cosentyx/nadac_history.csv | 620 |
| filings/restatements_triaged.csv | 616 |
| pipeline/loe_calendar.csv | 616 |
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
| filings/product_revenue_checks.csv | 448 |
| tables/ibes_recommendations.csv | 441 |
| onboard/VRTX/product_revenue_quarterly.csv | 431 |
| onboard/drug_kisqali/nadac_history.csv | 408 |
| market/event_returns.csv | 377 |
| secx/insider_open_market.csv | 356 |
| filings/part2_number_anchors.csv | 325 |
| onboard/drug_trikafta/orange_book_patents.csv | 289 |
| pricing/gtn_proxy.csv | 283 |
| policy/policy_exposure.csv | 273 |
| deals/duplicates.csv | 269 |
| costs/launch_and_marketing_benchmarks.csv | 265 |
| filings/part2_fills_AMGN.csv | 235 |
| rx/partd_prescribers_by_drug.csv | 229 |
| rx/prescriber_concentration.csv | 223 |
| onboard/drug_orkambi/orange_book_patents.csv | 220 |
| epi/indication_map.csv | 212 |
| pipeline/target_profiles.csv | 199 |
| onboard/drug_dupixent/medicaid_sdud.csv | 186 |
| policy/manufacturing_sites_verified.csv | 181 |
| rx/reconciliation.csv | 179 |
| rx/cms_spend_part2.csv | 176 |
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
| filings/part2_fills_MRK.csv | 138 |
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
| product/label_claims.csv | 124 |
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
| product/head_to_head_part2.csv | 76 |
| onboard/drug_eylea/head_to_head_pubmed.csv | 75 |
| onboard/drug_xolair/head_to_head_pubmed.csv | 75 |
| deals/deal_benchmarks.csv | 74 |
| onboard/drug_kisqali/orange_book_patents.csv | 72 |
| onboard/drug_xtandi/head_to_head_pubmed.csv | 72 |
| onboard/drug_xtandi/medicaid_sdud.csv | 72 |
| peers/peer_product_revenue_xbrl_checks.csv | 72 |
| onboard/NVS/products.csv | 71 |
| onboard/drug_kalydeco/head_to_head.csv | 70 |
| pricing/vyndaqel_net_price_sources.csv | 70 |
| secx/incentive_metrics_foreign.csv | 66 |
| onboard/drug_symdeko/orange_book_patents.csv | 65 |
| filings/discontinued_breakouts.csv | 62 |
| peers/sixk_index.csv | 61 |
| epi/medicare_market_checks.csv | 60 |
| onboard/NVS/ira_selected.csv | 57 |
| onboard/drug_dupixent/head_to_head_pubmed.csv | 57 |
| onboard/drug_kesimpta/head_to_head.csv | 57 |
| epi/indication_epidemiology.csv | 56 |
| rx/formulary_part2.csv | 56 |
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
| filings/part2_q4_anchors.csv | 44 |
| onboard/NVS/ibes_recommendations.csv | 44 |
| onboard/REGN/ibes_recommendations.csv | 44 |
| onboard/VRTX/ibes_recommendations.csv | 44 |
| onboard/drug_promacta/head_to_head_pubmed.csv | 44 |
| deals/part2_comp_sets.csv | 42 |
| policy/ira_selected_drugs.csv | 41 |
| onboard/drug_eylea/label_versions.csv | 38 |
| epi/attr_cm_prevalence_sources.csv | 37 |
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
| peers/amvuttra_indication_mix.csv | 26 |
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
| policy/icer_reports.csv | 16 |
| policy/ira_cut_check.csv | 16 |
| secx/insider_summary.csv | 16 |
