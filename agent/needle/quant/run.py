"""FIND over the detectors' saved candidate findings; writes findings_v3, the pitch findings table and the internal
league table (no model call).

Pitch output per ticker: out/<T>/findings_table.md and .json, the gated rows ranked by base-case dollar impact with the
Sharpest Needle picked by one plain rule (findings_table.py; rank_basis "impact"). The FIND score S and league_v3 are
still computed and written: they order candidates for internal review and are not pitched.

  python -m agent.needle.quant.run --all            all 10 shortlist companies + out/league_v3.json, .md and
                                                    out/league_v3_robustness.json (the variant table)
  python -m agent.needle.quant.run --ticker LLY     one company (out/LLY/findings_v3.jsonl, rejected_v3.jsonl)
  python -m agent.needle.quant.run --all --detect   re-run the detectors first (agent.needle.run.detect)
  python -m agent.needle.quant.run --all --nuggets docs/nuggets   add nugget-miner rows as candidates

  python -m agent.needle.quant.run --all --public   footnotes rendered with licensed text withheld

Inputs: out/<T>/signals_<detector>.jsonl (the existing engine's candidates), the moat (env NEEDLE_MOAT), the
citation index (env CITATIONS_DB). Output per finding: every FIND component, citations, confidence, old S, and
numeric_check (agent.needle.cite.gate). The numeric gate runs after scoring and before the league: every number in
the sentence (with its peer comparison) and in the impact formula must be verified by a passing citation, derived
from cited operands, or a labelled assumption. A row that fails goes to out/<T>/rejected_v3.jsonl with its
numeric_check and "rejected_by": "numeric_gate", and is excluded from the top 5, from L and from the Sharpest Needle.
Rows with E = 0 or a drop guard go there too ("rejected_by": "no page evidence" / "drop guard").
"""

import argparse
import json
import subprocess
import time

from agent.needle.detect import OUT, SHORTLIST
from agent.needle.schema import Signal, read_jsonl

from agent.needle.cite.gate import gate_record

from . import data, find, findings_table, guards, league

DETECTORS = ["forensics", "drift", "calls", "labels", "supply"]


def _old_scores(ticker):
    """Old S per (kind, sentence) from the old scorer's out/<T>/findings.jsonl (fixed scorer, commit 4009a40)."""
    rows = read_jsonl(OUT / ticker / "findings.jsonl")
    return {(r["signal_kind"], r["finding"]): r["score"] for r in rows}


def _old_league():
    """The committed league table the team has seen (git HEAD out/league.json, pre-fix scorer)."""
    try:
        txt = subprocess.run(["git", "show", "HEAD:out/league.json"], capture_output=True, text=True,
                             cwd=str(data.ROOT), check=True).stdout
        rows = json.loads(txt)
    except Exception:
        p = OUT / "league.json"
        rows = json.loads(p.read_text()) if p.exists() else []
    rows = sorted(rows, key=lambda r: -r["score"])
    return {r["ticker"]: (r["score"], i + 1, r.get("sharpest_needle")) for i, r in enumerate(rows)}


GATE_TEXT = ["sentence", "impact.formula"]   # the prose the UI renders: sentence (with the peer comparison) and math
PUBLIC = False                                # --public: footnotes withhold licensed text (render public=True)
GATE_LOG = {}                                 # ticker -> {"passed", "total", "unsupported", "reasons"} (last run)


def gate_findings(fs):
    """[(Scored, record with numeric_check)] split into (passed, failed) by the numeric gate (fail closed)."""
    ok_rows, bad_rows = [], []
    for f in fs:
        f.public = PUBLIC
        try:
            rec, ok = gate_record(f.to_dict(), GATE_TEXT, "citations")
        except Exception as e:                   # fail closed: a row the gate cannot check is not shown
            rec, ok = dict(f.to_dict(), numeric_check={"status": "failed", "checked": 0, "total": 0, "verified": 0,
                                                       "derived": 0, "assumed": 0, "unsupported": [
                                                           {"value": None, "where": "record", "reason": f"gate error: {e}"}]}), False
        (ok_rows if ok else bad_rows).append((f, rec))
    return ok_rows, bad_rows


