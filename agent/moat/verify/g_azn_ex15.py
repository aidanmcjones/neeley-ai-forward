"""Fetch AstraZeneca 20-F exhibit 15.1 (Annual Report and Form 20-F Information excerpts incl. Directors' Remuneration
Report) for FY2024 and FY2025 and land them page-marked under companies/AZN/."""
from agent.corpus import paged_text, render
from agent.moat import common
from agent.moat.verify.g_fetch import get

DOCS = [
    ("2025", "2026-02-24", "https://www.sec.gov/Archives/edgar/data/901832/000110465926019130/azn-20251231xex15d1.htm"),
    ("2024", "2025-02-18", "https://www.sec.gov/Archives/edgar/data/901832/000110465925014750/azn-20241231xex15d1.htm"),
]

for fy, filed, url in DOCS:
    raw = get(url)
    pages = paged_text(raw)
    rel = f"companies/AZN/20f_FY{fy}_ex15d1.md"
    hdr = (f"<!-- source: {url}\n     ticker: AZN  type: annual_report  form: 20-F exhibit 15.1  filed: {filed}  "
           f"period: {fy}-12-31\n     retrieved: {common.now()} -->\n")
    row = common.write("secx", rel, render(pages, hdr), ticker="AZN", group="companies", doc_type="annual_report",
                       form="20-F", period=f"{fy}-12-31", filed=filed, source_url=url, pages=len(pages),
                       pages_with_folio=sum(1 for f, _ in pages if f))
    print(row["path"], row["pages"], row["pages_with_folio"], row["chars"])
