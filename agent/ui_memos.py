#!/usr/bin/env python3
"""ui_memos: a library of cached chat answers and CEO memos for the judge-facing chatbot.

Reads the exported cockpit data in ui/public/data (meta.json, league.json, proof.json, companies/<T>.json)
and writes ui/public/data/memos.json (contract: docs/ui_memos.md). Every number printed in a memo carries a
[n] marker whose cite copies an evidence object from the company file, or a "row" cite that names the exact
data row it came from (league score, priced-in scorecard row, meta count, proof row). Nothing is written by a
model: stance text is the exporter's template stance (generated_by "template") or the DECIDE output
(generated_by "decide_v2"); tables and lists are assembled from data (generated_by "data").

    PYTHONPATH=. python -m agent.ui_memos            # write memos.json and _sample/memos.json
    PYTHONPATH=. python -m agent.ui_memos --check    # validate both files against the data they cite
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "ui" / "public" / "data"
SAMPLE = DATA / "_sample"

CHAT_KINDS = ("needle", "findings", "product", "peers", "priced_in", "why_company", "league", "needles", "products",
              "decides", "ai_wrong", "limits", "moat", "how_it_works")
MEMO_KINDS = ("ceo_memo", "prove_wrong")
ROW_ORDER = ("approved_uses", "safety", "dosing", "timeline", "pricing")

NICK = {  # extra name variants a judge might type (the canonical name comes from meta.companies)
    "MRK": ["Merck"], "BMY": ["BMS", "Bristol Myers", "Bristol"], "PFE": ["Pfizer"], "LLY": ["Lilly", "Eli Lilly"],
    "NVO": ["Novo", "Novo Nordisk"], "ABBV": ["AbbVie"], "JNJ": ["J&J", "Johnson and Johnson"],
    "AZN": ["AstraZeneca", "Astra"], "AMGN": ["Amgen"], "GILD": ["Gilead"],
}

LEADS = [  # plain-words lead by signal kind (same table as agent/ui_export.py)
    (("dio", "inventory"), "Inventory is building faster than sales"),
    (("dso", "receivables", "rec_gap"), "Customers are taking longer to pay than revenue growth explains"),
    (("rnd",), "R&D spending jumped as a share of revenue"),
    (("gross_margin",), "Gross margin moved sharply"),
    (("etr", "tax_rate"), "The effective tax rate swung"),
    (("impairment",), "A write-down hit the books"),
    (("label_broader",), "The label is broader than rivals'"),
    (("label_narrower",), "The label is narrower than rivals'"),
    (("dosing_advantage",), "Dosing is less frequent than rivals'"),
    (("dosing_burden",), "Dosing is more frequent than rivals'"),
    (("boxed_warning_disadvantage",), "It carries a boxed warning a rival does not"),
    (("boxed_warning_advantage",), "A rival carries a boxed warning it does not"),
    (("exclusivity",), "Exclusivity ends earlier than rivals'"),
    (("ira",), "Medicare price setting reaches this product"),
    (("mfn",), "The MFN agreement reaches Medicaid"),
    (("qa_",), "Management deflected an analyst question"),
    (("risk_", "mdna_"), "The filing wording changed"),
    (("trial",), "A late-stage trial was stopped"),
]

PROVE_WRONG = [  # early signals that would show the call is wrong, by kind (same table as the exporter)
    (("dio", "inventory"), "Inventory days fall back toward the peer median in the next two 10-Qs."),
    (("dso", "receivables", "rec_gap"), "Receivables growth falls back inside revenue growth in the next two 10-Qs."),
    (("rnd",), "R&D share of revenue returns toward the peer median in the next two 10-Qs."),
    (("gross_margin",), "Gross margin holds at the prior-year level in the next two quarterly reports."),
    (("etr", "tax_rate"), "The effective tax rate reverts to the prior-year level in the next 10-Q."),
    (("impairment",), "No further impairment on the same asset in the next two filings."),
    (("label", "dosing", "boxed"), "A new DailyMed label version for the product or a rival closes the gap within twelve months."),
    (("exclusivity",), "A settlement, court ruling or new patent listing moves the generic or biosimilar entry date."),
    (("mfn",), "The company's own disclosure puts the Medicaid MFN cost well below this estimate in the next 10-Q."),
    (("ira", "spend_per_claim"), "CMS's next selected-drug list or MFP schedule leaves the product's exposure unchanged."),
    (("qa_", "call_topic"), "Management gives the product-level number analysts asked for on the next earnings call."),
    (("risk_", "mdna_"), "The next 10-K drops or softens the new wording without a matching hit to results."),
    (("trial",), "The sponsor restarts or replaces the stopped trial within twelve months."),
]

OPTION_WHY = {
    "Defend": "fix the exposure the filings reveal (channel, receivables, margin, disclosure) before the market prices it",
    "Attack": "press a label, dosing or safety advantage over rivals with prescribers and payers",
    "Reprice": "reset net price and contracting where IRA, MFN or gross-to-net pressure lands",
    "Partner-or-buy": "license or acquire to replace revenue at risk from earlier exclusivity loss, a narrower label or a dropped trial",
}

NEEDLE_RULE = "the biggest cited impact that analysts asked about least"
STATUS_TEXT = {  # muted caveat shown only when the needle did not qualify on its own
    "provisional": "Caveat: analysts have asked about this item about as often as the company's other findings, so "
                   "it is the needle only provisionally.",
    "floor_relaxed": "Caveat: no finding at this company was rarely discussed; this is the best row from its "
                     "least-discussed group.",
    "none": "Caveat: no finding at this company was rarely discussed, so the largest cited impact is shown and "
            "labelled, not promoted.",
}
PRICED_CALL = {  # needle status -> plain priced-in call, by the same rule (how rarely analysts asked)
    "strict": "not priced in: analysts rarely asked about the needle item",
    "provisional": "only partly priced in: analysts asked about it about as often as the company's other findings",
    "floor_relaxed": "mostly priced in: no finding at this company was rarely discussed",
    "none": "priced in: no finding at this company was rarely discussed",
}
ACTION_WORDS = {  # decide kill-signal action codes -> plain words
    "bayes": "update the scenario weights with the observed signal",
    "replace_bear": "replace the bear case with the observed path and re-run the valuation",
    "review": "review the move at the next board cycle", "stop": "stop the move",
}
PITCH_FORBIDDEN = re.compile(r"\bscore L\b|\bS = |materiality score|robustness", re.I)
PART2 = [  # case Part 2 elements a CEO memo must carry, as a heading or a kpi label
    ("one CEO move", r"^Recommendation"), ("budget", r"^Budget"), ("return math", r"^Return math|^Expected value"),
    ("two rejected alternatives", r"^Alternatives rejected"), ("6 to 12 month kill signals", r"prove us wrong|^Kill signals"),
    ("why it lands with the deciders", r"deciders"),
]
PART1_COLUMNS = ("Impact", "Peer", "Confidence", "Source")

DEMO_NOTE = "Pipeline demonstration; not the team's Part 2 recommendation, which follows the company pick."
DEMO_LABEL = ("Pipeline demonstration: this move was valued by rules on cited findings; the team's final "
              "recommendation is a separate decision.")
TEMPLATE_LABEL = ("Template stance, no valued move yet: options are ranked by rules on the verified findings; "
                  "no budgeted move has been valued for this company.")

# number whitelist for the --check pass: digits inside these patterns need no [n] marker
WHITELIST = [
    r"\[\d+\]",                                   # cite markers
    r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b",            # ISO dates (before the year pattern)
    r"\b(?:FY)?(?:19|20)\d{2}(?:Q[1-4])?\b",      # years, FY2024, 2026Q2
    r"\bQ[1-4]\s?(?:19|20)\d{2}\b",               # Q2 2026
    r"\b(?:10-K|10-Q|20-F|8-K|6-K)s?\b",           # filing forms
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, (?:19|20)\d{2}\b",  # written dates
    r"\bPart [BD]\b", r"\bSection 232\b",         # Medicare parts, tariff statute
    r"\bPart [12]\b",                              # the case's Part 1 / Part 2
    r"\b[0-9a-f]{12}(?:-d\d)?\b",                 # finding ids
    r"\bR\d{3}\b",                                 # traceable moat row ids
    r"\b\d+(?: to \d+)? (?:months|quarters)\b",   # horizon phrases in prove-wrong rules
    r"\bsha256\b", r"\bH = \d\b",                   # method names
    r"\bp\. ?[0-9A-Z-]+\b",                        # page labels inside a Source cell
]
WHITELIST_NOTE = ("whitelisted without a marker: years and fiscal periods, ISO dates, filing form names, Medicare "
                  "Part B/D, Section 232, finding ids and R-row ids, horizon phrases such as 'next 6 to 12 months', "
                  "page labels in Source cells, and kpi labels")


# ---------------------------------------------------------------- small helpers
def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def money(x):
    if x is None:
        return "n/a"
    return f"${x / 1e9:,.2f}B" if abs(x) >= 1e9 else f"${x / 1e6:,.0f}M"


def match_rule(kind, rules):
    for keys, val in rules:
        if any(k in (kind or "") for k in keys):
            return val
    return None


PROPER = {"Medicare", "Medicaid", "CMS", "MFN", "US", "FDA", "SEC", "TrumpRx", "Part", "IRA", "Q3", "R&D"}


def lc(lead):
    """Lowercase a lead phrase's first letter unless it opens with a proper noun."""
    first = (lead or "").split(" ")[0]
    return lead if first in PROPER or first.isupper() or not lead else lead[0].lower() + lead[1:]


def poss(name):
    return name + "'" if name.endswith("s") else name + "'s"


def norm_alias(s):
    return re.sub(r"[^a-z0-9&]+", " ", (s or "").lower()).strip()


def words(md):
    return len(re.sub(r"\[\d+\]", "", md or "").split())


def clip(text, n=20):
    """First n words of a marked text; markers stay attached to their word (a derived marker contains spaces)."""
    toks = re.findall(r"(?:\[[^\]]*\]|\S)+", text or "")
    return " ".join(toks) if len(toks) <= n else " ".join(toks[:n]).rstrip(",;:") + " ..."


def rest_marks(full, clipped, C):
    """Markers present in the full marked text but cut from its clipped form, so the cites stay referenced."""
    have = set(seg_markers(clipped)[0])
    return C.mark(*[n for n in seg_markers(full)[0] if n not in have])


CHANNEL_WORDS = {"ira_mfp": "Medicare negotiated price", "ira_expected": "expected Medicare price setting",
                 "loe_erosion": "loss of exclusivity", "mfn_cash_price": "most-favored-nation cash price",
                 "label_breadth_medicare": "Medicare label breadth"}


def attention_words(f, ctx, t, C):
    """(sentence, cites) on analyst attention from the engine's note, without scorecard mechanics: counts from the
    calls data ("Analysts have not asked about it on the last N calls" / "Analysts raised it in M of the last N
    calls"), the scorecard row's quarters when the note only carries a scorecard share, else "not measurable"."""
    note, ons = obscurity_cite(f, C, t)
    if not note:
        return "Analyst attention: not measurable from the calls we hold", []
    m = re.search(r"qa_turns regex '[^']+': (\d+) of (\d+) quarters", note) or re.search(r"qa_turns: analysts named \S+ in (\d+) of (\d+) quarters", note)
    if m:
        a, n = int(m.group(1)), int(m.group(2))
        return (f"Analysts have not asked about it on the last {n} calls" if a == 0 else f"Analysts raised it in {a} of the last {n} calls"), ons
    m = re.search(r"priced_in_scorecard \w+ (\w+): ([\d.]+)", note)
    if m and ctx is not None:
        row = next((r for r in (ctx.companies.get(t) or {}).get("priced_in") or [] if r.get("topic") == m.group(1)), None)
        if row and row.get("quarters_covered"):
            a, n = int(row.get("quarters_asked") or 0), int(row["quarters_covered"])
            pn = priced_in_cite(t, row, C)
            return (f"Analysts have not asked about it on the last {n} calls" if a == 0 else f"Analysts raised it in {a} of the last {n} calls"), ons + [pn]
    return "Analyst attention: not measurable from the calls we hold", ons


def attention_cell(note):
    """The analyst-attention clause of a plain attention note, short enough for a table cell."""
    t = plain_obscurity(note).rstrip(".")
    if "; " in t:
        t = t.rsplit("; ", 1)[1]
    elif ", and " in t:
        t = t.split(", and ", 1)[1]
    return t[0].upper() + t[1:] if t else "not tested"


def shorten(text, n=150):
    """Cut long cell text at a clause boundary so no number is cut in half."""
    text = (text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n]
    for sep in ("; ", ". ", ", "):
        i = cut.rfind(sep)
        if i > n // 2:
            return cut[:i] + " ..."
    i = cut.rfind(" ")
    return cut[:i] + " ..." if i > 0 else cut + " ..."


def fmt_metric(kind, v):
    if v is None:
        return "n/a"
    k = kind or ""
    if any(x in k for x in ("dso", "dio")):
        return f"{v:.0f} days"
    if any(x in k for x in ("outpace", "rec_gap", "faers", "demand")):
        return f"{v * 100:+.1f} pts"
    if any(x in k for x in ("margin", "tax", "rnd", "etr")):
        return f"{v * 100:.1f}%"
    return f"{v:.2f}"


def nc_status(f):
    return ((f or {}).get("numeric_check") or {}).get("status")


def verification_str(e):
    v = e.get("verification")
    if isinstance(v, dict):
        return v.get("status") or "unverified"
    if isinstance(v, str) and v:
        return v
    ex = e.get("excerpt") or {}
    return "located" if isinstance(ex, dict) and ex.get("located") else "sample"


# ---------------------------------------------------------------- cites
class Cites:
    """Per-memo cite book: evidence objects and data-row cites, numbered in order of first use."""

    def __init__(self):
        self.items, self.by_id = [], {}

    def add(self, cite):
        cid = cite["cite_id"]
        fid = cite.get("finding_id")
        if cid in self.by_id:
            n = self.by_id[cid]
            prev = self.items[n - 1]
            if fid and fid not in prev["finding_ids"]:
                prev["finding_ids"].append(fid)
            return n
        n = len(self.items) + 1
        self.items.append({"n": n, **cite, "finding_ids": [fid] if fid else []})
        self.by_id[cid] = n
        return n

    @staticmethod
    def mark(*ns):
        return "".join(f"[{n}]" for n in dict.fromkeys(n for n in ns if n))

    def after(self, text, *ns):
        """text followed by its markers; nothing appended when the text already carries inline markers."""
        marks = self.mark(*ns)
        return f"{text} {marks}" if marks else text


# ---------------------------------------------------------------- inline markers ([n], [derived: a, b], [constant: X], [assumption])
MARK = re.compile(r"\[(\d+)\]|\[derived: ([^\]]+)\]|\[constant: ([A-Za-z0-9_]+)\]|\[assumption(?:: [^\]]*)?\]|\[licensed source\]")
LICENSED = "[licensed source]"
MAX_TAIL = 6  # a sentence's trailing run of blanket cites is capped at this many markers in a memo


def strip_marks(text):
    return MARK.sub("", text or "")


def finding_cite_index(f):
    """cite_id -> (evidence object, ev_cite index) over a finding's evidence and data citations."""
    out = {}
    for i, e in enumerate(f.get("evidence") or []):
        out.setdefault(e.get("cite_id"), (e, i))
    for i, e in enumerate(f.get("data_citations") or []):
        out.setdefault(e.get("cite_id"), (e, 100 + i))
    return out


def _dedupe_runs(text):
    def run(m):
        toks = re.findall(r"\[[^\]]+\]", m.group(0))
        return "".join(dict.fromkeys(toks))
    return re.sub(r"(?:\[[^\]]+\])+", run, text)


def _cap_tail(text, limit):
    m = re.search(r"((?:\[\d+\]|\[licensed source\])+)\s*$", text)
    if not m:
        return text
    toks = re.findall(r"\[[^\]]+\]", m.group(1))
    nums = [x for x in toks if x != LICENSED][:limit]
    keep = nums + ([LICENSED] if LICENSED in toks else [])
    return text[:m.start(1)] + "".join(keep)


def remark(text, f, C, t, limit=MAX_TAIL, mm=None, lic=None, unresolved=()):
    """Renumber a finding's marked text to this memo's cite numbers: [n] is the finding's footnote number, which
    marker_map turns into a cite_id; [derived: a, b] operands are renumbered the same way; [constant: X] and
    [assumption] and [assumption: reason] pass through (the UI shows the reason in a tooltip); a footnote on a
    licensed data row prints as [licensed source]; an unresolved
    footnote is dropped (the number stays, as it is also in the gated sentence). `mm` and `lic` default to the
    finding's own maps; a findings_table row passes its own."""
    mm = mm if mm is not None else (f.get("marker_map") or {})
    lic = {int(x) for x in (lic if lic is not None else (f.get("marker_licensed") or []))}
    unresolved = {int(x) for x in unresolved}
    index = finding_cite_index(f)
    cache = {}

    def memo_n(n):
        if n not in cache:
            if n in lic:
                cache[n] = "licensed"
            elif n in unresolved:
                cache[n] = None
            else:
                hit = index.get(mm.get(str(n))) if mm.get(str(n)) else None
                cache[n] = C.add(ev_cite(hit[0], f.get("id"), t, hit[1])) if hit else None
        return cache[n]

    text = text or ""
    tail = re.search(r"((?:\[\d+\])+)\s*$", text)
    if tail:  # cap the trailing run of blanket cites before any cite is added to the memo
        nums = [int(x) for x in re.findall(r"\[(\d+)\]", tail.group(1))]
        keep = [n for n in nums if n not in lic][:limit] + [n for n in nums if n in lic][:1]
        text = text[:tail.start(1)] + "".join(f"[{n}]" for n in nums if n in keep)

    def sub(m):
        if m.group(1):
            r = memo_n(int(m.group(1)))
            return LICENSED if r == "licensed" else (f"[{r}]" if r else "")
        if m.group(2):
            out, lic_hit = [], False
            for x in (x.strip() for x in m.group(2).split(",")):
                if x.isdigit():
                    r = memo_n(int(x))
                    if r == "licensed":
                        lic_hit = True
                    elif r:
                        out.append(str(r))
                elif x:
                    out.append(x)
            if out:
                return f"[derived: {', '.join(dict.fromkeys(out))}]" + (LICENSED if lic_hit else "")
            return LICENSED if lic_hit else ""
        return m.group(0)
    return _cap_tail(_dedupe_runs(MARK.sub(sub, text)), limit)


def marked_sentence(f, C, t, row=None, unresolved=()):
    """The finding's sentence_marked (or the findings_table row's, resolved through the row's marker_map)
    renumbered for this memo, or None when the export carries no marked sentence."""
    src = row if isinstance(row, dict) and row.get("sentence_marked") else f
    sm = src.get("sentence_marked")
    if not isinstance(sm, str) or not sm.strip():
        return None
    s = remark(plain_sentence(sm.strip()), f, C, t, mm=src.get("marker_map") or {}, lic=src.get("marker_licensed") or [],
               unresolved=unresolved if src is row else ())
    s = re.sub(r"\.\s*((?:\[[^\]]+\])+)\s*$", r"\1", s)
    s = own_discount(s, C)
    return s.rstrip(".")


def own_discount(text, C):
    """'(CMS-published analog, cited)' becomes 'negotiated discount for this drug' when the discount's cite quote names
    the drug itself (the row is the drug's own CMS line, not a borrowed analog)."""
    m = re.search(r"^(\w[\w-]*)'s .*?discount [\d.]+%\[(\d+)\] \(CMS-published analog, cited\)", text)
    if not m:
        return text
    drug, n = m.group(1), int(m.group(2))
    cite = C.items[n - 1] if 0 < n <= len(C.items) else {}
    if drug.lower() in f"{cite.get('quote') or ''} {cite.get('excerpt') or ''}".lower():
        return text.replace("(CMS-published analog, cited)", "(CMS-published negotiated discount for this drug)", 1)
    return text


GENERIC_TITLES = {"government document", "document", "source", ""}


def doc_label(e):
    """A readable document title; the exporter labels some government files 'government document'."""
    title = (e.get("doc_title") or e.get("doc_label") or "").replace("(third_party)", "(third-party transcript)")
    title = re.sub(r"^moat table (?:[\w]+/)*([\w-]+)\.csv$", lambda m: "verified data table: " + m.group(1).replace("_", " ") + " (machine data)", title)
    if title.lower() not in GENERIC_TITLES:
        return title
    did = e.get("doc_id") or ""
    date = re.search(r"(?:19|20)\d{2}-\d{2}-\d{2}", did)
    if "/wh/" in did or "whitehouse.gov" in (e.get("url") or ""):
        return "White House fact sheet" + (f" {date.group(0)}" if date else "")
    if "/cms/" in did or "cms.gov" in (e.get("url") or ""):
        return "CMS document" + (f" {date.group(0)}" if date else "")
    cit = re.split(r"[,(§]", e.get("citation") or "")[0].strip()
    return cit if cit and cit.lower() not in GENERIC_TITLES else (title or "source document")


VERBATIM = ("exact", "substring", "fuzzy")


def verbatim_quote(e):
    """The cite's quote only when it is a located page quote (exact, substring or fuzzy); a constructed line
    (number_match with a quote_note) is never printed as a quote."""
    return (e.get("quote") or None) if verification_str(e) in VERBATIM else None


def cite_text(e):
    """Text that carries the cited value, for numeric gating only: the quote, the located excerpt match, a
    constructed line (labelled by quote_note) and the value itself."""
    ex = e.get("excerpt") if isinstance(e.get("excerpt"), dict) else {}
    return " ".join(str(x) for x in (e.get("quote"), ex.get("match"), e.get("value")) if x)


