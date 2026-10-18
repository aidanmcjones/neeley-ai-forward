"""Build a standalone index for the migrated 10-K archive in R2 (tenk_archive/date=<filed>/<accession>.txt.gz).

1. Map accession -> CIK, company, form, filing date from SEC EDGAR: every registrant under the drug and biotech
   SIC codes (2834, 2835, 2836, 8731) and their full filing histories (submissions API).
2. Read each text from R2 and record Item section offsets (agent.tenk.find_sections) and size.
3. Write index/tenk_archive_index.jsonl to R2 (and data/sec/ locally). Rows the SEC lookup cannot match keep
   company=None so nothing is dropped.

Run:  python -m agent.archive_index            (about 20 to 30 minutes for ~20k filings)
"""

import gzip
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agent.tenk import ANNUAL_FORMS, Store, ciks_for_sic, find_sections, sec_get

PREFIX = "tenk_archive/"
SICS = ["2834", "2835", "2836", "8731"]
OUT_LOCAL = Path(__file__).resolve().parent.parent / "data" / "sec" / "tenk_archive_index.jsonl"


def archive_keys(store):
    keys = []
    for page in store.s3.get_paginator("list_objects_v2").paginate(Bucket=store.bucket, Prefix=PREFIX):
        keys += [o["Key"] for o in page.get("Contents", [])]
    return keys


def accession_map():
    ciks = []
    for sic in SICS:
        found = ciks_for_sic(sic)
        print(f"SIC {sic}: {len(found)} registrants", flush=True)
        ciks += found
    ciks = list(dict.fromkeys(ciks))
    amap = {}
    for i, cik in enumerate(ciks, 1):
        try:
            sub = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)
        except Exception:
            continue
        blocks = [sub.get("filings", {}).get("recent", {})]
        for page in sub.get("filings", {}).get("files", []):
            try:
                blocks.append(sec_get(f"https://data.sec.gov/submissions/{page['name']}", as_json=True))
            except Exception:
                pass
        for b in blocks:
            for j, form in enumerate(b.get("form", [])):
                if form.split("/")[0] in {f.split("/")[0] for f in ANNUAL_FORMS} or form.startswith("10-K"):
                    amap[b["accessionNumber"][j]] = {
                        "cik": cik, "company": sub.get("name"), "sic": sub.get("sic"),
                        "tickers": sub.get("tickers", []), "form": form,
                        "period": (b.get("reportDate") or [None] * len(b["form"]))[j] or None,
                        "primary_doc": b["primaryDocument"][j],
                    }
        if i % 250 == 0:
            print(f"  {i}/{len(ciks)} companies, {len(amap):,} annual filings mapped", flush=True)
    return amap


def main():
    store = Store()
    if store.kind != "r2":
        raise SystemExit("R2 credentials not set (.env)")
    keys = archive_keys(store)
    print(f"{len(keys):,} archived filings in R2", flush=True)
    amap = accession_map()

    def row(key):
        m = re.search(r"date=(\d{4}-\d{2}-\d{2})/([\d-]+)\.txt\.gz$", key)
        filed, acc = (m.group(1), m.group(2)) if m else (None, Path(key).name.split(".")[0])
        if acc.isdigit():
            acc = f"{acc[:10]}-{acc[10:12]}-{acc[12:]}" if len(acc) == 18 else acc
        meta = amap.get(acc, {})
        try:
            text = gzip.decompress(store.get(key)).decode(errors="ignore")
            sections, chars = find_sections(text), len(text)
        except Exception:
            sections, chars = {}, None
        cik = meta.get("cik")
        src = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{meta['primary_doc']}"
               if cik and meta.get("primary_doc") else None)
        return {"accession": acc, "filed_date": filed, **{k: meta.get(k) for k in
                ("cik", "company", "sic", "tickers", "form", "period", "primary_doc")},
                "source_url": src, "text_chars": chars, "storage": "r2", "storage_key": key, "sections": sections}

    rows = []
    with ThreadPoolExecutor(16) as pool:
        for i, r in enumerate(pool.map(row, keys), 1):
            rows.append(r)
            if i % 2000 == 0:
                print(f"  indexed {i:,}/{len(keys):,}", flush=True)
    data = "".join(json.dumps(r) + "\n" for r in rows).encode()
    OUT_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    OUT_LOCAL.write_bytes(data)
    store.put("index/tenk_archive_index.jsonl", data, "application/x-ndjson")
    matched = sum(1 for r in rows if r["cik"])
    print(f"done: {len(rows):,} rows, {matched:,} matched to a company ({100 * matched / max(len(rows), 1):.1f}%)")


if __name__ == "__main__":
    main()
