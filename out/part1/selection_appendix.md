# Selection appendix: blind pick vs league v3 vs Parker's red team

Written after selection.md was sealed (sha256 903fc656fa7a1d1b2bdf303d8d8f9321d5f1f7b741f6b751c4cdf4f9c40c8fa7, sealed 2026-10-18T04:12:05Z). selection.md was not edited after sealing.

Sources compared:
- Blind: out/part1/selection.md (this run), built only from out/part1/_blind/<T>/synthesis.json and reader_summary.md plus the case PDF.
- League: out/league_v3.md (formula ranking, L = top-5 S x min(1, N_eff/3)).
- Red team: docs/nuggets/best_needle.json, which records the per-company best needle and the /30 scores from Parker's docs/red_team_v3_final.md. No docs/red_team*.md file exists on disk in the quant-model worktree; I read docs/red_team_v3_final.md read-only through `git show b908519f:docs/red_team_v3_final.md` (the commit best_needle.json and docs/nuggets/NOTE.md name) to get Parker's stated pick and reasons.

## Top 3 side by side

| Place | Blind (this run) | League v3 | Red team v3 (Parker) |
|---|---|---|---|
| 1 | AMGN | JNJ (1.5399) | MRK (25.5/30, "pick") |
| 2 | MRK | AMGN (1.2000) | JNJ (24.5) |
| 3 | PFE | ABBV (0.8769) | PFE (23.5) |
| Where the others put the blind picks | | AMGN 2, MRK 5, PFE 7 | MRK 1, PFE 3, AMGN 5 (tied with NVO, 20.5) |

## Where they agree

- **No single company is top 3 in all three, but four companies are top 3 in two of the three:** AMGN (blind, league), MRK (blind, red team), PFE (blind, red team), JNJ (league, red team). The blind top 3 overlaps the red team on two names and the league on one.
- **MRK is Parker's pick and the blind number 2.** Both treat Merck as a company with several real, filing-sourced rows and good transcripts (red team: official transcripts; blind: four grade-A calls). The league ranks it 5th only because its scored rows (Blackstone R&D funding, gross margin) are small on the formula.
- **PFE is 3rd in both the blind run and the red team,** and both lean on the product leg: the red team scores Pfizer's product comparison 4.5/5, the blind run picks Pfizer over Novo on the Vyndaqel vs Attruby and Amvuttra tie.
- **ABBV and BMY needles are the same in all three:** the Skyrizi royalty extending to combination assets with payments to 2044, and the end of the Keytruda/Tecentriq royalties on December 31, 2026. All three treat both companies as essentially one-item names.
- **AZN is at or near the bottom everywhere** (league 10th, red team 10th, blind eliminated), and all three land on the chargeback line as its best item; the red team adds that BMS's chargebacks rose faster, and the blind BMY-c01 ruling shows the same BMS charge-back rise.
- **The league's JNJ top finding is obvious by both other methods.** The league's #1 row is the 2029 Genmab/DARZALEX royalty and IRA timing; the blind synthesis killed the Genmab royalty (JNJ-c07) as material but obvious, and the red team calls it "context: the CEO pitched it".

## Where they differ, and why

