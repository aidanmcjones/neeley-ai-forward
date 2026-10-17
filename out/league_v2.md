# League v2 (FIND, docs/quant_model.md)

As of 2026-10-17. L = (sum of top-5 S) x min(1, N_eff / 3). Old score and rank: committed out/league.json (old scorer, before the gross-margin level fix). Deterministic, no API key.

| Rank | Ticker | League L | Top-5 sum | N_eff | Blocks | Top finding | Sharpest Needle | Old score | Old rank |
|---|---|---|---|---|---|---|---|---|---|
| 1 | AMGN | 0.3412 | 0.6900 | 1.48 | 3 (APT) | Days sales outstanding 93 days (Q2 2026) vs peers; peer median 72 days, z +1.8 (S 0.3213, MEDIUM) | Days sales outstanding 93 days (Q2 2026) vs peers; peer median 72 days, z +1.8 (S 0.3213, O 0.76; strict) | 0.0894 | 5 |
| 2 | GILD | 0.2838 | 0.7819 | 1.09 | 2 (PT) | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; ... (S 0.7486, HIGH) | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; ... (S 0.7486, O 0.29; provisional) | 0.1079 | 4 |
| 3 | JNJ | 0.1666 | 0.2851 | 1.75 | 3 (ACT) | Inventory +12.9% YoY vs revenue +6.6% (Q2 2026); gap +6.3 pts; peer median -4.5 pts, z +0.7 (S 0.2033, MEDIUM) | Inventory +12.9% YoY vs revenue +6.6% (Q2 2026); gap +6.3 pts; peer median -4.5 pts, z +0.7 (S 0.2033, O 0.66; strict) | 0.0696 | 8 |
| 4 | AZN | 0.1076 | 0.2500 | 1.29 | 2 (AP) | DSO 64 days vs 56 a year earlier (+13.5%) (FY2025); peer median 72 days, z -0.7 (S 0.0746, MEDIUM) | DSO 64 days vs 56 a year earlier (+13.5%) (FY2025); peer median 72 days, z -0.7 (S 0.0746, O 0.41; provisional) | 0.19 | 2 |
| 5 | MRK | 0.0970 | 0.1467 | 1.98 | 2 (AT) | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 (S 0.0800, MEDIUM) | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 (S 0.0800, O 0.76; strict) | 0.1398 | 3 |
| 6 | ABBV | 0.0703 | 0.1632 | 1.29 | 2 (PT) | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; b... (S 0.0725, HIGH) | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; b... (S 0.0725, O 0.17; provisional) | 0.075 | 7 |
| 7 | BMY | 0.0417 | 0.0853 | 1.46 | 2 (PT) | Pomalyst's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $2,069.1M; ... (S 0.0524, HIGH) | new paragraph in risk factors vs FY2024 (topics: tariff) (S 0.0067, O 0.35; provisional) | 0.0451 | 10 |
| 8 | LLY | 0.0399 | 0.0622 | 1.93 | 3 (APT) | Verzenio's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,428.7M; ... (S 0.0304, HIGH) | Effective tax rate 23.3% vs 16.5% a year earlier (+6.8 pts) (Q2 2026); peer median 17.7%, z +1.0 (S 0.0021, O 0.76; strict) | 0.3034 | 1 |
| 9 | NVO | 0.0281 | 0.0703 | 1.20 | 3 (ATX) | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 (S 0.0369, MEDIUM) | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 (S 0.0369, O 0.34; provisional) | 0.05 | 9 |
| 10 | PFE | 0.0180 | 0.0350 | 1.54 | 2 (PT) | new paragraph in risk factors vs FY2024 (topics: litigation, ai) (S 0.0101, MEDIUM) | Effective tax rate 62.3% vs 4.6% a year earlier (+57.7 pts) (Q2 2026); peer median 17.7%, z +3.0 (S 0.0020, O 0.68; strict) | 0.0788 | 6 |

