# LLY blind reader summary

## The company in five lines
- Eli Lilly: FY2025 revenue $65.2B, up 45%, net income $20.6B (10-K FY2025 p.57).
- Mounjaro plus Zepbound were 56% of 2025 revenue and 65% of H1 2026 revenue (10-K FY2025 p.29; 10-Q 2026Q2 p.26).
- Growth is all volume. Price fell 10% in the U.S. in 2025, then 5% in the U.S. and 31% outside it in H1 2026 (10-K p.49; 10-Q 2026Q2 p.28).
- The November 2025 U.S. government deal trades lower prices for Medicare, Medicaid and cash-pay access. The 10-Q shows the Medicare piece is a Bridge program that ends Dec 31, 2027 (10-Q 2026Q2 p.25).
- The balance sheet is built for a very large launch: inventory up 81%, net PP&E up 44%, $1.5B of pre-launch orforglipron stock, and contingent consideration up tenfold in 2026.

## Three strongest candidates
1. **LLY-c09 Product fine print + LLY-c01 Language drift (read together).**
   - Zepbound's U.S. label has no CV-risk or MASH indication, and its obesity outcomes trial is still in Phase 3.
   - Wegovy has both indications, and Novo says CMS pays for obesity drugs in Part D only when they carry them.
   - Lilly's Medicare obesity access comes from a Bridge that expires 12/31/2027. Lilly also added a new risk factor saying deal volume may not offset the price concessions.
   - This is the sharpest needle candidate.
2. **LLY-c03 Inventory and receivables.**
   - In 2025, inventory grew 81% and receivables 61%, against revenue growth of 45%.
   - Work in process doubled. Days of inventory on cost of sales went from 329 to 454.
   - $1.5B of orforglipron pre-launch stock is at risk.
   - The new risk-factor wording about over-built capacity (LLY-c02) supports this.
3. **LLY-c05 Segment and product table changes.**
   - The FY2025 10-K stopped breaking out 10 named products.
   - The MD&A "Other products" line went from $3.4B (7.5% of revenue) to $22.9B (35.2%).
   - The regrouping hides a 16.7% U.S. decline in the legacy insulin bucket.

Runners-up:
- LLY-c04: U.S. rebate deductions grew 49.9% against 43% U.S. revenue growth. The rebate liability grew 45% against 33% in Q2 2026.
- LLY-c06: contingent consideration rose from $251M to $2.5B.
- LLY-c10: Mounjaro's ex-U.S. revenue passed its U.S. revenue in Q2 2026.
- LLY-c11 (low confidence): the Zepbound KwikPen costs pharmacies 36-54% less than single-dose pens at the same dose (NADAC).

## Data gaps (with queries tried)
- **Transcripts.** The only Lilly transcript at grade A or B is 2025Q3. Q4 2025 and Q2 2026 are grade C and Q1 2026 is grade D. So no speaker quotes from the last three calls can be used (LLY-n01). Greps for 'true-up', 'rebate', 'prior-period', 'NRDL' and 'stocking' found the topics but not quotable text.
- **List price.** No Lilly rows in company_list_vs_net.csv or wac_increases.csv. I used NADAC (an acquisition-cost survey) as the list-side proxy instead.
- **Medicare share of Zepbound.** Not disclosed anywhere in the index (searched 'Medicare' with 'obesity' in the 10-K and 10-Q). LLY-c09 is therefore sized as a sensitivity only.
- **Incretin product-liability MDLs.** No accrual, claim count or range is disclosed. The query 'NAION' found no NAION text in any of the five incretin labels (LLY-n02).
- **Novo Nordisk like-for-like figures not pulled.** This covers gross-to-net, inventory days, tax rate and insulin product breakout. The query 'insulin sales by product human insulin' (NVO annual_report) returned no FY2025 product table.
- **Orange Book / paragraph IV.** The 10-Q 2026Q2 p.18 notes tirzepatide ANDA filings from July 2026. These are patent and exclusivity items, so they were excluded under the brief.
