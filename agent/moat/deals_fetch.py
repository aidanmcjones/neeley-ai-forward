"""Fetch deal 8-K documents (main doc + EX-99) for harvested hits; write page-marked md under deals/."""
import json, re, sys
from collections import defaultdict
from pathlib import Path
import agent.tenk as t
t.MIN_INTERVAL = 0.3
from agent.corpus import paged_text, render
from agent.moat.common import write, OUT, header, note_gap

SIC_OK = {"2833", "2834", "2835", "2836", "8731", "2830"}
hits = defaultdict(lambda: {"docs": set()})
for l in open("data/moat/scratch/deals_hits.jsonl"):
    r = json.loads(l)
    if r.get("done") or r["sic"] not in SIC_OK:
        continue
    h = hits[r["acc"]]
    h.update(cik=r["cik"], name=r["name"], date=r["date"], sic=r["sic"])
    h["docs"].add(r["fn"])
    h.setdefault("qs", set()).add(r["q"])


def rank(fn):
    f = fn.lower()
    if re.search(r"ex-?(10|2|3|4|5|21|23|99\.?[2-9])", f) and not re.search(r"ex-?99[-_.]?1", f):
        return 9
    if re.search(r"ex-?99|pressrelease|press", f):
        return 0
    return 1


done = set(p.stem.split("_", 1)[1] for p in (OUT / "deals").glob("*.md")) if (OUT / "deals").exists() else set()
n = 0
for acc, h in sorted(hits.items(), key=lambda kv: kv[1]["date"], reverse=(len(sys.argv) > 1)):
    if acc in done or (OUT / 'deals' / f"{h['date']}_{acc}.md").exists():
        continue
    docs = sorted(h["docs"], key=rank)
    docs = [d for d in docs if rank(d) < 9][:2] or docs[:1]
    pages = []
    urls = []
    cik = int(h["cik"])
    for fn in docs:
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{fn}"
        try:
            raw = t.sec_get(url)
        except Exception as e:
            note_gap("deals", h["name"], url, f"fetch failed {e}")
            continue
        urls.append(url)
        pg = paged_text(raw)
        if len(pg) > 12:
            pg = pg[:12]
        pages.extend(pg)
    if not pages:
        continue
    meta = f"acc={acc} cik={cik} filer={h['name'].split('  ')[0]} filed={h['date']}"
    md = render(pages, header(urls[0], docs="|".join(docs)) + f"<!-- {meta} -->\n")
    write("deals", f"deals/{h['date']}_{acc}.md", md, ticker=None, group="deals", doc_type="8-K+EX99", form="8-K",
          filed=h["date"], source_url=urls[0], pages=len(pages), upload=False)
    n += 1
    if n % 100 == 0:
        print("fetched", n, flush=True)
print("done", n)
