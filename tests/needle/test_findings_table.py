"""Pitch findings table (agent/needle/quant/findings_table.py): ranked by dollar impact, needle by the plain rule
"the biggest-impact finding that analysts asked about least"."""

import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from agent.needle.quant import findings_table as FT
from tests.needle.test_markers import lookalikes, markers, footnotes

ROOT = Path(__file__).resolve().parents[2]


def row(id_, eps, a, blocked=False, nq=""):
    imp = NS(d_eps={"base": eps}, d_oi={"base": eps * 1000}, channel="x", formula="")
    return NS(id=id_, impact=imp, vector={"a": a}, needle_blocked=blocked, not_quantified=nq)


def test_rank_by_impact_and_plain_needle_rule():
    rows = [row("small_obscure", 0.05, 0.0), row("big_known", 0.90, 0.6), row("mid_obscure", 0.30, 0.0),
            row("blocked", 2.0, 0.0, blocked=True), row("unquantified", 0.0, 0.0, nq="no channel")]
    assert [f.id for f in FT.rank(rows)] == ["blocked", "big_known", "mid_obscure", "small_obscure", "unquantified"]
    # lowest analyst share among quantified, non-blocked rows is 0.0; the biggest of those is mid_obscure
    assert FT.pick_needle(rows).id == "mid_obscure"
    assert FT.pick_needle([row("u", 0.0, 0.0, nq="x")]) is None


def _check_rule(d):
    rows = d["rows"]
    eps = [r["d_eps_base_abs"] for r in rows]
    assert eps == sorted(eps, reverse=True) and [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    cand = [r for r in rows if r["d_eps_base_abs"] > 0 and not r["needle_blocked"]]
    needles = [r for r in rows if r["needle"]]
    if not cand:
        assert d["needle_id"] is None and not needles
        return
    lo = min(r["analyst_share_asked"] for r in cand)
    assert len(needles) == 1 and needles[0]["id"] == d["needle_id"]
    by = {r["id"]: r for r in rows}
    if d.get("needle_source") == "red_team":     # the human read governs: Parker's best needle, gated and slide-ready
        assert d["needle_id"] == d["red_team_needle_id"] and d["needle_reason"].startswith("red-team read")
        n = by[d["plain_rule_needle_id"]]          # the plain-rule pick is still recorded and must obey the rule
    else:
        assert d["needle_reason"] == FT.PLAIN_REASON and d["needle_id"] == d["plain_rule_needle_id"]
        n = needles[0]
    assert n["analyst_share_asked"] == lo
    assert n["d_eps_base_abs"] == max(r["d_eps_base_abs"] for r in cand if r["analyst_share_asked"] == lo)


@pytest.mark.parametrize("t", ["AMGN", "MRK", "LLY"])
def test_findings_table_output_is_impact_ranked_with_markers(t):
    p = ROOT / "out" / t / "findings_table.json"
    if not p.exists():
        pytest.skip("out/<T>/findings_table.json not generated (gitignored)")
    d = json.loads(p.read_text())
    assert d["rank_basis"] == "impact" and d["numeric_check"]["status"] in ("passed", "no_numbers")
    assert all("S" not in r for r in d["rows"])
    _check_rule(d)
    md = (ROOT / "out" / t / "findings_table.md").read_text()
    assert not lookalikes(md)
    notes = footnotes(md)
    assert all(n in notes for n in markers(md))