def score_ticker(ticker, write=True, extra_signals=None):
    co = data.company(ticker)
    old = _old_scores(ticker)
    shown, withheld, seen = [], [], set()
    ira_products = {d[1].split("/")[0].lower() for d in find.IRA_DRUGS if d[0] == ticker}
    sigs = [s for det in DETECTORS for s in read_jsonl(OUT / ticker / f"signals_{det}.jsonl", Signal)]
    sigs += [s for s in (extra_signals or []) if s.ticker == ticker]
    nid_map, nug_sigs = {}, []
    for sig in sigs:
        if sig.detector == "nuggets":
            nug_sigs.append(sig)
            continue
        if sig.kind == "trial_terminated" and not sig.meta.get("business_reason"):
            continue
        if sig.kind == "ira_exposed" and (sig.meta.get("product") or "").lower() in ira_products:
            continue   # the IRA generator scores this drug with the full channel
        key = (sig.kind, sig.detail, sig.evidence[0].source() if sig.evidence else "")
        if key in seen:
            continue
        seen.add(key)
        f = find.score_signal(sig, co)
        nid_map[needle_branch_id(sig)] = f
        if sig.kind in guards.RECEIVABLE_KINDS:      # thread #19 (c): footnote read before needle eligibility
            find.apply_receivables_read(f, guards.receivables_read(sig, [e.doc_id for e in sig.evidence]), co)
        f.old_S = old.get((sig.kind, sig.detail))
        dropped = False
        for g in guards.check(sig, sigs):
            find.apply_guard(f, g)
            dropped = dropped or g[0] == "drop"
        (shown if f.vector["E"] > 0 and not dropped and f.guard != "drop" else withheld).append(f)
    for f in find.ira_findings(ticker, co) + find.mfn_findings(ticker, co):
        (shown if f.vector["E"] > 0 else withheld).append(f)
    # nugget-miner rows (docs/nuggets): same ladder, impact math and gate; matched to the row they enrich
    nug_rows = []
    for sig in nug_sigs:
        f = find.score_nugget(sig, co)
        nug_rows.append(f)
        dropped = False
        for g in guards.check(sig, sigs):          # the detector guards apply to nugget rows by kind
            find.apply_guard(f, g)
            dropped = dropped or g[0] == "drop"
        (shown if f.vector["E"] > 0 and not dropped else withheld).append(f)
    NUGGET_LOG[ticker] = enrich(nug_rows, nid_map, shown + withheld)
    # numeric gate (docs/gate_wiring.md 1): after scoring, before the league; failed rows never reach the top 5
    passed, failed = gate_findings(shown)
    shown = [f for f, _ in passed]
    gated = failed
    if nug_rows:
        ok_ids = {f.id for f in shown}
        NUGGET_LOG[ticker].update({"rows": len(nug_rows), "shown_pass_gate": sum(f.id in ok_ids for f in nug_rows),
                                   "failed_gate": sum(f.id in {g.id for g, _ in failed} for f in nug_rows),
                                   "no_page_evidence": sum(any(f is w for w in withheld) for f in nug_rows)})
    GATE_LOG[ticker] = {"passed": len(passed), "total": len(passed) + len(failed),
                        "unsupported": sum(len(r["numeric_check"]["unsupported"]) for _, r in failed),
                        "failed": [{"id": f.id, "kind": f.kind, "S": f.S, "unsupported": r["numeric_check"]["unsupported"]}
                                   for f, r in failed]}
    shown.sort(key=lambda f: -f.S)
    # review R2: a text or call row mapped to a channel points at the row that carries that channel's dollars
    for f in shown:
        if f.not_quantified.startswith("mapped to"):
            tgt = next((g for g in shown if g.S > 0 and g.impact.channel == f.impact.channel and g is not f), None)
            f.flags.append(f"corroborates {tgt.id} ({tgt.kind})" if tgt else
                           f"no scored {f.impact.channel} row for {ticker}: not quantified")
    if not write:
        return co, shown, withheld + [f for f, _ in gated]
    d = OUT / ticker
    d.mkdir(parents=True, exist_ok=True)
    recs = {f.id: r for f, r in passed}
    with (d / "findings_v3.jsonl").open("w", encoding="utf-8") as fh:
        for f in shown:
            rec, _ = gate_record(f.to_dict(), GATE_TEXT, "citations") if f.id not in recs else (recs[f.id], True)
            fh.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
    with (d / "rejected_v3.jsonl").open("w", encoding="utf-8") as fh:
        for f, rec in gated:
            fh.write(json.dumps(dict(rec, rejected_by="numeric_gate"), default=str, ensure_ascii=False) + "\n")
        for f in withheld:
            f.public = PUBLIC
            rec, _ = gate_record(f.to_dict(), GATE_TEXT, "citations")
            why = "drop guard" if f.guard == "drop" else "no page evidence"
            fh.write(json.dumps(dict(rec, rejected_by=why), default=str, ensure_ascii=False) + "\n")
    # pitch output: the same gated rows ranked by dollar impact, needle by the plain rule (findings_table.py)
    findings_table.write(ticker, shown, d, PUBLIC)
    for old in ("findings_v2.jsonl", "rejected_v2.jsonl"):     # ungated v2 rows must not linger next to v3
        (d / old).unlink(missing_ok=True)
    g = GATE_LOG[ticker]
    print(f"{ticker} gate: {g['passed']}/{g['total']} passed, {g['unsupported']} numbers unsupported")
    return co, shown, withheld + [f for f, _ in gated]


