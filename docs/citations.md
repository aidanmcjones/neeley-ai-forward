# Citation plumbing

Hard requirement: every number and quote the model outputs carries an in-text marker and a footnote that is clickable and resolves to the exact source page. Code lives in `agent/needle/cite/`; tests in `tests/needle/test_cite.py`. No API calls are made anywhere in the package.

## What comes from the shared index and what is new

One index, one verifier. The canonical index is the scraper's `data/moat/index/citations.sqlite` (tables docs, pages, facts, turns, meta; page id convention `doc_id#p<page_no>`, page_no = first number of `[[page N | printed M]]`). `agent/moat/cite.py`, `agent/moat/index.py` (the builder) and `tests/moat/test_cite.py` are copied verbatim from data-moat commit `704741d`, with two changes: `cite.DB` resolves from env `CITATIONS_DB`, else the repo-local file, else the gap-data worktree copy (the sqlite is gitignored); and two data-tree tests skip when `data/moat` is absent. The sqlite is read through `agent.moat.cite` only.

From `agent/moat/cite.py` (not reimplemented): `db()`, `label(row)` (the `doc_title`, e.g. "Merck 10-K FY2025"), `where(row, page_no, printed)` (the location string: "p. 58", "Item 1A", "section <title>", "PDF p. 3", "file page N (no printed page number)"), `get_page()` (page text), `cite()`, and `verify_quote()` (rung 2 of the ladder). `search_pages` / `search_facts` are available for retrieval and feed `build_cited_request`.

Written here (`agent/needle/cite/`): `index.py` (adapter only: alias resolution for the documents stored under both id schemes, corpus-style <-> moat-style id fallback, doc_type vocabulary, `location()`; no second index), `locator.py` (Citation, Claim, Verification), `numbers.py` (the one number tokenizer), `deeplink.py`, `viewer.py`, `viewer_server.py`, `verify.py` (the ladder and the old per-claim gate), `gate.py` (the per-number gate), `facts.py` (facts status whitelist), `render.py`, `llm.py`. Tests: `tests/needle/test_cite.py` and `tests/needle/test_gate.py` (synthetic sqlite with the same schema, every adversarial case from review C, plus real-index checks that skip without the data). Wiring into the quant writers: `docs/gate_wiring.md`.

`load_index(db_path=None)` is cached. Because `agent.moat.cite` holds one global DB path, the adapter re-points it before every query; `CITATIONS_DB` or `load_index(path)` selects the sqlite. Both id schemes resolve: `NVO:6k/2025-08-06_caq22025.md` (corpus path, canonical) and `NVO:companies/NVO/6k/2025-08-06_0001628280-25-038087.md` (moat) are the same record. When no record has the exact id, `resolve()` tries the other scheme (`VRTX:10k_FY2024.md` -> `VRTX:companies/VRTX/10k_FY2024.md` and back), then a unique suffix among the ticker's records (review D13: VRTX detectors used the corpus form while VRTX is indexed only under the moat form, so all 29 rows were withheld).

## The contract

```
Citation
  cite_id            stable hash of (canonical_id, page, normalized quote)
  canonical_id, ticker, doc_type (10-K|10-Q|20-F|8-K|call transcript|label|proxy|comment letter|press|other)
  doc_title          "MRK 10-K FY2025", "MRK 10-Q 2023-05-05"
  period
  location           moat.where() string: "p. 58", "Item 1A", "section Warnings", "PDF p. 3"
  speaker, raw_doc_type, page_scheme, license   (transcripts; drive deep-link rules; license gates public output)
  page               file page (the [[page N]] marker; what the verifier checks)
  folio              printed page (pages.printed), verbatim: "58", "?", "Item 1A"
  char_start/char_end span of the quote inside the page text (None until located)
  quote              verbatim text from that page
  claim_type         quote | number | paraphrase
  value, unit        the number as emitted ("29,482", "USD millions"), for number claims
  source_url         whole-document URL from the manifest
  deep_link          see below ("" if the document has no http source)
  viewer_link        <VIEWER_BASE>/viewer?doc=<canonical_id>&page=<n>&q=<quote>
  verification       {status: exact|substring|fuzzy|number_match|unverified, score 0..1, checked_at, detail}
  confidence_note    why a citation failed or what was approximated
Claim(text, citations, derived=None, assumptions=None)   (derived / assumptions: gate.py shapes)
```
`Citation.to_dict()` / `Citation.from_dict()` round trip through JSON.

