"""Point NEEDLE at ANY drug maker: ticker in, full analysis out, no hand-built configuration.

  1. SEC filings, page-marked (agent.corpus.Collector) into data/corpus/onboarded/<TICKER>/
  2. Products: the company's brands in Medicare Part D (manufacturer name match), ranked by 2024 spend
  3. Rivals: drugs in the same FDA pharmacologic class (NLM RxClass, FDA SPL "has_EPC"), other manufacturers,
     ranked by Part D spend
  4. Drug packs (FDA label sections + Orange/Purple Book, Paragraph IV, IRA, Medicare slices) via agent.drug_pack
  5. Writes out/<TICKER>/case_set.json, which agent.needle.detect picks up as that company's product set
  6. Runs every detector and the scorer
Earnings-call transcripts are not fetched automatically (IR sites block scripts); the calls detector reports
"no transcripts loaded" and the inbox (data/corpus/_inbox) accepts them later.

Usage:  python -m agent.needle.onboard VRTX [--products 3 --rivals 2] [--no-sec]
"""

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

from agent import corpus, drug_pack
from agent.needle.detect import OUT

ROOT = Path(__file__).resolve().parent.parent.parent
EXT = ROOT / "data" / "external"
RXCLASS = "https://rxnav.nlm.nih.gov/REST/rxclass"
STOP = {"inc", "corp", "corporation", "co", "plc", "ltd", "llc", "company", "the", "holdings", "group", "sa", "ag",
        "nv", "a/s", "pharmaceuticals", "pharmaceutical", "therapeutics", "biosciences", "sciences"}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def company_key(name):
    """Distinctive first word of the registrant name: 'VERTEX PHARMACEUTICALS INC' -> 'vertex'."""
    words = [w for w in re.split(r"[\s,.&]+", name.lower()) if w and w not in STOP]
    return words[0] if words else name.lower().split()[0]


def partd():
    d = pd.read_csv(EXT / "partd_spending_dy24.csv", dtype=str)
    d["spend"] = pd.to_numeric(d["Tot_Spndng_2024"], errors="coerce").fillna(0)
    return d[d["Mftr_Name"] != "Overall"]


def products(d, key, n):
    mine = d[d["Mftr_Name"].str.lower().str.startswith(key[:6])]
    top = (mine.groupby(["Brnd_Name", "Gnrc_Name"], as_index=False)["spend"].sum()
           .sort_values("spend", ascending=False))
    top = top[~top["Brnd_Name"].str.lower().eq(top["Gnrc_Name"].str.lower())]  # brands only, not generics
    return top.head(n).to_dict("records")


def epc_classes(ingredient):
    r = requests.get(f"{RXCLASS}/class/byDrugName.json", timeout=30,
                     params={"drugName": ingredient.split()[0].lower(), "relaSource": "FDASPL", "relas": "has_EPC"})
    info = r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
    return list({c["rxclassMinConceptItem"]["classId"]: c["rxclassMinConceptItem"]["className"] for c in info}.items())


def class_members(class_id):
    r = requests.get(f"{RXCLASS}/classMembers.json", timeout=30,
                     params={"classId": class_id, "relaSource": "FDASPL", "rela": "has_EPC"})
    ms = r.json().get("drugMemberGroup", {}).get("drugMember", [])
    return sorted({m["minConcept"]["name"].lower() for m in ms})


def rivals(d, key, product, n):
    own = product["Gnrc_Name"].lower()
    found = {}
    for cid, cname in epc_classes(own):
        for ing in class_members(cid):
            rows = d[d["Gnrc_Name"].str.lower().str.contains(re.escape(ing.split()[0]), na=False)
                     & ~d["Mftr_Name"].str.lower().str.startswith(key[:6])]
            rows = rows[~rows["Brnd_Name"].str.lower().eq(rows["Gnrc_Name"].str.lower())]
            for _, r in rows.iterrows():
                b = r["Brnd_Name"]
                if b.lower() != product["Brnd_Name"].lower():
                    cur = found.get(b, {"Brnd_Name": b, "Gnrc_Name": r["Gnrc_Name"], "Mftr_Name": r["Mftr_Name"],
                                        "spend": 0.0, "class": cname})
                    cur["spend"] += r["spend"]
                    found[b] = cur
        time.sleep(0.2)
    return sorted(found.values(), key=lambda x: -x["spend"])[:n]


def build_pack(manifest, bulk, brand, generic, labeler_word, company):
    s = slug(brand)
    meta = drug_pack.find_setid(brand.upper(), re.escape(labeler_word.upper()[:6]))
    ok = False
    if meta:
        xml = drug_pack.get(f"{drug_pack.DM}/services/v2/spls/{meta['setid']}.xml").content
        drug_pack.write(manifest, s, "label_sections.md", drug_pack.label_markdown(xml, meta).encode("utf-8"),
                        f"{drug_pack.DM}/drugInfo.cfm?setid={meta['setid']}", "fda_label", company)
        ok = True
    for rel, df in bulk.slices(brand.upper(), generic.split()[0].upper()).items():
        if len(df):
            drug_pack.write(manifest, s, rel, df.to_csv(index=False).encode(), f"data/external ({rel})",
                            "drug_reference_data", company)
    return s, ok


def onboard(ticker, n_products=3, n_rivals=2, sec=True):
    ticker = ticker.upper()
    t0 = time.time()
    tmap = corpus.ticker_map()
    if ticker not in tmap:
        raise SystemExit(f"unknown ticker {ticker}")
    cik = tmap[ticker]
    manifest = corpus.Manifest(corpus.OUT / "manifest.jsonl")
    sub = corpus.sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)
    key = company_key(sub["name"])
    log = {"ticker": ticker, "cik": cik, "registrant": sub["name"], "match_key": key}
    if sec:
        corpus.Collector(ticker, "onboarded", cik, manifest).run()
    d = partd()
    prods = products(d, key, n_products)
    bulk = drug_pack.Bulk()
    case, packs = {}, []
    for p in prods:
        pslug, ok = build_pack(manifest, bulk, p["Brnd_Name"], p["Gnrc_Name"], key, ticker)
        packs.append({"slug": pslug, "label": ok, "spend_2024": p["spend"]})
        rs = []
        for r in rivals(d, key, p, n_rivals):
            rslug, rok = build_pack(manifest, bulk, r["Brnd_Name"], r["Gnrc_Name"],
                                    company_key(r["Mftr_Name"]), r["Mftr_Name"])
            packs.append({"slug": rslug, "label": rok, "spend_2024": r["spend"], "class": r["class"]})
            if rok:
                rs.append(rslug)
        if ok:
            case[pslug] = rs
    out = OUT / ticker
    out.mkdir(parents=True, exist_ok=True)
    (out / "case_set.json").write_text(json.dumps({"case_set": case, "packs": packs, **log}, indent=2),
                                       encoding="utf-8")
    log.update({"products": [p["Brnd_Name"] for p in prods], "case_set": case, "seconds_setup": round(time.time() - t0)})
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--products", type=int, default=3)
    ap.add_argument("--rivals", type=int, default=2)
    ap.add_argument("--no-sec", action="store_true")
    a = ap.parse_args()
    log = onboard(a.ticker, a.products, a.rivals, not a.no_sec)
    print(json.dumps(log, indent=2))
    from agent.needle import run as needle_run
    import sys
    sys.argv = ["run", "--ticker", a.ticker.upper()]
    needle_run.main()


if __name__ == "__main__":
    main()
