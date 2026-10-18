"""tables/loe_calendar.csv: one row per company x drug x territory, company-stated LOE next to FDA rule output."""
import io
import re

import pandas as pd

from agent.moat.common import write, note_gap
from agent.stated_loe import load
from agent.tenk import Store

S = Store()
frames = []
for n in ["BMY_PFE_JNJ", "LLY_AMGN_REGN", "MRK_BMY_ABBV"]:
    frames.append(pd.read_csv(io.BytesIO(S.get(f"derived/product_table/{n}.csv"))))
pt = pd.concat(frames).drop_duplicates(["cik", "brand"])
stated = pd.DataFrame(load())


def key(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


NAME2TICK = {14272: "BMY", 78003: "PFE", 200406: "JNJ", 59478: "LLY", 318154: "AMGN", 872589: "REGN",
             310158: "MRK", 1551152: "ABBV", 882095: "GILD", 1860742: "BLCO"}
rows = []
seen = set()
sidx = {}
for _, r in stated.iterrows():
    sidx.setdefault((int(r.cik), key(r["product"])), r)
for _, r in pt.iterrows():
    cik = int(r.cik)
    s = sidx.get((cik, key(r.brand)))
    seen.add((cik, key(r.brand)))
    src = f"R2 derived/product_table/*.csv#{r.brand}"
    jp = s["japan_loe"] if s is not None else None
    base = dict(ticker=r.ticker, company=r.company, cik=cik, brand=r.brand, ingredient=r.ingredient,
                modality=r.modality, revenue_latest_fy=r.revenue_latest_fy)
    rows.append({**base, "territory": "US", "company_stated_loe": r.loe_company_stated,
                 "rule_output_loe": r.loe_fda_estimate, "best_estimate": r.loe_best_estimate,
                 "best_basis": r.loe_basis, "orange_book_last_patent": r.loe_last_listed_patent,
                 "orange_book_substance": r.loe_orange_book_substance,
                 "exclusivity_latest_date": r.exclusivity_latest_date, "purple_book_ref_exclusivity": r.pb_ref_exclusivity,
                 "first_generic_or_biosimilar": r.piv_first_generic_marketing or r.biosimilar_first_approval,
                 "biosimilar_count": r.biosimilar_count, "generic_anda_holders": r.generic_anda_holders_count,
                 "quote": r.loe_company_quote, "source": src, "source_row": f"{cik}:{r.brand}:US"})
    rows.append({**base, "territory": "EU", "company_stated_loe": r.loe_eu_stated, "best_estimate": r.loe_eu_stated,
                 "best_basis": "company stated", "quote": r.loe_company_quote, "source": src,
                 "source_row": f"{cik}:{r.brand}:EU"})
    rows.append({**base, "territory": "Japan", "company_stated_loe": jp, "best_estimate": jp,
                 "best_basis": "company stated" if jp else None,
                 "quote": s["quote"] if s is not None else None,
                 "source": s["source_url"] if s is not None else src, "source_row": f"{cik}:{r.brand}:JP"})
for _, s in stated.iterrows():
    k = (int(s.cik), key(s["product"]))
    if k in seen:
        continue
    seen.add(k)
    base = dict(ticker=NAME2TICK.get(int(s.cik)), company=s.company, cik=int(s.cik), brand=s["product"],
                ingredient=s.ingredient)
    for terr, col in [("US", "us_loe"), ("EU", "eu_loe"), ("Japan", "japan_loe")]:
        rows.append({**base, "territory": terr, "company_stated_loe": s[col], "best_estimate": s[col],
                     "best_basis": "company stated: " + str(s.basis), "quote": s.quote, "source": s.source_url,
                     "source_row": f"{int(s.cik)}:{s['product']}:{terr}"})
df = pd.DataFrame(rows)
df = df[df.company_stated_loe.notna() | df.best_estimate.notna() | (df.territory == "US")]
write("pipeline", "tables/loe_calendar.csv", df.to_csv(index=False), group="pipeline", doc_type="table",
      source_url="R2 derived/company_stated_loe.jsonl + derived/product_table")
print(len(df), df.brand.nunique(), df.territory.value_counts().to_dict())
note_gap("pipeline", "GILD/AZN/NVO", "loe_calendar", "product_table covers 9 companies; NVO, AZN, GSK, SNY, TAK have no stated-LOE rows")
