"""Show duplicate-key rows in insider_trades.csv."""
import csv
from collections import defaultdict

rows = list(csv.DictReader(open("data/moat/tables/insider_trades.csv")))
g = defaultdict(list)
for r in rows:
    g[(r["ticker"], r["person"], r["date"], r["code"], r["shares"], r["price"], r["security"])].append(r)
for k, v in g.items():
    if len(v) > 1:
        print(k, [(x["accession"], x["owned_after"], x["acq_disp"], x["url"].rsplit("/", 1)[-1]) for x in v])
