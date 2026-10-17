"""Citation plumbing tests: offline, deterministic, synthetic data root (no dependency on the gitignored corpus)."""

import json
import sqlite3
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest

from agent.needle.cite import render, verify as V
from agent.needle.cite.deeplink import build_deep_link, build_viewer_link, fact_link, text_fragment
from agent.needle.cite.index import load_index
from agent.moat import cite as moat
from agent.findings import MARKER
from agent.needle.cite.llm import CITATION_SYSTEM_RULE, build_cited_request, parse_cited_response
from agent.needle.cite.locator import Citation, Claim
from agent.needle.cite.viewer import render_viewer

EDGAR = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/xyz-20251231.htm"
PDF = "https://www.sec.gov/Archives/edgar/data/1/000000000126000002/filename1.pdf"
DM = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc-123"
EXACT = ("Net sales of Keytruda were $29,482 million in 2025, an increase of 18 percent, driven by "
         "continued uptake across indications.")

K10 = f"""<!-- source: {EDGAR} -->
[[page 1 | printed ?]]
Cover page of the annual report. Nothing here.

[[page 2 | printed 41]]
Results of operations. {EXACT}

Other income was ($183) million lower.   Gross margin was 71.5% in 2025.

[[page 3 | printed Item 1A]]
Risk factors. Pricing pressure from IRA negotiation may reduce revenue materially in future years.
"""
LABEL = """<!-- source: x -->
## 5 WARNINGS AND PRECAUTIONS

### 5.1 Serious Infections

Patients treated with the drug are at increased risk for developing serious infections that may lead to death.
"""


SCHEMA = """CREATE TABLE docs (doc_id TEXT PRIMARY KEY, ticker TEXT, company TEXT, "group" TEXT, doc_type TEXT, form TEXT,
  period TEXT, filed TEXT, source_quality TEXT, source_url TEXT, path TEXT, stream TEXT, quote_grade TEXT,
  superseded_by TEXT, license TEXT, drug TEXT, n_pages INTEGER, page_scheme TEXT, notes TEXT);
CREATE TABLE pages (id INTEGER PRIMARY KEY, doc_id TEXT, page_no INTEGER, printed TEXT, char_start INTEGER,
  char_end INTEGER, speakers TEXT, text TEXT);"""


def _doc(con, doc_id, doc_type, url, path, text, form="", period="", filed="", scheme="marker", lic="", drug=""):
    con.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, "AAA", "AAA", "companies", doc_type, form, period, filed, "official", url, path, "", "", "", lic, drug,
                 0, scheme, ""))
    parts = MARKER.split(text)
    if len(parts) == 1:
        pages = [(1, "?", text)]
    else:
        pages = [(int(parts[i]), parts[i + 1].strip(), parts[i + 2]) for i in range(1, len(parts) - 2, 3)]
    for n, pr, t in pages:
        con.execute("INSERT INTO pages (doc_id,page_no,printed,text) VALUES (?,?,?,?)", (doc_id, n, pr, t))
    con.execute("UPDATE docs SET n_pages=? WHERE doc_id=?", (len(pages), doc_id))


@pytest.fixture(scope="module")
def root(tmp_path_factory):
    """A synthetic citations.sqlite with the scraper's schema (both id schemes, one overlapping document)."""
    f = tmp_path_factory.mktemp("idx") / "citations.sqlite"
    con = sqlite3.connect(f)
    con.executescript(SCHEMA)
    _doc(con, "AAA:10k_FY2025.md", "annual_report", EDGAR, "data/corpus/companies/AAA/10k_FY2025.md", K10, "10-K", "2025-12-31", "2026-02-20")
    _doc(con, "AAA:companies/AAA/10k_copy.md", "annual_report", EDGAR, "data/moat/companies/AAA/10k_copy.md", K10, "10-K", "2025-12-31", "2026-02-20")
    _doc(con, "AAA:companies/AAA/10q_2025Q1.md", "quarterly_report", "https://www.sec.gov/Archives/edgar/data/1/2/q.htm",
         "data/moat/companies/AAA/10q_2025Q1.md", "[[page 1 | printed 1]]\nQuarter text here is long enough to quote.\n", "10-Q", "2025-03-31", "2025-05-01")
    _doc(con, "drug:foo:label_sections.md", "fda_label", DM, "data/corpus/drugs/foo/label_sections.md", LABEL, scheme="section", drug="foo")
    _doc(con, "foo:drugs/foo/label_v2.md", "fda_label_version", DM.replace("drugInfo.cfm?setid=abc-123", "getFile.cfm?setid=abc-123&type=zip&version=2"),
         "data/moat/drugs/foo/label_v2.md", "[[page 1 | printed Warnings]]\nVersion two text for the label that is long enough.\n")
    _doc(con, "AAA:verified/calls/AAA_Q1_bbg.pdf", "transcript", "", "x", "[[page 1 | printed 3]]\nBloomberg licensed transcript text is long enough here.\n",
         scheme="pdf_page", lic="bloomberg_licensed")
    con.commit()
    con.close()
    return f


