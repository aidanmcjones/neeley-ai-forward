"""DECIDE: reference case to the cent, monotonicity, structure, ranking, kill revision, CLI on the sample file."""

import json
from pathlib import Path

import pytest

from agent.needle.quant import decide as D
from agent.needle.quant import decide_cli as CLI
from agent.needle.quant import kill as K
from agent.needle.quant import moves as M

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "docs" / "examples"


def ref(**over):
    """Section 5.5 synthetic label expansion: two placebo pivotals at $28.8M over months 1-24, readout 24, approval 37."""
    return D.evaluate_move("M3", over, [], name="reference")


def test_reference_case_to_the_cent():
    r = ref()
    assert round(r.ev, 1) == 1431.2
    assert [round(r.ev_by_scenario[s], 1) for s in ("bear", "base", "bull")] == [1161.0, 1464.6, 1768.2]
    assert round(r.in_window_pv["base"], 1) == -53.3
    assert round(r.car, 1) == 57.6
    assert r.payback_month == 51
    assert round(r.spread, 1) == 607.2
    assert r.p_alive_end == pytest.approx(0.675 * 0.915)


def test_scenario_weights_sum_to_one_and_multipliers():
    assert sum(M.P_SCENARIO.values()) == pytest.approx(1.0)
    assert M.P_SCENARIO == {"bear": 0.50, "base": 0.11, "bull": 0.39}
    assert M.MULT_SCENARIO == {"bear": 0.8, "base": 1.0, "bull": 1.2}
    assert sum(M.MCDA_WEIGHTS.values()) == pytest.approx(1.0)
    with pytest.raises(AssertionError):
        D.evaluate_move("M3", {}, [], p_scenario={"bear": 0.5, "base": 0.5, "bull": 0.5})


def test_higher_wacc_lowers_ev():
    assert ref().ev > D.evaluate_move("M3", {}, [], wacc=0.10).ev > D.evaluate_move("M3", {}, [], wacc=0.15).ev


@pytest.mark.parametrize("code", sorted(M.TEMPLATES))
def test_each_template_has_24_monthly_periods(code):
    t = M.TEMPLATES[code]
    plan = t.build()
    assert plan.horizon >= 24
    for l in plan.lines:
        assert len(l.amount) == plan.horizon == len(l.prob)
    r = D.evaluate_move(t, {}, [])
    for s in M.SCENARIOS:
        rows = r.tables[s]
        assert [x["month"] for x in rows[:24]] == list(range(1, 25))
        assert len(rows) == plan.horizon
    assert r.car >= 0
    assert r.payback_month is None or 1 <= r.payback_month <= 120


def test_every_template_input_is_classified_and_cites_benchmarks():
    r = D.evaluate_move("M3", {}, [])
    cited = [i for i in r.inputs if i.citation_ids]
    assert cited, "benchmark defaults must carry citations"
    bench = [c for c in r.citations if c.canonical_id.startswith("benchmark:")]
    assert bench and all(c.claim_type == "number" and c.verification.status == "unverified"
                         and c.confidence_note == "external benchmark" for c in bench)
    url = [c for c in bench if c.source_url]
    assert url and all(c.deep_link == c.source_url for c in url)


def test_finding_citations_and_feed_into_pricing_baseline():
    finding = {"id": "LLY-ira-1", "ticker": "LLY", "signal_kind": "ira_negotiation", "score": 0.03,
               "finding": "Verzenio MFP", "impact": {"base": -428.6},
               "evidence": [{"doc_id": "LLY:10k_FY2025.md", "page": 46, "quote": "HHS selected Trulicity and Verzenio", "citation": "LLY 10-K FY2025, p. 46"}]}
    r = D.evaluate_move("M4", {"base_us_rev_annual": 5723.0}, [finding])
    inp = {i.name: i for i in r.inputs}["baseline_delta_rev_annual"]
    assert inp.kind == "finding" and inp.finding_id == "LLY-ira-1" and inp.value == pytest.approx(428.6 * -1 * -1)
    assert inp.citation_ids and any(c.canonical_id == "LLY:10k_FY2025.md" and c.page == 46 for c in r.citations)
    assert "LLY-ira-1" in r.finding_ids
    # the Part 1 delta lowers the baseline the move is measured on: EV changes with the finding
    assert r.ev != D.evaluate_move("M4", {"base_us_rev_annual": 5723.0}, []).ev


