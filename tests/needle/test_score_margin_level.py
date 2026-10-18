"""Regression: a gross-margin LEVEL peer outlier must not be scored as a margin change x TTM revenue.

Before the fix, LLY's "Gross margin 85.8% vs peer median 74.1%" row got 0.858 x TTM revenue (about $68B) of
"impact", capped I_norm at 1.0 and supplied 80.3 percent of LLY's league score (docs/quant_model.md section 10.2).
"""

import pandas as pd

from agent.needle import score
from agent.needle.schema import Signal


def _panel():
    q = [f"{y}Q{i}" for y in (2024, 2025, 2026) for i in (1, 2, 3, 4)][:10]
    return pd.DataFrame({"revenue": [20e9] * len(q), "cogs": [3e9] * len(q)}, index=q)


def test_margin_level_outlier_has_no_dollar_path():
    sig = Signal(ticker="LLY", detector="forensics", kind="gross_margin_peer_outlier", period="2026Q2",
                 value=0.858, peer_median=0.741, peer_z=1.85)
    dollars, formula = score._impact(sig, _panel(), 30e9)
    assert dollars is None
    assert "level" in formula


def test_margin_change_still_scored_as_change():
    sig = Signal(ticker="LLY", detector="forensics", kind="gross_margin_drop", period="2026Q2", value=-0.03)
    dollars, _ = score._impact(sig, _panel(), 30e9)
    assert abs(dollars - 0.03 * 80e9) < 1
