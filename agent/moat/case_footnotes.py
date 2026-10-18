"""Footnote extracts on four topics from the two latest annual reports and the latest quarterly/interim report.

Answers: what do the notes say about litigation reserves, partner royalty splits, contingent consideration (payments
owed on past acquisitions) and tax-rate changes, and what changed against the prior year?

    from agent.moat.case_footnotes import footnotes
    footnotes("JNJ", topic="litigation", k=10)
    footnotes(ticker, topic="all"|"litigation"|"royalty"|"contingent_consideration"|"tax_rate", docs=None, k=40)

`docs` optionally overrides the doc_id list (default: annual_report docs of the latest two fiscal years, plus the
latest quarterly_report or interim_report). `k` is the total cap for "all" (split evenly across topics) or the cap
for a single topic.

Row fields: ticker, kind, text (1 to 3 sentences, under 600 chars, a verbatim substring of the page), numbers (dollar
amounts and percentages found in text), doc_year, topic, citation, url, locator/source_id (doc_id#p<page>),
quote_grade "", license, plus new_vs_prev, also_in_prev_year, prev_numbers, doc_id, page_no.
kind is one of: "footnote" (latest annual report), "latest_10q" (latest quarterly/interim report),
"dropped_from_latest" (prior-year sentence with no near match in the latest annual report).
Rows pass cite.verify_quote(text, doc_id, page_no).

Text-only by design: no XBRL or companyfacts numbers are pulled. Use the financial tables helpers for those.

CLI: python -m agent.moat.case_footnotes JNJ [topic] [-k 20]
"""

import re
import sys

from agent.moat import cite as C

TOPICS = {
    "litigation": ['"accrued" NEAR "litigation"', '"legal reserve"', '"loss contingency"', '"probable and estimable"',
                   '"accrual" NEAR "lawsuit"', '"talc"', '"opioid"', '"Zantac"', '"antitrust"'],
    "royalty": ['"royalt"* NEAR "percent"', '"tiered" NEAR "royalt"*', '"royalty rate"', '"profit share"',
                '"collaboration" NEAR "royalt"*', '"royalt"* NEAR "licens"*', '"royalt"* NEAR "net sales"',
                '"royalt"* NEAR "sales"', '"royalt"* NEAR "alliance"', '"royalt"* NEAR "partner"'],
    "contingent_consideration": ['"contingent consideration"', '"milestone payments" NEAR "acquisition"',
                                 '"fair value" NEAR "contingent"', '"earn-out"'],
    "tax_rate": ['"effective tax rate"', '"Pillar Two"', '"GILTI"', '"tax reform"', '"unrecognized tax benefits"',
                 '"repatriation"', '"Puerto Rico" NEAR "tax"', '"tax rate" NEAR "increase"'],
}
NUM_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:billion|million|thousand|bn|mn|m)\b)?|\d+(?:\.\d+)?\s?(?:%|percent\b)",
                    re.I)
SENT_RE = re.compile(r"(?<=[.;!?])\s+(?=[A-Z$(“\"])")
MAXLEN = 600


def _terms(q):
    """Quoted terms of an FTS query -> compiled regexes (trailing * means prefix)."""
    out = []
    for t, star in re.findall(r'"([^"]+)"(\*?)', q):
        pat = re.escape(t).replace(r"\ ", r"\s+")
        out.append(re.compile(r"\b" + pat + (r"\w*" if star else r"\b"), re.I))
    return out


def select_docs(ticker):
    """({year: [annual doc_ids]} for the latest two fiscal years, latest quarterly/interim doc_id or None)."""
    rows = C.db().execute("SELECT doc_id, doc_type, period, filed FROM docs WHERE ticker=? AND superseded_by='' "
                          "AND doc_type IN ('annual_report','quarterly_report','interim_report')", (ticker.upper(),)).fetchall()
    ann = [r for r in rows if r["doc_type"] == "annual_report"]
    years = sorted({r["period"][:4] for r in ann}, reverse=True)[:2]
    by_year = {y: [r["doc_id"] for r in ann if r["period"][:4] == y] for y in years}
    qs = [r for r in rows if r["doc_type"] != "annual_report"]
    q = max(qs, key=lambda r: (r["filed"] or "", r["period"] or "")) if qs else None
    return by_year, (q["doc_id"] if q else None)


def _sentences(text):
    out = []
    for line in re.split(r"\n+", text):
        line = line.strip()
        if not line or line.startswith("|") or line.startswith("#"):
            continue
        out += [s.strip() for s in SENT_RE.split(" ".join(line.split())) if s.strip()]
    return out


def _window(sents, i, regs):
    """Smallest 1 to 3 sentence window around i that holds all terms, under MAXLEN."""
    for lo, hi in ((i, i), (i - 1, i), (i, i + 1), (i - 1, i + 1)):
        if lo < 0 or hi >= len(sents):
            continue
        t = " ".join(sents[lo:hi + 1])
        if len(t) < MAXLEN and all(r.search(t) for r in regs):
            return t
    s = sents[i]
    if len(s) < MAXLEN:
        return s
    m = regs[0].search(s)
    a = max(0, min(m.start() - 200, len(s) - MAXLEN + 1)) if m else 0
    return s[a:a + MAXLEN - 1].strip()


def _pages(doc_ids, fts, limit=25):
    ph = ",".join("?" * len(doc_ids))
    return C.db().execute(
        f"SELECT p.doc_id, p.page_no, p.text FROM pages_fts JOIN pages p ON p.id=pages_fts.rowid "
        f"WHERE pages_fts MATCH ? AND p.doc_id IN ({ph}) ORDER BY bm25(pages_fts) LIMIT ?", [fts, *doc_ids, limit]).fetchall()


