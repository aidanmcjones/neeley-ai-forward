"""Epi item 2: re-check all 30 indication_epidemiology rows against source copies; recompute derived counts.

SEER rows are parsed from the saved Stat Facts pages (prevalence, 2026 new cases, 5-year survival, 65+ share =
65-74 + 75-84 + >84 bins of new cases). Web rows were re-read from the live primary pages on 2026-10-17 (WebFetch
for cdc.gov, which blocks curl; EuropePMC REST for Helmick) and the verbatim sentences saved page-marked as
epi/sources/primary_recheck.md. Rows with no reachable primary page get confidence 'low, no primary copy'.
"""
import io
import re

import pandas as pd

from agent.moat.common import header, write
from agent.moat.verify.pe_lib import ROOT

SRC = ROOT / "data/moat/epi/sources"
RECHECK = [
    ("https://www.cdc.gov/mmwr/preview/mmwrhtml/mm6446a4.htm", "Vital Signs: Estimated Percentages and Numbers of Adults with Indications for Preexposure Prophylaxis to Prevent HIV Acquisition, United States, 2015 (MMWR early release 2015-11-24)",
     ["An estimated 1,232,000 (95%: CI: 661,000-1,803,000) adults in the United States", "Approximately 24.7% of sexually active adult men who have sex with men (MSM)",
      "18.5% of persons who inject drugs (115,000 [CI = 45,000-185,000])", "0.4% of heterosexually active adults (624,000 [CI = 404,000-846,000])"]),
    ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:18163481 (PubMed 18163481)", "Helmick et al. Estimates of the prevalence of arthritis and other rheumatic conditions in the United States. Part I. Arthritis and Rheumatism 2008 (abstract)",
     ["For specific conditions, the best available prevalence estimates were applied to the corresponding 2005 US population estimates from the Census Bureau, to estimate the number affected with each condition.",
      "We estimated that rheumatoid arthritis affects 1.3 million adults (down from the estimate of 2.1 million for 1995)"]),
    ("https://www.cdc.gov/nchs/products/databriefs/db508.htm", "NCHS Data Brief No. 508, September 2024, NHANES August 2021-August 2023",
     ["the prevalence of obesity in adults was 40.3%, with no significant differences between men and women",
      "The prevalence of severe obesity in adults was 9.4% and was higher in women than men for each age group."]),
    ("https://www.cdc.gov/diabetes/php/data-research/index.html", "National Diabetes Statistics Report, CDC (last updated September 16, 2026)",
     ["Estimated number of people with diagnosed or undiagnosed diabetes in the United States, 2023: 40.1 million; 12.0% of the population",
      "Estimated number of people with diagnosed diabetes in the United States, including 28.8 million adults aged >=18 years: 29.1 million",
      "Estimated percentage of adults aged >=18 years with diabetes who are undiagnosed, representing 11.0 million people: 27.6%",
      "Estimated number of people aged 65 years or older (52.1%) with prediabetes: 31.3 million"]),
    ("https://www.cdc.gov/hiv/data-research/facts-stats/index.html", "CDC Fast Facts: HIV in the US (dated April 22, 2024; 2022 data)",
     ["In 2022, an estimated 1.2 million people in the US had HIV.", "There were 37,981 new HIV diagnoses in the US and dependent areas in 2022.",
      "For every 100 people with HIV 87 knew their HIV status.", "65 were virally suppressed (per 100 people with diagnosed HIV)",
      "of people aged 65 and older, 163,626 were diagnosed with HIV."]),
    ("https://www.cdc.gov/nchs/data/hestat/hestat122.htm", "NCHS Health E-Stat 122, August 2026: Inflammatory Bowel Disease Among Adults Age 18 and Older: United States, 2023-2024 (NHIS)",
     ["In 2023-2024, 1.6% of adults had ever been diagnosed with any inflammatory bowel disease", "including 1.2% who had ever been diagnosed with ulcerative colitis",
      "and 0.5% who had ever been diagnosed with Crohn's disease.", "CD: 0.5% (about 1.3 million adults)", "UC: 1.2% (about 3.1 million adults)", "IBD: 1.6% (about 4.1 million adults)",
      "CD: 0.3% for adults ages 18-29 to 0.6% for adults age 70 and older", "UC: 0.4% for adults ages 18-29 to 2.2% for adults age 70 and older"]),
    ("https://www.cdc.gov/nchs/products/databriefs/db363.htm", "NCHS Data Brief No. 363, April 2020 (Carroll, Fryar): Total and High-density Lipoprotein Cholesterol in Adults: United States, 2015-2018",
     ["During 2015-2018, 11.4% of adults had high total cholesterol, and prevalence was similar by race and Hispanic origin.", "crude (unadjusted) 11.5%; ages 20-39 7.5%, 40-59 15.7%, 60 and over 11.4%"]),
    ("https://jamanetwork.com/journals/jamadermatology/fullarticle/2781378", "Armstrong AW et al. Psoriasis Prevalence in Adults in the United States. JAMA Dermatol 2021;157(8):940-946",
     ["Psoriasis prevalence among US adults 20 years or older was 3.0% (95% CI, 2.6%-3.4%).", "Based on the 2020 US census data, this outcome translates to an estimated 7.55 million US adults with psoriasis.",
      "This population-based cross-sectional study used 2011-2014 NHANES data", "In this nationally representative cross-sectional study including 12 625 participants"]),
]
RP = {"type 2 diabetes": 4, "obesity": 3, "HIV-1 treatment": 5, "Crohn's disease": 6, "ulcerative colitis": 6,
      "hypercholesterolemia (incl. HeFH)": 7, "plaque psoriasis": 8, "rheumatoid arthritis": 2, "HIV PrEP": 1}
