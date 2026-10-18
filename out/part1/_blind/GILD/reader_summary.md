# GILD (Gilead Sciences): blind reader summary

## The company in five lines
1. FY2025 revenue was $29,443M (+2%). HIV made up $20,752M, or 70.5% of it, and Biktarvy alone was $14,334M (48.7%) (10-K FY2025 pp.37, 39).
2. Net product sales grew 1.1% while gross sales grew about 5.3%. The gross-to-net rate went from 38% to 41% (10-K FY2025 p.40).
3. Biktarvy was selected for Medicare negotiation, with the negotiated price taking effect in 2028. The December 2025 MFN deal adds Medicaid MFN prices, pauses Section 232 tariffs for three years, and includes a clause handing back part of any international revenue gains (10-K FY2025 pp.19-20).
4. 2026 is a heavy business-development year. About $11.2B of acquired IPR&D in Q2 2026 (Arcellx, Tubulis, Ouro) turned GAAP and non-GAAP EPS guidance negative (8-K 2026-08-04).
5. HIV growth in 2026 is now led by realized price and channel mix, with demand listed last (10-Q 2026Q2 p.31; Q2 2026 slides p.9).

## Three strongest candidates
1. **GILD-c05 (Footnotes): IP-sale revenue "not expected to reoccur" did recur and stays in non-GAAP.** In Q3 2025 Gilead booked $400M of previously constrained revenue from an old IP sale and called it non-recurring. Another $156M came in Q2 2026. The proxy strips it out of the EPS used for executive pay ($0.25, or 3.1% of FY2025 non-GAAP EPS of $8.15), but it stays in the non-GAAP figures investors get. Confidence: high.
2. **GILD-c03 (Gross-to-net): the GTN rate rose 251 bps to 40.8% of gross sales.** At the 2024 rate, that change cost about $1.2B of 2025 net revenue. Management cited a Part D redesign headwind of about $900M, which leaves roughly $327M unexplained. The FY2025 10-K also dropped the split between rebates and other deductions. Over the same period Biktarvy's list price rose faster than Dovato's (+5.9% vs +4.0% in 2025). Confidence: high.
3. **GILD-c04 (Inventory and receivables): inventory and receivables outgrew sales.** Total inventory rose 21.7% and net receivables 11.2%, against 1.1% sales growth. Days of inventory went from 210 to 256. Most of the build sits in other long-term assets. It includes $613M of Trodelvy made on a manufacturing process FDA had not yet approved, which was $568M by June 2026, and this is the same year the ASCENT-07 trial missed. Confidence: medium.

Runner-up: **GILD-c06 (Earnings-call Q&A).** On the October 2025 call, management called HIV growth "real demand-driven" and would not size its Medicaid exposure. By Q2 2026, Biktarvy's growth drivers in the 10-Q read price, then inventory, then demand. GILD-c01 adds that the 10-K's IRA wording now includes spillover into Medicaid rebates and 340B prices.

## Data gaps and limits
- **Transcripts.** Of the last four calls, only 2025Q3 is grade A. The 2025Q4, 2026Q1 and 2026Q2 calls are grade C (Motley Fool / roic.ai), so I read them for context but quote no speaker from them, and cite 2026Q2 by label only. Queries tried: `cite.py "ACA subsidies" --ticker GILD`, a scan of the three grade-C transcripts for Medicaid/MFN/IRA/inventory/price, and a check of `transcripts_index.csv` (it has no better grades). The grade-A 2025Q3 transcript also exists as a Bloomberg copy, which I did not quote.
- **Gross-to-net.** Gilead discloses GTN only once a year. The 10-Qs have no GTN table (grep "gross-to-net" in 10-Q 2026Q1/Q2 returned nothing), so I cannot measure GTN for 2026.
- **Peer GTN.** I found no shortlist peer that discloses a comparable GTN percentage (`cite.py "gross-to-net deductions percent of gross sales" --doc-type annual_report --since 2026-01-01`). I used WAC and NADAC tables as the peer price proxy instead.
- **IP sale.** The counterparty and the IP behind the constrained revenue are never named (`cite.py "constrained revenues sale intellectual property" --ticker GILD`).
- **Medicare/Medicaid exposure.** The government-channel share of Biktarvy comes from CMS gross spend and Medicaid reimbursed amounts (medicare_market.csv), not from Gilead's net revenue. Gilead does not disclose payer-mix percentages.
- **Biktarvy label expansion.** The index has no epidemiology for the treatment-experienced, viremic, resistance-free subgroup (indication_epidemiology.csv covers HIV prevalence and viral suppression only), so c08 is sized per 1,000 patients.
- **Litigation.** The 10-K discloses no accrual for the ~23,000 TDF plaintiffs or the Texas qui tam case, which moved from August to December 2026 (no-finding GILD-n02).
- **Page numbers.** The math strings cite printed page numbers ("p.39"). The evidence `page` field is the index page_no, which runs one higher than the printed page in the 10-K, and the label next to it gives the printed page.
