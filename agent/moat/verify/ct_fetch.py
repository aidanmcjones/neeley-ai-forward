"""Fetch full ClinicalTrials.gov v2 records for every NCT in head_to_head.csv (plus extra searches) into a cache."""
import csv
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/ct_cache")
H = {"User-Agent": "Neeley AI Forward hackathon"}
API = "https://clinicaltrials.gov/api/v2/studies"
# extra searches for pairs the collector could not query by generic name (code names / new INNs)
EXTRA = [("enlicitide", "evolocumab", "MK-0616 AND evolocumab"), ("enlicitide", "alirocumab", "MK-0616 AND alirocumab"),
         ("enlicitide", "inclisiran", "MK-0616 AND inclisiran"), ("enlicitide", "evolocumab", "enlicitide AND evolocumab"),
         ("orforglipron", "semaglutide", "LY3502970 AND semaglutide"), ("tafamidis", "acoramidis", "AG10 AND tafamidis"),
         ("tafamidis", "vutrisiran", "ALN-TTRSC02 AND tafamidis"), ("ustekinumab", "risankizumab", "Wezlana AND risankizumab")]


def get(params):
    for i in range(4):
        try:
            r = requests.get(API, params=params, headers=H, timeout=90)
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == 3:
                raise
            time.sleep(3)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    ids = sorted({r["nct_id"] for r in csv.DictReader(open(ROOT / "data/moat/tables/head_to_head.csv"))})
    todo = [i for i in ids if not (CACHE / f"{i}.json").exists()]
    for k in range(0, len(todo), 50):
        j = get({"filter.ids": ",".join(todo[k:k + 50]), "pageSize": 100})
        for s in j.get("studies", []):
            nct = s["protocolSection"]["identificationModule"]["nctId"]
            (CACHE / f"{nct}.json").write_text(json.dumps(s))
        print(k, len(j.get("studies", [])), flush=True)
        time.sleep(0.5)
    extra = []
    for a, b, q in EXTRA:
        j = get({"query.intr": q, "pageSize": 100})
        for s in j.get("studies", []):
            nct = s["protocolSection"]["identificationModule"]["nctId"]
            (CACHE / f"{nct}.json").write_text(json.dumps(s))
            extra.append({"nct_id": nct, "drugs": f"{a} vs {b}", "query": q})
        print(q, len(j.get("studies", [])), flush=True)
        time.sleep(0.5)
    (CACHE / "_extra.json").write_text(json.dumps(extra))
    print("missing", [i for i in ids if not (CACHE / f"{i}.json").exists()])


main()
