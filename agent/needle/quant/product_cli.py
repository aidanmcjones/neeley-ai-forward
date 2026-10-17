"""Write the product fine print for one product.

    python -m agent.needle.quant.product_cli --ticker LLY --product zepbound [--out out] [--data-root PATH]

Outputs out/<TICKER>/product_<product>.json and .md: the five-row side-by-side, the tied financial finding(s), the
growth-limiter sentence with the priced-in call, empty cells with reasons, and footnotes from cite.render_markdown.
"""

import argparse
import json
from pathlib import Path

from agent.needle.cite import render
from agent.needle.cite.locator import Claim
from agent.needle.quant import product as P

REPO = Path(__file__).resolve().parents[3]


def _cell_text(cell):
    if cell.empty:
        return f"empty ({cell.empty_reason})"
    t = cell.value.replace("|", "/").replace("\n", " ")
    return t if len(t) < 420 else t[:417] + "..."


def build(ticker, product, data_root=None, index=None):
    cmp_ = P.compare(ticker, product, data_root=data_root, index=index)
    finds = P.tie_to_financials(cmp_)
    sentence, priced, reasons, gl_cites = P.growth_limiter(cmp_, finds)
    # claims in a fixed order so footnote numbers can be mapped back to table cells
    claims, keys = [], []
    for rk, _ in P.ROWS:
        for e in cmp_.entities:
            c = cmp_.rows[rk][e["name"]]
            claims.append(Claim(f"{e['name']}, {rk}", list(c.citations)))
            keys.append((rk, e["name"]))
    n_cells = len(claims)
    claims += [Claim(f.text, list(f.citations)) for f in finds]
    claims.append(Claim(sentence, list(gl_cites)))
    marks, _ = render._number(claims)
    md = render.render_markdown(claims)
    sources = md.split("**Sources**", 1)[1] if "**Sources**" in md else ""
    names = [e["name"] for e in cmp_.entities]
    L = [f"# Product fine print: {cmp_.entities[0]['name']} ({ticker}) vs listed rivals", "",
         f"As of {cmp_.as_of}. Rivals are the case appendix set. Label rows cite DailyMed label sections; timeline rows cite the 10-K page; "
         "pricing rows cite CMS and White House pages. Numbers with no page (Orange Book, NADAC, Part D files) are table refs in the JSON.", "",
         "| Row | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for rk, title in P.ROWS:
        cells = []
        for e in cmp_.entities:
            i = keys.index((rk, e["name"]))
            cells.append(_cell_text(cmp_.rows[rk][e["name"]]) + "".join(f"[{n}]" for n in marks[i]))
        L.append(f"| {title} | " + " | ".join(cells) + " |")
    L += ["", "## Tied financial finding", ""]
    for k, f in enumerate(finds):
        m = "".join(f"[{n}]" for n in marks[n_cells + k])
        imp = f.impact
        L += [f"- **{f.channel}** ({f.confidence} confidence): {f.text}{m}",
              f"  - math: {imp['formula']}",
              f"  - dRev bull/base/bear: ${imp['dRev']['bull']:,} / ${imp['dRev']['base']:,} / ${imp['dRev']['bear']:,}; dOI at CM {imp['CM']}: base ${imp['dOI']['base']:,}",
              f"  - peer: {f.peer.get('named_peer_row')}",
              f"  - obscurity: {f.obscurity_note}"]
    if not finds:
        L.append("No finding passed: " + "; ".join(cmp_.context.get("unquantified", [])))
    L += ["", "## What limits growth, and is it priced in", "",
          sentence + "".join(f"[{n}]" for n in marks[-1]), "", f"Priced in: **{priced}**"] + [f"- {r}" for r in reasons]
    emp = cmp_.empties()
    L += ["", "## Empty cells", ""] + ([f"- {r} / {n}: {why}" for r, n, why in emp] or ["- none"])
    unc = cmp_.uncited()
    L += ["", "## Cells with values but no verified page citation (table refs only, see JSON)", ""] + ([f"- {r} / {n}" for r, n in unc] or ["- none"])
    unq = cmp_.context.get("unquantified", [])
    if unq or cmp_.notes:
        L += ["", "## Channels not quantified", ""] + [f"- {u}" for u in unq + cmp_.notes]
    L += ["", "**Sources**" + sources]
    out = {"comparison": cmp_.to_dict(), "findings": [f.record() for f in finds],
           "growth_limiter": {"sentence": sentence, "priced_in": priced, "reasons": reasons,
                              "citations": [c.to_dict() for c in gl_cites]},
           "empty_cells": [{"row": r, "entity": n, "reason": w} for r, n, w in emp],
           "uncited_cells": [{"row": r, "entity": n} for r, n in unc]}
    return out, "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--product", default=None)
    ap.add_argument("--out", default=str(REPO / "out"))
    ap.add_argument("--data-root", default=None)
    a = ap.parse_args(argv)
    t = a.ticker.upper()
    prod = (a.product or P.DEFAULT_PRODUCT[t]).lower()
    data, md = build(t, prod, a.data_root)
    d = Path(a.out) / t
    d.mkdir(parents=True, exist_ok=True)
    (d / f"product_{prod}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (d / f"product_{prod}.md").write_text(md, encoding="utf-8")
    print(f"{t} {prod}: {len(data['findings'])} finding(s), {len(data['empty_cells'])} empty cell(s) -> {d / ('product_' + prod + '.md')}")
    return data


if __name__ == "__main__":
    main()
