#!/usr/bin/env python3
"""ui_part1_fixture: a Part 1 sample in the exporter's four shapes, built from real gated data.

Writes ui/public/data/_sample/part1/ (index.json with sample: true, selection.json, <T>.json, <T>_trace.json) so the
UI can be built before the model session produces out/part1. Every number and cite is copied from the exported
company files (ui/public/data/companies/<T>.json) through the same renderers agent/ui_memos.py uses; what is
illustrative is the pick order (LLY, GILD, MRK), the selection prose and the trace (assembled from the engine's gate
and red-team decisions; the blind skeptic pass has not run). The output goes through agent/ui_part1_export's
transforms and hard checks before anything is written. Contract: docs/ui_part1.md.

    PYTHONPATH=. python -m agent.ui_part1_fixture
    PYTHONPATH=. python -m agent.ui_part1_export --check --sample
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

from agent import ui_memos as M
from agent import ui_part1_export as X

ROOT = X.ROOT
PICKED = ["LLY", "GILD", "MRK"]
PRODUCT = {"LLY": "zepbound", "GILD": "biktarvy", "MRK": "keytruda"}
MAX_STEPS = 40
TAIL = 3  # cites marked after a product cell or line

SAMPLE_NOTE = ("Sample fixture, not the team's Part 1 answer. The pick order LLY, GILD, MRK is illustrative; the "
               "selection text and its hash are written by agent/ui_part1_fixture.py, not sealed by the model session. "
               "Findings, impact math, sources, product cells and the priced-in call are copied from the gated company "
               "files with the public withholding rule applied. The trace is assembled from the engine's gate and "
               "red-team decisions; the blind skeptic pass has not run, so the skeptic fields are null.")
TRACE_NOTE = "Illustrative trace assembled from the engine's gate and red-team decisions; the blind skeptic pass has not run"
ROW_KEYS = dict(zip(M.ROW_ORDER, X.ROW_KEYS))


# ---------------------------------------------------------------- cite book that keeps the full evidence object
class RecordCites(M.Cites):
    """ui_memos.Cites numbering, but each item is the company file's evidence object (withheld later by the
    exporter), plus n and finding_ids. Row cites are kept as ui_memos builds them."""

    def __init__(self):
        super().__init__()
        self.raw = {}

    def feed(self, evs):
        for e in evs or []:
            if isinstance(e, dict) and e.get("cite_id"):
                self.raw.setdefault(e["cite_id"], e)

    def add(self, cite):
        cid = cite["cite_id"]
        fresh = cid not in self.by_id
        n = super().add(cite)
        if fresh and cid in self.raw:
            item = self.items[n - 1]
            self.items[n - 1] = {"n": n, **copy.deepcopy(self.raw[cid]), "doc_label": cite.get("doc_title"),
                                 "finding_ids": item["finding_ids"]}
        return n

    def marker_map(self):
        return {str(c["n"]): c["cite_id"] for c in self.items}


def clean(text):
    out = re.sub(r"\s{2,}", " ", M.strip_marks(text or ""))
    return re.sub(r"\s+([;,.:)])", r"\1", out).strip()


def page_of(e):
    p = e.get("printed")
    return p if p not in (None, "", "?", "X") else e.get("page")


def row_ref_cite(C, cid, ref, title, quote, t, verification="engine record"):
    return C.add(M.row_cite(cid, ref, title, quote, verification, ticker=t))


# ---------------------------------------------------------------- findings
def first_page_cite(f):
    for e in f.get("evidence") or []:
        if not e.get("withheld") and M.verification_str(e) in M.VERBATIM and e.get("page") is not None and e.get("quote"):
            return e
    return None


def finding_record(ctx, t, f, row, unres, n):
    C = RecordCites()
    C.feed(f.get("evidence"))
    C.feed(f.get("data_citations"))
    text, ns = M.sentence(f, C, t, row=row, unresolved=unres)
    finding_marked = C.after(text, *ns)
    src_e = first_page_cite(f)
    source = None
    if src_e:
        sn = C.add(M.ev_cite(src_e, f["id"], t))
        source = {"doc_title": M.doc_label(src_e), "period": src_e.get("period"), "page": page_of(src_e),
                  "quote": src_e.get("quote"), "url": src_e.get("deep_link") or src_e.get("url"),
                  "speaker": src_e.get("speaker") or None, "cite": sn}
    itxt, formula, ins = M.impact_cell(f, C, t)
    math_marked = None
    if formula and ins:
        mb = M.impact_math(f, C, t, "Impact math", ins[0], row, unres)
        math_marked = mb.get("text_marked")
    peer, pns = M.peer_cell(f, C, t, row=row, unresolved=unres)
    peer_marked = C.after(peer, *pns)
    imp = f.get("impact") or {}
    direction = "adverse" if (imp.get("adverse") or f.get("direction") in ("adverse", "negative")) else (f.get("direction") or None)
    nc = copy.deepcopy((row or {}).get("numeric_check") or f.get("numeric_check"))
    return {
        "n": n, "finding_id": f["id"], "signal_kind": f.get("signal_kind"),
        "finding": clean(finding_marked), "finding_marked": finding_marked,
        "marker_map": None,  # filled after every cite is added
        "source": source,
        "cites": None,
        "impact": {"text": clean(itxt), "text_marked": C.after(itxt, *ins), "math": formula,
                   "math_marked": math_marked, "direction": direction, "numeric_check": nc},
        "peer": clean(peer_marked), "peer_marked": peer_marked,
        "confidence": (row or {}).get("confidence") or f.get("confidence"),
        "table_rank": (row or {}).get("rank"),
        "_C": C,
    }


def seal_record(rec):
    C = rec.pop("_C")
    rec["marker_map"] = C.marker_map()
    rec["cites"] = C.items
    return rec


def needle_why(c):
    """ui_memos.needle_memo's reading of needle_reason: printed when it adds something, else a plain clause."""
    reason = c.get("needle_reason")
    src = c.get("needle_source")
    if not isinstance(reason, str) or not reason.strip():
        return None
    why = re.sub(r"^red-team read: ", "", reason.strip().rstrip("."))
    why = re.sub(r"Parker's best needle for [A-Z]+ \(([A-Z]+)-nugget-(\d+), docs/[\w./-]+\); his one-line reason carries figures the gate does not support, so it is not printed",
                 r"the red team's pick (nugget \2), confirmed by the gate; the reviewer's own reason carries figures the gate does not support, so it is not printed", why)
    if why.startswith("plain rule"):
        why = "chosen by the plain rule: the biggest cited impact that analysts asked about least"
    elif src == "red_team" and not why.startswith("the red team"):
        why = "chosen by the red-team read, confirmed by the gate: " + why
    return M.plain_terms(why)


