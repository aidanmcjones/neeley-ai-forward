# ABBV blind read: reader summary

## The company in five lines

1. FY2025 net revenue was $61,160M, up 8.6%. U.S. revenue was $46,603M, or 76.2% of the total (10-K FY2025 p.39). That is the highest U.S. share on the shortlist.
2. Skyrizi ($17,562M) and Rinvoq ($8,304M) now make up about 42% of revenue. Humira fell 49.5% to $4,540M (10-K FY2025 p.15, p.40).
3. Four IRA-selected drugs are in the queue: Imbruvica (2026), Vraylar and Linzess (2027), and Botox (2028). Imbruvica's U.S. sales are down 37.6% in H1 2026, against a 38% negotiated cut.
4. The MFN deal (January 2026) gives a three-year tariff and price-mandate exemption in exchange for "low prices in Medicaid", TrumpRx direct-to-patient listings and a $100B U.S. pledge over ten years.
5. GAAP results are dominated by the Skyrizi partner-royalty liability. It stood at $25.4B at year-end 2025 and $27.5B at June 2026, and its fair-value charges were $6.5B in 2025.

## Three strongest candidates

- **ABBV-c05, Footnotes (sharpest needle candidate).** The June 2026 10-Q (p.13) adds a new royalty tail on "pipeline assets in combination with Skyrizi", paid out to 2044 at a 38% probability. The FY2025 10-K (p.81) had already lengthened the Skyrizi royalty period to 2037, four years past the 2033 composition-of-matter patent. Cash royalty runs at 16 to 18% of Skyrizi sales. Management pitches Skyrizi-backbone combinations as "underappreciated", and no call has addressed the fact that those combinations carry the royalty. J&J's whole contingent-consideration book is $753M.
- **ABBV-c02, Gross-to-net.** Medicaid and Medicare rebate provisions rose 34.1% ($15,866M to $21,283M; 10-K FY2025 p.47). That is $5.4B more, against only $3.6B of U.S. net revenue growth. About $4.1B of 2025 revenue was absorbed above the U.S. growth rate. BMS's equivalent line rose only 9% under the same Part D redesign. AbbVie discloses no GTN percentage.
- **ABBV-c04, Segment and product table changes.** The 2026 10-Qs drop the whole Eye Care franchise ($2,109M in 2025) into "All other". H1 2025 was restated from $1,350M to $2,370M, which reconciles exactly to H1 2025 eye care of $1,020M, and the bucket is now down 10%. This happened as Alphagan and Combigan went onto TrumpRx.

The other candidates are:

- c01: Language drift (MFN spillover, the 340B admission, and the deleted "would significantly impact" sentence)
- c03: Year-end 2025 receivables and finished goods build, which has since unwound (low confidence)
- c06: The CEO deflected on the Vraylar and Linzess IRA cuts (44% and 75%), with a $1.1B to $2.2B 2027 exposure
- c07: Skyrizi's IV-only IBD induction versus Tremfya's subcutaneous option (low confidence)
- c08: Highest U.S. concentration on the shortlist, with a $100B pledge that is roughly business-as-usual spend

## Data gaps (what the index could not supply)

- **Transcripts.** Only the 2025Q3 transcript is grade B. 2024Q1 to 2025Q2, 2025Q4 and 2026Q1 are grade C, and 2026Q2 is grade D (all third-party). Three of the last four calls therefore cannot be quoted. I searched them for "royalt", "contingent", "Medicaid", "rebate", "inventory", "340B", "eye care", "Alphagan", "TrumpRx", "induction" and "Part D", and used them only to judge what was already said. No official A-grade transcripts or Bloomberg transcripts are indexed for ABBV.
- **No 2026Q3 filing.** The Q3 2026 10-Q and earnings release are not in the index. The latest are the 10-Q for 2026-06-30 and the 8-K pre-announcement dated 2026-10-05.
- **No GTN percentage or gross sales.** AbbVie does not disclose these. The GTN ratio in c02 is implied from provisions divided by (net revenue plus provisions), and it mixes U.S. and international.
- **Vraylar and Linzess Medicare share.** There are no Part D spending rows for Vraylar or Linzess in data/moat/tables/partd_by_year.csv (I tried grep "vraylar|linzess"). The c06 estimate therefore uses Imbruvica's realized pass-through as a bound.
- **Skyrizi royalty counterparty and rate.** Neither the 10-K nor the 10-Q names the royalty recipient or the rate (I grepped "Boehringer" and "royalty period": no hit). The 16 to 18% is an effective cash rate.
- **Skyrizi revenue by indication and route.** No source splits Skyrizi revenue by indication or by IV versus SC start, so c07 is a sensitivity only.
- **Pledge composition.** The split of the MFN pledge between R&D and capex, and its incremental share, are not disclosed (press release: "Further terms of this agreement remain confidential").
- **Peer U.S. shares.** In c08 these come from the compiled verified table (fact:policy/force_summary.csv) rather than each peer's 10-K page.
