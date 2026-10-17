# Citation plumbing

Hard requirement: every number and quote the model outputs carries an in-text marker and a footnote that is clickable and resolves to the exact source page. Code lives in `agent/needle/cite/`; tests in `tests/needle/test_cite.py`. No API calls are made anywhere in the package.

## What comes from the shared index and what is new

One index, one verifier. The canonical index is the scraper's `data/moat/index/citations.sqlite` (tables docs, pages, facts, turns, meta; page id convention `doc_id#p<page_no>`, page_no = first number of `[[page N | printed M]]`). `agent/moat/cite.py`, `agent/moat/index.py` (the builder) and `tests/moat/test_cite.py` are copied verbatim from data-moat commit `704741d`, with two changes: `cite.DB` resolves from env `CITATIONS_DB`, else the repo-local file, else the gap-data worktree copy (the sqlite is gitignored); and two data-tree tests skip when `data/moat` is absent. The sqlite is read through `agent.moat.cite` only.

From `agent/moat/cite.py` (not reimplemented): `db()`, `label(row)` (the `doc_title`, e.g. "Merck 10-K FY2025"), `where(row, page_no, printed)` (the location string: "p. 58", "Item 1A", "section <title>", "PDF p. 3", "file page N (no printed page number)"), `get_page()` (page text), `cite()`, and `verify_quote()` (rung 2 of the ladder). `search_pages` / `search_facts` are available for retrieval and feed `build_cited_request`.

Written here (`agent/needle/cite/`): `index.py` (adapter only: alias resolution for the 4 documents stored under both id schemes, doc_type vocabulary, `location()`; no second index), `locator.py` (Citation, Claim, Verification), `deeplink.py`, `viewer.py`, `verify.py` (ladder rungs 1, 3, 4, the number guard, value parsing, gate), `render.py`, `llm.py`. Tests: `tests/needle/test_cite.py` (23 tests on a synthetic sqlite with the same schema, plus one on the real index).

`load_index(db_path=None)` is cached. Because `agent.moat.cite` holds one global DB path, the adapter re-points it before every query; `CITATIONS_DB` or `load_index(path)` selects the sqlite. Both id schemes resolve: `NVO:6k/2025-08-06_caq22025.md` (corpus path, canonical) and `NVO:companies/NVO/6k/2025-08-06_0001628280-25-038087.md` (moat) are the same record.

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
  viewer_link        /viewer?doc=<canonical_id>&page=<n>&q=<quote>
  verification       {status: exact|substring|fuzzy|number_match|unverified, score 0..1, checked_at, detail}
  confidence_note    why a citation failed or what was approximated
Claim(text, citations)
```
`Citation.to_dict()` / `Citation.from_dict()` round trip through JSON.

## Verification ladder (`verify.py`)

1. exact: quote is a byte substring of the cited page (score 1.0).
2. substring: `agent.moat.cite.verify_quote` (equal after NFKC, smart quotes and dashes, case, whitespace; `agent.findings._norm`) (0.98).
3. fuzzy: `rapidfuzz.fuzz.partial_ratio >= 90` (score = ratio/100; difflib fallback if rapidfuzz is missing). 90 because markdown-conversion noise scores 93-99 and real paraphrases 60-80; there is no published threshold. Guard: every numeral in the quote must appear in the matched page span, since one altered digit in a long quote still scores about 98.
4. number_match: for `claim_type="number"`, the emitted value (parentheses = negative, percent, thousand/million/billion, table-header scale) is found among the numbers on the cited page although the quote did not verify (score 0.6).
5. else unverified. A note says if the quote is on another page ("quote is on page 2, not page 3"). Wrong pages are never silently corrected.

For number claims whose quote does verify, the value must also appear in the matched span, else the citation is unverified (quote right, number wrong). Shared: `verify_quote`, `_norm`, `_numbers`. Mine: exact rung and char span, fuzzy rung and number guard, value parsing and unit normalization, `number_match`, the gate. Not used: `findings.verify()` (needs a per-ticker docs dict) and its transcript speaker rule (see gaps).

## Gate

`gate(claims) -> (passed, rejected)`. A claim passes only if at least one citation is not `unverified`; passed claims keep only their verified citations. Claims with no citations are rejected.

## Deep links (`deeplink.py`)

Branches on `docs.source_url`, raw `doc_type`, `page_scheme` and `license`. EDGAR has no page anchors, so file page and printed folio live in the footnote and the viewer link.

| Source | Rule | Real example |
|---|---|---|
| SEC filings (annual, quarterly, 8-K, 6-K, earnings release, EDGAR press release) | EDGAR primary htm + `#:~:text=` + first 8 words of the quote, percent-encoded (`-` `,` `&` too). Chrome/Edge honor it; Safari lands at the top. No quote: plain URL | `https://www.sec.gov/Archives/edgar/data/310158/000031015826000063/mrk-20251231.htm#:~:text=direct%2Dto%2Dpatient%20program%20at%20affordable%20prices%20for%20the%20US` |
| sec_comment_letter | `.htm`: text fragment. `.pdf`: `#page=N` (PDF page) | `https://www.sec.gov/Archives/edgar/data/310158/000000000025003816/filename1.pdf#page=2` |
| CMS, White House, Federal Register and other PDFs | url + `#page=N` | `https://www.cms.gov/files/document/fact-sheet-medicare-selected-drug-negotiation-list-ipay-2026.pdf#page=2` |
| fda_label | DailyMed setid page, plain. No `#section-N` (anchors are unstable across versions); the section title is in the footnote | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=608d4f0d-b19f-46d3-749a-7159aa5f933d` |
| fda_label_version | the stored URL is a getFile zip; link the history page instead | `https://dailymed.nlm.nih.gov/dailymed/history.cfm?setid=8baba4ea-2855-42fa-9bd9-5a7548d4cec3` |
| transcript (third-party page) | plain page; footnote shows speaker and quote | fool.com call transcript URL |
| Bloomberg (`license = bloomberg_licensed`), LSEG Grade A PDFs in `verified/calls/src/`, anything without an http URL, R2 keys | no deep link, viewer route only | |
| facts rows | `fact_link(source)`: http sources (cms.gov, data.medicaid.gov) link directly; R2 keys and WRDS ids use the local route | |

