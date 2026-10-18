"""costs stream: CMS Open Payments general payments by associated drug, program years 2023-2025 (marketing-spend proxy)."""
import csv
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from agent.moat.common import note_gap, write

API = "https://openpaymentsdata.cms.gov/api/1"
YEARS = {2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9", 2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff"}
YEARS_EXTRA = {
         2025: "fb0b1734-1410-429d-92f6-3f4b35218e5e"}
DRUGS = ("amjevita amvuttra apretude attruby biktarvy cabenuva cosentyx darzalex darzalex-faspro dovato eliquis enbrel entyvio "
         "farxiga foundayo humira ibrance imfinzi janumet januvia jardiance keytruda keytruda-qlex kisqali lazcluze leqvio "
         "lipfendra mounjaro opdivo opdivo-qvantig ozempic praluent repatha rinvoq rybelsus rybrevant sarclisa skyrizi stelara "
         "tagrisso tecentriq tremfya trulicity verzenio vyndamax vyndaqel wegovy wezlana xarelto yeztugo zepbound").split()
NAME = "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_{}"
AMT = "Total_Amount_of_Payment_USDollars"


def dist_id(ds):
    r = requests.get(f"{API}/metastore/schemas/dataset/items/{ds}?show-reference-ids=true", timeout=60).json()
    return r["distribution"][0]["identifier"]


def q(d, drug, group=None, tries=4):
    name = drug.replace("-", " ").upper()
    props = [{"expression": {"operator": "sum", "operands": [AMT]}, "alias": "usd"},
             {"expression": {"operator": "count", "operands": ["record_number"]}, "alias": "n"}]
    body = {"conditions": [{"groupOperator": "or", "conditions": [{"property": NAME.format(i), "value": name, "operator": "="}
                                                                   for i in range(1, 6)]}],
            "limit": 500, "count": False, "results": True, "schema": False, "keys": True, "format": "json"}
    if group:
        props = [group] + props
        body["groupings"] = [{"property": group}]
    body["properties"] = props
    for i in range(tries):
        try:
            r = requests.post(f"{API}/datastore/query/{d}", json=body, timeout=300)
            if r.status_code == 200:
                return r.json()["results"]
            err = r.text[:200]
        except Exception as e:  # noqa
            err = str(e)
        time.sleep(3 * (i + 1))
    raise RuntimeError(err)


def one(yr, d, drug):
    cf = Path(f"data/moat/scratch/costs_op/{yr}_{drug}.json")
    if cf.exists():
        return json.load(open(cf))
    tot = q(d, drug)
    res = {"tot": tot, "nature": [], "manufacturer": []}
    if False:
        res["nature"] = q(d, drug, "Nature_of_Payment_or_Transfer_of_Value")
        res["manufacturer"] = q(d, drug, "Submitting_Applicable_Manufacturer_or_Applicable_GPO_Name")
    cf.parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(cf, "w"))
    print(yr, drug, res["tot"][0]["n"], flush=True)
    return res


def main():
    rows = []
    jobs = []
    with ThreadPoolExecutor(6) as ex:
        for yr, ds in YEARS.items():
            d = dist_id(ds)
            for drug in DRUGS:
                jobs.append((yr, d, ds, drug, ex.submit(one, yr, d, drug)))
        for yr, d, ds, drug, fut in jobs:
            res = fut.result()
            tot = res["tot"]
            n, usd = int(tot[0]["n"] or 0), float(tot[0]["usd"] or 0)
            src = f"{API}/datastore/query distribution {d} (Open Payments general payments PY{yr}, dataset {ds})"
            rows.append({"drug": drug, "program_year": yr, "breakdown": "total", "category": "all", "records": n,
                         "usd": round(usd, 2), "source": src, "source_row": f"{drug}|{yr}|total"})
            for col, tag in (("Nature_of_Payment_or_Transfer_of_Value", "nature"),
                             ("Submitting_Applicable_Manufacturer_or_Applicable_GPO_Name", "manufacturer")):
                for x in res[tag]:
                    rows.append({"drug": drug, "program_year": yr, "breakdown": tag, "category": x[col], "records": int(x["n"]),
                                 "usd": round(float(x["usd"] or 0), 2), "source": src,
                                 "source_row": f"{drug}|{yr}|{tag}|{x[col]}"})
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    write("costs", "tables/open_payments_by_drug.csv", buf.getvalue(), group="costs", doc_type="table",
          source_url=API, upload=False)
    for r in rows:
        if r["breakdown"] == "total" and r["records"] == 0:
            note_gap("costs", None, f"Open Payments {r['drug']} PY{r['program_year']}", "no records under exact name match")


if __name__ == "__main__":
    main()
