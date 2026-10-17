# Build plan: NEEDLE, head to toe

## Context
The corpus is shared (branch `corpus`, PR #5). Parker approved the NEEDLE concept: a forensic engine whose findings are backtested on past filings, corroborated by data management doesn't control, and turned into live predictions that can be checked. Every claim is page-verified and written to a tamper-evident audit trail, and the engine generalizes to any ticker. It's aimed at the likely judges (McKesson, Gartner, PwC Responsible AI, a bank CISO, Dallas AI, the AI Forward director) and the 7-category rubric, which scores only what's demonstrated. Build rules from Parker: fastest and most efficient path, fewest tokens, highest accuracy, a self-check after every substep.

## Rubric and repeatability alignment (added after review)
- **AI essential ("AI reads, code checks"):** the LLM does semantic reading: classifying changed risk/MD&A paragraphs (new, softened, hedged, removed), scoring Q&A deflection, extracting and comparing label clauses, writing findings, running the trial. Code verifies every LLM output (quote on page, numbers reconcile). Batched, cached, changed paragraphs only.
- **Core, bulletproof by 5:30 pm:** phases 0 to 3, labels, P&L impact math (case requires it), market "priced in" test (case requires it), score, run, UI. Everything else is stretch.
- **Case coverage:** product comparison includes pricing and GTN (Part D, NADAC, IRA MFP, 10-K rebate footnote). Confidence = verify result x outside corroboration. Every prompt and rejection is auto-logged, feeding the How We Did It report.
- **Design:** named users are buy-side pharma analyst and corporate strategy/IR, plus a distributor view. Accessibility: color-blind-safe palette, keyboard navigation, text labels on charts.
- **Impact:** measured manual-vs-NEEDLE time on one 10-K, plus the path to real use.
- **Repeatability:** new `agent/needle/onboard.py`: ticker -> CIK/filings -> products from XBRL ProductOrServiceAxis -> Orange/Purple Book by applicant -> DailyMed label -> rivals by RxClass EPC/ATC -> outside data. Config is generated, not hand-coded; transcripts optional (calls detector flags "not loaded"). Tests: full run on a non-shortlist ticker (VRTX or BIIB) with zero manual edits, and on all 10 without hand fixes.
- **Coordination:** Parker's other Claude session commits to `corpus` (label fixes 4d913fa, 7964caa). Pull before branching; split file ownership between the two sessions.

## Efficiency rules (apply to every step)
- **Deterministic code first.** The LLM is used only for finding prose and the trial, always through `agent/llm.py:call` (file-cached, so each prompt runs once).
- **Models by job:** haiku for fetch errands, sonnet for scoped coding workers, Opus (this session) for design, review and integration.
- **Skills:**
  - `/orchestrator` for parallel waves of 3 or more independent modules
  - `/parallel-dispatch` for per-source fetches
  - `/adversarial-review` only at 3 gates: verifier, backtest method, final findings
- **Hook:** a PostToolUse hook in project `.claude/settings.json` runs `pytest -q tests/needle -x` (about 2 seconds) after any edit under `agent/needle/`, so every substep self-checks automatically. Added via the `update-config` skill.
- **Every module ships with a small test** that runs on 2 tickers (AZN, JNJ). A module isn't done until its test passes and its output has been spot-checked against the source.

## Ownership and coordination
- **New branch `needle`** off `corpus`. All code is new, in `agent/needle/` and `app/needle_app.py`. Aidan's `app/main.py`, `agent/llm.py` and the other existing files are not edited.
- **One agent-chat note to Aidan:** "NEEDLE build on branch `needle`, files claimed: `agent/needle/*`, `app/needle_app.py`, `tests/needle/*`; plan in `docs/needle.md`." Plus the work-log thread his CLAUDE.md asks for.
- **Blocker for LLM steps only:** an `ANTHROPIC_API_KEY` in `.env` (Parker or Aidan). Every deterministic step proceeds without it.

## Architecture
```
agent/needle/
  schema.py        Signal, Evidence, Finding, Prediction dataclasses (spec §6) + JSONL io
  pages.py         page store: every corpus doc -> (doc_id, page_idx, printed, text); normalized search
  xbrl.py          quarterly panel per ticker (rev, inventory, AR, GM, R&D, SG&A, impairments, rebate accruals) incl. MCK/COR/CAH
  detect/drift.py      Risk Factors + MD&A paragraph diff FY24 vs FY25 (added/removed/hedged), printed-page evidence
  detect/forensics.py  working-capital vs revenue, DSO/DIO, GM, impairments; peer z across the 10
  detect/calls.py      Q&A deflection phrases, new phrases, KPIs dropped between consecutive releases/decks
  detect/labels.py     rival label side-by-side (indications, boxed warning, contraindications, dosing, REMS) + OB/PB dates + IRA
  detect/supply.py     manufacturer inventory/AR vs distributor 10-K commentary vs NADAC vs Part D/FAERS trends
  outside.py       fetchers: NADAC (data.medicaid.gov), FAERS (openFDA counts), ClinicalTrials.gov changes, Part D quarterly, distributor 10-Ks
  verify.py        quote-on-cited-page check (normalized exact, then fuzzy >= 0.97), number reconcile vs xbrl/page text
  audit.py         hash-chained ledger (sha256 prev+record) for every signal, verdict, prediction; verify_chain()
  trial.py         prosecutor / defense / judge via llm.call (cached), only on findings that pass verify.py
  backtest.py      as-of FY2020-23 signals (code only, names masked) vs objective XBRL events -> hit rate per signal type
  predict.py       live predictions from signals x hit rates x outside corroboration; J&J Q3 blind test; sealed forecasts
  score.py         materiality spec S formula, obscurity, Sharpest Needle, league table
  run.py           python -m agent.needle.run --ticker X | --all  -> out/<T>/{signals,findings,predictions}.jsonl
app/needle_app.py  Streamlit: league table | findings | source page w/ highlight | AI-caught panel | proof (backtest, J&J blind, sealed hashes)
tests/needle/      one fast test per module
```

## Phases (each substep: build, then test, then spot-check against source, then commit)
| # | Phase | How | Self-check |
|---|---|---|---|
| 0 | Branch, `docs/needle.md`, agent-chat claim, pytest hook, `schema.py` | Opus, direct | hook fires; schema round-trips |
| 1 | `pages.py` + `xbrl.py` (+ fetch MCK/COR/CAH companyfacts and 10-Ks via existing `agent/corpus.py`) | Opus, direct (foundation) | 20 random printed-page lookups match the files; panel matches 3 hand-checked 10-Q numbers |
| 2 | Detectors drift, forensics, calls, labels | `/orchestrator`, 4 sonnet workers, 1 file each, shared schema | each test passes on AZN+JNJ; 5 evidence quotes spot-checked per detector |
| 3 | `verify.py` + `audit.py` | Opus, direct | seeded bad claims (wrong page, altered number, prior year) 100% rejected; good claims >= 95% pass; then **`/adversarial-review` gate 1** |
| 4 | `outside.py` + `detect/supply.py` | `/parallel-dispatch` haiku fetchers per source, then one sonnet worker for supply.py | row counts and date ranges logged; 3 values cross-checked against the source site |
| 5 | `backtest.py`: pull FY2020-23 10-Ks with `agent/corpus.py` (window param), code-only signals, events defined *before* looking (revenue drop >= 5% within 8 quarters, impairment >= 2% of assets, GM drop >= 3 points) | Opus design + sonnet worker | events table hand-checked for 5 companies; **`/adversarial-review` gate 2** on leakage and method |
| 6 | `predict.py`: J&J blind (hide Q3'26 docs, predict, compare to Q3 8-K); sealed forecasts for MRK/BMY/LLY/AZN/PFE/NVO, sha256 committed | Opus | blind run provably excludes Q3 docs (assert on manifest dates) |
| 7 | `score.py` + `trial.py` + `run.py --all` (LLM steps need the API key) | Opus + cached LLM | league table for all 10; every surfaced finding has verify ✓ + ledger entry |
| 8 | `app/needle_app.py` per the sketch | sonnet worker, Opus review | click-through from 5 findings opens the right page and highlight |
| 9 | Stretch, in order: live any-ticker run; market "priced in" event study (free daily prices); management credibility record; exposure graph; P&L tornado | waves via `/orchestrator` | each behind a working core; **`/adversarial-review` gate 3** on final findings |

**Checkpoints:**
- 5:30 pm Sat: phases 0 to 3 plus a minimal 7 and 8 (golden path).
- Overnight: `run.py --all` cached.
- Sunday 2:00 pm: Devpost submission (the only deadline).

## Verification (end to end)
- `pytest -q tests/needle` is green.
- `python -m agent.needle.run --all` completes. `out/` holds signals, findings and predictions for all 10. `audit.verify_chain()` returns True.
- `streamlit run app/needle_app.py`: league table renders; clicking any finding shows its exact source page with the quote highlighted; the AI-caught panel lists rejected claims with reasons; the proof tab shows backtest hit rates, the J&J blind result, and the sealed hashes matching the committed file.
- Parker signs off every finding that reaches a slide.
