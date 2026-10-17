# League v3 (FIND after the two-round adversarial review)

As of 2026-10-17. L = (sum of top-5 S, one row per underlying fact) x min(1, N_eff / 3). H = 3 months. MFN rows are directional at pi_min; IRA rows use the one class rule (impact.ira_class_rule). Rows without an impact channel are 'not quantified' (S = 0) and stay in findings_v2.jsonl. v2 columns: committed out/league_v2.json. The score is computed by code with no model call; the data layer, onboarding and the citation verifier were built with AI agents (see docs/league_v3_note.md).

| Rank | Ticker | League L | Top-5 sum | N_eff | Blocks | Top finding | Sharpest Needle | v2 L | v2 rank |
|---|---|---|---|---|---|---|---|---|---|
| 1 | AMGN | 0.0877 | 0.2047 | 1.29 | 2 (AP) | Receivables 10,227 vs 8,701 a year earlier (+17.5%, 2026Q2 vs 2025Q2) against quarterly revenue 1... (S 0.1787, MEDIUM) | Receivables 10,227 vs 8,701 a year earlier (+17.5%, 2026Q2 vs 2025Q2) against quarterly revenue 1... (S 0.1787, D 1.00, O 0.57; strict) | 0.5432 | 1 |
| 2 | GILD | 0.0511 | 0.1532 | 1.00 | 1 (P) | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; ... (S 0.1531, HIGH) | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; ... (S 0.1531, D 0.40, O 0.05; floor relaxed) | 0.4067 | 2 |
| 3 | AZN | 0.0290 | 0.0674 | 1.29 | 2 (AP) | DSO 64 days vs 56 a year earlier (+13.5%) (FY2025); peer median 72 days, z -0.7 (S 0.0237, MEDIUM) | DSO 64 days vs 56 a year earlier (+13.5%) (FY2025); peer median 72 days, z -0.7 (S 0.0237, D 1.00, O 0.17; strict) | 0.1127 | 4 |
| 4 | MRK | 0.0199 | 0.0597 | 1.00 | 1 (A) | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 (S 0.0597, MEDIUM) | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 (S 0.0597, D 1.00, O 0.57; strict) | 0.0970 | 5 |
| 5 | BMY | 0.0086 | 0.0257 | 1.00 | 1 (P) | Pomalyst's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $2,069.1M; ... (S 0.0165, HIGH) | Pomalyst's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $2,069.1M; ... (S 0.0165, D 0.30, O 0.02; floor relaxed) | 0.0698 | 7 |
| 6 | NVO | 0.0081 | 0.0243 | 1.00 | 1 (A) | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 (S 0.0140, MEDIUM) | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 (S 0.0140, D 0.90, O 0.13; strict) | 0.0281 | 10 |
| 7 | ABBV | 0.0066 | 0.0197 | 1.00 | 1 (P) | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; b... (S 0.0101, HIGH) | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; b... (S 0.0101, D 0.60, O 0.05; strict) | 0.0881 | 6 |
| 8 | LLY | 0.0051 | 0.0152 | 1.00 | 1 (P) | Trulicity's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $4,898.4M;... (S 0.0086, HIGH) | Trulicity's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $4,898.4M;... (S 0.0086, D 0.25, O 0.03; provisional) | 0.0691 | 8 |
| 9 | PFE | 0.0007 | 0.0020 | 1.00 | 1 (P) | Xeljanz's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,013.3M; b... (S 0.0020, HIGH) | Xeljanz's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,013.3M; b... (S 0.0020, D 0.25, O 0.03; floor relaxed) | 0.0384 | 9 |
| 10 | JNJ | 0.0001 | 0.0004 | 1.00 | 1 (P) | JNJ signed an MFN agreement on 2026-01-08 that extends MFN pricing to Medicaid (R037); US investm... (S 0.0004, MEDIUM) | none | 0.1950 | 3 |

Strict Sharpest Needle (D >= 0.5, E >= 0.90, not LOW, z = 0, S > 0): 5 of 10; provisional or floor-relaxed: GILD, BMY, LLY, PFE, JNJ.

