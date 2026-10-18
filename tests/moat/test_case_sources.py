"""Offline checks for agent.moat.case_sources (no network)."""
import pytest

from agent.moat import cite as C

pytestmark = pytest.mark.skipif(not C.DB.exists(), reason="build the index first")


def test_imports():
    from agent.moat import case_sources as S
    assert callable(S.build)


def test_shortlist_rows_no_fda():
    from agent.moat import case_sources as S
    md, gaps, rows = S.build(fda=False)
    assert len(rows) == 10
    assert "## Gaps" in md and isinstance(gaps, list)
