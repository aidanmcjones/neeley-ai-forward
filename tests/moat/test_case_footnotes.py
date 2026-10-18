"""case_footnotes checks. No API key needed; needs data/moat/index/citations.sqlite."""

import pytest

from agent.moat import cite as C
from agent.moat.case_footnotes import footnotes

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first: python -m agent.moat.index")


def test_jnj_litigation_rows_verify():
    rows = footnotes("JNJ", "litigation", k=10)
    assert rows
    for r in rows:
        assert r["citation"] and r["locator"] and r["url"] and len(r["text"]) < 600
        assert C.verify_quote(r["text"], r["doc_id"], r["page_no"])
    assert {r["kind"] for r in rows} <= {"footnote", "latest_10q", "dropped_from_latest"}


def test_mrk_royalty_rows():
    rows = footnotes("MRK", "royalty", k=10)
    assert rows and all(r["topic"] == "royalty" and "numbers" in r for r in rows)


def test_unknown_returns_empty():
    assert footnotes("ZZZZ") == []
    assert footnotes("JNJ", "nonsense") == []
