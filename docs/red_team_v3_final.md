# Red team v3: final needle audit, all 10 companies (Sat Oct 17, 2026)

Scope: `docs/nuggets/<T>.md` and `<T>.jsonl` for MRK, BMY, PFE, LLY, NVO, ABBV, JNJ, AZN, AMGN, GILD, against the case PDF (Part 1 and Part 2 minimums, appendix starter threads), the rubric, `docs/red_team_v2_company_pick.md` and the 10 round-1 checks in `.claude/agents/nugget-miner.md`. Quotes were not re-verified (all 828 already pass the page verifier). Effort went into substance: I recomputed each needle headline from the cited page or data row, and opened the corpus where a claim was contested (MRK 10-K patent table and 10-Q litigation note, Orange Book `patent.txt` for NDA 208558, AMGN 10-Q tax note, NVO AR useful lives, LLY 10-K and 10-Q Jardiance note, CMS selected-drug file for Biktarvy, transcript greps for MRK, BMY, NVO, LLY, GILD, ABBV). Scores use the v2 scale (six criteria, 5 points each, 30 total) so they compare with v2.

Check codes used below: **B** baseline years, **W** inside 24 months, **S** not already said on a call, **P** priced-in defense, **R** peer column filled, **U** units and scope, **L** no label-table dates, **T** transcript trust, **N** no unsourced claims, **A** stacked assumptions. **$** means the impact does not reach revenue, operating income or EPS.

## (a) Summary table

