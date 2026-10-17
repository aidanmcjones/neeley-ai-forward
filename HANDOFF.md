# Handoff

Update this every hour and at the end of every task.

**Last updated:** Sat Oct 17, ~12:00, corpus branch (Parker's agent)

## Sat Oct 17: the real case and the source corpus
- The case is "The Fine Print" (Advanced track): pick 1 of 10 drugmakers, 5+ cited findings with page numbers and
  impact math, a Sharpest Needle, one product vs rivals, then one CEO move. Case and rubric PDFs are with Parker.
  Last night's LOE / revenue-at-risk plan is mostly superseded; the collectors are reused.
- data/corpus/: 835 page-anchored documents for the 10 companies, 9 rival makers and 52 drugs. Start at
  data/corpus/README.md, then manifest.csv and GAPS.md.
- New code (new files only; no existing file edited): agent/corpus.py (SEC with page markers), agent/drug_pack.py
  (labels + FDA/CMS slices), agent/ir_fetch.py (verbatim IR saves), agent/corpus_check.py (manifest + gaps).
- Open: company not picked yet. Slides for BMY, ABBV, LLY, AMGN, REGN, ALNY need a manual browser download
  (IR sites return 403 to scripts). 36 of 54 transcripts are third-party: verify cited quotes before use.

## What works
- agent/llm.py: Claude Opus 5.5 call with cache and refusal fallback
- app/main.py: Streamlit page that loads data/ files, asks a question, shows the answer

- agent/tenk.py: standalone SEC collector. Pulls 10-K and 20-F primary documents, strips to text, finds Item
  sections, gzips to R2 or data/sec/, writes index/tenk_index.jsonl, saves XBRL facts. Tested live on MCK (10-K)
  and ALC (20-F). section_text(row, "business" | "risks" | "mdna") returns just that part.
  Run: `python -m agent.tenk --tickers MCK,COR,CAH,MRK,BMY,ALC --years 6`

## What's broken or untested
- Nothing deployed yet. Full case data arrives Sat 9 am.
- R2 bucket for this repo not created yet; collector falls back to data/sec/ (gitignored) until R2_* env vars are set.
- Live Claude call untested until ANTHROPIC_API_KEY is in .env.

## Next 3 tasks
1. Copy the pharma case files into data/ and docs/ when they drop Saturday 9 am
2. Write PLAN.md one-liner, persona, golden path
3. Wire one case input through one prompt into one rendered output

## How to run
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # paste the API key
python -m agent.llm    # should print: scaffold OK
streamlit run app/main.py
```

## Sat Oct 17, evening: NEEDLE cockpit UI (branch `ui`)

**What it is.** `ui/` is a static single-page app (Vite + React 18 + TypeScript + Tailwind 3 + Recharts,
hash router) that reads precomputed JSON from `ui/public/data/` written by `python -m agent.ui_export`.
No API key, no network, fonts bundled: it runs with Wi-Fi off. Spec and data contract: `docs/ui_spec.md`.
Seven screens: Briefing (opens here, league leader preloaded: AMGN under v2), Ask NEEDLE, Product fine print, Three forces
and priced-in, Proof, Data moat, CEO memo; plus the global source drawer and ⌘K palette.

**How to run.**
```
cd ui && npm install
npm run dev -- --port 5173                        # http://localhost:5173/#/
npm run build && python3 -m http.server 8090 -d dist   # static build: http://localhost:8090/#/
python -m agent.ui_export                         # (repo root) regenerate ui/public/data/
PYTHONPATH=. python ui/server.py --port 8787      # optional live Ask; then open /?live=1#/ask
```

**What works (checked in headless Chrome at 1280x800).** All 7 routes x 10 tickers load with no console
errors or warnings, no "undefined" / "NaN" / "null" / "[object Object]" text, no horizontal overflow; every
product tab and every Ask preset for all 10 tickers is clean too (102 states). Hero and KPI row sit above the
fold for every ticker. Pinned exhibits render full size in the memo and print without clipping. Keyboard:
Tab reaches the company select, nav, chips and grid rows; Enter on a chip opens the source drawer, Esc
closes and returns focus; ⌘K opens the palette; `?q=` and "Jump to <T>" survive a hard reload. Dark mode
text passes a 3:1 contrast scan (4 tickers x 7 routes). The static build loads `/#/` and `/#/proof` with zero off-origin requests.

**v2 data (follow-up pass, same evening).** The UI now reads the v2 engine export. League order AMGN, GILD,
JNJ, AZN, MRK, ABBV, BMY, LLY, PFE, NVO; default ticker AMGN. New on screen: needle status pill (strict /
provisional / floor relaxed; 5 of 10 provisional), withheld-citation chips and drawer, the decide panel and
kill-signal table (stance.decide covers LLY only; the other nine keep the template stance), Score anatomy v2,
product v2 tables with per-cell citations (20 of 22 case-set products; AMGN Repatha and Enbrel pending a
product_cli error, so they show the v1 table with a note), and a numbers-check pill next to "quote located".
Re-swept: 70 route pages and 102 product/Ask states clean, dark mode and static build clean.

**Known gap: numbers are not page-checked yet.** The verifier proves each quote is on its page, not the
numbers in the finding sentence; the citation skeptics found about 58% of numeric tokens in v2 finding
sentences on pages that do not contain them. Until league_v3 fills `numeric_check`, every finding shows a muted
"numbers not yet page-checked" pill (hero, grid rows, memo points, Ask answers); the demo must not present
numbers as page-verified. **AMGN's needle (receivables +17.5% YoY) is disputed pending v3:** the cited balance
sheet compares June 2026 with December 2025, which is 6.9%.

**v3 data (third pass).** `meta.engine` v3. League order AMGN, GILD, AZN, MRK, BMY, NVO, ABBV, LLY, PFE, JNJ;
rank change vs v2 shown next to the rank. JNJ has needle status none: the hero says no row qualifies and shows
the highest-scored finding as such. Robustness table (8 variants; AMGN leads in 6, GILD in 2) on the Briefing
and Proof. Finding flags as pills; guard reason, corroborates link, fact key and impact channel in the
selected-row strip. `numeric_check` is still unchecked everywhere pending the gate commit. Re-swept: 70 routes,
102 sub-states, 10 printed memos clean; hero above the fold for all 10 (headline drops to 32 px for very long
sentences); dark mode and static build clean.

**Derived cites and marked sentences (fourth pass).** The UI renders `derived_from` evidence (own chip style;
drawer lists clickable operands; memo sources print "derived from [n][m]"; withheld wins) and
`finding.sentence_marked` (`[n]` chips, `[derived: a, b]`, amber `[assumption]` pills) on the hero, grid, memo
points and Ask answers. Both were checked by injecting values; the export does not carry them yet. Proof now
states the public status whitelist (exact, substring, fuzzy, number_match, derived; machine_data and
unverified never quote). For the current artifact link, see PR #22.

**Chat overhaul (Sat Oct 17, night): the chat is the demo, the cockpit is depth.** `/#/` is now one page: a
chatbot over cached answers in `ui/public/data/memos.json` (format "chat" for Part 1 Find questions, "memo"
for the Part 2 CEO memo card with TO / FROM / RE / DATE, Copy as markdown and Print). Suggested chips run
needle, findings, product, priced-in, the CEO memo, then "Where was the AI wrong?", and `ask_next` chips let a
judge click through in under a minute. `/#/?q=<prompt>` opens on an answer. The seven cockpit screens moved
under `/#/cockpit` (old links redirect), reached from a small "Full cockpit" link. Until the exporter's
memos.json lands, the page shows a 3-record sample (`_sample/memos.json`) with a banner.

**Pitch trim (Sat Oct 17, late night).** League score, S equation, score anatomy, robustness and rank vs v2
are off every judge-facing surface (chat and cockpit Briefing / Proof) and live at `/#/cockpit/triage` (unlinked,
"Internal triage view, not part of the pitch"). The chat starts at "Pick a company" unless
`meta.default_ticker_source` is "pick". Parker's trim layer (`ui/public/assets/trim.js`, `trim.css`) runs on
cockpit routes only with a "Full detail" pill; `fit.css` is now in the repo and linked from `index.html`.

**Open.**
- `sentence_marked` / `derived_from` in the export.
- `numeric_check` and token-level assumption tags (for "[assumption]" markers) not in the export yet.
- stance.decide for the nine companies other than LLY; AMGN product v2 tables.
- VRTX is onboarding-pending (no findings, no company file, not in the picker).
- The JS bundle is about 800 kB (about 230 kB gzip); fine for a local demo, not code-split.