def load_nuggets(path):
    """Parker's nugget-miner rows (docs/nuggets/<TICKER>.jsonl: the Finding schema plus signal_family, obscurity
    rung, case_fit, part2_hook) as candidate Signals. They go through the same scoring, guards and citation gate as
    detector signals; a nugget whose kind maps to no impact channel is kept as "not quantified". `path` is a file or
    a directory of *.jsonl files."""
    from pathlib import Path
    from agent.needle.schema import Evidence
    p = Path(path)
    files = sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
    bn_file = (p if p.is_dir() else p.parent) / "best_needle.json"
    best = json.loads(bn_file.read_text())["best_needle"] if bn_file.exists() else {}
    out = []
    for fp in files:
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            evs = [Evidence(doc_id=e.get("doc_id", ""), page=e.get("page"), quote=e.get("quote", ""),
                            speaker=e.get("speaker", ""), figures=list(e.get("figures") or [])) for e in r.get("evidence") or []]
            peer = r.get("peer") or {}
            meta = {k: r.get(k) for k in ("signal_family", "obscurity_rung", "case_fit", "part2_hook", "topics",
                                          "product", "id") if r.get(k) is not None}
            meta["source"] = f"nuggets:{fp.name}"
            if r.get("best_needle") is None and best:
                r["best_needle"] = best.get(str(r["ticker"]).upper()) == r.get("id")
            meta["nugget"] = r
            out.append(Signal(ticker=str(r["ticker"]).upper(), detector="nuggets", kind=r.get("signal_kind") or "nugget",
                              period=str(r.get("period") or ""), value=peer.get("metric_value"),
                              peer_median=peer.get("peer_median"), peer_z=peer.get("z"),
                              detail=r.get("finding") or r.get("sentence") or "", evidence=evs, meta=meta))
    return out


NUGGET_LOG = {}                               # ticker -> nugget ingest counts (last run)


