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

## Citation index

`data/moat/index/citations.sqlite` (R2 `moat/index/citations.sqlite.gz`): 3,118 docs, 39,940 pages, 69,553 facts,
FTS5 search, transcript grades, `verify_quote`. API in `agent/moat/cite.py`; docs in `docs/research/citation_index.md`.

```
python -m agent.moat.cite "Genmab royalty" --ticker JNJ --doc-type annual_report
```

## Trust rules

- Quote transcripts only from grade A or B (see `verified/calls/transcript_grades.csv`), or after a check against the Bloomberg copy.
- Bloomberg exports (`data/corpus/_inbox/bloomberg/`, R2 `bloomberg/`) are licensed: cite, never redistribute.
- `data/moat/verify/ai_wrong.jsonl` logs every error type the verifiers found (61 entries): the "AI was confidently wrong" material for the report.
- Rebuild the coverage tracker with `python -m agent.moat.progress && python -m agent.moat.progress_page`.
