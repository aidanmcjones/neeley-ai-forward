# NEEDLE cockpit (`ui/`)

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
request outside its own origin. Deep links: `/#/ask?q=...`; company via `?t=BMY` (before or
inside the hash). The picked company is remembered in localStorage (`needle.ticker`) and kept in
step with any `?t=` in the URL, so a hard reload keeps it. A first visit with nothing stored opens
`/#/` on `meta.default_ticker` (the league leader).

## Screens

- `/` **Briefing**: KPI row, the Sharpest Needle hero (engine verdict, why unseen, impact, peers,
  page cites), the sortable findings grid with filters, peer and score charts for the selected row,
  and the draft stance panel.
- `/ask` **Ask NEEDLE**: preset and typed questions answered by the offline retriever with cited
  sentences, a "what was checked" trace, exhibit cards (timeline, head-to-head, price, peer) with
  Pin to memo, and source cards.
- `/product` **Product fine print**: product vs rivals on label, safety, dosing, exclusivity,
  IRA, Medicare spend and gross-to-net; price series per drug; what limits growth.
- `/forces` **Three forces and priced-in**: IRA / MFN / tariff exposure across the 10, the
  priced-in scorecard, consensus vs guidance and the IRA cut check.
- `/proof` **Proof**: verifier rules and verdict counts, AI-caught cases, backtest (v1 refuted,
  v2 with CIs), calibration, the J&J blind test and sealed forecasts with in-browser sha256 check.
- `/moat` **Data moat**: coverage matrix, the derived tables, no-free-source proxies, corpus
  trust levels and the any-ticker onboarding card.
- `/memo` **CEO memo**: one printable page from `stance`, editable inline (saved per browser),
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

## Known data gaps (stated, not hidden)

- Company-stated exclusivity / LOE dates are not in this export; timelines show the FDA estimate
  (Orange / Purple Book) and say "company-stated LOE not exported".
- 166 findings are held for a human: no automatic check could confirm a page quote. They are
  shown and labelled, never used for stance dollars.
- LLY gross-margin impact dollars are flagged suspect by the exporter (impact exceeds trailing
  operating income); the UI strikes them through and says why.
- `meta.moat.stages` text is stale (it still says Model "blocked" and UI "waiting"); the Data moat
  screen shows it as exported until the exporter is updated.
- NVO and AZN file 20-F / 6-K, so they have no quarterly product revenue breakouts
  (`discontinued_breakouts` is empty) and no sealed forecast. AZN has no rejected claims and LLY no
  IRA cut rows; those panels show an empty state. VRTX is onboarded but has no findings yet
  (`meta.onboarding_pending`), so it is not in the company picker.

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
