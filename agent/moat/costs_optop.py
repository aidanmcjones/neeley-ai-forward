import csv
rows = list(csv.DictReader(open("data/moat/tables/open_payments_by_drug.csv")))
tot = {}
for r in rows:
    if r["breakdown"] == "total":
        tot.setdefault(r["drug"], {})[r["program_year"]] = (float(r["usd"]), int(r["records"]))
top = sorted(tot.items(), key=lambda kv: -(kv[1].get("2024", (0, 0))[0]))
for d, v in top[:14]:
    print(d, {y: (round(a), n) for y, (a, n) in sorted(v.items())})
print("zero:", [d for d, v in tot.items() if all(a == 0 for a, n in v.values())])
