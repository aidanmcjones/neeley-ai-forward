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

## NEEDLE UI (branch `ui`, PR #22 at 7723625, artifact version 6)

**What it is.** `ui/` is a static app (Vite + React + TypeScript + Tailwind + Recharts) over precomputed JSON
in `ui/public/data/`. No API key, no live model, no network at runtime. The demo is a chat page at `/#/`;
the seven cockpit screens are the depth at `/#/cockpit` (one small "Full cockpit" link). Full details:
`ui/README.md`.

**Regenerate and publish** (repo root):
```
NEEDLE_TICKER=XXX PYTHONPATH=. python -m agent.ui_export   # NEEDLE_TICKER optional: the team's pick
PYTHONPATH=. python -m agent.ui_memos
PYTHONPATH=. python -m agent.ui_memos --check
cd ui && npm run build                                     # then publish the root of ui/dist/
```
Local: `cd ui && npm run dev -- --port 5173` or `python3 -m http.server 8090 -d ui/dist`.

**What works.**
- Chat: per-answer loading (`ui/vite.memos-index.js` derives `memos_index.json` and `memos/<id>.json`, with a
  full-file fallback; chips in 0.6 s and first answer in 0.9 s at 20 Mbps). With no pick
  (`default_ticker_source: "unpicked"`) it starts at "Pick a company" with six global questions; picking a
  company runs its 7-step `suggested_by_ticker` flow from needle to CEO memo. Part 1 answers as chat, Part 2
  as a memo card with Copy and Print.
- Needle: red-team read or plain rule (`needle_source`, shown on the pill), `needle_reason` under the
  headline; explained-by-footnote rows are never the needle. Findings grid ranked by impact with a Peer column.
- DECIDE: AMGN, MRK and GILD as pipeline demonstrations, LLY as the real valued move; why it will work, why we
  passed, cash-at-risk notes, least-bad option when nothing clears the hurdle, and the kill table with the
  physician-breadth row (Open Payments baseline, withheld machine-data chips).
- Every number carries a chip (page, withheld, derived, data row) and the numbers-check pill; assumption
  markers show their reason. Score L, S, robustness and needle-status words appear only on `/cockpit/triage`
  (unlinked, "Internal triage view, not part of the pitch"); tooltips and drawers filter them out elsewhere.
- Parker's trim layer on cockpit routes with a "Full detail" pill; the chat page is untouched by it.
- Last sweeps (this commit's data): chat 16 of 17 clean (the one flag is honest-limits prose saying "no
  detector yet"), cockpit 80 pages, 102 sub-states and 10 printed memos clean, hero above the fold at
  1280 x 800 for all ten, drawer term filter clean.

**Known gaps.**
- AZN and NVO needles come from the plain rule, not the red-team read.
- 6 companies (ABBV, AZN, BMY, JNJ, NVO, PFE) have a template stance, not a valued move.
- VRTX products are missing (onboarding pending, no findings or company file).
- The JS bundle is about 800 kB (230 kB gzip).
- Needle answers run over 160 words for AMGN (184), ABBV (195) and GILD (197).
- `meta.honest_limits` still mentions "a published robustness table".
