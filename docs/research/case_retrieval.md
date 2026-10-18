# Case retrieval helpers

Reference for the model and UI sessions. The case's "Where findings hide" list has eight items, and each maps to one helper in `agent/moat/`: language drift to `case_risk_diff`; gross-to-net to `case_gtn`; inventory and receivables growing faster than revenue to `case_working_capital`; segment and product table changes to `case_segments`; footnotes (litigation reserves, partner royalty splits, acquisition payments, tax-rate changes) to `case_footnotes`; earnings-call Q&A (deflections, new phrases, dropped metrics) to `case_calls`; product fine print (label breadth, boxed warnings, safety programs) to `case_labels`; and peer contrast, with exposure to the three forces (IRA, MFN, tariffs), to `case_labels` side by side and `case_forces`. Every row a helper returns is cited through `agent/moat/cite.py`: a document plus printed page, or a verified table row plus its source. The helpers retrieve and sort; they do not rank or call findings. The reader judges relevance.

## Shared row contract

Every row from every helper is a dict with at least:

| Field | Meaning |
|---|---|
| `ticker` | Company ticker (or the maker ticker for label rows) |
| `kind` | Row type, named per helper below |
| `text` | Verbatim sentence or table-row text, under 600 chars |
| `citation` | Human-readable citation, e.g. "Merck 10-K FY2025, p. 29" |
| `url` | Source URL |
| `locator` / `source_id` | `doc_id#p<page_no>` for indexed pages, or the `facts` locator (`fact:<table>#<row>`) for verified table rows |
| `quote_grade` | Transcript grade A to D; empty for non-transcript documents |
| `license` | Empty, or `bloomberg_licensed` |

Table-backed rows also carry `verify_status` and `source` (the table and row they came from). Raw tables that are not verified copies carry `verify_status = unverified_raw`.

Guarantee: every sentence shown as `text` (and `prev_text`, `quote`, `question` where present) passes `cite.verify_quote(text, doc_id, page_no)` on its locator, an exact substring match on that one page after NFKC, curly-quote, dash, whitespace and case normalisation. Rows that fail are dropped. `verify_quote` has no 20-character minimum and no speaker or figure checks; for findings also run `agent.findings.verify()` or `agent.needle.pages.check()`.

Transcript grades (`quote_grade`): A and B are quotable. C needs a Bloomberg check before it goes in a findings table. D is unquotable. Ungraded transcripts (mostly peers) never pass a `grade_min` filter.

Bloomberg license rule: Bloomberg text is licensed. Rows keep `license="bloomberg_licensed"`; cite them, never copy their text into a public artifact, the app, or a slide.

## Quick reference

| Helper module | Function | Answers | Speed |
|---|---|---|---|
| `agent.moat.case_risk_diff` | `risk_diff(ticker, section="both", fy=None, prev=None, k=60, min_chars=80)` | Sentences added, dropped or reworded in risk factors and MD&A year over year | 0.2 to 0.7 s (NVO 3.7 s) |
| `agent.moat.case_gtn` | `gtn_series(ticker=None, drug=None, k=200)` | List-like vs net-like price series and filing deduction text | about 1 s |
| `agent.moat.case_working_capital` | `working_capital(ticker, quarters=12)` | Inventory, receivables, DSO, DIO against revenue growth | local XBRL cache read |
| `agent.moat.case_segments` | `segment_changes(ticker, kind=None, k=200)` | Restated or reclassified revenue, products no longer broken out | table reads plus page lookups |
| `agent.moat.case_footnotes` | `footnotes(ticker, topic="all", docs=None, k=40)` | Litigation, royalty, contingent consideration, tax-rate notes and year-over-year change | FTS queries on the index |
| `agent.moat.case_calls` | `call_qa(ticker, quarters=4, flags=(...), grade_min="C", k=80)`; `dropped_metrics(ticker, releases=6)` | Deflected questions, new phrases, never-asked topics, dropped release metrics | index reads |
| `agent.moat.case_labels` | `label_compare(drug, rivals=None, sections=(...))` | Label, REMS, exclusivity, pricing and head-to-head side by side with rivals | table and index reads |
| `agent.moat.case_forces` | `forces(ticker, force="all", k=60)` | IRA, MFN and tariff exposure from verified tables, filings and calls | FTS plus table reads |

Run every CLI as `PYTHONPATH=. python -m agent.moat.<module> ...` from the repo root. The citation index (`data/moat/index/citations.sqlite`) must be present; see `docs/research/citation_index.md`.

## Helpers

## Risk-factor and MD&A drift (agent/moat/case_risk_diff.py)

Answers: which sentences a company added, dropped or reworded in its risk factors and its MD&A between its latest annual report and the one before.

Call: `risk_diff(ticker, section="risk_factors" | "mdna" | "both", fy=None, prev=None, k=60, min_chars=80) -> list[dict]`

