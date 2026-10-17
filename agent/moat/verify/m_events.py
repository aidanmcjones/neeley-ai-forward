"""Verify event_returns: recompute 30 random events, group exhibits of one filing, add timing notes."""
import bisect
import csv
import io
import random
from collections import defaultdict
from agent.moat.common import write
from agent.moat.verify.m_qa import ROOT

ADR = {"ROCHE": "RHHBY", "Roche": "RHHBY"}
# typical earnings release timing (ET): after close means the day-0 window misses the reaction
AFTER_CLOSE = {"AMGN", "GILD", "REGN", "ALNY", "BBIO"}
PRE_MARKET = {"ABBV", "BMY", "JNJ", "LLY", "MRK", "PFE", "AZN", "NVO", "GSK", "SNY", "NVS", "TAK"}


def main():
    px = defaultdict(dict)
    with open(ROOT / "data/moat/tables/prices_daily.csv") as f:
        for r in csv.DictReader(f):
            px[r["ticker"]][r["date"]] = float(r["adj_close"])
    ds = sorted(px["XLV"])
    ev = list(csv.DictReader(open(ROOT / "data/moat/tables/event_returns.csv")))
    random.seed(20261017)
    sample = set(random.sample(range(len(ev)), 30))
    groups = defaultdict(list)
    for i, r in enumerate(ev):
        groups[(r["ticker"], r["filed"], r["form"])].append(i)
    out, n_ok, n_bad, bad = [], 0, 0, []
    for i, r in enumerate(ev):
        g = groups[(r["ticker"], r["filed"], r["form"])]
        prim = sorted(g, key=lambda k: (("ex" in ev[k]["doc_id"].lower().split(":")[-1]) is False, -len(ev[k]["doc_id"])))
        primary = g[0] if len(g) == 1 else min(g, key=lambda k: ("ex" in ev[k]["doc_id"].split(":")[-1].lower(), ev[k]["doc_id"]))
        check = ""
        if i in sample:
            t = ADR.get(r["ticker"], r["ticker"])
            i0 = bisect.bisect_left(ds, r["filed"])

            def ab(a, b):
                return (px[t][ds[b]] / px[t][ds[a]] - 1) - (px["XLV"][ds[b]] / px["XLV"][ds[a]] - 1)
            calc = (ab(i0 - 1, i0), ab(i0 - 1, i0 + 1), ab(i0 - 2, i0 + 5), px[t][ds[i0]] / px[t][ds[i0 - 1]] - 1)
            got = (float(r["abn_day0"]), float(r["abn_0_to_1"]), float(r["abn_m1_to_5"]), float(r["raw_day0"]))
            okk = all(abs(a - b) < 6e-5 for a, b in zip(calc, got)) and ds[i0] == r["day0_date"]
            n_ok += okk
            n_bad += not okk
            check = "match" if okk else f"MISMATCH calc={[round(x, 5) for x in calc]}"
            if not okk:
                bad.append((r["doc_id"], check))
        tk = r["ticker"]
        timing = ""
        if r["doc_type"] == "earnings_release":
            timing = ("after close typical: use abn_0_to_1 (day-0 return is pre-release)" if tk in AFTER_CLOSE else
                      "pre-market typical: abn_day0 captures reaction" if tk in PRE_MARKET else "timing unknown")
        elif r["form"] in ("10-K", "10-Q", "20-F", "6-K"):
            timing = "filing time not in manifest; periodic reports often follow the earnings release, so reaction may predate filing"
        out.append(list(r.values())[:-2] + [f"{tk}|{r['filed']}|{r['form']}", len(g), "yes" if i == primary else "no",
                                           timing, check, r["source"], r["source_row"]])
    cols = list(ev[0].keys())[:-2] + ["event_group", "docs_in_group", "is_primary", "timing_note", "recompute_check", "source", "source_row"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(out)
    write("verify_market", "verified/market/event_returns.csv", buf.getvalue(), group="market", doc_type="table",
          source_url="data/moat/tables/event_returns.csv + prices_daily.csv", upload=False)
    print("events", len(ev), "groups", len(groups), "multi-doc groups", sum(1 for g in groups.values() if len(g) > 1),
          "dup rows", sum(len(g) - 1 for g in groups.values()), "recompute ok", n_ok, "bad", n_bad, bad[:5])


main()
