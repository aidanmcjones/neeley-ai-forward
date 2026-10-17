import pandas as pd

from agent.needle import backtest as bt


def test_quarter_math():
    assert bt._shift("2025Q4", 1) == "2026Q1"
    assert bt._shift("2026Q1", -4) == "2025Q1"
    assert bt._prior_quarters("2025Q4", 3) == ["2025Q1", "2025Q2", "2025Q3"]


def test_signal_and_event_rules():
    q = [bt._shift("2020Q1", i) for i in range(16)]
    df = pd.DataFrame({"revenue": [100.0] * 16, "cogs": [30.0] * 16, "inventory": [50.0] * 16,
                       "receivables": [40.0] * 16, "assets": [1000.0] * 16, "impairment": [0.0] * 16}, index=q)
    df.loc["2021Q1", "inventory"] = 60.0                      # +20% vs flat revenue -> signal
    assert bt.signals_at(df, "2021Q1")["inventory_outpaces_revenue"]
    assert not bt.signals_at(df, "2021Q2")["inventory_outpaces_revenue"]
    df.loc["2022Q2", "impairment"] = 25.0                     # 2.5% of assets -> event within 8 quarters
    ev = bt.events_after(df, "2021Q1")
    assert ev["impairment"] == "2022Q2" and ev["any"] == "2022Q2"
    assert bt.events_after(df, "2023Q1") is None              # forward window not fully observed


def test_point_in_time_uses_first_filing():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"start": "2021-01-01", "end": "2021-03-31", "val": 100, "filed": "2021-05-01"},
        {"start": "2021-01-01", "end": "2021-03-31", "val": 90, "filed": "2022-05-01"},  # later restatement
    ]}}}}}
    assert bt.pit_series(facts, ["Revenues"], stock=False)["2021Q1"] == 100


def test_wilson_interval():
    lo, hi = bt.wilson(50, 100)
    assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60
