# JNJ blind read: reader summary

## The company in five lines

1. FY2025 sales were $94.2B (+6.0%), but that headline is volume +8.4% and price -3.1%. The price drag is the worst in the 2020-2025 10-K tables (10-K FY2025 p.23).
2. Innovative Medicine is $60.4B. STELARA fell to 6.5% of revenue as biosimilars arrived. DARZALEX (15.0% of revenue, $14.4B) and TREMFYA ($5.2B, U.S. +79% in Q3 2026) carry the growth.
3. In January 2026 J&J signed an MFN deal with the U.S. government. It covers Medicaid at developed-country prices, TrumpRx, and a tariff exemption, and its terms are confidential. Pharma tariffs are zero for MFN signers only until January 20, 2029.
4. Drug manufacturing is mostly outside the U.S.: 3 U.S. Innovative Medicine plants against 16 abroad (10-K FY2025 p.18), down from 4 U.S. plants a year earlier.
5. 2026 guidance is about $100.7B operational sales and $11.10 adjusted EPS (2026Q3 call p.8). An Orthopaedics spin is planned for mid-2027.

## Three strongest candidates

1. **JNJ-c03 (Peer contrast): drug plants moving the wrong way before the 2029 tariff cliff.** U.S. Innovative Medicine plants fell from 4 to 3 and non-U.S. plants rose from 14 to 16 between the FY2024 and FY2025 10-Ks. A Q2 2026 restructuring ($650-750M) exits more Innovative Medicine plants. The zero tariff for MFN signers ends January 20, 2029, after which EU-origin goods pay 15% and the onshoring-plan rate rises to 100% in 2030. AbbVie has 10 of 19 significant plants domestic; J&J has the lowest U.S. share of FDA-registered sites on the shortlist (5 of 20). Illustrative cost is $0.9-1.2B a year at the 15% rate (about $0.30-0.40 EPS); that figure rests on stated assumptions.
2. **JNJ-c01 (Gross-to-net): price swung from 0.0 to -3.1 points of growth.** That is about $2.75B of 2025 revenue. Innovative Medicine rebate accruals outgrew segment sales in both 2024 (+11.1% vs +4.0%) and 2025 (+7.6% vs +6.0%), while AbbVie's rebate provisions grew in line with its revenue. No call in 2025Q4-2026Q3 discussed it.
3. **JNJ-c02 (Language drift): the MFN deal is barely disclosed.** It gets one sentence in the FY2025 10-K business section. It is absent from Risk Factors and from both 2026 10-Qs, and its terms are confidential. The CFO says each quarter that margin guidance "absorbs" its cost but never sizes it, and no analyst asked about it on four calls. BMS and Merck name their terms in their 10-Ks. Sensitivity: about $0.12 EPS per 1% of U.S. Innovative Medicine sales conceded.

The other candidates, all with verified quotes:

- c05: ICOTYDE sales were deflected on three straight calls. The revenue ceiling is $126M in Q3 2026, shared with IMAAVY, against more than 20,000 patients started.
- c07: the Genmab royalty is sized for the first time at $2.4B, giving a U.S. roll-off worth about $0.47 EPS from 2029. The Xoma TREMFYA royalty suit survived dismissal.
- c08: 2025 filings blamed "Part D redesign"; the 2026 10-Qs say "patient mix" instead, as U.S. ERLEADA growth slows to +4.7% ahead of IRA 2028.
- c04: finished goods are up 19% year over year against 6.6% sales growth. This is low confidence because AbbVie shows a similar 2025 build.
- c06: TREMFYA's subcutaneous induction label edge comes with a falling IV ASP: -11.8% vs Skyrizi -6.2%. Low confidence.

## Data gaps, with the queries tried

- **No 10-Q for Q3 2026.** The latest 10-Q is 2026Q2, so Q3 balance-sheet, inventory and legal updates come only from the 8-K and the call.
- **No ICOTYDE list price or WAC, and no split of IMAAVY sales.** Searched "ICOTYDE price", wac_increases.csv and nadac_history.csv. So the free-drug share in c05 cannot be computed.
- **No TREMFYA net price for subcutaneous (Part D) doses.** Only the IV J1628 Part B ASP is public, which limits c06. The partb_asp_quarterly.csv rows are table facts with no page, so verify_quote cannot run on them. They were checked verbatim against the CSV and flagged with a verify_note.
- **MFN agreement terms are confidential.** The 2026-01-08 press release says so, and there is no contract exhibit in the index. Searched "most favored", "TrumpRx", "access to medicines" and "developed countries" across the FY2025 10-K and the 2026 10-Qs.
- **Plant-by-product mix and customs values are not disclosed,** so the tariff figure in c03 is a bound, not a forecast.
- **Genmab royalty contract term is not in the index.** Searched "Genmab", material_agreements and agreements. The 2029 roll-off rests on 10-K patent dates plus the CEO's 2026Q1 remark.
- **Transcript quality.** The 2026Q2 transcript file has its spaces collapsed, so its quotes are taken from the official PDF (JNJ:verified/calls/src/JNJ_2026Q2_official.pdf), grade A. 2024Q4 and 2025Q1 are grade C and were not quoted. All quoted transcripts are grade A.
- **No price/volume split in 10-Qs.** Searched the 2026Q1 and 2026Q2 10-Qs for "Volume Price Currency", so it is unknown whether the 2025 price drag continued into 2026.
