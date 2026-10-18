"""Per-drug gross-to-net exposure summary for the case-appendix drugs (agent/drug_pack.DRUGS)."""
from pathlib import Path

import numpy as np
import pandas as pd

from agent.drug_pack import DRUGS

V = Path("data/moat/verified/pricing")
g = pd.read_csv(V / "gtn_proxy.csv")
wac = pd.read_csv("data/moat/tables/wac_increases.csv", dtype={"ndc_raw": str})
wac["amt"] = pd.to_numeric(wac.wac_increase_amount, errors="coerce")
wac["after"] = pd.to_numeric(wac.wac_after_increase, errors="coerce")
wac["bad"] = wac.source.str.contains("2020-prescription")  # 2020 HCAI file columns shifted (year in amount column)
wac["d"] = pd.to_datetime(wac.wac_effective_date, errors="coerce")
IPAY_SEL = {2026: "2023-08-29", 2027: "2025-01-17", 2028: "2026-01 (IPAY 2028 list)"}


def pct(a, b):
    return None if a is None or b is None or pd.isna(a) or pd.isna(b) or a == 0 else round(100 * (b / a - 1), 1)


def series(d, col, lo=2020):
    s = d[["year", col]].dropna()
    s = s[s.year >= lo]
    if len(s) < 2:
        return None
    a, b = s.iloc[0], s.iloc[-1]
    return int(a.year), int(b.year), a[col], b[col]


def wac_summary(slug):
    w = wac[(wac.drug == slug) & (wac.d >= "2019-01-01")]
    if not len(w):
        return 0, None, None, ""
    ev = w.drop_duplicates(["d"]).shape[0]  # distinct increase dates across NDCs
    top = w.ndc_raw.value_counts().index[0]
    x = w[w.ndc_raw == top].sort_values("d")
    good = x[~x.bad & x.amt.notna() & x.after.notna()]
    cum = None
    if len(good):
        first, last = good.iloc[0], good.iloc[-1]
        cum = round(100 * (last.after / (first.after - first.amt) - 1), 1)
        span = f"{first.d.date()}..{last.d.date()}"
    else:
        span = ""
    note = f"NDC {top}: {len(x)} increases {span}; cumulative = last WAC after / WAC before first valid increase"
    if x.bad.any():
        note += "; 2020 HCAI rows have shifted columns, amounts unusable but endpoints bracket them"
    return ev, cum, top, note


nad = pd.read_csv("data/moat/tables/nadac_history.csv", dtype={"ndc": str})
nad = nad[nad.match_kind == "brand"].copy()
nad["y"] = nad.as_of_date.str[:4].astype(int)
nad["p"] = pd.to_numeric(nad.nadac_per_unit, errors="coerce")
NP = nad.groupby(["drug", "ndc", "y"]).agg(p=("p", "mean"), unit=("pricing_unit", "first"), desc=("ndc_description", "first")).reset_index()


def same_ndc(slug):
    """Fixed-basket list-like trend: each NDC's mean NADAC in the latest year vs the earliest year >= 2020 it shares with the latest."""
    x = NP[(NP.drug == slug) & (NP.y >= 2020)]
    if not len(x):
        return None
    y1 = x.y.max()
    last = x[x.y == y1].set_index("ndc")
    for y0 in sorted(x.y.unique()):
        if y0 == y1:
            return None
        first = x[x.y == y0].set_index("ndc")
        j = first.join(last, rsuffix="_1", how="inner")
        if len(j):
            chg = (j.p_1 / j.p - 1).median()
            return int(y0), int(y1), float(chg), len(j), "/".join(sorted(j.unit.unique())), j.desc.iloc[0]
    return None


