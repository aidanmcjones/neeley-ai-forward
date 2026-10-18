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


def text_problems(obj, path="$", out=None):
    out = [] if out is None else out
    if isinstance(obj, str):
        if REPR.search(obj):
            out.append(f"{path} carries a repr string: {obj[:60]}")
        m = FORBIDDEN.search(obj)
        if m:
            out.append(f"{path} carries the pitch-forbidden word '{m.group(0)}'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            text_problems(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            text_problems(v, f"{path}[{i}]", out)
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
    """The hash covers the text above the line; one trailing newline either way is accepted."""
    cands = {text, text.rstrip("\n"), text.rstrip("\n") + "\n"}
    return any(hashlib.sha256(c.encode("utf-8")).hexdigest() == (sha or "").lower() for c in cands)


def build_selection(sel, md_text=None):
    sel = copy.deepcopy(sel)
    if md_text is not None:
        above, line_sha = split_selection_md(md_text)
        if line_sha and line_sha != str(sel.get("sha256") or "").lower():
            raise ExportError("selection.md hash line differs from selection.json sha256")
        sel["selection_md"] = above
    if not sha_ok(sel.get("selection_md") or "", sel.get("sha256")):
        raise ExportError("selection.json sha256 is not the sha256 of selection.md above its hash line")
    withhold_tree(sel)
    walk_marked(sel, fix=True)
    return sel


def selection_problems(sel):
    errs = []
    for k in ("picked", "reasons", "eliminated", "sealed_at", "sha256", "selection_md"):
        if k not in sel:
            errs.append(f"selection.json missing {k}")
    picked = sel.get("picked") or []
    if not (isinstance(picked, list) and 1 <= len(picked) <= 3):
        errs.append("selection.picked must list one to three tickers")
    for t in picked:
        if t not in (sel.get("reasons") or {}):
            errs.append(f"selection.reasons has no entry for {t}")
    if not sha_ok(sel.get("selection_md") or "", sel.get("sha256")):
        errs.append("selection.json sha256 does not match selection_md")
    return errs


# ---------------------------------------------------------------- company record
def build_company(rec):
    rec = copy.deepcopy(rec)
    withhold_tree(rec)
    for f in rec.get("findings") or []:
        reconcile_source(f)
    walk_marked(rec, fix=True)
    return rec


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
    names = [pt.get("product")] + list(pt.get("rivals") or [])
    for r in rows:
        for nm in names:
            if nm not in (r.get("cells") or {}):
                errs.append(f"{t}.product_table row '{r.get('row')}' has no cell for {nm}")
    for k in ("financial_tie", "growth_limiter", "priced_in"):
        if not isinstance(pt.get(k), dict):
            errs.append(f"{t}.product_table.{k} missing")
    if (pt.get("priced_in") or {}).get("call") not in PRICED_CALLS:
        errs.append(f"{t}.product_table.priced_in.call {(pt.get('priced_in') or {}).get('call')!r}")
    return errs, warns


# ---------------------------------------------------------------- trace
def build_trace(lines, ticker=None):
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
        if s["verdict"] == "killed":
            cand["text"] = strip_ungated_numbers(cand.get("text") or "")
        s["candidate"] = cand
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


def trace_problems(tr, t, sample=False):
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
        if s.get("verdict") == "killed" and re.search(r"\d", ((s.get("candidate") or {}).get("text") or "").replace(WITHHELD_FIGURE, "")):
            errs.append(f"{p} killed candidate prints an ungated number")
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
    if not sample and OUT.joinpath("selection.md").exists():
        above, _ = split_selection_md(OUT.joinpath("selection.md").read_text())
        if not sha_ok(above, sel.get("sha256")):
            errs.append("out/part1/selection.md no longer hashes to the exported sha256: re-export")
    files = {"selection.json": sel}
    for t in idx.get("tickers") or []:
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
            errs += trace_problems(tr, t, sample)
            files[f"{t}_trace.json"] = tr
    for t in idx.get("picked") or []:
        if t not in (idx.get("tickers") or []):
            errs.append(f"picked {t} has no exported record")
    for name, obj in files.items():
        errs += [f"{name}: {x}" for x in numeric_problems(obj)]
        errs += [f"{name}: {x}" for x in text_problems(obj)]
        errs += [f"{name}: {x}" for x in withhold_problems(obj)]
        errs += [f"{name}: {x}" for x in walk_marked(copy.deepcopy(obj))]
    return errs, warns


def all_problems(objs):
    errs = []
    for name, obj in objs.items():
        errs += [f"{name}: {x}" for x in numeric_problems(obj)]
        errs += [f"{name}: {x}" for x in text_problems(obj)]
        errs += [f"{name}: {x}" for x in withhold_problems(obj)]
        errs += [f"{name}: {x}" for x in walk_marked(copy.deepcopy(obj))]
    return errs


def write_bundle(dest, selection, records, traces, index_extra):
    """Validate everything in memory, then write the four shapes. Raises ExportError before writing anything."""
    objs = {"selection.json": selection}
    errs = selection_problems(selection)
    for t, rec in records.items():
        e, _ = company_problems(rec, t, index_extra.get("sample", False))
        errs += e
        objs[f"{t}.json"] = rec
    for t, tr in traces.items():
        errs += trace_problems(tr, t, index_extra.get("sample", False))
        objs[f"{t}_trace.json"] = tr
    meta = read_json(DATA / "meta.json", {}) or {}
    index = {"generated_at": now_iso(), "engine": meta.get("engine"), "prompt": PROMPT,
             "picked": selection.get("picked"), "tickers": [t for t in records],
             "sealed": {"sha256": selection.get("sha256"), "sealed_at": selection.get("sealed_at")},
             "sample": False}
    index.update(index_extra)
    objs["index.json"] = index
    errs += all_problems(objs)
    if errs:
        raise ExportError("refusing to write:\n  " + "\n  ".join(errs[:60]))
    dest = Path(dest)
    for name, obj in objs.items():
        write(dest / name, obj)
    return index


# ---------------------------------------------------------------- export
def export(src=OUT, dest=DEST):
    src = Path(src)
    if not (src / "selection.json").exists():
        print(f"{src} is absent (the model session has not produced Part 1 yet); nothing written.")
        return 0
    sel_raw = read_json(src / "selection.json")
    md = (src / "selection.md").read_text() if (src / "selection.md").exists() else None
    if md is None:
        raise ExportError("out/part1/selection.md is missing: the sealed text cannot be checked")
    selection = build_selection(sel_raw, md)
    records, traces = {}, {}
    tickers = list(selection.get("picked") or [])
    tickers += sorted(p.name for p in src.iterdir() if p.is_dir() and (p / "part1.json").exists() and p.name not in tickers)
    for t in tickers:
        pj = src / t / "part1.json"
        if not pj.exists():
            raise ExportError(f"{pj} missing for picked ticker {t}")
        records[t] = build_company(read_json(pj))
        tj = src / t / "trace.jsonl"
        if not tj.exists():
            raise ExportError(f"{tj} missing")
        traces[t] = build_trace(read_jsonl(tj), t)
    write_bundle(dest, selection, records, traces, {"sample": False})
    print(f"wrote {dest}: index.json, selection.json, " + ", ".join(f"{t}.json, {t}_trace.json" for t in records))
    return 0


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
