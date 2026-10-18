"""Pull Part D prescriber-by-drug rows for the case ingredients, per year, to scratch + R2 (rx/raw/)."""
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from agent.drug_pack import DRUGS
from agent.moat.common import store

YEARS = {2019: "2a6705e6-7a1e-460c-ba22-35249a531918", 2020: "7795fe20-e80e-435a-a9ed-d2d65e05feeb",
         2021: "f68114ed-f854-4ffc-9c6e-ed78b5e2f8d0", 2022: "b101b457-ffa4-49bb-8fd9-27c1266086e2",
         2023: "e54db557-cd82-4e91-a0fe-61aad5865d69", 2024: "9552739e-3d05-4c1b-8eff-ecabf391e2e5"}
TMP = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx")
S = requests.Session()
KEEP = ["Prscrbr_NPI", "Prscrbr_State_Abrvtn", "Prscrbr_Type", "Brnd_Name", "Gnrc_Name", "Tot_Clms",
        "Tot_30day_Fills", "Tot_Drug_Cst", "Tot_Benes"]


def get(url, params, tries=6):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=120)
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError(url)


def pull(year, ing):
    base = f"https://data.cms.gov/data-api/v1/dataset/{YEARS[year]}/data"
    p = {"filter[Gnrc_Name][operator]": "CONTAINS", "filter[Gnrc_Name][value]": ing}
    n = get(base + "/stats", p)["found_rows"]
    rows = []
    for off in range(0, n, 5000):
        rows += get(base, {**p, "size": 5000, "offset": off})
    return rows


def main():
    ings = sorted({v[2].lower().split(";")[0].split(",")[0].strip() for v in DRUGS.values()})
    for year in YEARS:
        out = TMP / f"partd_{year}.csv.gz"
        if out.exists():
            continue
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(lambda i: (i, pull(year, i)), ings))
        recs = []
        for ing, rows in res:
            for r in rows:
                recs.append({"query_ingredient": ing,
                             "source_row": f"{year}:{r['Prscrbr_NPI']}:{r['Brnd_Name']}:{r['Gnrc_Name']}",
                             **{k: r.get(k) for k in KEEP}})
            print(year, ing, len(rows), flush=True)
        df = pd.DataFrame(recs).drop_duplicates("source_row")
        df.to_csv(out, index=False)
        store().put(f"rx/raw/partd_prescribers_{year}.csv.gz", out.read_bytes(), "application/gzip")


if __name__ == "__main__":
    main()
