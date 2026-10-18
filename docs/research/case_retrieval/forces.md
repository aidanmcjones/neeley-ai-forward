# case_forces: IRA, MFN and tariff exposure per company

Answers: what the verified policy tables and the company's own filings and calls say about IRA Medicare negotiation, the MFN deal and tariff exposure.

Call: `forces(ticker, force="all" | "ira" | "mfn" | "tariff", k=60) -> list[dict]` in `agent/moat/case_forces.py`. An unknown ticker returns `[]`. After the first `k` rows, one `peer_matrix` row is always appended.

## Fields

Every row: `ticker, kind, force, item, value, unit, effective_date, text, citation, url, locator, source_id, verify_status, source, quote_grade, license`.

- `kind`: summary, exposure_item, ira_drug, mfn_term, tariff_item, manufacturing_site, filing_statement, call_statement, peer_matrix.
- Table rows: `locator` is the facts locator (doc page of the underlying source when indexed, else `fact:<table>#<row>`); `verify_status` and `source` come from the table.
- Statement rows: sentence found on an indexed page, checked with `verify_quote`; `locator` is `doc_id#p<page>`; transcripts carry `quote_grade` (A or B only).
- Extra fields: ira_drug rows from ira_cut_check carry `mfp_usd, list_usd, recomputed_pct`; manufacturing_site rows (one per country) carry `country, in_us`; summary rows carry `fields` and `traceable_row_ids`.
- peer_matrix: `value` = {ticker: {ira_share_of_total_revenue_pct, mfn_date, us_investment_pledge_usd_bn, tariff_exempt_until}} for the 10 shortlist tickers; `locators` is the parallel dict of facts locators.

## Sources and limits

- data/moat/verified/policy/: force_summary.csv, policy_exposure.csv (dropped rows skipped), ira_cut_check.csv, manufacturing_sites_verified.csv, definitions.md.
- Filing and call sentences: two latest annual reports (duplicate `_d2` copies skipped), latest 10-Q or interim, last four transcripts graded A or B, found through FTS on ten terms (Inflation Reduction Act, maximum fair price, negotiated price, Most Favored Nation, MFN, tariff, Section 232, manufacturing investment, TrumpRx, direct-to-consumer), at most 3 sentences per document.
- Manufacturing counts are FDA CDER registrations only (a floor; CBER sites under-covered). Revenue bases and pledge horizons differ by company; read definitions.md before comparing.
- Sentence splitting is regex based; a sentence cut mid-abbreviation can be short.
- The press release, gov, CMS fact sheet and 8-K documents are reached through the policy_exposure rows (which cite them), not searched separately.

## CLI

```
python -m agent.moat.case_forces NVO ira
[ira_drug/ira] IRA Ozempic/Rybelsus/Wegovy (IPAY 2027): % cut of MFP vs list = 71 | $274 $959 71% | CMS fact sheet, p. 2 | policy_gov:policy_gov/cms/cms_fact_sheet_negotiated_prices_ipay2027.md#p2
[filing_statement/ira] negotiated price = | The negotiated price for the products in Medicare Part D will go into effect in 2027. | Novo Nordisk 20-F FY2025, p. 7 | NVO:20f_FY2025.md#p8
```

## Known gaps

- Statement search is page-level FTS, so recall depends on FTS ranking (top 12 pages per document).
- Press release and 8-K documents are not independently searched for tickers lacking policy_exposure rows.
- The tariff force also returns manufacturing-footprint rows because they bear on tariff exposure.
