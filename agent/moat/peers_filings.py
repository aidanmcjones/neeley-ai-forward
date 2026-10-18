"""Peers: annual reports FY2022-FY2024 and quarterly 10-Q / results 6-K, 2023 to Sep 2025, page-marked. Resumable."""
import re, sys
import agent.tenk as tenk
tenk.MIN_INTERVAL = 0.4
from agent.tenk import sec_get, html_to_text
from agent.corpus import filings, folder_docs, paged_text, render, quarter_label, now
from agent.moat.common import write, note_gap, OUT

CIKS = {"NVS": 1114448, "GSK": 1131399, "SNY": 1121404, "TAK": 1395064, "REGN": 872589, "ALNY": 1178670,
        "BBIO": 1743881}
FOREIGN = {"NVS", "GSK", "SNY", "TAK"}
ANNUAL_YEARS = {"TAK": ("2023", "2024", "2025")}
mode = sys.argv[1] if len(sys.argv) > 1 else "all"
only = sys.argv[2].split(",") if len(sys.argv) > 2 else list(CIKS)
RES = re.compile(r"financial report|first (three|six|nine) months|first (quarter|half)|(first|second|third|fourth)[- ]quarter|"
                 r"half[- ]year|full[- ]year|interim|results|Q[1-4]|9M|H1|FY", re.I)
SKIP = re.compile(r"repurchase|voting rights|transactions in own|notification of major|director/pdmr|block listing", re.I)


def save(t, rel, url, f, doc_type):
    if (OUT / rel).exists():
        return True
    try:
        raw = sec_get(url)
    except Exception as e:
        note_gap("peers", t, rel, repr(e))
        return False
    pages = paged_text(raw)
    header = (f"<!-- source: {url}\n     ticker: {t}  type: {doc_type}  form: {f['form']}  filed: {f['filed']}  "
              f"period: {f['period']}\n     retrieved: {now()} -->\n")
    write("peers", rel, render(pages, header), ticker=t, group="companies", doc_type=doc_type, form=f["form"],
          period=f["period"], filed=f["filed"], source_url=url, pages=len(pages),
          pages_with_folio=sum(1 for p, _ in pages if p))
    print(t, rel, len(pages), flush=True)
    return True


def url_of(cik, f):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accession'].replace('-', '')}/{f['primary_doc']}"


def annual(t, cik, fs):
    form = "20-F" if t in FOREIGN else "10-K"
    years = ANNUAL_YEARS.get(t, ("2022", "2023", "2024"))
    got = set()
    for f in fs:
        if f["form"] == form and (f["period"] or "")[:4] in years:
            fy = f["period"][:4]
            save(t, f"companies/{t}/{form.lower().replace('-', '')}_FY{fy}.md", url_of(cik, f), f, "annual_report")
            got.add(fy)
    for y in years:
        if y not in got:
            note_gap("peers", t, f"annual FY{y}", "no matching filing in EDGAR submissions")


def quarterly(t, cik, fs):
    if t not in FOREIGN:
        for f in fs:
            if f["form"] == "10-Q" and "2023-01-01" <= (f["period"] or "") <= "2025-09-30":
                save(t, f"companies/{t}/10q_{quarter_label(f['period'])}.md", url_of(cik, f), f, "quarterly_report")
        return
    for f in fs:
        if f["form"] != "6-K" or not ("2023-01-01" <= f["filed"] <= "2025-09-30"):
            continue
        try:
            docs = folder_docs(cik, f["accession"])
        except Exception as e:
            note_gap("peers", t, f"6-K {f['accession']}", repr(e))
            continue
        for n, u in docs:
            if not n.lower().endswith((".htm", ".html")) or "-index" in n:
                continue
            rel = f"companies/{t}/6k/{f['filed']}_{f['accession']}.md"
            if (OUT / rel).exists():
                break
            try:
                raw = sec_get(u)
            except Exception as e:
                note_gap("peers", t, rel, repr(e))
                continue
            txt = html_to_text(raw)
            head = txt[:4000]
            if len(txt) < 30000 or not RES.search(head) or SKIP.search(head[:1500]):
                continue
            save(t, rel, u, f, "foreign_current_report")
            break


for t in only:
    cik = CIKS[t]
    _, fs = filings(cik, "2022-01-01")
    fs = [f for f in fs if f["form"] not in ("10-K/A", "20-F/A")]
    if mode in ("all", "a"):
        annual(t, cik, fs)
    if mode in ("all", "q"):
        quarterly(t, cik, fs)
print("done")
