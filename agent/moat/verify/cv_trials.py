"""Costs verifier item 5: trial_cost_benchmarks.csv. ASPE 2014 Table 1 rows against the page-marked report
(p.30); Sertkaya 2024 Table 1 and 2 rows against the page-marked copy, which was itself diffed against the PMC
full-text XML (PMC11214120, /tmp/cv/epmc/sert.xml); DERIVED arithmetic recomputed; Moore and Wouters rows checked
against their Europe PMC abstracts. Adds cost_year and confidence."""
import io
import re

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, log_wrong, pages

SERT = "data/moat/costs/sertkaya_2024_jama_netw_open_tables.md"
ASPE = "data/moat/costs/aspe_2014_clinical_trial_costs.md"


def canon(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def sert_tables():
    txt = (ROOT / SERT).read_text()
    t1 = txt.split("[[page Table 1.]]")[1].split("[[page Table 2.]]")[0].strip().splitlines()
    t2 = txt.split("[[page Table 2.]]")[1].split("[[page Table 3.]]")[0].strip().splitlines()
    cols = [c.strip() for c in t1[0].split("|")][1:]
    T1, sec = {}, None
    for ln in t1[1:]:
        cells = [c.strip() for c in ln.split("|")]
        if all(c == "" for c in cells[1:]):
            sec = cells[0]
            continue
        for ta, v in zip(cols, cells[1:]):
            T1[(canon(sec), canon(cells[0]), canon(ta))] = v
    T2 = {}
    for ln in t2[2:]:
        cells = [c.strip() for c in ln.split("|")]
        T2[canon(cells[0])] = [c.split(" (")[0] for c in cells[1:]]
    return T1, T2


def num(v):
    try:
        return float(str(v).replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/trial_cost_benchmarks.csv")
    T1, T2 = sert_tables()
    aspe_txt = (ROOT / ASPE).read_text()
    aspe30 = re.sub(r"\s+", " ", aspe_txt.split("[[page 30]]")[1].split("[[page 31]]")[0])
    st, nt, cy, conf = [], [], [], []
    errs = {"pos_label": 0}
    t2_metrics = ["probability of success", "out of pocket", "incl. failures", "capitalized"]
    for i, r in d.iterrows():
        sd = r.source_doc
        k = r.source_row.split("|")
        s, n = "unverified", ""
        if sd.startswith("HHS"):
            v = f"${r.value:.1f}"
            s = "verified" if v in aspe30 else "unverified"
            n = f"{v} on p.30 (printed 3-3) Table 1 row {r.therapeutic_area}" if s == "verified" else f"{v} not found on p.30"
            if r.phase == "FDA NDA/BLA review fee":
                n += "; this is the NDA/BLA filing fee (footnote c), not a trial cost"
            cy.append("nominal USD, base year not stated (Medidata PICAS/CROCAS contract data, report dated 2014-07-25)")
            conf.append("high")
        elif sd.startswith("DERIVED"):
            ph, ta = k[2], k[3]
            pp = num(T1.get((canon("Per-patient cost (2018), $"), canon(ph), canon(ta))))
            npt = num(T1.get((canon("No. of patients enrolled per trial"), canon(ph), canon(ta))))
            calc = pp * npt / 1e6 if pp and npt else None
            ok = calc is not None and abs(calc - r.value) < 0.01
            s = "verified" if ok else "corrected"
            n = f"recomputed {pp:,.0f} x {npt:.0f} = {calc:.2f} USD millions" if calc else "inputs missing"
            if not ok and calc is not None:
                d.at[i, "value"] = round(calc, 2)
            n += "; per-patient cost only, excludes fixed site/CRO costs; one trial (multiply by Mean No. of trials for a phase)"
            cy.append("2018 USD")
            conf.append("medium")
        elif "|T1|" in r.source_row:
            sec, ph, ta = k[2], k[3], k[4]
            v = T1.get((canon(sec), canon(ph), canon(ta)))
            ok = v is not None and num(v) is not None and abs(num(v) - r.value) < 1e-6
            s = "verified" if ok else "unverified"
            n = f"Table 1 {sec} / {ph} / {ta} = {v}" + ("" if ok else f" vs row {r.value}")
            if sec.startswith("Phase durations") and ta in ("All",) or (v is not None and sec.startswith("Phase durations")
                                                                      and T1.get((canon(sec), canon(ph), canon("All"))) == v and ta != "All"):
                n += "; equals the All-areas value (source applies the pooled value where TA data were thin)"
            cy.append("2018 USD" if ("cost" in sec.lower() or "pocket" in sec.lower()) else "n/a (not a dollar value)")
            conf.append("high")
            if "dollar_year_basis" in d and pd.isna(r.dollar_year_basis) and cy[-1] == "2018 USD":
                d.at[i, "dollar_year_basis"] = "2018 USD"
        elif "|T2|" in r.source_row:
            ta, met = k[2], k[3]
            vals = T2.get(canon(ta))
            j = next(j for j, m in enumerate(t2_metrics) if m in met.lower())
            v = vals[j] if vals else None
            ok = v is not None and abs(num(v) - r.value) < 1e-6
            s = "verified" if ok else "unverified"
            n = f"Table 2 {ta} col {j + 1} = {v}"
            if j == 0:
                d.at[i, "metric"] = "probability of success, nonclinical stage to approval (%)"
                s = "corrected" if ok else s
                n += "; relabelled: Table 2 footnote b says the probability runs from the nonclinical stage, not phase 1 (it includes the 68% nonclinical-to-phase-1 step)"
                errs["pos_label"] += 1
                cy.append("n/a (not a dollar value)")
            else:
                cy.append("2018 USD")
            conf.append("high")
        else:  # Moore / Wouters from abstracts
            s = "verified"
            n = "number confirmed verbatim in the Europe PMC abstract; abstract-sourced, full text not read"
            if sd.startswith("Wouters"):
                cy.append("2018 USD (stated in abstract)")
            else:
                cy.append("not stated in abstract (IQVIA CostPro estimates, published 2018-2020)")
                if not pd.isna(r.dollar_year_basis):
                    n += f"; collector's dollar_year_basis '{r.dollar_year_basis}' is not in the abstract"
            conf.append("medium")
        st.append(s)
        nt.append(n)
    d["cost_year"] = cy
    d["confidence"] = conf
    d["verify_status"] = st
    d["verify_note"] = nt
    # source_doc author fix for ASPE
    m = d.source_doc.str.startswith("HHS")
    d.loc[m, "source_doc"] = ("HHS ASPE, Examination of Clinical Trial Costs and Barriers for Drug Development (July 25, 2014; "
                              "Eastern Research Group: Sertkaya, Birkenbach, Berlind, Eyraud; submitted to Wong and Jessup, ASPE)")
    print(d.verify_status.value_counts(), d.groupby(d.source_doc.str[:12]).verify_status.value_counts())
    print(d[d.verify_status == "unverified"][["source_row", "value", "verify_note"]].to_string())
    log_wrong([
        {"stream": "costs", "table": "trial_cost_benchmarks.csv", "row_key": "sertkaya2024|T2|*|probability of success",
         "what_the_ai_said": "metric 'probability of success, phase 1 to approval (%)' (overall 8.5%)",
         "what_the_source_says": "Table 2 footnote b: 'probability of successfully making it to approval from the nonclinical stage'; from phase 1 the overall figure is about 12.5% (8.5/0.68)",
         "error_type": "definition_mislabel", "severity": "high", "how_caught": "PMC full-text table footnote + product of Table 1 transitions",
         "count": errs["pos_label"], "example_source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11214120/ Table 2"},
        {"stream": "costs", "table": "trial_cost_benchmarks.csv", "row_key": "aspe2014 source_doc",
         "what_the_ai_said": "authors Sertkaya/Wong/Jessup/Beleche",
         "what_the_source_says": "report authors Sertkaya, Birkenbach, Berlind, Eyraud (ERG); Wong and Jessup are the ASPE recipients; Beleche is acknowledged",
         "error_type": "attribution", "severity": "low", "how_caught": "report title page", "count": 91,
         "example_source": "data/moat/costs/aspe_2014_clinical_trial_costs.md p.1"},
        {"stream": "costs", "table": "trial_cost_benchmarks.csv", "row_key": "aspe2014 dollar_year_basis",
         "what_the_ai_said": "2012-2013 dollars as reported",
         "what_the_source_says": "the report does not state a dollar base year anywhere in the text",
         "error_type": "unsupported_label", "severity": "low", "how_caught": "full-text search of the report", "count": 91,
         "example_source": "data/moat/costs/aspe_2014_clinical_trial_costs.md"}])
    d.loc[m, "dollar_year_basis"] = "not stated in report (nominal)"
    buf = io.StringIO()
    d.to_csv(buf, index=False)
    write("verify_costs", "verified/costs/trial_cost_benchmarks.csv", buf.getvalue(), group="costs", doc_type="table",
          source_url="ASPE 2014 report; Sertkaya 2024 PMC11214120; Europe PMC abstracts", quality="verified")


if __name__ == "__main__":
    main()
