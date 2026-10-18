import csv
import io
import time
import requests
from agent.moat.common import write, note_gap

TICKERS = "MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD NVS GSK SNY TAK REGN ALNY BBIO RHHBY MCK COR CAH XLV SPY".split()
tok = open("/Users/aidanjones/.config/catalyst-lab/tiingo").read().strip()


def main():
    rows = []
    for t in TICKERS:
        url = f"https://api.tiingo.com/tiingo/daily/{t}/prices"
        r = requests.get(url, params={"startDate": "2020-01-01", "token": tok}, timeout=60)
        if r.status_code != 200:
            note_gap("market", t, "prices_daily", f"tiingo HTTP {r.status_code}")
            print(t, r.status_code)
            continue
        js = r.json()
        for d in js:
            rows.append([t, d["date"][:10], d["adjClose"], d["adjVolume"], f"tiingo:daily/{t}/prices", f"{t}:{d['date'][:10]}"])
        print(t, len(js), flush=True)
        time.sleep(0.5)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ticker", "date", "adj_close", "adj_volume", "source", "source_row"])
    w.writerows(rows)
    write("market", "tables/prices_daily.csv", buf.getvalue(), group="market", doc_type="table",
          source_url="https://api.tiingo.com/tiingo/daily")
    print(len(rows))


main()