Rows downgraded to pi_min because they do not meet their backtest trigger (review A1): AMGN 1, GILD 0, AZN 0, MRK 0, BMY 0, NVO 0, ABBV 0, LLY 0, PFE 0, JNJ 1.

Blocks: A accounting, T text/disclosure, C calls, P policy/contractual, L label, X outside data, F footnote.

## Robustness: the ranking under each variant

| Variant | What changes | #1 | #2 | #3 | #4 | #5 | Strict needles |
|---|---|---|---|---|---|---|---|
| base | v3 rules: H = 3, MFN directional at pi_min, IRA class rule, L = top-5 x N_eff/3 | AMGN 0.0877 | GILD 0.0511 | AZN 0.0290 | MRK 0.0199 | BMY 0.0086 | 5 of 10 |
| raw_sum | no concentration multiplier: rank by the raw top-5 sum | AMGN 0.2047 | GILD 0.1532 | AZN 0.0674 | MRK 0.0597 | BMY 0.0257 | 5 of 10 |
| mfn_universal | MFN at Pfizer's universal 0.65% of US revenue with pi = 1 (the v2 rule) | AMGN 0.1681 | GILD 0.0576 | AZN 0.0290 | JNJ 0.0265 | MRK 0.0199 | 10 of 10 |
| amgn_rec_pi_min | AMGN receivables row (gap +8.01 pts, trigger 8) at pi_min with the anchor size kept | GILD 0.0511 | AZN 0.0290 | AMGN 0.0261 | MRK 0.0199 | BMY 0.0086 | 5 of 10 |
| amgn_rec_not_fired | AMGN receivables row treated as below its trigger (v3 rule for unfired flags: S = 0) | GILD 0.0511 | AZN 0.0290 | MRK 0.0199 | AMGN 0.0087 | BMY 0.0086 | 5 of 10 |
| H6 | obscurity half-life 6 months (the v2 base) | AMGN 0.1847 | GILD 0.1386 | AZN 0.0825 | BMY 0.0280 | MRK 0.0264 | 5 of 10 |
| ira_spec | IRA league value on the spec formula G x max(0, d - g_pre) instead of the class rule | AMGN 0.0785 | GILD 0.0460 | AZN 0.0270 | MRK 0.0199 | ABBV 0.0118 | 5 of 10 |
| c_anchor_half | c = 0.5 on anchor rows too (consensus test not defined for them) | AMGN 0.0591 | GILD 0.0511 | AZN 0.0197 | MRK 0.0100 | BMY 0.0086 | 4 of 10 |

Leader across variants: AMGN, GILD.
Place 1: AMGN, GILD (unsettled).
Place 2: AZN, GILD (unsettled).
Place 3: AMGN, AZN, MRK (unsettled).

## 1. AMGN  L = 0.0877
Constants: Rev_TTM 38,095.0, t 0.1501, D 544.0M, sigma_EPS 0.3452 USD. Largest finding share 87%. Findings 47 (3 scored, 37 not quantified), withheld 29, guarded 22. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.17866 | 4.981 | 1.000 | 0.570 | 1.000 | 0.0629 | 0.00 | MEDIUM | A | Receivables 10,227 vs 8,701 a year earlier (+17.5%, 2026Q2 vs 2025Q2) against quarterly revenue 10,054 vs 9,179 (+9.5%); gap +8.0 pts (derived); peer median ... |
| 2 | 0.02564 | 0.469 | 0.700 | 0.055 | 1.000 | 1.0000 | 0.00 | HIGH | P | Otezla's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $994.0M; base list discount 65% (CMS-published analog, cited). |
| 3 | 0.00039 | 0.776 | 0.900 | 0.091 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | AMGN signed an MFN agreement on 2025-12-19 that extends MFN pricing to Medicaid (R023); TrumpRx: Repatha $573 -> $239/mo (R031). Direction: adverse to US net... |

