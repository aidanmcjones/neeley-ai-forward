# MRK Part 2: Decide

Generated 2026-10-18T05:32:37+00:00. Merck & Co., Inc. Candidates considered: 5. Skeptic outcome: 4 killed, 1 narrowed, 0 survived as stated.

## The move

Merck's CFO and head of manufacturing fund a $7.5M[derived: assumption], 15-person[assumption] team that by month 6[assumption] splits the $5.9B[1] long-dated inventory pool by product and discloses the split in the 10-Q inventory note, then releases only the sellable surplus, up to $1.0B[2] counted net of reserve charges, to retire the 4.30%[2] notes due 2028 instead of refinancing them.

  numeric_check: passed (6 checked: 3 verified, 1 derived, 2 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)
  [2] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)

Type: other:working_capital_release

### Budget

amount_usd: 7,500,000; people: 15; period: 24 months

$7.5M[derived: assumption] over 24[assumption] months: 15[assumption] people x $250,000[assumption] loaded cost per person-year x 2[assumption] years, all assumptions because no Merck page gives supply-planning headcount or cost per person. Owners: the CFO and the head of manufacturing. They decide at month 6[assumption], on the review's product split, whether anything is released.

  numeric_check: passed (6 checked: 0 verified, 1 derived, 5 assumed)

## Drivers (Part 1 findings)

- Finding 2: Driver. The long-dated inventory pool is the only Part One finding that both skeptics left standing as a move: it ties up cash Merck is now borrowing to replace, it kept growing after the tariff delay that was its stated reason, and a product split plus a capped, net-of-reserve release is a step the CFO controls without a counterparty.
- Finding 1: Not the driver, though it is the Sharpest Needle. Both skeptics killed the tax-settlement move: Merck already contests the NOPAs in administrative proceedings, the annual report says resolution may take a number of years, a reserved penalty would come back as a non-cash release, and disclosing reserve coverage would hand the IRS Merck's own estimate. The move's cash plan keeps this exposure separate from the inventory release (see case_for.net).

## Case for it

### Cost

Cost is $7.5M[derived: assumption] = 15[assumption] people x $250,000[assumption] per person-year x 2[assumption] years. Write-downs the review finds are not a cost of the move: Merck is already booking them (non-GAAP gross margin guidance moved from about 82.0%[1] to about 81.0%[1] and now includes higher inventory reserves), so they are netted out of the release on the return side.

  numeric_check: passed (6 checked: 2 verified, 1 derived, 3 assumed)

  [1] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)

### Return

Return is pre-tax interest avoided on the 4.30%[1] notes over 24[assumption] months, by release scenario: nothing if the review finds the pool is bridge or pre-patent-expiry stock; $14.5M[derived: 1, 2, 3] if $0.34B[derived: 1, 2, 3] is released, the $1.0B[1] cap less a $0.66B[derived: 2, 3] impaired slice; $43M[derived: 1, assumption] if the full $1.0B[1] is released. Weighted 30%[assumption], 40%[assumption] and 30%[assumption], expected interest is $18.7M[derived: 1, 2, 3, assumption] and the expected one-time cash release is $0.43B[derived: 1, 2, 3, assumption], counted net of reserve charges.

  numeric_check: passed (13 checked: 3 verified, 6 derived, 4 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [3] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)

### Math, step by step

1. Pool: $5.9B[1] at June 30, 2026 and $5.5B[1] at December 31, 2025, against $3.8B[2] at December 31, 2024. It grew $0.4B[derived: 1] in the first half of 2026, after the December 2025 tariff delay, and it is almost entirely raw materials and work in process[3].

  numeric_check: passed (4 checked: 3 verified, 1 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)
  [2] Merck 10-K FY2025, p. 105 "these amounts included $ 5.5 billion and $ 3.8 billion, respectively, of inventories not expected to be sold within one year" (exact)
  [3] Merck 10-Q 2026-06-30, p. 19 "Amounts recognized as Other Assets are comprised almost entirely of raw materials and work in process inventories" (exact)

