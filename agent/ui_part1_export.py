#!/usr/bin/env python3
"""ui_part1_export: copy the model session's Part 1 deliverable into the judge-facing UI data.

Contract: docs/ui_part1.md. Reads out/part1/ (selection.json, selection.md, <T>/part1.json, <T>/trace.jsonl; the
appendix is ignored) and writes ui/public/data/part1/ (index.json, selection.json, <T>.json, <T>_trace.json) with the
public withholding rule applied to every cite and the hard checks below. No model call, no network, no API key.

    PYTHONPATH=. python -m agent.ui_part1_export                  # export out/part1 -> ui/public/data/part1
    PYTHONPATH=. python -m agent.ui_part1_export --check          # validate ui/public/data/part1 (exit 1 on errors)
    PYTHONPATH=. python -m agent.ui_part1_export --check --sample # also validate ui/public/data/_sample/part1

Hard checks (export refuses to write, --check exits 1):
- no record carries numeric_check.status "failed" or "unchecked"; "passed" carries checked > 0 and the breakdown;
- every [n] marker (and every [derived: a, b] operand) in a *_marked field resolves to a cite on that record
  (through its marker_map when it has one, else by the cite's n); on export an unresolved marker is dropped and
  the number stays;
- no "Citation(" or "Claim(" substring; no pitch-forbidden words (the ui_memos --check list plus "league");
- the trace header's eight categories equal the contract's, verbatim and in order;
- selection.json sha256 equals sha256 of selection.md's text above its trailing "sha256:" line;
- withholding: licensed (Bloomberg) cites have no quote, excerpt or links; machine_data cites have no quote or
  excerpt (value and viewer_link kept); unverified cites have no quote, excerpt or links; number_match cites have
  no quote (excerpt kept);
- a killed trace candidate prints no digits (ungated figures are replaced by "[figure withheld: not gated]").
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

from agent.needle.cite.numbers import tokenize
from agent.ui_memos import MARK, PITCH_FORBIDDEN, VERBATIM

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "part1"
DATA = ROOT / "ui" / "public" / "data"
DEST = DATA / "part1"
SAMPLE_DEST = DATA / "_sample" / "part1"

CATEGORIES = [
    "Language drift",
    "Gross-to-net",
    "Inventory and receivables growing faster than revenue",
    "Segment and product table changes",
    "Footnotes",
    "Earnings-call Q&A",
    "Product fine print",
    "Peer contrast",
]
ROW_KEYS = ["approved uses", "boxed warnings and safety", "dosing and convenience",
            "patent and exclusivity timeline", "pricing and gross-to-net"]
PRICED_CALLS = ("priced in", "not priced in", "untestable")
VERDICTS = ("survived", "killed", "narrowed")
PROMPT = "find material, non-obvious findings about one company and compare one of its key products against its rivals."

PUBLIC_STATUSES = {"exact", "substring", "fuzzy", "number_match", "derived"}
NC_OK = ("passed", "no_numbers")
NC_KEYS = ("checked", "total", "verified", "derived", "assumed")
FORBIDDEN = re.compile(PITCH_FORBIDDEN.pattern + r"|\bleague\b", re.I)
REPR = re.compile(r"Citation\(|Claim\(")
LOST_DOLLAR = re.compile(r"[ (]\.\d")  # "(.4B": a "$2" eaten by shell expansion
# sealed text that may name the internal ranking (it says it did not read it) and the blind readers' ungated
# sizing: kept verbatim for the record, exempt from the pitch-word check, never printed as card prose
UNGATED_KEYS = {"selection_md", "reasons", "eliminated"}
UNGATED_NOTE = ("verbatim from the sealed selection.md; carries the blind readers' sizing, which the numeric gate has "
                "not passed, so the UI never prints it as prose (use the *_card text)")
CARD_FALLBACK = "Figures withheld: the reasoning is in the sealed selection record."
WITHHELD_FIGURE = "[figure withheld: not gated]"
LICENSED_REASON = "Bloomberg/licensed source: quote and links withheld from the public export"
MACHINE_REASON = "machine data, no page copy: quote withheld, value shown"


class ExportError(Exception):
    pass


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def read_jsonl(p):
    out = []
    for line in Path(p).read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- withholding
def vstatus(e):
    v = e.get("verification")
    if isinstance(v, dict):
        return v.get("status")
    if isinstance(v, str):
        return v
    return e.get("verify_status")


def withhold_kind(e):
    """None when the cite may show its quote; else 'licensed' | 'machine_data' | 'unverified' | 'number_match'."""
    if str(e.get("cite_id") or "").startswith("row:"):
        return None  # data-row cite: its quote is the row itself
    lic = str(e.get("license") or "").lower()
    st = vstatus(e)
    if "bloomberg" in lic or "licensed" in str(e.get("withheld_reason") or "").lower() or (lic and lic != "none"):
        return "licensed"
    if st == "machine_data" or "machine_data" in f"{e.get('doc_type') or ''}{e.get('raw_doc_type') or ''}":
        return "machine_data"
    if st not in PUBLIC_STATUSES or (e.get("withheld") and "machine data" not in str(e.get("withheld_reason") or "")):
        return "unverified"
    if st == "number_match":
        return "number_match"
    return None


def withhold(e):
    """A copy of one cite with the public rule applied (docs/citations.md, agent/ui_export.withhold_reason)."""
    e = copy.deepcopy(e)
    if e.get("numeric_check") is None:
        e.pop("numeric_check", None)
    kind = withhold_kind(e)
    if kind in ("licensed", "unverified"):
        e.update(quote=None, excerpt=None, url=None, deep_link=None, viewer_link=None, withheld=True)
        e["withheld_reason"] = e.get("withheld_reason") or (
            LICENSED_REASON if kind == "licensed" else f"citation status {vstatus(e) or 'missing'} is not public: quote and links withheld")
        if kind == "licensed":
            e["value"] = None
    elif kind == "machine_data":
        e.update(quote=None, excerpt=None, url=None, deep_link=None, withheld=True)
        e["withheld_reason"] = e.get("withheld_reason") or MACHINE_REASON
    elif kind == "number_match":
        e["quote"] = None
        e["quote_note"] = e.get("quote_note") or "the quote did not verify; the number is on the cited page"
    return e


def withhold_tree(obj):
    """Apply withhold() to every dict inside any 'cites' list, at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cites" and isinstance(v, list):
                obj[k] = [withhold(c) if isinstance(c, dict) else c for c in v]
            else:
                withhold_tree(v)
    elif isinstance(obj, list):
        for v in obj:
            withhold_tree(v)
    return obj


