# Red team v2: which company we pitch (Sat Oct 17)

Scope: AZN, MRK, JNJ, AMGN nugget files (`docs/nuggets/*.md`, `*.jsonl`, `*_ai_caught.jsonl`), the case PDF, the rubric, `out/league.json`, `out/*/labels_table.json` and `docs/red_team_v1.md`. Read-only review.

How I tested: I re-ran `agent.needle.pages.check` on every evidence quote in all four `.jsonl` files (238 quotes). All 238 return `verified`. For the top 3 nuggets per company I opened the cited page in `data/corpus` and recomputed at least one number by hand. I also checked them against the CMS MFP and Part D files in `data/external`.

## 1. Verdict

| Rank | Company | Score (of 30) | One-line reason |
|---|---|---|---|
| 1 | **MRK** | 24.5 | Contractual, dated, two-sided-confirmed needle; official transcripts; Keytruda Qlex vs Opdivo Qvantig is a real label difference that shows up in the numbers; kill signals land inside 6 months |
| 2 | JNJ | 23.5 | Best evidence base (5 official calls through Q3 2026) and best peer column, but its named needle is the CEO's own talking point and pays off in 2029 |
| 3 | AMGN | 20 | Enough rows, but the needle is small ($97M one quarter), transcripts are third-party, and the Q3 2025 call is missing |
| 4 | AZN | 16.5 | Biggest single number, but the baseline year is an outlier, product coverage misses the listed rivals, and the transcripts are third-party, mislabeled and partly unattributed |

**Pick: MRK. Runner-up: JNJ (close).** Biggest risk: a judge calls the Keytruda royalty end "priced in". The 6.5% then 2.5% then zero schedule has been public since the 2017 BMS/Ono settlement, and it sits in plain MD&A text in both companies' 10-Ks. Section 8 covers the defense.

## 2. Top-3 attack, per company

Legend: Real = not a one-off, not mechanical, not double counted. Hidden = not in the starter thread, not asked on calls.

### AZN

| Nugget | Real? | Hidden? | My recompute (doc, page) | Assumptions | Verdict |
|---|---|---|---|---|---|
| 001 US gross-to-net give-back $1,804m | Partly. The 2025 ratio (49.5%) is almost the same as 2023 (49.1%). 2024 (53.3%) is the outlier. Against the 2023 rate, 2025 is $170m *better*, not $1.8bn worse. Part of the 29% jump is the 2025 Part D redesign, which hits every peer. Prior-year accrual adjustments were a $175m release (favorable), so true-ups do not explain it | Yes on calls (grep of 3 third-party transcripts). The GTN table is in the 20-F MD&A, so the data is public | 20-F FY2025 p.34: 23,444 / 47,385 = 49.48%; 21,655 / 40,641 = 53.28%; 17,961 / 36,568 = 49.12%; 47,385 x 53.28% - 23,444 = 1,804. Managed care 13,963 / 10,825 = +29.0%. Confirmed | 20% tax and 1,550m shares are reasonable. Bear "+1 pt from MFN" is labelled | Survives as a row only if framed as "the 2024 improvement fully reversed". The jsonl says the Audit Committee "ordered" a review; AR p.85 says "requested". Fix the verb |
| 003 Calquence MFP $8,600 vs $13,910 per claim | Real. Statutory price, effective Jan 2027 | No. An analyst asked about it on 2025Q3 (unnamed speaker) | CMS MFP file: CALQUENCE 8,600 per 30 days from 01/01/2027; Part D DY24 maleate: $1,701,974,921, 122,356 claims, $13,910/claim. 8,600 / 13,910 = -38.2%; 8,600 / 9,571.07 (Imbruvica 2027) = -10.1%. Confirmed | Units mismatch: the MFP is per 30 days, the CMS figure is per *claim*, and a claim can be a 90-day fill. Net = 80% of gross is plausible for Part D oncology but unsourced | Survives, but Calquence is NOT a listed AZN competitive-set product (Tagrisso, Farxiga, Imfinzi), so it cannot carry the product comparison |
| 002 Receivables are a factoring artifact | Real, but it is a *debunk*: impact $0 | Yes (footnote only) | 20-F FY2025 p.F-29: (10,289 - 2,681) / (8,335 - 667) - 1 = -0.78%. Confirmed | Bear 2% loss on the pool is labelled | Not a findings row (no material impact). Best used as the "tool caught its own false positive" slide |

### MRK

