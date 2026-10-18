"""NADAC history and SDUD national totals via the data.medicaid.gov datastore API."""
import sys, time, requests
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap

S = "pricing"
BASE = "https://data.medicaid.gov/api/1/datastore/query/{ds}/0"
NADAC = {2020: "c933dc16-7de9-52b6-8971-4b75992673e0", 2021: "d5eaf378-dcef-5779-83de-acdd8347d68e", 2022: "dfa2ab14-06c2-457a-9e36-5cb6d80f8d93",
         2023: "4a00010a-132b-4e4d-a611-543c9521280f", 2024: "99315a95-37ac-4eee-946a-3c523b4c481e", 2025: "f38d0706-1239-442c-a3cc-40ef1b686ac0",
         2026: "fbb83258-11c7-47f5-8b18-5f8e79f7e704"}
SDUD = {2020: "cc318bfb-a9b2-55f3-a924-d47376b32ea3", 2021: "eec7fbe6-c4c4-5915-b3d0-be5828ef4e9d", 2022: "200c2cba-e58d-4a95-aa60-14b99736808d",
        2023: "d890d3a9-6b00-43fd-8b31-fcba4c8e2909", 2024: "61729e5a-7aa8-448c-8903-ba3e0cd0ea3c", 2025: "158a1baa-5506-400a-8ec3-97756f0b0536",
        2026: "2957a7f9-9a15-453e-9afd-3bbdcbac8fd3"}
H = {"User-Agent": "Neeley AI Forward hackathon"}


def query(ds, conds, limit=5000):
    out, off = [], 0
    while True:
        p = {"limit": limit, "offset": off}
        for i, (k, v, op) in enumerate(conds):
            p[f"conditions[{i}][property]"] = k
            p[f"conditions[{i}][value]"] = v
            p[f"conditions[{i}][operator]"] = op
        for att in range(4):
            try:
                r = requests.get(BASE.format(ds=ds), params=p, headers=H, timeout=120)
                r.raise_for_status()
                break
            except Exception:
                time.sleep(3 * (att + 1))
        else:
            print("FAIL", ds, conds)
            return out
        time.sleep(0.3)
        res = r.json()["results"]
        out += res
        if len(res) < limit:
            return out
        off += limit


def brand_key(slug):
    return DRUGS[slug][0].upper()


def run_nadac():
    rows = []
    terms = [(s, brand_key(s), "brand") for s in DRUGS] + [(s, DRUGS[s][2].upper(), "generic_ingredient") for s in DRUGS]
    for y, ds in NADAC.items():
        seen, jobs = set(), []
        for slug, term, kind in terms:
            if kind == "generic_ingredient":
                if term in seen:
                    continue
                seen.add(term)
            jobs.append((slug, term, kind))
        with ThreadPoolExecutor(8) as ex:
            results = list(ex.map(lambda j: query(ds, [("ndc_description", j[1] + "%", "like")]), jobs))
        for (slug, term, kind), res in zip(jobs, results):
            for r in res:
                rows.append(dict(drug=slug, match_kind=kind, match_term=term, year_dataset=y, **{k: r[k] for k in
                    ["ndc_description", "ndc", "nadac_per_unit", "effective_date", "pricing_unit", "pharmacy_type_indicator", "explanation_code",
                     "classification_for_rate_setting", "corresponding_generic_drug_nadac_per_unit", "as_of_date"]},
                    source=f"https://data.medicaid.gov/dataset/{ds}", source_row=f"ndc={r['ndc']}|effective_date={r['effective_date']}|as_of={r['as_of_date']}|ds={y}"))
        print("nadac", y, len(rows), flush=True)
        df = pd.DataFrame(rows).drop_duplicates(["match_term", "ndc", "effective_date", "as_of_date", "year_dataset", "match_kind", "drug"])
        write(S, "tables/nadac_history.csv", df.to_csv(index=False), group="pricing", doc_type="table", source_url="https://data.medicaid.gov/dataset/fbb83258-11c7-47f5-8b18-5f8e79f7e704", upload=(y == 2026))
    got = set(df[df.match_kind == "brand"].drug)
    for s in DRUGS:
        if s not in got:
            note_gap(S, DRUGS[s][3], s, "no NADAC brand rows (not retail-pharmacy dispensed, or not yet listed)")
    print("nadac no brand:", [s for s in DRUGS if s not in got])


def run_sdud():
    rows = []
    for y, ds in SDUD.items():
        slugs = list(DRUGS)
        with ThreadPoolExecutor(8) as ex:
            results = list(ex.map(lambda sl: query(ds, [("state", "XX", "="), ("product_name", brand_key(sl) + "%", "like")]), slugs))
        for slug, res in zip(slugs, results):
            for r in res:
                rows.append(dict(drug=slug, ndc=r["ndc"], product_name=r["product_name"].strip(), utilization_type=r["utilization_type"], year=r["year"],
                    quarter=r["quarter"], units_reimbursed=r["units_reimbursed"], prescriptions=r["number_of_prescriptions"],
                    total_amount_reimbursed=r["total_amount_reimbursed"], medicaid_amount_reimbursed=r["medicaid_amount_reimbursed"],
                    non_medicaid_amount_reimbursed=r["non_medicaid_amount_reimbursed"], suppression_used=r["suppression_used"],
                    source=f"https://data.medicaid.gov/dataset/{ds}", source_row=f"state=XX|ndc={r['ndc']}|{r['utilization_type']}|{r['year']}Q{r['quarter']}"))
        print("sdud", y, len(rows), flush=True)
        df = pd.DataFrame(rows).drop_duplicates(["drug", "ndc", "utilization_type", "year", "quarter"])
        write(S, "tables/medicaid_sdud.csv", df.to_csv(index=False), group="pricing", doc_type="table", source_url="https://data.medicaid.gov/dataset/158a1baa-5506-400a-8ec3-97756f0b0536", upload=(y == 2026))
    got = set(df.drug)
    for s in DRUGS:
        if s not in got:
            note_gap(S, DRUGS[s][3], s, "no SDUD national (XX) rows by product_name prefix")
    print("sdud none:", [s for s in DRUGS if s not in got])


if __name__ == "__main__":
    for w in sys.argv[1:]:
        {"nadac": run_nadac, "sdud": run_sdud}[w]()
