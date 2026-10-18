"""case_labels helper checks. No API key needed; needs data/moat/index/citations.sqlite."""

import pytest

from agent.moat import cite as C
from agent.moat.case_labels import label_compare

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first: python -m agent.moat.index")


def test_keytruda_and_three_rivals_cited():
    rows = label_compare("keytruda")
    drugs = {r["drug"] for r in rows if r["kind"] == "label_section"}
    assert {"keytruda", "opdivo", "imfinzi", "tecentriq"} <= drugs
    assert all(r["citation"] and r["locator"] and r["text"] for r in rows)
    assert all(len(r["text"]) <= 600 for r in rows)
    assert {r["section"] for r in rows if r["kind"] == "matrix"} >= {"indications", "dosing", "rems"}
    assert any(r["kind"] == "rems" and r["verify_status"] for r in rows)


def test_label_section_text_verifies_on_its_page():
    rows = [r for r in label_compare("skyrizi", sections=("indications", "dosing")) if r["kind"] == "label_section"]
    assert rows
    for r in rows:
        doc_id, page = r["locator"].rsplit("#p", 1)
        assert C.verify_quote(r["text"][:200], doc_id, int(page))


def test_extra_rivals_and_fallback_to_full_label():
    rows = label_compare("vyndaqel", rivals=["eliquis"], sections=("indications", "boxed_warning"))
    assert {r["drug"] for r in rows if r["kind"] == "label_section"} == {"vyndaqel", "eliquis"}
    assert any(r["kind"] == "label_section" and r["section"] == "boxed_warning" for r in rows)


def test_unknown_drug_returns_empty():
    assert label_compare("notadrug") == []
