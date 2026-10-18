# Footnote extracts (agent/moat/case_footnotes.py)

Answers: what the notes of the two latest annual reports and the latest 10-Q (or interim report) say about litigation reserves, partner royalty splits, contingent consideration and tax-rate changes, and what changed year over year.

Call: `footnotes(ticker, topic="all" | "litigation" | "royalty" | "contingent_consideration" | "tax_rate", docs=None, k=40) -> list[dict]`

`k` is split evenly across topics for "all"; for a single topic it is the cap. `docs` overrides the doc_id list (no year comparison then).

## Fields

`ticker`, `kind`, `text` (1 to 3 sentences, under 600 chars, verbatim from the page), `numbers` (dollar amounts and percentages found in `text`), `doc_year`, `topic`, `citation`, `url`, `locator` / `source_id` (`doc_id#p<page_no>`), `quote_grade` (""), `license` (""), `doc_id`, `page_no`, `new_vs_prev`, `also_in_prev_year`, `prev_numbers` (numbers from the matching prior-year sentence, so a changed figure is visible).

`kind`:
- `footnote`: sentence in the latest annual report. `new_vs_prev=True` when no near match exists in the prior-year report; `also_in_prev_year=True` when one does.
- `latest_10q`: sentence in the latest quarterly or interim report with no near match in the latest annual report.
- `dropped_from_latest`: prior-year annual sentence with no near match in the latest annual report.

Every `text` passes `cite.verify_quote(text, doc_id, page_no)`.

## Method and sources

Per topic a list of FTS5 queries (see `TOPICS` in the module) runs against `pages_fts`, restricted to annual_report docs of the latest two fiscal years (by `period` year; all docs of that year, so 20-F exhibits and NVO `_d2` files are included) plus the newest quarterly_report or interim_report. Hit pages are split into sentences; a window of up to 3 sentences that contains every quoted term of the query is kept. Near-duplicates are merged by digit-masked token overlap (Jaccard 0.85 within a period, 0.6 across periods, so a sentence whose figure changed counts as "also in prev year" with differing `numbers` / `prev_numbers`).

Text only. No XBRL or companyfacts numbers are pulled; use the table helpers for reported values.

## CLI

```
python -m agent.moat.case_footnotes JNJ litigation -k 8
[litigation|footnote] Johnson & Johnson 10-K FY2025, p. 110 <JNJ:10k_FY2025.md#p115> new_vs_prev=True also_in_prev_year=False
    As of December 28, 2025, the total present value of the reserve to resolve the talc claims is approximately $3.4 billion, ...
[litigation|dropped_from_latest] Johnson & Johnson 10-K FY2024, p. 109 <JNJ:10k_FY2024.md#p114> new_vs_prev=False also_in_prev_year=False
```

## Known gaps

- Table rows (lines starting with `|`) are skipped, so figures that live only in tables are missed; numbers inside prose are returned.
- Query lists are generic and not tuned per company. Partner names are not hard-coded, so royalty recall depends on the filing wording ("royalt*" near collaboration, license, sales, partner, alliance).
- NVO interim reports are one page each, so the 600 char window is the only locator inside them.
- Several queries (e.g. "accrual" NEAR "lawsuit") return nothing for some issuers; an empty topic means no sentence matched, not that the topic is absent.
- Fiscal-year labelling uses the doc `period` year, which can be off by one for 52/53-week filers in older years (not an issue for the two latest years).
