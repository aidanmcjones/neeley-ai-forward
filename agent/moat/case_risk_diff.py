"""Risk-factor and MD&A language drift between two annual reports of one company.

Answers: which sentences did the company add, drop or reword in its risk factors (10-K Item 1A, 20-F Item 3.D or the
annual report risk overview) and its MD&A (10-K Item 7, 20-F Item 5 or the annual report financial review) between
the latest annual report and the one before?

    from agent.moat.case_risk_diff import risk_diff
    risk_diff("MRK", section="risk_factors", k=20)
    risk_diff(ticker, section="risk_factors"|"mdna"|"both", fy=None, prev=None, k=60, min_chars=80)

`fy` / `prev` are annual_report doc_ids ("MRK:10k_FY2025.md") or years ("2025", "FY2025"). Defaults: the latest
annual report period for the ticker and the one before. For 20-F filers the main 20-F is read first; when its section
is short (under MIN_WORDS words, e.g. NVO and AZN incorporate their risk overview and financial review by reference)
the same-period companion doc (NVO `_d2` annual report, AZN `_ex15d1` exhibit) is appended.

Rows (sorted by `salience`, highest first, at most `k` diff rows per section, plus one kind="section_stats" row per
section): ticker, kind ("added" | "removed" | "changed" | "section_stats"), section, text, prev_text, citation, url,
locator, source_id, doc_id, page_no, prev_citation, prev_url, prev_locator, prev_doc_id, prev_page_no, quote_grade "",
license, similarity, diff (word level "-old +new" for changed rows), salience, flags.
For "added" and "changed" rows text is the new sentence on the new doc page. For "removed" rows text and prev_text are
the old sentence and the citation/locator point to the old doc page (it is not in the new doc). For "section_stats"
rows text is the section heading as printed on its first page, and words / prev_words / delta_words / pct_change /
summary carry the counts. Every text passes cite.verify_quote(text, doc_id, page_no) on its locator, and every
prev_text passes it on prev_locator; rows that fail are dropped. A section_stats row flagged "coverage_mismatch" (section
sizes more than 3x apart, usually a doc captured as one giant page in one year) comes with no diff rows.

CLI: python -m agent.moat.case_risk_diff MRK [--section both] [--fy 2025] [--prev 2024] [-k 20]
"""

import argparse
import difflib
import re
import sys
import time
from functools import lru_cache

from agent.moat import cite as C
from agent.moat.case_sets import all_drugs

MIN_WORDS = 1500  # locate(): a main-doc section shorter than this pulls in the same-period companion doc
COMPANION_WORDS = 3000  # risk_diff(): companions are used in both years when either main section is shorter
MISMATCH_RATIO = 3.0  # section word counts this far apart are reported in section_stats but not diffed
MAX_TEXT = 590
HEAD = r"(?:^|\n)[ \t​ >*#|]*"  # heading must start a line (markdown and zero-width noise allowed)

SECTIONS = {
    "risk_factors": {
        "label": "risk factors",
        "items": [
            (r"item\s*1a\.?\s*[:\-\u2013\u2014]?\s*\**\s*risk\s+factors", r"item\s*1b\b|item\s*1c\b|item\s*2\.?\s*\**\s*properties"),
            (r"(?:item\s*3\.?\s*)?d\.\s*risk\s+factors", r"item\s*4\.?\s*\**\s*information\s+on\s+the\s+company"),
        ],
        # running header/footer that tags a page of an annual-report style doc as part of the section
        "tag": r"risk overview|/\s*risk management\b|risk management\s*\(continued\)|/\s*key operational risks\b",
    },
    "mdna": {
        "label": "MD&A",
        "items": [
            (r"item\s*7\.?\s*[:\-\u2013\u2014]?\s*\**\s*management[’']?s\s+discussion", r"item\s*7a\b"),
            (r"item\s*5\.?\s*[:\-\u2013\u2014]?\s*\**\s*operating\s+and\s+financial\s+review",
             r"item\s*6\.?\s*[:\-\u2013\u2014]?\s*\**\s*directors"),
        ],
        "tag": r"\bfinancial review\b|/\s*financial performance\b|/\s*financials\b",
    },
}

