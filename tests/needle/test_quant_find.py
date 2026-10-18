"""FIND reference answers (docs/quant_model.md section 10) and unit checks of every FIND component."""

from datetime import date
from types import SimpleNamespace

import pytest

from agent.needle.quant import evidence as EV
from agent.needle.quant import find, impact as IM, league, obscurity as OB
from agent.needle.quant import weights as W
from agent.needle.quant.data import MOAT

AS_OF = date(2026, 10, 17)
need_moat = pytest.mark.skipif(not (MOAT / "tables" / "ibes_actuals.csv").exists(), reason="moat data not present")

# LLY constants, section 10.1
REV, TAX, D, SIGMA = 79665.0, 0.2049, 893.7, 2.0294


def co(**kw):
    base = dict(rev_ttm=REV, tax=TAX, shares=D, sigma=SIGMA, currency="USD", fin_currency="USD", citations={},
                flags=[])
    base.update(kw)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------- weights pinned to section 11.1
def test_weights_match_table():
    assert (W.PI_INVENTORY, W.PI_DIO, W.PI_RECEIVABLES, W.PI_DSO, W.PI_GROSS_MARGIN_DROP) == \
        (0.0466, 0.0318, 0.0629, 0.0851, 0.0422)
    assert (W.PI_MISSTATEMENT, W.PI_RISK_FACTOR, W.PI_LITIGATION_TEXT, W.PI_MDNA, W.PI_INSIDER, W.PI_8K, W.PI_MIN,
            W.PI_NONE) == (0.0491, 0.0226, 0.0349, 0.0226, 0.0201, 0.0061, 0.0055, 0.0028)
    assert (W.R, W.H_MONTHS, W.ANCHOR, W.H_VALUE, W.N_STAR, W.NEEDLE_O, W.NEEDLE_E, W.E_HIGH, W.E_MED) == \
        (0.0785, 3.0, 0.03, 0.9, 3, 0.5, 0.90, 0.95, 0.745)
    assert W.H_MONTHS_SENSITIVITY == 6.0     # review A11: H = 3 base, 6 the sensitivity
    assert (W.CM_PRICE, W.CM_VOLUME, W.DELTA_OOS, W.M_MDP_CATASTROPHIC) == (1.0, 0.7, 0.26, 0.20)


# ---------------------------------------------------------------- LLY company constants from the data layer
@need_moat
def test_lly_constants():
    from agent.needle.quant.data import company
    c = company("LLY")
    assert round(c.rev_ttm, 1) == 79665.0
    assert round(c.tax, 4) == 0.2049
    assert round(c.shares, 1) == 893.7
    assert abs(c.sigma - 2.0294) < 2e-4          # 2 x sd 1.0147 (spec prints 2.0294 and 2.0295)
    assert all(x.verification.ok or x.verification.status == "derived"
               for k in ("Rev_TTM", "t", "D", "sigma_EPS") for x in c.citations[k])
    # review D11: companyfacts has no CY2025Q4 frame; Q4 = FY - 9M is a derived citation over both operand frames
    q4 = [x for x in c.citations["Rev_TTM"] if "2025Q4" in x.quote or "CY2025 -" in x.quote]
    assert q4 and all(x.verification.status == "derived" and x.canonical_id == "derived" for x in q4)
    assert "CY2025Q1" in q4[0].confidence_note and "CY2025 " in q4[0].confidence_note + " "


# ---------------------------------------------------------------- Finding A: gross-margin level outlier
def test_gross_margin_level_outlier_scores_zero():
    sig = SimpleNamespace(kind="gross_margin_peer_outlier", value=0.858, peer_median=0.741, peer_z=1.85,
                          detector="forensics", meta={})
    fam = find.family_of(sig, ["gross_margin"])
    assert fam.pi == 0.0
    assert find.score(1.0, 0.3, 1.0, fam.pi) == 0.0


# ---------------------------------------------------------------- Finding B: DIO
def dio_S(H=6.0, r=W.R, hc=W.DELTA_OOS, anchor=W.ANCHOR):
    d_eps = anchor * REV * (1 - TAX) / D
    M = find.materiality(d_eps, 0.5, SIGMA, r)
    O = OB.obscurity(0, 0, 0.6, 0, 0, OB.months_between(date(2026, 8, 5), AS_OF), H)
    return find.score(M, O, 1.0, W.backtest_pi(0.217, 0.174, hc)), M, O


@need_moat
def test_azn_sigma_per_share_basis():
    from agent.needle.quant.data import company
    assert abs(company("AZN").sigma - 0.5408) < 1e-3     # ZEN per-ADR history x 2 (review A2)


