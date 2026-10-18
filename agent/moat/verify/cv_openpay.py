"""Costs verifier item 3: re-query CMS Open Payments general payments (PY2023, PY2024) by associated drug name across
all 5 drug-name slots. Nature-of-payment breakdown for 6 drugs, totals for the 12 largest + 8 random others, and
retries of the 9 zero-record brands under alternative names. Cached in /tmp/cv/op."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from agent.moat.verify.pe_lib import ROOT

API = "https://openpaymentsdata.cms.gov/api/1"
YEARS = {2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9", 2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff"}
NAME = "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_{}"
AMT = "Total_Amount_of_Payment_USDollars"
NAT = "Nature_of_Payment_or_Transfer_of_Value"
C = Path("/tmp/cv/op")
NATURE6 = ["tecentriq", "entyvio", "imfinzi", "tremfya", "rinvoq", "skyrizi"]
ALT = {"attruby": ["ATTRUBY", "ACORAMIDIS"], "darzalex-faspro": ["DARZALEX FASPRO", "DARZALEX-FASPRO", "DARZALEX SC"],
       "foundayo": ["FOUNDAYO", "ORFORGLIPRON"], "keytruda-qlex": ["KEYTRUDA QLEX", "KEYTRUDA-QLEX", "KEYTRUDA SC"],
       "lazcluze": ["LAZCLUZE", "LAZERTINIB"], "lipfendra": ["LIPFENDRA"],
       "opdivo-qvantig": ["OPDIVO QVANTIG", "OPDIVO-QVANTIG", "OPDIVO SC"], "wezlana": ["WEZLANA", "USTEKINUMAB-AUUB"],
       "yeztugo": ["YEZTUGO", "LENACAPAVIR"]}


def dist(ds):
    f = C / f"dist_{ds}.txt"
    if f.exists():
        return f.read_text()
    r = requests.get(f"{API}/metastore/schemas/dataset/items/{ds}?show-reference-ids=true", timeout=60).json()
    f.write_text(r["distribution"][0]["identifier"])
    return f.read_text()


def q(yr, names, group=None):
    key = f"{yr}_{'+'.join(names)}_{group or 'tot'}".replace(" ", "_").replace("/", "_")
    f = C / f"{key}.json"
    if f.exists():
        return json.load(open(f))
    conds = [{"property": NAME.format(i), "value": n, "operator": "="} for i in range(1, 6) for n in names]
    props = [{"expression": {"operator": "sum", "operands": [AMT]}, "alias": "usd"},
             {"expression": {"operator": "count", "operands": ["record_number"]}, "alias": "n"}]
    body = {"conditions": [{"groupOperator": "or", "conditions": conds}], "limit": 500, "count": False,
            "results": True, "schema": False, "keys": True, "format": "json"}
    if group:
        props = [group] + props
        body["groupings"] = [{"property": group}]
    body["properties"] = props
    err = ""
    for i in range(3):
        try:
            t = time.time()
            r = requests.post(f"{API}/datastore/query/{dist(YEARS[yr])}", json=body, timeout=400)
            if r.status_code == 200:
                res = r.json()["results"]
                json.dump(res, open(f, "w"))
                print("ok", key, round(time.time() - t), flush=True)
                return res
            err = r.text[:200]
        except Exception as e:  # noqa: BLE001
            err = str(e)
        time.sleep(5 * (i + 1))
    print("FAIL", key, err, flush=True)
    return None


def main():
    C.mkdir(parents=True, exist_ok=True)
    op = pd.read_csv(ROOT / "data/moat/tables/open_payments_by_drug.csv")
    tot = op[op.breakdown == "total"]
    big = tot.groupby("drug").usd.sum().sort_values(ascending=False)
    top12 = list(big.index[:12])
    rnd = list(big.iloc[12:][big.iloc[12:] > 0].sample(8, random_state=7).index)
    jobs = []
    for yr in YEARS:
        for dname in NATURE6:
            jobs.append((yr, [dname.upper()], NAT))
        for dname in top12 + rnd:
            if dname not in NATURE6:
                jobs.append((yr, [dname.replace("-", " ").upper()], None))
        for dname, alts in ALT.items():
            jobs.append((yr, alts, None))
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(top12, rnd, len(jobs))
        return
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda j: q(*j), jobs))
    json.dump({"top12": top12, "rnd": rnd}, open(C / "sample.json", "w"))


if __name__ == "__main__":
    main()
