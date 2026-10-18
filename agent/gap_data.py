"""Pull the free data gaps for the pharma case into R2 (bucket in R2_BUCKET, normally neeley-ai-forward).

Gaps filled (see docs/research/pharma_data_map.md, section 11):
  reference   the FDA/CMS files agent/public_data.py downloaded, copied to R2       public/<file>
  partd_q     Medicare Quarterly Part D spending, 2025 Q1-Q4 (fresher than DY2024)   public/partd_quarterly_2025.csv.gz
  nadac       NADAC 2026 weekly pharmacy acquisition cost + First Time NADAC rates   public/nadac_2026.csv.gz, public/nadac_first_time.csv.gz
  firstgen    FDA first generic approvals (this year's page)                          public/first_generics.csv
  formulary   Part D formulary (SPUF, latest quarter) summarized per RXCUI           formulary/rxcui_summary.csv.gz, formulary/plan_info.csv.gz
  classes     RxClass ATC + FDA EPC class per ingredient (every brand NDA/BLA)       classes/ingredient_classes.jsonl.gz
  labels      openFDA label indications for the 14 candidates' brands                classes/brand_indications.jsonl.gz
  trials      ClinicalTrials.gov Phase 2/3 since 2018, per candidate company         trials/<cik>.jsonl.gz
  eightk      8-Ks since 2020 with Items 2.02 / 7.01 / 8.01, primary doc + EX-99      8k/<cik>/<accession>.txt.gz
              (copied from the Catalyst Lab bucket when it already holds the filing)
  products    product-level revenue facts from each 10-K's XBRL instance             xbrl_product/<cik>/<accession>.jsonl.gz, xbrl_instance/...
Every step writes its rows to index/gap/<step>.jsonl (key, source URL, rows, bytes, retrieved_at).

Run:  python -m agent.gap_data --external ../scaffold/data/external              # all steps
      python -m agent.gap_data --steps trials,eightk
"""

import argparse
import csv
import gzip
import io
import json
import os
import re
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from agent.tenk import Store, html_to_text, sec_get

ROOT = Path(__file__).resolve().parent.parent
CATALYST_BUCKET = "catalyst-lab-archive"
UA = {"User-Agent": os.environ.get("SEC_USER_AGENT", "Neeley AI Forward hackathon")}

COMPANIES = {  # cik: (name, applicant / sponsor regex for FDA and ClinicalTrials.gov)
    927653: ("McKesson", r"MCKESSON"),
    1140859: ("Cencora", r"CENCORA|AMERISOURCE"),
    721371: ("Cardinal Health", r"CARDINAL HEALTH"),
    1167379: ("Alcon", r"\bALCON"),
    1860742: ("Bausch + Lomb", r"BAUSCH (AND|&|\+) LOMB|BAUSCH & LOMB"),
    1551152: ("AbbVie", r"ABBVIE|ALLERGAN|PHARMACYCLICS"),
    310158: ("Merck", r"MERCK SHARP|\bMSD\b|MERCK (AND|&) CO|MERCK RESEARCH"),
    14272: ("Bristol Myers Squibb", r"BRISTOL[- ]MYERS|CELGENE|JUNO THERA|MYOKARDIA|KARUNA"),
    78003: ("Pfizer", r"PFIZER|WYETH|HOSPIRA|SEAGEN|PHARMACIA"),
    59478: ("Eli Lilly", r"ELI LILLY|\bLILLY\b|LOXO|IMCLONE"),
    200406: ("Johnson & Johnson", r"JANSSEN|JOHNSON (AND|&) JOHNSON|ACTELION"),
    872589: ("Regeneron", r"REGENERON"),
    318154: ("Amgen", r"\bAMGEN|HORIZON THERA"),
    882095: ("Gilead", r"GILEAD|KITE PHARMA"),
}
CT_SPONSOR_QUERY = {
    927653: "McKesson", 1140859: "Cencora", 721371: "Cardinal Health", 1167379: "Alcon",
    1860742: "Bausch & Lomb", 1551152: "AbbVie OR Allergan", 310158: "Merck Sharp & Dohme",
    14272: "Bristol-Myers Squibb OR Celgene", 78003: "Pfizer", 59478: "Eli Lilly",
    200406: "Janssen OR Johnson & Johnson", 872589: "Regeneron", 318154: "Amgen", 882095: "Gilead OR Kite",
}
EIGHTK_ITEMS = {"2.02", "7.01", "8.01"}  # earnings, Reg FD (often IRA / settlement statements), other events
REVENUE_CONCEPT = re.compile(r"Revenue|Sales", re.I)
# product axes (US GAAP srt:ProductOrServiceAxis, IFRS ProductsAndServicesAxis) plus business segments,
# which is how distributors and Alcon break out revenue
BREAKDOWN_AXIS = re.compile(r"ProductOrServiceAxis|ProductsAndServicesAxis|SegmentsAxis")

