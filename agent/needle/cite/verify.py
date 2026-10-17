"""Verification ladder for a Citation, and the gate that refuses uncited or unverifiable claims.

Ladder, first rung that holds wins (status, score):
  1. exact         quote is a byte-for-byte substring of the cited page            score 1.00
  2. substring     equal after normalization (NFKC, smart quotes/dashes, case,     score 0.98
                   whitespace collapsed; this is agent.findings._norm)
  3. fuzzy         rapidfuzz.fuzz.partial_ratio >= FUZZY_THRESHOLD (difflib        score = ratio/100
                   fallback), AND every number in the quote is in the matched span
  4. number_match  claim_type "number": the emitted `value` (after unit normalization)   score 0.6
                   is found among the numbers on the cited page although the quote itself did not verify
  else unverified  (a note says if the quote lives on another page or another document)

FUZZY_THRESHOLD = 90. The research notes found no published threshold for citation matching. 90 is chosen
because partial_ratio measures the best aligned window the length of the quote: markdown conversion noise (stray
spaces in tables, dropped footnote marks, a swapped quote character) costs about 1 edit per 20-40 characters and
scores 93-99, while a real paraphrase or a rewritten clause lands near 60-80. 90 sits in the empty gap between the
two. The number guard exists because one altered digit in a long quote still scores 98: fuzzy never accepts a quote
whose numerals differ from the page span it matched.

Numeric normalization: commas dropped, parentheses = negative, '%' / 'percent', scale words (thousand, million,
billion, bn, mm, k). Tables in these filings say "in millions" once in the header, so a bare 15,144 on the page is
also accepted against an emitted 15,144 million or 15.144 billion (page numeral x 1e3/1e6/1e9 equals the claim).
A claim of +183 against a page showing (183) matches with a note; a claim of -183 against a page showing 183 does not.

Reuse: rung 2 calls agent.moat.cite.verify_quote (the shared normalized-substring verifier) on the sqlite page;
_norm and _numbers come from agent.findings. Mine: rung 1 (exact + char span), the fuzzy rung and its number guard,
and the numeric value check (verify_quote has no numeric semantics). Pages come from the shared sqlite via
agent.needle.cite.index (an adapter, not a second index). agent.findings.verify itself is not called (it needs a
per-ticker docs dict); its transcript speaker rule is not repeated here.
"""

import re
import unicodedata
from dataclasses import replace
from datetime import datetime, timezone
from difflib import SequenceMatcher

from agent.findings import _norm, _numbers
from agent.moat.cite import verify_quote

from .deeplink import build_deep_link, build_viewer_link
from .index import load_index
from .locator import Verification

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

FUZZY_THRESHOLD = 90
MIN_QUOTE_CHARS = 20          # same floor as agent.findings.verify
_TR = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm_with_map(text):
    """(normalized text, list mapping each normalized char to its index in `text`)."""
    out, idx, space = [], [], True
    for i, ch in enumerate(text):
        for c in unicodedata.normalize("NFKC", ch).translate(_TR).lower():
            if c.isspace():
                if not space:
                    out.append(" ")
                    idx.append(i)
                    space = True
            else:
                out.append(c)
                idx.append(i)
                space = False
    if out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def _span_in_raw(norm_start, norm_end, imap, raw):
    s = imap[norm_start]
    e = imap[norm_end - 1] + 1
    return s, e


def _partial(a, b):
    """(score 0..100, start, end) best window of b (page) matching a (quote)."""
    if fuzz is not None:
        al = fuzz.partial_ratio_alignment(a, b)
        return al.score, al.dest_start, al.dest_end
    n = len(a)                                    # difflib fallback: coarse window scan, then refine
    best = (0.0, 0, min(n, len(b)))
    step = max(1, n // 4)
    for s in range(0, max(1, len(b) - n + 1), step):
        r = SequenceMatcher(None, a, b[s:s + n], autojunk=False).ratio() * 100
        if r > best[0]:
            best = (r, s, s + n)
    return best


# ------------------------------------------------------------------ numbers
_SCALE = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mm": 1e6, "m": 1e6, "mn": 1e6,
          "billion": 1e9, "bn": 1e9, "b": 1e9, "trillion": 1e12}
_NUM = re.compile(r"(\()?\s*[$€£]?\s*(-|−)?\s*(\d[\d,]*(?:\.\d+)?)\s*(\))?\s*"
                  r"(%|percent\b|thousands?\b|millions?\b|billions?\b|trillions?\b|bn\b|mm\b|mn\b|k\b|m\b|b\b)?", re.I)


def parse_numbers(text):
    """List of dicts {num: float numeral, neg: bool, scale: float|None, pct: bool} found in text."""
    out = []
    for m in _NUM.finditer(text or ""):
        raw = m.group(3).replace(",", "").rstrip(".")
        try:
            num = float(raw)
        except ValueError:
            continue
        word = (m.group(5) or "").lower()
        out.append({"num": num, "neg": bool(m.group(2)) or (bool(m.group(1)) and bool(m.group(4))),
                    "scale": _SCALE.get(word.rstrip("s") if word.endswith("s") and len(word) > 2 else word), "pct": word in ("%", "percent")})
    return out


def parse_claim_value(value, unit=""):
    """Emitted value + unit string ('USD millions', 'percent') -> candidate dict, or None."""
    cand = parse_numbers(str(value))
    if not cand:
        return None
    c = cand[0]
    u = (unit or "").lower()
    if c["scale"] is None:
        for w, f in (("trillion", 1e12), ("billion", 1e9), ("million", 1e6), ("thousand", 1e3)):
            if w in u:
                c["scale"] = f
                break
    if "percent" in u or "%" in u or "pct" in u:
        c["pct"] = True
    return c


