# AZN nuggets (AstraZeneca, 20-F filer, USD)

Mined 17 Oct 2026 from `data/corpus/companies/AZN`, the CMS IRA file and the drug packs; revised the same day in challenger round 2 (section at the end). Every filing quote in `AZN.jsonl` passes `agent.needle.pages.check`; drug-label quotes are grep-checked because label files have no page markers. Verifier misses and analytic corrections are logged in `AZN_ai_caught.jsonl`. Starter thread (cancer growth, Farxiga exclusivity loss, US pricing politics) is not restated. Row numbers below are the `AZN-nugget-0NN` ids in the jsonl.

## Ranked findings

| # | Finding | Source | Impact (math) | Peer comparison | Confidence |
|---|---|---|---|---|---|
| 010 | Under a sawtooth US gross-to-net ratio, one line rose every year: chargebacks (340B covered entities, VA, DoD, hospital contracts) went from 7.5% of US gross sales (2022) to 8.4%, 9.8% and 10.8% (2025). Over the same years AZN's suits against state 340B contract-pharmacy laws grew from 8 states to 22, and it is losing (Arkansas pause order Apr 2025; Fifth Circuit for Louisiana, rehearing denied Jul 2026). Zero "340B" or "chargeback" hits on any call | AZN 20-F FY2025 p. 33, 34, F-58; AR 2024 p. 85 (2022 column); 20-F FY2024 p. F-60 (8 states); interim report 2026Q2 p. 35, 36 | Measured: 47,385 x (10.79% - 7.48%) = $1,569m of 2025 revenue above the 2022 rate ($1,128m vs 2023). Forward (one assumption, trend continues): 1.10 pts x 47,385 = $523m in 2026, 3.8% of op. profit 13,743; EPS $0.27. Bear $643m (largest step), bull $0 | BMS charge-backs and cash discounts 12.4% to 16.0% of gross (2023 to 2025, global; BMS 10-K FY2025 p. 81) vs AZN 9.6% to 11.8% on the same basis. Industry trend; AZN's losing 22-state fight is the company-specific part | Medium |
| 011 | Both current US labels show an OS win over Tagrisso alone: J&J's Rybrevant + Lazcluze (MARIPOSA, HR 0.75) and AZN's Tagrisso + chemo (FLAURA2, HR 0.77, 47.5 vs 37.6 months). Only J&J's regimen removes Tagrisso, and its label carries VTE in 36%, 4 months of preventive anticoagulation, rash 86%, infusion reactions 63%. Tagrisso US still grew $301m in 2025 and 10% in H1 2026 | Rybrevant USPI s. 2.7, 5.3, 14.1; Tagrisso USPI s. 14; AZN 20-F FY2025 p. 26; interim report 2026Q2 p. 38; JNJ 10-K FY2025 p. 83; JNJ 10-Q Q2 2026 p. 33 | J&J US franchise $534m (2025) = 17% of Tagrisso US $3,064m. Measured erosion to date $0. Sensitivity: each 5% of Tagrisso US lost = $153m (assumption), EPS $0.08 | Rybrevant/Lazcluze is the case's named rival. Lazcluze 2024 Part D 183 beneficiaries vs Tagrisso 12,370 (CMS DY2024) | Medium |
| 004 | Enhertu sales-related payables to Daiichi Sankyo: $673m due within a year (2024: $377m). Total sales-linked partner payables $1,952m (+$657m) | AZN 20-F FY2025, p. F-33, F-28 (50:50 profit split) | 673 = 4.9% of op. profit in 2026 cash. If capitalised, the +$419m adds about $52m/yr Reported amortisation (treatment inferred) | Counterparty filings not in corpus; no shortlist peer discloses a comparable partner payable | Medium |
| 005 | The BMS diabetes earn-out ($1,164m cash in 2025) ends with a final $257m in 2026 | AZN 20-F FY2025, p. F-33, F-5 | 1,164 - 257 = $907m/yr cash tailwind from 2027 (bear $614m, bull $1,164m). Cash only; Core EPS unaffected | No shortlist peer shows a comparable earn-out roll-off | High |
| 003 | Calquence's Medicare price from Jan 2027 is $8,600 per 30 days: 38% below the 2024 Part D claim ($13,910) and 10% below Imbruvica's MFP. Brukinsa, not selected, keeps its pricing. Not a case competitive-set product | CMS MFP file; CMS Part D DY2024; AZN 20-F FY2025, p. 26; AR 2025, p. 35, 191 | Part D net 1,702 x 0.8 = $1,362m x 22.7% cut = $309m/yr (bear $479m, bull $139m); EPS $0.16. Net = 80% of gross is assumed; a claim can be a 90-day fill while the MFP is per 30 days, so the cut may be overstated | Imbruvica MFP $9,571 (2027); Brukinsa Part D $1,724m in 2024 | Medium |
| 001 | US net-to-gross is a sawtooth: 53.8% (2022), 49.1%, 53.3%, 49.5% (2025). The 2025 "give-back" only reverses 2024's improvement. The Audit Committee "requested a review of the nature and accounting for sales incentives"; scope and result are not disclosed | AZN 20-F FY2025, p. 34, F-32; AR 2024, p. 85; AR 2025, p. 85 | vs 2024 rate $1,804m worse; vs 2023 rate $168m better; vs 2022 rate $2,025m worse. No trend, so base $0 | GSK US net/gross 53.7% to 52.2% (GSK 20-F FY2025) | High (facts); context only |
| 007 | MFN never sized. CFO Sarin: the headwind is "already factored in our guidance". Fredrickson (to Peter Verdult, BNP, 2026Q2 call): "we don't give brand-specific pricing commentary on MFN and don't plan to". The H1 2026 report names the agreement as a gross-margin drag | 6-K 2026-07-27, p. 21 (cite first); 2025Q4 and 2026Q2 calls (third-party allmind.ai) | Sensitivity: 1% of US net sales 23,444 = $234m; 2% = $469m, EPS $0.24 (assumption) | Not run; PFE and MRK MFN disclosure is the next contrast | Medium |
| 008 | Prosecutors indicted the China operating company itself in Nov 2025 on illegal-trade and personal-data charges tied to Imfinzi, Imjudo and Enhertu imports. Not raised on any call | AZN 20-F FY2025, p. F-57, F-58; AR 2025, p. 35 | Fine 1x to 5x of $3.5m = $3.5m to $17.5m. China revenue $6,654m is the exposure base; no disruption number is carried | No other shortlist company discloses an indictment of its China entity | Low |