def test_dio_reference():
    imp = IM.anchor(co())
    assert abs(imp.d_eps["base"] - 2.1262) < 2e-4   # spec rounds t
    assert round(IM.dio(16793, 3268), 1) == 468.9
    assert round(IM.dio(2630, 3268), 1) == 73.4
    S, M, O = dio_S()
    assert round(M, 4) == 1.0089
    assert round(O, 4) == 0.3032
    assert round(S, 5) == 0.00973
    conf, _ = EV.confidence(1.0, 1, False, False, False, False, False)
    assert conf == "MEDIUM"
    assert O < W.NEEDLE_O


# ---------------------------------------------------------------- Finding C: Verzenio IRA
def verz_S(H=6.0, r=W.R, m=W.M_MDP_CATASTROPHIC):
    imp = IM.ira(co(), "Verzenio", 1428.714, find.ONC, m, 2028)
    M = find.materiality(imp.d_eps["base"], imp.t_years, SIGMA, r)
    O = OB.obscurity(0, 0, 0.5, 0, 0, OB.months_between(date(2026, 1, 27), AS_OF), H)
    return find.score(M, O, 1.0, 1.0), imp, M, O


def test_verzenio_reference():
    S, imp, M, O = verz_S()
    assert [round(imp.d_rev[k], 1) for k in ("bull", "base", "bear")] == [257.2, 428.6, 571.5]
    assert round(imp.d_eps["base"], 2) == 0.38
    assert round(imp.d_eps["base"], 4) == 0.3813
    assert round(imp.t_years, 3) == 1.706
    assert round(M, 4) == 0.1652
    assert round(O, 4) == 0.1843
    assert round(S, 4) == 0.0304
    conf, _ = EV.confidence(1.0, 2, True, False, True, False, True)
    assert conf == "HIGH"
    assert O < W.NEEDLE_O


@need_moat
def test_lly_end_to_end_matches_worked_example(monkeypatch):
    from agent.needle.quant.run import score_ticker
    monkeypatch.setattr(W, "H_MONTHS", 6.0)     # the worked example's half-life (now the sensitivity, review A11)
    _, fs, wh = score_ticker("LLY", write=False)
    by = {f.kind: f for f in fs + wh}
    # review A1: LLY's DIO rose +14.2% YoY, below the backtest dio_rising trigger (+15%), so pi = pi_min; review R2:
    # an unfired flag does not get the anchor event size either, so the row is "not quantified" with S = 0 (v2 printed
    # 0.00168 = 1.0089 x 0.3032 x 1.0 x 0.0055; spec 10.3 printed 0.00973 with the backtest pi)
    dio = by["dio_peer_outlier"]
    assert dio.S == 0 and dio.not_quantified.startswith("not quantified") and dio.to_dict()["impact"] is None
    assert dio.pi_downgraded and dio.vector["pi"] == W.PI_MIN
    # guard 2 (agent-chat #19): on revenue, LLY's days inventory is not a peer outlier, so the row is withheld
    assert dio.guard == "drop" and dio in wh
    assert "capacity build, not channel stuffing" in by["dio_peer_outlier"].flags
    v = [f for f in fs if f.kind == "ira_selected" and f.product == "Verzenio"][0]
    # league value uses the KQ2 class rule (1.0 x list discount, review A15); spec formula kept alongside
    # review A12: FY2028 consensus first appears after the selection date, so c is untestable and set to 0.5
    # (uninformative) instead of 0: both values halve (v2 printed 0.0507 and 0.0304 with c = 0)
    assert v.vector["c"] == W.C_UNTESTABLE
    # review S3: one IRA formula, G x max(0, k x d - m_avoided): Verzenio base 1428.7 x (0.50 - 0.15) = 500.0
    assert round(v.impact.d_rev["base"], 1) == 500.0
    assert round(v.S, 4) == 0.0178 and round(v.vector["S_spec_formula"], 4) == 0.0152
    assert v.confidence == "HIGH" and v.vector["n_ind"] == 2
    assert all(f.S == 0 for f in fs if f.kind == "gross_margin_peer_outlier")
    assert not by["dio_peer_outlier"].needle_eligible
    # review R1: the Needle floor is on the discussion term D, not on O (Verzenio O 0.18 but D = 1 - a)
    assert v.needle_eligible == (v.vector["D"] >= W.NEEDLE_O) and v.vector["O"] < W.NEEDLE_O


