# AZN nuggets (AstraZeneca, 20-F filer, USD)

Mined 17 Oct 2026 from `data/corpus/companies/AZN`, the CMS IRA file and the drug packs. Every quote in `AZN.jsonl` passes `agent.needle.pages.check`. Verifier misses and analytic corrections are logged in `AZN_ai_caught.jsonl`. Starter thread (cancer growth, Farxiga exclusivity loss, US pricing politics) is not restated.

## Ranked findings

| # | Finding | Source | Impact (math) | Peer comparison | Confidence |
|---|---|---|---|---|---|
| 1 | US gross sales +16.6% but net sales +8.3% in 2025. Managed care and Medicare deductions +29%, and net/gross fell from 53.3% to 49.5%. The Audit Committee "requested a review of the nature and accounting for sales incentives". | AZN 20-F FY2025, p. 34 (GTN table), p. F-32 (US accrual $5,941m vs $4,978m), p. 27 (Q4 GTN true-ups on Fasenra, Breztri); Annual Report 2025, p. 85 | 47,385 x 53.3% - 23,444 = $1,804m revenue vs 2024 rate; EPS 1,804 x 0.8 / 1,550 = $0.93. Each further 1 pt = $474m (3.4% of op. profit 13,743). 2023 rate was 49.1%, so 2024 may be the outlier year | GSK US net/gross 53.7% to 52.2% (-1.5 pts) and its accrual fell; AZN -3.8 pts and its accrual rose 19% (GSK 20-F FY2025) | High |
| 2 | Calquence's Medicare price from Jan 2027 is $8,600 per 30 days: 38% below the 2024 Part D claim ($13,910) and 10% below Imbruvica's MFP. Brukinsa, not selected, keeps its pricing. | CMS MFP file; CMS Part D DY2024; AZN 20-F FY2025, p. 26; Annual Report 2025, p. 35, p. 191 (AZN suing HHS) | Part D net 1,702 x 0.8 = $1,362m x 22.7% cut = $309m/yr (bear $479m, bull $139m); EPS $0.16. Assumes net = 80% of gross | Imbruvica MFP $9,571 (2027); Brukinsa Part D $1,724m in 2024, up from $801m | Medium |
| 3 | The code's needle (receivables +14.7 pts over revenue) comes from factoring, not collections. Factorable receivables and China bank acceptance drafts rose from $667m to $2,681m. All other trade receivables fell 0.8%. | AZN 20-F FY2025, p. F-29; 20-F FY2024, p. F-29; 6-K 2026-07-27, p. 31 | (10,289 - 2,681) / (8,335 - 667) - 1 = -0.8%. Code's $1,219m at risk becomes about $0 (bear $54m at 2% loss on the pool). Already reversing: $14,330m at H1 2026 | Gap moves from +14.7 pts to about -9.4 pts, below the -0.3 pt peer median | High |
| 4 | Enhertu sales-related payables to Daiichi Sankyo: $673m due within a year (2024: $377m). Total sales-linked partner payables $1,952m (+$657m). | AZN 20-F FY2025, p. F-33, p. F-28 (50:50 profit split) | 673 = 4.9% of op. profit in 2026 cash. If capitalised, the +$419m adds about $52m/yr Reported amortisation (treatment inferred) | Counterparty filings not in corpus | Medium |
| 5 | The BMS diabetes earn-out ($1,164m cash in 2025) ends with a final $257m in 2026. | AZN 20-F FY2025, p. F-33, p. F-5 | 1,164 - 257 = $907m/yr cash tailwind from 2027 (bear $614m, bull $1,164m). Core EPS unaffected | None comparable in corpus | High |
| 6 | MFN never sized. CFO Sarin: the headwind is "already factored in our guidance". On launch pricing, Fredrickson (to Peter Verdult, BNP): "we don't give brand-specific pricing commentary on MFN and don't plan to". The H1 2026 report names the agreement as a gross-margin drag. | 2025Q4 and 2026Q2 calls (third_party allmind.ai); 6-K 2026-07-27, p. 21 | Sensitivity: 1% of US net sales 23,444 = $234m; base 2% = $469m, EPS $0.24 (assumption) | Not run; PFE and MRK MFN disclosure is the next contrast | Medium |
| 7 | The tariff exemption is "three years" from Oct 2025 (about Oct 2028, not Jan 2029). The onshoring promise softened from "all" (press release) to "substantially all" (annual report). Most APIs are still externally sourced. | Press release 2025-10-10; Annual Report 2025, p. 35; 20-F FY2025, p. F-5; 2025Q4 call (Sarin) | 23,444 x 10% imported x 25% transfer value x 100% tariff = $586m/yr (bear $1,172m); EPS $0.30. All shares assumed. Capex $2.8bn (2025), about $3.7bn (2026) vs $10bn/yr headline | Not run | Low |
| 8 | Prosecutors indicted the China operating company itself in Nov 2025 on illegal-trade and personal-data charges linked to Imfinzi, Imjudo and Enhertu imports. Not raised on any call. | AZN 20-F FY2025, p. F-57, F-58; Annual Report 2025, p. 35 | Fine 1x to 5x of $3.5m = up to $17.5m. Bear: 5% of China revenue 6,654 = $333m (assumption) | No peer discloses a China entity indictment | Low |
| 9 | Tagrisso's 2024 Part D spend ($1.63bn) beats four drugs selected for 2028 negotiation, yet it is on no list. Three Paragraph IV filers are lined up. | CMS Part D DY2024; CMS MFP file; FDA Paragraph IV list; AZN 20-F FY2025, p. 26 | If selected for 2029: 1,627 x 0.8 x 22.7% = $295m/yr; EPS $0.15. Eligibility unconfirmed (needs_human) | Erleada $1,386m, Verzenio $1,057m: both selected | Low |