store = Store()
_index_by_step = {}


def now():
    return datetime.now(timezone.utc).isoformat()


def gz(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=6)


def record(step, key, source, rows=None, nbytes=None, **extra):
    row = {"step": step, "key": key, "source": source, "rows": rows, "bytes": nbytes, "retrieved_at": now(), **extra}

    # one index file per step so steps can run in parallel processes; reruns replace rows by key
    if step not in _index_by_step:
        old = (store.get(f"index/gap/{step}.jsonl") or b"").decode().splitlines()
        _index_by_step[step] = {json.loads(l)["key"]: l for l in old if l}
    _index_by_step[step][key] = json.dumps(row)
    store.put(f"index/gap/{step}.jsonl", ("\n".join(_index_by_step[step].values()) + "\n").encode())
    print(f"  {key}  rows={rows} bytes={nbytes}", flush=True)


def fetch(url, **kw):
    for attempt in range(5):
        r = requests.get(url, headers=UA, timeout=kw.pop("timeout", 300), **kw)
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
    raise RuntimeError(f"failed after retries: {url}")


def put_csv_gz(step, key, url, content: bytes):
    rows = content.count(b"\n") - 1
    data = gz(content)
    store.put(key, data, "application/gzip")
    record(step, key, url, rows, len(data))


# ---------------------------------------------------------------- simple downloads

def step_reference(external: Path):
    for p in sorted(external.glob("*")):
        if p.is_file():
            data = p.read_bytes()
            store.put(f"public/{p.name}", data)
            record("reference", f"public/{p.name}", "agent/public_data.py", None, len(data))


def step_partd_q():
    url = "https://data.cms.gov/sites/default/files/2026-07/QDD_PTD_RQ2603_P01_V10_DQT2601_20260708.csv"
    put_csv_gz("partd_q", "public/partd_quarterly_2025.csv.gz", url, fetch(url).content)


def medicaid_download_url(dataset_id):
    meta = fetch(f"https://data.medicaid.gov/api/1/metastore/schemas/dataset/items/{dataset_id}"
                 "?show-reference-ids=true").json()
    return meta["distribution"][0]["data"]["downloadURL"]


def step_nadac():
    for key, ds in [("public/nadac_2026.csv.gz", "fbb83258-11c7-47f5-8b18-5f8e79f7e704"),
                    ("public/nadac_first_time.csv.gz", "e3af839d-8175-5be0-b94e-4a302ed7a035")]:
        url = medicaid_download_url(ds)
        put_csv_gz("nadac", key, url, fetch(url, timeout=900).content)


def step_firstgen():
    url = ("https://www.fda.gov/drugs/drug-and-biologic-approval-and-ind-activity-reports/"
           "first-generic-drug-approvals")
    tables = pd.read_html(io.StringIO(fetch(url).text))
    df = pd.concat(tables, ignore_index=True)
    data = df.to_csv(index=False).encode()
    store.put("public/first_generics.csv", data, "text/csv")
    record("firstgen", "public/first_generics.csv", url, len(df), len(data))


# ---------------------------------------------------------------- Part D formulary

def latest_spuf_url():
    catalog = fetch("https://data.cms.gov/data.json").json()
    urls = []
    for ds in catalog["dataset"]:
        if ds["title"].startswith("Quarterly Prescription Drug Plan Formulary"):
            urls += [d.get("downloadURL") for d in ds.get("distribution", []) if d.get("downloadURL", "").endswith(".zip")]
    dated = [u for u in urls if re.search(r"_(\d{8})\.zip$", u)]
    return max(dated, key=lambda u: re.search(r"_(\d{8})\.zip$", u).group(1))


