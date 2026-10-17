"""Number tokenizer shared by the verify ladder, the numeric gate, the renderer and the LLM parser.

tokenize(text) returns every numeral in text as a NumTok with its unit and scale context:
  * scale words right after the number: thousand(s), million(s), billion(s), trillion(s), bn, mn, mm, and a single
    M / B / K (or m / b / k) glued to the digits ("$319M", "$18.43B"). Scale multiplies the numeral.
  * unit: "%" (also "percent", "pct"), "pts" (pts, points, percentage points), "bps", "x" (multiples), else "".
  * sign: a leading "-", U+2212 or "+" that is not glued to a preceding letter or digit, or accounting parentheses
    "(183)" / "($183)" -> negative.
  * currency: $, US$, USD, EUR, GBP, euro and pound signs, before or (USD) after the numeral.
  * decimals: how many decimals the text printed; the gate uses it as the display precision.

Excluded by rule (kind != "number"; the gate neither checks nor counts them):
  * years: a bare 4-digit integer 1900-2099 with no comma, decimal, currency, unit, scale, sign or parentheses.
    "2030 million", "$2030" and "(2030)" are numbers, "in 2030" is a year.
  * dates: ISO dates (2025-12-19), slash dates (8/27/2029, 12/2025), "January 27, 2026", "Jan 2026".
  * period labels: Q2 2026, 2026Q2, 4Q25, FY2025, CY2025Q2I, H1 2026, 1H26.
  * form names: 10-K, 10-Q, 20-F, 8-K, 6-K, 40-F, S-1, DEF 14A.
  * page and section numbers: p. 41, pp. 3-4, page 7, file page 2, PDF p. 3, Item 1A, Note 12, Section 5.1, Part D,
    Table 3, Exhibit 99.1, row 12, CIK 0000310158, NCT01234567, ids (hex hashes of 8+ chars, c_xxxx cite ids).
  * markers and links: [1], [1][2], [derived: 1, 2], [assumption], URLs and markdown link targets.
  * identifiers glued to letters: GLP-1, IL-23, PD-1, COVID-19, Q4, H1, 1st, 3rd, Part-B2.
Everything else that looks like a number (counts, percents, money, multiples, z-scores, ratios) is a number.
"""

import re
from dataclasses import dataclass

ZW_CHARS = "​‌‍⁠﻿­"
_ZW = re.compile("[" + ZW_CHARS + "]")


_ZWSP_WORD = re.compile(r"(?<=[^\W\d_])\u200b(?=[^\W\d_])")


def strip_zw(s):
    """Remove zero-width spaces/joiners, word joiner, BOM and soft hyphen (conversion noise, review C10). A zero-width
    space between two letters is a word break in the source ('Net\u200bsales'), so it becomes a space; anywhere
    else (inside '29,\u200b482') it is dropped."""
    return _ZW.sub("", _ZWSP_WORD.sub(" ", s or ""))


def zw_char(s, i):
    """What strip_zw turns s[i] into: the char itself, ' ' (word-break ZWSP) or '' (dropped)."""
    ch = s[i]
    if ch not in ZW_CHARS:
        return ch
    if ch == "\u200b" and 0 < i < len(s) - 1 and s[i - 1].isalpha() and s[i + 1].isalpha():
        return " "
    return ""


def strip_zw_map(s):
    """(strip_zw(s), list mapping each kept char to its index in s)."""
    out, idx = [], []
    s = s or ""
    for i in range(len(s)):
        c = zw_char(s, i)
        if c:
            out.append(c)
            idx.append(i)
    return "".join(out), idx


SCALE = {"thousand": 1e3, "thousands": 1e3, "k": 1e3, "million": 1e6, "millions": 1e6, "m": 1e6, "mn": 1e6, "mm": 1e6,
         "billion": 1e9, "billions": 1e9, "b": 1e9, "bn": 1e9, "trillion": 1e12, "trillions": 1e12}

_MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
          r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?")
