# Part 2 in the chat (UI side)

The second chip, "Part 2: CEO move", answers the case's own sentence: "recommend one strategic move for the
next 24 months, with a specific budget or commitment of people behind it." The answer is cached per picked
company from `ui/public/data/part2/<T>.json`, exported by `agent/ui_part2_export.py` from the model session's
`out/part2/<T>/part2.json` under `docs/part2/UI_CONTRACT.md` (quant-model). The chip appears only when
`data/part2/index.json` lists at least one finished company; until then the page is unchanged.

Run after each engine commit, from the ui worktree:

    PYTHONPATH=. /opt/homebrew/bin/python3 -m agent.ui_part1_export && PYTHONPATH=. /opt/homebrew/bin/python3 -m agent.ui_part1_export --check
    PYTHONPATH=. /opt/homebrew/bin/python3 -m agent.ui_part2_export && PYTHONPATH=. /opt/homebrew/bin/python3 -m agent.ui_part2_export --check
    cd ui && npm run build

Part 2 is exported after Part 1 because the drivers are checked against `data/part1/<T>.json` finding numbers and
the company's Part 1 gated figures join the Part 2 gated set.

## What the answer renders, in order

1. The move in one sentence, with its type and the budget line (amount and people only when the budget block's
   numeric check passed).
2. The case for it: the Part 1 findings that drive it as chips (a chip opens the Part 1 answer at that finding),
   cost and return side by side, the math step by step, the net line. Every number carries its citation chip
   through the block's `marker_map`.
3. The two rejected alternatives with why the team passed and which skeptic pressed the point.
4. Kill signals for months 6 to 12: signal, threshold, window, reading.
5. Why it will work: who decides, why it lands with them, what the evidence can and cannot tell us, and any
   point the CFO and Decider skeptics left unresolved.
6. Anything a doctor or patient would see, under the label "Student concept, not actual promotional material."
   (printed from a UI constant, never from data). The piece is withheld unless `rules_check.risks_prominent`
   and `rules_check.labelled` are both true. The six promotion rules render as a checklist from `rules_check`.
7. The claims map: claim, label section or study, source chip.
8. The numbers pill: `numeric_summary`, the exporter's sum of every block's numeric check, plus the count of
   figures the gate withheld.
9. "How it decided": the trace, candidates with the two skeptics' rounds and the verdict.

## Rules the exporter enforces

Same gate as Part 1. Every gated block (move, budget, cost, return, each math step, net, each why_passed, each
kill signal, lands_because, can_tell, cannot_tell, each promo piece) must carry `numeric_check` with status
`passed` or `no_numbers`; a failed or unchecked block fails the company. Any figure in prose that no passed
block governs and that the gate never passed (in Part 2 or in the company's Part 1 record) becomes
"[figure withheld: not gated]". Identifiers, month windows, labels and cite fields are exempt. Exactly two
rejected alternatives, at least one kill signal with signal, threshold and month window, drivers that name
real Part 1 finding numbers, the exact student-concept label when `has_material` is true, empty pieces and
claims map when it is false. Unknown top-level keys are dropped and printed. A company that fails is listed in
`index.missing` with its errors and is not written; the UI shows its tab disabled as "writing".

## Fixture

No `_sample/part2` ships: there is no real Part 2 source to build one from, and a placeholder would be invented
content. Render checks before the real files land used a throwaway fixture in the session scratchpad, exported
through the same `--src/--dest` path and deleted afterwards.