@pytest.fixture(scope="module", autouse=True)
def _restore_moat_db():
    """agent.moat.cite keeps one global DB path; put it back so other test modules see the real index."""
    old = moat.DB
    yield
    moat.DB = old
    moat.db.cache_clear()


@pytest.fixture(scope="module")
def idx(root):
    return load_index(root)


def cite(page=2, quote=EXACT, **kw):
    return Citation(canonical_id="AAA:10k_FY2025.md", page=page, quote=quote, **kw)


# ---------------------------------------------------------------- index
def test_both_id_schemes_resolve_to_one_record(idx):
    a, b = idx.resolve("AAA:10k_FY2025.md"), idx.resolve("AAA:companies/AAA/10k_copy.md")
    assert a is b and a.canonical_id == "AAA:10k_FY2025.md" and a.doc_type == "10-K"
    assert idx.canonical("AAA:companies/AAA/10k_copy.md") == "AAA:10k_FY2025.md"
    assert idx.resolve("AAA:companies/AAA/10q_2025Q1.md").doc_type == "10-Q"   # moat-only doc stays separate
    assert idx.resolve("nope") is None


def test_page_accessor_and_folios(idx):
    assert idx.get_page("AAA:10k_FY2025.md", 2)[:2] == (2, "41")
    assert idx.get_page("AAA:companies/AAA/10k_copy.md", 1)[1] == "?"      # alias resolves to the canonical doc
    assert idx.get_page("AAA:10k_FY2025.md", 3)[1] == "Item 1A"
    assert idx.get_page("AAA:10k_FY2025.md", 99) is None
    assert idx.location("AAA:10k_FY2025.md", 2) == "p. 41" and idx.location("AAA:10k_FY2025.md", 3) == "Item 1A"
    assert idx.location("AAA:10k_FY2025.md", 1).startswith("file page 1")
    assert idx.location("drug:foo:label_sections.md", 1).startswith("section")
    assert moat.cite("AAA:10k_FY2025.md", 2) == ("AAA 10-K FY2025, p. 41", EDGAR)   # shared moat function agrees
    assert idx.get_page("drug:foo:label_sections.md", 1)[0] == 1     # unpaged label = one page


@pytest.mark.skipif(not moat._GAP.exists(),
                    reason="real data not present")
def test_real_overlap_document_resolves_both_ways(root):
    from agent.needle.cite.index import load_index
    i = load_index(moat._GAP)
    a = i.resolve("NVO:6k/2025-08-06_caq22025.md")
    b = i.resolve("NVO:companies/NVO/6k/2025-08-06_0001628280-25-038087.md")
    assert a is not None and a is b and a.exists()
    assert i.get_page("MRK:companies/MRK/10q_2023Q1.md", 3) is not None
    assert i.get_page("MRK:10k_FY2025.md", 60)[1] == "58"


# ---------------------------------------------------------------- verify ladder
def test_exact(idx):
    c = V.verify(cite(), idx)
    v = c.verification
    assert v.status == "exact" and v.score == 1.0 and v.checked_at
    page_text = idx.get_page(c.canonical_id, 2)[2]
    assert page_text[c.char_start:c.char_end] == EXACT
    assert c.folio == "41" and c.location == "p. 41" and c.doc_title == "AAA 10-K FY2025" and c.source_url == EDGAR
    assert c.deep_link.startswith(EDGAR + "#:~:text=") and c.viewer_link.startswith("/viewer?doc=")


