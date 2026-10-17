import pytest

from agent.needle import pages
from agent.needle.detect import drift

KINDS = {f"{s}_{k}" for s in ("risk", "mdna") for k in ("added", "removed", "intensified", "modified")}


@pytest.mark.parametrize("ticker", ["AZN", "JNJ"])
def test_drift(ticker):
    sigs = drift.run(ticker)
    assert len(sigs) >= 5
    ds = pages.docs(ticker)
    for s in sigs:
        assert s.kind in KINDS and s.detector == "drift"
        assert s.evidence
        for e in s.evidence:
            assert pages.check(e, ds)[0] == "verified"
    assert any(s.meta["topics"] for s in sigs)


def test_nvo_uses_glossy_reports():
    sigs = drift.run("NVO")
    assert len(sigs) >= 5
    ds = pages.docs("NVO")
    assert all(ds[e.doc_id]["row"]["doc_type"] == "annual_report_glossy" for s in sigs for e in s.evidence)
    assert all(pages.check(e, ds)[0] == "verified" for s in sigs for e in s.evidence)
