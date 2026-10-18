"""rx verifier item 4 (queries): fresh Open Payments re-queries across all 5 drug-name slots, grouped by nature of
payment, for 6 PY2021-2022 drug-years the costs verifier never touched, plus 10 research drug-years. Names are matched
in upper and title case (the collector and the costs verifier both sent upper case only). Cached in /tmp/rxv/op."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

# dataset ids copied from agent/moat/rx_openpay.py (that module runs its collector on import)
GEN = {2021: "0380bbeb-aea1-58b6-b708-829f92a48202", 2022: "df01c2f8-dc1f-4e79-96cb-8208beaf143c",
       2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9", 2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff"}
RES = {2021: "ce1d28dd-0094-5060-a036-580329439600", 2022: "fdc3c773-018a-412c-8a81-d7b8a13a037b",
       2023: "ec9521bf-9d97-4603-814c-f4132d34bc4f", 2024: "2f15cb85-8887-4dcc-a318-1f8ec1d815b3"}

C = Path("/tmp/rxv/op")
C.mkdir(parents=True, exist_ok=True)
PN = "name_of_drug_or_biological_or_device_or_medical_supply_"
NAT = "nature_of_payment_or_transfer_of_value"
GEN_JOBS = [("tecentriq", 2021), ("entyvio", 2022), ("imfinzi", 2021), ("rinvoq", 2022), ("jardiance", 2021),
            ("mounjaro", 2022)]
RES_JOBS = [("biktarvy", 2021), ("biktarvy", 2024), ("amvuttra", 2023), ("cabenuva", 2021), ("keytruda", 2023),
            ("mounjaro", 2023), ("skyrizi", 2022), ("jardiance", 2024), ("tecentriq", 2022), ("eliquis", 2023)]


def names(slug):
    b = slug.replace("-", " ")
    return sorted({b.upper(), b.title()})


def post(ds, body, key):
    f = C / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    u = f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{ds}/0"
    rows, off = [], 0
    while True:
        b = {**body, "limit": 500, "offset": off, "results": True, "count": False, "schema": False}
        for i in range(6):
            try:
                r = requests.post(u, json=b, timeout=900)
                if r.ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(10 * (i + 1))
        else:
            print("FAIL", key, flush=True)
            return None
        rows += r.json()["results"]
        if len(r.json()["results"]) < 500:
            break
        off += 500
    f.write_text(json.dumps(rows))
    print("ok", key, flush=True)
    return rows


def body(slug, group):
    conds = [{"property": f"{PN}{i}", "operator": "in", "value": names(slug)} for i in range(1, 6)]
    props = [{"expression": {"operator": "sum", "operands": ["total_amount_of_payment_usdollars"]}, "alias": "usd"},
             {"expression": {"operator": "count", "operands": ["record_id"]}, "alias": "n"}]
    b = {"conditions": [{"groupOperator": "or", "conditions": conds}], "properties": ([group] if group else []) + props}
    if group:
        b["groupings"] = [group]
    return b


def main():
    jobs = [(GEN[y], body(s, NAT), f"gen_{s}_{y}") for s, y in GEN_JOBS]
    jobs += [(RES[y], body(s, None), f"res_{s}_{y}") for s, y in RES_JOBS]
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda j: post(*j), jobs))


if __name__ == "__main__":
    main()