Companies with no finding clearing the strict Needle floors (O >= 0.5, E >= 0.90, not LOW, z = 0): 5 of 10 (GILD, AZN, ABBV, BMY, NVO). Their Needle column shows the provisional pick (highest S among findings with O at or above the company median) or, failing that, the 'floor relaxed' pick (top-quartile O within the company).

Blocks: A accounting, T text/disclosure, C calls, P policy/contractual, L label, X outside data, F footnote.

## 1. AMGN  L = 0.3412
Constants: Rev_TTM 38,095.0, t 0.1501, D 544.0M, sigma_EPS 0.3452 USD. Largest finding share 47%. Findings 53, withheld 22. Flags: none

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.32131 | 4.981 | 0.758 | 1.000 | 0.0851 | MEDIUM | A | Days sales outstanding 93 days (Q2 2026) vs peers; peer median 72 days, z +1.8 |
| 2 | 0.23749 | 4.981 | 0.758 | 1.000 | 0.0629 | MEDIUM | A | Receivables +17.5% YoY vs revenue +9.5% (Q2 2026); gap +8.0 pts; peer median -0.3 pts, z +1.2 |
| 3 | 0.06257 | 0.320 | 0.196 | 1.000 | 1.0000 | HIGH | P | Otezla's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $994.0M; base list discount 65%. |
| 4 | 0.03564 | 4.981 | 0.275 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: ira, gtn, 340b, litigation, supply, pricing) |
| 5 | 0.03297 | 4.981 | 0.393 | 0.745 | 0.0226 | MEDIUM | T | stronger wording in risk factors vs FY2024 (topics: supply, ai); hedges dropped: could |

## 2. GILD  L = 0.2838
Constants: Rev_TTM 30,457.0, t 0.1854, D 1,243.0M, sigma_EPS 0.4031 USD. Largest finding share 96%. Findings 36, withheld 13. Flags: TTM GAAP ETR -0.657 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.74857 | 2.539 | 0.295 | 1.000 | 1.0000 | HIGH | P | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; base list discount 66%. |
| 2 | 0.01067 | 1.430 | 0.287 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in MD&A vs FY2024 (topics: generic, litigation, supply) |
| 3 | 0.00790 | 1.430 | 0.328 | 0.745 | 0.0226 | MEDIUM | T | stronger wording in risk factors vs FY2024 (topics: supply); hedges dropped: may |
| 4 | 0.00790 | 1.430 | 0.328 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: supply) |
| 5 | 0.00691 | 1.430 | 0.287 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: ira, mfn, tariff, gtn, supply, pricing) |

## 3. JNJ  L = 0.1666
Constants: Rev_TTM 97,929.0, t 0.1651, D 2,440.1M, sigma_EPS 0.1457 USD. Largest finding share 71%. Findings 44, withheld 21. Flags: none

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.20327 | 6.644 | 0.657 | 1.000 | 0.0466 | MEDIUM | A | Inventory +12.9% YoY vs revenue +6.6% (Q2 2026); gap +6.3 pts; peer median -4.5 pts, z +0.7 |
| 2 | 0.03578 | 6.644 | 0.320 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: pricing) |
| 3 | 0.02182 | 6.644 | 0.195 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 |
| 4 | 0.01251 | 6.644 | 0.312 | 0.745 | 0.0081 | MEDIUM | T | stronger wording in MD&A vs FY2024 (topics: pricing, china); new risk vocabulary: substantial; new figures: $9.3, 1.1%, 2025; new topics:... |
| 5 | 0.01171 | 6.644 | 0.430 | 0.745 | 0.0055 | MEDIUM | C | Jennifer Taubert deflected a gtn question in 2026Q1 ('more to come'); asked: 'Great, thanks for taking the question and congrats on all t... |