Not slide-ready (kept in the jsonl with `slide_ready: false`):

- **006 Tariff exemption and onshoring wording.** Facts usable in prose: the delay is "three years" from 10 Oct 2025 (about Oct 2028), the promise went from "all" (press release) to "substantially all" (AR 2025 p. 35), and most APIs are externally sourced. Its dollar scenario rests on assumed inputs and is not shown.
- **009 Tagrisso IRA selection risk.** needs_human: the eligibility rule is unconfirmed.
- **002 Receivables factoring.** $0 impact. Use only as the "AI caught its own false positive" example: the code's $1,219m receivables flag is a factoring and China bank-draft pool (667 to 2,681); the rest of trade receivables fell 0.8% (20-F p. F-29).

## Sharpest Needle candidate

**#010, the chargeback line under a flat-looking gross-to-net.** The round 1 needle (#001) failed the baseline test: AZN's US net-to-gross ratio alternates every year, so a "$1.8bn give-back" against 2024 is a $168m improvement against 2023. Splitting the same table by line shows what does trend: chargebacks, the line where 340B covered entities, the VA, the DoD and hospital contract prices are credited, rose every year from 7.5% to 10.8% of US gross sales, $1.57bn of 2025 revenue above the 2022 rate. In the same period AstraZeneca widened its court challenge to state 340B contract-pharmacy laws from 8 states to 22 and kept losing (Arkansas pause order, Colorado and Maryland injunctions denied, Fifth Circuit for Louisiana with rehearing denied in July 2026). Neither "340B" nor "chargeback" appears on any call in the corpus. It beats the runner-up (#011, the Tagrisso label comparison) because #011 shows no measured erosion yet, while #010 has four years of verified data and a court calendar inside the 24-month window. Honest limits (red team v3): BMS shows a larger creep on the same basis (+3.6 pts vs AZN +2.2 pts, 2023 to 2025), so the trend is an industry one and is not AZN-specific 340B leakage; the row is no longer slide-ready, and the 20-F does not split chargebacks by program, so the 340B link is an inference. Against MRK's contractual royalty needle, #010 is weaker; AZN's best is a medium-confidence needle.

## Part 2 hooks

