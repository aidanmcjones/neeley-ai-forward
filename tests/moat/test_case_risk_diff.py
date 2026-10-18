"""case_risk_diff checks. No API key needed; needs data/moat/index/citations.sqlite (python -m agent.moat.index)."""

import pytest

from agent.moat import cite as C
from agent.moat.case_risk_diff import risk_diff

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first: python -m agent.moat.index")


@pytest.fixture(scope="module")
def mrk():
    return risk_diff("MRK", section="both", k=25)


def test_mrk_rows_cited_and_verified(mrk):
    kinds = {r["kind"] for r in mrk}
    assert {"section_stats", "added", "changed"} <= kinds
    assert {r["section"] for r in mrk} == {"risk_factors", "mdna"}
    for r in mrk:
        assert r["citation"] and r["url"].startswith("https://") and r["locator"] == r["source_id"]
        doc_id, page = r["locator"].rsplit("#p", 1)
        assert C.verify_quote(r["text"], doc_id, int(page)), r["locator"]
        if r["prev_text"]:
            pdoc, ppage = r["prev_locator"].rsplit("#p", 1)
            assert C.verify_quote(r["prev_text"], pdoc, int(ppage)), r["prev_locator"]
        assert len(r["text"]) < 600


def test_mrk_defaults_compare_latest_two_10ks(mrk):
    stats = [r for r in mrk if r["kind"] == "section_stats"]
    assert len(stats) == 2
    for s in stats:
        assert s["doc_id"] == "MRK:10k_FY2025.md" and s["prev_doc_id"] == "MRK:10k_FY2024.md"
        assert s["words"] > 1000 and s["prev_words"] > 1000
    changed = [r for r in mrk if r["kind"] == "changed"]
    assert all(r["prev_text"] and r["diff"] for r in changed)


def test_foreign_filer_uses_20f_and_explicit_years():
    rows = risk_diff("AZN", section="risk_factors", k=5)
    assert rows and rows[0]["kind"] == "section_stats"
    assert rows[0]["doc_id"] == "AZN:20f_FY2025.md" and rows[0]["prev_doc_id"] == "AZN:20f_FY2024.md"
    older = risk_diff("MRK", section="risk_factors", fy="2024", prev="FY2023", k=3)
    assert older and older[0]["doc_id"] == "MRK:10k_FY2024.md"
    assert older[0]["prev_doc_id"].endswith("10k_FY2023.md")


def test_unknown_ticker_returns_empty():
    assert risk_diff("ZZZZ") == []
