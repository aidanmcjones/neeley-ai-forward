"""Costs verifier item 6 helper: fetch openFDA drugsfda records for every application in new_indication_benchmarks
(cached /tmp/cv/fda) and ClinicalTrials.gov v2 records for the sampled NCTs (cached /tmp/cv/ct)."""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

from agent.moat.verify.pe_lib import ROOT

FDA = Path("/tmp/cv/fda")
CT = Path("/tmp/cv/ct")


def get(url, path):
    if path.exists() and path.stat().st_size > 0:
        return
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Neeley AI Forward hackathon aidan@justinianhq.com"})
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:  # noqa: BLE001
        print("fail", url, e)
    time.sleep(0.25)


def main():
    FDA.mkdir(parents=True, exist_ok=True)
    CT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(ROOT / "data/moat/tables/new_indication_benchmarks.csv")
    for a in sorted(d.appl_no.unique()):
        q = f"application_number:(BLA{a:06d}+NDA{a:06d})"
        get(f"https://api.fda.gov/drug/drugsfda.json?search={q}&limit=5", FDA / f"{a}.json")
    ids = sys.argv[1:] if len(sys.argv) > 1 else sorted(d.nct_id.dropna().unique())
    for n in ids:
        get(f"https://clinicaltrials.gov/api/v2/studies/{n}?fields=protocolSection.identificationModule,"
            f"protocolSection.conditionsModule,protocolSection.sponsorCollaboratorsModule,protocolSection.armsInterventionsModule",
            CT / f"{n}.json")
    print(len(list(FDA.glob("*.json"))), len(list(CT.glob("*.json"))))


if __name__ == "__main__":
    main()
