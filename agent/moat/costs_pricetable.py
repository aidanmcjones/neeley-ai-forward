"""costs stream, table 4: precedent pricing moves with disclosed effect. Each row: verbatim quote located by anchor in a page-marked file."""
import csv
import io
import re

from agent.moat.common import note_gap, write

PAGE = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")
C = "data/corpus/companies/"
M = "data/moat/companies/"
# (company, product, move_type, move_date, magnitude, effect_kind, file, anchor, width_before, width_after)
SPEC = [
 ("LLY", "Humalog/Humulin/insulins", "list price cut", "2023-03-01", "70% off insulin list prices; $35/month patient cap", "company statement (call)",
  M + "LLY/transcripts/2025Q2_transcript.md", "reducing list prices by 70%", 200, 200),
 ("LLY", "insulins", "list price cut (citation)", "2023-03-01", "Lilly news release 'Lilly Cuts Insulin Prices by 70% and Caps Patient Insulin Out-of-Pocket Costs at $35 Per Month (Mar. 1, 2023)'", "release cited in proxy",
  M + "LLY/proxy_2024.md", "Lilly Cuts Insulin Prices by 70%", 100, 200),
 ("NVO", "US insulin portfolio", "list price cut (disclosed realized net/list change)", "2023", "US insulin list price change avg 0.1% (2023), net price change avg -24.4% (2023), -19.5% (2022), -10.9% (2021)", "20-F table",
  M + "NVO/20f_FY2023_d2.md", "US insulin portfolio List price change", 100, 300),
 ("NVO", "insulins", "list price cut", "2024-01-01", "reduced insulin list prices cited as a driver of lower operating cash flow in Q1 2024", "company statement (6-K)",
  M + "NVO/6k/2024-05-02_0001628280-24-019781.md", "combined with reduced insulin list prices", 300, 200),
 ("NVO", "Wegovy/Ozempic/Rybelsus", "list price cut", "2027-01-01 (announced 2026-02-24)", "WAC lowered to $675/month; about 50% (Wegovy) and 35% (Ozempic) below current list; direct-to-patient self-pay prices unchanged", "company release",
  C + "NVO/policy/press_2026-02-24_us_list_price_reduction.md", "will lower the list price, or wholesale acquisition cost", 100, 500),
 ("MRK", "Januvia/Janumet", "list price cut aligned to net", "2025-01-01", "list price lowered to align with net; lower Medicaid rebates; higher realized net price", "10-K statement",
  C + "MRK/10k_FY2024.md", "In early 2025, Merck lowered the list price", 400, 400),
 ("MRK", "Januvia/Janumet", "list price cut: realized effect", "FY2025", "Januvia/Janumet sales +12% to $2,544M (2025) vs $2,268M (2024, -33%), primarily higher net pricing in the U.S.", "10-K statement (revenue effect)",
  C + "MRK/10k_FY2025.md", "grew 12% in 2025 primarily due to higher net pricing", 200, 200),
 ("MRK", "Januvia/Janumet", "list price cut: guidance on effect", "Q1 2025 call", "CFO: lower list prices reduced Medicaid rebates, so higher net sales expected for these products in 2025", "call quote",
  M + "MRK/transcripts/2025Q1_transcript.md", "we lowered the list prices for the Januvia family", 150, 350),
 ("MRK", "Januvia/Janumet", "direct-to-patient cash price", "2025-12-19", "cash price approximately 70% off current list price through direct-to-patient program (MFN agreement)", "company release",
  C + "MRK/policy/press_2025-12-19_mfn_agreement.md", "approximately 70% off of the current list price", 200, 200),
 ("BMY/PFE", "Eliquis", "direct-to-patient option", "2025-09-08", "eligible US patients pay more than 40% below list price via Eliquis 360 Support", "company release",
  C + "BMY/policy/press_2025-07-17_eliquis-direct-to-patient.md", "more than 40% less than the current list price", 250, 200),
 ("BMY/PFE", "Eliquis", "Cost Plus Drugs channel", "2026-04-27", "Eliquis on CostPlusDrugs.com at $345 for a 30-day supply for cash-paying patients", "company release",
  C + "BMY/earnings/2026-04-30_a2026q1ex991.md", "collaboration with Mark Cuban Cost Plus Drug Company", 100, 350),
 ("BMY", "Eliquis", "list price reduction: cash-flow effect", "Q1 2026", "$1.2 billion lower net cash collections from Eliquis list price reductions in Q1 2026, expected to be more than offset by lower rebate payments later in the year", "call quote",
  C + "BMY/transcripts/2026Q1_transcript.md", "This quarter's cash flow reflects roughly $1.2 billion", 50, 400),
 ("BMY", "Sotyktu, Zeposia, Reyataz, Baraclude, Orencia SC", "direct-to-patient cash price", "2025-12-19", "approximately 80% off current list prices for cash-paying patients (MFN agreement)", "company release",
  C + "BMY/policy/press_2025-12-19_us-government-agreement.md", "making these important medicines available at discounts approximately 80% off", 300, 100),
 ("AMGN", "Repatha", "direct-to-patient (AmgenNow)", "2025-10-06", "$239/month, nearly 60% below list price", "company release",
  C + "AMGN/policy/press_2025-10-06_amgennow_repatha.md", "at a monthly price of $239", 150, 200),
 ("AMGN", "Repatha and another product", "MFN agreement DTP price", "2025-12-19", "$299/month, nearly 60% and 80% below current US list", "company release",
  C + "AMGN/policy/press_2025-12-19_mfn_agreement.md", "discounted monthly price of $299", 150, 200),
 ("LLY/NVO", "Ozempic, Wegovy, Zepbound, orforglipron", "TrumpRx/MFN direct price", "2025-11-06", "Ozempic/Wegovy from $1,000/$1,350 to $350 per month; Zepbound from $1,086 to average $346; Medicare price $245, $50 copay", "White House fact sheet in company folder",
  C + "LLY/policy/press_2025-11-06_wh_mfn_factsheet.md", "will fall from $1,000 and $1,350 per month", 150, 400),
 ("LLY", "Foundayo (orforglipron)", "launch price, self-pay", "2026-04-09", "from $149/month lowest dose self-pay; commercial copay card $25; Medicare Part D $50 from 2026-07-01", "company release",
  C + "LLY/policy/press_2026-04-09_foundayo_launch_pricing.md", "available starting at $149 per month", 250, 200),
 ("LLY", "Trulicity, Emgality", "direct price vs list", "2025-11-06", "Trulicity $389/month ($598 off list); Emgality $299 per pen ($443 off list)", "White House fact sheet in company folder",
  C + "LLY/policy/press_2025-11-06_wh_mfn_factsheet.md", "Trulicity, a commonly used diabetes medicine, at $389", 150, 150),
 ("AZN", "chronic-disease portfolio", "direct-to-consumer sales", "2025-10-10", "DTC sales at discounts up to 80% off list prices (US government agreement)", "company release",
  C + "AZN/policy/press_2025-10-10_us_government_agreement.md", "Direct-to-Consumer (DTC) sales to eligible patients", 100, 250),
 ("AZN", "Symbicort", "list price reduction (WAC)", "2024-01", "6-K Q1 2024 commentary: US 'Encouraging demand following list price reduction'", "company 6-K",
  M + "AZN/6k/2024-04-25_0001654954-24-004975.md", "Encouraging demand following list price reduction", 300, 200),
 ("AZN", "Farxiga", "authorized generic", "2024-Q1", "AZ launched an authorized generic of Farxiga; US demand strong in Q1 2024", "call quote",
  M + "AZN/transcripts/2024Q1_transcript.md", "benefited from the launch of an authorized generic", 200, 200),
 ("AZN", "Farxiga", "authorized generic: revenue effect", "Q1 2025", "US Farxiga revenue down 90% vs prior year, when revenue benefited from AG launch and stocking", "call quote",
  M + "AZN/transcripts/2025Q1_transcript.md", "Total revenue in the U.S. was down 90%", 150, 250),
 ("AZN", "Symbicort", "authorized generic plus WAC cut", "2024-Q3 call", "strategy to launch an authorized generic as well as lower the US WAC is benefiting AZ; uncertainty about number of generics entering", "call quote",
  M + "AZN/transcripts/2024Q3_transcript.md", "launch an authorized generic as well as lowering our list price", 200, 300),
 ("LLY", "Humalog", "own authorized generics (insulin lispro)", "FY2021", "Humalog US revenue includes Lilly's own insulin lispro authorized generics; no rapid severe decline expected or experienced", "10-K statement",
  M + "LLY/10k_FY2021.md", "Included in the revenue of Humalog in the U.S. are our own insulin lispro authorized generics", 200, 300),
 ("GSK", "Advair, Flovent", "authorized generics ahead of AMP cap removal", "2024", "increased use of authorized generic versions of Advair and Flovent fully offset the headwind from removal of the Medicaid AMP cap", "call quote",
  M + "GSK/transcripts/2024Q4_transcript.md", "increased use of authorized generic versions of Advair and Flovent fully offset", 100, 250),
 ("BMY", "Abraxane", "authorized generic entry: revenue effect", "FY2022", "US revenue -35% in 2022 primarily due to entry of authorized generics and lower demand; AG arrangements include supply sales and profit-sharing fees", "10-K statement",
  M + "BMY/10k_FY2022.md", "entry of authorized generics and lower demand", 200, 250),
 ("GILD", "Epclusa, Harvoni", "own authorized generics via Asegua subsidiary", "ongoing", "sells authorized generics of Epclusa and Harvoni through separate subsidiary Asegua Therapeutics", "10-K statement",
  M + "GILD/10k_FY2023.md", "authorized generic versions of Epclusa and Harvoni in the U.S. through our separate subsidiary", 150, 150),
 ("JNJ", "Sotyktu etc. peer: see policy", "placeholder", "", "", "", "", "", 0, 0),
]
SPEC = [s for s in SPEC if s[2] != "placeholder"]
rows = []
for co, prod, mtype, date, mag, kind, f, anc, wb, wa in SPEC:
    txt = open(f, errors="ignore").read()
    mm = re.search(r"\s+".join(re.escape(w) for w in anc.split()), txt)
    i = mm.start() if mm else -1
    if i < 0:
        note_gap("costs", co, f"pricing anchor not found: {anc[:50]}", f)
        continue
    page = "?"
    for pm in PAGE.finditer(txt[:i]):
        page = pm.group(1)
        printed = pm.group(2) or ""
    quote = " ".join(txt[max(0, i - wb):mm.end() + wa].split())
    rows.append({"company": co, "product": prod, "move_type": mtype, "effective_date": date, "magnitude": mag, "effect_evidence_type": kind,
                 "verbatim_quote": quote, "page": page, "file": f, "source": f, "source_row": f"{co}|{prod}|{mtype}|p{page}"})
note_gap("costs", "BMY/PFE", "Eliquis Cost Plus deal: only the BMS Q1 2026 release (April 2026) found; no volume effect disclosed yet", "no post-launch quarter in corpus")
note_gap("costs", "LLY/NVO/SNY", "insulin 2023-2024 cuts: primary Lilly/Novo/Sanofi press releases themselves not in corpus; only citations, call quotes and NVO net-price table", "no volume-effect statement in corpus")
note_gap("costs", "PFE", "Pfizer DTC prices in MFN release: PFE policy press files are empty extractions", "corpus extraction empty")
buf = io.StringIO()
w = csv.DictWriter(buf, list(rows[0].keys()))
w.writeheader()
w.writerows(rows)
write("costs", "tables/pricing_move_benchmarks.csv", buf.getvalue(), group="costs", doc_type="table", source_url="company filings, calls, releases", upload=False)
print(len(rows), "of", len(SPEC))