_MASKS = [
    re.compile(r"https?://\S+|/viewer\?\S+|\]\([^)\s]*\)"),                       # URLs, markdown link targets
    re.compile(r"\[(?:\d+(?:\s*[,;]\s*\d+)*|derived:[^\]]*|assumption[^\]]*)\]", re.I),   # markers
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{1,2}/\d{4}\b"),     # dates
    re.compile(_MONTH + r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b|\b\d{1,2}\s+" + _MONTH + r"\s+\d{4}\b|" + _MONTH + r"\s+\d{4}\b"),
    re.compile(r"\b(?:Q[1-4]\s?(?:FY)?\s?'?\d{2,4}|[1-4]Q\s?'?\d{2,4}|\d{4}\s?Q[1-4]I?|FY\s?'?\d{2,4}(?:\s?Q[1-4])?|"
               r"CY\s?\d{4}(?:Q[1-4]I?)?|[12]H\s?'?\d{2,4}|H[12]\s?'?\d{2,4})\b", re.I),
    re.compile(r"\b(?:10-K|10-Q|20-F|8-K|6-K|40-F|S-[1-4]|DEF\s?14A)\b", re.I),
    re.compile(r"(?:\b(?:file\s+page|PDF\s+p|pp?|pages?|Item|Note|Notes|Section|Part|Table|Exhibit|Figure|Fig|"
               r"row|CIK|ID|Rule|Schedule|Appendix|Chapter|Article|NCT|Phase|Tier|Stage|Grade|Cycle)\.?|§|#)\s*"
               r"[A-Z]?\d[\w.]*(?:\s*(?:-|–|to)\s*[A-Z]?\d[\w.]*)?", re.I),
    re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{8,}\b|\bc_[0-9a-f]+\b"),   # hashes, cite ids
]

_TOKEN = re.compile(
    r"(?P<open>\(\s*)?"
    r"(?P<cur>US\$|USD\s?|EUR\s?|GBP\s?|[$€£]\s?)?"
    r"(?P<sign>[-−+])?"
    r"(?P<cur2>[$€£]\s?)?"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)"
    r"(?P<close>\s*\))?"
    r"(?P<unit>\s?%|\s?(?:percentage\s+points?|percent|pct|pts?|points?|bps|basis\s+points)\b|"
    r"\s?(?:thousands?|millions?|billions?|trillions?)\b|\s?(?:bn|mn|mm)\b|[MBKmbk]\b|x\b|\s?(?:USD|EUR|GBP)\b)?",
)


@dataclass
class NumTok:
    raw: str
    start: int
    end: int
    num: float                 # absolute numeral as printed (commas dropped)
    neg: bool = False
    scale: float | None = None  # from an inline scale word; None when the text printed none
    unit: str = ""             # "%", "pts", "bps", "x" or ""
    currency: str = ""         # "$", "EUR", "GBP" or ""
    decimals: int = 0
    kind: str = "number"       # number | year | id

    @property
    def pct(self):
        return self.unit == "%"

    def value(self, ctx_scale=None):
        """Signed value with inline scale, else ctx_scale, else 1."""
        v = self.num * (self.scale or ctx_scale or 1.0)
        return -v if self.neg else v


def _mask(text):
    chars = list(text)
    for rx in _MASKS:
        for m in rx.finditer(text):
            for i in range(m.start(), m.end()):
                if not chars[i].isspace():
                    chars[i] = " " if not chars[i].isdigit() else "\x00"
    return "".join(chars)


def _cur(s):
    s = (s or "").strip().upper()
    if not s:
        return ""
    if s in ("$", "US$", "USD"):
        return "$"
    return {"€": "EUR", "£": "GBP"}.get(s, s)


def tokenize(text, include_years=False, include_ids=False):
    """All numbers in text (see the module docstring). Years and ids are returned only when asked for. start/end are
    offsets into the text as given (zero-width chars are skipped for parsing but offsets map back)."""
    orig = text or ""
    text, omap = strip_zw_map(orig) if any(c in ZW_CHARS for c in orig) else (orig, None)
    masked = _mask(text)
    out = []
    for m in _TOKEN.finditer(masked):
        s, e = m.start(), m.end()
        num_s = m.start("num")
        if "\x00" in masked[s:e]:
            continue
        g = m.groupdict()
        raw_num = g["num"]
        prev = masked[s - 1] if s > 0 else " "
        kind = "number"
        sign = g["sign"]
        neg = False
        if sign:
            before_sign = masked[m.start("sign") - 1] if m.start("sign") > 0 else " "
            if before_sign.isalpha():
                kind = "id"                                  # GLP-1, IL-23, PD-1
            elif before_sign.isdigit():
                sign = None                                  # range "18-20": the second number is unsigned
                s = m.start("cur2") if g["cur2"] else num_s
            else:
                neg = sign in "-−"
        if not g["open"] and not g["cur"] and not g["sign"] and (prev.isalnum() or prev in "._"):
            kind = "id"                                      # glued to a word: Q4, H1, abc123
        unit_raw = (g["unit"] or "").strip()
        nxt = masked[e] if e < len(masked) else " "
        if not unit_raw and (nxt.isalpha() or nxt == "_"):
            kind = "id"                                      # 1st, 3rd, 4Q, 10K-like
        paren = bool(g["open"]) and bool(g["close"])
        if paren:
            neg = True
        elif g["open"]:
            s = m.start("cur") if g["cur"] else m.start("sign") if g["sign"] else m.start("cur2") if g["cur2"] else num_s
        try:
            num = float(raw_num.replace(",", ""))
        except ValueError:
            continue
        ul = unit_raw.lower()
        scale, unit, cur = None, "", _cur(g["cur"] or g["cur2"])
        if ul in ("%", "percent", "pct"):
            unit = "%"
        elif ul.startswith("percentage") or ul in ("pt", "pts", "point", "points"):
            unit = "pts"
        elif ul == "bps" or ul.startswith("basis"):
            unit = "bps"
        elif ul == "x":
            unit = "x"
        elif ul in ("usd", "eur", "gbp"):
            cur = cur or _cur(ul)
        elif unit_raw in ("m", "b", "k") and not cur:
            kind = "id"                                      # "Phase 2b", "3m": too ambiguous to read as a scale
        elif ul:
            scale = SCALE.get(ul)
        decimals = len(raw_num.split(".")[1]) if "." in raw_num else 0
        is_year = (kind == "number" and re.fullmatch(r"(?:19|20)\d\d", raw_num) is not None and not cur and not unit
                   and scale is None and not sign and not paren)
        if is_year:
            kind = "year"
        if (kind == "year" and not include_years) or (kind == "id" and not include_ids):
            continue
        os_, oe = (omap[s], omap[e - 1] + 1) if omap is not None and e > s else (s, e)
        out.append(NumTok(raw=text[s:e].strip(), start=os_, end=oe, num=num, neg=neg, scale=scale,
                          unit=unit, currency=cur, decimals=decimals, kind=kind))
    return out