def ev_cite(e, finding_id, ticker, idx=0):
    withheld = bool(e.get("withheld"))
    url = e.get("deep_link") or e.get("url")
    return {
        "cite_id": e.get("cite_id") or f"ev:{finding_id}:{idx}", "finding_id": finding_id, "ticker": ticker,
        "doc_title": doc_label(e), "doc_title_raw": e.get("doc_title"), "period": e.get("period"),
        "page": e.get("printed") or e.get("page"), "file_page": e.get("page"), "location": e.get("location"),
        "citation": e.get("citation"), "doc_type": e.get("doc_type"), "speaker": e.get("speaker") or None,
        "claim_type": e.get("claim_type"), "value": e.get("value"),
        "quote": None if withheld else e.get("quote"), "excerpt": None if withheld else e.get("excerpt"),
        "url": None if withheld else url, "withheld": withheld, "withheld_reason": e.get("withheld_reason"),
        "verification": verification_str(e), "derived_from": e.get("derived_from"),
        "derived_expr": e.get("derived_expr"), "numeric_check": None,
        "quote_note": e.get("quote_note") or None, "viewer_link": e.get("viewer_link") or None,
    }


def row_cite(cid, ref, doc_title, quote, verification, ticker=None, finding_id=None, page=None, url=None, value=None):
    """A cite to a data row rather than a page: `ref` names the exact JSON path the checker resolves."""
    return {
        "cite_id": cid, "finding_id": finding_id, "ticker": ticker, "doc_title": doc_title, "period": None,
        "page": page, "quote": quote, "excerpt": None, "url": url, "withheld": False, "withheld_reason": None,
        "verification": verification, "derived_from": None, "numeric_check": None, "ref": ref,
        "value": None if value is None else str(value),
    }


def resolve_ref(ref, ctx):
    """Resolve 'file.json:a.b[k=v].c[3]' against the data dir. Returns (object or None, error)."""
    file, _, path = ref.partition(":")
    obj = ctx.file(file)
    if obj is None:
        return None, f"file {file} missing"
    segs, buf, depth = [], "", 0
    for ch in path:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "." and depth == 0:
            segs.append(buf)
            buf = ""
        else:
            buf += ch
    if buf:
        segs.append(buf)
    for seg in segs:
        m = re.match(r"^([^\[]*)((?:\[[^\]]*\])*)$", seg)
        key, sels = m.group(1), re.findall(r"\[([^\]]*)\]", m.group(2))
        if key:
            if not isinstance(obj, dict) or key not in obj:
                return None, f"key {key} missing"
            obj = obj[key]
        for sel in sels:
            if not isinstance(obj, list):
                return None, f"selector [{sel}] on non-list"
            if "=" in sel:
                k, v = sel.split("=", 1)
                hits = [x for x in obj if isinstance(x, dict) and str(x.get(k)) == v]
                if not hits:
                    return None, f"no row with {k}={v}"
                obj = hits[0]
            else:
                try:
                    obj = obj[int(sel)]
                except (ValueError, IndexError):
                    return None, f"bad index [{sel}]"
    return obj, None


# ---------------------------------------------------------------- data context
class Ctx:
    def __init__(self, data_dir, sample=False):
        self.dir, self.sample = Path(data_dir), sample
        self.meta = read_json(self.dir / "meta.json", {}) or {}
        self.league = read_json(self.dir / "league.json", []) or []
        self.proof = read_json(self.dir / "proof.json", {}) or {}
        self.companies, self.names = {}, {}
        for row in self.meta.get("companies") or []:
            self.names[row["ticker"]] = row.get("name") or row["ticker"]
        for p in sorted((self.dir / "companies").glob("*.json")):
            c = read_json(p)
            if c and c.get("findings") is not None:
                self.companies[c["ticker"]] = c
                self.names.setdefault(c["ticker"], c.get("name") or c["ticker"])
        self.league_by = {r["ticker"]: r for r in self.league}
        self.tickers = [r["ticker"] for r in self.league if r["ticker"] in self.companies] + \
                       [t for t in self.companies if t not in self.league_by]
        d = self.meta.get("default_ticker")
        self.default = d if d in self.companies else (self.tickers[0] if self.tickers else None)
        self._files = {}

    def file(self, name):
        if name not in self._files:
            if name == "meta.json":
                self._files[name] = self.meta
            elif name == "league.json":
                self._files[name] = self.league
            elif name == "proof.json":
                self._files[name] = self.proof
            elif name.startswith("companies/"):
                self._files[name] = self.companies.get(name[len("companies/"):-5])
            else:
                self._files[name] = None
        return self._files[name]

    def name(self, t):
        return self.names.get(t, t)

    def nicks(self, t):
        out = [self.name(t)] + [n for n in NICK.get(t, []) if n != self.name(t)]
        return list(dict.fromkeys(out))

    def finding(self, t, fid):
        c = self.companies.get(t) or {}
        for f in c.get("findings") or []:
            if f.get("id") == fid or f.get("source_id") == fid:
                return f
        for v2 in ((c.get("labels") or {}).get("v2") or {}).values():
            for f in (v2 or {}).get("findings") or []:
                if isinstance(f, dict) and f.get("id") == fid:
                    return f
        return None

    def usable(self, t):
        """Verified findings with page evidence whose numeric check did not fail, best first."""
        fs = [f for f in self.companies[t].get("findings") or []
              if (f.get("verdict") or "verified") == "verified" and nc_status(f) != "failed" and f.get("evidence")
              and not label_cell_uncited(self.companies[t], f)]

        def key(f):
            imp = f.get("impact") or {}
            usd = imp.get("dollars") if (imp.get("currency") or "USD") == "USD" and not imp.get("suspect") else None
            return (-(f.get("score") or 0), -(usd or 0), 0 if f.get("confidence") == "high" else 1, -len(f["evidence"]))
        return sorted(fs, key=key)

    def needle(self, t):
        """(finding, status). The pitch-facing needle is needle_id_rule (the plain rule); status is the league
        status only when the rule needle is the league needle, else None (nothing is said about the league)."""
        c = self.companies[t]
        lid = c.get("needle_id") or (self.league_by.get(t) or {}).get("needle_id")
        rid = c.get("needle_id_rule") or (((c.get("findings_table") or {}).get("needle_id")) if isinstance(c.get("findings_table"), dict) else None)
        nid = rid or lid
        f = self.finding(t, nid) if nid else None
        status = c.get("needle_status") or (self.league_by.get(t) or {}).get("needle_status") or ("strict" if f else "none")
        if f is None or nc_status(f) == "failed" or not f.get("evidence") or f.get("explained_by_footnote"):
            pool = [x for x in self.usable(t) if not x.get("explained_by_footnote")]
            f = pool[0] if pool else None
            status = "none" if nid is None else status
            return f, (status or "none").replace(" ", "_")
        if rid and rid != lid:
            return f, None
        return f, (status or "none").replace(" ", "_")

    def table_rows(self, t):
        """findings_table rows by finding id, plus the table's unresolved marker list."""
        ft = self.companies[t].get("findings_table") or {}
        rows = ft.get("rows") if isinstance(ft, dict) else ft
        by = {r.get("finding_id") or r.get("id"): r for r in rows or [] if isinstance(r, dict)}
        unres = set(int(x) for x in (ft.get("marker_unresolved") or [])) if isinstance(ft, dict) else set()
        return by, unres

    def products(self, t):
        lab = self.companies[t].get("labels") or {}
        v2, comp = lab.get("v2") or {}, {r["product"]: r for r in lab.get("comparison") or []}
        return [(slug, v2.get(slug), comp.get(slug)) for slug in dict.fromkeys(list(v2) + list(comp))]

    def top_product(self, t):
        prods = self.products(t)
        if not prods:
            return None
        tied = [p for p in prods if (p[1] or {}).get("findings")]
        return (tied or prods)[0][0]

    def first_product(self, t):
        """The first case product (meta.case_sets order), else the product with a tied finding."""
        slugs = [p[0] for p in self.products(t)]
        for slug in ((self.meta.get("case_sets") or {}).get(t) or {}):
            if slug in slugs:
                return slug
        return self.top_product(t)

    def flow(self, t):
        prod = self.first_product(t)
        return [f"needle:{t}", f"why_company:{t}", f"findings:{t}", f"product:{t}:{prod}" if prod else None,
                f"priced_in:{t}", f"ceo_memo:{t}", f"prove_wrong:{t}"]


# ---------------------------------------------------------------- finding renderers
def lead_cites(f, C, t, n=2):
    """Cite numbers for a finding's first n evidence items (the exporter's cites_of convention)."""
    ns = [C.add(ev_cite(e, f["id"], t, i)) for i, e in list(enumerate(f.get("evidence") or []))[:n]]
    if not ns:
        ns = [C.add(ev_cite(e, f["id"], t, i)) for i, e in list(enumerate(f.get("data_citations") or []))[:1]]
    return ns


def sentence(f, C, t, n=2, row=None, unresolved=()):
    """(finding sentence, trailing cite numbers). With a sentence_marked the markers are inline, renumbered to this
    memo, and the trailing list is empty; otherwise the plain sentence plus its first n evidence cites. Dosing
    findings print every regimen in their label quotes."""
    marked = marked_sentence(f, C, t, row, unresolved)
    text, ns = (marked, []) if marked else (plain_sentence((f.get("finding") or "").strip().rstrip(".")), lead_cites(f, C, t, n))
    if "dosing" in (f.get("signal_kind") or ""):
        labels = []
        for e in f.get("evidence") or []:
            regs = regimens([verbatim_quote(e)])
            if regs:
                labels.append(f"{str(e.get('doc_title') or '').replace(' label', '')}: {' or '.join(regs)}")
        if labels:
            text = re.sub(r"\s*\(\d+(?:\[assumption\])?/yr\)", "", text)
            text += f" (label regimens: {'; '.join(labels)})"
    return text, ns


def impact_cites(f, C, t, n=3):
    data = [e for e in (f.get("data_citations") or []) if e.get("cite_id")][:n]
    ns = [C.add(ev_cite(e, f["id"], t, 100 + i)) for i, e in enumerate(data)]
    if not ns:
        ns = lead_cites(f, C, t, 1)
    return ns


def impact_math(f, C, t, label, cite, row=None, unresolved=()):
    """Math block for a finding's impact: plain formula as text, the engine's formula_marked (or the findings_table
    row's impact_marked, resolved through the row's marker_map), renumbered, as text_marked."""
    if isinstance(row, dict) and isinstance(row.get("impact_marked"), str) and row["impact_marked"].strip():
        marked = remark(row["impact_marked"], f, C, t, mm=row.get("marker_map") or {}, lic=row.get("marker_licensed") or [],
                        unresolved=unresolved)
    else:
        fm = f.get("formula_marked") or (f.get("impact") or {}).get("formula_marked")
        marked = remark(fm, f, C, t) if isinstance(fm, str) and fm.strip() else None
    return math_block(label, plain_formula(f), cite, marked)


def short_nq(f):
    r = f.get("not_quantified") or ""
    imp = f.get("impact") or {}
    m = re.match(r"mapped to the (\w+) channel", r)
    if m:
        return f"corroborates the {m.group(1).upper()} row, which carries the dollars"
    if "flag not fired" in r:
        return "not quantified: below the backtest trigger"
    if "drift topics" in r or "mdna" in (f.get("signal_kind") or "") or "risk_" in (f.get("signal_kind") or ""):
        return "not quantified: wording change with no dollar channel"
    if "calls topics" in r:
        return "not quantified: call signal with no dollar channel"
    if r:
        return "not quantified: no dollar channel for this ratio"
    form = imp.get("formula") or ""
    if "favorable" in form:
        return "favourable vs peers: no adverse scenario"
    if "already in reported numbers" in form:
        return "already in reported numbers: no further EPS effect"
    return "not quantified"


GATED_IMPACT_KEYS = ("text_gated", "gated_text", "text")


def gated_impact_text(f):
    """The engine's gated impact text when it exists (impact.text_gated / impact_gated), else the formula."""
    imp = f.get("impact") or {}
    for k in GATED_IMPACT_KEYS:
        if isinstance(imp.get(k), str) and imp[k].strip():
            return strip_marks(imp[k]).strip()
    if isinstance(f.get("impact_gated"), str) and f["impact_gated"].strip():
        return strip_marks(f["impact_gated"]).strip()
    return strip_marks(imp.get("formula") or "").strip()


def plain_formula(f):
    """The impact formula without markers (impact.formula, else the gated text stripped of markers)."""
    imp = f.get("impact") or {}
    if isinstance(imp.get("formula"), str) and imp["formula"].strip():
        return strip_marks(imp["formula"]).strip()
    return gated_impact_text(f)



def _f(x):
    return float(str(x).replace(",", ""))


def _pct(x):
    """0.1501 -> '15%', 0.0065 -> '0.65%', 0.4 -> '40%' (the check accepts a percent of a gated decimal)."""
    v = _f(x) * 100
    if v >= 1:
        return f"{v:.0f}%" if abs(v - round(v)) < 0.1 else f"{v:.1f}%"
    return f"{v:g}%"


def _m(x, cur="USD"):
    v = _f(x)
    sign = "$" if cur in ("USD", None, "") else f"{cur} "
    return f"{sign}{v:,.0f}M" if abs(v - round(v)) < 0.05 else f"{sign}{v:,.1f}M"


def _tuple(x):
    return [t.strip() for t in x.split(",")]


def plain_impact(f):
    """(plain-English impact text, raw formula for the math block). Only numbers that appear in the formula."""
    imp = f.get("impact") or {}
    text = gated_impact_text(f)
    cur = imp.get("currency") or "USD"
    fx = f" (stated in {cur}, not converted to US dollars)" if cur != "USD" else ""
    m = re.match(r"^([\d.]+) x Rev_TTM ([\d,.]+) x \(1 - t ([\d.]+)\) / D ([\d,.]+)", text)
    if m:
        a, r, t, d = m.groups()
        return (f"Operating income lower. Base case: {_pct(a)} of trailing revenue of {_m(r, cur)} at risk, "
                f"taxed at {_pct(t)}, over {_f(d):,.0f}M diluted shares{fx}"), text
    m = re.match(r"^G ([\d,.]+) x max\(0, k \(([^)]+)\) x d \(([^)]+)\) - m_avoided \(([^)]+)\)\)(?: \(class rule: ([^)]+)\))?", text)
    if m:
        g, k, d, mv, cls = m.groups()
        k, d, mv = _tuple(k), _tuple(d), _tuple(mv)
        share = "applied in full" if all(_f(x) == 1 for x in k) else f"on the {_pct(k[1])} of spend not already rebated"
        avoided = "" if all(_f(x) == 0 for x in mv) else f", less {_pct(mv[1])} of rebates no longer paid"
        return (f"Revenue lower from the Medicare negotiated price. Base case: Medicare spend of {_m(g)} at a "
                f"{_pct(d[1])} discount {share}{avoided}; bull and bear vary the shares"
                + (f" ({cls})" if cls else "")), text
    m = re.match(r"^s_MFN \(([^)]+)\) x Rev_US ([\d,.]+)", text)
    if m:
        sv, r = _tuple(m.group(1)), m.group(2)
        return (f"US net price lower. Base case assumes {_pct(sv[1])} of US revenue of {_m(r)} (bull {_pct(sv[0])}, "
                f"bear {_pct(sv[2])}); the deal terms are confidential, so the size is a scenario"), text
    if "static label difference" in text:
        return "Not quantified: the label difference is already in the revenue run-rate, and new-start share inputs are not in the data", None
    if "already in reported numbers" in text:
        return "Already in reported numbers: no further earnings effect unless the accrual changes", None
    if "favorable" in text:
        return "Favourable against peers: no adverse scenario", None
    if not text:
        return short_nq(f), None
    direction = "Operating income lower" if (imp.get("adverse") or f.get("direction") in ("adverse", "negative")) else "Direction as stated"
    return f"{direction} in the base case; the math is shown below{fx}", text


TOPIC_WORDS = {
    "receivable": "receivables", "research and development": "R&D spending", "tax rate": "the tax rate",
    "gross margin|cost of (sales|products)": "gross margin or cost of sales", "impairment": "impairments",
    "litigation|lawsuit|talc": "litigation", "China": "China",
    "IRA_negotiation": "Medicare price negotiation", "gross_to_net_price": "gross-to-net pricing",
    "biosimilar_generic": "biosimilars and generics", "inventory_channel": "inventory and the channel",
    "MFN": "the MFN deal", "tariff": "tariffs", "guidance": "guidance", "pipeline": "the pipeline",
}


def topic_words(x):
    return TOPIC_WORDS.get(x) or x.replace("_", " ").replace("|", " or ")


def plain_obscurity(note):
    """Plain-English version of the engine's obscurity note; the raw note goes to a math block."""
    if not note:
        return ""
    m = re.match(r"^not in the earnings-release headline and not asked on calls; qa_turns regex '([^']+)': (\d+) of (\d+) quarters", note)
    if m:
        return (f"Not in the earnings-release headline, and analysts raised {topic_words(m.group(1))} in "
                f"{m.group(2)} of the last {m.group(3)} earnings calls")
    m = re.match(r"^raised: headline h ([\d.]+), analyst attention a ([\d.]+); (.*)$", note)
    if m:
        h, a, rest = m.groups()
        tail = ""
        m2 = re.match(r"priced_in_scorecard \w+ (\w+): ([\d.]+)", rest)
        m3 = re.match(r"qa_turns regex '([^']+)': (\d+) of (\d+) quarters", rest)
        if m2:
            tail = f"; analysts' share of calls raising {topic_words(m2.group(1))} is {m2.group(2)}"
        elif m3:
            tail = f"; analysts raised {topic_words(m3.group(1))} in {m3.group(2)} of the last {m3.group(3)} earnings calls"
        elif "imputed" in rest:
            tail = "; imputed from the scorecard median"
        return f"partly raised: headline score {h}, attention {a} (higher = more discussed){tail}"
    return re.sub(r"\bqa_turns regex\b", "analyst questions matching", note)


def _dict_to_words(m):
    """({'xarelto': 10}) -> (Xarelto 10), as the exporter's plain() does for v1-era sentences."""
    try:
        import ast
        d = ast.literal_eval("{" + m.group(1) + "}")
        return "(" + ", ".join(f"{str(k).replace('-', ' ').title()} {v:g}" if isinstance(v, (int, float)) else f"{str(k).title()} {v}"
                               for k, v in d.items()) + ")"
    except Exception:
        return m.group(0)


def plain_sentence(text):
    """Finding sentence for display: peer z as 'sd above/below', derivation notes shortened, dict literals to
    words; numbers unchanged."""
    t = re.sub(r"\(\{([^{}]*)\}\)", _dict_to_words, text or "")
    t = t.replace(" (derived from the shortlist peer panel, not page-cited)", " (peer figures computed, not page-cited)")
    t = re.sub(r", z ([+-])([\d.]+)", lambda m: f" ({m.group(2)} standard deviations {'above' if m.group(1) == '+' else 'below'})", t)
    t = t.replace(" (derived)", "")
    return plain_terms(t)


ABBREV = [  # engine or industry shorthand -> plain words (first use per text; the rest are left as they are)
    (r"\bDSO\b", "days sales outstanding (DSO)"), (r"\bDIO\b", "days inventory on hand (DIO)"),
    (r"\bSDUD\b", "state drug utilization data (SDUD)"), (r"\bDTC\b", "direct-to-consumer (DTC)"),
    (r"\bHCAI WAC\b", "California HCAI-reported list price (WAC)"), (r"\bWAC\b", "list price (WAC)"),
    (r"\bNADAC\b", "pharmacy acquisition cost (NADAC)"), (r"\bASP\b", "Medicare average sales price (ASP)"),
    (r"\bMFP\b", "Medicare negotiated price (MFP)"),
]


def plain_terms(text):
    """Strip traceable row ids such as (R023), Orange Book exclusivity codes before a date, and .csv file names; expand
    shorthand on first use."""
    t = re.sub(r"\s*\(R\d{3}(?:, R\d{3})*\)", "", text or "")
    t = re.sub(r"\b[A-Z]{1,4}-\d{1,4}\s+(?=(?:19|20)\d{2}-\d{2}-\d{2})", "", t)
    t = re.sub(r"\b[\w/]+\.csv\b", "our verified product-revenue table", t)
    t = re.sub(r"\s*\(cited input \w+\)", " (cited input)", t)
    t = t.replace("(third_party)", "(third-party transcript)").replace("labels_table", "label table").replace("ai_caught", "AI-caught")
    for pat, full in ABBREV:
        if re.search(pat, t) and full not in t:
            t = re.sub(pat, full, t, count=1)
    return t


def plain_peer(clause):
    m = re.match(r"peer median (.+?), z ([+-])([\d.]+)", clause or "")
    if m:
        return f"{m.group(3)} standard deviations {'above' if m.group(2) == '+' else 'below'} the peer median of {m.group(1)}"
    return clause


MONEY = r"\$[\d.,]+\s?(?:bn|B|M|K|m|k)?\b"


def gate_passed(nc):
    return isinstance(nc, dict) and nc.get("status") == "passed" and not nc.get("unsupported")


