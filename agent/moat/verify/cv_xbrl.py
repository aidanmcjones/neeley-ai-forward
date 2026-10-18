"""Costs verifier item 1a: recheck every XBRL row of company_cost_structure.csv for the 10 case companies
against a fresh SEC companyfacts pull (cached in /tmp/cv/cf), flag restatements, and record which filing each
row holds. Writes /tmp/cv/xbrl_checked.csv for cv_struct.py to merge.
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

from agent.moat.verify.pe_lib import ROOT

CF = Path("/tmp/cv/cf")
TEN = "MRK BMY PFE LLY NVO ABBV JNJ AZN AMGN GILD".split()
ANNUAL = {"10-K", "20-F", "10-K/A", "20-F/A"}


def load(cik):
    return json.load(open(CF / f"CIK{int(cik):010d}.json"))


def period_facts(cf, ns, concept, unit, end, instant):
    arr = cf["facts"].get(ns, {}).get(concept, {}).get("units", {}).get(unit, [])
    out = []
    for f in arr:
        if f.get("end") != end:
            continue
        if instant:
            if f.get("start"):
                continue
        else:
            if not f.get("start"):
                continue
            dd = (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days
            if not 350 <= dd <= 380:
                continue
        out.append(f)
    return out


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/company_cost_structure.csv")
    x = d[(d.ticker.isin(TEN)) & d.page_cite.isna()].copy()
    cache = {}
    res = []
    for i, r in x.iterrows():
        tk, conc, end, accn = r.source_row.split("|")
        ns, concept = conc.split(":")
        cik = r.source.split("/data/")[1].split("/")[0]
        if cik not in cache:
            cache[cik] = load(cik)
        cf = cache[cik]
        fs = period_facts(cf, ns, concept, r.unit, end, r.metric.startswith("headcount"))
        ann = [f for f in fs if f.get("form") in ANNUAL]
        q = [f for f in fs if f.get("form") not in ANNUAL]
        mine = [f for f in ann if f["accn"] == accn]
        status, notes = "verified", []
        if not mine:
            status = "unverified"
            notes.append(f"accession {accn} not found for {conc} {end} in fresh companyfacts")
            res.append({"idx": i, "verify_status": status, "verify_note": "; ".join(notes)})
            continue
        f = mine[0]
        if abs(float(f["val"]) - float(r.value)) > 0.5:
            status = "corrected"
            notes.append(f"value {r.value:.0f} -> {f['val']} per companyfacts")
        ann_sorted = sorted(ann, key=lambda z: z.get("filed", ""))
        orig = ann_sorted[0]
        vals = {}
        for a in ann_sorted:
            vals.setdefault(float(a["val"]), []).append(f"{a['accn']}({a.get('form')} fy{a.get('fy')} filed {a.get('filed')})")
        holds = "original" if f["accn"] == orig["accn"] else f"later comparative (filed {f.get('filed')}, fy{f.get('fy')} {f.get('form')})"
        if f.get("fp") != "FY":
            notes.append(f"fp={f.get('fp')} not FY")
        restated = len(vals) > 1
        res.append({"idx": i, "verify_status": status, "verify_note": "; ".join(notes),
                    "row_holds": holds,
                    "original_10k_accn": orig["accn"], "original_10k_filed": orig.get("filed"),
                    "original_value": float(orig["val"]),
                    "restated": restated,
                    "restatement_detail": " | ".join(f"{v:.0f}: {', '.join(a)}" for v, a in vals.items()) if restated else "",
                    "quarterly_dupes": len(q)})
    out = pd.DataFrame(res).set_index("idx")
    out.to_csv("/tmp/cv/xbrl_checked.csv")
    print(out.verify_status.value_counts(), out.restated.value_counts(), out.row_holds.str[:5].value_counts())
    print(out[out.restated].join(x[["ticker", "fiscal_year", "metric", "value"]])[
        ["ticker", "fiscal_year", "metric", "value", "row_holds", "original_value", "restatement_detail"]].to_string())


if __name__ == "__main__":
    main()