def needle_branch_id(sig):
    """The needle branch's finding id for a detector Signal (agent/needle/score.py on origin/needle: ticker,
    detector and six digits of sha256(kind|detail)); nugget rows name the row they enrich by this id."""
    import hashlib
    six = int(hashlib.sha256("|".join((sig.kind, sig.detail)).encode()).hexdigest(), 16) % 10 ** 6
    return f"{sig.ticker}-{sig.detector}-{six:06d}"


def _page_match(nf, rows):
    """A detector row sharing a cited (document, page) with the nugget and printing one of its quoted figures."""
    ev = getattr(nf, "nugget_evidence", None) or []
    for f in rows:
        if f.detector == "nuggets":
            continue
        for c in f.citations:
            if c.page is None or not c.verification.ok:
                continue
            for e in ev:
                if e["page"] == c.page and e["doc"].split(":")[-1].split("/")[-1] == \
                        str(c.canonical_id).split(":")[-1].split("/")[-1] and \
                        any(str(x) in (c.quote or "") for x in e["figures"] if len(str(x)) >= 3):
                    return f
    return None


def enrich(nug_rows, nid_map, rows):
    """Match each nugget's `enriches` id to our row (needle-branch id, else the cited page and value). A match shares
    one fact key (one fact, one row in the league and the findings table) and the nugget's verified quotes are added
    to our row as corroboration. Returns counts."""
    by_nid = {(f.nugget or {}).get("id"): f for f in nug_rows}
    log = {"enriches": 0, "matched_by_id": 0, "matched_by_page": 0, "unmatched": []}
    for nf in nug_rows:
        tid = (nf.nugget or {}).get("enriches")
        if not tid:
            continue
        log["enriches"] += 1
        tgt = nid_map.get(tid) or by_nid.get(tid)
        how = "id"
        if tgt is None:
            tgt, how = _page_match(nf, rows), "page and value"
        if tgt is None or tgt is nf:
            log["unmatched"].append(tid)
            nf.flags.append(f"enriches {tid}: no matching row on this branch")
            continue
        log["matched_by_id" if how == "id" else "matched_by_page"] += 1
        key = tgt.fact_key or f"enrich:{tgt.id}"
        tgt.fact_key = nf.fact_key = key
        have = {c.cite_id for c in tgt.citations}
        add = [c for c in nf.citations if c.verification.ok and c.page is not None and c.cite_id not in have][:3]
        tgt.citations += add
        tgt.corroborated_by.append(nf.nugget.get("id"))
        tgt.flags.append(f"corroborated by nugget {nf.nugget.get('id')} ({len(add)} verified quote(s) added; "
                         f"matched by {how})")
        nf.flags.append(f"enriches {tgt.id} (needle-branch id {tid}, matched by {how}): one fact, counted once")
    return log


def _one(f, n=110):
    return (f.sentence if len(f.sentence) <= n else f.sentence[:n - 3] + "...").replace("|", "/")


def _v2():
    p = OUT / "league_v2.json"
    rows = json.loads(p.read_text()) if p.exists() else []
    return {r["ticker"]: (r["L"], r["rank"], r.get("needle_status")) for r in rows}


