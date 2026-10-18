import csv, json, collections
R = list(csv.DictReader(open("data/moat/tables/restatements.csv")))
g = collections.defaultdict(list)
for r in R:
    v = json.loads(r["values_by_accession"])
    accs = sorted({a for l in v.values() for a in l})
    multi_in_one = len([a for l in v.values() for a in l]) != len(set(a for l in v.values() for a in l))
    g[(r["ticker"], r["concept"].split(":")[1][:20], r["product_member"])].append((r["geography"][-14:], r["other_dims"][-70:], r["period_start"], r["period_end"], r["pct_diff"], tuple(accs), multi_in_one))
out = open("data/moat/scratch/f_clusters.txt", "w")
for k, l in sorted(g.items()):
    pcts = [float(x[4]) for x in l]
    print(k, len(l), "pct", min(pcts), max(pcts), "accs", sorted({a for x in l for a in x[5]})[:5], "multi1", sum(x[6] for x in l),
          "geo", sorted({x[0] for x in l}), "dims", sorted({x[1] for x in l})[:2], "periods", sorted({x[2] + "/" + x[3] for x in l})[:4], file=out)
