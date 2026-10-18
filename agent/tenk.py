"""Standalone SEC annual-report collector for the pharma case.

For each company: list its filings (data.sec.gov submissions API), download the primary document of every
annual report (10-K family, plus 20-F for foreign filers like Alcon), strip HTML to text, record where each
Item starts (Item 1 Business, 1A Risk Factors, 7 MD&A, ...), gzip it, and store it in R2 (or locally), with
one row per filing in an index. Also saves each company's XBRL financial facts.

Storage keys:   tenk/<cik>/<accession>.txt.gz     xbrl/<cik>.json     index/tenk_index.jsonl
R2 is used when R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET are set; otherwise files go
under data/sec/. SEC requires a descriptive User-Agent with a contact address: set SEC_USER_AGENT.

Usage:
  python -m agent.tenk --tickers MCK,COR,CAH,MRK,BMY,ALC --years 6
  python -m agent.tenk --sic 2834,2836,5122 --years 3 --budget-min 90
"""

import argparse
import gzip
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / "data" / "sec"
ANNUAL_FORMS = {"10-K", "10-K/A", "10-K405", "10-KT", "20-F", "20-F/A"}
# Where the case-relevant text lives. 10-K: Item 1 business/products/patents, 1A risks, 7 MD&A (product sales).
# 20-F (foreign filers such as Alcon): Item 3 key info and risk factors, 4 business, 5 operating review.
SECTION_MAP = {"10-K": {"business": "1", "risks": "1A", "mdna": "7"},
               "20-F": {"business": "4", "risks": "3", "mdna": "5"}}
MIN_INTERVAL = 0.125  # 8 requests per second, under SEC's 10 per second limit

_last_request = 0.0
_session = requests.Session()


# ---------------------------------------------------------------- HTTP

def sec_get(url, as_json=False):
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        sys.exit("Set SEC_USER_AGENT, e.g. 'Neeley AI Forward hackathon you@example.com'")
    global _last_request
    for attempt in range(5):
        wait = MIN_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        r = _session.get(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}, timeout=60)
        if r.status_code == 200:
            return r.json() if as_json else r.text
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
    raise RuntimeError(f"SEC request failed after retries: {url}")


# ---------------------------------------------------------------- storage

class Store:
    def __init__(self):
        need = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"]
        self.bucket = os.environ.get("R2_BUCKET")
        if all(os.environ.get(k) for k in need):
            import boto3

            self.s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                region_name="auto",
            )
            self.kind = "r2"
        else:
            self.s3 = None
            self.kind = "local"

    def put(self, key, data: bytes, content_type="application/octet-stream"):
        if self.s3:
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        else:
            path = LOCAL_DIR / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def get(self, key):
        try:
            if self.s3:
                return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
            return (LOCAL_DIR / key).read_bytes()
        except Exception:
            return None


# ---------------------------------------------------------------- companies

def ticker_map():
    data = sec_get("https://www.sec.gov/files/company_tickers_exchange.json", as_json=True)
    fields = data["fields"]
    rows = [dict(zip(fields, r)) for r in data["data"]]
    return {r["ticker"].upper(): int(r["cik"]) for r in rows if r.get("ticker")}


def ciks_for_sic(sic):
    """Every registrant EDGAR lists under one SIC code (company browse, 100 per page)."""
    ciks, start = [], 0
    while True:
        atom = sec_get(
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K&dateb=&owner=include"
            f"&SIC={sic}&start={start}&count=100&output=atom"
        )
        found = [int(c) for c in re.findall(r"<cik>(\d+)</cik>", atom)]
        ciks += found
        if len(found) < 100:
            return ciks
        start += 100


# ---------------------------------------------------------------- filings

def annual_filings(cik, since):
    sub = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)
    blocks = [sub.get("filings", {}).get("recent", {})]
    for page in sub.get("filings", {}).get("files", []):
        if page.get("filingTo", "9999") >= since:
            blocks.append(sec_get(f"https://data.sec.gov/submissions/{page['name']}", as_json=True))
    out, seen = [], set()
    for b in blocks:
        for i, form in enumerate(b.get("form", [])):
            acc = b["accessionNumber"][i]
            if form in ANNUAL_FORMS and b["filingDate"][i] >= since and acc not in seen:
                seen.add(acc)
                out.append({
                    "form": form, "accession": acc, "filed_date": b["filingDate"][i],
                    "period": b.get("reportDate", [None] * len(b["form"]))[i] or None,
                    "accepted_at": b.get("acceptanceDateTime", [None] * len(b["form"]))[i],
                    "primary_doc": b["primaryDocument"][i],
                })
    return sub, sorted(out, key=lambda f: f["filed_date"])


# ---------------------------------------------------------------- text

_BLOCK = re.compile(r"(?i)</?(p|div|br|tr|li|h[1-6]|table|section)\b[^>]*>")


