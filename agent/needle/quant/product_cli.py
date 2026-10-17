"""Write the product fine print for one product.

    python -m agent.needle.quant.product_cli --ticker LLY --product zepbound [--out out] [--data-root PATH] [--public]

Outputs out/<TICKER>/product_<product>.json and .md: the five-row side-by-side, the tied financial finding(s), the
growth-limiter sentence with the priced-in call, empty cells with reasons, and footnotes from cite.render. Every number
is checked by the numeric gate (agent.needle.cite.gate); the JSON carries numeric_check at the document level and per
item, and uncited_cells lists exactly the cells the gate withholds (review D9).
"""

import argparse
import json
from pathlib import Path

from agent.needle.quant import product as P

REPO = Path(__file__).resolve().parents[3]


def _cell_text(cell):
    if cell.empty:
        return f"empty ({cell.empty_reason})"
    t = cell.value.replace("|", "/").replace("\n", " ")
    return t if len(t) < 420 else t[:417] + "..."


def build(ticker, product, data_root=None, index=None, public=False):
    """(json dict, markdown). Every number in the markdown is a gated cell (docs/gate_wiring.md 4): table cells,
    the tied finding sentence and its math lines, the growth-limiter sentence and its reasons. A cell that fails is
    printed as withheld and listed under "Cells with values but no verified page citation"; a channel that fails is
    not printed as a finding (product.tie_to_financials)."""
    from agent.needle.cite.gate import gate_document, numeric_gate
    from agent.needle.quant.decide_cli import Doc
    from agent.needle.quant.product_gate import NOTE_A, limiter_maps
    cmp_ = P.compare(ticker, product, data_root=data_root, index=index)
    finds = P.tie_to_financials(cmp_)
    sentence, priced, reasons, gl_cites = P.growth_limiter(cmp_, finds)
    doc = Doc(public)
    withheld = []

    def line(section, where, text, cites=(), dm=None, am=None):
        res = numeric_gate([(where, text)], [c for c in cites if c.verification.ok], dm, am)
        if res.passed or res.numeric_check["status"] == "unchecked":
            return doc.cell(section, where, text, cites, dm, am)
        withheld.append({"where": where, "text": text, "numeric_check": res.numeric_check})
        return f"(withheld by the numeric gate: {len(res.numeric_check['unsupported'])} unsupported number(s); see JSON)"
    names = [e["name"] for e in cmp_.entities]
    L = [f"# Product fine print: {cmp_.entities[0]['name']} ({ticker}) vs listed rivals", "",
         f"As of {cmp_.as_of}. Rivals are the case appendix set. Label rows cite DailyMed label sections; timeline rows cite "
         "the 10-K page; pricing rows cite CMS and White House pages and the verified facts rows (policy_exposure, "
         "gtn_proxy, gtn_exposure). Every number carries a marker: [n] a citation, [derived: ...] computed from cited "
         "or labelled operands, [assumption] a labelled assumption (model constants, counts taken from a cited label "
         "section, and table values with no verified facts row, whose file and key the label names).", "",
         "| Row | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    failed_cells = []
    for rk, title in P.ROWS:
        cells = []
        for e in cmp_.entities:
            c = cmp_.rows[rk][e["name"]]
            if c.empty:
                cells.append(_cell_text(c).replace("|", "/"))
                continue
            res = P.cell_gate(cmp_, rk, e["name"])
            if res.passed:
                cells.append(doc.cell("cells", f"{rk}/{e['name']}", _cell_text(c), res.citations, res.derived,
                                      res.assumptions))
            else:
                failed_cells.append({"row": rk, "entity": e["name"], "numeric_check": res.numeric_check})
                cells.append("(withheld by the numeric gate; see below)")
        L.append(f"| {title} | " + " | ".join(cells) + " |")
    L += ["", "## Tied financial finding", ""]
    for k, f in enumerate(finds):
        L += [f"- **{f.channel}** ({f.confidence} confidence): "
              + doc.cell("findings", f"findings/{f.channel}", f.text, f.citations, f.derived, f.assumptions)]
        for j, m in enumerate(f.impact.get("math_lines", [])):
            L.append("  - " + doc.cell("math", f"math/{f.channel}[{j}]", m, f.citations, f.derived, f.assumptions))
        L += [f"  - peer: {line('findings', f'peer/{f.channel}', str(f.peer.get('named_peer_row')), f.citations, f.derived, f.assumptions)}",
              f"  - obscurity: {line('findings', f'obscurity/{f.channel}', f.obscurity_note)}"]
    if not finds:
        L.append("No finding passed: " + line("findings", "none", "; ".join(cmp_.context.get("unquantified", [])), (), None,
                                              NOTE_A))
    gl_dm, gl_am = {}, {}
    if finds:
        gl_dm, gl_am = dict(finds[0].derived or {}), dict(finds[0].assumptions or {})
    topics = []
    if finds:
        tp = next((x.split("=", 1)[1] for x in finds[0].flags if x.startswith("topic=")), "").split("|")
        topics = [(t, cmp_.context.get("scorecard", {}).get(t)) for t in tp]
    lc, ldm, lam = limiter_maps(cmp_, finds[0] if finds else None, topics)
    gl_dm.update(ldm)
    gl_am.update(lam)
    gl_am.update(NOTE_A)
    L += ["", "## What limits growth, and is it priced in", "",
          doc.cell("growth limiter", "growth_limiter", sentence, gl_cites, gl_dm, gl_am), "", f"Priced in: **{priced}**"]
    for j, r in enumerate(reasons):
        L.append("- " + line("growth limiter", f"reasons[{j}]", r, list(gl_cites) + lc, gl_dm, gl_am))
    emp = cmp_.empties()
    L += ["", "## Empty cells", ""] + ([f"- {r} / {n}: {line('empty', f'empty/{r}/{n}', why)}" for r, n, why in emp]
                                       or ["- none"])
    unc = cmp_.uncited()
    tab = cmp_.table_only()
    L += ["", "## Cells with values but no verified page citation", "",
          "Withheld (a number in the cell is not verified, derived or labelled):", ""]
    L += [f"- {r} / {n}: " + "; ".join(f"{u['value']} ({u['reason']})" for u in
                                         P.cell_gate(cmp_, r, n).numeric_check["unsupported"][:4]) for r, n in unc] or ["- none"]
    L += ["", "Shown, with numbers labelled as unverified table values (file and key in the label and the JSON refs):", ""]
    L += [f"- {r} / {n}" for r, n in tab] or ["- none"]
    unq = cmp_.context.get("unquantified", [])
    if unq or cmp_.notes:
        L += ["", "## Channels not quantified", ""] + [f"- {line('notes', f'notes[{j}]', u, (), None, NOTE_A)}"
                                                       for j, u in enumerate(unq + cmp_.notes)]
    summary = gate_document(doc.sections())
    md = doc.render("\n".join(L) + "\n")
    out = {"comparison": cmp_.to_dict(), "findings": [f.record() for f in finds],
           "growth_limiter": {"sentence": sentence, "priced_in": priced, "reasons": reasons,
                              "citations": [c.to_dict() for c in gl_cites]},
           "empty_cells": [{"row": r, "entity": n, "reason": w} for r, n, w in emp],
           "uncited_cells": [{"row": r, "entity": n, "numeric_check": P.cell_gate(cmp_, r, n).numeric_check}
                             for r, n in unc],
           "table_value_cells": [{"row": r, "entity": n} for r, n in tab],
           "numeric_check": summary["numeric_check"],
           "numeric_items": [{k: it[k] for k in ("where", "text", "passed", "numeric_check")} for it in summary["items"]],
           "withheld_lines": withheld}
    return out, md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--product", default=None)
    ap.add_argument("--out", default=str(REPO / "out"))
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--public", action="store_true", help="render footnotes with licensed text withheld (public build)")
    a = ap.parse_args(argv)
    t = a.ticker.upper()
    prod = (a.product or P.DEFAULT_PRODUCT[t]).lower()
    data, md = build(t, prod, a.data_root, public=a.public)
    d = Path(a.out) / t
    d.mkdir(parents=True, exist_ok=True)
    (d / f"product_{prod}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (d / f"product_{prod}.md").write_text(md, encoding="utf-8")
    print(f"{t} {prod}: {len(data['findings'])} finding(s), {len(data['empty_cells'])} empty cell(s) -> {d / ('product_' + prod + '.md')}")
    return data


if __name__ == "__main__":
    main()
