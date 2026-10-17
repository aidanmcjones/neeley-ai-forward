"""costs stream, table 2: trial cost benchmarks from ASPE 2014, Sertkaya 2024, Moore 2018/2020, Wouters 2020."""
import csv
import io
import re
import xml.etree.ElementTree as ET

import pymupdf

from agent.moat.common import write

ASPE_URL = "https://aspe.hhs.gov/sites/default/files/migrated_legacy_files//44516/rpt_erg.pdf"
SERT = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11214120/ (JAMA Netw Open 2024;7(6):e2415445, doi 10.1001/jamanetworkopen.2024.15445)"
rows = []


def add(source_doc, cite, phase, ta, metric, value, unit, basis, url, key, note=""):
    rows.append({"source_doc": source_doc, "table_or_page": cite, "phase": phase, "therapeutic_area": ta, "metric": metric, "value": value,
                 "unit": unit, "dollar_year_basis": basis, "note": note, "source": url, "source_row": key})


# ---- ASPE 2014: page-mark and parse Table 1 (page 30 of the PDF, report page 3-3)
d = pymupdf.open("/tmp/costs_dl/aspe/rpt_erg.pdf")
write("costs", "costs/aspe_2014_clinical_trial_costs.md", "\n".join(f"[[page {i + 1}]]\n{p.get_text()}" for i, p in enumerate(d)),
      group="costs", doc_type="report", period="2014", source_url=ASPE_URL, pages=len(d), upload=False)
t = " ".join(d[29].get_text().split())
t = t[t.index("Anti-Infective"):t.index("[a] The numbers")]
names = ["Anti-Infective", "Cardiovascular", "Central Nervous System", "Dermatology", "Endocrine", "Gastrointestinal", "Genitourinary System",
         "Hematology", "Immunomodulation", "Oncology", "Ophthalmology", "Pain and Anesthesia", "Respiratory System"]
for i, n in enumerate(names):
    j = t.index(n)
    k = t.index(names[i + 1]) if i + 1 < len(names) else len(t)
    vals = re.findall(r"\$([\d.]+)", t[j:k])
    # order: P1, P2, P3, subtotal(1-3), FDA review fee, P4, total
    for lab, v in zip(["Phase 1", "Phase 2", "Phase 3", "Phase 1-3 subtotal", "FDA NDA/BLA review fee", "Phase 4", "Total"], vals):
        add("HHS ASPE, Examination of Clinical Trial Costs and Barriers for Drug Development (July 25, 2014; Sertkaya/Wong/Jessup/Beleche, Eastern Research Group)",
            "PDF p.30 (report p.3-3), Table 1", lab, n, "total cost per single study", float(v), "USD millions", "2012-2013 dollars as reported (Medidata PICAS/CROCAS contracts)",
            ASPE_URL + "#page=30", f"aspe2014|T1|{n}|{lab}", "assumes one trial per phase")

# ---- Sertkaya 2024: Tables 1 and 2 from the open-access XML
root = ET.parse("/tmp/costs_dl/sertkaya/sertkaya.xml").getroot()


def txt(e):
    return " ".join("".join(e.itertext()).split())


tables = {txt(tw.find("label"))[:8]: tw for tw in root.iter("table-wrap")}
doc = []
for lab, tw in tables.items():
    doc.append(f"[[page {lab}]]\n" + "\n".join(" | ".join(txt(c) for c in tr) for tr in tw.iter("tr")))
write("costs", "costs/sertkaya_2024_jama_netw_open_tables.md", "\n".join(doc), group="costs", doc_type="article_tables", period="2024", source_url=SERT, upload=False)
t1 = [[txt(c) for c in tr] for tr in tables["Table 1."].iter("tr")]
hdr = t1[0][1:]
sect = None
unitmap = {"Phase durations, mo": ("months", "phase duration"), "Per-patient cost (2018), $": ("USD per patient", "per-patient cost"),
           "No. of patients enrolled per trial": ("patients", "patients enrolled per trial"), "Mean No. of trials": ("trials", "mean number of trials per development"),
           "Transition success probabilities, %": ("percent", "transition success probability"), "Out-of-pocket estimates (millions), $": ("USD millions", "out-of-pocket cost for the phase")}