def sharpest_needle(ctx, t, recs):
    c = ctx.companies[t]
    nid = c.get("needle_id_rule")
    hit = next((r for r in recs if r["finding_id"] == nid), recs[0] if recs else None)
    C = RecordCites()
    why = needle_why(c)
    out = {"finding_n": hit["n"] if hit else None, "finding_id": hit["finding_id"] if hit else None,
           "why": why, "why_marked": None, "cites": []}
    if why:
        n = row_ref_cite(C, f"row:needle_reason:{t}", f"companies/{t}.json:needle_reason",
                         "needle selection record (red team vs rule)", c.get("needle_reason"), t)
        out["why_marked"] = f"{why} [{n}]"
        out["cites"] = C.items
    return out


# ---------------------------------------------------------------- product table
def cell_record(t, slug, rk, ent, cell):
    C = RecordCites()
    cites = [x for x in cell.get("citations") or [] if isinstance(x, dict)]
    C.feed(cites)
    ns = [C.add(M.ev_cite(e, None, t, i)) for i, e in enumerate(cites)]
    nc = (cell.get("numeric_check") or {}).get("status")
    page_ok = any(not e.get("withheld") and M.verification_str(e) in M.VERBATIM and e.get("page") is not None for e in cites)
    val = cell.get("value")
    if val in (None, ""):
        reason = M.plain_terms(cell.get("empty_reason") or "not located")
        text = "no data: " + X.strip_ungated_numbers(reason)
        return {"text": text, "text_marked": text, "cites": C.items, "status": "empty"}
    if cell.get("uncited") or not cell.get("verified") or nc not in X.NC_OK or not page_ok:
        return {"text": "needs citation", "text_marked": "needs citation", "cites": C.items, "status": "needs citation",
                "note": "the value has no verified page citation, so it is not printed"}
    text = val
    if rk == "dosing":
        text = M.dosing_text(val, [M.verbatim_quote(e) for e in cites])
    text = M.plain_cell(text)
    return {"text": text, "text_marked": C.after(text, *ns[:TAIL]), "cites": C.items, "status": "cited"}


