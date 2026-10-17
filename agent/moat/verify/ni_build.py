"""New-indication rebuild, step 2: for every efficacy-supplement approval row, find the DailyMed label version that
implemented it, diff its section 1 and section 14 against the prior version, take the trial(s) newly named in
section 14 as the pivotal trial(s), and pull enrollment and dates from ClinicalTrials.gov v2.
Stage output: /tmp/ni/stage.csv (reviewed by hand, then written by ni_write.py)."""
import csv
import difflib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
TMP = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp")
CT_OLD = TMP / "ct_cache"
CT = Path("/tmp/ni/ct")
SPL = json.loads(Path("/tmp/ni/spl_parsed.json").read_text())
COSTS = ROOT / "data/moat/verified/costs"

NOT_TRIAL = set("""NSCLC SCLC HNSCC CRC HCC RCC TNBC MSI MMR DMMR PD-L1 EGFR ALK HER2 HER2- BRCA FDA ECOG RECIST BICR ORR
PFS OS DFS EFS RFS DOR CPS TPS IV SC AUC HIV RNA ADA CI HR LDL LDL-C HDL HBA1C BMI CV MACE TNF IL ACR ASAS PASI IGA NYHA
CKD ESKD EGFR HF HFREF HFPEF COPD UC CD PSA AS NR-AXSPA PSO PSA JIA RA MTX DMARD DMARDS VTE DVT PE AF NVAF ACS CAD PAD
MI CABG WHO NCCN USA US EU II III IV TB GI ULN ALT AST NCI CTCAE BID QD QW Q2W Q3W Q4W Q6W ADT MCRPC NMCRPC MHSPC CRPC
SBRT CRT IMRT GEJ ESCC SCC CSCC MCC BTC HL CHL PMBCL UCC MIBC NMIBC BCG TMB TMB-H SD CR PR PD NE NA AE SAE ART CAB RPV
DTG 3TC FTC TAF TDF BIC PREP ATTR ATTR-CM ATTR-PN TTR NT-PROBNP KCCQ MRCP TIA ICH GFR UACR CYP OATP T2D T1D DPP-4 GLP-1
SGLT2 CDAI SES-CD CDEC HS HISCR GCA PMR PJIA ERA JPSA AXSPA NRAXSPA CTCL MM RRMM NDMM ASCT AL MGUS SMM ISS R-ISS FISH
HRQOL QOL PRO HSCT GVHD DMFS MFS RPFS TTP ORR DCR CNS HBV HCV HLA MRI CT PET IRC IRF RANDOMIZED EASI SCORAD VIGA BSA DLQI NRS PRN TEAE MRD NGS CTDNA CDX IHC PCR SPL OR AND THE KEYTRUDA OPDIVO YERVOY""".split())


def months(a, b):
    return round((b - a).days / 30.4375, 1)


def pdate(s):
    if not s:
        return None
    s = str(s)
    if len(s) == 7:
        s += "-15"
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def ct_get(nct):
    for p in (CT / f"{nct}.json", CT_OLD / f"{nct}.json"):
        if p.exists() and p.stat().st_size > 50:
            return json.loads(p.read_text())
    CT.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(f"https://clinicaltrials.gov/api/v2/studies/{nct}",
                                     headers={"User-Agent": "Neeley AI Forward hackathon research"})
        raw = urllib.request.urlopen(req, timeout=60).read()
        (CT / f"{nct}.json").write_bytes(raw)
        time.sleep(0.2)
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print("ct fail", nct, e)
        return None


def ct_search(term, drug_generic):
    key = re.sub(r"\W+", "_", f"{term}_{drug_generic}")
    p = CT / f"_search_{key}.json"
    CT.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        q = urllib.parse.urlencode({"query.term": term, "query.intr": drug_generic, "pageSize": 10,
                                    "fields": "NCTId,Acronym,BriefTitle,Phase,EnrollmentCount,LeadSponsorName"})
        try:
            req = urllib.request.Request(f"https://clinicaltrials.gov/api/v2/studies?{q}",
                                         headers={"User-Agent": "Neeley AI Forward hackathon research"})
            p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
            time.sleep(0.2)
        except Exception as e:  # noqa: BLE001
            print("search fail", term, e)
            return []
    hits = []
    for s in json.loads(p.read_text()).get("studies", []):
        idm = s["protocolSection"]["identificationModule"]
        acr = (idm.get("acronym") or "").upper().replace(" ", "").replace("-", "")
        if acr and acr == term.upper().replace(" ", "").replace("-", ""):
            hits.append(idm["nctId"])
    return hits


