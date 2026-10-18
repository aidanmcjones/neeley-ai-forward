# Citation index

The case rule is "Every finding needs a citation... Check everything against the source." This index makes that rule mechanical. Every number or quote an AI output shows should come back from here as a document plus printed page, or as a verified table row plus its source.
Retrieval helpers built on this index (risk-factor drift, gross-to-net, working capital, segments, footnotes, calls, labels, forces) are documented in `docs/research/case_retrieval.md`.


- Build: `python -m agent.moat.index` (about 8 seconds). Add `--upload` to gzip it and put it to R2 at `moat/index/citations.sqlite.gz`.
- File: `data/moat/index/citations.sqlite`, 329 MB (84.6 MB gzipped). It is gitignored. Fetch it from R2 with `agent.tenk.Store().get("moat/index/citations.sqlite.gz")` and gunzip.
- Query: `agent/moat/cite.py` (Python API and CLI).
- Tests: `tests/moat/test_cite.py` (10 checks, no API key needed).

## What is in it (build of 2026-10-17)

| Stream | Docs | Pages |
|---|---|---|
| corpus (Parker's `data/corpus`) | 881 | 16,185 |
| secx | 1,193 | 8,787 |
| filings | 134 | 8,295 |
| product (label versions) | 717 | 3,059 |
| policy | 52 | 1,912 |
| calls | 65 | 1,340 |
| verify_calls (official LSEG PDFs) | 17 | 213 |
| bloomberg (licensed PDFs) | 5 | 114 |
| pricing, ibes, market, verify_* tables and notes | 54 | 35 |
| **Total** | **3,118** | **39,940** |

There are 69,553 facts: calls 7,706, filings 1,276, market 2,917, policy 468, pricing 1,016 (verified copies only), product 7,787, secx 500, and IBES plus daily prices 47,883. The index also holds 8,540 speaker turns.

## Schema

**docs**: one row per document or table in `data/corpus/manifest.csv`, `manifest.jsonl` and `*/*/sources.jsonl`, all `data/moat/manifests/*.jsonl`, the Bloomberg inbox PDFs, and any `data/moat/verified/*/*.md` note that no manifest lists. If a doc_id appears more than once, the later row wins, so `verify_*` manifests override the collector ones.

Columns: `doc_id, ticker, company, group, doc_type, form, period, filed, source_quality, source_url, path, stream, quote_grade, superseded_by, license, drug, n_pages, page_scheme, notes`.

- `page_scheme` is one of:
  - `marker`: `[[page N | printed M]]` markers in the file.
  - `section`: FDA labels with no markers. There is one page per heading, and printed is the heading, such as "5.2 Bleeding".
  - `pdf_page`: one page per PDF page. Printed is the PDF page number.
  - `none`: CSV tables and one HTML file.
- `superseded_by` is set in two cases:
  - The mislabeled AZN corpus transcript (`AZN:transcripts/2026Q1_transcript.md`, which is really the Q2 call) points to the moat Q1 copy.
  - Each raw `data/moat/tables/*.csv` that has a verified copy of the same name points to that verified doc.
- `license = 'bloomberg_licensed'` marks the Bloomberg PDFs.

**pages**: `id, doc_id, page_no, printed, char_start, char_end, speakers, text`.
- `page_no` is the first number in the marker, the same number NEEDLE uses. So `f"{doc_id}#p{page_no}"` is exactly the source id that `agent.findings.verify()` and `agent/needle/pages.py` accept.
- `char_start` and `char_end` are offsets into the source file text. For PDFs they are offsets into the concatenated page text.
- `speakers` lists the speakers whose turns start on that page.

**turns**: `doc_id, page_no, turn_no, speaker, char_start`. Turns are detected three ways:
- Markdown transcripts: `**Name:**` lines.
- Bloomberg PDFs: the participant roster plus `Q - ` and `A - ` lines.
- LSEG PDFs: `Name - Company - Title` lines.

**facts**: `id, table, doc_id, row_key, ticker, drug, period, field, value, unit, source, source_row, verify_status, row_json, text`. There is one row per CSV row of:
- every `data/moat/verified/*/*.csv`, with `verify_status` taken from the row, or `verified` when the row has none;
- `data/moat/tables/ibes_*.csv` and `prices_daily.csv`, with `verify_status = no_verified_copy`.

`field` and `value` hold the table's headline column, picked by heuristic (for example `ira_share_of_total_revenue_pct`). `row_json` holds every column. `text` is the row rendered as "table: col = value; ..." for full-text search.

The raw pricing tables in `data/moat/tables` are **not** indexed. They mix units: 31 rows use the wrong Part B code, and the MFP is averaged across units. Only `verified/pricing/*` is used. The raw files would come back, flagged `unverified`, only if `verified/pricing/` were missing at build time.

**pages_fts** and **facts_fts** are FTS5 tables (porter, unicode61) over `pages.text` and `facts.text`.

**meta** records build time, counts, the fact table list, the pricing source, and skipped docs.

## How to query

```python
from agent.moat.cite import search_pages, search_facts, get_page, cite, verify_quote

search_pages("Genmab royalty", ticker="JNJ", doc_type="annual_report", since="2025-01-01", grade_min="B", k=10)
# -> [{doc_id, page_no, printed, citation, url, snippet, quote_grade, license, score, source_id}, ...]
search_facts("ira_share_of_total_revenue_pct", ticker="AZN", table="force_summary")
get_page("JNJ:10k_FY2025.md", 8)             # full page row
cite("JNJ:10k_FY2025.md", 8)                 # ("Johnson & Johnson 10-K FY2025, p. 3", "https://www.sec.gov/...")
verify_quote("royalty amounts to Genmab were approximately $2.4 billion", "JNJ:10k_FY2025.md", 8)  # True
```

```
python -m agent.moat.cite "Keytruda royalty" --ticker MRK
python -m agent.moat.cite "Ozempic net price" --ticker NVO --grade A
python -m agent.moat.cite "IRA share" --facts --table force_summary
```

How a query string is handled:
- Plain words are joined with AND.
- If AND finds nothing, the search falls back to OR.
- FTS syntax (quotes, `OR`, `NEAR`, `*`) is passed through unchanged.
- Superseded docs are hidden unless you pass `include_superseded=True`.

`verify_quote` uses the same normalization as `agent.findings.verify()`: NFKC, curly quotes, dashes, whitespace and case. It is an exact substring match on the one cited page. It does not run verify()'s 20-character minimum or its speaker and figure checks. For findings, run `agent.findings.verify()` or `agent.needle.pages.check()` as well.

## Grade rules (transcripts)

`quote_grade` comes from `data/moat/verified/calls/transcript_grades.csv`, matched on both `path` and `quote_from`. Bloomberg PDFs are grade A.

| Grade | Meaning |
|---|---|
| A, B | Quotable |
| C | Needs a Bloomberg check before it goes in a findings table. Where a Bloomberg copy of the same call exists, `notes` names it. |
| D | Unquotable |

Using `grade_min`:
- `grade_min="B"` keeps A and B transcripts. It drops C, D and *ungraded* transcripts (mostly the peers), so an ungraded call never passes a quality filter by accident.
- Non-transcript docs are not affected by `grade_min`.

## Limits

- Bloomberg text is licensed. It is in the index so that quotes can be checked and cited. Never copy it into a public artifact, the app, or a slide. Cite it instead. The index file itself must stay private (R2 and local only).
- Some pages have no folio, such as 6-Ks, 8-K exhibits, cover pages, and GSK/SNY 20-Fs. Their citation reads "file page N (no printed page number)". Labels are cited by section. PDFs are cited by PDF page.
- `JNJ:verified/calls/src/JNJ_2026Q2_mb.html` is not page-indexed. The corpus `drug_reference_data` CSVs (209) are docs only, not facts.
- The fact `field`, `value`, `unit`, `period` and `source` columns are picked by heuristic per table. When precision matters, read `row_json`. Some tables carry their own status words in `verify_status` (`fixed`, `added`, `dropped`, `True`/`False`, `yes`/`no`). Treat `dropped` and `False` rows as rejected.
- Rank is plain BM25. A 10-K page and an SEC comment letter about the same topic can outrank each other. Filter by `doc_type` when you want filings only.