def test_substring_after_whitespace_and_quote_changes(idx):
    q = EXACT.replace(" ", "  ").replace("Net sales", "net\nsales")
    c = V.verify(cite(quote=q), idx)
    assert c.verification.status == "substring"
    assert idx.get_page(c.canonical_id, 2)[2][c.char_start:c.char_end].lower().startswith("net sales")


def test_fuzzy_slight_misquote(idx):
    q = EXACT.replace("continued uptake", "continuing uptake").replace("driven by", "driven by the")
    c = V.verify(cite(quote=q), idx)
    assert c.verification.status == "fuzzy" and 0.9 <= c.verification.score < 1


def test_fuzzy_refuses_altered_number(idx):
    q = EXACT.replace("$29,482", "$28,482")
    c = V.verify(cite(quote=q), idx)
    assert c.verification.status == "unverified" and "numbers differ" in c.confidence_note


def test_paraphrase_is_unverified(idx):
    c = V.verify(cite(quote="Revenue from the flagship oncology drug rose strongly last year because of new approvals."), idx)
    assert c.verification.status == "unverified"


def test_wrong_page(idx):
    c = V.verify(cite(page=3), idx)
    assert c.verification.status == "unverified" and "quote is on page 2, not page 3" in c.confidence_note
    assert V.verify(cite(page=99), idx).verification.status == "unverified"
    assert V.verify(Citation("AAA:missing.md", 1, EXACT), idx).verification.status == "unverified"


def test_number_claims(idx):
    ok = V.verify(cite(claim_type="number", value="29,482", unit="USD millions"), idx)
    assert ok.verification.status == "exact"
    bad = V.verify(cite(claim_type="number", value="29,842", unit="USD millions"), idx)
    assert bad.verification.status == "unverified" and "not on the cited page" in bad.confidence_note
    # quote absent but number on the page -> number_match
    nm = V.verify(cite(quote="", claim_type="number", value="29.482", unit="USD billions"), idx)
    assert nm.verification.status == "number_match" and nm.verification.score == 0.6
    # parentheses negative and percent
    assert V.verify(cite(quote="", claim_type="number", value="-183", unit="USD millions"), idx).verification.status == "number_match"
    assert V.verify(cite(quote="", claim_type="number", value="71.5", unit="percent"), idx).verification.status == "number_match"
    assert V.verify(cite(quote="", claim_type="number", value="71.5", unit="USD millions"), idx).verification.status == "unverified"
    assert V.verify(cite(quote="", claim_type="number", value="15", unit="USD billions"), idx).verification.status == "unverified"


def test_parse_numbers():
    n = V.parse_numbers("($1,234.5) million and 12%")
    assert n[0]["num"] == 1234.5 and n[0]["neg"] and n[0]["scale"] == 1e6 and n[1]["pct"]


# ---------------------------------------------------------------- gate
def test_gate(idx):
    good, bad = V.verify(cite(), idx), V.verify(cite(quote="Totally invented sentence about revenue doubling."), idx)
    claims = [Claim("A", [good]), Claim("B", [bad]), Claim("C", [bad, good]), Claim("D", [])]
    passed, rejected = V.gate(claims)
    assert [c.text for c in passed] == ["A", "C"] and [c.text for c in rejected] == ["B", "D"]
    assert all(x.verification.ok for c in passed for x in c.citations)


# ---------------------------------------------------------------- render
def test_render_links_and_dedupe(idx):
    a, b = V.verify(cite(), idx), V.verify(cite(quote=EXACT.upper()), idx)       # same evidence modulo case
    c = V.verify(Citation("AAA:10k_FY2025.md", 3, "Pricing pressure from IRA negotiation may reduce revenue materially"), idx)
    cl = [Claim("Keytruda sales were $29,482 million.", [a]), Claim("Margin held.", [b, c])]
    md = render.render_markdown(cl)
    assert "[1]" in md and "[2]" in md and "[3]" not in md
    assert "Keytruda sales were $29,482 million.[1]" in md and "Margin held.[1][2]" in md
    assert 'AAA 10-K FY2025, p. 41 (file page 2) -- "' in md and "AAA 10-K FY2025, Item 1A (file page 3)" in md
    assert "[open](https://www.sec.gov/" in md and "[viewer](/viewer?doc=" in md and "verified: exact" in md
    h = render.render_html(cl)
    assert '<sup><a href="#fn-1">[1]</a></sup>' in h and 'id="fn-2"' in h and 'href="/viewer?doc=' in h