def tie_record(t, slug, v2):
    for tie in v2.get("findings") or []:
        if not isinstance(tie, dict) or not tie.get("finding"):
            continue
        if not M.tied_gate(tie) and (tie.get("numeric_check") or {}).get("status") != "no_numbers":
            continue
        C = RecordCites()
        C.feed(tie.get("evidence"))
        ns = [C.add(M.ev_cite(e, tie.get("id"), t, i)) for i, e in enumerate(tie.get("evidence") or [])]
        text = M.plain_terms(tie["finding"].rstrip("."))
        return {"finding_id": tie.get("id"), "channel": tie.get("channel"), "text": text,
                "text_marked": C.after(text, *ns[:TAIL]),
                "math": M.strip_marks((tie.get("impact") or {}).get("formula") or "").strip() or None,
                "numeric_check": copy.deepcopy(tie.get("numeric_check")), "cites": C.items}
    return {"finding_id": None, "text": "No product channel passed the numeric gate, so no financial tie is printed.",
            "text_marked": "No product channel passed the numeric gate, so no financial tie is printed.", "math": None,
            "cites": []}


def limiter_record(t, slug, gl):
    C = RecordCites()
    cites = [x for x in gl.get("citations") or [] if isinstance(x, dict)]
    C.feed(cites)
    ns = [C.add(M.ev_cite(e, None, t, i)) for i, e in enumerate(cites)]
    quotes = [M.cite_text(e) for e in cites]
    s = M.money_gate(M.plain_terms((gl.get("sentence") or "").rstrip(".")), quotes, gl.get("numeric_check"))
    if not ns and re.search(r"\d", s):
        ns = [row_ref_cite(C, f"row:gl:{t}:{slug}", f"companies/{t}.json:labels.v2.{slug}.growth_limiter",
                           "product growth limiter (agent.needle.quant.product)", gl.get("sentence"), t, "computed")]
    return {"sentence": s + ".", "sentence_marked": C.after(s, *ns[:TAIL]) + ".",
            "numeric_check": copy.deepcopy(gl.get("numeric_check")), "cites": C.items}