rows = []
for slug, (name, _, ingr, co) in DRUGS.items():
    d = g[g.drug == slug].sort_values("year")
    r = {"drug": slug, "company": co}
    src = []
    # list-like
    s = same_ndc(slug)
    if s:
        y0, y1, chg, k, unit, ex = s
        r["list_like_series"] = f"NADAC same-NDC change, median of {k} NDCs (per {unit}; e.g. {ex})"
        r["list_like_from"], r["list_like_to"] = y0, y1
        r["list_like_start"], r["list_like_end"] = 100.0, 100.0 * (1 + chg)
        src.append("nadac_history.csv")
    else:
        upc = d.dropna(subset=["partd_units_per_claim"])
        drift = len(upc) > 1 and abs(upc.partd_units_per_claim.iloc[-1] / upc.partd_units_per_claim.iloc[0] - 1) > 0.15
        col = "partd_spend_per_claim" if drift else "partd_spend_per_unit"
        s = series(d, col)
        if s:
            r["list_like_series"] = "Part D gross spend per claim (units/claim drifted >15%)" if drift else "Part D gross spend per dosage unit"
            r["list_like_from"], r["list_like_to"], r["list_like_start"], r["list_like_end"] = s
            src.append("partd_by_year.csv")
    if s:
        r["list_like_pct"] = pct(r["list_like_start"], r["list_like_end"])
    # net-like
    sa = series(d[d.get("asp_quarters", pd.Series(dtype=float)).fillna(0) >= 1], "asp_payment_limit_per_hcpcs_unit") if "asp_hcpcs" in d else None
    if sa:
        r["net_like_series"] = f"Part B ASP payment limit per HCPCS unit {d.asp_hcpcs.dropna().iloc[0]}"
        r["net_like_from"], r["net_like_to"], r["net_like_start"], r["net_like_end"] = sa
        r["net_like_pct"] = pct(sa[2], sa[3])
        src.append("partb_asp_quarterly.csv")
    m = d.dropna(subset=["ira_mfp_per_30day"]) if "ira_mfp_per_30day" in d else d.iloc[0:0]
    p = Path(f"data/corpus/drugs/{slug}/ira_negotiation.csv")
    if p.exists():
        ipay = int(pd.read_csv(p, dtype=str).IPAY.iloc[0])
        r["ira_ipay"] = ipay
        r["ira_mfp_effective"] = f"{ipay}-01-01"
        src.append(str(p))
        if len(m):
            mr = m.iloc[0]
            r["ira_mfp_per_30day"] = mr.ira_mfp_per_30day
            if not pd.isna(mr.get("nadac_vs_mfp_ndc_matched_median")):
                r["nadac_vs_mfp_ndc_matched"] = round(mr.nadac_vs_mfp_ndc_matched_median, 2)
                r["mfp_discount_vs_nadac_pct"] = round(100 * (1 - 1 / mr.nadac_vs_mfp_ndc_matched_median), 1)
                if not sa:
                    r["net_like_series"] = f"IRA MFP {ipay} vs NADAC {int(mr.nadac_year_for_mfp)} same NDC-9"
        else:
            r["ira_status_note"] = "selected; MFP not yet published" if ipay >= 2028 else ""
        if slug == "stelara":
            r["ira_status_note"] = "IPAY 2026 MFP in force 2026; CMS lists all NDCs deselected with MFP end 2026-12-31 (biosimilars)"
    else:
        r["ira_ipay"] = ""
    ev, cum, top, note = wac_summary(slug)
    r["wac_increase_events_since_2019"] = ev
    r["wac_cum_pct_since_2019"] = cum
    r["wac_note"] = note
    if ev:
        src.append("wac_increases.csv (California HCAI)")
    if slug == "stelara":
        r["asp_vs_nadac_per_mg_2024"] = round(float(d[d.year == 2024].asp_vs_nadac_per_mg.iloc[0]), 3)
    r["sources"] = "; ".join(src)
    rows.append(r)

df = pd.DataFrame(rows)


def call(r):
    lp, npct = r.get("list_like_pct"), r.get("net_like_pct")
    bits = []
    if pd.notna(lp) and pd.notna(npct):
        gap = lp - npct
        bits.append(f"list-like {lp:+.0f}% vs net-like {npct:+.0f}%: gap {'widening' if gap > 10 else 'narrowing' if gap < -10 else 'stable'}")
    elif pd.notna(lp):
        bits.append(f"list-like {lp:+.0f}% ({int(r.list_like_from)}-{int(r.list_like_to)}); no free net series")
    if pd.notna(r.get("mfp_discount_vs_nadac_pct")):
        bits.append(f"MFP {r.mfp_discount_vs_nadac_pct:.0f}% below NADAC on same NDC")
    elif r.get("ira_ipay") == 2028:
        bits.append("IPAY 2028 selected, MFP pending")
    if r.get("wac_increase_events_since_2019"):
        bits.append(f"{int(r.wac_increase_events_since_2019)} HCAI WAC increases" + (f", cum {r.wac_cum_pct_since_2019:+.0f}%" if pd.notna(r.wac_cum_pct_since_2019) else ""))
    return "; ".join(bits) if bits else "no free price series"


def conf(r):
    if pd.notna(r.get("nadac_vs_mfp_ndc_matched")) or (str(r.get("list_like_series")).startswith("NADAC") and pd.notna(r.get("net_like_pct"))):
        return "high"
    if pd.notna(r.get("list_like_pct")) and "per claim" in str(r.get("list_like_series")):
        return "low"
    if pd.notna(r.get("list_like_pct")):
        return "medium"
    return "low"


df["exposure_call"] = df.apply(call, axis=1)
df["confidence"] = df.apply(conf, axis=1)
df.to_csv(V / "gtn_exposure.csv", index=False)
pd.set_option("display.width", 250, "display.max_colwidth", 120, "display.max_rows", 100)
print(df[["drug", "list_like_series", "list_like_from", "list_like_to", "list_like_pct", "net_like_series", "net_like_pct", "ira_ipay", "nadac_vs_mfp_ndc_matched",
          "wac_increase_events_since_2019", "wac_cum_pct_since_2019", "confidence"]].to_string())
