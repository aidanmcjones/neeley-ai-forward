"""Verification ladder for a Citation, and the gate that refuses uncited or unverifiable claims.

Ladder, first rung that holds wins (status, score):
  1. exact         quote is a byte-for-byte substring of the cited page (zero-width chars removed)   score 1.00
  2. substring     equal after normalization (NFKC, smart quotes/dashes, case, whitespace collapsed,  score 0.98
                   zero-width chars removed; the agent.findings._norm / agent.moat.cite.verify_quote rule)
  3. fuzzy         rapidfuzz.fuzz.partial_ratio >= FUZZY_THRESHOLD (difflib fallback), AND the       score = ratio/100
                   quote's numerals appear in the same order as a contiguous run of the matched
                   span's numerals, AND no direction word flips (DIRECTION_PAIRS, NEGATIONS)
  4. number_match  claim_type "number" with a non-empty quote that did not verify: the emitted value  score 0.6
                   is on the cited page with the same sign and the same scale. The footnote then shows
                   the page text around that number (NUMBER_WINDOW chars), never the unverified quote.
  else unverified  (a note says if the quote lives on another page, spans the page break, or another document)

Before rungs 1-3 fail, a quote that runs past the end of the cited page is tried against page N + page N+1 joined;
a hit keeps its status and the note "spans pages N-N+1" (char_end then counts into page N+1).

Short quotes (review C9): a quote shorter than SHORT_QUOTE_CHARS (12) characters or with fewer than SHORT_QUOTE_TOKENS
(3) tokens can verify at most as "substring", and only at a token boundary: "8" never matches inside "$29,482" or
"18". (Quote claims still need MIN_QUOTE_CHARS = 20; the short rule bites on number claims.)

FUZZY_THRESHOLD = 90. The research notes found no published threshold for citation matching. 90 is chosen
because partial_ratio measures the best aligned window the length of the quote: markdown conversion noise (stray
spaces in tables, dropped footnote marks, a swapped quote character) costs about 1 edit per 20-40 characters and
scores 93-99, while a real paraphrase or a rewritten clause lands near 60-80. 90 sits in the empty gap between the
two. One altered digit or one flipped word in a long quote still scores 97-98, so the rung has two guards (review C8):
the ordered numeral sequence (not a set: swapping 18 and 29,482 is rejected) and the direction-word check: the
count of each word in DIRECTION_PAIRS and NEGATIONS must be the same in the quote and in the matched span
("an increase of 18 percent" vs "a decrease of 18 percent" is rejected).

Numbers (review C7): agent.needle.cite.numbers. Commas dropped, parentheses = negative, '%' / 'percent', scale words
(thousand, million, billion, bn, mm, glued M/B/K). A page number takes its inline scale word, else the scale the page
declares before it ("(in millions)", "USD millions", "$ in thousands"), else 1. So "15,144" under "(in millions)"
supports "15,144 million" and "15.144 billion" but never "15,144 thousand"; "2,025 employees" never supports
"$2.025 billion"; a page "($183)" never supports a claim of +183, and "183" never supports -183.

Reuse: _norm and the transcript constants come from agent.findings; the normalization equals
agent.moat.cite.verify_quote's plus zero-width stripping (verify_quote itself keeps U+200B, review C10, so rung 2
matches on the adapter's own normalized page text). Pages come from the shared sqlite via agent.needle.cite.index (an
adapter, not a second index). agent.findings.verify itself is not called (it needs a per-ticker docs dict), but its
transcript rules are applied here (review B12, transcript_rule): a quote that sits before the fool.com "Full
Conference Call Transcript" marker comes from the LLM-written takeaways and is rejected; a named speaker whose surname
is not in the 4,000 characters before the quote, or is not the nearest "**Name (title):**" label before it, is
rejected; with no speaker named, the quote is attributed to that nearest label.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from difflib import SequenceMatcher

from agent.findings import FOOL_START, _norm

from .deeplink import build_deep_link_with_note, build_viewer_link
from .index import load_index
from .locator import Verification
from .numbers import declared_scale, zw_char, parse_value, same_number, strip_zw, strip_zw_map, tokenize

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

FUZZY_THRESHOLD = 90
MIN_QUOTE_CHARS = 20          # same floor as agent.findings.verify
SHORT_QUOTE_CHARS = 12
SHORT_QUOTE_TOKENS = 3
NUMBER_WINDOW = 60            # chars of page text on each side of a number_match hit
_TR = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-",
                     "\u00a0": " "})

# Direction words for the fuzzy guard. Each pair is antonymous; any count difference between quote and matched span
# (for either word of a pair) rejects the fuzzy match.
DIRECTION_PAIRS = [("increase", "decrease"), ("increased", "decreased"), ("increases", "decreases"),
                   ("increasing", "decreasing"), ("rose", "fell"), ("rise", "fall"), ("rises", "falls"),
                   ("rising", "falling"), ("risen", "fallen"), ("up", "down"), ("higher", "lower"),
                   ("high", "low"), ("gain", "loss"), ("gains", "losses"), ("grew", "declined"), ("grow", "decline"),
                   ("growth", "decline"), ("above", "below"), ("more", "less"), ("positive", "negative"),
                   ("favorable", "unfavorable"), ("improved", "worsened"), ("expand", "contract"),
                   ("expanded", "contracted"), ("surplus", "deficit"), ("profit", "loss"), ("before", "after"),
                   ("maximum", "minimum"), ("over", "under"), ("inflow", "outflow"), ("approved", "rejected")]
NEGATIONS = ("not", "no", "never", "without", "neither", "nor", "none", "cannot")
_DIRWORDS = {w for p in DIRECTION_PAIRS for w in p} | set(NEGATIONS)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm_with_map(text):
    """(normalized text, list mapping each normalized char to its index in `text`). Zero-width chars are dropped."""
    out, idx, space = [], [], True
    for i in range(len(text)):
        ch = zw_char(text, i)
        if not ch:
            continue
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


def _nz(s):
    return _norm(strip_zw(s))


def _span_in_raw(norm_start, norm_end, imap, raw=None):
    return imap[norm_start], imap[norm_end - 1] + 1


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


def _numseq(s):
    return [n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", s or "")]


def _ordered_run(q, s):
    """True when list q appears as a contiguous run inside list s (q empty -> True)."""
    if not q:
        return True
    return any(s[i:i + len(q)] == q for i in range(len(s) - len(q) + 1))


def _direction_flip(quote_n, span_n):
    """'' when direction and negation words agree, else a short description of the first difference."""
    qc = Counter(w for w in re.findall(r"[a-z]+", quote_n) if w in _DIRWORDS)
    sc = Counter(w for w in re.findall(r"[a-z]+", span_n) if w in _DIRWORDS)
    for w in sorted(set(qc) | set(sc)):
        if qc[w] != sc[w]:
            return f"direction word differs: '{w}' x{qc[w]} in quote, x{sc[w]} on page"
    return ""


def _bounded_find(hay, needle):
    """First index of needle in hay at a token boundary (no letter/digit glued on either side, and a numeral is not
    part of a longer digit string such as '29,482'), or -1."""
    start = 0
    while True:
        i = hay.find(needle, start)
        if i < 0:
            return -1
        e = i + len(needle)
        left = hay[i - 1] if i > 0 else " "
        right = hay[e] if e < len(hay) else " "
        bad = left.isalnum() or right.isalnum()
        if not bad and needle[:1].isdigit() and left in ",." and i >= 2 and hay[i - 2].isdigit():
            bad = True
        if not bad and needle[-1:].isdigit() and right in ",." and e + 1 < len(hay) and hay[e + 1].isdigit():
            bad = True
        if not bad:
            return i
        start = i + 1


# ------------------------------------------------------------------ numbers
def parse_numbers(text):
    """List of dicts {num, neg, scale, pct} for every number in text (years included). Kept for callers of the old
    API; new code uses agent.needle.cite.numbers.tokenize."""
    return [{"num": t.num, "neg": t.neg, "scale": t.scale, "pct": t.pct}
            for t in tokenize(text, include_years=True, include_ids=True)]


def parse_claim_value(value, unit=""):
    """Emitted value + unit string ('USD millions', 'percent') -> candidate dict, or None (old API)."""
    t = parse_value(value, unit)
    return None if t is None else {"num": t.num, "neg": t.neg, "scale": t.scale, "pct": t.pct}


def value_on_text(claim, text, full_text=None, offset=0):
    """Does the emitted number appear in text? Returns (found, note, (start, end) of the hit in text or None).
    Page-declared scale is read from full_text (the whole page) up to offset + the hit position."""
    c = parse_value(claim.value, claim.unit) if claim.value not in (None, "") else None
    if c is None:
        return False, "no parsable value", None
    full = text if full_text is None else full_text
    why = ""
    for p in tokenize(text, include_years=True):
        ok, reason = same_number(c, p, None, declared_scale(full, offset + p.start))
        if ok:
            return True, "", (p.start, p.end)
        if reason == "sign differs":
            why = f"value {claim.value} {claim.unit} is on the page with the opposite sign ({p.raw})"
    return False, why or f"value {claim.value} {claim.unit} not on the cited page", None


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
    status, score, span, note, shown = _ladder(base, text)
    link_text = text
    if status == "unverified" and _quote_ok(base):
        nxt = idx.get_page(rec.canonical_id, page + 1)
        if nxt is not None:
            joined = text + "\n" + nxt[2]
            s2, sc2, sp2, n2, sh2 = _ladder(base, joined, number_rung=False)
            if s2 != "unverified" and sp2 and sp2[1] > len(text):
                status, score, span, shown, link_text = s2, sc2, sp2, sh2, joined
                note = (n2 + "; " if n2 else "") + f"spans pages {page}-{page + 1}"
    if status == "unverified":
        elsewhere = _elsewhere(base, idx, page)
        if elsewhere:
            note = (note + "; " if note else "") + elsewhere
    base.char_start, base.char_end = span if span else (None, None)
    if shown is not None:
        base.quote = shown
    if status != "unverified" and rec.raw_doc_type == "transcript":
        status, score, note, base.speaker = transcript_rule(base, idx, page, span, status, score, note)
    base.deep_link, link_note = build_deep_link_with_note(base, link_text)
    if link_note:
        note = (note + "; " if note else "") + link_note
    base.viewer_link = build_viewer_link(base)
    return replace(base, verification=Verification(status, round(score, 4), now, note), confidence_note=note)


_SPEAKER = re.compile(r"\*\*([^*\n]{2,80}?)(?:\s*\([^)\n]*\))?:\*\*")
SPEAKER_WINDOW = 4000     # same window as agent.findings.verify


def transcript_rule(c, idx, page, span, status, score, note):
    """agent.findings' earnings-call checks inside the ladder (review B12). Returns (status, score, note, speaker)."""
    pages = sorted(idx.pages(c.canonical_id).items())
    off, flat = 0, []
    pos = None
    for n, (_, t) in pages:
        if n == page:
            pos = off + (span[0] if span else 0)
        flat.append(t)
        off += len(t) + 1
    flat = "\n".join(flat)
    if pos is None:
        return status, score, note, c.speaker
    low = flat.lower()
    start = low.find(FOOL_START)
    if start != -1 and pos < start:
        return "unverified", 0.0, "quote comes from the LLM-written fool.com takeaways, not the call", c.speaker
    before = flat[max(0, pos - SPEAKER_WINDOW):pos]
    labels = list(_SPEAKER.finditer(flat[:pos]))
    if c.speaker:
        surname = _norm(c.speaker.split()[-1])
        if surname and surname not in _norm(before):
            return "unverified", 0.0, f"speaker {c.speaker!r} not found just before the quote", c.speaker
        if labels and surname and surname not in _norm(labels[-1].group(1)):
            return ("unverified", 0.0, f"quote is spoken by {labels[-1].group(1).strip()!r}, not {c.speaker!r}",
                    c.speaker)
        return status, score, note, c.speaker
    if not labels:
        return status, score, (note + "; " if note else "") + "speaker not identified", ""
    who = labels[-1].group(1).strip()
    return status, score, (note + "; " if note else "") + f"speaker attributed from transcript label: {who}", who