ADULTS = 341_784_857 * (1 - 0.211)  # Census QuickFacts 2025 total x (1 - under-18 share), per web_extracts p14


def write_recheck():
    parts = [header("multiple primary pages, re-read live 2026-10-17 by the Opus verifier", method="WebFetch verbatim sentence extraction (cdc.gov blocks curl); EuropePMC REST for PubMed abstract; sentences are quotes, not full page copies")]
    for k, (url, title, quotes) in enumerate(RECHECK, 1):
        parts.append(f"\n[[page {k} | printed {k}]]\nURL: {url}\nTITLE: {title}\n" + "\n".join(f"> {q}" for q in quotes) + "\n")
    write("verify_epi", "epi/sources/primary_recheck.md", "".join(parts), group="epi", doc_type="source_extract",
          quality="verified_extract", source_url="see per-page URL", pages=len(RECHECK))


def seer(fname):
    t = (SRC / fname).read_text(errors="replace")
    L = [l.strip() for l in t.split("\n") if l.strip()]
    out = {}
    m = re.search(r"In (20\d\d), there were an estimated ([\d,]+) (?:people|women|men)", t)
    out["prev"] = int(m.group(2).replace(",", "")) if m else None
    out["prev_year"] = m.group(1) if m else None
    m = re.search(r"Estimated New Cases in (20\d\d) ([\d,]+)", t)
    out["inc"] = int(m.group(2).replace(",", "")) if m else None
    i = next(k for k, l in enumerate(L) if l.startswith("5-Year"))
    out["surv"] = float(next(L[j] for j in range(i, i + 4) if re.match(r"^[\d.]+%$", L[j]))[:-1])
    med = next(k for k, l in enumerate(L) if l == "Median Age" and "Diagnosis" in L[k + 1])
    bins = {}
    for j in range(max(0, med - 25), med):
        if L[j] in ("65–74", "75–84", ">84"):
            bins[L[j]] = float(L[j + 1].rstrip("%"))
    out["s65"] = round(sum(bins.values()), 1) if len(bins) == 3 else None
    out["median_age"] = int(L[med + 2]) if L[med + 2].isdigit() else None
    return out


