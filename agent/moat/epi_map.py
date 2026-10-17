"""epi stream step 1: tables/indication_map.csv (drug -> controlled-vocabulary indications, label section cited)."""
import csv
import io
import re
from pathlib import Path

from agent.moat.common import ROOT, note_gap, write

LABELS = ROOT / "data" / "corpus" / "drugs"

# heading regex -> vocab (checked in order) for labels with numbered 1.x subsections
HEAD_RULES = [
    (r"polyneuropathy", "hATTR polyneuropathy"),
    (r"cardiomyopathy", "ATTR-CM"),
    (r"rheumatoid", "rheumatoid arthritis"),
    (r"juvenile psoriatic|juvenile idiopathic|polyarticular|enthesitis", "juvenile arthritis (JIA / JPsA / ERA)"),
    (r"psoriatic arthritis", "psoriatic arthritis"),
    (r"ankylosing|axial spondylo", "ankylosing spondylitis / axSpA"),
    (r"plaque psoriasis", "plaque psoriasis"),
    (r"atopic", "atopic dermatitis"),
    (r"hidradenitis", "hidradenitis suppurativa"),
    (r"uveitis", "uveitis"),
    (r"crohn", "Crohn's disease"),
    (r"ulcerative colitis", "ulcerative colitis"),
    (r"giant cell", "giant cell arteritis"),
    (r"vitiligo|alopecia", "other immune-mediated skin disease"),
    (r"nonvalvular atrial fibrillation|atrial fibrillation", "atrial fibrillation (stroke prevention)"),
    (r"deep vein|pulmonary embolism|venous thromboembolism|dvt|vte", "venous thromboembolism (DVT/PE)"),
    (r"coronary|peripheral artery|major cardiovascular events", "established CVD risk reduction (MACE)"),
    (r"melanoma", "melanoma"),
    (r"(?<!non-)small cell lung", "SCLC"),
    (r"light chain", "AL amyloidosis"),
    (r"fontan", "pediatric thromboprophylaxis (Fontan)"),
    (r"non-small cell|nsclc", "NSCLC"),
    (r"mesothelioma", "malignant pleural mesothelioma"),
    (r"head and neck", "HNSCC"),
    (r"hodgkin|mediastinal", "lymphoma (cHL / PMBCL)"),
    (r"urothelial|bladder", "urothelial / bladder cancer"),
    (r"microsatellite|mismatch|tumor mutational|colorectal|colon", "colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H"),
    (r"gastric|gastroesophageal", "gastric / GEJ cancer"),
    (r"esophageal", "esophageal cancer"),
    (r"cervical", "cervical cancer"),
    (r"hepatocellular", "hepatocellular carcinoma"),
    (r"biliary", "biliary tract cancer"),
    (r"merkel", "Merkel cell carcinoma"),
    (r"renal cell", "renal cell carcinoma"),
    (r"endometrial", "endometrial cancer"),
    (r"cutaneous squamous", "cutaneous squamous cell carcinoma"),
    (r"triple-negative", "triple-negative breast cancer"),
    (r"ovarian", "ovarian cancer"),
    (r"alveolar soft", "alveolar soft part sarcoma"),
    (r"her2-positive", "HER2+ breast cancer"),
    (r"breast", "HR+/HER2- breast cancer"),
    (r"multiple myeloma", "multiple myeloma"),
]

