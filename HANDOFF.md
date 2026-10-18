# Handoff

Update this every hour and at the end of every task.

**Last updated:** Sat Oct 17, ~12:00, corpus branch (Parker's agent)

## Sat Oct 17 evening: why Merck
- docs/how_we_picked_mrk.md: the 7 steps from case to MRK, the v3 scores and files used. All 110 MRK nugget
  quotes re-verified (load BMY, PFE, JNJ, GSK, AZN docs alongside MRK).

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