def priced_record(ctx, t, slug, gl):
    C = RecordCites()
    reasons = gl.get("reasons") or []
    line, _ = M.priced_in_line(gl)
    if line.startswith("Priced-in call: not testable"):
        call = "untestable"
        text = line.replace("Priced-in call: not testable", "The priced-in question cannot be tested") + "."
    else:
        call = "priced in" if gl.get("priced_in") else "not priced in"
        text = ("The market has already priced this in" if gl.get("priced_in") else
                "The market has not clearly priced this in") + ", on the analyst-attention, starter-thread and consensus tests."
    ns = []
    if reasons:
        ns.append(row_ref_cite(C, f"row:gl_reasons:{t}:{slug}", f"companies/{t}.json:labels.v2.{slug}.growth_limiter.reasons",
                               "priced-in test inputs: analyst-attention scorecard, case starter thread, I/B/E/S consensus "
                               "(data/moat/verified/market)", " | ".join(reasons), t, "computed"))
    m = next((re.search(r"asked about (\w+) in", r) for r in reasons if re.search(r"asked about (\w+) in", r)), None)
    if m:
        topic = m.group(1)
        row = next((r for r in ctx.companies[t].get("priced_in") or [] if r.get("topic") == topic), None)
        if row:
            q = (f"{topic}: asked in {row.get('quarters_asked')} of {row.get('quarters_covered')} quarters "
                 f"({row.get('quarter_range')}), {row.get('analyst_turns_on_topic')} analyst turns, tier "
                 f"{row.get('analyst_attention_tier')}, last asked {row.get('last_quarter_asked')}")
            ns.append(row_ref_cite(C, f"row:priced_in:{t}:{topic}", f"companies/{t}.json:priced_in[topic={topic}]",
                                   "analyst-attention scorecard (data/moat/verified/market/analyst_topics.csv)", q, t, "computed"))
    body = text.rstrip(".")
    return {"call": call, "text": text, "text_marked": C.after(body, *ns) + ".", "cites": C.items}


def product_table(ctx, t, slug):
    v2 = ((ctx.companies[t].get("labels") or {}).get("v2") or {}).get(slug) or {}
    ents = v2.get("entities") or []
    names = [e["name"] for e in ents]
    rows = []
    for rk in M.ROW_ORDER:
        src = (v2.get("rows") or {}).get(rk) or {}
        rows.append({"row": ROW_KEYS[rk], "title": (v2.get("row_titles") or {}).get(rk),
                     "cells": {nm: cell_record(t, slug, rk, nm, src.get(nm) or {}) for nm in names}})
    gl = v2.get("growth_limiter") or {}
    return {"product": names[0] if names else slug.capitalize(), "slug": slug,
            "maker": ents[0].get("maker") if ents else None, "rivals": names[1:],
            "rows": rows, "financial_tie": tie_record(t, slug, v2), "growth_limiter": limiter_record(t, slug, gl),
            "priced_in": priced_record(ctx, t, slug, gl), "source_file": v2.get("source_file")}


def company_part1(ctx, t):
    c = ctx.companies[t]
    fs, _ = M.ranked_findings(ctx, t)
    by, unres = ctx.table_rows(t)
    recs = [finding_record(ctx, t, f, by.get(f["id"]), unres, i) for i, f in enumerate(fs, 1)]
    recs = [seal_record(r) for r in recs]
    return {"ticker": t, "name": ctx.name(t), "sample": True,
            "rank_basis": (c.get("findings_table") or {}).get("rank_basis"),
            "findings": recs, "sharpest_needle": sharpest_needle(ctx, t, recs),
            "product_table": product_table(ctx, t, PRODUCT[t])}


# ---------------------------------------------------------------- trace
NUGGET_FAMILY = {"language_drift": "Language drift", "gtn": "Gross-to-net",
                 "inventory_receivables": "Inventory and receivables growing faster than revenue",
                 "segment_change": "Segment and product table changes", "footnotes": "Footnotes",
                 "call_qa": "Earnings-call Q&A", "label_fine_print": "Product fine print"}
