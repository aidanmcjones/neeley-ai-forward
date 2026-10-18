import glob
import re
PAGE = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")
files = ["BMY/policy/press_2025-07-17_eliquis-direct-to-patient", "AMGN/policy/press_2025-10-06_amgennow_repatha", "AMGN/policy/press_2025-12-19_mfn_agreement",
         "LLY/policy/press_2025-11-06_wh_mfn_factsheet", "LLY/policy/press_2026-04-09_foundayo_launch_pricing", "LLY/policy/press_2026-02-05_wh_trumprx_factsheet",
         "NVO/policy/press_2026-02-24_us_list_price_reduction", "NVO/policy/press_2026-07-01_medicare_glp1_bridge", "PFE/policy/press_2025-09-30_mfn_landmark_agreement",
         "MRK/policy/press_2025-12-19_mfn_agreement", "GILD/policy/press_2025-12-19_mfn_agreement", "JNJ/policy/press_2026-01-08_us_government_agreement_mfn",
         "ABBV/policy/press_2026-01-12_mfn_trump_agreement", "AZN/policy/press_2025-10-10_us_government_agreement", "BMY/policy/press_2025-12-19_us-government-agreement"]
for f in files:
    p = f"data/corpus/companies/{f}.md"
    t = open(p, errors="ignore").read()
    print("#####", f)
    n = 0
    for s in re.split(r"(?<=[.!?])\s+", " ".join(t.split())):
        if re.search(r"\$\s?\d|\d+%", s) and re.search(r"price|Medicaid|MFN|direct|cash|cost|discount|launch|out-of-pocket|per month", s, re.I) and len(s) < 500:
            print("-", s)
            n += 1
            if n >= 7:
                break
