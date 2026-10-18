# AZN blind reader summary

## The company in five lines

- AstraZeneca PLC files a 20-F in USD under IFRS. FY2025 Total Revenue was $58,739m and Reported EPS was $6.60 per ordinary share (1,550m weighted shares) [20-F FY2025 p.F-2, F-22].
- The US is 40.8% of revenue ($23,970m), the lowest US share on the shortlist. China is $6,636m [p.F-22; force_summary.csv].
- Oncology is about 46% of H1 2026 revenue. Tagrisso ($7,254m), Imfinzi ($6,063m) and Calquence ($3,518m) lead it [p.F-16; 2026Q2 results p.7].
- H1 2026: Total Revenue +6% at CER, Core EPS +11%. Farxiga US loss of exclusivity and China VBP are the stated headwinds. China fell 13% at CER in Q2 [2026Q2 results p.1, p.7].
- Policy: an MFN deal (2025-10-10, terms confidential), $50bn of US manufacturing and R&D over 5 years, a Section 232 tariff delay to 2029-01-20, and IRA prices on Farxiga (2026, -68%) and Calquence (2027, -40%).

## Three strongest candidates

1. **AZN-c05 Gross-to-net (high).** In 2025, US gross sales rose 16.6% but net sales rose only 8.3%. Deductions grew $5.0bn to $23.9bn, or 50.5% of gross. Managed-care and Medicare rebates rose 29% and chargebacks rose 29%. Each 1pp of the rate is worth about $474m [20-F FY2025 p.34]. This is the highest discount rate among makers with a disclosed figure (BMY about 47%, TAK 46%).
2. **AZN-c02 Inventory and receivables (medium).** FY2025 inventories rose 24% and trade receivables rose 23%, against revenue +8.6%. DSO went from 56 to 64 days. Factorable receivables went from $0.67bn to $2.68bn. US destocking on Tagrisso, Imjudo and Lynparza followed in Q1 and H1 2026, and the H1 working-capital outflow nearly doubled [p.F-29; 2026Q1 p.8; 2026Q2 p.8, p.20].
3. **AZN-c03 Peer contrast (medium).** The $50bn US pledge is about 2.1x FY2025 US revenue over 5 years, one of the heaviest on the shortlist. Yet the Americas entities book only $440m of operating profit on $27.6bn of revenue, so profit sits in the UK and Europe, which is what an import tariff hits after 2029 [press release 2025-10-10; p.F-22].

Also worth reading:
- **c01 China.** A new anti-bribery principal risk names reimbursement exclusion, and the China customs matter escalated to an indictment of the operating company.
- **c04 Tax.** About $0.18 of the Q2 2026 Core EPS and $0.30 of FY2025 EPS came from one-off tax items, while cash tax ran at 31%.
- **c06 Calquence.** On the Q3 2025 call management called the IRA selection expected, then AZN sued HHS over it.
- **c07 Tagrisso.** The rival's label shows an OS win against Tagrisso monotherapy.

## Data gaps (queries tried)

- **Earnings calls.** Only 2025Q3 has a quotable grade-B transcript. 2025Q4 and 2026Q2 are one-page grade C. 2026Q1 is grade C or Bloomberg-licensed (cite only). So deflection analysis is limited to one quarter (see AZN-n02).
- **Calquence Medicare share.** There are no Calquence rows in tables/partd_by_year.csv, so the AZN-c06 impact is a range built on a stated reader assumption.
- **Channel inventory.** No weeks-on-hand disclosure. `search_pages("wholesaler inventory weeks on hand channel", AZN)` returned only old 2023 6-K text (AZN-n03).
- **Rival revenue.** Rybrevant + Lazcluze revenue was not found as a clean row. `search_pages("Rybrevant Lazcluze sales", JNJ)` hit only footnotes in JNJ 10-K FY2025 p.88.
- **Restatements.** verified/filings/restatements_triaged.csv and discontinued_breakouts.csv have no AZN rows (XBRL-based, and AZN files a 20-F). Checked manually instead (AZN-n01).
- **MFN terms.** The company states that the "Specific terms of this agreement remain confidential", so MFN exposure cannot be sized from filings.
