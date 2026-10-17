"""costs stream: new-indication benchmarks. Each efficacy supplement approval joined to the best-matching Phase 3 trial from ClinicalTrials.gov."""
import csv
import io
import json
import time
from datetime import date
from pathlib import Path

import requests

from agent.moat.common import note_gap, write

CT = "https://clinicaltrials.gov/api/v2/studies"
CACHE = Path("data/moat/scratch/costs_ct")
CACHE.mkdir(parents=True, exist_ok=True)
GENERIC = {"mounjaro": "tirzepatide", "zepbound": "tirzepatide", "ozempic": "semaglutide", "wegovy": "semaglutide", "rybelsus": "semaglutide", "rybrevant": "amivantamab", "lazcluze": "lazertinib", "wezlana": "ustekinumab", "amjevita": "adalimumab", "amvuttra": "vutrisiran", "apretude": "cabotegravir", "sarclisa": "isatuximab", "keytruda-qlex": "pembrolizumab", "opdivo-qvantig": "nivolumab", "darzalex-faspro": "daratumumab hyaluronidase"}


def fetch(term):
    f = CACHE / (term.replace(" ", "_") + ".json")
    if f.exists():
        return json.load(open(f))
    out, tok = [], None
    for _ in range(6):
        p = {"query.intr": term, "filter.advanced": "AREA[Phase]PHASE3 AND AREA[StudyType]INTERVENTIONAL",
             "fields": "NCTId,BriefTitle,Phase,EnrollmentInfo,StartDateStruct,PrimaryCompletionDateStruct,OverallStatus,Condition,LeadSponsorName",
             "pageSize": 200}
        if tok:
            p["pageToken"] = tok
        r = requests.get(CT, params=p, timeout=60)
        if r.status_code != 200:
            break
        j = r.json()
        out += j.get("studies", [])
        tok = j.get("nextPageToken")
        if not tok:
            break
        time.sleep(0.3)
    if out:
        json.dump(out, open(f, "w"))
    return out


def d(s):
    if not s:
        return None
    s = s["date"]
    parts = [int(x) for x in s.split("-")]
    return date(parts[0], parts[1] if len(parts) > 1 else 6, parts[2] if len(parts) > 2 else 15)


def main():
    sup = [r for r in csv.DictReader(open("data/moat/verified/product/supplement_approvals.csv"))
           if r["status"] == "AP" and r["submission_class"].startswith("Efficacy")]
    rows = []
    byd = {}
    for r in sup:
        byd.setdefault(r["drug"], []).append(r)
    for drug, items in sorted(byd.items()):
        term = GENERIC.get(drug, drug.replace("-", " "))
        studies = fetch(term)
        cands = []
        for s in studies:
            pm = s["protocolSection"]
            st, pc = d(pm["statusModule"].get("startDateStruct")), d(pm["statusModule"].get("primaryCompletionDateStruct"))
            enr = pm.get("designModule", {}).get("enrollmentInfo", {}).get("count")
            if not (st and pc and enr):
                continue
            cands.append({"nct": pm["identificationModule"]["nctId"], "title": pm["identificationModule"]["briefTitle"], "enr": enr, "start": st, "pc": pc,
                          "phases": "/".join(pm["designModule"].get("phases", [])), "cond": "; ".join(pm.get("conditionsModule", {}).get("conditions", []))[:120],
                          "sponsor": pm["sponsorCollaboratorsModule"]["leadSponsor"]["name"], "status": pm["statusModule"]["overallStatus"]})
        for it in items:
            ad = date.fromisoformat(it["status_date"])
            best = None
            for c in cands:
                gap = (ad - c["pc"]).days
                if 0 <= gap <= 900 and c["enr"] >= 100:
                    sc = (gap, -c["enr"])
                    if best is None or sc < best[0]:
                        best = (sc, c)
            row = {"drug": drug, "appl_no": it["appl_no"], "submission_no": it["submission_no"], "approval_date": it["status_date"],
                   "review_priority": it["review_priority"], "supplement_source": it["source"] + "#" + it["source_row"], "match_method": "heuristic: Phase 3 trial with enrollment>=100 whose primary completion is 0-900 days before approval, nearest",
                   "nct_id": "", "phase": "", "enrollment": "", "start_date": "", "primary_completion": "", "months_start_to_primary_completion": "",
                   "months_primary_completion_to_approval": "", "conditions": "", "sponsor": "", "trial_title": "", "source": "", "source_row": f"{drug}|{it['appl_no']}:{it['submission_no']}"}
            if best:
                c = best[1]
                row.update({"nct_id": c["nct"], "phase": c["phases"], "enrollment": c["enr"], "start_date": c["start"], "primary_completion": c["pc"],
                            "months_start_to_primary_completion": round((c["pc"] - c["start"]).days / 30.44, 1),
                            "months_primary_completion_to_approval": round((ad - c["pc"]).days / 30.44, 1), "conditions": c["cond"], "sponsor": c["sponsor"],
                            "trial_title": c["title"], "source": f"https://clinicaltrials.gov/study/{c['nct']}"})
            else:
                row["source"] = f"{CT}?query.intr={term}&filter.advanced=AREA[Phase]PHASE3 (no trial matched)"
            rows.append(row)
        print(drug, len(items), sum(1 for r in rows if r["drug"] == drug and r["nct_id"]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    write("costs", "tables/new_indication_benchmarks.csv", buf.getvalue(), group="costs", doc_type="table", source_url=CT, upload=False)
    note_gap("costs", None, "new_indication_benchmarks", "trial-to-supplement join is heuristic (nearest completed Phase 3 before approval); no label-to-NCT crosswalk")


main()
