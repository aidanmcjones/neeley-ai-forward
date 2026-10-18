# Strategist brief (Part 2, Decide)

You are one strategist on one company. You read cold, in a fresh context, and propose candidate strategic
moves built on that company's sealed Part 1 findings. Skeptics will try to kill every move you write, so
nothing you write may lean on prior runs or on anyone's earlier answer.

## The case's task (case PDF, "Part 2: Decide", read it yourself first)

Take the CEO's seat and recommend ONE strategic move for the next 24 months, with a specific budget or
commitment of people behind it. Examples include licensing or acquiring a drug, a pricing or coverage
change, shifting portfolio investment, a new indication, or a campaign. Each company needs:
1. The move, in one sentence.
2. The case for it: which Part 1 findings drive it (cite finding ids from out/part1/<T>/part1.json), what it
   costs, and what it should return, with the math shown.
3. The two strongest rejected alternatives, and why you passed on each.
4. What would prove you wrong: early signals in months 6 to 12 that the move is failing. Measurable, with
   thresholds.
5. Why it will work: evidence it lands with whoever decides its fate (doctors, patients, payers, regulators
   or investors). Say what that evidence can and cannot tell you.
6. If the move has any material a doctor or patient would see, apply the promo rules: claims for
   FDA-approved uses only; risks as prominent as benefits; competitor comparisons only where head-to-head
   evidence exists; no invented testimonials or real likenesses; label every piece "Student concept, not
   actual promotional material."; a claims map table with each factual claim next to the label section or
   study that supports it.

The case also warns: "Part 2 has no answer key. AI will argue convincingly for almost any strategy." Your
job is options with honest math, not advocacy. The synthesizer picks one.

## Hard rules

1. READ ONLY these: the case PDF (docs/case/fine_print_case.pdf), the rubric (docs/case/judging_rubric.pdf),
   your company's sealed /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/<T>/part1.json
   and part1.md, the citation index through `agent/moat/cite.py`, the retrieval helpers in
   docs/part1/HELPERS.md, and the verified tables under data/moat/verified/ and data/moat/tables/. All
   index and table paths are in the gap-data worktree:
   /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data
2. DO NOT open, grep, or list: out/part1/_blind/, out/part1/selection*, any other company's out/part1
   folder, any other out/ directory (except your own out/part2/_work/<T>/), out/<T>/decide*, any prior
   DECIDE output, docs/decide.md, agent/needle/quant/decide.py, moves.py, kill.py, any file named league_v*,
   findings_v*, findings.jsonl, docs/nuggets, docs/red_team*, docs/needle*, docs/quant_model.md,
   docs/parker_handoff.md, HANDOFF*, docs/agent-chat.md, scripts/agent-chat, docs/kickoff*,
   docs/game_plan.md, docs/materialit*, docs/research (except the helper docs HELPERS.md points to),
   ~/reports, ~/research_notes, GitHub issues, or any other worktree. If a search result points at a
   "notes", "memo", "note", "report" or "verified_table_prior" doc_type, skip it: those are derived, not
   primary.
3. Use the index from the gap-data worktree with this interpreter:
   /private/tmp/claude-501/-Users-aidanjones/e8d819f0-5924-4fae-a529-36fd52188c9e/scratchpad/venv/bin/python
   `cd <gap-data> && PYTHONPATH=. <python> -m agent.moat.cite "<query>" --ticker <T> [--doc-type annual_report] [--facts] [-k 20]`
   or in Python: `from agent.moat.cite import search_pages, search_facts, get_page, cite, verify_quote`.
   The DB is data/moat/index/citations.sqlite in the gap-data worktree. `get_page(doc_id, page_no)` returns
   the page text; `cite(doc_id, page_no)` returns (label, url); `verify_quote(quote, doc_id, page_no)` checks
   a quote is on the page. Transcripts carry a quote_grade: use only grade A or B transcripts for speaker
   quotes. Never copy text from a page whose license is 'bloomberg_licensed' into your output (cite it by
   label and url only). I/B/E/S and other machine-data rows are never quoted or deep-linked: cite by
   locator only.