| Nugget | Real? | Hidden? | My recompute | Assumptions | Verdict |
|---|---|---|---|---|---|
| 001 2.5% Keytruda royalty to BMS/Ono ends after Dec 31, 2026 | Real and contractual. It is a one-time *step*, which is the point: it flatters 2027 | Zero "royalt" hits on 4 official calls. But the rate and end date are in Merck's 10-K MD&A (p.54) and the 10-Q (p.34), and the settlement has been public since 2017, so sell-side models likely carry it | MRK 10-K p.53: 2.5% x 31,680 = 792. BMY 10-K p.89: 588 / 0.75 = 784 (within 1%). BMY 10-Q p.10: 308 / 0.75 x 2 = 821. EPS 821 x 0.867 / 2,507 = $0.284. Confirmed | Base uses the H1 2026 run-rate; bull uses 7% growth; both labelled. BMS's figure is "after legal fees", so the gross-up slightly understates | Survives. Strongest needle in the set *if* framed as the net, one-year lift (see section 8) |
| 002 Gardasil: CFO "will very much impact" vs 10-K "not material" | Real language contradiction (a case "language drift" item) | Analyst-asked once (Divan, 2025Q3). The CDC change was national news | 10-Q 2026Q2 p.28: US H1 1,027 vs 1,082 = -5.1%. 10-K: 2,641 x 40% x 50% = 528. Confirmed | 40% adolescent revenue share is undisclosed and drives the whole number. The impact depends on the First Circuit appeal of the Mar 16, 2026 stay. AHIP coverage runs to end-2027 (10-Q p.35), which cushions it | Survives as Medium. Show the contradiction, give the dollar figure as a range |
| 003 Winrevair 22% royalty "replaces" the Keytruda royalty | Real, but it is the same royalty theme as 001 (risk of a double count on the slide). The royalty was already in 2025 cost of sales, so it is not new cost | Yes (0 call hits) | 10-K p.58 and p.132: 22% x 1,443 = 317. 10-Q: H1 1,114 / 615 = 1.81. 1,443 x 1.81 x 22% = 575. Confirmed. BMS books 289 vs 317 implied (gap logged) | Full-year growth = H1 growth is aggressive (launch curves decelerate) | Merge into 001 as the "net" line, or keep as its own row with the 001 overlap stated. Do not count it twice in an EPS bridge |

### JNJ

| Nugget | Real? | Hidden? | My recompute | Assumptions | Verdict |
|---|---|---|---|---|---|
| 001 Genmab DARZALEX royalty, 12% to 20%, ~$2.4B, US roll-off 2029 | Real. The rate is newly disclosed (absent from the FY2024 10-K p.3; confirmed) | **No.** Duato put the 2029 roll-off in Q1 2026 prepared remarks as an upside ("cleanest growth story"). Genmab reports the royalty publicly every quarter. Rung = prepared_remarks | 10-K FY2025 p.3: 2,400 / 14,351 = 16.72%; Q4 2025 schedule: US 8,266 x 16.72% = 1,382; EPS 1,382 x 0.825 / 2,448.6 = $0.47. Confirmed | Bull 15% compounding to 2029 is labelled. Whether FASPRO sales stay royalty-bearing after 2029 is not in the corpus | Survives as a row, weak as Sharpest Needle: it pays in 2029, outside the 24-month Part 2 window, and management already sells it |
| 002 Prior-period US rebate true-ups at 3.0% (2.0% in 2024) | Real disclosure, but the **sign is unknown**. The "rising into 2026" framing is wrong: Q1 2026 is 4.7% vs 4.6% in Q1 2025 (10-Q Q1 p.23), so the quarters are seasonal, not rising | Yes (footnote only, never asked) | 10-K p.51: 3.0% x 36,344 = 1,090; 2.0% x 33,970 = 679; step-up 411. Confirmed | The base case assumes favorable releases; that assumption is unsupported. Bull is $0 | Survives as a question-style Medium row with the LLY peer (<1%). Rewrite the kill signal: quarterly vs annual is not like for like |
| 010 Non-STELARA US erosion $390M per quarter | Real. OPSUMIT generics plus the IMBRUVICA IRA price (effective Jan 2026, so partly starter-thread "Medicare negotiation") | Partly. Wolk called it "not nearly as impactful as STELARA"; no one added it up | Q3 2026 8-K schedule: OPSUMIT 409 to 193, REMICADE 326 to 258, SIMPONI 309 to 269, IMBRUVICA 211 to 145 = -390; STELARA -654; 390 / 654 = 59.6%. Confirmed | 80% contribution margin is labelled. Schedule pages have no printed folio ("p. ?") | Survives, High |