def reconcile_source(rec):
    """A finding's source quote shows only when a non-withheld verbatim cite on the record carries it."""
    src = rec.get("source")
    if not isinstance(src, dict) or not src.get("quote"):
        return
    ok = any(isinstance(c, dict) and not c.get("withheld") and vstatus(c) in VERBATIM and c.get("quote") == src["quote"]
             for c in rec.get("cites") or [])
    if not ok:
        src["quote"] = None
        src["url"] = None
        src["quote_note"] = "quote withheld under the public rule"


# ---------------------------------------------------------------- markers
def _resolver(ctx):
    """ctx = the nearest dict carrying 'cites'. Returns n -> bool."""
    if ctx is None:
        return lambda n: False
    cites = [c for c in ctx.get("cites") or [] if isinstance(c, dict)]
    ids = {c.get("cite_id") for c in cites}
    ns = {c.get("n") for c in cites}
    mm = ctx.get("marker_map") if isinstance(ctx.get("marker_map"), dict) else None
    if mm is not None:
        return lambda n: mm.get(str(n)) in ids and mm.get(str(n)) is not None
    return lambda n: n in ns


def fix_marked(text, ok, bad):
    """Drop [n] markers and derived operands that do not resolve; the number before them stays."""
    def sub(m):
        if m.group(1):
            n = int(m.group(1))
            if ok(n):
                return m.group(0)
            bad.append(n)
            return ""
        if m.group(2):
            keep = []
            for x in (x.strip() for x in m.group(2).split(",")):
                if x.isdigit():
                    if ok(int(x)):
                        keep.append(x)
                    else:
                        bad.append(int(x))
                elif x:
                    keep.append(x)
            return f"[derived: {', '.join(keep)}]" if keep else ""
        return m.group(0)
    return MARK.sub(sub, text)


def walk_marked(obj, fix=False, path="$", ctx=None, problems=None):
    """Check (and with fix=True repair) every *_marked string against its record's cites."""
    problems = [] if problems is None else problems
    if isinstance(obj, dict):
        here = obj if isinstance(obj.get("cites"), list) else ctx
        ok = _resolver(here)
        for k, v in list(obj.items()):
            if k.endswith("_marked") and isinstance(v, str):
                bad = []
                new = fix_marked(v, ok, bad)
                if bad:
                    problems.append(f"{path}.{k}: markers {sorted(set(bad))} do not resolve to a cite on the record")
                    if fix:
                        obj[k] = re.sub(r"\s{2,}", " ", new).strip()
            else:
                walk_marked(v, fix, f"{path}.{k}", here, problems)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_marked(v, fix, f"{path}[{i}]", ctx, problems)
    return problems


def strip_ungated_numbers(text):
    """Replace every digit-bearing token with the withheld placeholder (a killed candidate was never gated)."""
    if not text:
        return text
    text = text.replace(WITHHELD_FIGURE, "\0")
    tok = re.compile(r"[^\s()\[\]{}\"']*\d[^\s()\[\]{}\"']*")

    def sub(m):
        s = m.group(0)
        tail = re.search(r"[.,;:!?]+$", s)
        return "\0" + (tail.group(0) if tail else "")
    out = tok.sub(sub, text)
    out = re.sub(r"\0(?:\s*(?:,|->|to|vs\.?|and|or|-)?\s*\0)+", "\0", out)
    return out.replace("\0", WITHHELD_FIGURE)