def step_formulary():
    url = latest_spuf_url()
    with tempfile.TemporaryDirectory(dir=os.environ.get("CLAUDE_JOB_DIR")) as tmp:
        zpath = Path(tmp) / "spuf.zip"
        with requests.get(url, headers=UA, stream=True, timeout=3600) as r:
            r.raise_for_status()
            with open(zpath, "wb") as f:
                for chunk in r.iter_content(1 << 22):
                    f.write(chunk)
        outer = zipfile.ZipFile(zpath)

        def open_member(pattern):
            # SPUF nests one zip per file; members are pipe-delimited text
            name = next(n for n in outer.namelist() if re.search(pattern, n, re.I))
            if name.lower().endswith(".zip"):
                inner = zipfile.ZipFile(io.BytesIO(outer.read(name)))
                return inner.open(inner.namelist()[0]), name
            return outer.open(name), name

        fh, name = open_member(r"plan information")
        plans = pd.read_csv(fh, sep="|", dtype=str, encoding="latin-1")
        data = gz(plans.to_csv(index=False).encode())
        store.put("formulary/plan_info.csv.gz", data, "application/gzip")
        record("formulary", "formulary/plan_info.csv.gz", url, len(plans), len(data), member=name)

        fh, name = open_member(r"basic drugs formulary")
        parts = []
        for chunk in pd.read_csv(fh, sep="|", dtype=str, encoding="latin-1", chunksize=2_000_000,
                                 usecols=lambda c: c.upper() in {"FORMULARY_ID", "RXCUI", "TIER_LEVEL_VALUE",
                                                                  "QUANTITY_LIMIT_YN", "PRIOR_AUTHORIZATION_YN",
                                                                  "STEP_THERAPY_YN"}):
            chunk.columns = [c.upper() for c in chunk.columns]
            parts.append(chunk.drop_duplicates(["FORMULARY_ID", "RXCUI"]))
        f = pd.concat(parts).drop_duplicates(["FORMULARY_ID", "RXCUI"])
        n_form = f["FORMULARY_ID"].nunique()
        f["TIER"] = pd.to_numeric(f["TIER_LEVEL_VALUE"], errors="coerce")
        for c in ("QUANTITY_LIMIT_YN", "PRIOR_AUTHORIZATION_YN", "STEP_THERAPY_YN"):
            f[c] = f[c].eq("Y")
        g = f.groupby("RXCUI").agg(formularies=("FORMULARY_ID", "nunique"), tier_median=("TIER", "median"),
                                   tier_mean=("TIER", "mean"), prior_auth_share=("PRIOR_AUTHORIZATION_YN", "mean"),
                                   step_therapy_share=("STEP_THERAPY_YN", "mean"),
                                   quantity_limit_share=("QUANTITY_LIMIT_YN", "mean")).reset_index()
        g["coverage_share"] = g["formularies"] / n_form
        g["total_formularies"] = n_form
        data = gz(g.round(4).to_csv(index=False).encode())
        store.put("formulary/rxcui_summary.csv.gz", data, "application/gzip")
        record("formulary", "formulary/rxcui_summary.csv.gz", url, len(g), len(data), member=name,
               total_formularies=n_form)


# ---------------------------------------------------------------- drug classes and indications

def brand_products(external: Path):
    """(brand, ingredient, appl_no, applicant, modality) for every Rx NDA (Orange Book) and 351(a) BLA (Purple Book)."""
    out = []
    ob = zipfile.ZipFile(external / "orange_book.zip")
    prod = pd.read_csv(ob.open("products.txt"), sep="~", dtype=str, encoding="latin-1")
    prod = prod[(prod["Appl_Type"] == "N") & (prod["Type"] == "RX")]
    for r in prod.drop_duplicates(["Trade_Name", "Ingredient"]).itertuples():
        out.append((r.Trade_Name, r.Ingredient, r.Appl_No, r.Applicant_Full_Name, "small molecule"))
    lines = (external / "purple_book_2026_09.csv").read_text(encoding="utf-8-sig", errors="replace").splitlines()
    hdr = [i for i, l in enumerate(lines) if l.startswith("N/R/U") or l.startswith('"N/R/U')]
    pb = pd.read_csv(io.StringIO("\n".join(lines[hdr[-1]:])), dtype=str)
    pb = pb[pb["License Type"].str.startswith("351(a)", na=False)]
    for r in pb.drop_duplicates(["Proprietary Name", "Proper Name"]).itertuples():
        out.append((r[pb.columns.get_loc("Proprietary Name") + 1], r[pb.columns.get_loc("Proper Name") + 1],
                    r[pb.columns.get_loc("BLA Number") + 1], r[pb.columns.get_loc("Applicant") + 1], "biologic"))
    return out