## 2. GILD  L = 0.0511
Constants: Rev_TTM 30,457.0, t 0.1854, D 1,243.0M, sigma_EPS 0.4031 USD. Largest finding share 100%. Findings 30 (2 scored, 22 not quantified), withheld 20, guarded 18. Flags: TTM GAAP ETR -0.657 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.15310 | 2.818 | 0.400 | 0.054 | 1.000 | 1.0000 | 0.50 | HIGH | P | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; assumed base list discount 65.5% (median of the 16 cycle 1-2... |
| 2 | 0.00011 | 0.216 | 0.900 | 0.091 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | GILD signed an MFN agreement on 2025-12-19 that extends MFN pricing to Medicaid (R025); US investment pledge $32bn; TrumpRx: Epclusa $24,920 -> $2,425 (R033)... |

## 3. AZN  L = 0.0290
Constants: Rev_TTM 58,739.0, t 0.1749, D 1,562.0M, sigma_EPS 0.5408 USD. Largest finding share 35%. Findings 36 (6 scored, 26 not quantified), withheld 27, guarded 40. Flags: annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4); sigma_EPS window skips a quarter (I/B/E/S gap); last 8 available surprises used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.02370 | 1.658 | 1.000 | 0.168 | 1.000 | 0.0851 | 0.00 | MEDIUM | A | DSO 64 days vs 56 a year earlier (+13.5%) (FY2025); peer median 72 days, z -0.7 |
| 2 | 0.01751 | 1.658 | 1.000 | 0.168 | 1.000 | 0.0629 | 0.00 | MEDIUM | A | Receivables 10,237 vs 8,302 a year earlier (+23.3%, 2025 vs 2024) against annual revenue 58,739 vs 54,073 (+8.6%); gap +14.7 pts (derived); peer median -0.3 ... |
| 3 | 0.01038 | 1.658 | 0.800 | 0.134 | 1.000 | 0.0466 | 0.00 | MEDIUM | A | Inventory 6,557 vs 5,288 a year earlier (+24.0%, 2025 vs 2024) against annual revenue 58,739 vs 54,073 (+8.6%); gap +15.4 pts (derived); peer median -4.5 pts... |
| 4 | 0.00875 | 0.374 | 0.300 | 0.023 | 1.000 | 1.0000 | 0.00 | HIGH | P | Calquence's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,614.2M; base list discount 40% (CMS-published analog, cited). |
| 5 | 0.00708 | 1.658 | 0.800 | 0.134 | 1.000 | 0.0318 | 0.00 | MEDIUM | A | DIO 225 days vs 189 a year earlier (+19.0%) (FY2025); peer median 187 days, z +0.4 |

## 4. MRK  L = 0.0199
Constants: Rev_TTM 66,569.0, t 0.1854, D 2,470.0M, sigma_EPS 0.2554 USD. Largest finding share 100%. Findings 41 (1 scored, 34 not quantified), withheld 35, guarded 30. Flags: TTM GAAP ETR 0.467 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.05975 | 2.483 | 1.000 | 0.570 | 1.000 | 0.0422 | 0.00 | MEDIUM | A | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 |

## 5. BMY  L = 0.0086
Constants: Rev_TTM 49,186.0, t 0.2212, D 2,048.0M, sigma_EPS 0.4778 USD. Largest finding share 64%. Findings 30 (2 scored, 24 not quantified), withheld 22, guarded 27. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01645 | 0.703 | 0.300 | 0.023 | 1.000 | 1.0000 | 0.00 | HIGH | P | Pomalyst's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $2,069.1M; base list discount 60% (CMS-published analog, cited). |
| 2 | 0.00922 | 0.453 | 0.150 | 0.020 | 1.000 | 1.0000 | 0.50 | HIGH | P | Orencia's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $2,450.1M; base list discount 66% (CMS-published analog, cited). |

## 6. NVO  L = 0.0081
Constants: Rev_TTM 309,064.0, t 0.2153, D 4,447.7M, sigma_EPS 0.6160 DKK. Largest finding share 58%. Findings 38 (2 scored, 31 not quantified), withheld 19, guarded 27. Flags: annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4)

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01402 | 2.557 | 0.900 | 0.130 | 1.000 | 0.0422 | 0.00 | MEDIUM | A | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 |
| 2 | 0.01032 | 2.557 | 0.600 | 0.087 | 1.000 | 0.0466 | 0.00 | MEDIUM | A | Inventory 49,623 vs 40,849 a year earlier (+21.5%, 2025 vs 2024) against annual revenue 309,064 vs 290,403 (+6.4%); gap +15.1 pts (derived); peer median -4.5... |

