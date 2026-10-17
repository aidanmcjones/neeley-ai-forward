"""Ground truth outside the filings: FAERS (openFDA), NADAC (CMS) and ClinicalTrials.gov fetchers.

Each fetcher writes data/outside/<source>/<slug>.json = {"source_url", "retrieved_at", "rows": [...]} (+ "error" on failure).
Idempotent: an existing file is skipped unless --refresh. CLI: python -m agent.needle.outside [--refresh] [--only faers|nadac|trials]
"""

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path

import requests

from agent.needle.detect import CASE_SETS, SHORTLIST

ROOT = Path(__file__).resolve().parent.parent.parent
OUTSIDE = ROOT / "data" / "outside"
FAERS = "https://api.fda.gov/drug/event.json"
NADAC_SEARCH = "https://data.medicaid.gov/api/1/search"
NADAC_QUERY = "https://data.medicaid.gov/api/1/datastore/query/{id}/0"
CT = "https://clinicaltrials.gov/api/v2/studies"
SPONSORS = {"MRK": ["Merck Sharp & Dohme", "Merck"], "BMY": ["Bristol-Myers Squibb"], "PFE": ["Pfizer"],
            "LLY": ["Eli Lilly and Company"], "NVO": ["Novo Nordisk"], "ABBV": ["AbbVie"],
            "JNJ": ["Janssen", "Johnson & Johnson"], "AZN": ["AstraZeneca"], "AMGN": ["Amgen"],
            "GILD": ["Gilead Sciences"]}


def _ua():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("SEC_USER_AGENT"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return "NEEDLE research"


S = requests.Session()
S.headers["User-Agent"] = _ua()


def _get(url, params=None, tries=2):
    last = None
    for _ in range(tries):
        try:
            r = S.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5)
    raise last


def _write(source, slug, url, rows, **extra):
    p = OUTSIDE / source / f"{slug}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"source_url": url, "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                             "rows": rows, **extra}, indent=1), encoding="utf-8")
    return p


def products():
    out = []
    for prods in CASE_SETS.values():
        for k, rivals in prods.items():
            for s in [k, *rivals]:
                if s not in out:
                    out.append(s)
    return out


# ---- FAERS ----------------------------------------------------------------------------------------------------
def _faers_search(brand):
    b = brand.upper()
    # openFDA's harmonized brand_name misses some brands (ELIQUIS), so also match the reported product name
    return f'(patient.drug.openfda.brand_name:"{b}"+OR+patient.drug.medicinalproduct:"{b}")'


def _faers_daily(search, lo, hi):
    url = f"{FAERS}?search={search}+AND+receivedate:[{lo}+TO+{hi}]&count=receivedate&limit=500"
    last = None
    for _ in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 404:  # openFDA: 404 NOT_FOUND = zero matches
                return {}, url
            r.raise_for_status()
            return {x["time"]: x["count"] for x in r.json()["results"]}, url
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2)
    raise last


def faers_latest_date():
    y = dt.date.today().year
    d = _get(f"{FAERS}?search=receivedate:[{y}0101+TO+{y}1231]&count=receivedate&limit=500")
    return max(x["time"] for x in d["results"])


def _last_quarters(latest, n):
    ld = dt.datetime.strptime(latest, "%Y%m%d").date()
    y, q = ld.year, (ld.month - 1) // 3 + 1
    qend = dt.date(y + (q == 4), (q * 3) % 12 + 1, 1) - dt.timedelta(days=1)
    if ld < qend:  # latest quarter not fully covered yet
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    out = []
    for _ in range(n):
        out.append((y, q))
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    return out[::-1]


def fetch_faers(slug, refresh=False, n_quarters=12, latest=None):
    if (OUTSIDE / "faers" / f"{slug}.json").exists() and not refresh:
        return "skip"
    latest = latest or faers_latest_date()
    quarters = _last_quarters(latest, n_quarters)
    lo = f"{quarters[0][0]}{(quarters[0][1] - 1) * 3 + 1:02d}01"
    hi = f"{quarters[-1][0]}1231"
    base = _faers_search(slug)
    rows = {f"{y}Q{q}": {"quarter": f"{y}Q{q}", "reports": 0, "serious": 0} for y, q in quarters}
    urls = []
    try:
        for key, search in (("reports", base), ("serious", base + "+AND+serious:1")):
            for yr in range(quarters[0][0], quarters[-1][0] + 1):  # one daily-count call per calendar year (<=1000 days)
                daily, url = _faers_daily(search, max(lo, f"{yr}0101"), min(hi, f"{yr}1231"))
                urls.append(url)
                for d, c in daily.items():
                    qq = f"{d[:4]}Q{(int(d[4:6]) - 1) // 3 + 1}"
                    if qq in rows:
                        rows[qq][key] += c
                time.sleep(0.3)
    except Exception as e:  # noqa: BLE001
        return _write("faers", slug, urls[0] if urls else FAERS, [], error=f"{type(e).__name__}: {e}")
    return _write("faers", slug, urls[0], list(rows.values()), latest_receivedate=latest,
                  query=f"brand_name or medicinalproduct = {slug.upper()}", urls=urls)