### AMGN

| Nugget | Real? | Hidden? | My recompute | Assumptions | Verdict |
|---|---|---|---|---|---|
| 002 Enbrel Q2 -4% flattered by a 16-pt favorable true-up | Real, but **small**: $97M in one quarter, about 1% of quarterly product sales. Amgen's own bridges do not reconcile: Q1 -18% (-92) plus Q2 +16% (+97) nets to +5, yet the H1 bridge says +6% (+67). The two quarters may describe different estimate pools. The honest H1 figure (-19%) is printed in the same table | Yes (no speaker mentions Enbrel on the Q2 call; third-party transcript) | 10-Q Q2 p.35: 16% x 604 = 96.6; (580 - 97) / 604 = -20.0%. 10-Q Q1 p.36: 18% x 510 = 91.8. Confirmed | The bridge-percent-times-prior-year method is the standard read | Survives, but it is not "most material". It also has a near-term test: the Q3 10-Q comes in early Nov |
| 001 Receivables are gross-to-net, deductions 52% to 54% | Real. Same baseline issue as AZN: 2023 was 53%, so 2024 was the low year. The 54% and 52% are rounded (+/- 0.4B) | Yes (footnote only) | 10-K p.F-6: 9,570 / 6,782 = +41.1%. p.77: 35,148 / 0.46 = 76,409, so 1 pt = 764. Confirmed | Base +0.5 pt is an average of two years: thin | Survives as a row. Pair it with AZN's factoring debunk as the "AI caught" story only if AMGN is the pick |
| 003 2025 net-price decline was all Enbrel; it spread to 5 brands in H1 2026 | Real. Derived arithmetic, not stated anywhere | Yes | 10-K p.61, p.64: 3% x 32,026 = 961. p.66: 36% x 3,316 = 1,194. Confirmed | H2 = H1 annualization is labelled | Survives, Medium |

## 3. How many findings-table rows survive

A row survives if every quote verifies, it is not a one-off or a mechanical artifact, it is outside the starter thread, it has a dollar impact on revenue, operating income or EPS, it is at least Medium confidence, and it is not needs_human.

| Company | Solid rows | Marginal | Cut | Peer column filled on solid rows | Pass (>= 5)? |
|---|---|---|---|---|---|
| MRK | 001, 002, 004, 005, 007, 008, 009 (7) | 003 (merge with 001), 006 (only after the fix in section 9) | 010 (two stacked assumptions) | 3 of 7. 002, 004, 007, 008 say "None checked" | Yes |
| JNJ | 001, 002, 010, 006, 004 ERLEADA, 007 ZYTIGA fold, 003 Part D drift (7) | 008 talc (press-release headline) | 005 Darzalex IRA (needs_human), 009 gov deal (assumption only) | 5 of 7 (best peer column of the four) | Yes |
| AMGN | 002, 001, 003, 006 IRS, 009 biosimilars, 004 Repatha, 007 TAVNEOS, 010 Otezla, 008 profit splits (9) | none | 005 (third-party, needs_human, duplicates 004), 011 (illustrative) | 4 of 9 are "against itself" or internal | Yes |
| AZN | 001, 003 Calquence, 004 Enhertu payables (3) | 005 BMS earn-out (cash only, no EPS effect), 006 MFN (assumption-sized, third-party quotes) | 002 (debunk, $0), 007 tariff (low), 008 China (low), 009 Tagrisso (needs_human) | 2 of 3 | Only with marginal rows |

## 4. Sharpest Needle: most material AND least discussed

| Company | Named needle | Material? | Least discussed? | Holds up under a skeptic? | Score /5 |
|---|---|---|---|---|---|
| MRK | 001 Keytruda royalty ends | $0.82B pretax, 3.9% of pretax, $0.28 EPS, in 2027 | 0 call mentions; plain MD&A text; 2017 settlement public | Yes: reconciles to the counterparty's 10-K within 1% | 4 |
| JNJ | 001 Genmab royalty | $1.4B/yr, but from 2029 | No: the CEO pitched it on the Q1 2026 call | Yes on numbers, but fails "least discussed" | 2.5 |
| AMGN | 002 Enbrel true-up | $97M to $132M one-off | Yes | Bridges do not reconcile (H1 6% vs Q1 + Q2) | 2.5 |
| AZN | 001 US GTN give-back | $1.8B | Yes on calls | Fragile: the 2023 ratio equals 2025, and the Part D redesign is industry-wide | 3 |

