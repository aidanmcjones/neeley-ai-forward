"""Download government primary texts for the policy stream and write page-marked markdown under policy_gov/."""
import io
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

import pypdf

from agent.moat.common import header, note_gap, write

UA = {"User-Agent": "Mozilla/5.0 (research; aidan@justinianhq.com)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=90).read()


def pdf_to_md(raw, url, **meta):
    r = pypdf.PdfReader(io.BytesIO(raw))
    out = [header(url, **meta)]
    for i, p in enumerate(r.pages, 1):
        out.append(f"\n[[page {i} | printed {i}]]\n\n" + (p.extract_text() or ""))
    return "".join(out), len(r.pages)


def put_pdf(rel, url, raw, ticker=None, doc_type="gov_pdf", period=None):
    md, n = pdf_to_md(raw, url, type=doc_type)
    write("policy", rel, md, ticker=ticker, group="policy_gov", doc_type=doc_type, period=period,
          source_url=url, pages=n)
    print("ok", rel, n)


CMS = "https://www.cms.gov"
FACT = {
    "cms_fact_sheet_selected_list_ipay2026.md": "/files/document/fact-sheet-medicare-selected-drug-negotiation-list-ipay-2026.pdf",
    "cms_fact_sheet_negotiated_prices_ipay2026.md": "/files/document/fact-sheet-negotiated-prices-initial-price-applicability-year-2026.pdf",
    "cms_fact_sheet_selected_list_ipay2027.md": "/files/document/factsheet-medicare-negotiation-selected-drug-list-ipay-2027.pdf",
    "cms_fact_sheet_negotiated_prices_ipay2027.md": "/files/document/fact-sheet-negotiated-prices-ipay-2027.pdf",
    "cms_fact_sheet_selected_list_ipay2028.md": "/files/document/factsheet-medicare-negotiation-selected-drug-list-ipay-2028.pdf",
    "cms_fact_sheet_third_cycle.md": "/files/document/fact-sheet-medicare-drug-price-negotiation-third-cycle.pdf",
    "cms_fact_sheet_top50_eligible_ipay2028.md": "/files/document/factsheet-medicare-top-50-negotiation-eligible-drug-list-ipay-2028.pdf",
    "cms_fact_sheet_manufacturer_agreements_ipay2026.md": "/files/document/fact-sheet-manufacturer-agreements-selected-drugs-ipay-2026.pdf",
    "cms_ipay2028_final_guidance_renegotiation.md": "/files/document/ipay-2028-final-guidance.pdf",
}
MFP = ["breo-ellipta", "calquence", "ibrance", "janumet-janumet-xr", "linzess", "ofev", "austedo-austedo-xr", "eliquis",
       "enbrel", "entresto", "farxiga", "imbruvica", "januvia", "jardiance", "novolog/fiasp", "otezla-otezla-xr",
       "ozempic-rybelsus-wegovy", "pomalyst", "stelara", "tradjenta", "trelegy-ellipta", "vraylar", "xarelto", "xifaxan",
       "xtandi"]
PREFIX = {"breo-ellipta", "calquence", "ibrance", "janumet-janumet-xr", "linzess", "ofev"}

if __name__ == "__main__":
    which = sys.argv[1]
    if which == "cms":
        for rel, path in FACT.items():
            try:
                put_pdf("policy_gov/cms/" + rel, CMS + path, get(CMS + path), doc_type="cms_fact_sheet")
            except Exception as e:
                print("FAIL", rel, e)
                note_gap("policy", None, rel, f"download failed {e}")
            time.sleep(0.5)
    if which == "mfp":
        for slug in MFP:
            pre = "file-" if slug in PREFIX else ""
            url = f"{CMS}/files/zip/{pre}mfp-explanation-{slug}.zip"
            try:
                z = zipfile.ZipFile(io.BytesIO(get(urllib.parse.quote(url, safe=":/"))))
                done = False
                for name in z.namelist():
                    if name.lower().endswith(".pdf"):
                        base = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
                        put_pdf(f"policy_gov/cms/mfp_explanation_{base}.md", url, z.read(name), doc_type="mfp_explanation")
                        done = True
                        break
                if not done:
                    print("no pdf in", slug, z.namelist())
            except Exception as e:
                print("FAIL", slug, e)
                note_gap("policy", None, f"mfp_explanation_{slug}", f"download failed {e}")
            time.sleep(0.5)
