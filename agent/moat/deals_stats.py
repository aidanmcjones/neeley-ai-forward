import csv, collections
rows = list(csv.DictReader(open("data/moat/tables/deal_comps.csv")))
print(len(rows))
print(collections.Counter(r["deal_type"] for r in rows))
print(collections.Counter(r["stage_at_deal"] or "unk" for r in rows))
print(collections.Counter(r["origin"] for r in rows))
print(collections.Counter(r["confidence"] for r in rows))
print("with upfront or total", sum(1 for r in rows if r["upfront_usd_m"] or r["total_potential_usd_m"]))
print("both parties", sum(1 for r in rows if r["acquirer_or_licensee"] and r["target_or_licensor"]))
print("years", sorted(collections.Counter(r["date"][:4] for r in rows).items()))
for b in csv.DictReader(open("data/moat/tables/deal_benchmarks.csv")):
    if b["therapeutic_area"] in ("ALL", "NA") or b["segment"] == "acquisition":
        print(b["segment"][:5], b["stage_at_deal"], b["therapeutic_area"], b["metric"], "n", b["n"], b["q1"], b["median"], b["q3"])
ex = [r for r in rows if r["origin"] == "edgar_8k" and r["confidence"] == "high" and r["acquirer_or_licensee"] and r["target_or_licensor"] and r["milestones_usd_m"]][:400:80]
ex += [r for r in rows if r["deal_type"] == "acquisition" and r["acquirer_or_licensee"]][:2]
for r in ex:
    print(r["deal_id"], r["date"], r["deal_type"], "|", r["acquirer_or_licensee"], "<-", r["target_or_licensor"], "|", r["asset"], r["stage_at_deal"],
          "| up", r["upfront_usd_m"], "ms", r["milestones_usd_m"], "tot", r["total_potential_usd_m"], "|", r["source_row"], "|", r["quote"][:140])
