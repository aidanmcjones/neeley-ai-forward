"""consensus_vs_guidance.csv: latest IBES FY2026 revenue consensus (SAL, fpi=1) vs company guidance (quoted, cited)."""
import csv
import io
from agent.moat.common import write
from agent.moat.verify.m_qa import ROOT

C = "data/corpus/companies"
# ticker: (ibes ticker, guidance low, high, unit, quote, file, page/line, basis note)
G = {
    "ABBV": ("ABBV", 67600, 67600, "USD m", "We now expect total net revenues of approximately $67.6 billion, an increase of $300 million",
             f"{C}/ABBV/transcripts/2026Q2_transcript.md", "L444 (CFO prepared remarks; the 8-K exhibit gives EPS guidance only)", "point estimate"),
    "AMGN": ("AMGN", 38200, 39400, "USD m", "We now expect 2026 total revenues in the range of $38.2 billion to $39.4 billion",
             f"{C}/AMGN/transcripts/2026Q2_transcript.md", "L458 (CFO prepared remarks; corpus 8-K is cover page only)", ""),
    "AZN": ("AZN", 58739 * 1.05, 58739 * 1.09, "USD m (implied)", "Total Revenue is expected to increase by a mid-to-high single-digit percentage [at CER]",
            f"{C}/AZN/6k/2026-07-27_azn-20260630x6k.md", "page 2 (printed 1) L376; FY2025 Total Revenue $58,739m from 20f_FY2025.md page 61 (printed F-2) L18463",
            "range implied as +5% to +9% at CER on FY2025; IBES is reported-currency; only 4 estimates"),
    "BMY": ("BMY", 49000, 50000, "USD m", "Raising 2026 revenue guidance to a range of ~$49.0 billion to $50.0 billion",
            f"{C}/BMY/earnings/2026-07-30_a2026q2ex991-filing.md", "page 1 (printed 1) L27", ""),
    "GILD": ("GIL1", 30100, 30400, "USD m", "Product sales $ 30,100 $ 30,400 (Previously $30,000 to $30,400)",
             f"{C}/GILD/earnings/2026-08-04_exhibit991earningspressrel.md", "page 3 L99",
             "guidance is product sales only; IBES SAL is total revenue incl. royalty/contract revenue, so part of the gap is definitional"),
    "JNJ": ("JNJ", 101200, 101200, "USD m", "increasing 2026 guidance with estimated reported sales of $101.2 Billion or 7.4% at the midpoint",
            f"{C}/JNJ/earnings/2026-10-13_a2026q3exhibit991.md", "page 1 L33 (Q3 release, 2026-10-13; IBES snapshot predates it, July guide was $101.1B)", "midpoint"),
    "LLY": ("LLY", 85000, 87000, "USD m", "We now expect full-year revenue to be between $85 and $87 billion",
            f"{C}/LLY/transcripts/2026Q2_transcript.md", "L114 (CFO prepared remarks; corpus 8-K is cover page only)", ""),
    "MRK": ("MRK", 66300, 67300, "USD m", "now anticipates full-year 2026 sales to be between $66.3 billion and $67.3 billion",
            f"{C}/MRK/earnings/2026-08-04_tm2621496d1_ex99-1.md", "page 1 L770", ""),
    "NVO": ("NVO", 309100 * 0.94, 309100 * 1.00, "DKK m (implied)", "Adjusted sales growth for 2026 is now expected to be 0% to -6% at CER",
            f"{C}/NVO/6k/2026-08-04_caq22026.md", "page 2 (printed 90) L97; FY2025 sales DKK 309.1bn from 6k/2026-02-03_caq42025.md page 2 L67",
            "implied on reported FY2025 sales; guidance base is adjusted sales (excl. 340B provision reversal) at CER, so treat as approximate"),
    "PFE": ("PFE", 60500, 62500, "USD m", "Raises Full-Year 2026 Revenue Guidance by $500 Million at the Midpoint to a Range of $60.5 to $62.5 Billion",
            f"{C}/PFE/earnings/2026-08-04_pfe-6282026xex99.md", "page 1 L51", ""),
}


def main():
    rev = list(csv.DictReader(open(ROOT / "data/moat/tables/ibes_revenue_consensus.csv")))
    rows = []
    for tk, (it, lo, hi, unit, q, f, pg, note) in G.items():
        cand = [r for r in rev if r["ticker"] == it and r["measure"] == "SAL" and r["fpi"] == "1" and r["fpedats"] == "2026-12-31"]
        r = max(cand, key=lambda r: r["statpers"])
        mean = float(r["meanest"])
        mid = (lo + hi) / 2
        pos = ("at point guidance" if abs(mean - mid) / mid < 0.0025 else ("above" if mean > hi else "below")) if lo == hi else ("within" if lo <= mean <= hi else ("above" if mean > hi else "below"))
        rows.append([tk, it, r["fpedats"], r["statpers"], int(float(r["numest"])), round(mean, 1), round(float(r["medest"]), 1),
                     round(float(r["lowest"]), 1), round(float(r["highest"]), 1), r["curcode"], round(lo, 1), round(hi, 1), unit, q, f, pg,
                     round(mean - mid, 1), round((mean - mid) / mid * 100, 2), pos, note, "WRDS ibes.statsum_xepsus", r["source_row"]])
    cols = ["ticker", "ibes_ticker", "fiscal_period_end", "consensus_date", "n_estimates", "consensus_mean_m", "consensus_median_m",
            "consensus_low_m", "consensus_high_m", "currency", "guidance_low_m", "guidance_high_m", "guidance_unit", "guidance_quote",
            "guidance_file", "guidance_page", "gap_mean_minus_guidance_mid_m", "gap_pct", "consensus_vs_range", "note", "source", "source_row"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    write("verify_market", "verified/market/consensus_vs_guidance.csv", buf.getvalue(), group="market", doc_type="table",
          source_url="WRDS IBES + company releases", upload=False)
    for r in rows:
        print(r[0], r[3], r[4], r[5], r[9], "guide", r[10], r[11], "gap", r[16], f"{r[17]}%", r[18])


main()
