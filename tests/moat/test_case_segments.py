from agent.moat.case_segments import segment_changes


def test_restatement_rows_cited():
    rows = segment_changes("MRK", kind="restatement", k=20)
    assert rows
    for r in rows:
        assert r["kind"] == "restatement" and r["citation"] and r["locator"] and r["text"]


def test_unknown_ticker_empty():
    assert segment_changes("ZZZZ") == []


def test_kind_filter_and_all_cited():
    rows = segment_changes("MRK", k=60)
    assert "restatement" in {r["kind"] for r in rows}
    assert all(r["kind"] == "discontinued_breakout" for r in segment_changes("ABBV", kind="discontinued_breakout"))
    assert all(r["citation"] and r["locator"] for r in rows)