def ct_fields(d):
    ps = d["protocolSection"]
    st = ps.get("statusModule", {})
    return {"enrollment": ps.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
            "start_date": st.get("startDateStruct", {}).get("date"),
            "primary_completion_date": st.get("primaryCompletionDateStruct", {}).get("date"),
            "acronym": ps["identificationModule"].get("acronym"),
            "title": ps["identificationModule"].get("briefTitle"),
            "sponsor": ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
            "phases": ",".join(ps.get("designModule", {}).get("phases", [])),
            "conditions": " ".join(ps.get("conditionsModule", {}).get("conditions", []))}


def sents(text, sec="", head=""):
    text = re.sub(r"\[\s*see [^\]]*\]", "", text)
    text = re.sub(r"\(\s*\d+(\.\d+)?\s*\)", "", text)
    if sec and text.startswith(f"{sec} {head}"):
        text = text[len(f"{sec} {head}"):]
    text = re.sub(r"\s+", " ", text).replace(" .", ".").replace(" ,", ",")
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z])", text) if len(s.strip()) > 25]


TRIAL_RX = re.compile(r"\b([A-Z][A-Za-z]*[A-Z][A-Za-z0-9]*(?:[- ]?\d{1,4}[A-Za-z]?)?|Trial \d+|Study \d+)\s*\(\s*(NCT\d{8})")
NAME_RX = re.compile(r"\b((?:[A-Z][A-Za-z]*[A-Z]{2,}[A-Za-z]*|[A-Z]{3,})(?:[- ](?:[A-Z]{1,2})?\d{1,4}[A-Za-z]?)?)\b")
LEAD_RX = re.compile(r"(?:investigated|evaluated|demonstrated|assessed|established|studied)\s+in\s+(?:the\s+)?"
                     r"((?:[A-Z][A-Za-z0-9]*[- ]?)+\d*)")


def trials_in(text):
    """Return ordered list of (name, nct) found in a section 14 text."""
    out = []
    seen = set()
    for m in TRIAL_RX.finditer(text):
        k = m.group(2)
        if k not in seen:
            seen.add(k)
            out.append((m.group(1).strip(), k))
    for m in re.finditer(r"NCT\d{8}", text):
        if m.group(0) not in seen:
            seen.add(m.group(0))
            out.append(("", m.group(0)))
    return out


def names_in(text):
    out = []
    for m in NAME_RX.finditer(text):
        n = m.group(1)
        if not re.search(r"\d", n) and len(n) < 5:
            continue
        if n.upper() in NOT_TRIAL or len(n) < 4 or n.upper().rstrip("0123456789- ") in NOT_TRIAL:
            continue
        if not re.search(r"\d", n) and not n.isupper():
            continue
        if n not in out:
            out.append(n)
    return out


def norm(n):
    return re.sub(r"[\s-]", "", n.upper())


