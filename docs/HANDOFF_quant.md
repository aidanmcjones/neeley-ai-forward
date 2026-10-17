# Handoff: the quant model (for Parker and Aidan)

State as of 2026-10-17 evening. Freeze: Sunday 10:30. Spec: `docs/quant_model.md` (v2.0, this branch). Companion docs: `docs/ai_in_the_build.md`, `docs/honest_limits.md`, `docs/decide.md`, `docs/product_fineprint.md`, `docs/citations.md`.

## What exists on quant-model

| Piece | Code | Status |
|---|---|---|
| FIND (M, O, E, π, confidence, needle, league) | `agent/needle/quant/{find,impact,obscurity,evidence,league,weights,data,run}.py` | committed (ca12339); v3 changes landing now |
| Product fine print (five-row side-by-side, tie to numbers, growth limiter, priced-in call) | `agent/needle/quant/{product,product_cli}.py` | committed; shared IRA formula landing in v3 |
| DECIDE (moves, five numbers, selection, kill signals) | `agent/needle/quant/{moves,decide,kill,decide_cli}.py` | committed; one ramp and M · E fit landing in v3; run so far only on old LLY rows |
| Citations (verify ladder, gate, deep links, footnotes, cited-request builder) | `agent/needle/cite/*.py` | committed; transcript speaker check landing in v3 |
| Courtroom trial | `agent/needle/trial.py` | committed; needs the API key; reads old-shape `findings.jsonl` |
| Tests | `tests/needle/test_quant_find.py`, `test_decide.py`, `test_product.py`, `test_cite.py`, `test_trust.py` | pass at ca12339 |

v3 changes being made on quant-model now: MFN direction-only at π_min; AZN duplicate receivables row removed; needle floor on the discussion term with a 3-month half-life (6 as sensitivity); anchor rows only for fired backtest flags, others "not quantified"; consensus default 0.5 when untestable; one IRA formula for FIND, product and DECIDE; DECIDE one ramp and strategic fit on M · E; transcript speaker check; `league_v3` with a robustness table.

## How to run the three CLIs

Environment (the moat and index are gitignored and live in the gap-data worktree):

```
export NEEDLE_MOAT=/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data/data/moat
export CITATIONS_DB=$NEEDLE_MOAT/index/citations.sqlite
```

1. **FIND and the league** (no API key, about 20 s):
   ```
   python -m agent.needle.quant.run --all              # all ten: out/<T>/findings_v*.jsonl, out/league_v*.json and .md
   python -m agent.needle.quant.run --ticker AMGN      # one company
   python -m agent.needle.quant.run --all --detect     # re-run the detectors first
   ```
2. **Product fine print** (no API key):
   ```
   python -m agent.needle.quant.product_cli --ticker <T> --product <slug>     # out/<T>/product_<slug>.json and .md
   ```
3. **DECIDE** (no API key):
   ```
   python -m agent.needle.quant.decide_cli --ticker <T> --findings out/<T>/findings_v3.jsonl --moves moves_<T>.json
   ```
   `moves_<T>.json` lists candidate moves with their parameters, `cash_and_equivalents` (a cited 10-Q number) and the finding ids each move addresses; template: `docs/examples/moves_LLY.json`. Output: `out/<T>/decide.json` and `.md`.

## How to read league_v3 and make the pick

1. Open `out/league_v3.md`. For each company: L, the raw top-5 sum, N_eff, blocks, largest-finding share, the top five rows (S, M, O, E, π, confidence) and the Sharpest Needle with its status (strict, provisional, floor relaxed).
2. Read the **robustness table** first. Its rows: as computed; no N_eff term (raw sum); IRA rows at π 0.5; Biktarvy on the comparison formula; AMGN's receivables row at π_min; H = 6.
3. **Pick only a company that is in the top two in every row.** In v2, AMGN and GILD were top two everywhere; which was first depended on the N_eff term (GILD leads on the raw sum) and on AMGN's receivables row, which sits exactly on the 8-point trigger. If that still holds in v3, the honest framing is "AMGN and GILD both survive every variant; we pick X because ...", with the reason stated in numbers (needle status, diversity, largest-share).
4. Before committing to AMGN: check its Q2 2026 10-Q for an acquisition, timing or Part D redesign billing cause of the receivables gap. Before committing to GILD: its score is mostly one Biktarvy IRA row on an assumed discount range, and the row is adjacent to GILD's starter thread (HIV durability); GILD had no strict needle in v2.
5. The "why it beat the other nine" sentence names rank, the raw sum beside L, N_eff and the needle status, each with its number, and cites the robustness table.

## What feeds the deck

| Deck element | Source |
|---|---|
| Findings table (five rows: sentence, source, impact with math, peer, confidence) | top five rows of the picked company in `out/<T>/findings_v3.jsonl`: `sentence_md` (with footnote markers), `impact.formula` and `d_rev` / `d_eps`, `peer` ("no peer analogue" when empty), `confidence`. Show S as a tier and π as a tier, not decimals |
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
2. Courtroom trial on the same rows: `python -m agent.needle.trial --ticker <T> --top 5` after pointing it at the v3 findings. "fails" lowers confidence to LOW; bad quotes land in `out/<T>/ai_caught.jsonl`.
3. Memo and Q&A through `agent/llm.py` (cached).
Nothing from the pass changes a number. Re-runs read the cache.

## Open items, in priority order for the Sunday 10:30 freeze

1. **Land v3 and re-run.** `python -m agent.needle.quant.run --all` to produce `league_v3` and its robustness table; send the numbers back so the `[v3: pending]` placeholders in `docs/quant_model.md` (Sections 4.8, 5.5, 9, 10.3-10.6) and `docs/honest_limits.md` are filled. Check two v3 interactions: (a) with c = 0.5 on untestable type C rows, those rows clear the needle floor (D ≥ 0.5) only when h = a = s = 0, so count strict needles; (b) confirm whether MFN rows keep the base-rate size as an internal M (the spec says yes, never printed) or are set to not quantified.
2. **Make the pick** from the robustness table (above).
3. **Point the app at league_v3.** `app/needle_app.py:155` still reads `out/league.json` (old scorer, LLY first). Fix before any screen recording.
4. **Product table** for the picked product with the shared IRA formula; commit the output.
5. **DECIDE on the picked company's v3 findings** with a moves file; add one EV line at 10.5% and the decider-evidence table.
6. **LLM pass** (one pass, cached) once the key is armed; wire the cited call through the cache and point the trial at v3 findings first.
7. **Merge** quant-spec (docs only) into quant-model. Expect no code conflicts.
8. **Not doing before the freeze** (stated as limits instead): backtest re-run (panel not on disk), flag-strength scaling, leave-one-year-out, litigation-topic and Lazy Prices table choice (moot once drift rows are not quantified), 20-F headline from interim report page 1, a public page viewer, a live new-ticker run (use the recorded VRTX run).