def test_no_finding_means_strategic_fit_zero_and_flag():
    r = ref()
    assert r.mcda_parts["strategic_fit"] == 0.0
    assert any("strategic fit 0" in f for f in r.flags)


def test_rank_moves_orders_by_ev_and_select_reports_two_rejected():
    a = D.evaluate_move("M3", {"peak_sales": 800}, [], name="A")
    b = D.evaluate_move("M3", {"peak_sales": 400}, [], name="B")
    c = D.evaluate_move("M3", {"peak_sales": 100}, [], name="C")
    d = D.evaluate_move("M3", {"peak_sales": 50}, [], name="D")
    ranked = D.rank_moves([c, a, d, b])
    assert [x.name for x in ranked] == ["A", "B", "C", "D"] and [x.rank for x in ranked] == [1, 2, 3, 4]
    sel = D.select_move([c, a, d, b], cash=1000)
    assert sel.chosen.name == "A" and [x.name for x in sel.rejected] == ["B", "C"]
    assert all(x.binding_reason for x in sel.rejected)


def test_feasibility_gate_uses_cash_at_risk():
    big = D.evaluate_move("M3", {"peak_sales": 5000, "trial_cost_each": 500}, [], name="big")
    small = D.evaluate_move("M3", {"peak_sales": 300}, [], name="small")
    sel = D.select_move([big, small], cash=200)
    assert sel.chosen.name == "small"
    assert "exceeds cash" in sel.rejected[0].binding_reason


def test_mcda_tiebreak_when_intervals_overlap():
    a = D.evaluate_move("M3", {"peak_sales": 800}, [], name="A", capability={"x": True}, stakeholders={"y": False})
    b = D.evaluate_move("M3", {"peak_sales": 790}, [], name="B", capability={"x": True}, stakeholders={"y": True})
    assert a.ev > b.ev and b.mcda > a.mcda
    sel = D.select_move([a, b], cash=1000)
    assert sel.chosen.name == "B"   # EV intervals [EV_bear, EV_bull] overlap, so the higher MCDA wins
    assert any("overlap" in n for n in sel.notes)


def test_kill_breach_lowers_ev_and_matches_spec_posterior():
    r = ref()
    rev = K.revise_ev(r, ["zs_breadth"])
    assert rev.p_posterior["bear"] == pytest.approx(0.834, abs=1e-3)
    assert rev.p_posterior["base"] == pytest.approx(0.101, abs=1e-3)
    assert rev.p_posterior["bull"] == pytest.approx(0.065, abs=1e-3)
    assert rev.ev_revised < rev.ev_remaining_prior
    assert rev.ev_revised_total < r.ev
    # three ZS metrics are one observation: same revision as one breach
    three = K.revise_ev(r, ["zs_breadth", "zs_return_writing", "zs_depth"])
    assert three.ev_revised == pytest.approx(rev.ev_revised)


def test_year_one_miss_sets_bear_to_070_and_review_signals_do_not_move_ev():
    r = ref()
    miss = K.revise_ev(r, ["year_one_sales"])
    assert miss.p_posterior["bear"] == pytest.approx(0.70)
    assert miss.ev_revised < miss.ev_remaining_prior
    rv = K.revise_ev(r, ["safety"])
    assert rv.ev_revised == pytest.approx(rv.ev_remaining_prior) and rv.review == ["safety"]


def test_stop_rule():
    r = D.evaluate_move("M3", {"peak_sales": 5}, [], name="weak")
    assert K.revise_ev(r, ["zs_breadth"]).stop is True


def test_cli_runs_on_sample_file(tmp_path):
    out = tmp_path / "LLY"
    rc = CLI.main(["--ticker", "LLY", "--findings", str(EX / "findings_LLY_old.jsonl"), "--moves", str(EX / "moves_LLY.json"),
                   "--out", str(out)])
    assert rc == 0
    d = json.loads((out / "decide.json").read_text())
    assert d["ticker"] == "LLY" and d["cash_and_equivalents"] == 8950
    assert len(d["rejected"]) == 2 and len(d["ranked"]) == 3
    assert set(d["chosen"]["five"]) == {"ev", "car", "payback_month", "spread", "mcda"}
    evs = [r["ev"] for r in d["ranked"]]
    assert evs == sorted(evs, reverse=True)
    md = (out / "decide.md").read_text()
    for h in ("## Recommended move", "### Budget", "### Return math", "## Five numbers", "## Kill signals", "**Sources**"):
        assert h in md
    assert md.count("verified: unverified") >= 1
