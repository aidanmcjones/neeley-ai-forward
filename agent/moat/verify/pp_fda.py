"""Pipeline verifier item 4 (partial): every PDUFA/decision quote vs its cited doc and page; ticker attribution of
Drugs@FDA rows. Usage: python -m agent.moat.verify.pp_fda [--write]
"""
import re
import sys
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, norm, pages

f = pd.read_csv("data/moat/tables/fda_calendar.csv")
f["verify_status"] = "unverified"
f["verify_note"] = ""
MON = "January|February|March|April|May|June|July|August|September|October|November|December"


def loose(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", norm(s).lower()).split())


q = f[f.quote.notna()]
for i, r in q.iterrows():
    doc = str(r.doc)
    if not (ROOT / doc).exists():
        f.at[i, "verify_status"], f.at[i, "verify_note"] = "check", "cited doc not on disk"
        continue
    try:
        pg = pages(doc)
        page = int(float(r.page))
    except Exception:
        f.at[i, "verify_status"], f.at[i, "verify_note"] = "check", "page not parseable"
        continue
    txt = loose(pg.get(page, ("", ""))[1]) + " " + loose(pg.get(page + 1, ("", ""))[1])
    ok = loose(r.quote) in txt
    other = None
    if not ok:
        other = next((n for n, (_, t) in pg.items() if loose(r.quote) in loose(t)), None)
    d = pd.to_datetime(r.date, errors="coerce")
    date_ok = False
    if pd.notna(d):
        ql = str(r.quote)
        date_ok = (str(d.year) in ql and (d.strftime("%B") in ql or d.strftime("%b") in ql or
                                          re.search(r"(first|second|third|fourth) quarter|half|mid|end of|early|late", ql, re.I)
                                          is not None)) or d.strftime("%Y-%m-%d") in ql
    if ok and date_ok:
        st, note = "pass", "quote verbatim on cited page; date in quote"
    elif ok:
        st, note = "check", "quote verbatim but date not stated in the quote at that precision"
    elif other:
        st, note = "page_wrong", f"quote verbatim on page {other}, not {page}"
    else:
        st, note = "fail", "quote not found in cited doc"
    f.at[i, "verify_status"], f.at[i, "verify_note"] = st, note
print(f.loc[q.index].verify_status.value_counts().to_dict())
print(f.loc[q.index][f.loc[q.index].verify_status != "pass"][["ticker", "drug", "date", "verify_note"]].head(25).to_string())
# Drugs@FDA rows: the ticker comes from the case-company match; flag rows where the sponsor is clearly someone else
SPON = {"MRK": r"merck|msd|organon", "PFE": r"pfizer|wyeth|hospira|seagen|arena|pharmacia", "LLY": r"lilly",
        "BMY": r"bristol|celgene|squibb|karuna|mirati|receptos", "ABBV": r"abbvie|allergan|pharmacyclics",
        "JNJ": r"janssen|johnson|actelion|mcneil|ortho", "AMGN": r"amgen|horizon|immunex|onyx",
        "GILD": r"gilead|kite|immunomedics", "AZN": r"astrazeneca|alexion|medimmune|zeneca", "NVO": r"novo"}
dd = f[f.source_type.str.startswith("Drugs@FDA", na=False)]
mism = [i for i, r in dd.iterrows() if r.ticker in SPON and not re.search(SPON[r.ticker], str(r.sponsor), re.I)]
for i in mism:
    f.at[i, "verify_note"] = f"sponsor {f.at[i, 'sponsor']} is not {f.at[i, 'ticker']}: row tracks an action on the company ingredient or partner product (exposure, not sponsorship)"
    f.at[i, "verify_status"] = "exposure_not_sponsor"
print("Drugs@FDA rows", len(dd), "ticker suspect", len(mism))
print(f.loc[mism][["ticker", "sponsor", "drug"]].drop_duplicates().head(15).to_string())
if "--write" in sys.argv:
    write("verify_pipeline", "verified/pipeline/fda_calendar.csv", f.to_csv(index=False), group="pipeline",
          doc_type="table", quality="verified", source_url="Drugs@FDA; Purple Book; company documents")