def numbers(text):
    """Gate-eligible numbers only (years, dates, ids and page numbers excluded)."""
    return tokenize(text)


_DECL = re.compile(r"(?:\bin\s+|\bamounts\s+in\s+|\(\s*(?:\$|USD|US\$|€|£)?\s*(?:in\s+)?|\b(?:USD|US\$|\$)\s*(?:in\s+)?)"
                   r"(thousands|millions|billions)\b", re.I)


def declared_scale(text, pos=None):
    """Scale a table header or sentence declares before pos ('(in millions)', 'USD millions', '$ in thousands');
    the nearest declaration before pos wins. None when the text declares none."""
    t = text if pos is None else text[:pos]
    last = None
    for m in _DECL.finditer(t or ""):
        last = m
    return SCALE[last.group(1).lower()] if last else None


def parse_value(value, unit=""):
    """An emitted value plus a unit string ('USD millions', 'percent', 'year') -> NumTok or None."""
    toks = tokenize(str(value), include_years=True, include_ids=True)
    if not toks:
        return None
    t = toks[0]
    t.kind = "number"
    u = (unit or "").lower()
    if t.scale is None:
        for w in ("trillion", "billion", "million", "thousand"):
            if w in u:
                t.scale = SCALE[w]
                break
    if not t.unit:
        if "percentage point" in u or u in ("pts", "points"):
            t.unit = "pts"
        elif "percent" in u or "%" in u or "pct" in u:
            t.unit = "%"
    if not t.currency and ("usd" in u or "$" in u):
        t.currency = "$"
    return t


def tolerance(tok, scale=1.0):
    """Half a unit of the last printed digit, in absolute terms: '29' covers 28.5..29.5, '1,937.9M' covers +-0.05M."""
    return 0.5 * 10 ** (-tok.decimals) * (scale or 1.0) + 1e-9 * max(1.0, abs(tok.num * (scale or 1.0)))


def same_number(claim, src, claim_ctx=None, src_ctx=None):
    """(match, reason). Does src (a number in a source text) support claim (a number in emitted text)?

    Unit must agree ('%' with '%', 'pts' with 'pts', plain with plain); sign must agree (parentheses = negative); a
    currency printed on both sides must agree. Scale: each side uses its inline scale word, else the scale its context
    declares (table header 'in millions'), else 1. A claim with no scale of its own and no context is compared on the
    printed numeral as well (restating a table cell). The claim may round the source to the claim's printed precision,
    never the reverse."""
    if claim.unit != src.unit:
        return False, f"unit differs ({claim.unit or 'plain'} vs {src.unit or 'plain'})"
    if claim.currency and src.currency and claim.currency != src.currency:
        return False, "currency differs"
    cs = claim.scale or claim_ctx
    ss = src.scale or src_ctx
    cands = []
    if cs:
        cands.append((claim.num * cs, src.num * (ss or 1.0), cs))
    else:
        cands.append((claim.num, src.num, 1.0))                         # numeral as printed
        if ss:
            cands.append((claim.num, src.num * ss, 1.0))                # claim printed the full value
    hit = any(abs(a - b) <= tolerance(claim, sc) for a, b, sc in cands)
    if not hit:
        return False, "value differs"
    if claim.neg != src.neg:
        return False, "sign differs"
    return True, ""
