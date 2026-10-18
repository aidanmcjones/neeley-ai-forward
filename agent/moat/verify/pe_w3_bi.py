"""Peers wave 3 item 3: verify the 6 Boehringer Ingelheim Jardiance statements and append them to
verified/peers/rival_product_statements.csv.

Checks: quote verbatim on the cited page (whitespace-normalized), EUR figure and growth rate inside the quote match
the expected values, and the printed folio. The collector's folios came from a heuristic; a folio is kept only when
the number stands alone on a line at the top or bottom of the page text, otherwise printed_page is blanked.

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_bi.py [--write]
"""
import io
import re
import sys

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, norm, pages

SRC = ROOT / "data/moat/tables/rival_product_statements_wave3.csv"
VER = ROOT / "data/moat/verified/peers/rival_product_statements.csv"
EXPECT = {"2022FY": ("5,832", "48.0"), "2023FY": ("7,382", "26.6"), "2024FY": ("8,357", "13.2")}


def bnorm(s):
    return norm(re.sub(r"\xad\s*", "", str(s)))


def doc_folios(path):
    """Share of pages whose marker folio stands alone at the page edge (how far the collector heuristic holds)."""
    pg = pages(path)
    good = sum(1 for pr, t in pg.values() if pr not in ("?", "") and folio_ok(t, pr)[0])
    return good, sum(1 for pr, _ in pg.values() if pr not in ("?", "")), len(pg)


def folio_ok(text, printed):
    ls = [l.strip() for l in text.split("\n") if l.strip()]
    edge = ls[:3] + ls[-3:]
    return any(re.fullmatch(rf"{re.escape(str(printed))}", l) for l in edge), edge


def main():
    w = pd.read_csv(SRC)
    v = pd.read_csv(VER)
    v = v[v.maker != "BOEHRINGER"]  # rerun-safe
    out = []
    for p in sorted(w.path.unique()):
        print(p, "folio confirmed / pages with folio / pages:", doc_folios(p))
    for _, r in w.iterrows():
        pr, txt = pages(r.path)[int(r.page)]
        verb = bnorm(r.quote) in bnorm(txt)
        fig, gr = EXPECT[r.period]
        has = (fig in r.quote and gr in r.quote) if r.topic == "revenue|growth" else None
        fo, edge = folio_ok(txt, r.printed_page)
        offs = [k - int(q) for k, (q, _) in pages(r.path).items() if q.isdigit()]
        modal = max(set(offs), key=offs.count)
        fo = fo and (int(r.page) - int(r.printed_page) == modal)  # folio must sit on the document's constant offset
        print(r.period, r.page, r.printed_page, "| marker printed:", pr, "| verbatim", verb, "| figures", has,
              "| folio", fo, edge)
        rec = r.to_dict()
        rec["quote_check"] = "verbatim" if verb else "not_found"
        rec["verify_status"] = "verified" if verb and has is not False else "failed"
        rec["printed_ok"] = bool(fo)
        if not fo:
            rec["printed_page"] = None
        rec["source_role"] = "maker_doc"
        rec["page_granularity"] = ("page; printed folio blank: collector folio was a heuristic not confirmed on the "
                                   "page" if not fo else "page") + ("; document is the BI annual 'Highlights' report "
                                                                   "(annualreports.com), not the audited financial statements")
        if "OFEV" in r.quote:
            rec["subject"], rec["other_products"] = "shared", "OFEV"
        out.append(rec)
    n = pd.DataFrame(out)
    if "--write" in sys.argv:
        allv = pd.concat([v, n[v.columns]], ignore_index=True)
        buf = io.StringIO()
        allv.to_csv(buf, index=False)
        write("verify_peers", "verified/peers/rival_product_statements.csv", buf.getvalue(), group="peers",
              doc_type="table", quality="verified")
        print("written", len(allv))


if __name__ == "__main__":
    main()