def company_for(applicant):
    for cik, (_, rx) in COMPANIES.items():
        if applicant and re.search(rx, applicant, re.I) and not re.search(r"KGAA|EMD SERONO", applicant, re.I):
            return cik
    return None


def step_classes(external: Path):
    products = brand_products(external)
    ingredients = sorted({str(p[1]).strip().lower() for p in products if isinstance(p[1], str)})
    rows = []
    s = requests.Session()
    for i, ing in enumerate(ingredients):
        base = re.split(r";|,", ing)[0].strip()  # combination products: classify the first component too
        row = {"ingredient": ing}
        for src, extra in (("ATC", ""), ("FDASPL", "&relas=has_EPC")):
            try:
                r = s.get("https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json",
                          params={"drugName": ing if src == "FDASPL" else base, "relaSource": src}, timeout=30)
                items = r.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []) if r.ok else []
            except (requests.RequestException, ValueError):
                items = []
            row[src.lower()] = sorted({(x["rxclassMinConceptItem"]["classId"], x["rxclassMinConceptItem"]["className"])
                                       for x in items if src != "FDASPL" or x.get("rela", "").lower() == "has_epc"})
            row.setdefault("rxcui", next((x["minConcept"]["rxcui"] for x in items), None))
            time.sleep(0.06)  # RxNav allows 20 requests per second
        rows.append(row)
        if i % 500 == 0:
            print(f"  classes {i}/{len(ingredients)}", flush=True)
    data = gz("\n".join(json.dumps(r) for r in rows).encode())
    store.put("classes/ingredient_classes.jsonl.gz", data, "application/gzip")
    record("classes", "classes/ingredient_classes.jsonl.gz", "https://rxnav.nlm.nih.gov/REST/rxclass", len(rows), len(data))

    prod_rows = [{"brand": b, "ingredient": ing, "appl_no": a, "applicant": ap, "modality": m, "cik": company_for(ap)}
                 for b, ing, a, ap, m in products]
    data = gz("\n".join(json.dumps(r) for r in prod_rows).encode())
    store.put("classes/brand_products.jsonl.gz", data, "application/gzip")
    record("classes", "classes/brand_products.jsonl.gz", "Orange Book products.txt + Purple Book 351(a)",
           len(prod_rows), len(data))


def step_labels(external: Path):
    brands = sorted({(b.strip(), company_for(ap)) for b, _, _, ap, _ in brand_products(external)
                     if isinstance(b, str) and company_for(ap)})
    key = os.environ.get("OPENFDA_API_KEY")
    rows = []
    for brand, cik in brands[:950]:  # 1,000 calls per day without an API key
        params = {"search": f'openfda.brand_name:"{brand}"', "limit": 1}
        if key:
            params["api_key"] = key
        r = requests.get("https://api.fda.gov/drug/label.json", params=params, timeout=30)
        res = r.json().get("results", []) if r.ok else []
        lab = res[0] if res else {}
        rows.append({"brand": brand, "cik": cik, "set_id": lab.get("set_id"),
                     "indications": " ".join(lab.get("indications_and_usage", []))[:4000] or None,
                     "pharm_class_epc": lab.get("openfda", {}).get("pharm_class_epc"),
                     "rxcui": lab.get("openfda", {}).get("rxcui")})
        time.sleep(0.27)  # 240 per minute
    data = gz("\n".join(json.dumps(r) for r in rows).encode())
    store.put("classes/brand_indications.jsonl.gz", data, "application/gzip")
    record("labels", "classes/brand_indications.jsonl.gz", "https://api.fda.gov/drug/label.json", len(rows), len(data),
           brands_total=len(brands))


