"""Pull CMS Part D Prescribers by Geography and Drug (national and state rows) for every case brand, 2019-2024.
These are CMS's own drug-level totals: all prescribers (no 11-claim cut) and distinct beneficiaries."""
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from agent.drug_pack import DRUGS
from agent.moat.verify.rx_lib import PD_GEO, cms, classify

OUT = "/tmp/rxv/geo.csv"


def pull(job):
    y, word, lvl = job
    rows = cms(PD_GEO[y], {"filter[Prscrbr_Geo_Lvl]": lvl, "filter[Brnd_Name][operator]": "CONTAINS",
                           "filter[Brnd_Name][value]": word})
    return [{**r, "year": y} for r in rows]


def main():
    words = sorted({v[0].split()[0].title() for v in DRUGS.values()})
    jobs = [(y, w, lvl) for y in PD_GEO for w in words for lvl in ("National",)]
    jobs += [(y, w, "State") for y in (2023, 2024) for w in ("Eliquis", "Ozempic", "Jardiance", "Mounjaro", "Repatha",
                                                              "Xarelto", "Skyrizi", "Trulicity")]
    with ThreadPoolExecutor(8) as ex:
        res = [r for rows in ex.map(pull, jobs) for r in rows]
    df = pd.DataFrame(res)
    df["drug"] = [classify(b) for b in df.Brnd_Name]
    df = df[df.drug.notna()].drop_duplicates(["year", "Prscrbr_Geo_Lvl", "Prscrbr_Geo_Desc", "Brnd_Name", "Gnrc_Name"])
    df.to_csv(OUT, index=False)
    print(df.groupby(["Prscrbr_Geo_Lvl", "year"]).size(), df[df.Prscrbr_Geo_Lvl == "National"].drug.nunique())


if __name__ == "__main__":
    main()
