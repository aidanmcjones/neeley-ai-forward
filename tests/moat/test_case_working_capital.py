"""Working-capital helper checks. No API key needed; needs the citation index and the cached XBRL table."""

import pytest

from agent.moat import cite as C
from agent.moat import case_working_capital as W
from agent.moat.common import OUT

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first: python -m agent.moat.index")


def test_mrk_quarters():
    rows = W.working_capital("MRK")
    q = [r for r in rows if r["kind"] == "quarter"]
    assert len(q) >= 8
    for r in q:
        assert r["revenue"] and r["inventory"] and r["citation"] and r["locator"]
    assert any(r["locator"].startswith("MRK:") for r in q)


def test_unknown_ticker_empty():
    assert W.working_capital("ZZZZ") == []


def test_cache_file_exists_with_columns():
    W._load()
    p = OUT / W.CACHE_REL
    assert p.exists()
    assert p.read_text().splitlines()[0].split(",") == W.COLS
