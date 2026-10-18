# Red team v1: holes in what we built and plan, Sat Oct 17, about 4 pm

Scored against the rubric (7 categories, demonstrated only) and the case minimums. Ranked by points at stake per hour to fix.

## 1. The league table ranks on our weakest evidence
- Every current Sharpest Needle is a mechanical ratio, and `docs/needle_gate2.md` already shows forensic ratios do not predict revenue drops or impairments.
- **MRK needle is a one-off.** "R&D 58.7% of revenue" is a $5.7B acquired IPR&D charge ($2.31 per share) in Q2 2026 (`MRK/10q_2026Q2.md`, "Merck recorded a charge of $5.7 billion to Research and development expenses"). A judge who reads the 10-Q will catch it in 30 seconds.
- **LLY needle is distorted.** 469 days of inventory comes from dividing inventory ($16.8B) by cost of sales at an 85.8% gross margin. High-margin companies always look extreme on this ratio. This is the same root cause as the scorer bug.
- **AZN double counts.** `AZN-forensics-400151` and `AZN-forensics-490332` are the same receivables fact under two signal kinds. Check FX and the IFRS receivable definition before using it.
- **The real nuggets are not in the table.** Genmab royalty disclosed only after the SEC asked, the Keytruda royalty ending, gross-to-net on Stelara/Skyrizi/Tremfya, products folded into "Other" (agent-chat #9 to #17) are all qualitative, footnote-level, and exactly what the case rewards.
- **Fix:** choose the company on nugget quality, not league score. Run `nugget-miner` on the top 3 candidates. The league table becomes supporting evidence ("the code flagged it, a human confirmed the cause"), not the selector. Add a one-off filter (IPR&D, impairment, FX) and a duplicate-fact collapse to the scorer. (Aidan, 1 hour)

## 2. The deliverables judges score are not started
- PLAN.md still has a blank one-liner, persona and golden path. There is no deck, findings table, Part 2 or How We Did It report yet. Submission is Sun 1:00 pm.
- Three agents on four branches (needle, quant-model, data-moat, ui), across two repos, is an integration risk. Completeness scores what runs.
- **Fix:** company locked by 7 pm tonight. Findings table and Part 2 drafted tonight, with model numbers dropped in when they land. Merge freeze Sun 9 am, not 10:30. One golden path, rehearsed. (Parker)

## 3. Part 2 risks looking like "the AI picked the strategy"
- The case says "Part 2 has no answer key. AI will argue convincingly for almost any strategy. Your team has to pick one and defend it." A 5-number DECIDE score that outputs a winner invites the question "so you let the model decide?"
- **Fix:** present DECIDE as the stress test of a move we chose, with the human reasoning first and the model as the check. Kill signals at months 6 and 12 are the strongest part, so lead with them.
- "Why it will work" still needs real evidence from doctors, payers or regulators: payer coverage policies, CMS Part D utilization, ClinicalTrials.gov head-to-head status. State what each source cannot tell us.

## 4. Use of AI: the strongest story is buried
- The LLM prose steps are still blocked on the API key. If the demo shows only deterministic code, "AI is essential" is hard to argue.
- Our best AI story is AI that catches AI: 61 logged errors, the verifier rejecting seeded bad quotes, and the gate 2 backtest refuted by AI skeptics before any judge saw it. That is a 4 on Responsible Design.
- **Fix:** get the key tonight, or run the prose through Claude Code and cache it. Put an "AI caught" moment in the live demo.

## 5. Presentation: too much to show
- Seven screens, 69,553 facts and a 1,000-line spec will not land in a few minutes at a table.
- **Fix:** one sentence: "Wall Street reads the headline; we read the footnote and prove every quote." Demo in 90 seconds: the needle, click to the highlighted source page, the AI-caught panel, a sealed forecast verified in the browser. Everything else goes in the appendix or Q&A.

## 6. Go beyond (cheap, high-signal)
- **Live onboarding:** ask a judge to name a ticker and run `onboard` live (already proven on VRTX). This proves the reusable build and Innovation in one move.
- **Distributor lens for the McKesson judge:** channel inventory and receivables cross-checked against distributor 10-K commentary (`detect/supply.py`).
- **Lead with the honest negative result:** "Our first backtest said 59% vs 43%. Our own skeptics refuted it." That builds trust for Completeness.
- **Accessibility** for Design: color-blind palette, text labels and keyboard navigation, all called out on one slide.

## Projected rubric
| Category | Today | After fixes 1 to 5 |
|---|---|---|
| Innovation | 3 | 4 |
| Technical | 3 | 4 |
| AI and Responsible | 3 | 4 |
| Completeness | 2 | 3 to 4 |
| Design | 3 | 3 to 4 |
| Impact | 2 | 3 |
| Presentation | 2 | 4 |

## Status after the audit (Sat about 5 pm)
| Hole | Status | Where |
|---|---|---|
| 1. League ranks on weakest evidence | Fixed in code: level-as-change bug, favorable outliers, margin-neutral days inventory, trailing-4Q tax rate, IPR&D one-offs (with cited "no tax benefit" text), duplicate peer rows, label and undirected-MD&A needles, TOC paragraphs, half-year impact math. 48 tests pass, ledger intact. League now: AZN, MRK, NVO, GILD, AMGN, ABBV, JNJ, BMY, PFE, LLY | agent/needle/{score,pages}.py, detect/{forensics,drift,calls}.py, tests/needle/test_forensics.py |
| 1b. Choose on nuggets | Running: nugget-miner on AZN, MRK, JNJ, AMGN | docs/nuggets/ |
| 2. Deliverables not started | Scaffolded: PLAN.md filled (Parker to confirm), demo_script.md golden path, deck/outline.md, docs/part2.md, docs/how_we_did_it.md with 8 caught errors | |
| 3. Part 2 looks AI-picked | Framed in docs/part2.md: human picks, model stress-tests | |
| 4. API key | Open: human action (Aidan) | |
| 5. Presentation | 5-step golden path with one-liner | demo_script.md |
| 6. Go beyond | Live onboard step in demo; distributor and accessibility items in deck outline | |
| Not fixable here | Aidan's quant-model branch replaces this scorer. Its spec should carry the same guards (agent-chat #19) | |
