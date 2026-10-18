"""Fetch AZN half-year results 6-Ks the collector missed (filed by a second agent as 'FORM 6K')."""
import json, os
os.environ.setdefault("SEC_USER_AGENT", "Neeley AI Forward hackathon aidan@justinianhq.com")
import agent.tenk
agent.tenk.MIN_INTERVAL = 0.5
from agent.tenk import sec_get, html_to_text
from agent.corpus import paged_text, render, now
from agent.moat.common import write, OUT

SUBS = json.load(open("data/moat/scratch/f_subs.json"))
MISSING = ["0001104659-23-085104", "0001104659-24-082531", "0001104659-25-071432"]
for acc in MISSING:
    f = SUBS[acc]
    url = f"https://www.sec.gov/Archives/edgar/data/901832/{acc.replace('-', '')}/{f['primary_doc']}"
    rel = f"companies/AZN/6k/{f['filed']}_{acc}.md"
    if (OUT / rel).exists():
        print("exists", rel); continue
    raw = sec_get(url)
    head = html_to_text(raw)[:3000]
    pages = paged_text(raw)
    header = (f"<!-- source: {url}\n     ticker: AZN  type: foreign_current_report  form: 6-K  filed: {f['filed']}  "
              f"period: {f['period']}\n     retrieved: {now()} -->\n")
    row = write("filings", rel, render(pages, header), ticker="AZN", group="companies", doc_type="foreign_current_report",
                form="6-K", period=f["period"], filed=f["filed"], source_url=url, pages=len(pages),
                pages_with_folio=sum(1 for p, _ in pages if p))
    print(rel, len(pages), len(raw), head[:300].replace("\n", " "))