Text fragments cannot be validated by curl or server side: the browser matches them and silently skips the highlight on a miss. Smoke test (read-only `curl -sI`, SEC user agent): EDGAR htm x3 (MRK, PFE, LLY 10-K/10-Q base URLs) 200; SEC comment letter PDF 200; Novo IR PDF 200; DailyMed setid 200; the AstraZeneca IR PDF returned 403 to a script user agent.

Viewer link: `/viewer?doc=<canonical_id>&page=<n>&q=<urlencoded quote, first 400 chars>`; it is the only route for licensed text. `viewer.render_viewer(doc, page, q, db_path=None, public=False)` returns HTML and refuses licensed documents when `public=True`; the module docstring shows the Streamlit call. There is no public page viewer and R2 is private, so the route stays local.

## Render

`render_markdown(claims)`: `claim text[1][2]` in order of first appearance, then

```
[n] <doc_title>, p. <folio> (file page <page>) -- "<quote>" -- [open](deep_link) · [viewer](viewer_link) · verified: <status>
```
The page text is the moat `where()` string (`Citation.location`): `p. 58`, `Item 1A`, `section <title>`, `PDF p. 3`, or `file page N (no printed page number)`; `(file page N)` is appended when absent. `render_markdown(claims, public=True)` withholds quote text and the viewer link of licensed (Bloomberg) citations; transcript footnotes show `speaker: quote`. `render_html` uses `<sup><a href="#fn-n">[n]</a></sup>` and `<li id="fn-n">`. Identical citations (same document, page, normalized quote) share one number.

## API pattern (`llm.py`)

- `build_cited_request(system, question, pages)` returns a Messages API body: one `search_result` block per page (`source` = viewer link, `title` = "<doc_title> p. <folio>", content = one text block per paragraph, `citations: {enabled: true}`), `cache_control: ephemeral` on the last block, `temperature: 0`, and `CITATION_SYSTEM_RULE` appended to the system prompt.
- `parse_cited_response(response_json, index, pages=None, documents=None)` turns every `text` block into a `Claim` and each `search_result_location` / `char_location` / `page_location` into a verified `Citation`. The page number comes from our own `source`, never from model output. With `strict_numbers=True` a claim containing a number absent from all its cited texts is downgraded to unverified (years are ignored).
- Citations cannot be combined with structured outputs (`output_config.format` returns 400). If JSON is needed, do a second, non-cited call on the verified claims and carry `cite_id`s through.
- Citations must be enabled on all or none of a request's blocks.

## Still missing

- A public host for the viewer (hard blocker for external readers). The app serves only local files; R2 is private and stores moat docs as gzip (`moat/<rel>.gz`); the corpus is not in R2. A deployed app needs the data or a signed-URL proxy.
- EDGAR iXBRL fact anchors (`ix.xhtml?doc=...#fact-identifier-N`) are not generated; derived numbers (ratios, z-scores) cite only the filing page of the base figure, not the XBRL concept and accession.
- Text-fragment hit rate on SEC HTML is unmeasured.
- Transcript speaker rule (`findings.verify`) and the fool.com takeaway exclusion are not applied here.
- Facts rows (`search_facts`) are not Citations yet: they link via `fact_link` only; `page_scheme = none` documents (tables, drug reference data) have no pages.
- The index contract is frozen at 704741d until the scraper's Sunday freeze; re-copy `agent/moat/cite.py` if it changes.
- Not live-tested against the Anthropic API (no key); the response shapes follow the documented fields. If the API joins multi-block `cited_text` without whitespace, the fuzzy rung absorbs it.
- 2 indexed paths are listed in manifests but absent on disk (`DocRecord.exists()` is False).
