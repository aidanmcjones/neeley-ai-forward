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
from agent.needle.cite.locator import Claim, json_default
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
    cur = _currency(f.ticker)
    ia = {}
    if eps and getattr(f, "mfn_placeholder", False):
        from .find import MFN_MARKER_LABEL
        GW.assume(ia, f"dEPS_{f.id}", round(eps, 2), MFN_MARKER_LABEL)
        GW.assume(ia, f"dOI_{f.id}", round(oi, 1), MFN_MARKER_LABEL, f"{cur} millions")
    elif eps:
        GW.assume(ia, f"dEPS_{f.id}", round(eps, 2), "model output: base-case |dEPS| of this row's impact formula, "
                                                     f"{cur} per share (reporting currency, not converted)")
        GW.assume(ia, f"dOI_{f.id}", round(oi, 1), f"model output: base-case |dOI| of this row's impact formula, {cur} M", f"{cur} millions")
    imp = Claim(f"{cur} {eps:.2f} per share; dOI {cur} {oi:,.1f}M" if eps else "not quantified", [], assumptions=ia,
                where=f"impact/{f.id}")
    a = share_asked(f)
    aa = GW.assume({}, f"a_{f.id}", round(a, 2), "obscurity term a (analyst share asked): "
                   + str((f.vector or {}).get("a_source") or "no topic match; 1.0 by default"))
    share = Claim(f"{a:.2f}", [], assumptions=aa, where=f"share/{f.id}")
    from . import peer as PEER
    ptxt, pc, pd_, pa, _ = PEER.gated(f)
    f.peer_comparison = ptxt
    pcl = Claim(ptxt, pc, derived=pd_, assumptions=pa, where=f"peer/{f.id}")
    return sent, form, imp, share, pcl


def _currency(ticker):
    """The reporting currency the row's dollars are in (NVO reports in DKK; no FX conversion without a cited rate)."""
    try:
        from . import data
        cur = str(data.company(ticker).fin_currency or "USD")
    except Exception:
        return "USD"
    return "USD" if cur.upper().startswith("USD") else cur.split()[0].upper()


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


PLAIN_REASON = "plain rule: biggest impact, least asked about"


