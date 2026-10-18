"""rx verifier item 5: Part B providers by drug. Re-pulls 9 code-years from the CMS Physician and Other Practitioners by
Provider and Service file, cross-checks every total against CMS's national Geography and Service rows and the Part B
Spending by Drug totals, confirms each HCPCS code against the HCPCS long descriptors (NLM HCPCS API mirror of the CMS
file), and relabels Darzalex Faspro (J9144) rows that the collector filed under IV Darzalex."""
import json

import pandas as pd
import requests

from agent.moat.verify.rx_lib import C, ROOT, cms, out

T = ROOT / "data/moat/tables"
PROV = {2021: "31dc2c47-f297-4948-bfb4-075e1bec3a02", 2022: "e650987d-01b7-4f09-b75e-b0b075afbf98",
        2023: "0e9f2f2b-7bf9-451a-912c-e02e654dd725", 2024: "92396110-2aed-4d63-a6a2-5d6207d46a29"}
GEO = {2021: "f00f462f-bb61-48b1-a321-1c50d78ce175", 2022: "87304f15-9ed0-41dc-a141-6141a0327453",
       2023: "ddee9e22-7889-4bef-975a-7853e4cd0fbb", 2024: "6fea9d79-0129-4e4c-b1b8-23cd86a4f435"}
SPEND = "76a714ad-3a2c-43ac-b76d-9dadf8f7d890"
CODES = {"J9271": "keytruda", "J9277": "keytruda-qlex", "J9299": "opdivo", "J9289": "opdivo-qvantig",
         "J9145": "darzalex", "J9144": "darzalex-faspro", "J3358": "stelara-iv", "J3380": "entyvio", "J9022": "tecentriq",
         "J9173": "imfinzi", "J9227": "sarclisa", "J9061": "rybrevant", "J1306": "leqvio", "J0225": "amvuttra",
         "J0741": "cabenuva", "J0739": "apretude"}
EXPECT = {"J9271": "pembrolizumab", "J9277": "pembrolizumab", "J9299": "nivolumab", "J9289": "nivolumab",
          "J9145": "daratumumab", "J9144": "hyaluronidase-fihj", "J3358": "intravenous", "J3380": "vedolizumab",
          "J9022": "atezolizumab", "J9173": "durvalumab", "J9227": "isatuximab", "J9061": "amivantamab",
          "J1306": "inclisiran", "J0225": "vutrisiran", "J0741": "cabotegravir and rilpivirine", "J0739": "pre-exposure"}
SAMPLE = [("J9271", 2023), ("J9299", 2023), ("J9145", 2023), ("J9144", 2023), ("J3380", 2022), ("J9022", 2022),
          ("J9173", 2023), ("J3358", 2023), ("J1306", 2023)]


def hcpcs(code):
    f = C / f"hcpcs_{code}.json"
    if not f.exists():
        r = requests.get("https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search",
                         params={"terms": code, "df": "code,long_desc", "maxList": 5}, timeout=60).json()
        f.write_text(json.dumps(r))
    r = json.loads(f.read_text())
    return {c: d for c, d in r[3]}.get(code)