def money_gate(text, quotes, gate=None):
    """Dollar figures in product text stay only when their digits appear in a cited quote, or when the engine's
    per-number gate on that text passed (its dollars are then derived from cited operands: revenue and erosion);
    otherwise the clause is replaced by its direction and 'size not page-verified'."""
    if gate_passed(gate):
        return text or ""
    qtext = " ".join(q for q in quotes if q)

    derived = set(re.findall("(" + MONEY + r")\[derived: [^\]]+\]", text or ""))
    money_in_quotes = [m for m in re.findall(MONEY, text or "") if m not in derived]

    def forms(tok):
        digits = re.sub(r"[^\d.]", "", tok).rstrip(".")
        if not digits:
            return []
        out = [digits, digits.replace(".", ",")]
        try:  # comma-grouped form as filings print it ($3,400M -> 3,400)
            whole, _, frac = digits.partition(".")
            out.append(f"{int(whole):,}" + (f".{frac}" if frac else ""))
        except ValueError:
            pass
        return out

    def ok(tok):
        if any(x in qtext for x in forms(tok)):
            return True
        # a figure the engine marks [derived: ...] prints when the operands it is derived from (the other money
        # figures in the sentence: revenue, erosion) are themselves in the cited quotes
        return tok in derived and bool(money_in_quotes) and all(any(x in qtext for x in forms(m)) for m in money_in_quotes)
    t = text or ""
    MM = "(" + MONEY + r")(?:\[derived: [^\]]+\])?"  # a money figure with its optional derived marker
    t = re.sub(r"\s*about " + MM + r" base \(" + MM + r" bull to " + MM + r" bear\) on ([^$]+?)'s " + MM + r" of annual revenue",
               lambda m: m.group(0) if all(ok(m.group(i)) for i in (1, 2, 3, 5)) else
               f" an adverse revenue effect for {m.group(4)} whose size is not page-verified (the revenue and erosion inputs are not cited)", t)
    t = re.sub(r",? worth about " + MM + r" a year in the base case",
               lambda m: m.group(0) if ok(m.group(1)) else ", an adverse revenue effect whose size is not page-verified", t)
    t = re.sub(r"the range is " + MM + r" base \(" + MM + r" bull to " + MM + r" bear\)",
               lambda m: m.group(0) if all(ok(m.group(i)) for i in (1, 2, 3)) else "the size is not page-verified", t)
    t = re.sub(r"(?:about |around )?" + MM + r"(?: of annual revenue| a year| per year)?",
               lambda m: m.group(0) if ok(m.group(1)) else "an amount not page-verified", t)
    return t


REGIMEN = re.compile(r"(?:once |twice )?(?:every|each) (?:\d+|other) (?:weeks?|months?|days?|hours?)|once (?:monthly|weekly|daily)|"
                     r"twice (?:daily|a day)|(?:once )?a day\b|monthly|weekly|daily", re.I)


def regimens(quotes):
    """Every dosing interval named in the label quotes, in order, deduplicated ('every 2 weeks or once monthly')."""
    out = []
    for q in quotes:
        for m in REGIMEN.finditer(q or ""):
            x = m.group(0).lower().replace("each", "every")
            if x not in out:
                out.append(x)
    return out


def dosing_text(value, quotes):
    regs = regimens(quotes)
    if not regs:
        return value
    route = (value or "").split(",")[0].strip()
    route = route if route and route.lower() not in ("", "n/a") and not REGIMEN.search(route) else "Dosing"
    return f"{route}, {' or '.join(regs)}"


def priced_in_line(gl):
    """(sentence, reasons) for a product's priced-in call; 'not testable' when the engine says it could not test."""
    reasons = gl.get("reasons") or []
    untestable = next((r for r in reasons if "cannot be tested" in r or "not tested" in r.split(":")[0]), None)
    if untestable or not gl.get("sentence") or gl["sentence"].startswith("The data do not support"):
        why = (untestable or "no quantified channel").split(";")[0].split(":")[-1].strip()
        return f"Priced-in call: not testable with the data we hold ({why})", reasons
    call = "the market has already priced this in" if gl.get("priced_in") else "the market has not clearly priced this in"
    return f"Our call: {call}, on the analyst-attention, starter-thread and consensus tests", reasons


def math_block(label, text, cite, text_marked=None):
    b = {"type": "math", "label": label, "text": text, "cite": cite}
    if text_marked:
        b["text_marked"] = text_marked
    return b


FOOTNOTE_KEYS = ("explained_by_footnote_note", "footnote_note", "explanation_note", "explanation", "footnote")


def footnote_note(f):
    """The note on a row the engine marks explained_by_footnote (a receivables rise that a filing footnote accounts
    for), else None."""
    if not f.get("explained_by_footnote"):
        return None
    for k in FOOTNOTE_KEYS:
        v = f.get(k)
        if isinstance(v, dict):
            v = v.get("note") or v.get("text")
        if isinstance(v, str) and v.strip():
            m = re.search(r"explained by footnote \((.+?)(?:, [A-Z]+:[\w.-]+\.md)?\)", v)
            return (m.group(1) if m else v.split(";")[0].replace("footnote read: ", "")).strip().rstrip(".")
    return "a filing footnote accounts for the movement"


def footnote_cite(f, C, t):
    """Cite for the footnote note: the finding's evidence row the engine names, else a row cite to the note."""
    index = finding_cite_index(f)
    for k in ("explained_by_footnote_cite_id", "footnote_cite_id", "footnote_cite"):
        cid = f.get(k)
        if isinstance(cid, dict):
            cid = cid.get("cite_id")
        if cid and index.get(cid):
            e, i = index[cid]
            return C.add(ev_cite(e, f.get("id"), t, i))
    key = next((k for k in FOOTNOTE_KEYS if isinstance(f.get(k), str) and f[k].strip()), "explained_by_footnote")
    return C.add(row_cite(f"row:footnote:{t}:{f['id']}", f"companies/{t}.json:findings[id={f['id']}].{key}",
                          "engine footnote read (agent.needle.quant.receivables)", f.get(key) if isinstance(f.get(key), str) else footnote_note(f),
                          "engine note", ticker=t, finding_id=f.get("id")))


def impact_cell(f, C, t):
    """(plain impact text, formula or None, cites). Only the engine's gated math is used; never impact.dollars."""
    imp = f.get("impact") or {}
    if f.get("explained_by_footnote"):
        return f"Explained by footnote: {plain_terms(footnote_note(f))}", None, [footnote_cite(f, C, t)]
    if imp.get("suspect"):
        return "Withheld: impact figure flagged suspect (above trailing operating income)", None, []
    text = gated_impact_text(f)
    if f.get("not_quantified") or not text or not (imp.get("quantified") or imp.get("dollars") is not None):
        if text and not imp.get("quantified") and not f.get("not_quantified") and not re.search(r"\d", text):
            return plain_impact(f)[0], None, []
        return short_nq(f)[0].upper() + short_nq(f)[1:], None, []
    plain, formula = plain_impact(f)
    ns = impact_cites(f, C, t) if formula else []
    return plain, formula, ns


def peer_cell(f, C, t, row=None, unresolved=()):
    """Peer comparison as the engine wrote it: the findings_table row's peer_text (gated, markers resolved through
    the row's marker_map) when present, else the peer clause of the finding sentence, else the peer note."""
    p = f.get("peer") or {}
    pt = row.get("peer_text") if isinstance(row, dict) else None
    if isinstance(pt, str) and pt.strip():
        txt = remark(pt.strip().rstrip("."), f, C, t, mm=row.get("marker_map"), lic=row.get("marker_licensed"), unresolved=unresolved)
        return plain_peer(plain_terms(txt)) if not MARK.search(txt) else plain_terms(txt), []
    m = re.search(r"peer median[^;()]*", f.get("finding") or "")
    if m:
        return plain_peer(m.group(0).strip().rstrip(",")), []
    if p.get("named_peer_row"):
        return shorten(p["named_peer_row"], 120), []
    if p.get("note"):
        note = p["note"].split(";")[0]
        if note.lower().startswith("no peer"):
            return "no peer comparison for this signal type", []
        return shorten(plain_terms(note), 110), []
    return "no peer comparison for this signal type", []


def source_cell(f, C, t):
    labels = []
    for i, e in enumerate((f.get("evidence") or [])[:2]):
        n = C.add(ev_cite(e, f["id"], t, i))
        lab = doc_label(e)
        page = e.get("printed") or e.get("page")
        loc = f", p. {page}" if page not in (None, "", "None", "?") and not str(page).startswith("row") else (f", {e.get('location')}" if e.get("location") and "section" in str(e.get("location")) else "")
        labels.append(f"{lab}{loc} [{n}]")
    return "; ".join(labels)


def findings_table(fs, C, t, ctx=None):
    rows, maths = [], []
    by, unres = ctx.table_rows(t) if ctx else ({}, set())
    for i, f in enumerate(fs, 1):
        row = by.get(f.get("id"))
        s, ns = sentence(f, C, t, row=row, unresolved=unres)
        imp, formula, ins = impact_cell(f, C, t)
        peer, pns = peer_cell(f, C, t, row=row, unresolved=unres)
        rows.append([C.after(s, *ns), C.after(imp, *ins), C.after(peer, *pns),
                     f.get("confidence") or "n/a", source_cell(f, C, t)])
        if formula and ins and not f.get("explained_by_footnote"):
            lead = match_rule(f.get("signal_kind"), LEADS) or "finding"
            maths.append(impact_math(f, C, t, f"Impact math, row {i} ({lc(lead)})", ins[0], row, unres))
    return {"type": "table", "columns": ["Finding", "Impact", "Peer", "Confidence", "Source"], "rows": rows}, maths


def anchor_note(fs):
    """One sentence per memo on the 3% anchor when any row's impact uses it."""
    if any(re.match(r"^0\.03 x Rev_TTM", plain_formula(f)) for f in fs):
        return "3% of trailing revenue is the engine's anchor assumption for ratio signals, not a measured loss[assumption]; "
    return ""


def aggregate_nc(fs):
    ncs = [f.get("numeric_check") for f in fs if isinstance(f.get("numeric_check"), dict)]
    if not ncs:
        return {"status": "unchecked"}
    out = {"status": "passed" if all(n.get("status") == "passed" for n in ncs) else "unchecked"}
    for k in ("checked", "total", "verified", "derived", "assumed"):
        out[k] = sum(n.get(k) or 0 for n in ncs)
    out["rows"] = len(ncs)
    return out


def obscurity_cite(f, C, t):
    note = ((f.get("vector") or {}).get("obscurity_note")) or ""
    if not note:
        return "", []
    n = C.add(row_cite(f"row:obscurity:{t}:{f['id']}", f"companies/{t}.json:findings[id={f['id']}].vector",
                       "analyst-attention test: ten quarters of earnings-call Q&A, the earnings-release headline and "
                       "the case starter thread (agent.needle.quant.obscurity)", note, "computed", ticker=t,
                       finding_id=f["id"]))
    return note, [n]


def league_cite(t, ctx, C):
    r = ctx.league_by.get(t) or {}
    q = ", ".join(f"{k} {r.get(k)}" for k in ("rank", "needle_status", "v2_rank", "old_rank", "n_verified",
                                              "n_rejected", "high_confidence") if r.get(k) is not None)
    if r.get("score") is not None:
        q += f", L {r['score']:.4f} (raw {r['score']})"
    return C.add(row_cite(f"row:league:{t}", f"league.json:[ticker={t}]",
                          f"{ctx.meta.get('league_file') or 'league.json'} (league row {t})", q,
                          "computed by agent.needle.quant.league, no model call", ticker=t))


def meta_cite(path, ctx, C, title=None, quote=None):
    obj, err = resolve_ref(f"meta.json:{path}", ctx)
    scalar = not isinstance(obj, (dict, list))
    val = obj if scalar else (f"{len(obj)} entries" if quote is None else quote)
    return C.add(row_cite(f"row:meta:{path}", f"meta.json:{path}", title or f"ui/public/data/meta.json {path}",
                          quote or f"{path} = {val}", "counted by agent/ui_export.py at export", value=val if scalar else None))


def proof_cite(path, ctx, C, title, quote=None, url=None, page=None):
    obj, err = resolve_ref(f"proof.json:{path}", ctx)
    q = quote if quote is not None else (obj if not isinstance(obj, (dict, list)) else json.dumps(obj, ensure_ascii=False)[:300])
    return C.add(row_cite(f"row:proof:{path}", f"proof.json:{path}", title, str(q), "from out/ files at export",
                          url=url, page=page))


# ---------------------------------------------------------------- aliases and prompts
VARIANT_PLAIN = {  # out/league_v3_robustness.json variant keys -> plain words
    "base": "the base rules",
    "raw_sum": "no concentration discount (rank by the raw top-five sum)",
    "mfn_universal": "the MFN rows at the older universal rate",
    "amgn_rec_pi_min": "the Amgen receivables row scored at the minimum probability",
    "amgn_rec_not_fired": "the Amgen receivables row treated as below its trigger",
    "H6": "a six-month attention half-life",
    "ira_spec": "the Medicare rows on the draft formula",
    "c_anchor_half": "a half-weight consensus test on anchor rows",
}


ALIAS = {
    "needle": ["{t} needle", "{n} needle", "sharpest needle {n}", "what is {n}'s sharpest needle",
               "{n} sharpest needle", "what did you find at {n}", "least discussed finding {n}", "{t} sharpest needle"],
    "findings": ["{n} findings", "{t} findings", "top findings {n}", "five findings {n}", "{n} findings table",
                 "what are the findings for {n}", "show me {n}'s findings", "{t} top 5"],
    "product": ["{p} vs rivals", "{p} fine print", "compare {p}", "{p} comparison", "{p} label comparison",
                "{t} {p}", "{p} vs {r}", "{p} exclusivity and pricing", "what limits {p}", "{p} rivals"],
    "prove_wrong": ["what would prove us wrong on {n}", "prove us wrong {t}", "{n} kill signals", "{t} kill signals",
                    "how would we know we are wrong about {n}", "{n} early warning signals",
                    "what would prove you wrong {n}", "{t} prove wrong"],
    "peers": ["{n} vs peers", "{t} peers", "{n} peer comparison", "how does {n} compare to peers",
              "{n} three forces", "{t} ira mfn tariff", "{n} vs the other nine", "{t} peer table"],
    "priced_in": ["is {n} priced in", "{t} priced in", "has the market priced in {n}", "{n} priced in",
                  "{n} analyst attention", "what do analysts ask {n}", "{t} consensus vs guidance",
                  "is the {n} needle priced in"],
    "ceo_memo": ["write the ceo memo for {n}", "{t} memo", "{n} memo", "ceo memo {n}", "what should {n}'s ceo do",
                 "{t} ceo memo", "{n} recommendation", "decide {t}", "what should {n} do", "{n} strategic move"],
    "league": ["league", "league table", "internal triage", "how did you choose which company to look at first",
               "triage order", "reading order", "which company did you read first", "internal ranking"],
    "needles": ["which company has the sharpest needle", "which company has the sharpest needle and why",
                "which company wins", "best needle across companies", "rank the needles", "who wins", "which company",
                "sharpest needle across companies", "needles by company", "all needles", "every company's needle",
                "compare the needles"],
    "products": ["which product has the weakest fine print", "which product has the weakest fine print vs rivals",
                 "weakest fine print", "products vs rivals", "fine print across products", "all products",
                 "product table", "which product is weakest", "compare all products", "growth limiters"],
    "decides": ["which companies have a valued ceo move", "valued ceo moves", "decide outputs", "which companies have a decide",
                "ceo moves across companies", "all ceo moves", "valued moves", "which companies have a valued move",
                "decide summary", "compare the ceo moves"],
    "why_company": ["why {n}", "why did you pick {n}", "why {t} over the others", "why {n} over the other nine",
                    "{n} over the other nine", "why choose {n}", "why {t}", "{n} company choice",
                    "why does {n} beat the other nine", "why {t} over the other nine"],
    "limits": ["what are the honest limits of this analysis", "honest limits", "limits", "limitations",
               "what are the limits", "what do you not know", "what can't you claim", "caveats", "what is missing",
               "weaknesses of the analysis", "what data do you lack"],
    "ai_wrong": ["where was the ai wrong", "ai wrong", "where the ai was confidently wrong", "ai mistakes",
                 "what did the ai get wrong", "how did you catch ai errors", "confidently wrong", "hallucinations",
                 "verifier catches"],
    "moat": ["what did you scrape", "data moat", "what data did you collect", "beyond the case packet", "sources",
             "how much data", "corpus", "what did you build this weekend", "coverage"],
    "how_it_works": ["how does it work", "how it works", "how does needle work", "explain the method", "methodology",
                     "how do you verify", "what is the score", "how are findings scored", "explain the pipeline"],
}


def aliases(kind, ctx, t=None, product=None, rival=None):
    names = ctx.nicks(t) if t else [ctx.name(ctx.default)] if ctx.default else [""]
    out = []
    for tpl in ALIAS[kind]:
        if "{n}" in tpl:
            for nm in names:
                out.append(tpl.format(n=nm, t=(t or ctx.default or "").lower(), p=product or "", r=rival or ""))
        else:
            out.append(tpl.format(n=names[0], t=(t or ctx.default or "").lower(), p=product or "", r=rival or ""))
    seen, uniq = set(), []
    for a in out:
        k = norm_alias(a)
        if k and k not in seen:
            seen.add(k)
            uniq.append(a.lower())
    return uniq[:14]


def ask_next(kind, ctx, t):
    d = ctx.default
    prod = ctx.top_product(t) if t else None
    pid = f"product:{t}:{prod}" if prod else None
    dec = next((x for x in ctx.tickers if ((ctx.companies[x].get("stance") or {}).get("decide") or {}).get("moves")
                and not ((ctx.companies[x].get("stance") or {}).get("decide") or {}).get("demo")), None)
    table = {
        "needle": [f"why_company:{t}", f"findings:{t}", f"ceo_memo:{t}"],
        "why_company": [f"needle:{t}", f"findings:{t}", f"ceo_memo:{t}"],
        "findings": [pid, f"priced_in:{t}", f"ceo_memo:{t}"],
        "product": [f"priced_in:{t}", f"ceo_memo:{t}"],
        "priced_in": [f"ceo_memo:{t}", f"peers:{t}"],
        "peers": [f"ceo_memo:{t}", f"why_company:{t}"],
        "ceo_memo": [f"prove_wrong:{t}", f"priced_in:{t}", "decides:global"],
        "prove_wrong": [f"ceo_memo:{t}", f"needle:{t}"],
        "league": ["needles:global", "how_it_works:global", "ai_wrong:global"],
        "needles": ["products:global", "decides:global", "how_it_works:global"],
        "products": ["needles:global", "decides:global", "ai_wrong:global"],
        "decides": [f"ceo_memo:{dec}" if dec else None, "needles:global", "how_it_works:global"],
        "ai_wrong": ["limits:global", "how_it_works:global", "needles:global"],
        "limits": ["ai_wrong:global", "how_it_works:global", "needles:global"],
        "moat": ["how_it_works:global", "ai_wrong:global", "limits:global"],
        "how_it_works": ["ai_wrong:global", "limits:global", "needles:global"],
    }
    return [x for x in table[kind] if x][:3]


def record(kind, ctx, t, prompt, summary, blocks, C, generated_by, numeric_check=None, product=None, rival=None,
           memo_header=None):
    mid = f"{kind}:{t}" if t and not product else (f"{kind}:{t}:{product}" if product else f"{kind}:global")
    rec = {"id": mid, "format": "memo" if kind in MEMO_KINDS else "chat", "prompt": prompt,
           "aliases": aliases(kind, ctx, t, product, rival), "ticker": t, "kind": kind, "generated_by": generated_by,
           "summary": summary, "blocks": blocks, "cites": C.items,
           "numeric_check": numeric_check or {"status": "unchecked"}, "ask_next": ask_next(kind, ctx, t)}
    d = (((ctx.companies.get(t) or {}).get("stance") or {}).get("decide") or {}) if t else {}
    rec["demo"] = bool(d.get("demo"))
    rec["demo_note"] = DEMO_NOTE if d.get("demo") else None
    if kind in MEMO_KINDS:
        rec["memo_header"] = memo_header
    return rec


def as_of_date(ctx):
    return (ctx.meta.get("as_of") or dt.datetime.now(dt.timezone.utc).isoformat())[:10]


