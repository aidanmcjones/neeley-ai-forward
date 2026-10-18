# NEEDLE (`ui/`)

**The demo is the chat page at `/#/`. The cockpit at `/#/cockpit` is the depth.**

Static single-page app (Vite + React 18 + TypeScript + Tailwind v3 + Recharts, hash router) that reads
precomputed JSON from `public/data/`. No API key, no live model, no network at runtime; fonts are bundled
(@fontsource), so `dist/` works with Wi-Fi off from any static server or sub-path (`base: "./"`).
State of this document: PR #22, branch `ui` at 7723625 (artifact version 6).

## Run

```bash
cd ui
npm install                                   # exact versions pinned in package.json
npm run dev -- --port 5173                    # http://localhost:5173/#/ (restart after vite config changes)
npm run typecheck                             # tsc --noEmit
npm run build                                 # tsc --noEmit && vite build -> ui/dist/
python3 -m http.server 8090 -d dist           # serve the static build: http://localhost:8090/#/
```

## Regenerate and publish

From the repo root, in this order:

```bash
NEEDLE_TICKER=XXX PYTHONPATH=. python -m agent.ui_export   # company files, league, meta, proof (NEEDLE_TICKER optional)
PYTHONPATH=. python -m agent.ui_memos                      # memos.json and _sample/memos.json
PYTHONPATH=. python -m agent.ui_memos --check              # every marker, cite and number checked; exit 1 on errors
cd ui && npm run build                                     # dist/ with memos_index.json and memos/<id>.json
```

Publish the root of `ui/dist/` as is (index.html plus `assets/` and `data/`). `index.html` already links
`assets/fit.css`, `assets/trim.css` and `assets/trim.js`, so the publish step patches nothing.

`NEEDLE_TICKER` (env or the repo `.env`) is the team's pick. Set, the exporter writes
`meta.default_ticker_source: "pick"`; unset (or not one of the ten), it writes `"unpicked"`.

## Chat (`/`, the demo)

One centered column (max 760 px): the NEEDLE wordmark, "Ask for a memo. Every number is cited to the page.",
a company pill, the thread and a prompt box (Enter sends, Shift+Enter new line). Answers are cached in
`public/data/memos.json`; if it is missing the page uses the 3-record `_sample/memos.json` with a banner.

- **Default company.** "unpicked" starts at "Pick a company" with the company-agnostic `memos.suggested`
  (sharpest needle across the ten, how it works, where the AI was wrong, the data moat, products, honest limits).
  Picking a company switches to `memos.suggested_by_ticker[T]`, a 7-step flow: needle, why this company,
  findings, product, priced in, CEO memo, what would prove us wrong. "pick" preselects that company. The league
  leader is never auto-selected. The cockpit routes on `meta.default_ticker` as before.
- **Two formats.** `format: "chat"` (Part 1, Find) answers as prose with cite chips, KPI rows and tables, then
  `ask_next` follow-up chips. `format: "memo"` (Part 2, Decide) is a paper card with TO / FROM / RE / DATE,
  section tables (return math, alternatives rejected, why it will work, kill signals), byline, numbers-check
  pill, Copy as markdown and Print (prints only that card, with every "Show the math" opened).
- **Per-answer loading.** `memos.json` is about 4.6 MB. `vite.memos-index.js` (a Vite plugin) derives a 46 kB
  `data/memos_index.json` (prompts, aliases, kinds, suggestions) and one `data/memos/<id>.json` per answer,
  served in dev and emitted into `dist/` at build, never committed. The chat paints its chips from the index
  and fetches only the answer asked for; without the index (a plain copy of `public/`) it falls back to the
  full file. Static build, throttled: 20 Mbps chips 0.6 s and first answer 0.9 s.
- **Matching** (`src/lib/memos.ts`): exact prompt or alias, then term overlap with the retriever's synonym
  groups (floor 0.3), favouring the selected company; no match replies "I can write these memos:" with the
  chips and a "Show all prompts" list by kind.
- **Reveal**: a 1.5 to 2.5 s typewriter, skippable by click, instant under reduced motion.

## Part 1 answer and reasoning trace

The hero chip on an empty chat is the case's Part 1 prompt, verbatim. It (or a typed match: the exact prompt,
"part 1", "find material", "non-obvious findings", "compare ... product ... rivals") answers with the cached
Part 1 deliverable instead of a memo; the company pill does not apply (the pick is sealed).

