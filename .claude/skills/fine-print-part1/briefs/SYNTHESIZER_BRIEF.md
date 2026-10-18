# Synthesizer brief (Phase A dialectic)

Two skeptics examined one company's candidate nuggets through different lenses (materiality and math;
obviousness), then read each other. You resolve the exchange. You do not vote and you do not average.

Inputs, all under /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/<T>/:
candidates.jsonl, skeptic_materiality_r1.json, skeptic_obviousness_r1.json, skeptic_materiality_r2.json,
skeptic_obviousness_r2.json, reader_summary.md. Where the skeptics still disagree on a fact, open the cited
page yourself through agent/moat/cite.py (gap-data worktree, same interpreter the readers used) and settle
it from the source. Same DO NOT READ list as the readers.

For each candidate, rule: survived (as stated), narrowed (survives as the corrected claim you write), or
killed. A candidate that only survives because the reader wanted it to is killed. "Unrefuted" is weaker than
"confirmed": say which you mean in the reason.

Write <quant-model>/out/part1/_blind/<T>/synthesis.json:
{"ticker":"T","company":"...",
 "rulings":[{"id":"T-c01","category":"...","verdict":"survived|narrowed|killed",
   "claim":"the surviving sentence (corrected if narrowed)",
   "reason":"what each side conceded, what still disagrees, how you settled it, with doc_id and page",
   "materiality":"high|medium|low","obviousness":"low|medium|high",
   "confidence":"high|medium|low","unresolved":"text or null"}],
 "product":{"verdict":"survived|narrowed|killed","product":"...","rivals":[...],"reason":"..."},
 "company_score":{"material_non_obvious_survivors":N,"best_candidate_id":"...","one_line":"why this company is or is not a good pick on the case's test"}}

Then append the rulings to trace form: write <quant-model>/out/part1/_blind/<T>/trace_part.jsonl, one JSON
per candidate: {"step":n,"category":"...","query":"<from candidate>","documents":[<from candidate>],
"candidate":{"text":"...","cites":[<evidence from candidate>]},
"skeptic_materiality":{"round1":"...","round2":"..."},"skeptic_obviousness":{"round1":"...","round2":"..."},
"verdict":"survived|killed|narrowed","verdict_reason":"..."} and also one line per no_finding record with
verdict "killed" and reason "no finding: <documents checked>".
