"""Pipeline verifier item 3, part 2: excerpt checks, hand-called name collisions, verify_status, and the write.

Reads data/moat/verify/pp_cache/targets_recomputed.csv and targets_checks.csv (from pp_targets).
Usage: python -m agent.moat.verify.pp_targets_write [--write]
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import log_wrong
from agent.moat.verify.pp_targets_lib import toks

C = Path("data/moat/verify/pp_cache")
v = pd.read_csv(C / "targets_recomputed.csv")
ck = pd.read_csv(C / "targets_checks.csv")

# hand-checked name collisions (token overlap passes, but the SEC filer is a different business)
COLLIDE = {"PTC": "PTC Inc. (software), not PTC Therapeutics (PTCT)",
           "COMP": "Compass, Inc. (real estate), not Compass Therapeutics (CMPX)",
           "VIK": "Viking Holdings Ltd (cruise line), not Viking Therapeutics (VKTX)",
           "MGIH": "Millennium Group International Holdings (packaging), not Millennium Pharmaceuticals (Takeda subsidiary)"}
PARENT = {"GRFS": "CT.gov sponsor is a Grifols US subsidiary; SEC filer is parent Grifols SA",
          "GPCR": "sponsor is a subsidiary of Structure Therapeutics",
          "NVCR": "sponsor is NovoCure GmbH, filer NovoCure Ltd"}


def sub(cik):
    f = C / "sec" / f"sub_{cik}.json"
    return json.loads(f.read_text()) if f.exists() else {}


def latest_10k(sb):
    rec = sb.get("filings", {}).get("recent", {})
    for i, f in enumerate(rec.get("form", [])):
        if f in ("10-K", "10-K/A", "10-KT", "20-F"):
            return rec["filingDate"][i], f
    return None, None


ex_rows, status = [], []
for i, r in v.iterrows():
    sb = sub(int(r.sponsor_cik))
    lk, lform = latest_10k(sb)
    note = [r.verify_note] if isinstance(r.verify_note, str) and r.verify_note else []
    ex = r.tenk_excerpt
    if isinstance(ex, str) and Path(ex).exists():
        txt = Path(ex).read_text(errors="ignore")
        cik_ok = f"/data/{int(r.sponsor_cik)}/" in txt.split("\n")[0]
        nm = [w for w in toks(r.sec_filer_name) if len(w) > 3]
        name_ok = any(w in txt.lower() for w in nm) if nm else True
        asset_ok = str(r.asset).lower()[:6] in txt.lower()
        is_fin = bool(re.search(r"total current assets|net cash used in operating activities", txt, re.I))
        ex_rows.append(dict(ticker=r.ticker, asset=r.asset, excerpt=ex, cik_in_url=cik_ok, filer_name_in_text=name_ok,
                            asset_in_text=asset_ok, is_financial_statement=is_fin, tenk_filed=r.tenk_filed,
                            latest_annual_filed=lk, latest_annual_form=lform, is_latest=str(r.tenk_filed) == str(lk)))
        if str(r.tenk_filed) != str(lk):
            note.append(f"excerpt 10-K filed {r.tenk_filed} but latest annual filing is {lform} {lk}")
        if not (cik_ok and asset_ok):
            note.append("excerpt does not show filer name or asset")
    if r.ticker in COLLIDE:
        note.append("name collision: " + COLLIDE[r.ticker])
        st = "dropped"
    elif pd.isna(r.price):
        st = "no_price"
    else:
        c = ck.iloc[i]
        st = "pass" if all(c[k] for k in ["cash_ok", "sec_ok", "debt_ok", "burn_ok", "shares_ok", "ev_ok",
                                          "runway_ok"]) else "recomputed"
    if r.ticker in PARENT:
        note.append(PARENT[r.ticker])
    if isinstance(r.debt_concept, str) and r.debt_concept.startswith("stale"):
        note.append("no debt fact within 200 days of the balance sheet: EV assumes zero debt, check the 10-K debt note")
    v.at[i, "verify_note"] = "; ".join(dict.fromkeys(note))
    status.append(st)
v["verify_status"] = status
exr = pd.DataFrame(ex_rows)
exr.to_csv(C / "target_excerpt_checks.csv", index=False)
print(v.verify_status.value_counts().to_dict())
print("excerpts", len(exr), "ok", int((exr.cik_in_url & exr.asset_in_text).sum()),
      "financial statement", int(exr.is_financial_statement.sum()), "latest", int(exr.is_latest.sum()))
print(exr[~(exr.cik_in_url & exr.asset_in_text) | ~exr.is_latest].to_string())
keep, drop = v[v.verify_status != "dropped"], v[v.verify_status == "dropped"]
if "--write" in sys.argv:
    write("verify_pipeline", "verified/pipeline/target_profiles.csv", keep.to_csv(index=False), group="pipeline",
          doc_type="table", quality="verified", source_url="SEC XBRL companyfacts; Tiingo daily; CT.gov")
    write("verify_pipeline", "verified/pipeline/target_profiles_dropped.csv", drop.to_csv(index=False),
          group="pipeline", doc_type="table", quality="rejected", source_url="SEC submissions")
    m = ck.has_mcap
    log_wrong([
        dict(stream="pipeline", table="target_profiles.csv", row_key="debt/securities/cash (latest() helper)",
             what_the_ai_said="current debt e.g. NKTR $133.5M, KPTI $169.3M, ENTA $2.0M; securities e.g. VNDA $382.6M",
             what_the_source_says="each is the newest fact of the FIRST concept that ever had data: NKTR LongTermDebt dated "
                                  "2015-06-30, ENTA 2010-11-30, VNDA securities 2022-06-30; EV off by up to $400M",
             error_type="stale_xbrl_fact", severity="high",
             how_caught="re-read SEC companyfacts, matched each value to its fact date",
             count=int(v[m].drop_duplicates("ticker").verify_note.str.contains(
                 "collector debt|collector securities|collector cash_date").sum()),
             example_source="https://data.sec.gov/api/xbrl/companyfacts/CIK0000906709.json"),
        dict(stream="pipeline", table="target_profiles.csv", row_key="PTC, COMP, VIK, MGIH",
             what_the_ai_said="CT.gov sponsors PTC Therapeutics, Compass Therapeutics, Viking Therapeutics, Millennium "
                              "Pharmaceuticals mapped to SEC filers PTC, COMP, VIK, MGIH",
             what_the_source_says="those filers are PTC Inc. (software), Compass Inc. (real estate), Viking Holdings "
                                  "(cruises), Millennium Group International (packaging)",
             error_type="entity_name_collision", severity="high", how_caught="SEC submissions name vs sponsor, by hand",
             count=int(len(drop)), example_source="https://data.sec.gov/submissions/CIK0001820953.json"),
        dict(stream="pipeline", table="target_profiles.csv", row_key="ANAB annual_operating_cash_burn",
             what_the_ai_said="annual operating cash burn $52.6M (period end 2026-06-30)",
             what_the_source_says="that is the 6-month transition period on Form 10-KT (2026-01-01 to 2026-06-30); "
                                  "FY2025 operating cash flow was +$19.7M",
             error_type="period_mislabel", severity="medium", how_caught="companyfacts start/end dates", count=1,
             example_source="AnaptysBio 10-KT filed 2026-09-21"),
        dict(stream="pipeline", table="target_profiles.csv", row_key="tenk_excerpt",
             what_the_ai_said="one 10-K excerpt cited per target",
             what_the_source_says="every excerpt is an asset passage (business or risk factors); none is a balance sheet "
                                  "or cash flow statement, so cash, debt and burn rest on XBRL companyfacts only",
             error_type="citation_scope", severity="low", how_caught="read all excerpts", count=int(len(exr)),
             example_source="data/moat/pipeline/CLDX/10k_Barzolvolimab.md"),
    ])