`fy` and `prev` take an annual_report doc_id (`"MRK:10k_FY2025.md"`) or a year (`"2025"`, `"FY2025"`). Defaults: the latest annual report period for the ticker and the one before it. `k` caps the diff rows per section (rows sorted by `salience`); one `section_stats` row per section is always added on top. `min_chars` drops shorter sentences (headings, table fragments).

### Fields

`ticker`, `kind`, `section`, `text`, `prev_text`, `citation`, `url`, `locator` / `source_id` (`doc_id#p<page_no>`), `doc_id`, `page_no`, `prev_citation`, `prev_url`, `prev_locator`, `prev_doc_id`, `prev_page_no`, `quote_grade` (""), `license`, `similarity` (changed rows, 0 to 1), `diff` (changed rows, word level `-[old] +[new]`), `salience`, `flags` (which boosts fired, plus `year_rollforward` or `coverage_mismatch`).

`kind`:
- `added`: sentence in the new report with no exact or fuzzy match in the old one. `text` and `locator` are the new doc page.
- `removed`: sentence in the old report with no match in the new one. `text` = `prev_text` = the old sentence, and `citation` / `locator` point to the old doc page (the sentence is not in the new doc).
- `changed`: fuzzy pair (character ratio 0.6 or more after a word-overlap prefilter). `text` is the new sentence on the new page, `prev_text` the old one on `prev_locator`.
- `section_stats`: `text` is the section heading as printed on its first page (verifiable); `words`, `prev_words`, `delta_words`, `pct_change`, `sentences`, `prev_sentences`, `n_added`, `n_removed`, `n_changed`, `pages`, `prev_pages` and a one-line `summary` carry the counts.

Every `text` passes `cite.verify_quote(text, doc_id, page_no)` on its locator and every `prev_text` passes it on `prev_locator`; rows that fail are dropped (0 dropped across the 10 shortlist tickers when built).

`salience`: base 1.0 added, 0.9 removed; changed rows score the changed words (plus 1.5 x (1 - similarity)) and are cut to 15% when only years changed. Boosts: non-year numbers, `%`, `$`, drug names (`case_sets.all_drugs()` plus docs.drug), and words such as material, may not, could, no longer, new, IRA, Medicare, tariff, MFN, litigation, exclusivity, generic, biosimilar, 340B, compounding (full list in `KEYWORDS`). It is a sort key, not a finding.

### Method and sources

Only the citation index (`pages` table, annual_report docs, superseded docs skipped). No network, nothing cached on disk.

1. Section location per doc. Item headings at a line start: 10-K "Item 1A. Risk Factors" to "Item 1B"/"Item 1C"/"Item 2", "Item 7. Management's Discussion" to "Item 7A"; 20-F "D. Risk Factors" to "Item 4. Information on the Company", "Item 5. Operating and Financial Review" to "Item 6. Directors". The longest start-to-next-end span wins, so table-of-contents entries are skipped. Without an item heading, a running header or footer tags the pages ("Risk Overview", "/ Risk management", "/ Key operational risks", "Financial Review", "/ Financial performance", "/ Financials").
2. 20-F companions. When either year's main section is under 3,000 words and both years have a same-period companion doc, the companion's section is appended in both years: NVO `_d2` annual report ("Risk management" and the financial pages), AZN `_ex15d1` exhibit ("Financial Review"). AZN risk factors come from the main 20-F Item 3.D (5,800 words), so the exhibit is not used for them.
3. Sentences. Paragraphs are rebuilt from the page text (table lines skipped; blank lines that are only PDF line wraps are joined), split into sentences, cut to 590 chars at a word boundary.
4. Diff. `difflib.SequenceMatcher` on normalised sentence lists; sentences that only moved are dropped; the leftover removed and added sentences are paired greedily into `changed` rows.
5. If the two sections differ in size by more than 3x, only the `section_stats` row is returned, flagged `coverage_mismatch` (a capture problem, not a disclosure change).

Runtime on the 765 MB index, `section="both"`: 0.2 to 0.7 s for the US 10-K filers, 0.6 s AZN, 3.7 s NVO (one 585k-char page).

### CLI

```
python -m agent.moat.case_risk_diff MRK --section risk_factors -k 5
[risk_factors|section_stats] risk factors: 11,176 words vs 10,745 prior (+431, +4.0%); 33 added, 18 removed, 62 changed sentences before the k cap
[risk_factors|removed] salience=5.2 Merck 10-K FY2024, p. 28 <MRK:10k_FY2024.md#p30>
    In addition, the Company expects U.S. sales of Keytruda to decline beginning in January 2028 upon implementation of government pricing under the IRA, and to further decline upon loss of market exclusivity following expiration of the U.S. compound patent in December 2028.
[risk_factors|added] salience=4.1 Merck 10-K FY2025, p. 29 <MRK:10k_FY2025.md#p31>
    The Company expects a significant decline in sales of Januvia in the first half of 2026 reflecting the impact of government price setting noted above and subsequently, ...
```

