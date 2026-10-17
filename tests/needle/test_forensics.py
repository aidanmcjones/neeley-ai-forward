import pytest

from agent.needle import pages, xbrl
from agent.needle.detect import forensics


@pytest.mark.parametrize("t", ["JNJ", "AZN"])
def test_signals_and_evidence(t):
    sigs = forensics.run(t)
    assert len(sigs) >= 1
    ds = pages.docs(t)
    for s in sigs:
        assert s.detector == "forensics" and "concepts" in s.meta and "series" in s.meta
        if not s.evidence:
            assert s.meta.get("evidence") == "xbrl_only"
        for ev in s.evidence:
            assert pages.check(ev, ds)[0] == "verified"


def test_jnj_inventory_yoy():
    p = xbrl.panel("JNJ")
    assert p.at["2026Q2", "inventory"] == 15144000000 and p.at["2025Q2", "inventory"] == 13412000000
    ps, hist = forensics._history("JNJ")[:2]
    assert ps[0] == "2026Q2"
    assert hist["2026Q2"]["inv_yoy"] == pytest.approx(xbrl.yoy(p, "inventory")["2026Q2"])
    assert round(hist["2026Q2"]["inv_yoy"], 3) == 0.129
