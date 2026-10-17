"""Ticker -> candidate findings from the page-anchored corpus, each checked against the page it cites.

One Claude call proposes findings; a deterministic verifier then checks every one against the source text:
  - the quote must appear on the cited page (whitespace, quotes and dashes normalized)
  - a quote found on a different page is rejected with the page it is really on
  - for earnings calls, the named speaker must appear just before the quote, and quotes from the
    LLM-written fool.com TAKEAWAYS / SUMMARY sections are rejected
  - every cited figure must appear on the cited page, else the finding goes to a human
Nothing reaches the verified file unless it passes. Rejections are the "AI was confidently wrong" log.

Works for any ticker under data/corpus (the 10 case companies and the rival makers).

Usage:
  python -m agent.findings --ticker BMY              # needs ANTHROPIC_API_KEY
  python -m agent.findings --ticker BMY --dry-run    # show which pages would be sent, no API call
Writes eval/out/<TICKER>_verified.jsonl, _needs_human.jsonl, _rejected.jsonl.
"""

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
OUT = ROOT / "eval" / "out"

DOC_TYPES = {"annual_report", "quarterly_report", "transcript"}
MARKER = re.compile(r"\[\[page (\d+) \| printed ([^\]]+)\]\]")
CHUNK = 6000
FOOL_START = "full conference call transcript"

# Where the case says findings hide. Pages are ranked by how many of these they hit.
KEYWORDS = [
    r"gross[- ]to[- ]net", r"rebate", r"chargeback", r"inventor(y|ies)", r"receivable", r"Medicare",
    r"Inflation Reduction Act|\bIRA\b", r"maximum fair price|negotiat", r"most[- ]favou?red[- ]nation|\bMFN\b",
    r"tariff", r"exclusivity|patent", r"biosimilar|generic", r"litigation|reserve", r"contingent consideration",
    r"royalt", r"collaboration|profit[- ]shar", r"effective tax rate", r"reclassif|recast|no longer report",
    r"impairment", r"guidance", r"boxed warning|label", r"340B", r"Part D", r"price (increase|decrease|reduction)",
]
KW = [re.compile(k, re.I) for k in KEYWORDS]

SYSTEM = (
    "You are a forensic equity analyst reading a drug maker's own filings and earnings calls. "
    "Find what a press-release skim would miss: language that changed between years, widening gross-to-net, "
    "inventory or receivables growing faster than revenue, products no longer broken out, footnote items "
    "(litigation reserves, royalty splits, contingent payments, tax rate), deflected analyst questions, and "
    "exposure to Medicare negotiation, MFN pricing deals and tariffs. Patent cliffs alone are already priced in. "
    "Use only the provided documents. Never invent a quote, page or number."
)

PROMPT = """Each document above is one page (or part of a page) of a filing or call, tagged with a source id like
BMY:10k_FY2025.md#p47. Propose up to {n} findings that would change an investor's view of {ticker}.

Return ONLY a JSON array. Each item:
{{"finding": "one plain-English sentence",
  "source": "the exact source id the quote comes from",
  "quote": "a short passage copied character for character from that one source, 15 to 60 words",
  "speaker": "for earnings calls, the speaker's full name; otherwise empty",
  "figures": ["each number your impact math uses, written exactly as it appears in the quote's source"],
  "impact_math": "estimated effect on revenue, operating income or EPS, with the arithmetic shown",
  "category": "language_drift | gross_to_net | inventory_receivables | segment_change | footnote | call_qa | policy_exposure | other",
  "why_not_obvious": "why the market may not have priced this in",
  "confidence": "high | medium | low"}}"""


def _norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                                   "–": "-", "—": "-", " ": " "}))
    return re.sub(r"\s+", " ", s).strip().lower()