# ---------------------------------------------------------------- sensitivity: order C > B kept at x0.5 / x1.5
@pytest.mark.parametrize("f", [0.5, 1.5])
def test_sensitivity_order_kept(f):
    assert verz_S(H=6 * f)[0] > dio_S(H=6 * f)[0]
    assert verz_S(r=W.R * f)[0] > dio_S(r=W.R * f)[0]
    assert verz_S()[0] > dio_S(hc=0.26 * f)[0]
    assert verz_S()[0] > dio_S(anchor=0.03 * f)[0]
    assert verz_S(m=0.20 * f)[0] > dio_S()[0]
    # spec 10.6 numbers
    assert round(dio_S(H=6 * f)[0], 5) == {0.5: 0.00738, 1.5: 0.01068}[f]
    assert round(verz_S(m=0.20 * f)[0], 5) == {0.5: 0.04058, 1.5: 0.02029}[f]


# ---------------------------------------------------------------- league concentration penalty
def F(S, block, **v):
    vec = {"O": 0.6, "z": 0, "E": 1.0}
    vec.update(v)
    return SimpleNamespace(S=S, family=SimpleNamespace(block=block), vector=vec, confidence="MEDIUM",
                           needle_eligible=vec["O"] >= 0.5 and vec["E"] >= 0.9)


def test_concentration_penalty():
    one = [F(0.1, "A") for _ in range(5)]
    L, top, ne, _ = league.league_score(one)
    assert ne == pytest.approx(1.0) and L == pytest.approx(0.5 / 3)
    three = [F(0.1, "A"), F(0.1, "T"), F(0.1, "P")]
    L3, _, ne3, _ = league.league_score(three)
    assert ne3 == pytest.approx(3.0) and L3 == pytest.approx(0.3)
    two = [F(0.3, "A"), F(0.1, "T")]
    L2, _, ne2, _ = league.league_score(two)
    assert ne2 == pytest.approx(0.16 / 0.10) and L2 == pytest.approx(0.4 * 1.6 / 3)


def test_same_fact_counts_once_in_league():
    """Review S1: a time-series flag and its peer-outlier twin on the same metric and period are one finding."""
    a = F(0.05, "A"); a.fact_key, a.id, a.flags = "AZN|2025|receivables_gap", "a", []
    b = F(0.05, "A"); b.fact_key, b.id, b.flags = "AZN|2025|receivables_gap", "b", []
    c = F(0.04, "P"); c.fact_key, c.id, c.flags = "", "c", []
    L, top, _, _ = league.league_score([a, b, c])
    assert len(top) == 2 and {f.id for f in top} == {"a", "c"}
    assert any(x.startswith("same fact as a") for x in b.flags)


def test_needle_floor_on_discussion_term_not_decay():
    """Review R1: an old fact with D >= 0.5 keeps its Needle eligibility; decay only lowers S."""
    assert OB.discussion(0, 0, 0.2, 0, 0) == pytest.approx(0.8)
    O = OB.obscurity(0, 0, 0.2, 0, 0, 12.0)
    assert O == pytest.approx(0.8 * 2 ** (-12 / W.H_MONTHS)) and O < W.NEEDLE_O
    fs = [F(0.5, "A", O=0.05, D=0.8), F(0.1, "T", O=0.6, D=0.4)]
    fs[0].needle_eligible, fs[1].needle_eligible = True, False
    n, st = league.sharpest_needle(fs)
    assert st == "strict" and n.S == 0.5


def test_needle_rule_and_fallbacks():
    fs = [F(0.5, "A", O=0.3), F(0.1, "T", O=0.6)]
    n, st = league.sharpest_needle(fs)
    assert st == "strict" and n.S == 0.1
    fs = [F(0.5, "A", O=0.3), F(0.1, "T", O=0.2)]
    n, st = league.sharpest_needle(fs)
    assert st == "provisional" and n.S == 0.5


# ---------------------------------------------------------------- confidence boundaries (section 4.7)
def test_confidence_boundaries():
    assert EV.confidence(0.95, 2, False, False, True, False, True)[0] == "HIGH"
    assert EV.confidence(0.9499, 2, False, False, True, False, True)[0] == "MEDIUM"
    assert EV.confidence(1.0, 1, False, False, True, False, True)[0] == "MEDIUM"     # one source, derived
    assert EV.confidence(1.0, 1, True, False, True, False, True)[0] == "HIGH"       # verbatim official source
    assert EV.confidence(1.0, 2, False, True, True, False, True)[0] == "MEDIUM"     # entailed / LLM key claim
    assert EV.confidence(1.0, 2, False, False, False, False, True)[0] == "MEDIUM"   # non-diagnostic
    assert EV.confidence(0.745, 1, False, False, False, False, True)[0] == "MEDIUM"
    assert EV.confidence(0.7449, 1, False, False, False, False, True)[0] == "LOW"
    assert EV.confidence(1.0, 2, True, False, True, True, True)[0] == "LOW"          # contradicted
    assert EV.confidence(1.0, 2, True, False, True, False, True, trial_fails=True)[0] == "LOW"