2. Release cap: $1.0B[1], the size of the 4.30%[1] notes due 2028. A full release leaves the pool at $4.9B[derived: 1, 2], still above the $3.8B[3] December 2024 level, so the move never treats the whole $2.1B[derived: 2, 3] build as surplus.

  numeric_check: passed (5 checked: 3 verified, 2 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)
  [3] Merck 10-K FY2025, p. 105 "these amounts included $ 5.5 billion and $ 3.8 billion, respectively, of inventories not expected to be sold within one year" (exact)

3. Impairment haircut: guidance gross margin moved from about 82.0%[1] to about 81.0%[1] for higher inventory reserves. 1 point[derived: 1] on the $66.3B[2] low end of revenue guidance is $0.66B[derived: 1, 2]. The middle scenario releases $1.0B[3] - $0.66B[derived: 1, 2] = $0.34B[derived: 1, 2, 3].

  numeric_check: passed (8 checked: 4 verified, 4 derived, 0 assumed)

  [1] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)
  [3] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)

4. Interest by scenario, straight-line release (average balance is half the release) at 4.30%[1] for 2[assumption] years: $0.34B[derived: 1, 2, 3] / 2[assumption] x 4.30%[1] x 2[assumption] = $14.5M[derived: 1, 2, 3]; $1.0B[1] / 2[assumption] x 4.30%[1] x 2[assumption] = $43M[derived: 1]; no release earns nothing.

  numeric_check: passed (12 checked: 4 verified, 3 derived, 5 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [3] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)

5. Weights 30%[assumption] on no release, 40%[assumption] on the middle and 30%[assumption] on the full release: expected interest = 40%[assumption] x $14.5M[derived: 1, 2, 3] + 30%[assumption] x $43M[derived: 1] = $18.7M[derived: 1, 2, 3, assumption]; expected release = 40%[assumption] x $0.34B[derived: 1, 2, 3] + 30%[assumption] x $1.0B[1] = $0.43B[derived: 1, 2, 3, assumption].

  numeric_check: passed (13 checked: 1 verified, 5 derived, 7 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [3] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)

6. Against cost: expected interest of $18.7M[derived: 1, 2, 3, assumption] is 2.5[derived: 1, 2, 3, assumption] times the $7.5M[derived: assumption] cost over 24[assumption] months, and the middle scenario's $14.5M[derived: 1, 2, 3] is 1.9[derived: 1, 2, 3, assumption] times cost. Released cash itself comes on top.

  numeric_check: passed (6 checked: 0 verified, 5 derived, 1 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [3] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)

### Net, and the Sharpest Needle

Net over 24[assumption] months: expected interest of $18.7M[derived: 1, 2, 3, assumption] less the $7.5M[derived: assumption] cost is $11.2M[derived: 1, 2, 3, assumption] pre-tax, plus an expected one-time cash release of $0.43B[derived: 1, 2, 3, assumption], which is zero if the review finds no sellable surplus. Part 1's Sharpest Needle, the IRS transition-tax NOPAs of about $1.56B[derived: 4, 5] before interest ($1.3B[4] of tax plus $260M[5] of penalties), does not drive this move: both skeptics killed the tax move because Merck is already contesting the NOPAs[6], resolution may take a number of years[7], and a reserved penalty would come back as a non-cash reserve release. The cash plan keeps that exposure separate: even the full $1.0B[1] release would cover only 64%[derived: 1, 4, 5] of the $1.56B[derived: 4, 5], Merck already carries $546M[8] of accrued interest and penalties, and any tax payment would come from the $8,363M[9] of cash and investments at June 30, 2026, not from the release, which retires debt. Interest on any tax owed is left unsized: the IRS rate page is not yet in the index.

  numeric_check: passed (13 checked: 5 verified, 7 derived, 1 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [3] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)
  [4] Merck 10-Q 2026-06-30, p. 25 "would increase the amount of the one-time transition tax on certain undistributed earnings of foreign subsidiaries by approximately $ 1.3 billion" (exact)
  [5] Merck 10-Q 2026-06-30, p. 25 "the NOPAs included penalties of approximately $ 260 million. These amounts are exclusive of any interest that may be due" (exact)
  [6] Merck 10-Q 2026-06-30, p. 25 "is vigorously contesting the NOPAs through available administrative proceedings" (exact)
  [7] Merck 10-K FY2025, p. 129 "It may take a number of years to reach resolution of this matter" (exact)
  [8] Merck 10-K FY2025, p. 129 "Liabilities for accrued interest and penalties were $ 546 million and $ 437 million as of December 31, 2025 and 2024, respectively" (exact)
  [9] Merck 10-Q 2026-06-30, p. 45 "Cash and investments $ 8,363 $ 15,521" (exact)