# ---------------------------------------------------------------- Part 1 chat answers
def needle_memo(ctx, t):
    c, name, C = ctx.companies[t], ctx.name(t), Cites()
    f, status = ctx.needle(t)
    if f is None:
        blocks = [{"type": "callout", "tone": "warn", "md": f"No verified finding with page evidence for {name}, so there is no needle to show."}]
        return record("needle", ctx, t, f"What is {poss(name)} Sharpest Needle?", f"No needle for {name}.", blocks, C, "data")
    lead = match_rule(f.get("signal_kind"), LEADS) or "The sharpest needle"
    by0, unres0 = ctx.table_rows(t)
    s, ns = sentence(f, C, t, row=by0.get(f.get("id")), unresolved=unres0)
    src = c.get("needle_source") or ((c.get("findings_table") or {}).get("needle_source") if isinstance(c.get("findings_table"), dict) else None)
    chosen = {"red_team": ", chosen by the red-team read, confirmed by the gate", "rule": ", chosen by the plain rule"}.get(src, "")
    p = f"**{lead}.** {poss(name)} Sharpest Needle (biggest cited impact, least asked about{chosen}): {C.after(s, *ns)}."
    reason = c.get("needle_reason")
    if isinstance(reason, str) and ("carries figures the gate does not support" in reason or reason.startswith("plain rule")):
        reason = None  # nothing to add: the rule is already stated, or the reviewer's reason is not printable
    if isinstance(reason, str):
        nums = re.findall(r"\d[\d,.]*\d|\d", reason)
        if nums and all(x in strip_marks(s) for x in nums):
            reason = None  # the needle sentence already carries every figure in the reason
    if isinstance(reason, str) and reason.strip():
        rn = C.add(row_cite(f"row:needle_reason:{t}", f"companies/{t}.json:needle_reason", "needle selection record (red team vs rule)",
                            reason, "engine record", ticker=t))
        why = re.sub(r"^red-team read: ", "", reason.strip().rstrip("."))
        why = re.sub(r"Parker's best needle for [A-Z]+ \(([A-Z]+)-nugget-(\d+), docs/[\w./-]+\); his one-line reason carries figures the gate does not support, so it is not printed",
                     r"the red team's pick (nugget \2); the reviewer's own reason carries figures the gate does not support, so it is not printed", why)
        p += f" Why this one: {plain_terms(why)} [{rn}]."
    att, ons = attention_words(f, ctx, t, C)
    p += f" {att} {C.mark(*ons)}." if ons else f" {att}."
    note = ((f.get("vector") or {}).get("obscurity_note")) or ""
    imp = f.get("impact") or {}
    itxt, formula, ins = impact_cell(f, C, t)
    p += f" Impact: {itxt} {C.mark(*ins)}." if ins else f" Impact: {itxt}."
    blocks = [{"type": "p", "md": p}]
    if status in STATUS_TEXT:
        blocks.append({"type": "callout", "tone": "muted", "md": STATUS_TEXT[status]})
    rule = c.get("needle_rule") or ((c.get("findings_table") or {}).get("needle_rule") if isinstance(c.get("findings_table"), dict) else None)
    if rule:
        rn = C.add(row_cite(f"row:needle_rule:{t}", f"companies/{t}.json:needle_rule" if c.get("needle_rule") else f"companies/{t}.json:findings_table.needle_rule",
                            "needle rule as stated by the engine (out/<T>/findings_table.json)", rule, "engine rule", ticker=t))
        blocks.append(math_block("Needle rule, as the engine states it", rule, rn))
    by, unres = ctx.table_rows(t)
    if formula and ins:
        blocks.append(impact_math(f, C, t, "Impact math", ins[0], by.get(f.get("id")), unres))
    if note:
        blocks.append(math_block("Analyst-attention test, as computed", note, ons[0]))
    kpi = [{"label": "Confidence", "value": f.get("confidence") or "n/a", "cite": None},
           {"label": "Direction", "value": ("adverse" if (imp.get("adverse") or f.get("direction") in ("adverse", "negative")) else (f.get("direction") or "n/a")), "cite": None},
           {"label": "Signal type", "value": (f.get("signal_family") or f.get("signal_kind") or "n/a").replace("_", " "), "cite": None}]
    blocks.append({"type": "kpi", "items": kpi})
    nc = f.get("numeric_check") if isinstance(f.get("numeric_check"), dict) else None
    if nc and nc.get("status") == "passed" and nc.get("total"):
        n = C.add(row_cite(f"row:nc:{t}:{f['id']}", f"companies/{t}.json:findings[id={f['id']}].numeric_check",
                           "per-number citation gate (agent.needle.cite.gate_document)", json.dumps(nc), "gate record",
                           ticker=t, finding_id=f["id"]))
        blocks.append({"type": "callout", "tone": "ok",
                       "md": f"Per-number gate, finding sentence: {nc['checked']} of {nc['total']} passed "
                             f"({nc.get('verified', 0)} page-verified, {nc.get('derived', 0)} derived, {nc.get('assumed', 0)} assumptions) [{n}]."})
    elif nc and nc.get("status") == "failed":
        blocks.append({"type": "callout", "tone": "warn", "md": "This row failed the per-number gate and is excluded."})
    else:
        blocks.append({"type": "callout", "tone": "muted",
                       "md": "Quote located on the cited page; the per-number gate recorded no checked figures for this row."})
    summary = f"{lead}: {name}'s needle, confidence {f.get('confidence') or 'n/a'}."
    return record("needle", ctx, t, f"What is {poss(name)} Sharpest Needle?", summary, blocks, C, "template", nc)


def ranked_findings(ctx, t, n=5):
    """(findings, rank basis sentence). The company's findings_table (cited findings ranked by dollar impact) when the
    export carries one, else the engine's order with the needle first."""
    c = ctx.companies[t]
    needle, _ = ctx.needle(t)
    ft = c.get("findings_table") or {}
    rows = ft.get("rows") if isinstance(ft, dict) else ft
    if rows:
        ids = [r.get("finding_id") or r.get("id") for r in rows if isinstance(r, dict)]
        pool = {f["id"]: f for f in ctx.usable(t)}
        fs = [pool[i] for i in ids if i in pool]
        basis = (ft.get("rank_basis") if isinstance(ft, dict) else None) or "dollar impact"
        if needle and needle in fs:
            fs.remove(needle)
            fs.insert(0, needle)
        if fs:
            return fs[:n], f"ranked by {basis} (the engine's findings table), with the Sharpest Needle first"
    fs = ctx.usable(t)
    if needle and needle in fs:
        fs.remove(needle)
        fs.insert(0, needle)
    return fs[:n], "in the engine's order, with the Sharpest Needle first"


def label_cell_uncited(c, finding):
    """True when a boxed-warning finding names a product whose product-table safety cell is uncited."""
    if "boxed" not in (finding.get("signal_kind") or ""):
        return False
    m = re.match(r"^(\w[\w-]*)", finding.get("finding") or "")
    if not m:
        return False
    for v2 in ((c.get("labels") or {}).get("v2") or {}).values():
        cell = (((v2 or {}).get("rows") or {}).get("safety") or {}).get(m.group(1))
        if isinstance(cell, dict) and cell.get("uncited"):
            return True
    return False


def findings_memo(ctx, t):
    name, C = ctx.name(t), Cites()
    needle, _ = ctx.needle(t)
    fs, basis = ranked_findings(ctx, t)
    lead = (match_rule(needle.get("signal_kind"), LEADS) if needle else None) or "the first row"
    p = (f"Here are {poss(name)} five verified findings, {basis}. Each row carries its source page, its impact "
         f"math, its peer comparison and our confidence. The Sharpest Needle is {lc(lead)}. Rows "
         f"without a dollar channel are marked not quantified rather than guessed, and every row links to its "
         f"filing page or label section.")
    table, maths = findings_table(fs, C, t, ctx)
    blocks = [{"type": "p", "md": p}, table, *maths]
    quant = sum(1 for f in fs if impact_cell(f, Cites(), t)[2])
    blocks.append({"type": "callout", "tone": "muted",
                   "md": ("Impact cells give the direction and the inputs of the engine's gated math (shown under each "
                          "row); " + anchor_note(fs) + "peer medians are computed across the ten shortlist companies "
                          "from SEC XBRL and are not page-cited."
                          if quant else "No row in this set states an impact formula; the table shows why.")})
    return record("findings", ctx, t, f"Show {poss(name)} five cited findings",
                  f"Five cited findings for {name}, {basis}.", blocks, C, "data", aggregate_nc(fs))


def cell_marks(cell, C, t, slug, rk, ent):
    if cell.get("uncited"):
        return [], False
    cites = cell.get("citations") or []
    ns = [C.add(ev_cite(e, None, t, i)) for i, e in list(enumerate(cites))[:3]]
    if ns:
        return ns, False
    val = cell.get("value")
    if not val or not re.search(r"\d", str(val)):
        return [], False
    reason = cell.get("empty_reason") or "no page located; value is a table reference"
    n = C.add(row_cite(f"row:cell:{t}:{slug}:{rk}:{ent}", f"companies/{t}.json:labels.v2.{slug}.rows.{rk}.{ent}",
                       cell.get("source") or f"product table {slug} ({rk}, {ent})", str(val),
                       f"table reference, no page located ({reason})", ticker=t))
    return [n], True


def plain_cell(v):
    v = plain_terms(str(v))
    v = re.sub(r"\b1 contraindication\(s\)", "1 contraindication", v)
    v = re.sub(r"\b(\d+) contraindication\(s\)", r"\1 contraindications", v)
    v = re.sub(r"\b1 warnings and precautions\b", "1 warning and precaution", v)
    v = v.replace("REMS: none found in label sections one to five", "no REMS program in the label")
    v = v.replace("; titration in label", "")
    return v


def tied_gate(tied):
    """A tied product finding's dollars print when its per-number check passed and the engine marks the impact gated."""
    nc = tied.get("numeric_check")
    return nc if ((tied.get("impact") or {}).get("gated") is True and gate_passed(nc)) else None


def product_memo(ctx, t, slug, v2, comp):
    name, C = ctx.name(t), Cites()
    ents = (v2 or {}).get("entities") or []
    pname = ents[0]["name"] if ents else slug.capitalize()
    maker = ents[0].get("maker") if ents else name
    rivals = [e["name"] for e in ents[1:]] or [r.capitalize() for r in (comp or {}).get("rivals") or []]
    rival_slug = (ents[1]["slug"] if len(ents) > 1 else ((comp or {}).get("rivals") or [""])[0])
    gl = (v2 or {}).get("growth_limiter") or {}
    p = f"{pname} ({maker}) against {', '.join(rivals)} on the case's five rows: uses, safety, dosing, exclusivity, pricing."
    if gl.get("sentence"):
        gns = [C.add(ev_cite(e, None, t, i)) for i, e in list(enumerate(gl.get("citations") or []))[:3]]
        if not gns and re.search(r"\d", gl["sentence"]):
            gns = [C.add(row_cite(f"row:gl:{t}:{slug}", f"companies/{t}.json:labels.v2.{slug}.growth_limiter",
                                  "product growth limiter (agent.needle.quant.product)", gl["sentence"], "computed", ticker=t))]
        gq = [cite_text(e) for e in gl.get("citations") or []]
        p += " " + C.after(money_gate(plain_terms(gl["sentence"].rstrip(".")), gq, gl.get("numeric_check")), *gns) + "."
    tied = ((v2 or {}).get("findings") or [None])[0]
    if isinstance(tied, dict) and tied.get("finding"):
        tns = [C.add(ev_cite(e, tied.get("id"), t, i)) for i, e in list(enumerate(tied.get("evidence") or []))[:2]]
        tq = [cite_text(e) for e in tied.get("evidence") or []]
        p += " Tied finding: " + C.after(money_gate(plain_terms(tied["finding"].rstrip(".")), tq, tied_gate(tied)), *tns) + "."
    elif (v2 or {}).get("notes"):
        notes = [re.sub(r"^\w+ produced no finding: ", "", n) for n in v2["notes"]]
        notes = [n for n in notes if not var_tokens(n)] or ["no label-to-numbers channel had its inputs"]
        note = shorten(plain_terms(notes[0].rstrip(".")), 160)
        nn = C.add(row_cite(f"row:notes:{t}:{slug}", f"companies/{t}.json:labels.v2.{slug}.notes",
                            "product module notes (agent.needle.quant.product)", " | ".join(v2["notes"]), "engine note", ticker=t))
        p += f" No label row ties to a financial finding yet: {note} [{nn}]."
    if gl:
        call, reasons = priced_in_line(gl)
        if reasons:
            rn = C.add(row_cite(f"row:gl_reasons:{t}:{slug}", f"companies/{t}.json:labels.v2.{slug}.growth_limiter.reasons",
                                "priced-in test inputs: analyst-attention scorecard, case starter thread, I/B/E/S consensus "
                                "(data/moat/verified/market)", " | ".join(reasons), "computed", ticker=t))
            p += f" {call} [{rn}]."
        else:
            p += f" {call}."
    blocks = [{"type": "p", "md": p}]
    table_ref = uncited = False
    if v2 and v2.get("rows"):
        cols = ["Row", pname] + rivals
        rows = []
        for rk in ROW_ORDER:
            row = (v2["rows"] or {}).get(rk) or {}
            out = [(v2.get("row_titles") or {}).get(rk, rk)]
            for ent in [pname] + rivals:
                cell = row.get(ent) or {}
                ns, ref = cell_marks(cell, C, t, slug, rk, ent)
                table_ref = table_ref or ref
                if cell.get("uncited"):
                    val, uncited = "needs citation: no page located for this value", True
                else:
                    val = cell.get("value") or ("no data: " + (cell.get("empty_reason") or "not located"))
                    if rk == "dosing" and cell.get("citations"):
                        val = dosing_text(val, [verbatim_quote(c) for c in cell["citations"] if isinstance(c, dict)])
                    val = shorten(plain_cell(val), 170)
                out.append(C.after(val, *ns))
            rows.append(out)
        blocks.append({"type": "table", "columns": cols, "rows": rows})
    elif comp:
        cols = ["Row", pname] + rivals
        rows = []
        for r in comp.get("rows") or []:
            out = [r.get("label") or r.get("field")]
            for s in [slug] + (comp.get("rivals") or []):
                v = (r.get("values") or {}).get(s) or {}
                if v.get("uncited"):
                    out.append("needs citation: no page located for this value")
                    uncited = True
                    continue
                ns = [C.add(ev_cite(v["citation"], None, t))] if isinstance(v.get("citation"), dict) and v["citation"].get("cite_id") else []
                val = v.get("value")
                if not ns and val is not None and re.search(r"\d", str(val)):
                    ns = [C.add(row_cite(f"row:cmp:{t}:{slug}:{r.get('field')}:{s}",
                                         f"companies/{t}.json:labels.comparison[product={slug}].rows[field={r.get('field')}].values.{s}",
                                         v.get("source") or "comparison table", str(val), "table reference", ticker=t))]
                    table_ref = True
                out.append(C.after(shorten(plain_cell(val) if val is not None else "n/a", 170), *ns))
            rows.append(out)
        blocks.append({"type": "table", "columns": cols, "rows": rows})
    if table_ref or uncited:
        blocks.append({"type": "callout", "tone": "muted",
                       "md": ("Table reference: our verified table, no page located for that date. " if table_ref else "")
                             + ("Needs citation: a value not tied to a page, so not printed as fact. " if uncited else "")
                             + "Other cells cite the label section or filing page."})
    nc = (v2 or {}).get("numeric_check") if isinstance((v2 or {}).get("numeric_check"), dict) else None
    summary = f"{pname} vs {', '.join(rivals)} on label, safety, dosing, exclusivity and pricing."
    return record("product", ctx, t, f"Compare {pname} with its rivals on the fine print", summary, blocks, C, "data",
                  nc, product=slug, rival=rival_slug)


def forces_cite(x, ctx, C):
    fr = ctx.companies[x].get("forces") or {}
    q = "; ".join(f"{k} {fr.get(k)}" for k in ("ira_share_of_total_revenue_pct", "mfn_date", "tariff_exempt_until",
                                               "pct_mfg_sites_outside_us", "mfg_sites_non_us", "mfg_sites_total",
                                               "us_revenue_share_pct", "us_investment_pledge_usd_bn"))
    return C.add(row_cite(f"row:forces:{x}", f"companies/{x}.json:forces",
                          f"moat table policy/force_summary.csv, rows {fr.get('traceable_row_ids') or 'n/a'} "
                          "(CMS selected-drug lists, White House MFN releases, FDA registration files, 10-K geography)",
                          q, "verified table row", ticker=x))


def peers_memo(ctx, t):
    name, C = ctx.name(t), Cites()
    needle, _ = ctx.needle(t)
    p = (f"Here is how {name} sits against the other nine on the three forces the case names: Medicare price "
         f"negotiation, the MFN agreement and the tariff exemption that comes with it.")
    if needle and re.search(r"peer median", needle.get("finding") or ""):
        ptxt, _ = peer_cell(needle, C, t)
        pns = lead_cites(needle, C, t)
        lead = match_rule(needle.get("signal_kind"), LEADS) or "the needle"
        p += f" On its needle metric ({lc(lead)}) the company sits at {ptxt} {C.mark(*pns)}."
    fr = ctx.companies[t].get("forces") or {}
    if fr:
        n = forces_cite(t, ctx, C)
        p += (f" {poss(name)} IRA-selected drugs ({fr.get('ira_drugs') or 'none listed'}) are "
              f"{fr.get('ira_share_of_total_revenue_pct') if fr.get('ira_share_of_total_revenue_pct') is not None else 'n/a'}% "
              f"of FY2025 revenue [{n}].")
    order = [t] + [x for x in ctx.tickers if x != t]
    rows = []
    for x in order:
        f = ctx.companies[x].get("forces") or {}
        if not f:
            continue
        n = forces_cite(x, ctx, C)
        ira = f.get("ira_share_of_total_revenue_pct")
        mfg = f.get("pct_mfg_sites_outside_us")
        rows.append([f"**{ctx.name(x)}**" if x == t else ctx.name(x),
                     f"{ira}% [{n}]" if ira is not None else f"n/a [{n}]",
                     f"{f.get('mfn_date') or 'n/a'}", f"{f.get('tariff_exempt_until') or 'n/a'}",
                     (f"{mfg}% ({f.get('mfg_sites_non_us')} of {f.get('mfg_sites_total')} sites)" if mfg is not None else "n/a"),
                     f"{f.get('us_revenue_share_pct')}%" if f.get("us_revenue_share_pct") is not None else "n/a"])
    blocks = [{"type": "p", "md": p}]
    if rows:
        blocks.append({"type": "table", "columns": ["Company", "IRA share of revenue", "MFN signed", "Tariff exempt until",
                                                    "Mfg sites outside US", "US revenue share"], "rows": rows})
        blocks.append({"type": "callout", "tone": "muted",
                       "md": "Manufacturing-site counts come from FDA registration files, which undercount biologics "
                             "plants; treat that column as a proxy. Every row names its traceable moat rows."})
    return record("peers", ctx, t, f"How does {name} compare with its peers on the three forces?",
                  f"{name} vs the other nine on IRA exposure, MFN terms, tariffs and US revenue share.", blocks, C, "data")


def priced_in_cite(t, row, C):
    topic = row.get("topic")
    page = f"{row.get('latest_example_file')} line {int(row['latest_example_line'])}" if row.get("latest_example_line") else None
    q = f"{topic}: quarters asked {row.get('quarters_asked')} of {row.get('quarters_covered')}, tier {row.get('analyst_attention_tier')}, last asked {row.get('last_quarter_asked')}"
    if row.get("latest_example_quote"):
        q += f". {row.get('latest_example_speaker')}: {row.get('latest_example_quote')}"
    return C.add(row_cite(f"row:priced_in:{t}|{topic}", f"companies/{t}.json:priced_in[topic={topic}]",
                          f"priced-in scorecard row {t} | {topic} ({row.get('source') or 'data/moat/verified/market'})",
                          q, "verified table row", ticker=t, page=page))


def priced_call(ctx, t, C):
    """(plain priced-in call, cites). By league status when the rule needle is the league needle; otherwise from the
    analyst-attention scorecard row for the needle's topic."""
    needle, status = ctx.needle(t)
    if status in PRICED_CALL:
        return PRICED_CALL[status], []
    hit = scorecard_row(ctx.companies[t], needle)
    if hit and hit.get("quarters_covered"):
        n = priced_in_cite(t, hit, C)
        asked, cov = hit.get("quarters_asked") or 0, hit.get("quarters_covered")
        call = ("not priced in: analysts never asked about the needle topic in the calls we read" if asked == 0 else
                "only partly priced in: analysts asked about the needle topic in a minority of the calls we read" if asked * 2 < cov else
                "mostly priced in: analysts asked about the needle topic in most of the calls we read")
        return f"{call} ({asked} of {cov} quarters)", [n]
    if needle:
        note = ((needle.get("vector") or {}).get("obscurity_note")) or ""
        if note:
            n = C.add(row_cite(f"row:obscurity:{t}:{needle['id']}", f"companies/{t}.json:findings[id={needle['id']}].vector",
                               "analyst-attention test: ten quarters of earnings-call Q&A, the earnings-release headline and "
                               "the case starter thread (agent.needle.quant.obscurity)", note, "computed", ticker=t, finding_id=needle["id"]))
            raised = re.search(r"analysts raised (.+?) in (\d+) of the last (\d+) earnings calls", plain_obscurity(note))
            if raised:
                k, tot = int(raised.group(2)), int(raised.group(3))
                call = ("not priced in: analysts never raised " + raised.group(1) + f" in the last {tot} earnings calls" if k == 0 else
                        f"only partly priced in: analysts raised {raised.group(1)} in {k} of the last {tot} earnings calls" if k * 2 < tot else
                        f"mostly priced in: analysts raised {raised.group(1)} in {k} of the last {tot} earnings calls")
                return call, [n]
            return f"not tested by a scorecard topic; the needle's own attention test reads: {plain_obscurity(note).rstrip('.')}", [n]
    return "not tested: no analyst-attention row matches the needle topic", []