# ---- NADAC ----------------------------------------------------------------------------------------------------
def nadac_datasets():
    """[(year, dataset id)] for the calendar-year NADAC datasets, newest first."""
    d = _get(NADAC_SEARCH, {"fulltext": "NADAC", "page-size": 50})
    out = []
    for v in d["results"].values():
        m = re.fullmatch(r"NADAC \(National Average Drug Acquisition Cost\) (\d{4})", v["title"])
        if m:
            out.append((int(m.group(1)), v["identifier"]))
    return sorted(out, reverse=True)


def fetch_nadac(slug, refresh=False, datasets=None, years=3):
    if (OUTSIDE / "nadac" / f"{slug}.json").exists() and not refresh:
        return "skip"
    cutoff = (dt.date.today() - dt.timedelta(days=365 * years)).isoformat()
    rows, url = [], NADAC_SEARCH
    try:
        datasets = datasets or nadac_datasets()
        for yr, ident in datasets:
            if yr < int(cutoff[:4]):
                continue
            url = NADAC_QUERY.format(id=ident)
            off = 0
            while True:
                d = _get(url, {"conditions[0][property]": "ndc_description", "conditions[0][operator]": "contains",
                               "conditions[0][value]": slug.upper(), "limit": 500, "offset": off})
                for r in d["results"]:
                    if r["effective_date"] >= cutoff and r["ndc_description"].upper().startswith(slug.upper()):
                        rows.append({k: r[k] for k in ("effective_date", "nadac_per_unit", "ndc_description", "ndc", "pricing_unit")})
                if len(d["results"]) < 500:
                    break
                off += 500
        return _write("nadac", slug, url, rows, note="empty rows = brand not in NADAC (retail-pharmacy NDCs only)")
    except Exception as e:  # noqa: BLE001
        return _write("nadac", slug, url, [], error=f"{type(e).__name__}: {e}")


# ---- ClinicalTrials.gov ---------------------------------------------------------------------------------------
def fetch_trials(ticker, refresh=False):
    if (OUTSIDE / "trials" / f"{ticker}.json").exists() and not refresh:
        return "skip"
    since = (dt.date.today() - dt.timedelta(days=548)).isoformat()
    rows, seen = [], set()
    try:
        for spons in SPONSORS[ticker]:
            tok = None
            while True:
                p = {"query.spons": spons, "filter.overallStatus": "TERMINATED|WITHDRAWN|SUSPENDED",
                     "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{since},MAX] AND (AREA[Phase]PHASE2 OR AREA[Phase]PHASE3)",
                     "fields": "NCTId,BriefTitle,OverallStatus,WhyStopped,LastUpdatePostDate,Phase,LeadSponsorName",
                     "pageSize": 200, **({"pageToken": tok} if tok else {})}
                d = _get(CT, p)
                for s in d.get("studies", []):
                    pm = s["protocolSection"]
                    idm, st = pm["identificationModule"], pm["statusModule"]
                    nct = idm["nctId"]
                    ph = pm.get("designModule", {}).get("phases", [])
                    lead = pm.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "")
                    if nct in seen or not any(x in ph for x in ("PHASE2", "PHASE3")):
                        continue
                    if not any(w.lower() in lead.lower() for w in SPONSORS[ticker]):
                        continue
                    seen.add(nct)
                    rows.append({"nct_id": nct, "title": idm.get("briefTitle", ""), "status": st.get("overallStatus"),
                                 "why_stopped": st.get("whyStopped", ""),
                                 "last_update": st.get("lastUpdatePostDateStruct", {}).get("date"),
                                 "phases": ph, "lead_sponsor": lead, "url": f"https://clinicaltrials.gov/study/{nct}"})
                tok = d.get("nextPageToken")
                if not tok:
                    break
        return _write("trials", ticker, CT, rows, sponsors_queried=SPONSORS[ticker], since=since)
    except Exception as e:  # noqa: BLE001
        return _write("trials", ticker, CT, [], error=f"{type(e).__name__}: {e}")


def load(source, slug):
    p = OUTSIDE / source / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--only", choices=["faers", "nadac", "trials"])
    a = ap.parse_args()
    prods = products()
    if a.only in (None, "faers"):
        latest = faers_latest_date()
        for s in prods:
            print("faers", s, fetch_faers(s, a.refresh, latest=latest) == "skip" and "skip" or "ok", flush=True)
    if a.only in (None, "nadac"):
        ds = nadac_datasets()
        for s in prods:
            print("nadac", s, fetch_nadac(s, a.refresh, datasets=ds) == "skip" and "skip" or "ok", flush=True)
    if a.only in (None, "trials"):
        for t in SHORTLIST:
            print("trials", t, fetch_trials(t, a.refresh) == "skip" and "skip" or "ok", flush=True)


if __name__ == "__main__":
    main()
