"""Page-marked 10-Qs (2023Q1-2025Q3), annuals FY2021-FY2023, AZN/NVO results 6-Ks. Resumable."""
import re, sys
import agent.tenk as tenk
tenk.MIN_INTERVAL = 0.2
from agent.tenk import sec_get, html_to_text
from agent.corpus import filings, folder_docs, paged_text, render, quarter_label, RESULTS_RE, now
from agent.moat.common import write, note_gap, OUT

CIKS = {"MRK": 310158, "BMY": 14272, "PFE": 78003, "LLY": 59478, "ABBV": 1551152, "JNJ": 200406, "AMGN": 318154,
        "GILD": 882095, "NVO": 353278, "AZN": 901832}
FOREIGN = {"NVO", "AZN"}
want_order = sys.argv[1] if len(sys.argv) > 1 else "all"


def save(t, rel, url, f, doc_type):
    if (OUT / rel).exists():
        return
    try:
        raw = sec_get(url)
    except Exception as e:
        note_gap("filings", t, rel, repr(e))
        return
    pages = paged_text(raw)
    header = (f"<!-- source: {url}\n     ticker: {t}  type: {doc_type}  form: {f['form']}  filed: {f['filed']}  "
              f"period: {f['period']}\n     retrieved: {now()} -->\n")
    body = render(pages, header)
    write("filings", rel, body, ticker=t, group="companies", doc_type=doc_type, form=f["form"], period=f["period"],
          filed=f["filed"], source_url=url, pages=len(pages), pages_with_folio=sum(1 for p, _ in pages if p))
    print(t, rel, len(pages), flush=True)


def url_of(cik, f):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accession'].replace('-', '')}/{f['primary_doc']}"


def do_quarterly(t, cik, fs):
    if t in FOREIGN:
        pat = re.compile(r"financial report|first (three|six|nine) months|first (quarter|half)|(first|second|third|fourth)[- ]quarter|half[- ]year|full[- ]year|results", re.I)
        for f in fs:
            if f["form"] != "6-K" or not ("2023-01-01" <= f["filed"] <= "2025-09-30"):
                continue
            if t == "AZN" and not re.search(r"result|H1|9M|FY|Q[1-4]", f["desc"], re.I):
                continue
            try:
                docs = folder_docs(cik, f["accession"])
            except Exception as e:
                note_gap("filings", t, f"6-K {f['accession']}", repr(e))
                continue
            for n, u in docs:
                if n.lower().endswith((".htm", ".html")) and "-index" not in n:
                    rel = f"companies/{t}/6k/{f['filed']}_{f['accession']}.md"
                    if (OUT / rel).exists():
                        continue
                    try:
                        raw = sec_get(u)
                    except Exception as e:
                        note_gap("filings", t, rel, repr(e))
                        continue
                    head = html_to_text(raw)[:4000]
                    if not pat.search(head) or re.search(r"repurchase|voting rights|transactions in own", head[:1500], re.I) or len(raw) < 40000:
                        continue
                    save(t, rel, u, f, "foreign_current_report")
                    break
        return
    for f in fs:
        if f["form"] == "10-Q" and "2023-01-01" <= (f["period"] or "") <= "2025-09-30":
            save(t, f"companies/{t}/10q_{quarter_label(f['period'])}.md", url_of(cik, f), f, "quarterly_report")


def do_annual(t, cik, fs):
    form = "20-F" if t in FOREIGN else "10-K"
    for f in fs:
        if f["form"] == form and (f["period"] or "")[:4] in ("2021", "2022", "2023"):
            fy = f["period"][:4]
            stem = f"{form.lower().replace('-', '')}_FY{fy}"
            save(t, f"companies/{t}/{stem}.md", url_of(cik, f), f, "annual_report")
            if t == "NVO":
                base = re.sub(r"\.htm$", "", f["primary_doc"])
                for n, u in folder_docs(cik, f["accession"]):
                    m = re.fullmatch(rf"{re.escape(base)}_(d\d+)\.htm", n)
                    if m:
                        save(t, f"companies/{t}/{stem}_{m.group(1)}.md", u, f, "annual_report")


for t, cik in CIKS.items():
    _, fs = filings(cik, "2021-01-01")
    fs = [f for f in fs if f["form"] != "10-K/A"]
    if want_order in ("all", "q"):
        do_quarterly(t, cik, fs)
for t, cik in CIKS.items():
    if want_order in ("all", "a"):
        _, fs = filings(cik, "2021-01-01")
        do_annual(t, cik, fs)
print("done")
