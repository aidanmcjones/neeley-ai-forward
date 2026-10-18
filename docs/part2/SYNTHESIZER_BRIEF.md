# Synthesizer brief (Part 2 dialectic and writer)

Two skeptics examined one company's candidate moves through different lenses (CFO and math; decider and
compliance), then read each other. You resolve the exchange, pick ONE move, and write the gated Part 2
deliverable. You do not vote and you do not average.

Inputs: under /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part2/_work/<T>/:
candidates.jsonl, skeptic_cfo_r1.json, skeptic_decider_r1.json, skeptic_cfo_r2.json,
skeptic_decider_r2.json, strategist_summary.md, data_requests.md; plus out/part1/<T>/part1.json and
part1.md, the case PDF, and docs/citations.md for statuses, markers and the public rule. Where the skeptics
still disagree on a fact, open the cited page yourself through agent/moat/cite.py (gap-data worktree,
PYTHONPATH=., same interpreter) and settle it from the source. Same DO NOT READ list as the strategist.

## Rulings
For each candidate, rule: survived (as stated), narrowed (survives as the corrected move you write), or
killed, with a reason naming what each side conceded, what still disagrees, and the doc_id and page that
settled it. "Unrefuted" is weaker than "confirmed": say which you mean. A candidate that only survives
because the strategist wanted it to is killed.

## The pick
- ONE move, ruled survived or narrowed. Never a move the CFO skeptic refuted on the math and did not
  concede in round 2. If nothing survives, say so plainly and name the least-bad narrowed move as such.
- The two strongest rejected alternatives with stated reasons. They may be killed candidates; the reason is
  the skeptic's argument, cited.
- Kill signals: at least two, each with signal, threshold and month window inside months 6 to 12.
- Evidence section: the decider, why it lands, what the evidence can tell, what it cannot.
- Promo: if any doctor or patient would see material, apply all six rules and fill rules_check; every
  piece carries the label "Student concept, not actual promotional material." and every claim has a row
  in the claims map.
- Disagreement that survived round 2 goes in `unresolved` as {topic, cfo_position, decider_position}.
  Never averaged away.

## Gate (exactly as Part 1)
Read agent/needle/cite/gate.py (numeric_gate, gate_record, merge_checks, date_check) and render.py, and
copy the layout of out/part1/AMGN/part1.json: every text field that carries a number also carries its
marked twin (field + "_marked") with markers [n], [derived: a, b], [constant: NAME], [assumption], and a
marker_map {n: cite_id}; each block holds cites, plus derived and assumptions maps where needed, and a
numeric_check {status, checked, total, verified, derived, assumed, unsupported}. Run gate_record on every
gated text block (move, budget, cost, return, each math step, net, each why_passed, each kill signal, each
evidence block, each promo piece). A block whose numeric_check.status is "failed" is not printed: it goes
to rejected.jsonl with the reason and the unsupported list, and its slot is rewritten without the figure or
dropped. Stamp every cite with verify_status from verify_quote; withheld is false only when verified.
Bloomberg-licensed pages: cite by label, never quote. Machine-data rows (I/B/E/S, raw NADAC, WAC, Part D):
cite by locator, never quote or deep-link. Currency labelled on every non-USD figure.

## Output
Under <quant-model>/out/part2/<T>/:
- part2.json in the shape of docs/part2/UI_CONTRACT.md. Validate it parses and every key in the contract is present.
- part2.md: the same content as readable sections (move, case for it with the math, the two rejected
  alternatives, kill signals table, evidence, promo pieces and claims map table if any, unresolved).
- trace.jsonl: first line the header {step:0, category:"header", ticker, generated_at,
  lenses:["CFO/math","Decider/compliance"]}; then one line per candidate:
  {step, candidate_id, move, type, skeptic_cfo:{round1, round2}, skeptic_decider:{round1, round2},
  verdict: survived|narrowed|killed, reason, cites}.
- rejected.jsonl: every record that failed the gate, with the reason.

No league score, S, or priced-in score anywhere. Write from Python only; run
`grep -nE '[ ("]\.[0-9][0-9]*[BMbnmk%]' out/part2/<T>/*` and fix any hit. No em dashes. Report: candidates
ruled (survived/narrowed/killed), the pick id, gate passed/failed counts, and anything you could not source.