KIND_RULES = [  # (signal_kind pattern, category, note); first match wins; nugget families are read first
    (r"^(risk_|mdna_)|drift|contradiction", "Language drift", None),
    (r"^(qa_|call_)|dodge|deflection", "Earnings-call Q&A", None),
    (r"_peer_outlier$", "Peer contrast", None),
    (r"^(label_|boxed_|dosing_|exclusivity_|faers_)|patent|paragraph_iv|spend_per_claim", "Product fine print", None),
    (r"gtn|rebate|net_price|^ira_|^mfn_|ira_selection|program_cliff", "Gross-to-net", None),
    (r"^dio_|^dso_|inventory|receivable|distributor_commentary", "Inventory and receivables growing faster than revenue", None),
    (r"segment|revenue_quality|demand_divergence|gross_margin_drop|discontinued", "Segment and product table changes", None),
    (r"impairment|trial_terminated|footnote|royalty|collaboration|contingent|expense_offset|litigation", "Footnotes", None),
    (r"tax_rate_shift|rnd_shift", "Footnotes", "tax and R&D shifts are read from the income-statement footnotes; no closer case category"),
]
QUERY = {
    "mdna_added": "MD&A paragraphs added since the prior filing",
    "mdna_removed": "MD&A paragraphs removed since the prior filing",
    "mdna_modified": "MD&A paragraphs reworded since the prior filing",
    "mdna_intensified": "MD&A wording that grew stronger since the prior filing",
    "risk_added": "risk factors added since the prior annual report",
    "risk_removed": "risk factors removed since the prior annual report",
    "risk_modified": "risk factors reworded since the prior annual report",
    "risk_intensified": "risk factors whose wording grew stronger since the prior annual report",
    "tax_rate_shift": "a shift in the effective tax rate against a year earlier",
    "etr_peer_outlier": "an effective tax rate far from the peer median",
    "rnd_shift": "a shift in R&D spending against a year earlier",
    "rnd_pct_peer_outlier": "R&D as a share of revenue far from the peer median",
    "gross_margin_peer_outlier": "gross margin far from the peer median",
    "gross_margin_drop": "a fall in gross margin against a year earlier",
    "dio_peer_outlier": "days of inventory far from the peer median",
    "call_topic_surge": "a topic analysts suddenly raised more often on earnings calls",
    "qa_deflection": "an analyst question management did not answer",
    "qa_repeated_deflection": "the same analyst question deflected on more than one call",
    "label_narrower": "a label with narrower approved uses than a rival's",
    "label_broader": "a label with broader approved uses than a rival's",
    "boxed_warning_advantage": "a boxed warning a rival carries and the product does not",
    "boxed_warning_disadvantage": "a boxed warning the product carries and a rival does not",
    "dosing_burden": "a heavier dosing schedule than a rival's",
    "spend_per_claim_gap": "a gap in Medicare spend per claim against a rival",
    "exclusivity_earlier": "an exclusivity end earlier than the market assumes",
    "ira_selected": "a product selected for Medicare price negotiation",
    "ira_exposed": "a product exposed to a future Medicare negotiated price",
    "mfn_medicaid": "the terms of the most-favored-nation pricing agreement",
    "demand_divergence": "product revenue moving apart from prescription volume",
    "faers_serious_rising": "rising serious adverse-event reports in FDA's FAERS data",
    "distributor_commentary": "drug-distributor filings that discuss the product class next to inventory or channel language",
    "trial_terminated": "a clinical trial stopped for business reasons",
    "impairment": "a booked impairment in the footnotes",
}


def category_of(kind, nugget_family=None, peer=None):
    if nugget_family in NUGGET_FAMILY:
        return NUGGET_FAMILY[nugget_family], None
    for pat, cat, note in KIND_RULES:
        if re.search(pat, kind or ""):
            return cat, note
    if "peer" in (kind or "") or (isinstance(peer, dict) and peer.get("comparable")):
        return "Peer contrast", None
    return "Footnotes", "no case category matches this signal; filed under Footnotes"


def query_of(kind, nugget_family=None):
    if kind in QUERY:
        return "Looked for " + QUERY[kind] + "."
    words = (kind or "signal").replace("_", " ")
    if nugget_family:
        return f"Red-team read of the {nugget_family.replace('_', ' ')} pages for {words}."
    return f"Looked for {words}."


