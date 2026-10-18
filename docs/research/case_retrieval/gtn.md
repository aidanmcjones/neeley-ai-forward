# case_gtn: gross-to-net series

Answers: how a company's and its drugs' list-like prices (WAC, Part D gross, NADAC) move against net-like prices (ASP, company-reported net), plus what the filings say about sales deductions and rebates.

## Call

```python
from agent.moat.case_gtn import gtn_series
rows = gtn_series(ticker=None, drug=None, k=200)   # at least one of ticker / drug
```

`drug` is a lower-case case_sets key; `"a/b"` pairs (for example `vyndaqel/vyndamax`) match both. A key also matches its hyphenated variants (`darzalex` matches `darzalex-faspro`, `keytruda` matches `keytruda-qlex`). A ticker pulls the drugs that the pricing tables list for that company plus `case_sets.products()`. Unknown inputs return `[]`. Rows are sorted by drug, then period (company-level and filing rows have `drug == ""`). Typical call time is about 1 second.

## Fields

Every row: `ticker`, `kind`, `drug`, `period`, `year`, `text` (under 600 chars), `value`, `unit`, `verify_status`, `source`, `source_row`, `citation`, `url`, `locator`, `source_id`, `quote_grade`, `license`, `table`. Extra fields per kind (list/net change, ratios, IRA MFP, NDC counts, `quote` for filing rows).

| kind | Source | Notes |
|---|---|---|
| company_list_vs_net | verified/pricing/company_list_vs_net.csv | company-estimated average list vs net price change per year; `locator` is the report page |
| drug_gtn_exposure | verified/pricing/gtn_exposure.csv | one row per drug: list-like vs net-like change, WAC events, IRA MFP |
| drug_gtn_proxy | verified/pricing/gtn_proxy.csv | per drug-year: Part D spend per unit, ASP, NADAC, ratios, MFP |
| wac_event | tables/wac_increases.csv | CA HCAI WAC increases, collapsed across NDCs with the same date and amount |
| nadac | tables/nadac_history.csv | latest weekly as-of date in each year (each quarter for a drug-only call), simple mean over NDCs |
| partd_support | tables/partd_by_year.csv | Part D gross per unit, overall manufacturer rows, year grain |
| partb_asp | tables/partb_asp_quarterly.csv | Q4 of each year plus the newest quarter per HCPCS code |
| filing_sales_deduction_table | search_pages on 10-K, 10-Q, interim reports | page excerpt with a deduction or rebate table; `quote` passes `verify_quote` |
| filing_statement | search_pages on filings and transcripts (grade B or better) | sentence-level excerpt around the matched phrase |

`locator` is the `facts.locator` when the row is indexed, else `fact:<table>#<row_key>`. Filing rows use `doc_id#p<page_no>`.

## Limits

- Raw tables (`tables/*`) are not verified copies; their `verify_status` is `unverified_raw` unless the facts table says otherwise, and their citation reads "Raw table".
- Part D and NADAC are list-like, ASP is net-like but excludes Medicaid rebates. Units differ across series (see data/moat/verified/pricing/movements.md and tables/README_pricing.md); NADAC means are simple means over NDCs, strengths may differ.
- The `k` cap keeps company-level, exposure, filing-table rows first, then proxy rows, WAC events and ASP, then NADAC and Part D support.
- The 2020 WAC rows in tables/wac_increases.csv have a shifted column layout (the amount cell holds the year); they are returned with `value=None` and `verify_status=unreliable_raw`. Logged in data/moat/verify/ai_wrong.jsonl.
- Filing excerpts are capped at 560 characters, so a long table may be cut; open the cited page for the rest.

## CLI

```
python -m agent.moat.case_gtn BMY
python -m agent.moat.case_gtn --drug keytruda
```

```
-    2025 company_list_vs_net     BMY 2025: average list price change 3.6%, average net price change -4.2% ... | Bristol Myers Squibb pricing report 2025, p. 37 | BMY:companies/BMY/pricing_report_2025.md#p37
keytruda 2024 drug_gtn_proxy      keytruda 2024; Part D gross spend per unit 1,390.73; ASP payment limit ... | Verified table pricing/gtn_proxy.csv, row keytruda|2024 | fact:pricing/gtn_proxy.csv#6
```

## Known gaps

No per-product net price from the companies themselves; no free ASP for self-administered drugs; company list-vs-net exists only for the companies in company_list_vs_net.csv; the filing hits depend on each filer's wording.
