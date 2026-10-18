# NEEDLE (`ui/`)

**One page, one question.** The app at `/#/` answers the case's Part 1 prompt ("find material, non-obvious
findings about one company and compare one of its key products against its rivals.") from precomputed JSON.
There is no cockpit and no other route; every other path returns to `/`.

Static single-page app (Vite + React 18 + TypeScript + Tailwind v3, hash router). No API key, no model, no
network at runtime; fonts are bundled (@fontsource), so `dist/` works offline from any static server or
sub-path (`base: "./"`). JS bundle about 222 kB (70 kB gzip).

## Run

```bash
cd ui
npm install                                   # exact versions pinned in package.json
npm run dev -- --port 5173                    # http://localhost:5173/#/
npm run typecheck                             # tsc --noEmit
npm run build                                 # tsc --noEmit && vite build -> ui/dist/
python3 -m http.server 8090 -d dist           # serve the static build: http://localhost:8090/#/
```

Publish the root of `ui/dist/` as is (index.html plus `assets/` and `data/`).

## The page

- An empty chat shows one suggestion: the Part 1 prompt chip. There is no company pill and no other chip.
- Typing the prompt or an alias ("part 1", "find material", "non-obvious findings", "compare ... product ...
  rivals") answers with the Part 1 deliverable. "why this company", "why <name>" or "why did it beat the other
  nine" answers with the selection card alone. Anything else gets one muted line ("This demo answers the
  case's Part 1 prompt. Click the chip above.") and the chip again.
- Under the answer, the follow-up chips are the other two picks; they switch the answer in place.
- The page reads only `data/part1/*` and `data/meta.json` (company names). It loads no memos.

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

- **Pitch rule**: every string from part1 files passes `scrub()` (the Answer.tsx INTERNAL regex plus
  `INTERNAL_TEXT`), so no league score, S or robustness wording renders.
- **Reveal**: header, selection card and Findings first, the rest 0.7 s later (click to show at once).

## Citations, markers and pitch rules

- Chips open the source drawer: page cites (purple), withheld (dashed, "Quote withheld: <reason>"), derived
  ("ƒ", operands listed), data rows ("▦", the JSON path and the check). A cite id with no exported evidence
  object renders as a struck "[n]" (Source not exported).
- Markers: `[n]` chip (through the nearest `marker_map`; runs over three collapse to "+N"),
  `[derived: a, b]`, `[constant: NAME]` muted pill, `[assumption]` / `[assumption: reason]` amber pill.
- Numbers-check pill: passed with verified / derived / assumed counts, failed with the unsupported list,
  `no_numbers`, or unchecked.
- Pitch rules: no league score, no S, no robustness or needle-status words anywhere; every part1 string
  passes `scrub()` and the chips and drawer drop any line naming them.

## Code map

- `src/screens/Chat.tsx`: the page. `src/App.tsx`: the one route.
- `src/components/chat/`: `Part1Answer` (layout, findings, product, priced in), `Part1Selection` (card and
  sealed document drawer), `Part1Trace` (reasoning trace), `Md` (inline markdown and marker pills).
- `src/components/`: `CiteChip`, `SourceDrawer`, `NumericCheck`, `ConfPill`.
- `src/lib/part1.ts`: loaders, routing, scrub, figure guard, cite resolution. `src/lib/cites.ts`: derived /
  row helpers and the pitch filter. `src/lib/data.ts`: `fetchJson` and the withholding rule.
  `src/lib/types.ts`: the data contract as types.
