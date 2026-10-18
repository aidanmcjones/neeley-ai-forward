"""rx verifier item 6: formulary history. Recomputes coverage, tier, PA/ST/QL for every mapped RXCUI from the CMS
quarterly formulary PUF basic-drugs files the collector used (scratch copies), checks the formulary-RXCUI grain for
double counting, re-confirms the RXCUI map for 20 brands against RxNav, and adds part_b_drug / contract_year."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from agent.moat.verify.rx_lib import C, ROOT, log_wrong, out

SP = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx/spuf")
T = ROOT / "data/moat/tables"
SAMPLE_Q = ["2024Q4", "2026Q3"]
# physician-administered (Part B) vs self-administered (Part D); mixed = IV induction or office forms under Part B
PART_B = {"keytruda", "keytruda-qlex", "opdivo", "opdivo-qvantig", "darzalex", "darzalex-faspro", "imfinzi", "tecentriq",
          "sarclisa", "rybrevant", "leqvio", "amvuttra", "cabenuva", "apretude"}
MIXED = {"entyvio", "stelara", "skyrizi", "tremfya", "cosentyx", "wezlana", "yeztugo"}
IV_WORDS = ("Injection",)
SC_WORDS = ("Prefilled Syringe", "Auto-Injector", "Pen Injector", "Cartridge", "Injector")
BRANDS20 = ["eliquis", "xarelto", "ozempic", "rybelsus", "wegovy", "jardiance", "farxiga", "mounjaro", "zepbound",
            "trulicity", "repatha", "praluent", "skyrizi", "rinvoq", "humira", "stelara", "biktarvy", "januvia",
            "entyvio", "keytruda"]
S = requests.Session()


def rx(path):
    f = C / ("rxnav_" + path.replace("/", "_").replace("?", "_").replace("=", "_").replace("&", "_"))
    if f.exists():
        return json.load(open(f))
    for i in range(5):
        try:
            r = S.get("https://rxnav.nlm.nih.gov/REST/" + path, timeout=60)
            if r.ok:
                json.dump(r.json(), open(f, "w"))
                return r.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2)
    return {}


def summarize(q):
    f = pd.read_csv(SP / f"{q}_basic_formulary.txt", sep="|", dtype=str, encoding="latin-1",
                    usecols=["FORMULARY_ID", "CONTRACT_YEAR", "RXCUI", "NDC", "TIER_LEVEL_VALUE", "QUANTITY_LIMIT_YN",
                             "PRIOR_AUTHORIZATION_YN", "STEP_THERAPY_YN"])
    grain = f.groupby(["FORMULARY_ID", "RXCUI"]).size()
    n_form = f.FORMULARY_ID.nunique()
    f["tier"] = pd.to_numeric(f.TIER_LEVEL_VALUE, errors="coerce")
    g = f.groupby("RXCUI").agg(formularies=("FORMULARY_ID", "nunique"), tier_median=("tier", "median"),
                               pa=("PRIOR_AUTHORIZATION_YN", lambda s: s.eq("Y").mean()),
                               st=("STEP_THERAPY_YN", lambda s: s.eq("Y").mean()),
                               ql=("QUANTITY_LIMIT_YN", lambda s: s.eq("Y").mean()))
    g["coverage"] = g.formularies / n_form
    meta = {"rows": len(f), "formularies": n_form, "contract_years": sorted(f.CONTRACT_YEAR.unique().tolist()),
            "max_rows_per_formulary_rxcui": int(grain.max()), "pairs_with_dupes": int((grain > 1).sum())}
    return g, meta


def form_route(drug, name):
    if drug in PART_B:
        return True
    if drug in MIXED:
        n = str(name)
        return not any(w in n for w in SC_WORDS) and any(w in n for w in IV_WORDS)
    return False


def check_map(m):
    """For each SBD/BPCK of 20 brands: RxNav properties (name, tty, active) and the brand name it belongs to."""
    rows = []
    sub = m[m.drug.isin(BRANDS20)]

    def one(r):
        p = rx(f"rxcui/{r.rxcui}/properties.json").get("properties") or {}
        bn = []
        for cg in rx(f"rxcui/{r.rxcui}/related.json?tty=BN").get("relatedGroup", {}).get("conceptGroup", []) or []:
            bn += [c["name"] for c in cg.get("conceptProperties", []) or []]
        st = rx(f"rxcui/{r.rxcui}/historystatus.json").get("rxcuiStatusHistory", {}).get("metaData", {}).get("status")
        return {"drug": r.drug, "rxcui": r.rxcui, "tty_collector": r.tty, "tty_rxnav": p.get("tty"),
                "name_rxnav": p.get("name"), "brand_names_rxnav": "|".join(bn), "rxnav_status": st, "link": r.link}

    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(one, [r for r in sub.itertuples()]))
    return pd.DataFrame(rows)


def main():
    col = pd.read_csv(T / "formulary_history.csv", dtype={"rxcui": str})
    summ, metas = {}, {}
    for q in col.quarter.unique():
        summ[q], metas[q] = summarize(q)
        print(q, metas[q], flush=True)
    m = pd.read_csv("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx/rxcui_map.csv", dtype=str)
    mc = check_map(m)
    mc.to_csv("/tmp/rxv/rxcui_check.csv", index=False)
    brand_of = {}
    for r in mc.itertuples():
        if r.link == "brand":
            want = r.drug.replace("-", " ").lower()
            ok = r.tty_rxnav == r.tty_collector and any(want == b.lower() for b in str(r.brand_names_rxnav).split("|"))
            brand_of[r.rxcui] = (ok, r.brand_names_rxnav, r.rxnav_status)
    shared = m.groupby("rxcui").drug.nunique()
    shared = set(shared[shared > 1].index)
    rows = []
    for _, r in col.iterrows():
        o = r.to_dict()
        g, meta = summ[r.quarter], metas[r.quarter]
        o["contract_year"] = int(meta["contract_years"][0])
        o["part_b_drug"] = form_route(r.drug, r.rxcui_name)
        notes = []
        mine = g.loc[r.rxcui] if r.rxcui in g.index else None
        if mine is None:
            ok = pd.isna(r.formularies)
            if r.rxcui_link == "generic_equivalent":
                notes.append("SCD (generic-name) RXCUI: plan formularies list the brand SBD, so absence here is not "
                             "non-coverage of the brand")
            elif o["part_b_drug"]:
                notes.append("physician-administered (Part B) product: Part D formulary absence is expected, not a "
                             "coverage gap")
            else:
                notes.append("not on any Part D formulary in this file")
        else:
            ok = (abs(mine.coverage - (r.coverage_share or -1)) < 1e-3 and mine.formularies == r.formularies
                  and (mine.tier_median == r.tier_median) and abs(mine.pa - r.prior_auth_share) < 1e-3
                  and abs(mine.st - r.step_therapy_share) < 1e-3)
            if not ok:
                notes.append(f"recomputed coverage {mine.coverage:.4f}, tier {mine.tier_median}, PA {mine.pa:.4f}, "
                             f"ST {mine.st:.4f}")
                o.update(formularies=mine.formularies, coverage_share=round(mine.coverage, 4),
                         tier_median=mine.tier_median, prior_auth_share=round(mine.pa, 4),
                         step_therapy_share=round(mine.st, 4), quantity_limit_share=round(mine.ql, 4))
        o["covered_in_any_formulary"] = None if (o["part_b_drug"] and mine is None) else (mine is not None)
        b = brand_of.get(r.rxcui)
        if b is not None:
            o["rxcui_rxnav_check"] = "ok" if b[0] else f"MISMATCH: RxNav brand {b[1]}"
            if not b[0]:
                notes.append(f"RxNav says this SBD belongs to brand '{b[1]}', not {r.drug}")
                ok = False
        if r.rxcui in shared:
            notes.append("this SCD is shared by several brands (" + "|".join(sorted(m[m.rxcui == r.rxcui].drug)) +
                         "): never sum SCD rows across drugs")
        o["in_opus_sample"] = r.quarter in SAMPLE_Q
        notes.append(f"CMS release label {r.quarter} holds contract year {o['contract_year']} formularies; coverage_share = "
                     f"formulary IDs listing the RXCUI / {meta['formularies']} formulary IDs (unweighted by plans or "
                     f"enrollees; one row per formulary-RXCUI so no double count)")
        o["verify_status"] = "verified" if ok else "corrected"
        o["verify_note"] = "; ".join(notes)
        rows.append(o)
    df = pd.DataFrame(rows)
    out("formulary_history.csv", df.round(4), "CMS quarterly Prescription Drug Plan Formulary PUF (basic drugs file)")
    print(df.verify_status.value_counts().to_dict(), df.groupby("in_opus_sample").verify_status.value_counts().to_dict())
    print(mc.assign(ok=[brand_of.get(x, (None,))[0] for x in mc.rxcui]).query("link=='brand' and ok!=True").to_string())
    sm = df[df.quarter.isin(SAMPLE_Q) & (df.rxcui_link == "brand") & df.drug.isin(
        ["eliquis", "xarelto", "ozempic", "jardiance", "mounjaro", "repatha", "skyrizi", "rinvoq", "biktarvy", "trulicity"])]
    print(sm.groupby(["drug", "quarter"]).agg(cov=("coverage_share", "max"), tier=("tier_median", "median"),
                                             pa=("prior_auth_share", "max")).to_string())
    json.dump({"metas": metas, "status": df.verify_status.value_counts().to_dict(),
               "map_checked": int((mc.link == "brand").sum()),
               "map_bad": [x for x, v in brand_of.items() if not v[0]],
               "part_b_rows": int(df.part_b_drug.sum()),
               "uncovered_brand_partd": int(((df.rxcui_link == "brand") & ~df.part_b_drug & (df.covered_in_any_formulary == False)).sum())},
              open("/tmp/rxv/formulary_summary.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
