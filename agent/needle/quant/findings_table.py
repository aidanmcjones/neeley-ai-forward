"""Pitch-facing findings table: gated FIND rows ranked by dollar impact, with the Sharpest Needle picked by one
plain-English rule (docs/quant_model.md section 12).

  rank basis   |dEPS| in the base scenario (USD per share, from the row's impact formula); ties by |dOI| (USD M)
  needle rule  "the biggest-impact finding that analysts asked about least": among quantified rows (|dEPS| > 0),
               keep those with the lowest analyst-share-asked (the obscurity discussion term a, section 4.4), then
               take the one with the largest |dEPS|. A row a guard marks as never-the-needle is skipped.

The internal FIND score S and the league (league_v3) still order candidates for review; they are not printed here.
Output: out/<T>/findings_table.md and .json (rank_basis "impact"). Every number carries the same per-number markers
and one shared footnote list (agent.needle.cite.render); the model outputs dEPS, dOI and a are labelled assumptions
("model output" / "obscurity term"), as decide.md labels its model outputs.
"""

import json

from agent.needle.cite.gate import gate_document
from agent.needle.cite.locator import Claim
from agent.needle.cite.render import claim_markup, render_footnotes_md

from . import gatewire as GW

RANK_BASIS = "impact"
NEEDLE_RULE = ("the biggest-impact finding that analysts asked about least: among quantified findings, those with "
               "the lowest analyst-share-asked, then the largest base-case |dEPS|")


def impact_of(f):
    """(|dEPS| base, |dOI| base) of a Scored row; (0, 0) when the row is not quantified."""
    if f.not_quantified or not f.impact:
        return 0.0, 0.0
    return abs(float((f.impact.d_eps or {}).get("base") or 0.0)), abs(float((f.impact.d_oi or {}).get("base") or 0.0))


def share_asked(f):
    """Analyst share of recent calls that asked about the topic (obscurity term a); 1.0 when it is unknown."""
    a = (f.vector or {}).get("a")
    return 1.0 if a is None else float(a)


def rank(rows):
    """Scored rows sorted by impact, largest first."""
    return sorted(rows, key=lambda f: tuple(-x for x in impact_of(f)))


def pick_needle(rows):
    """The row the plain rule picks, or None when no row is quantified."""
    cand = [f for f in rows if impact_of(f)[0] > 0 and not getattr(f, "needle_blocked", False)]
    if not cand:
        return None
    lo = min(share_asked(f) for f in cand)
    return max((f for f in cand if share_asked(f) == lo), key=lambda f: impact_of(f))


def _claims(f):
    ok = [c for c in f.citations if c.verification.ok]
    dm, am = dict(f.derived or {}), dict(f.assumptions or {})
    sent = Claim(f.sentence, ok, derived=dm, assumptions=am, where=f"finding/{f.id}")
    formula = "" if f.not_quantified else (f.impact.formula or "")
    form = Claim(formula, ok, derived=dm, assumptions=am, where=f"formula/{f.id}") if formula else None
    eps, oi = impact_of(f)
    ia = {}
    if eps:
        GW.assume(ia, f"dEPS_{f.id}", round(eps, 2), "model output: base-case |dEPS| of this row's impact formula, "
                                                     "USD per share")
        GW.assume(ia, f"dOI_{f.id}", round(oi, 1), "model output: base-case |dOI| of this row's impact formula, USD M")
    imp = Claim(f"{eps:.2f} per share; dOI {oi:,.1f}" if eps else "not quantified", [], assumptions=ia,
                where=f"impact/{f.id}")
    a = share_asked(f)
    aa = GW.assume({}, f"a_{f.id}", round(a, 2), "obscurity term a (analyst share asked): "
                   + str((f.vector or {}).get("a_source") or "no topic match; 1.0 by default"))
    share = Claim(f"{a:.2f}", [], assumptions=aa, where=f"share/{f.id}")
    return sent, form, imp, share


def _cell(s):
    return " ".join(str(s or "").split()).replace("|", "/")


