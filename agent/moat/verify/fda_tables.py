"""Verify supplement_approvals.csv against Drugs@FDA Submissions.txt, recalls.csv against openFDA, rems.csv lightly."""
import csv
import io
import time
import zipfile
from collections import Counter
from pathlib import Path

import requests

from agent.drug_pack import DRUGS
from agent.moat.common import store

ROOT = Path(__file__).resolve().parents[3]
OUTD = ROOT / "data/moat/verified/product"
H = {"User-Agent": "Neeley AI Forward hackathon"}


def rd(z, name):
    names = {n.lower(): n for n in z.namelist()}
    return list(csv.DictReader(io.TextIOWrapper(z.open(names[name]), encoding="latin-1"), delimiter="\t"))


def save(name, rows, extra):
    cols = list(rows[0].keys())
    for c in extra:
        if c not in cols:
            cols.append(c)
    with open(OUTD / name, "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(rows)


def supplements():
    z = zipfile.ZipFile(io.BytesIO(store().get("public/drugsatfda.zip")))
    subs = rd(z, "submissions.txt")
    prods = rd(z, "products.txt")
    by = {}
    for s in subs:
        by.setdefault((s["ApplNo"], s["SubmissionNo"]), []).append(s)
    names = {}
    for p in prods:
        names.setdefault(p["ApplNo"], set()).add(p["DrugName"].strip().upper())
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/supplement_approvals.csv")))
    for r in rows:
        cand = [s for s in by.get((r["appl_no"], r["submission_no"]), []) if s["SubmissionStatus"] == r["status"]]
        brand = DRUGS[r["drug"]][0].upper()
        if not cand:
            r["verify_status"], r["verify_note"] = "dropped", "no matching ApplNo+SubmissionNo+status row in Submissions.txt"
            continue
        dates = {s["SubmissionStatusDate"][:10] for s in cand}
        types = {s["SubmissionType"].strip() for s in cand}
        note = [f"matched Submissions.txt ApplNo {r['appl_no']} SubmissionNo {r['submission_no']} ({'/'.join(sorted(types))})"]
        st = "verified"
        if r["status_date"] not in dates:
            st = "fixed"
            note.append(f"status_date {r['status_date']} not in source; source has {sorted(dates)}")
            r["status_date"] = sorted(dates)[0]
        if len(cand) > 1:
            note.append(f"{len(cand)} source rows share this ApplNo+SubmissionNo (ORIG and SUPPL numbering overlap); "
                        f"dates {sorted(dates)}")
        if brand not in names.get(r["appl_no"], set()):
            st = "fixed" if st == "verified" else st
            note.append(f"application {r['appl_no']} product names {sorted(names.get(r['appl_no'], []))} do not include {brand}")
        r["verify_status"], r["verify_note"] = st, "; ".join(note)
    save("supplement_approvals.csv", rows, ["verify_status", "verify_note"])
    print("supplements", Counter(r["verify_status"] for r in rows))


def recalls():
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/recalls.csv")))
    for r in rows:
        j = requests.get("https://api.fda.gov/drug/enforcement.json",
                         params={"search": f'recall_number:"{r["recall_number"]}"', "limit": 5}, headers=H, timeout=60)
        res = j.json().get("results", []) if j.status_code == 200 else []
        time.sleep(0.3)
        if not res:
            r["verify_status"], r["verify_note"] = "dropped", "recall_number not found in openFDA enforcement"
            continue
        e = res[0]
        diffs = [k for k, f in (("report_date", "report_date"), ("firm", "recalling_firm"),
                                ("classification", "classification"), ("status", "status")) if r[k] != e.get(f)]
        note = ["recall_number, date, firm, class and status match openFDA enforcement record" if not diffs else
                "differs from openFDA: " + ", ".join(f"{k} {r[k]} -> {e.get(f)}" for k, f in
                                                    (("report_date", "report_date"), ("firm", "recalling_firm"),
                                                     ("classification", "classification"), ("status", "status")) if k in diffs)]
        for k, f in (("report_date", "report_date"), ("firm", "recalling_firm"), ("classification", "classification"),
                     ("status", "status")):
            r[k] = e.get(f)
        st = "fixed" if diffs else "verified"
        brand = DRUGS[r["drug"]][0].split()[0].lower()
        desc = r["product_description"].lower()
        if brand not in desc:
            prod = r["product_description"].split("(")[0].strip()[:40]
            note.append(f"product recalled is {prod}, not {DRUGS[r['drug']][0]}: matched on shared ingredient")
            r["recalled_product"] = prod
            st = "fixed"
        else:
            r["recalled_product"] = DRUGS[r["drug"]][0]
        r["verify_status"], r["verify_note"] = st, "; ".join(note)
    save("recalls.csv", rows, ["recalled_product", "verify_status", "verify_note"])
    print("recalls", Counter(r["verify_status"] for r in rows))
    for r in rows:
        print(r["drug"], r["recall_number"], r["recalled_product"], r["verify_status"], r["verify_note"][:120])


def rems():
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/rems.csv")))
    html = requests.get("https://www.accessdata.fda.gov/scripts/cder/rems/index.cfm",
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text.lower()
    for r in rows:
        b, ing = r["brand"].split()[0].lower(), r["ingredient"].lower()
        present = b in html or ing in html
        if (r["rems_active"] == "yes") == present:
            r["verify_status"], r["verify_note"] = "verified", f"REMS@FDA list re-fetched: brand/ingredient {'present' if present else 'absent'}"
        else:
            r["verify_status"] = "fixed"
            r["verify_note"] = f"REMS@FDA list re-fetched: brand/ingredient {'present' if present else 'absent'}, collector said {r['rems_active']}"
            r["rems_active"] = "yes" if present else "no"
    save("rems.csv", rows, ["verify_status", "verify_note"])
    print("rems", Counter(r["verify_status"] for r in rows), [r["drug"] for r in rows if r["rems_active"] == "yes"])


if __name__ == "__main__":
    supplements()
    recalls()
    rems()
