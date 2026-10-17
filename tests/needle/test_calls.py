import pytest

from agent.needle import pages
from agent.needle.detect import SKIP_DOCS
from agent.needle.detect import calls


@pytest.fixture(scope="module")
def jnj():
    return calls.run("JNJ")


def test_jnj_has_signals(jnj):
    assert len(jnj) >= 1


def test_jnj_evidence_valid(jnj):
    docs = pages.docs("JNJ", ("transcript", "earnings_release"))
    for s in jnj:
        for ev in s.evidence:
            assert ev.doc_id not in SKIP_DOCS
            assert 20 <= len(ev.quote.split()) <= 45
            status, _ = pages.check(ev, docs)
            assert status in ("verified", "needs_human")


def test_azn_no_bad_transcripts():
    sigs = calls.run("AZN")
    bad = {"AZN:transcripts/2026Q1_transcript.md", "AZN:transcripts/2025Q3_transcript.md"}
    for s in sigs:
        for ev in s.evidence:
            assert ev.doc_id not in bad