| Company | Best needle (one sentence) | Headline impact, recomputed | Checks failed (best needle) | Score /30 | Slide-ready rows | Product comparison with label diff tied to a number |
|---|---|---|---|---|---|---|
| MRK | 001: the 2.5% Keytruda royalty to BMS and Ono ends Dec 31, 2026, so 2027 gets a one-year margin step right before the Dec 2028 cliff, and nobody has said so on a call | BMY 10-Q Q2 p.10: $308M H1 / 0.75 x 2 = $821M gross pretax, x 0.867 / 2,507 = $0.28 EPS; cross-check 2.5% x $31,680M = $792M. Net 2027: $541M to $786M ($0.19 to $0.27) | P (public since 2017; defense written but must be on the slide). Twin risk: BMY carries the same contract | **25.5** | 10 | Yes (Keytruda Qlex 2043 vs Opdivo Qvantig 2028 protection; Part B spend; $463M a quarter Qlex) |
| JNJ | 010: four "other" US products went from flat to -$390M a quarter in Q3 2026, 60% of STELARA's drop, and cross STELARA's remaining decline by Q1 2027 | $390M x 4 = $1,560M revenue, x 80% x 0.825 / 2,448.6 = $0.42. Ex-IMBRUVICA (an IRA price, starter-thread force): $324M x 4 = $1,296M, $0.35 | S partial (Wolk: "not nearly as impactful as STELARA"); P (generic dates public; "patent cliffs are priced in" applies directly) | **24.5** | 8 | Yes (DARZALEX FASPRO SC vs Sarclisa IV; Part B $9,236 vs $6,356 per claim) |
| PFE | 001: Eliquis US +$466M in H1 2026 is a rebate windfall from BMS's list-price cut that ends with April 2028 generics | (3,087 - 2,621) x 2 = $932M, x 0.873 / 5,713 = $0.14; bull (half price) $0.07 | S partial (Schott asked; CFO would not split it); P (BMS guide and cut are public); twin with BMY-003 | **23.5** | 8 | Yes (Ibrance metastatic-only vs Verzenio and Kisqali adjuvant; Part D claims -20% vs +215% and +394%) |
| BMY | 001: the same royalty from the receiving side: $0.67B of other income disappears in 2027, unmentioned on four calls | ($308M + $26M) x 2 = $668M, x 0.82 / 2,048 = $0.27, 3.9% of the $6.875 guide midpoint | P; T (fool.com only); sits in OI&E, below operating income (EPS only); twin with MRK-001 | **22** | 7 | Yes (Qvantig has no disclosed protection past 2028, cannot be used with Yervoy; $2.1B of US nivolumab moving to it) |
| AMGN | 006, restated: the IRS Puerto Rico claim ($7.6B of tax and penalties plus interest) exceeds Amgen's entire tax reserve for all open years ($6.3B), with a decision due late 2026 or early 2027 | 3.6 + 5.1 + 2.0 - 0.9 - 2.2 = $7.6B plus interest vs 4.4 UTB + 1.9 accrued interest and penalties = $6.3B: **at least $1.3B unreserved** ($2.39 GAAP EPS, no tax shield), before claim interest and before 2016 to 2018 | S partial (CFO in Q1 prepared remarks); P (a reserve below the claim is normal GAAP measurement); one-off binary tax item; T | **20.5** | 9 | Yes, thin (Repatha vs oral Lipfendra with food restriction; label has no page markers) |
| NVO | 001: 61% of H1 2026 FCF was a growing US rebate accrual on falling sales, and the Jan 2027 WAC cut forces it to unwind | 140,201 - (133,349 - 26,760) = DKK 33,612m = 60.8% of DKK 55,297m FCF; guide implies H2 FCF of DKK -10.3bn to -0.3bn | **$** (cash only, no EPS); T (allmind.ai) | **20.5** | 9 | Partial (Wegovy pill DKK 1,083 vs injectable DKK 2,391 per script; formulation, not a label restriction) |
| LLY | 002: Jardiance revenue has carried a rising one-off every year (9%, 17%, 21%) and the up-to-$910M of 2026 milestones has no 2027 successor in the filings | 10-K p.66: up to $910M "in 2026", $500M booked H1 (10-Q p.12). 2027 step-down up to $910M, x 0.802 / 899.3 = $0.81 (3.5% of pretax) | S partial (CFO named the $250M milestone in Q2 prepared remarks); T | **20** | 6 | Partial (semaglutide $274 MFP vs Mounjaro Part D at $1,241 per claim: a price gap, not a label gap) |
| ABBV | 001, reframed: the Skyrizi royalty bypasses adjusted EPS, and since the Q2 2026 10-Q it extends to combination assets with payments to 2044 | $1,784M x 2 = $3,568M; / 1,773M = $2.01 pretax per share, $1.65 if tax-effected at 18%: 11.9% to 14.5% of the $13.86 midpoint | **S fails on size** (CFO: "roughly $3.5 billion of SKYRIZI royalty payments", Q4 2025 call); U (pretax per share set against after-tax EPS); a level, not a change | **19.5** | 6 | Yes, illustrative (Rinvoq TNF-failure step and boxed warning vs Skyrizi none; 7.7 pt growth gap, not causal) |
| GILD | 001: Biktarvy ($11.5B US) takes a Medicare set price Jan 1, 2028, eight years before the 2036 LOE management cites, and Gilead widened the spillover risk to "potentially other segments" | Part D gross $3,456M x (1 - 40.8%) = $2,046M x 25% = $511M, x 0.807 / 1,255 = $0.33 | P (selection public since CMS file of Jan 27, 2026, and already a row in Aidan's model); A (two assumptions, MFP unpublished); T | **19** | 6 | Yes (Yeztugo no boxed warning, q6m vs Apretude boxed, q2m; $223M vs about $180M US) |
| AZN | 010 (least bad): chargebacks rose every year, 7.5% to 10.8% of US gross, while AZN loses its 22-state 340B fight | 47,385 x (10.79% - 7.48%) = $1,568M above the 2022 rate; forward 1.10 pt x 47,385 = $521M, $0.27 | U and N (340B link inferred; mix toward hospital oncology is an equal explanation); R contradicts it (BMS rose 3.6 pts vs AZN 2.2 pts on the same basis, 2023 to 2025); T | **17.5** | 5 (one is cash-only) | Partial (Tagrisso vs Rybrevant + Lazcluze: VTE 36% and 4 months of anticoagulation; Lazcluze 183 vs Tagrisso 12,370 Part D beneficiaries; measured erosion $0) |

## (b) Per-company notes

### MRK (pick)
- **Needle 001 holds.** My recompute matches v2: BMS's H1 2026 Keytruda royalty line is $308M (10-Q p.10, Q2 $149M vs $132M, so still growing), which grosses to $821M at BMS's 75% share; 2.5% x $31,680M = $792M. Zero "royalt" hits on Merck's four calls. The net 2027 line ($541M to $786M) is honest and avoids the 003 double count. Impact reaches cost of sales, so operating income and EPS: strongest impact type in the set.
- **Runner-up 012 (Lynparza from Sept 2027): partly refuted as written.** What the corpus says: the MRK 10-K patent table lists Lynparza US "2027" with footnote (7), "Eligible for six months pediatric market exclusivity" (10-K p.14). The 10-Q (p.22) says no filer challenges the compound patent, so "the earliest date the FDA can approve any of the currently pending generic applications is September 2027". The Orange Book (NDA 208558) shows that compound patent 7,449,464 expires Sep 8, 2027. But the same listing also has drug-product patents to Oct 7, 2029 (11,633,396 and others) and Dec 31, 2029 (8,475,842), plus method patents to 2031 and 2041. Those are the patents in the New Jersey suits. The trial wording moved from "expected in 2026" (10-K) to "awaiting a trial date" (10-Q Q2), and Cipla filed a second Paragraph IV in June 2026. The correct sentence: "Generics can be approved from September 2027 at the earliest. Entry then depends on formulation patents running to late 2029 that are in litigation with no trial date, and a pediatric grant would push the earliest date to March 2028." The 80% first-year erosion rests on a date that is a floor, not a forecast. That is three stacked conditions (date, at-risk launch, erosion), so it fails A. Keep it as a Medium-Low row. It must not appear on the needle slide as "2028 starts taking it back".
- **MRK vs BMY on one contract: it helps MRK, if framed right.** The two-sided reconciliation (Merck's 2.5% x sales vs BMS's 75% share, within 1%) is the best "evidence that holds up" item in the whole set. A judge who says "BMS has the same needle" is right on the fact and wrong on the finding. For BMS it is a $0.67B other-income loss below operating income, and it is dwarfed by the $1.5B to $2.0B Eliquis Europe step that BMS already talks about. For Merck it is a cost-of-sales gift that lands in the last full year before the Keytruda cliff, so 2027 is a peak, not a run-rate. A two-sided slide is the strongest *evidence* framing but not the strongest *headline*. Headline: "Merck's 2027 margin carries a one-year royalty gift of $0.5B to $0.8B net, which the Dec 2028 cliff takes back." Put the BMS reconciliation in a corner box as proof, and use BMY-004 (Qvantig gets no protection past 2028 vs Merck's 2043 claim for Qlex) in the product comparison.
- Other rows: 002 Gardasil (40% cohort assumption) and 005 Halozyme Europe (3% royalty assumed) stay Medium. 006 is correctly re-attributed to Ohtuvayre. 010 stays off slides. `out/MRK/labels_table.json` still carries Keytruda "2031-01-25" (2 hits) and has no Qlex row: not fixed since v2.
- Score: Needle 4, Rows 5, Product 4.5, Part 2 4, Evidence 4, Distance 4 = **25.5** (v2 24.5; +0.5 rows for filled peers, +0.5 product from BMY-004).

### JNJ (runner-up)
- **Needle 010 is real and better than v2's 001.** Every input comes from a schedule. It uses one forward assumption and contradicts management's own framing. Weak points: (1) it is loss-of-exclusivity erosion of known generics and biosimilars, and the case says patent cliffs are priced in. The non-obvious part is only the aggregation and the Q1 2027 crossover. (2) $66M a quarter of it is IMBRUVICA's IRA price, a starter-thread force; show the $324M ex-IMBRUVICA figure too. (3) Wolk spoke to it qualitatively.
- Runner-up 001 (Genmab royalty) remains context: the CEO pitched it and it lands in 2029.
- Best evidence base (official LSEG transcripts through Q3 2026). The peer column is the strongest of the ten.
- Score: Needle 3.5, Rows 4.5, Product 3.5, Part 2 4, Evidence 5, Distance 4 = **24.5** (v2 23.5).

### PFE (new to the shortlist)
- **Needle 001**: arithmetic confirmed (10-Q p.38: US $3,087M vs $2,621M). Pfizer's line is alliance profit share, so near-full drop-through is plausible. Holes: Chris Schott asked about it on the Q2 call, so S is partial. The cause sits in BMS's 10-Q. "Higher demand globally" is in the same Pfizer sentence, so the price share is unknown (bull case at half). It also ends at an Eliquis LOE that is BMS's starter thread.
- **Runner-up 002 (Vyndaqel share 82% to 51%) has a scope flaw.** The denominator includes Amvuttra's US polyneuropathy sales, a market tafamidis does not serve in the US, so the share understates Vyndaqel's ATTR-CM position. The trend is real; restate as "US Vyndaqel flat while Amvuttra and Attruby added $1.25B" and drop the share percentages, or split Amvuttra by indication if Alnylam discloses it.
- Strong product comparison: case-listed Ibrance vs Verzenio and Kisqali (adjuvant label gap shows in Part D claims), plus the Vyndaqel family vs Attruby and Amvuttra. Official transcripts.
- Score: Needle 3, Rows 4, Product 4.5, Part 2 3.5, Evidence 4.5, Distance 4 = **23.5**.

### BMY
- Needle 001 equals MRK-001 from the receiving side. My arithmetic matches: 308 + 26 = 334 x 2 = $668M, $0.27. It is income in OI&E, so it reaches EPS but not operating income. BMS 2025Q3 and Q4 calls each mention royalties only in OI&E guidance (diabetes and general), never Keytruda: S passes.
- Runner-up 002 (Hengrui $600M IPRD outside guidance) is a recurring kind of charge that analysts adjust for. 003 (Eliquis rebate reset) is the mirror of PFE-001 and was asked twice on calls.
- Only 7 rows, and the transcripts are fool.com. Product comparison is good (004).
- Score: Needle 3.5, Rows 4, Product 4, Part 2 3.5, Evidence 3, Distance 4 = **22**.

### AMGN
- **Honest headline.** The file compares the $7.6B claim (which includes $2.0B of penalties and excludes interest) with $4.4B of gross UTB (which excludes interest and penalties). The two sides do not use the same basis. Amgen also reserves $1.9B of accrued interest and penalties (10-K p.F-25), so total tax reserves are $6.3B for every open year and jurisdiction. The defensible line: "$7.6B claimed for 2010 to 2015 alone, plus 10 to 16 years of interest, against $6.3B reserved for all years: at least $1.3B unreserved before any claim interest, and the 2016 to 2018 NOPA is on top." Show $3.2B only as the bear (with the method stated) and $0 as the bull.
- Two more holes: a GAAP reserve below the IRS ask is normal (the more-likely-than-not measurement), so "the claim exceeds the reserve" alone is not a red flag. The UTB not growing for three NOPAs is the sharper fact. It is also a one-off binary tax item, which is exactly why MRK's own IRS NOPAs were rejected as context. Amgen's case at least has a decision date, so it stays the needle, but at 3 of 5.
- Runner-up 002 (Enbrel true-up) is correctly demoted. 001 (deductions 50.6% to 54.4% over four years) is the best High row.
- Score: Needle 3, Rows 4, Product 3.5, Part 2 3, Evidence 2.5, Distance 4.5 = **20.5** (v2 20).

### NVO
- **Pick 001 over 003.** 001 is the only zero-assumption number: DKK 33,612m of rebate accrual build = 60.8% of H1 FCF. Its test comes on Nov 5 (Q3 balance sheet). It is cash-only, so in the findings table its Impact cell must say "DKK 0 EPS; DKK 31 to 34bn of FCF". Name 002 (prior-year releases) as the P&L route if the accrual proves too high.
- 003 (unbuilt plants) is better than the file says on one point. The AR gives the useful-life ranges (buildings 10 to 50 years, plant and machinery 5 to 25 years), so the 20-year assumption is bounded by a cited policy, not invented. Cite it. What is still unknown is when the DKK 130.6bn comes into service. It stays the P&L runner-up.
- 002 fails S: the CFO named the DKK 2bn true-up on the Q2 call. Allmind.ai transcripts, only 3 distinct calls.
- Score: Needle 3, Rows 4, Product 3.5, Part 2 3.5, Evidence 2.5, Distance 4 = **20.5**.

### LLY
- **001 is a sensitivity, not a forecast:** the $100 per claim is our choice, so the "headline" is a number we picked. It also leans on a third-party transcript quote ("small proportion") and on the semaglutide MFP, which is NVO's starter thread. Keep it as the product-comparison tie (Mounjaro vs semaglutide).
- **Switch the needle to 002.** It is audited and contractual. The 10-K says "up to $910 million ... in 2026" and the 10-Q shows $500M booked, $410M left. It has a three-year baseline and lands in 2027 with one assumption (no new amendment). Limits: smaller ($0.81 at most), the CFO named the $250M Q2 milestone in prepared remarks, and Lilly could refill it, as it did with amendments in 2024 and 2025.
- Score: Needle 3, Rows 3.5, Product 3.5, Part 2 3.5, Evidence 2.5, Distance 4 = **20**.

### ABBV
- **001 fails S on size.** CFO Reents: "we expect to generate free cash flow of $18.5 billion in 2026, which includes roughly $3.5 billion of SKYRIZI royalty payments" (Q4 2025 call), and "nearly $2.2 billion" for 9M 2025 (Q3 2025 call). The $3.6B headline restates his number. What is new and unsaid: (a) it bypasses adjusted EPS and margins; (b) the Q2 2026 10-Q extends it to combination assets, with payments to 2044. Lead with (b). Unit fix: $2.01 is pretax per share against an after-tax EPS guide. Show $1.65 to $2.01 and say tax treatment is unknown.
- Runner-up 004 (government rebates +34%, GTN 56.0%, 56.0%, 56.8%) passes B but its cause (Part D redesign) is inferred and industry-wide.
- Score: Needle 2.5, Rows 3.5, Product 3.5, Part 2 3, Evidence 3, Distance 4 = **19.5**.

### GILD
- **001 stays the best GILD row, as a spillover finding, not a selection finding.** The CMS file confirms selection (IPAY 2028, effective 01/01/2028, added 01/27/2026; MFP blank). The transcript grep finds zero substantive IRA or negotiation hits (every "IRA" hit in the fool.com files is site navigation). Since the selection is public and Aidan's model already has the row, the slide must claim only what is new: the "potentially other segments" wording (10-Q Q2 p.41), the 2036 LOE vs 2028 price framing gap, and the ENBREL 340B-mix precedent. With two assumptions and no published MFP, confidence is Medium at best. CMS publishes the price around Nov 30, 2026, which could sink or confirm it during judging season.
- Runner-up 002 (ISL/LEN 50/50 with Merck) depends on an unlaunched product. 004 (Trodelvy $568M inventory on an unapproved process) has base $0.
- Score: Needle 3, Rows 3.5, Product 3.5, Part 2 3.5, Evidence 2.5, Distance 3 = **19**.

### AZN
- **010's own peer column argues against it.** On the same global basis, BMS charge-backs rose 12.4% to 16.0% (+3.6 pts, 2023 to 2025) while AZN rose 9.6% to 11.8% (+2.2 pts). So AZN's creep is *below* the peer's. Chargebacks also carry VA, DoD and hospital contract pricing. The 2025 mix shift toward hospital-administered oncology (Imfinzi US +35%, Enhertu) explains the line as well as 340B does. The 340B link is an inference (N). The forward $521M assumes the trend continues (A).
- Runner-up 011 (Tagrisso vs Rybrevant + Lazcluze) is the only case-product comparison but shows $0 measured erosion. 005 is cash-only. 003 Calquence is off-list, analyst-asked, and carries a per-claim vs per-30-day units issue.
- Score: Needle 2.5, Rows 3, Product 3, Part 2 3, Evidence 2, Distance 4 = **17.5** (v2 16.5).

## (c) Ranking, pick, runner-up, risk

| Rank | Company | Score /30 | v2 score |
|---|---|---|---|
| 1 | MRK | 25.5 | 24.5 |
| 2 | JNJ | 24.5 | 23.5 |
| 3 | PFE | 23.5 | not scored |
| 4 | BMY | 22 | not scored |
| 5 (tie) | AMGN | 20.5 | 20 |
| 5 (tie) | NVO | 20.5 | not scored |
| 7 | LLY | 20 | not scored |
| 8 | ABBV | 19.5 | not scored |
| 9 | GILD | 19 | not scored |
| 10 | AZN | 17.5 | 16.5 |

**Pick: MRK. Runner-up: JNJ.**

Why MRK: its needle is contractual and dated, it lands inside the window, it is absent from all four calls, and it reaches operating income through cost of sales. It is also the only needle in the set confirmed to within 1% from the counterparty's own filing. MRK has the most slide-ready rows (10) with peers filled. Its product comparison now has a two-company label and protection contrast (Qlex 2043 vs Qvantig 2028, plus the Yervoy bar on Qvantig) tied to dollars ($463M a quarter of Qlex, $2.1B of nivolumab moving). JNJ is one point behind: best sourcing, but its needle is loss-of-exclusivity erosion, which the case calls priced in.

**Single biggest risk of the pick:** a judge says "the royalty end is public since 2017 and BMS has the same finding, so this is a footnote restatement, not a needle". **Mitigation:** (1) headline the Merck-only consequence (2027 is a margin peak, net $0.54B to $0.79B, before the Dec 2028 cliff), not the royalty end; (2) state the public schedule up front, then show the 0-hit grep on both companies' calls and the 1% reconciliation as the proof box; (3) answer the BMS point in one line: for BMS it is an other-income loss smaller than the Eliquis Europe step it already guides, while for Merck it inflates the base year that every 2028 cliff model starts from.

**Did round 2 change the v2 recommendation?** No. Both finalists gained about a point. JNJ gained from swapping its needle from the CEO-pitched 2029 royalty to the second-wave erosion. MRK gained from filling four empty peer cells and from BMY-004's evidence for the product comparison. The new Lynparza row (012) adds a row but overclaims its date, which cost about half a point it would otherwise have added. The gap stays one point. PFE, which v2 did not score, enters at #3 on the strength of its product comparison and official transcripts. Its needle is weaker than MRK's because an analyst raised it and its cause sits in BMS's filing.

**Top 3 must-fix items for MRK before slides:**
1. Restate MRK-012: "earliest FDA approval Sept 2027 (compound patent 7,449,464, Sep 8, 2027); entry then depends on formulation patents to Oct and Dec 2029 in litigation with no trial date; six-month pediatric eligibility could move it to March 2028 (10-K p.14 footnote 7)". Drop "2028 starts taking it back" from the needle line, or make it "can start taking it back". Parker, 20 min.
2. Needle slide framing: headline the net 2027 peak, add the priced-in sentence, add a proof box with the BMS reconciliation, and give the one-line BMS-twin answer. The product slide uses BMY-004 (Qvantig 2028 vs Qlex 2043). Parker, 30 min.
3. Fix `out/MRK/labels_table.json`. It still shows Keytruda "protection ends 2031-01-25" and has no Qlex row. Overwrite it from the 10-K patent table (Keytruda US 2028, Qlex 2043; EU 2031) and the Purple Book. Patch the detector so orphan exclusivity is not read as biologic protection. Aidan (code) and Parker (slide), 1 hr.

## (d) Do not use

| Item | Why |
|---|---|
| MRK-012 "faces US generics from Sept 2027" as a certain date, and "2028 starts taking it back" on the needle slide | Sept 2027 is the earliest approval date; formulation patents run to late 2029 and are in litigation with no trial date; pediatric exclusivity eligibility (10-K p.14) |
| MRK-010 $1,050M MFN figure | Three stacked assumptions; illustrative only |
| Keytruda "2031-01-25", Enbrel "2010-11-02", DARZALEX "2027-11-16" and "intravenous" from `out/*/labels_table.json` | Orphan exclusivity mixed with patent expiry; still uncorrected for MRK |
| AMGN-006 "$7.6B vs $4.4B" as the headline gap | It compares a claim that includes penalties with a reserve that excludes interest and penalties; use $7.6B plus interest vs $6.3B (floor $1.3B) |
| ABBV-001 "$3.6B royalty nobody discusses" | The CFO stated "roughly $3.5 billion" on the Q4 2025 call; $2.01 is pretax per share against after-tax EPS |
| AZN-010 "AZN-specific 340B leakage" | BMS's same-basis creep is larger (+3.6 vs +2.2 pts); the 340B link is inferred; mix explains it equally |
| PFE-002 "Pfizer's US TTR share 82% to 51%" | Denominator includes Amvuttra polyneuropathy sales, a market tafamidis does not serve in the US |
| LLY-001 "$511M" as a forecast | We chose the $100 per claim concession; show it as a per-$100 sensitivity only |
| GILD-001 "Biktarvy selection" as a hidden finding | Public since the Jan 27, 2026 CMS file and already in Aidan's model; claim only the spillover wording and the 2036 vs 2028 gap |
| NVO-001 with an EPS figure, or its 2027 DKK 49bn "kicker" | Cash-only; the 2027 leg rests on three assumptions |
| NVO-002 as "not discussed" | The CFO named the DKK 2bn true-up on the Q2 2026 call |
| Any AZN 2026Q1 transcript quote, AZN 2025Q3 named speaker, fool.com TAKEAWAYS line, or GILD 2025Q3 quote | Known bad files (README, GAPS) |
| JNJ-005 $1,009M, JNJ-009 $727M, AMGN-005, AMGN-011, AZN-006, AZN-009 | needs_human or pure assumption; already flagged not slide-ready |
| "Genmab royalty disclosed only after the SEC asked", "exec pay excludes eroding products" | Unsupported: no CORRESP or DEF 14A in the corpus |
| MRK-001 and MRK-003, or MRK-001 and BMY-001, as separate lines in one EPS bridge | Same contract or same royalty theme; one net line only |
