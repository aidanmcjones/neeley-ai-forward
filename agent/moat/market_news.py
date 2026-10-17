import csv
import io
import sys
import time
from collections import defaultdict
import requests
from agent.moat.common import write, note_gap

COMPANY = {"MRK": '"Merck"', "BMY": '"Bristol Myers Squibb"', "PFE": '"Pfizer"', "LLY": '"Eli Lilly"',
           "NVO": '"Novo Nordisk"', "ABBV": '"AbbVie"', "JNJ": '"Johnson & Johnson"', "AZN": '"AstraZeneca"',
           "AMGN": '"Amgen"', "GILD": '"Gilead"'}
TOPIC = {
    "IRA_negotiation": '("Inflation Reduction Act" OR "drug price negotiation" OR "Medicare negotiation")',
    "MFN": '("most favored nation" OR "MFN pricing")',
    "tariff": '(tariff OR tariffs)',
    "gross_to_net_price": '(rebates OR "net price" OR "gross-to-net" OR "price cuts")',
    "inventory_channel": '(destocking OR "inventory" OR wholesaler)',
    "biosimilar_generic": '(biosimilar OR generic OR "loss of exclusivity" OR "patent cliff")',
    "guidance": '(guidance OR outlook)',
    "pipeline": '(pipeline OR "phase 3" OR "clinical trial")',
    "top_products": None,
}
PRODUCTS = {"MRK": "(Keytruda OR Januvia)", "BMY": "(Eliquis OR Opdivo)", "PFE": "(Ibrance OR Vyndaqel)",
            "LLY": "(Mounjaro OR Zepbound)", "NVO": "(Ozempic OR Wegovy)", "ABBV": "(Skyrizi OR Rinvoq)",
            "JNJ": "(Stelara OR Darzalex)", "AZN": "(Tagrisso OR Farxiga)", "AMGN": "(Enbrel OR Repatha)",
            "GILD": "(Biktarvy OR Yeztugo)"}
URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch(q, tries=4):
    for k in range(tries):
        time.sleep(12)
        try:
            r = requests.get(URL, params={"query": q + " sourcelang:english", "mode": "timelinevolraw", "format": "json",
                                          "startdatetime": "20230101000000", "enddatetime": "20261016000000"}, timeout=60)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                return r.json()
            print("retry", r.status_code, r.text[:80].replace("\n", " "), flush=True)
            time.sleep(10 * (k + 1))
        except Exception as e:
            print("err", e, flush=True)
            time.sleep(10)
    return None


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    rows = []
    n = 0
    for tk, name in COMPANY.items():
        for topic, expr in TOPIC.items():
            if n >= limit:
                break
            n += 1
            expr = expr or PRODUCTS[tk]
            q = f"{name} {expr}"
            js = fetch(q)
            if not js or not js.get("timeline"):
                note_gap("market", tk, f"news_mentions {topic}", "GDELT returned no data / rate limited")
                continue
            by = defaultdict(float)
            for pt in js["timeline"][0]["data"]:
                by[pt["date"][:6]] += pt["value"]
            for ym, v in sorted(by.items()):
                rows.append([tk, topic, f"{ym[:4]}-{ym[4:6]}", int(v), q, f"gdelt:doc:timelinevolraw:{tk}:{topic}:{ym}"])
            print(tk, topic, len(by), flush=True)
        dump(rows)
    dump(rows)
    print(len(rows))


def dump(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ticker", "topic", "month", "article_count", "query", "source", "source_row"])
    w.writerows([r[:5] + [URL, r[5]] for r in rows])
    write("market", "tables/news_mentions.csv", buf.getvalue(), group="market", doc_type="table", source_url=URL)


main()
