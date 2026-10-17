# NEEDLE (`ui/`)

**The demo is the chat page at `/#/`; the cockpit at `/#/cockpit` is the depth.**

Static single-page app (Vite + React 18 + TypeScript + Tailwind v3 + Recharts) that reads
precomputed JSON from `public/data/`. No network at runtime, fonts bundled via @fontsource.
Spec and data contract: `../docs/ui_spec.md`.

## Run

```bash
cd ui
npm install                                   # exact versions pinned in package.json
npm run dev -- --port 5173                    # http://localhost:5173/#/ (hot reload)
npm run typecheck                             # tsc --noEmit
npm run build                                 # tsc --noEmit && vite build -> ui/dist/
python3 -m http.server 8090 -d dist           # serve the static build: http://localhost:8090/#/
```

`base: "./"` and a hash router mean `dist/` works from any static server or sub-path, with Wi-Fi off:
fonts are bundled (@fontsource woff2 in `dist/assets/`), and the default build makes no network
request outside its own origin. Deep links: `/#/?q=<prompt>` opens the chat on that answer;
`/#/cockpit/ask?q=...` for the cockpit (old `/#/ask`, `/#/proof`, ... links redirect under `/cockpit`); company via `?t=BMY` (before or
inside the hash). The picked company is remembered in localStorage (`needle.ticker`) and kept in
step with any `?t=` in the URL, so a hard reload keeps it. A first visit with nothing stored opens
`/#/` on `meta.default_ticker` (the league leader).

## Chat (the demo page, `/`)

One centered column (max 760 px), no side nav: the NEEDLE wordmark, "Ask for a memo. Every number is cited to
the page.", a company pill, the thread, and a prompt box (Enter sends, Shift+Enter new line). Answers are
cached in `public/data/memos.json` (no API key, no live mode); if it is missing the page uses the 3-record
fixture `public/data/_sample/memos.json` and says so.

- **Two formats.** `format: "chat"` (Part 1, Find) answers as prose with inline cite chips, optional KPI row
  or table, then follow-up chips from `ask_next`. `format: "memo"` (Part 2, Decide) renders a paper card with a
  TO / FROM / RE / DATE header (`memo_header`), section headings, byline, numeric-check pill, Copy as markdown
  and Print (prints only that card).
- **Blocks**: h, p (markdown: **bold**, *italic*, `code`, `[n]` cite chips, `[derived: a, b]`, amber
  `[assumption]`), kpi, table, list, callout. Cite chips open the shared source drawer; withheld and derived
  styles are the same as in the cockpit, and derived operands resolve against the memo's own `cites`.
- **Data-row cites** (`cite_id` "row:...", no page or url): a "data" chip (▦, solid underline), separate from
  withheld (dashed) and derived (ƒ); the drawer shows the source, the JSON path in `ref`, the check text from
  `verification` and the row text in `quote`.
- **Math blocks** (`{type: "math", label, text, cite}`): a collapsed "Show the math: <label>" disclosure in
  monospace with its cite chip; Print opens them so the printed memo shows the formulas.
- **Reveal**: a typewriter of 1.5 to 2.5 s per answer, skippable by click; instant under reduced motion.
- **Matching** (`src/lib/memos.ts`): exact prompt or alias first, then term overlap using the retriever's
  synonym groups over prompt + aliases (floor 0.3), preferring the selected company; no match replies "I can
  write these memos:" with the suggested chips and a "Show all prompts" list grouped by kind.
- **Suggestions**: `memos.suggested` (a Part 1 to Part 2 flow), re-mapped by kind when the company pill changes.
  Kinds: needle, findings, product, peers, priced_in, league, ai_wrong, moat, how_it_works (format chat) and
  ceo_memo, prove_wrong (format memo); ceo_memo is the Part 2 step. Memo cites may carry `derived_expr`, shown
  in the drawer as "Computed as".
- Byline: teal AiMark only for model-written records; template / decide_v2 / data read "rules, no model".
  Numeric-check pill: passed (counts), failed, unchecked, or `no_numbers` ("no numbers to check").

