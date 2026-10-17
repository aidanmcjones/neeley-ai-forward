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
    ("Collect", "running", "Part 1 streams done. Wave 2 running: deal comps, cost benchmarks, epidemiology, prescribers and payments, pipeline and targets, rival-maker depth, onboarding commands"),
    ("Verify", "done", "Opus re-checked all 10 buckets against source pages; 61 AI error types logged for the report"),
    ("Citation index", "done", "citations.sqlite: 3,118 docs, 39,940 pages, 69,553 facts, cite() and verify_quote(); frozen through the Sun 10:30 am freeze"),
    ("Model", "blocked", "Model session is wiring NEEDLE to the index; the LLM steps still wait on the Anthropic API key"),
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
    ("Cost and return math", "Collecting: company cost structure, trial cost per phase (ASPE, JAMA), launch and DTC spend, Open Payments per drug", "collecting"),
    ("Deal comps (acquire or license)", "Collecting: 300+ biopharma deals since 2020 from 8-Ks and 10-K notes with upfront, milestones, royalty; benchmarks by stage and area", "collecting"),
    ("Market sizing", "Collected: 212 drug x indication label rows, 30 of 50 indications with US prevalence (CDC, SEER, NIDDK, PMC), Part D 2024 floor for 318 drug-periods, 124 funnels. Opus verifying; 20 indications still have no epidemiology", "verifying"),
    ("Peer comparison at rival-maker depth", "Collected: 3 annual reports, quarterlies and 6 calls each for NVS, GSK, SNY, TAK, REGN, ALNY, BBIO, Roche; 852 quoted statements about the 17 rival products. Opus verifying quotes page by page. Boehringer blocked by bot protection", "verifying"),
    ("Prescriber and payer uptake", "Collecting: Part D prescribers by specialty and state 2019 to 2023, concentration, Open Payments, formulary history, Part B providers", "collecting"),
    ("Pipeline and targets", "Collecting: Phase 2/3 landscape in the case indications, non-owned assets, target profiles with cash and EV, FDA and LOE calendars", "collecting"),
    ("Two rejected alternatives", "Argument, built from Part 1 and the tables above", "waiting"),
    ("What would prove us wrong (6 to 12 months)", "Argument; leading indicators come from prescriber, formulary and price series", "waiting"),
    ("Why it will work: doctors, payers, investors", "Mentor and industry interviews today in room 2303 plus prescriber, formulary and consensus data", "human"),
    ("Promo rules and claims map (campaign only)", "Verified head-to-head table (37 pairs) says which rival claims have evidence", "ready"),
    ("Any company, any drug", "Opus worker building onboard_company and onboard_drug commands with incremental index --add; proving on REGN, NVS, VRTX, Dupixent, Xtandi", "collecting"),
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
