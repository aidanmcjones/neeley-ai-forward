"""Roche annual reports FY2022-24 (+finance reports) and last quarterly releases as page-marked PDFs text."""
import io
import re
import pypdf
import requests
from agent.moat.common import write, note_gap, header, OUT

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
A = "https://assets.roche.com/f/176343/x/"
DOCS = [
    ("annual_report_2024", A + "09457b2a19/ar24e.pdf", "annual_report", "2024FY"),
    ("finance_report_2024", A + "38d96ed8ec/fb24e.pdf", "annual_report", "2024FY"),
    ("annual_report_2023", A + "98b8e2ba9d/ar23e.pdf", "annual_report", "2023FY"),
    ("finance_report_2023", A + "3b1fb647e2/fb23e.pdf", "annual_report", "2023FY"),
    ("annual_report_2022", A + "43f14540f2/ar22e.pdf", "annual_report", "2022FY"),
    ("finance_report_2022", A + "537a274a55/fb22e.pdf", "annual_report", "2022FY"),
    ("results_2025Q1_slides", A + "0cd9054dc9/irp250424.pdf", "results_release", "2025Q1"),
    ("results_2025H1_report", A + "2d95c66259/hy25e.pdf", "results_release", "2025H1"),
    ("results_2025H1_slides", A + "cc1705dc16/irp250724.pdf", "results_release", "2025H1"),
    ("results_20259M_slides", A + "a22e1c7d2f/irp251023.pdf", "results_release", "2025Q3"),
    ("results_2025FY_slides", A + "dea78e334b/irp260129.pdf", "results_release", "2025FY"),
    ("results_2026Q1_slides", A + "75c58a5152/irp260423.pdf", "results_release", "2026Q1"),
]
FOLIO = re.compile(r"^\s*(\d{1,3})\s*$")


def main():
    for name, url, dt, per in DOCS:
        rel = f"companies/ROCHE/{name}.md"
        if (OUT / rel).exists():
            continue
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=120)
            r.raise_for_status()
            rd = pypdf.PdfReader(io.BytesIO(r.content))
            parts, nf = [header(url, ticker="ROCHE", type=dt, period=per, quality="official", format="pdf")], 0
            for i, pg in enumerate(rd.pages, 1):
                t = pg.extract_text() or ""
                lines = [l for l in t.split("\n") if l.strip()]
                folio = next((FOLIO.match(l).group(1) for l in lines[:2] + lines[-2:] if FOLIO.match(l)), None)
                nf += bool(folio)
                parts.append(f"\n\n[[page {i} | printed {folio or '?'}]]\n\n{t}")
            write("peers", rel, "".join(parts) + "\n", ticker="ROCHE", group="companies", doc_type=dt, period=per,
                  source_url=url, pages=len(rd.pages), pages_with_folio=nf)
            print("OK", rel, len(rd.pages), flush=True)
        except Exception as e:
            note_gap("peers", "ROCHE", name, repr(e))
            print("FAIL", name, e, flush=True)
    for item in ("annual reports FY2022-FY2024", "quarterly results releases (last 6)", "earnings call transcripts 2024Q1-2025Q2"):
        note_gap("peers", "BOEHRINGER", item, "boehringer-ingelheim.com is behind Incapsula bot protection (HTTP 200 with challenge page; PDFs 403); no mirror found")
    note_gap("peers", "ROCHE", "earnings call transcripts 2024Q1-2025Q2", "Roche posts no transcripts; MarketBeat has none; roic.ai page is a listing only")
    note_gap("peers", "BOEHRINGER", "transcripts", "private company: no earnings calls")


main()