GUARD_WORDS = {
    "2": "review guard: not a peer outlier once measured on the right base",
    "8": "review guard: an MD&A change with no direction read yet, so it cannot be a finding",
    "9": "review guard: no evidence quote is a full sentence (a table of contents or a parsed table)",
}


def kill_reason(r):
    by, reason = r.get("rejected_by") or "", r.get("reason") or ""
    if by == "numeric_gate":
        parts = []
        for u in r.get("unsupported") or (r.get("numeric_check") or {}).get("unsupported") or []:
            why = u.get("reason") or ""
            if "unit differs" in why:
                parts.append("a number in the sentence matches a cited figure only in a different unit")
            elif "sign differs" in why:
                parts.append("a number in the sentence has the opposite sign to the cited figure")
            else:
                parts.append("a number in the sentence is carried by no passing citation, derivation or assumption")
        return "numeric gate: " + "; ".join(dict.fromkeys(parts or ["a number did not pass"]))
    if by == "drop guard":
        m = re.search(r"guard (\d+):", reason)
        if m and m.group(1) in GUARD_WORDS:
            return GUARD_WORDS[m.group(1)]
        if m and m.group(1) == "3":
            return ("review guard: the pre-tax base is too small for a tax rate to mean anything" if "not meaningful" in reason
                    else "review guard: the tax-rate move is under the shift threshold")
        return "review guard: dropped (the guard recorded no further reason)"
    if by == "no page evidence":
        return "evidence gate: no page-verified citation backs it"
    return X.strip_ungated_numbers(reason) or "rejected by the gate"


def documents_of(evs):
    out = []
    for e in evs or []:
        if isinstance(e, dict) and e.get("doc_id"):
            out.append({"doc_id": e["doc_id"], "doc_title": M.doc_label(e), "page": page_of(e)})
    return out


