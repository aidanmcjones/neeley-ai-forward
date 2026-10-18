> Superseded. This was the Saturday plan. The final deck is `Needle_in_the_Haystack_Pitch_Deck.pptx` (see README.md); the league table it mentions was internal triage only and is not in the deck.

# Deck outline (maps every slide to a case deliverable and a rubric category)

Owner: Parker. One idea per slide. Every number carries its citation in small type. No em dashes. Brackets are filled
from docs/nuggets/<TICKER>.md and the DECIDE model once the company is locked.

| # | Slide | Case requirement | Rubric | Source |
|---|---|---|---|---|
| 1 | Title: one-liner, team, track, case | Video intro | Presentation | PLAN.md |
| 2 | Why [COMPANY] beat the other nine: corrected league table plus nugget quality | P1 company choice | Innovation, Impact | out/league.json, docs/nuggets/*.md |
| 3 | The starter thread everyone knows, and what it misses | P1 "not obvious" | Innovation | case appendix |
| 4 | Findings table: 5+ rows, case column order (Finding, Source, Impact math, Peer, Confidence) | P1 findings table | Completeness, Technical | docs/nuggets/[TICKER].md |
| 5 | Sharpest Needle: one finding, its page, its dollars, why nobody is talking about it | P1 Sharpest Needle | Innovation, Presentation | nugget + obscurity rung |
| 6 | Product fine print: [PRODUCT] vs rivals on uses, boxed warnings, dosing, exclusivity, price and GTN | P1 product comparison | Completeness | out/[TICKER]/labels_table.json, data/corpus/drugs |
| 7 | Where the label shows up in the numbers, plus the one-sentence growth limiter and priced-in call | P1 tie label to finding | Impact | nugget with case_fit P1.ties_label_to_numbers |
| 8 | Part 2: the move in one sentence, budget, people | P2 move | Impact | docs/part2.md |
| 9 | The case for it: findings that drive it, cost, return, math | P2 case | Impact, Technical | DECIDE output |
| 10 | Two alternatives we rejected and why | P2 alternatives | Presentation | docs/part2.md |
| 11 | What would prove us wrong: month 6 and 12 kill signals | P2 kill signals | Responsible AI | DECIDE kill signals |
| 12 | Why it lands with doctors, payers, regulators, investors, and what that evidence cannot tell us | P2 why it works | Impact | docs/part2.md |
| 13 | How it works: AI reads, code checks; page verifier; audit ledger; skeptic gates | Reusable build | Technical, AI | docs/needle.md |
| 14 | AI caught: the confident errors and how we caught them | How We Did It | Responsible AI | docs/how_we_did_it.md |
| 15 | Limits we state up front | Completeness honesty | Completeness | materiality_spec section 8, gate 2 |
| A1 | Appendix: impact math for every finding | Supporting math | Technical | nuggets impact.formula |
| A2 | Appendix: claims map (claim, label section or study) | Promo rules | Responsible AI | only if Part 2 has a campaign |
| A3 | Appendix: campaign concept, labelled "Student concept, not actual promotional material." | Promo rules | Design | only if Part 2 has a campaign |
| A4 | Appendix: backtest v2 and calibration | Proof | Technical | docs/needle_gate2.md |

Accessibility on every slide: color-blind-safe palette, text labels on charts, 18 pt minimum body text.