## Verification ladder (`verify.py`)

1. exact: quote is a byte substring of the cited page after zero-width characters are removed (score 1.0).
2. substring: equal after NFKC, smart quotes and dashes, case, whitespace (the `agent.findings._norm` / `verify_quote` rule) plus zero-width stripping (0.98).
3. fuzzy: `rapidfuzz.fuzz.partial_ratio >= 90` (score = ratio/100; difflib fallback). 90 because markdown-conversion noise scores 93-99 and real paraphrases 60-80; there is no published threshold. Two guards (review C8): the quote's numerals must appear in the same order as a contiguous run of the matched span's numerals (a set test let "$18 million ... 29,482 percent" through), and no direction word or negation may change count between quote and span (`DIRECTION_PAIRS`: increase/decrease, rose/fell, up/down, higher/lower, gain/loss, grew/declined, above/below, more/less, positive/negative, favorable/unfavorable, ...; `NEGATIONS`: not, no, never, without, ...).
4. number_match: `claim_type="number"` with a NON-EMPTY quote that did not verify, and the emitted value is on the page with the same sign and the same scale (score 0.6). The footnote then shows the page text around the number, never the unverified quote, and the note records the model's quote.
5. else unverified. Notes say if the quote is on another page ("quote is on page 2, not page 3") or straddles the previous page break ("quote spans pages 1-2; cite page 1"). Wrong pages are never silently corrected.

Extra rules (review C7, C9, C10, C13):
- Numbers (`numbers.py`): commas dropped, parentheses or a leading minus = negative, `%`/percent, pts, bps, x, currency, scale words (thousand, million, billion, bn, mn, mm, glued `$319M`). A page number uses its inline scale, else the scale the page declares before it ("(in millions)", "USD millions", "$ in thousands"), else 1. So "15,144" under "(in millions)" supports "15.144 billion" and never "15,144 thousand"; "2,025 employees" never supports "$2.025 billion"; "($183)" never supports +183. A claim may round the source to its own printed precision ("$1,937.9M" from "$1,937,912,000"), never the reverse.
- Short quotes (< 12 characters or < 3 tokens) verify at most as substring and only at a token boundary: "8" never matches inside "$29,482".
- Zero-width space, ZWNJ, ZWJ, word joiner, BOM and soft hyphen are removed before matching (a ZWSP between two letters counts as a space); spans map back to the raw page.
- A quote that runs past the end of page N is tried on page N + page N+1 joined; a hit keeps its status with the note "spans pages N-N+1".
- For number claims whose quote verifies, the value must also be in the matched span, else unverified (quote right, number wrong).

## Gates

`verify.gate(claims) -> (passed, rejected)` is the old per-claim check (one verified citation passes the claim). It is kept for compatibility but does not enforce the rule: one verified quote cleared any number of invented numbers (review C6). Use the numeric gate.

`gate.numeric_gate(text_blocks, claims, derived=None, assumptions=None) -> GateResult` tokenizes every number in every text block (sentence, impact math, peer comparison, table cell, formula line) and classifies each:
- verified: on the quote, the verified value+unit, or the page text of a citation whose status is exact, substring, fuzzy or number_match (scale and sign aware). Unverified citations support nothing.
- derived: matches a `derived` entry whose expression re-computes from supported operands (passing citations carrying the operand, labelled assumptions, or other derived entries) within 0.5% relative or the printed precision, whichever is larger.
- assumed: matches an `assumptions` entry with a non-empty label. In a block named like a formula (formula, math, impact) bare 0, 1 and 100 are arithmetic constants.
- unsupported: everything else, with a reason.

Not counted (documented in `numbers.py`): bare years 1900-2099 (a year with a unit, "2030 million", is a number), dates, period labels (Q2 2026, FY2025, CY2025Q2I), form names (10-K), page / item / note / section numbers, ids and hashes, footnote markers and URLs.

The `numeric_check` field every gated record and document carries:

