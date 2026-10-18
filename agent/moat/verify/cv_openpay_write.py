"""Costs verifier item 3 (write): build open_payments_by_nature.csv for the 6 drugs and the verified
open_payments_by_drug.csv from the re-queries cached by cv_openpay.py."""
import io
import json
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.cv_openpay import ALT, NATURE6, YEARS, dist
from agent.moat.verify.pe_lib import ROOT, log_wrong

C = Path("/tmp/cv/op")
NAT = "Nature_of_Payment_or_Transfer_of_Value"
PROMO = {"Food and Beverage", "Travel and Lodging", "Consulting Fee", "Honoraria", "Gift", "Entertainment", "Education",
         "Compensation for services other than consulting, including serving as faculty or as a speaker at a venue other than a continuing education program",
         "Compensation for serving as faculty or as a speaker for a non-accredited and noncertified continuing education program",
         "Compensation for serving as faculty or as a speaker for an accredited or certified continuing education program"}
IP = {"Royalty or License", "Current or prospective ownership or investment interest", "Acquisitions"}


def load(yr, names, group=None):
    key = f"{yr}_{'+'.join(names)}_{group or 'tot'}".replace(" ", "_").replace("/", "_")
    f = C / f"{key}.json"
    return json.load(open(f)) if f.exists() else None


