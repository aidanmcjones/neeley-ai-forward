"""Drugs@FDA efficacy supplements, openFDA recalls, REMS."""
import csv
import io
import re
import time
import zipfile

import requests

from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap, store

H = {"User-Agent": "Neeley AI Forward hackathon"}


def tocsv(rows, cols):
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(cols)
    w.writerows(rows)
    return f.getvalue()


def rd(z, name):
    return list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="latin-1"), delimiter="\t"))


def supplements():
    raw = store().get("public/drugsatfda.zip")
    if raw is None:
        note_gap("product", "all", "drugsatfda supplements", "R2 public/drugsatfda.zip missing")
        return 0
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = {n.lower(): n for n in z.namelist()}
    prods, subs = rd(z, names["products.txt"]), rd(z, names["submissions.txt"])
    try:
        docs = rd(z, names["applicationsdocstype_lookup.txt"])
    except Exception:
        docs = []
    cls = {r["SubmissionClassCodeID"]: r["SubmissionClassCodeDescription"] for r in rd(z, names["submissionclass_lookup.txt"])}
    for s in subs:
        s["SubmissionType"] = s["SubmissionType"].strip()
        s["SubmissionClassCodeDescription"] = cls.get(s["SubmissionClassCodeID"], "")
    appdocs = {}
    for r in rd(z, names["applicationdocs.txt"]):
        appdocs.setdefault((r["ApplNo"], r["SubmissionNo"], r["SubmissionType"].strip()), []).append(r)
    rows = []
    for slug, (brand, _, ing, _) in DRUGS.items():
        b = brand.split()[0].upper()
        appl = {p["ApplNo"] for p in prods if p["DrugName"].upper().strip() == brand.upper()}
        for s in subs:
            if s["ApplNo"] in appl and (s["SubmissionType"] == "ORIG" or (s["SubmissionType"] == "SUPPL" and "efficacy" in s["SubmissionClassCodeDescription"].lower())) and s["SubmissionStatus"] == "AP":
                links = appdocs.get((s["ApplNo"], s["SubmissionNo"], s["SubmissionType"]), [])
                rows.append([slug, s["ApplNo"], s["SubmissionNo"], s["SubmissionStatus"], s["SubmissionStatusDate"][:10],
                             s["SubmissionClassCodeDescription"], s.get("ReviewPriority", ""),
                             " ; ".join(d.get("ApplicationDocsURL", "") for d in links)[:400],
                             "R2:public/drugsatfda.zip#Submissions.txt", f"{s['ApplNo']}:{s['SubmissionNo']}"])
    rows.sort(key=lambda r: (r[0], r[4]))
    write("product", "tables/supplement_approvals.csv",
          tocsv(rows, ["drug", "appl_no", "submission_no", "status", "status_date", "submission_class", "review_priority",
                       "doc_urls", "source", "source_row"]), group="product", doc_type="table")
    print("supplements", len(rows), "cols", list(subs[0].keys()))
    return len(rows)


def recalls():
    rows = []
    seen = set()
    for slug, (brand, _, ing, _) in DRUGS.items():
        for field, term in (("openfda.brand_name", brand.split()[0]), ("openfda.generic_name", ing)):
            url = "https://api.fda.gov/drug/enforcement.json"
            q = f'{field}:"{term}" AND report_date:[20200101 TO 20261231]'
            try:
                r = requests.get(url, params={"search": q, "limit": 100}, headers=H, timeout=60)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                for e in r.json()["results"]:
                    if e["recall_number"] in seen:
                        continue
                    seen.add(e["recall_number"])
                    rows.append([slug, e["recall_number"], e["report_date"], e["recalling_firm"], e["classification"],
                                 e["status"], e["reason_for_recall"][:400], e["product_description"][:300],
                                 e.get("distribution_pattern", "")[:150], f"{url}?search={q}", e["recall_number"]])
            except Exception as ex:
                note_gap("product", slug, "openFDA enforcement", repr(ex))
            time.sleep(0.3)
    write("product", "tables/recalls.csv",
          tocsv(rows, ["drug", "recall_number", "report_date", "firm", "classification", "status", "reason",
                       "product_description", "distribution", "source", "source_row"]), group="product", doc_type="table")
    print("recalls", len(rows))


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:]:
        globals()[a]()
