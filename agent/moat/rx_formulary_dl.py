"""Download the four SPUF zips to scratch and pull out the basic-formulary member (kept in scratch only)."""
import io
import re
import sys
import zipfile
from pathlib import Path

import requests

URLS = {
    "2023Q4": "https://data.cms.gov/sites/default/files/2025-01/1fc9b722-db45-4925-96c0-1bde30a2ae0f/SPUF_2024_20250131_2023q4.zip",
    "2024Q4": "https://data.cms.gov/sites/default/files/2025-01/e78ce888-f571-4d86-baf0-7a1f9efffff4/SPUF_2025_20250109.zip",
    "2025Q4": "https://data.cms.gov/sites/default/files/2026-01/5942aa7e-a0c4-4e65-bd56-32608c33649f/SPUF_2026_20260107.zip",
    "2026Q3": "https://data.cms.gov/sites/default/files/2026-10/062e9434-ed9d-4e83-abbd-4d64eb375949/SPUF_2026_20261007.zip",
}
TMP = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx/spuf")
TMP.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; neeley hackathon)"}


def main():
    for q, url in URLS.items():
        out = TMP / f"{q}_basic_formulary.txt"
        if out.exists():
            continue
        z = TMP / f"{q}.zip"
        with requests.get(url, headers=UA, stream=True, timeout=3600) as r:
            r.raise_for_status()
            with open(z, "wb") as f:
                for chunk in r.iter_content(1 << 22):
                    f.write(chunk)
        outer = zipfile.ZipFile(z)
        print(q, outer.namelist(), flush=True)
        name = next(n for n in outer.namelist() if re.search(r"basic drugs formulary", n, re.I))
        if name.lower().endswith(".zip"):
            inner = zipfile.ZipFile(io.BytesIO(outer.read(name)))
            src = inner.open(inner.namelist()[0])
        else:
            src = outer.open(name)
        with open(out, "wb") as f:
            while True:
                b = src.read(1 << 22)
                if not b:
                    break
                f.write(b)
        z.unlink()
        print(q, "done", out.stat().st_size, flush=True)


main()