The cockpit screens below now live under `/cockpit` (link "Full cockpit" under the prompt box).

## Screens

- `/cockpit` **Briefing**: KPI row, the Sharpest Needle hero (engine verdict, why unseen, impact, peers,
  page cites), the sortable findings grid with filters, peer and score charts for the selected row,
  and the draft stance panel.
- `/cockpit/ask` **Ask NEEDLE**: preset and typed questions answered by the offline retriever with cited
  sentences, a "what was checked" trace, exhibit cards (timeline, head-to-head, price, peer) with
  Pin to memo, and source cards.
- `/cockpit/product` **Product fine print**: product vs rivals on label, safety, dosing, exclusivity,
  IRA, Medicare spend and gross-to-net; price series per drug; what limits growth.
- `/cockpit/forces` **Three forces and priced-in**: IRA / MFN / tariff exposure across the 10, the
  priced-in scorecard, consensus vs guidance and the IRA cut check.
- `/cockpit/proof` **Proof**: verifier rules and verdict counts, AI-caught cases, backtest (v1 refuted,
  v2 with CIs), calibration, the J&J blind test and sealed forecasts with in-browser sha256 check.
- `/cockpit/moat` **Data moat**: coverage matrix, the derived tables, no-free-source proxies, corpus
  trust levels and the any-ticker onboarding card.
- `/cockpit/memo` **CEO memo**: one printable page from `stance`, editable inline (saved per browser),
  pinned exhibits drawn full size, Export PDF via `window.print()`.
- Global: source drawer (any citation chip; Enter opens, Esc closes) and the ⌘K / Ctrl-K palette.

## Data

`public/data/` is written by the exporter, from the repo root:

```bash
python -m agent.ui_export        # writes ui/public/data/{meta,league,proof}.json and companies/<T>.json
```

If `public/data/meta.json` is missing, the loaders fall back to the tiny smoke-test fixture in
`public/data/_sample/` and every screen shows an amber "sample data" banner. Any other missing
file is reported by name ("Could not load /data/companies/BMY.json"), never silently blanked.
`useData()` returns `source` (`{prefix, sample}`), the base every `data/...` path resolves from.

## Live model (optional)

Ask is offline by default and never fakes a model. For live answers, from the repo root:

```bash
PYTHONPATH=. python ui/server.py --port 8787   # needs ANTHROPIC_API_KEY in the env or .env
```

then open `/?live=1#/ask` (remembered; `?live=0` turns it off). Only then does the page probe
`http://localhost:8787/api/health`; the answer is grounded in the retrieved findings and its
cites and numbers are checked server side.

## v2 engine data (Sat Oct 17 evening)

The export now comes from the v2 engine (FIND, `docs/quant_model.md`; league note `docs/league_v2_note.md`).
League order: AMGN, GILD, JNJ, AZN, MRK, ABBV, BMY, LLY, PFE, NVO; `meta.default_ticker` is AMGN.

- **Needle status pill** (hero, and a suffix in the company picker): `league[].needle_status` strict (green),
  provisional or floor_relaxed (warn, tooltip explains the fallback). Provisional today: GILD, AZN, ABBV, BMY, NVO.
- **Withheld citations**: evidence with `withheld: true` (unverified, or a licensed source) renders as a dashed,
  muted chip; the drawer shows document, period and page only, plus "Quote withheld: <reason>", never an empty
  excerpt box. Ask trace chips, source cards and the live source card follow the same rule.
- **Decide panel** (`stance.decide`, LLY only today): the three moves with EV, cash at risk, payback month,
  scenario spread and MCDA, chosen move first and badged, footnote chips f1..fN (listed under "Move inputs"
  in the memo), and the kill-signal table under "What would prove us wrong". Other companies keep the
  template stance and show `stance.note`.
- **Score anatomy v2**: S = M x O x E x pi from `vector.v2`, with the v1 score struck through; v1 chart otherwise.
- **Product v2** (`labels.v2[slug]`): five cited rows with a chip in every cell, the tied product findings
  and growth limiter, and the uncited-cell count as a footnote; the v1 table sits in a collapsible below.
  AMGN (Repatha, Enbrel) has no v2 table yet: v1 table with "v2 table pending (product_cli error)".
