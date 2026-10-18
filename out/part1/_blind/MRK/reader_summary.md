# MRK blind read: reader summary

## The company in five lines

1. Merck had $65.0B of 2025 sales (+1.3%). Keytruda was 49% of sales, with U.S. Keytruda at $18.8B (10-K FY2025 p.31, p.134).
2. The starter thread is the Keytruda 2028 LOE and the Januvia LOE plus IRA price. Both are in the filings and on every call, so I excluded them.
3. The defense is Keytruda Qlex (subcutaneous). It was approved September 2025, got its permanent J-code April 2026, and was $463M in Q2 2026, about 5.5% of Keytruda-family sales.
4. 2025 U.S. growth (+$4.2B) came mostly from a $3.3B drop in chargeback and rebate provisions, not from gross demand. Over the same year, inventory grew about 15 times faster than sales.
5. The new growth bridge is Winrevair, Capvaxive, Ohtuvayre and Lipfendra (approved July 2026). It runs into an MFN deal that ties in-term launches to MFN-country reference pricing.

## Three strongest candidates

1. **MRK-c01, inventory build.** Total inventory rose 19.8% in 2025 against sales up 1.3% (12,339 vs 10,302). Inventory not expected to sell within a year went from $3.8B to $5.5B to $5.9B (Jun 2026). Neither MD&A nor any call explains it, and the FY2025 risk factors added a new sentence on inventory write-downs. BMS inventory grew 5.2% over the same year. Confidence medium.
2. **MRK-c02, gross-to-net narrowing.** The U.S. chargeback and rebate provision fell from $13.3B to $10.0B while U.S. sales rose $4.2B, so about 78% of U.S. growth was a narrower discount gap. Part of that was a Januvia "favorable true-up to customer discounts", and it is already reversing (Q2 2026 Januvia U.S. -31%). BMS's U.S. GTN rate widened from 49% to 53% over the same year. Confidence medium.
3. **MRK-c05 with MRK-c10, Keytruda Qlex conversion ceiling.** Management still targets 30-40% adoption by 2028, but:
   - Qlex is 7.9% of U.S. Keytruda-family sales in Q2 2026.
   - The CFO says use is "predominantly" monotherapy or oral combinations.
   - The label has Qlex dosed alongside same-day IV chemo.
   - Medicare pays about 4.1% more per Qlex dose than per IV dose (395 mg x $32.13 vs 200 mg x $60.97).
   - The 10-K added "lower than expected utilization of Keytruda Qlex" as a risk.

   Each 10 points of adoption shortfall leaves about $1.9B of U.S. Keytruda on the biosimilar-exposed IV form.

The other candidates, all verified:
- c03: IRS transition-tax NOPA of $1.3B plus $260M penalties, about $0.63/share, with the wording hardening each filing.
- c04: Halozyme injunction banning Keytruda SC in Germany. The appeal has slipped three filings in a row, and Halozyme has added a counterclaim covering seven more EU markets.
- c06: MFN deal terms. These include MFN reference pricing on launches and foreign-revenue sharing. BMS's deal instead has a "balanced pricing" approach and a shield from future pricing mandates.
- c07: Vaccine schedule drift. Rotavirus and hepatitis vaccines moved to shared decision-making, and insurers have pledged no cost-sharing only through end-2027.
- c08: Koselugo and three small products folded into "Other". Lump-sum Koselugo payments are now booked inside Sales.
- c09: The Keytruda IRA date moved from Jan 2028 to Jan 2029. Confidence is low because it was said once on the Q4 2025 call.

## Data gaps (with queries tried)

- **No reason for the inventory build.** I searched for 'inventor' across the FY2025 10-K, both 2026 10-Qs and the four A-grade calls. The only hits were about China, Capvaxive and Enflonsia stocking.
- **No Keytruda IRA discount or Medicare net share.** I used CMS Part B gross spend ($5,988.5M, fact rx/partb_providers_by_drug.csv#948) as an upper-bound base. There is no `ira_negotiation` file for Keytruda.
- **No Keytruda sales by country.** Germany and the seven Dutch-counterclaim markets can't be sized. I searched 'Germany', 'Europe' and 'Keytruda SC' in the 10-K and 10-Qs.
- **MFN contract details are not in the index.** The "certain exceptions", the MFN Countries basket and the revenue-sharing formula are missing. I searched 'repatriate foreign revenue' across all tickers and 'MFN Countries'.
- **No Lipfendra price or WAC row.** I searched for 'Lipfendra' in the 10-Q 2026Q2, the Q1 and Q2 2026 calls, and the gtn_proxy and wac_increases tables.
- **The Tecentriq subcutaneous (Hybreza) label is not in the index,** so the SC comparison covers only Opdivo Qvantig.
- **I did not retrieve AstraZeneca or Roche filing or call statements on Imfinzi and Tecentriq.** The rival-maker comparison uses BMS only.
- **The 2024Q1 to 2025Q1 transcripts are grade C,** so I used no speaker quotes from them. The four latest calls (2025Q3 to 2026Q2) are grade A and were read in full by keyword.
- **The Qlex ASP is a 3-quarter mean** (fact pricing/gtn_proxy.csv#9), so the 4.1% per-dose premium is provisional.