## 4. AZN  L = 0.1076
Constants: Rev_TTM 58,739.0, t 0.1749, D 1,562.0M, sigma_EPS 0.4189 USD. Largest finding share 30%. Findings 51, withheld 11. Flags: annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4)

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.07464 | 2.140 | 0.410 | 1.000 | 0.0851 | MEDIUM | A | DSO 64 days vs 56 a year earlier (+13.5%) (FY2025); peer median 72 days, z -0.7 |
| 2 | 0.05517 | 2.140 | 0.410 | 1.000 | 0.0629 | MEDIUM | A | Receivables +23.3% YoY vs revenue +8.6% (FY2025); gap +14.7 pts; peer median -0.3 pts, z +2.1 |
| 3 | 0.05517 | 2.140 | 0.410 | 1.000 | 0.0629 | MEDIUM | A | Receivables-vs-revenue growth gap +14.7 pts (FY2025) vs peers; peer median -0.3 pts, z +2.1 |
| 4 | 0.03270 | 2.140 | 0.328 | 1.000 | 0.0466 | MEDIUM | A | Inventory +24.0% YoY vs revenue +8.6% (FY2025); gap +15.4 pts; peer median -4.5 pts, z +1.3 |
| 5 | 0.03235 | 0.386 | 0.084 | 1.000 | 1.0000 | HIGH | P | Calquence's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,614.2M; base list discount 40%. |

## 5. MRK  L = 0.0970
Constants: Rev_TTM 66,569.0, t 0.1854, D 2,470.0M, sigma_EPS 0.2554 USD. Largest finding share 55%. Findings 50, withheld 25. Flags: TTM GAAP ETR 0.467 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.08003 | 2.483 | 0.764 | 1.000 | 0.0422 | MEDIUM | A | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1 |
| 2 | 0.02646 | 2.483 | 0.410 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in MD&A vs FY2024 (topics: litigation) |
| 3 | 0.01371 | 2.483 | 0.328 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: gtn, pricing) |
| 4 | 0.01323 | 2.483 | 0.205 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in MD&A vs FY2024 (topics: generic, litigation, pricing) |
| 5 | 0.01323 | 2.483 | 0.205 | 0.745 | 0.0349 | MEDIUM | T | reworded paragraph in risk factors vs FY2024 (topics: generic, litigation, pricing); new figures: 2029 |

## 6. ABBV  L = 0.0703
Constants: Rev_TTM 64,386.0, t 0.2739, D 1,771.0M, sigma_EPS 0.5227 USD. Largest finding share 44%. Findings 34, withheld 16. Flags: none

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.07247 | 0.432 | 0.168 | 1.000 | 1.0000 | HIGH | P | Linzess's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,937.9M; base list discount 75%. |
| 2 | 0.04566 | 0.206 | 0.221 | 1.000 | 1.0000 | HIGH | P | Botox's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,143.1M; base list discount 66%. |
| 3 | 0.02382 | 0.142 | 0.168 | 1.000 | 1.0000 | HIGH | P | Vraylar's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $1,085.8M; base list discount 44%. |
| 4 | 0.01531 | 1.459 | 0.404 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in MD&A vs FY2024 (topics: litigation) |
| 5 | 0.00595 | 1.459 | 0.242 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: tariff, supply) |

## 7. BMY  L = 0.0417
Constants: Rev_TTM 49,186.0, t 0.2212, D 2,048.0M, sigma_EPS 0.4778 USD. Largest finding share 61%. Findings 38, withheld 13. Flags: none

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.05235 | 0.625 | 0.084 | 1.000 | 1.0000 | HIGH | P | Pomalyst's Medicare price is set by negotiation from January 2027: CMS Part B+D spend $2,069.1M; base list discount 60%. |
| 2 | 0.01611 | 0.146 | 0.111 | 1.000 | 1.0000 | HIGH | P | Orencia's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $2,450.1M; base list discount 66%. |
| 3 | 0.00669 | 1.131 | 0.351 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: tariff) |
| 4 | 0.00574 | 1.131 | 0.195 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in MD&A vs FY2024 (topics: litigation, pricing) |
| 5 | 0.00446 | 1.131 | 0.234 | 0.745 | 0.0226 | MEDIUM | T | stronger wording in risk factors vs FY2024 (topics: supply, ai); new risk vocabulary: significant; new topics: ai |

