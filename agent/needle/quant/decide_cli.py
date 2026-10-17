"""Evaluate candidate CEO moves for one ticker and write out/<T>/decide.json and out/<T>/decide.md.

    python -m agent.needle.quant.decide_cli --ticker LLY --findings out/LLY/findings_v3.jsonl --moves moves.json [--public]

--findings accepts findings_v3.jsonl rows (gated FIND rows) and the old out/<T>/findings.jsonl rows (Finding shape).
Every number in decide.md is a cell checked by the numeric gate (agent.needle.cite.gate.gate_document): verified by a
passing citation (company citations are re-verified, never trusted from the moves file), derived from cited or
labelled operands, or labelled an assumption (external benchmarks, model outputs, team inputs). If any headline cell
fails, decide.md is not written: decide_rejected.md lists the failures and the exit code is 2. finding_ids that do
not resolve against the findings file also exit 2 (review D8). decide.json carries numeric_check. On every exit 2 any
decide.json and decide.md left by an earlier run are deleted first (a stale file must never be read as current); the
rejected run's JSON goes to decide_rejected.json.
--moves is JSON (or YAML when PyYAML is installed): {"as_of", "cash_and_equivalents", "moves": [...]} or a bare list.
See docs/examples/moves_LLY.json.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from agent.needle.cite.locator import Claim
from agent.needle.cite.render import render_markdown
from agent.needle.quant import decide as D
from agent.needle.quant import kill as K
from agent.needle.quant.moves import PAYBACK_SEARCH, SCENARIOS, WINDOW, get_template, r_monthly


def load_findings(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return D.normalize_findings(rows)


def load_moves(path):
    text = Path(path).read_text()
    if str(path).endswith((".yaml", ".yml")):
        import yaml  # optional dependency
        spec = yaml.safe_load(text)
    else:
        spec = json.loads(text)
    return {"moves": spec} if isinstance(spec, list) else spec


def _num(spec):
    return spec["value"] if isinstance(spec, dict) else spec


def run(ticker, findings, spec, as_of=None, cash=None):
    cash_spec = spec.get("cash_and_equivalents")
    cash = cash if cash is not None else (_num(cash_spec) if cash_spec is not None else None)
    results = []
    for mv in spec["moves"]:
        t = get_template(mv["template"])
        results.append(D.evaluate_move(
            t, mv.get("params", {}), findings, name=mv.get("name"), capability=mv.get("capability"),
            stakeholders=mv.get("stakeholders"), finding_ids=mv.get("finding_ids"), why=mv.get("why", ""),
            context=dict(mv.get("context") or {}, ticker=ticker)))
    sel = D.select_move(results, cash)
    ranked = sorted(results, key=lambda r: r.ev, reverse=True)   # statuses were set by select_move
    cash_claim = None
    if isinstance(cash_spec, dict) and cash_spec.get("citation"):
        c = D.citation_from_dict(cash_spec["citation"], cash_spec["value"], "USD millions")
        cash_claim = Claim(f"cash and equivalents {cash_spec['value']:,} (latest balance sheet)", [c])
    return {"ticker": ticker, "as_of": as_of or spec.get("as_of") or str(date.today()), "cash": cash, "cash_claim": cash_claim,
            "selection": sel, "ranked": ranked, "demo": bool(spec.get("demo")),
            "header_note": str(spec.get("header_note") or (DEMO_NOTE if spec.get("demo") else ""))}


DEMO_NOTE = ("Pipeline demonstration for the default ticker; not the team's Part 2 recommendation, which follows the "
             "company pick.")


def kill_table(result, context=None):
    """Kill signals with, where the rx tables have a row, the chosen product's latest-year baseline (cited facts row).
    The ZS thresholds stay the rule; a baseline says where the product starts."""
    base = {}
    if context and context.get("product"):
        try:
            from agent.needle.quant import verified_tables as V
            base = V.rx_baselines(context["product"])
        except Exception:
            base = {}
    rows = []
    for sg in K.signals_for(result):
        rev = K.revise_ev(result, [sg.id])
        rows.append({"id": sg.id, "signal": sg.name, "threshold": sg.threshold, "source": sg.source, "lag": sg.lag,
                     "check_month": sg.check_month, "action": sg.action, "basis": sg.basis,
                     "p_posterior": rev.p_posterior, "ev_remaining_prior": rev.ev_remaining_prior,
                     "ev_revised": rev.ev_revised, "ev_revised_total": rev.ev_revised_total, "stop": rev.stop,
                     "baseline": base.get(sg.id)})
    used = {sg.id for sg in K.signals_for(result)}
    extra = [v for k, v in base.items() if k not in used]
    if extra:
        rows.append({"id": "rx_context", "signal": "Prescriber and payer baselines (rx tables)", "threshold": "context",
                     "source": "CMS Part D / Part B PUF, formulary files, Open Payments", "lag": "Part D PUF about 18 months",
                     "check_month": 0, "action": "review", "basis": "", "p_posterior": {}, "ev_remaining_prior": 0.0,
                     "ev_revised": 0.0, "ev_revised_total": 0.0, "stop": False,
                     "baseline": None, "context": extra})
    return rows


def f1(x):
    return f"{x:,.1f}"


# --------------------------------------------------------------------------------------------------------------
# Gated document (docs/gate_wiring.md 3): every number in decide.md is a cell that the numeric gate classifies
# --------------------------------------------------------------------------------------------------------------

TOP20 = {"top20": {"value": "20", "unit": "%", "label": "definition: claims share of the top 20% of prescribers "
                                                         "(rx/prescriber_concentration.csv column top20pct_share)"}}
MODEL = "model output: computed by the DECIDE cash model (agent/needle/quant/moves.py {code}) from the inputs listed"


class Doc:
    """Collects gated cells. cell() returns a placeholder; render() replaces each with the marked-up text (one
    footnote numbering for the whole document) and appends the Sources list."""

    def __init__(self, public=False):
        self.items, self.public = [], public

    def cell(self, section, where, text, cites=(), derived=None, assumptions=None, dates=""):
        text = str(text)
        cites = [c for c in cites if getattr(c, "verification", None) is not None and c.verification.ok]
        self.items.append({"section": section, "where": where, "text": text, "citations": cites,
                           "derived": derived or {}, "assumptions": assumptions or {}, "dates": dates})
        return f"\x00{len(self.items) - 1}\x00"

    def sections(self):
        out = {}
        for it in self.items:
            out.setdefault(it["section"], []).append({k: it[k] for k in ("where", "text", "citations", "derived",
                                                                         "assumptions")})
        return out

    def claims(self):
        return [Claim(it["text"], it["citations"], derived=it["derived"], assumptions=it["assumptions"],
                      dates=it.get("dates", "")) for it in self.items]

    def render(self, md):
        import re
        from agent.needle.cite.render import claim_markup, render_footnotes_md
        texts, order = claim_markup(self.claims())
        body = re.sub("\x00(\\d+)\x00", lambda m: texts[int(m.group(1))], md)
        return body + ("\n" + render_footnotes_md(order, self.public) if order else "")


def _derived(value, expr, ops, unit=""):
    from agent.needle.cite.gate import derived_entry
    return derived_entry(value, expr, ops, unit)


def move_maps(r):
    """(derived, assumptions) for one move: compositions are derived, model leaves and benchmarks are labelled."""
    A = dict(D.global_assumptions())
    lab = MODEL.format(code=r.code)

    def leaf(key, v, unit=""):
        A[key] = {"value": f"{float(v):.12g}", "label": lab, "unit": unit}
        return {"value": float(v), "assumption": lab}
    for i in r.inputs:
        A.update(D.input_assumptions(i, [c for c in r.citations if c.cite_id in i.citation_ids]))
    Dm = {}
    for i in r.inputs:
        Dm.update(i.derived or {})
    # review verify2 4: PV pieces, payback month and cash at risk are compositions, derived from the monthly model
    # rows (labelled model outputs) and the labelled WACC, never a bare [assumption]
    Dm["r_mo"] = _derived(r_monthly(r.wacc), "(1 + w) ** (1 / 12) - 1",
                          {"w": {"value": r.wacc, "assumption": D.benchmark_label("wacc")}})

    def month(key, v, m, what):
        return {"value": float(v), "assumption": lab + f" ({what}, month {m})"}
    for s in SCENARIOS:
        rows_s = r.tables[s]
        for part, sel in (("pvin", lambda m: m <= WINDOW), ("pvtv", lambda m: m > WINDOW)):
            ops = {f"n{x['month']}": month(f"{s}_{x['month']}", x["net"], x["month"], f"{s} expected net cash flow")
                   for x in rows_s if sel(x["month"])}
            expr = " + ".join(f"n{x['month']} * (1 + r) ** -{x['month']}" for x in rows_s if sel(x["month"])) or "0"
            ops["r"] = {"derived": "r_mo"}
            Dm[f"{part}_{s}"] = _derived(r.in_window_pv[s] if part == "pvin" else r.tv_pv[s], expr, ops)
        Dm[f"ev_{s}"] = _derived(r.ev_by_scenario[s], "a + b", {"a": {"derived": f"pvin_{s}"},
                                                                 "b": {"derived": f"pvtv_{s}"}})
    p = r.p_scenario
    Dm["ev"] = _derived(r.ev, "pb * eb + pm * em + pu * eu", {
        "pb": {"value": p["bear"], "assumption": D.benchmark_label("p_bear")},
        "pm": {"value": p["base"], "assumption": D.benchmark_label("p_base")},
        "pu": {"value": p["bull"], "assumption": D.benchmark_label("p_bull")},
        "eb": {"derived": "ev_bear"}, "em": {"derived": "ev_base"}, "eu": {"derived": "ev_bull"}})
    Dm["spread"] = _derived(r.spread, "u - b", {"u": {"derived": "ev_bull"}, "b": {"derived": "ev_bear"}})
    lines = {k: v for k, v in r.budget.items() if not k.startswith("total")}
    if lines:
        Dm["budget_total"] = _derived(sum(lines.values()), " + ".join(f"l{i}" for i in range(len(lines))),
                                      {f"l{i}": leaf(f"budget_{k}", v) for i, (k, v) in enumerate(lines.items())})
    co, ci = (r.car_parts or {}).get("out") or [], (r.car_parts or {}).get("in") or []
    if co:
        ops = {f"o{m}": month("", v, m, "bear non-avoidable outflow before the first readout") for m, v in enumerate(co, 1)}
        ops.update({f"i{m}": month("", v, m, "bear inflow before the first readout") for m, v in enumerate(ci, 1)})
        Dm["car"] = _derived(r.car, f"max(0, ({' + '.join(f'o{m}' for m in range(1, len(co) + 1))}) - "
                                    f"({' + '.join(f'i{m}' for m in range(1, len(ci) + 1)) or '0'}))", ops)
    else:
        leaf("car", r.car)
    if r.payback_month is not None:
        horizon = min(len(r.expected_cf["base"]), PAYBACK_SEARCH)
        ops = {"pb": {"value": r.p_scenario["bear"], "assumption": D.benchmark_label("p_bear")},
               "pm": {"value": r.p_scenario["base"], "assumption": D.benchmark_label("p_base")},
               "pu": {"value": r.p_scenario["bull"], "assumption": D.benchmark_label("p_bull")}, "r": {"derived": "r_mo"}}
        terms = []
        for m in range(1, min(horizon, r.payback_month) + 1):
            for sc, k in (("bear", "b"), ("base", "m"), ("bull", "u")):
                ops[f"{k}{m}"] = month("", r.expected_cf[sc][m - 1], m, f"{sc} expected net cash flow")
            terms.append(f"(pb * b{m} + pm * m{m} + pu * u{m}) * (1 + r) ** -{m}")
        Dm["payback"] = _derived(r.payback_month, f"payback({', '.join(terms)})", ops)
    parts = list(r.mcda_parts.items())
    Dm["mcda"] = _derived(r.mcda, " + ".join(f"0.25 * x{i}" for i in range(len(parts))),
                          {f"x{i}": leaf(f"mcda_{k}", v) for i, (k, v) in enumerate(parts)})
    A["mcda_w"] = {"value": "0.25", "label": "design: MCDA weights 0.25 each (spec 5.2)"}
    probs = [i for i in r.inputs if str(i.unit) == "probability" and isinstance(i.value, (int, float))
             and i.name.startswith("p_")]
    prod = 1.0
    for i in probs:
        prod *= float(i.value)
    if probs and abs(prod - r.p_alive_end) < 1e-9:
        def _op(i):
            if i.derived:
                return {"derived": next(iter(i.derived))}
            ok = [c for c in r.citations if c.cite_id in i.citation_ids and c.verification.ok]
            if ok:
                return (float(i.value), ok[0])
            return {"value": float(i.value), "assumption": A.get(f"{i.name}#0", {}).get("label")
                    or D.benchmark_label("p_nonnme_ph3")}
        Dm["p_alive"] = _derived(r.p_alive_end, " * ".join(f"q{k}" for k in range(len(probs))),
                                 {f"q{k}": _op(i) for k, i in enumerate(probs)})
    else:
        leaf("p_alive", r.p_alive_end)
    rows = r.tables["base"]
    for q in range(8):
        seg = rows[q * 3:(q + 1) * 3]
        for col, sign in (("cf_in", 1), ("cf_out", -1), ("net", 1)):
            Dm[f"q{q + 1}_{col}"] = _derived(sign * sum(x[col] for x in seg), f"{sign} * (m1 + m2 + m3)",
                                             {f"m{j + 1}": {"value": x[col], "assumption": lab + f" (month {x['month']})"}
                                              for j, x in enumerate(seg)})
    return Dm, A


def merged_maps(results):
    Dm, A = {}, {}
    for i, r in enumerate(results):
        d, a = move_maps(r)
        Dm.update({f"m{i}_{k}": _rekey(v, i) for k, v in d.items()})
        A.update({f"m{i}_{k}": v for k, v in a.items()})
    return Dm, A


def _rekey(e, i):
    e = dict(e)
    e["operands"] = {k: ({"derived": f"m{i}_{o['derived']}"} if isinstance(o, dict) and "derived" in o else o)
                     for k, o in (e.get("operands") or {}).items()}
    return e


def _gate_line(doc, section, where, text, cites, Dm, A):
    """A secondary prose line (flag, note, binding reason): gated alone; a line that fails is withheld from the
    document (replaced by a notice), never printed with an unsupported number."""
    from agent.needle.cite.gate import numeric_gate
    ok = [c for c in cites if c.verification.ok]
    res = numeric_gate([(where, text)], ok, Dm, A)
    if res.passed or res.numeric_check["status"] == "unchecked":
        return doc.cell(section, where, text, ok, Dm, A), None
    return ("(withheld by the numeric gate: a number in this line is not supported; see decide.json)"), {"where": where, "text": text, "numeric_check": res.numeric_check}


def build_md(out, findings, public=False):
    """(markdown, gate summary, withheld lines). Every number is a gated cell; see docs/gate_wiring.md 3."""
    sel, T = out["selection"], out["ticker"]
    c = sel.top          # the chosen move, or the least-bad option when no candidate has EV above zero
    doc = Doc(public)
    by_id = {D.finding_id(f): f for f in findings}
    Dc, Ac = move_maps(c)
    Dall, Aall = merged_maps([c] + sel.rejected)
    try:     # company constants (TTM ETR t, Rev_TTM, D) derived from their XBRL operands, as FIND does
        from agent.needle.quant import data, gatewire as GW
        cd, ca = GW.company_maps(data.company(T), {}, {})
        for m in (Dc, Dall):
            m.update(cd)
        for m in (Ac, Aall):
            m.update(ca)
    except Exception:
        pass
    for m in (Ac, Aall):
        m["window"] = {"value": "24", "label": "design: the case's 24-month decision window"}
        m["partd_lag"] = {"value": "18", "label": "CMS Part D Prescriber PUF publication lag, about 18 months (assumption)"}
    withheld = []

    def line(section, where, text, cites=(), dm=None, am=None):
        t, w = _gate_line(doc, section, where, text, cites, Dall if dm is None else dm, Aall if am is None else am)
        if w:
            withheld.append(w)
        return t

    def cell(section, where, text, cites=(), derived=Dc, assumptions=Ac):
        return doc.cell(section, where, text, cites, derived, assumptions)
    p = c.p_scenario
    L = [f"# Decide: {T} 24-month CEO move (as of {out['as_of']})", ""]
    if out.get("header_note"):
        L += ["> " + line("header", "header_note", out["header_note"], (), {}, {}), ""]
    L += [
         cell("header", "header", f"All dollars USD millions. EV is present value at {out['as_of']} at WACC {c.wacc:.2%}, "
              f"scenario weights {p['bear']:.2f} / {p['base']:.2f} / {p['bull']:.2f} (bear / base / bull)."), "",
         ]
    if sel.chosen is None:
        L += ["## No candidate clears the hurdle; least-bad option: " + c.name + " (EV "
              + cell("header", "least_bad_ev", f1(c.ev), (), Dall, Aall) + ")", ""]
    else:
        L += [(f"## Chosen move (pipeline demonstration): {c.name}" if out.get("demo") else f"## Recommended move: {c.name}"),
              ""]
    L += ["Selection rule: " + line("selection", "selection_rule", sel.rule) + ".", ""]
    if c.why:
        # the moves file's narrative: only the addressed findings' passing citations can support its numbers
        fc = [x for fid in c.finding_ids for x in (D.finding_citations(by_id[fid]) if fid in by_id else [])]
        L += [line("why", "why", c.why, fc, {}, {}), ""]
    L += ["Part 1 findings that drive it:", ""]
    for fid in c.finding_ids:
        f = by_id.get(fid, {})
        sent = f.get("sentence") or f.get("finding", "")
        cits = D.finding_citations(f) if f else []
        from agent.needle.cite.gate import numeric_gate
        res = numeric_gate([("finding", sent)], [x for x in cits if x.verification.ok], f.get("derived"),
                           f.get("assumptions"))
        if res.passed or res.numeric_check["status"] == "unchecked":
            txt = doc.cell("findings", f"finding/{fid}", sent[:300], cits, f.get("derived"), f.get("assumptions"))
        else:
            txt = "(sentence withheld by the numeric gate: its numbers are not supported by a passing citation)"
            withheld.append({"where": f"finding/{fid}", "text": sent, "numeric_check": res.numeric_check})
        L.append(f"- {fid} ({D.finding_kind(f)}): {txt}")
    if not c.finding_ids:
        L.append("- none: this move addresses no Part 1 finding and cannot be recommended")
    L += ["", "### Budget (undiscounted, first 24 months)", "", "| Line | USD M |", "|---|---|"]
    for k, v in c.budget.items():
        L.append(f"| {k} | {cell('budget', f'budget/{k}', f1(v))} |")
    cash_txt = ""
    if out["cash"] is not None:
        cc = out["cash_claim"].citations if out["cash_claim"] else []
        cash_txt = "; cash and equivalents " + cell("budget", "budget/cash", f"{out['cash']:,.0f}" if float(out["cash"]).is_integer() else f1(out["cash"]), cc)
    L += ["", "Cash at risk (bear scenario, technical failure at the first readout, net of inflows and avoidable "
          f"payments): {cell('budget', 'budget/car', f1(c.car))}" + cash_txt, "", "### Return math, line by line", ""]
    for i, n in enumerate(c.notes):
        L.append(f"- {line('notes', f'notes[{i}]', n, (), Dc, Ac)}")
    L += ["", "| Scenario | Revenue multiplier | PV months 1-24 | PV terminal value (month 25 on) | Scenario EV |",
          "|---|---|---|---|---|"]
    from agent.needle.quant.moves import MULT_SCENARIO
    for s in SCENARIOS:
        L.append(f"| {s} | {cell('scenarios', f'scenarios/{s}/mult', MULT_SCENARIO[s])} | "
                 f"{cell('scenarios', f'scenarios/{s}/pv_in', f1(c.in_window_pv[s]))} | "
                 f"{cell('scenarios', f'scenarios/{s}/pv_tv', f1(c.tv_pv[s]))} | "
                 f"{cell('scenarios', f'scenarios/{s}/ev', f1(c.ev_by_scenario[s]))} |")
    L += ["", cell("five numbers", "ev_line", f"EV = {p['bear']:.2f} x {f1(c.ev_by_scenario['bear'])} + {p['base']:.2f} x "
                   f"{f1(c.ev_by_scenario['base'])} + {p['bull']:.2f} x {f1(c.ev_by_scenario['bull'])} = {f1(c.ev)}"),
          cell("five numbers", "spread_line", f"Scenario EV spread = EV(bull only) - EV(bear only) = "
                                              f"{f1(c.ev_by_scenario['bull'])} - {f1(c.ev_by_scenario['bear'])} = {f1(c.spread)}"),
          "Technical P(success to the end of the plan) = " + cell("five numbers", "p_alive", f"{c.p_alive_end:.4f}"), "",
          "Base-scenario expected cash flow by quarter (months 1-24, undiscounted, USD M):", "",
          "| Quarter | Inflow (risk-weighted) | Outflow (risk-weighted) | Net |", "|---|---|---|---|"]
    rows = c.tables["base"]
    for q in range(8):
        seg = rows[q * 3:(q + 1) * 3]
        L.append(f"| Q{q + 1} | {cell('cash flow', f'cf/Q{q + 1}/in', f1(sum(x['cf_in'] for x in seg)))} | "
                 f"{cell('cash flow', f'cf/Q{q + 1}/out', f1(-sum(x['cf_out'] for x in seg)))} | "
                 f"{cell('cash flow', f'cf/Q{q + 1}/net', f1(sum(x['net'] for x in seg)))} |")
    L += ["", "Inputs:", "", "| Input | Value | Unit | Kind |", "|---|---|---|---|"]
    for i in c.inputs:
        cl = [x for x in c.citations if x.cite_id in i.citation_ids]
        L.append(f"| {i.name} | {cell('inputs', f'inputs/{i.name}', D._fmt_val(i.value), cl, dict(Dc, **(i.derived or {})), D.input_assumptions(i, cl))} "
                 f"| {i.unit} | {i.kind}{' (' + i.finding_id + ')' if i.finding_id else ''} |")
    L += ["", "## Five numbers: " + ("chosen move" if sel.chosen is not None else "least-bad option")
          + " and the two rejected alternatives", "",
          "| Move | EV | Downside cash at risk | Payback | Scenario EV spread | MCDA |", "|---|---|---|---|---|---|"]
    for r in [c] + sel.rejected:
        pb = "none in the payback search window" if r.payback_month is None else "month " + cell("five numbers", f"five/{r.name}/payback",
                                                                               r.payback_month, (), Dall, Aall)
        L.append(f"| {r.name} | {cell('five numbers', f'five/{r.name}/EV', f1(r.ev), (), Dall, Aall)} | "
                 f"{cell('five numbers', f'five/{r.name}/CaR', f1(r.car), (), Dall, Aall)} | {pb} | "
                 f"{cell('five numbers', f'five/{r.name}/spread', f1(r.spread), (), Dall, Aall)} | "
                 f"{cell('five numbers', f'five/{r.name}/MCDA', f'{r.mcda:.3f}', (), Dall, Aall)} |")
    L.append("")
    for r in sel.rejected:
        L.append(f"- Rejected: **{r.name}**. Binding reason: {line('selection', f'binding/{r.name}', r.binding_reason)}.")
    for i, n in enumerate(sel.notes):
        L.append(f"- Note: {line('selection', f'selection_note[{i}]', n)}")
    L += ["", f"MCDA parts ({'chosen' if sel.chosen is not None else 'least-bad'}): " + cell("five numbers", "mcda_parts", ", ".join(
        f"{k} {v:.2f}" for k, v in c.mcda_parts.items()) + " (weights 0.25 each)") + ".", ""]
    L += ["## Kill signals (early 6-to-12-month signals that would prove the move wrong)", "",
          "| Signal | Threshold | Baseline (chosen product, latest year in the rx tables) | Source and lag | Check month | "
          "If breached |", "|---|---|---|---|---|---|"]
    from agent.needle.cite.numbers import tokenize
    for k in out["kill"]:
        if k["id"] == "rx_context":
            for j, (v, cit, txt) in enumerate(k.get("context") or []):
                bd = {}
                if v is not None and cit is not None and abs(v) <= 1:
                    from agent.needle.cite.gate import derived_entry
                    bd["pct"] = derived_entry(v * 100, "x * 100", {"x": (v, cit)}, "%")
                txt_cell = cell("kill signals", f"kill/rx_context[{j}]", txt, [cit] if cit else [], bd, TOP20)
                src = cell("kill signals", f"kill/rx_context[{j}]/source", f"{k['source']}; lag {k['lag']}", (), {},
                           {"lag": {"value": "18", "label": "CMS Part D PUF publication lag, about 18 months (assumption)"}})
                L.append(f"| {k['signal']} | context | {txt_cell} | {src} | n/a | human review |")
            continue
        ka = {f"thr{j}": {"value": f"{t.num * (-1 if t.neg else 1):.12g}", "unit": t.unit,
                          "label": f"kill-signal threshold (assumption; basis: {k['basis'] or 'design rule'})"}
              for j, t in enumerate(tokenize(k["threshold"]))}
        ka.update({f"lag{j}": {"value": f"{t.num:.12g}", "unit": t.unit,
                               "label": "data-source publication lag (kill.py; assumption)"}
                   for j, t in enumerate(tokenize(f"{k['source']}; lag {k['lag']}"))})
        ka["check"] = {"value": str(k["check_month"]), "label": "design: month the signal is checked (kill.py)"}
        if k["action"] == "review":
            eff = "human review; EV not auto-updated"
            ed = {}
        else:
            eff = (f"p(bear) {c.p_scenario['bear']:.2f} to {k['p_posterior']['bear']:.2f}; remaining EV "
                   f"{f1(k['ev_remaining_prior'])} to {f1(k['ev_revised'])}" + ("; STOP" if k["stop"] else ""))
            lab = "model output: kill-signal Bayes revision (agent/needle/quant/kill.py)"
            ka.update({"pb": {"value": f"{c.p_scenario['bear']:.12g}", "label": D.benchmark_label("p_bear")},
                       "pp": {"value": f"{k['p_posterior']['bear']:.12g}", "label": lab},
                       "er": {"value": f"{k['ev_remaining_prior']:.12g}", "label": lab},
                       "ev": {"value": f"{k['ev_revised']:.12g}", "label": lab}})
        w = f"kill/{k['id']}"
        bl = "no rx row: research threshold only"
        if k.get("baseline"):
            v, cit, txt = k["baseline"]
            bd = {}
            if v is not None and abs(v) <= 1:
                from agent.needle.cite.gate import derived_entry
                bd["pct"] = derived_entry(v * 100, "x * 100", {"x": (v, cit)}, "%")
            bl = cell("kill signals", w + "/baseline", txt, [cit], bd, TOP20)
        L.append(f"| {k['signal']} | {cell('kill signals', w + '/threshold', k['threshold'], (), {}, ka)} | {bl} | "
                 f"{cell('kill signals', w + '/source', k['source'] + '; lag ' + k['lag'], (), {}, ka)} | "
                 f"{cell('kill signals', w + '/check', k['check_month'], (), {}, ka)} | "
                 f"{cell('kill signals', w + '/effect', eff, (), {}, ka)} |")
    if any(r.code == "M4" for r in [c] + sel.rejected):
        try:
            from agent.needle.quant import verified_tables as V
            pm = V.pricing_moves(T)
        except Exception:
            pm = []
        if pm:
            L += ["", "Pricing-move precedents for the pricing and access move (verified table "
                      "costs/pricing_move_benchmarks.csv, verbatim magnitude):", ""]
            for j, (row, cit) in enumerate(pm):
                txt = f"{row.get('product')}: {row.get('move_type')}, {row.get('magnitude')} ({row.get('effect_type')})"
                L.append("- " + line("pricing precedents", f"pricing_moves[{j}]", txt, [cit], {}, {}))
    L += ["", line("kill signals", "part_d_note", K.PART_D_NOTE + " The baselines come from the chosen product's latest "
                   "year in the rx tables; the thresholds are the ZS rule, with the research constants as labelled "
                   "fallbacks."), "", "## Flags", ""]
    for r in [c] + sel.rejected:
        fa = {}
        for i in r.inputs:
            fa.update(D.input_assumptions(i, [x for x in r.citations if x.cite_id in i.citation_ids]))
        for i, fl in enumerate(r.flags):
            L.append(f"- {r.name}: {line('flags', f'flags/{r.name}[{i}]', fl, (), Dc, fa)}")
    L += ["", "## Inputs and Sources", ""]
    if out["cash_claim"]:
        L.append("- " + doc.cell("inputs", "cash_claim", out["cash_claim"].text, out["cash_claim"].citations))
    for r in [c] + sel.rejected:
        for i, cl in enumerate(r.claims):
            L.append(f"- ({r.name}) " + doc.cell("inputs", f"claims/{r.name}[{i}]", cl.text, cl.citations,
                                               cl.derived, cl.assumptions))
    bench = {}
    for r in [c] + sel.rejected:
        for x in r.citations:
            if x.canonical_id.startswith("benchmark:"):
                bench[x.canonical_id] = x
    if bench:
        L += ["", "External benchmarks (not in the citation index, unverified; every number taken from them is "
                  "labelled [assumption] above):", ""]
        for x in bench.values():
            L.append(f"- {x.canonical_id.split(':', 1)[1]}: {x.source_url or 'no URL'}")
    from agent.needle.cite.gate import gate_document
    summary = gate_document(doc.sections())
    return doc.render("\n".join(L) + "\n"), summary, withheld


def rejected_md(out, summary, withheld):
    L = [f"# Decide: {out['ticker']} rejected by the numeric gate", "",
         "decide.md is not written: at least one headline number is not verified by a passing citation, derived from "
         "cited operands, or labelled an assumption (docs/gate_wiring.md 3).", "", "## Failed items", ""]
    for it in summary["items"]:
        if it["passed"]:
            continue
        L.append(f"- {it['where']}: {it['text'][:160]}")
        for u in it["numeric_check"]["unsupported"]:
            L.append(f"    - {u['value']}: {u['reason']}")
    return "\n".join(L) + "\n"


def to_json(out, summary=None, withheld=()):
    sel = out["selection"]
    d = {"ticker": out["ticker"], "as_of": out["as_of"], "demo": out.get("demo", False),
         "header_note": out.get("header_note", ""), "cash_and_equivalents": out["cash"],
         "chosen": sel.chosen.to_dict() if sel.chosen is not None else None,
         "least_bad": sel.least_bad.name if sel.least_bad is not None else None,
         "least_bad_move": sel.least_bad.to_dict() if sel.least_bad is not None else None,
         "selection_rule": sel.rule, "rejected": [r.to_dict() for r in sel.rejected],
         "ranked": [{"name": r.name, "rank": r.rank, "status": r.status, "binding_reason": r.binding_reason, **r.five()} for r in out["ranked"]],
         "selection_notes": sel.notes, "kill_signals": out["kill"]}
    if summary is not None:
        d["numeric_check"] = summary["numeric_check"]
        d["numeric_items"] = [{k: it[k] for k in ("where", "text", "passed", "numeric_check")} for it in summary["items"]]
        d["withheld_lines"] = list(withheld)
    return d


def _clear_stale(d):
    """Exit-2 path: delete decide.json and decide.md from an earlier run before the rejection is written, so a stale
    recommendation can never be read as the current one."""
    for stale in ("decide.json", "decide.md"):
        (d / stale).unlink(missing_ok=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--findings", required=True)
    ap.add_argument("--moves", required=True)
    ap.add_argument("--out", default=None, help="output directory (default out/<TICKER>)")
    ap.add_argument("--cash", type=float, default=None, help="cash and equivalents, USD M (overrides the moves file)")
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--public", action="store_true", help="render footnotes with licensed text withheld (public build)")
    a = ap.parse_args(argv)
    findings = load_findings(a.findings)
    spec = load_moves(a.moves)
    d = Path(a.out or f"out/{a.ticker}")
    d.mkdir(parents=True, exist_ok=True)
    known = {D.finding_id(f) for f in findings}
    missing = sorted({fid for mv in spec["moves"] for fid in mv.get("finding_ids") or [] if fid not in known})
    if missing:      # review D8: a move's finding ids must resolve against the findings file
        _clear_stale(d)
        (d / "decide_rejected.md").write_text(
            f"# Decide: {a.ticker} rejected\n\nfinding_ids in {a.moves} do not resolve against {a.findings}: "
            + ", ".join(missing) + "\n")
        print(f"finding_ids do not resolve against {a.findings}: {', '.join(missing)}", file=sys.stderr)
        return 2
    out = run(a.ticker, findings, spec, a.as_of, a.cash)
    ctx = next((dict(mv.get("context") or {}, ticker=a.ticker) for mv in spec["moves"]
                if (mv.get("name") or get_template(mv["template"]).name) == out["selection"].top.name), {})
    out["kill"] = kill_table(out["selection"].top, ctx)
    md, summary, withheld = build_md(out, findings, a.public)
    js = json.dumps(to_json(out, summary, withheld), indent=2, default=str)
    if not summary["passed"]:
        _clear_stale(d)
        (d / "decide_rejected.json").write_text(js)
        (d / "decide_rejected.md").write_text(rejected_md(out, summary, withheld))
        nc = summary["numeric_check"]
        print(f"{a.ticker}: numeric gate failed ({len(nc['unsupported'])} unsupported of {nc['total']}); wrote "
              f"{d / 'decide_rejected.md'}", file=sys.stderr)
        return 2
    for stale in ("decide_rejected.md", "decide_rejected.json"):
        (d / stale).unlink(missing_ok=True)
    (d / "decide.json").write_text(js)
    (d / "decide.md").write_text(md)
    sel = out["selection"]
    c = sel.top
    print(f"{a.ticker}: {'chosen' if sel.chosen is not None else 'NO CANDIDATE CLEARS THE HURDLE; least-bad'} {c.name}: EV {c.ev:,.1f}, CaR {c.car:,.1f}, payback {c.payback_month}, spread {c.spread:,.1f}, MCDA {c.mcda:.3f}")
    print(f"  rule: {sel.rule}")
    for r in sel.rejected:
        print(f"  rejected {r.name}: EV {r.ev:,.1f}, CaR {r.car:,.1f}, payback {r.payback_month}, MCDA {r.mcda:.3f} ({r.binding_reason})")
    print(f"wrote {d / 'decide.json'} and {d / 'decide.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
