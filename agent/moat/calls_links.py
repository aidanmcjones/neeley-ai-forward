import re, sys, requests
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
EX = {"MRK": "NYSE", "BMY": "NYSE", "PFE": "NYSE", "LLY": "NYSE", "NVO": "NYSE", "ABBV": "NYSE", "JNJ": "NYSE",
      "AZN": "NASDAQ", "AMGN": "NASDAQ", "GILD": "NASDAQ"}
out = {}
for t, ex in EX.items():
    r = requests.get(f"https://www.marketbeat.com/stocks/{ex}/{t}/earnings/", headers={"User-Agent": UA}, timeout=60)
    links = sorted(set(re.findall(r'/earnings/reports/[0-9\-]+[a-z0-9\-]*/', r.text)))
    print(t, r.status_code, len(links))
    for l in links:
        print("  ", l)