def priced_in_memo(ctx, t):
    name, c, C = ctx.name(t), ctx.companies[t], Cites()
    needle, status = ctx.needle(t)
    p = f"Is {poss(name)} needle already priced in? "
    maths = []
    if needle:
        note, ons = obscurity_cite(needle, C, t)
        lead = match_rule(needle.get("signal_kind"), LEADS) or "the needle"
        if note:
            att, ans = attention_words(needle, ctx, t, C)
            p += f"On {lc(lead)}: {att[0].lower() + att[1:]} {C.mark(*ans)}. " if ans else f"On {lc(lead)}: {att[0].lower() + att[1:]}. "
            maths.append(math_block("Analyst-attention test, as computed", note, ons[0]))
    rows = sorted(c.get("priced_in") or [], key=lambda r: (r.get("share_of_quarters_asked") if r.get("share_of_quarters_asked") is not None else 9))
    never = [r for r in rows if (r.get("quarters_asked") or 0) == 0]
    if never:
        n = priced_in_cite(t, never[0], C)
        p += (f"Analysts have not asked about {topic_words(never[0]['topic'])} in any of the "
              f"{never[0].get('quarters_covered')} earnings calls we read [{n}]. ")
    cvg = c.get("consensus_vs_guidance") or {}
    if cvg.get("guidance_quote"):
        n = C.add(row_cite(f"row:guidance:{t}", f"companies/{t}.json:consensus_vs_guidance",
                           f"{name} earnings call ({cvg.get('guidance_file')}), {cvg.get('guidance_page')}",
                           cvg["guidance_quote"], "quote located in transcript", ticker=t,
                           page=cvg.get("guidance_page")))
        rel = cvg.get("consensus_vs_range") or "unknown"
        p += (f"Management guided: \"{cvg['guidance_quote'].strip()}\" [{n}]; Street consensus sits {rel} that range "
              f"(I/B/E/S figures are licensed, so we show the position, not the numbers). ")
    call, cns = priced_call(ctx, t, C)
    p += f"Our call: {C.after(call, *cns)}."
    blocks = [{"type": "p", "md": p.strip()}, *maths]
    if rows:
        trs = []
        for r in rows[:6]:
            n = priced_in_cite(t, r, C)
            trs.append([topic_words(r["topic"]), f"{r.get('quarters_asked')} of {r.get('quarters_covered')} [{n}]",
                        r.get("analyst_attention_tier") or "n/a", r.get("last_quarter_asked") or "never"])
        blocks.append({"type": "table", "columns": ["Topic", "Quarters asked", "Attention", "Last asked"], "rows": trs})
        blocks.append({"type": "callout", "tone": "muted",
                       "md": "Topics are sorted least-discussed first; the scorecard counts analyst Q&A turns across the "
                             "ten most recent earnings calls."})
    return record("priced_in", ctx, t, f"Is {poss(name)} needle already priced in?",
                  f"Priced-in test for {name}: analyst attention by topic, guidance versus consensus, and our call.",
                  blocks, C, "data")


# ---------------------------------------------------------------- global chat answers
def league_memo(ctx):
    """Internal triage only: the order in which we read the companies, ranks and counts, no scores."""
    C = Cites()
    p = ("Before the pitch work started we ran an internal triage to decide which company to read first. It is not "
         "a pitch output and it did not choose the company: the company pick is a human decision informed by the "
         "red team, and the Part 1 case for it is the findings themselves. The triage order, ranks only:")
    rows = []
    for r in ctx.league:
        x = r["ticker"]
        if x not in ctx.companies:
            continue
        n = league_cite(x, ctx, C)
        f, _ = ctx.needle(x)
        lead = (match_rule(f.get("signal_kind"), LEADS) if f else None) or "no needle"
        rows.append([f"{r.get('rank', '')}", ctx.name(x), lead,
                     f"{r.get('n_verified', 'n/a')} verified / {r.get('n_rejected', 'n/a')} rejected [{n}]"])
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Triage rank", "Company", "Sharpest Needle", "Findings"], "rows": rows},
              {"type": "callout", "tone": "muted",
               "md": "Caveat: this order came from an internal ranking score that is not part of the pitch; it "
                     "decided only which company we looked at first. Ask for a company's needle, findings or CEO memo "
                     "to see the evidence."}]
    return record("league", ctx, None, "Internal triage: how we chose which company to look at first",
                  "The internal reading order of the ten companies, ranks only; not a pitch output.", blocks, C, "data")

AI_PICKS = [  # (stream, table-or-key substring) in display order; first five that exist are shown
    ("peers", "rival_product_statements"), ("peers", "peer_product_revenue"), ("pipeline", "entity_name_collision"),
    ("costs", "company_cost_structure"), ("rx", "humira"), ("filings", "restatements"),
]


AI_CASE_PICKS = [1, 3, 4, 7, 11, 17, 22, 26]  # case numbers shown (backtest, gate, needle reads, transcripts, red team, challenger, verifier, data layer)


def ai_cases_memo(ctx):
    C = Cites()
    cases = [c for c in ctx.proof.get("ai_wrong_cases") or [] if isinstance(c, dict)]
    total = len(cases)
    ct = C.add(row_cite("row:proof:ai_wrong_cases", "proof.json:ai_wrong_cases",
                        "docs/ai_in_the_build.md, the logged cases where the AI was confidently wrong",
                        f"{total} cases; dates {cases[0].get('date')} to {cases[-1].get('date')}" if cases else "0 cases",
                        "counted at export"))
    picks = [c for c in cases if c.get("n") in AI_CASE_PICKS] or cases[:8]
    trs = []
    for c in picks[:8]:
        refs = c.get("evidence_refs") or ([c["evidence"]] if c.get("evidence") else [])
        n = C.add(row_cite(f"row:proof:ai_case:{c.get('n')}", f"proof.json:ai_wrong_cases[n={c.get('n')}]",
                           ("evidence: " + ", ".join(refs)) if refs else "docs/ai_in_the_build.md (no file reference logged)",
                           f"{c.get('date')}: AI claimed {c.get('ai_claimed')} | caught by {c.get('caught_by')} | fix: {c.get('fix')}",
                           "logged case", url=None))
        trs.append([f"{c.get('date')}", f"{shorten(c.get('ai_claimed') or '', 170)} [{n}]",
                    f"{shorten(c.get('caught_by') or '', 90)} [{n}]", f"{shorten(c.get('fix') or '', 190)} [{n}]"])
    kinds = Counter((c.get("caught_by") or "").split(" (")[0].split(",")[0].strip() for c in cases)
    p = (f"Yes, {total} times that we logged [{ct}]. Each case records what the model claimed, who or what caught it "
         f"and the fix; none was caught by asking the model again. Here are {len(trs)} of the {total} [{ct}], from "
         f"the first backtest to the data layer.")
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Date", "What the AI claimed", "Caught by", "Fix"], "rows": trs},
              {"type": "callout", "tone": "ok",
               "md": "Every case cites its evidence file or commit; the full log is docs/ai_in_the_build.md. Only "
                     "verified rows are citable anywhere in this app."}]
    return record("ai_wrong", ctx, None, "Where was the AI confidently wrong?",
                  f"{total} logged cases where the AI was confidently wrong, with how each was caught and fixed.",
                  blocks, C, "data")


def limits_memo(ctx):
    C = Cites()
    lims = [x for x in ctx.meta.get("honest_limits") or [] if isinstance(x, dict) and x.get("sentence")
            and not PITCH_FORBIDDEN.search(f"{x.get('sentence')} {x.get('proxy')}")
            and not var_tokens(f"{x.get('sentence')} {x.get('proxy')}")]  # limits about the internal league are not pitched
    data, method = [], []
    for x in lims:
        n = C.add(row_cite(f"row:meta:limit:{norm_alias(x.get('limit') or '')[:40]}", f"meta.json:honest_limits[limit={x.get('limit')}]",
                           f"{x.get('source') or 'docs/honest_limits.md'}: {x.get('limit')}",
                           f"{x.get('sentence')} Proxy: {x.get('proxy')}", "stated limit"))
        has_proxy = x.get("proxy") not in (None, "", "None")
        (data if has_proxy else method).append((x, n))
    blocks = [{"type": "p", "md": ("The limits we state in the pitch, grouped as data we do not have (with the proxy we use "
                                    "instead) and limits of the method itself. Each sentence is the one in docs/honest_limits.md.")}]
    if data:
        blocks.append({"type": "h", "text": "Data we do not have, and the proxy we use"})
        blocks.append({"type": "table", "columns": ["Limit", "What we do not claim", "Proxy"],
                       "rows": [[x.get("limit"), f"{x.get('sentence')} [{n}]", f"{shorten(x.get('proxy'), 200)} [{n}]"] for x, n in data]})
    if method:
        blocks.append({"type": "h", "text": "Limits of the method"})
        blocks.append({"type": "table", "columns": ["Limit", "What we do not claim"],
                       "rows": [[x.get("limit"), f"{x.get('sentence')} [{n}]"] for x, n in method]})
    return record("limits", ctx, None, "What are the honest limits of this analysis?",
                  f"{len(lims)} stated limits: data we lack and the proxy we use, and limits of the method.", blocks, C, "data")


def ai_wrong_memo(ctx):
    if ctx.proof.get("ai_wrong_cases"):
        return ai_cases_memo(ctx)
    C = Cites()
    rows = ctx.proof.get("ai_wrong") or []
    rows = [r for r in rows if r.get("what_the_source_says")]
    picks = []
    for stream, key in AI_PICKS:
        for i, r in enumerate(rows):
            if r.get("stream") == stream and key in json.dumps(r) and i not in [p[0] for p in picks]:
                picks.append((i, r))
                break
    for i, r in enumerate(rows):  # fallback: distinct high-severity streams
        if len(picks) >= 5:
            break
        if r.get("severity") == "high" and r.get("stream") not in [p[1].get("stream") for p in picks]:
            picks.append((i, r))
    picks = picks[:5]
    total = len(ctx.proof.get("ai_wrong") or [])
    n_total = proof_cite("ai_wrong", ctx, C, "data/moat/verify/ai_wrong.jsonl (every logged AI error)",
                         quote=f"{total} rows; by stream: " + ", ".join(f"{k} {v}" for k, v in Counter(r.get("stream") for r in rows).most_common()))
    streams = Counter(r.get("stream") for r in rows)
    top_stream = streams.most_common(1)[0] if streams else None
    p = (f"Yes, often. The second-pass verifier logged {total} cases where a model wrote something the source does "
         f"not say [{n_total}]")
    if top_stream:
        p += f"; {top_stream[1]} of them are in the {top_stream[0]} stream alone [{n_total}]"
    p += (". Each one was caught by re-reading the cited page or the raw government file, never by asking the model "
          "again. Here are five from different streams, with what was wrong and how we caught it.")
    trs = []
    for i, r in picks:
        said = r.get("what_the_ai_said") or r.get("what_the_ai_wrote") or ""
        n = proof_cite(f"ai_wrong[{i}]", ctx, C, r.get("example_source") or r.get("example_cite") or f"{r.get('stream')}/{r.get('table')}",
                       quote=r.get("what_the_source_says"))
        trs.append([f"{r.get('stream')} / {r.get('table')}", f"{shorten(said, 170)} [{n}]",
                    f"{shorten(r.get('what_the_source_says'), 190)} [{n}]", f"{shorten(r.get('how_caught'), 150)} [{n}]"])
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Stream / table", "What the AI said", "What the source says", "How we caught it"], "rows": trs},
              {"type": "callout", "tone": "ok",
               "md": "Only verified rows are citable anywhere in this app; dropped rows are kept for the write-up."}]
    return record("ai_wrong", ctx, None, "Where was the AI confidently wrong?",
                  f"{total} logged AI errors; five examples with how the verifier caught each.", blocks, C, "data")


def moat_memo(ctx):
    C, m = Cites(), ctx.meta
    corp, moat = m.get("corpus") or {}, m.get("moat") or {}
    bits = []
    if corp.get("docs"):
        bits.append(f"{corp['docs']} page-anchored source documents [{meta_cite('corpus.docs', ctx, C)}] "
                    f"covering {corp.get('companies')} shortlist companies, {corp.get('peers')} rival makers and "
                    f"{corp.get('drugs')} drugs [{meta_cite('corpus.companies', ctx, C)}][{meta_cite('corpus.peers', ctx, C)}][{meta_cite('corpus.drugs', ctx, C)}]")
    if corp.get("pages"):
        bits.append(f"{corp['pages']} pages indexed so every quote can be checked on its page [{meta_cite('corpus.pages', ctx, C)}]")
    if corp.get("transcripts_graded"):
        bits.append(f"{corp['transcripts_graded']} call transcripts graded A to C for quotability [{meta_cite('corpus.transcripts_graded', ctx, C)}]")
    if moat.get("tables"):
        bits.append(f"{len(moat['tables'])} derived tables, each row carrying its source row "
                    f"[{meta_cite('moat.tables', ctx, C, quote=f'moat.tables = {len(moat['tables'])} tables')}]")
    if moat.get("ai_wrong_count"):
        bits.append(f"{moat['ai_wrong_count']} AI errors logged by the second-pass verifier [{meta_cite('moat.ai_wrong_count', ctx, C)}]")
    led = m.get("ledger") or {}
    if led.get("n"):
        bits.append(f"a hash-chained ledger of {led['n']} records, {'intact' if led.get('ok') else 'broken'} at export [{meta_cite('ledger.n', ctx, C)}]")
    p = "Beyond the case packet we built our own corpus: " + "; ".join(bits) + "." if bits else "The sample build carries no corpus counts."
    p += " Every bucket below was verified by a second pass against the source page or the raw CMS and SEC files."
    blocks = [{"type": "p", "md": p}]
    rows = []
    for b in moat.get("buckets") or []:
        st = (moat.get("status") or {}).get(b["key"]) or []
        n = C.add(row_cite(f"row:meta:bucket:{b['key']}", f"meta.json:moat.buckets[key={b['key']}]",
                           "data/moat/progress.json bucket", f"{b.get('label')}: {b.get('why')} ({', '.join(st)})", "tracker row"))
        rows.append([f"{b.get('label')} [{n}]", b.get("why") or "", ", ".join(st) or "n/a"])
    if rows:
        blocks.append({"type": "table", "columns": ["Bucket", "Why we collected it", "Status"], "rows": rows})
    d = ctx.default
    if d:
        f, _ = ctx.needle(d)
        if f:
            lead = match_rule(f.get("signal_kind"), LEADS) or "the needle"
            docs = list(dict.fromkeys(doc_label(e) for e in f.get("evidence") or []))[:6]
            ns = [C.add(ev_cite(e, f["id"], d, i)) for i, e in list(enumerate(f.get("evidence") or []))[:3]]
            note, ons = obscurity_cite(f, C, d)
            why = (f"Why it mattered: {poss(ctx.name(d))} Sharpest Needle ({lc(lead)}) rests on "
                   f"{', '.join(x for x in docs if x)} {C.mark(*ns)}")
            if note:
                att, ans = attention_words(f, ctx, d, C)
                why += f", plus the call transcripts behind its attention test ({att[0].lower() + att[1:]}) {C.mark(*(ans or ons))}"
            blocks.append({"type": "p", "md": why + "."})
    return record("moat", ctx, None, "What did you scrape beyond the case packet?",
                  "The corpus and verified tables behind every citation, bucket by bucket.", blocks, C, "data")


def needle_line(ctx, t, C):
    """One line for a company's Sharpest Needle: marked sentence, impact direction or gated figure, analyst attention."""
    f, status = ctx.needle(t)
    if not f:
        return None, None
    by, unres = ctx.table_rows(t)
    s, ns = sentence(f, C, t, row=by.get(f.get("id")), unresolved=unres)
    itxt, _, ins = impact_cell(f, C, t)
    note, ons = obscurity_cite(f, C, t)
    line = f"**{ctx.name(t)}**: {C.after(s, *ns)}. Impact: {C.after(itxt, *ins)}."
    if note:
        line += f" How rarely analysts asked: {C.after(plain_obscurity(note).rstrip('.'), *ons)}."
    if status in STATUS_TEXT:
        line += f" ({STATUS_TEXT[status].split(': ', 1)[1].rstrip('.')}.)"
    return line, f


def gated_dollars(f):
    """A dollar impact the engine gated, for ordering only (never printed); None when the figure is ungated."""
    imp = f.get("impact") or {}
    if imp.get("suspect") or imp.get("dollars") is None or (imp.get("currency") or "USD") != "USD":
        return None
    if imp.get("gated") or (imp.get("quantified") and not imp.get("ungated_dropped")):
        return abs(float(imp["dollars"]))
    return None


def needles_memo(ctx):
    C = Cites()
    lines = []
    for i, t in enumerate(ctx.tickers):
        f, status = ctx.needle(t)
        if not f:
            continue
        by, unres = ctx.table_rows(t)
        s_, ns = sentence(f, C, t, row=by.get(f.get("id")), unresolved=unres)
        itxt, _, ins = impact_cell(f, C, t)
        att, ons = attention_words(f, ctx, t, C)
        att = att.replace("Analyst attention: ", "")
        if status in STATUS_TEXT:
            att += " (caveat: " + {"provisional": "provisional needle", "floor_relaxed": "best of the least-discussed group",
                                   "none": "largest impact, not promoted"}[status] + ")"
        cell = clip(s_, 20)
        row = [ctx.name(t), cell, C.after(clip(itxt.split(". ")[0], 14), *ins), C.after(att, *ons),
               (C.mark(*ns) + rest_marks(s_, cell, C)) or "inline"]
        g = gated_dollars(f)
        lines.append((0 if g is not None else 1, -(g or 0), i, row))
    lines.sort(key=lambda x: x[:3])
    gated = sum(1 for x in lines if x[0] == 0)
    order = "by gated dollar impact, then the engine's needle order" if gated else "in the engine's needle order (no needle carries a gated dollar total)"
    p = (f"Each company's Sharpest Needle by the same plain rule (biggest cited impact, least asked about), {order}. "
         f"The company pick is a human decision informed by the red team; this table is the evidence, not the pick.")
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Company", "Sharpest Needle", "Impact direction", "Analyst attention", "Cites"],
               "rows": [x[3] for x in lines]}]
    return record("needles", ctx, None, "Which company has the sharpest needle?",
                  "Every company's Sharpest Needle on one page, with its impact and how rarely analysts asked.",
                  blocks, C, "data")


def products_memo(ctx):
    C = Cites()
    items = []
    for t in ctx.tickers:
        for slug, v2, comp in ctx.products(t):
            ents = (v2 or {}).get("entities") or []
            pname = ents[0]["name"] if ents else slug.capitalize()
            rivals = [e["name"] for e in ents[1:]] or [r.capitalize() for r in (comp or {}).get("rivals") or []]
            gl = (v2 or {}).get("growth_limiter") or {}
            tied = ((v2 or {}).get("findings") or [None])[0]
            head = f"{pname} ({ctx.name(t)}) vs {', '.join(rivals) or 'no rival on file'}"
            glc, gns = "not named", []
            if gl.get("sentence"):
                gns = [C.add(ev_cite(e, None, t, i)) for i, e in list(enumerate(gl.get("citations") or []))[:2]]
                if not gns and re.search(r"\d", gl["sentence"]):
                    gns = [C.add(row_cite(f"row:gl:{t}:{slug}", f"companies/{t}.json:labels.v2.{slug}.growth_limiter",
                                          "product growth limiter (agent.needle.quant.product)", gl["sentence"], "computed", ticker=t))]
                gq = [cite_text(e) for e in gl.get("citations") or []]
                glc = money_gate(plain_terms(gl["sentence"].rstrip(".")), gq, gl.get("numeric_check"))
                glc = re.sub(r"^What limits .+?'s growth is ", "", glc)
                glc = re.sub(r", and the market has (?:already|not clearly) priced (?:this|it) in$", "", glc)
                glc = re.sub(r"^The data do not support naming what limits .+?'s growth: ", "not named: ", glc)
            if isinstance(tied, dict) and (tied.get("sentence_marked") or tied.get("finding")):
                direction = (tied.get("direction") or "adverse") + (f" ({CHANNEL_WORDS.get(tied.get('channel'), str(tied.get('channel')).replace('_', ' '))})" if tied.get("channel") else "")
                tns = [C.add(ev_cite(e, tied.get("id"), t, i)) for i, e in list(enumerate(tied.get("evidence") or []))[:2]]
                weight = 0
            else:
                direction, tns, weight = "none: no label row ties to a finding", [], 1
            call = priced_in_line(gl)[0] if gl else "not tested"
            call = re.sub(r"^Our call: the market has ", "", call).replace("Priced-in call: ", "").split(", on the")[0].replace("priced this in", "priced in")
            items.append((weight, [head, C.after(clip(glc, 20), *gns), C.after(direction, *tns), call]))
    items.sort(key=lambda x: x[0])
    p = ("One row per case product: its growth limiter from the fine-print table, the direction of the finding it ties to, "
         "and our priced-in call. Products with a tied finding come first; which is weakest is a judgment the table supports, not a score.")
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Product vs rivals", "Growth limiter", "Tied finding", "Priced-in call"],
               "rows": [x[1] for x in items]}]
    return record("products", ctx, None, "Which product has the weakest fine print vs rivals?",
                  "Every case product's growth limiter, tied finding and priced-in call on one page.", blocks, C, "data")


def decides_memo(ctx):
    C = Cites()
    items, have = [], []
    for t in ctx.tickers:
        st = ctx.companies[t].get("stance") or {}
        d = st.get("decide") or {}
        if not d.get("moves"):
            continue
        have.append(t)
        mv, least_bad = decide_pick(d)
        n = decide_cite(d, t, mv, C)
        bud, _ = budget_total(mv)
        flag = "pipeline demonstration" if d.get("demo") else "valued move"
        pm = mv.get("payback_month")
        items.append([ctx.name(t), ("least-bad option (no candidate clears the hurdle): " if least_bad else "chosen: ") + mv.get("name"),
                      f"{mny(mv.get('ev'))} [{n}]", mny(bud) if bud is not None else "not stated",
                      f"{pm}" if pm is not None else "none within the horizon",
                      C.after(str(d.get("selection_rule") or "not stated").strip().rstrip("."), n), flag])
    rest = [ctx.name(t) for t in ctx.tickers if t not in have]
    lst = ((ctx.meta.get("v2_status") or {}).get("decide_v2")) or have
    cn = C.add(row_cite("row:meta:decide_v2", "meta.json:v2_status.decide_v2" if (ctx.meta.get("v2_status") or {}).get("decide_v2") else "meta.json:companies",
                        "meta.json v2_status.decide_v2 (companies with a DECIDE output)",
                        f"{', '.join(lst)}: {len(have)} of {len(ctx.tickers)} companies", "counted at export"))
    p = (f"{len(have)} of the {len(ctx.tickers)} companies carry a DECIDE output [{cn}]: one CEO move valued against two "
         f"alternatives on the same five numbers, with kill signals.")
    if rest:
        p += f" The other {len(rest)} ({', '.join(rest)}) carry template stances with no valued move yet [{cn}]."
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Company", "Move", "Expected value", "Budget, 24 months", "Payback month", "Selection rule", "Flag"],
               "rows": items} if items else {"type": "p", "md": "No DECIDE output in this export."}]
    return record("decides", ctx, None, "Which companies have a valued CEO move?",
                  f"{len(have)} DECIDE outputs summarised with their chosen or least-bad move, EV and demo flag.",
                  blocks, C, "data")


