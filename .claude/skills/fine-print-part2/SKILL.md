---
name: fine-print-part2
description: "Run the Neeley 'Fine Print' Part 2 (Make the Call) pipeline on a company that passed Part 1: a fresh-context strategist proposes four or more cited CEO moves from the sealed Part 1 findings, a CFO/math skeptic and a Decider/compliance skeptic try to kill each move over two rounds reading each other, and a synthesizer picks ONE move with budget, return math, two rejected alternatives, kill signals, decider evidence and promo claims map, every figure through the per-number citation gate and the UI exporter's hard checks. Triggers: 'fine print part 2', 'make the call', 'CEO move', 'run the strategist', 'Part 2 pipeline', 'decide for <ticker>', 'rerun Part 2 for <ticker>', 'rebuild out/part2'. Requires out/part1/<T>/part1.json from fine-print-part1."
---

# Fine Print, Part 2: Make the Call

This skill packages the pipeline that produced `out/part2/` on the `quant-model` branch of
`aidanmcjones/neeley-ai-forward` (PR #21; final MRK ff953cd, PFE f10006e, AMGN 630a439; briefs 319b38a and
6c76a16). The briefs under `briefs/` are byte-for-byte copies of `docs/part2/*.md` plus the Part 1 files they
depend on (`docs/part1/HELPERS.md`, `docs/part1/UI_CONTRACT.md` as PART1_UI_CONTRACT.md). They ARE the
prompts the workers were given: every worker was told to read its brief in full and follow it. Point the
worker at the file; do not paraphrase. `reference/LAUNCH_PROMPTS.md` holds the exact launch texts, the
round-2 resume messages and the mid-wave coordinator messages recovered from the orchestrating session's
transcript.

The case's task (case PDF, Part 2): take the CEO's seat and recommend ONE strategic move for the next 24
months with a specific budget or commitment of people; the case for it (which Part 1 findings drive it, cost,
return with the math); the two strongest rejected alternatives; what would prove you wrong (measurable
signals in months 6 to 12); why it will work (evidence it lands with whoever decides, and what that evidence
cannot tell you); and, for anything a doctor or patient would see, the six promo rules and a claims map. The
case warns "Part 2 has no answer key. AI will argue convincingly for almost any strategy", so the design is
options with honest math, two skeptics who default to kill, and a synthesizer who never averages.

## Files in this skill

| File | What it is |
|---|---|
| `briefs/README.md` | Stages, waves, output locations, the rules every stage keeps |
| `briefs/STRATEGIST_BRIEF.md` | READ ONLY and DO NOT READ lists, what to propose, candidates.jsonl contract, data_requests.md |
| `briefs/SKEPTIC_BRIEF.md` | Lenses CFO AND MATH (skeptic_cfo) and DECIDER AND COMPLIANCE (skeptic_decider), round shapes |
| `briefs/SYNTHESIZER_BRIEF.md` | Rulings, the pick, the gate exactly as Part 1, output files |
| `briefs/UI_CONTRACT.md` | part2.json shape plus the UI exporter's hard checks (appended at 6c76a16). Never change it without the UI session |
| `briefs/HELPERS.md` | The scraper's retrieval helpers and the index-rebuild note (from docs/part1) |
| `briefs/PART1_UI_CONTRACT.md` | The Part 1 shape, because drivers[].finding_n and the gated-figure set check against it |
| `reference/citations.md` | Verify ladder, statuses, the public rule, the per-number gate, markers |
| `reference/LAUNCH_PROMPTS.md` | Verbatim launch, resume and mid-wave messages, one per role |

## Environment