def src(yr):
    return (f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{dist(YEARS[yr])} (General Payments PY{yr}, dataset "
            f"{YEARS[yr]}); drug name matched in any of the 5 drug-name slots; queried 2026-10-17")


def main():
    op = pd.read_csv(ROOT / "data/moat/tables/open_payments_by_drug.csv")
    samp = json.load(open(C / "sample.json"))
    nat_rows = []
    api_tot = {}
    for yr in YEARS:
        for dname in NATURE6:
            res = load(yr, [dname.upper()], NAT)
            if res is None:
                continue
            tusd = sum(float(x["usd"]) for x in res)
            tn = sum(int(x["n"]) for x in res)
            api_tot[(dname, yr)] = (tusd, tn)
            for x in res:
                nat = x[NAT]
                cls = "promotional (food, travel, consulting, speaking, education)" if nat in PROMO else \
                      "royalty / license / ownership" if nat in IP else "other (grants, space rental, charity, supplies)"
                nat_rows.append({"drug": dname, "program_year": yr, "nature_of_payment": nat, "class": cls,
                                 "records": int(x["n"]), "usd": round(float(x["usd"]), 2),
                                 "share_of_drug_total": round(float(x["usd"]) / tusd, 4) if tusd else None,
                                 "source": src(yr), "source_row": f"{dname}|{yr}|{nat}",
                                 "verify_status": "verified", "verify_note": "re-queried from the CMS API by Opus verifier"})
        for dname in samp["top12"] + samp["rnd"]:
            if dname in NATURE6:
                continue
            res = load(yr, [dname.replace("-", " ").upper()])
            if res:
                api_tot[(dname, yr)] = (float(res[0]["usd"] or 0), int(res[0]["n"] or 0))
    nat = pd.DataFrame(nat_rows)
    summ = nat.groupby(["drug", "program_year", "class"]).usd.sum().unstack().fillna(0)
    summ["promo_share"] = summ.iloc[:, [c.startswith("promotional") for c in summ.columns]].sum(axis=1) / summ.sum(axis=1)
    print(summ.round(0).to_string())
    d = op.copy()
    d["api_usd_slots1to5"] = None
    d["api_records_slots1to5"] = None
    d["verify_status"] = "not_rechecked"
    d["verify_note"] = "not in the 20-drug recheck sample; collector matched drug-name slots 1-2 only"
    errs = []
    for i, r in d.iterrows():
        k = (r.drug, r.program_year)
        if k in api_tot:
            u, n = api_tot[k]
            d.at[i, "api_usd_slots1to5"] = round(u, 2)
            d.at[i, "api_records_slots1to5"] = n
            diff = (u - r.usd) / r.usd if r.usd else None
            if diff is not None and abs(diff) <= 0.01:
                d.at[i, "verify_status"] = "verified"
                d.at[i, "verify_note"] = f"API total across slots 1-5 within 1% ({diff:+.2%})"
            else:
                d.at[i, "verify_status"] = "corrected"
                d.at[i, "verify_note"] = (f"API total across slots 1-5 is {u:,.0f} USD / {n} records vs collector {r.usd:,.0f} / "
                                          f"{r.records} (slots 1-2 only); use the API figure")
                d.at[i, "usd"] = round(u, 2)
                d.at[i, "records"] = n
                errs.append((r.drug, r.program_year, r.usd, u))
        if r.drug in ("tecentriq", "entyvio", "imfinzi", "tremfya", "rinvoq", "skyrizi"):
            s = summ.loc[(r.drug, r.program_year)] if (r.drug, r.program_year) in summ.index else None
            if s is not None:
                d.at[i, "verify_note"] += f"; promotional share {s.promo_share:.1%} (see open_payments_by_nature.csv)"
    # zero-record brands under alternative names
    zrows = []
    for dname, alts in ALT.items():
        for yr in YEARS:
            res = load(yr, alts)
            u = float(res[0]["usd"] or 0) if res else None
            n = int(res[0]["n"] or 0) if res else None
            zrows.append({"drug": dname, "program_year": yr, "breakdown": "total", "category": "all", "records": n, "usd": u,
                          "source": src(yr), "source_row": f"{dname}|{yr}|total|alt-names",
                          "api_usd_slots1to5": u, "api_records_slots1to5": n,
                          "verify_status": "verified" if res is not None else "unverified",
                          "verify_note": f"retry under names {alts}: " + ("query failed" if res is None else
                                         f"{n} records" + ("" if n else "; zero is real (brand launched after the program year or "
                                                           "payments filed under the parent brand / generic name not used)"))})
    d = pd.concat([d, pd.DataFrame(zrows)], ignore_index=True)
    print(d.verify_status.value_counts().to_dict())
    print(pd.DataFrame(zrows)[["drug", "program_year", "records", "usd"]].to_string())
    for name, df in (("open_payments_by_drug.csv", d), ("open_payments_by_nature.csv", nat)):
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        write("verify_costs", f"verified/costs/{name}", buf.getvalue(), group="costs", doc_type="table",
              source_url="CMS Open Payments API", quality="verified")
    t = summ.loc["tecentriq"] if "tecentriq" in summ.index.get_level_values(0) else None
    log_wrong([{"stream": "costs", "table": "open_payments_by_drug.csv", "row_key": "drug-name slots",
                "what_the_ai_said": "general payments by associated drug, grouped on drug-name slots 1 and 2",
                "what_the_source_says": f"{len(errs)} of {len(api_tot)} rechecked drug-years differ by more than 1% once slots 3-5 are included",
                "error_type": "incomplete_query", "severity": "medium", "how_caught": "re-query CMS API with all 5 slots",
                "count": len(errs), "example_source": "; ".join(f"{a} PY{b}: {c:,.0f} -> {e:,.0f}" for a, b, c, e in errs[:3])},
               {"stream": "costs", "table": "open_payments_by_drug.csv", "row_key": "tecentriq/entyvio/imfinzi totals as marketing proxy",
                "what_the_ai_said": "general payments total used as a marketing-spend proxy",
                "what_the_source_says": "promotional share by nature: " + "; ".join(
                    f"{dn} PY{yr} {summ.loc[(dn, yr)].promo_share:.0%}" for dn, yr in summ.index),
                "error_type": "proxy_scope", "severity": "high", "how_caught": "nature_of_payment breakdown", "count": len(summ),
                "example_source": "open_payments_by_nature.csv"}])


if __name__ == "__main__":
    main()