def evidence_cite(t, ctx, C):
    e = (ctx.meta.get("evidence_located") or {}).get(t) or {}
    return C.add(row_cite(f"row:meta:evidence:{t}", f"meta.json:evidence_located.{t}",
                          "meta.json evidence_located (per-company counts at export)",
                          "; ".join(f"{k} {e.get(k)}" for k in ("findings", "verified", "high_confidence", "rejected", "evidence", "located")),
                          "counted by agent/ui_export.py at export", ticker=t))


def why_company_memo(ctx, t):
    name, c, C = ctx.name(t), ctx.companies[t], Cites()
    f, status = ctx.needle(t)
    st = c.get("stance") or {}
    d = st.get("decide") or {}
    ev = (ctx.meta.get("evidence_located") or {}).get(t) or {}
    p = ""
    if ev.get("verified") is not None:
        n = evidence_cite(t, ctx, C)
        p += (f"{name} has {ev['verified']} page-verified findings, {ev.get('high_confidence', 0)} at high confidence; "
              f"{ev.get('rejected', 0)} candidate rows were rejected by the verifier [{n}].")
    if f:
        lead = match_rule(f.get("signal_kind"), LEADS) or "the needle"
        itxt, _, ins = impact_cell(f, C, t)
        p += f" Its Sharpest Needle is {lc(lead)} {C.mark(*lead_cites(f, C, t))}."
        p += f" Impact: {C.after(itxt, *ins)}."
        att, ons = attention_words(f, ctx, t, C)
        p += f" {C.after(att, *ons)}." if ons else f" {att}."
    if d.get("moves"):
        mv, least_bad = decide_pick(d)
        n = decide_cite(d, t, mv, C)
        p += (f" A valued CEO move exists ({'pipeline demonstration' if d.get('demo') else 'DECIDE output'}): "
              f"{mv.get('name')}, expected value {mny(mv.get('ev'))} [{n}].")
    else:
        p += " No valued CEO move exists yet; the stance is a rule-ranked template."
    rows = []
    for x in ctx.tickers:
        e = (ctx.meta.get("evidence_located") or {}).get(x) or {}
        fx, _ = ctx.needle(x)
        lead = (match_rule(fx.get("signal_kind"), LEADS) if fx else None) or "no needle"
        n = evidence_cite(x, ctx, C) if e.get("verified") is not None else None
        dx = ((ctx.companies[x].get("stance") or {}).get("decide") or {})
        rows.append([f"**{ctx.name(x)}**" if x == t else ctx.name(x),
                     f"{e.get('verified', 'n/a')} ({e.get('high_confidence', 0)} high) [{n}]" if n else "n/a",
                     lead, ("yes, demo" if dx.get("demo") else "yes") if dx.get("moves") else "no"])
    blocks = [{"type": "p", "md": p},
              {"type": "table", "columns": ["Company", "Verified findings", "Sharpest Needle", "Valued move"], "rows": rows},
              {"type": "callout", "tone": "muted",
               "md": "Caveat: the company choice is a human decision informed by the red team; this is the evidence, not a score."}]
    return record("why_company", ctx, t, f"Why {name} over the other nine?",
                  f"The findings case for {name}: verified findings, its needle, its impact and whether a valued move exists.",
                  blocks, C, "data")


def howto_cite(ctx, C, needle_word):
    """Row cite to the section of proof.how_we_did_it_md whose heading contains needle_word, else None."""
    md = ctx.proof.get("how_we_did_it_md")
    if not isinstance(md, str):
        return None
    parts = re.split(r"(?m)^(?=## )", md)
    sec = next((x for x in parts if x.startswith("## ") and needle_word.lower() in x.splitlines()[0].lower()), None)
    if not sec:
        return None
    head = sec.splitlines()[0][3:].strip()
    body = " ".join(l.strip() for l in sec.splitlines()[1:] if l.strip() and not l.startswith("|"))[:240]
    return C.add(row_cite(f"row:proof:how:{norm_alias(head)[:30]}", "proof.json:how_we_did_it_md",
                          f"docs/how_we_did_it_quant.md, section {head}", f"{head}: {body}", "team report section"))


def how_it_works_memo(ctx):
    C, m, pr = Cites(), ctx.meta, ctx.proof
    tot, led = m.get("totals") or {}, m.get("ledger") or {}
    wf, wrong = howto_cite(ctx, C, "Workflow"), howto_cite(ctx, C, "wrong")
    s = ["**Four outputs.** A findings table (source page, impact math, peer comparison, confidence; ranked by impact); "
         "the Sharpest Needle (biggest cited impact, least asked about); the product fine-print table (uses, safety, "
         "dosing, exclusivity, pricing vs rivals, with a growth limiter and a priced-in call); and DECIDE (one CEO move "
         "with a budget against two alternatives on the same five numbers, with kill signals)."]
    v = ("**Verify to the page.** A finding survives only if its quote is on the cited page and every figure is on it "
         "or derived from ones that are")
    if tot.get("rejected"):
        v += f"; the rest go to a rejected log ({tot['rejected']} rows [{meta_cite('totals.rejected', ctx, C)}])"
    s.append(v + (f" [{wf}]." if wf else "."))
    s.append("**Numeric gate.** Every printed number carries a marker to its page, derivation or stated assumption; "
             "failed rows are excluded, oversized impacts withheld, licensed data never printed" + (f" [{wf}]." if wf else "."))
    sealed = (pr.get("sealed") or {})
    preds = ((sealed.get("file") or {}).get("predictions")) or []
    if preds:
        n = proof_cite("sealed.file_hash", ctx, C, "docs/needle_sealed.md and out/predictions/sealed_2026Q3.json",
                       quote=f"{len(preds)} predictions ({', '.join(p['ticker'] for p in preds)}); sha256 {sealed.get('file_hash')}")
        s.append(f"**Sealed forecasts.** Revenue forecasts for {len(preds)} companies were hashed and committed before Q3 results [{n}].")
    cal = pr.get("calibration") or {}
    if cal.get("coverage"):
        n = proof_cite("calibration", ctx, C, "out/predictions/calibration.json")
        s[-1] = s[-1].rstrip(".") + f"; calibration {cal['coverage']} coverage on {cal.get('n_cases')} firm-quarters against a {cal.get('target')} target [{n}]"
        bl = pr.get("blind") or {}
        ak = bl.get("answer_key") or {}
        if bl.get("outcome") == "hit" or (bl.get("prediction") or {}).get("outcome") == "hit":
            n2 = proof_cite("blind", ctx, C, ak.get("citation") or "blind test", quote=ak.get("quote"))
            s[-1] += f"; a blind J&J Q3 test landed inside [{n2}]"
        s[-1] += "."
    if led.get("n"):
        s.append(f"**Ledger.** Every run appends to a hash-chained ledger ({led['n']} records, "
                 f"{'intact' if led.get('ok') else 'broken'} [{meta_cite('ledger.n', ctx, C)}]).")
    s.append("**Honesty.** Memos are rule-drafted from verified findings and DECIDE numbers, not model-written; the AI's "
             "confident errors are logged with fixes" + (f" [{wrong}]." if wrong else "."))
    proof_rows = [[x.split("**")[1].rstrip("."), x.split("** ", 1)[1]] for x in s[3:] if x.startswith("**")]
    tail = [x for x in s[3:] if not x.startswith("**")]
    blocks = [{"type": "p", "md": " ".join(s[:3] + tail)}]
    if proof_rows:
        blocks.append({"type": "table", "columns": ["Proof", "What we did"], "rows": proof_rows})
    return record("how_it_works", ctx, None, "How does NEEDLE work?",
                  "Four outputs: findings table, Sharpest Needle, product fine print, DECIDE; verified to the page, "
                  "gated per number, sealed forecasts.", blocks, C, "data")

# ---------------------------------------------------------------- Part 2 memos
def demo_callout(d, label):
    if d.get("demo"):
        return DEMO_NOTE
    return label + ": " + DEMO_LABEL.split(": ", 1)[1]


def decide_label(stance, ctx, t):
    """Demo/disclaimer label on a DECIDE output: decide.demo when the export states it, else read generically."""
    d = stance.get("decide") or {}
    if isinstance(d.get("demo"), bool):
        return "Pipeline demonstration" if d["demo"] else None
    for src in (d, stance):
        for key in ("label", "demo_label", "demo", "disclaimer", "pipeline_demo", "status_label"):
            v = src.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
            if v is True:
                return "Pipeline demonstration"
    picks = ctx.meta.get("team_pick") or ctx.meta.get("team_picks") or []
    if stance.get("generated_by") == "decide_v2" and t not in (picks if isinstance(picks, list) else [picks]):
        return "Pipeline demonstration"
    return None


TOPIC_MAP = [  # finding kind or topic words -> priced-in scorecard topic
    (("inventory", "dio"), "inventory_channel"), (("ira", "spend_per_claim"), "IRA_negotiation"),
    (("mfn",), "MFN"), (("gtn", "pricing", "price"), "gross_to_net_price"), (("tariff",), "tariff"),
    (("generic", "exclusivity", "loe", "biosimilar"), "biosimilar_generic"), (("guidance",), "guidance"),
    (("rnd", "pipeline", "trial"), "pipeline"),
]


def scorecard_row(c, f):
    """The priced-in scorecard row whose topic matches the finding's kind or topics, else None."""
    if not f:
        return None
    words = " ".join([f.get("signal_kind") or ""] + list((f.get("vector") or {}).get("topics") or [])).lower()
    topic = match_rule(words, TOPIC_MAP)
    return next((r for r in c.get("priced_in") or [] if r.get("topic") == topic), None) if topic else None


def option_cites(st, ctx, t, C, name):
    opt = next((o for o in st.get("options") or [] if o.get("name") == name), None)
    ns = []
    for fid in (opt or {}).get("finding_ids") or []:
        f = ctx.finding(t, fid)
        if f and f.get("evidence") and nc_status(f) != "failed" and not (f.get("impact") or {}).get("suspect"):
            ns += impact_cites(f, C, t, 1)
        if len(ns) >= 2:
            break
    return ns


FIVE = ("ev", "cash_at_risk", "payback_month", "spread", "mcda")


def mny(v):
    v = float(v or 0)
    return f"-${abs(v):,.1f}M" if v < 0 else f"${v:,.1f}M"


def decide_pick(d):
    """(move, least_bad). The chosen move; or, when decide says chosen is null, the least-bad move it names."""
    moves = d.get("moves") or []

    def find(x):
        if isinstance(x, dict):
            return x
        if isinstance(x, str):
            return next((m for m in moves if m.get("name") == x or m.get("code") == x), None)
        return None
    if "chosen" in d and d.get("chosen") is None and d.get("least_bad") is not None:
        return find(d["least_bad"]) or (moves[0] if moves else None), True
    mv = find(d.get("chosen")) or next((m for m in moves if m.get("status") == "chosen"), None) or (moves[0] if moves else None)
    return mv, False


def budget_total(mv):
    b = mv.get("budget") if isinstance(mv.get("budget"), dict) else {}
    for k, v in b.items():
        if "total" in k.lower() and isinstance(v, (int, float)):
            return v, k
    return None, None


def decide_cite(d, t, mv, C):
    moves = d.get("moves") or []
    i = next((k for k, m in enumerate(moves) if m is mv), 0)
    bud, bk = budget_total(mv)
    q = "; ".join(f"{k} {mv.get(k)}" for k in FIVE)
    if bud is not None:
        q += f"; {bk} {bud}"
    if car_note(mv, d) and (mv.get("cash_at_risk") or 0) == 0:
        q += f"; cash_at_risk_note {car_note(mv, d)}"
    return C.add(row_cite(f"row:decide:{t}:{i}", f"companies/{t}.json:stance.decide.moves[{i}]",
                          f"out/{t}/decide.json (agent.needle.quant.decide): {mv.get('name')}", q,
                          (mv.get("numeric_check") or {}).get("status") or "decide record", ticker=t))


ROW_META_KEYS = {"cite", "cites", "cite_id", "cite_ids", "citations", "citation", "ref", "quote", "url", "source_ref",
                 "evidence", "numeric_check", "id"}


def why_it_works_table(d, t, C):
    """stance.decide.why_it_works_rows (prescription, formulary, FDA-calendar and analyst-question data) as a table
    with a cite per row: evidence-shaped citations on the row when it carries them, else a row cite to the record.
    Accepts a list of dicts, a list of lists, or {columns, rows}."""
    src = d.get("why_it_works_rows")
    if isinstance(src, dict):
        cols, rows = src.get("columns"), src.get("rows")
    else:
        cols, rows = None, src
    if not isinstance(rows, list) or not rows:
        return None
    out = []
    for i, r in enumerate(rows):
        if isinstance(r, dict) and r.get("decider") and "what_our_data_shows" in r:
            # decide.md rows: markers in the data cell are footnote numbers into the row's own cites
            mm = {}
            text0 = str(r.get("what_our_data_shows") or "")
            nums = list(dict.fromkeys(seg_markers(text0)[0]))  # footnote numbers in order of first appearance
            claimed = {int(e["n"]) for e in r.get("cites") or [] if isinstance(e, dict) and e.get("n") is not None}
            free = [x for x in nums if x not in claimed]
            for j, e in enumerate(r.get("cites") or []):
                if isinstance(e, dict) and e.get("n") is None and e.get("cite_id") and free:
                    e = dict(e, n=free.pop(0))  # cites exported without a footnote number map to the markers in order
                if not isinstance(e, dict) or e.get("n") is None:
                    continue
                base = f"stance.decide.why_it_works_rows{'.rows' if isinstance(src, dict) else ''}[{i}].cites[{j}]"
                page = e.get("printed") or e.get("page")
                rc = row_cite(f"row:why:{t}:{i}:{e['n']}", f"companies/{t}.json:{base}", doc_label(e),
                              "" if e.get("withheld") else (e.get("quote") or ""), verification_str(e), ticker=t, page=page,
                              url=None if e.get("withheld") else (e.get("deep_link") or e.get("url") or None), value=e.get("value"))
                rc.update({"quote_note": e.get("quote_note") or None, "viewer_link": e.get("viewer_link") or None,
                           "withheld": bool(e.get("withheld")), "withheld_reason": e.get("withheld_reason")})
                mm[str(e["n"])] = C.add(rc)
            unres = {int(x) for x in r.get("markers_unresolved") or []}

            def sub(m, mm=mm, unres=unres):
                if m.group(1):
                    n_ = mm.get(m.group(1))
                    return f"[{n_}]" if n_ and int(m.group(1)) not in unres else ""
                if m.group(2):
                    ops = [str(mm.get(x)) if x.isdigit() and mm.get(x) else x for x in (y.strip() for y in m.group(2).split(",")) if x and not (x.isdigit() and int(x) in unres)]
                    return f"[derived: {', '.join(ops)}]" if ops else ""
                return m.group(0)
            data = _dedupe_runs(MARK.sub(sub, plain_terms(str(r.get("what_our_data_shows") or ""))))
            cols = ["Decider", "What the move needs", "What our data shows", "What only interviews can show"]
            out.append([str(r.get("decider") or ""), plain_terms(str(r.get("what_the_move_needs") or "")), data,
                        plain_terms(str(r.get("what_only_interviews_can_show") or ""))])
            continue
        if isinstance(r, dict):
            cols = cols or [k for k in r.keys() if k not in ROW_META_KEYS]
            cells = ["" if r.get(k) is None else plain_terms(plain_cell(r.get(k))) for k in cols]
            cites = r.get("citations") or r.get("cites") or r.get("evidence") or []
            ns = [C.add(ev_cite(e, None, t, 200 + 10 * i + j)) for j, e in enumerate(cites[:2]) if isinstance(e, dict) and e.get("quote")]
            if not ns:
                ns = [C.add(row_cite(f"row:why:{t}:{i}", f"companies/{t}.json:stance.decide.why_it_works_rows{'.rows' if isinstance(src, dict) else ''}[{i}]",
                                     f"out/{t}/decide.json why_it_works_rows ({r.get('source') or 'decide record'})",
                                     "; ".join(f"{k} {r.get(k)}" for k in cols if r.get(k) not in (None, "")), "decide record", ticker=t))]
        elif isinstance(r, list):
            cols = cols or [f"Column {k + 1}" for k in range(len(r))]
            cells = ["" if x is None else plain_terms(plain_cell(x)) for x in r]
            ns = [C.add(row_cite(f"row:why:{t}:{i}", f"companies/{t}.json:stance.decide.why_it_works_rows{'.rows' if isinstance(src, dict) else ''}[{i}]",
                                 "out/{t}/decide.json why_it_works_rows", "; ".join(str(x) for x in r), "decide record", ticker=t))]
        else:
            continue
        cells[-1] = C.after(cells[-1], *ns)
        out.append(cells)
    if not out:
        return None
    return {"type": "table", "columns": [str(c).replace("_", " ").capitalize() for c in cols], "rows": out}


def car_note(mv, d=None):
    note = mv.get("cash_at_risk_note") or (d or {}).get("cash_at_risk_note")
    return str(note).strip().rstrip(".") if note else None


def car_text(mv, d=None):
    car, bud = mv.get("cash_at_risk"), budget_total(mv)[0]
    if (car or 0) == 0 and bud:
        return plain_terms(car_note(mv, d)) or "none under the base case"
    return mny(car)


def five_kpi(mv, n, d=None):
    pm = mv.get("payback_month")
    car = car_text(mv, d)
    return [{"label": "Expected value, $M", "value": f"{mv.get('ev') or 0:,.1f}", "cite": n},
            {"label": "Cash at risk" + (", $M" if car.startswith(("$", "-$")) else ""), "value": car.lstrip("$") if car.startswith("$") else car, "cite": n},
            {"label": "Payback month", "value": f"{pm}" if pm is not None else "none within the horizon", "cite": n},
            {"label": "Scenario spread, $M", "value": f"{mv.get('spread') or 0:,.1f}", "cite": n},
            {"label": "Weighted score (MCDA)", "value": f"{mv.get('mcda') or 0:.3f}", "cite": n}]


def deciders_sentence(ctx, t, st, C, needle, fs, rec):
    """Two sentences from this company's cited findings (the needle and the top impact row) naming the audiences from
    stance.deciders, plus what the evidence can and cannot tell you."""
    ded = st.get("deciders") or ["Payers: CMS (Medicare negotiation) and Part D plan sponsors",
                                 "Investors: analysts and holders who will read the next 10-Q and earnings call",
                                 "Regulators: FDA (labels, exclusivity) and SEC (disclosure)"]
    parts = []
    for x in ded:
        label, _, body = x.partition(":")
        parts.append(f"{label.strip().lower()} ({body.strip()})" if body else x[0].lower() + x[1:])
    lead = (match_rule(needle.get("signal_kind"), LEADS) if needle else None) or "the needle"
    top = next((f for f in fs if f is not needle and not f.get("explained_by_footnote") and impact_cell(f, Cites(), t)[2]
                and (match_rule(f.get("signal_kind"), LEADS) or "") != lead), None)
    bits = []
    if needle:
        bits.append(f"{lc(lead)} {C.mark(*lead_cites(needle, C, t, 1))}")
    if top:
        tl = match_rule(top.get("signal_kind"), LEADS) or "the next finding"
        bits.append(f"{lc(tl)} {C.mark(*lead_cites(top, C, t, 1))}")
    first = (f"The move answers what the filings show, " + " and ".join(bits) + ", and lands with " + "; ".join(parts) + ".") \
        if bits else "It lands with " + "; ".join(parts) + "."
    second = ("Those pages show the size and timing of the exposure, not how prescribers, patients or payers will "
              "respond: no survey or claims evidence was gathered.")
    return first + " " + second