## Two rejected alternatives

### MRK-m01 (campaign), killed on the Decider/compliance lens

Move: Fund a U.S. field program converting Keytruda IV patients to Keytruda Qlex, or its narrowed pilot in IV-chemotherapy combination regimens.

Why we passed: Management already says it is on track to reach 30%[1] to 40%[1] peak adoption of Keytruda Qlex by end of 2027 and has a contracting strategy to make conversion frictionless[2], so a funded program adds nothing the company has not announced and paid for. The label's crossover data cover monotherapy only, the draft doctor piece left out the route-specific administration-reaction warning, and the CFO lens found the narrowed chemotherapy-combination pilot earns no return inside 24[assumption] months.

  numeric_check: passed (3 checked: 2 verified, 0 derived, 1 assumed)

  [1] Merck investor presentation 2026-06, p. 25 "On track to achieve 30% to 40% peak adoption of KEYTRUDA QLEX by end of 2027" (substring)
  [2] Merck 2025Q3 earnings call (official), p. 15 "a commercial contracting strategy that really will make it frictionless to convert patients over" (exact)

### MRK-m02 (license_or_acquire), killed on the CFO/math lens

Move: If the German appeal fails, authorize a Germany-only settlement license with Halozyme on the MDASE patents for subcutaneous Keytruda.

Why we passed: No indexed page gives German Keytruda sales or an MDASE settlement royalty (the Halozyme comps in the index are voluntary Hypercon platform licenses), so neither cost nor return can be sized. Merck is winning on validity, with four PTAB decisions finding every challenged claim unpatentable[1], only Germany is under an injunction[2], and international Keytruda Qlex already sold $68M[3] in the second quarter of 2026 against $3,293M[4] of international IV Keytruda.

  numeric_check: passed (2 checked: 2 verified, 0 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 22 "The PTAB has since issued FWDs regarding four of the instituted PGR petitions finding every challenged claim unpatentable" (exact)
  [2] Merck 10-Q 2026-06-30, p. 22 "a preliminary injunction was awarded against the Company, prohibiting sales in Germany" (exact)
  [3] Merck 10-Q 2026-06-30, p. 28 "Keytruda Qlex 395 68 463" (exact)
  [4] Merck 10-Q 2026-06-30, p. 28 "Keytruda $ 4,611 $ 3,293 $ 7,904" (exact)

## Kill signals

| Signal | Threshold | Window | Gate |
|---|---|---|---|
| Month 6 product-split review: sellable surplus found in the long-dated pool | below $0.34B | month 6 | passed |
| Inventories not expected to be sold within one year, 10-Q inventory note | at or above $5.9B | month 7 (Q1 2027 10-Q) | passed |
| Same long-dated line, 10-Q inventory note | above $5.5B | month 10 (Q2 2027 10-Q) | passed |
| Non-GAAP gross margin guidance cut that cites inventory reserves | any cut below about 81.0% | months 6 to 10 (Q1 and Q2 2027 earnings slides) | passed |

1. Stop the release phase if the month 6[assumption] review finds less than $0.34B[derived: 1, 2, 3] of sellable surplus in the $5.9B[4] pool, the middle scenario after an impaired slice the size of the 2026 reserve cut.

  numeric_check: passed (3 checked: 1 verified, 1 derived, 1 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [2] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)
  [3] Merck earnings slides 2026Q2, p. 18 "Revenue $65.8B to $67.0B $66.3B to $67.3B" (exact)
  [4] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)