## 7. ABBV  L = 0.0066
Constants: Rev_TTM 64,386.0, t 0.2739, D 1,771.0M, sigma_EPS 0.5227 USD. Largest finding share 51%. Findings 32 (4 scored, 18 not quantified), withheld 19, guarded 12. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01012 | 0.216 | 0.600 | 0.047 | 1.000 | 1.0000 | 0.00 | HIGH | P | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; base list discount 75% (CMS-published analog, cited). |
| 2 | 0.00841 | 0.206 | 0.300 | 0.041 | 1.000 | 1.0000 | 0.50 | HIGH | P | Botox's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,143.1M; assumed base list discount 65.5% (median of the 16 cycle 1-2 ne... |
| 3 | 0.00098 | 0.021 | 0.600 | 0.047 | 1.000 | 1.0000 | 0.00 | HIGH | P | Vraylar's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,085.8M; base list discount 44% (CMS-published analog, cited). |
| 4 | 0.00014 | 0.237 | 0.900 | 0.109 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | ABBV signed an MFN agreement on 2026-01-12 that extends MFN pricing to Medicaid (R041); US investment pledge $100bn; TrumpRx: Alphagan, Combigan, Humira, Syn... |

## 8. LLY  L = 0.0051
Constants: Rev_TTM 79,665.0, t 0.2049, D 893.7M, sigma_EPS 2.0295 USD. Largest finding share 57%. Findings 39 (3 scored, 34 not quantified), withheld 23, guarded 26. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.00859 | 0.253 | 0.250 | 0.034 | 1.000 | 1.0000 | 0.50 | HIGH | P | Trulicity's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $4,898.4M; base list discount 71% (CMS-published analog, cited). |
| 2 | 0.00654 | 0.193 | 0.250 | 0.034 | 1.000 | 1.0000 | 0.50 | HIGH | P | Verzenio's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,428.7M; base list discount 50% (CMS-published analog, cited). |
| 3 | 0.00004 | 0.144 | 0.700 | 0.051 | 1.000 | 0.0055 | 0.00 | MEDIUM | P | LLY signed an MFN agreement on 2025-11-06 that extends MFN pricing to Medicaid (R010); US investment pledge $50bn; TrumpRx: Zepbound avg $346/mo; Trulicity $... |

## 9. PFE  L = 0.0007
Constants: Rev_TTM 63,696.0, t 0.1854, D 5,699.0M, sigma_EPS 0.2509 USD. Largest finding share 99%. Findings 41 (2 scored, 36 not quantified), withheld 25, guarded 22. Flags: TTM GAAP ETR -0.039 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.00196 | 0.058 | 0.250 | 0.034 | 1.000 | 1.0000 | 0.50 | HIGH | P | Xeljanz's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,013.3M; base list discount 66% (CMS-published analog, cited). |
| 2 | 0.00002 | 0.132 | 0.500 | 0.028 | 1.000 | 0.0055 | 0.29 | MEDIUM | P | PFE signed an MFN agreement on 2025-09-30 that extends MFN pricing to Medicaid (R002); US investment pledge $70bn; TrumpRx: avg 50%, up to 85% (R004). Direct... |

## 10. JNJ  L = 0.0001
Constants: Rev_TTM 97,929.0, t 0.1651, D 2,440.1M, sigma_EPS 0.1457 USD. Largest finding share 100%. Findings 38 (1 scored, 32 not quantified), withheld 28, guarded 22. Flags: none

| # | S | M | D | O | E | pi | c | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.00044 | 0.809 | 0.837 | 0.098 | 1.000 | 0.0055 | 0.08 | MEDIUM | P | JNJ signed an MFN agreement on 2026-01-08 that extends MFN pricing to Medicaid (R037); US investment pledge $55bn; TrumpRx: participating (R038). Direction: ... |

