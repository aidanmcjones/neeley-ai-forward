# Ranker brief (Phase A, blind selection)

You rank the ten shortlist companies on the case's own test and seal the result. Read only:
- the case PDF and rubric (gap-data docs/case/),
- the ten synthesis.json and reader_summary.md files under
  /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/<T>/,
- and, only to settle a fact, the cited pages through agent/moat/cite.py (gap-data worktree, interpreter
  /private/tmp/claude-501/-Users-aidanjones/e8d819f0-5924-4fae-a529-36fd52188c9e/scratchpad/venv/bin/python).
Same DO NOT READ list as the readers (no league_v*, findings_v*, docs/nuggets, docs/red_team*, docs/needle*,
docs/quant_model.md, HANDOFF*, agent-chat, other worktrees) until the seal is written.

## The test (case text)
Material enough to change an investor's view AND not obvious (not the starter thread, a patent cliff,
a press-release headline, or something management said plainly), PLUS one product from the company's
competitive set that compares well against its listed rivals and ties to a financial finding. The case
also needs at least five findings per company, so count how many surviving or narrowed rulings each
company has and how far it is from five with honest, cited, sized rows (killed-as-obvious rows can still
be table rows if cited and sized; they just do not count toward "material and not obvious").

## Method
No formula, no score. Write a short reasoned comparison. For each company record: survivors (survived +
narrowed) with materiality and obviousness grades, the best candidate and its size, the product ruling,
the data limits the reader hit (transcript grades, missing tables). Then rank. Ties break on the product
comparison and on how many honest rows can fill a five-row table.

## Output
1. <quant-model>/out/part1/selection.md: top 3 with why each beat the other nine (one paragraph each),
   then one line per eliminated company, then a "Method" section of five lines, then a "Limits" section.
   No numbers that are not in a synthesis.json ruling or a cited page. No em dashes.
   LAST LINE exactly: `sha256: <hex>` where hex = sha256 of the file content above that line (everything
   before the final newline that precedes "sha256:"). Compute it with
   `python -c "import hashlib,sys; print(hashlib.sha256(open(p,'rb').read()).hexdigest())"` on the file
   before appending the line, then append the line.
2. <quant-model>/out/part1/selection.json: {"picked":[T1,T2,T3],"reasons":{T:text},"eliminated":{T:one line},
   "survivors":{T:[ids]},"sealed_at":ISO8601 UTC,"sha256":hex}.
3. Only after both are written and the hash line is appended: read out/league_v3.md and docs/nuggets/best_needle.json
   and docs/red_team*.md (if present) in the quant-model worktree, and write
   <quant-model>/out/part1/selection_appendix.md comparing the blind top 3 and needle candidates with the
   league ranking and Parker's red-team pick, stating plainly where they agree and differ and why. Do not
   touch selection.md after sealing.
Report the three picks, the hash, and the file paths.
