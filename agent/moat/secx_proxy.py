import re
from agent.moat.secx_lib import *

METRIC = re.compile(r"(revenue|sales|EPS|earnings per share|non-GAAP|operating income|free cash flow|cash flow|pipeline|"
                    r"milestone|ROIC|return on invested capital|relative TSR|total shareholder return|TSR|R&D|"
                    r"innovation|launch|approval|margin|net income|operating margin|diversity|ESG|quality)", re.I)
PLAN = re.compile(r"annual (cash )?incentive|annual bonus|short[- ]term|performance share|PSU|performance unit|"
                  r"long[- ]term incentive|LTI|AIP|MIP|performance award|EIP|incentive plan", re.I)
WEIGHT = re.compile(r"\b(\d{1,3}(?:\.\d)?)\s?%")
PAGE = re.compile(r"\[\[page (\d+) \| printed ([^\]]+)\]\]")


def metrics(body, t, year, url):
    rows = []
    parts = PAGE.split(body)
    # parts: [pre, n, printed, text, n, printed, text ...]
    for i in range(1, len(parts), 3):
        n, printed, text = parts[i], parts[i + 1], parts[i + 2]
        if not PLAN.search(text):
            continue
        for ln in text.splitlines():
            ln = ln.strip()
            if 12 < len(ln) < 260 and METRIC.search(ln) and WEIGHT.search(ln):
                w = WEIGHT.findall(ln)
                if all(float(x) <= 100 for x in w):
                    pl = PLAN.search(text)
                    rows.append({"ticker": t, "year": year, "metric_text": ln, "weights_pct": ";".join(w),
                                 "plan_context": pl.group(0), "pdf_page": n, "printed_page": printed, "url": url})
    return rows


def main():
    allrows = []
    for t, cik in ciks().items():
        if t in ("AZN", "NVO"):
            note_gap("secx", t, "proxy", "foreign private issuer, no DEF 14A")
            continue
        _, fs = filings(cik, "2024-01-01")
        for f in [x for x in fs if x["form"] == "DEF 14A"]:
            year = f["filed"][:4]
            url = url_of(cik, f["accession"], f["primary_doc"])
            try:
                raw = sec_get(url)
            except Exception as e:
                note_gap("secx", t, f"proxy {f['accession']}", repr(e))
                continue
            rel = f"companies/{t}/proxy_{year}.md"
            row = save_doc(rel, url, raw, t, "proxy_statement", f)
            body = (OUT / rel).read_text(encoding="utf-8")
            r = metrics(body, t, year, url)
            allrows += r
            print(t, year, row["pages"], len(r), flush=True)
        write_csv("tables/exec_comp_metrics.csv", ["ticker", "year", "metric_text", "weights_pct", "plan_context",
                                                  "pdf_page", "printed_page", "url"], allrows)


main()
