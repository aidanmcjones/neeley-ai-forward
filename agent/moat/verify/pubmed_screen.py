"""Screen head_to_head_pubmed.csv titles + publication types: real head-to-head RCT vs indirect comparison."""
import csv
import re
from pathlib import Path

from agent.moat.verify.h2h import APPENDIX, has

ROOT = Path(__file__).resolve().parents[3]
OUTD = ROOT / "data/moat/verified/product"
AP = {frozenset(p) for p in APPENDIX}
OVERRIDE = {  # human read of titles flagged by the rule
    "41544603": ("rct_not_h2h_in_title", "MARIPOSA-2 is amivantamab+chemo vs chemo; osimertinib only as prior therapy"),
    "42669070": ("rct_not_h2h_in_title", "HELIOS-B subgroup by baseline tafamidis use; vutrisiran vs placebo, not vs tafamidis"),
    "39159638": ("h2h_rct_regimen", "JCOG2007: randomised phase 3, pembrolizumab+chemo vs nivolumab+ipilimumab+chemo; "
                 "registered in jRCT, not ClinicalTrials.gov, so the CT.gov screen cannot see it"),
}


def classify(r, a, b):
    t, pt = r["title"].lower(), r["pubtypes"].lower()
    both = has(t, a) and has(t, b)
    if re.search(r"network meta|indirect|matching-adjusted|maic|bucher|mixed treatment", t):
        return "indirect_comparison"
    if "meta-analysis" in pt or "systematic review" in pt or re.search(r"meta-analys|systematic review", t):
        return "meta_analysis_pooled"
    if re.search(r"real-world|real world|retrospective|cohort|propensity|claims|registry|observational|nationwide", t):
        return "observational"
    if "randomized controlled trial" in pt and both:
        return "h2h_rct_candidate"
    if "randomized controlled trial" in pt:
        return "rct_not_h2h_in_title"
    if re.search(r"post hoc|post-hoc|secondary analysis|subgroup", t) and both:
        return "h2h_rct_secondary_analysis"
    return "other"


def main():
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/head_to_head_pubmed.csv")))
    out = []
    for r in rows:
        a, b = r["drugs"].split(" vs ")
        r["appendix_pair"] = "y" if frozenset((a, b)) in AP else "n"
        r["evidence_type"] = classify(r, a, b)
        r["verify_status"] = "verified"
        if r["pmid"] in OVERRIDE:
            r["evidence_type"], why = OVERRIDE[r["pmid"]]
            r["verify_status"] = "fixed"
            r["verify_note"] = f"human read of title overrode rule: {why}"
        r["verify_note"] = ("rule screen of title + PubMed publication types; h2h_rct_candidate means pubtype RCT and "
                            "both drugs named in the title, still read the abstract before citing")
        out.append(r)
    with open(OUTD / "head_to_head_pubmed.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(Counter((r["appendix_pair"], r["evidence_type"]) for r in out))
    for r in out:
        if r["appendix_pair"] == "y" and r["evidence_type"] in ("h2h_rct_candidate", "h2h_rct_secondary_analysis"):
            print(r["drugs"], r["pmid"], r["year"], r["title"][:150])


main()
