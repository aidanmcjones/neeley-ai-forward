"""Harvest EDGAR FTS hits for deal 8-Ks into data/moat/scratch/deals_hits.jsonl."""
import json, datetime as dt, urllib.parse
from pathlib import Path
import agent.tenk as t
t.MIN_INTERVAL = 0.3
OUTF = Path("data/moat/scratch/deals_hits.jsonl")
OUTF.parent.mkdir(parents=True, exist_ok=True)
QUERIES = [
    '"upfront payment" "license agreement"',
    '"upfront payment" "collaboration agreement"',
    '"upfront" "milestone" "royalties" "exclusive license"',
    '"merger agreement" "per share in cash"',
    '"tender offer" "per share in cash" "acquire"',
    '"asset purchase agreement" "upfront"',
    '"option" "upfront" "exercise" "license"',
    '"royalty purchase agreement"',
]
SICS = {"2833", "2834", "2835", "2836", "8731", "3841", "3826", "6199", "2830"}
seen = set()
if OUTF.exists():
    for l in OUTF.open():
        r = json.loads(l)
        if r.get("done"):
            seen.add((r["q"], r["m"]))


def months():
    d = dt.date(2020, 1, 1)
    while d <= dt.date(2026, 10, 17):
        n = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield d, min(n - dt.timedelta(days=1), dt.date(2026, 10, 17))
        d = n


with OUTF.open("a") as f:
    for qi, q in enumerate(QUERIES):
        for s, e in months():
            if (qi, s.isoformat()) in seen:
                continue
            frm = 0
            kept = 0
            while True:
                u = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q) +
                     f"&forms=8-K&dateRange=custom&startdt={s}&enddt={e}&from={frm}")
                try:
                    j = t.sec_get(u, as_json=True)
                except Exception as ex:
                    print("ERR", u, ex, flush=True)
                    break
                hits = j["hits"]["hits"]
                for h in hits:
                    sr = h["_source"]
                    if not (set(sr.get("sics") or []) & SICS):
                        continue
                    acc, fn = h["_id"].split(":")
                    f.write(json.dumps({"q": qi, "m": s.isoformat(), "acc": acc, "fn": fn, "cik": sr["ciks"][0],
                                        "name": sr["display_names"][0], "date": sr["file_date"],
                                        "sic": sr["sics"][0]}) + "\n")
                    kept += 1
                frm += len(hits)
                if not hits or frm >= j["hits"]["total"]["value"] or frm >= 1000:
                    break
            f.write(json.dumps({"q": qi, "m": s.isoformat(), "done": True, "kept": kept}) + "\n")
            f.flush()
        print("query done", qi, flush=True)
