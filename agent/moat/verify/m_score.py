"""priced_in_scorecard.csv: per company x topic analyst attention, press attention, earnings-day reaction."""
import csv
import io
import statistics as st
from collections import defaultdict
from agent.moat.common import write
from agent.moat.verify.m_qa import ROOT

V = ROOT / "data/moat/verified/market"
UP = True


def qend(q):
    y, n = int(q[:4]), int(q[-1])
    return f"{y}-{['03-31', '06-30', '09-30', '12-31'][n - 1]}"


def nextq_end(q):
    y, n = int(q[:4]), int(q[-1])
    y2, n2 = (y + 1, 1) if n == 4 else (y, n + 1)
    return qend(f"{y2}Q{n2}")


def main():
    at = list(csv.DictReader(open(V / "analyst_topics.csv")))
    ev = [r for r in csv.DictReader(open(V / "event_returns.csv")) if r["is_primary"] == "yes"
          and r["doc_type"] in ("earnings_release", "foreign_current_report")]
    news = list(csv.DictReader(open(ROOT / "data/moat/tables/news_mentions.csv")))
    nz = defaultdict(lambda: [0, 0])
    for r in news:
        nz[(r["ticker"], r["topic"])][0] += int(r["article_count"])
        nz[(r["ticker"], r["topic"])][1] += 1
    # earnings reaction per company-quarter: first primary release filed after quarter end and before next quarter end
    react = {}
    for r in at:
        k = (r["ticker"], r["quarter"])
        if k in react:
            continue
        a, b = qend(r["quarter"]), nextq_end(r["quarter"])
        c = sorted([e for e in ev if e["ticker"] == r["ticker"] and a < e["filed"] <= b and e["doc_type"] == "earnings_release"],
                   key=lambda e: e["filed"])
        if not c:
            c = sorted([e for e in ev if e["ticker"] == r["ticker"] and a < e["filed"] <= b], key=lambda e: e["filed"])
        react[k] = (float(c[0]["abn_0_to_1"]), c[0]["doc_id"]) if c else None
    tot_turns = defaultdict(int)
    for r in at:
        if r["topic"] == "guidance":
            tot_turns[r["ticker"]] += int(r["analyst_turns"])
    agg = defaultdict(lambda: {"q": [], "asked": [], "turns": 0, "askers": 0, "ra": [], "rn": [], "ex": None})
    for r in at:
        a = agg[(r["ticker"], r["topic"])]
        a["q"].append(r["quarter"])
        t = int(r["turns_with_topic"])
        a["turns"] += t
        a["askers"] += int(r["analysts_asking"])
        rc = react.get((r["ticker"], r["quarter"]))
        if t:
            a["asked"].append(r["quarter"])
            if a["ex"] is None or r["quarter"] > a["ex"][0]:
                a["ex"] = (r["quarter"], r["example_speaker"], r["example_quote"][:200], r["example_file"], r["example_line"])
        if rc:
            (a["ra"] if t else a["rn"]).append(rc[0])
    rows = []
    for (tk, topic), a in sorted(agg.items()):
        qs = sorted(a["q"])
        streak = 0
        for q in reversed(qs):
            if q in a["asked"]:
                break
            streak += 1
        share = a["turns"] / tot_turns[tk] if tot_turns[tk] else 0
        n = nz.get((tk, topic))
        mean = lambda xs: round(st.mean(xs), 4) if xs else ""
        absmean = lambda xs: round(st.mean([abs(x) for x in xs]), 4) if xs else ""
        attention = len(a["asked"]) / len(qs)
        tier = "never asked" if not a["asked"] else ("rarely asked" if attention <= 0.2 else ("sometimes" if attention < 0.6 else "routinely asked"))
        ex = a["ex"] or ("", "", "", "", "")
        rows.append([tk, topic, len(qs), f"{qs[0]}..{qs[-1]}", len(a["asked"]), round(attention, 2), a["turns"], round(share, 4),
                     a["askers"], max(a["asked"]) if a["asked"] else "", streak, tier,
                     n[0] if n else "", n[1] if n else "", "GDELT DOC timelinevolraw" if n else "not collected yet (GDELT job incomplete)",
                     len(a["ra"]), mean(a["ra"]), absmean(a["ra"]), len(a["rn"]), mean(a["rn"]), absmean(a["rn"]),
                     ex[0], ex[1], ex[2], ex[3], ex[4],
                     "data/moat/verified/market/analyst_topics.csv; event_returns.csv; data/moat/tables/news_mentions.csv",
                     f"{tk}|{topic}"])
    cols = ["ticker", "topic", "quarters_covered", "quarter_range", "quarters_asked", "share_of_quarters_asked", "analyst_turns_on_topic",
            "share_of_all_analyst_turns", "analyst_asker_count_sum", "last_quarter_asked", "recent_unasked_streak", "analyst_attention_tier",
            "gdelt_articles_total", "gdelt_months", "press_source", "n_earnings_events_topic_asked", "mean_abn_0_to_1_when_asked",
            "mean_abs_abn_0_to_1_when_asked", "n_earnings_events_not_asked", "mean_abn_0_to_1_not_asked", "mean_abs_abn_0_to_1_not_asked",
            "latest_example_quarter", "latest_example_speaker", "latest_example_quote", "latest_example_file", "latest_example_line",
            "source", "source_row"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    write("verify_market", "verified/market/priced_in_scorecard.csv", buf.getvalue(), group="market", doc_type="table",
          source_url="verified analyst_topics + event_returns + GDELT", upload=UP)
    for r in rows:
        if r[11] in ("never asked", "rarely asked"):
            print(r[0], r[1], f"{r[4]}/{r[2]}", r[6], r[11])
    print(len(rows), "rows; react coverage", sum(1 for v in react.values() if v), "/", len(react))


main()
