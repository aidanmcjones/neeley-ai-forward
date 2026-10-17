"""Download the free FDA / CMS reference files the pharma case needs into data/external/ (gitignored).

Exclusivity: Orange Book (small-molecule patents + exclusivity), Purple Book (biologics), Paragraph IV list.
Pricing: IRA selected drugs + negotiated prices, Medicare Part D and Part B spending by drug.
Bridges: Drugs@FDA (sponsors, approvals), openFDA NDC directory (NDC <-> NDA/BLA).
Source map and caveats: docs/research/pharma_data_map.md

Run:  python -m agent.public_data
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

OUT = Path(__file__).resolve().parent.parent / "data" / "external"

FILES = {
    "orange_book.zip": "https://www.fda.gov/media/76860/download",
    "purple_book_2026_09.csv":
        "https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-September-data-download.csv",
    "paragraph_iv.xlsx": "https://www.fda.gov/media/194880/download?attachment",
    "ira_selected_drugs_mfp.zip":
        "https://www.cms.gov/files/zip/selected-drug-list-negotiated-prices-also-known-maximum-fair-prices-statutezip.zip",
    "partd_spending_dy24.csv":
        "https://data.cms.gov/sites/default/files/2026-06/98218f98-166c-4723-8438-c344a4ef96a6/"
        "DSD_PTD_RY26_P04_V10_DY24_BGM.csv",
    "partb_spending_dy24.csv":
        "https://data.cms.gov/sites/default/files/2026-06/6616fc91-eb70-404c-9f27-1448e47a3a73/"
        "DSD_PTB_RY26_P06_V10_DYT24_HCPCS-%20260602.csv",
    "drugsatfda.zip": "https://www.fda.gov/media/89850/download",
    "openfda_ndc.json.zip": "https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip",
}


def main():
    ua = os.environ.get("SEC_USER_AGENT") or sys.exit("Set SEC_USER_AGENT (name and contact email)")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        r = requests.get(url, headers={"User-Agent": ua}, timeout=300)
        r.raise_for_status()
        (OUT / name).write_bytes(r.content)
        print(f"{name:32s} {len(r.content) / 1e6:7.2f} MB")


if __name__ == "__main__":
    main()