```
numeric_check = {status: passed | failed | unchecked, checked, total, verified, derived, assumed,
                 unsupported: [{value, where, reason}]}
```
`passed` only when `unsupported` is empty; `unchecked` when there was no text (not shown either). `where` is `<field>@<char offset>`. Fail closed: an exception while checking a number marks it unsupported with reason "gate error: ...". `gate_record(record, text_fields, citation_field)` returns `(record + numeric_check, passed)` for findings dicts (dotted fields such as `impact.formula`; `derived` / `assumptions` read from the record). `gate_document(sections)` gates decide and product documents per claim or per cell and returns `{passed, numeric_check (document level), items, failed}`.

Facts rows (`facts.py`, review C4): `fact_status_grade(verify_status)` whitelists verified / corrected / fixed / yes / True / match / matches page as exact-equivalent (1.0); `no_verified_copy` is machine data (0.6, number_match only when the value is re-read from the row); `unverified_onboard` and `unchecked` are "unverified (not checked)"; any other value is unverified.

## Deep links (`deeplink.py`)

Branches on `docs.source_url`, raw `doc_type`, `page_scheme` and `license`. EDGAR has no page anchors, so file page and printed folio live in the footnote and the viewer link.

| Source | Rule | Real example |
|---|---|---|
| SEC filings (annual, quarterly, 8-K, 6-K, earnings release, EDGAR press release) | EDGAR primary htm + `#:~:text=` + a run of 4-8 consecutive words of the verified span that sits inside ONE block of the stored page text (a line, split at table pipes; no leading bullet), percent-encoded (`-` `,` `&` too). No such run, no page text or no quote: plain URL and a note (review D5: runs that crossed table cells never matched). Chrome/Edge honor it; Safari lands at the top | `https://www.sec.gov/Archives/edgar/data/310158/000031015826000063/mrk-20251231.htm#:~:text=direct%2Dto%2Dpatient%20program%20at%20affordable%20prices%20for%20the%20US` |
| sec_comment_letter | `.htm`: text fragment. `.pdf`: `#page=N` (PDF page) | `https://www.sec.gov/Archives/edgar/data/310158/000000000025003816/filename1.pdf#page=2` |
| CMS, White House, Federal Register and other PDFs | url + `#page=N` where N is the index page_no. Basis: page_scheme `pdf_page` is the PDF page by construction; `marker` PDFs carry one marker per PDF page and excerpts keep the original numbering (BMY pricing_report_2025.md = pages 35-39 of the Impact Report). `section` / `none` (e.g. the ASPE costs excerpt) have no PDF page: plain URL and a note | `https://www.cms.gov/files/document/fact-sheet-medicare-selected-drug-negotiation-list-ipay-2026.pdf#page=2` |
| fda_label | DailyMed setid page, plain. No `#section-N` (anchors are unstable across versions); the section title is in the footnote | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=608d4f0d-b19f-46d3-749a-7159aa5f933d` |
| fda_label_version | the stored URL is a getFile zip; link the history page instead | `https://dailymed.nlm.nih.gov/dailymed/history.cfm?setid=8baba4ea-2855-42fa-9bd9-5a7548d4cec3` |
| transcript (third-party page) | plain page; footnote shows speaker and quote | fool.com call transcript URL |
| Bloomberg (`license = bloomberg_licensed`), LSEG Grade A PDFs in `verified/calls/src/`, anything without an http URL, R2 keys | no deep link, viewer route only | |
| facts rows | `fact_link(source)`: http sources (cms.gov, data.medicaid.gov) link directly; R2 keys and WRDS ids use the local route | |

Fragments are validated against the converted page text, not the live HTML, so the viewer link stays the guaranteed route. Smoke test (read-only `curl -sI`, SEC user agent): EDGAR htm x3 (MRK, PFE, LLY 10-K/10-Q base URLs) 200; SEC comment letter PDF 200; Novo IR PDF 200; DailyMed setid 200; the AstraZeneca IR PDF returned 403 to a script user agent.