Options: `--section risk_factors|mdna|both`, `--fy`, `--prev`, `-k`, `--min-chars`. Prints a one-line reason and no rows when the ticker lacks two annual reports.

### Known gaps

- A `removed` row means "no near match in the new section", not "dropped from the filing": the sentence may have moved to another Item. Check with `cite.search_pages` before calling it a deletion.
- Reworded sentences below the 0.6 ratio show as one `removed` plus one `added` row (common in MD&A, where the year's figures are rewritten).
- NVO FY2025 `_d2` is one 585k-char page, so its rows cite "file page 1 (no printed page number)"; the pseudo pages used to find the section are split at the "Novo Nordisk Annual Report 2025 /" running headers. NVO FY2024 `_d2` has real pages.
- Tables are skipped (lines starting with `|`), but some PDF-derived pages (AZN `_ex15d1`) flatten tables into prose, so a few rows are table text.
- GSK (1-page 20-F captures) returns []; SNY FY2025 vs FY2024 returns only a `coverage_mismatch` stats row; Roche and Boehringer have no risk-factor heading in their annual reports, so only MD&A-like financial review pages are found for Roche.
- NVS 20-F risk factors locate to about 2,900 words, which may be a partial section; not checked against the filing.
- Section boundaries are heading heuristics. When a filer changes its heading style between years, word counts move without any disclosure change, so read `pages` / `prev_pages` before using `pct_change`.

## case_gtn: gross-to-net series

Answers: how a company's and its drugs' list-like prices (WAC, Part D gross, NADAC) move against net-like prices (ASP, company-reported net), plus what the filings say about sales deductions and rebates.

### Call

```python
from agent.moat.case_gtn import gtn_series
rows = gtn_series(ticker=None, drug=None, k=200)   # at least one of ticker / drug
```

`drug` is a lower-case case_sets key; `"a/b"` pairs (for example `vyndaqel/vyndamax`) match both. A key also matches its hyphenated variants (`darzalex` matches `darzalex-faspro`, `keytruda` matches `keytruda-qlex`). A ticker pulls the drugs that the pricing tables list for that company plus `case_sets.products()`. Unknown inputs return `[]`. Rows are sorted by drug, then period (company-level and filing rows have `drug == ""`). Typical call time is about 1 second.

### Fields

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

### Limits

- Raw tables (`tables/*`) are not verified copies; their `verify_status` is `unverified_raw` unless the facts table says otherwise, and their citation reads "Raw table".
- Part D and NADAC are list-like, ASP is net-like but excludes Medicaid rebates. Units differ across series (see data/moat/verified/pricing/movements.md and tables/README_pricing.md); NADAC means are simple means over NDCs, strengths may differ.
- The `k` cap keeps company-level, exposure, filing-table rows first, then proxy rows, WAC events and ASP, then NADAC and Part D support.
- The 2020 WAC rows in tables/wac_increases.csv have a shifted column layout (the amount cell holds the year); they are returned with `value=None` and `verify_status=unreliable_raw`. Logged in data/moat/verify/ai_wrong.jsonl.
- Filing excerpts are capped at 560 characters, so a long table may be cut; open the cited page for the rest.

### CLI

```
python -m agent.moat.case_gtn BMY
python -m agent.moat.case_gtn --drug keytruda
```

```
-    2025 company_list_vs_net     BMY 2025: average list price change 3.6%, average net price change -4.2% ... | Bristol Myers Squibb pricing report 2025, p. 37 | BMY:companies/BMY/pricing_report_2025.md#p37
keytruda 2024 drug_gtn_proxy      keytruda 2024; Part D gross spend per unit 1,390.73; ASP payment limit ... | Verified table pricing/gtn_proxy.csv, row keytruda|2024 | fact:pricing/gtn_proxy.csv#6
```

### Known gaps

No per-product net price from the companies themselves; no free ASP for self-administered drugs; company list-vs-net exists only for the companies in company_list_vs_net.csv; the filing hits depend on each filer's wording.

## Working capital (inventory, receivables, revenue growth)

Answers: are inventory or receivables growing faster than revenue, is DSO drifting, and what does management say about it.

Call: `agent.moat.case_working_capital.working_capital(ticker, quarters=12) -> list[dict]`
CLI: `python -m agent.moat.case_working_capital MRK [LLY ...]`

### Fields
Every row: `ticker, kind, text, citation, url, locator, source_id, quote_grade (""), license ("")`.

- `kind="quarter"` (10-Q/10-K filers) or `kind="annual"` (IFRS filers with no quarterly XBRL), newest first:
  `period_end, unit, revenue, revenue_yoy_pct, inventory, inventory_yoy_pct, receivables, receivables_yoy_pct,
  dso_days, dio_days, dso_yoy_pct, inventory_to_revenue_ttm, flags, restated_from, balance_sheet_doc,
  xbrl_sources, verify_status, source`.
- `flags` may hold: `inventory_outpaces_revenue`, `receivables_outpace_revenue` (growth above revenue growth and above zero),
  `dso_up_10pct_yoy`, `restated`.
- `restated_from`: {field: {value, accn, filed}} when an earlier filing showed a different number for the same period
  (the latest accession is the value returned).
- `kind="filing_note"`: up to 2 page hits per phrase (inventory increase, days sales outstanding, wholesaler inventory,
  channel inventory, pre-launch inventory, destocking) in the latest 10-Q, 10-K and interim report; `topic` names the phrase.
- Citation: the balance-sheet page of the matching 10-Q/10-K/20-F in the index (`doc_id#p<page>`); when no such document is
  indexed, `locator = "url:<companyfacts URL>#<concept>/<accn>"`.

### Data and limits
- Source: SEC XBRL companyfacts, read from the local `data/corpus/*/*/xbrl_companyfacts.json.gz` files (a missing ticker is
  fetched from data.sec.gov at 1 request per second). Per-concept facts are cached to
  `data/moat/tables/xbrl_working_capital.csv` (ticker, concept, period_end, period_start, fy, fp, form, accn, filed, value,
  unit, source_url), 2018 onward, for the 10 shortlist tickers plus REGN, BBIO, ALNY, NVS, TAK, SNY, GSK.
- Quarterly revenue and cost of goods are derived from cumulative durations (Q4 = FY minus 9M); the latest accession per period wins.
- DSO = receivables / period revenue x period days; DIO = inventory / cost of goods sold x period days (blank without a COGS concept).
- IFRS filers (NVO, NVS, GSK, SNY, TAK, AZN) return annual rows with yoy against the prior year; their XBRL has no
  quarterly growth. Cost of goods is mostly absent for IFRS filers, so DIO is blank. A ticker whose cached facts lack a
  revenue concept returns few or no rows.
- The cache table is read directly and is not in the citation index.

### Example
```
[quarter] MRK 2026-06-30: revenue 16,607m USD (+5.1% yoy); inventory 6,207m USD (-6.0% yoy); receivables 12,564m USD (+6.1% yoy); DSO 68.1 days; DIO 127.1 days | flags=['receivables_outpace_revenue'] | Merck 10-Q 2026-06-30, p. 4 | MRK:10q_2026Q2.md#p4
[quarter] MRK 2025-12-31: revenue 16,400m USD (+5.0% yoy); inventory 6,658m USD (+9.0% yoy); receivables 11,775m USD (+14.6% yoy); DSO 66.1 days | flags=['inventory_outpaces_revenue', 'receivables_outpace_revenue'] | Merck 10-K FY2025, p. 72 | MRK:10k_FY2025.md#p74
```

### Known gaps
- Rows need both a revenue period and a balance-sheet point; sparse early histories (BBIO) return fewer than 12 rows.
- Dollar figures come from XBRL, not parsed from the page text; the cited page is located by keyword (Inventories, receivable, Total assets).
- Tickers not in the cache return [].

## case_segments: segment and product table changes

Answers: which past revenue numbers were revised or reclassified, which products stopped being broken out, and what the filings say about recasts.

### Call

```
from agent.moat.case_segments import segment_changes
segment_changes(ticker, kind=None, k=200) -> list[dict]
```

`kind` is one of `restatement`, `discontinued_breakout`, `series_break`, `revenue_check`, `table_note` (None returns a capped mix of all). An unknown ticker returns `[]`. An invalid kind raises ValueError.

### Fields

Always: `ticker, kind, text (under 600 chars), citation, url, locator, source_id, quote_grade, license, doc_id, page_no`.
Table rows add `table, row_key, verify_status, source`. Restatements add `product, geography, period, class, pct_diff, min_value, max_value`. Discontinued breakouts add `product, period, value, unit, folded_into, citation_without` (the filing that omits the product). Series breaks add `prev_value, value, delta`.

### Sources and limits

- `data/moat/verified/filings/restatements_triaged.csv` (kind restatement; text shows first and last value by accession order and the explanation).
- `discontinued_breakouts.csv` (kind discontinued_breakout; citation points at the last filing that printed the product).
- `product_revenue_checks.csv` (kind revenue_check; series_break when two accessions print different values for the same product, geography and period, and each accession prints a single value).
- `jnj_fiscal_quarters.csv` (kind table_note, JNJ files whose quarter label is off by one).
- `table_note`: sentences from the latest 10-K and up to two later 10-Qs matching the terms reclassified, recast, revised, prior period, no longer separately, included in other, other pharmaceutical; each sentence passes `cite.verify_quote`; 10 max.
- Citations resolve to a page via the CSV citation (file path plus `pN`) against `docs.path`. When the CSV gives no page, citation is the verified table row and locator is the facts locator.
- `data/moat/tables/product_revenue_quarterly.csv` has no verified copy, and the onboard copies in the index are `unverified_onboard`, so they are not used.

### CLI example

```
python -m agent.moat.case_segments MRK --kind discontinued_breakout --k 2
[discontinued_breakout] Invanz no longer broken out after 10-K filed 2023-02-24 (0001628280-23-005061); last reported $189.0M ... | Merck 10-K FY2022, p. 125 | MRK:companies/MRK/10k_FY2022.md#p127
[discontinued_breakout] Vaqta no longer broken out after 10-K filed 2024-02-26 (0001628280-24-006850); last reported $180.0M ... | Merck 10-K FY2023, p. 124 | MRK:companies/MRK/10k_FY2023.md#p126
```

### Known gaps

- Restatements and breakouts exist for ABBV, AMGN, BMY, GILD, JNJ, LLY, MRK, PFE only; other tickers get table notes only.
- Series breaks come from the revenue-check table, which holds one value per accession for most products, so few rows appear.
- Table notes are keyword matches and include routine accounting reclassifications (hedges, AOCI); the reader must judge relevance.

## Footnote extracts (agent/moat/case_footnotes.py)

Answers: what the notes of the two latest annual reports and the latest 10-Q (or interim report) say about litigation reserves, partner royalty splits, contingent consideration and tax-rate changes, and what changed year over year.

Call: `footnotes(ticker, topic="all" | "litigation" | "royalty" | "contingent_consideration" | "tax_rate", docs=None, k=40) -> list[dict]`

`k` is split evenly across topics for "all"; for a single topic it is the cap. `docs` overrides the doc_id list (no year comparison then).

### Fields

`ticker`, `kind`, `text` (1 to 3 sentences, under 600 chars, verbatim from the page), `numbers` (dollar amounts and percentages found in `text`), `doc_year`, `topic`, `citation`, `url`, `locator` / `source_id` (`doc_id#p<page_no>`), `quote_grade` (""), `license` (""), `doc_id`, `page_no`, `new_vs_prev`, `also_in_prev_year`, `prev_numbers` (numbers from the matching prior-year sentence, so a changed figure is visible).

`kind`:
- `footnote`: sentence in the latest annual report. `new_vs_prev=True` when no near match exists in the prior-year report; `also_in_prev_year=True` when one does.
- `latest_10q`: sentence in the latest quarterly or interim report with no near match in the latest annual report.
- `dropped_from_latest`: prior-year annual sentence with no near match in the latest annual report.

Every `text` passes `cite.verify_quote(text, doc_id, page_no)`.

### Method and sources

Per topic a list of FTS5 queries (see `TOPICS` in the module) runs against `pages_fts`, restricted to annual_report docs of the latest two fiscal years (by `period` year; all docs of that year, so 20-F exhibits and NVO `_d2` files are included) plus the newest quarterly_report or interim_report. Hit pages are split into sentences; a window of up to 3 sentences that contains every quoted term of the query is kept. Near-duplicates are merged by digit-masked token overlap (Jaccard 0.85 within a period, 0.6 across periods, so a sentence whose figure changed counts as "also in prev year" with differing `numbers` / `prev_numbers`).

Text only. No XBRL or companyfacts numbers are pulled; use the table helpers for reported values.

### CLI

```
python -m agent.moat.case_footnotes JNJ litigation -k 8
[litigation|footnote] Johnson & Johnson 10-K FY2025, p. 110 <JNJ:10k_FY2025.md#p115> new_vs_prev=True also_in_prev_year=False
    As of December 28, 2025, the total present value of the reserve to resolve the talc claims is approximately $3.4 billion, ...
[litigation|dropped_from_latest] Johnson & Johnson 10-K FY2024, p. 109 <JNJ:10k_FY2024.md#p114> new_vs_prev=False also_in_prev_year=False
```

### Known gaps

- Table rows (lines starting with `|`) are skipped, so figures that live only in tables are missed; numbers inside prose are returned.
- Query lists are generic and not tuned per company. Partner names are not hard-coded, so royalty recall depends on the filing wording ("royalt*" near collaboration, license, sales, partner, alliance).
- NVO interim reports are one page each, so the 600 char window is the only locator inside them.
- Several queries (e.g. "accrual" NEAR "lawsuit") return nothing for some issuers; an empty topic means no sentence matched, not that the topic is absent.
- Fiscal-year labelling uses the doc `period` year, which can be off by one for 52/53-week filers in older years (not an issue for the two latest years).

## Earnings calls: Q&A deflection, new phrases, dropped metrics

Module: `agent/moat/case_calls.py`

**What it answers:** which analyst questions management avoided, which phrases appear for the first time in the latest call, which topics analysts stopped asking about, and which product lines or metrics a company stopped printing in its earnings materials.

### Call signatures

```python
from agent.moat.case_calls import call_qa, dropped_metrics

call_qa(ticker, quarters=4, flags=("deflection", "new_phrase", "never_asked"), grade_min="C", k=80) -> list[dict]
dropped_metrics(ticker, releases=6) -> list[dict]
```

`call_qa` returns `qa_pair` rows (sorted by `deflection_score`, highest first, at most `k`), up to 25 `new_phrase` rows for the latest call, and every `never_asked` row for the ticker. `dropped_metrics` returns `dropped_metric` rows. An unknown ticker returns `[]` from both.

### Fields

Every row: `ticker`, `kind`, `text` (verified sentence or table-row text, under 600 chars), `citation`, `url`, `locator`, `source_id`, `quote_grade`, `license`.

- `qa_pair`: `quarter`, `analyst`, `analyst_firm`, `speaker`, `firm`, `question`, `question_verified`, `question_locator`, `answer` (same as `text`), `answer_words`, `question_words`, `deflection_score` (0 to 1), `deflection_reasons` (list), `quotable` (grade A or B), `doc_id`, `page_no`, `role_source` (`qa_turns.csv` or `turns (heuristic role)`).
- `new_phrase`: `quarter`, `phrase`, `phrase_kind` (`capitalised` or `ngram`), `mentions`, `compared_against` (prior three call doc_ids), `quotable`, `doc_id`, `page_no`. `text` is the first sentence in the latest call that uses the phrase.
- `never_asked`: `topic`, `quarters_asked`, `quarters_covered`, `recent_unasked_streak`, `flag`, `quarter` (last asked), `verify_status`, `source`. Cited to the `facts.locator` of `market/never_asked.csv`.
- `dropped_metric`: `series` (`earnings_release`, `earnings_slides` or `10-Q product sales`), `metric_kind` (`label` or `key_metric`), `label`, `last_seen`, `times_seen`, `releases_compared`, `missing_from`, `checked_against` (first doc_id of the latest release), `checked_against_all`. Cited to the last release page where the label appears.

### How it works

- One transcript per quarter: grade A, then B, then C (D only with `grade_min="D"`), superseded docs skipped. Ties prefer the doc covered by `qa_turns.csv`. Bloomberg docs are used and keep `license="bloomberg_licensed"`: cite, never copy their text into a public artifact.
- Turns come from `data/moat/verified/calls/qa_turns.csv` (analyst vs executive labels) when it covers the chosen doc, else from the index `turns` table with heuristic roles (known names from `qa_turns.csv`, firm words, a trailing question mark).
- Each analyst question is paired with the executive turns that follow it. Deflection score adds: quantitative question (number, guidance, how much, timing, when) with no number in the answer (0.35); deflection phrases such as "not going to comment", "we don't guide", "stay tuned", "too early" (0.2 each, up to 0.4); answer under 60% of the question's length (0.15); under 15% overlap with the question's content words (0.2).
- The answer sentence shown is the run of sentences that verifies on one page with `cite.verify_quote`, starting at the deflection phrase when there is one.
- New phrases: capitalised phrases and repeated content bigrams or trigrams from the latest call (analyst questions removed, speaker and firm names, months and stop words excluded) that appear in none of the prior three calls.
- Dropped metrics: each series is compared only with itself. Labels come from lines followed by a figure, markdown table rows, and "<Name> Sales Were $X" lines; key-metric words (gross-to-net, NBRx, TRx, market share, patients on therapy, ex-U.S., constant currency, and similar) are checked by presence. A label is reported only if it appears in at least 2 earlier releases, is absent from the latest two as a parsed line, and its text (minus a trailing geography) appears nowhere in the latest two releases. A series is skipped when the latest releases parse to under half the earlier median label count (a format change, not a drop).

### Data sources and limits

- Citation index `docs`, `pages`, `turns`, `facts` (read only). 167 `earnings_release` docs cover 14 tickers; `earnings_slides` cover 12; 10-Qs cover US filers only.
- Grade C transcripts are single third-party sources: speaker names and drug names can be misspelled, which shows up as false new phrases. Check `quote_grade` before quoting.
- Some corpus transcripts are a single file page, so `citation` reads "file page 1 (no printed page number)".

### CLI example

```
PYTHONPATH=. python -m agent.moat.case_calls MRK -k 2
[qa_pair] 2025Q3 grade=A score=0.95 Courtney Breen -> Rob Davis  <MRK:transcripts/2025Q3_transcript.md#p14>
[new_phrase] 2026Q2 grade=A phrase='LIPFENDRA' x13  <MRK:transcripts/2026Q2_transcript.md#p3>
[never_asked] 2025Q2 grade=- topic=IRA_negotiation streak=4  <fact:market/never_asked.csv#65>

PYTHONPATH=. python -m agent.moat.case_calls MRK --dropped
[earnings_release/label] 'Pifeltro' last seen 2026-02-03 (x3), missing from ['2026-04-30', '2026-08-04']  <MRK:earnings/2026-02-03_tm264564d1_ex99-1.md#p1>
```

### Known gaps

- Deflection and new-phrase flags are heuristics. Read the cited page before calling an answer evasive.
- Heuristic roles (docs without `qa_turns.csv` coverage, such as Bloomberg PDFs) can mispair a question with a closing remark.
- Dropped labels include one-off line items (charges, guidance rows) and labels printed only in fourth-quarter releases (full-year tables), as well as true product or metric drops. A label renamed in the latest releases is filtered only when the old name survives as a substring.
- 10-Q sales pages are found by keyword and label count, so a 10-Q whose product table layout changes may be skipped.

## case_labels: side-by-side label sections

What it answers: how a product's FDA label, REMS, label changes, exclusivity dates, price series and head-to-head trials line up against the rivals the case lists for it.

Call: `agent.moat.case_labels.label_compare(drug, rivals=None, sections=("indications","boxed_warning","contraindications","warnings","rems","dosing","exclusivity","pricing"))`

`drug` is a case key (keytruda, skyrizi, vyndaqel). `rivals` defaults to the rivals in `agent/moat/case_sets.py` for that product (every shortlist company's sets are searched); a list of keys overrides it. Unknown drug returns `[]`.

### Fields returned

Every row: `ticker, kind, drug, maker, section, text (<=600 chars), citation, url, locator, source_id, quote_grade, license`.

- `kind="label_section"`: `heading, full_text_chars, label_effective, label_doc_type, has_boxed_warning, pages_in_section`; plus `n_indications` (indications), `boxed_warning_terms` (boxed_warning), `dosing_summary` (list of route and frequency phrases, dosing). `text` starts at the section's first page, so its first 200 characters verify with `cite.verify_quote(text[:200], doc_id, page_no)` on the locator page.
- `kind="rems"`: `rems_active, elements`, from `product/rems.csv`.
- `kind="label_change"`: latest 5 per drug from `product/label_changes_key.csv` (falls back to `label_changes.csv`); `effective_date, version, materiality`.
- `kind="exclusivity"`: one row per territory from `pipeline/loe_calendar.csv` with `orange_book_last_patent, exclusivity_latest_date, purple_book_ref_exclusivity, company_stated_loe, first_generic_or_biosimilar`; the locator is the 10-K page when the table row names one.
- `kind="pricing"`: `pricing/gtn_exposure.csv` (list-like and net-like series, IRA fields) and the latest year of `pricing/gtn_proxy.csv`.
- `kind="head_to_head"`: `product/h2h_by_pair.csv` pair verdicts and direct trials from `product/head_to_head.csv` for (drug, rival) pairs, matched through the ingredient names in `rems.csv`; extra fields `rival, pair`.
- `kind="matrix"`: one row per section, `matrix = {drug: one-line summary}`, `citation` and `locator` joined with " ; ".
- Table rows also carry `verify_status, source, source_row, table, row_key`; `locator` is the facts locator.

### Data sources and limits

- Labels: latest `fda_label_version` doc per drug (dated, four sections plus boxed warning), unless its date is before 2025-01-01, in which case the current full `fda_label` doc is used (`STALE_BEFORE` in the module). Drugs with no version doc use the full label, which is split into subsections, so `full_text_chars` and `text` cover the first subsection page only for some drugs; `n_indications` counts numbered sub-headings.
- `label_effective` is empty for full-label docs (no date in the index).
- `dosing_summary` is regex phrase matching over the first 2,500 characters of the dosing section; it is a pointer, not a regimen.
- `has_boxed_warning` is false when no boxed-warning page exists in the chosen doc.
- `h2h_by_pair.csv` has no `verify_status` column, so those rows carry an empty one.

### CLI example

```
python -m agent.moat.case_labels vyndaqel --section indications dosing
[label_section] vyndaqel indications :: ## 1. INDICATIONS AND USAGE VYNDAQEL and VYNDAMAX are indicated for the treatment of the cardiomyopathy ...
    Vyndaqel label, section 1. INDICATIONS AND USAGE <drug:vyndaqel:label_sections.md#p1>
[label_section] vyndaqel dosing :: ### 2.1 Recommended Dosage The recommended dosage is either VYNDAQEL 80 mg ... orally once daily ...
    Vyndaqel label, section 2.1 Recommended Dosage <drug:vyndaqel:label_sections.md#p2>
```

### Known gaps

- Generic placeholders in the case sets (sitagliptin, dapagliflozin) have no label docs and return no label rows.
- Exclusivity and pricing rows exist only for brands in `loe_calendar.csv` and the pricing tables; others show "no data in the index" in the matrix.
- Rival products whose label is only in the full `fda_label` doc give subsection-level pages, not whole-section text.

## case_forces: IRA, MFN and tariff exposure per company

Answers: what the verified policy tables and the company's own filings and calls say about IRA Medicare negotiation, the MFN deal and tariff exposure.

Call: `forces(ticker, force="all" | "ira" | "mfn" | "tariff", k=60) -> list[dict]` in `agent/moat/case_forces.py`. An unknown ticker returns `[]`. After the first `k` rows, one `peer_matrix` row is always appended.

### Fields

Every row: `ticker, kind, force, item, value, unit, effective_date, text, citation, url, locator, source_id, verify_status, source, quote_grade, license`.

- `kind`: summary, exposure_item, ira_drug, mfn_term, tariff_item, manufacturing_site, filing_statement, call_statement, peer_matrix.
- Table rows: `locator` is the facts locator (doc page of the underlying source when indexed, else `fact:<table>#<row>`); `verify_status` and `source` come from the table.
- Statement rows: sentence found on an indexed page, checked with `verify_quote`; `locator` is `doc_id#p<page>`; transcripts carry `quote_grade` (A or B only).
- Extra fields: ira_drug rows from ira_cut_check carry `mfp_usd, list_usd, recomputed_pct`; manufacturing_site rows (one per country) carry `country, in_us`; summary rows carry `fields` and `traceable_row_ids`.
- peer_matrix: `value` = {ticker: {ira_share_of_total_revenue_pct, mfn_date, us_investment_pledge_usd_bn, tariff_exempt_until}} for the 10 shortlist tickers; `locators` is the parallel dict of facts locators.

### Sources and limits

- data/moat/verified/policy/: force_summary.csv, policy_exposure.csv (dropped rows skipped), ira_cut_check.csv, manufacturing_sites_verified.csv, definitions.md.
- Filing and call sentences: two latest annual reports (duplicate `_d2` copies skipped), latest 10-Q or interim, last four transcripts graded A or B, found through FTS on ten terms (Inflation Reduction Act, maximum fair price, negotiated price, Most Favored Nation, MFN, tariff, Section 232, manufacturing investment, TrumpRx, direct-to-consumer), at most 3 sentences per document.
- Manufacturing counts are FDA CDER registrations only (a floor; CBER sites under-covered). Revenue bases and pledge horizons differ by company; read definitions.md before comparing.
- Sentence splitting is regex based; a sentence cut mid-abbreviation can be short.
- The press release, gov, CMS fact sheet and 8-K documents are reached through the policy_exposure rows (which cite them), not searched separately.

### CLI

```
python -m agent.moat.case_forces NVO ira
[ira_drug/ira] IRA Ozempic/Rybelsus/Wegovy (IPAY 2027): % cut of MFP vs list = 71 | $274 $959 71% | CMS fact sheet, p. 2 | policy_gov:policy_gov/cms/cms_fact_sheet_negotiated_prices_ipay2027.md#p2
[filing_statement/ira] negotiated price = | The negotiated price for the products in Medicare Part D will go into effect in 2027. | Novo Nordisk 20-F FY2025, p. 7 | NVO:20f_FY2025.md#p8
```

### Known gaps

- Statement search is page-level FTS, so recall depends on FTS ranking (top 12 pages per document).
- Press release and 8-K documents are not independently searched for tickers lacking policy_exposure rows.
- The tariff force also returns manufacturing-footprint rows because they bear on tariff exposure.

## case_sets.py, case_sources.py and CASE_SOURCES.md

`agent/moat/case_sets.py` is the case appendix as data (source: `docs/case/fine_print_case.pdf`, "Appendix: Company Shortlist & Competitive Sets"). It holds `SHORTLIST` (MRK, BMY, PFE, LLY, NVO, ABBV, JNJ, AZN, AMGN, GILD), `COMPANY_NAMES`, `FOREIGN_FILERS`, `STARTER_THREADS` (one case-provided thread per company), `COMPETITIVE_SETS` ({ticker: {product_key: [(rival_key, maker_ticker, note)]}}; a key like `skyrizi/rinvoq` is one set shared by both drugs) and `BACKGROUND_ONLY` (MariTide). Functions: `products(ticker)`, `rivals(ticker, product=None)`, `all_drugs()`, `maker_tickers()`. Drug keys are lower case and hyphenated like the index `drug` column; Boehringer is `BOEHRINGER`, Roche is `ROCHE`, ViiV is reported under `GSK`, generic placeholders use maker `GENERIC`.

`agent/moat/case_sources.py` checks the moat database against the case's "Source material" list for the 10 shortlist companies and writes `data/moat/CASE_SOURCES.md`, a table with one row per company and seven columns: annual reports, last four calls (with grade), latest 10-Q or interim, rival filings and statements (gaps marked GAP), FDA labels with openFDA currency, Orange/Purple Book and FDA calendar, and the 10-K patent table. `build(fda=True)` returns `(markdown, gaps, rows)`. Regenerate from the repo root:

```
PYTHONPATH=. python -m agent.moat.case_sources            # with the openFDA currency check (network)
PYTHONPATH=. python -m agent.moat.case_sources --no-fda   # skip openFDA
```

It prints the markdown and also writes the gap list to the `GAPS_JSON` path set in the module. The committed file was generated 2026-10-17 with openFDA on.

## Tests

```
PYTHONPATH=. python -m pytest tests/moat -q
```
