"""REMS@FDA: is any of the 52 products on the approved REMS list; plus Drugs@FDA REMS documents."""
import csv
import io
import re
import zipfile

import requests

from agent.drug_pack import DRUGS
from agent.moat.common import write, store

URL = "https://www.accessdata.fda.gov/scripts/cder/rems/index.cfm"


def main():
    html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
    items = {}
    for m in re.finditer(r'REMS=(\d+)" title="([^"]+)"', html):
        items.setdefault(m.group(1), m.group(2))
    low = " | ".join(items.values()).lower()
    z = zipfile.ZipFile(io.BytesIO(store().get("public/drugsatfda.zip")))
    rd = lambda n: list(csv.DictReader(io.TextIOWrapper(z.open(n), encoding="latin-1"), delimiter="\t"))
    prods = rd("Products.txt")
    docs = [d for d in rd("ApplicationDocs.txt") if d["ApplicationDocsTypeID"] == "19"]
    rows = []
    for slug, (brand, _, ing, _) in DRUGS.items():
        appl = {p["ApplNo"] for p in prods if p["DrugName"].upper().strip() == brand.upper()}
        hit = [f"{k}:{v}" for k, v in items.items() if brand.split()[0].lower() in v.lower() or ing.lower() in v.lower()]
        rd_ = [d for d in docs if d["ApplNo"] in appl]
        rows.append([slug, brand, ing.lower(), "yes" if hit else "no", "; ".join(hit),
                     "ETASU or other elements: see REMS detail page" if hit else "none (no REMS)", len(rd_),
                     "; ".join(d["ApplicationDocsURL"] for d in rd_)[:300], URL,
                     f"REMS@FDA approved list ({len(items)} entries) matched on brand/ingredient: {slug}"])
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(["drug", "brand", "ingredient", "rems_active", "rems_entries", "elements", "drugsatfda_rems_docs",
                "drugsatfda_rems_doc_urls", "source", "source_row"])
    w.writerows(rows)
    write("product", "tables/rems.csv", f.getvalue(), group="product", doc_type="table", source_url=URL)
    print(len(rows), sum(r[3] == "yes" for r in rows), len(items))


main()