for r in t1[1:]:
    if all(x == "" for x in r[1:]):
        sect = r[0]
        continue
    if sect not in unitmap:
        continue
    unit, metric = unitmap[sect]
    for ta, v in zip(hdr, r[1:]):
        ta = ta.replace("Cardio-vascular", "Cardiovascular").replace("Derma-tology", "Dermatology").replace("Gastro-intestinal", "Gastrointestinal").replace("Hema-tology", "Hematology")
        if v in ("NA", ""):
            continue
        add("Sertkaya, Beleche, Jessup, Sommers. Costs of Drug Development and R&D Intensity in the US, 2000-2018. JAMA Netw Open 2024", "Table 1", r[0], ta, metric,
            float(v.replace(" ", "")), unit, "2018 USD" if "USD" in unit else "", SERT, f"sertkaya2024|T1|{sect}|{r[0]}|{ta}",
            "per-patient costs from negotiated CRO/site contract data")
        if sect.startswith("Per-patient") and False:
            pass
# derived: Phase cost per trial = per-patient x patients
pp = {(r["therapeutic_area"], r["phase"]): r["value"] for r in rows if r["metric"] == "per-patient cost" and r["source_doc"].startswith("Sertkaya")}
npat = {(r["therapeutic_area"], r["phase"]): r["value"] for r in rows if r["metric"] == "patients enrolled per trial"}
for k, v in pp.items():
    if k in npat:
        add("DERIVED from Sertkaya 2024 Table 1 (per-patient cost x patients enrolled per trial)", "Table 1", k[1], k[0], "implied direct cost per trial", round(v * npat[k] / 1e6, 2),
            "USD millions", "2018 USD", SERT, f"sertkaya2024|derived|{k[1]}|{k[0]}", "excludes site/CRO fixed costs not captured in per-patient cost")
t2 = [[txt(c) for c in tr] for tr in tables["Table 2."].iter("tr")]
for r in t2[2:]:
    if len(r) == 4:
        ta, pos, c1, c2, c3 = r[0], *r[1:], None
    ta, pos, cost, exp, cap = (r + [None] * 5)[:5]
    if cost is None:
        continue
    for lab, v in (("probability of success, phase 1 to approval (%)", pos), ("mean cost per approved drug, out of pocket (USD millions)", cost),
                   ("mean expected cost per approved drug incl. failures (USD millions)", exp), ("mean expected capitalized cost per approved drug (USD millions)", cap)):
        add("Sertkaya et al. JAMA Netw Open 2024", "Table 2", "all phases (nonclinical through phase 4)", ta, lab, float(v.split(" ")[0]), "percent" if "%" in lab else "USD millions",
            "2018 USD", SERT, f"sertkaya2024|T2|{ta}|{lab}", "95% CI in source: " + v)