def test_evidence_noisy_or_and_weakest_link():
    from agent.needle.cite.locator import Citation, Verification
    fz = lambda i: Citation(canonical_id=f"d{i}", quote="x", verification=Verification("fuzzy", 0.9))
    ex = Citation(canonical_id="e", quote="y", verification=Verification("exact", 1.0))
    assert EV.evidence_score([[fz(1), fz(2)]]) == pytest.approx(0.99)
    assert EV.evidence_score([[ex], [fz(1)]]) == pytest.approx(0.90)
    assert EV.evidence_score([[fz(1), fz(1)]]) == pytest.approx(0.90)   # same document counts once
    assert EV.evidence_score([]) == 0.0


# ---------------------------------------------------------------- channels
def test_loe_and_ira_window():
    c = co()
    imp = IM.loe(c, "x", 1000.0, date(2029, 8, 27), biologic=True)
    assert imp.d_eps["base"] == 0 and "outside" in imp.flags[0]
    imp = IM.loe(c, "x", 1000.0, date(2027, 1, 1), biologic=False)   # year 2 (R 0.15) is the largest in window
    assert imp.fiscal_year == 2028 and imp.d_rev["base"] == pytest.approx(850.0) and imp.cm == 0.7
    imp = IM.ira(c, "x", 1000.0, 0.5, 0.2, 2026)
    assert imp.d_eps["base"] == 0                          # already effective
    imp = IM.ira(c, "x", 1000.0, 0.5, 0.6, 2027)
    assert imp.d_rev["base"] == 0                          # g_pre >= d zeroes the finding
    assert IM.tariff_note(100.0) == {0.15: 15.0, 0.2: 20.0, 1.0: 100.0}


def test_favorable_signs_get_pi_zero():
    s = SimpleNamespace(kind="rec_gap_peer_outlier", value=-0.12, peer_median=0.0, peer_z=-1.7, detector="forensics",
                        meta={})
    assert find.family_of(s, ["receivables"]).pi == 0.0
    s = SimpleNamespace(kind="tax_rate_shift", value=-0.2, peer_median=None, peer_z=None, detector="forensics", meta={})
    assert find.family_of(s, ["tax"]).pi == 0.0


def test_starter_thread():
    assert OB.starter_thread("LLY", "Trulicity loses exclusivity in 2027", ["generic"]) == 1.0
    assert OB.starter_thread("LLY", "Verzenio ira negotiation", ["ira"]) == 0.0
    assert OB.starter_thread("JNJ", "Erleada ira negotiation", ["ira"]) == 1.0
    assert OB.starter_thread("NVO", "Ozempic/Rybelsus/Wegovy ira", ["ira"]) == 1.0


# ---------------------------------------------------------------- graceful degradation: 20-F filer
@need_moat
def test_20f_filer_degrades_with_flags():
    from agent.needle.quant.data import company
    from agent.needle.quant.run import score_ticker
    c = company("NVO")
    assert c.annual_only and c.currency == "DKK"
    assert any("annual filer" in f for f in c.flags)
    _, fs, _ = score_ticker("NVO", write=False)
    assert fs, "NVO must still score"
    assert all(any("h_f imputed" in x for x in f.flags) for f in fs)      # no earnings release in the index
    sema = [f for f in fs if f.kind == "ira_selected"]
    assert sema and sema[0].vector["z"] == 1.0 and sema[0].S == 0.0        # starter thread
    assert any("FX" in x for x in sema[0].flags)


@need_moat
def test_amgn_receivables_yoy_on_one_basis():
    """Review D1: receivables and revenue growth are both year-on-year (Q2 2026 vs Q2 2025), every operand is cited
    (prior-year 10-Q page included), and the gap is a derived citation."""
    from agent.needle.quant.run import score_ticker
    _, fs, _ = score_ticker("AMGN", write=False)
    f = [x for x in fs if x.kind == "receivables_outpace_revenue"][0]
    assert "10,227 vs 8,701" in f.sentence and "+17.5%" in f.sentence and "+9.5%" in f.sentence
    assert any(c.canonical_id.endswith("10q_2025Q2.md") and c.verification.ok for c in f.citations)
    assert any(c.verification.status == "derived" for c in f.citations)
    assert not f.pi_downgraded            # +8.01 pts meets the 8-pt trigger (an edge case: see league_v3)
