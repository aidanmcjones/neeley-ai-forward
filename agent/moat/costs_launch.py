"""costs stream, table 3: launch and marketing benchmarks (10-K advertising, Open Payments by drug, call quotes)."""
import csv
import io
import json

from agent.moat.common import note_gap, write

COLS = ["datum_type", "ticker", "product", "period", "value", "unit", "speaker", "quote_or_note", "page", "file", "source", "source_row"]
rows = []
for r in csv.DictReader(open("data/moat/tables/company_cost_structure.csv")):
    if r["metric"] in ("advertising_text", "advertising"):
        rows.append({"datum_type": "10-K advertising expense", "ticker": r["ticker"], "product": "company total", "period": f"FY{r['fiscal_year']}",
                     "value": r["value"], "unit": r["unit"], "speaker": "", "quote_or_note": r["note"] or r["concept"], "page": r["page_cite"],
                     "file": r["source"] if r["metric"] == "advertising_text" else "", "source": r["source"], "source_row": r["source_row"]})
    if r["metric"] == "field_force_fte":
        rows.append({"datum_type": "field force size", "ticker": r["ticker"], "product": "company total", "period": f"FY{r['fiscal_year']}", "value": r["value"],
                     "unit": "FTE", "speaker": "", "quote_or_note": r["note"], "page": r["page_cite"], "file": r["source"], "source": r["source"], "source_row": r["source_row"]})
for r in csv.DictReader(open("data/moat/tables/open_payments_by_drug.csv")):
    if r["breakdown"] == "total":
        rows.append({"datum_type": "CMS Open Payments general payments by associated drug", "ticker": "", "product": r["drug"], "period": f"PY{r['program_year']}",
                     "value": r["usd"], "unit": "USD", "speaker": "", "quote_or_note": f"{r['records']} payment records; manufacturer-reported payments to physicians and teaching hospitals tied to this drug (speaker fees, meals, consulting, travel); excludes research and ownership payments; a proxy for HCP promotional spend only",
                     "page": "", "file": "", "source": r["source"], "source_row": r["source_row"]})
for c in json.load(open("data/moat/scratch/costs_calls.json")):
    rows.append({"datum_type": "earnings-call statement on launch / DTC / field force", "ticker": c["ticker"], "product": "", "period": c["quarter"] + " (" + c["call_date"] + ")",
                 "value": "", "unit": "", "speaker": c["speaker"], "quote_or_note": c["quote"], "page": c["page"], "file": c["file"], "source": c["source_url"],
                 "source_row": f"{c['ticker']}|{c['quarter']}|{abs(hash(c['quote'])) % 10**8}"})
# curated 10-K / release statements
for t, per, q, pg, f in [
    ("BMY", "FY2023", "Sotyktu is the key growth driver for BMS and we continue to make further investments to accelerate the launch through direct to consumer advertising and adding field force support", "43", "data/moat/companies/BMY/10k_FY2023.md"),
    ("BMY", "FY2023", "higher advertising and promotion costs resulting from additional new product launches ($121 million)", "54", "data/moat/companies/BMY/10k_FY2023.md"),
]:
    rows.append({"datum_type": "10-K launch investment statement", "ticker": t, "product": "Sotyktu" if "Sotyktu" in q else "new launches", "period": per, "value": "121" if "121" in q else "",
                 "unit": "USD millions" if "121" in q else "", "speaker": "", "quote_or_note": q, "page": pg, "file": f, "source": f, "source_row": f"{t}|{per}|{q[:30]}"})
note_gap("costs", None, "Medicare Part D direct-to-consumer context", "no primary CMS source located in the time box; DTC counts are only visible in company advertising lines")
note_gap("costs", None, "sales-force size per company", "only Novartis (field force FTE) states a count; US peers disclose no rep counts in 10-K Item 1")
buf = io.StringIO()
w = csv.DictWriter(buf, COLS)
w.writeheader()
w.writerows(rows)
write("costs", "tables/launch_and_marketing_benchmarks.csv", buf.getvalue(), group="costs", doc_type="table", source_url="10-K, CMS Open Payments, calls", upload=False)
from collections import Counter
print(len(rows), Counter(r["datum_type"] for r in rows))
