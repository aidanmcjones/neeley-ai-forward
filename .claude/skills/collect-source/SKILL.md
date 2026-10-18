---
name: collect-source
description: Save an investor-relations or public document (transcript, slides, investor deck, press release, annual report) into data/corpus verbatim with page markers via agent.ir_fetch. Use whenever a task says collect, pull, fetch or fill a corpus gap.
---

# Collecting a source document

## Hard rules
- Find URLs with WebSearch or WebFetch, but **never save text you read through WebFetch** (it paraphrases). Every save goes through:
  ```bash
  python -m agent.ir_fetch "<URL>" --ticker <T> --rel <subpath>.md --type <type> --period <period> --quality official|third_party [--group companies|peers] [--keep-pdf]
  ```
  It downloads the raw file, converts it mechanically with `[[page N | printed P]]` markers, and logs a row to `sources.jsonl`.
- If it errors (HTTP 403, a JS page, a scanned PDF), try another source for the same document. Never paste text in to work around it.
- Write only inside `data/corpus/<group>/<T>/`. No git, no code edits. SEC 10-K, 10-Q and 8-K are already collected; do not re-collect them.
- Skip files over 50 MB. Keep to the time box you were given; partial is fine.

## Paths and types
| What | `--rel` | `--type` | Notes |
|---|---|---|---|
| Earnings call | `transcripts/<YYYYQn>_transcript.md` | transcript | Full call incl. Q&A with speaker names, never a summary. Prefer the IR site (official), else a free full text such as fool.com (third_party). |
| Earnings slides | `presentations/<YYYYQn>_earnings_slides.md` | earnings_slides | `--quality official --keep-pdf` |
| Investor day, JPM deck | `presentations/<YYYY-MM>_<short-name>.md` | investor_presentation | `--keep-pdf` |
| Policy press release (MFN, tariffs, US manufacturing, TrumpRx, IRA) | `policy/press_<YYYY-MM-DD>_<slug>.md` | press_release | official |

## Finish
- Append each miss, one per line, to `data/corpus/<group>/<T>/GAPS.txt`.
- Final report: a table of saved files (rel path, period, quality, source domain), then what you could not get and why.
- After a batch, `python -m agent.corpus_check` rebuilds `manifest.csv` and `GAPS.md` (leave that to the orchestrator when you are a parallel worker).