# ---------------------------------------------------------------- generic asserts
def numeric_problems(obj, path="$", out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        if "numeric_check" in obj:
            nc = obj["numeric_check"]
            if not isinstance(nc, dict) or nc.get("status") not in NC_OK:
                out.append(f"{path}.numeric_check status {(nc or {}).get('status') if isinstance(nc, dict) else nc!r} is not written")
            elif nc["status"] == "passed" and (not nc.get("checked") or any(k not in nc for k in NC_KEYS)):
                out.append(f"{path}.numeric_check says passed without a checked count or the breakdown")
            elif nc["status"] == "no_numbers" and (nc.get("total") or nc.get("checked") or nc.get("unsupported")):
                out.append(f"{path}.numeric_check says no_numbers but counts numbers")
        for k, v in obj.items():
            numeric_problems(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            numeric_problems(v, f"{path}[{i}]", out)
    return out


def text_problems(obj, path="$", out=None, sealed=False):
    """repr strings and lost dollar signs anywhere; pitch words anywhere except the sealed, ungated record text."""
    out = [] if out is None else out
    if isinstance(obj, str):
        if REPR.search(obj):
            out.append(f"{path} carries a repr string: {obj[:60]}")
        m = LOST_DOLLAR.search(obj)
        if m:
            out.append(f"{path} has '{obj[max(0, m.start() - 12):m.end() + 8]}': probable lost dollar sign")
        m = None if sealed else FORBIDDEN.search(obj)
        if m:
            out.append(f"{path} carries the pitch-forbidden word '{m.group(0)}'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            text_problems(v, f"{path}.{k}", out, sealed or (path == "$" and k in UNGATED_KEYS))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            text_problems(v, f"{path}[{i}]", out, sealed)
    return out


def withhold_problems(obj, path="$", out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cites" and isinstance(v, list):
                for i, c in enumerate(v):
                    if not isinstance(c, dict):
                        continue
                    p, kind = f"{path}.cites[{i}]", withhold_kind(c)
                    if kind in ("licensed", "unverified") and any(c.get(x) for x in ("quote", "excerpt", "url", "deep_link", "viewer_link")):
                        out.append(f"{p}: {kind} cite carries quote, excerpt or links")
                    if kind == "machine_data" and any(c.get(x) for x in ("quote", "excerpt", "url", "deep_link")):
                        out.append(f"{p}: machine_data cite carries a quote, excerpt or link")
                    if kind == "number_match" and c.get("quote"):
                        out.append(f"{p}: number_match cite shows a quote")
            else:
                withhold_problems(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            withhold_problems(v, f"{path}[{i}]", out)
    return out


# ---------------------------------------------------------------- selection
def split_selection_md(md):
    """(text above the trailing 'sha256:' line, the hex on it) or (md, None)."""
    lines = md.splitlines(keepends=True)
    for i in range(len(lines) - 1, -1, -1):
        if not lines[i].strip():
            continue
        m = re.match(r"^\s*sha256:\s*([0-9a-fA-F]{64})\s*$", lines[i])
        return ("".join(lines[:i]), m.group(1).lower()) if m else (md, None)
    return md, None


def sha_ok(text, sha):
    """The hash covers the text above the line with trailing newlines stripped (one trailing newline is also accepted)."""
    cands = {text.rstrip("\n"), text.rstrip("\n") + "\n"}
    return any(hashlib.sha256(c.encode("utf-8")).hexdigest() == (sha or "").lower() for c in cands)


def parse_selection_md(text):
    """({T: pick paragraph}, {T: eliminated line}, {T: name}) from '## Picks' / '### N. T (Name)' and '## Eliminated' / '- T: ...'."""
    picks, elim, names, section, cur = {}, {}, {}, None, None
    for line in text.splitlines():
        h2 = re.match(r"^##\s+(.+?)\s*$", line)
        if h2 and not line.startswith("###"):
            section, cur = h2.group(1).strip().lower(), None
            continue
        if section == "picks":
            h3 = re.match(r"^###\s+\d+\.\s+([A-Z]{1,5})\b\s*(?:\((.*)\))?", line)
            if h3:
                cur = h3.group(1)
                names[cur] = h3.group(2)
                picks[cur] = []
            elif cur and line.strip():
                picks[cur].append(line.strip())
        elif section == "eliminated":
            b = re.match(r"^\s*[-*]\s+([A-Z]{1,5}):\s*(.+)$", line)
            if b:
                cur = b.group(1)
                elim[cur] = b.group(2).strip()
            elif cur and line.strip():
                elim[cur] += " " + line.strip()
    return {t: " ".join(v) for t, v in picks.items()}, elim, names


ROW_COUNT = re.compile(r"\b\d+\s*-?\s*(?:rows?|survivors?)\b", re.I)
FORM_PLURAL = re.compile(r"\b(?:10-K|10-Q|20-F|8-K|6-K)s\b")


def figures(text):
    """Gate-eligible figures in text: the engine tokenizer's numbers (years, dates, period labels, form names, page
    numbers and ids glued to letters such as AMGN-c06 are exempt there), with row and survivor counts and plural
    form names ('10-Qs') also exempt."""
    t = ROW_COUNT.sub(lambda m: " " * len(m.group(0)), text or "")
    t = FORM_PLURAL.sub(lambda m: m.group(0)[:-1] + " ", t)
    return [x for x in tokenize(t) if x.kind == "number"]


def _drop_figure_parens(text):
    """Remove parenthetical groups (innermost first) that hold a figure; groups without one are kept."""
    keep = []
    while True:
        m = re.search(r"\([^()]*\)", text)
        if not m:
            break
        grp = m.group(0)
        if figures(grp):
            text = text[:m.start()].rstrip() + text[m.end():]
        else:
            keep.append(grp)
            text = text[:m.start()] + f"\x01{len(keep) - 1}\x02" + text[m.end():]
    return re.sub(r"\x01(\d+)\x02", lambda m: keep[int(m.group(1))], text)


ABBREV = re.compile(r"(?:\b(?:[A-Z]\.){1,3}|\b(?:vs|e\.g|i\.e|Inc|No|Co|Corp|Ltd|approx|est|St|Dr|Mr|Ms)\.)$")


def _sentences(text):
    """Sentence split that does not break after U.S., vs., Inc. and similar."""
    out, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z\"'])", text.strip()):
        head = text.strip()[start:m.start()]
        if ABBREV.search(head):
            continue
        out.append(head)
        start = m.end()
    out.append(text.strip()[start:])
    return [x for x in out if x.strip()]


def _tidy(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,;:.!?)])", r"\1", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"([,;:])\s*([,;:.])", r"\2", text)
    text = re.sub(r"[,;:]\s*$", "", text.strip())
    text = re.sub(r"^(?:and|but|while|with|so|or)\s+", "", text.strip(), flags=re.I)
    return text.strip()


DANGLING = {"a", "an", "the", "of", "to", "and", "or", "with", "plus", "cited", "at", "from", "by", "for", "as",
            "than", "about", "such", "in", "on", "is", "are", "was", "were"}
JOINER = re.compile(r"^\s*(?:and|but|while|so|though|although|yet)\b")
APPOSITIVE = re.compile(r"^\s*(?:a|an|the|which|who|whose|that|this|these|its)\b")


def _strip_sentence(sent, min_words=6):
    """One sentence without figures, or '' when what is left would not read: a sentence whose kept text before the
    first dropped clause is under six words, or ends on a dangling word, is dropped whole; a kept clause right after
    a dropped one that only continues it (starts with a, the, which, ...) is dropped too, and so is every clause
    after it until one opens with a joiner (and, but, while, so, though, yet)."""
    s = _drop_figure_parens(sent)
    keep = []
    s = re.sub(r"\([^()]*\)", lambda m: (keep.append(m.group(0)), f"\x01{len(keep) - 1}\x02")[1], s)
    end = "." if s.rstrip().endswith((".", "!", "?")) else ""
    body = s.rstrip().rstrip(".!?")
    parts = re.split(r"([;,])", body)
    out, gap, seen_gap, cont = [], False, False, False
    for i in range(0, len(parts), 2):
        clause = parts[i]
        restored = re.sub(r"\x01(\d+)\x02", lambda m: keep[int(m.group(1))], clause)
        if not clause.strip():
            continue
        if cont and not JOINER.match(clause):
            continue
        cont = False
        if figures(restored) or (gap and APPOSITIVE.match(clause)):
            if not seen_gap:
                before = re.sub(r"\x01\d+\x02", "", "".join(out))
                words = re.findall(r"[\w'-]+", before)
                if len(words) < min_words or (words and words[-1].lower() in DANGLING):
                    return ""
            if gap and APPOSITIVE.match(clause):
                cont = True
            gap = seen_gap = True
            continue
        if out:
            out.append(parts[i - 1] if i > 0 else ",")
        out.append(clause)
        gap = False
    if seen_gap and out:
        words = re.findall(r"[\w'-]+", re.sub(r"\x01\d+\x02", "", "".join(out)))
        if words and words[-1].lower() in DANGLING:
            return ""
    text = re.sub(r"\x01(\d+)\x02", lambda m: keep[int(m.group(1))], "".join(out))
    text = _tidy(text)
    if seen_gap and ":" in text:  # a colon left introducing only a stub: cut at the colon
        head, _, tail = text.rpartition(":")
        if len(re.findall(r"[\w'-]+", tail)) < 6 and len(re.findall(r"[\w'-]+", head)) >= 3:
            text = head.strip()
    if not text or not re.search(r"[A-Za-z]{3}", text):
        return ""
    return text[0].upper() + text[1:] + (end or ".")


def card_text(paragraph, fallback=True):
    """The paragraph with every figure removed in a way that still reads: parenthetical groups holding a figure go
    first, then any clause (split on ';' and ',') that still holds one; a paragraph that loses everything falls back
    to its first and last sentences stripped the same way (short kept openings allowed), then to a fixed note."""
    sents = _sentences(paragraph or "")
    out = [x for x in (_strip_sentence(s) for s in sents) if x]
    if not out and fallback and sents:
        ends = list(dict.fromkeys([sents[0], sents[-1]]))
        out = [x for x in (_strip_sentence(s, min_words=1) for s in ends) if x]
    text = " ".join(out) or (CARD_FALLBACK if fallback else "")
    if figures(text):
        raise ExportError(f"card text still carries a figure: {text[:80]}")
    return text


def build_selection(sel, md_text=None, sealed_doc_path="part1/selection.md"):
    """selection.json for the UI: picked, sealed_at and sha256 from selection.json; reasons and eliminated verbatim
    from the sealed selection.md (marked ungated), plus figure-free card text."""
    sel = copy.deepcopy(sel)
    if md_text is not None:
        above, line_sha = split_selection_md(md_text)
        if line_sha is None:
            raise ExportError("selection.md has no trailing 'sha256:' line")
        if line_sha != str(sel.get("sha256") or "").lower():
            raise ExportError("selection.md hash line differs from selection.json sha256")
        sel["selection_md"] = above
        picks, elim, names = parse_selection_md(above)
        missing = [t for t in sel.get("picked") or [] if t not in picks]
        if missing:
            raise ExportError(f"selection.md has no '### N. T' paragraph under '## Picks' for {missing}")
        if picks:
            sel["reasons"] = picks
            sel["eliminated"] = elim
        if names:
            sel["names"] = names
        sel["sealed_doc_path"] = sealed_doc_path
    if not sha_ok(sel.get("selection_md") or "", sel.get("sha256")):
        raise ExportError("selection.json sha256 is not the sha256 of selection.md above its hash line")
    sel["reasons_card"] = {t: card_text(v) for t, v in (sel.get("reasons") or {}).items()}
    sel["eliminated_card"] = {t: card_text(v) for t, v in (sel.get("eliminated") or {}).items()}
    sel["reasons_note"] = {"ungated": True, "note": UNGATED_NOTE}
    sel["eliminated_note"] = {"ungated": True, "note": UNGATED_NOTE}
    withhold_tree(sel)
    walk_marked(sel, fix=True)
    return sel


def selection_problems(sel):
    errs = []
    for k in ("picked", "reasons", "eliminated", "sealed_at", "sha256", "selection_md", "reasons_card",
              "eliminated_card", "reasons_note", "eliminated_note", "sealed_doc_path"):
        if k not in sel:
            errs.append(f"selection.json missing {k}")
    picked = sel.get("picked") or []
    if not (isinstance(picked, list) and 1 <= len(picked) <= 3):
        errs.append("selection.picked must list one to three tickers")
    for t in picked:
        if t not in (sel.get("reasons") or {}):
            errs.append(f"selection.reasons has no entry for {t}")
        if not (sel.get("reasons_card") or {}).get(t):
            errs.append(f"selection.reasons_card has no text for {t}")
    for k in ("reasons_card", "eliminated_card"):
        for t, v in (sel.get(k) or {}).items():
            if figures(v):
                errs.append(f"selection.{k}.{t} prints figures {[x.raw for x in figures(v)]}")
        if set(sel.get(k) or {}) != set(sel.get(k.replace("_card", "")) or {}):
            errs.append(f"selection.{k} tickers differ from {k.replace('_card', '')}")
    for k in ("reasons_note", "eliminated_note"):
        if (sel.get(k) or {}).get("ungated") is not True:
            errs.append(f"selection.{k} must carry ungated: true")
    if not sha_ok(sel.get("selection_md") or "", sel.get("sha256")):
        errs.append("selection.json sha256 does not match selection_md")
    return errs


# ---------------------------------------------------------------- company record
CONTRACT_TOP = {"ticker", "name", "findings", "sharpest_needle", "product_table", "sample", "rank_basis", "generated_at"}
# top-level keys the writers add that carry ungated sizing: dropped from the public record (finding-level `derived`
# is kept); any other unknown top-level key fails the checks
DROP_TOP = {"company_score", "not_sourced", "dash_note", "notes", "assumptions", "derived"}


def _norm_words(s, drop_possessor=True):
    s = re.sub(r"\([^()]*\)", " ", s or "")
    if drop_possessor:
        s = re.sub(r"\b[\w-]+['\u2019]s\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).split()


def _col_matches(name, key):
    """Normalized containment either way: the cell key's words all appear in the column name (parentheticals
    included), or the column name's first brand word appears in the key."""
    kw = set(_norm_words(key))
    full = set(re.sub(r"[^a-z0-9]+", " ", re.sub(r"\b[\w-]+['\u2019]s\b", " ", (name or "").lower())).split())
    if kw and kw <= full:
        return True
    nw = _norm_words(name)
    return bool(nw) and nw[0] in kw


def _short_label(name):
    words = re.sub(r"\([^()]*\)", " ", name or "")
    words = re.sub(r"\b[\w-]+['\u2019]s\s+", "", words)
    return re.sub(r"\s+", " ", words).strip() or name


def resolve_columns(pt):
    """[{key, label, full}] mapping the product, then each rival in order, to the cell key the rows use. Columns are
    matched by name; when that fails and every row has exactly len(rivals) + 1 cells, by position. Raises
    ExportError when a row cannot be resolved."""
    names = [pt.get("product")] + list(pt.get("rivals") or [])
    rows = [r for r in pt.get("rows") or [] if isinstance(r, dict)]
    if all(all(nm in (r.get("cells") or {}) for nm in names) for r in rows):
        return [{"key": nm, "label": _short_label(nm), "full": nm} for nm in names]
    keys = list(dict.fromkeys(k for r in rows for k in (r.get("cells") or {})))
    cols, used = [], set()
    for nm in names:
        hits = [k for k in keys if k not in used and (k == nm or _col_matches(nm, k))]
        if len(hits) != 1:
            cols = None
            break
        used.add(hits[0])
        cols.append({"key": hits[0], "label": hits[0], "full": nm})
    if cols is None or any(any(c["key"] not in (r.get("cells") or {}) for c in cols) for r in rows):
        if rows and all(len(r.get("cells") or {}) == len(names) for r in rows) and \
                all(list(r.get("cells")) == list(rows[0].get("cells")) for r in rows):
            cols = [{"key": k, "label": k, "full": nm} for k, nm in zip(rows[0]["cells"], names)]
        else:
            bad = [r.get("row") for r in rows if cols is None or any(c["key"] not in (r.get("cells") or {}) for c in cols)]
            raise ExportError(f"product_table rows {bad} cannot be matched to the product and rivals {names}")
    return cols


def build_company(rec):
    rec = copy.deepcopy(rec)
    for k in DROP_TOP:
        rec.pop(k, None)
    pt = rec.get("product_table")
    if isinstance(pt, dict) and pt.get("rows"):
        pt["columns"] = resolve_columns(pt)
    withhold_tree(rec)
    for f in rec.get("findings") or []:
        reconcile_source(f)
        if "verdict" not in f:
            f["verdict_inferred"] = ("on_the_record" if f.get("obviousness") == "high" and f.get("on_the_record")
                                     else "narrowed")
    walk_marked(rec, fix=True)
    gate_priced_evidence(rec)
    return rec


SMALL_COUNT = 12


def _small_count(tok):
    return tok.unit == "" and not tok.currency and tok.scale is None and not tok.neg and tok.decimals == 0 \
        and tok.num <= SMALL_COUNT


def gate_priced_evidence(rec):
    """priced_in.evidence[].finding carries no numeric check of its own: figures outside the company's gated set
    (which includes the passed priced_in.text) are withheld; plain counts up to twelve, quarters, years and dates
    stay. I/B/E/S machine-data cites show direction only (no value)."""
    pi = (rec.get("product_table") or {}).get("priced_in")
    if not isinstance(pi, dict):
        return
    for c in pi.get("cites") or []:
        if isinstance(c, dict) and withhold_kind(c) == "machine_data" and not str(c.get("cite_id")).startswith("gdelt:"):
            c["value"] = None
            c["shown"] = "direction only"
    have = {c.get("cite_id") for c in pi.get("cites") or [] if isinstance(c, dict)}
    for e in pi.get("evidence") or []:
        for cid in (e.get("cites") or []) if isinstance(e, dict) else []:
            if isinstance(cid, str) and cid.startswith("gdelt:") and cid not in have:
                pi.setdefault("cites", []).append(gdelt_cite(cid))
                have.add(cid)
    gated = gated_figures(rec)
    for e in pi.get("evidence") or []:
        if not isinstance(e, dict):
            continue
        n = 0
        for k in ("finding", "source"):
            if isinstance(e.get(k), str):
                e[k], m = withhold_ungated(e[k], gated, keep=_small_count)
                n += m
        e["figures_withheld"] = n


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def gdelt_cite(cid):
    """A row-style, withheld machine-data cite for a GDELT press-mention series id (no evidence object exists)."""
    m = re.search(r"(\d{4})(\d{2})$", cid)
    period = f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m and 1 <= int(m.group(2)) <= 12 else None
    return {"cite_id": cid, "doc_title": "GDELT press-attention series", "period": period, "page": None,
            "quote": None, "excerpt": None, "url": None, "deep_link": None, "viewer_link": None, "value": None,
            "withheld": True, "withheld_reason": "machine data: press-mention count series",
            "verification": {"status": "machine_data"}, "ref": cid, "shown": "count only"}


def priced_evidence_problems(rec, t):
    errs = []
    pi = (rec.get("product_table") or {}).get("priced_in") or {}
    gated = gated_figures(rec)
    ids = {c.get("cite_id"): c for c in pi.get("cites") or [] if isinstance(c, dict)}
    for c in ids.values():
        if withhold_kind(c) == "machine_data" and c.get("value") not in (None, ""):
            errs.append(f"{t}.priced_in cite {c.get('cite_id')}: machine-data (I/B/E/S) cite shows a value, not direction only")
    for i, e in enumerate(pi.get("evidence") or []):
        p = f"{t}.priced_in.evidence[{i}]"
        if not isinstance(e, dict):
            errs.append(f"{p} is not a record")
            continue
        for k in ("finding", "source"):
            v = e.get(k)
            if isinstance(v, str):
                bad = [x.raw for x in figures(v) if fig_key(x) not in gated and not _small_count(x)]
                if bad:
                    errs.append(f"{p}.{k} prints figures the gate did not pass: {bad[:4]}")
                if re.search(re.escape(WITHHELD_FIGURE) + r"[\s,;/-]*" + re.escape(WITHHELD_FIGURE), v):
                    errs.append(f"{p}.{k} shows two withheld markers in a row")
        if "figures_withheld" not in e:
            errs.append(f"{p} carries no figures_withheld count")
        for cid in e.get("cites") or []:
            if isinstance(cid, dict):
                continue  # an inline cite object: checked by the withholding walk
            if cid not in ids:
                errs.append(f"{p} cite {cid} does not resolve to a cite on priced_in")
    return errs


def company_problems(rec, t, sample=False):
    errs, warns = [], []
    if rec.get("ticker") != t:
        errs.append(f"{t}.json ticker is {rec.get('ticker')}")
    fs = rec.get("findings") or []
    if len(fs) < 5:
        warns.append(f"{t}: {len(fs)} findings (the case asks for at least five)")
    ns = set()
    for i, f in enumerate(fs):
        p = f"{t}.findings[{i}]"
        for k in ("n", "finding", "finding_marked", "marker_map", "source", "cites", "impact", "peer", "confidence"):
            if k not in f:
                errs.append(f"{p} missing {k}")
        ns.add(f.get("n"))
        if f.get("confidence") not in ("high", "medium", "low"):
            errs.append(f"{p}.confidence {f.get('confidence')!r}")
        imp = f.get("impact") or {}
        if not isinstance(imp.get("numeric_check"), dict):
            errs.append(f"{p}.impact.numeric_check missing")
        for k, cid in (f.get("marker_map") or {}).items():
            if cid not in {c.get("cite_id") for c in f.get("cites") or []}:
                errs.append(f"{p}.marker_map[{k}] -> {cid} is not a cite on the record")
    sn = rec.get("sharpest_needle") or {}
    if sn.get("finding_n") not in ns:
        errs.append(f"{t}.sharpest_needle.finding_n {sn.get('finding_n')} is not a finding")
    pt = rec.get("product_table") or {}
    rows = pt.get("rows") or []
    if [r.get("row") for r in rows] != ROW_KEYS:
        errs.append(f"{t}.product_table rows {[r.get('row') for r in rows]} != the five case rows in order")
    cols = pt.get("columns")
    names = [pt.get("product")] + list(pt.get("rivals") or [])
    if not isinstance(cols, list) or [c.get("full") for c in cols] != names:
        errs.append(f"{t}.product_table.columns must map the product and each rival, in order")
        cols = [{"key": nm} for nm in names]
    for r in rows:
        for c in cols:
            if c.get("key") not in (r.get("cells") or {}):
                errs.append(f"{t}.product_table row '{r.get('row')}' has no cell for column {c.get('key')}")
    errs += priced_evidence_problems(rec, t)
    extra = sorted(set(rec) - CONTRACT_TOP)
    if extra:
        errs.append(f"{t}.json carries top-level keys outside the contract: {extra}")
    for k in ("financial_tie", "growth_limiter", "priced_in"):
        if not isinstance(pt.get(k), dict):
            errs.append(f"{t}.product_table.{k} missing")
    if (pt.get("priced_in") or {}).get("call") not in PRICED_CALLS:
        errs.append(f"{t}.product_table.priced_in.call {(pt.get('priced_in') or {}).get('call')!r}")
    return errs, warns


# ---------------------------------------------------------------- trace
# ---------------------------------------------------------------- gated figures (trace text)
TRACE_TEXT_FIELDS = ("query", "verdict_reason")
GATED_CELL_STATUS = ("passed", "cited")


def fig_key(tok):
    """A figure's identity for the gated set: value with its inline scale, and its unit (currency ignored)."""
    return (round(tok.num * (tok.scale or 1.0), 6), tok.unit)


def _nc_passed(x):
    return isinstance(x, dict) and x.get("status") == "passed"


def gated_figures(rec):
    """Every figure in a company record's text whose numeric check passed: finding sentence, impact text and math,
    peer (finding impact.numeric_check passed); product cells with status passed (or cited, the fixture's word);
    financial_tie text and math, growth_limiter sentence (their numeric_check passed), priced_in text."""
    texts = []
    for f in rec.get("findings") or []:
        if _nc_passed((f.get("impact") or {}).get("numeric_check")) or _nc_passed(f.get("numeric_check")):
            imp = f.get("impact") or {}
            texts += [f.get("finding"), MARK.sub("", f.get("finding_marked") or ""), imp.get("text"), imp.get("math"),
                      f.get("peer")]
    pt = rec.get("product_table") or {}
    for r in pt.get("rows") or []:
        for c in (r.get("cells") or {}).values():
            if isinstance(c, dict) and (c.get("status") in GATED_CELL_STATUS or _nc_passed(c.get("numeric_check"))):
                texts.append(c.get("text"))
    ft = pt.get("financial_tie") or {}
    if _nc_passed(ft.get("numeric_check")) or _nc_passed(ft.get("math_numeric_check")):
        texts += [ft.get("text"), ft.get("math")]
    gl = pt.get("growth_limiter") or {}
    if _nc_passed(gl.get("numeric_check")):
        texts.append(gl.get("sentence"))
    texts.append((pt.get("priced_in") or {}).get("text"))
    out = set()
    for t in texts:
        if isinstance(t, str):
            out.update(fig_key(x) for x in figures(t))
    return out


def _collapse(text):
    sep = r"(?:\s*(?:,|;|->|/|-|to|vs\.?|and|or|from)?\s*)"
    return re.sub(re.escape(WITHHELD_FIGURE) + "(?:" + sep + re.escape(WITHHELD_FIGURE) + ")+", WITHHELD_FIGURE, text)


def withhold_ungated(text, gated, keep=None):
    """(text, n): every figure not in the gated set replaced by the withheld placeholder (a leading ~ or 'about'
    sign goes with it), runs collapsed so two placeholders never stand together."""
    if not isinstance(text, str) or not text:
        return text, 0
    toks = [x for x in figures(text) if fig_key(x) not in gated and not (keep and keep(x))]
    if not toks:
        return text, 0
    for x in sorted(toks, key=lambda x: x.start, reverse=True):
        a = x.start
        while a > 0 and text[a - 1] in "~\u2248":
            a -= 1
        text = text[:a] + WITHHELD_FIGURE + text[x.end:]
    return _collapse(text), len(toks)


def strip_killed(text, gated):
    """Killed candidates keep the stricter rule: every digit-bearing chunk goes unless all its figures are gated."""
    if not text:
        return text, 0
    n = 0
    text = text.replace(WITHHELD_FIGURE, "\0")
    tok = re.compile(r"[^\s()\[\]{}\"']*\d[^\s()\[\]{}\"']*")
    toks = figures(text)  # read on the whole text so units after a space ("20 points") count
    bad = [(x.start, x.end) for x in toks if fig_key(x) not in gated]
    good = [(x.start, x.end) for x in toks if fig_key(x) in gated]

    def sub(m):
        nonlocal n
        chunk, a, b = m.group(0), m.start(), m.end()
        over = lambda spans: any(x < b and y > a for x, y in spans)
        if over(good) and not over(bad):
            return chunk
        n += 1
        tail = re.search(r"[.,;:!?]+$", chunk)
        return "\0" + (tail.group(0) if tail else "")
    out = tok.sub(sub, text)
    out = re.sub(r"\0(?:\s*(?:,|->|to|vs\.?|and|or|-)?\s*\0)+", "\0", out)
    return out.replace("\0", WITHHELD_FIGURE), n


def _skeptic_strings(obj, fn):
    """Apply fn to every string inside a skeptic record; returns (new obj, count)."""
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, dict):
        n, out = 0, {}
        for k, v in obj.items():
            out[k], m = _skeptic_strings(v, fn)
            n += m
        return out, n
    if isinstance(obj, list):
        n, out = 0, []
        for v in obj:
            nv, m = _skeptic_strings(v, fn)
            out.append(nv)
            n += m
        return out, n
    return obj, 0


def gate_step_text(s, gated):
    """Withhold ungated figures in every trace text field of one step; sets figures_withheld."""
    n = 0
    fn = lambda x: withhold_ungated(x, gated)
    cand = s.get("candidate") or {}
    if isinstance(cand.get("text"), str):
        if s.get("verdict") == "killed":
            cand["text"], m = strip_killed(cand["text"], gated)
        else:
            cand["text"], m = fn(cand["text"])
        n += m
    for k in TRACE_TEXT_FIELDS:
        if isinstance(s.get(k), str):
            s[k], m = fn(s[k])
            n += m
    for k in ("skeptic_materiality", "skeptic_obviousness"):
        if s.get(k) is not None:
            s[k], m = _skeptic_strings(s[k], fn)
            n += m
    s["figures_withheld"] = n
    return s


def step_text_problems(s, gated, p):
    errs = []

    def chk(text, where):
        if not isinstance(text, str):
            return
        bad = [x.raw for x in figures(text) if fig_key(x) not in gated]
        if bad:
            errs.append(f"{p}.{where} prints figures the gate did not pass: {bad[:4]}")
        if re.search(re.escape(WITHHELD_FIGURE) + r"[\s,;/-]*" + re.escape(WITHHELD_FIGURE), text):
            errs.append(f"{p}.{where} shows two withheld markers in a row")
    chk((s.get("candidate") or {}).get("text"), "candidate.text")
    for k in TRACE_TEXT_FIELDS:
        chk(s.get(k), k)
    for k in ("skeptic_materiality", "skeptic_obviousness"):
        _skeptic_strings(s.get(k), lambda x, k=k: (chk(x, k), (x, 0))[1])
    if "figures_withheld" not in s:
        errs.append(f"{p} carries no figures_withheld count")
    return errs


def build_trace(lines, ticker=None, gated=frozenset()):
    if not lines:
        raise ExportError(f"{ticker}: trace is empty")
    header = copy.deepcopy(lines[0])
    if header.get("category") != "header" or header.get("step") not in (0, "0"):
        raise ExportError(f"{ticker}: trace line 1 is not the header")
    if header.get("categories") != CATEGORIES:
        raise ExportError(f"{ticker}: trace header categories differ from the contract's eight, verbatim and in order")
    steps = []
    for i, s in enumerate(lines[1:]):
        s = copy.deepcopy(s)
        if s.get("category") not in CATEGORIES:
            raise ExportError(f"{ticker}: step {s.get('step')} category {s.get('category')!r} is not one of the eight")
        if s.get("verdict") not in VERDICTS:
            raise ExportError(f"{ticker}: step {s.get('step')} verdict {s.get('verdict')!r}")
        seen, docs = set(), []
        for d in s.get("documents") or []:
            key = (d.get("doc_id"), str(d.get("page")) if d.get("page") is not None else None)
            if key not in seen:
                seen.add(key)
                docs.append(d)
        s["documents"] = docs
        cand = s.get("candidate") if isinstance(s.get("candidate"), dict) else {"text": s.get("candidate")}
        s["candidate"] = cand
        gate_step_text(s, gated)
        s["_i"] = i
        steps.append(s)
    steps.sort(key=lambda s: (CATEGORIES.index(s["category"]), s["_i"]))
    for s in steps:
        s.pop("_i", None)
    withhold_tree(steps)
    walk_marked(steps, fix=True)
    return {"header": header, "steps": steps, "summary": trace_summary(steps)}


def trace_summary(steps):
    return {"candidates": len(steps),
            "survived": sum(s.get("verdict") == "survived" for s in steps),
            "killed": sum(s.get("verdict") == "killed" for s in steps),
            "narrowed": sum(s.get("verdict") == "narrowed" for s in steps),
            "documents": len({d.get("doc_id") for s in steps for d in s.get("documents") or [] if d.get("doc_id")})}


def trace_problems(tr, t, sample=False, gated=frozenset()):
    errs = []
    h = tr.get("header") or {}
    if h.get("categories") != CATEGORIES:
        errs.append(f"{t}_trace header categories differ from the contract's eight")
    if h.get("ticker") != t:
        errs.append(f"{t}_trace header ticker {h.get('ticker')}")
    steps = tr.get("steps") or []
    order = [CATEGORIES.index(s.get("category")) if s.get("category") in CATEGORIES else -1 for s in steps]
    if -1 in order:
        errs.append(f"{t}_trace has a step outside the eight categories")
    elif order != sorted(order):
        errs.append(f"{t}_trace steps are not grouped in the contract's category order")
    for s in steps:
        p = f"{t}_trace step {s.get('step')}"
        if s.get("verdict") not in VERDICTS:
            errs.append(f"{p} verdict {s.get('verdict')!r}")
        for k in ("query", "documents", "candidate", "skeptic_materiality", "skeptic_obviousness", "verdict_reason"):
            if k not in s:
                errs.append(f"{p} missing {k}")
        if not sample:
            for k in ("skeptic_materiality", "skeptic_obviousness"):
                if not isinstance(s.get(k), dict):
                    errs.append(f"{p}.{k} is not a {{round1, round2}} record")
        keys = [(d.get("doc_id"), str(d.get("page"))) for d in s.get("documents") or []]
        if len(keys) != len(set(keys)):
            errs.append(f"{p} documents are not deduplicated")
        if s.get("verdict") == "killed":
            left = ((s.get("candidate") or {}).get("text") or "").replace(WITHHELD_FIGURE, "")
            for chunk in re.findall(r"[^\s()\[\]{}\"']*\d[^\s()\[\]{}\"']*", left):
                figs = figures(chunk)
                if not figs or not all(fig_key(x) in gated for x in figs):
                    errs.append(f"{p} killed candidate prints an ungated number: {chunk}")
                    break
        errs += step_text_problems(s, gated, p)
    if tr.get("summary") != trace_summary(steps):
        errs.append(f"{t}_trace summary {tr.get('summary')} != recomputed {trace_summary(steps)}")
    return errs


# ---------------------------------------------------------------- whole-directory check
def check_dir(d, sample=False):
    d = Path(d)
    errs, warns = [], []
    idx = read_json(d / "index.json")
    if not idx:
        return [f"{d}/index.json missing or unreadable"], warns
    if bool(idx.get("sample")) != sample:
        errs.append(f"{d}/index.json sample is {idx.get('sample')}, expected {sample}")
    if sample and not idx.get("sample_note"):
        errs.append(f"{d}/index.json carries no sample_note")
    sel = read_json(d / "selection.json")
    if not sel:
        errs.append(f"{d}/selection.json missing")
        sel = {}
    errs += selection_problems(sel)
    if idx.get("picked") != sel.get("picked"):
        errs.append("index.picked differs from selection.picked")
    sealed = idx.get("sealed") or {}
    if sealed.get("sha256") != sel.get("sha256") or sealed.get("sealed_at") != sel.get("sealed_at"):
        errs.append("index.sealed differs from selection sha256 / sealed_at")
    sdp = str(sel.get("sealed_doc_path") or "")
    doc = d / Path(sdp).name if sdp.endswith("part1/selection.md") else None
    if doc is None or not doc.is_file():
        errs.append(f"sealed document {sel.get('sealed_doc_path')} is not published next to selection.json")
    else:
        above, line_sha = split_selection_md(doc.read_text())
        if line_sha != sel.get("sha256") or not sha_ok(above, sel.get("sha256")):
            errs.append(f"{doc} does not verify against the sealed sha256")
        if above != sel.get("selection_md"):
            errs.append(f"{doc} differs from selection.json selection_md")
    if not sample and OUT.joinpath("selection.md").exists() and doc is not None and doc.is_file():
        if OUT.joinpath("selection.md").read_text() != doc.read_text():
            errs.append("the published selection.md is not a verbatim copy of out/part1/selection.md: re-export")
    avail, missing = idx.get("available"), idx.get("missing")
    if not isinstance(avail, list) or not isinstance(missing, list):
        errs.append("index.json must carry available and missing lists")
        avail, missing = list(idx.get("tickers") or []), []
    for t in idx.get("picked") or []:
        listed = [m.get("ticker") for m in missing if isinstance(m, dict)]
        if (t in avail) == (t in listed):
            errs.append(f"picked {t} must be in exactly one of available and missing")
    for m in missing:
        if not isinstance(m, dict) or not m.get("reason"):
            errs.append(f"index.missing entry {m!r} carries no reason")
    files = {"selection.json": sel}
    for t in avail:
        rec, tr = read_json(d / f"{t}.json"), read_json(d / f"{t}_trace.json")
        if rec is None:
            errs.append(f"{d}/{t}.json missing")
        else:
            e, w = company_problems(rec, t, sample)
            errs += e
            warns += w
            files[f"{t}.json"] = rec
        if tr is None:
            errs.append(f"{d}/{t}_trace.json missing")
        else:
            errs += trace_problems(tr, t, sample, gated_figures(rec or {}))
            files[f"{t}_trace.json"] = tr
    for t in [m.get("ticker") for m in missing if isinstance(m, dict)]:
        if (d / f"{t}.json").exists() or (d / f"{t}_trace.json").exists():
            errs.append(f"{t} is listed missing but a stale {t}.json or {t}_trace.json is on disk")
    errs += all_problems(files)
    return errs, warns


def all_problems(objs):
    errs = []
    for name, obj in objs.items():
        errs += [f"{name}: {x}" for x in numeric_problems(obj)]
        errs += [f"{name}: {x}" for x in text_problems(obj)]
        errs += [f"{name}: {x}" for x in withhold_problems(obj)]
        errs += [f"{name}: {x}" for x in walk_marked(copy.deepcopy(obj))]
    return errs


def company_bundle_problems(t, rec, tr, sample=False):
    """All hard-check errors for one company's two files (empty list = safe to write)."""
    errs, _ = company_problems(rec, t, sample)
    errs += trace_problems(tr, t, sample, gated_figures(rec))
    errs += all_problems({f"{t}.json": rec, f"{t}_trace.json": tr})
    return errs


def write_bundle(dest, selection, records, traces, index_extra, sealed_md, missing=None):
    """Write selection.json, the sealed selection.md (verbatim), index.json and every company whose files pass the
    hard checks; a company that fails is listed in index.missing with its errors and is not written. Raises
    ExportError (writing nothing) when the selection itself fails."""
    sample = index_extra.get("sample", False)
    missing = list(missing or [])
    errs = selection_problems(selection) + all_problems({"selection.json": selection})
    if sealed_md is None:
        errs.append("no sealed selection.md to publish")
    else:
        above, line_sha = split_selection_md(sealed_md)
        if line_sha != selection.get("sha256") or above != selection.get("selection_md"):
            errs.append("the sealed selection.md does not match selection.json")
    if errs:
        raise ExportError("refusing to write:\n  " + "\n  ".join(errs[:60]))
    ok = {}
    for t in records:
        cerrs = company_bundle_problems(t, records[t], traces[t], sample)
        if cerrs:
            missing.append({"ticker": t, "reason": "failed checks", "errors": cerrs[:20]})
            print(f"ERROR: {t} not written:\n  " + "\n  ".join(cerrs[:20]))
        else:
            ok[t] = (records[t], traces[t])
    meta = read_json(DATA / "meta.json", {}) or {}
    picked = list(selection.get("picked") or [])
    index = {"generated_at": now_iso(), "engine": meta.get("engine"), "prompt": PROMPT, "picked": picked,
             "tickers": list(ok), "available": [t for t in picked if t in ok] + [t for t in ok if t not in picked],
             "missing": missing,
             "sealed": {"sha256": selection.get("sha256"), "sealed_at": selection.get("sealed_at"),
                        "doc_path": selection.get("sealed_doc_path")},
             "sample": False}
    index.update(index_extra)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    gone = {m["ticker"] for m in missing}
    for t in gone:  # never leave a stale company file that the index does not vouch for
        for name in (f"{t}.json", f"{t}_trace.json"):
            (dest / name).unlink(missing_ok=True)
    (dest / "selection.md").write_text(sealed_md)
    write(dest / "selection.json", selection)
    for t, (rec, tr) in ok.items():
        write(dest / f"{t}.json", rec)
        write(dest / f"{t}_trace.json", tr)
    write(dest / "index.json", index)
    return index


# ---------------------------------------------------------------- export
def export(src=OUT, dest=DEST):
    src = Path(src)
    if not (src / "selection.json").exists():
        print(f"{src} is absent (the model session has not produced Part 1 yet); nothing written.")
        return 0
    if not (src / "selection.md").exists():
        raise ExportError("out/part1/selection.md is missing: the sealed text cannot be checked")
    md = (src / "selection.md").read_text()
    selection = build_selection(read_json(src / "selection.json"), md, "part1/selection.md")
    records, traces, missing = {}, {}, []
    for t in selection.get("picked") or []:
        pj, tj = src / t / "part1.json", src / t / "trace.jsonl"
        if not (pj.exists() and tj.exists()):
            missing.append({"ticker": t, "reason": "writing",
                            "absent": [p.name for p in (pj, tj) if not p.exists()]})
            continue
        try:
            records[t] = build_company(read_json(pj))
            traces[t] = build_trace(read_jsonl(tj), t, gated_figures(records[t]))
        except (ExportError, ValueError) as e:
            records.pop(t, None)
            missing.append({"ticker": t, "reason": "failed checks", "errors": [str(e)]})
            print(f"ERROR: {t} not written: {e}")
    index = write_bundle(dest, selection, records, traces, {"sample": False}, md, missing)
    print(f"wrote {dest}: selection.md, selection.json, index.json; available {index['available']}; "
          f"missing {[(m['ticker'], m['reason']) for m in index['missing']]}")
    if not index["available"]:
        print("no picked company has part1.json and trace.jsonl yet; the UI falls back to the sample for findings")
    return 1 if any(m["reason"] == "failed checks" for m in index["missing"]) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="validate the exported files instead of writing")
    ap.add_argument("--sample", action="store_true", help="with --check: also validate ui/public/data/_sample/part1")
    ap.add_argument("--src", default=str(OUT))
    ap.add_argument("--dest", default=str(DEST))
    a = ap.parse_args(argv)
    if a.check:
        bad = 0
        targets = []
        if Path(a.dest).joinpath("index.json").exists():
            targets.append((Path(a.dest), False))
        elif not a.sample:
            print(f"{a.dest} not exported yet (out/part1 has not landed); nothing to check.")
        if a.sample:
            targets.append((SAMPLE_DEST, True))
        for d, smp in targets:
            errs, warns = check_dir(d, smp)
            for w in warns:
                print(f"warning: {w}")
            for e in errs:
                print(f"ERROR: {e}")
            print(f"{d}: {len(errs)} errors, {len(warns)} warnings")
            bad += bool(errs)
        return 1 if bad else 0
    try:
        return export(a.src, a.dest)
    except ExportError as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