def _red_team():
    """{ticker: (nugget id, one-line reason)} from docs/nuggets/best_needle.json (Parker's red-team read)."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "docs" / "nuggets" / "best_needle.json"
    try:
        d = json.loads(p.read_text())
    except Exception:
        return {}
    return {t: (i, (d.get("reason") or {}).get(t, "")) for t, i in (d.get("best_needle") or {}).items()}


def red_team_pick(ticker, ranked, merged):
    """(row, nugget id, reason) when Parker's best needle for the company is a gated, slide-ready row (or merged into
    one as the same fact), else (None, id, reason)."""
    nid, reason = _red_team().get(ticker, (None, ""))
    if not nid:
        return None, None, ""
    for f in ranked:
        nug = getattr(f, "nugget", None) or {}
        if nug.get("id") == nid:
            ok = bool(nug.get("slide_ready")) and nug.get("verdict") == "verified"
            return (f if ok else None), nid, reason
    for g in merged:      # merged into a kept row as one fact: the kept row carries the needle
        nug = getattr(g, "nugget", None) or {}
        if nug.get("id") == nid and nug.get("slide_ready") and nug.get("verdict") == "verified":
            keep = next((f for f in ranked if f.id == g.merged_into), None)
            return keep, nid, reason
    return None, nid, reason


def build(ticker, rows, public=False):
    """(markdown, json dict) for one ticker's gated Scored rows. The Sharpest Needle is Parker's red-team best needle
    when that row passes the gate and is slide-ready (the human read governs), else the plain rule."""
    ranked, merged = merge_facts(rows)
    plain = pick_needle(ranked)
    rt_row, rt_id, rt_reason = red_team_pick(ticker, ranked, merged)
    needle, source = (rt_row, "red_team") if rt_row is not None else (plain, "plain_rule")
    per_row = [_claims(f) for f in ranked]
    flat = [c for cs in per_row for c in cs if c is not None]
    reason_claim = None
    if needle is not None:
        if source == "red_team":
            from agent.needle.cite.gate import numeric_gate
            sent = per_row[ranked.index(needle)][0]
            txt = f"red-team read: {rt_reason}" if rt_reason else "red-team read (docs/red_team_v3_final.md)"
            res = numeric_gate([("reason", txt)], sent.citations, sent.derived, sent.assumptions)
            if not (res.passed or res.numeric_check["status"] in ("no_numbers", "unchecked")):
                txt = (f"red-team read: Parker's best needle for {ticker} ({rt_id}, docs/red_team_v3_final.md); his "
                       "one-line reason carries figures the gate does not support, so it is not printed")
            reason_claim = Claim(txt, sent.citations, derived=sent.derived, assumptions=sent.assumptions,
                                 where="needle_reason")
        else:
            reason_claim = Claim(PLAIN_REASON, [], where="needle_reason")
        flat.append(reason_claim)
    texts, order = claim_markup(flat)
    it = iter(texts)
    marked = []
    for cs in per_row:
        marked.append([next(it) if c is not None else "" for c in cs])
    reason_md = next(it) if reason_claim is not None else ""
    summary = gate_document([{"where": c.where, "text": c.text, "citations": c.citations, "derived": c.derived,
                              "assumptions": c.assumptions} for c in flat])
    L = [f"# {ticker} findings ranked by dollar impact", "",
         "Rank basis: base-case |dEPS| (per share, reporting currency) from each finding's impact formula; ties by |dOI| (millions). "
         "Sharpest Needle: Parker's red-team best needle when that row passes the gate and is slide-ready (the human "
         "read governs), else the plain rule: " + NEEDLE_RULE + ".", ""]
    if needle is not None:
        i = ranked.index(needle)
        L += [f"**Sharpest Needle (rank {i + 1}):** {_cell(marked[i][0])}", "", f"Why this needle: {_cell(reason_md)}", ""]
    else:
        L += ["**Sharpest Needle:** none (no finding is quantified).", ""]
    L += ["| Rank | Finding | Impact math | Base-case abs dEPS (per share); abs dOI (M) | Analyst share asked | "
          "Peer comparison | Needle |", "|---|---|---|---|---|---|---|"]
    out_rows = []
    for i, (f, m) in enumerate(zip(ranked, marked), 1):
        is_n = f is needle
        L.append(f"| {i} | {_cell(m[0])} | {_cell(m[1]) or 'n/a'} | {_cell(m[2])} | {_cell(m[3])} | {_cell(m[4])} | "
                 f"{'**Needle**' if is_n else ''} |")
        eps, oi = impact_of(f)
        out_rows.append({"rank": i, "id": f.id, "signal_kind": f.kind, "direction": f.direction,
                         "channel": f.impact.channel if f.impact else None, "sentence": f.sentence,
                         "sentence_marked": m[0], "formula_marked": m[1] or None,
                         "d_eps_base_abs": eps, "d_oi_base_abs": oi, "analyst_share_asked": share_asked(f),
                         "analyst_share_source": (f.vector or {}).get("a_source"), "confidence": f.confidence,
                         "not_quantified": f.not_quantified or None,
                         "needle_blocked": bool(getattr(f, "needle_blocked", False)), "needle": is_n,
                         "peer_comparison": getattr(f, "peer_comparison", None), "peer_comparison_marked": m[4],
                         "nugget": getattr(f, "nugget", None) or None,
                         "corroborated_by": getattr(f, "corroborated_by", None) or None,
                         "merged": [g.id for g in merged if g.merged_into == f.id] or None})
    md = "\n".join(L) + ("\n" + render_footnotes_md(order, public) if order else "\n")
    js = {"ticker": ticker, "rank_basis": RANK_BASIS, "needle_rule": NEEDLE_RULE,
          "needle_id": needle.id if needle is not None else None, "needle_source": source if needle is not None else None,
          "plain_rule_needle_id": plain.id if plain is not None else None,
          "red_team_needle_id": rt_row.id if rt_row is not None else None, "red_team_nugget_id": rt_id,
          "needle_reason": reason_claim.text if reason_claim is not None else None, "rows": out_rows,
          "merged_rows": [{"id": g.id, "merged_into": g.merged_into, "sentence": g.sentence,
                           "nugget": (getattr(g, "nugget", None) or {}).get("id")} for g in merged],
          "numeric_check": summary["numeric_check"], "failed": summary["failed"],
          "note": "internal FIND score S and league_v3 order candidates for review only; not pitched"}
    return md, js


def write(ticker, rows, out_dir, public=False):
    md, js = build(ticker, rows, public)
    (out_dir / "findings_table.md").write_text(md, encoding="utf-8")
    (out_dir / "findings_table.json").write_text(json.dumps(js, indent=2, default=json_default, ensure_ascii=False),
                                                 encoding="utf-8")
    return js
