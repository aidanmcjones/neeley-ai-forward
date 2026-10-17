import pytest

from agent.needle import outside, pages
from agent.needle.detect import supply

DIST = ("MCK", "COR", "CAH")
needs_outside = pytest.mark.skipif(not (outside.OUTSIDE / "faers").exists(), reason="data/outside not fetched")


def _dist_docs():
    ds = {}
    for d in DIST:
        ds.update(pages.docs(d))
    return ds


@pytest.mark.parametrize("t", ["BMY", "LLY"])
def test_run_and_evidence(t):
    sigs = supply.run(t)
    ds = _dist_docs()
    for s in sigs:
        assert s.detector == "supply" and s.ticker == t
        for ev in s.evidence:
            assert 25 <= len(ev.quote.split()) <= 45
            assert pages.check(ev, ds)[0] == "verified"
        if not s.evidence:
            assert s.meta["data"]["source_url"].startswith("http")


def test_distributor_commentary_has_evidence():
    sigs = supply.distributor_echo("LLY")
    assert sigs and all(s.kind == "distributor_commentary" and s.evidence for s in sigs)


@needs_outside
@pytest.mark.parametrize("t", ["BMY", "LLY", "AMGN"])
def test_outside_signals_carry_source(t):
    for s in supply.run(t):
        if s.kind != "distributor_commentary":
            assert s.meta["data"]["source_url"].startswith("http"), s.kind
            assert "proxy" in s.detail.lower() or "unverified" in s.detail.lower() or "sponsor-written" in s.detail


@needs_outside
def test_trial_signal_meta():
    sigs = [s for s in supply.trial_stops("BMY")]
    for s in sigs:
        assert s.meta["url"] == f"https://clinicaltrials.gov/study/{s.meta['nct_id']}"


def test_faers_change_math():
    rows = [{"quarter": f"q{i}", "reports": r, "serious": r} for i, r in enumerate([100] * 4 + [100, 100, 100, 200])]
    q, t4 = supply._faers_change(rows)
    assert q == pytest.approx(1.0) and t4 == pytest.approx(0.25)
