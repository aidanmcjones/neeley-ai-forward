import csv
from collections import defaultdict

from agent.moat.common import ROOT

tot = defaultdict(lambda: defaultdict(lambda: [0, 0]))
seen = {}
with open(ROOT / "data/moat/tables/analyst_topics.csv") as f:
    for r in csv.DictReader(f):
        seen[(r["ticker"], r["quarter"])] = int(r["analyst_turns"])
        t = tot[r["ticker"]][r["topic"]]
        t[0] += int(r["turns_with_topic"])
        t[1] += 1 if int(r["turns_with_topic"]) > 0 else 0
for tk in tot:
    n = sum(v for (a, q), v in seen.items() if a == tk)
    q = sum(1 for (a, _) in seen if a == tk and seen[(a, _)] > 0)
    items = sorted(tot[tk].items(), key=lambda kv: -kv[1][0])
    fmt = lambda kv: f"{kv[0]}={kv[1][0]}({kv[1][1]}/{q}q)"
    print(tk, "turns", n, "qtrs", q, "TOP:", ", ".join(fmt(k) for k in items[:5]))
    core = [k for k in items if k[0] in ("IRA_negotiation", "MFN", "tariff", "gross_to_net_price", "inventory_channel", "biosimilar_generic")]
    print("   RARE:", ", ".join(fmt(k) for k in core[-5:]))
