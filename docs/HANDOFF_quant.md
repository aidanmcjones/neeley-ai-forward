# Handoff: the quant model (for Parker and Aidan)

State as of 2026-10-17 evening. Deadline: the Sunday 2:00 pm Devpost submission (the only deadline). Spec: `docs/quant_model.md` (v2.1, this branch, matching quant-model ee7846c). Companion docs: `docs/ai_in_the_build.md`, `docs/honest_limits.md`, `docs/decide.md`, `docs/product_fineprint.md`, `docs/citations.md`.

## State as of 2026-10-18 (submission day)

Part 1 (the blind "find the story" pass) and Part 2 (the "make the call" pass) are the pitch-facing outputs; the FIND, DECIDE and product CLIs below remain as internal triage and are not pitched. Part 1 is final at 7eb0dca (briefs 2979fb0): ten blind readers, a materiality and an obviousness skeptic per company over two rounds, a synthesizer per company, a sealed blind ranking (out/part1/selection.md, sha256 903fc656..., picked AMGN, MRK, PFE), then gated part1.json, part1.md, trace.jsonl and rejected.jsonl for the three under docs/part1/UI_CONTRACT.md; the independent verifier's seven attribution and scoping fails (out/part1/verify_report.md) were applied at 7eb0dca. Part 2 is final per company: MRK ff953cd (diagnose-then-release inventory move), PFE f10006e (ATTR-CM detection scale-up with promo claims map, CMS machine-data cites carrying the dataset URL), AMGN 630a439 (gated offer to fund and adjudicate the FDA-required PMR 4155-1 TAVNEOS trial, refreshed on data-moat d92e501); 13 candidates, 9 killed, 4 narrowed, 0 survived; out/part2/<T>/part2.json under docs/part2/UI_CONTRACT.md with the UI exporter's checks. The UI (PR #22, session aidanjones-71) exports both with 0 errors and 0 figures withheld. The two pipelines are packaged as Claude Code skills, fine-print-part1 and fine-print-part2, under .claude/skills/ on this branch (31195c3) and in ~/.claude/skills: SKILL.md with the wave structure, agent counts and models, forbidden lists, seal procedure, output layout, hard rules, verification steps and known gate limits; briefs/ byte copies of docs/part1 and docs/part2; reference/LAUNCH_PROMPTS.md with the verbatim launch and resume prompts. Tests on 2026-10-18 (PYTHONPATH=. with NEEDLE_MOAT and CITATIONS_DB set, run with the one local interpreter that has pytest, the e8d819f0 scratchpad venv; /opt/homebrew/bin/python3 has no pytest): 256 passed, 1 failed, 2 skipped. The failure is tests/moat/test_cite.py::test_grade_d_transcript_excluded_with_grade_min_b, a live-index search test copied verbatim from data-moat that picks the first grade-D transcript and expects a five-word FTS query to return it within k=50; the same test in the gap-data worktree's current copy (updated on data-moat after the 704741d pin) passes against the same index, so the quant-model copy is stale rather than the index or the gate being wrong; re-copying tests/moat/test_cite.py and agent/moat/cite.py from data-moat clears it. It touches no gate, arithmetic or output code. Export NEEDLE_MOAT and CITATIONS_DB in two separate export statements; a single export line leaves CITATIONS_DB as /index/citations.sqlite and 36 tests exit with "missing: run python -m agent.moat.index".

## What exists on quant-model

| Piece | Code | Status |
|---|---|---|
| FIND (M, O, E, π, confidence, needle, league) | `agent/needle/quant/{find,impact,obscurity,evidence,league,weights,data,run}.py` | committed; league_v3 at ee7846c, with nine red-team guards (`guards.py`) and a `--nuggets` ingest |
| Product fine print (five-row side-by-side, tie to numbers, growth limiter, priced-in call) | `agent/needle/quant/{product,product_cli}.py` | committed; uses FIND's IRA formula (`impact.ira_class_rule`) with CM 1.00 |
| DECIDE (moves, five numbers, selection, kill signals) | `agent/needle/quant/{moves,decide,kill,decide_cli}.py` | committed; 60-month label ramp and M · E fit committed in 9a1932c; run so far only on old LLY rows |
| Citations (verify ladder, per-number gate, deep links, footnotes, cited-request builder) | `agent/needle/cite/*.py` | committed; transcript speaker and fool.com rules in the ladder (8a94bc0); the numeric gate is wired into run.py (findings_v3 / rejected_v3), decide_cli.py (decide_rejected.md on failure) and product_cli.py (docs/gate_wiring.md) |
| Courtroom trial | `agent/needle/trial.py` | committed; needs the API key; reads old-shape `findings.jsonl` |
| Tests | `tests/needle/test_quant_find.py`, `test_decide.py`, `test_product.py`, `test_cite.py`, `test_trust.py` | plus `test_quant_guards.py`; updated with league_v3 |

In league_v3 (all committed): MFN direction-only at π_min (NVO and BMY company terms already effective, so 0); one fact one top-5 row (AZN duplicate gone); needle floor on the discussion term, H = 3 (6 as sensitivity), age from the first public date; anchor only for fired backtest flags, other text, call and unfired rows "not quantified"; c = 0.5 when untestable; one IRA formula G x max(0, k x d - m_avoided) for FIND, product and DECIDE; DECIDE 60-month label ramp and fit on M x E; transcript speaker check; nine red-team guards; the app reads `league_v3.json` first; an eight-variant robustness table. The v3 run still writes rows to `out/<T>/findings_v2.jsonl`.

## How to run the three CLIs

Environment (the moat and index are gitignored and live in the gap-data worktree):

```
export NEEDLE_MOAT=/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data/data/moat
export CITATIONS_DB=$NEEDLE_MOAT/index/citations.sqlite
```

1. **FIND and the league** (no API key, about 20 s):
   ```
   python -m agent.needle.quant.run --all              # all ten: out/<T>/findings_v2.jsonl, out/league_v3.json, .md, out/league_v3_robustness.json
   python -m agent.needle.quant.run --ticker AMGN      # one company
   python -m agent.needle.quant.run --all --detect     # re-run the detectors first
   python -m agent.needle.quant.run --all --nuggets docs/nuggets   # add Parker's nugget-miner rows (same guards and gate)
   ```
2. **Product fine print** (no API key):
   ```
   python -m agent.needle.quant.product_cli --ticker <T> --product <slug>     # out/<T>/product_<slug>.json and .md
   ```
3. **DECIDE** (no API key):
   ```
   python -m agent.needle.quant.decide_cli --ticker <T> --findings out/<T>/findings_v2.jsonl --moves moves_<T>.json
   ```
   `moves_<T>.json` lists candidate moves with their parameters, `cash_and_equivalents` (a cited 10-Q number) and the finding ids each move addresses; template: `docs/examples/moves_LLY.json`. Output: `out/<T>/decide.json` and `.md`.

## Making the pick

**Company choice is made by Parker's red-team read and a human read of the findings; league_v3 is internal triage only (it orders candidates for review and is not pitched).** The pitch ranks each company's findings by cited dollar impact (`out/<T>/findings_table.md` and `.json`, `rank_basis: "impact"`) and names the Sharpest Needle by one plain rule: the biggest-impact finding that analysts asked about least (docs/quant_model.md Sections 4.8 and 12).

### league_v3 as internal triage (not pitched)


1. Open `out/league_v3.md`. For each company: L, the raw top-5 sum, N_eff, blocks, largest-finding share, the top five rows (S, M, O, E, π, confidence) and the Sharpest Needle with its status (strict, provisional, floor relaxed).
2. Read the **robustness table** first (eight rows): base; no N_eff term; MFN at the v2 universal rule; AMGN's receivables row at π_min; that row as unfired; H = 6; IRA on the draft formula; c = 0.5 on anchor rows.
3. **What league_v3 says.** AMGN 0.0877 leads GILD 0.0511, AZN 0.0290, MRK 0.0199, BMY 0.0086. AMGN is first in 6 of 8 variants; GILD is first in the other 2, both about one row: AMGN's receivables growth beat revenue growth by +8.01 pts against an 8.00-pt trigger, and that row is 87% of AMGN's L. AZN is third in 6 of 8. The N_eff term and the MFN rule no longer decide #1. **First place is AMGN or GILD, and it turns on one human check.**
4. Before committing to AMGN: read its Q2 2026 10-Q for an acquisition, timing or Part D redesign billing cause of the receivables build; if there is one, GILD leads. AMGN has a strict needle (the same row). Before committing to GILD: its L is one Biktarvy IRA row on an assumed discount (no HIV MFP is published; 65.5% median of a cited 38-85% range), adjacent to GILD's starter thread (HIV durability), and its needle is "floor relaxed" (D 0.40).
5. The top-5 tables are thin (1 to 4 scored rows for most companies). The case's five findings can draw on "not quantified" rows in `findings_v2.jsonl` as qualitative findings, with their reason shown.
6. Do not pitch L, S or the league rank; the "why this company" argument comes from the red-team read and the findings themselves.

## What feeds the deck

| Deck element | Source |
|---|---|
| Findings table (ranked by dollar impact) | `out/<T>/findings_table.md` and `.json` (`rank_basis: "impact"`): marked sentence, marked impact math, base-case abs dEPS and dOI, analyst share asked, one shared footnote list. No S and no league number |
| Sharpest Needle | the row marked Needle in `findings_table.*` (`needle_id`): Parker's red-team best needle when it passes the gate and is slide-ready, else the plain rule (biggest impact, least asked about); `needle_source` says which |
| Why this company | Parker's red-team read and a human read of the findings (league_v3 is internal triage only) |
| Product table and growth limiter | `out/<T>/product_<slug>.md`: five rows, the tie row, the limiter sentence and the priced-in call with its reasons |
| DECIDE five numbers | `out/<T>/decide.md`: EV (in-window and TV), cash at risk, payback month, scenario spread, MCDA, for the pick and the two rejected moves with each one's binding reason; plus a hand-built decider-evidence table for the picked move |
| Kill signals | `kill.KILL_SIGNALS` as listed in `decide.md`: threshold, source and lag, check month, effect on EV |
| Footnotes | the `[n]` footnotes rendered by `cite.render_markdown`, `public=True` for anything shown outside the local app |
| Honest limits slide | `docs/honest_limits.md` |
| AI slide | `docs/ai_in_the_build.md` (the "AI was wrong" list) |

## The one-pass LLM plan

When the key is armed, run everything that needs a model once, cached, after the v3 numbers are final:
1. Finding prose for the picked company's top five and needle: `cite.llm.build_cited_request` (citations on every block), then `parse_cited_response`, then the verify ladder and the gate. Needs a call variant in `agent/llm.py` that sends that body through the same disk cache.
2. Courtroom trial on the same rows: `python -m agent.needle.trial --ticker <T> --top 5` after pointing it at the v3 rows (it still reads the old `findings.jsonl` at ee7846c). "fails" lowers confidence to LOW; bad quotes land in `out/<T>/ai_caught.jsonl`.
3. Memo and Q&A through `agent/llm.py` (cached).
Nothing from the pass changes a number. Re-runs read the cache.

## Open items, in priority order before the Sunday 2:00 pm Devpost submission

1. **Make the pick** (above): by the red-team read and a human read of the findings tables; league_v3 is triage only.
2. **Product table** for the picked product; commit the output.
3. **DECIDE on the picked company's v3 rows** with a moves file; add one EV line at 10.5% and the decider-evidence table.
4. **LLM pass** (one pass, cached) once the key is armed: first add a cited-call variant to `agent/llm.py` that sends `build_cited_request`'s body through the cache, and point `trial.py` at the v3 rows.
5. **Nuggets.** If Parker pushes his nugget files, re-run with `--nuggets` and check the robustness table again.
6. **Merge** quant-spec (docs only) into quant-model. Expect no code conflicts.
7. **Not doing before the submission** (stated as limits instead): backtest re-run (panel not on disk), flag-strength scaling, leave-one-year-out, 20-F headline from interim report page 1, a public page viewer, a dedicated peer set for off-shortlist tickers, a live new-ticker run (use the recorded VRTX run).