## 8. LLY  L = 0.0399
Constants: Rev_TTM 79,665.0, t 0.2049, D 893.7M, sigma_EPS 2.0295 USD. Largest finding share 49%. Findings 45, withheld 16. Flags: none

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.03044 | 0.165 | 0.184 | 1.000 | 1.0000 | HIGH | P | Verzenio's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,428.7M; base list discount 50%. |
| 2 | 0.01217 | 0.066 | 0.184 | 1.000 | 1.0000 | HIGH | P | Trulicity's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $4,898.4M; base list discount 71%. |
| 3 | 0.00973 | 1.009 | 0.303 | 1.000 | 0.0318 | MEDIUM | A | Days inventory 469 days (Q2 2026) vs peers; peer median 187 days, z +2.9 |
| 4 | 0.00719 | 1.009 | 0.274 | 0.745 | 0.0349 | MEDIUM | T | stronger wording in risk factors vs FY2024 (topics: generic, litigation); hedges dropped: could |
| 5 | 0.00266 | 1.009 | 0.157 | 0.745 | 0.0226 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: tariff, supply, china) |

## 9. NVO  L = 0.0281
Constants: Rev_TTM 309,064.0, t 0.2153, D 4,447.7M, sigma_EPS 0.6160 DKK. Largest finding share 52%. Findings 51, withheld 5. Flags: annual filer (20-F): Rev_TTM, t from the latest fiscal year (section 7.4)

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.03690 | 2.557 | 0.342 | 1.000 | 0.0422 | MEDIUM | A | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1 |
| 2 | 0.02716 | 2.557 | 0.228 | 1.000 | 0.0466 | MEDIUM | A | Inventory +21.5% YoY vs revenue +6.4% (FY2025); gap +15.1 pts; peer median -4.5 pts, z +1.3 |
| 3 | 0.00278 | 2.557 | 0.388 | 1.000 | 0.0028 | MEDIUM | X | CAH filing paragraph that discusses the GLP-1 class next to inventory, pricing or channel language: context for how NVO's product reaches... |
| 4 | 0.00188 | 2.557 | 0.262 | 1.000 | 0.0028 | MEDIUM | X | CAH filing paragraph that discusses the GLP-1 class next to inventory, pricing or channel language: context for how NVO's product reaches... |
| 5 | 0.00161 | 2.557 | 0.037 | 0.745 | 0.0226 | MEDIUM | T | paragraph dropped from risk factors vs FY2024 (topics: supply, china) |

## 10. PFE  L = 0.0180
Constants: Rev_TTM 63,696.0, t 0.1854, D 5,699.0M, sigma_EPS 0.2509 USD. Largest finding share 29%. Findings 46, withheld 19. Flags: TTM GAAP ETR -0.039 outside [0, 0.40] (one-off charges); peer median TTM ETR used

| # | S | M | O | E | pi | Conf | Block | Finding |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.01013 | 1.048 | 0.372 | 0.745 | 0.0349 | MEDIUM | T | new paragraph in risk factors vs FY2024 (topics: litigation, ai) |
| 2 | 0.00795 | 0.043 | 0.184 | 1.000 | 1.0000 | HIGH | P | Xeljanz's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,013.3M; base list discount 66%. |
| 3 | 0.00563 | 1.048 | 0.206 | 0.745 | 0.0349 | MEDIUM | T | stronger wording in risk factors vs FY2024 (topics: mfn, generic, litigation, supply, pricing); hedges dropped: potential; new figures: 1... |
| 4 | 0.00563 | 1.048 | 0.206 | 0.745 | 0.0349 | MEDIUM | T | reworded paragraph in MD&A vs FY2024 (topics: generic, litigation); new figures: $1.5 |
| 5 | 0.00563 | 1.048 | 0.206 | 0.745 | 0.0349 | MEDIUM | T | reworded paragraph in MD&A vs FY2024 (topics: generic, litigation) |

