# Fix notes 2 (branch quant-model, from 1551f27)

The only deadline is the Sunday 2:00 pm Devpost submission. Pitch-facing outputs: `out/<T>/findings_table.*` (impact-ranked, plain-rule needle, now with a peer column), `out/<T>/product_<p>.md` and `out/<T>/decide.md`. The league stays internal. Run used for every number below: `python -m agent.needle.quant.run --all --nuggets docs/nuggets/` on this branch, citation index as on disk at 2026-10-17 evening (the scraper's I/B/E/S `facts.ticker` fix included).

## Commits

| Commit | Item |
|---|---|
| f8b6eb8 | 1. Nuggets ingest for all ten companies |
| ff21dec | 2 (a-c). MFN marker, Biktarvy 2036 and first set-price-year precedents, receivables footnote read |
| 68d120a | 2 (d, e). LOE dates from loe_calendar and filings; turn-label speaker check |
| d1d900e | 3 (a) and audit 5, 6. Gated peer comparison per finding, page labels in footnotes, reporting currency |
| 4054a46 | 3 (b-d) and audit 1-4. DECIDE "Why it will work", "Why we passed", cash-at-risk reason; product limiter, priced-in, dosing |
| ace3c6a | 4. GILD demo moves fixture |
| 3079c1f | 3 (a) fix: a withheld peer line prints no count |
| (this commit) | 5, 6. Re-run, notes |

## 1. Nuggets ingest

Source: Parker's `docs/nuggets/<T>.jsonl` copied verbatim from origin/needle `b908519f59f78ed7aad86e2d224274d53f423648` (`docs/nuggets/NOTE.md`). The rows carry no `best_needle` field; `docs/nuggets/best_needle.json` records the best needle per company from `docs/red_team_v3_final.md` section (a), and the loader sets it.

How a nugget row is handled (`find.score_nugget`, `run.enrich`):
- Impact: the nugget's own bull / base / bear estimate on its P&L line, translated on FIND's constants. Revenue: dRev x CM (1.00 for gtn, forces, footnotes; 0.70 otherwise) x (1 - t) / D. Operating income: x (1 - t) / D. EPS line: below operating income (dOI 0); tax items carry no tax shield. Free-cash-flow rows (NVO 001, 010) are not quantified on EPS. The estimate prints as a labelled assumption ("nugget-miner estimate ..., Parker's derivation, not re-derived by FIND").
- Evidence: every quote runs our ladder. E is taken over the quotes that verify (a quote that fails is dropped from the evidence and flagged; none verified gives E = 0).
- Sentence numbers are supported, in order, by: a verified quote; a verified line of a page the nugget already cites; a code derivation from two quoted figures (a - b, a + b, growth, share, share of a total, points, change of scale; operands of two or more digits; three significant digits unless both figures sit in one quote or share a scale word); a labelled assumption when the number restates the nugget's own estimate or is printed in its impact derivation. Anything else fails the gate.
- Rows with `slide_ready` false or `verdict` needs_human are kept, flagged and never the needle. `best_needle` false is a flag only. The detector guards apply by kind.
- `enriches`: matched by the needle branch's id scheme (`<T>-<detector>-<sha256(kind|detail) mod 10^6>`), else by a shared cited page and a quoted figure. A match shares one fact key (counted once in the league; one row per fact in the findings table, the larger impact kept and the other listed under `merged_rows`), and up to three of the nugget's verified quotes are added to our row.

| Company | Nugget rows | Pass the gate (shown) | Fail the gate | enriches named | matched by id | matched by page | unmatched |
|---|---|---|---|---|---|---|---|
| ABBV | 8 | 7 | 1 | 4 | 1 | 1 | 2 |
| AMGN | 11 | 7 | 4 | 2 | 2 | 0 | 0 |
| AZN | 11 | 6 | 5 | 2 | 2 | 0 | 0 |
| BMY | 7 | 7 | 0 | 3 | 1 | 0 | 2 |
| GILD | 9 | 7 | 2 | 5 | 1 | 2 | 2 |
| JNJ | 10 | 7 | 3 | 2 | 1 | 0 | 1 |
| LLY | 9 | 9 | 0 | 3 | 1 | 1 | 1 |
| MRK | 12 | 8 | 4 | 2 | 1 | 0 | 1 |
| NVO | 10 | 4 | 6 | 6 | 6 | 0 | 0 |
| PFE | 10 | 8 | 2 | 4 | 2 | 1 | 1 |
| **Total** | **97** | **70** | **27** | **33** | **18** | **5** | **10** |

Unmatched enriches ids name drift and call rows whose detector text differs on this branch (the id hashes the detail text). Failing rows keep at least one number with no quote, derivation or estimate behind it; they are in `out/<T>/rejected_v3.jsonl` with `rejected_by: numeric_gate` and the unsupported numbers.

## 2. Parker's corrections (thread #19), before and after

| | Before | After |
|---|---|---|
| (a) MFN | Placeholder rows printed `s_MFN (0.003, 0.0065, 0.01)[constant: S_MFN]` and an unmarked dEPS in the table; a placeholder row was needle-blocked only when needle-eligible | The formula and the table's impact cell print `[assumption: no public MFN rate; terms confidential]`; M keeps the 0.65% internally; every placeholder row is needle-blocked; the sentence prints no dollar figure. Renderer: a label `marker: <text>` prints `[assumption: <text>]` |
| (b) GILD Biktarvy | IRA row: CMS spend and assumed discount only; product timeline read a cache (2033 projection) | The IRA row adds "US generic entry no earlier than April 1, 2036 under the patent settlements (10-K)" (GILD 10-K FY2025 file page 37) and the two first set-price-year precedents: bear, Amgen ENBREL net selling price -22% under Part D price setting (AMGN 10-Q Q2 2026 file page 40); bull, Eliquis revenue +22% after BMS's list-price cut (BMY 10-Q Q2 2026 file page 35). Product timeline: Company-stated US LOE 2036-04-01 (loe_calendar settlement row, 10-K) |
| (c) Receivables guard | AMGN's receivables row (+8.0-pt gap, anchor $1.79 a share) was AMGN's strict needle; AZN's DSO row was AZN's needle | A footnote read of the cited filing and the latest annual report (factoring, FVOCI receivables, bank acceptance drafts, gross billing with a separate rebate liability). AMGN: explained by footnote (sales-deduction liability 8,405 to 10,606, +2,201, against receivables +2,788; net 587; 10-K FY2025 file pages 83 and 109), impact lowered to the net movement (dEPS 0.64), needle-ineligible. AZN: explained by footnote (FVOCI receivables it can factor and China bank acceptance drafts, 667 to 2,681, against trade receivables 8,335 to 10,289; net -60; 20-F FY2025 p. F-29), impact 0, needle-ineligible. A row with terms found but no net movement is needle-ineligible; the read never raises an impact |
| (d) Label exclusivity | Product timelines printed "Orange/Purple Book protection ends 2031 vs company-stated 2028" (Keytruda's orphan date); FIND fell back to the labels_table date | `verified_tables.loe`: settlement entry date first (loe_calendar settlement row, else a dated settlement sentence in the latest 10-Q/10-K), then company_stated_loe (a bare year takes the Orange Book rule date in that year, cited), else rule_output_loe; never labels_table. Results: Keytruda 2028 (not 2031), Ibrance 2027-09-05, Vyndamax 2031-06-01 (PFE 10-Q Q2 2026 file page 29), Enbrel 2028-11-22 (core patent; DNA patent 4/24/2029), Darzalex 2029, Biktarvy 2036-04-01. The labels profile no longer counts orphan exclusivity as protection; labels_table.json regenerated (no Keytruda 2031-01-25). exclusivity_earlier rows without a loe_calendar date on both sides are dropped |
| (e) Speaker check | A named speaker passed if the surname appeared anywhere in the 4,000 characters before the quote, so "Greg Renza" passed for Anish Nikhanj's question (the operator named Renza); long prepared remarks failed | The named speaker must be the label of the turn that contains the quote, read from turn labels in the markdown, Refinitiv, roic.ai, Benzinga, plain-colon and Operator layouts; no window. Tests: the GILD Q2 2026 case (synthetic and real index) and a prepared-remarks turn longer than 4,000 characters |

## 3. Case gaps in the pitch outputs

- (a) Every findings-table row has `peer_comparison` (column "Peer comparison"): forensics rows give the same metric for every shortlist company from XBRL, the median derived from the cited per-company values, and the nearest named peer; IRA rows name another shortlist drug selected for the same year with its CMS spend cited; MFN rows name another company's cited Medicaid MFN term; LOE rows give the rival maker's company-stated LOE; label rows name the rival; nugget rows gate the nugget's own peer note. Otherwise "no comparable disclosure: <reason>"; a comparison that fails the gate is replaced by that line.
- (b) decide.md has "Why it will work: the evidence each decider needs": doctors (Part D prescribers, growth and concentration from the rx tables), payers (formulary coverage, or "Part B drug"), regulators (latest verified FDA calendar row naming the product), investors (quarters in which analysts named the product in qa_turns, one question cited to its transcript page), the interview-only column, and "No prescriber, payer, regulator or investor interview was run".
- (c) Each rejected alternative carries one "Why we passed" sentence on the five numbers and the binding reason (the old binding-reason lines were withheld by the gate because "120" had no label).
- (d) Growth-limiter sentences are present: Keytruda (loss of US exclusivity, $5.35B base, revenue operand cited to the 10-K sales line), Repatha (loss of US exclusivity, 2029-08-27), Biktarvy (the Medicare negotiated price, not yet published, $1.75B base on the CMS cuts; the CMS selected-list line cited).

Case-audit engine defects (coordinator list):
1. Limiter dollars: Opdivo's revenue was the Qvantig member ($238M); the product member is now the shortest brand member (Opdivo $10.05B, cited). The LOE limiter's revenue operand is a verified sales-table line when one prints the figure (Keytruda 18,829); the sentence says US or worldwide revenue and "median of 3 US launches in the LOE curve table, a labelled table value". Repatha's 1,663 has no single-line match in the 10-K text, so it stays a labelled table value.
2. Dosing: cells keep every regimen the quoted label sentence lists (Repatha every 2 weeks or once monthly; Praluent every 2 or 4 weeks; Cabenuva monthly or every 2 months; Keytruda every 3 or 6 weeks; Opdivo every 2 or 4 weeks). FIND drops dosing-difference rows (one regimen per label). "Titration in label" now needs an escalation or titration sentence that is not a "not recommended" line.
3. Priced-in: with no quantified channel, or no analyst-question row for the limiter's topic, the sentence says "not testable with our data" and `priced_in` is null; no verdict.
4. DECIDE: a zero cash at risk beside a budget now states why (bear inflows before the first readout cover the committed outflow, both printed); otherwise the committed outflow and inflows are printed. Kill signals are product-named and year-one sales takes the move's cited revenue input as its baseline; the evidence section is built from the company's own rows.
5. Footnotes with no page say "no page (machine-readable data row)"; page footnotes keep printed folio and file page. The peer median is derived from cited XBRL operands.
6. Impact cells print the reporting currency (DKK for NVO); no USD conversion without a cited FX rate.

## 4. GILD demo fixture

`docs/examples/moves_GILD.json` (demo: true, header note). decide_cli exit 0 for GILD, MRK and AMGN.

## 5. Needle per company under the plain rule, and Parker's red-team list

Rule: among quantified rows, the lowest analyst share asked, then the largest base-case |dEPS| (reporting currency per share). MFN placeholder rows, receivables rows explained by footnote, nuggets that are not slide-ready and guarded rows are never the needle.

| Company | Needle id | Finding | abs dEPS | Analyst share asked | Needle before (1551f27) | Parker's best needle |
|---|---|---|---|---|---|---|
| MRK | 0591acf35698 | Gross margin 73.5% vs 77.5% a year earlier (-4.0 pts) (Q2 2026); peer median 74.1%, z -0.1... | 0.66 | 0.00 | 0591acf35698 | MRK-nugget-001 (Keytruda royalty to BMS and Ono ends after 2026) |
| JNJ | 404ff62ad578 | Erleada's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $1,947.5M; base list discount 50% (CMS-published analog, cited).... | 0.23 | 0.18 | 404ff62ad578 | JNJ-nugget-010 (second wave of exclusivity losses) |
| PFE | 32f39186aaf4 (PFE-nugget-004) | Charges Pfizer keeps out of adjusted EPS as 'certain significant items' recur every year: impairments of $3.0B, $3.3B and $4.9B plus restructuring of ... | 0.82 | 0.00 | d516c2df7fcd | PFE-nugget-001 (Eliquis list-price cut) |
| BMY | 495193cbe833 (BMY-nugget-004) | Opdivo Qvantig, BMS's subcutaneous switch product, does not extend protection on BMS's own disclosure: the 10-K gives it the same 2028 US minimum excl... | 0.57 | 0.40 | 7f7c26eaeb9a | BMY-nugget-001 (Keytruda and Tecentriq royalties end) |
| AMGN | 24bbb7a6bbf3 (AMGN-nugget-001) | The receivables flag is a gross-to-net artifact, not channel stuffing: Amgen bills wholesalers at gross price, so receivables (+41% in 2025) track gro... | 1.20 | 0.10 | bc852b02400d | AMGN-nugget-006 (IRS Puerto Rico claim vs reserve) |
| NVO | 368385278158 | Gross margin 81.0% vs 84.7% a year earlier (-3.7 pts) (FY2025); peer median 74.1%, z +1.1... | 1.64 | 0.10 | 368385278158 | NVO-nugget-001 (rebate liability, cash only) |
| LLY | b1c0d840e1ed (LLY-nugget-002) | Jardiance revenue has carried a growing one-off every year (a $300M amendment payment in 2024, $570M in 2025, up to $910M of milestones limited to 202... | 0.81 | 0.50 | 4bf1a2f5e9e4 | LLY-nugget-001 (Ozempic $274 vs Mounjaro); red-team doc switched to LLY-nugget-002 |
| ABBV | 53d422aaae7b (ABBV-nugget-001) | Since the Q2 2026 10-Q, AbbVie's Skyrizi royalty extends to combination pipeline assets, with payments now projected to 2044 (38% probability for the ... | 1.46 | 0.00 | 702ebc520f15 | ABBV-nugget-001 (Skyrizi royalty) |
| GILD | 49af018377a3 | Biktarvy's Medicare price is set by negotiation from January 2028: CMS Part B+D spend $3,904.5M; assumed base list discount 65.5% (median of the cycle... | 1.29 | 0.20 | 49af018377a3 | GILD-nugget-001 (Biktarvy 2028 price) |
| AZN | b0573ba3b531 | Inventory 6,557 vs 5,288 a year earlier (+24.0%, 2025 vs 2024) against annual revenue 58,739 vs 54,073 (+8.6%); gap +15.4 pts (derived); peer median -... | 0.93 | 0.20 | c491682c6c0b | AZN-nugget-010 (chargebacks) |

How this compares with Parker's red-team list. The plain rule agrees with Parker on ABBV (Skyrizi royalty to 2044, ABBV-nugget-001) and GILD (Biktarvy's January 2028 Medicare price: our IRA row, which now carries the April 1, 2036 settlement date and the -22% and +22% first-year precedents, with Parker's GILD-nugget-001 merged into it as one fact), and on LLY with his final red-team pick (Jardiance one-off, LLY-nugget-002) rather than the Ozempic $274 vs Mounjaro row, which is marked not slide-ready. It differs on seven. On MRK, JNJ and NVO a detector or IRA row with analyst share 0.0 to 0.18 outranks his nugget (MRK gross margin -4.0 pts; JNJ Erleada's 2028 Medicare price; NVO gross margin -3.7 pts), because our share asked is measured on the row's topic in qa_turns while his obscurity rung is read on the item itself (MRK-nugget-001's topics score 0.50). AMGN's needle is the deduction-rate finding AMGN-nugget-001 (share 0.10), which is also the receivables row's footnote explanation; the IRS Puerto Rico row (AMGN-nugget-006, |dEPS| 2.39) passes the gate but carries share 0.50, so the rule ranks it below. BMY's needle is the Opdivo Qvantig protection row (BMY-nugget-004, share 0.40); the royalty row (BMY-nugget-001) scores 0.50 on its topic. PFE's needle is the recurring 'certain significant items' row (PFE-nugget-004, share 0.00); the Eliquis list-price row has share 0.90. AZN's chargeback row (AZN-nugget-010) does not pass the gate (two numbers without a quote or derivation: 7.5% and 8), so AZN falls to the inventory gap row (+15.4 pts, FY2025). NVO-nugget-001 is cash-only and not quantified on EPS, so it cannot be ranked by the dollar rule, as Parker notes. The ranking differences come from one input, the analyst-share term; a human read should decide whether to override it with Parker's rung where he checked the transcripts item by item.


## 6. Changed finding ids per company (for the UI)

Ids are sha256(ticker|kind|first citation)[:12]; nugget rows hash 'nugget|<nugget id>'. Added ids are the gated nugget rows; removed ids are rows a correction dropped: dosing-difference rows (audit 2) and, for JNJ, a call row whose quote failed the new turn-label speaker check.

- **MRK**: needle 0591acf35698 -> 0591acf35698. Added 8: 01f561376d76, 19c4fde8d3a2, 270055428844, 796df46154cc, 7fff54a278c7, a0afee4619a8, eed81303c1d7, fc8bf1fd46dd. Removed 1: 5ad818374c50 (januvia once daily (365/yr) vs ozempic once weekly (52/yr)). Merged (one fact, one row): 865a83a373d4 into 56ea4e659d72.
- **JNJ**: needle 404ff62ad578 -> 404ff62ad578. Added 7: 056e05d2dc09, 27d8d81f2265, 6648e7579d86, a0d67e31b1e7, b3b341581796, be46f62342cd, f55997ea7798. Removed 3: 482fe7f05c36 (darzalex once weekly (52/yr) vs sarclisa every 2 weeks (26/y); 4de282d495c1 (tremfya every 8 weeks (6.5/yr) vs rinvoq once daily (365/yr)); e7da89df59b6 (Jennifer Taubert deflected a other question in 2026Q2 ('we d). Merged (one fact, one row): 570485b15c91 into f55997ea7798.
- **PFE**: needle d516c2df7fcd -> 32f39186aaf4. Added 8: 24525c725d2e, 32f39186aaf4, 3ef15f7fc64b, 6b5957016f4c, 8a78af774155, 90b8742c925e, 93023c8e35b0, 99a2dabfdac5. Removed 2: 523d68a26d11 (vyndamax once daily (365/yr) vs amvuttra every 3 months (4/y); 6d14e05afcab (vyndamax once daily (365/yr) vs attruby twice daily (730/yr)). Merged (one fact, one row): 58fc7c9804c4 into 99a2dabfdac5.
- **BMY**: needle 7f7c26eaeb9a -> 495193cbe833. Added 7: 02ea659acb66, 09c2af7c308b, 26c40bb4dfae, 495193cbe833, 691218aa593b, acc8cdc96bd2, e387364988f2. Removed 1: b5f4aed59c44 (eliquis twice daily (730/yr) vs xarelto once daily (365/yr)). Merged (one fact, one row): none.
- **AMGN**: needle bc852b02400d -> 24bbb7a6bbf3. Added 7: 0dd2d4255287, 24bbb7a6bbf3, 2756b7c86172, 6301dece055e, 8fd08db29181, bc5842def326, df01b30ed900. Removed 4: 91586f346f38 (enbrel once weekly (52/yr) vs skyrizi every 12 weeks (4.3/yr); 99e6b4a7ec3d (enbrel once weekly (52/yr) vs rinvoq once daily (365/yr)); a85875859f56 (repatha monthly (12/yr) vs leqvio every 6 months (2/yr)); e736dbdb3d0f (repatha monthly (12/yr) vs lipfendra once daily (365/yr)). Merged (one fact, one row): bc852b02400d into 24bbb7a6bbf3.
- **NVO**: needle 368385278158 -> 368385278158. Added 4: 035042bdfbbd, 21196c25ac74, 96ce6210b65d, e52dd33697d8. Removed 1: 75198bdfa905 (wegovy once weekly (52/yr) vs foundayo once daily (365/yr)). Merged (one fact, one row): 96ce6210b65d into 368385278158; e52dd33697d8 into 368385278158.
- **LLY**: needle 4bf1a2f5e9e4 -> b1c0d840e1ed. Added 9: 2101e3ee6d4a, 450cc54e36aa, 573d2f0d6f4a, 8a11ca1b6853, 95f24fb976b5, 9a8917824228, b1c0d840e1ed, d689e5fdb404, f4a7780b90cc. Removed 0: none. Merged (one fact, one row): f4a7780b90cc into 9cdaa161375b.
- **ABBV**: needle 702ebc520f15 -> 53d422aaae7b. Added 7: 094963600058, 51cc230d5611, 53d422aaae7b, 69066921bdea, 7d4db3d9974e, acb4db12d4e6, e3e48802c565. Removed 2: e38a5893daa1 (skyrizi every 12 weeks (4.3/yr) vs entyvio every 2 weeks (26); f49c7ddae70e (rinvoq once daily (365/yr) vs entyvio every 2 weeks (26/yr)). Merged (one fact, one row): acb4db12d4e6 into e7af05b8c437; 1ea9d91ec6a8 into 7d4db3d9974e.
- **GILD**: needle 49af018377a3 -> 49af018377a3. Added 7: 488e8cc72ba4, 9fd7bce5651f, ad5f7464bbbf, c82cc00289cf, cdc443f73256, e305d3c6d908, f6f1c54114fe. Removed 2: 5f1a33fde1d6 (yeztugo once weekly (52/yr) vs apretude every 2 months (6/yr); e41204317cf4 (biktarvy once daily (365/yr) vs cabenuva monthly (12/yr)). Merged (one fact, one row): f6f1c54114fe into 49af018377a3.
- **AZN**: needle c491682c6c0b -> b0573ba3b531. Added 6: 62baae688068, 6b97051b511c, 9c80e5e17de2, a482d8ece2f6, b99c3949ca42, efe7ad14adb9. Removed 1: 8d0fa7ab1aaf (tagrisso is oral vs rybrevant intravenous). Merged (one fact, one row): none.

## I/B/E/S noise denominator after the scraper's ticker fix

sigma_EPS is unchanged: GILD 0.4031, AZN 0.5408 (USD per share, both before and after). It is computed from the I/B/E/S tables, not from `facts.ticker`. What changed is the citation behind it: GILD's 16 I/B/E/S operand citations now resolve as machine data (number_match). AZN's 16 still do not verify: the facts row holds the per-ordinary-share value (for example 0.99) while the cited value is the ADS-scaled figure (1.98), so the citation note reads "cited value differs from the row value". The ADS factor should be carried as a derived operand; not done here.

## Tests

Full suite: 252 passed, 2 skipped (was 237 passed, 2 skipped at 1551f27; 15 new tests: nugget impact math and id scheme, best-needle map, MFN marker, Biktarvy context, receivables footnote read, LOE dates, turn-label speaker (synthetic and real GILD), peer comparison, DKK, regimens, DECIDE sections, GILD fixture).

## 7. Needle decision: the human read governs

Coordinator decision after section 5: `findings_table` names Parker's red-team best needle when that row passes the gate and is slide-ready (a nugget merged into a kept row as one fact counts as the kept row), else the plain-rule needle. `findings_table.json` records `needle_id`, `needle_source` (red_team or plain_rule), `plain_rule_needle_id`, `red_team_needle_id` and `needle_reason`; `findings_table.md` prints "Why this needle:" with Parker's one-line reason (gated on the row's citations; when his line carries figures the gate does not support, a number-free line names his pick instead) or "plain rule: biggest impact, least asked about".

| Company | Needle id | Source | Row |
|---|---|---|---|
| MRK | eed81303c1d7 | red_team | MRK-nugget-001, Keytruda royalty to BMS and Ono ends Dec 31, 2026 |
| JNJ | b3b341581796 | red_team | JNJ-nugget-010, second wave of exclusivity losses |
| PFE | 8a78af774155 | red_team | PFE-nugget-001, Eliquis list-price rebate windfall |
| BMY | e387364988f2 | red_team | BMY-nugget-001, Keytruda and Tecentriq royalties end |
| AMGN | 2756b7c86172 | red_team | AMGN-nugget-006, IRS Puerto Rico claim vs reserve |
| NVO | 368385278158 | plain_rule | gross margin -3.7 pts (NVO-nugget-001 is cash-only and fails the gate) |
| LLY | b1c0d840e1ed | red_team | LLY-nugget-002, Jardiance one-off |
| ABBV | 53d422aaae7b | red_team | ABBV-nugget-001, Skyrizi royalty to 2044 |
| GILD | 49af018377a3 | red_team | Biktarvy 2028 Medicare price (GILD-nugget-001 merged into the IRA row) |
| AZN | b0573ba3b531 | plain_rule | inventory gap +15.4 pts (AZN-nugget-010 fails the gate) |

Suite after this change: 253 passed, 2 skipped.