def main():
    write_recheck()
    d = pd.read_csv(ROOT / "data/moat/tables/indication_epidemiology.csv")
    res = []
    for _, r in d.iterrows():
        chk, conf, copy, errs = [], r.confidence, None, []
        if str(r.source_local).startswith("epi/sources/seer_"):
            s = seer(r.source_local.split("/")[-1])
            copy = "data/moat/" + r.source_local
            for col, key in (("us_prevalence_n", "prev"), ("annual_incidence_n", "inc"),
                             ("five_year_survival_pct", "surv"), ("share_aged_65plus", "s65")):
                ok = s[key] is not None and abs(float(r[col]) - s[key]) < 0.051
                chk.append(f"{col}={'ok' if ok else 'MISMATCH ' + str(s[key])}")
                if not ok:
                    errs.append((col, r[col], s[key]))
            if "subset" in str(r.population_scope).lower() or "all subtypes" in str(r.population_scope) or \
                    "ALL lung" in str(r.population_scope) or "PROXY" in str(r.population_scope):
                chk.append("denominator is whole site or proxy, not the labelled subset")
        elif r.indication in RP:
            copy = f"data/moat/epi/sources/primary_recheck.md#page {RP[r.indication]}"
            chk.append("headline numbers re-read on the live primary page")
        else:
            copy = "data/moat/" + str(r.source_local)
        ind = r.indication
        if ind == "type 2 diabetes":
            chk.append(f"diagnosed_share recomputed 29.1/40.1 = {29.1 / 40.1 * 100:.1f}% (table has 72.4)")
            errs.append(("diagnosed_share", 72.4, round(29.1 / 40.1 * 100, 1)))
            chk.append("count covers type 1 + type 2; no T2D-only figure on the page")
        if ind == "obesity":
            n = 0.403 * ADULTS
            chk.append(f"DERIVED 40.3% x {ADULTS / 1e6:.1f}M = {n / 1e6:.1f}M ok; rate is NHANES 20+ applied to Census 18+ (overstates by about 2 birth cohorts)")
        if ind.startswith("atrial fibrillation"):
            chk.append(f"DERIVED 3.89% x {ADULTS / 1e6:.1f}M = {0.0389 * ADULTS / 1e6:.2f}M ok; 3.89% is a 5-year period prevalence among Epic Cosmos EHR patients (pmc_af p: line 98, 124), not a population survey; 70.40% anticoagulated verified")
            chk.append("CCW 4.60M / 6.7% (in note) has no primary copy (CCW charts return 404)")
            conf = "medium"
        if ind.startswith("hypercholesterolemia"):
            chk.append(f"DERIVED 11.4% x {ADULTS / 1e6:.1f}M = {0.114 * ADULTS / 1e6:.1f}M ok; 11.4% is AGE-ADJUSTED, crude 11.5% is the right rate for a count ({0.115 * ADULTS / 1e6:.1f}M); NHANES 20+ applied to 18+")
            chk.append("statin 26% is NCHS DB177 (2011-2012, adults 40+), not re-read; CCW 65.5% has no primary copy")
        if ind == "rheumatoid arthritis":
            chk.append("1.3M confirmed in Helmick 2008 abstract, built on 2005 Census population; still 19+ years old")
            conf = "low, dated (2005 base)"
        if ind == "plaque psoriasis":
            chk.append("3.0% and 7.55M confirmed (Armstrong 2021; count uses 2020 Census). NOTE the saved file epi/sources/pmc_psoriasis_armstrong.md is a different paper (PMC8254764, PATH tobacco biomarkers), not Armstrong")
            errs.append(("source copy pmc_psoriasis_armstrong.md", "Armstrong JAMA Derm 2021 psoriasis", "PMC8254764 PATH Study tobacco biomarker paper"))
        if ind in ("Crohn's disease", "ulcerative colitis"):
            chk.append("0.5%/1.3M and 1.2%/3.1M confirmed; 70+ value confirmed (CD 0.6%, UC 2.2%); 60-69 values (CD 0.6%, UC 1.5%) not on the re-read page summary; Medicare 67+ 0.40%/0.64% confirmed in pmc_ibd_medicare_mmwr.md line 78")
        if ind == "HIV-1 treatment":
            chk.append(f"diagnosed_n 87% x 1.2M = {0.87 * 1.2e6:,.0f} ok; 163,626 aged 65+ confirmed; '42% aged 55+' arithmetic needs the page total, not re-derivable from the saved extract")
        if ind == "HIV PrEP":
            chk.append("1,232,000 (95% CI 661,000-1,803,000) confirmed on the live MMWR page; it is a 2015 estimate. The 26% prescribed share is from a secondary UW document: no primary copy")
            conf = "low (2015 estimate; treated share has no primary copy)"
        if ind == "ATTR-CM":
            chk.append(f"100,000 does not appear in the saved review (pmc_attr_epidemiology_review.md); claims floor 6.1/million x 335M = {6.1e-6 * 335e6:,.0f} (table note says about 2,050); 54.9/million 65+ confirmed line 254")
            conf = "low, no primary copy (100,000)"
            errs.append(("us_prevalence_n", 100000, "not in any saved source; review gives 6.1 per million claims-diagnosed (~2,044)"))
        if ind in ("NSCLC", "SCLC") or "breast" in ind or ind.startswith("colorectal") or ind in ("HNSCC", "biliary tract cancer", "hepatocellular carcinoma", "lymphoma (cHL / PMBCL)", "renal cell carcinoma", "gastric / GEJ cancer"):
            chk.append("subset_caveat: prevalence/incidence are for the whole SEER site (or a proxy site), not the labelled subset")
        res.append(dict(checks=" | ".join(chk), confidence_verified=conf, source_copy=copy,
                        n_errors=len(errs), errors="; ".join(f"{a}: table {b} vs source {c}" for a, b, c in errs)))
    v = pd.concat([d, pd.DataFrame(res)], axis=1)
    v.loc[v.indication == "type 2 diabetes", "diagnosed_share"] = "72.6"
    v["confidence"] = v["confidence_verified"]
    v = v.drop(columns=["confidence_verified"])
    print(v[["indication", "confidence", "n_errors", "checks"]].to_string(max_colwidth=150))
    buf = io.StringIO()
    v.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/indication_epidemiology.csv", buf.getvalue(), group="tables", doc_type="table",
          quality="verified", source_url="data/moat/tables/indication_epidemiology.csv")


if __name__ == "__main__":
    main()
