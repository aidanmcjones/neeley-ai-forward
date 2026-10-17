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


def test_favorable_outlier_is_not_a_finding():
    """LLY's 85.8% gross margin is a strength; scoring its level as a change made $68B of phantom impact."""
    kinds = {s.kind for s in forensics.run("LLY")}
    assert "gross_margin_peer_outlier" not in kinds and "dio_peer_outlier" not in kinds


def test_gross_margin_level_has_no_dollar_path():
    from agent.needle import score
    from agent.needle.schema import Signal
    sig = Signal("LLY", "forensics", "gross_margin_peer_outlier", "2026Q2", 0.858)
    assert score._impact(sig, xbrl.panel("LLY"), 1e10)[0] is None


def test_ipr_and_d_charge_is_one_off():
    """MRK Q2 2026: $5.7B acquired IPR&D (Terns) explains the R&D jump and the tax rate (no tax benefit)."""
    sigs = {s.kind: s for s in forensics.run("MRK")}
    assert sigs["rnd_shift"].meta["one_off"]["dollars"] == 5.7e9
    assert sigs["tax_rate_shift"].meta.get("one_off")
    # LLY's R&D fell and its IPR&D sits on its own line: no one-off
    assert not any(s.meta.get("one_off") for s in forensics.run("LLY"))


def test_peer_outlier_duplicate_collapsed():
    from agent.needle import score
    kinds = [f.signal_kind for f in score.score_ticker("AZN")[0]]
    assert "receivables_outpace_revenue" in kinds and "rec_gap_peer_outlier" not in kinds


def test_impact_math_matches_the_sentence():
    """AZN FY2025: the formula must use the same receivables (10,237M vs 8,302M) and revenue growth (+8.6%)
    as the sentence, not half-year 6-K figures."""
    from agent.needle import score
    f = next(f for f in score.score_ticker("AZN")[0] if f.signal_kind == "receivables_outpace_revenue")
    assert "10,237M" in f.impact["formula"] and "8,302M" in f.impact["formula"] and "+8.6%" in f.impact["formula"]


def test_needle_never_undirected_mdna_or_label():
    from agent.needle import score
    for t in ("GILD", "JNJ", "MRK"):
        n = score.sharpest_needle(score.score_ticker(t)[0])
        assert n is None or (n.signal_kind not in score.NEEDS_DIRECTION and not n.signal_kind.startswith(
            ("label_", "dosing_", "boxed_")))
