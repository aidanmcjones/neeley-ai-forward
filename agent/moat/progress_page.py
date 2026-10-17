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
    ("Collect", "running", "Part 1 streams done. Wave 2: epidemiology, rival-maker depth, deal comps, pipeline and onboarding landed; cost benchmarks and prescribers still collecting"),
    ("Verify", "running", "Opus re-checked all 10 Part 1 buckets plus epi and peers; 83 AI error types logged for the report. Deals and pipeline verifying now"),
    ("Citation index", "done", "citations.sqlite: 6,607 docs, 71,682 pages, 79,954 facts, cite() and verify_quote(); contract frozen, new material added with index.py --add"),
    ("Model", "running", "Model session is wiring NEEDLE to the index and the Part 2 tables. API key is staged in .env, pending Aidan's arm once model, data and UI are complete (no spend before then)"),
    ("UI", "running", "UI session has 7 cockpit screens in build on top of the index"),
    ("Demo video", "waiting", "Sunday 10:30 to 12:30, after the code freeze; needs the company pick first"),
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
    ("Cost and return math", "Collected: cost structure FY2021 to FY2025 for the 10 plus USD peers (SG&A 13.5 to 26.3% of revenue, advertising 2.5 to 6%), trial cost per phase (ASPE 2014, Sertkaya 2024), 102 Open Payments drug-years, 27 precedent pricing moves with disclosed effects, 520 new-indication timing rows. Opus verifying against companyfacts and the pages", "verifying"),
    ("Deal comps (acquire or license)", "Verified and indexed: 554 of 1,611 deals hand-checked against the page (133 verified, 235 corrected, 400 dropped; 843 unchecked are leads, not comps). Benchmarks rebuilt from verified rows only: 74 cells, every acquisition row checked (median $1,675M vs the collector's $956M). Quotes were 97% verbatim; numbers passed 58 to 71% by field", "ready"),
    ("Market sizing", "Verified and indexed: 212 drug x indication label rows, US prevalence for 30 of 50 indications (all 30 rechecked on the primary page; ATTR-CM, RA and PrEP marked low confidence), Part D 2024 floors recomputed 15 of 15, 95 funnels with Medicare floor %. 20 indications still have no epidemiology", "ready"),
    ("Peer comparison at rival-maker depth", "Verified and indexed: 833 of 852 rival product statements verbatim on the cited page (19 publisher-text rows dropped, 224 junk speakers fixed), NVS top-20 revenue rebuilt from the 20-F, 72 of 72 XBRL rows match. 8 rival makers covered; Boehringer blocked by bot protection", "ready"),
    ("Pipeline and targets", "Verified and indexed: 3,383 Phase 2/3 trials reclassified to the epi vocabulary (collector regex was wrong 8%, new classifier 1 of 150), 2,222 assets after 177 trial-arm rows dropped, 199 target profiles with cash, debt and EV re-pulled from one balance-sheet date (collector used facts up to 10 years stale; 78 priced, Tiingo-limited), 452 LOE rows with stated date, page and a corrected rule date (5 wrong-strength generics flagged, biologics on BLA + 12 years), 921 FDA calendar rows", "ready"),
    ("Prescriber and payer uptake", "Collecting: Part D prescribers by specialty and state 2019 to 2023, concentration, Open Payments, formulary history, Part B providers", "collecting"),
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
