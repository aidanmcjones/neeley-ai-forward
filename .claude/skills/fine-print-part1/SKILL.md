---
name: fine-print-part1
description: "Run the Neeley 'Fine Print' Part 1 (Find the Story) pipeline: ten blind readers walk the case PDF's eight hiding places over the citation index, a materiality skeptic and an obviousness skeptic argue each candidate over two rounds, a synthesizer rules, a ranker seals a blind top 3 with a sha256, then Phase B writers produce the five-findings table, Sharpest Needle and product fine print for each picked company with every number through the per-number citation gate. Triggers: 'fine print part 1', 'find the story', 'run the blind readers', 'blind company selection', 'Part 1 pipeline', 'five findings table', 'sharpest needle', 'rerun Part 1 for <ticker>', 'rebuild out/part1'. Do not use for Part 2 (the CEO move); that is fine-print-part2."
---

# Fine Print, Part 1: Find the Story

This skill packages the pipeline that produced `out/part1/` on the `quant-model` branch of
`aidanmcjones/neeley-ai-forward` (PR #21; Part 1 final at 7eb0dca, briefs at 2979fb0). The briefs under
`briefs/` are byte-for-byte copies of `docs/part1/*.md` on that commit. They ARE the prompts the workers
were given: every worker was told to read its brief in full and follow it. Do not paraphrase them into the
launch prompt; point the worker at the file. `reference/LAUNCH_PROMPTS.md` holds the exact launch and resume
texts recovered from the orchestrating session's transcript, one per role.

The case's test (case PDF, Part 1): findings material enough to change an investor's view AND not obvious
(not the starter thread, a patent cliff, a press-release headline, or something management said plainly),
at least five per company with impact math, peer comparison and confidence, plus a Sharpest Needle and a
product fine-print comparison against the rivals the case lists. "Part 1 has points for what is hidden",
so the design is blind (fresh contexts, no access to prior runs), adversarial (two skeptics who read each
other), and fail-closed on numbers (the per-number gate).

## Files in this skill

| File | What it is |
|---|---|
| `briefs/BLIND_READER_BRIEF.md` | Phase A reader brief: READ ONLY list, DO NOT READ list, the eight hiding places with their exact category strings, candidates.jsonl contract |
| `briefs/SKEPTIC_BRIEF.md` | Both lenses (MATERIALITY AND MATH, OBVIOUSNESS), round 1 and round 2 shapes |
| `briefs/SYNTHESIZER_BRIEF.md` | Rulings survived / narrowed / killed, synthesis.json and trace_part.jsonl shapes |
| `briefs/RANKER_BRIEF.md` | Blind ranking on the case's test, the sealed selection.md and selection.json, the appendix written only after the seal |
| `briefs/PART1_WRITER_BRIEF.md` | Phase B writer: rows, needle, product table, the gate, output files |
| `briefs/UI_CONTRACT.md` | The out/part1 shape the UI exporter consumes. Never change it without the UI session |
| `briefs/HELPERS.md` | The scraper's retrieval helpers (case_sets, case_forces, case_footnotes, case_segments, case_working_capital, case_labels, case_gtn, case_calls, case_risk_diff) and the index-rebuild note |
| `reference/citations.md` | The citation package: verify ladder, statuses, the public rule, the per-number gate, markers |
| `reference/LAUNCH_PROMPTS.md` | Verbatim launch prompts and round-2 resume messages, one per role |

## Environment

- Code and outputs: the quant-model worktree (`/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model`, branch `quant-model`). Run git there; never `cd` to the main repo root; never bare `git stash`.
- Data: the gap-data worktree (`/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data`, branch `data-moat`, PR #16, final at d92e501): `docs/case/fine_print_case.pdf`, `docs/case/judging_rubric.pdf`, `data/moat/index/citations.sqlite`, `data/moat/verified/`, `data/moat/tables/`, `data/moat/CASE_SOURCES.md`, and `agent/moat/cite.py` (search_pages, search_facts, get_page, cite, verify_quote) plus the eight `agent/moat/case_*.py` helpers.
- Environment variables for the quant-model code: `export NEEDLE_MOAT=<gap-data>/data/moat` and, in a second export, `CITATIONS_DB=$NEEDLE_MOAT/index/citations.sqlite` (a single `export A=.. B=$A/..` line leaves B empty in zsh; the gate then exits with "/index/citations.sqlite missing").
- Interpreters. The briefs name the original session's scratchpad venv (`/private/tmp/claude-501/-Users-aidanjones/e8d819f0-.../scratchpad/venv/bin/python`, Python 3.14, with rapidfuzz and pytest); that path is session-specific and may be gone. Workers need an interpreter that imports `agent.moat.cite` from the gap-data worktree with `PYTHONPATH=.`; create a venv with rapidfuzz if the old one is missing and substitute the path in the launch prompt. For the quant-model generators and tests use `PYTHONPATH=. /opt/homebrew/bin/python3` (no pytest installed there as of 2026-10-18; `/usr/bin/python3` is too old).
- The gate: `agent/needle/cite/gate.py` (numeric_gate, gate_record, merge_checks, date_check) and `render.py` in the quant-model worktree. No API key is used anywhere; the worker agents are the reasoners.
- Subagent cap: 10 concurrent agents was in force (memory `subagent-cap-ten`); run `cap.sh` before each wave if that memory still applies.

## Stage order and wave structure (as run on 2026-10-17/18 CT)

Every launch below was `subagent_type: general-purpose`, `model: opus`, no effort override, with the worker preamble ("CONTEXT: You are a WORKER agent, not an orchestrator. RULES: Complete ONLY the task described below; use tools directly; write results to disk incrementally; do NOT spawn sub-agents; do NOT call TaskCreate/TaskUpdate or progress.sh; report results with absolute file paths and counts.") followed by `TASK: ...` naming the brief to read in full and the company. Times are UTC from the transcript.

| Wave | Agents | Model | Each received | Writes |
|---|---|---|---|---|
| A1 Blind readers | 10, one per shortlist company (MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD), launched together 03:27 to 03:28 | opus | BLIND_READER_BRIEF path, ticker and company name (NVO: "reports in DKK, keep currencies labelled"; AZN: "USD under IFRS, per-share may be per ordinary share or per ADR, label which"); nothing else | `out/part1/_blind/<T>/candidates.jsonl`, `reader_summary.md` |
| A2 Skeptics round 1 | 20 (materiality and obviousness per company), launched per company as its reader finished, 03:42 to 03:53 | opus | SKEPTIC_BRIEF path, lens, the company's candidates.jsonl and reader_summary.md, and three to five company-specific checks the orchestrator lifted from the candidates (for example "is the 5.6 times sales figure gross or net of tax, what share count") | `skeptic_materiality_r1.json`, `skeptic_obviousness_r1.json` |
| A3 Skeptics round 2 | the same 20 agents, resumed by SendMessage 03:49 to 04:00 (not new agents, so each keeps its round 1 notes) | opus | the other lens's round 1 file path, "read their argument AGAINST THE SOURCES, concede, hold or narrow, do not restate round 1", and the orchestrator's summary of where the two lenses clashed | `skeptic_materiality_r2.json`, `skeptic_obviousness_r2.json` |
| A4 Synthesizers | 10, one per company, launched as each company's four skeptic files existed, 03:53 to 04:07 | opus | SYNTHESIZER_BRIEF path, the blind folder, and the orchestrator's summary of where the skeptics converged and split, with the specific facts to settle from the page | `synthesis.json`, `trace_part.jsonl` |
| A5 Ranker | 1, launched 04:10 after all ten synthesis files existed | opus | RANKER_BRIEF path, the ten folders, the survivor counts per company with the instruction to rank on the case's test and not on that count alone | `out/part1/selection.md` (sealed), `selection.json`, then `selection_appendix.md` |
| B1 Writers | 3, one per picked company, launched together 04:14 | opus | PART1_WRITER_BRIEF, UI_CONTRACT, HELPERS, citations.md in that order, then the blind folder (synthesis.json first); the synthesizer's corrected wording per surviving id; which killed-as-obvious ids to use as on-the-record fill rows; the needle id; the product and its label edges and the finding it ties to | `out/part1/<T>/part1.json`, `part1.md`, `trace.jsonl`, `rejected.jsonl` |
| B2 Independent verifier | 1, launched 04:26 | opus | the three part1.json files, the index, the blind synthesis and skeptic files; "assume every number is WRONG until the cited page proves it; do not read the writers' reports or scripts; do not edit the part1 files" | `out/part1/verify_report.md` |
| B3 Priced-in calls, then verifier fixes | 1, launched 04:27, resumed twice | opus | replace the "untestable" priced-in call with an evidence-graded inference from four sources (item-level analyst attention in qa_turns, GDELT topic counts, I/B/E/S revision direction, event returns), gated; then (resume) apply the seven verifier fails, re-gating every touched text | the three part1.json and part1.md files |

Orchestrator-side steps between waves, done by the session itself rather than an agent: validate that every expected file exists and parses before starting the next wave (per company in Phase A, all three in Phase B); commit each wave; stamp verify_status, withheld and cite_id on every trace candidate cite by re-running verify_quote (a972ac3: 65 AMGN, 106 MRK, 89 PFE cites, all exact); after the seal, read the sealed file back and check the hash.

Wall clock: Phase A 03:27 to 04:12 UTC (45 minutes); Phase B writers 04:14 to about 04:26; verification, priced-in and fixes to 04:42. Commits on quant-model: e63a9d3 (blind folders and briefs), d457d7c (seal), 4be8696, 0aa2494 (seal procedure), 00cf846 PFE, c5c1c2d AMGN, d3c8980 MRK, 40f21b1, a972ac3, bf0ed1a (verify_report.md), a1ddc77 (priced-in), 7eb0dca (seven verifier fixes; final), 2979fb0 (HELPERS index-rebuild note).

What the run produced: 95 candidates across the ten companies (8 to 11 per company plus 1 to 4 no_finding records and one product record each); synthesizers ruled 70 killed, 25 narrowed, 0 survived as stated (the honest expected result; "management already said it" was the usual kill). Picked AMGN, MRK, PFE, sealed 2026-10-18T04:12:05Z, sha256 903fc656fa7a1d1b2bdf303d8d8f9321d5f1f7b741f6b751c4cdf4f9c40c8fa7. Each company's part1.json: 5 findings, all passed the gate, rejected.jsonl empty, needle finding 1, 5 product rows. The verifier checked 261 cites and 503 numbers: every number correct on its page, 7 attribution or scoping defects, all fixed at 7eb0dca.

Not recoverable from disk or transcript: per-agent token or dollar cost, any retries (the transcript shows one launch per role), and the exact wall time of each agent beyond the launch timestamps above.

## Input restrictions (the forbidden list)

Verbatim from BLIND_READER_BRIEF.md, and applied to skeptics, synthesizers and the ranker until the seal:

READ ONLY: the case PDF, the rubric, the citation index through `agent/moat/cite.py`, and the verified tables under `data/moat/verified/` and `data/moat/tables/`.

DO NOT open, grep, or list: any out/ directory (skeptics and synthesizers may read only `out/part1/_blind/<T>/` for their own company), any file named league_v*, findings_v*, findings.jsonl, docs/nuggets, docs/red_team*, docs/needle*, docs/quant_model.md, docs/parker_handoff.md, HANDOFF*, docs/agent-chat.md, docs/kickoff*, docs/game_plan.md, docs/materialit*, docs/research, ~/reports, ~/research_notes, GitHub issues, or any other worktree. Skip search results whose doc_type is "notes", "memo", "note", "report" or "verified_table_prior": derived, not primary.

Phase B writers may read league, needle and red-team files (Phase A is sealed) but every row must trace to a candidates.jsonl evidence object or a page the writer opens and verifies.

## The sealed selection (sha256 procedure, from out/part1/selection.json)

```json
"seal_procedure": {
  "covers": "every byte of selection.md before the final line that starts with 'sha256: ', with trailing newline characters removed",
  "excludes": "the 'sha256: <hex>' line itself and the newline(s) before it",
  "verify_shell": "sed '$d' out/part1/selection.md | perl -0pe 's/\\n+\\z//' | shasum -a 256",
  "verify_python": "import hashlib; t=open('out/part1/selection.md','rb').read(); i=t.rfind(b'sha256: '); print(hashlib.sha256(t[:i].rstrip(b'\\n')).hexdigest())",
  "note": "Hashing the whole file (including the hash line) cannot match by construction; that gives 6df19bb2... on the committed file."
}
```

The ranker computes the hash on the finished file, appends `sha256: <hex>` as the last line, writes selection.json ({picked, reasons, eliminated, survivors, sealed_at, sha256}), and only then reads league_v3.md, docs/nuggets/best_needle.json and docs/red_team*.md to write selection_appendix.md. selection.md is never edited after sealing (the appendix is a separate file so the hash stays valid). The UI reads the selection reasons from the sealed md, not the json.

## Output file layout

```
out/part1/
  _blind/<T>/            one folder per shortlist company (10)
    candidates.jsonl     header, candidate and no_finding lines, product line
    reader_summary.md
    skeptic_materiality_r1.json, skeptic_obviousness_r1.json
    skeptic_materiality_r2.json, skeptic_obviousness_r2.json
    synthesis.json       rulings, product ruling, company_score
    trace_part.jsonl     one line per candidate and no_finding
  selection.md           sealed; last line "sha256: <hex>"
  selection.json         picked, reasons, eliminated, survivors, sealed_at, sha256, seal_procedure
  selection_appendix.md  blind result vs league_v3 and the red-team pick (written after the seal)
  verify_report.md       the independent verifier's table per company and summary
  <T>/                   one folder per picked company (3)
    part1.json           UI_CONTRACT shape
    part1.md             the same content as readable sections
    trace.jsonl          header {step:0, category:"header", categories:[eight], ticker, generated_at} then the trace_part lines renumbered with finding_n
    rejected.jsonl       gate failures with reasons (empty in the final run)
```

The eight category strings, verbatim from the case and used everywhere: "Language drift", "Gross-to-net", "Inventory and receivables growing faster than revenue", "Segment and product table changes", "Footnotes", "Earnings-call Q&A", "Product fine print", "Peer contrast".

## Hard rules (every stage)

1. Every number comes from a page or fact row that is cited, or is arithmetic on cited numbers with the operands shown, or carries the literal tag [assumption]. No numbers from memory.
2. Quotes only from grade A or B transcripts; Bloomberg-licensed pages cited by label and url, never quoted; machine-data rows (I/B/E/S, raw NADAC, WAC, Part D, no_verified_copy) cited by locator, never quoted or deep-linked. Currency labelled on every NVO and AZN figure.
3. Every text field that carries a number has its marked twin (`field_marked`) with markers [n], [derived: a, b], [constant: NAME], [assumption] and a `marker_map` {n: cite_id} in the same block. A block with markers and no marker_map is not self-verifying (the verifier failed the AMGN needle for this).
4. Run gate_record on every finding and every product cell. Only `numeric_check.status` passed or no_numbers is printed; failed records go to rejected.jsonl with the reason.
5. Write output files from Python (json.dumps, open().write) or the Write tool, never shell heredocs or echo: the shell turned "$2.4B" into ".4B" once (4be8696 restored it).
6. After every write run `grep -nE '[ ("]\.[0-9][0-9]*[BMbnmk%]'` over the written files and fix every hit; also `grep -c $'\xe2\x80\x94'` must be 0 (no em dashes anywhere).
7. No league score, L, S, robustness words or priced-in score on any Part 1 output. The pitch-facing material is the impact-ranked cited findings, the needle by the plain rule, the product table.
8. Figure-free prose where the UI contract requires it: the selection card prints only figure-free sentences; any figure in trace or prose that is not in the company's gated-figure set is withheld by the UI exporter, and killed trace candidates lose all figures. Write kill reasons in words.
9. Skeptics default to refuted when they cannot independently confirm; synthesizers do not vote or average; "unrefuted" is weaker than "confirmed" and the reason says which.
10. The ranker uses no formula and no score. Never touch selection.md after the seal.

## Verification steps

1. After each wave: every expected file exists and `json.load` / line-wise `json.loads` succeeds for every company in the wave.
2. Seal: run `verify_python` above and compare with the last line of selection.md and `selection.json["sha256"]`.
3. Per part1.json: 5 or more findings; every `numeric_check.status` in {passed, no_numbers}; every `cites[]` entry a full evidence object (cite_id, doc_id, page, quote, url, verify_status, withheld, grade); every [n] marker resolves through the block's marker_map; product rows use the five exact row keys; priced_in.call in {"priced in", "not priced in", "untestable"}; trace header has the eight category strings; finding_n set on the rows.
4. Decimal grep and em-dash grep over `out/part1/**`.
5. Re-run verify_quote on every cite (findings and trace candidates) and stamp verify_status, withheld, cite_id, grade.
6. Independent verifier agent (the B2 prompt in LAUNCH_PROMPTS.md): fresh context, output files and sources only; fix what it finds and re-gate.
7. UI exporter check on the ui branch (PR #22): `PYTHONPATH=. /opt/homebrew/bin/python3 agent/ui_part1_export.py --check` must report 0 errors and 0 figures withheld; hand the UI session the new quant-model SHA whenever a ticker's outputs change. `docs/part1/UI_CONTRACT.md` does not change.
8. Tests: `PYTHONPATH=. <python with pytest> -m pytest tests -q` in the quant-model worktree with both env vars set.

## Known gate limits (state them, do not paper over them)

- The number tokenizer skips numbers that follow a "ROW" table label, so such a leg carries [assumption] with its page (AMGN TAVNEOS ROW $36M).
- The gate checks numbers, not attribution or scope: all seven verifier fails were attribution or scoping (an overclaimed "only" in a needle rationale, a refuted ratio restated, a guide applied to the wrong base, "launches with" vs "will be expanding in the future", a cite to a facts field that does not exist, a marker pointing at a non-operand cite, an uncited clause). An independent verifier pass is still required.
- `no_numbers` passes without evidence; a sentence with no figure is shown like a passed one.
- Not counted by the tokenizer: bare years 1900 to 2099, dates, period labels (Q2 2026, FY2025), form names (10-K), page / item / note numbers, ids, footnote markers, URLs.
- A number verifies only inside the quoted span or as the cite's own value; page text outside the quote never supports a number (so quote the span that carries the figure).
- Facts rows have no viewer link; XBRL cites point at companyfacts JSON; derived numbers cite the base figure's page, not an XBRL anchor.
- Transcript quotability depends on the index build: HELPERS.md lists which quarters became grade B after the blind pass (the blind skeptics used some only as "proof it was said").
- Topic-keyed attention tables (priced_in_scorecard, never_asked, analyst_topics, news_mentions) have a fixed nine-topic vocabulary; item-level attention must come from full text (qa_turns.csv); no item-level GDELT queries exist.
- Index gaps the readers hit are recorded per company in reader_summary.md and in selection.md's Limits section (no Q3 2026 10-Qs; Tecentriq SC and Rybrevant Faspro labels absent).

## Lessons recorded from the run

- "0 survived, N narrowed" is the intended honest trace result; on-the-record fill rows (killed by the obviousness skeptic, kept to reach five, obviousness "high") are tagged and say where management said it.
- Never name a real executive unless the name is on a cited page; use the role.
- Readers' data-gap notes can be wrong (the AMGN reader said TAVNEOS sales were in no filing table; the 10-K itemizes them); the synthesizer settles such facts from the page.
- The orchestrator's summaries in synthesizer and writer prompts are pointers, not evidence: every prompt says to verify against the files and the sources.
- Write partial output early (readers append each candidate as it is evidenced); the host Mac can sleep mid-run.
- Timelines: the only deadline is the Devpost submission; never cite or enforce another cutoff.
