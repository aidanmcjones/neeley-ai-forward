"""Finalize filings verification outputs: classify vanished breakouts, text-check them, write via common.write."""
import csv, io, json, re, collections
from agent.moat.verify.f_lib import pages
from agent.moat.common import write

V = list(csv.DictReader(open("data/moat/scratch/discontinued_breakouts.csv")))
CONSUMER = re.compile(r"Skin Health|OTC|Beauty|Oral Care|Baby Care|Womens Health", re.I)
CATEGORY = re.compile(r"In Line|LOEProducts|New Product Portfolio|HCVProduct Sales", re.I)
for r in V:
    doc = r["citation_without"].split(" ")[0]
    name = re.sub(r"^(HIVProducts|HCVProducts|Hepatitis BVirus Hepatitis Delta Virus Product)\s*", "", r["product"]).split()[0]
    still = ""
    if doc.endswith(".md"):
        for pg, pr, body in pages(doc):
            b = re.sub(r"\s+", " ", body)
            m = re.search(re.escape(name[:8]) + r"[^.]{0,40}?\$?\s?\d{1,3}(,\d{3})?\b", b, re.I)
            if m and re.search(r"\d", m.group(0)[len(name[:8]):]):
                # a product-table style hit: name followed closely by a number
                still = f"p{pg}/printed {pr}: '{m.group(0)[:80]}'"
                break
    if CONSUMER.search(r["product"]) and r["ticker"] == "JNJ":
        kind = "separation_not_quiet (Kenvue consumer health moved to discontinued operations in 2023)"
    elif CATEGORY.search(r["product"]):
        kind = "category_grouping_dropped (portfolio subtotal, not a single product)"
    elif r["ticker"] == "AMGN" and r["product"] == "Neulasta":
        kind = "product_no_longer_broken_out (in the revenue note only: AMGN 10-K FY2023 note table p123/printed F-20 has no Neulasta line and Other products U.S. 2022 = 3,776 vs 3,549 before; the MD&A table p75/printed 68 still prints Neulasta U.S. 959 / ROW 167 for 2022)"
    else:
        kind = "product_no_longer_broken_out"
    r["kind"] = kind
    r["text_check_later_filing"] = still or ("name not printed next to a number" if doc.endswith(".md") else "no page-marked copy")
cols = ["ticker", "product", "product_member", "kind", "first_filing", "last_filing", "first_filing_without", "comparative_period",
        "geography", "value_last_reported_usd", "folded_into", "evidence", "citation_last", "citation_without",
        "text_check_later_filing", "n_filings_with"]
buf = io.StringIO()
w = csv.DictWriter(buf, cols, extrasaction="ignore"); w.writeheader(); w.writerows(V)
open("data/moat/scratch/discontinued_breakouts_final.csv", "w").write(buf.getvalue())
print(collections.Counter(r["kind"].split(" ")[0] for r in V))
for r in V:
    if r["kind"].startswith("check_text"):
        print(r["ticker"], r["product"], r["text_check_later_filing"][:140])
