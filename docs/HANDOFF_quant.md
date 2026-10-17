# Handoff: the quant model (for Parker and Aidan)

State as of 2026-10-17 evening. Freeze: Sunday 10:30. Spec: `docs/quant_model.md` (v2.1, this branch, matching quant-model ee7846c). Companion docs: `docs/ai_in_the_build.md`, `docs/honest_limits.md`, `docs/decide.md`, `docs/product_fineprint.md`, `docs/citations.md`.

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

## How to read league_v3 and make the pick

1. Open `out/league_v3.md`. For each company: L, the raw top-5 sum, N_eff, blocks, largest-finding share, the top five rows (S, M, O, E, π, confidence) and the Sharpest Needle with its status (strict, provisional, floor relaxed).
2. Read the **robustness table** first (eight rows): base; no N_eff term; MFN at the v2 universal rule; AMGN's receivables row at π_min; that row as unfired; H = 6; IRA on the draft formula; c = 0.5 on anchor rows.
3. **What league_v3 says.** AMGN 0.0877 leads GILD 0.0511, AZN 0.0290, MRK 0.0199, BMY 0.0086. AMGN is first in 6 of 8 variants; GILD is first in the other 2, both about one row: AMGN's receivables growth beat revenue growth by +8.01 pts against an 8.00-pt trigger, and that row is 87% of AMGN's L. AZN is third in 6 of 8. The N_eff term and the MFN rule no longer decide #1. **First place is AMGN or GILD, and it turns on one human check.**
4. Before committing to AMGN: read its Q2 2026 10-Q for an acquisition, timing or Part D redesign billing cause of the receivables build; if there is one, GILD leads. AMGN has a strict needle (the same row). Before committing to GILD: its L is one Biktarvy IRA row on an assumed discount (no HIV MFP is published; 65.5% median of a cited 38-85% range), adjacent to GILD's starter thread (HIV durability), and its needle is "floor relaxed" (D 0.40).
5. The top-5 tables are thin (1 to 4 scored rows for most companies). The case's five findings can draw on "not quantified" rows in `findings_v2.jsonl` as qualitative findings, with their reason shown.
6. The "why it beat the other nine" sentence names rank, the raw sum beside L, N_eff and the needle status, each with its number, and cites the robustness table.

## What feeds the deck

| Deck element | Source |
|---|---|
| Findings table (five rows: sentence, source, impact with math, peer, confidence) | top five rows of the picked company in `out/<T>/findings_v2.jsonl` (v3 run): `sentence_md` (with footnote markers), `impact.formula` and `d_rev` / `d_eps`, `peer` ("no peer analogue" when empty), `confidence`. Show S as a tier and π as a tier, not decimals |
| Sharpest Needle | `needle` and `needle_status` in `league_v3.json`; print the status word if it is not strict |
| Why this company | the league row and the robustness table in `league_v3.md` |
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

## Open items, in priority order for the Sunday 10:30 freeze

1. **Make the pick** (above): the AMGN 10-Q receivables check decides AMGN vs GILD.
2. **Product table** for the picked product; commit the output.
3. **DECIDE on the picked company's v3 rows** with a moves file; add one EV line at 10.5% and the decider-evidence table.
4. **LLM pass** (one pass, cached) once the key is armed: first add a cited-call variant to `agent/llm.py` that sends `build_cited_request`'s body through the cache, and point `trial.py` at the v3 rows.
5. **Nuggets.** If Parker pushes his nugget files, re-run with `--nuggets` and check the robustness table again.
6. **Merge** quant-spec (docs only) into quant-model. Expect no code conflicts.
7. **Not doing before the freeze** (stated as limits instead): backtest re-run (panel not on disk), flag-strength scaling, leave-one-year-out, 20-F headline from interim report page 1, a public page viewer, a dedicated peer set for off-shortlist tickers, a live new-ticker run (use the recorded VRTX run).