def _same(a, b):
    return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1.0)


def value_on_text(claim, text):
    """Does the emitted number appear in text? Returns (found, note)."""
    c = parse_claim_value(claim.value, claim.unit) if claim.value not in (None, "") else None
    if c is None:
        return False, "no parsable value"
    cs = c["num"] * (c["scale"] or 1.0)
    for p in parse_numbers(text):
        if c["pct"] != p["pct"]:
            continue
        ps = p["num"] * (p["scale"] or 1.0)
        hit = _same(cs, ps)
        if not hit and c["scale"] and p["scale"] is None:       # "15,144 million" vs table cell 15,144
            hit = _same(c["num"], p["num"])
        if not hit and (c["scale"] is None or p["scale"] is None):
            hit = any(_same(cs, p["num"] * t) for t in (1e3, 1e6, 1e9)) and not c["pct"]
        if not hit:
            continue
        if c["neg"] and not p["neg"]:
            continue
        return True, ("page shows a parenthesized negative; claim sign differs" if p["neg"] and not c["neg"] else "")
    return False, f"value {claim.value} {claim.unit} not on the cited page"


# ------------------------------------------------------------------ ladder
def verify(citation, index=None):
    """Return a copy of `citation` with locator fields, links and verification filled in."""
    idx = index or load_index()
    rec = idx.resolve(citation.canonical_id)
    now = _now()
    if rec is None:
        return replace(citation, verification=Verification("unverified", 0.0, now, "unknown document id"))
    got = idx.get_page(rec.canonical_id, citation.page)
    base = replace(citation, canonical_id=rec.canonical_id, ticker=rec.ticker, doc_type=rec.doc_type,
                   doc_title=rec.doc_title, period=rec.period, source_url=rec.source_url, raw_doc_type=rec.raw_doc_type,
                   page_scheme=rec.page_scheme, license=rec.license, cite_id="")
    if got is None:
        v = Verification("unverified", 0.0, now, f"page {citation.page} not found in {rec.canonical_id}")
        base.viewer_link = build_viewer_link(base)
        return replace(base, verification=v, confidence_note=v.detail)
    page, folio, text = got
    base.folio = folio
    base.location = idx.location(rec.canonical_id, page)
    status, score, span, note = _ladder(base, text)
    if status == "unverified":
        elsewhere = _elsewhere(base, idx, page)
        if elsewhere:
            note = (note + "; " if note else "") + elsewhere
    base.char_start, base.char_end = span if span else (None, None)
    base.deep_link = build_deep_link(base, text)
    base.viewer_link = build_viewer_link(base)
    return replace(base, verification=Verification(status, round(score, 4), now, note), confidence_note=note)


def _ladder(c, text):
    q = (c.quote or "").strip()
    nq = _norm(q)
    ntext, imap = norm_with_map(text)
    has_val = c.value not in (None, "")
    quote_ok = len(nq) >= MIN_QUOTE_CHARS or (c.claim_type == "number" and len(nq) > 0)

    def with_value(status, score, span, note=""):
        """Numeric claims must also have their number in the matched span (or page when no span)."""
        if c.claim_type == "number" and has_val:
            seg = text[span[0]:span[1]] if span else text
            ok, n2 = value_on_text(c, seg)
            if not ok:
                return "unverified", 0.0, span, f"quote verified but {n2}"
            note = (note + "; " if note else "") + n2 if n2 else note
        return status, score, span, note

    if quote_ok:
        i = text.find(q)
        if i >= 0:
            return with_value("exact", 1.0, (i, i + len(q)))
        j = ntext.find(nq)
        if verify_quote(q, c.canonical_id, c.page) and j >= 0:      # shared moat verifier: normalized page substring
            return with_value("substring", 0.98, _span_in_raw(j, j + len(nq), imap, text))
        if len(nq) >= MIN_QUOTE_CHARS:
            score, ds, de = _partial(nq, ntext)
            if score >= FUZZY_THRESHOLD and de > ds:
                span = _span_in_raw(ds, de, imap, text)
                qn, sn = _numbers(nq), _numbers(ntext[ds:de])
                if not qn <= sn:
                    return "unverified", 0.0, span, f"fuzzy match {score:.0f} but numbers differ from page: {sorted(qn - sn)}"
                return with_value("fuzzy", score / 100.0, span, f"fuzzy partial_ratio {score:.0f}")
    if c.claim_type == "number" and has_val:
        ok, n2 = value_on_text(c, text)
        if ok:
            return "number_match", 0.6, None, "number found on page; quote not verified" + (f"; {n2}" if n2 else "")
        return "unverified", 0.0, None, n2
    return "unverified", 0.0, None, "quote not found on cited page" if quote_ok else "quote missing or too short to check"


def _elsewhere(c, idx, page):
    nq = _norm(c.quote)
    if len(nq) < MIN_QUOTE_CHARS:
        return ""
    for n, (_, t) in idx.pages(c.canonical_id).items():
        if n != page and nq in _norm(t):
            return f"quote is on page {n}, not page {page}"
    return ""


# ------------------------------------------------------------------ gate
def gate(claims):
    """(passed, rejected). A claim passes only if it has a citation whose status is not 'unverified'.
    Passed claims keep only their verified citations; rejected claims are returned untouched."""
    passed, rejected = [], []
    for cl in claims:
        good = [c for c in cl.citations if c.verification.ok]
        if good:
            passed.append(replace(cl, citations=good))
        else:
            rejected.append(cl)
    return passed, rejected
