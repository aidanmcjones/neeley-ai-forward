"""Write verified/filings outputs through common.write (uploads to R2 moat/verified/filings/*.gz) and the AI-was-wrong log."""
import csv, json, re
from pathlib import Path
from agent.moat.common import write

files = {"doc_checks.csv": "data/moat/scratch/doc_checks.csv",
         "jnj_fiscal_quarters.csv": "data/moat/scratch/jnj_fiscal_quarters.csv",
         "product_revenue_checks.csv": "data/moat/scratch/product_revenue_checks.csv",
         "restatements_triaged.csv": "data/moat/scratch/restatements_triaged.csv",
         "discontinued_breakouts.csv": "data/moat/scratch/discontinued_breakouts_final.csv"}
for name, src in files.items():
    row = write("verify_filings", f"verified/filings/{name}", Path(src).read_text(), group="tables", doc_type="table",
                source_url="derived: SEC EDGAR filings + XBRL instances (see citation columns)")
    print(row["path"], row["chars"])

P = list(csv.DictReader(open("data/moat/tables/product_revenue_quarterly.csv")))
nonrev = [r for r in P if not re.search(r"Revenue(s$|FromContract|FromCollaborative)", r["concept"])]
T = list(csv.DictReader(open("data/moat/scratch/restatements_triaged.csv")))
cnt = lambda c: sum(1 for r in T if r["class"] == c)
pct = sum(1 for r in T if r["class"] == "parse_artifact" and "percent-change" in r["explanation"])
same = sum(1 for r in T if r["class"] == "parse_artifact" and "SAME filing" in r["explanation"])
E = [
 {"stream": "filings", "table": "restatements.csv", "what_the_ai_said": "616 rows of restated product revenue (same period, different value across filings)",
  "what_the_source_says": f"0 are true restatements of the same scope. {cnt('recast_reclassification')} are recasts where the company moved products in or out of an Other bucket, renamed/merged a line, reclassified royalty income into revenue (PFE Q1 2024) or reorganized divisions (PFE 2025, 2026), mostly footnoted ('Previously in Other Oncology', 'Prior-period amounts have been recast')",
  "how_caught": "member-set reconciliation of old vs new filing for the same period plus reading the product-table footnotes", "count": cnt("recast_reclassification"),
  "example_source": "JNJ 10-K filed 2026-02-11 data/corpus/companies/JNJ/10k_FY2025.md p31/printed 26 footnotes (1)-(5)"},
 {"stream": "filings", "table": "restatements.csv", "what_the_ai_said": "LLY (and some PFE/BMY) product values were revised between filings (e.g. Mounjaro US FY2023 4,834.2 -> 4,834)",
  "what_the_source_says": "Same number at different precision: the older filing tags $0.1M, the newer rounds to $1M", "how_caught": "rounding test |max-min| <= $0.5M", "count": cnt("comparative_presentation"),
  "example_source": "LLY 10-K filed 2026-02-12 acc 0000059478-26-000013 vs 10-K filed 2024-02-21 acc 0000059478-24-000065"},
 {"stream": "filings", "table": "restatements.csv", "what_the_ai_said": "JNJ product growth-rate rows restated (PercentageChangeInSalesBySegmentOfBusiness)",
  "what_the_source_says": "Concept is a percent change, not revenue; it differs only because the revenue base was recast", "how_caught": "concept-name check", "count": pct,
  "example_source": "JNJ 10-K filed 2026-02-11 acc 0000200406-26-000016"},
 {"stream": "filings", "table": "restatements.csv", "what_the_ai_said": "LLY COVID-19 antibodies 2022 revenue restated (1,469.8 vs 1,470)",
  "what_the_source_says": "Both values are in the same 10-Q (two facts at different decimals for one context); nothing was restated", "how_caught": "same accession appears under two values", "count": same,
  "example_source": "LLY 10-Q filed 2023-05 acc 0000059478-23-000162"},
 {"stream": "filings", "table": "product_revenue_quarterly.csv", "what_the_ai_said": "product revenue panel with value_usd for every row",
  "what_the_source_says": "Rows include non-revenue concepts: percent changes (stored as e.g. 0.177 in value_usd), sales-based milestones, sales thresholds, contract-liability amounts", "how_caught": "concept census of the panel", "count": len(nonrev),
  "example_source": "company:PercentageChangeInSalesBySegmentOfBusiness in JNJ instances; company:SalesThreshold in MRK 10-K FY2022"},
 {"stream": "filings", "table": "data/moat/companies/PFE/10q_*.md", "what_the_ai_said": "gap note says only JNJ 10-Q file names use calendar labels",
  "what_the_source_says": "PFE has the same offset: 10q_2023Q2/Q3/Q4 are Pfizer fiscal Q1/Q2/Q3 2023 (periods end 2023-04-02, 07-02, 10-01)", "how_caught": "period-end vs file-label check", "count": 3,
  "example_source": "data/moat/companies/PFE/10q_2023Q2.md period 2023-04-02"},
 {"stream": "filings", "table": "data/moat/companies/AZN/6k", "what_the_ai_said": "13 AZN results 6-Ks 2023 to mid-2025",
  "what_the_source_says": "Only 8 are results announcements; 5 are an AGM result (x3), a DESTINY-PanTumor02 trial readout and a TROPION-Breast01 OS readout; the 3 half-year reports (H1 2023, H1 2024, H1 2025, filed by a second agent as 'FORM 6K') were missed and are now fetched",
  "how_caught": "EDGAR 6-K descriptions vs AZN results calendar (FY Feb, Q1 Apr, H1 Jul, 9M Nov)", "count": 8,
  "example_source": "0001654954-24-004501 RESULT OF AGM; missing 0001104659-24-082531 azn-20240630x6k.htm"},
 {"stream": "filings", "table": "data/moat/companies/AZN/6k", "what_the_ai_said": "page-marked AZN 6-Ks",
  "what_the_source_says": "All 13 original AZN 6-Ks are a single [[page 1 | printed ?]] block (press-release HTML has no page breaks), so no printed-page citation is possible", "how_caught": "page-marker census", "count": 13,
  "example_source": "data/moat/companies/AZN/6k/2024-04-25_0001654954-24-004975.md"},
]
with open("data/moat/verify/ai_wrong.jsonl", "a") as f:
    for e in E:
        f.write(json.dumps(e) + "\n")
print("logged", len(E))