KEYWORDS = {  # salience boosts, matched case-insensitively on word boundaries
    "material": 0.5, "materially": 0.5, "may not": 0.5, "could": 0.3, "no longer": 0.8, "new": 0.3,
    "IRA": 1.0, "Inflation Reduction Act": 1.0, "Medicare": 0.8, "Medicaid": 0.5, "tariff": 1.0, "tariffs": 1.0,
    "MFN": 1.0, "most favored nation": 1.0, "most-favored-nation": 1.0, "litigation": 0.6, "exclusivity": 0.9,
    "generic": 0.8, "generics": 0.8, "biosimilar": 0.9, "biosimilars": 0.9, "negotiation": 0.6, "negotiated": 0.6,
    "maximum fair price": 1.0, "patent": 0.5, "loss of": 0.4, "impairment": 0.6, "investigation": 0.5,
    "subpoena": 0.8, "recall": 0.5, "shortage": 0.5, "compounded": 0.8, "compounding": 0.8, "China": 0.5,
    "pricing": 0.4, "rebate": 0.5, "rebates": 0.5, "340B": 0.9, "PBM": 0.7, "decline": 0.4, "declined": 0.4,
}
YEAR = re.compile(r"^(?:fy)?(?:19|20)\d\d[,.;:)]*$", re.I)
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
SENT_RE = re.compile(r"(?<=[.!?;])\s+(?=[\"“(•A-Z0-9])|\s+•\s+")
DOC_SUFFIX = re.compile(r"_(?:d\d+|ex[\w]+)\.md$", re.I)


# ---------------------------------------------------------------- docs

def _annuals(ticker):
    rows = C.db().execute("SELECT doc_id, period, stream, n_pages FROM docs WHERE ticker=? AND doc_type='annual_report' "
                          "AND superseded_by='' ORDER BY period", (ticker.upper(),)).fetchall()
    by = {}
    for r in rows:
        by.setdefault(r["period"], []).append(r)
    out = []
    for period, ds in sorted(by.items()):
        # main doc first: no _d2/_ex suffix, corpus stream, then most pages
        ds = sorted(ds, key=lambda r: (bool(DOC_SUFFIX.search(r["doc_id"])), r["stream"] != "corpus", -r["n_pages"]))
        out.append((period, [r["doc_id"] for r in ds]))
    return out


def _resolve(annuals, want, default_idx):
    if want is None:
        return annuals[default_idx] if len(annuals) >= abs(default_idx) else None
    for period, ids in annuals:
        if want in ids:
            return period, [want] + [i for i in ids if i != want]
    y = re.sub(r"\D", "", str(want))[:4]
    hits = [a for a in annuals if a[0][:4] == y]
    return hits[-1] if hits else None


def _pages(doc_id):
    return [(r["page_no"], r["text"] or "") for r in
            C.db().execute("SELECT page_no, text FROM pages WHERE doc_id=? ORDER BY page_no", (doc_id,))]


# ---------------------------------------------------------------- section location

def _item_section(pages, start_re, end_re):
    """Longest span from a line-start heading matching start_re to the next end_re heading. [(page_no, text)]."""
    s_re, e_re = re.compile(HEAD + start_re, re.I), re.compile(HEAD + end_re, re.I)
    flat, offs = [], []
    pos = 0
    for no, t in pages:
        offs.append((pos, no, t))
        flat.append(t)
        pos += len(t) + 1
    full = "\n".join(flat)
    ends = [m.start() for m in e_re.finditer(full)]
    best = None
    for m in s_re.finditer(full):
        st = m.start() + (1 if full[m.start()] == "\n" else 0)
        nxt = [e for e in ends if e > m.end()]
        en = nxt[0] if nxt else None
        if en is None:
            continue
        if not best or en - st > best[1] - best[0]:
            best = (st, en)
    if not best:
        return []
    st, en = best
    out = []
    for base, no, t in offs:
        a, b = max(st, base), min(en, base + len(t))
        if a < b:
            out.append((no, t[a - base:b - base]))
    return out