2. Kill if the long-dated line in the Q1 2027 10-Q inventory note is still at or above the $5.9B[1] of June 30, 2026: the pool is being built on purpose, not released.

  numeric_check: passed (1 checked: 1 verified, 0 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)

3. Kill if the same line is above the $5.5B[1] of December 31, 2025 in the Q2 2027 10-Q: no sellable surplus is coming out.

  numeric_check: passed (1 checked: 1 verified, 0 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)

4. Kill if Merck cuts non-GAAP gross margin guidance below the about 81.0%[1] set on the Q2 2026 slides and again cites inventory reserves: the pool is being impaired, not released as cash.

  numeric_check: passed (1 checked: 1 verified, 0 derived, 0 assumed)

  [1] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)

## Evidence

Decider: Investors: debt and equity holders who read the 10-Q inventory note and liquidity table

Why it lands: Cash and investments fell from $15,521M[1] to $8,363M[1] and total debt rose from 36.0%[2] to 41.5%[2] of total liabilities and equity in the first half of 2026, while first-half interest expense rose to $1,004M[3] from $618M[3], up 62%[derived: 3]. Investors have a cited reason to want cash out of working capital, and a disclosed product split lets them check that the release is cash, not a write-down.

  numeric_check: passed (7 checked: 6 verified, 1 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 45 "Cash and investments $ 8,363 $ 15,521" (exact)
  [2] Merck 10-Q 2026-06-30, p. 45 "Total debt to total liabilities and equity 41.5 % 36.0 %" (exact)
  [3] Merck 10-Q 2026-06-30, p. 25 "Interest expense 525 305 1,004 618" (exact)

What the evidence can tell: The filings show the pool's size and path ($3.8B[1] at December 2024, $5.5B[2] at December 2025, $5.9B[2] at June 2026), that it is almost entirely raw materials and work in process[3], the 4.30%[4] coupon of the notes the release can retire, and that inventory reserves already moved gross margin guidance from about 82.0%[5] to about 81.0%[5].

  numeric_check: passed (6 checked: 6 verified, 0 derived, 0 assumed)

  [1] Merck 10-K FY2025, p. 105 "these amounts included $ 5.5 billion and $ 3.8 billion, respectively, of inventories not expected to be sold within one year" (exact)
  [2] Merck 10-Q 2026-06-30, p. 19 "these amounts included $ 5.9 billion and $ 5.5 billion, respectively, of inventories not expected to be sold within one year" (exact)
  [3] Merck 10-Q 2026-06-30, p. 19 "Amounts recognized as Other Assets are comprised almost entirely of raw materials and work in process inventories" (exact)
  [4] Merck 10-Q 2026-06-30, p. 19 "$ 1.0 billion of 4.30 % notes due 2028" (exact)
  [5] Merck earnings slides 2026Q2, p. 18 "Gross Margin Rate ~82.0% ~81.0% • Now includes higher inventory reserves" (exact)

What it cannot tell: No indexed page says what products the pool holds, whether part of it is reshoring bridge stock[1] or Keytruda drug substance built ahead of the patent expiry, how much of the 2026 reserve increase relates to it, or whether the 2028 notes can be prepaid at par. Until Merck discloses the split, the release size is unproven and could be zero, and write-downs may be required[2] on whatever is aged.

  numeric_check: no_numbers (0 checked: 0 verified, 0 derived, 0 assumed)

  [1] Merck 10-Q 2026-06-30, p. 32 "delay Section 232 tariffs for three years, enabling the Company to make investments in the U.S. to reshore manufacturing" (exact)
  [2] Merck 10-K FY2025, p. 73 "If future demand for the Company’s products are less favorable than forecasted, inventory write-downs may be required" (exact)

## Promo

No doctor or patient would see material from this move, so there are no pieces, no claims map and no rules check.

## Unresolved after round 2 (two positions, not averaged)

### What the long-dated inventory pool holds, and whether a release arrives as cash or as reserve charges

- CFO/math: No page ties the pool to tariff staging or to reshoring bridge stock; the reshoring reading is an inference too. The release math holds for any slice proven sellable at cost, so diagnose first and size the release on the sellable surplus only.
- Decider/compliance: Management is choosing to build: the pool grew after the tariff delay, which the filing ties to reshoring, and reserves are rising. Investors cannot verify any target until Merck discloses the split in the inventory note, so disclosure must come before any target, and the release must be counted net of reserve charges.

### Severity of the Qlex re-pricing candidate

- CFO/math: Fatal on its own numbers: certain forgone revenue inside the window against a smaller benefit after it, negative through the end of the decade whoever decides. The CFO round-two summary still describes the decider as rating it major.
- Decider/compliance: Rated it major in round one for the wrong-decider and wrong-lever reasons, then conceded fatal in round two once the CFO's net-negative math was in; the two files agree on fatal but give different reasons (math versus decider and lever).

### Whether CMS Part B payment-limit rows may size a decision when cited only by locator

- CFO/math: Machine-data rows cannot be quoted but can be cited by locator and are fit for sizing; the cross-quarter Qlex premium check used them that way.
- Decider/compliance: Did not open the rows beyond their locators and treats the cross-quarter premium only as a reason the re-price is sized to one quarter, not as a quoted fact to size a move on.

### Target segment for any salvage pilot of the Qlex conversion candidate

- CFO/math: Round one: monotherapy and oral-combination practices, where early use clusters. Round two: no segment earns a return inside the window, so any pilot is a post-patent-expiry option, not a funded return.
- Decider/compliance: IV-chemotherapy combination regimens, the segment management says lags; a pilot in monotherapy practices, where management already converts, cannot show causation.

## Rulings

| Candidate | Verdict | Reason |
|---|---|---|
| MRK-m01 | killed | Both lenses ruled it fatal after round two. The decider lens showed the conversion target and its funding are already announced, with an earlier deadline than the move, and the CFO lens conceded that this removes any incremental lift and so any return; the erosion proxy is also confounded by the Medicare Part D redesign. The promo piece failed fair balance and cited the annual report for indications. Confirmed killed, not merely unrefuted; settled by the investor-event adoption slide and the third-quarter call (see cites). Still disagreeing: which segment a salvage pilot should target. |
| MRK-m02 | killed | Both lenses refuted it as major. The CFO lens showed the royalty and upfront comps are voluntary Hypercon platform licenses, not an MDASE settlement, and the country share is invented; the decider lens showed Halozyme is escalating and Merck is winning on validity, so neither side has a reason to deal. Both converged on a contingent, Germany-only option after the appeal, unsized because no page gives German sales or a settlement royalty. Settled by the litigation note and product table in the second-quarter quarterly report (see cites). |
| MRK-m03 | killed | Both lenses ruled it fatal after round two: certain forgone revenue inside the window buys a smaller benefit after it, borrowed from the conversion candidate, and a lower payment limit cuts the add-on of the practice that actually chooses the route. Confirmed killed. Still disagreeing: whether the CMS payment-limit rows cited by locator may size a decision. |
| MRK-m04 | narrowed | Narrowed, not confirmed as stated. The CFO lens flipped to refuted in round two because no page shows the pool is sellable at cost and reserves are already cutting gross margin; the decider lens flipped to not refuted once the debt rate was re-cited to the notes due in the decade's late years and the liquidity table showed cash falling and leverage rising. Both conceded a diagnose-then-release form: split the pool by product and disclose it, release only sellable surplus up to the size of that note tranche, net of reserve charges. Settled by the inventory and debt notes and the liquidity table of the second-quarter quarterly report and the commercial paper note in the annual report (see cites). Still disagreeing: what the pool holds. |
| MRK-m05 | killed | Both lenses refuted it as major and converged: the administrative contest is already Merck's stated course, resolution may take years, a reserved penalty would be a non-cash release, a settlement concedes tax cash the cost never priced, and public reserve disclosure would hand the IRS Merck's own estimate. No new move remains beyond a private audit-committee range with no return claimed. Settled by the tax notes of the annual report and the second-quarter quarterly report (see cites). |
