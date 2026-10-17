"""Does the findings verifier catch the mistakes the case warns about? No API key needed.

Takes real passages from the corpus as true findings, then makes broken copies of each:
wrong page, altered number, paraphrased quote, invented quote, missing speaker, fool.com takeaways.
Every true finding must verify and every broken one must be caught.

Run: python -m eval.test_verifier [--ticker BMY]
"""

import argparse
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.findings import _numbers, load_docs, verify  # noqa: E402


def passage(text, rng):
    """A 30-word run from a page that contains a number, or None."""
    words = text.split()
    for _ in range(50):
        if len(words) < 60:
            return None
        i = rng.randrange(0, len(words) - 30)
        q = " ".join(words[i:i + 30])
        if re.search(r"\d{2,}", q) and "[[" not in q:
            return q
    return None


def cases(ticker, rng, n=8):
    docs = load_docs(ticker)
    out = []
    reports = [d for d in docs if docs[d]["row"]["doc_type"] in ("annual_report", "quarterly_report")]
    for doc_id in reports:
        pages = list(docs[doc_id]["pages"].items())
        rng.shuffle(pages)
        for n_page, (_, text) in pages:
            q = passage(text, rng)
            if not q:
                continue
            page_nums = _numbers(text)
            nums = [x for x in _numbers(q) if len(x) >= 3 and not re.fullmatch(r"(19|20)\d\d", x)]
            others = [p for p in docs[doc_id]["pages"] if p != n_page and q not in docs[doc_id]["pages"][p][1]]
            # A number that is clearly a figure, whose bumped value is not already on the page.
            nums = [x for x in nums if str(int(float(x)) + 7) not in page_nums and re.search(rf"(?<![\d,.]){re.escape(x)}(?![\d])", q)]
            if not nums or not others:
                continue
            num = nums[0]
            src = f"{doc_id}#p{n_page}"
            base = {"source": src, "quote": q, "figures": [num]}
            bumped = str(int(float(num)) + 7)
            changed = re.sub(rf"(?<![\d,.]){re.escape(num)}(?![\d])", bumped, q, count=1)
            out += [
                ("true finding", base, "verified"),
                ("wrong page", {**base, "source": f"{doc_id}#p{others[0]}"}, "rejected"),
                ("altered number", {**base, "figures": [bumped]}, "needs_human"),
                ("number changed inside quote", {**base, "quote": changed}, "rejected"),
                ("paraphrased quote", {**base, "quote": " ".join(reversed(q.split()))}, "rejected"),
                ("invented page", {**base, "source": f"{doc_id}#p9999"}, "rejected"),
            ]
            break
        if len(out) >= n * 6:
            break

    calls = [d for d in docs if docs[d]["row"]["doc_type"] == "transcript"]
    for doc_id in calls:
        flat_pages = docs[doc_id]["pages"]
        n_page, (_, text) = next(iter(flat_pages.items()))
        low = text.lower()
        start = low.find("full conference call transcript")
        if start > 0:  # fool.com: quote from the LLM takeaways above the call
            q = " ".join(text[:start].split()[-40:-10])
            out.append(("fool.com takeaways quote", {"source": f"{doc_id}#p{n_page}", "quote": q, "speaker": "Anyone"}, "rejected"))
        body = text[start:] if start > 0 else text
        q = passage(body, rng)
        if q:
            out.append(("call quote, no speaker", {"source": f"{doc_id}#p{n_page}", "quote": q, "speaker": ""}, "needs_human"))
    return docs, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="BMY")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    docs, tests = cases(a.ticker.upper(), random.Random(a.seed))
    passed = 0
    for name, finding, expected in tests:
        got, reason, _ = verify(finding, docs)
        ok = got == expected
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:30} expected {expected:12} got {got:12} {reason[:70]}")
    print(f"\n{passed}/{len(tests)} correct on {a.ticker.upper()}")
    sys.exit(0 if passed == len(tests) else 1)


if __name__ == "__main__":
    main()
