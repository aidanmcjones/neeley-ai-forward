"""Peers item 5: FY labels and [[page N | printed M]] markers, 2 annual docs per peer.

FY label: the file's FY must equal the 'fiscal year ended ...' on the cover (Takeda: FY ends Mar 31 of the next
calendar year, so 20f_FY2024 must say 'March 31, 2025').
Page markers: for SEC HTML filings there is no PDF; we check that the printed folio in the marker is the folio
printed on that page and that folios run in order. For Roche we download the PDF and compare page count and page
text for 6 pages.
"""
import io
import random
import re
import urllib.request
from pathlib import Path

import pandas as pd
import pymupdf

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, norm, pages

DOCS = {"NVS": ["20f_FY2022", "20f_FY2024"], "GSK": ["20f_FY2022", "20f_FY2024"], "SNY": ["20f_FY2023", "20f_FY2024"],
        "TAK": ["20f_FY2023", "20f_FY2025"], "REGN": ["10k_FY2022", "10k_FY2024"], "ALNY": ["10k_FY2022", "10k_FY2024"],
        "BBIO": ["10k_FY2023", "10k_FY2024"], "ROCHE": ["annual_report_2023", "finance_report_2024"]}
FYE = re.compile(r"(?:fiscal\s+year\s+ended|year\s+ended)\s*:?\s*(January|February|March|April|May|June|July|August|"
                 r"September|October|November|December)\s+(\d{1,2})\s*,\s*(20\d\d)", re.I)
UA = {"User-Agent": "Neeley AI Forward research aidan@justinianhq.com"}


def main():
    rows = []
    random.seed(5)
    for t, docs in DOCS.items():
        for doc in docs:
            path = f"data/moat/companies/{t}/{doc}.md"
            P = pages(path)
            txt = (ROOT / path).read_text(errors="replace")
            head = txt[:500]
            fy = int(re.search(r"(20\d\d)", doc).group(1))
            m = FYE.search(txt[:40000])
            cover = f"{m.group(1)} {m.group(2)}, {m.group(3)}" if m else None
            exp_year = fy + 1 if t == "TAK" else fy
            fy_ok = (m is not None and int(m.group(3)) == exp_year) if t != "ROCHE" else (str(fy) in txt[:3000])
            folio = [(k, p) for k, (p, _) in P.items() if p not in ("?", "")]
            sample = random.sample(folio, min(8, len(folio)))
            on_page = 0
            for k, p in sample:
                body = [l.strip() for l in P[k][1].split("\n") if l.strip()]
                edge = body[:4] + body[-4:]
                if any(re.search(r"(^|\D)" + re.escape(p) + r"(\D|$)", l) for l in edge):
                    on_page += 1
            ints = [int(p) for _, p in folio if p.isdigit()]
            mono = sum(1 for a, b in zip(ints, ints[1:]) if b < a)
            pdf_pages = pdf_match = None
            if t == "ROCHE":
                url = re.search(r"source: (\S+)", head).group(1)
                f = Path("/tmp/pev/pdf") / url.split("/")[-1]
                f.parent.mkdir(parents=True, exist_ok=True)
                if not f.exists():
                    f.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
                pdf = pymupdf.open(f)
                pdf_pages = pdf.page_count
                pick = random.sample([k for k in P if len(norm(P[k][1], True)) > 300], 6)
                pdf_match = 0
                for k in pick:
                    a = norm(P[k][1], True)[50:250]
                    b = norm(pdf[k - 1].get_text(), True)
                    pdf_match += a in b
                pdf_match = f"{pdf_match}/6"
            rows.append(dict(ticker=t, doc=doc, path=path, fy_label=fy, cover_period_end=cover, fy_label_ok=fy_ok,
                             md_pages=len(P), pages_with_folio=len(folio),
                             folio_on_page_sample=f"{on_page}/{len(sample)}", folio_out_of_order=mono,
                             pdf_pages=pdf_pages, pdf_text_match=pdf_match,
                             source_url=re.search(r"source: (\S+)", head).group(1)))
    v = pd.DataFrame(rows)
    print(v.drop(columns=["path", "source_url"]).to_string())
    buf = io.StringIO()
    v.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/annual_report_page_checks.csv", buf.getvalue(), group="tables",
          doc_type="table", quality="verified", source_url="data/moat/companies/<T>/ annual docs")


if __name__ == "__main__":
    main()
