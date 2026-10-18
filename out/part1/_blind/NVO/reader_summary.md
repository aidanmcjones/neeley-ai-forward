# NVO blind read: reader summary

## The company in five lines

1. Novo Nordisk (reports in DKK) had 2025 net sales of DKK 309,064m (+6% DKK, +10% CER) and operating profit of DKK 127,658m. 80% of sales come from IRA-selected drugs: Ozempic, Wegovy, Rybelsus and fast-acting insulin (AR2025 p.83, p.90).
2. For 2026 it guides on new "adjusted" measures that exclude a USD 4.2bn (DKK 26.8bn) 340B provision reversal and any impairment above DKK 1bn. The guide was raised to 0% to -6% CER on 4 Aug 2026 (6-K Q2 2026 p.2).
3. The US is 56% of sales. In Q2 2026 US Wegovy injectable sales fell 22% on price, and 39% of injectable scripts now run through self-pay. The new Wegovy pill (DKK 3,141m US in Q2) is offsetting the decline (6-K p.7, p.31).
4. The 2023-24 capacity build now looks too large. Commitments to contract manufacturers are DKK 91bn and assets under construction were impaired. Inventory write-downs rose 52%, and a DKK 3bn "right-sizing" charge was booked in Q2 2026.
5. In 2026 the balance sheet quality got worse: receivables are up 28% year on year on 2% sales growth (DSO about 82 to 103 days), and favourable rebate true-ups returned to adjusted growth.

## Three strongest candidates

- **NVO-c01 (Footnotes): DKK 91bn of off-balance-sheet contract-manufacturer commitments.** These were DKK 33.1bn at end-2023, 2.75 times less, and now equal 29.5% of 2025 sales. The first exit cost, about DKK 3bn for "right-sizing of manufacturing capacity agreements", hit Q2 2026 (AR2025 p.110; AR2024 p.130; 6-K Q2 2026 p.13). No call has discussed the size of the remaining stock.
- **NVO-c02 (Inventory and receivables): receivables grew 28% year on year on 2% sales growth.** DSO rose from 82 to 103 days, against Lilly's 79.5. This happened alongside "wholesaler pipeline fill" for the re-branded Ozempic pill and for the Wegovy pill outside the US. Factoring (DKK 5.6bn) is too small to explain it (6-K Q2 2026 p.29, p.11, p.10; 6-K Q2 2025 p.31, p.15; LLY 10-Q p.5, p.7).
- **NVO-c05 (Gross-to-net), paired with NVO-c08 (Q&A): the GTN tailwind that would "not repeat" has repeated.** The CFO (grade-B call) and the annual report both said the 2025 favourability would not recur. Q2 2026 adjusted growth was "positively impacted by rebate adjustments", worth roughly 2-3 points of the 7%. The rebate liability is 43.5% of a year's sales, and Medicaid rebates grew 17.7% against US sales growth of 3.4% before MFN Medicaid pricing applies. On the 5 Nov 2025 call, management declined to say whether channel prices would converge. The MFN deal announced the next day made them converge.

Runners-up: c04 (language drift that adds the "direct-to-patient cash channel" as a price-pressure driver; rated high confidence) and c09 (the Wegovy pill label says it was "not studied" in obese T2D and warns of subtherapeutic levels, while Foundayo was studied in T2D).

## Data gaps and what I could not find

- **Only one quotable grade-B call.** Of the last four calls, only 2025Q3 is grade B. 2025Q4, 2026Q1 and 2026Q2 are grade C, so I did not quote them. The 2026Q1 Bloomberg transcript is grade A but licensed, so I cited it without quoting. This means two figures rest on grade-C transcripts and are labelled as such: the DKK 2bn size of the Q2 2026 rebate true-up, and the "USD 5bn" H2 2025 GTN effect.
- **The 20-F FY2025 exhibit d2 is indexed as a single 585k-character page** (`NVO:20f_FY2025_d2.md`). Page-level citations therefore use the glossy Annual Report 2025 (`NVO:reports/annual_report_2025.md`) instead.
- **The press release `NVO:policy/press_2026-02-24_us_list_price_reduction.md` has 0 pages in the index.** Searching "list price reduction" returned no text, so the US list-price cut could not be quantified from a primary source.
- **Inventory at 30 Jun 2026 prints the same as at 31 Mar 2026** (DKK 51,352m in both 6-Ks). This may be an extraction error and should be checked against the PDF.
- **No comparable Lilly table of contract-manufacturer purchase obligations** was found. The query "purchase obligations" with ticker LLY returned no commitments table, so the peer comparison for c01 uses inventory and pre-launch stock instead.
- **The US T2D/obesity overlap could not be read cleanly.** The NVO Q2 2026 slide p.23 extracted as garbled numbers, so c09 uses 35m/115m only as an upper bound. The epidemiology tables have no T2D-within-obesity share.
- **Customs value and import share of US-sold semaglutide are not disclosed**, so the 2029 tariff estimate in c10 is an explicit assumption.
- **Quarterly gross-to-net detail is not disclosed.** The 6-Ks give no rebate roll-forward, so the Q2 2026 true-up cannot be sized from an official document.

Output: `out/part1/_blind/NVO/candidates.jsonl`. It holds 1 header, 10 candidates, 3 no-finding records and 1 product line. Every evidence quote passed `verify_quote`.
