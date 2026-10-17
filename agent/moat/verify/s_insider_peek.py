"""Peek at insider_trades.csv: roles, codes, url names, duplicate keys."""
import csv
from collections import Counter

rows = list(csv.DictReader(open("data/moat/tables/insider_trades.csv")))
print(len(rows))
print(Counter(r["code"] for r in rows).most_common())
print(Counter(r["derivative"] for r in rows))
print(Counter(r["url"].rsplit("/", 1)[-1] for r in rows).most_common(8))
print(Counter(r["role"] for r in rows).most_common(25))
print(Counter(r["date"][:4] for r in rows))
k = Counter((r["ticker"], r["person"], r["date"], r["code"], r["shares"], r["price"], r["security"]) for r in rows)
d = [x for x, c in k.items() if c > 1]
print("dup keys", len(d), sum(k[x] for x in d))
acc_by = {}
for r in rows:
    key = (r["ticker"], r["person"], r["date"], r["code"], r["shares"], r["price"], r["security"])
    acc_by.setdefault(key, set()).add(r["accession"])
multi = [(x, a) for x, a in acc_by.items() if len(a) > 1]
print("same txn in >1 accession", len(multi))
for x, a in multi[:5]:
    print(x, a)
for r in rows:
    if r["code"] in ("P",):
        print("P", r["ticker"], r["person"], r["role"], r["date"], r["value"])
