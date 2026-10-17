# MRK (Merck) nuggets

Ten verified nuggets, all 66 evidence quotes passed `agent.needle.pages.check`. Rows: `docs/nuggets/MRK.jsonl`. Misses and corrections: `docs/nuggets/MRK_ai_caught.jsonl`.
EPS math throughout: pretax $M x (1 - 13.3%) / 2,507M diluted shares (2025 tax 2,804 / 21,067 and net income 18,254 / EPS 7.28, MRK 10-K FY2025 p.77). Assumptions are labelled in each row's `impact.formula`.

## Ranked findings

| # | Finding | Source | Impact (math) | Peer comparison | Confidence |
|---|---|---|---|---|---|
| 1 (001) | The 2.5% royalty Merck pays BMS and Ono on all Keytruda and Keytruda Qlex sales ends after Dec 31, 2026: about $0.8B of cost of sales disappears in 2027, one year before the compound patent expires. | MRK 10-K FY2025 p.54; MRK 10-Q 2026Q2 p.34; BMY 10-K FY2025 p.32, p.89; BMY 10-Q 2026Q2 p.10 | BMY H1 2026 $308M / 0.75 x 2 = $821M (base); 2.5% x $31,680M = $792M (bear); $847M (bull). 3.9% of 2025 pretax; +$0.28 EPS in 2027 | BMS books $588M (75% share) in 2025, which grosses up to $784M, matching Merck's 2.5% x sales within 1%. Tecentriq royalty to BMS ends the same day. | High |
| 2 (002) | CFO said in Oct 2025 the ACIP HPV dosing decision "will very much impact" US Gardasil growth; after CDC cut adolescents to one dose, the 10-K and 10-Qs say "not material". The change is only stayed by a Mar 16, 2026 court injunction. | MRK 2025Q3 call p.14 to 15 (Divan, Litchfield); MRK 10-K FY2025 p.56, p.132; MRK 10-Q 2026Q2 p.28, p.35 | US Gardasil $2,641M x 9-14 cohort share 40% (assumption) x 50% fewer doses = $528M revenue (bear $660M, bull $330M); $0.14 EPS | H1 2026 US Gardasil already -5% ($1,027M vs $1,082M) with the change stayed | Medium |
| 3 (003) | The royalty bill migrates rather than vanishes: Winrevair (+81% in H1 2026) pays 22% of sales to BMS and carries a $5.4B intangible. | MRK 10-K FY2025 p.58, p.105, p.132; MRK 10-Q 2026Q2 p.37; BMY 10-K FY2025 p.90 | $1,443M x 1.81 (H1 growth, assumption) x 22% = $575M in 2026 (bear $635M, bull $556M), about 70% of the Keytruda royalty that ends; $220M per extra $1B of sales | BMS reports $289M Winrevair royalty income for 2025 vs $317M implied; gap logged | High |
| 4 (004) | 2026 R&D is reduced by $700M of Blackstone funding for sac-TMT; it does not repeat in 2027 and Blackstone gets low-to-mid single-digit royalties on all sac-TMT sales after first-line TNBC approval. | MRK 10-Q 2026Q2 p.7 | $700M R&D step-up in 2027 (bull $500M if spend is trimmed); -$0.24 EPS | None checked | High |
| 5 (005) | Keytruda Qlex, the IV-biosimilar defense, is enjoined in Germany by Halozyme (appeal hearing Nov 19, 2026), faces a Dutch counterclaim covering seven more countries, and Merck warns of possible "additional royalties" on Qlex, as Qlex sales reach $463M a quarter. | MRK 10-Q 2026Q2 p.22, p.34; MRK 2026Q2 call p.4; MRK 2025Q4 call p.11; MRK 10-K FY2025 p.132 | 35% Qlex adoption (Davis 30% to 40% by 2028) x $18,829M US Keytruda = $6,590M x 3% royalty (assumption) = $198M a year (bear 5% = $330M, bull 0); $0.07 EPS | BMS's Opdivo Qvantig label lists Halozyme as co-manufacturer (licensed); Merck chose Alteogen and litigates | Medium |
| 6 (006) | The cost of the Qlex switch never reaches non-GAAP EPS: $930M of Alteogen milestones capitalized and amortized to 2030, FY2025 non-GAAP definition widened to asset acquisitions, GAAP amortization up from $2.8B to $3.8B in 2026. Enriches MRK-forensics-641472. | MRK 10-K FY2025 p.64, p.89, p.106; MRK 10-K FY2024 p.61; MRK 10-Q 2026Q2 p.39 | +$1.0B GAAP-only amortization in 2026 ($0.35 GAAP EPS); Qlex share $930M / 5.3 yrs = $176M a year | FY2024 definition covered only "collaborations and licensing arrangements" | Medium |
| 7 (010) | Asked how much of the 50/50 US split would shift to price equalization, Robert Davis said he was "not going to get into" it; seven weeks later the MFN deal tied every launch in its three-year term (Lipfendra first) to MFN-country prices. Enriches MRK-calls-482796. | MRK 2025Q3 call p.14 (Breen, Davis); MRK 10-K FY2025 p.8, p.32; MRK 2026Q2 call p.13 to 14 | $70B launch opportunity x 50% US x 30% launched in term (assumption) x 10% MFN gap (assumption) = $1,050M peak revenue (bear $2.1B, bull $525M); $0.27 EPS | Section 232 tariff delay ends about Dec 2028, the same window as Keytruda compound patent (Dec 2028) and expected Keytruda IRA price (Jan 2029) | Low |
| 8 (007) | A second royalty ladder: Capvaxive and Vaxneuvance royalties fall from 7.25% to 2.5% in 2027 and the 7% US Gardasil royalty ends Dec 2028. | MRK 10-K FY2025 p.57, p.132 | ($759M + $825M) x 4.75% = $75M (2027) + 7% x $2,641M = $185M (2029) = $260M a year (bear $214M); $0.09 EPS | None checked | High |
| 9 (008) | Lenvima ($1.05B Eisai alliance) was selected in Jan 2026 for a Medicare set price effective Jan 1, 2028; settled generics can enter July 2030. | MRK 10-K FY2025 p.9, p.116, p.132 | $737M US profit share x 50% Medicare (assumption) x 40% cut (assumption) = $147M a year 2028 to mid-2030 (bear $221M, bull $92M); $0.05 EPS | Eisai bears the other half; no Eisai filing in corpus | Medium |
| 10 (009) | 75% of 2025 Koselugo alliance revenue ($325M of $436M) was one-off AstraZeneca cash booked as Sales, and AstraZeneca can revert to profit sharing in Jan 2027 or Jan 2028, cancelling the remaining $150M and $100M payments and royalties. | MRK 10-K FY2025 p.53; MRK 10-Q 2026Q2 p.8 | $150M 2027 payment at risk (bear $250M, bull 0); $0.05 EPS | Option sits with AstraZeneca, so it is exercised only when it hurts Merck | Medium |

