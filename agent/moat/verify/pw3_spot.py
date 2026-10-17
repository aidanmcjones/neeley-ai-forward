"""Wave 3: spot-check Yahoo-priced tickers against a second source (Tiingo if open, else Nasdaq historical API),
2026-10-16 close, tolerance 3%."""
import json, sys, time, requests, pandas as pd
TOK = open("/Users/aidanjones/.config/catalyst-lab/tiingo").read().strip()
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "Accept": "application/json"}
d = pd.read_csv("data/moat/tables/target_profiles_filled.csv")
y = d[d.price_source == "yahoo_chart"].drop_duplicates("ticker")
pick = sys.argv[1:] or list(y.ticker)[:12]
tiingo_open = True
out = []
for tk in pick:
    px = float(y[y.ticker == tk].price.iloc[0])
    pdate = str(y[y.ticker == tk].price_date.iloc[0])
    rec = {"ticker": tk, "yahoo": px, "yahoo_date": pdate}
    if tiingo_open:
        r = requests.get(f"https://api.tiingo.com/tiingo/daily/{tk}/prices",
                         params={"startDate": "2026-10-14", "endDate": "2026-10-16"},
                         headers={"Authorization": f"Token {TOK}"}, timeout=30)
        if r.status_code == 429:
            tiingo_open = False
        elif r.status_code == 200:
            last = [x for x in r.json() if x["date"][:10] == pdate]
            if last:
                rec.update(second=last[0]["close"], second_source="tiingo")
    if "second" not in rec:
        r = requests.get(f"https://api.nasdaq.com/api/quote/{tk}/historical",
                         params={"assetclass": "stocks", "fromdate": "2026-10-14", "todate": "2026-10-16", "limit": 5},
                         headers=UA, timeout=30)
        rows = ((r.json().get("data") or {}).get("tradesTable") or {}).get("rows") or []
        m = {f"{x['date'][6:]}-{x['date'][:2]}-{x['date'][3:5]}": float(x["close"].replace("$", "").replace(",", "")) for x in rows}
        if pdate in m:
            rec.update(second=m[pdate], second_source=f"nasdaq:api/quote/{tk}/historical")
        time.sleep(0.5)
    if "second" in rec:
        rec["pct"] = round(100 * (px - rec["second"]) / rec["second"], 3)
        rec["within_3pct"] = abs(rec["pct"]) <= 3
    out.append(rec)
    print(rec, flush=True)
json.dump(out, open("data/moat/verify/pw3_spot.json", "w"), indent=1)