def trace_lines(ctx, t, part1, generated_at):
    c = ctx.companies[t]
    raw = {}
    for name in ("findings_v3.jsonl", "rejected_v3.jsonl"):
        p = ROOT / "out" / t / name
        if p.exists():
            for row in X.read_jsonl(p):
                raw[row["id"]] = row
    rung = {}
    p = ROOT / "docs" / "nuggets" / f"{t}.jsonl"
    if p.exists():
        for n in X.read_jsonl(p):
            rung[n["id"]] = ((n.get("obscurity") or {}).get("rung"), n.get("verdict"))
    by, _ = ctx.table_rows(t)
    shown = {r["finding_id"]: r["n"] for r in part1["findings"]}
    needle_id = part1["sharpest_needle"].get("finding_id")
    survived, narrowed, killed = [], [], []

    def base(fid, kind, text, evs, verdict):
        rr = raw.get(fid) or {}
        nug = rr.get("nugget") or {}
        fam = (nug.get("signal_family") if isinstance(nug, dict) else None)
        fam = fam or (re.sub(r"^nugget: ", "", rr.get("signal_family") or "") if str(rr.get("signal_family") or "").startswith("nugget:") else None)
        cat, note = category_of(kind, fam, rr.get("peer"))
        step = {"category": cat, "query": query_of(kind, fam), "documents": documents_of(evs),
                "candidate": {"text": text}, "skeptic_materiality": None, "skeptic_obviousness": None,
                "verdict": verdict, "signal_kind": kind, "detector": rr.get("detector"), "block": rr.get("block"),
                "source_id": fid}
        if note:
            step["category_note"] = note
        nid = nug.get("id") if isinstance(nug, dict) else None
        if nid:
            step["nugget_id"] = nid
            if nid in rung:
                step["obscurity_rung"] = rung[nid][0]
        return step

    for f in c.get("findings") or []:
        fid, row = f["id"], by.get(f["id"]) or {}
        status = M.nc_status(f)
        if status == "failed":
            s = base(fid, f.get("signal_kind"), X.strip_ungated_numbers(M.strip_marks(f.get("finding") or "")), f.get("evidence"), "killed")
            s["verdict_reason"] = "numeric gate: a number in the sentence did not pass"
            killed.append(s)
            continue
        text = clean(row.get("sentence") or f.get("finding"))
        if fid in shown:
            s = base(fid, f.get("signal_kind"), text, f.get("evidence"), "survived")
            s["finding_n"] = shown[fid]
            s["verdict_reason"] = ("passed the citation and numeric gates; one of the five shown"
                                   + ("; the Sharpest Needle" if fid == needle_id else ""))
            survived.append((shown[fid], s))
        else:
            s = base(fid, f.get("signal_kind"), text, f.get("evidence"), "narrowed")
            s["verdict_reason"] = ("passed the citation and numeric gates; explained by a footnote, so not shown"
                                   if f.get("explained_by_footnote") else
                                   "passed the citation and numeric gates; ranked outside the five shown")
            s["table_rank"] = row.get("rank")
            narrowed.append(s)
    seen, dup = set(), 0
    for r in c.get("rejected") or []:
        reason = kill_reason(r)
        key = (r.get("signal_kind"), reason)
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        s = base(r["id"], r.get("signal_kind"), X.strip_ungated_numbers(M.strip_marks(r.get("finding") or "")), r.get("evidence"), "killed")
        s["verdict_reason"] = reason
        killed.append(s)
    survived = [s for _, s in sorted(survived, key=lambda x: x[0])]
    narrowed.sort(key=lambda s: (s.get("table_rank") is None, s.get("table_rank") or 0))
    room = max(0, MAX_STEPS - len(survived) - len(killed))
    kept_narrowed = narrowed[:room]
    steps = survived + kept_narrowed + killed
    for i, s in enumerate(steps, 1):
        s["step"] = i
    header = {"step": 0, "category": "header", "categories": list(X.CATEGORIES), "ticker": t,
              "generated_at": generated_at, "sample": True, "note": TRACE_NOTE,
              "trimmed": {"rows_total": len(c.get("findings") or []) + len(c.get("rejected") or []),
                          "killed_same_reason_dropped": dup, "narrowed_not_shown": len(narrowed) - len(kept_narrowed)},
              "sources": [f"out/{t}/findings_v3.jsonl", f"out/{t}/rejected_v3.jsonl", f"docs/nuggets/{t}.jsonl",
                          f"ui/public/data/companies/{t}.json"]}
    return [header] + steps


# ---------------------------------------------------------------- selection
def counts_cite(ctx, C, t):
    e = (ctx.meta.get("evidence_located") or {}).get(t) or {}
    return C.add(M.row_cite(f"row:meta:evidence:{t}", f"meta.json:evidence_located.{t}",
                            "meta.json evidence_located (per-company counts at export)",
                            "; ".join(f"{k} {e.get(k)}" for k in ("findings", "verified", "high_confidence", "rejected", "evidence", "located")),
                            "counted by agent/ui_export.py at export", ticker=t)), e


def decide_clause(ctx, C, t):
    d = ((ctx.companies[t].get("stance") or {}).get("decide") or {})
    if not d.get("moves"):
        return "no DECIDE run exists for it yet"
    n = C.add(M.row_cite(f"row:decide:{t}", f"companies/{t}.json:stance.decide.demo",
                         "DECIDE output flag (stance.decide.demo)", f"demo {bool(d.get('demo'))}", "engine record", ticker=t))
    return (f"a DECIDE run exists ({'pipeline demonstration' if d.get('demo') else 'valued move'}) [{n}]")