def html_to_text(raw):
    t = re.sub(r"(?is)<ix:header>.*?</ix:header>", " ", raw)
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t = _BLOCK.sub("\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def find_sections(text):
    """{"1": [start, end], "1A": [...], "7": [...]} character offsets. Each Item heading appears in the table of
    contents and again at the real section; keep the occurrence that starts the longest span."""
    hits = []
    for m in re.finditer(r"(?im)^\s*item\s+(\d{1,2}[A-K]?)\s*[\.:\-]", text):
        hits.append((m.start(), m.group(1).upper()))
    best = {}
    for i, (pos, key) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        if key not in best or (end - pos) > (best[key][1] - best[key][0]):
            best[key] = [pos, end]
    return best


# ---------------------------------------------------------------- run

def collect(ciks, years, budget_min, store, index_path):
    since = date(date.today().year - years, 1, 1).isoformat()
    stop_at = time.monotonic() + budget_min * 60
    done = set()
    if index_path.exists():
        done = {json.loads(line)["accession"] for line in index_path.read_text().splitlines() if line.strip()}
    n_new = 0
    with index_path.open("a") as idx:
        for cik in ciks:
            if time.monotonic() > stop_at:
                print("time budget reached; rerun to resume")
                break
            try:
                sub, filings = annual_filings(cik, since)
            except Exception as e:
                print(f"skip CIK {cik}: {e}")
                continue
            name, sic = sub.get("name"), sub.get("sic")
            try:
                facts = sec_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
                store.put(f"xbrl/{cik}.json", facts.encode(), "application/json")
            except Exception:
                pass  # foreign filers and small companies may have no XBRL facts
            for f in filings:
                if f["accession"] in done or time.monotonic() > stop_at:
                    continue
                acc_path = f["accession"].replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_path}/{f['primary_doc']}"
                try:
                    text = html_to_text(sec_get(url))
                except Exception as e:
                    print(f"  fail {f['accession']}: {e}")
                    continue
                gz = gzip.compress(text.encode())
                key = f"tenk/{cik}/{f['accession']}.txt.gz"
                store.put(key, gz, "application/gzip")
                row = {**f, "cik": cik, "company": name, "sic": sic, "source_url": url,
                       "text_chars": len(text), "gz_bytes": len(gz),
                       "sha256": hashlib.sha256(text.encode()).hexdigest(),
                       "storage": store.kind, "storage_key": key, "sections": find_sections(text),
                       "fetched_at": datetime.now(timezone.utc).isoformat()}
                idx.write(json.dumps(row) + "\n")
                idx.flush()
                done.add(f["accession"])
                n_new += 1
                print(f"  {name} {f['form']} {f['filed_date']} ({len(text):,} chars)")
    store.put("index/tenk_index.jsonl", index_path.read_bytes(), "application/x-ndjson")
    print(f"done: {n_new} new filings, {len(done)} total, storage={store.kind}")


def load_text(row, store=None):
    """Full text of one indexed filing; pass a section key via section_text for one Item."""
    data = (store or Store()).get(row["storage_key"])
    return gzip.decompress(data).decode() if data else None


def section_text(row, part, store=None):
    """part: "business", "risks", "mdna", or a raw Item number like "1A"."""
    form = "20-F" if row["form"].startswith("20-F") else "10-K"
    item = SECTION_MAP[form].get(part, part)
    text = load_text(row, store)
    span = row.get("sections", {}).get(item)
    return text[span[0]:span[1]] if text and span else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tickers", help="comma-separated tickers, e.g. MCK,COR,CAH,MRK")
    p.add_argument("--ciks", help="comma-separated CIKs")
    p.add_argument("--sic", help="comma-separated SIC codes to sweep, e.g. 2834,2836,5122")
    p.add_argument("--years", type=int, default=6)
    p.add_argument("--budget-min", type=float, default=100)
    a = p.parse_args()

    ciks = []
    if a.tickers:
        tmap = ticker_map()
        for t in a.tickers.split(","):
            t = t.strip().upper()
            if t in tmap:
                ciks.append(tmap[t])
            else:
                print(f"unknown ticker {t}")
    if a.ciks:
        ciks += [int(c) for c in a.ciks.split(",")]
    if a.sic:
        for s in a.sic.split(","):
            ciks += ciks_for_sic(s.strip())
    ciks = list(dict.fromkeys(ciks))
    if not ciks:
        sys.exit("nothing to collect: pass --tickers, --ciks or --sic")

    store = Store()
    index_path = LOCAL_DIR / "tenk_index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        remote = store.get("index/tenk_index.jsonl")
        index_path.write_bytes(remote or b"")
    print(f"{len(ciks)} companies, storage={store.kind}")
    collect(ciks, a.years, a.budget_min, store, index_path)


if __name__ == "__main__":
    main()
