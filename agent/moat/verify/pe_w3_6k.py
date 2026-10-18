"""Peers wave 3 item 1: quarter map of the SNY / TAK / GSK / NVS 6-K files (verified/peers/sixk_index.csv).

For each file: filing date, accession, pages, a title line from page 1, whether it is a results release and for
which period (from the title text), duplicate/alternate relations, and for 3 files per company whether the page
markers line up with the document structure (page count vs printed folio sequence, folio monotonic).

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_6k.py [--write]
"""
import io
import re
import sys

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, pages

TICKERS = ["SNY", "TAK", "GSK", "NVS"]
WAVE3_NVS = {"2025-10-28", "2026-02-04", "2026-04-28", "2026-07-21"}


def first_text(path, n=1600):
    pg = pages(path)
    t = pg[min(pg)][1] if pg else (ROOT / path).read_text(errors="replace")
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    return re.sub(r"\s+", " ", t).strip()[:n]


def period_from(t, tk, filed):
    tl = t.lower()
    y, m = int(filed[:4]), int(filed[5:7])
    if tk == "TAK":
        fy, q = ((y, 1) if m in (7, 8) else (y, 2) if m in (10, 11) else (y - 1, 3) if m in (1, 2) else (y - 1, 4))
        return f"FY{fy}Q{q}"
    cal = {1: (y - 1, 4), 2: (y - 1, 4), 4: (y, 1), 5: (y, 1), 7: (y, 2), 8: (y, 2), 10: (y, 3), 11: (y, 3)}.get(m)
    return f"{cal[0]}Q{cal[1]}" if cal else None


RESULTS = re.compile(r"(results|net sales|financial statements for the|half-year|half year|quarter|Q[1-4] 20\d\d|full[- ]year|turnover)", re.I)


def struct_check(path):
    pg = pages(path)
    folios = [(k, p) for k, (p, _) in sorted(pg.items()) if p.isdigit()]
    mono = all(int(b[1]) >= int(a[1]) for a, b in zip(folios, folios[1:]))
    offs = [k - int(p) for k, p in folios]
    modal = max(set(offs), key=offs.count) if offs else None
    on = sum(o == modal for o in offs)
    # does the folio stand alone at the page edge?
    edge = 0
    for k, p in folios:
        ls = [l.strip() for l in pg[k][1].split("\n") if l.strip()]
        edge += any(l == p for l in ls[:3] + ls[-3:])
    return dict(pages_marked=len(pg), pages_with_folio=len(folios), folio_monotonic=mono, folio_modal_offset=modal,
                folio_on_offset=on, folio_at_page_edge=edge)


