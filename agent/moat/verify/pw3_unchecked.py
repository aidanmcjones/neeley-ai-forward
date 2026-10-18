"""Wave 3: read the latest periodic filing for the 11 debt-unchecked target tickers; write snippets."""
import json, re, requests
from agent.moat.verify.pw3_docs import get, text, UA

T = {"LKFT": 1421876, "GRFS": 1438569, "LPCN": 1535955, "CANF": 1536196, "IPHA": 1598599, "ASND": 1612042,
     "LTRN": 1763950, "EVAX": 1828253, "MAIA": 1878313, "ANL": 1944552, "ABVX": 1956827}
PATS = [r"Total liabilities", r"Cash and cash equivalents", r"(borrowings|loans? payable|term loan|convertible (senior )?notes|notes payable)",
        r"(ADS|American Depositary Share)s? (each )?represent", r"ordinary shares.{0,40}outstanding", r"shares of common stock outstanding"]
out = open("data/moat/verify/pw3_docs_unchecked.txt", "w")
meta = {}
for tk, cik in T.items():
    s = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
    r = s["filings"]["recent"]
    rows = list(zip(r["form"], r["accessionNumber"], r["primaryDocument"], r["filingDate"], r["reportDate"]))
    pick = [x for x in rows if x[0] in ("10-Q", "10-K", "20-F", "10-KT")][:1]
    six = [x for x in rows if x[0] == "6-K"][:6]
    meta[tk] = {"name": s["name"], "periodic": pick, "sixk": six}
    out.write(f"===== {tk} {s['name']} periodic={pick} 6-K={[(x[1], x[3], x[2]) for x in six]}\n")
    for f, acc, doc, fd, rd in pick:
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
        t = text(get(url))
        out.write(f"## {f} {fd} {url} chars={len(t)}\n")
        for pat in PATS:
            for m in list(re.finditer(pat, t, re.I))[:2]:
                sn = re.sub(r"[\s/|​]+", " ", t[max(0, m.start() - 200): m.end() + 500])
                out.write(f"--- [{pat[:30]}] @{m.start()}: {sn}\n")
    out.flush()
json.dump(meta, open("data/moat/verify/pw3_unchecked_meta.json", "w"), indent=1)
print("done")
