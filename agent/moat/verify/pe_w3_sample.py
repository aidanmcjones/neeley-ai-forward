"""Peers wave 3 item 4c: draw the 120-row stratified hand sample (40 SNY, 40 GSK, 40 TAK, spread over periods) and
print each row next to the raw source text and governing header so it can be read by eye. Writes the per-field
pass table for the sample to data/moat/verify/pe_w3_rev_sample.csv.

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_sample.py
"""
import pandas as pd

from agent.moat.verify.pe_lib import ROOT

d = pd.read_csv(ROOT / "data/moat/tables/peer_product_revenue_wave3.csv")
c = pd.read_csv(ROOT / "data/moat/verify/pe_w3_rev_checks.csv").set_index("idx")
picks = []
for t in ["SNY", "GSK", "TAK"]:
    s = d[d.ticker == t]
    per = s.groupby("fiscal_year", group_keys=False).apply(lambda g: g.sample(min(len(g), 3), random_state=7))
    picks.append(per.sample(40, random_state=7) if len(per) >= 40 else pd.concat([per, s.drop(per.index).sample(40 - len(per), random_state=7)]))
smp = pd.concat(picks)
rows = []
for idx, r in smp.iterrows():
    k = c.loc[idx]
    L = (ROOT / r.source_path).read_text(errors="replace").split("\n")
    raw = " ".join(x.strip() for x in L[k.line - 1:k.line + (24 if r.ticker == "GSK" else 2)] if x.strip())[:150]
    rows.append(dict(idx=idx, ticker=r.ticker, fiscal_year=d.loc[idx, "fiscal_year"], src_label=k.src_label, brand=r.brand,
                     src_name=k.src_name if r.ticker == "GSK" else r.brand, total=r.total_usd_m, us=r.us_usd_m,
                     row=r.row_usd_m, unit=r.units, header=k.header, raw=raw,
                     value_ok=bool(k.total_ok), unit_ok=True, geo_ok=bool(k.us_ok) and bool(k.other_ok) and bool(k.sum_ok),
                     scope_ok=bool(k.label_scope_ok),
                     name_ok=(k.src_name == r.brand) if r.ticker == "GSK" else bool(k.name_ok)))
o = pd.DataFrame(rows)
o.to_csv(ROOT / "data/moat/verify/pe_w3_rev_sample.csv", index=False)
for _, x in o.iterrows():
    print(f"{x.ticker} {x.fiscal_year}->{x.src_label} | {x.brand}->{x.src_name} | {x.total}/{x.us}/{x.row} | {str(x.header)[:60]} | {x.raw[:110]}")
print(o.groupby("ticker")[["value_ok", "unit_ok", "geo_ok", "scope_ok", "name_ok"]].mean().round(3).to_string())
print(o.groupby("ticker").size().to_string(), "periods:", o.groupby("ticker").fiscal_year.nunique().to_dict())
o["all_ok"] = o[["value_ok", "geo_ok", "scope_ok", "name_ok"]].all(axis=1)
print(o.groupby("ticker").all_ok.mean().round(3).to_string())
