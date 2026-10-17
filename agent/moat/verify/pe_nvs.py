"""Peers item 2: rebuild and verify NVS top-20 brand net sales (USD m) from the 20-F Item 18 tables.

The collector's peer_product_revenue.csv put the therapeutic area / indication in `product`, read the wrong pages
(FY2022 doc p216 is the 2020 table; FY2023 p210 and FY2024 p188 are the therapeutic-area tables) and dropped
brands with no US column. This rebuilds every top-20 table straight from the page text and checks that the 20
brand totals add to the printed 'Top 20 brands total'.
"""
import io
import re

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, pages

DOCS = {2022: ("data/moat/companies/NVS/20f_FY2022.md", 214), 2023: ("data/moat/companies/NVS/20f_FY2023.md", 211),
        2024: ("data/moat/companies/NVS/20f_FY2024.md", 189), 2025: ("data/corpus/peers/NVS/20f_FY2025.md", 192)}
NUM = re.compile(r"^-?\s?\d{1,3}( \d{3})*$")
CLASSES = ("Immunology", "Neuroscience", "Cardiovascular", "Hematology", "Solid Tumors", "Oncology",
           "Established", "Other Promoted", "Ophthalmology", "Respiratory")


def num(s):
    return int(s.replace(" ", ""))


def parse(path, page):
    printed, t = pages(path)[page]
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    folio = lines[0] if re.match(r"^F-\d+$", lines[0]) else printed
    title = next(l for l in lines if "top 20" in l.lower())
    year = int(re.search(r"in (\d{4})", title).group(1))
    i = next(k for k, l in enumerate(lines) if l.startswith("Total") and "USD" in (l + lines[k + 1])) + 1
    if lines[i] == "USD m":
        i += 1
    rows, total = [], None
    while i < len(lines):
        l = lines[i]
        if l.lower().startswith(("top 20 brands total", "top 20 products total")):
            vals = []
            i += 1
            while i < len(lines) and NUM.match(lines[i]):
                vals.append(num(lines[i]))
                i += 1
            total = vals
            break
        name = re.sub(r"\s+\d$", "", l)  # strip footnote digit
        j = i + 1
        txt = []
        while j < len(lines) and not NUM.match(lines[j]):
            txt.append(lines[j])
            j += 1
        vals = []
        while j < len(lines) and NUM.match(lines[j]):
            vals.append(num(lines[j]))
            j += 1
        cls = txt[0] if txt else ""
        ind = " ".join(txt[1:])
        us, rw, tot = (vals + [None] * 3)[:3] if len(vals) == 3 else ((None, vals[0], vals[1]) if len(vals) == 2 else (None, None, vals[0] if vals else None))
        rows.append(dict(brand=name, classification=cls, key_indications=ind, us_usd_m=us, row_usd_m=rw,
                         total_usd_m=tot, n_values=len(vals)))
        i = j
    return year, folio, title, rows, total


def main():
    raw = pd.read_csv(ROOT / "data/moat/tables/peer_product_revenue.csv")
    out, checks = [], []
    for fy, (path, page) in DOCS.items():
        year, folio, title, rows, total = parse(path, page)
        s = sum(r["total_usd_m"] or 0 for r in rows)
        checks.append(dict(fiscal_year=fy, page=page, folio=folio, table_year=year, n_brands=len(rows),
                           sum_totals=s, printed_top20_total=(total or [None])[-1], sum_ok=(total and s == total[-1])))
        for k, r in enumerate(rows, 1):
            out.append(dict(ticker="NVS", fiscal_year=year, rank=k, **r, units="USD millions",
                            doc=path.split("/")[-1][:-3], page=page, printed_page=folio, source_path=path,
                            source=path + f"#page {page}", source_row=f"{r['brand']}|{year}",
                            verify_note=("US column blank in the filing (no US sales booked by Novartis)"
                                         if r["us_usd_m"] is None else "")))
    v = pd.DataFrame(out)
    print(pd.DataFrame(checks).to_string())
    # map each collector row to the true brand/year by its value tuple
    key = {}
    for _, r in v.iterrows():
        vals = [x for x in (r.us_usd_m, r.row_usd_m, r.total_usd_m) if x == x and x is not None]
        key[tuple(int(x) for x in vals)] = (r.brand, r.fiscal_year)
    m = []
    for _, r in raw.iterrows():
        vals = tuple(int(x.replace(" ", "")) for x in str(r.values_raw).split(" ; ") if re.fullmatch(r"[\d ]+", x.strip()))
        hit = key.get(vals)
        m.append(dict(collector_fy=r.fiscal_year, collector_product=r["product"], collector_page=r.page,
                      values_raw=r.values_raw, true_brand=hit[0] if hit else None, true_fy=hit[1] if hit else None))
    m = pd.DataFrame(m)
    m["status"] = m.apply(lambda x: "not_a_top20_brand_row" if x.true_brand is None else
                          ("wrong_fy_and_product_label" if x.true_fy != x.collector_fy else "product_label_wrong"), axis=1)
    print(m.status.value_counts())
    print(m.groupby(["collector_fy", "status"]).size())
    m.to_pickle("/tmp/pe_nvs_map.pkl")
    buf = io.StringIO()
    v.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/peer_product_revenue.csv", buf.getvalue(), ticker="NVS", group="tables",
          doc_type="table", quality="verified", source_url="NVS 20-F Item 18 top 20 brands tables")
    buf = io.StringIO()
    m.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/peer_product_revenue_collector_map.csv", buf.getvalue(), ticker="NVS",
          group="tables", doc_type="table", quality="verified", source_url="data/moat/tables/peer_product_revenue.csv")
    print(v[v.fiscal_year == 2025][["brand", "us_usd_m", "row_usd_m", "total_usd_m"]].to_string())


if __name__ == "__main__":
    main()