# ---- abstract-level literature rows
EPMC = "https://europepmc.org/article/MED/"
lit = [
 ("Moore TJ, Zhang H, Anderson G, Alexander GC. Estimated Costs of Pivotal Trials for Novel Therapeutic Agents Approved by the US FDA, 2015-2016. JAMA Intern Med 2018;178(11):1451-1457", "Abstract, Results",
  "pivotal", "all", "median estimated cost per pivotal trial", 19.0, "USD millions", "2017-2018 (IQVIA-type CRO benchmark tool)", EPMC + "30264133", "moore2018|median", "138 trials supporting 59 drugs; IQR 12.2-33.1; range <5 to 346.8"),
 ("Moore TJ et al. 2018", "Abstract, Results", "pivotal", "all", "mean cost, uncontrolled (no control group) pivotal trial", 13.5, "USD millions", "", EPMC + "30264133", "moore2018|uncontrolled", "26 of 138 trials; 95% CI 10.1-16.9"),
 ("Moore TJ et al. 2018", "Abstract, Results", "pivotal", "all", "mean cost, placebo or active comparator pivotal trial", 35.1, "USD millions", "", EPMC + "30264133", "moore2018|controlled", "95% CI 25.4-44.8"),
 ("Moore TJ et al. 2018", "Abstract, Results", "pivotal", "all", "max single-trial estimate (noninferiority, clinical-benefit endpoint)", 346.8, "USD millions", "", EPMC + "30264133", "moore2018|max", "95% CI 252.0-441.5"),
 ("Moore TJ, Heyward J, Anderson G, Alexander GC. Variation in the estimated costs of pivotal clinical benefit trials supporting US approval of new therapeutic agents. BMJ Open 2020;10:e038863", "Abstract, Results",
  "pivotal", "all", "median estimated cost per pivotal trial", 19.0, "USD millions", "", EPMC + "32532786", "moore2020|trial", "225 trials, 101 new agents; IQR 12-33"),
 ("Moore TJ et al. BMJ Open 2020", "Abstract, Results", "pivotal", "all", "median estimated cost per patient", 41413, "USD per patient", "", EPMC + "32532786", "moore2020|patient", "IQR 29,894-75,047; enrollment range 4 to 8442"),
 ("Moore TJ et al. BMJ Open 2020", "Abstract, Results", "pivotal", "all", "median pivotal-trial cost per approved new drug", 48.0, "USD millions", "", EPMC + "32532786", "moore2020|drug", "101 new molecular entities; IQR 20-102"),
 ("Moore TJ et al. Estimated costs of pivotal trials for FDA-approved cancer drugs, 2015-2017. Clin Trials 2020", "Abstract, Results", "pivotal", "Oncology", "median estimated cost per pivotal trial", 31.7, "USD millions", "", EPMC + "32114790", "moore2020onc|median", "39 trials, 30 drugs; IQR 17.0-60.4"),
 ("Moore TJ et al. Clin Trials 2020 (oncology)", "Abstract, Results", "pivotal", "Oncology", "median cost, ORR primary-endpoint trial", 17.7, "USD millions", "", EPMC + "32114790", "moore2020onc|orr", "IQR 11.9-27.1"),
 ("Moore TJ et al. Clin Trials 2020 (oncology)", "Abstract, Results", "pivotal", "Oncology", "median cost, PFS primary-endpoint trial", 42.3, "USD millions", "", EPMC + "32114790", "moore2020onc|pfs", "IQR 34.6-101.2"),
 ("Wouters OJ, McKee M, Luyten J. Estimated Research and Development Investment Needed to Bring a New Medicine to Market, 2009-2018. JAMA 2020;323(9):844-853", "Abstract, Results",
  "all phases incl. failures, capitalized at 10.5%", "all", "median capitalized R&D per new drug", 985.3, "USD millions", "2018 USD", EPMC + "32125404", "wouters2020|median", "95% CI 683.6-1228.9; 63 drugs of 355 with data"),
 ("Wouters OJ et al. JAMA 2020", "Abstract, Results", "all phases incl. failures, capitalized at 10.5%", "all", "mean capitalized R&D per new drug", 1335.9, "USD millions", "2018 USD", EPMC + "32125404", "wouters2020|mean", "95% CI 1042.5-1637.5"),
]
for src, cite, ph, ta, met, val, unit, basis, url, key, note in lit:
    add(src, cite, ph, ta, met, val, unit, basis, url, key, note)

cols = list(rows[0].keys())
buf = io.StringIO()
w = csv.DictWriter(buf, cols)
w.writeheader()
w.writerows(rows)
write("costs", "tables/trial_cost_benchmarks.csv", buf.getvalue(), group="costs", doc_type="table", source_url="ASPE 2014; JAMA Netw Open 2024; Moore; Wouters", upload=False)
print(len(rows))
for r in rows:
    if r["metric"] in ("total cost per single study",) and r["therapeutic_area"] in ("Oncology", "Cardiovascular"):
        print(r["therapeutic_area"], r["phase"], r["value"])
