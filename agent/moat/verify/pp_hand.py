"""Pipeline verifier item 1: hand labels for the 150-trial sample (read by Opus from title + CT.gov conditions).

Default = the epi-vocabulary classifier label, which I read row by row and accepted; these are the overrides.
Also scores the collector's own label: CORRECT maps each collector label to the hand labels it legitimately covers.
"""
import pandas as pd

C = "data/moat/verify/pp_cache/"
S = pd.read_csv(C + "land_sample_checks.csv")
OVER = {
    78: ("gastric / GEJ cancer", "HER2-expressing GI basket led by gastroesophageal adenocarcinoma"),
    80: ("MASH", "esophageal varices in NASH cirrhosis, not esophageal cancer"),
    74: ("biliary tract cancer", "Gall Bladder Cancer matched the bladder regex"),
    111: ("hidradenitis suppurativa", "HS trial of an incretin; not obesity"),
    127: ("pulmonary fibrosis / ILD (no epi row)", "ILD incl. RA-associated ILD is not an RA trial"),
    134: ("diabetic macular edema (no epi row)", "aflibercept eye trial; diabetes is only the population"),
    137: ("chronic kidney disease", "renal function outcome trial of retatrutide"),
    66: ("chronic hand eczema (no epi row)", "chronic hand eczema is not atopic dermatitis"),
    63: ("peripheral artery disease (no epi row)", "factor XI inhibitor in PAD vascular outcomes, not AF"),
    91: ("peripheral artery disease (no epi row)", "ischemic ulcer healing in PAD, not lipids"),
    33: ("HER2+ breast cancer", "pertuzumab biosimilar: HER2+ by label"),
    34: ("HER2+ breast cancer", "HER2+/HR+ first line: HER2 drives the regimen"),
    18: ("HIV PrEP", "implant in participants at low risk: prevention study"),
}
CORRECT = {
    "NSCLC": {"NSCLC"}, "type 2 diabetes": {"type 2 diabetes"},
    "obesity": {"obesity", "established CVD risk reduction (MACE)", "obstructive sleep apnea (with obesity)"},
    "afib anticoagulation": {"atrial fibrillation (stroke prevention)", "venous thromboembolism (DVT/PE)"},
    "melanoma": {"melanoma"}, "RCC": {"renal cell carcinoma"}, "HCC": {"hepatocellular carcinoma"},
    "bladder/urothelial": {"urothelial / bladder cancer"}, "gastric": {"gastric / GEJ cancer"},
    "esophageal": {"esophageal cancer"}, "HNSCC": {"HNSCC"}, "TNBC": {"triple-negative breast cancer"},
    "HR+ breast": {"HR+/HER2- breast cancer"}, "plaque psoriasis": {"plaque psoriasis"},
    "psoriatic arthritis": {"psoriatic arthritis"}, "Crohn's": {"Crohn's disease"},
    "ulcerative colitis": {"ulcerative colitis"}, "rheumatoid arthritis": {"rheumatoid arthritis"},
    "atopic dermatitis": {"atopic dermatitis"}, "multiple myeloma": {"multiple myeloma"},
    "HIV": {"HIV-1 treatment", "HIV PrEP"}, "ATTR-CM": {"ATTR-CM"},
    "hypercholesterolemia/ASCVD": {"hypercholesterolemia (incl. HeFH)", "established CVD risk reduction (MACE)"},
    "MASH": {"MASH"},
}
S["hand_label"] = S.epi_label
S["hand_note"] = ""
for i, (lab, note) in OVER.items():
    S.loc[i, "hand_label"] = lab
    S.loc[i, "hand_note"] = note
S["collector_correct"] = [h in CORRECT.get(c, set()) for c, h in zip(S.collector_label, S.hand_label)]
S["epi_classifier_correct"] = S.epi_label == S.hand_label
S[["nct_id", "collector_label", "epi_label", "hand_label", "hand_note", "collector_correct",
   "epi_classifier_correct"]].to_csv(C + "land_hand_labels.csv", index=False)
mis = S.groupby("collector_label").agg(n=("nct_id", "size"), wrong=("collector_correct", lambda x: int((~x).sum())))
mis["misclassification_rate"] = mis.wrong / mis.n
mis.to_csv(C + "land_misclass.csv")
print(mis.to_string())
print("collector wrong", int((~S.collector_correct).sum()), "/", len(S), "; epi classifier wrong",
      int((~S.epi_classifier_correct).sum()))
print(S[~S.epi_classifier_correct][["nct_id", "epi_label", "hand_label"]].to_string())