- **Data** (`src/lib/part1.ts`, shapes in `src/lib/types.ts`): `data/part1/index.json`, else
  `data/_sample/part1/index.json`; then `selection.json`, and `<T>.json` plus `<T>_trace.json` for each of the
  three picked tickers (all three load at once so the 1 / 2 / 3 switcher swaps instantly). Written by
  `agent/ui_part1_export.py`; the sample fixture by `agent/ui_part1_fixture.py`. From `_sample` (or
  `index.sample: true`) the answer shows one muted line: "Sample data: the blind reasoning pass has not run yet".
- **Layout** (case "Minimum expectations"): header with the switcher; "Why <name> beat the other nine" (reason,
  collapsible "the other nine", seal sha256 short form and sealed_at); Findings table (Finding | Source | Impact
  with "Show the math" and the numeric gate pill | Peer comparison | Confidence); Sharpest Needle; Product fine
  print (five rows, product then rivals, "needs citation" cells muted), Tie to the numbers, what limits growth,
  priced in ("untestable" reads as a plain statement). Markers render through `Md` with the existing CiteChip and
  SourceDrawer: `[n]` resolves via the nearest `marker_map` against every cite in the company file, else the
  local `cites` entry with that `n`.
- **Selection card prose** comes only from `selection.reasons_card` / `eliminated_card` (figure-free). The
  verbatim `reasons` / `eliminated` carry ungated figures and never render as prose; while the card fields are
  absent they are a fallback with every sentence carrying a figure dropped (years, dates, 10-K / 10-Q / 20-F,
  candidate ids like AMGN-c06 and counts up to 12 are allowed). `checkCardFigures` in `src/lib/part1.ts`
  console.warns, naming the ticker, if a rendered card string still carries any other figure.
  "Read the sealed selection" opens `data/<selection.sealed_doc_path>` (else `selection_md`) in a side
  drawer, under a muted note with sealed_at and the sha256 short form.
- **Missing picks**: `index.available` / `index.missing` keep all three picks in the switcher; a missing pick is
  disabled with a "writing" hint, the answer opens on the first available pick, and a muted line says so when
  the number one pick is still being written.
- **Reasoning trace** ("How the answer was found"): a summary strip (candidates, survived, killed, narrowed,
  documents read), then the eight "Where findings hide" categories in the case's order, collapsed; each opens to
  its queries, distinct documents (title, page) and candidate cards with a verdict badge, the reason, a link to
  the finding it became, and the materiality / obviousness skeptic rounds on demand. When the trace is a sample or
  every skeptic field is null, one muted line says it is illustrative.
- **Routing**: "why this company", "why <name>", "why did it beat the other nine" answer with the selection card
  alone when a part1 selection exists, else the `why_company` memo. Everything else routes to the memos as before;
  the ask-next chips under the Part 1 answer offer the other two picks and `memos.suggested_by_ticker[T]`.
- **Pitch rule**: every string from part1 files passes `scrub()` (the Answer.tsx INTERNAL regex plus
  `INTERNAL_TEXT`), so no league score, S or robustness wording renders.
- **Reveal**: header, selection card and Findings first, the rest 0.7 s later (click to show at once).

## Cockpit (`/cockpit/...`, unlinked except for "Full cockpit" under the prompt box)

- **Briefing**: KPI row; the Sharpest Needle hero; the findings grid; the stance panel.
  - Hero: `needle_id_rule` (falling back to `needle_id`). The pill reads "Needle: red-team read,
    gate-confirmed" (`needle_source: "red_team"`) or "Needle: plain rule" (`"rule"`), with the plain-rule
    sentence as tooltip; `needle_reason` is the muted line under the headline. A paragraph-length needle shows
    its first sentence as the headline and the rest as body text; the impact formula sits behind "Show the
    math"; three proof chips plus "+N more". Rows `explained_by_footnote` are never the needle.
  - Grid: `findings_table` order, "ranked by impact", the table's own marked sentences, a Peer column from
    `peer_text` / `peer_comparison`, flag pills, and a selected-row strip (footnote note, not-quantified
    reason, guard, corroborates link, fact key, impact channel).
  - Stance panel with DECIDE: AMGN, MRK and GILD are pipeline demonstrations (muted note, "Pipeline
    demonstration (rules, no model)" byline), LLY is a real valued move. Moves show EV, cash at risk (with
    `cash_at_risk_note` beside a zero), payback, spread and MCDA; a `chosen: null` decide badges the
    "Least-bad option" and shows the `selection_rule`. "Why it will work" (`why_it_works_rows`) is a cited
    table with footnote chips; "Why we passed" comes from `stance.alternatives[].why_passed`.
