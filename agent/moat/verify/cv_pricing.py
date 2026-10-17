"""Costs verifier item 4: pricing_move_benchmarks.csv. Re-find each verbatim quote on its cited page, check the
number and date against the quote, and add effect_type and disclosed_effect (empty unless the company disclosed one).
Per-row judgements are below (read every quote in full on its page)."""
import io

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import PAGE_RE, ROOT, log_wrong, norm, pages

# row: (effect_type, disclosed_effect, status, note)
J = {
    0: ("list_cut", "", "verified", "70% list cut and $35 cap verbatim (2025Q2 call); the 2023-03-01 date is not in this quote, it comes from the release title in row 1"),
    1: ("list_cut", "", "verified", "release title and date verbatim in proxy footnote p.99; a citation, not a disclosure of effect"),
    2: ("net_price", "US insulin net price change avg -24.4% (2023), -19.5% (2022), -10.9% (2021); list change 0.1%/0.0%/0.0%", "verified",
        "table verbatim p.92; this is realized net price, not a list cut: list prices were flat in 2021-23"),
    3: ("cash_timing", "Q1 2024 free cash flow DKK 5.0bn vs 24.8bn, partly from rebate phasing combined with reduced insulin list prices (not quantified separately)", "verified",
        "quote verbatim p.13; effective date 2024-01-01 is not in the quote (Novo's insulin list cuts took effect 1 Jan 2024); effect is on cash flow timing, not sales"),
    4: ("list_cut", "", "verified", "WAC $675 effective 2027-01-01, ~50% Wegovy / ~35% Ozempic below current list, verbatim; announced 2026-02-24; future move, no effect yet"),
    5: ("net_price", "", "verified", "verbatim 10-K FY2024 p.58: list cut in early 2025 to reduce Medicaid rebates -> higher realized net price; expectation, not a measured effect"),
    6: ("net_price", "Januvia/Janumet worldwide sales $2,544M in 2025, +12%, primarily higher US net pricing incl. a favorable true-up, partly offset by volume declines", "verified",
        "numbers verbatim 10-K FY2025 p.61 ($2,544M +12%; 2024 $2,268M -33%)"),
    7: ("net_price", "", "verified", "CFO guidance verbatim 2025Q1 call p.5: expects higher net sales in 2025 (not quantified)"),
    8: ("dtc_price", "", "verified", "~70% off list cash price via DTP, verbatim MFN release 2025-12-19"),
    9: ("dtc_price", "", "verified", ">40% below list from Sept 8 (2025) verbatim; release dated 2025-07-17"),
    10: ("dtc_price", "", "verified", "$345 per 30-day supply from April 27, 2026 verbatim in Q1 2026 results exhibit p.4"),
    11: ("cash_timing", "about $1.2B lower net cash collections in Q1 2026 from Eliquis list price reductions, expected to be more than offset later in 2026 by lower rebate payments", "verified",
          "transcript reads '$1.2 billion and lower net cash collections' (transcription garble of 'in lower'); number and claim match"),
    12: ("dtc_price", "", "verified", "~80% off list for Sotyktu, Zeposia, Reyataz, Baraclude, Orencia SC, verbatim"),
    13: ("dtc_price", "", "verified", "$239/month, nearly 60% below list, verbatim; AmgenNow launched October 2025"),
    14: ("dtc_price", "", "corrected", "product was 'Repatha and another product': the $299 price (nearly 60% and 80% below list) is for Aimovig and Amjevita; Repatha stays $239 (row 13)"),
    15: ("dtc_price", "", "verified", "TrumpRx prices verbatim in White House fact sheet; a government statement, not a company disclosure"),
    16: ("dtc_price", "", "verified", "$149/month lowest-dose self-pay verbatim; $25 savings card verbatim; launch price, not a cut"),
    17: ("dtc_price", "", "verified", "Trulicity $389 ($598 off list), Emgality $299/pen ($443 off) verbatim in fact sheet"),
    18: ("dtc_price", "", "verified", "up to 80% off list DTC verbatim"),
    19: ("volume", "", "verified", "'Encouraging demand following list price reduction' verbatim in Q1 2024 6-K; effective date 2024-01 is not in the source; demand comment is qualitative"),
    20: ("volume", "", "verified", "verbatim: US Farxiga demand strong, benefited from authorized generic launch (Q1 2024)"),
    21: ("volume", "US Farxiga revenue down 90% vs Q1 2024, when revenue benefited from the authorized generic launch and stocking", "verified",
         "verbatim 2025Q1 call p.6; '90%' refers to Farxiga US revenue per context"),
    22: ("list_cut", "", "verified", "verbatim 2024Q3 call p.22 (Ruud Dobber context); qualitative, no number"),
    23: ("volume", "", "verified", "verbatim LLY 10-K FY2021 p.44; AG revenue is inside Humalog US, not split out"),
    24: ("net_price", "authorized generics of Advair and Flovent fully offset the 2024 headwind from Medicaid AMP cap removal (not quantified)", "verified", "verbatim GSK 2024Q4 call p.7 (David Redfern)"),
    25: ("volume", "Abraxane US revenue -35% in 2022, primarily authorized generic entry and lower demand", "verified", "verbatim BMY 10-K FY2022 p.48"),
    26: ("volume", "", "verified", "verbatim GILD 10-K FY2023 p.58; structural fact, no effect disclosed"),
}


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/pricing_move_benchmarks.csv")
    st, nt, et, de, fq = [], [], [], [], []
    for i, r in d.iterrows():
        P = pages(r.file)
        q = norm(PAGE_RE.sub(" ", r.verbatim_quote), loose=True)
        q_core = q[20:-20]
        pg = int(r.page)
        on = q_core in norm(P.get(pg, ("", ""))[1], loose=True)
        if not on:
            # allow a quote that spans a page break
            on = q_core in norm(P.get(pg, ("", ""))[1] + " " + P.get(pg + 1, ("", ""))[1], loose=True)
        fq.append("on cited page" if on else "NOT on cited page")
        e, x, s, n = J[i]
        if not on:
            s, n = "unverified", "quote not found on cited page; " + n
        et.append(e)
        de.append(x)
        st.append(s)
        nt.append(n)
    d["quote_check"] = fq
    d["effect_type"] = et
    d["disclosed_effect"] = de
    d["verify_status"] = st
    d["verify_note"] = nt
    d.loc[14, "product"] = "Aimovig, Amjevita"
    print(d.quote_check.value_counts(), d.verify_status.value_counts(), d.effect_type.value_counts())
    log_wrong([{"stream": "costs", "table": "pricing_move_benchmarks.csv", "row_key": "AMGN|MFN agreement DTP price (row 14)",
                "what_the_ai_said": "product 'Repatha and another product' at $299/month",
                "what_the_source_says": "the $299 AmgenNow price is for Aimovig and Amjevita; Repatha is $239",
                "error_type": "attribution", "severity": "medium", "how_caught": "read quote on page", "count": 1,
                "example_source": "data/corpus/companies/AMGN/policy/press_2025-12-19_mfn_agreement.md p.1"},
               {"stream": "costs", "table": "pricing_move_benchmarks.csv", "row_key": "NVO|US insulin portfolio (row 2)",
                "what_the_ai_said": "move_type 'list price cut' with net change -24.4% (2023)",
                "what_the_source_says": "US insulin list price change was +0.1% (2023), 0.0%, 0.0%: the -24.4% is realized net price erosion, not a list cut",
                "error_type": "effect_type_conflation", "severity": "medium", "how_caught": "read 20-F table", "count": 1,
                "example_source": "data/moat/companies/NVO/20f_FY2023_d2.md p.92"}])
    buf = io.StringIO()
    d.to_csv(buf, index=False)
    write("verify_costs", "verified/costs/pricing_move_benchmarks.csv", buf.getvalue(), group="costs", doc_type="table",
          source_url="company filings, calls and releases (see file, page)", quality="verified")


if __name__ == "__main__":
    main()
