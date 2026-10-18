"""Download White House and Federal Register texts for the policy stream."""
import html
import io
import re
import time

import pypdf

from agent.moat.common import header, note_gap, write
from agent.moat.policy_gov import get

WH = "https://www.whitehouse.gov"
DOCS = [
    ("wh/wh_fact_sheet_2025-07-31_mfn_letters_actions.md", WH + "/fact-sheets/2025/07/fact-sheet-president-donald-j-trump-announces-actions-to-get-americans-the-best-prices-in-the-world-for-prescription-drugs/", "html"),
    ("wh/wh_fact_sheet_2025-09-30_first_deal_pfizer.md", WH + "/fact-sheets/2025/09/fact-sheet-president-donald-j-trump-announces-first-deal-to-bring-most-favored-nation-pricing-to-american-patients/", "html"),
    ("wh/wh_fact_sheet_2025-10-10_second_deal_astrazeneca.md", WH + "/fact-sheets/2025/10/fact-sheet-president-donald-j-trump-announces-second-deal-to-bring-most-favored-nation-pricing-to-american-patients/", "html"),
    ("wh/wh_fact_sheet_2025-11-06_lilly_novo.md", WH + "/fact-sheets/2025/11/fact-sheet-president-donald-j-trump-announces-major-developments-in-bringing-most-favored-nation-pricing-to-american-patients/", "html"),
    ("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md", WH + "/fact-sheets/2025/12/fact-sheet-president-donald-j-trump-announces-largest-developments-to-date-in-bringing-most-favored-nation-pricing-to-american-patients/", "html"),
    ("wh/wh_fact_sheet_2026-02-05_trumprx_launch.md", WH + "/fact-sheets/2026/02/fact-sheet-president-donald-j-trump-launches-trumprx-gov-to-bring-lower-drug-prices-to-american-patients/", "html"),
    ("wh/wh_fact_sheet_2026-04-regeneron_lists_all_signers.md", WH + "/fact-sheets/2026/04/fact-sheet-president-donald-j-trump-announces-deal-with-regeneron-to-bring-most-favored-nation-pricing-to-american-patients/", "html"),
    ("wh/wh_fact_sheet_2026-08-nine_additional_manufacturers.md", WH + "/fact-sheets/2026/08/fact-sheet-president-donald-j-trump-announces-deal-with-nine-additional-pharmaceutical-manufacturers-to-lower-drug-prices-for-americans/", "html"),
    ("wh/wh_fact_sheet_2026-09-medicaid_all_50_states.md", WH + "/fact-sheets/2026/09/fact-sheet-president-donald-j-trump-announces-lower-drug-prices-for-all-50-state-medicaid-programs/", "html"),
    ("wh/wh_cea_2026-05_savings_from_mfn.md", WH + "/wp-content/uploads/2026/05/Savings-from-MFN-Drug-Pricing-Policy.pdf", "pdf"),
    ("tariff/wh_proclamation_11020_2026-04-02_section232_pharma.md", WH + "/presidential-actions/2026/04/adjusting-imports-of-pharmaceuticals-and-pharmaceutical-ingredients-into-the-united-states/", "html"),
    ("tariff/fr_proclamation_11020_2026-06956.md", "https://www.federalregister.gov/documents/full_text/text/2026/04/09/2026-06956.txt", "txt"),
    ("tariff/fr_bis_onshoring_notice_2026-09489.md", "https://public-inspection.federalregister.gov/2026-09489.pdf", "pdf"),
    ("tariff/fr_amendment_effective_dates_2026-19498.md", "https://public-inspection.federalregister.gov/2026-19498.pdf", "pdf"),
]


def html_text(raw):
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|br)>|<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def pages_from(kind, raw):
    if kind == "pdf":
        r = pypdf.PdfReader(io.BytesIO(raw))
        return [p.extract_text() or "" for p in r.pages]
    if kind == "txt":
        t = raw.decode("utf-8", "replace")
        chunks = [t[i:i + 6000] for i in range(0, len(t), 6000)]
        return chunks
    return [html_text(raw)]


if __name__ == "__main__":
    for rel, url, kind in DOCS:
        try:
            raw = get(url)
            pgs = pages_from(kind, raw)
            body = header(url, type="gov") + "".join(f"\n[[page {i} | printed {i}]]\n\n{p}\n" for i, p in enumerate(pgs, 1))
            write("policy", "policy_gov/" + rel, body, group="policy_gov", doc_type="gov", source_url=url, pages=len(pgs))
            print("ok", rel, len(pgs), len(body))
        except Exception as e:
            print("FAIL", rel, e)
            note_gap("policy", None, rel, f"download failed {e}")
        time.sleep(0.5)
