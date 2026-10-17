from agent.needle.schema import Evidence, Finding, Signal, read_jsonl, write_jsonl


def test_signal_round_trip(tmp_path):
    s = Signal("AZN", "forensics", "inventory_outpaces_revenue", "2025FY", 0.24, 0.05, 2.1, "inventory +24% vs revenue +9%",
               [Evidence("AZN:20f_FY2025.md", 142, "inventories increased", figures=["24"])])
    write_jsonl(tmp_path / "s.jsonl", [s])
    back = read_jsonl(tmp_path / "s.jsonl", Signal)[0]
    assert back == s
    assert back.evidence[0].source() == "AZN:20f_FY2025.md#p142"


def test_finding_ignores_unknown_keys(tmp_path):
    write_jsonl(tmp_path / "f.jsonl", [{"id": "X-1", "ticker": "X", "finding": "f", "signal_kind": "k", "extra": 1}])
    f = read_jsonl(tmp_path / "f.jsonl", Finding)[0]
    assert f.id == "X-1" and f.verdict == "unverified"
