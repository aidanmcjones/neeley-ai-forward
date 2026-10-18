"""Company US pricing transparency reports -> page-marked markdown (selected pages for long ESG reports)."""
import requests, pymupdf, re
from agent.moat.common import write, header, note_gap

S = "pricing"
# ticker, year, url, pages (1-based, None = all), label
DOCS = [
    ("MRK", 2023, "https://www.merck.com/wp-content/uploads/sites/124/2024/02/PricingAction_TransparencyReport_2023.pdf", None),
    ("PFE", 2025, "https://cdn.pfizer.com/pfizercom/Pfizer_2025_Impact_Report_02JUN2026.pdf", range(52, 57)),
    ("BMY", 2025, "https://www.esg.bms.com/assets/bms-esg/us/documents/BMS-Impact-Report-2025.pdf", range(35, 40)),
    ("SNY", 2026, "https://www.sanofi.us/assets/dot-us/pages/images/our-company/Social-impact/responsible-business-values/pricing-principles/Sanofi-Pricing-Principles-2026-Continued-Transparency-in-the-US.pdf", None),
    ("NVO", 2025, "https://www.novonordisk.com/content/dam/nncorp/global/en/investors/irmaterial/annual_report/2026/novo-nordisk-form-20-f-2025.pdf", range(15, 20)),
    ("GSK", 2025, "https://www.gsk.com/media/di5bk40q/responsible-business-report.pdf", range(8, 13)),
    ("TAK", 2025, "https://assets-dam.takeda.com/image/upload/LOC/en-us/pricing-philosophy/2025_Pricing_Transparency.pdf", None),
    ("LLY", 2025, "https://investor.lilly.com/static-files/45a92498-43d0-4e2d-a4e6-a9131841cfd6", range(6, 11)),
]
H = {"User-Agent": "Mozilla/5.0 (Neeley AI Forward hackathon)"}
for tk, yr, url, pages in DOCS:
    try:
        r = requests.get(url, headers=H, timeout=120)
        r.raise_for_status()
        doc = pymupdf.open(stream=r.content, filetype="pdf")
    except Exception as e:
        print("FAIL", tk, url, e)
        note_gap(S, tk, f"pricing_report_{yr}", f"download failed: {e}")
        continue
    idx = [i for i in range(len(doc)) if pages is None or (i + 1) in pages]
    out = header(url, ticker=tk, doc="US pricing transparency", year=yr, total_pdf_pages=len(doc), pages_included=f"{idx[0]+1}-{idx[-1]+1}")
    for i in idx:
        out += f"\n[[page {i+1} | printed {i+1}]]\n" + doc[i].get_text() + "\n"
    write(S, f"companies/{tk}/pricing_report_{yr}.md", out, ticker=tk, doc_type="pricing_report", period=str(yr), source_url=url, pages=len(idx))
    print("ok", tk, yr, len(doc), len(out), flush=True)
    low = out.lower()
    for m in re.finditer(r"(net price|list price)[^\n]{0,160}", low):
        print("   ", m.group(0)[:200])
        break