def ceo_memo(ctx, t):
    name, c, C = ctx.name(t), ctx.companies[t], Cites()
    st = c.get("stance") or {}
    d = st.get("decide") or {}
    needle, status = ctx.needle(t)
    gen = "decide_v2" if st.get("generated_by") == "decide_v2" and d.get("moves") else "template"
    label = decide_label(st, ctx, t)
    mv, least_bad = decide_pick(d) if gen == "decide_v2" else (None, False)
    rec = (mv.get("name") if mv else None) or st.get("recommended") or "Defend"
    lead = (match_rule(needle.get("signal_kind"), LEADS) if needle else None) or "the top finding"
    suffix = f" ({label.lower()})" if label else (" (template stance)" if gen == "template" else "")
    re_line = (f"No move clears the hurdle; least-bad option: {rec}{suffix}" if least_bad else
               f"{rec}{suffix}" if mv else f"{rec}: {lc(lead)}{suffix}")
    header = {"to": f"CEO, {name}", "from": "NEEDLE desk", "re": re_line, "date": as_of_date(ctx)}
    blocks = []
    if label:
        blocks.append({"type": "callout", "tone": "muted", "md": demo_callout(d, label)})
    elif gen == "template":
        blocks.append({"type": "callout", "tone": "muted", "md": TEMPLATE_LABEL})
    fs, _ = ranked_findings(ctx, t)
    # Recommendation
    blocks.append({"type": "h", "text": "Recommendation"})
    opts = {o.get("name"): o for o in st.get("options") or []}
    if mv:
        n = decide_cite(d, t, mv, C)
        bud, _ = budget_total(mv)
        cash = d.get("cash_and_equivalents")
        if least_bad:
            p = f"**No candidate clears the hurdle; least-bad option: {rec} (EV {mny(mv.get('ev'))})** [{n}]."
        else:
            p = f"**Move: {rec}.**"
        why = (mv.get("why") or st.get("headline") or "").strip().rstrip(".")
        if why:
            p += f" {why}."
        if d.get("selection_rule"):
            p += f" {str(d['selection_rule']).strip().rstrip('.')} [{n}]."
        p += (f" Budget: {mny(bud)} committed over 24 months [{n}]; " if bud is not None else " ") + \
             (f"expected value {mny(mv.get('ev'))}, payback month {mv.get('payback_month')} [{n}]."
              if mv.get("payback_month") is not None else
              f"expected value {mny(mv.get('ev'))}, no payback within the horizon [{n}].")
        if cash is not None and bud is not None:
            cn = C.add(row_cite(f"row:decide_cash:{t}", f"companies/{t}.json:stance.decide.cash_and_equivalents",
                                f"out/{t}/decide.json cash and equivalents", f"cash_and_equivalents {cash}",
                                "decide input", ticker=t))
            p += f" Decision needed: approve {mny(bud)} over 24 months against {mny(cash)} of cash and equivalents [{cn}]."
        kpi = [{"label": "Least-bad option" if least_bad else "Recommended", "value": rec, "cite": n},
               {"label": "Budget, $M committed over 24 months", "value": f"{bud:,.1f}" if bud is not None else "not stated", "cite": n},
               *five_kpi(mv, n, d)]
    else:
        rns = option_cites(st, ctx, t, C, rec)
        ndir = impact_cell(needle, Cites(), t)[0].split(".")[0].rstrip() if needle else ""
        p = (f"**Template stance: {rec} archetype, not a valued move.** {OPTION_WHY.get(rec, '').capitalize() or st.get('headline', '')}. "
             f"No DECIDE run has valued a budgeted move for {name}; the options are ranked by rules on the verified findings.")
        if rns and ndir:
            p += (f" The verified findings behind it point the same way: {lc(lead)}, {lc(ndir)} "
                  f"{C.mark(*rns)}.")
        elif not rns:
            p += " No finding in this bucket states an impact formula, so the option is ranked by the size of its cited findings."
        kpi = [{"label": "Template stance", "value": f"{rec} archetype", "cite": None},
               {"label": "Budget", "value": "not valued: no DECIDE run for this company", "cite": None},
               {"label": "Expected value", "value": "not valued", "cite": None},
               {"label": "Direction", "value": (lc(ndir)) if (rns and ndir) else "not quantified", "cite": rns[0] if rns else None},
               {"label": "Confidence", "value": (needle or {}).get("confidence") or "n/a", "cite": None}]
    blocks += [{"type": "p", "md": p}, {"type": "h", "text": "Return math: the five numbers" if mv else "Return math"},
               {"type": "table", "columns": ["Number", "Value"],
                "rows": [[i["label"], C.after(str(i["value"]), i["cite"]) if i.get("cite") else str(i["value"])] for i in kpi]}]
    if mv:
        blocks.append({"type": "callout", "tone": "muted",
                       "md": ("Expected value: present value across bear, base and bull. Cash at risk: committed cash the "
                              "base case does not recover. Weighted score (MCDA): fit, capability, execution risk and "
                              "stakeholder evidence; used only when expected-value ranges overlap.")})
    # Why
    blocks.append({"type": "h", "text": "Why: the five findings that drive it"})
    if needle:
        ns = lead_cites(needle, C, t)
        itxt, formula, ins = impact_cell(needle, C, t)
        why = f"The Sharpest Needle ({NEEDLE_RULE}): {lc(lead)} {C.mark(*ns)}."
        why += f" Impact: {itxt} {C.mark(*ins)}." if ins else f" Impact: {itxt}."
        att, ons = attention_words(needle, ctx, t, C)
        why += f" {att} {C.mark(*ons)}." if ons else f" {att}."
        blocks.append({"type": "p", "md": why})
        note = ((needle.get("vector") or {}).get("obscurity_note")) or ""
        if note and ons:
            blocks.append(math_block("Analyst-attention test, as computed", note, ons[0]))
    table, maths = findings_table(fs, C, t, ctx)
    blocks += [table, *maths]
    # Alternatives
    blocks.append({"type": "h", "text": "Alternatives rejected"})
    items = []
    if mv:
        others = sorted([m for m in d.get("moves") or [] if m is not mv], key=lambda m: m.get("rank") or 99)
        alts = {a.get("name"): a for a in st.get("alternatives") or []}
        for m in others[:2]:
            n = decide_cite(d, t, m, C)
            reason = m.get("binding_reason") or (alts.get(m.get("name")) or {}).get("why_rejected") or "lower expected value"
            reason = re.sub(r"\s*\(spec [\d.]+\)", "", reason).strip().rstrip(";. ")
            pm = m.get("payback_month")
            reason = reason.replace("MCDA", "weighted score")
            passed = m.get("why_passed") or (alts.get(m.get("name")) or {}).get("why_passed")
            if passed:
                passed = re.sub(r"^Why we passed: ", "", str(passed).strip().rstrip(".")).replace("MCDA", "weighted score")
                passed = re.sub(r"\s*\(spec [\d.]+\)", "", passed)
            items.append([m.get("name"), f"{mny(m.get('ev'))} [{n}]", C.after(car_text(m, d), n), f"{pm}" if pm is not None else "none within the horizon",
                          mny(m.get("spread")), f"{m.get('mcda') or 0:.3f}", f"{plain_terms(passed)} [{n}]" if passed else reason])
        cols = ["Move", "Expected value", "Cash at risk", "Payback month", "Spread", "Weighted score",
                "Why we passed" if any(m.get("why_passed") or (alts.get(m.get("name")) or {}).get("why_passed") for m in others[:2]) else "Not chosen because"]
    else:
        for alt in (st.get("alternatives") or [])[:2]:
            an = alt.get("name")
            top = next((ctx.finding(t, fid) for fid in (opts.get(an) or {}).get("finding_ids") or [] if ctx.finding(t, fid)), None)
            ans = option_cites(st, ctx, t, C, an)
            behind = ""
            if top:
                tl = match_rule(top.get("signal_kind"), LEADS) or "its top finding"
                tns = lead_cites(top, C, t, 1)
                behind = f" ({lc(tl)} {C.mark(*(tns + ans))})"
            items.append([an, f"would {OPTION_WHY.get(an, 'address a different finding')}", behind.strip(" ()") or "no quantified finding",
                          f"smaller cited impacts than the needle; fallback if the {rec} kill signals fire"])
        cols = ["Option", "Would", "Finding behind it", "Why not now"]
    blocks.append({"type": "table", "columns": cols, "rows": items} if items else {"type": "p", "md": "No alternative recorded."})
    # Prove wrong
    blocks.append({"type": "h", "text": "What would prove us wrong: kill signals, 6 to 12 months"})
    blocks.append({"type": "table", "columns": ["Signal", "Baseline today", "What it would show"], "rows": kill_rows(ctx, t, C, fs, st, gen)[:3]})
    blocks.append({"type": "p", "md": "Two signals firing in one quarter pause the move and re-run the valuation."})
    # Deciders
    blocks.append({"type": "h", "text": "Why it lands with the deciders"})
    wiw = why_it_works_table(d, t, C)
    if wiw:
        blocks.append(wiw)
    blocks.append({"type": "p", "md": deciders_sentence(ctx, t, st, C, needle, fs, rec)})
    # Priced in
    blocks.append({"type": "h", "text": "Priced in or not"})
    pi, pns = priced_call(ctx, t, C)
    pp = C.after(pi[0].upper() + pi[1:], *pns)
    hit = scorecard_row(c, needle)
    if hit:
        n = priced_in_cite(t, hit, C)
        pp += (f"; analysts raised {topic_words(hit['topic'])} in {hit.get('quarters_asked')} of "
               f"{hit.get('quarters_covered')} quarters [{n}]")
    elif needle:
        att, ons = attention_words(needle, ctx, t, C)
        pp += f"; {att[0].lower() + att[1:]} {C.mark(*ons)}" if ons else f"; {att[0].lower() + att[1:]}"
    blocks.append({"type": "p", "md": pp + "."})
    summary = ((f"{'Least-bad option' if least_bad else 'Recommend'} {rec} for {name} (EV {mny(mv.get('ev'))})" if mv else
                f"Template stance for {name} (no valued move): {rec} archetype; {lc(lead)}") + f"; {pi.split(':')[0]}.")
    nc = needle.get("numeric_check") if needle and isinstance(needle.get("numeric_check"), dict) else None
    if gen == "decide_v2":
        nc = d.get("numeric_check") or nc
    return record("ceo_memo", ctx, t, f"Write the CEO memo for {name}", summary, blocks, C, gen, nc, memo_header=header)

def baseline_parts(base):
    """(label text, cite dicts) from a kill-signal baseline: {value, text, cites} (current export), [value, repr,
    label] (older) or a bare string."""
    if isinstance(base, dict):
        return (base.get("text") or None), [c for c in base.get("cites") or [] if isinstance(c, dict)]
    if isinstance(base, list) and base and isinstance(base[-1], str):
        return base[-1], []
    return (base if isinstance(base, str) else None), []


def kill_parts(ctx, t, C, i, k):
    """(signal, baseline today, what it would show) for one DECIDE kill signal, all in plain words and cited, or
    None when the row is a context row or has no baseline. The physician-breadth row (Open Payments) reads:
    'Doctors with any <product> contact in Open Payments | 2,751 in 2024 (...) | a fall below 30% of that by
    month 6 stops the move; annual file, ...'."""
    if k.get("threshold") == "context" or not k.get("signal"):
        return None
    label, cites = baseline_parts(k.get("baseline"))
    if not label:
        return None
    label = re.sub(r";?\s*api_\w+$", "", label).strip()
    n = C.add(row_cite(f"row:kill:{t}:{i}", f"companies/{t}.json:stance.kill_signals[{i}]",
                       f"out/{t}/decide.json kill-signal table ({k.get('source')})",
                       "; ".join(f"{key} {k.get(key)}" for key in ("id", "signal", "threshold", "source", "lag", "check_month", "action") if k.get(key) not in (None, ""))
                       + f"; baseline {label}", "decide record", ticker=t))
    ns = [n] + [C.add(ev_cite(c, None, t, 300 + 10 * i + j)) for j, c in enumerate(cites[:2]) if c.get("cite_id")]
    act = ACTION_WORDS.get(k.get("action"), str(k.get("action") or "review").replace("_", " "))
    stops = "stops the move" if k.get("stop") else f"; then {act}"
    sig, thr, lag = plain_terms(k.get("signal") or ""), str(k.get("threshold") or ""), plain_terms(k.get("lag") or "")
    product = sig.split(":")[0].strip() if ":" in sig else None
    m = re.match(r"Open Payments ([\d,]+) distinct physicians \(PY(\d{4})\): ([\d,]+) paid relationships \(([^)]*)\), ([\d,]+) light-touch only", label)
    if k.get("id") == "physician_breadth" and m and product:
        pct = re.search(r"(\d+)%", thr)
        signal = f"Doctors with any {product} contact in Open Payments"
        base_md = f"{m.group(1)} in {m.group(2)} ({m.group(3)} paid relationships: {m.group(4)}; {m.group(5)} light-touch only) {C.mark(*ns)}"
        what = (f"a fall below {pct.group(1)}% of that by month {k.get('check_month')}" if pct else
                f"{thr} by month {k.get('check_month')}") + (f" {stops}" if not stops.startswith(";") else stops) + (f"; {lag}" if lag else "")
        return signal, base_md, what
    return (sig, f"{plain_terms(label)} {C.mark(*ns)}",
            f"{thr} by month {k.get('check_month')} ({plain_terms(k.get('source') or '')})" + (f" {stops}" if not stops.startswith(";") else stops) + (f"; {lag}" if lag else ""))


def kill_rows(ctx, t, C, fs, st, gen):
    """[signal, baseline today, what it would show] rows: decide signals with a baseline, then findings-based rules."""
    rows = []
    if gen == "decide_v2" and st.get("kill_signals"):
        for i, k in enumerate(st["kill_signals"]):
            parts = kill_parts(ctx, t, C, i, k)
            if parts:
                rows.append(list(parts))
    seen = set()
    for f in fs:
        if len(rows) >= 3:
            break
        if f.get("explained_by_footnote") or "explained_by" in str(f.get("signal_kind") or ""):
            continue  # a footnote-explained or artifact-explaining row is not a signal to watch
        rule = match_rule(f.get("signal_kind"), PROVE_WRONG)
        if not rule or rule in seen:
            continue
        seen.add(rule)
        lead = match_rule(f.get("signal_kind"), LEADS) or "the finding"
        s_, ns = sentence(f, C, t)
        cell = clip(s_, 18)
        rows.append([lead, C.after(cell + rest_marks(s_, cell, C), *ns), rule.rstrip(".")])
    if len(rows) < 3:
        sf = ctx.companies[t].get("sealed_forecast") or {}
        iv = next((b for b in sf.get("basis") or [] if "interval" in b), "")
        if iv:
            n = C.add(row_cite(f"row:sealed:{t}", f"companies/{t}.json:sealed_forecast",
                               "out/predictions/sealed_2026Q3.json (sha256-committed, docs/needle_sealed.md)",
                               f"{sf.get('id')}: {'; '.join(sf.get('basis') or [])}", "sealed forecast", ticker=t))
            rows.append(["Q3 2026 revenue growth", f"sealed forecast {iv}, hashed before results [{n}]", "a print outside the sealed interval"])
    return rows


def kill_signals(ctx, t, C, fs, st, gen, brief=False):
    items = []
    if gen == "decide_v2" and st.get("kill_signals"):
        for i, k in enumerate(st["kill_signals"]):
            if brief and len(items) >= 4:
                break
            parts = kill_parts(ctx, t, C, i, k)
            if not parts:
                continue  # context rows are inputs, not signals; a signal with no baseline has nothing to move from
            sig, base_md, what = parts
            items.append(f"**{sig}**: {base_md}; {what}.")
        if len(items) >= 3:
            return items
    seen = set()
    for f in fs:
        rule = match_rule(f.get("signal_kind"), PROVE_WRONG)
        if not rule or rule in seen or f.get("explained_by_footnote") or "explained_by" in str(f.get("signal_kind") or ""):
            continue
        seen.add(rule)
        lead = match_rule(f.get("signal_kind"), LEADS) or "the finding"
        if brief:
            items.append(f"{rule} Baseline: {lc(lead)} {C.mark(*lead_cites(f, C, t))}.")
        else:
            s, ns = sentence(f, C, t)
            cell = clip(s, 30)
            items.append(f"{rule} Baseline today: {C.after(cell + rest_marks(s, cell, C), *ns)}.")
        if len(items) >= 3:
            break
    sf = ctx.companies[t].get("sealed_forecast") or {}
    iv = next((b for b in sf.get("basis") or [] if "interval" in b), "")
    if iv:
        n = C.add(row_cite(f"row:sealed:{t}", f"companies/{t}.json:sealed_forecast",
                           "out/predictions/sealed_2026Q3.json (sha256-committed, docs/needle_sealed.md)",
                           f"{sf.get('id')}: {'; '.join(sf.get('basis') or [])}", "sealed forecast", ticker=t))
        items.append(f"Q3 2026 revenue growth lands outside our sealed forecast ({iv}), which was hashed and committed "
                     f"before results [{n}].")
    for x in st.get("prove_wrong") or []:
        if len(items) >= 4:
            break
        if not re.search(r"\d", re.sub("|".join(WHITELIST), "", x)) and x not in items:
            items.append(x)
    return items


def what_we_would_do(st, needle, rec):
    has_peer = bool(re.search(r"peer median", (needle or {}).get("finding") or ""))
    alts = [a.get("name") for a in st.get("alternatives") or [] if a.get("name") and a.get("name") != rec]
    fallback = alts[0] if alts else None
    p = "Check each signal at every 10-Q and after every earnings call. "
    p += ("If the needle metric closes toward the peer median and the sealed forecast holds, " if has_peer else
          "If the needle's exposure does not materialise in the filings and the sealed forecast holds, ")
    p += f"the {rec} commitment is released"
    p += f"; if two signals fire instead, the move shifts toward {fallback}." if fallback else "; if two signals fire instead, the move is paused and re-valued."
    return p + " We publish the check, hit or miss, in the ledger."


def prove_wrong_memo(ctx, t):
    name, c, C = ctx.name(t), ctx.companies[t], Cites()
    st = c.get("stance") or {}
    gen = "decide_v2" if st.get("generated_by") == "decide_v2" and (st.get("decide") or {}).get("moves") else "template"
    label = decide_label(st, ctx, t)
    needle, status = ctx.needle(t)
    fs, _ = ranked_findings(ctx, t)
    mv, least_bad = decide_pick(st.get("decide") or {}) if gen == "decide_v2" else (None, False)
    rec = (mv.get("name") if mv else None) or st.get("recommended") or "Defend"
    suffix = f" ({label.lower()})" if label else (" (template stance)" if gen == "template" else "")
    header = {"to": f"CEO, {name}", "from": "NEEDLE desk", "re": f"What would prove us wrong on {rec}{suffix}",
              "date": as_of_date(ctx)}
    d = st.get("decide") or {}
    blocks = [*([{"type": "callout", "tone": "muted", "md": demo_callout(d, label)}] if label else
               [{"type": "callout", "tone": "muted", "md": TEMPLATE_LABEL}] if gen == "template" else []),
              {"type": "h", "text": "Kill signals, first six to twelve months"},
              {"type": "p", "md": (f"The {rec} move for {name} rests on the findings below. Each signal names the filing or "
                                   f"data row we will re-read, and the baseline it must move from; if two fire in the same "
                                   f"quarter, leadership pauses the move and the valuation is re-run.")},
              {"type": "list", "items": kill_signals(ctx, t, C, fs[:5], st, gen)},
              {"type": "h", "text": "What we would do"},
              {"type": "p", "md": what_we_would_do(st, needle, rec)}]
    deciders = st.get("deciders") or []
    if deciders:
        blocks.append({"type": "callout", "tone": "muted", "md": "Who decides its fate: " + "; ".join(deciders) + "."})
    nc = needle.get("numeric_check") if needle and isinstance(needle.get("numeric_check"), dict) else None
    return record("prove_wrong", ctx, t, f"What would prove us wrong on {name}?",
                  f"Kill signals for the {rec} move at {name}, with the cited baseline each must move from.",
                  blocks, C, gen, nc, memo_header=header)


# ---------------------------------------------------------------- build
def build(ctx, kinds=None):
    memos = []
    want = set(kinds) if kinds else None
    def ok(k):
        return want is None or k in want
    for t in ctx.tickers:
        if ok("needle"):
            memos.append(needle_memo(ctx, t))
        if ok("why_company"):
            memos.append(why_company_memo(ctx, t))
        if ok("findings"):
            memos.append(findings_memo(ctx, t))
        if ok("product"):
            for slug, v2, comp in ctx.products(t):
                memos.append(product_memo(ctx, t, slug, v2, comp))
        if ok("peers") and ctx.companies[t].get("forces"):
            memos.append(peers_memo(ctx, t))
        if ok("priced_in") and (ctx.companies[t].get("priced_in") or ctx.companies[t].get("consensus_vs_guidance")):
            memos.append(priced_in_memo(ctx, t))
        if ok("ceo_memo"):
            memos.append(ceo_memo(ctx, t))
        if ok("prove_wrong"):
            memos.append(prove_wrong_memo(ctx, t))
    if ok("league") and ctx.league:
        memos.append(league_memo(ctx))
    if ok("needles") and len(ctx.tickers) > 1:
        memos.append(needles_memo(ctx))
    if ok("products") and any(ctx.products(t) for t in ctx.tickers):
        memos.append(products_memo(ctx))
    if ok("decides") and len(ctx.tickers) > 1:
        memos.append(decides_memo(ctx))
    if ok("ai_wrong") and (ctx.proof.get("ai_wrong_cases") or any(r.get("what_the_source_says") for r in ctx.proof.get("ai_wrong") or [])):
        memos.append(ai_wrong_memo(ctx))
    if ok("limits") and ctx.meta.get("honest_limits"):
        memos.append(limits_memo(ctx))
    if ok("moat") and (ctx.meta.get("corpus") or ctx.meta.get("moat")):
        memos.append(moat_memo(ctx))
    if ok("how_it_works") and ctx.meta.get("totals"):
        memos.append(how_it_works_memo(ctx))
    ids = {m["id"] for m in memos}
    for m in memos:
        m["ask_next"] = [x for x in m["ask_next"] if x in ids][:3]
    d = ctx.default
    picked = (ctx.meta.get("default_ticker_source") or "unpicked") == "pick" and d
    if picked:
        suggested = [x for x in ctx.flow(d) if x and not x.startswith("prove_wrong:")] + ["ai_wrong:global"]
    else:  # no pick made: company-agnostic entry points only
        suggested = ["needles:global", "how_it_works:global", "ai_wrong:global", "moat:global", "products:global",
                     "limits:global"]
    suggested = [x for x in suggested if x in ids][:7]
    by_ticker = {t: [x for x in ctx.flow(t) if x in ids] for t in ctx.tickers}
    return {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "mode": "cached",
            "engine": ctx.meta.get("engine") or ("sample" if ctx.sample else "unknown"), "default_ticker": d,
            "default_ticker_source": ctx.meta.get("default_ticker_source") or "unpicked",
            "as_of": ctx.meta.get("as_of"), "suggested": suggested, "suggested_by_ticker": by_ticker, "memos": memos,
            "note": "Cached answers assembled by agent/ui_memos.py from ui/public/data; no model call. " + WHITELIST_NOTE}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


