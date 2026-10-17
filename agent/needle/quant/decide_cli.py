"""Evaluate candidate CEO moves for one ticker and write out/<T>/decide.json and out/<T>/decide.md.

    python -m agent.needle.quant.decide_cli --ticker LLY --findings out/LLY/findings_v2.jsonl --moves moves.json

--findings accepts the new findings_v2.jsonl rows and the old out/<T>/findings.jsonl rows (Finding dataclass shape).
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
from agent.needle.quant.moves import SCENARIOS, WINDOW, get_template


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
            stakeholders=mv.get("stakeholders"), finding_ids=mv.get("finding_ids"), why=mv.get("why", "")))
    sel = D.select_move(results, cash)
    ranked = sorted(results, key=lambda r: r.ev, reverse=True)   # statuses were set by select_move
    cash_claim = None
    if isinstance(cash_spec, dict) and cash_spec.get("citation"):
        c = D.citation_from_dict(cash_spec["citation"], cash_spec["value"], "USD millions")
        cash_claim = Claim(f"cash and equivalents {cash_spec['value']:,} (latest balance sheet)", [c])
    return {"ticker": ticker, "as_of": as_of or spec.get("as_of") or str(date.today()), "cash": cash, "cash_claim": cash_claim,
            "selection": sel, "ranked": ranked}


def kill_table(result):
    rows = []
    for sg in K.signals_for(result):
        rev = K.revise_ev(result, [sg.id])
        rows.append({"id": sg.id, "signal": sg.name, "threshold": sg.threshold, "source": sg.source, "lag": sg.lag,
                     "check_month": sg.check_month, "action": sg.action, "basis": sg.basis,
                     "p_posterior": rev.p_posterior, "ev_remaining_prior": rev.ev_remaining_prior,
                     "ev_revised": rev.ev_revised, "ev_revised_total": rev.ev_revised_total, "stop": rev.stop})
    return rows


def f1(x):
    return f"{x:,.1f}"


def five_row(r):
    pb = "none within 120" if r.payback_month is None else f"month {r.payback_month}"
    return f"| {r.name} | {f1(r.ev)} | {f1(r.car)} | {pb} | {f1(r.spread)} | {r.mcda:.3f} |"


def build_md(out, findings):
    sel, T = out["selection"], out["ticker"]
    c = sel.chosen
    by_id = {D.finding_id(f): f for f in findings}
    L = [f"# Decide: {T} 24-month CEO move (as of {out['as_of']})", "",
         f"All dollars USD millions. EV is present value at {out['as_of']} at WACC {c.wacc:.2%}, scenario weights "
         f"{c.p_scenario['bear']:.2f} / {c.p_scenario['base']:.2f} / {c.p_scenario['bull']:.2f} (bear / base / bull).", "",
         f"## Recommended move: {c.name}", ""]
    if c.why:
        L += [c.why, ""]
    L += ["Part 1 findings that drive it:", ""]
    for fid in c.finding_ids:
        f = by_id.get(fid, {})
        L.append(f"- {fid} ({D.finding_kind(f)}): {f.get('finding', '')[:160]}")
    if not c.finding_ids:
        L.append("- none: this move addresses no Part 1 finding and cannot be recommended")
    L += ["", "### Budget (undiscounted, first 24 months)", "", "| Line | USD M |", "|---|---|"]
    for k, v in c.budget.items():
        L.append(f"| {k} | {f1(v)} |")
    L += ["", f"Cash at risk (bear scenario, technical failure at the first readout, net of inflows and avoidable payments): {f1(c.car)}"
          + (f"; cash and equivalents {f1(out['cash'])}" if out["cash"] is not None else ""), "",
          "### Return math, line by line", ""]
    for n in c.notes:
        L.append(f"- {n}")
    L += ["", "| Scenario | Revenue multiplier | PV months 1-24 | PV terminal value (month 25 on) | Scenario EV |", "|---|---|---|---|---|"]
    from agent.needle.quant.moves import MULT_SCENARIO
    for s in SCENARIOS:
        L.append(f"| {s} | {MULT_SCENARIO[s]} | {f1(c.in_window_pv[s])} | {f1(c.tv_pv[s])} | {f1(c.ev_by_scenario[s])} |")
    p = c.p_scenario
    L += ["", f"EV = {p['bear']:.2f} x {f1(c.ev_by_scenario['bear'])} + {p['base']:.2f} x {f1(c.ev_by_scenario['base'])} + "
          f"{p['bull']:.2f} x {f1(c.ev_by_scenario['bull'])} = **{f1(c.ev)}**",
          f"Scenario EV spread = EV(bull only) - EV(bear only) = {f1(c.ev_by_scenario['bull'])} - {f1(c.ev_by_scenario['bear'])} = {f1(c.spread)}",
          f"Technical P(success to the end of the plan) = {c.p_alive_end:.4f}", "",
          "Base-scenario expected cash flow by quarter (months 1-24, undiscounted, USD M):", "",
          "| Quarter | Inflow (risk-weighted) | Outflow (risk-weighted) | Net |", "|---|---|---|---|"]
    rows = c.tables["base"]
    for q in range(8):
        seg = rows[q * 3:(q + 1) * 3]
        L.append(f"| Q{q + 1} | {f1(sum(x['cf_in'] for x in seg))} | {f1(-sum(x['cf_out'] for x in seg))} | {f1(sum(x['net'] for x in seg))} |")
    L += ["", "Inputs:", "", "| Input | Value | Unit | Kind |", "|---|---|---|---|"]
    for i in c.inputs:
        L.append(f"| {i.name} | {i.value} | {i.unit} | {i.kind}{' (' + i.finding_id + ')' if i.finding_id else ''} |")
    L += ["", "## Five numbers: chosen move and the two rejected alternatives", "",
          "| Move | EV | Downside cash at risk | Payback | Scenario EV spread | MCDA |", "|---|---|---|---|---|---|", five_row(c)]
    for r in sel.rejected:
        L.append(five_row(r))
    L.append("")
    for r in sel.rejected:
        L.append(f"- Rejected: **{r.name}**. Binding reason: {r.binding_reason}.")
    for n in sel.notes:
        L.append(f"- Note: {n}")
    L += ["", "MCDA parts (chosen): " + ", ".join(f"{k} {v:.2f}" for k, v in c.mcda_parts.items()) + " (weights 0.25 each).", ""]
    L += ["## Kill signals (early 6-to-12-month signals that would prove the move wrong)", "",
          "| Signal | Threshold | Source and lag | Check month | If breached |", "|---|---|---|---|---|"]
    for k in out["kill"]:
        if k["action"] == "review":
            eff = "human review; EV not auto-updated"
        else:
            eff = (f"p(bear) {c.p_scenario['bear']:.2f} to {k['p_posterior']['bear']:.2f}; remaining EV "
                   f"{f1(k['ev_remaining_prior'])} to {f1(k['ev_revised'])}" + ("; STOP" if k["stop"] else ""))
        L.append(f"| {k['signal']} | {k['threshold']} | {k['source']}; lag {k['lag']} | {k['check_month']} | {eff} |")
    L += ["", K.PART_D_NOTE, "", "## Flags", ""]
    for r in [c] + sel.rejected:
        for f in r.flags:
            L.append(f"- {r.name}: {f}")
    claims = []
    if out["cash_claim"]:
        claims.append(Claim("\n- " + out["cash_claim"].text, out["cash_claim"].citations))
    for r in [c] + sel.rejected:
        for cl in r.claims:
            claims.append(Claim(f"\n- [{r.name}] {cl.text}", cl.citations))
    L += ["", "## Inputs and Sources", "", render_markdown(claims)]
    return "\n".join(L) + "\n"


def to_json(out):
    sel = out["selection"]
    d = {"ticker": out["ticker"], "as_of": out["as_of"], "cash_and_equivalents": out["cash"],
         "chosen": sel.chosen.to_dict(), "rejected": [r.to_dict() for r in sel.rejected],
         "ranked": [{"name": r.name, "rank": r.rank, "status": r.status, "binding_reason": r.binding_reason, **r.five()} for r in out["ranked"]],
         "selection_notes": sel.notes, "kill_signals": out["kill"]}
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--findings", required=True)
    ap.add_argument("--moves", required=True)
    ap.add_argument("--out", default=None, help="output directory (default out/<TICKER>)")
    ap.add_argument("--cash", type=float, default=None, help="cash and equivalents, USD M (overrides the moves file)")
    ap.add_argument("--as-of", default=None)
    a = ap.parse_args(argv)
    findings = load_findings(a.findings)
    spec = load_moves(a.moves)
    out = run(a.ticker, findings, spec, a.as_of, a.cash)
    out["kill"] = kill_table(out["selection"].chosen)
    d = Path(a.out or f"out/{a.ticker}")
    d.mkdir(parents=True, exist_ok=True)
    (d / "decide.json").write_text(json.dumps(to_json(out), indent=2, default=str))
    (d / "decide.md").write_text(build_md(out, findings))
    c = out["selection"].chosen
    print(f"{a.ticker}: chosen {c.name}: EV {c.ev:,.1f}, CaR {c.car:,.1f}, payback {c.payback_month}, spread {c.spread:,.1f}, MCDA {c.mcda:.3f}")
    for r in out["selection"].rejected:
        print(f"  rejected {r.name}: EV {r.ev:,.1f}, CaR {r.car:,.1f}, payback {r.payback_month}, MCDA {r.mcda:.3f} ({r.binding_reason})")
    print(f"wrote {d / 'decide.json'} and {d / 'decide.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
