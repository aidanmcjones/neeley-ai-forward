# out/part2 contract (for the UI session)

out/part2/<T>/part2.json is the cached Part 2 ("Decide") chat response for one of AMGN, MRK, PFE.

A "gated text block" is {text, text_marked, marker_map:{n: cite_id}, cites:[cite], numeric_check}.
numeric_check = {status: "passed"|"no_numbers"|"failed"|"unchecked", checked, total, verified, derived, assumed, unsupported}.
A cite is the Part 1 evidence object:
{cite_id, doc_id, page, quote, label, url, quote_grade, verify_status, withheld, grade}
(quote is null for Bloomberg-licensed and machine-data cites; withheld is false only when verify_quote verified the cite: verify_status exact, substring, fuzzy or number_match,
as in docs/citations.md; machine_data cites are never quoted or deep-linked).

part2.json:
{ticker, company, generated_at,
 move:{text, text_marked, marker_map, cites, numeric_check, type,
   budget:{amount_usd, people, period, text, text_marked, marker_map, cites, numeric_check}},
 drivers:[{finding_n, why, cites}],                        (finding_n = findings[].n in out/part1/<T>/part1.json)
 case_for:{cost:{gated text block}, return:{gated text block},
   math_steps:[{step, text, text_marked, marker_map, cites, numeric_check}],
   net:{gated text block}},
 rejected:[{id, move, type, why_passed:{gated text block}, skeptic_lens}],     (exactly 2)
 kill_signals:[{signal, threshold, month_window, text, text_marked, marker_map, cites, numeric_check}],
 evidence:{decider, lands_because:{gated text block}, can_tell:{gated text block}, cannot_tell:{gated text block}},
 promo:{has_material, label:"Student concept, not actual promotional material.",
   pieces:[{title, body, body_marked, marker_map, cites, numeric_check}],
   claims_map:[{claim, support_section, cite}],
   rules_check:{approved_uses_only, risks_prominent, h2h_only, no_testimonials, labelled, claims_map_present}},
 unresolved:[{topic, cfo_position, decider_position}],
 candidates_considered: N,
 skeptic_summary:{killed, narrowed, survived}}

type is one of license_or_acquire | pricing_or_coverage | portfolio_shift | new_indication | campaign | other:<name>.
skeptic_lens is "CFO/math" or "Decider/compliance". When promo.has_material is false, pieces and
claims_map are [] and rules_check values are null.

Only text whose numeric_check.status is "passed" or "no_numbers" is printed by the UI. Figures withheld by
the gate are never rendered; "failed" records live in rejected.jsonl with the reason. No league score, S,
or priced-in score appears anywhere in Part 2. Treat any key not in this contract as pass-through and drop it.

out/part2/<T>/trace.jsonl, one JSON per line:
Header line: {step:0, category:"header", ticker, generated_at, lenses:["CFO/math","Decider/compliance"]}.
Steps: {step, candidate_id, move, type, skeptic_cfo:{round1, round2}, skeptic_decider:{round1, round2},
 verdict: survived|narrowed|killed, reason, cites}.

out/part2/<T>/part2.md is the human-readable twin; out/part2/<T>/rejected.jsonl holds gate failures.