- **Ask, Product, Forces, Proof, Data moat, Memo** as before. Product shows the v2 five-row table with a chip
  per cell and muted "needs citation" cells. Proof keeps verifier, gate, backtest and seals, and adds "Where
  the AI was confidently wrong" (`proof.ai_wrong_cases`) and "Honest limits" (`meta.honest_limits`). The memo
  carries the kill-signal table with a Baseline column: the physician-breadth row (Open Payments) cites its
  baseline with withheld machine-data chips; `context` rows show value plus chip.
- **`/cockpit/triage`** ("Internal triage", not in the side nav, muted "not part of the pitch" banner): the
  league score, league needle, rank vs v2, robustness variants and score anatomy. Old links (`#/ask`,
  `#/proof`, ...) redirect under `/cockpit`.
- **Trim layer** (Parker's `docs/ui-trim/`, in `public/assets/trim.js` + `trim.css`): cuts or fades secondary
  content by its visible label on cockpit routes only; the "Full detail" pill (bottom right) turns it off.
  Adapted: it never runs on the chat page, and pinned exhibits are cut only when none are pinned.
  `public/assets/fit.css` lets the cockpit shrink below 1280 px.

## Citations, markers and pitch rules

- Chips: page cites (purple), withheld (dashed, drawer says "Quote withheld: <reason>", never an empty quote
  box), derived ("ƒ", drawer lists clickable operands), data rows ("▦", drawer shows the JSON path and the check).
- Markers in `sentence_marked`, `formula_marked`, memo markdown and math `text_marked`: `[n]` chip (resolved
  through `marker_map`; runs of more than three collapse to "+N"), `[derived: a, b]`, `[constant: NAME]` muted
  pill, `[assumption]` / `[assumption: reason]` amber pill (reason as tooltip, printed as small text),
  `marker_licensed` numbers as one muted "licensed source" mark.
- Numbers-check pill (separate from "quote located"): passed with verified / derived / assumed counts, failed
  with the unsupported list, `no_numbers`, or unchecked.
- Pitch rules: score L, the S equation, score anatomy, robustness, rank vs v2 and needle-status words never
  appear outside `/cockpit/triage`. The chat league answer is a plain ranked list; chip tooltips, drawers and
  source cards drop any line naming them; "Detector" reads "Signal type".

## Known gaps

- AZN and NVO needles come from the plain rule (`needle_source: "rule"`), not the red-team read.
- 6 companies (ABBV, AZN, BMY, JNJ, NVO, PFE) have a template stance, not a valued DECIDE move.
- VRTX is onboarding-pending: no findings, no company file and no product tables.
- The JS bundle is about 800 kB (230 kB gzip); at 5 Mbps the header takes about 1.7 s.
- Needle answers run over the 160-word chat target for AMGN (184), ABBV (195) and GILD (197).
- `meta.honest_limits` still mentions "a published robustness table" though that table now lives on triage.

## Live model (optional, off by default)

`PYTHONPATH=. python ui/server.py --port 8787` with `ANTHROPIC_API_KEY` set, then open
`/?live=1#/cockpit/ask`. The default build never probes it.

## Code map

- `src/screens/Chat.tsx`: the demo page; `src/components/chat/` (Answer, Md); `src/lib/memos.ts`
  (index-first loader, `loadMemo`, `matchMemo`, memo cite to evidence).
- `src/lib/data.ts`: loaders, `DataProvider`, `useData`, `findNeedle` (rule needle, never explained-by-footnote).
- `src/lib/cites.ts`: marker parser, derived / row / withheld helpers, the pitch-term filter.
- `src/lib/types.ts`: the data contract as types. `src/lib/retrieve.ts`: offline retriever (Ask, chat matching).
- `src/screens/`: Briefing, Ask, Product, Forces, Proof, Moat, Memo, Triage; parts in `src/components/<screen>/`;
  DECIDE tables in `src/components/decide/Decide.tsx`.
- `vite.memos-index.js`: the index / per-answer plugin. `public/assets/`: fit, trim.
- Teal is for model or template output only; purple is sourced data and navigation.

## Print

`@media print` hides the chrome and side nav. On the chat page, Print on a memo card prints only that card;
`/cockpit/memo` prints the full memo with its title row hidden.
