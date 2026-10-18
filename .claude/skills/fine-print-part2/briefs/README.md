# Part 2 (Decide) pipeline

The three companies are AMGN, MRK and PFE, from the sealed Part 1 selection (out/part1/selection.json).
No other company runs Part 2. Each company runs the same three-stage pipeline on its sealed
out/part1/<T>/part1.json.

## Stages
1. Strategist (docs/part2/STRATEGIST_BRIEF.md): fresh context, proposes 4 or more cited candidate moves of
   at least two types, each with cost, return math, decider evidence, kill signals and a promo flag.
2. Skeptic pair (docs/part2/SKEPTIC_BRIEF.md): lens CFO/math and lens Decider/compliance, both default to
   kill. Round 1 independent; round 2 each reads the other's round 1 file and concedes, holds or narrows.
3. Synthesizer (docs/part2/SYNTHESIZER_BRIEF.md): rules on each candidate, picks ONE move and two rejected
   alternatives, runs the per-number fail-closed gate, writes the deliverable.

## Waves
- Wave 1: three strategists in parallel (one per company).
- Wave 2: six round 1 skeptics in parallel (two lenses x three companies).
- Wave 3: six round 2 skeptics in parallel, each given the other lens's round 1 file.
- Wave 4: three synthesizers in parallel.
Each wave starts only when the previous wave's files exist and parse for all three companies.

## Where outputs land (quant-model worktree)
- out/part2/_work/<T>/: candidates.jsonl, strategist_summary.md, data_requests.md,
  skeptic_cfo_r1.json, skeptic_decider_r1.json, skeptic_cfo_r2.json, skeptic_decider_r2.json.
- out/part2/<T>/: part2.json (shape in docs/part2/UI_CONTRACT.md), part2.md, trace.jsonl, rejected.jsonl.

## Rules every stage keeps
Citation index and tables from the gap-data worktree only; every number cited, derived from cited
operands, or marked [assumption]; quotes from grade A or B transcripts only; Bloomberg-licensed text cited
by label, never quoted; I/B/E/S rows never quoted; outputs written from Python, never shell heredoc;
the `[ ("]\.[0-9]` grep run after every write; no em dashes; no league score, S, or priced-in score.
