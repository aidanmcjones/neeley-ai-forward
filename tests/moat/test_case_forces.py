import pytest

from agent.moat import cite as C
from agent.moat.case_forces import forces

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first")


def test_nvo_ira():
    rs = forces("NVO", "ira")
    ira = [r for r in rs if r["force"] == "ira" and r["kind"] in ("ira_drug", "exposure_item", "summary")]
    assert ira and all(r["citation"] and r["locator"] for r in ira)
    pm = [r for r in rs if r["kind"] == "peer_matrix"][0]
    assert "NVO" in pm["value"] and "locators" in pm


def test_azn_tariff_mfn():
    assert any(r["kind"] == "tariff_item" and r["citation"] for r in forces("AZN", "tariff"))
    assert any(r["kind"] == "mfn_term" and r["citation"] for r in forces("AZN", "mfn"))


def test_statements_verified_and_unknown():
    for r in forces("MRK", "all", k=200):
        if r["kind"] in ("filing_statement", "call_statement"):
            d, p = r["locator"].split("#p")
            assert C.verify_quote(r["text"], d, int(p))
    assert forces("ZZZZ") == []
