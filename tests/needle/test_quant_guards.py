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
