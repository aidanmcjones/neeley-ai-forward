"""Log the AI errors found while closing the NVO/AZN pay-metric and 2026-launch label/price gaps (run once)."""
from agent.moat.verify.pe_lib import AIW, log_wrong

E = [
    {"stream": "secx", "table": "progress.json (fine_print bucket, agent/moat/progress.py)",
     "what_the_ai_said": "Foreign filers' remuneration report is Item 6B of the 20-F, which is indexed, so the three 20-Fs stand in for the three proxies",
     "what_the_source_says": "Neither indexed 20-F holds the pay tables. NVO 20-F Item 6B only cross-references the separate Remuneration Report (6-K): the 2025 one was in data/corpus, the 2024 one (6-K 2025-02-05, acc 0001628280-25-003906) was not collected. AZN's Directors' Remuneration Report is in 20-F exhibit 15.1, which was not collected for FY2024 or FY2025 (the main 20-F document has no Group scorecard or PSP outcome tables)",
     "how_caught": "read the 20-F Item 6 cross-references and the EDGAR filing index; fetched the missing documents",
     "count": 2,
     "example_source": "NVO 20-F FY2025 acc 0000353278-26-000012 (sections 3.5-3.8 cited by reference); AZN 20-F FY2025 acc 0001104659-26-019130 exhibit azn-20251231xex15d1.htm"},
    {"stream": "product", "table": "progress.json (product_evidence note, agent/moat/progress.py)",
     "what_the_ai_said": "foundayo has one label version so far (2026 launch), no history to compare",
     "what_the_source_says": "DailyMed setid 8ac446c5-feba-474f-a103-23facb9b5c62 has two versions: SPL v5 (effective 2026-04-01, initial approval) and v10 (effective 2026-07-29, published 2026-08-13; sections 16, 17 and the Medication Guide changed; Drugs@FDA S-3 labeling AP 2026-08-04). Foundayo was missing from verified label_changes only because the label verifier's APPENDIX list omitted it and no key section changed",
     "how_caught": "DailyMed history.json and SPL XML diff",
     "count": 1,
     "example_source": "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/8ac446c5-feba-474f-a103-23facb9b5c62/history.json"},
]

if __name__ == "__main__":
    have = AIW.read_text()
    new = [e for e in E if e["what_the_ai_said"] not in have]
    log_wrong(new)
    print("appended", len(new))
