"""Append distinct market/ibes collector error types to data/moat/verify/ai_wrong.jsonl."""
import csv
import json
from agent.moat.verify.m_qa import ROOT

V = list(csv.DictReader(open(ROOT / "data/moat/verified/market/analyst_topics.csv")))
C = {(r["ticker"], r["quarter"], r["topic"]): r for r in csv.DictReader(open(ROOT / "data/moat/tables/analyst_topics.csv"))}


def flips(topic, direction):
    out = []
    for r in V:
        c = C.get((r["ticker"], r["quarter"], r["topic"]))
        if not c or r["topic"] != topic:
            continue
        a, b = int(c["turns_with_topic"]), int(r["turns_with_topic"])
        if (direction == "fp" and a > 0 and b == 0) or (direction == "fn" and a == 0 and b > 0):
            out.append((r, c))
    return out


fp_inv = flips("inventory_channel", "fp")
fp_top = flips("top_products", "fp")
fn_all = [x for t in ["IRA_negotiation", "MFN", "tariff", "gross_to_net_price", "inventory_channel", "biosimilar_generic", "pipeline", "guidance", "top_products"]
          for x in flips(t, "fn")]
low = [(k, r) for k, r in C.items() if k[2] == "MFN" and int(r["analyst_turns"]) < 3]
ex_low = low[0][1]
vrow = next(r for r in V if (r["ticker"], r["quarter"], r["topic"]) == low[0][0])
E = [
    {"stream": "market", "table": "analyst_topics",
     "what_the_ai_said": f"{len(low)} company-quarters have fewer than 3 analyst turns (e.g. {ex_low['ticker']} {ex_low['quarter']}: {ex_low['analyst_turns']} analyst turns)",
     "what_the_source_says": f"the transcripts contain full Q&A sessions; verified parse finds {vrow['analyst_turns']} analyst question turns for {vrow['ticker']} {vrow['quarter']}",
     "how_caught": "layout-specific re-parse (roic initials, benzinga labels, allmind position rules) and operator-introduction counts",
     "count": len(low), "example_source": ex_low["source"]},
    {"stream": "market", "table": "analyst_topics",
     "what_the_ai_said": "topic absent (0 analyst turns) for cells where analysts did ask, because questions were attributed to executives or never parsed",
     "what_the_source_says": f"e.g. {fn_all[0][0]['ticker']} {fn_all[0][0]['quarter']} {fn_all[0][0]['topic']}: {fn_all[0][0]['example_speaker']} asked: {fn_all[0][0]['example_quote'][:160]}",
     "how_caught": "rebuilt analyst/executive separation from operator introductions, labels and cross-quarter roster; spot-read calls",
     "count": len(fn_all), "example_source": f"{fn_all[0][0]['example_file']} line {fn_all[0][0]['example_line']}"},
    {"stream": "market", "table": "analyst_topics",
     "what_the_ai_said": "inventory_channel questions counted from the bare word 'channel' (DTC channel, LillyDirect channel, channel checks)",
     "what_the_source_says": "those questions are about distribution or access, not inventory or stocking; verified pattern requires inventory/stocking/wholesaler/channel-inventory terms",
     "how_caught": "read matched terms per cell (matched_terms column)", "count": len(fp_inv),
     "example_source": fp_inv[0][1]["example_file"] + " line " + fp_inv[0][1]["source_row"] if fp_inv else ""},
    {"stream": "market", "table": "analyst_topics",
     "what_the_ai_said": "top_products counted any big-pharma brand name (one shared list), so competitor brands (e.g. Ozempic on a Lilly call) count as questions on the company's own top products",
     "what_the_source_says": "company-specific product lists change the cell; e.g. questions naming only competitor brands are not about the company's products",
     "how_caught": "per-company product lists from the 10-K segment tables", "count": len(fp_top),
     "example_source": fp_top[0][1]["example_file"] + " line " + fp_top[0][1]["source_row"] if fp_top else ""},
    {"stream": "market", "table": "analyst_topics",
     "what_the_ai_said": "coverage is the 39 company-quarters in data/corpus (2025Q3 to 2026Q2)",
     "what_the_source_says": "101 company-quarters are available once data/moat/companies/*/transcripts (2024Q1 to 2025Q3) are included; 'never asked' claims need the longer window",
     "how_caught": "file inventory", "count": 62, "example_source": "data/moat/companies/AMGN/transcripts/2024Q1_transcript.md"},
    {"stream": "market", "table": "event_returns",
     "what_the_ai_said": "377 events, one row per manifest document",
     "what_the_source_says": "113 rows are extra exhibits or cover 8-Ks of the same filing (same ticker, filed date, form): 264 distinct events; counting them separately overweights those dates",
     "how_caught": "grouped by ticker+filed+form; recomputed 30 random events from prices_daily (30/30 match)", "count": 113,
     "example_source": "data/moat/tables/event_returns.csv (e.g. ABBV 2026-07-31 8-K and its exhibit 99.1)"},
    {"stream": "ibes", "table": "ibes_eps_consensus",
     "what_the_ai_said": "AZN consensus pulled under IBES tickers AZN and ZEN together",
     "what_the_source_says": "ZEN is per-ADR (FY2025 EPS 4.57 USD, last snapshot 2026-02-19, FY1=2025) while AZN is per ordinary share (FY2026 EPS 10.31); an ADR is half a share, so mixing the series doubles or halves EPS",
     "how_caught": "per-ticker FY1 check vs AZN core EPS history; revenue is unaffected", "count": 1,
     "example_source": "data/moat/tables/ibes_eps_consensus.csv ticker=ZEN"},
]
with open(ROOT / "data/moat/verify/ai_wrong.jsonl", "a") as f:
    for e in E:
        f.write(json.dumps(e) + "\n")
for e in E:
    print(e["table"], e["count"], e["what_the_ai_said"][:90])