def _split_running(text):
    """Split a one-page mega doc (e.g. NVO _d2) at its running 'Annual Report 20xx /' headers."""
    cuts = [m.start() for m in re.finditer(r"(?:[A-Z][\w&]+\s+)*Annual\s+Report\s+20\d\d(?:\s*/|\s+\d{1,3}\b)", text)]
    if len(cuts) < 3:
        return [text]
    bounds = [0] + cuts + [len(text)]
    return [text[a:b] for a, b in zip(bounds, bounds[1:]) if b > a]


def _tag_section(pages, tag_re):
    """Longest run of pages (one untagged page allowed inside the run) whose header or footer matches tag_re."""
    t_re = re.compile(tag_re, re.I)
    units, tagged = [], []
    for no, t in pages:
        if len(t) > 100000:  # pseudo pages: the running header opens each segment, so test the head only
            for seg in _split_running(t):
                units.append((no, seg))
                tagged.append(bool(t_re.search(" ".join(seg[:220].split()))))
        else:
            units.append((no, t))
            tagged.append(bool(t_re.search(" ".join(t[:220].split())) or t_re.search(" ".join(t[-320:].split()))))
    best, cur, gap = (0, 0), None, 0
    for i, ok in enumerate(tagged + [False, False]):
        if ok:
            if cur is None:
                cur = i
            gap = 0
            end = i + 1
            if end - cur > best[1] - best[0]:
                best = (cur, end)
        elif cur is not None:
            gap += 1
            if gap > 1:
                cur, gap = None, 0
    return units[best[0]:best[1]]


def _words(chunks):
    return sum(len(re.findall(r"[A-Za-z]{2,}", t)) for _, t in chunks)


@lru_cache(maxsize=64)
def _doc_section(doc_id, section):
    """(item-heading chunks, running-header chunks) for one doc."""
    spec = SECTIONS[section]
    pages = _pages(doc_id)
    chunks = []
    for s, e in spec["items"]:
        chunks = _item_section(pages, s, e)
        if _words(chunks) >= 150:
            break
    if _words(chunks) < 150:
        chunks = []
    return chunks, _tag_section(pages, spec["tag"])


def locate(doc_ids, section, companion=None):
    """[(doc_id, page_no, text)] for the section in one fiscal year.

    The main doc's item section comes first (its running-header section when no item heading is found). Companion
    docs of the same period (20-F exhibits) are appended when companion=True, or, when companion is None, when the
    main section has fewer than MIN_WORDS words."""
    if not doc_ids:
        return []
    item, tagged = _doc_section(doc_ids[0], section)
    main = item or (tagged if _words(tagged) >= 150 else [])
    out = [(doc_ids[0], no, t) for no, t in main]
    if companion is None:
        companion = _words(main) < MIN_WORDS
    if companion:
        for doc_id in doc_ids[1:3]:
            c_item, c_tag = _doc_section(doc_id, section)
            best = max((c_item, c_tag), key=_words)
            if _words(best) >= 150:
                out += [(doc_id, no, t) for no, t in best]
    return out


def main_words(doc_ids, section):
    if not doc_ids:
        return 0
    item, tagged = _doc_section(doc_ids[0], section)
    return _words(item or (tagged if _words(tagged) >= 150 else []))


# ---------------------------------------------------------------- sentences and diff

def _sentences(chunks, min_chars):
    out = []
    for doc_id, no, text in chunks:
        # paragraphs = runs of non-blank, non-table lines; single newlines inside a paragraph are PDF line wraps
        # a blank line is a paragraph break only when the next line opens a new sentence (some PDF conversions put a
        # blank line after every visual line); joining lines only inserts whitespace, so quotes still verify
        paras, cur, blank = [], [], False
        for line in text.split("\n"):
            s = line.strip()
            if s.startswith("|"):
                if cur:
                    paras.append(" ".join(cur))
                cur, blank = [], False
            elif not s:
                blank = True
            else:
                if blank and cur and (re.search(r"[.!?:;”\"]$", cur[-1]) or not re.match(r"[a-z(\d$%,]", s)):
                    paras.append(" ".join(cur))
                    cur = []
                cur.append(s)
                blank = False
        if cur:
            paras.append(" ".join(cur))
        for s in paras:
            for sent in SENT_RE.split(" ".join(s.split())):
                sent = sent.strip(" ​•*#>-")
                if len(sent) < min_chars or len(re.findall(r"[A-Za-z]{3,}", sent)) < 8:
                    continue
                if len(sent) > MAX_TEXT:
                    sent = sent[:MAX_TEXT].rsplit(" ", 1)[0]
                out.append({"doc_id": doc_id, "page_no": no, "text": sent, "key": _key(sent)})
    return out


