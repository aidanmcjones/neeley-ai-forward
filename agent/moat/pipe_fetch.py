"""Harvest CT.gov v2 industry Phase 2/3 interventional trials started 2019+ in case indications."""
import json
import time
from pathlib import Path

import requests

OUT = Path("data/moat/scratch/pipeline")
OUT.mkdir(parents=True, exist_ok=True)
API = "https://clinicaltrials.gov/api/v2/studies"
H = {"User-Agent": "Neeley AI Forward hackathon"}
INDS = {
    "t2d": "type 2 diabetes", "obesity": "obesity OR overweight OR weight management",
    "afib": "atrial fibrillation OR stroke prevention OR venous thromboembolism",
    "nsclc": "non-small cell lung cancer", "melanoma": "melanoma", "rcc": "renal cell carcinoma",
    "hcc": "hepatocellular carcinoma", "bladder": "urothelial carcinoma OR bladder cancer",
    "gastric": "gastric cancer OR gastroesophageal junction", "esoph": "esophageal cancer OR esophageal squamous",
    "hnscc": "head and neck squamous cell carcinoma", "tnbc": "triple negative breast cancer",
    "hrbc": "HR-positive breast cancer OR hormone receptor positive breast cancer",
    "pso": "plaque psoriasis", "psa": "psoriatic arthritis", "cd": "Crohn's disease", "uc": "ulcerative colitis",
    "ra": "rheumatoid arthritis", "ad": "atopic dermatitis", "mm": "multiple myeloma",
    "hiv": "HIV infection OR HIV-1 OR HIV pre-exposure prophylaxis", "attr": "transthyretin amyloid cardiomyopathy",
    "lipid": "hypercholesterolemia OR atherosclerotic cardiovascular disease OR lipoprotein(a)",
    "mash": "NASH OR MASH OR nonalcoholic steatohepatitis OR metabolic dysfunction-associated steatohepatitis",
}
FIELDS = ("NCTId|BriefTitle|LeadSponsorName|LeadSponsorClass|CollaboratorName|InterventionName|InterventionType|"
          "Phase|OverallStatus|EnrollmentCount|StartDate|PrimaryCompletionDate|HasResults|Condition|"
          "InterventionOtherName|StudyType")
ADV = ("AREA[StudyType]INTERVENTIONAL AND AREA[Phase](PHASE2 OR PHASE3) AND "
       "AREA[StartDate]RANGE[2019-01-01,MAX] AND AREA[LeadSponsorClass]INDUSTRY")


def get(p):
    for i in range(5):
        r = requests.get(API, params=p, headers=H, timeout=120)
        if r.status_code == 200:
            return r.json()
        time.sleep(5 * (i + 1))
    raise RuntimeError(p)


for k, q in INDS.items():
    f = OUT / f"{k}.json"
    if f.exists():
        continue
    studies, tok = [], None
    while True:
        p = {"query.cond": q, "filter.advanced": ADV, "fields": FIELDS, "pageSize": 1000, "format": "json"}
        if tok:
            p["pageToken"] = tok
        d = get(p)
        studies += d["studies"]
        tok = d.get("nextPageToken")
        time.sleep(1.5)
        if not tok:
            break
    f.write_text(json.dumps(studies))
    print(k, len(studies), flush=True)