def merge_facts(rows):
    """One fact, one row: rows sharing a fact_key (a statistical flag and its twin, or a nugget and the detector row it
    enriches) keep the larger-impact row; the others are listed as merged into it, not ranked. Returns (kept, merged)."""
    kept, merged, seen = [], [], {}
    for f in rank(rows):
        k = getattr(f, "fact_key", "") or ""
        if k and k in seen:
            f.merged_into = seen[k].id
            merged.append(f)
            continue
        if k:
            seen[k] = f
        kept.append(f)
    return kept, merged


def build(ticker, rows, public=False):
    """(markdown, json dict) for one ticker's gated Scored rows."""
    ranked, merged = merge_facts(rows)
    needle = pick_needle(ranked)
    per_row = [_claims(f) for f in ranked]
    flat = [c for cs in per_row for c in cs if c is not None]
    texts, order = claim_markup(flat)
    it = iter(texts)
    marked = []
    for cs in per_row:
        marked.append([next(it) if c is not None else "" for c in cs])
    summary = gate_document([{"where": c.where, "text": c.text, "citations": c.citations, "derived": c.derived,
                              "assumptions": c.assumptions} for c in flat])
    L = [f"# {ticker} findings ranked by dollar impact", "",
         "Rank basis: base-case |dEPS| (USD per share) from each finding's impact formula; ties by |dOI| (USD M). "
         "Sharpest Needle rule: " + NEEDLE_RULE + ".", ""]
    if needle is not None:
        i = ranked.index(needle)
        L += [f"**Sharpest Needle (rank {i + 1}):** {_cell(marked[i][0])}", ""]
    else:
        L += ["**Sharpest Needle:** none (no finding is quantified).", ""]
    L += ["| Rank | Finding | Impact math | Base-case abs dEPS (USD/share); abs dOI (USD M) | Analyst share asked | Needle |",
          "|---|---|---|---|---|---|"]
    out_rows = []
    for i, (f, m) in enumerate(zip(ranked, marked), 1):
        is_n = f is needle
        L.append(f"| {i} | {_cell(m[0])} | {_cell(m[1]) or 'n/a'} | {_cell(m[2])} | {_cell(m[3])} | "
                 f"{'**Needle**' if is_n else ''} |")
        eps, oi = impact_of(f)
        out_rows.append({"rank": i, "id": f.id, "signal_kind": f.kind, "direction": f.direction,
                         "channel": f.impact.channel if f.impact else None, "sentence": f.sentence,
                         "sentence_marked": m[0], "formula_marked": m[1] or None,
                         "d_eps_base_abs": eps, "d_oi_base_abs": oi, "analyst_share_asked": share_asked(f),
                         "analyst_share_source": (f.vector or {}).get("a_source"), "confidence": f.confidence,
                         "not_quantified": f.not_quantified or None,
                         "needle_blocked": bool(getattr(f, "needle_blocked", False)), "needle": is_n,
                         "nugget": getattr(f, "nugget", None) or None,
                         "corroborated_by": getattr(f, "corroborated_by", None) or None,
                         "merged": [g.id for g in merged if g.merged_into == f.id] or None})
    md = "\n".join(L) + ("\n" + render_footnotes_md(order, public) if order else "\n")
    js = {"ticker": ticker, "rank_basis": RANK_BASIS, "needle_rule": NEEDLE_RULE,
          "needle_id": needle.id if needle is not None else None, "rows": out_rows,
          "merged_rows": [{"id": g.id, "merged_into": g.merged_into, "sentence": g.sentence,
                           "nugget": (getattr(g, "nugget", None) or {}).get("id")} for g in merged],
          "numeric_check": summary["numeric_check"], "failed": summary["failed"],
          "note": "internal FIND score S and league_v3 order candidates for review only; not pitched"}
    return md, js


def write(ticker, rows, out_dir, public=False):
    md, js = build(ticker, rows, public)
    (out_dir / "findings_table.md").write_text(md, encoding="utf-8")
    (out_dir / "findings_table.json").write_text(json.dumps(js, indent=2, default=str, ensure_ascii=False),
                                                 encoding="utf-8")
    return js