def _numbers(s):
    """Every number in s, commas dropped: '$48,194 million' -> {'48194'}."""
    return {n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", s or "")}


def _parse_json(text):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise ValueError("model returned no JSON array")
    return json.loads(m.group(0))


# ---------------------------------------------------------------- corpus

def load_docs(ticker):
    """{doc_id: {"row": manifest row, "pages": {n: (printed, text)}, "flat": normalized full text}}"""
    docs = {}
    with open(CORPUS / "manifest.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["ticker"] != ticker or row["doc_type"] not in DOC_TYPES:
                continue
            path = ROOT / row["path"]
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            parts = MARKER.split(text)
            pages = {int(parts[i]): (parts[i + 1].strip(), parts[i + 2]) for i in range(1, len(parts) - 2, 3)}
            docs[row["doc_id"]] = {"row": row, "pages": pages, "flat": _norm(text)}
    if not docs:
        raise SystemExit(f"no filings or transcripts for {ticker} in {CORPUS / 'manifest.csv'}")
    return docs


def label(row):
    """Human citation prefix: 'BMY 10-K FY2025', 'BMY 10-Q 2026-06-30', 'BMY 2026Q2 earnings call (third_party)'."""
    t, period = row["ticker"], row["period"]
    if row["doc_type"] == "annual_report":
        return f"{t} {row['form'] or 'annual report'} FY{period[:4]}"
    if row["doc_type"] == "quarterly_report":
        return f"{t} 10-Q {period}"
    return f"{t} {period} earnings call ({row['source_quality']})"


def cite(doc, page):
    printed = doc["pages"][page][0]
    where = f"p. {printed}" if printed != "?" else f"file page {page} (no printed page number)"
    return f"{label(doc['row'])}, {where}"


def select(docs, max_chars):
    """Highest-keyword chunks across all documents, up to max_chars. Returns {source_id: text}."""
    chunks = []
    for doc_id, d in docs.items():
        for n, (_, text) in d["pages"].items():
            for k in range(0, max(len(text), 1), CHUNK):
                piece = text[k:k + CHUNK]
                score = sum(1 for kw in KW if kw.search(piece))
                if d["row"]["doc_type"] == "transcript":
                    score += 1  # calls are short and are where deflections live
                if score:
                    chunks.append((score, f"{doc_id}#p{n}", piece))
    chunks.sort(key=lambda c: -c[0])
    picked, used = {}, 0
    for _, sid, piece in chunks:
        if used + len(piece) > max_chars:
            continue
        picked[sid] = picked.get(sid, "") + piece
        used += len(piece)
    return picked


# ---------------------------------------------------------------- verifier

def verify(f, docs):
    """Returns (status, reason, citation). status: verified | needs_human | rejected."""
    m = re.fullmatch(r"(.+)#p(\d+)", str(f.get("source", "")).strip())
    if not m or m.group(1) not in docs:
        return "rejected", f"unknown source {f.get('source')!r}", ""
    doc, page = docs[m.group(1)], int(m.group(2))
    if page not in doc["pages"]:
        return "rejected", f"page {page} does not exist in {m.group(1)}", ""
    q = _norm(f.get("quote"))
    if len(q) < 20:
        return "rejected", "quote missing or too short to check", ""
    on_page = _norm(doc["pages"][page][1])
    if q not in on_page:
        elsewhere = [n for n, (_, t) in doc["pages"].items() if q in _norm(t)]
        if elsewhere:
            return "rejected", f"quote is on page {elsewhere[0]}, not page {page}", cite(doc, elsewhere[0])
        other = [i for i, d in docs.items() if q in d["flat"]]
        if other:
            return "rejected", f"quote is in {other[0]}, not {m.group(1)}", ""
        return "rejected", "quote not found anywhere in the corpus (paraphrased or invented)", ""

    citation = cite(doc, page)
    if doc["row"]["doc_type"] == "transcript":
        pos = doc["flat"].find(q)
        start = doc["flat"].find(FOOL_START)
        if start != -1 and pos < start:
            return "rejected", "quote comes from the LLM-written fool.com takeaways, not the call", citation
        speaker = (f.get("speaker") or "").strip()
        surname = _norm(speaker.split()[-1]) if speaker else ""
        if not surname:
            return "needs_human", "earnings-call quote with no speaker named", citation
        if surname not in doc["flat"][max(0, pos - 4000):pos]:
            return "needs_human", f"speaker {speaker!r} not found just before the quote", citation

    page_nums = _numbers(doc["pages"][page][1])
    missing = [x for x in f.get("figures") or [] if _numbers(str(x)) and not _numbers(str(x)) <= page_nums]
    if missing:
        return "needs_human", f"figures not on the cited page: {missing}", citation
    return "verified", "", citation


# ---------------------------------------------------------------- run

def run(ticker, n=12, max_chars=150_000, dry_run=False):
    docs = load_docs(ticker)
    context = select(docs, max_chars)
    print(f"{ticker}: {len(docs)} documents, {len(context)} chunks, {sum(map(len, context.values())):,} chars selected")
    if dry_run:
        for sid in context:
            print("  ", sid)
        return None

    from agent.llm import call
    result = call(PROMPT.format(n=n, ticker=ticker), context=context, system=SYSTEM, effort="high")
    proposed = _parse_json(result["text"])

    OUT.mkdir(parents=True, exist_ok=True)
    buckets = {"verified": [], "needs_human": [], "rejected": []}
    for f in proposed:
        status, reason, citation = verify(f, docs)
        buckets[status].append({**f, "ticker": ticker, "status": status, "reason": reason, "citation": citation})
    for status, rows in buckets.items():
        with open(OUT / f"{ticker}_{status}.jsonl", "w", encoding="utf-8") as out:
            out.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    print(f"proposed {len(proposed)}: " + ", ".join(f"{k} {len(v)}" for k, v in buckets.items())
          + f" (cached: {result['cached']}) -> {OUT}")
    return buckets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--n", type=int, default=12, help="max findings to propose")
    ap.add_argument("--max-chars", type=int, default=150_000, help="context budget")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    run(a.ticker.upper(), a.n, a.max_chars, a.dry_run)


if __name__ == "__main__":
    main()
