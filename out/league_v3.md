# League v3 (FIND after the two-round adversarial review)

As of 2026-10-17. L = (sum of top-5 S, one row per underlying fact) x min(1, N_eff / 3). H = 3 months. MFN rows are directional at pi_min; IRA rows use the one class rule (impact.ira_class_rule). Rows without an impact channel are 'not quantified' (S = 0) and stay in findings_v2.jsonl. v2 columns: committed out/league_v2.json. The score is computed by code with no model call; the data layer, onboarding and the citation verifier were built with AI agents (see docs/league_v3_note.md).

| Rank | Ticker | League L | Top-5 sum | N_eff | Blocks | Top finding | Sharpest Needle | v2 L | v2 rank |
|---|---|---|---|---|---|---|---|---|---|
| 1 | JNJ | 1.5399 | 2.7248 | 1.70 | 3 (CFP) | 2029 is the same year the Genmab DARZALEX US patents expire and the US royalty ends, but it may a... (S 1.8425, MEDIUM) | J&J's FY2025 10-K newly puts a number on the Genmab royalty (the FY2024 10-K gave none): 12% to 2... (S 0.4234, D 0.50, O 0.14; strict) | 0.1950 | 3 |
| 2 | AMGN | 1.2000 | 3.4003 | 1.06 | 3 (AFP) | $7.6B claimed (2010-2015 tax and penalties net of credits, plus undisclosed interest) vs $6.3B re... (S 1.8860, MEDIUM) | $7.6B claimed (2010-2015 tax and penalties net of credits, plus undisclosed interest) vs $6.3B re... (S 1.8860, D 0.50, O 0.29; strict) | 0.5432 | 1 |
| 3 | ABBV | 0.8769 | 2.4902 | 1.06 | 3 (FLP) | Since the Q2 2026 10-Q, AbbVie's Skyrizi royalty extends to combination pipeline assets, with pay... (S 2.4224, MEDIUM) | Since the Q2 2026 10-Q, AbbVie's Skyrizi royalty extends to combination pipeline assets, with pay... (S 2.4224, D 1.00, O 0.91; strict) | 0.0881 | 6 |
| 4 | GILD | 0.5008 | 0.7676 | 1.96 | 4 (CFPT) | Gilead's own deal terms set a high bar for anito-cel: Arcellx holders get a $300M CVR only if ani... (S 0.4462, MEDIUM) | Gilead's own deal terms set a high bar for anito-cel: Arcellx holders get a $300M CVR only if ani... (S 0.4462, D 0.50, O 0.29; strict) | 0.4067 | 2 |
| 5 | MRK | 0.1913 | 0.3810 | 1.51 | 4 (ACFP) | Merck's 2026 R&D line is flattered by $700M of Blackstone funding for sac-TMT, booked as a reduct... (S 0.2500, MEDIUM) | Merck's 2026 R&D line is flattered by $700M of Blackstone funding for sac-TMT, booked as a reduct... (S 0.2500, D 0.50, O 0.29; strict) | 0.0970 | 5 |
| 6 | LLY | 0.1261 | 0.1774 | 2.13 | 3 (FLP) | Jardiance revenue has carried a growing one-off every year (a $300M amendment payment in 2024, $5... (S 0.1087, MEDIUM) | Jardiance revenue has carried a growing one-off every year (a $300M amendment payment in 2024, $5... (S 0.1087, D 0.50, O 0.29; strict) | 0.0691 | 8 |
| 7 | PFE | 0.1203 | 0.1892 | 1.91 | 3 (FPT) | Metsera's obesity progress is landing as GAAP losses: Pfizer's contingent-consideration liability... (S 0.0847, MEDIUM) | Metsera's obesity progress is landing as GAAP losses: Pfizer's contingent-consideration liability... (S 0.0847, D 0.50, O 0.29; strict) | 0.0384 | 9 |
| 8 | NVO | 0.0975 | 0.2668 | 1.10 | 3 (AFP) | 69% of the DKK 82.1bn Catalent price (know-how 41.1bn plus goodwill 15.2bn) was booked for 'accel... (S 0.2546, MEDIUM) | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 (S 0.0140, D 0.90, O 0.13; strict) | 0.0281 | 10 |
| 9 | BMY | 0.0763 | 0.1694 | 1.35 | 3 (FPT) | The Keytruda and Tecentriq patent royalties end on December 31, 2026, so BMS loses about $0.67B a... (S 0.1384, MEDIUM) | The Keytruda and Tecentriq patent royalties end on December 31, 2026, so BMS loses about $0.67B a... (S 0.1384, D 0.50, O 0.27; strict) | 0.0698 | 7 |
| 10 | AZN | 0.0739 | 0.0923 | 2.40 | 3 (AFP) | AstraZeneca owes Daiichi Sankyo $673m of Enhertu sales-related payments within a year (up from $3... (S 0.0524, MEDIUM) | AstraZeneca owes Daiichi Sankyo $673m of Enhertu sales-related payments within a year (up from $3... (S 0.0524, D 0.50, O 0.08; strict) | 0.1127 | 4 |

Strict Sharpest Needle (D >= 0.5, E >= 0.90, not LOW, z = 0, S > 0): 10 of 10; provisional or floor-relaxed: none.

Rows downgraded to pi_min because they do not meet their backtest trigger (review A1): JNJ 1, AMGN 1, ABBV 0, GILD 0, MRK 0, LLY 0, PFE 0, NVO 0, BMY 0, AZN 0.

Blocks: A accounting, T text/disclosure, C calls, P policy/contractual, L label, X outside data, F footnote.

## Robustness: the ranking under each variant

| Variant | What changes | #1 | #2 | #3 | #4 | #5 | Strict needles |
|---|---|---|---|---|---|---|---|
| base | v3 rules: H = 3, MFN directional at pi_min, IRA class rule, L = top-5 x N_eff/3 | JNJ 1.5399 | AMGN 1.2000 | ABBV 0.8769 | GILD 0.5008 | MRK 0.1913 | 10 of 10 |
| raw_sum | no concentration multiplier: rank by the raw top-5 sum | AMGN 3.4003 | JNJ 2.7248 | ABBV 2.4902 | GILD 0.7676 | MRK 0.3810 | 10 of 10 |
| mfn_universal | MFN at Pfizer's universal 0.65% of US revenue with pi = 1 (the v2 rule) | JNJ 1.5624 | AMGN 1.2681 | ABBV 0.8952 | GILD 0.5170 | MRK 0.1913 | 10 of 10 |
| amgn_rec_pi_min | AMGN receivables row (gap +8.01 pts, trigger 8) at pi_min with the anchor size kept | JNJ 1.5399 | AMGN 1.1432 | ABBV 0.8769 | GILD 0.5008 | MRK 0.1913 | 10 of 10 |
| amgn_rec_not_fired | AMGN receivables row treated as below its trigger (v3 rule for unfired flags: S = 0) | JNJ 1.5399 | AMGN 1.1432 | ABBV 0.8769 | GILD 0.5008 | MRK 0.1913 | 10 of 10 |
| H6 | obscurity half-life 6 months (the v2 base) | JNJ 2.0142 | AMGN 1.6448 | ABBV 0.9746 | GILD 0.6582 | MRK 0.2941 | 10 of 10 |
| ira_spec | IRA league value on the spec formula G x max(0, d - g_pre) instead of the class rule | JNJ 1.5399 | AMGN 1.1914 | ABBV 0.8875 | GILD 0.5008 | MRK 0.1913 | 10 of 10 |
| c_anchor_half | c = 0.5 on anchor rows too (consensus test not defined for them) | JNJ 0.7699 | AMGN 0.6135 | ABBV 0.4482 | GILD 0.2504 | MRK 0.0957 | 4 of 10 |

Leader across variants: AMGN, JNJ.
Place 1: AMGN, JNJ (unsettled).
Place 2: AMGN, JNJ (unsettled).
Place 3: ABBV (settled).

## 1. JNJ  L = 1.5399
Constants: Rev_TTM 97,929.0, t 0.1651, D 2,440.1M, sigma_EPS 0.1457 USD. Largest finding share 68%. Findings 36 (6 scored, 25 not quantified), withheld 40 (numeric gate 10), guarded 27. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.84245 | 2.247 | 0.820 | 0.820 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | 2029 is the same year the Genmab DARZALEX US patents expire and the US royalty ends, but it may also be the first year DARZALEX could face IRA Part B price s... |
| 2 | 0.42338 | 3.078 | 0.500 | 0.138 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | J&J's FY2025 10-K newly puts a number on the Genmab royalty (the FY2024 10-K gave none): 12% to 20% of all DARZALEX net sales, about $2.4 billion in 2025 (up... |
| 3 | 0.35790 | 4.474 | 0.080 | 0.080 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Talc has swung J&J's GAAP results by billions every year (charges of $5.1 billion in 2024, a $7.0 billion reversal in 2025, $0.8 billion in 1H 2026 and a $5.... |
| 4 | 0.09894 | 0.793 | 0.820 | 0.125 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | ERLEADA, which management names as a 2026 growth driver, was put on the IRA list for government-set Medicare prices from 2028; the only mention is one senten... |
| 5 | 0.00216 | 0.786 | 0.500 | 0.500 | 1.000 | 0.0055 | 0.00 | MEDIUM | C | Analysts asked twice about ICOTYDE sampling and free drug and got patient counts instead; the 'Other Immunology' line that holds ICOTYDE plus IMAAVY booked o... |

## 2. AMGN  L = 1.2000
Constants: Rev_TTM 38,095.0, t 0.1501, D 544.0M, sigma_EPS 0.3452 USD. Largest finding share 55%. Findings 46 (7 scored, 33 not quantified), withheld 41 (numeric gate 8), guarded 31. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.88600 | 6.565 | 0.500 | 0.287 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | $7.6B claimed (2010-2015 tax and penalties net of credits, plus undisclosed interest) vs $6.3B reserved for all open years (UTB $4.4B plus $1.9B accrued inte... |
| 2 | 1.41797 | 4.936 | 0.500 | 0.287 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Amgen still carries TAVNEOS at $2.4B ($2.3B tied to the US) although FDA's drug center proposed withdrawing approval, alleging 'untrue statements of material... |
| 3 | 0.06424 | 1.791 | 1.000 | 0.570 | 1.000 | 0.0629 | 0.00 | MEDIUM | A | Receivables 10,227 vs 8,701 a year earlier (+17.5%, 2026Q2 vs 2025Q2) against quarterly revenue 10,054 vs 9,179 (+9.5%); gap +8.0 pts (derived); peer median ... |
| 4 | 0.02564 | 0.469 | 0.700 | 0.055 | 1.000 | 1.0000 | 0.00 | HIGH | P | Otezla's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $994.0M; base list discount 65% (CMS-published analog, cited). |
| 5 | 0.00651 | 2.288 | 0.900 | 0.517 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | Amgen's entire 2025 net-price decline came from one product: Enbrel lost about $1.19B to lower net price while the whole company lost about $0.96B, so the re... |

## 3. ABBV  L = 0.8769
Constants: Rev_TTM 64,386.0, t 0.2739, D 1,771.0M, sigma_EPS 0.5227 USD. Largest finding share 97%. Findings 34 (9 scored, 19 not quantified), withheld 25 (numeric gate 1), guarded 17. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2.42240 | 2.653 | 1.000 | 0.913 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Since the Q2 2026 10-Q, AbbVie's Skyrizi royalty extends to combination pipeline assets, with payments now projected to 2044 (38% probability for the pipelin... |
| 2 | 0.03034 | 0.107 | 0.500 | 0.283 | 1.000 | 1.0000 | 0.00 | MEDIUM | L | Rinvoq's US label requires prior failure of a TNF blocker in RA, PsA, AS, nr-axSpA, UC, Crohn's and pJIA (UC and Crohn's have a narrow carve-out) and carries... |
| 3 | 0.01894 | 0.167 | 0.200 | 0.113 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | Botox (listed by CMS as 'BOTOX; BOTOX COSMETIC') was selected for Medicare price setting from Jan 1, 2028, on about $601M of 2024 Medicare Part B plus Part D... |
| 4 | 0.01012 | 0.216 | 0.600 | 0.047 | 1.000 | 1.0000 | 0.00 | HIGH | P | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; base list discount 75% (CMS-published analog, cited). |
| 5 | 0.00841 | 0.206 | 0.300 | 0.041 | 1.000 | 1.0000 | 0.50 | HIGH | P | Botox's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,143.1M; assumed base list discount 65.5% (median of the cycle 1-2 negot... |

## 4. GILD  L = 0.5008
Constants: Rev_TTM 30,457.0, t 0.1854, D 1,243.0M, sigma_EPS 0.4031 USD. Largest finding share 58%. Findings 32 (8 scored, 20 not quantified), withheld 27 (numeric gate 4), guarded 22. Flags: TTM GAAP ETR -0.657 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.44625 | 1.542 | 0.500 | 0.289 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Gilead's own deal terms set a high bar for anito-cel: Arcellx holders get a $300M CVR only if anito-cel reaches $6.0B of cumulative sales from launch (revenu... |
| 2 | 0.31925 | 0.788 | 0.700 | 0.405 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | Gilead widened its Biktarvy price-spillover warning in May 2026 to 'potentially other segments' (beyond Medicaid rebates and 340B ceiling prices), and the Me... |
| 3 | 0.00088 | 0.393 | 0.700 | 0.405 | 1.000 | 0.0055 | 0.00 | MEDIUM | T | Gilead's HIV growth switched from volume to price in 2026: Biktarvy's stated drivers went from 'higher demand' (2024, 2025) to 'higher average realized price... |
| 4 | 0.00071 | 0.442 | 0.500 | 0.292 | 1.000 | 0.0055 | 0.00 | MEDIUM | C | Gilead's switch-market plan hands half of each switched patient to Merck: the once-weekly islatravir plus lenacapavir pill (launch targeted for 2027, non-inf... |
| 5 | 0.00054 | 0.243 | 0.700 | 0.405 | 1.000 | 0.0055 | 0.00 | MEDIUM | T | Between the February 2026 10-K and the May 2026 10-Q, Gilead's description of its MFN deal changed from MFN prices 'in Medicaid for select existing and futur... |

## 5. MRK  L = 0.1913
Constants: Rev_TTM 66,569.0, t 0.1854, D 2,470.0M, sigma_EPS 0.2554 USD. Largest finding share 66%. Findings 44 (6 scored, 29 not quantified), withheld 44 (numeric gate 9), guarded 32. Flags: TTM GAAP ETR 0.467 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.24997 | 0.857 | 0.500 | 0.292 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Merck's 2026 R&D line is flattered by $700M of Blackstone funding for sac-TMT, booked as a reduction of R&D through the year and paid in Q4 2026; nothing rep... |
| 2 | 0.05975 | 2.483 | 1.000 | 0.570 | 1.000 | 0.0422 | 0.00 | MEDIUM | A | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 |
| 3 | 0.05429 | 0.318 | 1.000 | 0.171 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Behind the Keytruda roll-off sits a second royalty ladder: the 7.25% royalty on Capvaxive and Vaxneuvance falls to 2.5% from 2027, and the 7% royalty on US G... |
| 4 | 0.01512 | 0.180 | 0.500 | 0.084 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | Lenvima, Merck's $1.05B Eisai alliance, was picked in January 2026 for Medicare price setting effective January 1, 2028, with settled generics allowed in Jul... |
| 5 | 0.00190 | 0.900 | 0.700 | 0.384 | 1.000 | 0.0055 | 0.00 | MEDIUM | C | Asked in October 2025 how much of Merck's 50/50 US vs ex-US revenue split would shift through price equalization, CEO Robert Davis said he was 'not going to ... |

## 6. LLY  L = 0.1261
Constants: Rev_TTM 79,665.0, t 0.2049, D 893.7M, sigma_EPS 2.0295 USD. Largest finding share 61%. Findings 47 (8 scored, 35 not quantified), withheld 24 (numeric gate 0), guarded 29. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.10867 | 0.378 | 0.500 | 0.287 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Jardiance revenue has carried a growing one-off every year (a $300M amendment payment in 2024, $570M in 2025, up to $910M of milestones limited to 2026, $500... |
| 2 | 0.02890 | 0.101 | 0.500 | 0.287 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | The Medicare GLP-1 Bridge that opened Zepbound and Foundayo to seniors at $245 ends December 31, 2027 and exists only because Part D plans declined to opt in... |
| 3 | 0.01735 | 0.151 | 0.200 | 0.115 | 1.000 | 1.0000 | 0.00 | MEDIUM | L | Verzenio is already shrinking in the US (Q2 2026 -9%) and now faces two clocks at once: a Medicare set price from January 2028 and a Cipla patent challenge f... |
| 4 | 0.01385 | 0.060 | 0.400 | 0.230 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | Lilly's tariff shield is conditional: the government deal gives a three-year Section 232 grace period only 'provided that we meet U.S. manufacturing investme... |
| 5 | 0.00859 | 0.253 | 0.250 | 0.034 | 1.000 | 1.0000 | 0.50 | HIGH | P | Trulicity's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $4,898.4M; base list discount 71% (CMS-published analog, cited). |

## 7. PFE  L = 0.1203
Constants: Rev_TTM 63,696.0, t 0.1854, D 5,699.0M, sigma_EPS 0.2509 USD. Largest finding share 45%. Findings 41 (8 scored, 30 not quantified), withheld 35 (numeric gate 8), guarded 24. Flags: TTM GAAP ETR -0.039 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.08470 | 0.297 | 0.500 | 0.285 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Metsera's obesity progress is landing as GAAP losses: Pfizer's contingent-consideration liability rose from $1.79B to $2.26B in H1 2026, a $550M charge (vers... |
| 2 | 0.05196 | 0.130 | 0.700 | 0.399 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | Pfizer has never disclosed a rate or a dollar cost for its MFN pricing agreement: the terms are confidential, the CEO refused to quantify it ('no matter how ... |
| 3 | 0.04081 | 0.143 | 0.500 | 0.285 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | Selling the 11.7% ViiV stake for $1.875B also ended a dividend of $265M to $272M a year that sat inside adjusted income, so adjusted pretax income loses abou... |
| 4 | 0.00975 | 3.108 | 1.000 | 0.570 | 1.000 | 0.0055 | 0.00 | MEDIUM | T | Charges Pfizer keeps out of adjusted EPS as 'certain significant items' recur every year: impairments of $3.0B, $3.3B and $4.9B plus restructuring of $2.2B, ... |
| 5 | 0.00196 | 0.058 | 0.250 | 0.034 | 1.000 | 1.0000 | 0.50 | HIGH | P | Xeljanz's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,013.3M; base list discount 66% (CMS-published analog, cited). |

## 8. NVO  L = 0.0975
Constants: Rev_TTM 309,064.0, t 0.2153, D 4,447.7M, sigma_EPS 0.6160 DKK. Largest finding share 95%. Findings 37 (6 scored, 29 not quantified), withheld 30 (numeric gate 9), guarded 29. Flags: annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4)

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.25461 | 1.116 | 0.400 | 0.228 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | 69% of the DKK 82.1bn Catalent price (know-how 41.1bn plus goodwill 15.2bn) was booked for 'accelerated access to capacity' during a fill-finish shortage Nov... |
| 2 | 0.01032 | 2.557 | 0.600 | 0.087 | 1.000 | 0.0466 | 0.00 | MEDIUM | A | Inventory 49,623 vs 40,849 a year earlier (+21.5%, 2025 vs 2024) against annual revenue 309,064 vs 290,403 (+6.4%); gap +15.1 pts (derived); peer median -4.5... |
| 3 | 0.00149 | 1.178 | 0.400 | 0.230 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | Novo has released prior-year rebate accruals into sales three years running (DKK 2.4bn, 6.5bn, 4.2bn), told investors the 2025 benefit would not recur, then ... |
| 4 | 0.00043 | 1.265 | 0.400 | 0.061 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | Novo's US gross-to-net rose to 69.5% in 2025 from 68.7% (73.7% in 2023), and the mix moved toward statutory Medicaid rebates (+18%) and patient and other US ... |

## 9. BMY  L = 0.0763
Constants: Rev_TTM 49,186.0, t 0.2212, D 2,048.0M, sigma_EPS 0.4778 USD. Largest finding share 82%. Findings 33 (8 scored, 22 not quantified), withheld 26 (numeric gate 3), guarded 28. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.13839 | 0.504 | 0.500 | 0.274 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | The Keytruda and Tecentriq patent royalties end on December 31, 2026, so BMS loses about $0.67B a year of pretax income in 2027. That is roughly $0.27 of EPS... |
| 2 | 0.01645 | 0.703 | 0.300 | 0.023 | 1.000 | 1.0000 | 0.00 | HIGH | P | Pomalyst's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $2,069.1M; base list discount 60% (CMS-published analog, cited). |
| 3 | 0.00922 | 0.453 | 0.150 | 0.020 | 1.000 | 1.0000 | 0.50 | HIGH | P | Orencia's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $2,450.1M; base list discount 66% (CMS-published analog, cited). |
| 4 | 0.00497 | 0.453 | 0.020 | 0.011 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | BMS raised its 2026 non-GAAP EPS guidance to $6.75 to $7.00 on July 30, but that guidance excludes Acquired IPRD charges incurred after June 30. The same day... |
| 5 | 0.00033 | 0.217 | 0.500 | 0.274 | 1.000 | 0.0055 | 0.00 | MEDIUM | T | In April 2026 BMS settled with Dr. Reddy's to allow an IV Orencia biosimilar in the US 'upon approval' (subcutaneous from February 2028). Orencia was also pi... |

## 10. AZN  L = 0.0739
Constants: Rev_TTM 58,739.0, t 0.1749, D 1,562.0M, sigma_EPS 0.5408 USD. Largest finding share 57%. Findings 39 (9 scored, 25 not quantified), withheld 35 (numeric gate 6), guarded 43. Flags: annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4); sigma_EPS window skips a quarter (I/B/E/S gap); last 8 available surprises used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05236 | 0.623 | 0.500 | 0.084 | 1.000 | 1.0000 | 0.00 | MEDIUM | F | AstraZeneca owes Daiichi Sankyo $673m of Enhertu sales-related payments within a year (up from $377m) and $1,952m in total sales-linked payables to three par... |
| 2 | 0.01377 | 0.273 | 0.300 | 0.050 | 1.000 | 1.0000 | 0.00 | MEDIUM | P | Tagrisso drew $1.63bn of Medicare Part D spend in 2024, more than four oncology drugs CMS selected for 2028 negotiation (Erleada, Verzenio, Lenvima, Kisqali)... |
| 3 | 0.01038 | 1.658 | 0.800 | 0.134 | 1.000 | 0.0466 | 0.00 | MEDIUM | A | Inventory 6,557 vs 5,288 a year earlier (+24.0%, 2025 vs 2024) against annual revenue 58,739 vs 54,073 (+8.6%); gap +15.4 pts (derived); peer median -4.5 pts... |
| 4 | 0.00875 | 0.374 | 0.300 | 0.023 | 1.000 | 1.0000 | 0.00 | HIGH | P | Calquence's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,614.2M; base list discount 40% (CMS-published analog, cited). |
| 5 | 0.00708 | 1.658 | 0.800 | 0.134 | 1.000 | 0.0318 | 0.00 | MEDIUM | A | DIO 225 days vs 189 a year earlier (+19.0%) (FY2025); peer median 187 days, z +0.4 |