def main():
    rows = []
    for tk in TICKERS:
        for f in sorted((ROOT / f"data/moat/companies/{tk}/6k").glob("*.md")):
            rel = str(f.relative_to(ROOT))
            m = re.match(r"(\d{4}-\d{2}-\d{2})_([\d-]+?)(_ex\d+)?\.md", f.name)
            filed, acc, ex = m.group(1), m.group(2), m.group(3) or ""
            if tk == "NVS" and filed not in WAVE3_NVS:
                continue
            t = first_text(rel)
            hdr = (ROOT / rel).read_text(errors="replace")[:600]
            src = re.search(r"source: (\S+)", hdr)
            rows.append(dict(ticker=tk, filed=filed, accession=acc, exhibit=ex.strip("_") or "main", file=rel,
                             source_url=src.group(1) if src else None, pages=len(pages(rel)),
                             chars=f.stat().st_size, period=period_from(t, tk, filed), first_page=t[:400]))
    d = pd.DataFrame(rows)
    kinds, alts = [], []
    for _, r in d.iterrows():
        t = r.first_page
        same = d[(d.ticker == r.ticker) & (d.period == r.period)]
        if r.ticker == "SNY":
            rel = same[same.first_page.str.contains("Press Release")]
            rel_acc = rel.accession.iloc[0] if len(rel) else None
            if "Press Release" in t:
                k, a = "results_release", None
            elif "HALF-YEAR MANAGEMENT REPORT" in t.upper():
                k, a = "half_year_management_report", rel_acc
            elif "Condensed half-year consolidated financial statements" in t:
                k = "condensed_half_year_statements"
                a = "0001121404-25-000022 (same H1 2025 statements refiled 2025-10-27)" if r.filed == "2025-10-27" else rel_acc
            elif "Q3 and YTD 2025 summary" in t:
                k, a = "q3_ytd_summary_exhibit", rel_acc
            else:
                k, a = "other", None
        elif r.ticker == "TAK":
            if r.exhibit == "ex2":
                k, a = "results_release", None
            elif "FINANCIAL APPENDIX" in t:
                k, a = "financial_appendix", f"{r.accession}_ex2 (companion exhibit)"
            else:
                rel = same[same.exhibit == "ex2"]
                k, a = "quarterly_securities_report", (rel.accession.iloc[0] + "_ex2") if len(rel) else None
        elif r.ticker == "GSK":
            k, a = ("results_release" if "RESULTS" in t else "other"), None
        else:
            if "Financial Report Q4" in t:
                k, a = "results_release", None
            else:
                k = "condensed_financial_report" if "CONDENSED" in t.upper() else "interim_financial_report"
                a = None
                if r.filed == "2026-02-04":
                    a = f"{r.accession} main (Financial Report Q4 2025)"
        kinds.append(k)
        alts.append(a)
    d["doc_kind"] = kinds
    # the 2025-10-27 refiling carries the H1 2025 statements (June 30, 2025), not Q3
    d.loc[(d.ticker == "SNY") & (d.filed == "2025-10-27") & (d.exhibit == "main"), "period"] = "2025Q2"
    import json
    man = {json.loads(l)["path"]: json.loads(l)["period"] for l in (ROOT / "data/moat/manifests/peers.jsonl").read_text().splitlines()}
    d["manifest_period"] = d.file.map(man)
    d["is_results_release"] = d.doc_kind.isin(["results_release", "condensed_financial_report", "interim_financial_report"]) & ~((d.ticker == "NVS") & (d.filed == "2026-02-04") & (d.exhibit == "ex2"))
    d["duplicate_of"] = [a if a and "refiled" in a else None for a in alts]
    d["alternate_of"] = [a if a and "refiled" not in a else None for a in alts]
    # period scope of the main figures in each release
    sc = []
    for _, r in d.iterrows():
        q = r.period[-1]
        if r.ticker == "TAK":
            sc.append({"1": "Q1 (3 months)", "2": "H1 cumulative (6 months)", "3": "9M cumulative", "4": "full fiscal year"}[q])
        else:
            sc.append({"1": "Q1", "2": "Q2 and H1", "3": "Q3 and 9M", "4": "Q4 and FY"}[q])
    d["period_scope"] = sc
    pick = {}
    for tk in TICKERS:
        f = d[d.ticker == tk].file.tolist()
        pick.update({x: True for x in (f[0], f[len(f) // 2], f[-1])})
    st = [struct_check(x) if x in pick else {} for x in d.file]
    st = pd.DataFrame(st, index=d.index)
    d = pd.concat([d, st], axis=1)
    d["page_check"] = None
    for i, r in d.iterrows():
        if r.file not in pick:
            continue
        if r.pages == 1:
            d.at[i, "page_check"] = "one page (EDGAR HTML has no page breaks): page cite is the whole document"
        else:
            d.at[i, "page_check"] = (f"{int(r.pages_with_folio)}/{int(r.pages_marked)} pages carry a folio; monotonic={r.folio_monotonic}; "
                                     f"{int(r.folio_on_offset)} on constant offset {r.folio_modal_offset}; {int(r.folio_at_page_edge)} folios stand alone at the page edge")
    d = d.drop(columns=["first_page"]).assign(first_page=[x[:200] for x in [r["first_page"] for r in rows]])
    if "--write" in sys.argv:
        buf = io.StringIO()
        d.to_csv(buf, index=False)
        write("verify_peers", "verified/peers/sixk_index.csv", buf.getvalue(), group="peers", doc_type="table",
              quality="verified")
    print(d.groupby(["ticker", "doc_kind"]).size().to_string())
    print(d[d.page_check.notna()][["ticker", "file", "page_check"]].to_string())
    if "--write" not in sys.argv and False:
        for _, r in d.iterrows():
            print(r.ticker, r.filed, r.accession, r.exhibit, r.pages, r.chars, r.period, "|", r.first_page[:260])
        return d
    return d


if __name__ == "__main__":
    main()