JNJ alternative: 010 (second-wave erosion, $1.56B a year, High) is a better JNJ needle than 001. AMGN alternative: 006 IRS ($3.2B gap above the reserve). It is bigger, but the CFO read it in Q1 prepared remarks.

## 5. Product fine print: is there a label difference that shows up in the numbers?

| Company | Listed product and rivals | Label difference | Where it shows in the numbers | Data gaps | Score /5 |
|---|---|---|---|---|---|
| MRK | Keytruda vs Opdivo, Imfinzi, Tecentriq | 21 indications vs 14, 6, 7 (labels_table). Keytruda Qlex (subcutaneous, Alteogen enzyme) vs Opdivo Qvantig (Halozyme listed as a manufacturer on the label) | Part B 2024 spend $5.99B vs $1.93B, $0.84B, $0.68B. Qlex $463M per quarter. $930M Alteogen milestones capitalized. Halozyme German injunction plus "additional royalties" warning (005, 006) | The code's table says Keytruda "protection ends 2031-01-25" (orphan exclusivity) and gives no patents. The 10-K says the compound patent ends Dec 2028, with two 2029 PTA patents. Must be overwritten from the 10-K. Qlex is not a row in labels_table | 4 |
| JNJ | DARZALEX vs Sarclisa; TREMFYA vs Skyrizi, Rinvoq, Wezlana | DARZALEX 7 indications vs 3; FASPRO subcutaneous with its own patents vs Sarclisa IV. TREMFYA q8w vs Skyrizi q12w; Rinvoq has a boxed warning | Part B per claim $9,236 vs $6,356. DARZALEX Part B $2.68B vs $68M. The FASPRO patents are why the royalty ends while the franchise continues (001) | The code's table lists DARZALEX route "intravenous" and "protection ends 2027-11-16", which contradicts the 10-K (2029 US) | 3.5 |
| AMGN | Enbrel vs Skyrizi, Rinvoq, Humira; Repatha vs Praluent, Leqvio, Lipfendra | Enbrel boxed warning and weekly dosing vs Skyrizi none and q12w. Lipfendra oral with a food restriction | Enbrel net price -36%, US 3,288 to 2,199. Repatha net price falling each year (004, 010) | Enbrel "protection ends 2010-11-02" in the code's table is wrong. The Lipfendra label has no page markers. The Gordon quote is from a third-party transcript | 3.5 |
| AZN | Tagrisso vs Rybrevant + Lazcluze | Oral daily vs IV q3w; 5 indications vs 4 | Only 009 (Tagrisso IRA eligibility), which is needs_human and Low. Calquence (003) is off-list | No verified label-to-number tie for a listed product | 2 |

## 6. Part 2 fuel: credible, budgetable move with 6 to 12 month kill signals

| Company | Best move the nuggets support | Budget source | Kill signals inside 6 to 12 months | Score /5 |
|---|---|---|---|---|
| MRK | Use the ~$0.8B 2027 royalty roll-off as a one-year fund to secure Keytruda Qlex: settle or license Halozyme's European rights and push conversion ahead of the Dec 2028 biosimilar window, rather than book it as margin | 001 ($821M base), net of 003 (Winrevair 22%) | Dutch Halozyme decision (due about end Oct 2026). German appeal hearing Nov 19, 2026. Qlex quarterly sales vs the 30% to 40% adoption path. AstraZeneca's Koselugo option (Jan 2027). Gardasil First Circuit ruling | 4 |
| JNJ | Size BD to the combined STELARA plus second-wave gap (~$4.2B annualized), or fund ICOTYDE access | 001 is 2029 cash, outside the window. Needs a current-year source | CMS selected-drug list (early 2027, DARZALEX). First ICOTYDE sales line (2027). Talc 95% participation. Enterprise Business Review Dec 8, 2026 | 3.5 |
| AMGN | Hold a $3B to $7B tax reserve before any debt-funded deal; defend Repatha with DTC pricing | 006 | Q3 2026 Enbrel YoY (10-Q in early Nov). Tax Court decision (2H 2026) | 3 (the move is defensive) |
| AZN | Price new launches for MFN from day one; fund US capex with the ~$0.9B freed BMS earn-out | 005 | Shenzhen trial date. Most other signals (Virginia plant, Oct 2028) fall outside 12 months | 3 |

## 7. Evidence weaknesses