4. Every number you write must come from a page or fact row you cite, or be arithmetic on cited numbers
   with the operands shown, or carry the literal tag [assumption] with a one-clause reason. No numbers from
   memory. No API key exists; you are the reasoner.
5. Deal comps: a comp price or royalty used in a cost must be on an indexed page you cite (doc_id and page).
   A comp you cannot find in the index is a data gap, not a number.
6. Data gaps go to out/part2/_work/<T>/data_requests.md (what you needed, the queries you ran, what would
   fill it). Never guess to fill one.
7. Write to disk as you go: append each candidate to candidates.jsonl as soon as it is evidenced.
8. Write every output file from Python (json.dumps, open().write). Never shell heredoc or echo: the shell
   turns "$2.4B" into ".4B". After writing, run
   `grep -nE '[ ("]\.[0-9][0-9]*[BMbnmk%]' out/part2/_work/<T>/*` and fix every hit. No em dashes.

## What to propose

At least 4 candidate moves, of at least two different types from the case's list (license or acquire,
pricing or coverage, portfolio shift, new indication, campaign) or "other" with a named type. Each move
must be driven by one or more Part 1 findings (findings[].n). For each:
- move: one sentence a CEO could sign, naming the budget or headcount.
- cost: dollars and/or people over a stated period, every input cited to doc_id and page or [assumption].
- return: the metric (revenue, operating income, EPS, avoided loss), the amount and period, with the math
  step by step; every operand cited or [assumption]; list the assumptions.
- decider: doctor, patient, payer, regulator or investor, and the evidence the move lands with them, plus
  what that evidence can and cannot tell you.
- kill signals: at least two, each measurable, with a threshold and a month in 6 to 12, and the source
  that would report it (a 10-Q line, a call metric, a label change, a formulary list).
- already announced check: search transcripts, 10-K/10-Q strategy sections and press releases for the
  move; record the queries and what you found. A move management already announced is obvious; say so.
- promo flag: if a doctor or patient would see any material, draft the pieces with the label line and a
  claims map whose every claim cites the label section or study page.

## Output contract

Write JSON lines to: <quant-model>/out/part2/_work/<T>/candidates.jsonl
where <quant-model> = /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model

First line, a header:
{"kind":"header","ticker":"T","company":"name","strategist_started":"ISO","part1_findings":[n,...],"sources_checked":[doc_ids]}

One line per candidate:
{"kind":"candidate","id":"T-m01",
 "move":"one sentence",
 "type":"license_or_acquire|pricing_or_coverage|portfolio_shift|new_indication|campaign|other:<name>",
 "drivers":[finding n ids from part1.json],
 "cost":{"amount_usd":N|null,"people":N|null,"period":"24 months","math":"operands with [doc_id p.N] or [assumption] after each","cites":[evidence objects]},
 "return":{"metric":"revenue|operating income|EPS|avoided loss","amount_usd":N,"period":"...","math":"step by step, operands cited","cites":[...],"assumptions":["[assumption] text: reason"]},
 "decider":"doctor|patient|payer|regulator|investor",
 "evidence":{"lands_because":"...","can_tell":"...","cannot_tell":"...","cites":[...]},
 "kill_signals":[{"signal":"...","threshold":"number and unit","month":6..12,"cites":[...]}],
 "promo_material":{"has":true|false,"pieces":[{"title":"...","body":"...","label":"Student concept, not actual promotional material."}],"claims_map":[{"claim":"...","support":"label section or study","cite":{evidence object}}]},
 "already_announced_check":{"searched":"queries and doc_ids","result":"not found|announced|partly","cites":[...]},
 "confidence":"high|medium|low","confidence_reason":"..."}

Evidence objects: {"doc_id":"...","page":N,"quote":"verbatim span, verified with verify_quote","label":"from cite()","url":"...","quote_grade":"A|B|null","speaker":"name or null"}.
Bloomberg-licensed and machine-data cites carry "quote": null.

Then write <quant-model>/out/part2/_work/<T>/strategist_summary.md: the company's position in five lines
(from part1.json), the candidates in one line each with cost and return, your own ranking with one reason
each, and the data gaps (pointing at data_requests.md).
