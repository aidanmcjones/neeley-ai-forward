"""The trial's quote checker must log invented / misplaced quotes as AI-caught, with no API call."""

from agent.needle import pages, trial
from agent.needle.schema import Finding


def test_quote_checker_catches_bad_quotes():
    d = pages.docs("JNJ")
    doc_id, doc = next((i, x) for i, x in d.items() if x["row"]["doc_type"] == "quarterly_report")
    n, (_, text) = next((n, v) for n, v in doc["pages"].items() if pages.paragraphs(v[1], 25))
    real = " ".join(pages.paragraphs(text, 25)[0].split()[:20])
    out = {"quotes": [{"source": f"{doc_id}#p{n}", "quote": real},
                      {"source": f"{doc_id}#p{n}", "quote": "Management expects severe erosion across every franchise next year"},
                      {"source": "not-a-document", "quote": real},
                      {"source": "drug:eliquis:label_sections.md", "quote": "Eliquis cures atrial fibrillation in all patients"}]}
    caught = []
    ok = trial._check_quotes("prosecutor", out, d, Finding("JNJ-x", "JNJ", "f", "k"), caught)
    assert ok == 1 and len(caught) == 3
    assert {c["reason"] for c in caught} >= {"source id is not a real document page", "quote not found in the FDA label"}


def test_dry_run_builds_context_for_labels():
    r = trial.run("AZN", top=5, dry_run=True)
    assert r and all(x["context_chars"] > 0 for x in r)