def main():
    col = pd.read_csv(T / "partb_providers_by_drug.csv")
    codes = []
    for c, slug in CODES.items():
        d = hcpcs(c) or ""
        codes.append({"hcpcs": c, "drug": slug, "hcpcs_long_desc": d, "code_ok": EXPECT[c] in d.lower()})
    codes = pd.DataFrame(codes)
    print(codes.to_string())
    geo, spend = {}, {}
    for c in CODES:
        for y in GEO:
            g = cms(GEO[y], {"filter[HCPCS_Cd]": c, "filter[Rndrng_Prvdr_Geo_Lvl]": "National"})
            if g:
                geo[(c, y)] = {"providers_all": sum(int(x["Tot_Rndrng_Prvdrs"]) for x in g),
                               "benes_all": sum(int(x["Tot_Benes"]) for x in g),
                               "services_all": sum(float(x["Tot_Srvcs"]) for x in g),
                               "pay_all": sum(float(x["Tot_Srvcs"]) * float(x["Avg_Mdcr_Pymt_Amt"]) for x in g)}
        s = cms(SPEND, {"filter[HCPCS_Cd]": c})
        for y in GEO:
            if s and s[0].get(f"Tot_Spndng_{y}"):
                spend[(c, y)] = {"partb_total_spend": float(s[0][f"Tot_Spndng_{y}"]),
                                 "partb_total_units": float(s[0][f"Tot_Dsg_Unts_{y}"] or 0),
                                 "partb_total_benes": float(s[0][f"Tot_Benes_{y}"] or 0)}
    rec = {}
    for c, y in SAMPLE:
        rows = pd.DataFrame(cms(PROV[y], {"filter[HCPCS_Cd]": c}))
        for k in ("Tot_Srvcs", "Avg_Mdcr_Pymt_Amt", "Tot_Benes"):
            rows[k] = pd.to_numeric(rows[k])
        rec[(c, y)] = {"providers": rows.Rndrng_NPI.nunique(), "services": rows.Tot_Srvcs.sum(),
                       "pay": (rows.Tot_Srvcs * rows.Avg_Mdcr_Pymt_Amt).sum()}
    d = col.copy()
    d["drug_collector"] = d.drug
    d["drug"] = [CODES.get(c, s) for c, s in zip(d.hcpcs, d.drug)]
    st, nt = [], []
    for c in ("providers_all_cms", "beneficiaries_all_cms", "services_all_cms", "payment_all_physician_file_usd",
              "partb_total_spend_usd", "partb_total_units", "partb_total_benes"):
        d[c] = None
    for i, r in d.iterrows():
        notes = []
        ok = bool(codes.set_index("hcpcs").loc[r.hcpcs, "code_ok"])
        if r.drug != r.drug_collector:
            notes.append(f"{r.hcpcs} is {codes.set_index('hcpcs').loc[r.hcpcs, 'hcpcs_long_desc']} (subcutaneous "
                         f"Darzalex Faspro), relabelled from '{r.drug_collector}'")
            ok = False
        if r.level == "total":
            g = geo.get((r.hcpcs, r.year))
            if g:
                d.loc[i, ["providers_all_cms", "beneficiaries_all_cms", "services_all_cms", "payment_all_physician_file_usd"]] = \
                    [g["providers_all"], g["benes_all"], g["services_all"], round(g["pay_all"], 2)]
                notes.append(f"provider file keeps provider-code rows with 11+ beneficiaries only: {r.providers} of "
                             f"{g['providers_all']} providers, {r.services / g['services_all']:.0%} of services")
            sp = spend.get((r.hcpcs, r.year))
            if sp:
                d.loc[i, ["partb_total_spend_usd", "partb_total_units", "partb_total_benes"]] = \
                    [sp["partb_total_spend"], sp["partb_total_units"], sp["partb_total_benes"]]
                notes.append(f"physician-office file pays {r.medicare_payment_est_usd / sp['partb_total_spend']:.0%} of "
                             f"all Part B spend on this code (hospital outpatient billing is outside this file)")
            x = rec.get((r.hcpcs, r.year))
            if x:
                same = (x["providers"] == r.providers and abs(x["services"] - r.services) < 1
                        and abs(x["pay"] - r.medicare_payment_est_usd) < 1)
                notes.append("re-pulled provider rows: providers, services and payment match" if same else
                             f"re-pull gives {x['providers']} providers, {x['services']:,.0f} services, {x['pay']:,.0f} USD")
                ok = ok and same
        notes.append("beneficiaries_sum_over_providers double-counts patients seen by several providers")
        st.append("verified" if ok else "corrected")
        nt.append("; ".join(notes))
    d["verify_status"], d["verify_note"] = st, nt
    d["in_opus_sample"] = [(c, y) in rec and lv == "total" for c, y, lv in zip(d.hcpcs, d.year, d.level)]
    # add code-years absent from the collector table but present in CMS national rows (all-provider totals only)
    extra = []
    have = set(zip(d.hcpcs, d.year))
    for (c, y), g in geo.items():
        if (c, y) in have:
            continue
        sp = spend.get((c, y), {})
        extra.append({"drug": CODES[c], "hcpcs": c, "hcpcs_desc": codes.set_index("hcpcs").loc[c, "hcpcs_long_desc"],
                      "year": y, "level": "total", "key": "ALL", "providers": 0 if y < 2024 else None,
                      "providers_all_cms": g["providers_all"], "beneficiaries_all_cms": g["benes_all"],
                      "services_all_cms": g["services_all"], "payment_all_physician_file_usd": round(g["pay_all"], 2),
                      "partb_total_spend_usd": sp.get("partb_total_spend"), "partb_total_units": sp.get("partb_total_units"),
                      "partb_total_benes": sp.get("partb_total_benes"),
                      "source": f"https://data.cms.gov/data-api/v1/dataset/{GEO[y]}/data?filter[HCPCS_Cd]={c}&filter[Rndrng_Prvdr_Geo_Lvl]=National",
                      "source_row": f"{y}:{c}:national", "verify_status": "added_from_cms_geography",
                      "verify_note": ("no provider in the provider-service file had 11+ beneficiaries, so the collector's "
                                      "pull was empty; national all-provider totals from Geography and Service" if y < 2024
                                      else "2024 file published but not pulled by collector; national totals only")})
    d = pd.concat([d, pd.DataFrame(extra)], ignore_index=True)
    out("partb_providers_by_drug.csv", d, "CMS Medicare Physician and Other Practitioners by Provider and Service")
    print(d.verify_status.value_counts().to_dict(), d[d.in_opus_sample == True].verify_status.value_counts().to_dict())
    t = d[d.level == "total"]
    print(t[["drug", "hcpcs", "year", "providers", "providers_all_cms", "services", "services_all_cms",
             "medicare_payment_est_usd", "partb_total_spend_usd", "verify_status"]].to_string())
    json.dump({"codes": codes.to_dict("records"), "status": d.verify_status.value_counts().to_dict(),
               "sample": {f"{c}:{y}": {k: float(v) for k, v in x.items()} for (c, y), x in rec.items()}},
              open("/tmp/rxv/partb_summary.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
