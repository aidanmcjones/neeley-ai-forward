"""Open Payments: general and research payments tied to the case drugs, program years 2021-2024.

A payment record can name up to 5 products and each is credited the full amount, so drug totals overlap.
Queries are unindexed table scans (about 30 s each), so they are batched with IN lists and cached.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from agent.drug_pack import DRUGS
from agent.moat.common import write

GEN = {2021: "0380bbeb-aea1-58b6-b708-829f92a48202", 2022: "df01c2f8-dc1f-4e79-96cb-8208beaf143c",
       2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9", 2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff"}
RES = {2021: "ce1d28dd-0094-5060-a036-580329439600", 2022: "fdc3c773-018a-412c-8a81-d7b8a13a037b",
       2023: "ec9521bf-9d97-4603-814c-f4132d34bc4f", 2024: "2f15cb85-8887-4dcc-a318-1f8ec1d815b3"}
TMP = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx/op")
TMP.mkdir(parents=True, exist_ok=True)
S = requests.Session()
PN = "name_of_drug_or_biological_or_device_or_medical_supply_"
NAT = "nature_of_payment_or_transfer_of_value"
SUM = {"expression": {"operator": "sum", "operands": ["total_amount_of_payment_usdollars"]}, "alias": "usd"}
CNT = {"expression": {"operator": "count", "operands": ["record_id"]}, "alias": "n"}
PHYS_FROM = 2024  # distinct-physician counts cost one 30 s table scan per drug-slot-year, so only the latest year
BRANDS = {slug: v[0].upper() for slug, v in DRUGS.items()}
SLUG = {b: s for s, b in BRANDS.items()}


def post(ds, body, cache):
    f = TMP / cache
    if f.exists():
        return json.loads(f.read_text())
    u = f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{ds}/0"
    out, off, count = [], 0, None
    while True:
        b = {**body, "limit": 500, "offset": off, "results": True, "count": True, "schema": False}
        for i in range(8):
            try:
                r = S.post(u, json=b, timeout=900)
                if r.ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(5 * (i + 1))
        else:
            raise RuntimeError(cache)
        j = r.json()
        out += j["results"]
        count = j.get("count")
        if len(j["results"]) < 500:
            break
        off += 500
    res = {"rows": out, "count": count}
    f.write_text(json.dumps(res))
    return res


def inlist(slot):
    return [{"property": f"{PN}{slot}", "operator": "in", "value": list(BRANDS.values())}]


def bucket(nature):
    n = (nature or "").lower()
    if n.startswith("consulting"):
        return "consulting"
    if n.startswith("compensation for services other than consulting") or n.startswith("honoraria"):
        return "speaking"
    if n.startswith("food"):
        return "food"
    if n.startswith("travel"):
        return "travel"
    if n.startswith("education") or "continuing education" in n:
        return "education"
    return "other"


def spec(s):
    return ((s or "").split("|")[-1].strip()) or "Unspecified"


def job_gen(a):
    kind, year, slot = a
    p = f"{PN}{slot}"
    if kind == "nat":
        return post(GEN[year], {"conditions": inlist(slot), "properties": [p, NAT, SUM, CNT], "groupings": [p, NAT]}, f"gen_nat_{year}_{slot}.json")
    return post(GEN[year], {"conditions": inlist(slot), "properties": [p, "covered_recipient_specialty_1", SUM, CNT],
                            "groupings": [p, "covered_recipient_specialty_1"]}, f"gen_spec_{year}_{slot}.json")


def job_phys(a):
    year, slot, brand = a
    if not (TMP / f"gen_phys_{year}_{slot}_{brand}.json").exists():
        return None  # timeboxed: resume by deleting this early return and rerunning
    conds = [{"property": f"{PN}{slot}", "operator": "=", "value": brand},
             {"property": "covered_recipient_type", "operator": "=", "value": "Covered Recipient Physician"}]
    r = post(GEN[year], {"conditions": conds, "properties": ["covered_recipient_npi"], "groupings": ["covered_recipient_npi"], "limit": 1}, f"gen_phys_{year}_{slot}_{brand}.json")
    return r["count"]


def job_res(a):
    year, slot = a
    p = f"{PN}{slot}"
    return post(RES[year], {"conditions": inlist(slot), "properties": [p, SUM, CNT], "groupings": [p]}, f"res_{year}_{slot}.json")


def main():
    years, slots = list(GEN), range(1, 6)
    with ThreadPoolExecutor(8) as ex:
        nat = list(ex.map(job_gen, [("nat", y, s) for y in years for s in slots]))
        spc = list(ex.map(job_gen, [("spec", y, s) for y in years for s in slots]))
    print("nat/spec done", flush=True)
    keys = [(y, s) for y in years for s in slots]
    agg = {}
    for (y, s), r in zip(keys, nat):
        for x in r["rows"]:
            k = (y, SLUG.get(x[f"{PN}{s}"].upper()))
            if k[1] is None:
                continue
            d = agg.setdefault(k, {"nat": {}, "n": 0, "spec": {}, "slots": set()})
            b = bucket(x[NAT])
            d["nat"][b] = d["nat"].get(b, 0) + float(x["usd"] or 0)
            d["n"] += int(x["n"])
            d["slots"].add(s)
    for (y, s), r in zip(keys, spc):
        for x in r["rows"]:
            k = (y, SLUG.get(x[f"{PN}{s}"].upper()))
            if k[1] is None or k not in agg:
                continue
            sp = spec(x["covered_recipient_specialty_1"])
            agg[k]["spec"][sp] = agg[k]["spec"].get(sp, 0) + float(x["usd"] or 0)
    pj = [(y, s, BRANDS[slug]) for (y, slug), d in agg.items() for s in d["slots"] if y >= PHYS_FROM]
    with ThreadPoolExecutor(16) as ex:
        pc = list(ex.map(job_phys, pj))
    phys = {}
    for (y, s, b), c in zip(pj, pc):
        if c is None:
            phys[(y, SLUG[b])] = -1
        elif phys.get((y, SLUG[b])) != -1:
            phys[(y, SLUG[b])] = phys.get((y, SLUG[b]), 0) + c
    rows = []
    for (y, slug), d in sorted(agg.items(), key=lambda t: (t[0][1], t[0][0])):
        sp = sorted(d["spec"].items(), key=lambda t: -t[1])[:5]
        rows.append({"drug": slug, "brand": BRANDS[slug], "program_year": y, "total_usd": round(sum(d["nat"].values()), 2),
                     "n_payments": d["n"], "n_physicians_upper_bound": (phys.get((y, slug)) if phys.get((y, slug), -1) >= 0 else None),
                     **{f"usd_{k}": round(d["nat"].get(k, 0), 2) for k in ("consulting", "speaking", "food", "travel", "education", "other")},
                     "top_specialties_by_usd": "; ".join(f"{k}:{v:.0f}" for k, v in sp),
                     "source": f"https://openpaymentsdata.cms.gov/dataset/{GEN[y]}",
                     "source_row": f"general_payments PY{y} product={BRANDS[slug]} slots {sorted(d['slots'])}"})
    df = pd.DataFrame(rows)
    write("rx", "tables/open_payments_by_drug.csv", df.to_csv(index=False), group="rx", doc_type="table",
          source_url="https://openpaymentsdata.cms.gov/")
    print(df.groupby("drug")["total_usd"].sum().sort_values(ascending=False).head(12), flush=True)

    with ThreadPoolExecutor(8) as ex:
        rres = list(ex.map(job_res, keys))
    rr = {}
    for (y, s), r in zip(keys, rres):
        for x in r["rows"]:
            slug = SLUG.get(x[f"{PN}{s}"].upper())
            if slug:
                d = rr.setdefault((slug, y), [0.0, 0])
                d[0] += float(x["usd"] or 0)
                d[1] += int(x["n"])
    rdf = pd.DataFrame([{"drug": s, "brand": BRANDS[s], "program_year": y, "research_usd": round(v[0], 2), "n_research_payments": v[1],
                         "source": f"https://openpaymentsdata.cms.gov/dataset/{RES[y]}",
                         "source_row": f"research_payments PY{y} product={BRANDS[s]}"} for (s, y), v in sorted(rr.items())])
    write("rx", "tables/open_payments_research.csv", rdf.to_csv(index=False), group="rx", doc_type="table",
          source_url="https://openpaymentsdata.cms.gov/")
    print(len(df), len(rdf))


main()
