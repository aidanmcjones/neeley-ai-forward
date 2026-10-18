# Part 1 writer brief (Phase B)

You write the Part 1 deliverable for one top-3 company, from the blind-pass rulings, with every number
passing the per-number citation gate. Inputs:
- /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/<T>/
  (candidates.jsonl for evidence objects, synthesis.json for rulings, trace_part.jsonl, both skeptic files)
- the case PDF (gap-data docs/case/fine_print_case.pdf) for the deliverable's exact requirements
- the citation index via agent/moat/cite.py and the retrieval helpers listed in docs/part1/HELPERS.md
  (run from the gap-data worktree with the scratchpad venv interpreter)
- the gate: agent/needle/cite/gate.py (numeric_gate, gate_record) and render.py in the quant-model worktree;
  read docs/citations.md for the statuses, markers and the public rule.
You may read league/needle/red-team files now (Phase A is sealed), but every row you write must trace to a
candidates.jsonl evidence object or a page you open and verify yourself.

## Rows
At least five findings. Use surviving and narrowed rulings first, in the synthesizer's corrected wording.
If fewer than five survive, add rows from killed-as-obvious candidates that are still true, cited and sized,
and mark each such row obviousness "high" with one honest clause saying it is on the record (where). Never
add a row the materiality skeptic refuted on the math. Each row: finding (one plain sentence), source
(filing and page, or speaker name plus exact quote from a grade A or B transcript only), impact with the
math shown (operands each with a cite), peer comparison (cited), confidence high/medium/low with the reason.

Sharpest Needle: the surviving ruling with the highest materiality and lowest obviousness; say why in two
sentences. If no ruling is both, say so plainly and name the least-bad choice as such.

Product fine print: the product from synthesis.json's product ruling vs the rivals the case lists. Five rows
with these exact keys: "approved uses", "boxed warnings and safety", "dosing and convenience",
"patent and exclusivity timeline", "pricing and gross-to-net". Use case_labels.label_compare for the
label rows and quote the label page, loe_calendar for exclusivity, case_gtn for pricing. Tie to at least
one financial finding (financial_tie with math). One sentence on what limits growth and whether it is
priced in (priced_in.call: "priced in" | "not priced in" | "untestable"; untestable when no consensus cite).

## Gate
Every text field that carries a number also carries its marked twin (field + "_marked") with markers
[n], [derived: a, b], [constant: NAME], [assumption], and a marker_map {n: cite_id}. Run gate_record on
each finding and each product cell; a record whose numeric_check.status is "failed" does not go into
part1.json: it goes to rejected.jsonl with the reason. Bloomberg-licensed pages: cite by label, never quote.
Machine-data rows (raw NADAC, WAC, Part D, I/B/E/S no_verified_copy): cite by locator, never quote or
deep-link. Currency labelled on every NVO and AZN figure.

## Output
<quant-model>/out/part1/<T>/part1.json in the contract agreed with the UI session (see
docs/part1/UI_CONTRACT.md), part1.md (the same content as a readable table and sections), trace.jsonl
(first line the header record {step:0, category:"header", categories:[the eight strings], ticker,
generated_at}; then the lines of trace_part.jsonl with step renumbered and finding_n added where a ruling
became a row), and rejected.jsonl. Validate the JSON parses. No em dashes anywhere. Report counts: rows,
gate passed/failed, needle id, product, and anything you could not source.