- **AMGN: blind 1st, league 2nd, red team 5th.** The difference is which needle is used. The league and red team both lead with the IRS Puerto Rico claim against the $6.3B reserve. The blind skeptics killed that item (AMGN-c05) as material but obvious, because the reserve adequacy and the audit method were discussed on the 2026Q1 call; the red team itself marks it "S partial", calls it "a one-off binary tax item", and scores Amgen's evidence 2.5/5 partly because the original headline compared different bases. The blind run instead leads with TAVNEOS (AMGN-c06, the league's own #2 Amgen row at S 1.418) and the deduction-rate accrual (AMGN-c02, which the red team calls Amgen's "best High row"). So the three methods agree on Amgen's raw material and disagree only on the headline; with TAVNEOS as the needle, the red team's main objection to Amgen falls away. Reason the blind run ranks Amgen first: it is the only company with two survivors graded high materiality, low obviousness, high confidence after two skeptic rounds.
- **MRK: same company, different needle.** Parker's needle is the 2.5% Keytruda royalty to BMS and Ono ending December 31, 2026 (a cost-of-sales gain in 2027). The blind MRK reader never generated that candidate from Merck's side; it appeared only on the BMS side (BMY-c03, narrowed, medium obviousness, with the risk that a strict judge reads it as an exclusivity loss). The blind needle is the IRS transition-tax NOPA (MRK-c03), which the red team mentions only as having been "rejected as context" because it is a one-off binary tax item. These are not in conflict: a Merck table could carry the royalty step (red team), the NOPA and the long-dated inventory pool (blind), and the two narrowed blind rows, which is a deeper honest row set than either source alone shows. The disagreement to settle is only which one is the Sharpest Needle; the red team's royalty reaches operating income and was recomputed two-sided, while the blind NOPA is unmentioned anywhere but is a ceiling whose overlap with the reserve is undisclosed.
- **PFE: same rank as the red team, different needle.** Parker's needle is the Eliquis U.S. +$466M H1 2026 rebate windfall from BMS's list-price cut; that candidate is not in the blind Pfizer set. The blind needle (PFE-c01, Vyndaqel class revenue share) is the red team's runner-up, which it flags for a scope flaw: the denominator includes Amvuttra's U.S. polyneuropathy sales. The blind synthesis records the same caveat in its unresolved field ("Amvuttra U.S. includes hATTR-PN revenue, so the class total is approximate"), so the two agree on the fix: state it as U.S. Vyndaqel flat while the rivals added about $1.25B, and treat the share percentages as approximate. The league ranks Pfizer 7th on the Metsera contingent consideration, which the blind skeptics killed as printed in the release reconciliations.
- **JNJ: league 1st, red team 2nd, blind eliminated.** The red team's JNJ needle (four "other" U.S. products falling to -$390M a quarter in Q3 2026) is not in the blind JNJ candidate set; the blind reader worked from the 2026Q2 10-Q and noted there is no Q3 2026 10-Q in the index. The red team itself says that needle is loss-of-exclusivity erosion that the case calls priced in, with only the aggregation non-obvious. The blind JNJ survivor (offshore plant drift, conditional on the 2029 tariff sunset) is conditional and the product edge is management's talking point. The JNJ gap is the clearest coverage difference between the methods: the red team had a row the blind reader never saw, and the league ranks on a row both other methods call obvious.
- **ABBV: league 3rd, blind and red team mid-table.** The league scores the Skyrizi combination royalty at S 2.42 with obscurity 0.91 and a full concentration multiplier on essentially one row (largest finding share 97%). The blind skeptics sized the new tail at about $1.0-1.5B of present value, bounded but not disclosed, and the red team says the $3.5B headline fails "not said" because the CFO gave it on the Q4 2025 call. All three agree it is one item; only the league formula lets one item carry a top-3 rank.
- **NVO: blind closest miss, red team 5th, league 8th,** each on a different needle (blind: DKK 91.0bn of contract-manufacturer commitments; red team: rebate accrual as 61% of H1 FCF, cash only; league: the Catalent purchase price). No method has Novo in the top 3.
- **GILD and LLY needles differ across all three** (GILD: Trodelvy inventory, Biktarvy 2028 price, anito-cel CVR; LLY: inventory days, Jardiance one-offs). Neither company is in any top 3 except GILD's league 4th.

## Why the methods diverge

1. **Candidate coverage.** Each method saw a different candidate set. The blind readers did not surface MRK's royalty step, PFE's Eliquis windfall, JNJ's Q3 2026 "other products" decline or LLY's Jardiance one-offs; the nugget files did not lead with AMGN's TAVNEOS or MRK's NOPA.
2. **Obviousness strictness.** The blind skeptics kill anything management said plainly, including on grade-C calls used as context, which removed the AMGN IRS claim, JNJ Genmab and PFE Metsera. The league scores obscurity on a continuous scale, so a discussed but large item can still lead.
3. **What is scored.** The red team score includes Part 2 fit and evidence quality (six criteria); the blind run judged only the Part 1 test (needle, five rows, product); the league scores sized rows only and applies a concentration multiplier.

## Plain reading for the team

- If the team's pick must survive all three lenses, the strongest cases are **MRK** (red team pick, blind 2nd, and its row set gets deeper when the two needle sources are combined) and **AMGN** (blind 1st, league 2nd, and its red-team weakness is the IRS headline, which the blind run replaces with TAVNEOS).
- **PFE** is the consistent third choice of the two judgment-based methods, held up mainly by its product comparison.
- **JNJ** is the main disagreement: two methods rank it top 2, but on rows (Genmab, the Q3 2026 erosion) that are either called obvious or flagged as patent-cliff erosion by the same methods' own notes, and the blind run had no access to the Q3 2026 row.