def test_unknown_folio_reads_file_page(idx):
    c = V.verify(Citation("AAA:10k_FY2025.md", 1, "Cover page of the annual report. Nothing here."), idx)
    assert "AAA 10-K FY2025, file page 1 (no printed page number) --" in render.render_markdown([Claim("x", [c])])


# ---------------------------------------------------------------- deep links
def test_deep_links_by_source_type():
    q = "Net sales of Keytruda were $29,482 million in 2025, an increase of 18 percent, driven by continued uptake"
    e = build_deep_link(Citation("a", 2, q, source_url=EDGAR, raw_doc_type="annual_report"))
    assert e == EDGAR + "#:~:text=Net%20sales%20of%20Keytruda%20were%20%2429%2C482%20million%20in"
    assert text_fragment("short quote here") == "#:~:text=short%20quote%20here"
    assert text_fragment("direct-to-patient, a & b") == "#:~:text=direct%2Dto%2Dpatient%2C%20a%20%26%20b"
    assert text_fragment("") == "" and build_deep_link(Citation("a", 2, "", source_url=EDGAR)) == EDGAR
    # comment letters: htm -> fragment, pdf -> #page; gov pdf -> #page
    assert build_deep_link(Citation("a", 2, q, source_url=PDF, raw_doc_type="sec_comment_letter")) == PDF + "#page=2"
    assert build_deep_link(Citation("a", 2, q, source_url=EDGAR.replace("xyz-20251231", "filename1"), raw_doc_type="sec_comment_letter")).count("#:~:text=") == 1
    cms = "https://www.cms.gov/files/document/fact-sheet.pdf"
    assert build_deep_link(Citation("a", 7, q, source_url=cms, raw_doc_type="cms_fact_sheet", page_scheme="marker")) == cms + "#page=7"
    # DailyMed: setid page, never #section; versions -> history page
    assert build_deep_link(Citation("a", 1, q, source_url=DM, raw_doc_type="fda_label")) == DM
    ver = "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid=abc-123&type=zip&version=2"
    assert build_deep_link(Citation("a", 1, q, source_url=ver, raw_doc_type="fda_label_version")) == \
        "https://dailymed.nlm.nih.gov/dailymed/history.cfm?setid=abc-123"
    # transcripts: third-party page plain; licensed or no URL: viewer only
    fool = "https://www.fool.com/earnings/call-transcripts/2025/10/31/x/"
    assert build_deep_link(Citation("a", 1, q, source_url=fool, raw_doc_type="transcript")) == fool
    assert build_deep_link(Citation("a", 1, q, source_url=fool, license="bloomberg_licensed")) == ""
    assert build_deep_link(Citation("a", 1, q, source_url="")) == ""
    assert build_deep_link(Citation("a", 1, q, source_url="https://example.com/page")) == "https://example.com/page"
    assert fact_link("https://data.medicaid.gov/api/x") .startswith("https://data.medicaid") and fact_link("moat/tables/x.csv.gz") == ""
    v = build_viewer_link(Citation("AAA:x/y.md", 4, "a b & c"))
    qs = parse_qs(urlsplit(v).query)
    assert urlsplit(v).path == "/viewer" and qs == {"doc": ["AAA:x/y.md"], "page": ["4"], "q": ["a b & c"]}


def test_dailymed_label_citation_end_to_end(idx):
    c = V.verify(Citation("drug:foo:label_sections.md", 1, "Patients treated with the drug are at increased risk for developing serious infections that may lead to death."), idx)
    assert c.verification.status in ("exact", "substring") and c.deep_link == DM and c.location.startswith("section")
    v2 = V.verify(Citation("foo:drugs/foo/label_v2.md", 1, "Version two text for the label that is long enough."), idx)
    assert v2.deep_link.endswith("history.cfm?setid=abc-123") and "Warnings" in v2.location


