# Fix notes 1 (branch quant-fix, from quant-model 358bae9)

The only deadline is the Sunday 2:00 pm Devpost submission. The AMGN and MRK decide files are pipeline demonstrations; the company pick is open between MRK, AMGN and GILD, and none of the fixtures is the recommendation.

## What changed

Citation index and gate
- `facts.locator` is read first (agent/needle/cite/facts.py `apply_locator`, called from data.py for every facts-row citation). `doc_id#pN` gives a normal page citation: the quote is the row's own quote field or the page line that matches the row's indication terms, never a bare value, and it must pass the verify ladder (deep link, viewer link). `fact:` keeps the facts citation with the row key. `url:` gives a machine-data citation linked to the URL, except an API endpoint or bulk file, which does not show the row (row key only). The whitelist still sets the status: a URL is not a check. Label-section rows (epi/indication_map.csv) resolve to their DailyMed label page through source_row. An older sqlite without the column reads as before.
- numeric_check status `no_numbers` when a text has no number (total 0). `gate.check_ok` treats it like `passed` for writers, league, top 5 and the app.
- Review verify2 fixes. (1) "Verified" now means the number is inside the quoted span or equals the citation's own value; page numerals outside the quote never support a number. The record's derived and assumption maps are read before any citation, a number named as derived whose derivation fails is unsupported, bare 0, 1 and 100 in a formula are arithmetic, and the assumption label follows the symbol printed before the number. Constants render as `[constant: NAME]`. (2) FIND renders `formula_md`; the app prints only `sentence_md` and `formula_md` (no ungated Impact dollars or peer line). (3) Product: dates, years and "12y" in timeline cells (and full dates and prose years in pricing cells) need a citation or a labelled table value, and are marked where read. `uncited_cells` lists cells with no citation. Label counts derive from cited items: indication counts from indication_map rows, warnings from section 5 headings, zero contraindications from the cited section 4. No ", p. 9" suffix in links. (4) DECIDE: PV pieces, payback month (`payback(...)`) and cash at risk are derived from the monthly model rows and WACC. Benchmark URLs that do not show their figure, or return 403, are dropped; the figure stays a labelled assumption naming the source. (5) Text fragments come from one block only: a flattened table row is split at its numeric cells, else plain URL plus viewer.
- Gate additions: count operands (one cited item = 1, no double counting), `median`, year operands (a year read from a cited date), `payback`.

