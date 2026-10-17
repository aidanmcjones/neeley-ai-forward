import random

import pytest

from agent.needle import pages, xbrl
from agent.needle.schema import Evidence


@pytest.mark.parametrize("ticker", ["AZN", "JNJ"])
def test_random_page_snippets_verify(ticker):
    """20 random snippets taken from real pages must verify against their own page, with a printed citation."""
    d = pages.docs(ticker)
    assert d, f"no documents for {ticker}"
    rng = random.Random(7)
    cands = [(i, n, p) for i, doc in d.items() if doc["row"]["doc_type"] != "transcript"
             for n, (_, t) in doc["pages"].items() for p in pages.paragraphs(t, 25)]
    for doc_id, n, para in rng.sample(cands, 20):
        quote = " ".join(para.split()[:20])
        ev = Evidence(doc_id, n, quote)
        status, reason = pages.check(ev, d)
        assert status == "verified", (doc_id, n, reason)
        assert ev.citation.startswith(ticker)


def test_wrong_page_rejected():
    d = pages.docs("JNJ")
    doc_id, doc = next((i, x) for i, x in d.items() if x["row"]["doc_type"] == "annual_report")
    n, (_, t) = next((n, v) for n, v in doc["pages"].items() if pages.paragraphs(v[1], 25))
    quote = " ".join(pages.paragraphs(t, 25)[0].split()[:20])
    other = next(m for m in doc["pages"] if m != n and pages.find_page({"pages": {m: doc["pages"][m]}}, quote) is None)
    status, reason = pages.check(Evidence(doc_id, other, quote), d)
    assert status == "rejected" and "not page" in reason


def test_panel_matches_10q_text():
    """Hand-checked against the 10-Q text: BMY Q2'26 revenue $12,973M, JNJ $25,310M, ABBV receivables $13,824M."""
    assert xbrl.panel("BMY").at["2026Q2", "revenue"] == 12_973_000_000
    assert xbrl.panel("JNJ").at["2026Q2", "revenue"] == 25_310_000_000
    assert xbrl.panel("ABBV").at["2026Q2", "receivables"] == 13_824_000_000


def test_twenty_f_annuals():
    a = xbrl.annual("AZN")
    assert a.at["2025", "revenue"] == 58_739_000_000 and a.at["2025", "inventory"] == 6_557_000_000
