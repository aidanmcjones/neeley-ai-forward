"""Trust layer: the verifier must kill seeded AI-style errors, and the ledger must detect tampering."""

import json
import re

from agent.needle import audit, pages
from agent.needle.schema import Evidence


def _income_page(d):
    """A JNJ 10-Q page with a quotable sentence that contains a dollar figure."""
    for doc_id, doc in d.items():
        if doc["row"]["doc_type"] != "quarterly_report":
            continue
        for n, (_, t) in doc["pages"].items():
            for para in pages.paragraphs(t, 25):
                m = re.search(r"\$\s?\d{1,3}(,\d{3})+|\$\s?\d+\.\d+ billion", para)
                if m:
                    words = para.split()
                    i = len(para[:m.start()].split())
                    quote = " ".join(words[max(0, i - 10): i + 12])
                    return doc_id, n, quote, m.group(0)
    raise AssertionError("no figure-bearing paragraph found")


def test_seeded_errors_are_caught():
    d = pages.docs("JNJ")
    doc_id, n, quote, fig = _income_page(d)
    good = Evidence(doc_id, n, quote, figures=[fig])
    assert pages.check(good, d)[0] == "verified"

    # 1. wrong page: same quote, cited one page later
    wrong_page = n + 1 if n + 1 in d[doc_id]["pages"] else n - 1
    assert pages.check(Evidence(doc_id, wrong_page, quote), d)[0] == "rejected"

    # 2. altered number inside the quote (the typical "AI rounded it" error)
    digits = re.search(r"\d", quote)
    bumped = quote[:digits.start()] + str((int(quote[digits.start()]) + 1) % 10) + quote[digits.start() + 1:]
    assert pages.check(Evidence(doc_id, n, bumped), d)[0] == "rejected"

    # 3. figure that is not on the cited page (e.g. a prior-year number pasted in)
    assert pages.check(Evidence(doc_id, n, quote, figures=["987,654"]), d)[0] == "needs_human"

    # 4. invented quote
    assert pages.check(Evidence(doc_id, n, "Management expects gross-to-net erosion to accelerate sharply "
                                          "next year across the entire immunology portfolio"), d)[0] == "rejected"


def test_ledger_detects_tampering(tmp_path):
    led = tmp_path / "ledger.jsonl"
    for i in range(5):
        audit.append("signal", {"i": i}, led)
    assert audit.verify_chain(led) == (True, 5, None)
    lines = led.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[2])
    rec["payload"]["i"] = 99
    lines[2] = json.dumps(rec)
    led.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, _, bad = audit.verify_chain(led)
    assert not ok and bad == 3


def test_seal_is_order_independent():
    assert audit.seal({"a": 1, "b": 2}) == audit.seal({"b": 2, "a": 1})