## Sharpest Needle candidate

**#1, the US gross-to-net give-back.** In 2025 AstraZeneca booked $6.7bn more US gross sales but kept only $1.8bn more net revenue. Managed care and Medicare deductions grew 29% against 16.6% gross growth. The audit committee's request to review "the nature and accounting for sales incentives" sits in the governance section, where analysts rarely read, and nobody asked about gross-to-net on the last four calls. It is large ($1.8bn, 13% of operating profit), verified line by line from the 20-F table, and it gets worse from here: MFN repricing of Medicaid and the Calquence MFP (#2) both hit this same line in 2026 to 2027. It beats the runner-up, the Calquence MFP, because #2 is one product and partly public (an analyst asked in Q3 2025), while #1 covers the whole US book and is visible only in the footnotes. One honest caveat: 2023's ratio (49.1%) was close to 2025's, so we frame it as "the 2024 improvement fully reversed", not a new low.

## Part 2 hooks

- Price new US launches (camizestrant, baxdrostat) for MFN and PBM reality from day one. Use DTC/TrumpRx and value-based contracts rather than list price plus rebates (#1, #6).
- Kill signal: if the Virginia plant is not producing by roughly October 2028, tariff cost lands before the January 2029 date most models use (#7).
- Use the roughly $0.9bn/yr freed by the end of the BMS earn-out (#5) to fund US capex without new debt. Net out the Enhertu partner payments (#4) before counting ADC growth as owned cash.
- Calquence: move lifecycle spend to fixed-duration combinations instead of defending Part D share at an MFP 10% below Imbruvica while Brukinsa prices freely (#2).
- Kill signal for China-led growth plans: the Shenzhen court trial date (#8).
- Drop the receivables flag from the deck as a red flag. Present it as an example of the tool catching its own false positive (#3).

## Rejected nuggets

- Gross margin metric switched from Product Sales to Total Revenue (Annual Report p. 85). Including Alliance Revenue of $3,067m lifts the reported margin by about 1.0 pt (81.9% vs 80.9%). That is optics only, below the materiality bar.
- Farxiga MFP of $178.50 per 30 days vs $939 per 2024 Part D claim: real, but the 2026 generic entry is the starter thread and swamps it.
- Inventory +24% vs revenue (code row): already in the code output and raised on calls. The $407m Andexxa provision reversal (20-F p. F-29) explains part of it.
- Seagen 8% Enhertu royalty judgment (20-F p. F-52): covers 2022 to 2024 sales only, the patent was ruled unpatentable by the USPTO, and AZN bears half via the 50:50 split. Small and backward-looking.
- China rebate accrual $619m vs $532m (20-F p. F-32): +16%, but too small to matter alone.
- Legal provisions cash paid of $720m in 2025 (20-F p. F-33): the matter behind it was not traced in time, so it was not used.