- **Numbers check pill**, separate from the "quote located" verdict: driven by `numeric_check`
  (`{status, checked, total, verified, derived, assumed, unsupported[]}`) on findings, decide moves and
  footnotes, and labels.v2 cells, with a block summary in the panel header when present. Passed = green
  "numbers page-checked a verified · b derived · c assumed"; failed = red "N numbers unsupported" (list in the
  tooltip); unchecked or absent = muted "numbers not yet page-checked". Shown on the hero, grid rows, memo
  points and Ask answers.

## v3 league (Sat Oct 17, late)

`meta.engine` is "v3". League order: AMGN, GILD, AZN, MRK, BMY, NVO, ABBV, LLY, PFE, JNJ (the subtitle shows
each company's change vs its v2 rank, e.g. JNJ ▼7 vs v2 #3). Needle status: AMGN, AZN, MRK, NVO, ABBV strict;
LLY provisional; GILD, BMY, PFE floor_relaxed; **JNJ none**: the hero says "No row qualifies as the Sharpest
Needle" and shows the top-scored finding labelled "Highest-scored finding" with a muted pill (no row is ever
promoted to needle; `needle_id` is null).

- **Robustness**: `meta.league_robustness` (out/league_v3_robustness.json, 8 variants) renders as a
  rank-by-variant table on the Briefing (under the charts) and on Proof (with the v2 rank column), the selected
  company highlighted, ∅ where no needle qualifies, and the reading "AMGN leads in 6 of 8 variants; GILD leads
  in 2 of 8".
- **Finding flags** (`flags`: needle_eligible, provisional, one_off, not_quantified, not_league_comparable) are
  labelled pills on grid rows and the hero. The selected-row strip under the grid shows the not-quantified
  reason, `guard_reason`, "corroborates <id>" (click jumps to that row), `fact_key` and `impact_channel`.
  Rejected rows show their guard text as the reason.
- Stance options exclude not_quantified rows; options with no dollar figure read "no quantified $".
- `numeric_check` is still null on every row (the uncited-claim gate is not committed yet), so every finding
  shows "numbers not yet page-checked".

## Derived citations and marked sentences (rendered from the spec, awaiting export)

- **Derived evidence** (`derived_from: [cite_id, ...]`, no quote): solid-bordered italic chip with an "ƒ" prefix
  (distinct from the dashed withheld chip). The drawer shows document, page, value, the computation
  (`derived_expr`) and "Derived from [a][b]", each operand a button that opens that operand's own drawer entry;
  never an empty quote box. Operands are looked up by `cite_id` anywhere in the company file. Memo Sources print
  "derived from [n][m]" with the operands' footnote numbers (operands not cited directly are appended); Ask
  source cards and live source cards say "derived from". `withheld: true` wins over `derived_from`.
- **`finding.sentence_marked`**: when present it replaces the sentence on the hero, grid rows, memo points (when
  the point starts with the finding sentence and has not been edited) and Ask answers. `[n]` becomes a cite
  chip for evidence n (1-based), `[derived: a, b]` a "derived" mark with operand chips, `[assumption]` an amber
  "assumption" pill. Absent: the plain sentence, unchanged. The UI never adds markers.
- Proof states the public status whitelist: exact, substring, fuzzy, number_match, derived (operands must pass);
  machine_data and unverified never show a quote.

## Known data gaps (stated, not hidden)

- **Numbers are not yet page-checked** (still true under v3: `numeric_check` is null until the gate commit). The verifier checks that each quote is on its page; it does not yet
  check the numbers in the finding sentence. The skeptic pass found about 58% of numeric tokens in v2 finding
  sentences sit on pages that do not contain them. Until league_v3 fills `numeric_check`, every finding shows
  "numbers not yet page-checked". AMGN's needle (receivables +17.5% YoY) was disputed: v3 now states it as 10,227 vs
  8,701 a year earlier (2026Q2 vs 2025Q2), but the numbers are still not page-checked.
