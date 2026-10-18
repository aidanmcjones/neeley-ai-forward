"""Map each case brand to RxNorm clinical-drug RXCUIs (SBD for the brand, SCD for its generic-name equivalent)."""
import json
import time
from pathlib import Path

import pandas as pd
import requests

from agent.drug_pack import DRUGS

S = requests.Session()
OUT = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx/rxcui_map.csv")


def j(url, **p):
    for i in range(5):
        try:
            r = S.get("https://rxnav.nlm.nih.gov/REST/" + url, params=p, timeout=60)
            if r.ok:
                return r.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2)
    return {}


def main():
    rows = []
    for slug, v in DRUGS.items():
        brand = v[0]
        g = j("drugs.json", name=brand)
        sbds = []
        for cg in g.get("drugGroup", {}).get("conceptGroup", []) or []:
            if cg.get("tty") in ("SBD", "BPCK"):
                for c in cg.get("conceptProperties", []) or []:
                    if brand.lower() in c["name"].lower():
                        sbds.append(c)
        for c in sbds:
            rows.append({"drug": slug, "rxcui": c["rxcui"], "tty": c["tty"], "rx_name": c["name"], "link": "brand"})
            rel = j(f"rxcui/{c['rxcui']}/related.json", tty="SCD")
            for cg in rel.get("relatedGroup", {}).get("conceptGroup", []) or []:
                for p in cg.get("conceptProperties", []) or []:
                    rows.append({"drug": slug, "rxcui": p["rxcui"], "tty": p["tty"], "rx_name": p["name"], "link": "generic_equivalent"})
        print(slug, len(sbds), flush=True)
        time.sleep(0.1)
    pd.DataFrame(rows).drop_duplicates(["drug", "rxcui"]).to_csv(OUT, index=False)


main()
