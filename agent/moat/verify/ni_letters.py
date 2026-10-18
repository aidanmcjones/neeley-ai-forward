"""New-indication rebuild: fetch each supplement's FDA approval letter (URL from Drugs@FDA, already in the collector
table) and keep the 'provides for' paragraph. Cache /tmp/ni/letters/<appl>_<supp>.pdf/.txt."""
import subprocess
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path("/tmp/ni/letters")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = ROOT / "data/moat/verified/costs"
    d = pd.concat([pd.read_csv(c / "new_indication_benchmarks.csv"), pd.read_csv(c / "new_indication_benchmarks_dropped.csv")])
    for r in d.itertuples():
        url = str(r.approval_letter_url)
        if not url.startswith("http"):
            continue
        url = url.replace("http://", "https://")
        p = OUT / f"{r.appl_no}_{int(r.submission_no)}.pdf"
        if not (p.exists() and p.stat().st_size > 1000):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; aidan@justinianhq.com)"})
                p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            except Exception as e:  # noqa: BLE001
                print("fail", url, e)
                continue
            time.sleep(0.3)
        t = p.with_suffix(".txt")
        if not t.exists():
            subprocess.run(["pdftotext", "-l", "3", str(p), str(t)], check=False)
    print(len(list(OUT.glob("*.txt"))))


if __name__ == "__main__":
    main()