def selection_record(ctx, t, picked_rank=None):
    C = RecordCites()
    name = ctx.name(t)
    n, e = counts_cite(ctx, C, t)
    c = ctx.companies[t]
    src = {"red_team": "chosen by the red-team read and confirmed by the gate", "rule": "chosen by the plain rule"}.get(c.get("needle_source"), "set by the engine")
    rn = C.add(M.row_cite(f"row:needle_source:{t}", f"companies/{t}.json:needle_source", "needle selection record (red team vs rule)",
                          str(c.get("needle_source")), "engine record", ticker=t))
    lead = M.match_rule((ctx.needle(t)[0] or {}).get("signal_kind"), M.LEADS)
    lead = f" ({M.lc(lead)})" if lead else ""
    dc = decide_clause(ctx, C, t)
    if picked_rank:
        marked = (f"Illustrative pick {picked_rank} of 3: {name} has {e.get('verified')} page-verified findings, "
                  f"{e.get('high_confidence', 0)} at high confidence [{n}]; its Sharpest Needle{lead} was {src} [{rn}]; {dc}.")
    else:
        marked = (f"{name}: {e.get('verified')} page-verified findings [{n}]; needle {src} [{rn}]; {dc}. "
                  f"Not picked in this illustrative order, which is not a ranking.")
    return {"text": clean(marked), "text_marked": marked, "cites": C.items}


def build_selection(ctx, generated_at):
    """(selection.json, selection.md) in the model session's shapes: the md carries '## Picks' with '### N. T (Name)'
    paragraphs, '## Eliminated' with '- T: ...' bullets and a trailing 'sha256:' line over the text above it."""
    others = [t for t in ctx.tickers if t not in PICKED]
    reason_records = {t: selection_record(ctx, t, i) for i, t in enumerate(PICKED, 1)}
    elim_records = {t: selection_record(ctx, t) for t in others}
    md = ["# Part 1 company selection (sample fixture, illustrative)", "",
          "This text is written by agent/ui_part1_fixture.py from the gated company files. It is not the model "
          "session's sealed selection; the order below is illustrative.", "", "## Picks", ""]
    for i, t in enumerate(PICKED, 1):
        md += [f"### {i}. {t} ({ctx.name(t)})", "", reason_records[t]["text"], ""]
    md += ["## Eliminated", ""] + [f"- {t}: {elim_records[t]['text']}" for t in others]
    above = "\n".join(md) + "\n"
    sha = hashlib.sha256(above.rstrip("\n").encode("utf-8")).hexdigest()
    sealed_md = above + f"sha256: {sha}\n"
    sel = {"picked": list(PICKED), "reasons": {t: r["text"] for t, r in reason_records.items()},
           "eliminated": {t: r["text"] for t, r in elim_records.items()},
           "reason_records": reason_records, "eliminated_records": elim_records,
           "sealed_at": generated_at, "sha256": sha, "sample": True,
           "sealed_note": "fixture hash of the illustrative selection text; not sealed by the model session"}
    return sel, sealed_md


def main(argv=None):
    ctx = M.Ctx(M.DATA)
    missing = [t for t in PICKED if t not in ctx.companies]
    if missing:
        print(f"ERROR: company files missing for {missing}; run agent.ui_export first")
        return 1
    generated_at = X.now_iso()
    sel, sealed_md = build_selection(ctx, generated_at)
    selection = X.build_selection(sel, sealed_md, "_sample/part1/selection.md")
    records, traces = {}, {}
    for t in PICKED:
        part1 = company_part1(ctx, t)
        records[t] = X.build_company(part1)
        traces[t] = X.build_trace(trace_lines(ctx, t, part1, generated_at), t)
    try:
        index = X.write_bundle(X.SAMPLE_DEST, selection, records, traces,
                               {"sample": True, "sample_note": SAMPLE_NOTE}, sealed_md)
    except X.ExportError as e:
        print(f"ERROR: {e}")
        return 1
    for t in PICKED:
        s = traces[t]["summary"]
        print(f"{t}: {len(records[t]['findings'])} findings, product {records[t]['product_table']['product']} vs "
              f"{', '.join(records[t]['product_table']['rivals'])}, trace {s}")
    print(f"wrote {X.SAMPLE_DEST}; available {index['available']}, missing {index['missing']}")
    return 1 if index["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
