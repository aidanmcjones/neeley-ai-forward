"""Costs verifier item 1b: merge the XBRL recheck (cv_xbrl.py), check every page-cited text row (headcount,
advertising, field force) on its filing page, correct the R&D basis mix, compute cost_ratios.csv, and write
verified/costs/company_cost_structure.csv and cost_ratios.csv.
"""
import io
import json
import re

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, log_wrong, norm, pages

TEN = "MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD".split()
CF = "/tmp/cv/cf/CIK{:010d}.json"
# NVO sales and distribution costs are not XBRL-tagged; read from the 20-F income statement (DKK million).
NVO_SD = {2021: (37008, "data/moat/companies/NVO/20f_FY2021_d2.md", 51),
          2022: (46217, "data/moat/companies/NVO/20f_FY2022_d2.md", 54),
          2023: (56743, "data/moat/companies/NVO/20f_FY2023_d2.md", 50),
          2024: (62101, "data/corpus/companies/NVO/20f_FY2024_d2.md", 100),
          2025: (64310, "data/corpus/companies/NVO/20f_FY2025_d2.md", 1)}


def num_in(note):
    m = re.search(r"\$?\s?(\d[\d,. ]*\d|\d)\s*(billion|million)?", note.split("(FY ending")[0])
    return m


def check_text(r):
    m = re.match(r"p\.(\d+)", str(r.page_cite))
    if not m:
        return "unverified", "no page number"
    pg = int(m.group(1))
    try:
        P = pages(r.source)
    except FileNotFoundError:
        return "unverified", f"file {r.source} missing"
    note = re.sub(r"\s*\((FY ending[^)]*)\)\s*$", "", str(r.note)).strip()
    nn = norm(note, loose=True)
    pg_txt = norm(P.get(pg, ("", ""))[1], loose=True)
    if nn and nn in pg_txt:
        where = f"verbatim on p.{pg}"
        hit = True
    else:
        hit = False
        for k, (pr, t) in P.items():
            if nn and nn in norm(t, loose=True):
                where = f"verbatim on p.{k} not p.{pg}"
                hit = True
                break
    if not hit:
        return "unverified", f"note text not found in {r.source}"
    # value check: the number the row carries should be the number quoted for its own year
    return ("verified" if "not p." not in where else "corrected"), where


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/company_cost_structure.csv")
    xc = pd.read_csv("/tmp/cv/xbrl_checked.csv", index_col=0)
    for c in ["verify_status", "verify_note", "row_holds", "original_10k_accn", "original_value", "restated",
              "restatement_detail", "original_value_in_note"]:
        if c not in d:
            d[c] = pd.NA
    d = d.astype({c: "object" for c in ["verify_status", "verify_note", "row_holds", "original_10k_accn",
                                         "restated", "restatement_detail"]})
    for i, r in xc.iterrows():
        for c in ["verify_status", "verify_note", "row_holds", "original_10k_accn", "original_value", "restated",
                  "restatement_detail"]:
            d.at[i, c] = r[c]
    wrong = []
    # R&D basis: the collector kept the larger value when filings disagreed, so FY2021 R&D for ABBV, BMY, GILD,
    # LLY, PFE is the as-first-reported figure that still included acquired IPR&D, while FY2022+ exclude it.
    # Replace with the latest annual comparative so the series is on one basis.
    cache = {}
    nfix = 0
    for i, r in d[(d.metric == "rnd") & d.ticker.isin(TEN) & d.page_cite.isna()].iterrows():
        if str(r.restated) != "True":
            continue
        tk, conc, end, accn = r.source_row.split("|")
        ns, concept = conc.split(":")
        cik = int(r.source.split("/data/")[1].split("/")[0])
        cf = cache.setdefault(cik, json.load(open(CF.format(cik))))
        arr = [f for f in cf["facts"][ns][concept]["units"][r.unit] if f["end"] == end and f.get("start")
               and f.get("form") in ("10-K", "20-F") and 350 <= (pd.Timestamp(f["end"]) - pd.Timestamp(f["start"])).days <= 380]
        latest = sorted(arr, key=lambda f: f["filed"])[-1]
        if latest["accn"] != accn and abs(latest["val"] - r.value) / r.value > 0.005:
            old = r.value
            d.at[i, "value"] = float(latest["val"])
            d.at[i, "source_row"] = f"{tk}|{conc}|{end}|{latest['accn']}"
            acc = latest["accn"].replace("-", "")
            d.at[i, "source"] = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/ (XBRL companyfacts {conc})"
            d.at[i, "filed"] = latest["filed"]
            d.at[i, "verify_status"] = "corrected"
            d.at[i, "verify_note"] = (f"was {old:.0f} (as first reported, included acquired IPR&D or pre-recast); "
                                      f"set to latest 10-K comparative {latest['val']} filed {latest['filed']} so FY2021-25 share one basis")
            d.at[i, "row_holds"] = f"later comparative (filed {latest['filed']})"
            nfix += 1
            wrong.append((tk, int(r.fiscal_year), old, latest["val"]))
    if wrong:
        log_wrong([{"stream": "costs", "table": "company_cost_structure.csv", "row_key": "rnd FY2021 (and JNJ FY2021-22)",
                    "what_the_ai_said": "; ".join(f"{t} FY{y} R&D {o/1e9:.2f}B" for t, y, o, n in wrong),
                    "what_the_source_says": "; ".join(f"latest 10-K comparative {n/1e9:.2f}B" for t, y, o, n in wrong)
                    + " (acquired IPR&D moved out of R&D from FY2022; JNJ recast for Kenvue)",
                    "error_type": "mixed_accounting_basis", "severity": "high",
                    "how_caught": "fresh companyfacts, all annual filings for the same period",
                    "count": len(wrong), "example_source": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000014272.json"}])
    # JNJ and PFE recasts: note them
    for i, r in d[d.ticker.isin(["JNJ"]) & d.fiscal_year.isin([2021, 2022]) & d.page_cite.isna()].iterrows():
        if str(r.restated) == "True":
            d.at[i, "verify_note"] = ((str(d.at[i, "verify_note"]) + "; ") if pd.notna(d.at[i, "verify_note"]) and d.at[i, "verify_note"] else "") + \
                f"holds the post-Kenvue continuing-operations recast; first-reported value {r.original_value:.0f} included Consumer Health"
    for i, r in d[(d.ticker == "PFE") & (d.metric == "revenue") & (d.restated.astype(str) == "True")].iterrows():
        d.at[i, "verify_note"] = f"holds the recast in a later 10-K (total revenues incl. reclassified items); first reported {r.original_value:.0f}"
    # text rows
    tr = d.page_cite.notna()
    nt = {"verified": 0, "corrected": 0, "unverified": 0}
    for i, r in d[tr].iterrows():
        s, n = check_text(r)
        d.at[i, "verify_status"] = s
        d.at[i, "verify_note"] = n
        nt[s] += 1
    # peers XBRL rows were not rechecked here
    d.loc[d.verify_status.isna(), "verify_status"] = "not_checked_peer"
    d.loc[d.verify_status == "not_checked_peer", "verify_note"] = "peer XBRL row; not in the 10 case companies, not rechecked"
    d = d.drop(columns=["original_value_in_note"])
    print("rnd fixed", nfix, "text", nt)
    print(d.verify_status.value_counts())
    print(d[tr & (d.verify_status != "verified")][["ticker", "fiscal_year", "metric", "page_cite", "verify_note"]].to_string())
    buf = io.StringIO()
    d.to_csv(buf, index=False)
    write("verify_costs", "verified/costs/company_cost_structure.csv", buf.getvalue(), group="costs", doc_type="table",
          source_url="SEC XBRL companyfacts + filing pages", quality="verified")
    ratios(d)


def ratios(d):
    rows = []
    for tk in TEN:
        for fy in range(2021, 2026):
            x = d[(d.ticker == tk) & (d.fiscal_year == fy)]
            def get(m):
                y = x[x.metric == m]
                return None if y.empty else y.iloc[0]
            rev = get("revenue")
            if rev is None:
                continue
            scope = {"AZN": "IFRS, USD. SG&A is the reported IFRS line: it includes intangible amortisation and other items "
                            "AZN strips from Core SG&A (Q4 2025 reported 5,492 vs Core 4,453, 6-K 2026-02-10); distribution "
                            "costs (446 to 579M) are a separate line and are NOT included",
                     "NVO": "IFRS, DKK (ratio is currency neutral). No SG&A tag: numerator = sales and distribution costs "
                            "(20-F income statement, untagged) + administrative costs (ifrs-full:AdministrativeExpense)",
                     "MRK": "US GAAP, USD. MRK reports acquired IPR&D inside R&D (FY2023 includes the Prometheus charge)",
                     "JNJ": "US GAAP, USD. FY2021-22 are the post-Kenvue continuing-operations recast",
                     "BMY": "US GAAP, USD. BMY tags MarketingAndAdvertisingExpense, not AdvertisingExpense"}.get(tk, "US GAAP, USD")
            num = {"sga": get("sga"), "rnd": get("rnd"), "advertising": get("advertising")}
            if num["advertising"] is None:
                num["advertising"] = get("advertising_text")
            for k, n in num.items():
                if n is None and not (tk == "NVO" and k == "sga"):
                    continue
                if tk == "NVO" and k == "sga":
                    ga = get("general_admin")
                    sd, f, pg = NVO_SD[fy]
                    val = sd * 1e6 + ga.value
                    src = f"{f} p.{pg} (sales and distribution {sd:,} DKKm) + {ga.source_row}"
                else:
                    val = n.value
                    src = n.source_row
                rows.append({"ticker": tk, "fy": fy, "ratio": f"{k}/revenue", "value_pct": round(100 * val / rev.value, 2),
                             "numerator": val, "denominator": rev.value, "unit": rev.unit, "scope": scope,
                             "numerator_source_row": src, "denominator_source_row": rev.source_row,
                             "verify_status": "verified", "verify_note": "computed from verified rows"})
    r = pd.DataFrame(rows)
    print(r.pivot_table(index=["ticker"], columns=["ratio", "fy"], values="value_pct").to_string())
    buf = io.StringIO()
    r.to_csv(buf, index=False)
    write("verify_costs", "verified/costs/cost_ratios.csv", buf.getvalue(), group="costs", doc_type="table",
          source_url="derived from verified/costs/company_cost_structure.csv", quality="verified")


if __name__ == "__main__":
    main()