- Budget US net price for 340B contract-pharmacy access instead of counting on the 22-state court fight; kill signal is the next ruling in the Colorado or Louisiana appeals (#010).
- Defend Tagrisso with Tagrisso plus chemotherapy (FLAURA2) where an OS benefit is wanted, rather than conceding the OS argument to Rybrevant plus Lazcluze (#011).
- Use the roughly $0.9bn/yr freed by the end of the BMS earn-out (#005) to fund US capex without new debt. Net out the Enhertu partner payments (#004) before counting ADC growth as owned cash.
- Price new US launches for MFN from day one (#007).
- Kill signal for China-led growth plans: the Shenzhen court trial date (#008).
- Present #002 as the tool catching its own false positive, not as a red flag.

## Rejected nuggets

- Gross margin metric switched from Product Sales to Total Revenue (AR p. 85). Including Alliance Revenue of $3,067m lifts the reported margin by about 1.0 pt. Optics only.
- Farxiga MFP of $178.50 per 30 days vs $939 per 2024 Part D claim: real, but US generics launched in Q2 2026 (US Farxiga $219m in Q2, -48%) and swamp it.
- Farxiga EU exclusivity: the 20-F lists EU patent dates of 2027 and 2028, both under validity proceedings, with the UK patent already invalid and challenges in France, Poland and Portugal (20-F p. 19, 21, F-52). The CFO already told the Q4 2025 call that EU protection extends to 2028, so it is not least discussed. Logged as context.
- Inventory +24% vs revenue (code row): already in the code output. The $407m Andexxa provision reversal (20-F p. F-29) explains part of it.
- Seagen 8% Enhertu royalty judgment: vacated by the Federal Circuit in Dec 2025 (20-F p. F-52). Gone.
- China rebate accrual $619m vs $532m (20-F p. F-32): +16%, too small alone.
- Legal provisions cash paid of $720m in 2025 (20-F p. F-33): matter not traced.

## Challenger round 2

What the red team said (docs/red_team_v2_company_pick.md): AZN ranked 4th of 4 at 16.5/30. The needle failed the baseline test, Calquence is off the case's product list, the transcripts are third-party, the 2026Q1 file duplicates 2026Q2, and 2025Q3 has no speaker names.

What I hunted, and what came out:

- **Gross-to-net, line by line, 2022 to 2025** (AR 2024 p. 85 adds 2022). Managed care and Medicare alternate (27.5%, 30.2%, 26.6%, 29.5% of gross), Medicaid is flat to down (5.9%, 6.6%, 5.4%, 5.3%), chargebacks rise every year (7.5%, 8.4%, 9.8%, 10.8%). Result: new #010; #001 demoted to context with base $0.
- **Audit Committee review.** AR 2025 p. 85 is a single sentence in the Chair's introduction; nothing in the AR or 20-F says what the review covered or found. Verb fixed to "requested". No wrongdoing implied.
- **Tagrisso vs Rybrevant + Lazcluze** (case product). New #011 from the two labels plus J&J's own segment table. This fills the product-comparison gap the red team scored at 2/5.
- **Farxiga erosion.** US Q2 2026 $219m (-48%); Brilinta US is the template ($2m in Q2 2026, -98%, one year after generics). Starter thread, so not a nugget. EU exclusivity was already discussed by the CFO.
- **Tariff (Oct 2028 vs Jan 2029, "all" vs "substantially all").** Facts hold, but the dollar figure is all assumption; #006 is marked not slide-ready.
- **China prosecution.** Fact kept; the $333m scenario was removed from #008.
- **Daiichi payables, BMS earn-out.** Unchanged, still verified. #005 is high confidence but cash-only.
- **Imfinzi vs Keytruda, FX.** No verified, non-obvious item found in the time available. Imfinzi US +35% in 2025 is a headline number; it was used only as the mix check in #010.

Fixes applied in place: #001 verb changed to "requested", reframed as "2024 improvement fully reversed", base $0, Fasenra true-up evidence removed (prior-year adjustments were a $175m release). #002 is AI-caught only ($0 base and bear, `slide_use: ai_caught_only`). #006 and #009 are `slide_ready: false`. #008 has no $333m figure. #003 now carries the per-claim vs per-30-day units caveat and the off-list note. No row cites the 2026Q1 transcript or names a 2025Q3 speaker. Every new or changed filing quote re-verified (all 57 filing and peer quotes in the jsonl return verified; 4 label quotes grep-checked).

Verdict: AZN now has a defensible, medium-confidence needle (#010) and a product comparison row (#011). That likely lifts AZN above 16.5, but it does not beat MRK: #010 is partly industry-wide and rests on an inferred 340B link, where MRK's royalty step is contractual and dated.

Five-line summary:
1. Kept: 11 rows in the jsonl (8 slide-ready findings, 2 not slide-ready, 1 AI-caught example); 2 new this round (#010, #011).
2. Dropped or demoted: #001 from needle to context; #002 to AI-caught only; $586m tariff and $333m China figures off slides; HRSA rebate-model hook dropped as unsupported.
3. Top candidate: #010, chargebacks up every year 7.5% to 10.8% of US gross while AZN loses its 22-state 340B fight; $523m/yr forward at trend, medium confidence.
4. Biggest gap: no split of chargebacks by program or product, no official AZN transcripts, and the Q1 2026 call is missing.
5. Next: a cross-ticker theme run on chargeback and 340B lines (BMY, AMGN, MRK, JNJ GTN tables) to test whether AZN's creep is above or below the group.