def _key(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w%$ ]+", " ", s.lower())).strip()


def _toks(s):
    return set(re.findall(r"[a-z]{3,}", s.lower()))


def _jacc(a, b):
    return len(a & b) / (len(a | b) or 1)


def _word_diff(old, new):
    a, b = old.split(), new.split()
    parts, dels, ins = [], [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            dels += a[i1:i2]
            parts.append("-[" + " ".join(a[i1:i2]) + "]")
        if op in ("insert", "replace"):
            ins += b[j1:j2]
            parts.append("+[" + " ".join(b[j1:j2]) + "]")
    return " ".join(parts)[:400], dels, ins


def _pair(old_items, new_items, thresh):
    """Greedy fuzzy pairing of leftover removed vs added sentences. Returns pairs, unpaired old, unpaired new."""
    for x in old_items + new_items:
        x.setdefault("toks", _toks(x["text"]))
    cands = []
    for i, o in enumerate(old_items):
        for j, n in enumerate(new_items):
            if _jacc(o["toks"], n["toks"]) >= 0.4:
                r = difflib.SequenceMatcher(None, o["key"], n["key"], autojunk=False).ratio()
                if r >= thresh:
                    cands.append((r, i, j))
    used_o, used_n, pairs = set(), set(), []
    for r, i, j in sorted(cands, reverse=True):
        if i not in used_o and j not in used_n:
            used_o.add(i)
            used_n.add(j)
            pairs.append((old_items[i], new_items[j], r))
    return (pairs, [o for i, o in enumerate(old_items) if i not in used_o],
            [n for j, n in enumerate(new_items) if j not in used_n])


def diff_sentences(old, new, thresh=0.6):
    """(changed pairs [(old, new, ratio)], removed [old], added [new]) using SequenceMatcher on sentence keys."""
    sm = difflib.SequenceMatcher(None, [o["key"] for o in old], [n["key"] for n in new], autojunk=False)
    rem, add = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            rem += old[i1:i2]
            add += new[j1:j2]
    old_keys, new_keys = {o["key"] for o in old}, {n["key"] for n in new}
    rem = [o for o in rem if o["key"] not in new_keys]  # moved, not removed
    add = [n for n in add if n["key"] not in old_keys]
    seen, add2 = set(), []
    for n in add:
        if n["key"] not in seen:
            seen.add(n["key"])
            add2.append(n)
    seen, rem2 = set(), []
    for o in rem:
        if o["key"] not in seen:
            seen.add(o["key"])
            rem2.append(o)
    return _pair(rem2, add2, thresh)


# ---------------------------------------------------------------- salience

def _drug_re():
    names = set(all_drugs())
    names |= {r[0] for r in C.db().execute("SELECT DISTINCT drug FROM docs WHERE drug != ''") if r[0]}
    names = sorted({n.replace("_", " ") for n in names if len(n) > 3}, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.I) if names else None


KW_RE = {k: re.compile(r"\b" + re.escape(k) + r"\b", 0 if k.isupper() else re.I) for k in KEYWORDS}


def _score_text(s, drug_re):
    score, flags = 0.0, []
    nums = [n for n in NUM.findall(s) if not YEAR.match(n)]
    if nums:
        score += 0.5
        flags.append("number")
    if "%" in s:
        score += 0.5
        flags.append("%")
    if "$" in s:
        score += 0.5
        flags.append("$")
    for k, rx in KW_RE.items():
        if rx.search(s):
            score += KEYWORDS[k]
            flags.append(k)
    if drug_re:
        drugs = {m.group(1).lower() for m in drug_re.finditer(s)}
        if drugs:
            score += 0.7 * min(len(drugs), 3)
            flags += sorted(drugs)
    return score, flags


# ---------------------------------------------------------------- rows

def _cite(doc_id, page_no):
    c, url = C.cite(doc_id, page_no)
    return c, url, f"{doc_id}#p{page_no}"


def _base(ticker, kind, section, item, license_):
    c, url, loc = _cite(item["doc_id"], item["page_no"])
    return {"ticker": ticker, "kind": kind, "section": section, "text": item["text"], "prev_text": "",
            "citation": c, "url": url, "locator": loc, "source_id": loc, "doc_id": item["doc_id"],
            "page_no": item["page_no"], "prev_citation": "", "prev_url": "", "prev_locator": "", "prev_doc_id": "",
            "prev_page_no": None, "quote_grade": "", "license": license_, "similarity": None, "diff": "",
            "salience": 0.0, "flags": []}


def _with_prev(row, item):
    c, url, loc = _cite(item["doc_id"], item["page_no"])
    row.update(prev_text=item["text"], prev_citation=c, prev_url=url, prev_locator=loc, prev_doc_id=item["doc_id"],
               prev_page_no=item["page_no"])
    return row


def _heading(chunks, section):
    """A short verbatim heading line from the first chunk of the section (falls back to its first 80 chars)."""
    doc_id, no, text = chunks[0]
    for line in text.split("\n"):
        s = " ".join(line.split()).strip(" ​*#>")
        if 4 <= len(s) <= 120 and re.search(r"risk|management|operating|financial|review|item", s, re.I):
            return s
    s = " ".join(text.split()).strip(" ​")
    return s[:80].rsplit(" ", 1)[0]


def _verified(row):
    if not C.verify_quote(row["text"], row["doc_id"], row["page_no"]):
        return False
    return not row["prev_text"] or C.verify_quote(row["prev_text"], row["prev_doc_id"], row["prev_page_no"])


def _license(doc_ids):
    q = ",".join("?" * len(doc_ids))
    lic = {r[0] for r in C.db().execute(f"SELECT license FROM docs WHERE doc_id IN ({q})", doc_ids) if r[0]}
    return sorted(lic)[0] if lic else ""


def _section_rows(ticker, section, new_ids, old_ids, k, min_chars, drug_re):
    # same companion rule for both years, so a doc that exists in only one year cannot fake a diff
    use_comp = (min(main_words(new_ids, section), main_words(old_ids, section)) < COMPANION_WORDS
                and len(new_ids) > 1 and len(old_ids) > 1)
    new_chunks, old_chunks = locate(new_ids, section, use_comp), locate(old_ids, section, use_comp)
    if not new_chunks or not old_chunks:
        return []
    lic = _license(sorted({c[0] for c in new_chunks + old_chunks}))
    nw, ow = _words([(n, t) for _, n, t in new_chunks]), _words([(n, t) for _, n, t in old_chunks])
    # a section 3x longer or shorter than the prior year almost always means the two docs were captured differently
    # (e.g. a 1-page and a 31-page conversion); diffing them would list the whole section as added or removed
    mismatch = max(nw, ow) > MISMATCH_RATIO * max(min(nw, ow), 1)
    new_s, old_s = _sentences(new_chunks, min_chars), _sentences(old_chunks, min_chars)
    pairs, removed, added = ([], [], []) if mismatch else diff_sentences(old_s, new_s)
    rows = []
    for n in added:
        r = _base(ticker, "added", section, n, lic)
        sc, fl = _score_text(n["text"], drug_re)
        r.update(salience=round(1.0 + sc, 2), flags=fl)
        rows.append(r)
    for o in removed:
        r = _with_prev(_base(ticker, "removed", section, o, lic), o)
        sc, fl = _score_text(o["text"], drug_re)
        r.update(salience=round(0.9 + sc, 2), flags=fl)
        rows.append(r)
    for o, n, ratio in pairs:
        r = _with_prev(_base(ticker, "changed", section, n, lic), o)
        d, dels, ins = _word_diff(o["text"], n["text"])
        delta = " ".join(dels + ins)
        sc, fl = _score_text(delta, drug_re)
        sc_full, _ = _score_text(n["text"], drug_re)
        sal = 0.4 + 1.5 * (1 - ratio) + sc + 0.2 * sc_full
        changed_toks = [t for t in dels + ins if re.search(r"\w", t)]
        if changed_toks and all(YEAR.match(t.strip("()")) for t in changed_toks):
            sal *= 0.15
            fl = fl + ["year_rollforward"]
        r.update(similarity=round(ratio, 3), diff=d, salience=round(sal, 2), flags=fl)
        rows.append(r)
    rows = [r for r in rows if _verified(r)]
    rows.sort(key=lambda r: -r["salience"])
    rows = rows[:k]

    head_new, head_old = _heading(new_chunks, section), _heading(old_chunks, section)
    st = {"doc_id": new_chunks[0][0], "page_no": new_chunks[0][1], "text": head_new}
    stats = _with_prev(_base(ticker, "section_stats", section, st, lic),
                       {"doc_id": old_chunks[0][0], "page_no": old_chunks[0][1], "text": head_old})
    pct = round(100.0 * (nw - ow) / ow, 1) if ow else None
    stats.update(words=nw, prev_words=ow, delta_words=nw - ow, pct_change=pct,
                 sentences=len(new_s), prev_sentences=len(old_s), n_added=len(added), n_removed=len(removed),
                 n_changed=len(pairs),
                 pages=sorted({f"{d}#p{n}" for d, n, _ in new_chunks}),
                 prev_pages=sorted({f"{d}#p{n}" for d, n, _ in old_chunks}),
                 summary=(f"{SECTIONS[section]['label']}: {nw:,} words vs {ow:,} prior ({nw - ow:+,}"
                          f"{'' if pct is None else f', {pct:+.1f}%'}); {len(added)} added, {len(removed)} removed, "
                          f"{len(pairs)} changed sentences before the k cap"
                          + ("; not diffed: section sizes differ more than 3x, check the doc capture" if mismatch else "")),
                 flags=["coverage_mismatch"] if mismatch else [], salience=99.0)
    if not _verified(stats):
        return rows
    return [stats] + rows


def risk_diff(ticker, section="risk_factors", fy=None, prev=None, k=60, min_chars=80):
    """Sentence-level drift in risk factors and/or MD&A between two annual reports. See module docstring."""
    ticker = (ticker or "").upper()
    annuals = _annuals(ticker)
    if len(annuals) < 2 and not (fy and prev):
        return []
    new = _resolve(annuals, fy, -1)
    if not new:
        return []
    if prev is None:
        older = [a for a in annuals if a[0] < new[0]]
        old = older[-1] if older else None
    else:
        old = _resolve(annuals, prev, -2)
    if not old or old[0] == new[0]:
        return []
    secs = ["risk_factors", "mdna"] if section == "both" else [section]
    if any(s not in SECTIONS for s in secs):
        raise ValueError(f"section must be risk_factors, mdna or both, got {section!r}")
    drug_re = _drug_re()
    out = []
    for s in secs:
        out += _section_rows(ticker, s, new[1], old[1], k, min_chars, drug_re)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ticker")
    ap.add_argument("--section", default="risk_factors", choices=["risk_factors", "mdna", "both"])
    ap.add_argument("--fy")
    ap.add_argument("--prev")
    ap.add_argument("-k", type=int, default=20)
    ap.add_argument("--min-chars", type=int, default=80)
    a = ap.parse_args(argv)
    t0 = time.time()
    rows = risk_diff(a.ticker, section=a.section, fy=a.fy, prev=a.prev, k=a.k, min_chars=a.min_chars)
    if not rows:
        print(f"no rows: {a.ticker.upper()} needs two annual_report docs in the index with a locatable section")
        return
    for r in rows:
        if r["kind"] == "section_stats":
            print(f"[{r['section']}|section_stats] {r['summary']}")
            print(f"    new: {r['citation']} <{r['locator']}>  prev: {r['prev_citation']} <{r['prev_locator']}>")
            continue
        print(f"[{r['section']}|{r['kind']}] salience={r['salience']} {r['citation']} <{r['locator']}>"
              + (f"  prev: {r['prev_citation']} <{r['prev_locator']}>" if r["kind"] == "changed" else ""))
        print(f"    {r['text'][:300]}")
        if r["kind"] == "changed":
            print(f"    diff: {r['diff'][:240]}")
    print(f"({len(rows)} rows, {time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main(sys.argv[1:])
