"""Guards from the red-team of the old scorer (agent-chat #19) and the nugget ingest path."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.needle.quant import guards as G
from agent.needle.quant.data import MOAT
from agent.needle.schema import Evidence, Signal

need_moat = pytest.mark.skipif(not (MOAT / "tables" / "ibes_actuals.csv").exists(), reason="moat data not present")
SAMPLE = Path(__file__).parent / "data" / "nuggets_sample.jsonl"


def S(kind, **kw):
    base = dict(ticker="ZZZ", detector="forensics", kind=kind, period="2026Q2", value=None, detail="", evidence=[],
                meta={})
    base.update(kw)
    return Signal(**base)


def test_guard6_twin_with_same_number_dropped():
    base = S("receivables_outpace_revenue", value=0.147)
    twin = S("rec_gap_peer_outlier", value=0.147)
    other = S("rec_gap_peer_outlier", value=0.20)
    assert G.twin_guard(twin, [base, twin])[0] == "drop"
    assert G.twin_guard(other, [base, other]) is None


def test_guard8_undirected_mdna_not_needle():
    assert G.needle_direction_guard(S("mdna_added", detector="drift", detail="new paragraph in MD&A"))[0] == "no_needle"
    assert G.needle_direction_guard(S("mdna_intensified", detector="drift",
                                      detail="stronger wording in MD&A; new risk vocabulary: decline")) is None
    assert G.needle_direction_guard(S("risk_added", detector="drift", detail="new paragraph in risk factors")) is None


def test_guard9_paragraph_filter():
    toc = "Strategic Aspirations 13 Strategic Aspirations 2025 14 Financial performance 20 Commercial execution 26"
    prose = "We expect pricing pressure in the United States to continue through 2027 as rebates rise further."
    assert not G.is_prose(toc) and not G.is_prose("Item 7 ........ 45 Item 8 ........ 60")
    assert G.is_prose(prose)
    assert G.paragraph_guard(S("risk_added", detector="drift", evidence=[Evidence("d", 1, toc)]))[0] == "drop"
    assert G.paragraph_guard(S("risk_added", detector="drift", evidence=[Evidence("d", 1, prose)])) is None


@need_moat
def test_guard2_dio_peer_on_revenue_lly():
    g = G.dio_peer_on_revenue(S("dio_peer_outlier", ticker="LLY"))
    assert g and g[0] == "drop" and "on revenue" in g[1]


@need_moat
@pytest.mark.parametrize("t", ["PFE", "MRK"])
def test_guard3_tax_on_small_or_negative_pretax(t):
    g = G.tax_guard(S("tax_rate_shift", ticker=t))
    assert g and g[0] == "drop" and "under 5% of revenue" in g[1]


@need_moat
def test_guard4_iprd_one_off_mrk():
    charge, sent, no_tax = G.iprd_charge("MRK", "2026Q2")
    assert round(charge) == 5700 and no_tax
    assert G.iprd_guard(S("rnd_shift", ticker="MRK"))[0] == "context"
    assert G.iprd_guard(S("tax_rate_shift", ticker="MRK"))[0] == "context"


@need_moat
def test_guard5_annual_row_reads_annual_table():
    from agent.needle.quant import find
    sig = S("receivables_outpace_revenue", ticker="AZN", period="2025", value=0.147)
    yb = find.yoy_basis(sig)
    assert yb and "annual revenue" in yb["sentence"] and not yb["mismatch"]
    bad = S("receivables_outpace_revenue", ticker="AZN", period="2025", value=0.30)
    assert "period mismatch" in find.yoy_basis(bad)["mismatch"]


def test_nuggets_load_two_rows():
    from agent.needle.quant.run import load_nuggets
    rows = load_nuggets(SAMPLE)
    assert len(rows) == 2 and all(r.detector == "nuggets" for r in rows)
    assert rows[0].meta["part2_hook"] == "none" and rows[0].evidence[0].page == 41


@need_moat
def test_nuggets_go_through_scoring_and_gate():
    from agent.needle.quant.run import load_nuggets, score_ticker
    _, fs, wh = score_ticker("MRK", write=False, extra_signals=load_nuggets(SAMPLE))
    shown = [f for f in fs if f.detector == "nuggets"]
    held = [f for f in wh if f.detector == "nuggets"]
    assert any("Terns" in f.sentence for f in shown + held)
    assert any("invented" in f.sentence for f in held)          # the citation gate withholds the fake quote
    terns = [f for f in shown + held if "Terns" in f.sentence][0]
    assert terns.S == 0 and terns.guard in ("drop", "context")  # guards 3 and 4 apply to nuggets too


def test_needle_branch_id_scheme():
    import hashlib
    from agent.needle.quant.run import needle_branch_id
    from agent.needle.schema import Signal
    s = Signal(ticker="AMGN", detector="forensics", kind="receivables_outpace_revenue", detail="x")
    six = int(hashlib.sha256(b"receivables_outpace_revenue|x").hexdigest(), 16) % 10 ** 6
    assert needle_branch_id(s) == f"AMGN-forensics-{six:06d}"


def test_nugget_impact_eps_translation_and_cash_only():
    from types import SimpleNamespace
    from agent.needle.quant import find
    co = SimpleNamespace(tax=0.2, shares=1000.0, citations={}, flags=[])
    imp, am, nq = find.nugget_impact(co, {"id": "X-nugget-001", "ticker": "X", "signal_family": "gtn",
                                          "impact": {"line": "revenue", "bull": 100, "base": 200, "bear": 400}})
    assert not nq and abs(imp.d_eps["base"] - 200 * 1.0 * 0.8 / 1000) < 1e-12
    assert imp.d_rev == {"bull": 100, "base": 200, "bear": 400} and am
    imp, _, nq = find.nugget_impact(co, {"id": "X-nugget-002", "signal_family": "gtn",
                                         "impact": {"line": "free_cash_flow", "base": 5000}})
    assert nq.startswith("not quantified on EPS") and not imp.quantified
    imp, _, _ = find.nugget_impact(co, {"id": "X-nugget-003", "signal_family": "footnotes", "signal_kind": "tax_dispute",
                                        "impact": {"line": "eps", "bull": 0, "base": 1300, "bear": 3200}})
    assert abs(imp.d_eps["base"] - 1.3) < 1e-12 and imp.d_oi["base"] == 0   # tax item: no tax shield, below OI


def test_nuggets_dir_sets_best_needle():
    from pathlib import Path
    from agent.needle.quant.run import load_nuggets
    d = Path(__file__).resolve().parents[2] / "docs" / "nuggets"
    if not (d / "best_needle.json").exists():
        pytest.skip("docs/nuggets not present")
    rows = load_nuggets(d)
    assert len(rows) == 97
    best = [r.meta["nugget"]["id"] for r in rows if r.meta["nugget"].get("best_needle")]
    assert sorted(best) == sorted(["MRK-nugget-001", "JNJ-nugget-010", "PFE-nugget-001", "BMY-nugget-001",
                                   "AMGN-nugget-006", "NVO-nugget-001", "LLY-nugget-002", "ABBV-nugget-001",
                                   "GILD-nugget-001", "AZN-nugget-010"])


def test_marker_label_prints_its_text():
    from agent.needle.cite import render
    assert render._assumption_tag("marker: no public MFN rate; terms confidential (internal 0.65%)") == \
        "assumption: no public MFN rate; terms confidential"
    assert render.is_marker("[assumption: no public MFN rate; terms confidential]")


@need_moat
def test_mfn_placeholder_rows_carry_the_explicit_marker():
    from agent.needle.quant import data, find
    from agent.needle.cite.render import claim_markup
    from agent.needle.cite.locator import Claim
    for t in ("GILD", "AMGN"):
        rows = find.mfn_findings(t, data.company(t))
        assert rows
        f = rows[0]
        assert getattr(f, "mfn_placeholder", False) and f.needle_blocked and f.vector["M"] > 0
        texts, _ = claim_markup([Claim(f.impact.formula, [], derived=f.derived, assumptions=f.assumptions,
                                       where="impact.formula")])
        assert "[assumption: no public MFN rate; terms confidential]" in texts[0]
        assert "$" not in f.sentence.split("Direction:")[1]


@need_moat
def test_gild_biktarvy_settlement_date_and_first_year_precedents():
    from agent.needle.quant import data, find
    f = [x for x in find.ira_findings("GILD", data.company("GILD")) if x.product == "Biktarvy"][0]
    assert "April 1, 2036" in f.sentence and "22%" in f.sentence
    pages = {(c.canonical_id, c.page) for c in f.citations if c.verification.ok}
    assert ("GILD:10k_FY2025.md", 37) in pages and ("AMGN:10q_2026Q2.md", 40) in pages \
        and ("BMY:10q_2026Q2.md", 35) in pages


@need_moat
def test_receivables_rows_explained_by_footnote_amgn_azn():
    from agent.needle.quant import run
    for t, net in (("AMGN", 587), ("AZN", -60)):
        _, fs, wh = run.score_ticker(t, write=False)
        rec = [f for f in fs + wh if f.kind == "receivables_outpace_revenue"]
        assert rec
        for f in rec:
            assert f.needle_blocked and getattr(f, "footnote_read", {}).get("status") == "explained by footnote"
            assert round(f.footnote_read["net"]) == net
    amgn = [f for f in run.score_ticker("AMGN", write=False)[1] if f.kind == "receivables_outpace_revenue"][0]
    assert amgn.impact.channel == "receivables_net" and 0 < amgn.impact.d_eps["base"] < 1.0


@need_moat
def test_findings_table_every_row_has_a_gated_peer_comparison():
    from agent.needle.quant import findings_table as FT, run
    _, fs, _ = run.score_ticker("AMGN", write=False)
    md, js = FT.build("AMGN", fs)
    assert js["rows"] and all(r["peer_comparison"] for r in js["rows"])
    rec = [r for r in js["rows"] if r["signal_kind"] == "tax_rate_shift"]
    assert rec and "median" in rec[0]["peer_comparison"] and "[derived" in rec[0]["peer_comparison_marked"]
    assert js["numeric_check"]["status"] in ("passed", "no_numbers") and not js["failed"]
    assert "AMGN USD" not in md and "USD " in md     # currency printed with the amount


@need_moat
def test_nvo_amounts_print_in_dkk():
    from agent.needle.quant import findings_table as FT
    assert FT._currency("NVO") == "DKK" and FT._currency("MRK") == "USD"


def test_needle_red_team_when_gated_and_slide_ready_else_plain_rule():
    from types import SimpleNamespace
    from agent.needle.quant import findings_table as FT
    rt = FT._red_team()
    if "MRK" not in rt:
        pytest.skip("docs/nuggets/best_needle.json not present")
    nid = rt["MRK"][0]
    ok = SimpleNamespace(id="a", nugget={"id": nid, "slide_ready": True, "verdict": "verified"}, merged_into="")
    other = SimpleNamespace(id="b", nugget={}, merged_into="")
    assert FT.red_team_pick("MRK", [other, ok], [])[0] is ok
    bad = SimpleNamespace(id="a", nugget={"id": nid, "slide_ready": False, "verdict": "verified"}, merged_into="")
    assert FT.red_team_pick("MRK", [other, bad], [])[0] is None          # not slide-ready: plain rule
    assert FT.red_team_pick("MRK", [other], [])[0] is None               # failed the gate (absent): plain rule
    gone = SimpleNamespace(id="g", nugget={"id": nid, "slide_ready": True, "verdict": "verified"}, merged_into="b")
    assert FT.red_team_pick("MRK", [other], [gone])[0] is other          # merged as one fact: the kept row
