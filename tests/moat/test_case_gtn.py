"""case_gtn: gross-to-net rows are cited and the filing quotes verify."""
from agent.moat import cite
from agent.moat.case_gtn import gtn_series

REQ = ("ticker", "kind", "text", "citation", "url", "locator", "source_id", "quote_grade", "license")


def test_ticker_rows_have_citations():
    rows = gtn_series(ticker="MRK")
    assert rows
    kinds = {r["kind"] for r in rows}
    assert "company_list_vs_net" in kinds and "drug_gtn_proxy" in kinds
    for r in rows:
        assert all(k in r for k in REQ)
        assert r["citation"] and r["locator"] and r["text"] and len(r["text"]) < 600
    for r in rows:
        if r["kind"] in ("company_list_vs_net", "drug_gtn_proxy", "drug_gtn_exposure"):
            assert r["verify_status"] and r["source"] and r["source_row"] is not None


def test_drug_rows_and_filing_quotes():
    rows = gtn_series(drug="keytruda")
    assert rows and {r["drug"] for r in rows} <= {"", "keytruda", "keytruda-qlex"}
    assert any(r["kind"] == "partb_asp" for r in rows)
    bmy = [r for r in gtn_series(ticker="BMY") if r["kind"].startswith("filing")]
    assert bmy
    for r in bmy:
        doc_id, pg = r["locator"].rsplit("#p", 1)
        assert cite.verify_quote(r["quote"], doc_id, int(pg))


def test_unknown_returns_empty():
    assert gtn_series(ticker="ZZZZ") == []
    assert gtn_series(drug="nosuchdrug") == []