Same as fine-print-part1: quant-model worktree for code and outputs, gap-data worktree for the case PDF,
rubric, `citations.sqlite`, verified tables and `agent/moat/cite.py` (run with `PYTHONPATH=.`); export
`NEEDLE_MOAT` and then `CITATIONS_DB` in two separate exports; an interpreter that imports `agent.moat.cite`
(the briefs name the original session's scratchpad venv, which is session-specific; substitute); the gate at
`agent/needle/cite/gate.py` and `render.py`. Inputs that must exist first: `out/part1/<T>/part1.json` and
`part1.md` for the company, sealed by fine-print-part1. No API key is used; no agent may set, read or rename
ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_HOLD. Subagent cap 10 was in force (memory `subagent-cap-ten`).
Only the companies in `out/part1/selection.json["picked"]` run Part 2.

## Stage order and wave structure (as run on 2026-10-18, times UTC)

Every launch was `model: opus` with no subagent_type (the default general-purpose agent) and no effort
override, with the worker preamble ("CONTEXT: You are a WORKER agent, not an orchestrator. RULES: Complete
ONLY the task described below; use tools directly; write results to disk incrementally; do NOT spawn
sub-agents; do NOT call TaskCreate/TaskUpdate or progress.sh; report results with absolute file paths and
counts; no em dashes anywhere; never set, read or rename ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_HOLD; keep
helper scripts in your own scratchpad subfolder, never at the scratchpad root") followed by `TASK: ...`.

| Wave | Agents | Each received | Writes |
|---|---|---|---|
| 0 Briefs | 1 agent (05:05), given a 10k-character prompt to write docs/part2 by mirroring docs/part1's tone, hard rules, forbidden lists and gate rules | the docs/part1 files, the case's Part 2 text, the UI session's part2.json shape | `docs/part2/*.md` (already exist; skip this wave unless the briefs change) |
| 1 Strategists | 3, one per picked company, launched together 05:07 | STRATEGIST_BRIEF path, ticker; "at least four moves of at least two types, each costed with cited math; finish within about 40 minutes; depth on four well-evidenced moves beats six thin ones"; mid-run (05:10) a SendMessage with the scraper's data inventory (which labels, deal comps, CMS tables and head-to-head rows are indexed and which are not) | `out/part2/_work/<T>/candidates.jsonl`, `strategist_summary.md`, `data_requests.md` |
| 2 Skeptics round 1 | 6 (CFO/math and Decider/compliance per company), launched per company as its strategist finished, 05:16 to 05:17 | SKEPTIC_BRIEF path, lens, candidates.jsonl with the candidate ids, part1.json, and the orchestrator's list of the specific operands, comps, deciders and promo pieces to test (for example "m03 prices a UCB buyout at 5x with no indexed comp"); PFE skeptics also got the scraper's notes (CMS Part D claims are annual to 2024; formulary counts are plan-count shares); "you will be resumed for round 2, keep your notes" | `skeptic_cfo_r1.json`, `skeptic_decider_r1.json` |
| 3 Skeptics round 2 | the same 6 agents resumed by SendMessage 05:21 to 05:23 | the other lens's round 1 file path, "read it in full, then read their arguments AGAINST THE CITED PAGES; concede, hold or narrow", and the orchestrator's statement of the key clash, with the inside-24-month math or decider question each side must answer | `skeptic_cfo_r2.json`, `skeptic_decider_r2.json` |
| 4 Synthesizers | 3, launched 05:24 to 05:25 once all four skeptic files existed and the scraper's data wave (data-moat db7f01f) was indexed | SYNTHESIZER_BRIEF, UI_CONTRACT including the exporter checks, part1.json (copy its block layout), the work folder, `out/part2/_work/data_wave_db7f01f.md`; a summary of what the skeptics concluded headed "verify against their files, do not trust this summary"; mid-run messages: the data-wave correction (files not yet on disk stay [assumption]), two rubric checks (one committed number plus people, owner and decision month in the move sentence; an explicit tie to the sealed Sharpest Needle in drivers[] and case_for), the number-anchors shortcut (`verified/filings/part2_number_anchors.csv`), and company fills | `out/part2/<T>/part2.json`, `part2.md`, `trace.jsonl`, `rejected.jsonl` |
| 5 Post-synthesis edits by the orchestrator | none | AMGN: a real executive named in the move replaced by the role; driver `why` text carrying filing digits reworded figure-free. PFE (f10006e): the 18 CMS machine-data cites given the dataset URL so citation chips resolve | the same files |
| 6 Targeted refresh | the AMGN synthesizer resumed (05:39 to 05:47) after the scraper's final fills (d92e501) | "Targeted refresh, not a rewrite": turn assumptions into cited figures only where a page carries the same number, rewrite the evidence section on the FDA precedent docs, update unresolved[]; the watcher's constraint: move sentence, rulings, rejected alternatives and kill signals unchanged; any published number that fails against its new source is written to `_work/<T>/refresh_discrepancies.md` and reported before editing; then the watcher's rulings applied (cited Sertkaya per-patient cost replaces the $150,000 assumption; month 12 stays an assumption; the move reworded to fund the FDA-required PMR 4155-1 trial) | 7bc2a9a, 630a439 |

Gate between waves (README): each wave starts only when the previous wave's files exist and parse for all
three companies (in practice skeptics were launched per company as soon as that company's strategist
finished). The orchestrator committed each wave (0217247 work files; ff953cd MRK, 8e75735 AMGN, b48297b
PFE; f10006e; 7bc2a9a; 630a439) and sent the UI session the SHA after each landing.

Wall clock: 05:05 to 05:37 UTC for briefs through the third part2.json; refresh to 05:47.

What the run produced: 13 candidates (AMGN 4, MRK 5, PFE 4); 9 killed, 4 narrowed, 0 survived as
stated; every chosen move is a narrowed candidate labelled unrefuted, not confirmed. MRK (type
other:working_capital_release): $7.5M, 15-person diagnose-then-release of the long-dated inventory pool,
drivers findings 2 and 1 (the IRS needle recorded as a non-driver with a gated sentence saying why), 4 kill
signals, no promo. AMGN (other:regulatory_evidence): $12.5M, 12-person gated offer to fully fund and
independently adjudicate the FDA-required PMR 4155-1 TAVNEOS trial, driver finding 1, 5 kill signals, no
promo; precedents cut against it and are recorded as such. PFE (campaign): $50M two-tranche ATTR-CM
detection scale-up with control sites and a 380-start gate, drivers 1, 4, 5, 3 kill signals, promo with two
pieces and a 17-row claims map. rejected.jsonl holds 5 (MRK), 6 (AMGN) and 2 (PFE) gate failures.

Not recoverable from disk or transcript: per-agent token or dollar cost; retries (one launch per role is
recorded); the strategist's exact reading time.

## Input restrictions (the forbidden list)

From STRATEGIST_BRIEF.md and applied in full to both skeptics and the synthesizer:

READ ONLY: the case PDF, the rubric, the company's sealed `out/part1/<T>/part1.json` and `part1.md`, the
citation index through `agent/moat/cite.py`, the helpers in HELPERS.md, the verified tables under
`data/moat/verified/` and `data/moat/tables/`.

DO NOT open, grep, or list: `out/part1/_blind/`, `out/part1/selection*`, any other company's out/part1
folder, any other out/ directory (except the company's own `out/part2/_work/<T>/`), `out/<T>/decide*`, any
prior DECIDE output, `docs/decide.md`, `agent/needle/quant/decide.py`, `moves.py`, `kill.py`, any file named
league_v*, findings_v*, findings.jsonl, docs/nuggets, docs/red_team*, docs/needle*, docs/quant_model.md,
docs/parker_handoff.md, HANDOFF*, docs/agent-chat.md, scripts/agent-chat, docs/kickoff*, docs/game_plan.md,
docs/materialit*, docs/research (except the helper docs HELPERS.md points to), ~/reports, ~/research_notes,
GitHub issues, or any other worktree. Skip "notes", "memo", "note", "report" and "verified_table_prior"
doc_types.

## Output file layout

```
out/part2/
  _work/
    data_wave_<sha>.md          what the scraper's data wave indexed (read before citing)
    <T>/
      candidates.jsonl          header line, then one candidate per line (T-m01 ...)
      strategist_summary.md
      data_requests.md          every data gap: what was needed, queries run, what would fill it
      data_replies.md           scraper replies (when any)
      skeptic_cfo_r1.json, skeptic_decider_r1.json
      skeptic_cfo_r2.json, skeptic_decider_r2.json
      refresh_discrepancies.md  numbers that failed against a new source during a refresh (if any)
  <T>/
    part2.json                  UI_CONTRACT shape
    part2.md                    readable twin: move, case with the math, two rejected, kill table, evidence, promo pieces and claims map, unresolved
    trace.jsonl                 header {step:0, category:"header", ticker, generated_at, lenses:["CFO/math","Decider/compliance"]} then one step per candidate
    rejected.jsonl              every block that failed the gate, with the reason and unsupported list
```

## Hard rules (every stage)

1. Every number is cited to a page or fact row, derived from cited operands with the operands shown, or tagged [assumption] with a one-clause reason. No numbers from memory. A deal comp not on an indexed page is a data gap (data_requests.md), not a number.
2. Quotes only from grade A or B transcripts; Bloomberg-licensed text by label only; I/B/E/S and other machine-data rows (raw NADAC, WAC, CMS Part D) never quoted or deep-linked: cite by locator with `quote: null`, `verify_status: machine_data`, `withheld: true`, and carry the dataset URL so the UI chip resolves to the source.
3. Gate exactly as Part 1: every gated text block carries text, text_marked, marker_map, cites, numeric_check; run gate_record on move, budget, cost, return, each math step, net, each why_passed, each kill signal, each evidence block, each promo piece. Failed blocks go to rejected.jsonl and their slot is rewritten without the figure or dropped. Every [n] in a *_marked field resolves through that block's marker_map to a cite in its cites. Every cites[] entry is the full evidence object (cite_id, doc_id, page, quote, label, url, verify_status, withheld, grade), never an id.
4. Figure-free prose where no gate governs it: `drivers[].why` and `rejected[].move` carry no digits at all (even "Part 1" or "10-Q" is withheld by the UI figure gate); trace kill reasons are written in words.
5. The pick is ONE move ruled survived or narrowed, never a move the CFO skeptic refuted on the math and did not concede in round 2. Exactly two rejected alternatives with skeptic_lens in {"CFO/math", "Decider/compliance"}. At least two kill signals with threshold and month_window inside months 6 to 12. Disagreement that survives round 2 goes to unresolved[] as two positions, never averaged.
6. The move sentence carries one committed number plus the people, the owning role and the decision month; the budget block must pass the gate or amount_usd and people are nulled by the exporter. The case_for ties explicitly to the sealed Sharpest Needle (drivers[] and case_for); when the needle is not the driver, one gated sentence says why.
7. Never name a real executive unless the name is on a cited page; name the role.
8. Promo: if a doctor or patient would see material, all six rules (approved uses only; risks as prominent as benefits; comparisons only with true head-to-head evidence, so none for `none_found` pairs in head_to_head_part2.csv; no invented testimonials or real likenesses; every piece labelled exactly "Student concept, not actual promotional material."; a claims map row per claim citing the label section or study page). When a label has no Section 5 or boxed warning (tafamidis, acoramidis), risks come from Section 6 Adverse Reactions. has_material false means pieces and claims_map empty and rules_check values null.
9. Write every output file from Python, never shell heredoc or echo; after writing run `grep -nE '[ ("]\.[0-9][0-9]*[BMbnmk%]' out/part2/<T>/*` and `grep -c $'\xe2\x80\x94'` (both clean). No em dashes. No league score, S, "S =", score L, robustness words or priced-in score anywhere. No "Citation(" or "Claim(" reprs.
10. In a refresh: move sentence, rulings, rejected alternatives and kill signals stay unchanged; a cited benchmark replaces an unsourced assumption even when it moves a number; timing assumptions stay when no page dates them; a published number that fails against its new source is logged to refresh_discrepancies.md and reported before editing.

## Verification steps

1. After each wave, for every company: files exist and parse; candidate ids in the skeptic files match candidates.jsonl.
2. part2.json structural pass against UI_CONTRACT's "Exporter checks the UI enforces": every gated block passed or no_numbers (passed needs checked > 0); drivers[].finding_n are integers that exist as findings[].n in out/part1/<T>/part1.json; rejected has exactly 2 entries; kill_signals non-empty with signal, threshold and month_window strings; promo consistency; skeptic_summary integers; unresolved entries have a topic; trace header lenses exactly ["CFO/math", "Decider/compliance"].
3. No digits in drivers[].why or rejected[].move; no ungated digits in killed trace steps.
4. Decimal grep and em-dash grep over `out/part2/<T>/*` and `out/part2/_work/<T>/*`.
5. verify_quote re-run on every cite; withheld is false only when verify_status is exact, substring, fuzzy or number_match.
6. UI exporter on the ui branch (PR #22), run after the Part 1 exporter because drivers and gated figures check against data/part1/<T>.json: `PYTHONPATH=. /opt/homebrew/bin/python3 agent/ui_part2_export.py --check`, 0 errors and 0 figures withheld. Hand the UI session the new quant-model SHA whenever a ticker's outputs change; `docs/part2/UI_CONTRACT.md` does not change.
7. Tests: `PYTHONPATH=. <python with pytest> -m pytest tests -q` in the quant-model worktree with both env vars set.

## Known gate limits and data limits

- Everything listed for Part 1 (ROW-label tokenizer skip; attribution and scope are not checked; no_numbers passes without evidence; years, dates, period labels, form names and page numbers are not counted; a number verifies only inside the quoted span or as the cite's value; facts rows have no viewer link).
- [assumption] budgets and scenario weights are allowed when marked, but the budget block must still pass the gate for amount_usd and people to publish.
- CMS Part D claims data is annual and ends at data year 2024; any "2025 Q1" or "2026" quarterly Part D claims figure is from a non-CMS source and must be re-sourced or dropped. Formulary counts are plan-count shares, not enrollment weighted.
- Neither Vyndaqel nor Vyndamax appears in a published IRA cohort for 2026 to 2028; 2029 status is [assumption] until CMS publishes (by 2027-02-01).
- Product-level gross-to-net and product-level consensus are not disclosed or indexed; bounding statements only.
- Deal comps exist only where a primary document is indexed (`verified/deals/deal_comps.csv`, comp sets in `part2_comp_sets.csv`); absent terms (Merck and Alteogen, Halozyme beyond 2017, Biogen and HI-Bio, argenx and Immunovant, any oral PCSK9 licence) are gaps.
- `coverage_policy_docs_part2.csv` rows are unverified snippets and can never carry a claim.
- Trial-cost benchmarks have no vasculitis category; the nearest (Sertkaya 2024 immunomodulation, 2018 dollars) is cited as the nearest benchmark with the basis stated and no inflation adjustment (no cited index in the store).
- FDA withdrawal precedents in the index (Avastin, Makena, Pepaxto, Ukoniq, Truseltiq, Blenrep, Leqembi, Exondys 51) show no sponsor trial offer accepted in lieu of withdrawal; state that with the pages when a move depends on it.

## Lessons recorded from the run

- The orchestrator's summary of the skeptic outcome in the synthesizer prompt is a pointer; the prompt says "verify against their files, do not trust this summary".
- Round 2 skeptics are resumed round 1 agents so they keep their notes; tell them in round 1 that they will be resumed.
- Give every skeptic the concrete operands, comps and pages to test, lifted from the candidates file; generic "check the math" produces generic verdicts.
- Hold the synthesizer wave until the scraper's data wave is indexed and tell it which announced files are not on disk yet (they stay [assumption]).
- The "two rubric checks" (one committed number with owner and decision month; an explicit tie to the sealed needle) were added mid-wave; put them in the synthesizer prompt from the start.
- Discrepancy handling in a refresh goes through the watcher: log, report, wait for apply or hold rulings.
- Keep helper scripts in a per-worker scratchpad subfolder; parallel workers writing at the scratchpad root collided.
- The only deadline is the Devpost submission; never cite or enforce another cutoff.