def main():
    rows = pd.concat([pd.read_csv(COSTS / "new_indication_benchmarks.csv").assign(src_file="kept"),
                      pd.read_csv(COSTS / "new_indication_benchmarks_dropped.csv").assign(src_file="dropped_file")])
    lc = pd.read_csv(ROOT / "data/moat/verified/product/indication_timeline.csv")
    setid = dict(zip(lc.drug, lc.setid))
    man = pd.read_csv(ROOT / "data/corpus/manifest.csv")
    tick = {r.doc_id.split(":")[1]: r.ticker for r in man.itertuples() if str(r.doc_id).endswith(":label_sections.md")}
    generic = {}
    for d in rows.drug.unique():
        p = ROOT / f"data/corpus/drugs/{d}/label_sections.md"
        g = ""
        if p.exists():
            m = re.search(r"title:.*?\(([a-z][a-z -]+)", p.read_text()[:600], re.I)
            g = m.group(1).split(" and ")[0].strip() if m else ""
        generic[d] = g
    # per-drug name -> NCT map from every version
    name2nct = {}
    for d, sid in setid.items():
        mp = {}
        for v in SPL.get(sid, {}).values():
            for _, (_, t) in v["s14"].items():
                for n, k in trials_in(t):
                    if n:
                        mp.setdefault(norm(n), k)
        name2nct[d] = mp
    out = []
    for r in rows.itertuples():
        A = date.fromisoformat(r.approval_date)
        sid = setid.get(r.drug)
        vers = sorted(((int(k), v) for k, v in SPL.get(sid, {}).items()), key=lambda x: (x[1]["eff"], x[0]))
        rec = {"drug": r.drug, "ticker": tick.get(r.drug, ""), "appl_no": r.appl_no,
               "supplement_number": int(r.submission_no), "approval_date": r.approval_date, "src_file": r.src_file,
               "letter": r.approval_letter_url, "old_nct": r.nct_id, "old_conf": r.match_confidence,
               "old_status": r.verify_status, "generic": generic.get(r.drug, ""), "setid": sid}
        idx = next((i for i, (_, v) in enumerate(vers) if date.fromisoformat(v["eff"]) >= date.fromordinal(A.toordinal() - 10)), None)
        if idx is None or idx == 0:
            rec.update(status="no_version", note="no label version on or after the approval date in the SPL cache" if idx is None
                       else "first cached label version; no prior version to diff")
            out.append(rec)
            continue
        vn, v = vers[idx]
        lag = (date.fromisoformat(v["eff"]) - A).days
        # walk forward while versions do not change s1/s14 (up to 200 days)
        j = idx
        while True:
            pv = vers[j - 1][1] if j > 0 else None
            cur = vers[j][1]
            if pv and (cur["s1"] != pv["s1"] or cur["s14"] != pv["s14"]):
                break
            if j + 1 < len(vers) and (date.fromisoformat(vers[j + 1][1]["eff"]) - A).days <= 200:
                j += 1
            else:
                break
        vn, v = vers[j]
        pvn, pv = vers[j - 1]
        lag = (date.fromisoformat(v["eff"]) - A).days
        rec.update(version=vn, prev_version=pvn, version_eff=v["eff"], lag_days=lag, rmc=v["rmc"][:300])
        old_s = [x for k, (h, t) in pv["s1"].items() for x in sents(t, k, h)]
        added = []
        for sec, (head, t) in v["s1"].items():
            for s in sents(t, sec, head):
                if s in old_s:
                    continue
                best = max((difflib.SequenceMatcher(None, s, o).ratio() for o in old_s), default=0)
                added.append((sec, head, s, round(best, 2), sec not in pv["s1"]))
        old14 = " ".join(t for _, t in pv["s14"].values())
        old_ncts = set(re.findall(r"NCT\d{8}", old14))
        old_names = set(norm(n) for n in names_in(old14))
        new_trials = []
        old_by_head = {}
        for _, (h, t) in pv["s14"].items():
            old_by_head.setdefault(norm(h), set()).update(re.findall(r"NCT\d{8}", t))
        for sec, (head, t) in v["s14"].items():
            prev = old_by_head.get(norm(head))
            for n, k in trials_in(t):
                fresh = k not in old_ncts and not (n and norm(n) in old_names)
                if fresh or (prev is None) or (k not in prev):
                    new_trials.append({"sec": sec, "head": head, "name": n, "nct": k, "via": "label_s14_nct",
                                       "fresh": fresh, "new_sec": prev is None})
        if not new_trials:
            for sec, (head, t) in v["s14"].items():
                for n in names_in(t):
                    if norm(n) not in old_names and norm(n) not in {norm(x["name"]) for x in new_trials}:
                        k = name2nct[r.drug].get(norm(n))
                        new_trials.append({"sec": sec, "head": head, "name": n, "nct": k,
                                           "via": "label_s14_nct_later_version" if k else "name_only"})
        rec["s1_added"] = json.dumps([a for a in added if a[3] < 0.97])
        rec["new_trials"] = json.dumps(new_trials)
        rec["new_s14_secs"] = ",".join(s for s in v["s14"] if s not in pv["s14"])
        rec["status"] = "diffed"
        out.append(rec)
    pd.DataFrame(out).to_csv("/tmp/ni/stage.csv", index=False)
    print(len(out))


if __name__ == "__main__":
    main()
