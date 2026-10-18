import csv, os, re, time
import pymupdf
import agent.tenk as tenk
from agent.moat.secx_lib import *
from agent.moat.secx_letters import TOPICS


def get_bytes(url):
    for a in range(4):
        time.sleep(0.5)
        r = tenk._session.get(url, headers={"User-Agent": os.environ["SEC_USER_AGENT"]}, timeout=60)
        if r.status_code == 200:
            return r.content
        time.sleep(2 ** a)
    raise RuntimeError(url)


def main():
    p = OUT / "tables" / "sec_comment_letters.csv"
    rows = list(csv.DictReader(p.open()))
    for r in rows:
        if not r["url"].lower().endswith(".pdf"):
            continue
        try:
            doc = pymupdf.open(stream=get_bytes(r["url"]), filetype="pdf")
        except Exception as e:
            note_gap("secx", r["ticker"], f"letter pdf {r['accession']}", repr(e)[:150])
            continue
        pages = [(str(i), pg.get_text()) for i, pg in enumerate(doc, 1)]
        full = "\n".join(t for _, t in pages)
        if len(full.strip()) < 200:
            note_gap("secx", r["ticker"], f"letter pdf {r['accession']}", "no extractable text (scanned?)")
        r["topics"] = ";".join(k for k, pat in TOPICS.items() if re.search(pat, full, re.I))
        rel = r["path"].replace("data/moat/", "")
        hdr = f"<!-- source: {r['url']} | ticker: {r['ticker']} type: sec_comment_letter form: {r['form']} filed: {r['date']} -->\n"
        write("secx", rel, render(pages, hdr), ticker=r["ticker"], group="companies", doc_type="sec_comment_letter",
              form=r["form"], filed=r["date"], source_url=r["url"], pages=len(pages), pages_with_folio=len(pages))
        m = re.search(r"(?is)(Form\s+(?:10-K|20-F|10-Q|8-K)[^\n]*\n[^\n]*\n?[^\n]*)", full)
        r["subject"] = " ".join(m.group(1).split())[:160] if m else ""
    cols = ["ticker", "date", "form", "accession", "topics", "url", "path", "subject"]
    write_csv("tables/sec_comment_letters.csv", cols, rows)


main()
