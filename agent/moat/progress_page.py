"""Render the data tracker page from data/moat/progress.json.

Run:  python -m agent.moat.progress && python -m agent.moat.progress_page
Writes data/moat/tracker.html (publish it as the artifact). Stream and stage states are kept in STATUS below and
edited by hand as the pipeline moves; the per-company numbers come from progress.py.
"""

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE = Path(__file__).with_name("progress_template.html")

STATUS = {
    # bucket key -> collect / verify state shown in the column header
    "annual": ("collected", "verified"), "quarterly": ("collected", "verified"),
    "calls": ("collected", "verified"), "product_revenue": ("collected", "verified"),
    "policy": ("collected", "verified"), "pricing": ("collected", "verified"),
    "consensus": ("collected", "verified"), "attention": ("collected", "verified"),
    "fine_print": ("collected", "verified"), "product_evidence": ("collected", "verified"),
}
STAGES = [
    ("Collect", "done", "Part 1 streams and all seven wave 2 streams landed: epidemiology, rival-maker depth, deal comps, pipeline and targets, cost benchmarks, prescribers and payers, onboarding commands. GDELT news still trickling in under its rate limit"),
    ("Verify", "done", "Opus re-checked every stream against the source page or the raw CMS and SEC files; 486 AI errors logged for the report. Only verified rows are citable; dropped rows are kept for the write-up"),
    ("Citation index", "done", "citations.sqlite with cite(), verify_quote() and a locator on every fact row; contract stable until the Devpost submission, new material added with index.py --add. PR #16 ready for review"),
    ("Model", "running", "Model session is wiring NEEDLE to the index and the Part 2 tables. API key is staged in .env, pending Aidan's arm once model, data and UI are complete (no spend before then)"),
    ("UI", "running", "UI session has 7 cockpit screens in build on top of the index"),
    ("Demo video", "waiting", "Recorded once model and UI are stable; the only deadline is the Devpost submission, Sunday 2:00 pm CT"),
]
PART1 = [
    ("Why this company beat the other nine", ["policy", "consensus", "attention"], "ready"),
    ("5+ findings with filing and page", ["annual", "quarterly", "calls", "fine_print"], "ready"),
    ("Impact math per finding", ["product_revenue", "consensus"], "ready"),
    ("Peer comparison per finding", ["annual", "quarterly", "product_revenue"], "ready"),
    ("Confidence and 'priced in' call", ["consensus", "attention"], "ready"),
    ("Sharpest Needle (least discussed)", ["attention", "fine_print"], "ready"),
    ("Product vs rivals: uses, boxed warnings, dosing", ["product_evidence"], "ready"),
    ("Product: patent and exclusivity timeline", ["product_evidence"], "ready"),
    ("Product: pricing and gross-to-net exposure", ["pricing"], "ready"),
    ("Exact call quotes with speaker", ["calls"], "ready"),
]
PART2 = [
    ("The move, with budget or people", "Engine must propose and price a move for any company; inputs below are being collected for all 10 and all 52 drugs", "collecting"),
    ("Cost and return math", "Verified and indexed: cost structure FY2021 to FY2025 checked row by row against SEC companyfacts (293 of 300 match, 7 R&D rows put on one IPR&D basis), cost_ratios per company-year with scope notes (AZN, NVO in DKK, MRK IPR&D), all 27 pricing moves verbatim with effect type, ASPE and Sertkaya trial costs 539 of 539 on the page, Open Payments split by nature (Tecentriq, Entyvio, Imfinzi are mostly royalties). New-indication timing table is unusable: 49 of 60 checked rows matched the wrong trial", "ready"),
    ("Deal comps (acquire or license)", "Verified and indexed: 554 of 1,611 deals hand-checked against the page (133 verified, 235 corrected, 400 dropped; 843 unchecked are leads, not comps). Benchmarks rebuilt from verified rows only: 74 cells, every acquisition row checked (median $1,675M vs the collector's $956M). Quotes were 97% verbatim; numbers passed 58 to 71% by field", "ready"),
    ("Market sizing", "Verified and indexed: 212 drug x indication label rows, US prevalence for all 50 indications (56 rows, every one read on the primary page; ATTR-CM, RA, PrEP, hATTR-PN and cSCC marked low confidence), 22 subset shares (NSCLC, HR+/HER2-, EGFR, dMMR, 65+ diabetes), Part D 2024 floors, sizing funnel for 173 of 173 drug x indication pairs (139 with Medicare floor %)", "ready"),
    ("Peer comparison at rival-maker depth", "Verified and indexed: 833 of 852 rival product statements verbatim on the cited page (19 publisher-text rows dropped, 224 junk speakers fixed), NVS top-20 revenue rebuilt from the 20-F, 72 of 72 XBRL rows match. 8 rival makers covered; Boehringer blocked by bot protection", "ready"),
    ("Pipeline and targets", "Verified and indexed: 3,383 Phase 2/3 trials reclassified to the epi vocabulary (collector regex was wrong 8%, new classifier 1 of 150), 2,222 assets after 177 trial-arm rows dropped, 199 target profiles with cash, debt and EV re-pulled from one balance-sheet date (collector used facts up to 10 years stale; 78 priced, Tiingo-limited), 452 LOE rows with stated date, page and a corrected rule date (5 wrong-strength generics flagged, biologics on BLA + 12 years), 921 FDA calendar rows", "ready"),
    ("Prescriber and payer uptake", "Verified and indexed: Part D prescribers by drug, specialty and state 2019 to 2024 with CMS all-prescriber counts and true beneficiaries added (the 11-claim floor hid 90% of Skyrizi prescribers; Biktarvy was missing; Humira undercounted 3 to 7x), concentration and growth on both bases, Open Payments 2021 to 2024 with royalties split from promotion, Part B providers for 16 HCPCS codes (Darzalex Faspro unmixed from IV), formulary history 1,780 of 1,780 recompute with contract_year and part_b flags", "ready"),
    ("Two rejected alternatives", "Argument, built from Part 1 and the tables above", "waiting"),
    ("What would prove us wrong (6 to 12 months)", "Argument; leading indicators come from prescriber, formulary and price series", "waiting"),
    ("Why it will work: doctors, payers, investors", "Mentor and industry interviews today in room 2303 plus prescriber, formulary and consensus data", "human"),
    ("Promo rules and claims map (campaign only)", "Verified head-to-head table (37 pairs) says which rival claims have evidence", "ready"),
    ("Any company, any drug", "Ready: `onboard_company <TICKER>` and `onboard_drug \"<BRAND>\"` build the same cited data for anything new and `index.py --add` registers it with stable ids. Proven on REGN (147 s, 77 docs), NVS (93 s), VRTX from zero (190 s, 85 docs), Dupixent and Xtandi. Onboarded facts are flagged unverified_onboard until a verifier runs", "ready"),
]
NO_SOURCE = [
    ("Commercial list and true net prices", "Medi-Span, First Databank, IQVIA", "Part B ASP, Medicaid, NADAC, Part D, company list-vs-net reports"),
    ("Ex-US prescription volume and pricing", "IQVIA", "Company product tables by geography"),
    ("Commercial insurer formularies", "Not public", "Medicare Part D formulary files"),
    ("Settlement terms behind generic entry dates", "Confidential; PACER is pay per page", "What each 10-K states, SEC 8-Ks"),
    ("Q3 2026 results", "Not reported until Oct 29 to Nov 5", "Sealed forecasts in NEEDLE"),
]


def main():
    prog = json.loads((ROOT / "data/moat/progress.json").read_text())
    data = {"as_of": prog["as_of"], "companies": prog["companies"], "buckets": prog["buckets"], "status": STATUS,
            "stages": STAGES, "part1": PART1, "part2": PART2, "no_source": NO_SOURCE,
            "built": datetime.now().strftime("%a %b %d, %I:%M %p")}
    html = TEMPLATE.read_text().replace("/*DATA*/null", json.dumps(data))
    (ROOT / "data/moat/tracker.html").write_text(html)
    print("wrote data/moat/tracker.html", len(html))


if __name__ == "__main__":
    main()
