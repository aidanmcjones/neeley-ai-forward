import csv, json, collections
R = list(csv.DictReader(open("data/moat/tables/restatements.csv")))
P = list(csv.DictReader(open("data/moat/tables/product_revenue_quarterly.csv")))
print(collections.Counter(r["ticker"] for r in R))
print(collections.Counter(r["concept"] for r in R).most_common(10))
print(collections.Counter(r["ticker"] for r in P))
print(collections.Counter(r["concept"] for r in P).most_common(15))
print(collections.Counter((r["ticker"], r["form"]) for r in P))
d = collections.Counter()
for r in R:
    s, e = r["period_start"], r["period_end"]
    d[r["n_values"]] += 1
print(d)
import statistics
pc = [float(r["pct_diff"]) for r in R]
print("pct buckets", collections.Counter(round(min(x,100)//5*5) for x in pc))
for r in R[:15]:
    print(r["ticker"], r["product_member"], r["geography"], r["other_dims"][:80], r["period_start"], r["period_end"], r["pct_diff"], r["values_by_accession"][:200])