def test_licensed_citation_is_viewer_only_and_withheld_when_public(idx):
    c = V.verify(Citation("AAA:verified/calls/AAA_Q1_bbg.pdf", 1, "Bloomberg licensed transcript text is long enough here."), idx)
    assert c.verification.ok and c.deep_link == "" and c.license == "bloomberg_licensed" and c.viewer_link
    team, pub = render.render_markdown([Claim("x", [c])]), render.render_markdown([Claim("x", [c])], public=True)
    assert "Bloomberg licensed transcript" in team and "Bloomberg licensed transcript" not in pub and "[viewer]" not in pub
    assert "Licensed source" in render_viewer(c.canonical_id, 1, "x", db_path=None, public=True)


def test_viewer_marks_quote(root):
    h = render_viewer("AAA:10k_FY2025.md", 2, EXACT, db_path=root)
    assert "<mark>Net sales of Keytruda" in h and "p. 41" in h
    assert "unavailable" in render_viewer("AAA:10k_FY2025.md", 50, "x", db_path=root)


# ---------------------------------------------------------------- llm
PAGES = [("AAA:10k_FY2025.md", 2, None, EDGAR), ("AAA:companies/AAA/10q_2025Q1.md", 1, "Quarter text here is long enough to quote.", "")]


def _pages(idx):
    return [(PAGES[0][0], 2, idx.get_page(PAGES[0][0], 2)[2], EDGAR), PAGES[1]]


def test_build_request(idx, monkeypatch):
    import agent.needle.cite.llm as L
    monkeypatch.setattr(L, "load_index", lambda *a, **k: idx)
    body = build_cited_request("You are an analyst.", "What were Keytruda sales?", _pages(idx))
    blocks = body["messages"][0]["content"]
    sr = [b for b in blocks if b["type"] == "search_result"]
    assert len(sr) == 2 and all(b["citations"] == {"enabled": True} for b in sr)
    assert sr[0]["title"] == "AAA 10-K FY2025 p. 41" and sr[0]["source"].startswith("/viewer?doc=AAA%3A10k_FY2025.md&page=2")
    assert "cache_control" in sr[-1] and "cache_control" not in sr[0]
    assert blocks[-1] == {"type": "text", "text": "What were Keytruda sales?"}
    assert "output_config" not in body and CITATION_SYSTEM_RULE in body["system"][0]["text"]
    assert len(sr[0]["content"]) >= 2          # one text block per paragraph


def _resp(source, quote, text="Keytruda sales were $29,482 million."):
    return {"content": [
        {"type": "text", "text": text, "citations": [{"type": "search_result_location", "cited_text": quote, "search_result_index": 0,
                                                       "start_block_index": 0, "end_block_index": 1, "source": source, "title": "t"}]},
        {"type": "text", "text": " "},
        {"type": "text", "text": "Sales also grew 99%."},
    ]}


def test_parse_search_result_response(idx):
    src = "/viewer?doc=AAA%3A10k_FY2025.md&page=2&q=x"
    claims = parse_cited_response(_resp(src, EXACT), idx)
    assert len(claims) == 2
    c = claims[0].citations[0]
    assert c.canonical_id == "AAA:10k_FY2025.md" and c.page == 2 and c.verification.status == "exact" and c.folio == "41"
    passed, rejected = V.gate(claims)
    assert [x.text for x in passed] == ["Keytruda sales were $29,482 million."] and rejected[0].citations == []


def test_parse_rejects_wrong_page_and_uncited_number(idx):
    wrong = parse_cited_response(_resp("/viewer?doc=AAA%3A10k_FY2025.md&page=3&q=x", EXACT), idx)
    assert wrong[0].citations[0].verification.status == "unverified"
    bad = parse_cited_response(_resp("/viewer?doc=AAA%3A10k_FY2025.md&page=2&q=x", EXACT, text="Sales were $31,000 million."), idx)
    assert bad[0].citations[0].verification.status == "unverified" and "31,000" in bad[0].citations[0].confidence_note