def _sig(text):
    """Digit-masked token set for near-duplicate detection."""
    return frozenset(re.sub(r"\d+", "#", w) for w in re.findall(r"[A-Za-z0-9$%.,]+", text.lower()))


def _sim(a, b):
    return len(a & b) / max(1, len(a | b))


def _extract(doc_ids, topic):
    """Candidate windows for a topic: [{text, doc_id, page_no, score}], best first."""
    cands = {}
    for q in TOPICS[topic]:
        regs = _terms(q)
        for r in _pages(doc_ids, q):
            sents = _sentences(r["text"])
            for i, s in enumerate(sents):
                if not any(x.search(s) for x in regs):
                    continue
                t = _window(sents, i, regs)
                if not all(x.search(t) for x in regs):
                    continue
                c = cands.setdefault((r["doc_id"], r["page_no"], t),
                                     {"text": t, "doc_id": r["doc_id"], "page_no": r["page_no"], "score": 0})
                c["score"] += 1
    for c in cands.values():
        c["score"] += 1.5 if NUM_RE.search(c["text"]) else 0
    return sorted(cands.values(), key=lambda c: -c["score"])


def _dedupe(cands):
    keep = []
    for c in cands:
        c["sig"] = _sig(c["text"])
        if not any(_sim(c["sig"], k["sig"]) >= 0.85 for k in keep):
            keep.append(c)
    return keep


def _row(ticker, topic, kind, year, c, **extra):
    cit, url = C.cite(c["doc_id"], c["page_no"])
    nums = [n.strip() for n in NUM_RE.findall(c["text"])]
    loc = f"{c['doc_id']}#p{c['page_no']}"
    return {"ticker": ticker, "kind": kind, "text": c["text"], "numbers": nums, "doc_year": year, "topic": topic,
            "citation": cit, "url": url, "locator": loc, "source_id": loc, "quote_grade": "", "license": "",
            "doc_id": c["doc_id"], "page_no": c["page_no"], **extra}


def _topic_rows(ticker, topic, by_year, qid, k, docs):
    if docs:
        return [_row(ticker, topic, "footnote", "", c, new_vs_prev=False, also_in_prev_year=False)
                for c in _dedupe(_extract(docs, topic))[:k]]
    years = list(by_year)
    cur_y = years[0]
    cur = _dedupe(_extract(by_year[cur_y], topic))
    prev = _dedupe(_extract(by_year[years[1]], topic)) if len(years) > 1 else []
    qc = _dedupe(_extract([qid], topic)) if qid else []
    rows, matched_prev = [], set()
    for c in cur:
        best = max(((_sim(c["sig"], p["sig"]), j) for j, p in enumerate(prev)), default=(0, -1))
        hit = best[0] >= 0.6
        if hit:
            matched_prev.add(best[1])
        rows.append(_row(ticker, topic, "footnote", cur_y, c, new_vs_prev=(not hit and bool(prev)), also_in_prev_year=hit,
                         prev_numbers=[n.strip() for n in NUM_RE.findall(prev[best[1]]["text"])] if hit else []))
    for j, p in enumerate(prev):
        if j in matched_prev or any(_sim(p["sig"], c["sig"]) >= 0.6 for c in cur):
            continue
        rows.append(_row(ticker, topic, "dropped_from_latest", years[1], p, new_vs_prev=False, also_in_prev_year=False))
    qper = C.db().execute("SELECT period FROM docs WHERE doc_id=?", (qid,)).fetchone()["period"] if qid else ""
    for c in qc:
        if any(_sim(c["sig"], x["sig"]) >= 0.6 for x in cur):
            continue
        rows.append(_row(ticker, topic, "latest_10q", qper, c, new_vs_prev=True, also_in_prev_year=False))

    def share(kind, n):
        return [r for r in rows if r["kind"] == kind][:n]
    out = share("dropped_from_latest", max(1, k // 5)) + share("latest_10q", max(1, k // 4))
    out = share("footnote", max(0, k - len(out))) + out
    order = {"footnote": 0, "latest_10q": 1, "dropped_from_latest": 2}
    return sorted(out, key=lambda r: order[r["kind"]])[:k]


def footnotes(ticker, topic="all", docs=None, k=40):
    ticker = (ticker or "").upper()
    topics = list(TOPICS) if topic == "all" else [topic] if topic in TOPICS else []
    if not topics:
        return []
    by_year, qid = ({}, None) if docs else select_docs(ticker)
    if not docs and not by_year:
        return []
    per = max(1, k // len(topics)) if topic == "all" else k
    rows = []
    for t in topics:
        rows += _topic_rows(ticker, t, by_year, qid, per, docs)
    return rows


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ticker")
    ap.add_argument("topic", nargs="?", default="all")
    ap.add_argument("-k", type=int, default=40)
    a = ap.parse_args(argv)
    rows = footnotes(a.ticker, a.topic, k=a.k)
    if not rows:
        print(f"no footnote rows for {a.ticker} topic={a.topic} (no annual/quarterly docs in the index or unknown topic)")
    for r in rows:
        print(f"[{r['topic']}|{r['kind']}] {r['citation']} <{r['locator']}> new_vs_prev={r['new_vs_prev']} "
              f"also_in_prev_year={r['also_in_prev_year']}")
        print(f"    {r['text']}")
        if r["numbers"]:
            print(f"    numbers: {', '.join(r['numbers'])}")


if __name__ == "__main__":
    main(sys.argv[1:])