- Company-stated exclusivity / LOE dates are not in the v1 export; v2 product tables carry the 10-K date where found.
- 11 finding citations are withheld under the public rule (quote not confirmed on the page); all 17 decide
  footnotes for LLY are external benchmarks or team inputs with quotes withheld, and several move inputs
  are flagged as assumptions in the data.
- `stance.decide` exists for LLY only; the other nine show the rule-drafted template stance.
- NVO and AZN file 20-F / 6-K: no quarterly product revenue breakouts and no sealed forecast. VRTX is
  onboarding-pending (no findings, so not in the picker).
- `sentence_marked` and `derived_from` are not in the current export yet (verified by injecting values); until
  they land, sentences render plain and no number carries an "[assumption]" marker.

## Code map

- `src/lib/types.ts`: types mirroring the data contract (optional, unknown-tolerant fields).
- `src/lib/data.ts`: loaders, `DataProvider`, `useData({ proof? })`, `CompanyContext`/`useCompany`
  (ticker from `?t=`, then localStorage, then `meta.default_ticker`), `resolveCite`, `findNeedle`.
- `src/lib/format.ts`: `money` ($1.2B / $340M), `pct`, `num`, `z`, `date`, `isoDate`.
- `src/lib/retrieve.ts`: offline retriever `retrieve(query, company) -> {findings, exhibits, trace}`.
- `src/lib/exhibits.ts`: exhibit shaping, memo pins (`usePins`, `togglePin`, `removePin`), theme colors for SVG.
- `src/screens/`: Briefing, Ask, Product, Forces, Proof, Moat, Memo; screen parts in `src/components/<screen>/`.
- `src/index.css`: theme tokens as CSS variables (light, dark via `prefers-color-scheme` unless
  `data-theme="light"`, and `data-theme="dark"`), AI pulse, print stylesheet.
- `tailwind.config.ts`: token colors (`bg-purple`, `text-teal`, `border-line`, ...), fonts
  `font-display` (Bebas Neue), `font-body` (Montserrat), `font-mono` (JetBrains Mono).

Teal (`teal`, `teal-soft`) is for model/template output only. Purple is sourced data and navigation.

## Components (`src/components/`, all re-exported from `index.ts`)

- `Chrome`: top bar with NEEDLE logo (teal "DLE"), tagline, company picker, As-of pill, ⌘K Ask button.
- `SideNav`: 220px route nav (Briefing, Ask, Product, Forces, Proof, Data moat, Memo) with active state.
- `KpiTile`: label, big Bebas number, footnote naming the source file (`footnote2` for a second line, or `wrap`); `hot` variant.
- `Panel`: titled card with optional right-side meta; `ai` variant for teal AI panels.
- `CiteChip`: mono `[n]`/label chip; click, Enter or Space opens the SourceDrawer; `onPreview` on hover/focus.
- `AiMark`: pulsing teal star plus label (static under `prefers-reduced-motion`).
- `StanceBadge`: teal stance label (Defend / Attack / Reprice / Partner ...).
- `ConfPill`: high/medium/low confidence pill, color plus text.
- `ScoreBar`: horizontal bar with a text value and a tone.
- `DataTable`: generic sortable table, sticky header, tabular numbers, keyboard row select callback.
- `SourceDrawer` / `SourceProvider` / `useSource`: global right drawer with citation, URL, page,
  speaker, figures checked, verifier status, transcript grade, excerpt with `<mark>`; Esc closes, focus trapped.
- `CommandPalette` / `PaletteProvider` / `usePalette`: ⌘K / Ctrl-K; company presets go to `/ask?q=`, "Jump to <T>" switches company.
- `EmptyState`: honest empty state naming the missing file.
- `ScreenFrame` / `SampleBanner`: screen title row with loading/error handling (`printTitle={false}` hides it in print); amber sample-data banner.

## Print

`@media print` hides `Chrome` and `SideNav` (`[data-chrome]`, `[data-sidenav]`, `.no-print`), so
`window.print()` on `/memo` exports just the memo.