| Company | Transcripts | needs_human rows | Assumption-heavy math | Other |
|---|---|---|---|---|
| MRK | 4 official (2025Q3 to 2026Q2). Q3 2026 call is Oct 29, after the showcase | 0 in the file. ai_caught logs 4 speaker-window misses, which were replaced | 002 (40% cohort), 005 (3% royalty on US sales; the PTAB has found every challenged claim unpatentable in 4 PGRs), 010 (stacked) | Printed folios present. Good |
| JNJ | 5 official LSEG, through Q3 2026 (freshest) | 005 Darzalex IRA | 009 (1% to 3% cost), 004 talc annualization | Sales-schedule pages have no printed folio; code ids are unstable between runs (logged) |
| AMGN | 3 third-party (fool.com); no Q3 2025 call; the LLM-summary lines on fool.com nearly polluted 002 | 005, 011 | 001 base (+0.5 pt), 007 (50% write-down) | Q2 earnings EX-99.1 missing; slides blocked (403) |
| AZN | 3 third-party (allmind.ai). The "2026Q1" file is a duplicate of Q2. 2025Q3 has no speaker names | 009 | 006, 007, 008 (all assumption-sized) | IFRS and USD vs GBP peers. The 20-F never mentions MFN (the detail sits in the AR exhibit) |

## 8. Ranking scorecard and recommendation

| Criterion (each /5) | MRK | JNJ | AMGN | AZN |
|---|---|---|---|---|
| Sharpest Needle | 4 | 2.5 | 2.5 | 3 |
| Rows surviving (>= 5, quality) | 4.5 | 4.5 | 4 | 2.5 |
| Product fine print tie | 4 | 3.5 | 3.5 | 2 |
| Part 2 fuel and kill signals | 4 | 3.5 | 3 | 3 |
| Evidence quality | 4 | 5 | 2.5 | 2 |
| Distance from starter thread | 4 | 4.5 | 4.5 | 4 |
| **Total /30** | **24.5** | **23.5** | **20** | **16.5** |

**Pick MRK.** Its best findings are contractual. They come with dates and reconcile to the counterparty's own filing, which is the "evidence that holds up" the case rewards. It is also the only company where a label difference (Keytruda Qlex's enzyme vs Opdivo Qvantig's licensed Halozyme enzyme) runs straight into dollars: $463M a quarter of Qlex, $930M of milestones, and a live injunction. Part 2 gets a funded move and kill signals that fire within weeks to months, not in 2028.

**Runner-up JNJ.** Switch to JNJ if the team cannot defend the "priced in" attack on the MRK needle. JNJ has the cleanest sourcing and peer column, but its needle must change from 001 to 010.

**Biggest risk of the MRK pick:** "priced in" and "starter thread". Five of Merck's ten nuggets orbit Keytruda, and the royalty schedule has been public since 2017. A judge could say the team restated the Keytruda cliff with a footnote attached. Defense: (a) call grep, 0 hits on 4 calls; (b) the claim is not "the royalty ends". The claim is that 2027 gets a one-time ~$0.8B margin lift, partly refilled by Winrevair's 22% and possibly by Halozyme royalties on Qlex, in the year before the Dec 2028 cliff, so 2027 margin is not a run-rate. Put that sentence in the priced-in line.

## 9. Must-fix before anything reaches a slide (MRK)

