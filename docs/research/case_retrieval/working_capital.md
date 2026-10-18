# Working capital (inventory, receivables, revenue growth)

Answers: are inventory or receivables growing faster than revenue, is DSO drifting, and what does management say about it.

Call: `agent.moat.case_working_capital.working_capital(ticker, quarters=12) -> list[dict]`
CLI: `python -m agent.moat.case_working_capital MRK [LLY ...]`

## Fields
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

## Data and limits
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

## Example
```
[quarter] MRK 2026-06-30: revenue 16,607m USD (+5.1% yoy); inventory 6,207m USD (-6.0% yoy); receivables 12,564m USD (+6.1% yoy); DSO 68.1 days; DIO 127.1 days | flags=['receivables_outpace_revenue'] | Merck 10-Q 2026-06-30, p. 4 | MRK:10q_2026Q2.md#p4
[quarter] MRK 2025-12-31: revenue 16,400m USD (+5.0% yoy); inventory 6,658m USD (+9.0% yoy); receivables 11,775m USD (+14.6% yoy); DSO 66.1 days | flags=['inventory_outpaces_revenue', 'receivables_outpace_revenue'] | Merck 10-K FY2025, p. 72 | MRK:10k_FY2025.md#p74
```

## Known gaps
- Rows need both a revenue period and a balance-sheet point; sparse early histories (BBIO) return fewer than 12 rows.
- Dollar figures come from XBRL, not parsed from the page text; the cited page is located by keyword (Inventories, receivable, Total assets).
- Tickers not in the cache return [].
