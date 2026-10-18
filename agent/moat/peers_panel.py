"""Peer product revenue from XBRL for REGN, ALNY, BBIO (all 10-Q/10-K since 2022)."""
import csv, io, json, re
import agent.tenk as tenk
tenk.MIN_INTERVAL = 0.4
from agent.tenk import sec_get
from agent.corpus import filings
from agent.gap_data import parse_product_revenue
from agent.moat.common import write, note_gap

US = {"REGN": 872589, "ALNY": 1178670, "BBIO": 1743881}
COLS = ["ticker", "accession", "form", "period_start", "period_end", "days", "concept", "product_member", "geography",
        "other_dims", "value_usd", "source", "source_row"]
PROD = re.compile(r"Product")
GEO = re.compile(r"Geograph|Country|Region")


def main():
    rows = []
    for t, cik in US.items():
        _, fs = filings(cik, "2022-01-01")
        for f in [x for x in fs if x["form"] in ("10-Q", "10-K")]:
            acc = f["accession"]
            folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
            try:
                idx = sec_get(f"{folder}/index.json", as_json=True)
                names = [x["name"] for x in idx["directory"]["item"]]
                inst = next((n for n in names if n.endswith("_htm.xml")), None) or next(
                    (n for n in names if re.fullmatch(r"[a-z]+-\d{8}\.xml", n)), None)
                if not inst:
                    note_gap("peers", t, f"xbrl {acc}", "no instance xml")
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
                print(t, acc, f["form"], f["period"], n, flush=True)
            except Exception as e:
                note_gap("peers", t, f"xbrl {acc}", repr(e))
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLS)
    w.writeheader()
    w.writerows(rows)
    write("peers", "tables/peer_product_revenue_xbrl.csv", buf.getvalue(), group="tables", doc_type="table",
          source_url="SEC EDGAR XBRL instances", period="2022-2026")
    print("rows", len(rows))


main()