## Sharpest Needle candidate

**MRK-nugget-001, the Keytruda royalty roll-off.** It is the only MRK finding that is contractual, footnote-only (zero mentions of "royalt" on four calls), and confirmed from the counterparty's own filing: BMS's $588M share grossed up by its 75% split lands within 1% of Merck's 2.5% x $31.7B. It is worth about $0.82B of pretax income and $0.28 of EPS in 2027, and it cuts against the expected story. Merck's margin gets a one-time lift in the very year before the patent cliff, which can make 2027 look like underlying strength. It beats the runner-up, the Gardasil single-dose contradiction (002), because 002 depends on an assumed adolescent revenue share and on how a court stay is resolved, while 001 is arithmetic on two audited filings. Pair it with 003 on the slide: the Keytruda royalty ends just as a 22% Winrevair royalty grows to about 70% of its size, so the net 2027 royalty tailwind is smaller than the headline.

## Part 2 hooks

- 001: Bank the 2027 royalty roll-off as a one-year bridge to fund Qlex conversion and launches; do not present it as growth.
- 002: Kill signal for a US Gardasil recovery plan: if the Mar 16, 2026 stay is lifted, cut US Gardasil by about a quarter.
- 003: Haircut royalty-burdened launches (Winrevair 22%, sac-TMT to Kelun and Blackstone) against wholly owned assets when sizing the Keytruda replacement.
- 004: Net the $700M Blackstone credit out of any 2026 operating-leverage claim; weigh repeat financings against the royalty they sell.
- 005: Kill signal: an adverse German appeal (Nov 19, 2026) or Dutch ruling lowers the Qlex conversion behind the "hill not cliff" LOE story.
- 006: Judge launch-funded growth on GAAP margins; the gap to non-GAAP widens by $1.0B in 2026.
- 010: Sequencing move: delay or price high the ex-US launches of Lipfendra and sac-TMT during the MFN term to protect US price.

## Rejected nuggets

- Contingent consideration from acquisitions: the business-combination liability is only $193M (MRK 10-K FY2025 p.103, fair value table), below the 1% of operating income bar.
- Terns $5.7B acquired IPR&D charge and the resulting 46.7% trailing tax rate: one-off, already routed to out/MRK/context.jsonl.
- Gardasil China (revised Zhifei contract in April 2026, revenue "immaterial in 2026"): already flagged by code drift rows MRK-drift-621121 and 854992; the new contract adds no dollar figure.
- Reblozyl royalty halving on patent expiry or generic entry (10-Q 2026Q2 collaboration note): no Reblozyl expiry date in the corpus, so no date or dollar path.
- Animal Health (Bravecto $1.1B, 18% of segment): no fine-print item beyond the existing concentration risk factor.
- Keytruda IRA selection expected 2027 for a Jan 1, 2029 price: Merck states it in the 10-K and Davis repeats it on the 2025Q4 call; too close to the starter thread.
- Keytruda patents to May or Nov 2029 (Davis, 2025Q4 call): analyst-asked and part of the starter-thread patent story.
