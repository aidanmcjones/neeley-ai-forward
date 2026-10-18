"""case_calls checks. No API key needed; needs data/moat/index/citations.sqlite."""

import time

import pytest

from agent.moat import cite as C
from agent.moat.case_calls import call_qa, dropped_metrics

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first: python -m agent.moat.index")


def test_mrk_call_qa_rows_have_verified_answers():
    t0 = time.time()
    rows = call_qa("MRK", quarters=4)
    assert time.time() - t0 < 15
    pairs = [r for r in rows if r["kind"] == "qa_pair"]
    assert pairs and {"new_phrase", "never_asked"} <= {r["kind"] for r in rows}
    for r in pairs[:20] + [r for r in rows if r["kind"] == "new_phrase"][:10]:
        assert r["citation"] and r["locator"] == f"{r['doc_id']}#p{r['page_no']}" == r["source_id"]
        assert C.verify_quote(r["text"], r["doc_id"], r["page_no"])
        assert 0 <= (r["deflection_score"] or 0) <= 1 and len(r["text"]) <= 600
    assert all(r["locator"].startswith("fact:") and r["verify_status"] for r in rows if r["kind"] == "never_asked")


def test_quotable_flag_matches_grade():
    rows = call_qa("NVO", quarters=4, flags=("deflection",), k=200)
    assert rows
    assert all(r["quotable"] == (r["quote_grade"] in ("A", "B")) for r in rows)
    assert all(r["license"] == "bloomberg_licensed" for r in rows if "bloomberg" in r["doc_id"])
    assert not [r for r in call_qa("NVO", flags=("deflection",), grade_min="A") if r["quote_grade"] != "A"]


def test_dropped_metrics_cited_against_latest_release():
    t0 = time.time()
    rows = dropped_metrics("MRK", releases=6)
    assert time.time() - t0 < 15
    assert rows
    for r in rows:
        assert r["kind"] == "dropped_metric" and r["checked_against"] and r["times_seen"] >= 2
        doc_id, page = r["locator"].split("#p")
        assert C.verify_quote(r["text"], doc_id, int(page)) and r["citation"]
        assert r["last_seen"] not in r["missing_from"]


def test_unknown_ticker_returns_empty():
    assert call_qa("ZZZZ") == []
    assert dropped_metrics("ZZZZ") == []
