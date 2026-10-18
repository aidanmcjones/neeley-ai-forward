"""Draw the stratified verification sample of deal_comps and run mechanical quote/number checks on each row.
Writes data/moat/verify/deals_work/sample.jsonl (one row per sampled deal with page context for hand review)."""
import json
import re

import pandas as pd

from agent.moat.verify.dv_lib import WORK, OUT, load, norm, source_text, amt_set, has_amt, isnum

d = load()
b = pd.read_csv(OUT / "tables" / "deal_benchmarks.csv")
small = set(x for r in b[b.n < 10].row_ids for x in r.split())
pick = {}


def add(ids, why):
    for i in ids:
        pick.setdefault(i, []).append(why)


add(d[d.origin.str.contains("own_8k")].deal_id, "own_8k")
for conf, n in (("high", 60), ("medium", 60), ("low:role", 60)):
    add(d[d.confidence == conf].sample(n, random_state=17).deal_id, conf)
add(d[d.confidence == "medium:role"].deal_id, "medium:role")
rest10k = d[(d.origin == "10k_note") & ~d.deal_id.isin(pick)]
add(rest10k.sample(40, random_state=17).deal_id, "10k")
add(sorted(small), "bench_n_lt_10")
# every acquisition row with price-to-revenue goes to pr_checks separately; also include them here
pr = b[b.metric == "price_to_trailing_revenue_x"].row_ids.iloc[0].split()
add(pr, "pr24")

out = []
for _, r in d[d.deal_id.isin(pick)].iterrows():
    try:
        page, doc, loc = source_text(r)
    except Exception as e:
        page, doc, loc = "", "", f"ERR {e}"
    q = norm(r["quote"])
    pn = norm(page)
    qok = bool(q) and q in pn
    qdoc = bool(q) and q in norm(doc)
    pv, dv = amt_set(page), amt_set(doc)
    chk = {}
    for f in ("upfront_usd_m", "milestones_usd_m", "total_potential_usd_m"):
        v = r[f]
        if not isnum(v):
            chk[f] = "blank"
        elif has_amt(pv, float(v)):
            chk[f] = "on_page"
        elif has_amt(dv, float(v)):
            chk[f] = "in_doc"
        elif f == "total_potential_usd_m" and isnum(r["upfront_usd_m"]) and isnum(r["milestones_usd_m"]) and abs(float(v) - float(r["upfront_usd_m"]) - float(r["milestones_usd_m"])) < 0.6:
            chk[f] = "derived_sum"
        else:
            chk[f] = "not_found"
    # context: 1200 chars around the quote on the page
    i = pn.find(q[:80]) if q else -1
    ctx = pn[max(0, i - 500): i + 900] if i >= 0 else pn[:1400]
    out.append(dict(deal_id=r["deal_id"], why=pick[r["deal_id"]], loc=loc, quote_on_page=qok, quote_in_doc=qdoc, num=chk,
                    row={k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items() if k not in ("source",)}, ctx=ctx))
with open(WORK / "sample.jsonl", "w") as f:
    for o in out:
        f.write(json.dumps(o) + "\n")
s = pd.DataFrame([dict(id=o["deal_id"], q=o["quote_on_page"], qd=o["quote_in_doc"], **o["num"]) for o in out])
print(len(out), "sampled")
print("quote on page", s.q.mean(), "in doc", s.qd.mean())
for f in ("upfront_usd_m", "milestones_usd_m", "total_potential_usd_m"):
    print(f, s[f].value_counts().to_dict())