# labels without usable 1.x subsections (or multi-bullet): explicit (vocab, sub_indication, section)
MANUAL = {
    "januvia": [("type 2 diabetes", "glycemic control", "1")],
    "janumet": [("type 2 diabetes", "glycemic control", "1")],
    "mounjaro": [("type 2 diabetes", "glycemic control", "1"), ("type 2 diabetes", "MACE risk reduction in T2D", "1")],
    "ozempic": [("type 2 diabetes", "glycemic control", "1"), ("type 2 diabetes", "MACE risk reduction in T2D with CVD", "1"),
                ("chronic kidney disease", "CKD in T2D (eGFR decline, ESKD, CV death)", "1")],
    "rybelsus": [("type 2 diabetes", "glycemic control", "1"), ("type 2 diabetes", "MACE risk reduction in T2D", "1")],
    "trulicity": [("type 2 diabetes", "glycemic control", "1"), ("type 2 diabetes", "MACE risk reduction in T2D", "1")],
    "farxiga": [("chronic kidney disease", "CKD at risk of progression", "1"), ("heart failure", "HF (all EF)", "1"),
                ("type 2 diabetes", "HHF risk reduction in T2D", "1"), ("type 2 diabetes", "glycemic control", "1")],
    "jardiance": [("heart failure", "HF", "1"), ("chronic kidney disease", "CKD at risk of progression", "1"),
                  ("type 2 diabetes", "CV death reduction in T2D with CVD", "1"), ("type 2 diabetes", "glycemic control", "1")],
    "wegovy": [("obesity", "chronic weight management (obesity/overweight with comorbidity)", "1"),
               ("established CVD risk reduction (MACE)", "MACE risk reduction in established CVD with obesity/overweight", "1"),
               ("MASH", "noncirrhotic MASH F2-F3", "1")],
    "zepbound": [("obesity", "chronic weight management", "1"), ("obstructive sleep apnea (with obesity)", "moderate to severe OSA", "1")],
    "foundayo": [("obesity", "chronic weight management", "1")],
    "lipfendra": [("hypercholesterolemia (incl. HeFH)", "LDL-C lowering", "1")],
    "leqvio": [("hypercholesterolemia (incl. HeFH)", "adults with hypercholesterolemia, HeFH; pediatric HoFH", "1")],
    "praluent": [("established CVD risk reduction (MACE)", "MACE risk reduction in adults at increased risk", "1"),
                 ("hypercholesterolemia (incl. HeFH)", "primary hyperlipidemia, HeFH, HoFH", "1")],
    "repatha": [("established CVD risk reduction (MACE)", "MACE risk reduction in adults at increased risk", "1"),
                ("hypercholesterolemia (incl. HeFH)", "primary hyperlipidemia, HeFH, HoFH", "1")],
    "attruby": [("ATTR-CM", "CV death and CV hospitalization", "1")],
    "vyndaqel": [("ATTR-CM", "CV mortality and CV hospitalization", "1")],
    "vyndamax": [("ATTR-CM", "CV mortality and CV hospitalization", "1")],
    "biktarvy": [("HIV-1 treatment", "complete regimen, treatment-naive or switch", "1")],
    "dovato": [("HIV-1 treatment", "complete regimen, naive or switch", "1")],
    "cabenuva": [("HIV-1 treatment", "virologically suppressed switch regimen", "1")],
    "apretude": [("HIV PrEP", "sexually acquired HIV-1 PrEP", "1")],
    "yeztugo": [("HIV PrEP", "sexually acquired HIV-1 PrEP", "1")],
    "entyvio": [("ulcerative colitis", "moderately to severely active UC", "1"), ("Crohn's disease", "moderately to severely active CD", "1")],
    "darzalex": [("multiple myeloma", "newly diagnosed and relapsed/refractory regimens", "1")],
    "sarclisa": [("multiple myeloma", "relapsed/refractory and newly diagnosed (non-ASCT)", "1")],
    "lazcluze": [("NSCLC", "first-line EGFR exon 19 del / L858R with amivantamab", "1")],
}


def sections(slug):
    f = LABELS / slug / "label_sections.md"
    t = f.read_text()
    m = re.search(r"\n## 1[.\s]+INDICATIONS.*?\n(.*?)\n## 2", t, re.S | re.I)
    sec = m.group(1) if m else ""
    return re.findall(r"###\s+(1\.\d+)\s+([^\n]+)", sec)


def src_for(slug):
    first = (LABELS / slug / "label_sections.md").read_text().split("\n", 1)[0]
    m = re.search(r"source: (\S+)", first)
    return m.group(1) if m else f"data/corpus/drugs/{slug}/label_sections.md"


def main():
    from agent.drug_pack import DRUGS
    rows, unmapped = [], []
    for slug in DRUGS:
        if not (LABELS / slug / "label_sections.md").exists():
            note_gap("epi", slug, "indication_map", "no label_sections.md in corpus")
            continue
        url = src_for(slug)
        if slug in MANUAL:
            for vocab, sub, sec in MANUAL[slug]:
                rows.append([slug, vocab, sub, sec, "INDICATIONS AND USAGE", url,
                             f"data/corpus/drugs/{slug}/label_sections.md#1 INDICATIONS AND USAGE|{vocab}|{sub}"])
            continue
        heads = sections(slug)
        if not heads:
            unmapped.append((slug, "no 1.x headings"))
            continue
        for num, head in heads:
            h = head.lower()
            vocab = next((v for pat, v in HEAD_RULES if re.search(pat, h)), None)
            if not vocab:
                unmapped.append((slug, head))
                continue
            # NSCLC with EGFR mutation -> flag as sub_indication only
            sub = head.strip()
            rows.append([slug, vocab, sub, num, head.strip(), url,
                         f"data/corpus/drugs/{slug}/label_sections.md#{num} {head.strip()}"])
    cols = ["drug", "indication", "sub_indication", "label_section", "label_section_heading", "source", "source_row"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    write("epi", "tables/indication_map.csv", buf.getvalue(), group="epi", doc_type="epi_table", source_url="DailyMed labels via data/corpus/drugs")
    print(len(rows), "rows;", len({r[0] for r in rows}), "drugs;", len({r[1] for r in rows}), "indications")
    print("unmapped", unmapped)
    for slug, h in unmapped:
        note_gap("epi", slug, "indication_map heading", f"unmapped heading: {h}")


if __name__ == "__main__":
    main()