Viewer link: `<VIEWER_BASE>/viewer?doc=<canonical_id>&page=<n>&q=<urlencoded quote, first 400 chars>`, with env `VIEWER_BASE` defaulting to `http://127.0.0.1:8765` (set it to "" for the relative form). It is the only route for licensed text. `viewer.render_viewer(doc, page, q, db_path=None, public=False)` returns HTML and refuses licensed documents when `public=True`. `python -m agent.needle.cite.viewer_server --port 8765 [--db PATH] [--public]` serves `GET /viewer` with the standard library only (review D6). The UI session may mount the same handler in `ui/server.py`: `viewer_server.viewer_response(query_string, db_path, public)` returns `(status, content_type, body)`. There is no public host yet and R2 is private, so the route stays local.

## Render

`render_markdown(claims, public=False, index=None)` / `render_html(...)` place markers per number (review D2, D15, C18), using the numeric gate's classification of each claim's text:

```
Keytruda sales were $29,482 million[1] and gross margin was 71.5%[2]; share 45.9%[derived: 1, 3] at a base rate of 0.65%[assumption].
```
When every number in a claim shares one citation, a single `[n]` goes after the clause. Citations that carry no number, and claims with no numbers, keep end-of-claim markers. Unsupported numbers get no marker (the gate stops them first). Footnotes:

```
[n] <doc_title>, <location> (file page <page>) -- "<quote>" -- [open](deep_link) · [viewer](viewer_link) · verified: <status>
```
The location is the moat `where()` string; "(file page N)" is added only when the page is known, so facts, XBRL and derived citations print no "file page None". Quotes are verbatim (double quotes kept). `public=True` (on every entry point) withholds quote text and the viewer link of licensed citations; transcript footnotes show `speaker: quote`. `render_html` uses `<sup><a href="#fn-n">[n]</a></sup>` and `<li id="fn-n">`. Identical citations share one number; operand citations of derived numbers are numbered too.

## API pattern (`llm.py`)

- `build_cited_request(system, question, pages)` returns a Messages API body: one `search_result` block per page (`source` = viewer link, `title` = "<doc_title> p. <folio>", content = one text block per paragraph, `citations: {enabled: true}`), `cache_control: ephemeral` on the last block, and `CITATION_SYSTEM_RULE` appended to the system field. No `temperature` unless passed (Claude Opus 5.5 returns 400 on sampling parameters, review C11).
- `parse_cited_response(response_json, index, pages=None, documents=None)` turns every `text` block into a `Claim` and each `search_result_location` / `char_location` / `page_location` into a verified `Citation`. The page number comes from our own `source`, never from model output. With `strict_numbers=True` the numeric gate runs on each claim against the cited_text of citations that PASSED local verification only (review C12); any unsupported number downgrades all the claim's citations. Bare years are ignored, "2030 million" is a number. Refusal, error and empty responses return no claims (or one uncited `fallback_text` claim); a `max_tokens` response drops its last text block.
- Citations cannot be combined with structured outputs (`output_config.format` returns 400). If JSON is needed, do a second, non-cited call on the verified claims and carry `cite_id`s through.
- Citations must be enabled on all or none of a request's blocks.

## Still missing

- Wiring the numeric gate into run.py / find.py / decide_cli.py / product_cli.py and data.py's status whitelist: see `docs/gate_wiring.md`.
- A public host for the viewer (hard blocker for external readers). `viewer_server.py` serves it locally. The app serves only local files; R2 is private and stores moat docs as gzip (`moat/<rel>.gz`); the corpus is not in R2. A deployed app needs the data or a signed-URL proxy.
- EDGAR iXBRL fact anchors (`ix.xhtml?doc=...#fact-identifier-N`) are not generated; derived numbers (ratios, z-scores) cite only the filing page of the base figure, not the XBRL concept and accession.
- Text-fragment hit rate on live SEC HTML is unmeasured (fragments are validated against the converted page text).
- Facts rows (`search_facts`) are not Citations yet: they link via `fact_link` only; `page_scheme = none` documents (tables, drug reference data) have no pages.
- The index contract is frozen at 704741d until the scraper's Sunday freeze; re-copy `agent/moat/cite.py` if it changes.
- Not live-tested against the Anthropic API (no key); the response shapes follow the documented fields. If the API joins multi-block `cited_text` without whitespace, the fuzzy rung absorbs it.
- 2 indexed paths are listed in manifests but absent on disk (`DocRecord.exists()` is False).
