# AMGN Part 2 refresh: discrepancies against the new fills (data-moat d92e501)

None of the figures below were edited. Each one is reported to the coordinator before any change.

## 1. Per-patient trial cost ($150,000 [assumption]) vs the immunomodulation benchmarks

- Published: math step 6 and case_for.return use $150,000 per patient [assumption] x 331 patients (Amgen 10-K FY2025 file p.8) = $49.65M trial, plus $25M [assumption] = $74.65M program, $62.15M conditional release, and an 18.1-point break-even for the full program.
- New source rows (no vasculitis category exists; immunomodulation is the nearest):
  - Sertkaya et al., JAMA Netw Open 2024, Table 1, Immuno-modulation Phase 3 per-patient cost $54,909 (2018 USD): costs/trial_cost_benchmarks.csv#217, verified.
  - Sertkaya 2024, Immuno-modulation Phase 3 out-of-pocket cost for the phase $52.4M (2018 USD): costs/trial_cost_benchmarks.csv#469.
  - Derived Sertkaya Phase 3 direct cost per trial $16.97M (per-patient cost x 309 patients; excludes site and CRO fixed costs): costs/trial_cost_benchmarks.csv#525.
  - ASPE 2014 (Sertkaya, Birkenbach et al.), Table 1, Immunomodulation Phase 3 $11.9M per single study: costs/trial_cost_benchmarks.csv#60.
- The gap: the published per-patient figure is about 2.7 times the Sertkaya Phase 3 per-patient benchmark. At $54,909 the trial would be about $18.2M, the program about $43.2M, the conditional release about $30.7M, and the full-program break-even about 10.4 points (all on the same $413.3M exposure).
- What does not move: the committed $12.5M, its 3.0-point break-even (2.4 to 3.6 points), the $20.7M expected avoided loss and the $8.2M net all sit on the gated offer and do not use the trial cost.
- Caveat on the benchmark: a five-year randomized trial with independent adjudication and a liver registry in a rare vasculitis is longer and costlier per patient than an average immunomodulation Phase 3; the benchmark is a 2018-dollar average with fixed costs excluded.

## 2. Month 12 as the earliest withdrawal effect ([assumption])

- The TAVNEOS notice (policy:policy/fda_tavneos_proposal_to_withdraw_2026.md p.1) dates only the hearing request (June 1, 2026) and the supporting data (June 29, 2026). It sets no date for a ruling, so it cannot replace the assumption with a cited date.
- Precedent pace from proposal to final decision:
  - Avastin breast cancer: notice December 16, 2010, final decision November 18, 2011, about 11 months (fda_avastin_breast_final_decision_2012.md p.1).
  - Makena: proposal October 5, 2020, final decision April 6, 2023, about 30 months (fda_makena_final_decision_2023.md p.1).
  - Pepaxto: notice August 25, 2023, withdrawn February 23, 2024, about 6 months, expedited accelerated-approval procedure (fda_pepaxto_final_decision_2024.md p.1).
- Read from the TAVNEOS notice of April 30, 2026, an Avastin pace would land around March 2027, about month 5 from now, before the assumed month 12. A Makena pace would land in late 2028. The assumption is inside the precedent range but is not its earliest point; an earlier bite would raise exposure inside the window and lower the break-even. Not edited.

## 3. Trial size: 331 vs 330 vs 300 (no change)

- Published: 331 (Amgen 10-K FY2025 file p.8). The FDA notice also says ADVOCATE "randomized 331 subjects" (proposal p.3). Label Section 14 says 330 (tavneos label v16 file p.40). The existing required safety trial plans 300 patients (proposal p.8). 331 stands, cited.

## 4. Cost of capital (no change)

- No published part2.json block carries an 8% hurdle or a note rate. The 8% appears only inside the verbatim skeptic positions in trace.jsonl, which are kept verbatim. The cited effective rates (6.3%, 5.6% and 5.2% on the 2048, 2051 and 2053 notes, Amgen 10-K FY2025 file p.141) and interest expense, net of $2,755M (file p.77 and p.150) were not added, because the refresh constraint allows only assumption-to-citation swaps of the same number.

## 5. Substantive flag on the move wording (not a number; move unchanged per the constraint)

- The FDA approval letter (policy:policy/fda_tavneos_approval_letter_2021.md p.3 to p.5) already requires a randomized controlled trial of at least five years (PMR 4155-1, safety including hepatotoxicity, final report 09/2031). It also carries a postmarketing efficacy commitment (PMC 4155-3). CDER's notice (p.8) says the same study is also assessing efficacy and has enrolled only 21 of a planned 300 patients.
- So the "designed confirmatory randomized trial" in the move overlaps a trial the FDA already required. The offer is most credible framed as fully funding and independently adjudicating that required trial, not as a new trial. The evidence section now says this; the move sentence was left as is.

## Rulings applied (coordinator, after this file was first written)

- Item 1 APPLIED. The per-patient cost is now the cited Sertkaya 2024 Immuno-modulation Phase 3 figure, $54,909 in 2018 USD (costs/trial_cost_benchmarks.csv#217, facts row verified, status exact). It is the nearest benchmark because no vasculitis category exists; no inflation index is in the store, so it is not adjusted, and the text says the 2018 basis understates today's cost. Recomputed through the gate: trial $18.2M (331 x $54,909), program $43.2M (plus the $25M registry [assumption]), conditional release $30.7M, full-program break-even 10.4 points. Unchanged: the committed $12.5M, 12 people, 3.0-point break-even (2.4 to 3.6), $20.7M expected avoided loss and $8.2M net.
- Item 2 HELD. Month 12 stays [assumption]. can_tell carries the hearing precedents, and this file holds the 6 to 30 month precedent range.
- Item 3 APPLIED. The move now offers to fully fund and independently adjudicate the FDA-required five-year randomized trial (PMR 4155-1) plus the U.S. liver-safety registry. Its cites add the 2021 approval letter p.3 (PMR 4155-1), p.4 (PMC 4155-3) and p.5 (trial completion 12/2030, final report 09/2031), and the CDER notice p.8 (21 of 300 enrolled). Budget, people, owner, gating and decision timing are unchanged. The budget, cost, return and math step 6 use the same trial wording. Step 6 sizes the trial at ADVOCATE's 331 patients and notes that the required trial plans 300, so the cost is stated on the high side. No kill signal describes the trial, so none changed.