def test_parse_fallbacks_by_index_and_document_locations(idx):
    by_index = parse_cited_response(_resp("t", EXACT), idx, pages=_pages(idx))
    assert by_index[0].citations[0].verification.status == "exact"
    resp = {"content": [{"type": "text", "text": "Risk is IRA pricing.", "citations": [
        {"type": "page_location", "cited_text": "Pricing pressure from IRA negotiation may reduce revenue materially",
         "document_index": 0, "document_title": "x", "start_page_number": 3, "end_page_number": 4},
        {"type": "char_location", "cited_text": "Pricing pressure from IRA negotiation", "document_index": 0,
         "start_char_index": 0, "end_char_index": 5}]}]}
    out = parse_cited_response(resp, idx, documents=[("AAA:10k_FY2025.md", 3)])
    assert [c.verification.status for c in out[0].citations] == ["exact", "exact"]
    by_doc = parse_cited_response(resp, idx, documents=["AAA:10k_FY2025.md"])      # page found by search for char_location
    assert by_doc[0].citations[1].page == 3


def test_citation_roundtrip(idx):
    c = V.verify(cite(), idx)
    d = c.to_dict()
    assert json.loads(json.dumps(d))["verification"]["status"] == "exact"
    assert Citation.from_dict(d) == c
    assert {"cite_id", "canonical_id", "ticker", "doc_type", "doc_title", "period", "page", "folio", "char_start", "char_end", "quote",
            "claim_type", "value", "unit", "source_url", "deep_link", "viewer_link", "verification", "confidence_note"} <= set(d)


# ---------------------------------------------------------------- transcript speaker and fool.com rules (review B12)
def test_transcript_speaker_and_fool_rules(tmp_path):
    import sqlite3
    from agent.needle.cite import index as I
    from agent.needle.cite import verify as V
    from agent.needle.cite.locator import Citation
    db = tmp_path / "c.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""CREATE TABLE docs (doc_id TEXT, ticker TEXT, company TEXT, "group" TEXT, doc_type TEXT,
      form TEXT, period TEXT, filed TEXT, source_quality TEXT, source_url TEXT, path TEXT, stream TEXT, quote_grade TEXT,
      superseded_by TEXT, license TEXT, drug TEXT, n_pages INTEGER, page_scheme TEXT, notes TEXT);
      CREATE TABLE pages (doc_id TEXT, page_no INTEGER, printed TEXT, char_start INTEGER, char_end INTEGER,
      speakers TEXT, text TEXT);""")
    take = "Key takeaways: management said demand for the lead product is strong across regions this quarter."
    call = ("Full Conference Call Transcript\n**Jane Roe (CFO at Acme):** Our gross-to-net erosion was about four "
            "points this year and we expect a similar step next year.\n**John Doe (CEO at Acme):** We remain "
            "confident in the launch trajectory and the pipeline readouts.")
    con.execute("INSERT INTO docs (doc_id, ticker, doc_type, period, filed, source_url, n_pages) VALUES "
                "('ACME:t.md', 'ACME', 'transcript', '2026Q2', '2026-07-30', 'https://www.fool.com/x/', 1)")
    con.execute("INSERT INTO pages (doc_id, page_no, text) VALUES ('ACME:t.md', 1, ?)", (take + "\n" + call,))
    con.commit()
    con.close()
    idx = I.load_index(db)
    q1 = "Our gross-to-net erosion was about four points this year"
    ok = V.verify(Citation("ACME:t.md", 1, q1), idx)
    assert ok.verification.ok and ok.speaker == "Jane Roe"                       # attributed from the label
    assert V.verify(Citation("ACME:t.md", 1, q1, speaker="Jane Roe"), idx).verification.ok
    wrong = V.verify(Citation("ACME:t.md", 1, q1, speaker="John Doe"), idx)
    assert not wrong.verification.ok and "John Doe" in wrong.confidence_note
    # a speaker who talks elsewhere in the window but is not the nearest label is still rejected
    later = "We remain confident in the launch trajectory and the pipeline readouts."
    assert V.verify(Citation("ACME:t.md", 1, later, speaker="John Doe"), idx).verification.ok
    mis = V.verify(Citation("ACME:t.md", 1, later, speaker="Jane Roe"), idx)
    assert not mis.verification.ok and "spoken by 'John Doe'" in mis.confidence_note
    fool = V.verify(Citation("ACME:t.md", 1, "management said demand for the lead product is strong"), idx)
    assert not fool.verification.ok and "fool.com takeaways" in fool.confidence_note
