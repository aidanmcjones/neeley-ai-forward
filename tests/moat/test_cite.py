"""Citation index checks. No API key needed; needs data/moat/index/citations.sqlite (python -m agent.moat.index)."""

import csv
import re
import time

import pytest

from agent.moat import cite as C
from agent.moat import index as I

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first: python -m agent.moat.index")

GENMAB = "royalty amounts to Genmab were approximately $2.4 billion and $2.0 billion, respectively"


def q(sql, *a):
    return C.db().execute(sql, a).fetchall()


def test_genmab_quote_on_right_printed_page():
    hits = C.search_pages("Genmab royalty amounts", ticker="JNJ", doc_type="annual_report", k=5)
    top = [h for h in hits if h["doc_id"] == "JNJ:10k_FY2025.md"][0]
    assert top["printed"] == "3" and top["page_no"] == 8
    assert C.verify_quote(GENMAB, "JNJ:10k_FY2025.md", 8)
    assert C.cite("JNJ:10k_FY2025.md", 8)[0] == "Johnson & Johnson 10-K FY2025, p. 3"
    assert C.cite("JNJ:10k_FY2025.md", 8)[1].startswith("https://www.sec.gov/")


def test_verify_quote_rejects_altered_number():
    assert not C.verify_quote(GENMAB.replace("$2.4", "$2.5"), "JNJ:10k_FY2025.md", 8)
    assert not C.verify_quote(GENMAB, "JNJ:10k_FY2025.md", 9)  # right quote, wrong page


def test_verify_quote_normalizes_whitespace_and_dashes():
    messy = GENMAB.replace(" ", "  \n ").upper()
    assert C.verify_quote(messy, "JNJ:10k_FY2025.md", 8)


def test_force_summary_fact_retrievable():
    with open(I.MOAT / "verified" / "policy" / "force_summary.csv", encoding="utf-8") as f:
        row = next(r for r in csv.DictReader(f) if r["ticker"] == "AZN")
    hits = C.search_facts("AZN ira_share_of_total_revenue_pct", ticker="AZN", table="force_summary")
    assert hits and hits[0]["table"] == "policy/force_summary.csv"
    assert hits[0]["field"] == "ira_share_of_total_revenue_pct"
    assert hits[0]["value"] == row["ira_share_of_total_revenue_pct"]
    assert hits[0]["verify_status"] == "verified"


def test_azn_mislabeled_transcript_superseded():
    d = C._doc("AZN:transcripts/2026Q1_transcript.md")
    assert d["superseded_by"] == "AZN:companies/AZN/transcripts/2026Q1_transcript.md"
    assert C._doc(d["superseded_by"]) is not None
    hits = C.search_pages("AstraZeneca first quarter", ticker="AZN", doc_type="transcript", k=50)
    assert all(h["doc_id"] != "AZN:transcripts/2026Q1_transcript.md" for h in hits)


def test_grade_d_transcript_excluded_with_grade_min_b():
    # a below-B transcript that is still live (D copies superseded by better moat copies are hidden by design)
    d_docs = [r["doc_id"] for r in q("SELECT doc_id FROM docs WHERE quote_grade IN ('C', 'D') AND n_pages > 0 "
                                     "AND superseded_by='' ORDER BY quote_grade DESC")]
    assert d_docs
    doc = d_docs[0]
    ticker = C._doc(doc)["ticker"]
    page = q("SELECT page_no, text FROM pages WHERE doc_id=? ORDER BY length(text) DESC LIMIT 1", doc)[0]
    words = [w for w in re.findall(r"[A-Za-z]{6,}", page["text"])][:5]
    query = " ".join(words)
    loose = C.search_pages(query, ticker=ticker, doc_type="transcript", k=50)
    assert any(h["doc_id"] == doc for h in loose)
    strict = C.search_pages(query, ticker=ticker, doc_type="transcript", grade_min="B", k=50)
    assert all(h["doc_id"] != doc for h in strict)
    assert all(h["quote_grade"] in ("A", "B") for h in strict)


def test_bloomberg_pdf_page_searchable():
    hits = C.search_pages("Jacobio license agreement", ticker="AZN", doc_type="transcript", k=10)
    bbg = [h for h in hits if "bloomberg" in h["doc_id"]]
    assert bbg and bbg[0]["quote_grade"] == "A" and bbg[0]["license"] == "bloomberg_licensed"
    assert bbg[0]["citation"].startswith("AstraZeneca 2026Q1 earnings call (Bloomberg), PDF p. ")
    turns = q("SELECT count(DISTINCT speaker) FROM turns WHERE doc_id=?", bbg[0]["doc_id"])[0][0]
    assert turns >= 10  # speaker turns detected


def test_counts_match_manifests():
    expect = set(I.corpus_rows()) | set(I.moat_rows()) | set(I.bloomberg_rows())
    have = {r[0] for r in q("SELECT doc_id FROM docs")}
    assert expect <= have
    assert have - expect == {d for d in have - expect if ":verified/" in d}  # only unlisted verified notes added
    # every page-marked doc has exactly as many pages as markers in its file
    for doc_id, path, n in q("SELECT doc_id, path, n_pages FROM docs WHERE page_scheme='marker' LIMIT 400"):
        text = (I.ROOT / path).read_text(encoding="utf-8", errors="ignore")
        assert n == len(I.MARKER.findall(text)), doc_id
    meta = dict(q("SELECT key, value FROM meta"))
    assert int(meta["n_pages"]) == q("SELECT count(*) FROM pages")[0][0]
    assert int(meta["n_facts"]) == q("SELECT count(*) FROM facts")[0][0]


def test_verified_pricing_supersedes_raw():
    tables = {r[0] for r in q('SELECT DISTINCT "table" FROM facts')}
    assert "pricing/gtn_proxy.csv" in tables
    assert not {"tables/gtn_proxy.csv", "tables/nadac_history.csv", "tables/partb_asp_quarterly.csv"} & tables
    assert C._doc("pricing:tables/gtn_proxy.csv")["superseded_by"] == "pricing:verified/pricing/gtn_proxy.csv"


def test_search_latency_under_200ms():
    C.search_pages("Keytruda royalty", ticker="MRK")  # warm the connection
    t = time.perf_counter()
    hits = C.search_pages("Keytruda royalty", ticker="MRK")
    C.search_pages("tariff")
    assert (time.perf_counter() - t) < 0.2
    assert hits and hits[0]["citation"].startswith("Merck ")
