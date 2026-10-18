# Where AI is in the build

For the pitch ("Use of AI and Responsible Design") and for judges. Spec: `docs/quant_model.md` Sections 4.7, 6.7 and 9.

**Pitch line:** "Every number you see was computed by deterministic code from a cited page. AI writes the words, argues the case and reads the calls, in one cached pass, and nothing it says reaches the screen until a page verifier has found it on the page it cites. When the AI was wrong, and it was, that is how we caught it."

## The deterministic track: no model runs

These run with no API key and give the same output every time:

| Step | Code | Output |
|---|---|---|
| Detectors (forensic ratios, filing-text drift, call patterns, labels, supply) | `agent/needle/detect/*.py`, `agent/needle/run.py` | `out/<T>/signals_*.jsonl` |
| FIND (M, O, E, π, confidence, Sharpest Needle) | `agent/needle/quant/find.py` and friends, `run.py` | `out/<T>/findings_v2.jsonl` (written by the v3 run), `out/league_v3.json` |
| League and robustness table | `agent/needle/quant/league.py`, `run.py` | `out/league_v3.md`, `out/league_v3_robustness.json` |
| Red-team guards | `agent/needle/quant/guards.py` | drop, context or no-needle reason on the row |
| Product fine print | `agent/needle/quant/product.py` | `out/<T>/product_<p>.json` and `.md` |
| DECIDE and kill signals | `agent/needle/quant/decide.py`, `moves.py`, `kill.py` | `out/<T>/decide.json` and `.md` |
| Citations: verify, gate, deep links, footnotes | `agent/needle/cite/*.py` | markers and footnotes on every row |

Confidence labels are a fixed rule over evidence grades (spec 4.7). No score, rank, confidence label, page number or dollar figure comes from a model.

## The citation gate: the human-oversight mechanism

Every number a reader sees passes `agent/needle/cite/gate.py` (`numeric_check`), one number at a time, and the gate fails closed.
- A number is **verified** only if it appears in the quoted span of a passing citation, or in that citation's own value. A numeral elsewhere on the same page does not count (the first version allowed this; see row 3 below).
- A number is **derived** if the record carries a formula whose operands are each cited, assumed or themselves derived, and the formula recomputes the printed number within 0.5% or its printed precision. A failed derivation is unsupported, with no fall-through to a page match.
- A number is **assumed** only if the record carries a non-empty label for it, and the label is printed beside it.
- Anything else is **unsupported**: the sentence is withheld and logged, never shown with a guess. A text with no numbers reports `no_numbers`, not a pass.
- FIND, PRODUCT and DECIDE each run every cell through the gate before the league, the app or any writer reads it. DECIDE re-verifies company citations itself and discards any status a caller supplied. If a gate fails, DECIDE writes `decide_rejected.md` and deletes stale outputs.
- Humans read every needle. The gate proves a number is on the cited page; a person decides whether the page means what the sentence says (rows 4, 5, 9 and 18 in the table below were caught that way, not by code).

## The league is triage, not the pitch

