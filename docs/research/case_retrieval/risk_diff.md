# Risk-factor and MD&A drift (agent/moat/case_risk_diff.py)

Answers: which sentences a company added, dropped or reworded in its risk factors and its MD&A between its latest annual report and the one before.

Call: `risk_diff(ticker, section="risk_factors" | "mdna" | "both", fy=None, prev=None, k=60, min_chars=80) -> list[dict]`

`fy` and `prev` take an annual_report doc_id (`"MRK:10k_FY2025.md"`) or a year (`"2025"`, `"FY2025"`). Defaults: the latest annual report period for the ticker and the one before it. `k` caps the diff rows per section (rows sorted by `salience`); one `section_stats` row per section is always added on top. `min_chars` drops shorter sentences (headings, table fragments).

## Fields

`ticker`, `kind`, `section`, `text`, `prev_text`, `citation`, `url`, `locator` / `source_id` (`doc_id#p<page_no>`), `doc_id`, `page_no`, `prev_citation`, `prev_url`, `prev_locator`, `prev_doc_id`, `prev_page_no`, `quote_grade` (""), `license`, `similarity` (changed rows, 0 to 1), `diff` (changed rows, word level `-[old] +[new]`), `salience`, `flags` (which boosts fired, plus `year_rollforward` or `coverage_mismatch`).

`kind`:
- `added`: sentence in the new report with no exact or fuzzy match in the old one. `text` and `locator` are the new doc page.
- `removed`: sentence in the old report with no match in the new one. `text` = `prev_text` = the old sentence, and `citation` / `locator` point to the old doc page (the sentence is not in the new doc).
- `changed`: fuzzy pair (character ratio 0.6 or more after a word-overlap prefilter). `text` is the new sentence on the new page, `prev_text` the old one on `prev_locator`.
- `section_stats`: `text` is the section heading as printed on its first page (verifiable); `words`, `prev_words`, `delta_words`, `pct_change`, `sentences`, `prev_sentences`, `n_added`, `n_removed`, `n_changed`, `pages`, `prev_pages` and a one-line `summary` carry the counts.

Every `text` passes `cite.verify_quote(text, doc_id, page_no)` on its locator and every `prev_text` passes it on `prev_locator`; rows that fail are dropped (0 dropped across the 10 shortlist tickers when built).

`salience`: base 1.0 added, 0.9 removed; changed rows score the changed words (plus 1.5 x (1 - similarity)) and are cut to 15% when only years changed. Boosts: non-year numbers, `%`, `$`, drug names (`case_sets.all_drugs()` plus docs.drug), and words such as material, may not, could, no longer, new, IRA, Medicare, tariff, MFN, litigation, exclusivity, generic, biosimilar, 340B, compounding (full list in `KEYWORDS`). It is a sort key, not a finding.

## Method and sources

Only the citation index (`pages` table, annual_report docs, superseded docs skipped). No network, nothing cached on disk.

1. Section location per doc. Item headings at a line start: 10-K "Item 1A. Risk Factors" to "Item 1B"/"Item 1C"/"Item 2", "Item 7. Management's Discussion" to "Item 7A"; 20-F "D. Risk Factors" to "Item 4. Information on the Company", "Item 5. Operating and Financial Review" to "Item 6. Directors". The longest start-to-next-end span wins, so table-of-contents entries are skipped. Without an item heading, a running header or footer tags the pages ("Risk Overview", "/ Risk management", "/ Key operational risks", "Financial Review", "/ Financial performance", "/ Financials").
2. 20-F companions. When either year's main section is under 3,000 words and both years have a same-period companion doc, the companion's section is appended in both years: NVO `_d2` annual report ("Risk management" and the financial pages), AZN `_ex15d1` exhibit ("Financial Review"). AZN risk factors come from the main 20-F Item 3.D (5,800 words), so the exhibit is not used for them.
3. Sentences. Paragraphs are rebuilt from the page text (table lines skipped; blank lines that are only PDF line wraps are joined), split into sentences, cut to 590 chars at a word boundary.
4. Diff. `difflib.SequenceMatcher` on normalised sentence lists; sentences that only moved are dropped; the leftover removed and added sentences are paired greedily into `changed` rows.
5. If the two sections differ in size by more than 3x, only the `section_stats` row is returned, flagged `coverage_mismatch` (a capture problem, not a disclosure change).

Runtime on the 765 MB index, `section="both"`: 0.2 to 0.7 s for the US 10-K filers, 0.6 s AZN, 3.7 s NVO (one 585k-char page).

## CLI

```
python -m agent.moat.case_risk_diff MRK --section risk_factors -k 5
[risk_factors|section_stats] risk factors: 11,176 words vs 10,745 prior (+431, +4.0%); 33 added, 18 removed, 62 changed sentences before the k cap
[risk_factors|removed] salience=5.2 Merck 10-K FY2024, p. 28 <MRK:10k_FY2024.md#p30>
    In addition, the Company expects U.S. sales of Keytruda to decline beginning in January 2028 upon implementation of government pricing under the IRA, and to further decline upon loss of market exclusivity following expiration of the U.S. compound patent in December 2028.
[risk_factors|added] salience=4.1 Merck 10-K FY2025, p. 29 <MRK:10k_FY2025.md#p31>
    The Company expects a significant decline in sales of Januvia in the first half of 2026 reflecting the impact of government price setting noted above and subsequently, ...
```

Options: `--section risk_factors|mdna|both`, `--fy`, `--prev`, `-k`, `--min-chars`. Prints a one-line reason and no rows when the ticker lacks two annual reports.

## Known gaps

- A `removed` row means "no near match in the new section", not "dropped from the filing": the sentence may have moved to another Item. Check with `cite.search_pages` before calling it a deletion.
- Reworded sentences below the 0.6 ratio show as one `removed` plus one `added` row (common in MD&A, where the year's figures are rewritten).
- NVO FY2025 `_d2` is one 585k-char page, so its rows cite "file page 1 (no printed page number)"; the pseudo pages used to find the section are split at the "Novo Nordisk Annual Report 2025 /" running headers. NVO FY2024 `_d2` has real pages.
- Tables are skipped (lines starting with `|`), but some PDF-derived pages (AZN `_ex15d1`) flatten tables into prose, so a few rows are table text.
- GSK (1-page 20-F captures) returns []; SNY FY2025 vs FY2024 returns only a `coverage_mismatch` stats row; Roche and Boehringer have no risk-factor heading in their annual reports, so only MD&A-like financial review pages are found for Roche.
- NVS 20-F risk factors locate to about 2,900 words, which may be a partial section; not checked against the filing.
- Section boundaries are heading heuristics. When a filer changes its heading style between years, word counts move without any disclosure change, so read `pages` / `prev_pages` before using `pct_change`.
