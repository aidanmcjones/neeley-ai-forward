# case_segments: segment and product table changes

Answers: which past revenue numbers were revised or reclassified, which products stopped being broken out, and what the filings say about recasts.

## Call

```
from agent.moat.case_segments import segment_changes
segment_changes(ticker, kind=None, k=200) -> list[dict]
```

`kind` is one of `restatement`, `discontinued_breakout`, `series_break`, `revenue_check`, `table_note` (None returns a capped mix of all). An unknown ticker returns `[]`. An invalid kind raises ValueError.

## Fields

Always: `ticker, kind, text (under 600 chars), citation, url, locator, source_id, quote_grade, license, doc_id, page_no`.
Table rows add `table, row_key, verify_status, source`. Restatements add `product, geography, period, class, pct_diff, min_value, max_value`. Discontinued breakouts add `product, period, value, unit, folded_into, citation_without` (the filing that omits the product). Series breaks add `prev_value, value, delta`.

## Sources and limits

- `data/moat/verified/filings/restatements_triaged.csv` (kind restatement; text shows first and last value by accession order and the explanation).
- `discontinued_breakouts.csv` (kind discontinued_breakout; citation points at the last filing that printed the product).
- `product_revenue_checks.csv` (kind revenue_check; series_break when two accessions print different values for the same product, geography and period, and each accession prints a single value).
- `jnj_fiscal_quarters.csv` (kind table_note, JNJ files whose quarter label is off by one).
- `table_note`: sentences from the latest 10-K and up to two later 10-Qs matching the terms reclassified, recast, revised, prior period, no longer separately, included in other, other pharmaceutical; each sentence passes `cite.verify_quote`; 10 max.
- Citations resolve to a page via the CSV citation (file path plus `pN`) against `docs.path`. When the CSV gives no page, citation is the verified table row and locator is the facts locator.
- `data/moat/tables/product_revenue_quarterly.csv` has no verified copy, and the onboard copies in the index are `unverified_onboard`, so they are not used.

## CLI example

```
python -m agent.moat.case_segments MRK --kind discontinued_breakout --k 2
[discontinued_breakout] Invanz no longer broken out after 10-K filed 2023-02-24 (0001628280-23-005061); last reported $189.0M ... | Merck 10-K FY2022, p. 125 | MRK:companies/MRK/10k_FY2022.md#p127
[discontinued_breakout] Vaqta no longer broken out after 10-K filed 2024-02-26 (0001628280-24-006850); last reported $180.0M ... | Merck 10-K FY2023, p. 124 | MRK:companies/MRK/10k_FY2023.md#p126
```

## Known gaps

- Restatements and breakouts exist for ABBV, AMGN, BMY, GILD, JNJ, LLY, MRK, PFE only; other tickers get table notes only.
- Series breaks come from the revenue-check table, which holds one value per accession for most products, so few rows appear.
- Table notes are keyword matches and include routine accounting reclassifications (hedges, AOCI); the reader must judge relevance.