# ---------------------------------------------------------------- check
def md_segments(block):
    """(segment text, kind) pairs: sentences of a paragraph, list items, table rows, kpi values."""
    t = block.get("type")
    if t == "p" or t == "callout":
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z*\"(])", block.get("md") or "")
        return [(p, "sentence") for p in parts if p.strip()]
    if t == "list":
        return [(x, "item") for x in block.get("items") or []]
    if t == "table":
        return [(" | ".join(r), "row") for r in block.get("rows") or []]
    if t == "kpi":
        return [(f"{i.get('value')}{'[' + str(i['cite']) + ']' if i.get('cite') else ''}", "kpi") for i in block.get("items") or []]
    if t == "h":
        return [(block.get("text") or "", "heading")]
    return []  # math blocks are checked separately


VAR_TOKENS = [  # engine variable names and formula fragments that may appear only in math blocks
    r"\bRev_[A-Za-z]+\b", r"\bs_MFN\b", r"\bm_avoided\b", r"\bqa_turns\b", r"\bpi_min\b", r"\bS = 0\b",
    r"\bdEPS\b", r"\bdRev\b", r"\bdOI\b", r"\bN_eff\b", r"\bMFP30\b", r"\blist30\b", r"\bpriced_in_scorecard\b",
    r"x max\(0", r"\(1 - t [\d.]+\)", r"/ D [\d,.]+", r"\bG [\d,.]+ x", r"\bk \([\d., ]+\)", r"\bd \([\d., ]+\)",
    r"\b[A-Za-z]+_[A-Za-z][A-Za-z0-9_]*\b(?!\.(?:csv|json|md|jsonl))",
]


def var_tokens(text):
    return [m.group(0) for pat in VAR_TOKENS for m in re.finditer(pat, text or "")]


def tok_float(x):
    try:
        return float(x.replace(",", ""))
    except ValueError:
        return None


def token_ok(tok, allowed_floats):
    """A printed number is fine if a gated number equals it, or equals it divided by 100 (percent of a decimal),
    at the precision printed."""
    v = tok_float(tok)
    if v is None:
        return True
    dec = len(tok.split(".")[1]) if "." in tok else 0
    tol = 0.5 * 10 ** (-dec)
    return any(abs(a - v) <= tol + 1e-9 or abs(a - v / 100) <= tol / 100 + 1e-12 for a in allowed_floats)


def unmarked_digits(text):
    stripped = re.sub("|".join(WHITELIST), "", strip_marks(text))
    return bool(re.search(r"\d", stripped))


def seg_markers(seg):
    """(cite numbers referenced by [n] and [derived: ...] operands, True when any marker kind is present)."""
    ns, any_mark = [], False
    for m in MARK.finditer(seg or ""):
        any_mark = True
        if m.group(1):
            ns.append(int(m.group(1)))
        elif m.group(2):
            ns += [int(x) for x in (y.strip() for y in m.group(2).split(",")) if x.isdigit()]
    return ns, any_mark


GATED_FIELDS = ("finding", "finding_raw", "sentence", "sentence_marked", "impact_gated")


def gated_text(f):
    """Every text field the numeric gate checks on a finding record (sentence, impact math, peer text)."""
    parts = [f.get(k) for k in GATED_FIELDS if isinstance(f.get(k), str)]
    imp = f.get("impact") or {}
    parts += [imp.get(k) for k in ("formula",) + GATED_IMPACT_KEYS if isinstance(imp.get(k), str)]
    peer = f.get("peer") or {}
    parts += [peer.get(k) for k in ("note", "named_peer_row") if isinstance(peer.get(k), str)]
    parts.append(((f.get("vector") or {}).get("obscurity_note")) or "")
    parts.append(f.get("obscurity_note") or "")
    parts += [f.get(k) for k in ("formula_marked",) if isinstance(f.get(k), str)]
    parts += [cite_text(e) for e in (f.get("evidence") or []) + (f.get("data_citations") or []) if isinstance(e, dict)]
    return strip_marks(" ".join(parts))


def num_tokens(text):
    return {x.replace(",", "") for x in re.findall(r"\d+(?:[.,]\d+)*", text or "")}


def product_gated_text(ctx, t, slug):
    v2 = (((ctx.companies.get(t) or {}).get("labels") or {}).get("v2") or {}).get(slug) or {}
    parts = []
    for row in (v2.get("rows") or {}).values():
        for cell in (row or {}).values():
            if not (cell or {}).get("uncited"):
                parts.append(str((cell or {}).get("value") or ""))
                parts += [cite_text(c) for c in (cell or {}).get("citations") or [] if isinstance(c, dict)]  # label quotes on the page
    gl = v2.get("growth_limiter") or {}
    parts += [gl.get("sentence") or "", gl.get("sentence_raw") or ""]
    for f in v2.get("findings") or []:
        if isinstance(f, dict):
            parts.append(gated_text(f))
    comp = next((r for r in ((ctx.companies.get(t) or {}).get("labels") or {}).get("comparison") or [] if r.get("product") == slug), None)
    for r in (comp or {}).get("rows") or []:
        for v in (r.get("values") or {}).values():
            if not (v or {}).get("uncited"):
                parts.append(str((v or {}).get("value") or ""))
    return " ".join(parts)


def allowed_tokens(m, ctx):
    """Numeric tokens a memo may print: gated fields of every cited finding, the data rows behind row cites,
    the product's gated cells, and the five decide numbers."""
    t, allowed = m.get("ticker"), set()
    for c in m.get("cites") or []:
        tk = c.get("ticker") or t
        for fid in dict.fromkeys([c.get("finding_id")] + (c.get("finding_ids") or [])):
            f = ctx.finding(tk, fid) if fid and tk in ctx.companies else None
            if f:
                allowed |= num_tokens(gated_text(f))
                row = ctx.table_rows(tk)[0].get(fid) if tk in ctx.companies else None
                if isinstance(row, dict):  # the findings_table row's gated peer text and marked cells
                    allowed |= num_tokens(" ".join(str(row.get(k) or "") for k in ("peer_text", "peer_comparison", "sentence_marked", "impact_marked")))
        if (c.get("cite_id") or "").startswith("row:"):
            allowed |= num_tokens(c.get("quote") or "")
            obj, _ = resolve_ref(c.get("ref") or "", ctx)
            if obj is not None:
                allowed |= num_tokens(json.dumps(obj, ensure_ascii=False))
    if m.get("kind") == "product" and t:
        allowed |= num_tokens(product_gated_text(ctx, t, m["id"].split(":")[-1]))
    if m.get("kind") == "products":
        for tk in ctx.companies:
            for slug, _, _ in ctx.products(tk):
                allowed |= num_tokens(product_gated_text(ctx, tk, slug))
    for tk in ([t] if t else [x for x in ctx.companies if m.get("kind") in ("decides", "why_company", "needles")]):
        d = ((ctx.companies.get(tk) or {}).get("stance") or {}).get("decide") or {}
        for mv in d.get("moves") or []:
            vals = [mv.get(k) for k in FIVE] + list((mv.get("budget") or {}).values() if isinstance(mv.get("budget"), dict) else [])
            for v in vals:
                if isinstance(v, (int, float)):
                    allowed |= num_tokens(f"{v} {v:,} {v:,.1f}")
        if isinstance(d.get("cash_and_equivalents"), (int, float)):
            v = d["cash_and_equivalents"]
            allowed |= num_tokens(f"{v} {v:,} {v:,.1f}")
        for it in d.get("numeric_items") or []:  # decide text that passed its own numeric check
            if isinstance(it, dict) and it.get("passed"):
                allowed |= num_tokens(it.get("text") or "")
    return allowed


def collect_cite_ids(obj, acc):
    if isinstance(obj, dict):
        if obj.get("cite_id"):
            acc.add(obj["cite_id"])
        for v in obj.values():
            collect_cite_ids(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect_cite_ids(v, acc)


def check(path, ctx):
    doc = read_json(path)
    errors, warns = [], []
    if not doc:
        return [f"{path}: missing or unreadable"], warns, {}
    memos = doc.get("memos") or []
    pools = {}
    try:
        mt = Path(path).stat().st_mtime
        newer = [p.name for p in list((ctx.dir / "companies").glob("*.json")) + [ctx.dir / "meta.json", ctx.dir / "proof.json", ctx.dir / "league.json"]
                 if p.exists() and p.stat().st_mtime > mt + 1]
        if newer:
            errors.append(f"{path.name} is older than {', '.join(sorted(newer))}: regenerate")
    except OSError:
        pass

    def pool(t):
        if t not in pools:
            acc = set()
            collect_cite_ids(ctx.companies.get(t) or {}, acc)
            pools[t] = acc
        return pools[t]
    ids = [m["id"] for m in memos]
    if len(set(ids)) != len(ids):
        errors.append("duplicate memo ids: " + ", ".join(k for k, v in Counter(ids).items() if v > 1))
    idset = set(ids)
    for s in doc.get("suggested") or []:
        if s not in idset:
            errors.append(f"suggested id {s} does not exist")
        if s.startswith("league:"):
            errors.append("league memo listed in suggested")
    for tk, ids_ in (doc.get("suggested_by_ticker") or {}).items():
        for s in ids_:
            if s not in idset:
                errors.append(f"suggested_by_ticker[{tk}] id {s} does not exist")
    if (doc.get("default_ticker_source") or "unpicked") != "pick" and doc.get("suggested"):
        for s in doc["suggested"]:
            if not s.endswith(":global"):
                errors.append(f"no company pick made, yet suggested carries the company answer {s}")
    seen_alias = {}
    stats = {"kinds": Counter(), "words": 0, "cites": 0, "row_cites": 0, "memos": len(memos), "words_by_format": Counter()}
    for m in memos:
        mid, t = m["id"], m.get("ticker")
        stats["kinds"][m.get("kind")] += 1
        fmt = "memo" if m.get("kind") in MEMO_KINDS else "chat"
        if m.get("format") != fmt:
            errors.append(f"{mid}: format {m.get('format')} should be {fmt}")
        if fmt == "memo" and not (m.get("memo_header") or {}).get("re"):
            errors.append(f"{mid}: memo format without memo_header")
        if m.get("kind") not in CHAT_KINDS + MEMO_KINDS:
            errors.append(f"{mid}: unknown kind {m.get('kind')}")
        if m.get("generated_by") not in ("template", "decide_v2", "data"):
            errors.append(f"{mid}: bad generated_by {m.get('generated_by')}")
        for a in [m.get("prompt")] + (m.get("aliases") or []):
            k = norm_alias(a)
            if k in seen_alias and seen_alias[k] != mid:
                errors.append(f"{mid}: alias '{a}' also used by {seen_alias[k]}")
            seen_alias[k] = mid
        if len(m.get("aliases") or []) < 6:
            warns.append(f"{mid}: only {len(m.get('aliases') or [])} aliases")
        if t and m.get("kind") == "needle":  # company-less needle phrasings must score the league memo, not a company
            names = [norm_alias(x) for x in ctx.nicks(t)] + [t.lower()]
            for a in [m.get("prompt")] + (m.get("aliases") or []):
                if not any(nm and nm in norm_alias(a) for nm in names):
                    errors.append(f"{mid}: alias '{a}' names neither the company nor the ticker")
        for x in m.get("ask_next") or []:
            if x not in idset:
                errors.append(f"{mid}: ask_next {x} does not exist")
            if x.startswith("league:"):
                errors.append(f"{mid}: ask_next leads to the league memo")
        if m.get("kind") == "ceo_memo":
            labels = [b.get("text") or "" for b in m.get("blocks") or [] if b.get("type") == "h"]
            labels += [i.get("label") or "" for b in m.get("blocks") or [] if b.get("type") == "kpi" for i in b.get("items") or []]
            labels += [str(r[0]) for b in m.get("blocks") or [] if b.get("type") == "table" for r in b.get("rows") or [] if r]
            for what, pat in PART2:
                if not any(re.search(pat, x) for x in labels):
                    errors.append(f"{mid}: Part 2 element missing ({what}): no heading or kpi label matches {pat!r}")
        if m.get("kind") == "findings":
            tabs = [b for b in m.get("blocks") or [] if b.get("type") == "table"]
            cols = tabs[0].get("columns") if tabs else []
            missing = [c for c in PART1_COLUMNS if c not in (cols or [])]
            if missing:
                errors.append(f"{mid}: findings table lacks the per-finding column(s) {missing}")
        if "demo" not in m or "demo_note" not in m:
            errors.append(f"{mid}: demo / demo_note missing")
        cites = {c["n"]: c for c in m.get("cites") or []}
        stats["cites"] += len(cites)
        allowed = allowed_tokens(m, ctx)
        for b in m.get("blocks") or []:
            if b.get("type") == "math":
                allowed |= num_tokens(b.get("text") or "")
                if b.get("cite") not in cites:
                    errors.append(f"{mid}: math block '{b.get('label')}' cite {b.get('cite')} missing")
                if not b.get("text"):
                    errors.append(f"{mid}: empty math block")
                if b.get("text_marked"):
                    for n in seg_markers(b["text_marked"])[0]:
                        if n not in cites:
                            errors.append(f"{mid}: math block marker [{n}] has no cite")
                    if strip_marks(b["text_marked"]).replace(" ", "") != (b.get("text") or "").replace(" ", "") \
                            and not b.get("text"):
                        errors.append(f"{mid}: math block text_marked without plain text")
            if PITCH_FORBIDDEN.search(b.get("label") or ""):
                errors.append(f"{mid}: internal score language in math label {b.get('label')!r}")
        if PITCH_FORBIDDEN.search(m.get("summary") or "") or PITCH_FORBIDDEN.search(m.get("prompt") or ""):
            errors.append(f"{mid}: internal score language in summary or prompt")
        allowed_floats = {tok_float(x) for x in allowed if tok_float(x) is not None}
        used = set()
        wc = 0
        for b in m.get("blocks") or []:
            if b.get("type") == "math":
                used.add(b.get("cite"))
                used.update(seg_markers(b.get("text_marked") or "")[0])
                continue
            if b.get("type") in ("p", "list", "callout"):
                wc += words(b.get("md") or " ".join(b.get("items") or []))
            pending = []  # sentences with numbers waiting for the next marker in the same block
            for seg, kind in md_segments(b):
                ns, any_mark = seg_markers(seg)
                for n in ns:
                    if n not in cites:
                        errors.append(f"{mid}: marker [{n}] has no cite")
                    used.add(n)
                if PITCH_FORBIDDEN.search(seg) and not (m.get("kind") == "league" and b.get("type") == "callout"):
                    errors.append(f"{mid}: internal score language in {kind}: {seg[:100]!r}")
                if any_mark:
                    pending = []
                elif unmarked_digits(seg):
                    if kind == "sentence":
                        pending.append(seg)
                    else:
                        errors.append(f"{mid}: number without a cite marker in {kind}: {seg[:110]!r}")
                stripped = re.sub("|".join(WHITELIST), "", strip_marks(seg))
                bad = [x for x in num_tokens(stripped) if not token_ok(x, allowed_floats)]
                if re.search(r"\{['\"]|\[\{|\(\{|': |\": ", seg) and not (m.get("kind") == "ai_wrong" and kind == "row"):
                    errors.append(f"{mid}: dict or list literal in {kind}: {seg[:100]!r}")
                if kind != "heading" and not (m.get("kind") == "ai_wrong" and kind == "row"):
                    vt = var_tokens(seg)
                    if vt:
                        errors.append(f"{mid}: engine variable token(s) {vt[:4]} in {kind}: {seg[:100]!r}")
                        stats["var_tokens"] = stats.get("var_tokens", 0) + len(vt)
                if bad and kind != "heading":
                    errors.append(f"{mid}: number(s) {bad} not in any gated field or cited data row, in {kind}: {seg[:100]!r}")
                    stats["ungated"] = stats.get("ungated", 0) + len(bad)
            for seg in pending:
                errors.append(f"{mid}: number without a cite marker in sentence: {seg[:110]!r}")
            if b.get("type") == "kpi":
                for i in b.get("items") or []:
                    if i.get("cite") is not None and i["cite"] not in cites:
                        errors.append(f"{mid}: kpi cite {i['cite']} missing")
        stats["words"] += wc
        stats["words_by_format"][fmt] += wc
        lo, hi = (200, 350) if fmt == "memo" else (30, 180 if m.get("kind") in ("decides", "limits", "how_it_works") else 160)
        if m.get("kind") in ("needles", "products"):
            hi = 120
        if not lo <= wc <= hi:
            warns.append(f"{mid}: {wc} prose words (target {lo} to {hi})")
        for n, c in cites.items():
            if n not in used:
                warns.append(f"{mid}: cite [{n}] never referenced")
            if c.get("withheld") and (c.get("quote") or c.get("excerpt") or c.get("url")):
                errors.append(f"{mid}: withheld cite [{n}] carries quote/excerpt/url")
            cid = c.get("cite_id") or ""
            if cid.startswith("row:"):
                stats["row_cites"] += 1
                obj, err = resolve_ref(c.get("ref") or "", ctx)
                if err or obj is None:
                    errors.append(f"{mid}: row cite [{n}] {cid} does not resolve: {err}")
                elif c.get("value") is not None and not c.get("withheld") and str(c["value"]) not in (c.get("quote") or ""):
                    # a withheld machine-data row shows its value with no quote by design
                    errors.append(f"{mid}: row cite [{n}] value {c['value']} not in quote")
                if cid.startswith("row:decide:") and isinstance(obj, dict):
                    for key in FIVE:
                        qm = re.search(rf"\b{key} (\S+)", c.get("quote") or "")
                        if qm and str(obj.get(key)) != qm.group(1).rstrip(";"):
                            errors.append(f"{mid}: row cite [{n}] {cid} quotes {key} {qm.group(1)} but the decide row now says {obj.get(key)}")
            elif cid.startswith("ev:"):
                _, fid, idx = cid.split(":")
                f = ctx.finding(c.get("ticker"), fid) if c.get("ticker") in ctx.companies else None
                if not f or int(idx) >= len(f.get("evidence") or []):
                    errors.append(f"{mid}: evidence cite [{n}] {cid} not in company file")
            else:
                tk = c.get("ticker") or t
                if not tk or cid not in pool(tk):
                    errors.append(f"{mid}: cite [{n}] {cid} not found in companies/{tk}.json")
            fid = c.get("finding_id")
            if fid and c.get("ticker") in ctx.companies:
                f = ctx.finding(c["ticker"], fid)
                if f and nc_status(f) == "failed":
                    errors.append(f"{mid}: cites finding {fid} whose numeric check failed")
                if f and (f.get("impact") or {}).get("suspect"):
                    for b in m.get("blocks") or []:
                        for seg, _ in md_segments(b):
                            if money((f["impact"] or {}).get("dollars") or 0) in seg and f"[{n}]" in seg:
                                errors.append(f"{mid}: suspect impact printed as dollars for {fid}")
    return errors, warns, stats


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate memos.json files instead of writing them")
    ap.add_argument("--data", default=str(DATA), help="data directory (default ui/public/data)")
    ap.add_argument("--no-sample", action="store_true", help="skip the _sample fallback file")
    a = ap.parse_args(argv)
    data = Path(a.data)
    targets = [(data, data / "memos.json", False)]
    if not a.no_sample and (data / "_sample" / "meta.json").exists():
        targets.append((data / "_sample", data / "_sample" / "memos.json", True))
    rc = 0
    for ddir, out, sample in targets:
        ctx = Ctx(ddir, sample=sample)
        if a.check:
            errors, warns, stats = check(out, ctx)
            print(f"== {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
            print(f"memos {stats.get('memos')}, kinds {dict(stats.get('kinds', {}))}")
            print(f"prose words {stats.get('words')} (chat {stats.get('words_by_format', {}).get('chat')}, "
                  f"memo {stats.get('words_by_format', {}).get('memo')}); cites {stats.get('cites')} "
                  f"of which row cites {stats.get('row_cites')}")
            print(f"gated-number rule: every printed number must appear in a gated field of a cited finding, a cited "
                  f"data row, the product's gated cells, a math block or the decide numbers (a percent of a gated "
                  f"decimal counts); violations {stats.get('ungated', 0)}")
            print(f"plain-English rule: engine variable names and formula fragments only inside math blocks "
                  f"(ai_wrong table cells quote the error log verbatim and are exempt); violations {stats.get('var_tokens', 0)}")
            print(f"whitelist: {WHITELIST_NOTE}")
            for w in warns:
                print("warn:", w)
            for e in errors:
                print("ERROR:", e)
            print(f"{len(errors)} errors, {len(warns)} warnings")
            rc = rc or (1 if errors else 0)
        else:
            if sample:
                d = ctx.default
                ctx.tickers = [d] if d else []
                doc = build(ctx, kinds=["needle", "league", "ceo_memo"])
                doc["default_ticker_source"] = "pick"  # the sample fixture shows the company flow
                doc["suggested"] = [m["id"] for m in doc["memos"] if m["kind"] != "league"][:3]
            else:
                doc = build(ctx)
            size = write(out, doc)
            kinds = Counter(m["kind"] for m in doc["memos"])
            print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(doc['memos'])} memos, "
                  f"{size / 1e6:.2f} MB, kinds {dict(kinds)}, suggested {doc['suggested']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
