"""Append distinct secx collector error types to data/moat/verify/ai_wrong.jsonl (run once)."""
from agent.moat.verify.s_write import ai_wrong

E = [
    dict(table="sec_comment_letters.csv", what_the_ai_said="BMY 2019-03-12 UPLOAD is an SEC comment letter to Bristol-Myers Squibb (topic: acquisitions)",
         what_the_source_says="Letter is addressed to Starboard Value's counsel (Olshan Frome Wolosky) about Starboard's PREC14A against the Celgene deal; BMS is not the filer and never replied",
         how_caught="read the addressee block of the staff letter", count=1,
         example_source="data/moat/companies/BMY/sec_letters/2019-03-12_UPLOAD_0000000000-19-004490.md p1"),
    dict(table="sec_comment_letters.csv", what_the_ai_said="topic keywords per letter (blank or contingencies/collaboration/acquisitions)",
         what_the_source_says="Highest-value letters have blank or wrong topics: MRK 2025 Keytruda license dependence (blank), AMGN 2024 price/volume MD&A (blank), LLY/NVO 2023 climate (blank, no climate tag), BMY 2020 forum bylaw tagged contingencies, GILD 2023 R&D-by-project tagged collaboration, PFE 2024 equity-award tender tagged acquisitions",
         how_caught="read every UPLOAD letter and compared to its topics cell", count=9,
         example_source="data/moat/tables/sec_comment_letters.csv rows MRK 2025-04-10, AMGN 2024-04-05"),
    dict(table="sec_comment_letters.csv", what_the_ai_said="each exchange has a staff UPLOAD letter",
         what_the_source_says="Five CORRESP replies (LLY Prevail 2021, GILD Immunomedics 2020 and CymaBay 2024, BMY RayzeBio 2024, AZN Icosavax 2024) have no staff letter in the collection; the M&A-office tender-offer letters were not collected",
         how_caught="paired every CORRESP with an UPLOAD by subject and date", count=5,
         example_source="data/moat/companies/GILD/sec_letters/2024-03-11_CORRESP_0001104659-24-032743.md"),
    dict(table="exec_comp_metrics.csv / gaps secx.jsonl", what_the_ai_said="ABBV short-term incentive weights are an image chart; 0 rows 2024-2026",
         what_the_source_says="The 2026 proxy text layer contains the per-NEO weight table (CEO: Platform Revenue 20%, IBT/op margin/ROA 60% equally weighted, ESG 10%, other 10%) and PSU/PVRSU/option weights 40/40/20",
         how_caught="read pdf pages 43-46 of the proxy", count=1, example_source="data/moat/companies/ABBV/proxy_2026.md pdf 43 / printed 40"),
    dict(table="exec_comp_metrics.csv", what_the_ai_said="percent + metric keyword on plan pages = incentive metric weight",
         what_the_source_says="About 20 of 58 rows for proxy year 2026 are not weights (payout %, business mix 55%/47%, IRA 1.6% revenue hit, biosimilar growth 37%, TSR percentiles, 157.66% factor parsed as 66); LLY Bonus Plan weights labeled lti; AMGN pdf 79 rows are the 2026 goals, not the 2025 plan",
         how_caught="hand read of every company's annual and LTI sections; verified table has 51 quoted rows", count=20,
         example_source="data/moat/tables/exec_comp_metrics.csv BMY 'Pipeline 3 3.0 100% 100.00%' -> weights '100;00'"),
    dict(table="exec_comp_metrics.csv", what_the_ai_said="printed_page '?' for MRK, BMY, ABBV proxies",
         what_the_source_says="Printed folio is in the page text (e.g. MRK pdf 54 shows '52', ABBV pdf 43 shows '40 | 2026 Proxy Statement')",
         how_caught="page read", count=3, example_source="data/moat/companies/MRK/proxy_2026.md pdf 54"),
    dict(table="insider_trades.csv", what_the_ai_said="one row per Form 4 transaction",
         what_the_source_says="4 exact duplicate rows inside one accession (GILD Mercier 2025-05-22 and 2025-08-15 incl. a 700-share sale) and 1 transaction re-reported in a 2025 Form 4/A (ABBV Thakkar 2024-02-15); no form-type column, so amendments are only detectable by filename (10 'form4a' URLs)",
         how_caught="key-level dedupe on person/date/code/shares/price/security/owned_after/accession", count=5,
         example_source="https://www.sec.gov/Archives/edgar/data/882095/000088209525000037/"),
    dict(table="material_agreements.csv", what_the_ai_said="32 rows of material license/collaboration agreements",
         what_the_source_says="4 are not commercial agreements: AMGN 4.3 indenture trustee resignation (2008), AMGN 10.14 Bradner employment letter, GILD 10.51 Parsey separation, GILD 10.58 employee invention form; 2 JNJ rows are Kenvue separation IP/trademark agreements",
         how_caught="title read per row", count=4, example_source="data/moat/tables/material_agreements.csv AMGN 4.3"),
]

if __name__ == "__main__":
    ai_wrong(E)
