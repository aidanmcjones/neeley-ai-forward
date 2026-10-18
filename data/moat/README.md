# Moat dataset: comprehensive, verified, cited data for the 10 shortlist companies

Built Sat Oct 17, 2026 on top of Parker's `data/corpus` (836 documents). Every document is page-marked
(`[[page N | printed M]]`), every table row carries `source` and `source_row`, and every stream was collected by a
Sonnet agent and then re-verified by an Opus agent against the primary source. Bulk files live in R2 bucket
`neeley-ai-forward` under `moat/`; only this README, GAPS.md and the manifests are in git.

| Stream | What | Verified outputs (use these) |
|---|---|---|
| filings | 10-K/20-F FY2021 to FY2023, 10-Qs 2023 to 2025, AZN/NVO results 6-Ks, quarterly product revenue panel | `verified/filings/`: restatements_triaged, discontinued_breakouts (51 products quietly folded into Other), product_revenue_checks, jnj_fiscal_quarters |
| calls | 10 quarters of transcripts per company, Q&A turns, 5 official Bloomberg PDFs | `verified/calls/`: transcript_grades (A/B quotable), qa_turns, cross_source diffs |
| policy | IRA, MFN, tariff, manufacturing exposure; 47 government documents | `verified/policy/`: force_summary, policy_exposure (261 quoted rows), definitions.md, manufacturing_sites_verified |
| pricing | Part B ASP, NADAC, Medicaid SDUD, Part D, California WAC, company list vs net | `verified/pricing/`: gtn_exposure (per appendix drug), gtn_proxy, movements.md, company_list_vs_net |
| product | label version history, head-to-head trials, supplements, recalls, REMS | `verified/product/`: h2h_by_pair (37 pairs), label_changes_key, label_changes, supplement_approvals |
| market | daily prices, event returns, analyst topic counts, GDELT, I/B/E/S from WRDS | `verified/market/`: priced_in_scorecard, analyst_topics, consensus_vs_guidance, never_asked |
| secx | SEC comment letters, proxies, 8-Ks, agreements, insider trades, subsidiaries | `verified/secx/`: comment_letter_findings (9 candidates), incentive_metrics, insider_summary, agreement_terms |
| epi | drug x indication label map, US prevalence for all 50 indications (CDC, SEER, NIDDK, AHA, primary papers), subset shares, Part D 2024 market floors, sizing funnels | `verified/epi/`: indication_map (212 rows), indication_epidemiology (56 rows, confidence column), indication_subset_shares (22), medicare_market_checks, market_sizing_inputs (173 funnels, subset_caveat, partb_flag) |
| peers | rival makers (NVS, GSK, SNY, TAK, REGN, ALNY, BBIO, Roche): 3 annual reports, quarterlies, 6 calls each | `verified/peers/`: rival_product_statements (833 verbatim, topic_fixed), peer_product_revenue (NVS top 20, rebuilt), peer_product_revenue_xbrl_checks, transcript_labels |
| deals | 1,611 biopharma deals 2020 to 2026 from 2,934 8-Ks and 10-K notes | `verified/deals/`: deal_comps (use verify_status verified or corrected only; unchecked rows are leads), deal_benchmarks (74 cells from verified rows, `thin` when n 5 to 9), duplicates, pr_checks (n=4, do not use) |
| pipeline | Phase 2/3 landscape, assets, target profiles, FDA and LOE calendars | `verified/pipeline/`: pipeline_landscape (use primary_indication_epi, stale_registry_date), pipeline_assets (2,188; marketed_comparator flag), target_profiles (199, all priced; cash, debt, EV from one balance-sheet date; negative_ev flag; royalty liabilities in debt_like_royalty_not_in_ev), loe_calendar (stated date + tenk_page, rule_method), fda_calendar (licensure_date, exposure_not_sponsor), pipe_indication_to_epi |
| peers (wave 3) | 6-K results releases for SNY, TAK, GSK, NVS; BBIO and NVS calls; Boehringer annual reports | `verified/peers/peer_product_revenue.csv` now 1,033 rows (NVS, GSK, SNY, TAK; currency and period_scope columns; TAK Q2 to Q4 are cumulative), sixk_index, rival_product_statements (839) |
| costs | cost structure, cost ratios, trial cost per phase, pricing moves, launch and marketing, Open Payments | `verified/costs/`: company_cost_structure (row_holds says restated vs original), cost_ratios (scope column), pricing_move_benchmarks (effect_type, disclosed_effect), trial_cost_benchmarks (cost_year, confidence), launch_and_marketing_benchmarks, open_payments_by_drug and _by_nature (use the promotional share only). new_indication_benchmarks: 82% of checked matches were wrong, do not use its timing columns |
| rx | Part D prescribers by drug, specialty, state 2019 to 2024; concentration; Open Payments 2021 to 2024; Part B providers; formulary history | `verified/rx/`: partd_prescribers_by_drug (use prescribers_all_cms and true_beneficiaries, the 11-claim floor hides most specialty prescribers), partd_prescribers_by_specialty, partd_prescribers_by_state, prescriber_concentration (use the _all_prescribers columns for launches), open_payments_by_drug (usd_promotional vs usd_royalty_license_ownership), open_payments_research, partb_providers_by_drug (16 HCPCS), formulary_history (contract_year, part_b_drug), reconciliation |
| onboard | `python -m agent.moat.onboard_company <TICKER>` and `onboard_drug "<BRAND>"` build all of the above for any new company or drug, then `index.py --add` | `onboard/<KEY>/*.csv`, flagged `unverified_onboard` until a verifier runs; docs/research/onboarding.md |

## Citation index

`data/moat/index/citations.sqlite` (R2 `moat/index/citations.sqlite.gz`): 6,649 docs, 71,706 pages, 106,230 facts,
FTS5 search, transcript grades, `verify_quote`. API in `agent/moat/cite.py`; docs in `docs/research/citation_index.md`.
Facts carry `verify_status`: use `verified`/`corrected`/`fixed`/`yes`/`True`; `unverified_onboard` means an onboarded
table no verifier has checked; `no_verified_copy` is machine data (prices, I/B/E/S). `*_dropped.csv` files are never indexed.
New material is registered with `python -m agent.moat.index --add` (ids stable, idempotent).

```
python -m agent.moat.cite "Genmab royalty" --ticker JNJ --doc-type annual_report
```

## Trust rules

- Quote transcripts only from grade A or B (see `verified/calls/transcript_grades.csv`), or after a check against the Bloomberg copy.
- Bloomberg exports (`data/corpus/_inbox/bloomberg/`, R2 `bloomberg/`) are licensed: cite, never redistribute.
- `data/moat/verify/ai_wrong.jsonl` logs every error the verifiers found (486 entries across 13 streams): the "AI was confidently wrong" material for the report.
- Rebuild the coverage tracker with `python -m agent.moat.progress && python -m agent.moat.progress_page`.
