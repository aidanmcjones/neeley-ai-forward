"""Re-run news_mentions queries against GDELT and compare month counts. Args: TICKER:TOPIC ..."""
import csv
import sys
import time
from collections import defaultdict
import requests
from agent.moat.verify.m_qa import ROOT

URL = "https://api.gdeltproject.org/api/v2/doc/doc"
rows = list(csv.DictReader(open(ROOT / "data/moat/tables/news_mentions.csv")))
print("table rows", len(rows), "pairs", sorted({(r["ticker"], r["topic"]) for r in rows}))
for arg in sys.argv[1:]:
    tk, topic = arg.split(":")
    mine = {r["month"]: int(r["article_count"]) for r in rows if r["ticker"] == tk and r["topic"] == topic}
    q = next(r["query"] for r in rows if r["ticker"] == tk and r["topic"] == topic)
    time.sleep(6)
    r = requests.get(URL, params={"query": q + " sourcelang:english", "mode": "timelinevolraw", "format": "json",
                                  "startdatetime": "20230101000000", "enddatetime": "20261016000000"}, timeout=90)
    if not r.text.strip().startswith("{"):
        print(arg, "GDELT error", r.status_code, r.text[:120])
        continue
    by = defaultdict(float)
    tot = defaultdict(float)
    for pt in r.json()["timeline"][0]["data"]:
        by[pt["date"][:6]] += pt["value"]
        tot[pt["date"][:6]] += pt.get("norm", 0)
    diffs = []
    for ym, v in sorted(by.items()):
        m = f"{ym[:4]}-{ym[4:6]}"
        diffs.append((m, mine.get(m), int(v), int(tot[ym])))
    same = sum(1 for d in diffs if d[1] == d[2])
    print(arg, "months", len(diffs), "identical", same, "sample", diffs[:3], diffs[-3:])
