import pandas as pd

from agent.needle import backtest as bt


def _panel(n=16):
    q = [bt._shift("2020Q1", i) for i in range(n)]
    return pd.DataFrame({"revenue|0": [100.0] * n, "cogs|0": [30.0] * n, "inventory|0": [50.0] * n,
                         "receivables|0": [40.0] * n, "assets|0": [1000.0] * n, "impairment|0": [0.0] * n}, index=q)


def test_quarter_math():
    assert bt._shift("2025Q4", 1) == "2026Q1"
    assert bt._prior_quarters("2025Q4", 3) == ["2025Q1", "2025Q2", "2025Q3"]
    assert bt._qlabel("2023-01-01") == "2022Q4"      # 52/53-week calendar end snaps back
    assert bt._qlabel("2023-03-31") == "2023Q1"


def test_signal_and_event_rules():
    df = _panel()
    df.loc["2021Q1", "inventory|0"] = 60.0                    # +20% vs flat revenue -> signal
    assert bt.signals_at(df, "2021Q1")["inventory_outpaces_revenue"]
    assert not bt.signals_at(df, "2021Q2")["inventory_outpaces_revenue"]
    df.loc["2022Q2", "impairment|0"] = 25.0                   # 2.5% of assets -> event within 8 quarters
    ev = bt.events_after(df, "2021Q1")
    assert ev["impairment"] == "2022Q2" and ev["hard"] == "2022Q2"
    assert bt.events_after(df, "2022Q3") is None              # 5 of 8 forward quarters, still listed: unobserved
    assert bt.events_after(df, "2022Q3", exited=True) is not None  # exited firm: >= 4 observed quarters count
    assert bt.events_after(df, "2023Q1", exited=True) is None      # only 3 observed: too short even for exits


def test_events_do_not_overlap_signal_quarter():
    """A one-quarter revenue dip AT t must not count as a future revenue_drop event."""
    df = _panel()
    df.loc["2021Q1", "revenue|0"] = 10.0
    assert "revenue_drop" not in bt.events_after(df, "2021Q1")


def test_concept_switch_is_not_a_level_change():
    df = _panel()
    df["revenue|1"] = None
    for q in df.index[8:]:                       # concept switch in 2022: old tag stops, new tag at 2x level
        df.loc[q, "revenue|1"], df.loc[q, "revenue|0"] = 200.0, None
    assert bt._yoy(df, "revenue", "2022Q1") is None          # no single concept spans the switch
    assert bt._yoy(df, "revenue", "2023Q1") == 0.0           # same concept on both sides


def test_point_in_time_uses_first_timely_filing():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"start": "2021-01-01", "end": "2021-03-31", "val": 100, "filed": "2021-05-01"},
        {"start": "2021-01-01", "end": "2021-03-31", "val": 90, "filed": "2022-05-01"},   # later restatement
        {"start": "2020-01-01", "end": "2020-03-31", "val": 80, "filed": "2021-05-01"},   # comparative, 396 days late
    ]}}}}}
    s = bt.pit_series(facts, ["Revenues"], stock=False)
    assert s["2021Q1"] == 100 and "2020Q1" not in s


def test_wilson_interval():
    lo, hi = bt.wilson(50, 100)
    assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60
