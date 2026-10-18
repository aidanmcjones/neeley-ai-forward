# Earnings calls: Q&A deflection, new phrases, dropped metrics

Module: `agent/moat/case_calls.py`

**What it answers:** which analyst questions management avoided, which phrases appear for the first time in the latest call, which topics analysts stopped asking about, and which product lines or metrics a company stopped printing in its earnings materials.

## Call signatures

```python
from agent.moat.case_calls import call_qa, dropped_metrics

call_qa(ticker, quarters=4, flags=("deflection", "new_phrase", "never_asked"), grade_min="C", k=80) -> list[dict]
dropped_metrics(ticker, releases=6) -> list[dict]
```

`call_qa` returns `qa_pair` rows (sorted by `deflection_score`, highest first, at most `k`), up to 25 `new_phrase` rows for the latest call, and every `never_asked` row for the ticker. `dropped_metrics` returns `dropped_metric` rows. An unknown ticker returns `[]` from both.

## Fields

Every row: `ticker`, `kind`, `text` (verified sentence or table-row text, under 600 chars), `citation`, `url`, `locator`, `source_id`, `quote_grade`, `license`.

- `qa_pair`: `quarter`, `analyst`, `analyst_firm`, `speaker`, `firm`, `question`, `question_verified`, `question_locator`, `answer` (same as `text`), `answer_words`, `question_words`, `deflection_score` (0 to 1), `deflection_reasons` (list), `quotable` (grade A or B), `doc_id`, `page_no`, `role_source` (`qa_turns.csv` or `turns (heuristic role)`).
- `new_phrase`: `quarter`, `phrase`, `phrase_kind` (`capitalised` or `ngram`), `mentions`, `compared_against` (prior three call doc_ids), `quotable`, `doc_id`, `page_no`. `text` is the first sentence in the latest call that uses the phrase.
- `never_asked`: `topic`, `quarters_asked`, `quarters_covered`, `recent_unasked_streak`, `flag`, `quarter` (last asked), `verify_status`, `source`. Cited to the `facts.locator` of `market/never_asked.csv`.
- `dropped_metric`: `series` (`earnings_release`, `earnings_slides` or `10-Q product sales`), `metric_kind` (`label` or `key_metric`), `label`, `last_seen`, `times_seen`, `releases_compared`, `missing_from`, `checked_against` (first doc_id of the latest release), `checked_against_all`. Cited to the last release page where the label appears.

## How it works

- One transcript per quarter: grade A, then B, then C (D only with `grade_min="D"`), superseded docs skipped. Ties prefer the doc covered by `qa_turns.csv`. Bloomberg docs are used and keep `license="bloomberg_licensed"`: cite, never copy their text into a public artifact.
- Turns come from `data/moat/verified/calls/qa_turns.csv` (analyst vs executive labels) when it covers the chosen doc, else from the index `turns` table with heuristic roles (known names from `qa_turns.csv`, firm words, a trailing question mark).
- Each analyst question is paired with the executive turns that follow it. Deflection score adds: quantitative question (number, guidance, how much, timing, when) with no number in the answer (0.35); deflection phrases such as "not going to comment", "we don't guide", "stay tuned", "too early" (0.2 each, up to 0.4); answer under 60% of the question's length (0.15); under 15% overlap with the question's content words (0.2).
- The answer sentence shown is the run of sentences that verifies on one page with `cite.verify_quote`, starting at the deflection phrase when there is one.
- New phrases: capitalised phrases and repeated content bigrams or trigrams from the latest call (analyst questions removed, speaker and firm names, months and stop words excluded) that appear in none of the prior three calls.
- Dropped metrics: each series is compared only with itself. Labels come from lines followed by a figure, markdown table rows, and "<Name> Sales Were $X" lines; key-metric words (gross-to-net, NBRx, TRx, market share, patients on therapy, ex-U.S., constant currency, and similar) are checked by presence. A label is reported only if it appears in at least 2 earlier releases, is absent from the latest two as a parsed line, and its text (minus a trailing geography) appears nowhere in the latest two releases. A series is skipped when the latest releases parse to under half the earlier median label count (a format change, not a drop).

## Data sources and limits

- Citation index `docs`, `pages`, `turns`, `facts` (read only). 167 `earnings_release` docs cover 14 tickers; `earnings_slides` cover 12; 10-Qs cover US filers only.
- Grade C transcripts are single third-party sources: speaker names and drug names can be misspelled, which shows up as false new phrases. Check `quote_grade` before quoting.
- Some corpus transcripts are a single file page, so `citation` reads "file page 1 (no printed page number)".

## CLI example

```
PYTHONPATH=. python -m agent.moat.case_calls MRK -k 2
[qa_pair] 2025Q3 grade=A score=0.95 Courtney Breen -> Rob Davis  <MRK:transcripts/2025Q3_transcript.md#p14>
[new_phrase] 2026Q2 grade=A phrase='LIPFENDRA' x13  <MRK:transcripts/2026Q2_transcript.md#p3>
[never_asked] 2025Q2 grade=- topic=IRA_negotiation streak=4  <fact:market/never_asked.csv#65>

PYTHONPATH=. python -m agent.moat.case_calls MRK --dropped
[earnings_release/label] 'Pifeltro' last seen 2026-02-03 (x3), missing from ['2026-04-30', '2026-08-04']  <MRK:earnings/2026-02-03_tm264564d1_ex99-1.md#p1>
```

## Known gaps

- Deflection and new-phrase flags are heuristics. Read the cited page before calling an answer evasive.
- Heuristic roles (docs without `qa_turns.csv` coverage, such as Bloomberg PDFs) can mispair a question with a closing remark.
- Dropped labels include one-off line items (charges, guidance rows) and labels printed only in fourth-quarter releases (full-year tables), as well as true product or metric drops. A label renamed in the latest releases is filtered only when the old name survives as a substring.
- 10-Q sales pages are found by keyword and label count, so a 10-Q whose product table layout changes may be skipped.
