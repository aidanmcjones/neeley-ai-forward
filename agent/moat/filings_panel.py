"""Quarterly product revenue panel from XBRL instances (10-Q/10-K since 2023) + restatements."""
import csv, io, re, json
from collections import defaultdict
import agent.tenk as tenk
tenk.MIN_INTERVAL = 0.2
from agent.tenk import sec_get
from agent.corpus import filings
from agent.gap_data import parse_product_revenue
from agent.moat.common import write, note_gap

US = {"MRK": 310158, "BMY": 14272, "PFE": 78003, "LLY": 59478, "ABBV": 1551152, "JNJ": 200406, "AMGN": 318154, "GILD": 882095}
COLS = ["ticker", "accession", "form", "period_start", "period_end", "days", "concept", "product_member", "geography",
        "other_dims", "value_usd", "source", "source_row"]
PROD = re.compile(r"ProductOrServiceAxis|ProductsAndServicesAxis")
GEO = re.compile(r"Geograph|Country|Region")


def main():
    rows = []
    for t, cik in US.items():
        _, fs = filings(cik, "2023-01-01")
        for f in [x for x in fs if x["form"] in ("10-Q", "10-K")]:
            acc = f["accession"]
            folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
            try:
                idx = sec_get(f"{folder}/index.json", as_json=True)
                names = [x["name"] for x in idx["directory"]["item"]]
                inst = next((n for n in names if n.endswith("_htm.xml")), None) or next(
                    (n for n in names if re.fullmatch(r"[a-z]+-\d{8}\.xml", n)), None)
                if not inst:
                    note_gap("filings", t, f"xbrl {acc}", "no instance xml")
                    continue
                xml = sec_get(f"{folder}/{inst}").encode()
                n = 0
                for r in parse_product_revenue(xml):
                    d = r["dims"]
                    prod = [v for k, v in d.items() if PROD.search(k)]
                    geo = [v for k, v in d.items() if GEO.search(k)]
                    oth = {k.split(":")[-1]: v for k, v in d.items() if not PROD.search(k) and not GEO.search(k)}
                    rows.append({"ticker": t, "accession": acc, "form": f["form"], "period_start": r["start"],
                                 "period_end": r["end"], "days": r["days"], "concept": r["concept"],
                                 "product_member": ";".join(prod), "geography": ";".join(geo),
                                 "other_dims": json.dumps(oth, sort_keys=True) if oth else "",
                                 "value_usd": r["value"], "source": f"{folder}/{inst}",
                                 "source_row": "|".join(f"{k.split(':')[-1]}={v}" for k, v in sorted(d.items()))})
                    n += 1
                print(t, acc, f["form"], n, flush=True)
            except Exception as e:
                note_gap("filings", t, f"xbrl {acc}", repr(e))
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLS)
    w.writeheader()
    w.writerows(rows)
    write("filings", "tables/product_revenue_quarterly.csv", buf.getvalue(), group="tables", doc_type="table",
          source_url="SEC EDGAR XBRL instances", period="2023-2026")
    key = defaultdict(lambda: defaultdict(set))
    for r in rows:
        k = (r["ticker"], r["concept"], r["product_member"], r["geography"], r["other_dims"], r["period_start"], r["period_end"])
        key[k][r["value_usd"]].add(r["accession"])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ticker", "concept", "product_member", "geography", "other_dims", "period_start", "period_end",
                "n_values", "min_value", "max_value", "pct_diff", "values_by_accession"])
    cnt = 0
    for k, vals in key.items():
        if len(vals) > 1:
            vs = sorted(vals)
            pct = (vs[-1] - vs[0]) / abs(vs[-1]) * 100 if vs[-1] else 0
            w.writerow(list(k) + [len(vs), vs[0], vs[-1], round(pct, 3),
                                  json.dumps({str(v): sorted(a) for v, a in vals.items()})])
            cnt += 1
    write("filings", "tables/restatements.csv", out.getvalue(), group="tables", doc_type="table",
          source_url="derived from tables/product_revenue_quarterly.csv")
    print("rows", len(rows), "restatements", cnt)


if __name__ == "__main__":
    main()
