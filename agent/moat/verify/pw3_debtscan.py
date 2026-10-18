"""Wave 3: re-scan the balance sheets the Sonnet worker called no_debt_line, across ALL liabilities
(current and non-current), for borrowing lines. Writes data/moat/verify/pw3_debtscan.csv."""
import re, csv, pandas as pd
from agent.moat.verify.pw3_docs import get, text

d = pd.read_csv("data/moat/tables/target_profiles_filled.csv").drop_duplicates("ticker")
x = d[d.debt_check == "no_debt_line"]
LINE = re.compile(r"(?i)\b(term loans?|loans? payable|notes? payable|convertible (senior )?notes?|senior (secured )?notes?|"
                  r"borrowings?|credit facility|long-term debt|debt, net|debt,? (current|non-?current)|notes?, net|"
                  r"royalt[a-z]* (liabilit|obligation|financing)|sale of future royalties|revenue interest|portion of (long-term )?debt|debt|loans?|financing (arrangement|obligation|liabilit[a-z]*))\b[^|]{0,80}\|[ |​$]*([\d,]+|—|-)")
rows = []
for _, r in x.iterrows():
    url = str(r.debt_source).split("; ")[-1].strip()
    try:
        t = re.sub(r"[ \t\xa0​]+", " ", text(get(url)))
    except Exception as e:
        rows.append({"ticker": r.ticker, "url": url, "hits": f"ERR {e}"}); continue
    flat = re.sub(r"\s*/\s*|\n", " | ", t)
    flat = re.sub(r"(\| ?)+", "| ", flat)
    a = re.search(r"(?i)total current assets", flat)
    start = a.start() if a else 0
    e = re.search(r"(?i)total liabilities and (stockholders|shareholders)", flat[start:])
    region = flat[start: start + (e.start() if e else 6000)]
    hits = sorted({re.sub(r"\s+", " ", m.group(0))[:140] for m in LINE.finditer(region)})
    rows.append({"ticker": r.ticker, "url": url, "region_chars": len(region), "hits": " || ".join(hits)})
    print(r.ticker, len(region), hits[:4], flush=True)
with open("data/moat/verify/pw3_debtscan.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ticker", "url", "region_chars", "hits"]); w.writeheader(); w.writerows(rows)
