"""Fetch Novo Nordisk Remuneration Report 2024 (6-K 2025-02-05) and land it page-marked under companies/NVO/6k/."""
from agent.corpus import paged_text, render
from agent.moat import common
from agent.moat.verify.g_fetch import get

URL = "https://www.sec.gov/Archives/edgar/data/353278/000162828025003906/novonordiskremunerationr.htm"
REL = "companies/NVO/6k/2025-02-05_novonordisk_remuneration.md"

raw = get(URL)
pages = paged_text(raw)
hdr = (f"<!-- source: {URL}\n     ticker: NVO  type: foreign_current_report  form: 6-K  filed: 2025-02-05  "
       f"period: 2024-12-31\n     retrieved: {common.now()} -->\n")
md = render(pages, hdr)
row = common.write("secx", REL, md, ticker="NVO", group="companies", doc_type="foreign_current_report", form="6-K",
                   period="2024-12-31", filed="2025-02-05", source_url=URL, pages=len(pages),
                   pages_with_folio=sum(1 for f, _ in pages if f))
print(row["path"], row["pages"], row["chars"])
