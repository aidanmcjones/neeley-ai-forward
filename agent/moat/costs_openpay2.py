"""Open Payments: one grouped query per program year and drug-name slot (slots 1-2), then filter to the case drugs."""
import csv
import io
import json
import time
from pathlib import Path

import requests

from agent.moat.common import write
from agent.moat.costs_openpay import API, DRUGS, YEARS, AMT, NAME, dist_id

CACHE = Path("data/moat/scratch/costs_op2")
CACHE.mkdir(parents=True, exist_ok=True)


def page(d, slot, offset):
    col = NAME.format(slot)
    body = {"properties": [col, {"expression": {"operator": "sum", "operands": [AMT]}, "alias": "usd"},
                           {"expression": {"operator": "count", "operands": ["record_number"]}, "alias": "n"}],
            "conditions": [{"property": col, "value": [x.replace("-", " ").upper() for x in DRUGS], "operator": "in"}],
            "groupings": [{"property": col}], "limit": 500, "offset": offset, "count": False, "results": True, "schema": False, "keys": True, "format": "json"}
    for i in range(4):
        try:
            r = requests.post(f"{API}/datastore/query/{d}", json=body, timeout=600)
            if r.status_code == 200:
                return r.json()["results"]
            print("status", r.status_code, r.text[:150], flush=True)
        except Exception as e:  # noqa
            print("err", e, flush=True)
        time.sleep(5 * (i + 1))
    raise RuntimeError("failed")


def grouped(yr, d, slot):
    f = CACHE / f"{yr}_slot{slot}.json"
    if f.exists():
        return json.load(open(f))
    out, off = [], 0
    while True:
        t = time.time()
        res = page(d, slot, off)
        out += res
        print(yr, slot, off, len(res), round(time.time() - t), flush=True)
        if len(res) < 500:
            break
        off += 500
    json.dump(out, open(f, "w"))
    return out


want = {x.replace("-", " ").upper(): x for x in DRUGS}
rows = []
for yr, ds in YEARS.items():
    d = dist_id(ds)
    src = f"{API}/datastore/query distribution {d} (Open Payments general payments PY{yr}, dataset {ds}); grouped by drug-name slots 1 and 2"
    agg = {}
    for slot in (1, 2):
        for x in grouped(yr, d, slot):
            nm = (x[NAME.format(slot)] or "").strip().upper()
            if nm in want:
                a = agg.setdefault(want[nm], [0, 0.0])
                a[0] += int(x["n"] or 0)
                a[1] += float(x["usd"] or 0)
    for drug in DRUGS:
        n, usd = agg.get(drug, [0, 0.0])
        rows.append({"drug": drug, "program_year": yr, "breakdown": "total", "category": "all", "records": n, "usd": round(usd, 2), "source": src,
                     "source_row": f"{drug}|{yr}|total"})
buf = io.StringIO()
w = csv.DictWriter(buf, list(rows[0].keys()))
w.writeheader()
w.writerows(rows)
write("costs", "tables/open_payments_by_drug.csv", buf.getvalue(), group="costs", doc_type="table", source_url=API, upload=False)
print("rows", len(rows))
