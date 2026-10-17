"""Fetch independent copies of earnings calls for cross-source verification (raw files under data/moat/verified/calls/src)."""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from agent.moat.common import ROOT

SRC = ROOT / "data" / "moat" / "verified" / "calls" / "src"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"

MRKU = "https://www.merck.com/wp-content/uploads/sites/124/{y}/{m}/MRK-USQ_Transcript_{d}.pdf"
PFEU = "https://s206.q4cdn.com/795948973/files/doc_financials/{fy}/{q}/PFE-USQ_Transcript_{d}.pdf"
JNJU = "https://s203.q4cdn.com/636242992/files/doc_financials/{fy}/{q}/JNJ-USQ_Transcript_{d}.pdf"

MRK = {"2024Q1": "2024-04-25", "2024Q2": "2024-07-30", "2024Q3": "2024-10-31", "2024Q4": "2025-02-04",
       "2025Q1": "2025-04-24", "2025Q2": "2025-07-29"}
PFE = {"2024Q1": "2024-05-01", "2024Q2": "2024-07-30", "2024Q3": "2024-10-29", "2024Q4": "2025-02-04",
       "2025Q1": "2025-04-29", "2025Q2": "2025-08-05"}
JNJ = {"2024Q1": "2024-04-16", "2024Q2": "2024-07-17", "2024Q3": "2024-10-15", "2024Q4": "2025-01-22",
       "2025Q1": "2025-04-15", "2025Q2": "2025-07-16", "2026Q2": "2026-07-15"}


def jobs():
    out = []
    for q, d in MRK.items():
        y, m, _ = d.split("-")
        mm = int(m)
        for mo in (mm, mm + 1 if mm < 12 else 1):
            yy = y if mo != 1 or mm == 1 else str(int(y) + 1)
            out.append((f"MRK_{q}_official.pdf", MRKU.format(y=yy, m=f"{mo:02d}", d=d)))
    for name, tmpl, table in (("PFE", PFEU, PFE), ("JNJ", JNJU, JNJ)):
        for q, d in table.items():
            fy, qq = q[:4], "q" + q[-1]
            out.append((f"{name}_{q}_official.pdf", tmpl.format(fy=fy, q=qq, d=d)))
    out.append(("JNJ_2026Q2_mb.html", "https://www.marketbeat.com/earnings/reports/2026-7-15-johnson-johnson-stock/"))
    return out


def get(j):
    name, url = j
    p = SRC / name
    if p.exists() and p.stat().st_size > 5000:
        return name, url, "cached"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    except Exception as e:
        return name, url, f"err {e}"
    ok = r.status_code == 200 and (r.content[:4] == b"%PDF" or name.endswith(".html"))
    if ok:
        p.write_bytes(r.content)
    return name, url, f"{r.status_code} {len(r.content)} {'saved' if ok else ''}"


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(6) as ex:
        for name, url, st in ex.map(get, jobs()):
            print(name, st, url, flush=True)


if __name__ == "__main__":
    main()