The internal ranking (`league_v3`) exists to decide which findings to read first. It is not what we show a judge as evidence. Ten companies cannot produce a significant ranking (minimum p = 0.10), the first league was led by a scorer bug (row 2), and its robustness table shows the first two places move with one assumption. The pitch ranks findings by their cited dollar impact, and the company and the Sharpest Needle were chosen by a human read of the cited pages (Parker's red team v2 and v3), with the league as supporting evidence.

## The LLM track: one pass once the key is armed

| Step | Code | What the model does | What stands between it and the screen |
|---|---|---|---|
| Finding prose | `agent/needle/cite/llm.py`: `build_cited_request`, `parse_cited_response` | writes the plain-English sentence for each top finding from the cited pages | each page is a `search_result` block with `citations: {enabled: true}` on every block; the page number comes from our own `source` field, never the model; every citation goes through the verification ladder and the gate; a sentence with a number not in its cited text is downgraded (`strict_numbers=True`) |
| Courtroom trial | `agent/needle/trial.py` | prosecutor argues the finding is material and unpriced, the company's CFO defends from its own filings, a judge rules | every quote any role cites is checked on its page; invented, paraphrased or wrong-page quotes go to `out/<T>/ai_caught.jsonl`; a "fails" ruling can only lower confidence to LOW |
| Drift and call reading | planned on top of the deterministic drift and call detectors | classifies what changed in a risk factor or how an answer deflected | same cited-request path and gate |
| The memo | `app/main.py` over `agent/llm.py` | answers the reader's questions over the cited context | same gate before display |

Rules of the pass:
- **One pass, cached.** Every call goes through `agent/llm.py`, which caches each answer on disk keyed on (model, prompt, context, system, effort). A rerun reads the cache, so nothing is paid twice, and a demo never waits on the API. Refusals and truncated answers are not cached. Model: Claude Opus 5.5 with server-side fallback.
- **Citations on, structured outputs off.** The API rejects citations combined with structured outputs (HTTP 400), and citations must be on for all document blocks or none. So the cited call returns text with citations; if JSON is needed, a second, non-cited call structures the already-verified claims and carries their citation ids through.
- **Verify, then gate.** The verifier (exact, normalized, fuzzy at 90 with a numeral guard, number on page) and the gate sit between the model and anything shown. A claim with no verified citation is withheld and logged.
- **The model can lower confidence, never raise it.**

Two wiring items are open before the pass runs (see `docs/HANDOFF_quant.md`): `agent/llm.py` today sends context as plain document text, so the cited path needs a call variant that sends `build_cited_request`'s body through the same cache; and `trial.py` reads the old engine's `findings.jsonl`, so it must be pointed at the v3 rows (`out/<T>/findings_v2.jsonl`) for its veto to reach the league. Both are still open at quant-model ee7846c.

## When the AI was wrong, and how we caught it

Both teams' cases in one table. "Caught by" is the check that found it: skeptic (adversarial review agents), human read, test, backtest, verifier (the page verifier or gate), or red team (a read-only Claude agent scoring our work against the rubric). Dates are 2026; Parker's cases were all found on Oct 17, the quant team's during Oct 16 to 17. Commit ids are on `quant-model` unless marked (needle).

| # | Date | What the AI claimed | Caught by | Fix | File or commit |
|---|---|---|---|---|---|
| 1 | Oct 16 | v1 backtest: gross-margin drops precede an adverse event 59% of the time vs a 43% base rate | two skeptics, then each read the other | Point-in-time windows; firm-clustered interval must clear 1. Only margin compression survives (12% with no flags to 61% with five); no flag predicts revenue drops or impairments | `docs/needle_gate2.md`, c3cf03d |
| 2 | Oct 16 | LLY leads the league; its margin implies about $68B of impact | human read (row-by-row trace of the score) | The 85.8% gross-margin level was scored as a change. A margin above peers now scores zero; LLY fell from 1st to 8th | 4009a40; `test_gross_margin_level_has_no_dollar_path` |
| 3 | Oct 17 | First citation gate: "verified" on 4 shown z-scores and 4 product counts | independent re-check of the gate output (verify2) | The gate accepted any numeral on the cited page (an EPS of 1.18, an I/B/E/S row of -0.13, a page footer "- 3 -"). Verified now means in the quoted span or the citation's own value; the record's own maps are read first; constants are labelled where read | 18be760, 22fdd8e; `docs/citations.md` |
| 4 | Oct 17 | AMGN needle from the code: receivables up faster than revenue, a collections flag | human read (needle) | Receivables track gross invoices to three wholesalers (75% of receivables); gross billing grew 15.4% vs net revenue 9.7%, with a separate rebate liability. The real signal is deductions rising from 51% to 54% of gross sales (2022 to 2025) | `docs/red_team_v3_final.md`, AMGN-nugget-002 (needle) |
| 5 | Oct 17 | AZN needle from the code: receivables +23.3% vs revenue +8.6%, $1,219m at risk | human read (needle) | Factorable receivables and Chinese bank acceptance drafts rose from $667m to $2,681m (20-F p. F-29); without them trade receivables fell 0.8%. Impact $0; kept as a false positive. Ratio flags are never a needle alone | `AZN_ai_caught.jsonl` (needle) |
| 6 | Oct 16 | Drug packs held the Ozempic oral-tablet, Sarclisa subcutaneous and Janumet XR labels | human read (label vs case product) | Right labels re-pulled; variants kept as separate files | 4d913fa |
| 7 | Oct 16 to 17 | Quotes from fool.com transcripts, which open with LLM-written takeaways that read like call text | verifier and human read | Corpus flags the summaries and a mislabeled AZN Q1 transcript; the verifier rejects quotes from those sections. ABBV and AMGN each had one such line avoided | 7964caa, 8a94bc0; `ABBV_ai_caught.jsonl` (needle) |
| 8 | Oct 17 | Finding ids were stable | test (two processes) | Ids used Python `hash()`, salted per process, so ids changed on every run and broke joins. Now sha256 | 33dd606 (needle) |
| 9 | Oct 17 | Label-table exclusivity dates: Trulicity 2026, Zepbound 2039, Ibrance 2037, Vyndamax 2035, Tremfya 2029 (Keytruda 2031 also) | human read against the 10-K patent tables | These were later-listed use or formulation patents or Purple Book reference exclusivity, not the compound date. FIND's exclusivity rows now read the company-stated date from the cited 10-K page and derive the gap from two dated operands | 4e1d003; `LLY/PFE/JNJ_ai_caught.jsonl` (needle) |
| 10 | Oct 17 | Speaker check passed Greg Renza (Truist) as the asker | verifier read by a human | The surname sat in the operator's introduction; the label on the question was Anish Nikhanj ("This is Anish on for Greg"). The check now needs the name on the speaker label, not within a text window | `GILD_ai_caught.jsonl` (needle); transcript speaker check in league_v3 |
| 11 | Oct 17 | MRK needle: R&D at 58.7% of revenue | red team | One-time $5.7B acquired IPR&D charge ($2.31 per share) that also drove a -95.8% tax rate. One-offs go to context, not signals | `test_ipr_and_d_charge_is_one_off` (needle) |
| 12 | Oct 17 | LLY holds 469 days of inventory; tax-rate signals fire | red team (agent-chat #19) | Days on cost of sales inflate at an 85% margin (on revenue, 67 days, not an outlier); tax signals fired on near-zero pre-tax income. Nine guards removed or demoted more than 240 rows | `agent/needle/quant/guards.py` |
| 13 | Oct 17 | AZN impact sentence said receivables 14,168M vs 11,047M, +11.7% | human read (audit) | The sentence used FY2025 year-end figures (+8.6%) while the math used half-year 6-K figures on a broader concept | `test_impact_math_matches_the_sentence` (needle) |
| 14 | Oct 17 | GILD needle: new MD&A language | audit | The paragraph was good news ("positive topline Phase 3 results"); code cannot tell direction. Undirected MD&A changes are not needle-eligible | needle |
| 15 | Oct 17 | Seven of ten needles were label facts ("Keytruda lists 21 indications"); NVO needle was a table of contents parsed as a paragraph | audit | Label findings floored at O = 0.5; paragraph filter requires a sentence | needle |
| 16 | Oct 17 | AZN draft: US gross-to-net worsened to a new low in 2025; $1,804m give-back as the Sharpest Needle | human read of the 20-F and the 2024 annual report | Net/gross alternates (53.75%, 49.1%, 53.3%, 49.5% for 2022 to 2025); 2025 is $168m better than 2023. Prior-year accrual adjustments were a $175m release, so true-ups do not explain it | `AZN_ai_caught.jsonl` (needle) |
| 17 | Oct 17 | AMGN: $7.6B IRS claim vs $4.4B reserve is a $3.2B unreserved gap | challenger round and human read | Accrued interest and penalties add $1.9B (reserve about $6.3B); the gap is at least $1.3B and a base case with two assumptions | `AMGN_ai_caught.jsonl` (needle) |
| 18 | Oct 17 | AMGN deductions rose 52% to 54% of gross sales | challenger round | 2023 was 53%, 2022 was 51%; exact ratios 50.6, 52.9, 52.5, 54.4. The trend vs 2023 is +1.5 points, not +2 | `AMGN_ai_caught.jsonl` (needle) |
| 19 | Oct 17 | ABBV Vraylar Medicare book = 1,136 / 3,612 = 31% | human read | Mixed years and gross vs net; rewritten as 1,136 / 3,260 = 35%, an upper bound | `ABBV_ai_caught.jsonl` (needle) |
| 20 | Oct 17 | GILD brief: Biktarvy faces a 2033 generic settlement | human read of the 10-K | The October 2025 settlements moved earliest US entry to April 1, 2036; 2033 was the old projection | `GILD_ai_caught.jsonl` (needle) |
| 21 | Oct 17 | PFE first read: US Vyndamax exclusivity ends 2026 to 2028 | human read of the 10-Q legal notes | Settlements in March to May 2026 permit generics on June 1, 2031; recast as a conditional finding | `PFE_ai_caught.jsonl` (needle) |
| 22 | Oct 17 | Page numbers on quotes (AMGN 10-Q Enbrel, TEPEZZA and BLINCYTO sentences; BMY revenue tables) | verifier | The quote was on the neighbouring file page; 20+ citations rejected and re-cited to the right file page and printed page | `AMGN_ai_caught.jsonl`, `BMY_ai_caught.jsonl` (needle) |
| 23 | Oct 17 | BMY: "Qvantig, we got 15% share" | human read of the 10-Q | 10-Q gives Qvantig 12.7% of US nivolumab revenue; 15% is probably a patient share and the speaker label is uncertain. Not used | `BMY_ai_caught.jsonl` (needle) |
| 24 | Oct 17 | Verifier could not confirm real quotes in long prepared remarks (speaker header over 4,000 characters earlier) in nine companies | verifier (an over-strict miss, the safe direction) | Quote dropped or replaced by a filing line; no unverified attribution shown | `*_ai_caught.jsonl` (needle) |
| 25 | Oct 16 | The reviewed draft spec said one universal MFN rate was certain and the needle rule "does not silently relax" | skeptics and synthesizer | Spec corrected; MFN is direction-only at the minimum probability; every correction listed by finding id | `docs/quant_model.md` Section 14 |
| 26 | Oct 17 | Data layer: 616 rows of "restated" product revenue | reconciliation | Zero true restatements; 447 were recasts where a company moved products between lines | `data/moat/verify/ai_wrong.jsonl` (472 rows by the evening of Oct 17) |

Counts: 26 numbered cases. Rows 1 to 3, 6 to 8, 12 and 25 are the quant team's catches of its own pipeline; rows 4, 5 and 9 to 24 come from Parker's nugget miner and red team. Parker's ten `_ai_caught.jsonl` files hold 151 entries in all (most are page, speaker-window and baseline rejections of the kind in rows 22 and 24); the table picks the instructive ones. Row 26 stands for the data layer's own log.