def league_rows(tickers, extra_signals=None, write=True):
    """League rows (sorted, ranked). write=False leaves findings_v2.jsonl untouched (robustness variants)."""
    old, v2 = _old_league(), _v2()
    rows = []
    for t in tickers:
        co, fs, wh = score_ticker(t, write=write, extra_signals=extra_signals)
        L, top, ne, blocks = league.league_score(fs)
        needle, status = league.sharpest_needle(fs)
        raw = sum(f.S for f in top)
        rows.append({"ticker": t, "L": L, "top5_sum": raw, "N_eff": ne, "blocks": blocks,
                     "largest_share": (top[0].S / raw) if raw else 0.0,
                     "n_blocks": len(blocks), "n_findings": len(fs), "n_withheld": len(wh),
                     "n_gate_rejected": GATE_LOG.get(t, {}).get("total", 0) - GATE_LOG.get(t, {}).get("passed", 0),
                     "gate_failed": GATE_LOG.get(t, {}).get("failed", []),
                     "n_scored": sum(f.S > 0 for f in fs), "n_not_quantified": sum(bool(f.not_quantified) for f in fs),
                     "n_guarded": sum(bool(f.guard) for f in fs + wh),
                     "comparable": co.comparable, "company_flags": co.flags,
                     "top": [{"id": f.id, "S": f.S, "kind": f.kind, "family": f.family.name, "block": f.family.block,
                              "confidence": f.confidence, "sentence": f.sentence, "M": f.vector["M"],
                              "O": f.vector["O"], "D": f.vector["D"], "E": f.vector["E"], "pi": f.vector["pi"],
                              "c": f.vector["c"], "flags": f.flags} for f in top],
                     "needle": None if needle is None else {"id": needle.id, "S": needle.S, "sentence": needle.sentence,
                                                           "O": needle.vector["O"], "D": needle.vector["D"],
                                                           "E": needle.vector["E"], "confidence": needle.confidence,
                                                           "kind": needle.kind, "flags": needle.flags},
                     "needle_status": status,
                     "n_pi_downgraded": sum(getattr(f, "pi_downgraded", False) for f in fs),
                     "n_strict_needle_candidates": sum(f.needle_eligible and f.S > 0 for f in fs),
                     "tariff_exposure": find.tariff_exposure(t),
                     "old_score": old.get(t, (None, None, None))[0], "old_rank": old.get(t, (None, None, None))[1],
                     "v2_L": v2.get(t, (None, None, None))[0], "v2_rank": v2.get(t, (None, None, None))[1],
                     "constants": {"Rev_TTM": co.rev_ttm, "t": co.tax, "D": co.shares, "sigma_EPS": co.sigma,
                                   "currency": co.currency, "annual_only": co.annual_only}})
    rows.sort(key=lambda r: -r["L"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


# ------------------------------------------------------------------ robustness (league_v3)
def _set(knobs):
    """Apply {(module, name): value} and return the previous values."""
    prev = {}
    for (mod, name), v in knobs.items():
        prev[(mod, name)] = getattr(mod, name)
        setattr(mod, name, v)
    return prev


def variants():
    from . import weights as W
    return [
        ("base", "v3 rules: H = 3, MFN directional at pi_min, IRA class rule, L = top-5 x N_eff/3", {}),
        ("raw_sum", "no concentration multiplier: rank by the raw top-5 sum", {}),
        ("mfn_universal", "MFN at Pfizer's universal 0.65% of US revenue with pi = 1 (the v2 rule)",
         {(find, "MFN_UNIVERSAL"): True}),
        ("amgn_rec_pi_min", "AMGN receivables row (gap +8.01 pts, trigger 8) at pi_min with the anchor size kept",
         {(find, "FORCE_PI_MIN"): {("AMGN", "receivables_outpace_revenue"): "keep_anchor"}}),
        ("amgn_rec_not_fired", "AMGN receivables row treated as below its trigger (v3 rule for unfired flags: S = 0)",
         {(find, "FORCE_PI_MIN"): {("AMGN", "receivables_outpace_revenue"): "not_fired"}}),
        ("H6", "obscurity half-life 6 months (the v2 base)", {(W, "H_MONTHS"): W.H_MONTHS_SENSITIVITY}),
        ("ira_spec", "IRA league value on the spec formula G x max(0, d - g_pre) instead of the class rule",
         {(find, "IRA_MODE"): "spec"}),
        ("c_anchor_half", "c = 0.5 on anchor rows too (consensus test not defined for them)",
         {(find, "C_ANCHOR_UNINFORMATIVE"): True}),
    ]


def robustness(tickers, extra_signals=None, base_rows=None):
    """{variant: {"label", "ranking": [(ticker, value)], "strict": n, "needles": {ticker: status}}}."""
    out = {}
    for key, label, knobs in variants():
        if key in ("base", "raw_sum") and base_rows is not None:
            rows = base_rows
        else:
            prev = _set(knobs)
            try:
                rows = league_rows(tickers, extra_signals, write=False)
            finally:
                _set(prev)
        val = "top5_sum" if key == "raw_sum" else "L"
        rk = sorted(rows, key=lambda r: -r[val])
        out[key] = {"label": label, "ranking": [(r["ticker"], r[val]) for r in rk],
                    "strict": sum(r["needle_status"] == "strict" for r in rows),
                    "needles": {r["ticker"]: r["needle_status"] for r in rows}}
    return out


def league_table(tickers, extra_signals=None, with_robustness=True):
    rows = league_rows(tickers, extra_signals, write=True)
    rob = robustness(tickers, extra_signals, base_rows=rows) if with_robustness else {}
    (OUT / "league_v3.json").write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    if rob:
        (OUT / "league_v3_robustness.json").write_text(json.dumps(rob, indent=2, default=str), encoding="utf-8")
    (OUT / "league_v3.md").write_text(render_md(rows, rob), encoding="utf-8")
    return rows


def render_robustness(rob):
    if not rob:
        return []
    L = ["## Robustness: the ranking under each variant", "",
         "| Variant | What changes | #1 | #2 | #3 | #4 | #5 | Strict needles |", "|---|---|---|---|---|---|---|---|"]
    for key, v in rob.items():
        cells = [f"{t} {x:.4f}" for t, x in v["ranking"][:5]]
        L.append(f"| {key} | {v['label']} | " + " | ".join(cells) + f" | {v['strict']} of {len(v['needles'])} |")
    leaders = sorted({v["ranking"][0][0] for v in rob.values()})
    L += ["", f"Leader across variants: {', '.join(leaders)}."]
    for pos in (1, 2, 3):
        at = sorted({v["ranking"][pos - 1][0] for v in rob.values()})
        L.append(f"Place {pos}: {', '.join(at)}{' (settled)' if len(at) == 1 else ' (unsettled)'}.")
    return L + [""]


def render_md(rows, rob=None):
    from . import weights as W
    no_needle = [r["ticker"] for r in rows if r["needle_status"] != "strict"]
    L = ["# League v3 (FIND after the two-round adversarial review)", "",
         f"As of {data.AS_OF.isoformat()}. L = (sum of top-5 S, one row per underlying fact) x min(1, N_eff / 3). "
         f"H = {W.H_MONTHS:g} months. MFN rows are directional at pi_min; IRA rows use the one class rule "
         "(impact.ira_class_rule). Rows without an impact channel are 'not quantified' (S = 0) and stay in "
         "findings_v2.jsonl. v2 columns: committed out/league_v2.json. The score is computed by code with no model "
         "call; the data layer, onboarding and the citation verifier were built with AI agents (see "
         "docs/league_v3_note.md).", "",
         "| Rank | Ticker | League L | Top-5 sum | N_eff | Blocks | Top finding | Sharpest Needle | v2 L | v2 rank |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        top = r["top"][0] if r["top"] else None
        tf = f"{_trim(top['sentence'])} (S {top['S']:.4f}, {top['confidence']})" if top else "none"
        nd = r["needle"]
        ns = f"{_trim(nd['sentence'])} (S {nd['S']:.4f}, D {nd['D']:.2f}, O {nd['O']:.2f}; {r['needle_status']})" \
            if nd else "none"
        L.append(f"| {r['rank']} | {r['ticker']} | {r['L']:.4f} | {r['top5_sum']:.4f} | {r['N_eff']:.2f} | "
                 f"{r['n_blocks']} ({''.join(sorted(r['blocks']))}) | {tf} | {ns} | "
                 f"{r['v2_L']:.4f} | {r['v2_rank']} |" if r["v2_L"] is not None else
                 f"| {r['rank']} | {r['ticker']} | {r['L']:.4f} | {r['top5_sum']:.4f} | {r['N_eff']:.2f} | "
                 f"{r['n_blocks']} | {tf} | {ns} | n/a | n/a |")
    L += ["", f"Strict Sharpest Needle (D >= 0.5, E >= 0.90, not LOW, z = 0, S > 0): {len(rows) - len(no_needle)} of "
          f"{len(rows)}; provisional or floor-relaxed: {', '.join(no_needle) or 'none'}.", "",
          "Rows downgraded to pi_min because they do not meet their backtest trigger (review A1): " +
          ", ".join(f"{r['ticker']} {r['n_pi_downgraded']}" for r in rows) + ".", "",
          "Blocks: A accounting, T text/disclosure, C calls, P policy/contractual, L label, X outside data, F footnote.",
          ""]
    L += render_robustness(rob)
    for r in rows:
        L.append(f"## {r['rank']}. {r['ticker']}  L = {r['L']:.4f}")
        c = r["constants"]
        L.append(f"Constants: Rev_TTM {c['Rev_TTM']:,.1f}, t {c['t']:.4f}, D {c['D']:,.1f}M, sigma_EPS "
                 f"{c['sigma_EPS']:.4f} {c['currency']}. Largest finding share {r['largest_share']:.0%}. Findings "
                 f"{r['n_findings']} ({r['n_scored']} scored, {r['n_not_quantified']} not quantified), withheld "
                 f"{r['n_withheld']} (numeric gate {r.get('n_gate_rejected', 0)}), guarded {r['n_guarded']}. Flags: {'; '.join(r['company_flags']) or 'none'}")
        L.append("")
        L.append("| # | S | M | D | O | E | pi | c | Conf | Block | Finding |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for i, f in enumerate(r["top"], 1):
            L.append(f"| {i} | {f['S']:.5f} | {f['M']:.3f} | {f['D']:.3f} | {f['O']:.3f} | {f['E']:.3f} | "
                     f"{f['pi']:.4f} | {f['c']:.2f} | {f['confidence']} | {f['block']} | {_trim(f['sentence'], 160)} |")
        L.append("")
    return "\n".join(L) + "\n"


def _trim(s, n=100):
    s = " ".join(str(s).split()).replace("|", "/")
    return s if len(s) <= n else s[:n - 3] + "..."


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--detect", action="store_true", help="re-run the detectors and the old scorer first")
    ap.add_argument("--nuggets", help="nugget-miner JSONL file or directory (docs/nuggets): extra candidate findings")
    ap.add_argument("--public", action="store_true", help="render footnotes with licensed text withheld (public build)")
    a = ap.parse_args()
    global PUBLIC
    PUBLIC = a.public
    extra = load_nuggets(a.nuggets) if a.nuggets else None
    tickers = SHORTLIST if a.all or not a.ticker else [a.ticker.upper()]
    t0 = time.time()
    if a.detect:
        from agent.needle import score as old_score
        from agent.needle.run import detect
        for t in tickers:
            detect(t)
            old_score.score_ticker(t)
    if len(tickers) > 1:
        for r in league_table(tickers, extra_signals=extra):
            nd = r["needle"]
            print(f"{r['rank']:2d} {r['ticker']:5s} L {r['L']:.4f}  top5 {r['top5_sum']:.4f}  N_eff {r['N_eff']:.2f}  "
                  f"old {r['old_score']} (#{r['old_rank']})  needle[{r['needle_status']}]: "
                  f"{(nd['sentence'][:70] if nd else 'none')}")
    else:
        co, fs, wh = score_ticker(tickers[0], extra_signals=extra)
        for f in fs[:10]:
            print(f"{f.S:.5f} M {f.vector['M']:.3f} O {f.vector['O']:.3f} E {f.vector['E']:.2f} pi {f.vector['pi']:.4f} "
                  f"{f.confidence:6s} {f.sentence[:90]}")
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