def _quote_ok(c):
    nq = _nz(c.quote)
    return len(nq) >= MIN_QUOTE_CHARS or (c.claim_type == "number" and len(nq) > 0)


def _ladder(c, text, number_rung=True):
    """(status, score, span, note, shown_quote or None). span = raw char offsets into text."""
    q = strip_zw(c.quote or "").strip()
    nq = _norm(q)
    clean, cmap = strip_zw_map(text)
    ntext, imap = norm_with_map(text)
    has_val = c.value not in (None, "")
    quote_ok = _quote_ok(c)
    short = len(nq) < SHORT_QUOTE_CHARS or len(nq.split()) < SHORT_QUOTE_TOKENS

    def with_value(status, score, span, note=""):
        """Numeric claims must also have their number in the matched span."""
        if c.claim_type == "number" and has_val:
            ok, n2, _ = value_on_text(c, text[span[0]:span[1]], text, span[0])
            if not ok:
                return "unverified", 0.0, span, f"quote verified but {n2}", None
        return status, score, span, note, None

    if quote_ok and short:
        j = _bounded_find(ntext, nq)
        if j >= 0:
            return with_value("substring", 0.98, _span_in_raw(j, j + len(nq), imap),
                              "short quote: capped at substring, matched at a token boundary")
    elif quote_ok:
        i = clean.find(q)
        if i >= 0:
            return with_value("exact", 1.0, (cmap[i], cmap[i + len(q) - 1] + 1))
        j = ntext.find(nq)
        if j >= 0:
            return with_value("substring", 0.98, _span_in_raw(j, j + len(nq), imap))
        if len(nq) >= MIN_QUOTE_CHARS:
            score, ds, de = _partial(nq, ntext)
            if score >= FUZZY_THRESHOLD and de > ds:
                span = _span_in_raw(ds, de, imap)
                qn, sn = _numseq(nq), _numseq(ntext[ds:de])
                if not _ordered_run(qn, sn):
                    return ("unverified", 0.0, None,
                            f"fuzzy match {score:.0f} but numbers differ from page (quote {qn}, page {sn})", None)
                flip = _direction_flip(nq, ntext[ds:de])
                if flip:
                    return "unverified", 0.0, None, f"fuzzy match {score:.0f} but {flip}", None
                return with_value("fuzzy", score / 100.0, span, f"fuzzy partial_ratio {score:.0f}")
    if number_rung and c.claim_type == "number" and has_val:
        if not q:
            return "unverified", 0.0, None, "number claim with an empty quote cannot verify", None
        ok, n2, hit = value_on_text(c, text)
        if ok:
            s0 = max(0, hit[0] - NUMBER_WINDOW)
            e0 = min(len(text), hit[1] + NUMBER_WINDOW)
            while s0 > 0 and not text[s0 - 1].isspace() and hit[0] - s0 < NUMBER_WINDOW + 20:
                s0 -= 1
            while e0 < len(text) and not text[e0].isspace() and e0 - hit[1] < NUMBER_WINDOW + 20:
                e0 += 1
            shown = " ".join(strip_zw(text[s0:e0]).split())
            return ("number_match", 0.6, (s0, e0),
                    f"number found on page; model quote not on page ({' '.join(q.split())[:80]!r}); "
                    "footnote shows the page text around the number", shown)
        return "unverified", 0.0, None, n2, None
    return "unverified", 0.0, None, "quote not found on cited page" if quote_ok else "quote missing or too short to check", None


def _elsewhere(c, idx, page):
    nq = _nz(c.quote)
    if len(nq) < MIN_QUOTE_CHARS:
        return ""
    pages = idx.pages(c.canonical_id)
    if page in pages and nq in _nz(pages[page][1]):
        return ""                                   # the quote is on the cited page; the failure is elsewhere
    for n, (_, t) in pages.items():
        if n != page and nq in _nz(t):
            return f"quote is on page {n}, not page {page}"
    prev = pages.get(page - 1)
    if prev and page in pages and nq in _nz(prev[1] + "\n" + pages[page][1]):
        return f"quote spans pages {page - 1}-{page}; cite page {page - 1}"
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