| Rank | Hole | Evidence | Case or rubric | Points at stake | Cheapest fix | Owner |
|---|---|---|---|---|---|---|
| 1 | The needle has no priced-in defense | MRK 10-K p.54 states the 2.5% rate and the 2026 end in MD&A; BMY 10-K p.32 | Case: Sharpest Needle "least discussed"; growth limiter plus priced-in call; Innovation | 2 to 3 | Reframe as the net one-year lift ($821M minus Winrevair growth minus possible Qlex royalty) that flatters 2027. State plainly that the schedule is public and that its effect on the 2027 margin is what goes unmentioned | Parker, 30 min |
| 2 | The peer column is empty on 4 of 7 solid rows | MRK.md rows 002, 004, 007, 008 ("None checked") | Case: five-column table complete; Completeness | 2 | Fill from the corpus: BMY non-GAAP definition for 006; GSK 20-F vaccine/ACIP exposure for 002; another shortlist R&D-funding deal for 004; GSK or PFE vaccine royalties for 007; LLY Verzenio or JNJ Erleada (same 2028 IRA list, `JNJ.md` row 6) for 008 | Parker, 1 hr |
| 3 | Product table has wrong exclusivity rows, and Qlex is missing | out/MRK/labels_table.json: Keytruda "protection ends 2031-01-25", patents "None"; MRK 10-K: compound patent Dec 2028, two 2029 PTA patents | Case: one product on all five dimensions; Technical | 2 | Overwrite the patent and exclusivity rows from the 10-K patent table. Add a Keytruda Qlex vs Opdivo Qvantig column from the drug packs. Fix the detector so biologic "protection" is not orphan exclusivity | Aidan (code), Parker (slide), 1 hr |
| 4 | 006 implies the $1.0B GAAP amortization rise is the Qlex cost | 10-K p.105: product rights 29,988 to 42,038, driven by Ohtuvayre $11.8B; Qlex share is $176M a year | Math holds; Responsible AI | 1 | Headline $176M for Qlex. Attribute the rest to Verona/Ohtuvayre | Parker, 15 min |
| 5 | 005 royalty base is US sales while the injunction is European | 10-Q p.22: German injunction; Dutch counterclaim; NJ suit on 15 patents; PTAB found every challenged claim unpatentable in 4 PGRs; Halozyme consented to UK revocation | Math holds | 1 | Show two bases (Europe only vs US plus Europe) and cite the PTAB wins in the bull case. Add the Dutch decision (about end Oct 2026) as the first kill signal | Parker, 20 min |
| 6 | 003 and 001 double count in any EPS bridge | MRK.md says "pair it with 003" | Case: impact math | 1 | One net royalty line in the bridge; 003 as a sub-bullet | Parker, 10 min |

## 10. Do NOT put on a slide

| Item | Why |
|---|---|
| `out/league.json` sharpest_needle strings (all ten), including AZN "receivables +14.7 pts" and MRK "Davis deflected..." | Mechanical or truncated. AZN's is disproved by AZN-002. MRK's is a cut-off question string. League rank is not a selector (red_team_v1 #1) |
| AZN-002 shown as a red flag | It is a factoring artifact with $0 impact. Usable only as the "AI caught" example |
| AZN-001 "Audit Committee ordered" | The source (AR p.85) says "requested a review". Do not imply wrongdoing |
| AZN-009 Tagrisso IRA $295m | needs_human; the eligibility rule is unconfirmed |
| AZN-007 tariff $586m, AZN-008 China bear $333m | Every input is assumed. The indictment fact can be stated without the number |
| Any quote from `AZN/transcripts/2026Q1_transcript.md` cited as Q1, or a named speaker from AZN 2025Q3 | The file is a Q2 duplicate, and 2025Q3 has no speaker names (GAPS.txt) |
| MRK-010 MFN $1,050M | Two stacked assumptions ($70B x 50% x 30% x 10%); Low |
| MRK-006 "$1.0B cost of the Qlex switch" | Misattribution: most of it is Ohtuvayre amortization |
| JNJ-008 DARZALEX IRA Part B 2029 ($1,009M) | needs_human; the eligibility rule comes from outside the corpus |
| JNJ-009 government deal $727M | Pure assumption; the terms are confidential |
| JNJ-002 kill signal "true-ups under 2% next 10-Q" and "rising to 4.7%" | Q1 is seasonally high (4.6% in Q1 2025), so a quarterly vs annual comparison is invalid |
| "Genmab royalty disclosed only after the SEC asked" (red_team_v1 #1) and "exec pay excludes eroding products" | Unsupported: no CORRESP or DEF 14A in the corpus (JNJ_ai_caught) |
| AMGN-005 Gordon contracting dodge, AMGN-011 tariff $513M | Third-party transcript, needs_human, duplicate or illustrative |
| Code labels_table rows: Enbrel "protection ends 2010-11-02", DARZALEX "intravenous" and "2027-11-16", Keytruda "2031-01-25" | Wrong against the 10-K patent disclosures |
| Anything quoting fool.com "takeaways" lines | LLM-written summary text, not the call (AMGN_ai_caught) |

## 11. Projected rubric effect of the pick (Part 1 content only)

| Category | MRK today | After fixes 1 to 5 |
|---|---|---|
| Innovation | 3 | 3 to 4 (the net-lift framing is a non-obvious read) |
| Completeness | 2 | 3 (peer column and product table complete) |
| Use of AI and Responsible | 3 | 4 (AI-caught misattribution in 006 and AZN factoring debunk shown) |
| Impact | 2 | 3 (funded Qlex move with dated kill signals) |
| Presentation | 2 | 3 to 4 (one sentence: "Merck's 2027 margin gets a one-year royalty gift right before the cliff, and the Keytruda Qlex defense is already under injunction") |