FIND
- Label rows recount indications from indication_map rows, each cited to its label line, and re-apply the detector rule (narrower: product <= rival median - 2). A row that no longer meets the rule is dropped.
- exclusivity_earlier rows use the company-stated LOE from pipeline/loe_calendar.csv, cited to the 10-K page as page evidence. The year gap is derived from the two dates (rival's own loe_calendar row when it exists). There is one id per product and rival (two rows used to share d8177d9f7349).
- TrumpRx prices are each cited to their own sentence on the White House page. k = 1 for low-rebate classes is a labelled constant.

DECIDE
- Exit 2 deletes any stale decide.json and decide.md first; the rejected run's JSON goes to decide_rejected.json.
- A move that addresses no gated finding cannot be chosen (spec 5.2).
- A moves file with `"demo": true` renders its header note and labels the chosen move as a demonstration.
- M3 timing comes from costs/new_indication_timing_summary.csv by TA when the context sets `"timing": "table"`.
- LOE dates parse month names ("May 2026") and M/D/Y.
- Wave 3 caveat columns are carried into the citation note: do_not_read_as_penetration, marketed_comparator, and native-currency peer revenue.

Docs
- Plan and handoff text use the one deadline, with no freeze clock times.

## LLY outcome (task 4)

- d2aae6b94153 (zepbound label, was LLY-labels-595152). The recount from cited indication_map rows is zepbound 2 vs wegovy 3, every row cited exact to its label line. The gap of 1 fails the detector's rule, so FIND drops the row (drop guard).
- d8177d9f7349, now 68c1713e96ef (trulicity vs ozempic, was LLY-labels-746909). The Trulicity date is now the company-stated 2027, cited substring to LLY 10-K FY2025 file page 12 through facts.locator. The gap is derived as rival year - product year. The row still fails: ozempic's 2041-02-17 is an Orange Book table value with no verified facts row or page.
- Re-pointed moves, with a `note` in docs/examples/moves_LLY.json:
  - Zepbound cash-pay (M4) now uses ccde14de6e25: MFN/TrumpRx, Zepbound avg $346/mo. It now passes, because the Trulicity $389 has its own sentence cited.
  - Trulicity defense (M5) now uses 4bf1a2f5e9e4 (Trulicity IRA price from January 2028).
  - Zepbound label expansion (M3) has no passing finding. It has strategic fit 0 and cannot be chosen.
- decide_cli LLY exits 0. numeric_check passed: 182 numbers, 19 verified, 72 derived, 91 assumed.

## Five numbers (USD M; payback in months)

| Ticker | Status | Move | EV | Cash at risk | Payback | Scenario EV spread | MCDA |
|---|---|---|---|---|---|---|---|
| LLY | chosen | Defend Trulicity through the 2027 loss of exclusivity and switch patients to Mounjaro | 597.8 | 0.0 | 9 | 520.6 | 0.661 |
| LLY | rejected | Expand the LillyDirect cash-pay Zepbound channel (MFN-aligned) | 233.8 | 22.9 | 23 | 236.8 | 0.665 |
| LLY | rejected | Seek new Zepbound indications to close the label gap with Wegovy (no finding, cannot be chosen) | 1,345.9 | 251.2 | 80 | 667.1 | 0.476 |
| AMGN (demo) | chosen | Expand a Repatha direct-to-patient cash channel at the TrumpRx price | -60.2 | 62.1 | none in 120 | 33.5 | 0.741 |
| AMGN (demo) | rejected | Defend ENBREL through its US loss of exclusivity | -5.2 | 80.0 | none in 120 | 161.7 | 0.566 |
| AMGN (demo) | rejected | Reprice Otezla into a cash channel ahead of its Medicare negotiated price | -97.4 | 71.8 | none in 120 | 9.8 | 0.549 |
| MRK (demo) | chosen | Move Keytruda patients to the subcutaneous formulation before the US loss of exclusivity | 5,491.7 | 0.0 | 18 | 2,971.0 | 0.654 |
| MRK (demo) | rejected | Reprice Janumet ahead of its Medicare negotiated price | -40.6 | 25.2 | none in 120 | 0.9 | 0.536 |
| MRK (demo) | rejected | Sell Januvia through a cash channel at the TrumpRx price | -108.9 | 59.8 | none in 120 | -11.2 | 0.539 |

Notes on the demo selections:
- AMGN: the ENBREL and Repatha EV intervals overlap, so the selection rule takes the higher MCDA, and the chosen demo move has a negative EV.
- MRK: the Keytruda EV rests on a team-input switch capture of 0.25 (labelled).

Each demo file has every claim passed or no_numbers, and all three moves carry five numbers:
- AMGN: 200 numbers (21 verified, 75 derived, 104 assumed)
- MRK: 182 numbers (13 verified, 71 derived, 98 assumed)

Finding anchors:
- AMGN: e78dad58497e (MFN, Repatha TrumpRx $573 to $239) with bc852b02400d (receivables, the strict needle); cc375a27a20d (ENBREL LOE 2028 vs Skyrizi 2033); a4b34956387a (Otezla IRA 2027).
- MRK: 3f39dd0d23f0 (Keytruda broadest label); 055023d4eff6 with fc96c4e7ed6a (Januvia TrumpRx and narrower label); dd2b47cc4d2b (Janumet IRA 2027).

## Census (the verifier's columns, re-run with the verifier's scripts pointed at this worktree)

| Output | Numbers | Verified in span | Verified page-only | Derived OK | Assumed (labelled) | Unsupported but passed |
|---|---|---|---|---|---|---|
| AMGN findings top 5 | 41 | 8 | 0 | 17 | 14 + 2 arithmetic | 0 |
| GILD findings top 5 | 25 (+3 identifiers) | 6 | 0 | 8 | 9 + 2 arithmetic | 0 |
| MRK findings top 5 | 18 (+1 identifier) | 0 | 0 | 9 | 8 + 1 arithmetic | 0 |
| product Keytruda | 81 | 5 | 0 | 30 | 40 | 0 |
| product Repatha | 29 | 4 | 0 | 11 | 11 | 0 |
| decide LLY | 202 | 18 | 0 | 72 | 89 | 0 |
| decide AMGN | 215 | 19 | 0 | 75 | 103 | 0 |

How to read the census:
- Verified in span includes the cases where a claim rounds a more precise source, for example $994.0M from $994,001,000.
- The md census still shows some items that are not gate failures:
  - unmarked structural numerals in headings ("24-month", "months 1-24", "Part 1")
  - table-row footnotes with no page (I/B/E/S, XBRL)
  - years, which are excluded by the documented rule
  - one arithmetic "100" in a product math line
- 5 facts rows have no page link in the product files ("table-row-or-unpaged").

## Not done

- Subset shares (epi/indication_subset_shares.csv) and the 50-indication epidemiology table are not wired into the product label-breadth channel. That channel is sized on Medicare coverage, not epidemiology.
- These figures stay labelled table values: ozempic's and the other Orange/Purple Book dates, and the LOE curve quantiles. None has a verified facts row.
- Text fragments are validated against the converted page text, not live EDGAR HTML.