# ---------------------------------------------------------------- ClinicalTrials.gov

def step_trials():
    for cik, q in CT_SPONSOR_QUERY.items():
        name, rx = COMPANIES[cik]
        studies, token = [], None
        while True:
            params = {"query.spons": q, "pageSize": 1000, "countTotal": "true",
                      "filter.advanced": "AREA[Phase](PHASE2 OR PHASE3) AND AREA[StartDate]RANGE[2018-01-01,MAX]"}
            if token:
                params["pageToken"] = token
            d = fetch("https://clinicaltrials.gov/api/v2/studies", params=params, timeout=120).json()
            studies += d.get("studies", [])
            token = d.get("nextPageToken")
            if not token:
                break
            time.sleep(1.2)
        lead = [s for s in studies if re.search(rx, s["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"], re.I)]
        data = gz("\n".join(json.dumps(s) for s in lead).encode())
        store.put(f"trials/{cik}.jsonl.gz", data, "application/gzip")
        record("trials", f"trials/{cik}.jsonl.gz", "https://clinicaltrials.gov/api/v2/studies", len(lead), len(data),
               company=name, matched_any_role=len(studies))
        time.sleep(1.2)


# ---------------------------------------------------------------- 8-Ks

def filings_since(cik, since, forms):
    sub = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)
    pages = [sub["filings"]["recent"]] + [sec_get(f"https://data.sec.gov/submissions/{f['name']}", as_json=True)
                                          for f in sub["filings"].get("files", []) if f.get("filingTo", "9") >= since]
    for p in pages:
        for i, form in enumerate(p["form"]):
            if form in forms and p["filingDate"][i] >= since:
                yield {k: p[k][i] for k in ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")}


def catalyst_8k_keys():
    if not store.s3:
        return {}
    keys, kw = {}, {"Bucket": CATALYST_BUCKET, "Prefix": "8k/"}
    while True:
        r = store.s3.list_objects_v2(**kw)
        for o in r.get("Contents", []):
            keys[Path(o["Key"]).name.split(".")[0]] = o["Key"]
        if not r.get("IsTruncated"):
            return keys
        kw["ContinuationToken"] = r["NextContinuationToken"]


def step_eightk(since="2020-01-01"):
    have = catalyst_8k_keys()
    for cik, (name, _) in COMPANIES.items():
        rows = []
        for f in filings_since(cik, since, {"8-K", "8-K/A"}):
            items = set(filter(None, (f["items"] or "").split(",")))
            if not items & EIGHTK_ITEMS:
                continue
            acc = f["accessionNumber"]
            key = f"8k/{cik}/{acc}.txt.gz"
            if acc in have:
                store.s3.copy_object(Bucket=store.bucket, Key=key, CopySource={"Bucket": CATALYST_BUCKET, "Key": have[acc]})
                source = f"r2://{CATALYST_BUCKET}/{have[acc]}"
            else:
                folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
                idx = sec_get(f"{folder}/index.json", as_json=True)
                docs = [f["primaryDocument"]] + [x["name"] for x in idx["directory"]["item"]
                                                 if re.search(r"ex-?99", x["name"], re.I) and x["name"].endswith((".htm", ".html", ".txt"))]
                parts = []
                for d in dict.fromkeys(docs):
                    parts.append(f"=== {d} {folder}/{d}\n" + html_to_text(sec_get(f"{folder}/{d}")))
                store.put(key, gz("\n\n".join(parts).encode()), "application/gzip")
                source = f"{folder}/{f['primaryDocument']}"
            rows.append({**f, "cik": cik, "company": name, "storage_key": key, "source": source})
        data = "\n".join(json.dumps(r) for r in rows).encode()
        store.put(f"index/8k_{cik}.jsonl", data)
        record("eightk", f"index/8k_{cik}.jsonl", "https://data.sec.gov/submissions", len(rows), len(data), company=name,
               copied_from_catalyst=sum(r["source"].startswith("r2://") for r in rows))


# ---------------------------------------------------------------- product-level revenue from XBRL instances

def parse_product_revenue(xml: bytes):
    from lxml import etree

    root = etree.fromstring(xml, parser=etree.XMLParser(huge_tree=True, recover=True))
    ns_x, ns_d = "http://www.xbrl.org/2003/instance", "http://xbrl.org/2006/xbrldi"
    contexts = {}
    for c in root.iter(f"{{{ns_x}}}context"):
        dims = {m.get("dimension"): (m.text or "").strip() for m in c.iter(f"{{{ns_d}}}explicitMember")}
        if not any(BREAKDOWN_AXIS.search(d) for d in dims):
            continue
        start, end = c.findtext(f".//{{{ns_x}}}startDate"), c.findtext(f".//{{{ns_x}}}endDate")
        if not (start and end):
            continue
        contexts[c.get("id")] = (start, end, dims)
    rows = []
    for el in root.iter():
        ctx = el.get("contextRef") if isinstance(el.tag, str) else None
        if ctx not in contexts or not REVENUE_CONCEPT.search(etree.QName(el).localname) or not (el.text or "").strip():
            continue
        start, end, dims = contexts[ctx]
        days = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
        try:
            value = float(el.text)
        except ValueError:
            continue
        q = etree.QName(el)
        prefix = "us-gaap" if "fasb.org" in q.namespace else "ifrs" if "ifrs" in q.namespace else "company"
        rows.append({"concept": f"{prefix}:{q.localname}", "start": start, "end": end, "days": days,
                     "value": value, "unit": el.get("unitRef"), "dims": dims})
    return rows


def step_products(ciks=None):
    index = [json.loads(l) for l in store.get("index/tenk_index.jsonl").decode().splitlines()]
    for f in index:
        if ciks and f["cik"] not in ciks:
            continue
        cik, acc = f["cik"], f["accession"]
        folder = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
        idx = sec_get(f"{folder}/index.json", as_json=True)
        names = [x["name"] for x in idx["directory"]["item"]]
        inst = next((n for n in names if n.endswith("_htm.xml")), None) or next(
            (n for n in names if re.fullmatch(r"[a-z]+-\d{8}\.xml", n)), None)
        if not inst:
            record("products", f"xbrl_product/{cik}/{acc}.jsonl.gz", folder, 0, 0, note="no XBRL instance found")
            continue
        cached = store.get(f"xbrl_instance/{cik}/{acc}.xml.gz")
        xml = gzip.decompress(cached) if cached else sec_get(f"{folder}/{inst}").encode()
        store.put(f"xbrl_instance/{cik}/{acc}.xml.gz", gz(xml), "application/gzip")
        rows = [{"cik": cik, "company": f["company"], "accession": acc, "form": f["form"], "period": f["period"], **r}
                for r in parse_product_revenue(xml)]
        data = gz("\n".join(json.dumps(r) for r in rows).encode())
        store.put(f"xbrl_product/{cik}/{acc}.jsonl.gz", data, "application/gzip")
        record("products", f"xbrl_product/{cik}/{acc}.jsonl.gz", f"{folder}/{inst}", len(rows), len(data))


# ---------------------------------------------------------------- main

STEPS = ["reference", "partd_q", "nadac", "firstgen", "classes", "labels", "trials", "eightk", "products", "formulary"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default=",".join(STEPS))
    ap.add_argument("--ciks", default="", help="products step only: limit to these CIKs (comma separated)")
    ap.add_argument("--external", default=str(ROOT / "data" / "external"),
                    help="folder with the files agent/public_data.py downloaded")
    args = ap.parse_args()
    if store.kind != "r2":
        sys.exit("R2 credentials not set; this collector writes to R2 only")
    external = Path(args.external)
    for step in args.steps.split(","):
        print(f"== {step}", flush=True)
        fn = globals()[f"step_{step}"]
        try:
            if step in ("reference", "classes", "labels"):
                fn(external)
            elif step == "products":
                fn({int(c) for c in args.ciks.split(",") if c})
            else:
                fn()
        except Exception as e:  # keep going so one broken source does not block the rest
            print(f"  FAILED {step}: {type(e).__name__}: {e}", flush=True)
            record(step, None, None, note=f"failed: {type(e).__name__}: {str(e)[:300]}")


if __name__ == "__main__":
    main()
