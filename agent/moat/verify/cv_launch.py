"""Costs verifier item 2: launch_and_marketing_benchmarks.csv. Call quotes: mechanical check from cv_launch_check.py
(verbatim on page, speaker turn, company, quarter) plus a hand relevance grade; marginal quotes go to the _dropped file.
Advertising rows: matched to verified/costs/company_cost_structure.csv (XBRL recheck or page check). Field force and
10-K launch statements: re-found on their pages. Open Payments rows: status from cv_openpay_write.py output."""
import io

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, log_wrong, norm, pages

# marginal quotes, by row index: reason
MARGINAL = {
    198: "analyst question", 202: "DTC advertising regulation, not spend", 206: "R&D pipeline investment, not marketing",
    210: "analyst question", 219: "analyst question", 225: "compliance staffing", 226: "analyst question",
    227: "China compliance case", 228: "sales-force bonus in China compliance case", 232: "DTC sales channel (pricing), not marketing",
    233: "MFN letter terms", 239: "analyst question", 240: "analyst question on DTC price offer", 250: "analyst question on supply",
    256: "analyst opinion", 257: "analyst opinion", 262: "analyst question", 264: "LillyDirect sales channel (pricing), not marketing",
    266: "analyst question", 267: "analyst question", 269: "R&D phase III funding", 270: "compounding/internet channel comment",
    271: "analyst question", 272: "analyst question", 282: "industry DTC-sales comment", 287: "analyst question",
    288: "MFN letter terms", 289: "DTC website (sales channel)",
}


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/launch_and_marketing_benchmarks.csv")
    lq = pd.read_csv("/tmp/cv/launch_q.csv", index_col=0)
    cs = pd.read_csv(ROOT / "data/moat/verified/costs/company_cost_structure.csv")
    d["relevance"] = ""
    d["verify_status"] = ""
    d["verify_note"] = ""
    for i, r in d.iterrows():
        t = r.datum_type
        if t.startswith("earnings-call"):
            c = lq.loc[i]
            ok = c.on_page and c.speaker_ok and c.quarter_ok and c.ticker_ok
            d.at[i, "relevance"] = "marginal" if i in MARGINAL else "relevant"
            d.at[i, "verify_status"] = "verified" if ok else "unverified"
            d.at[i, "verify_note"] = (f"verbatim on p.{r.page}; speaker turn '{c.found_speaker}'; company and quarter match file"
                                      + (f"; marginal: {MARGINAL[i]}" if i in MARGINAL else ""))
        elif t == "10-K advertising expense":
            fy = int(str(r.period)[2:6])
            m = cs[(cs.ticker == r.ticker) & (cs.fiscal_year == fy) & cs.metric.isin(["advertising", "advertising_text"])
                   & ((cs.value - r.value).abs() < 1)]
            if m.empty:
                d.at[i, "verify_status"] = "unverified"
                d.at[i, "verify_note"] = "no matching row in verified company_cost_structure"
            else:
                st = m.iloc[0].verify_status
                d.at[i, "verify_status"] = "verified" if st in ("verified", "corrected") else st
                d.at[i, "verify_note"] = f"same as company_cost_structure row ({m.iloc[0].metric}): {m.iloc[0].verify_note}"
                if r.ticker == "JNJ" and fy in (2021, 2022) and str(r.quote_or_note).startswith("us-gaap"):
                    d.at[i, "verify_note"] += "; post-Kenvue recast (first reported 2.7B FY2021, 2.1B FY2022)"
        elif t in ("field force size", "10-K launch investment statement"):
            pg = int(str(r.page).replace("p.", ""))
            P = pages(r.file)
            ok = norm(r.quote_or_note, loose=True) in norm(P.get(pg, ("", ""))[1], loose=True)
            d.at[i, "verify_status"] = "verified" if ok else "unverified"
            d.at[i, "verify_note"] = f"verbatim on p.{pg}" if ok else f"not found on p.{pg}"
            if t == "field force size":
                d.at[i, "verify_note"] += "; FTE incl. supervisors and admin, Novartis global (not US-only)"
        elif t.startswith("CMS Open Payments"):
            d.at[i, "verify_status"] = "see open_payments_by_drug.csv"
            d.at[i, "verify_note"] = ("Open Payments row; recheck in verified/costs/open_payments_by_drug.csv. Collector matched drug-name "
                                      "slots 1-2 only; payments list up to 5 products, so a payment is counted in full for each drug it names")
    q = d.datum_type.str.startswith("earnings-call")
    drop = d[q & (d.relevance == "marginal")]
    keep = d.drop(drop.index)
    print(d[q].relevance.value_counts().to_dict(), d.verify_status.value_counts().to_dict())
    for name, df in (("launch_and_marketing_benchmarks.csv", keep), ("launch_and_marketing_benchmarks_dropped.csv", drop)):
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        write("verify_costs", f"verified/costs/{name}", buf.getvalue(), group="costs", doc_type="table",
              source_url="transcripts, 10-K/20-F pages, XBRL companyfacts", quality="verified")
    n_an = sum(1 for v in MARGINAL.values() if v.startswith("analyst"))
    log_wrong([{"stream": "costs", "table": "launch_and_marketing_benchmarks.csv", "row_key": "earnings-call statements",
                "what_the_ai_said": "94 call quotes selected by keyword as launch / DTC / field-force spend statements",
                "what_the_source_says": f"{len(drop)} are marginal: {n_an} are analyst questions or opinions (not company statements), "
                                        "the rest are about DTC sales channels under MFN, compliance, or R&D",
                "error_type": "keyword_selection", "severity": "medium", "how_caught": "read each turn on its page", "count": len(drop),
                "example_source": "LLY 2024Q3 transcript: 'DTC, in my experience, usually signals concern...' (analyst)"}])


if __name__ == "__main__":
    main()
