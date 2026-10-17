"""Pipeline verifier items 1 and 6: landscape field check vs CT.gov v2 (150 sample), epi-vocabulary classifier,
stale registry dates. Usage: python -m agent.moat.verify.pp_land [--write]
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

from agent.moat.common import write

C = Path("data/moat/verify/pp_cache")
d = pd.read_csv("data/moat/tables/pipeline_landscape.csv")
sample = pd.read_csv(C / "ct_sample.csv").nct_id.tolist()
PH = {"PHASE2": "Phase 2", "PHASE3": "Phase 3"}

# epi vocabulary (data/moat/verified/epi/indication_map.csv) plus landscape-only labels. First match wins, so the
# specific subtypes come before the broad organ terms.
EPI = [
    ("NSCLC", r"non[- ]?small[- ]?cell lung|lung cancer, non-small|carcinoma, non-small|\bnsclc\b"),
    ("SCLC", r"\bsmall[- ]cell lung|\bsclc\b|extensive[- ]stage"),
    ("malignant pleural mesothelioma", r"mesothelioma"),
    ("triple-negative breast cancer", r"triple[- ]negative|\btnbc\b"),
    ("HER2+ breast cancer", r"(her2[- ]?(\+|positive|amplified|overexpress)|pertuzumab|perjeta|trastuzumab biosimilar)"
                            r".{0,80}breast|breast.{0,80}her2[- ]?(\+|positive|amplified)|disitamab.{0,80}breast"),
    ("HR+/HER2- breast cancer", r"hormone receptor[- ]positive|\bhr\+|hr-positive|\ber\+|er-positive|"
                                r"estrogen receptor[- ]positive|her2[- ](negative|-).{0,60}breast|luminal|"
                                r"(fulvestrant|letrozole|anastrozole|endocrine|palbociclib|ribociclib|abemaciclib|"
                                r"cdk4/6|serd\b).{0,120}breast|breast.{0,120}(fulvestrant|endocrine|cdk4/6|letrozole)"),
    ("breast cancer, subtype unstated (no epi row)", r"breast"),
    ("colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H", r"colorectal|msi-h|dmmr"),
    ("hepatocellular carcinoma", r"hepatocellular|\bhcc\b|liver cancer"),
    ("biliary tract cancer", r"biliary|cholangio|gallbladder"),
    ("renal cell carcinoma", r"renal cell|kidney cancer|\brcc\b"),
    ("urothelial / bladder cancer", r"urothelial|(?<!gall )bladder (cancer|neoplasm|carcinoma)|\bnmibc\b|\bmibc\b"),
    ("gastric / GEJ cancer", r"gastric (cancer|adenocarcinoma|carcinoma)|stomach (cancer|neoplasm)|"
                             r"gastro-?(o)?esophageal junction|\bgej\b"),
    ("esophageal cancer", r"(o)?esophageal (cancer|carcinoma|squamous|adenocarcinoma|neoplasm)|\bescc\b"),
    ("HNSCC", r"head and neck|\bhnscc\b|oropharyn|nasopharyn"),
    ("cutaneous squamous cell carcinoma", r"cutaneous squamous"),
    ("melanoma", r"melanoma"),
    ("multiple myeloma", r"myeloma"),
    ("lymphoma (cHL / PMBCL)", r"lymphoma"),
    ("AL amyloidosis", r"\bal amyloidosis|light[- ]chain amyloid"),
    ("ATTR-CM", r"transthyretin.{0,40}cardiomyopathy|attr-?cm|cardiac amyloid|amyloid.{0,30}cardiomyopathy|\battr\b"),
    ("hATTR polyneuropathy", r"polyneuropathy"),
    ("psoriatic arthritis", r"psoriatic arthritis"),
    ("plaque psoriasis", r"psoriasis"),
    ("hidradenitis suppurativa", r"hidradenitis"),
    ("ankylosing spondylitis / axSpA", r"ankylosing|axial spondyl|axspa"),
    ("juvenile arthritis (JIA / JPsA / ERA)", r"juvenile (idiopathic )?arthritis|\bjia\b"),
    ("rheumatoid arthritis", r"rheumatoid"),
    ("Crohn's disease", r"crohn"),
    ("ulcerative colitis", r"ulcerative colitis"),
    ("atopic dermatitis", r"atopic dermatitis|\beczema"),
    ("HIV PrEP", r"pre-?exposure prophylaxis|\bprep\b|low[- ]risk for human immunodeficiency|prevent.{0,20}hiv"),
    ("HIV-1 treatment", r"\bhiv\b|human immunodeficiency"),
    ("MASH", r"\bnash\b|\bmash\b|steatohepatitis|\bmasld\b|\bnafld\b|steatotic"),
    ("obstructive sleep apnea (with obesity)", r"sleep apnea"),
    ("atrial fibrillation (stroke prevention)", r"atrial fibrillation|stroke prevention"),
    ("venous thromboembolism (DVT/PE)", r"venous thrombo|thromboembol|deep vein|pulmonary embol|\bvte\b"),
    ("hypercholesterolemia (incl. HeFH)", r"cholesterol|\bldl|lipoprotein\(a\)|lp\(a\)|hyperlipid|dyslipid|"
                                          r"hypertriglycerid|triglycerid"),
    ("established CVD risk reduction (MACE)", r"cardiovascular (outcome|event|risk)|\bmace\b|atherosclero|"
                                              r"coronary|myocardial infarction|\bascvd\b"),
    ("heart failure", r"heart failure|\bhfpef\b|\bhfref\b"),
    ("chronic kidney disease", r"chronic kidney|diabetic kidney|\bckd\b|nephropathy|renal function"),
    ("type 2 diabetes", r"type 2 diab|\bt2d|diabetes mellitus,? type 2|\bt2dm\b"),
    ("obesity", r"obes|overweight|weight (management|loss|reduction)"),
]
# landscape-only labels with no epi indication (kept so nothing silently becomes blank)
PRE = {"chronic hand eczema (no epi row)": r"hand (eczema|dermatitis)",
       "diabetic macular edema (no epi row)": r"macular edema|diabetic (eye|retinopathy)",
       "pulmonary fibrosis / ILD (no epi row)": r"pulmonary fibrosis|interstitial lung",
       "peripheral artery disease (no epi row)": r"peripheral arter|limb ischemi|ischaemic ulcer|ischemic ulcer"}
NO_EPI = {"type 1 diabetes (no epi row)": r"type 1 diab|\bt1d"}
RX = ([(lab, re.compile(rx, re.I)) for lab, rx in PRE.items()] + [(lab, re.compile(rx, re.I)) for lab, rx in EPI]
      + [(lab, re.compile(rx, re.I)) for lab, rx in NO_EPI.items()])


def classify(conditions, title):
    """Conditions decide first (they are the registrant's own coding); the title only breaks a tie."""
    text = str(conditions) + " | " + str(title)
    for lab, rx in RX:
        if rx.search(text):
            return lab
    return None


d["primary_indication_epi"] = [classify(c, t) for c, t in zip(d.conditions, d.title)]
# collector label -> epi label mapping (majority on the whole table)
mp = (d.groupby(["primary_indication", "primary_indication_epi"]).size().rename("n").reset_index()
      .sort_values(["primary_indication", "n"], ascending=[True, False]))
tot = d.groupby("primary_indication").size()
mp["share_of_collector_label"] = [n / tot[p] for p, n in zip(mp.primary_indication, mp.n)]
epi_vocab = set(pd.read_csv("data/moat/verified/epi/indication_map.csv").indication)
mp["in_epi_vocab"] = mp.primary_indication_epi.isin(epi_vocab)

# ---- CT.gov field check on the sample
rows = []
for n in sample:
    f = C / "ct" / f"{n}.json"
    a = d[d.nct_id == n].iloc[0]
    if not f.exists():
        rows.append(dict(nct_id=n, fetched=False))
        continue
    p = json.loads(f.read_text())["protocolSection"]
    ph = p.get("designModule", {}).get("phases", [])
    phase = "Phase 2/3" if set(ph) >= {"PHASE2", "PHASE3"} else PH.get(ph[0] if ph else "", "/".join(ph))
    sponsor = p["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
    st = p["statusModule"]
    status = st.get("overallStatus")
    enr = p.get("designModule", {}).get("enrollmentInfo", {}).get("count")
    pc = st.get("primaryCompletionDateStruct", {}).get("date")
    conds = "; ".join(p.get("conditionsModule", {}).get("conditions", []))
    rows.append(dict(nct_id=n, fetched=True, sponsor_ok=sponsor == a.sponsor, phase_ok=phase == a.phase,
                     status_ok=status == a.status, enrollment_ok=(pd.isna(a.enrollment) and enr is None) or
                     (enr is not None and pd.notna(a.enrollment) and int(enr) == int(a.enrollment)),
                     primary_completion_ok=str(pc) == str(a.primary_completion),
                     conditions_ok=conds.replace("; ", "|") == str(a.conditions).replace(", ", "|").replace("; ", "|")
                     or set(x.strip().lower() for x in re.split(r";|\|", conds)) ==
                     set(x.strip().lower() for x in re.split(r";|\|", str(a.conditions))),
                     ct_sponsor=sponsor, ct_phase=phase, ct_status=status, ct_enrollment=enr, ct_pc=pc,
                     ct_conditions=conds, table_conditions=a.conditions, title=a.title,
                     collector_label=a.primary_indication, epi_label=a.primary_indication_epi if False else
                     d.loc[d.nct_id == n, "primary_indication_epi"].iloc[0]))
S = pd.DataFrame(rows)
S.to_csv(C / "land_sample_checks.csv", index=False)
print("sample", len(S), "fetched", S.fetched.sum())
for c in ["sponsor_ok", "phase_ok", "status_ok", "enrollment_ok", "primary_completion_ok", "conditions_ok"]:
    print(c, int(S[c].sum()), "/", int(S.fetched.sum()))
print(S[~S.conditions_ok][["nct_id", "ct_conditions", "table_conditions"]].head(5).to_string())
print(S[~S.status_ok | ~S.primary_completion_ok][["nct_id", "ct_status", "ct_pc"]].head(8).to_string())

# ---- stale registry dates
ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}


def pcdate(s):
    s = str(s)
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return pd.Timestamp(s) + pd.offsets.MonthEnd(0)
    return pd.to_datetime(s, errors="coerce")


d["stale_registry_date"] = [int(st in ACTIVE and pd.notna(pcdate(pc)) and pcdate(pc) < pd.Timestamp("2026-10-17"))
                            for st, pc in zip(d.status, d.primary_completion)]
print("stale", d.stale_registry_date.sum(), "of active", d.status.isin(ACTIVE).sum())

if "--write" in sys.argv:
    hand = pd.read_csv(C / "land_hand_labels.csv")  # from pp_hand
    S2 = S.drop(columns=["collector_label", "epi_label"]).merge(hand, on="nct_id", how="left")
    d["verify_status"] = "unsampled"
    d["hand_indication"] = None
    ok = S2.set_index("nct_id")
    for n in S2.nct_id:
        r = ok.loc[n]
        fields = all(r[c] for c in ["sponsor_ok", "phase_ok", "status_ok", "enrollment_ok", "primary_completion_ok"])
        d.loc[d.nct_id == n, "verify_status"] = "pass" if fields else "field_mismatch"
        d.loc[d.nct_id == n, "hand_indication"] = r.hand_label
    write("verify_pipeline", "verified/pipeline/pipeline_landscape.csv", d.to_csv(index=False), group="pipeline",
          doc_type="table", quality="verified", source_url="https://clinicaltrials.gov/api/v2/studies")
    write("verify_pipeline", "verified/pipeline/pipe_indication_to_epi.csv", mp.to_csv(index=False), group="pipeline",
          doc_type="table", quality="verified", source_url="data/moat/verified/epi/indication_map.csv")
