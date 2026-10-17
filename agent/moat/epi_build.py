"""epi stream steps 2-4: indication_epidemiology.csv, medicare_market.csv, market_sizing_inputs.csv."""
import csv
import io
import re

import pandas as pd

from agent.moat.common import OUT, header, note_gap, write

SRC = OUT / "epi" / "sources"
SEER = "https://seer.cancer.gov/statfacts/html/{}.html"

# Facts read through WebFetch/WebSearch from pages the shell cannot download (cdc.gov blocks curl); each is saved
# page-marked in epi/sources/web_extracts.md so the page number cites it.
EXTRACTS = [
    ("cdc_diabetes", "https://www.cdc.gov/diabetes/php/data-research/index.html",
     "CDC diabetes data page (2023): 40.1 million people, 12.0% of U.S. population, with diagnosed or undiagnosed diabetes, 2023. "
     "Diagnosed 29.1 million (28.8 million adults 18+). Undiagnosed 27.6% of adults 18+ with diabetes, 11.0 million people. "
     "52.1% of people 65+ (31.3 million) have prediabetes. 115.2 million adults 18+ with prediabetes. "
     "NIDDK diabetes statistics page (saved in niddk_diabetes.md) gives the 2021 version: 38.4 million (11.6%), diagnosed 29.7 million, 27.2 million adults 65+ with prediabetes."),
    ("nchs_obesity_db508", "https://www.cdc.gov/nchs/products/databriefs/db508.htm",
     "NCHS Data Brief 508 (Sept 2024), NHANES August 2021-August 2023: prevalence of obesity among adults 20+ was 40.3%; men 39.2%, women 41.3%; "
     "ages 20-39 35.5%, 40-59 46.4%, 60 and older 38.9%. Severe obesity 9.4% (age-adjusted 9.7%). Health E-Stat 111 (Feb 2026) reports 40.3% obesity, 9.7% severe, 31.7% overweight (age-adjusted, adults 20+)."),
    ("cdc_hiv_facts", "https://www.cdc.gov/hiv/data-research/facts-stats/index.html",
     "CDC HIV facts and stats (2022 data): an estimated 1.2 million people in the US had HIV; 37,981 new HIV diagnoses in 2022; 87 of every 100 people with HIV knew their status; "
     "65 of every 100 people with diagnosed HIV were virally suppressed. Age counts 55-59 160,708, 60-64 137,329, 65+ 163,626 (about 42% aged 55+ by arithmetic on the page's age table). "
     "CDC has paused PrEP coverage reporting and advises against citing specific PrEP coverage data points."),
    ("cdc_nchs_ibd_hestat122", "https://www.cdc.gov/nchs/data/hestat/hestat122.htm",
     "NCHS Health E-Stat 122, NHIS 2023-2024, adults 18+: ever diagnosed with IBD 1.6%, ulcerative colitis 1.2%, Crohn's disease 0.5%. "
     "Estimated adults: about 1.3 million Crohn's disease, about 3.1 million ulcerative colitis, about 4.1 million IBD. Ages 60-69 IBD 2.0%, 70+ IBD 2.7% (no 65+ band). Civilian noninstitutionalized population."),
    ("cdc_afib_about", "https://www.cdc.gov/heart-disease/about/atrial-fibrillation.html",
     "CDC About Atrial Fibrillation: gives no current U.S. total; states 12.1 million people in the US will have AFib by 2050 (projection)."),
    ("jama_derm_psoriasis_armstrong", "https://jamanetwork.com/journals/jamadermatology/fullarticle/2781378",
     "Armstrong et al., JAMA Dermatol 2021;157(8):940-946. NHANES 2011-2014, adults 20+, n=12,625. Psoriasis prevalence 3.0% (95% CI 2.6%-3.4%), "
     "translating to an estimated 7.55 million US adults. Women 3.2%, men 2.8%; ages 50-59 highest at 4.3%."),
    ("nchs_chol_db363", "https://stacks.cdc.gov/view/cdc/87484",
     "NCHS Data Brief 363 (Carroll, Fryar, April 2020), NHANES 2015-2018: age-adjusted prevalence of high total cholesterol (>=240 mg/dL) among adults 20+ was 11.4% "
     "(crude 11.5%); men 10.5%, women 12.1%; ages 20-39 7.5%, 40-59 15.7%, 60+ 11.4%."),
    ("nchs_statin_db177", "https://www.cdc.gov/nchs/products/databriefs/db177.htm",
     "NCHS Data Brief 177 (Dec 2014), NHANES 2003-2012, adults 40+: cholesterol-lowering medication use in past 30 days rose from 20% to 28%; statin use 18% to 26%; "
     "93% of users took a statin by 2011-2012; use rose from 17% at ages 40-59 to 48% at 75+. (Old; newer NHANES cycles self-report only.)"),
    ("helmick_ra_2008", "https://pubmed.ncbi.nlm.nih.gov/18163481/",
     "Helmick et al., Arthritis Rheum 2008;58(1):15-25 (CDC-authored, Estimates of the prevalence of arthritis and other rheumatic conditions in the US, Part I): "
     "rheumatoid arthritis affects 1.3 million US adults (down from 2.1 million in 1995 estimate), built from published studies on 2005 census population. Read via search summary, not the full paper."),
    ("ccw_medicare_chronic_2022", "https://www2.ccwdata.org/web/guest/medicare-charts/medicare-chronic-condition-charts",
     "CMS CCW Medicare chronic condition charts, fee-for-service beneficiaries with full coverage, 2022: hyperlipidemia 65.5%, rheumatoid arthritis/osteoarthritis (combined) 36.2%, hypertension 66.8%. "
     "CCW Table B.1.a count table: atrial fibrillation 4,603,555 of 68,266,781 beneficiaries in 2022 (6.7%), 4,757,488 in 2017. Read via search summary; the table PDFs 404 from this network."),
    ("cdc_mmwr_prep_2015", "https://www.cdc.gov/mmwr/preview/mmwrhtml/mm6446a4.htm",
     "CDC MMWR 2015;64(46):1291-5: about 1,232,000 US adults (95% CI 661,000-1,803,000) had indications for HIV PrEP (24.7% of sexually active MSM, 18.5% of PWID, 0.4% of heterosexually active adults). "
     "Read via search summary. A UW PrEP guidance document (secondary) cites 26% of those with an indication prescribed PrEP in 2022."),
    ("attr_review_pmc11740649", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11740649/",
     "Systematic review of ATTR epidemiology (saved in pmc_attr_epidemiology_review.md): US ATTR-CM prevalence about 6.1 per million (claims based), 54.9 per million among 65+; US incidence in 2018 3.9 per million person-years, 36.6 among elderly. "
     "Claims-based, so diagnosed cases only. A frequently cited secondary estimate is about 100,000 US patients with ATTR-CM, 1-2% diagnosed (HFSA 2021 abstract, not verified)."),
    ("pmc_af_cosmos", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11686049/",
     "Epic Cosmos 2019-2023 (full text saved in pmc_af_prevalence_2019_2023.md): 4,834,977 AF patients among 124,247,691 US adults 18+; overall AF prevalence 3.89%; 12.49% at ages 65+; mean age 76; "
     "70.40% had at least one anticoagulant prescription (predominantly apixaban); 24.58% of those 90+. Historical estimates 1%-2.5%; All of Us 4.2%."),
    ("census_quickfacts", "https://www.census.gov/quickfacts/US",
     "Census QuickFacts, July 1 2025 estimate: US population 341,784,857; persons under 18 are 21.1% (so 18+ is about 269.7 million, derived). "
     "Vintage 2024 press kit: population 65+ was 61.2 million in 2024."),
]


def write_extracts():
    body = ""
    for i, (sid, url, text) in enumerate(EXTRACTS, 1):
        body += f"[[page {i} | printed {i}]]\nSOURCE_ID: {sid}\nURL: {url}\n{text}\n\n"
    write("epi", "epi/sources/web_extracts.md", header("multiple (see per-page URL)") + body, group="epi",
          doc_type="epi_source", pages=len(EXTRACTS), quality="official-extract")
    return {sid: (i, url) for i, (sid, url, _) in enumerate(EXTRACTS, 1)}


def seer(slug):
    t = re.sub(r"\s+", " ", (SRC / f"seer_{slug}.md").read_text())
    g = lambda p: re.search(p, t)
    inc = g(r"Estimated New Cases in (\d{4}) ([\d,]+)")
    prev = g(r"there were an estimated ([\d,]+) (?:people|women) living with")
    sv = g(r"5-Year Relative Survival ([\d.]+)% (\d{4}.\d{4})")
    med = g(r"Median Age At Diagnosis (\d+)")
    seg = t.split("Percent of New Cases by Age Group", 1)[-1][:900]
    a = [float(x) for x in re.findall(r"(?:65.74|75.84|>84) ([\d.]+)%", seg)]
    p65 = round(sum(a[:3]), 1) if len(a) >= 3 else None
    return dict(inc_year=int(inc.group(1)) if inc else None, inc=int(inc.group(2).replace(",", "")) if inc else None,
                prev=int(prev.group(1).replace(",", "")) if prev else None, surv=float(sv.group(1)) if sv else None,
                surv_period=sv.group(2) if sv else None, med=int(med.group(1)) if med else None, p65=p65)


# indication -> (SEER slug, scope note)
SEER_MAP = {
    "multiple myeloma": ("mulmy", "all myeloma"),
    "NSCLC": ("lungb", "SEER figure is ALL lung and bronchus cancer; NSCLC is the large majority of lung cancers (NCI/ACS ~80-85%, secondary, not fetched) so apply a subtype share in the model"),
    "SCLC": ("lungb", "SEER figure is ALL lung and bronchus cancer; SCLC is a minority (~10-15%, secondary, not fetched)"),
    "melanoma": ("melan", "melanoma of the skin, all stages"),
    "HR+/HER2- breast cancer": ("breast", "SEER female breast cancer, all subtypes; HR+/HER2- is the majority subtype (SEER Breast Subtypes Stat Facts page not fetched) so apply a subtype share"),
    "triple-negative breast cancer": ("breast", "SEER female breast cancer, all subtypes; TNBC subtype share not fetched"),
    "HER2+ breast cancer": ("breast", "SEER female breast cancer, all subtypes; HER2+ subtype share not fetched"),
    "urothelial / bladder cancer": ("urinb", "urinary bladder"),
    "renal cell carcinoma": ("kidrp", "kidney and renal pelvis (RCC is most of it)"),
    "HNSCC": ("oralcav", "PROXY: oral cavity and pharynx only; larynx not included"),
    "lymphoma (cHL / PMBCL)": ("hodg", "Hodgkin lymphoma only; PMBCL (rare NHL) not included"),
    "colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H": ("colorect", "all colorectal; MSI-H/dMMR is a minority subset (not fetched)"),
    "gastric / GEJ cancer": ("stomach", "stomach only; GEJ/esophageal adenocarcinoma overlaps esophageal"),
    "esophageal cancer": ("esoph", "esophagus"),
    "cervical cancer": ("cervix", "cervix uteri"),
    "hepatocellular carcinoma": ("livibd", "PROXY: liver and intrahepatic bile duct (HCC is most of it)"),
    "biliary tract cancer": ("livibd", "PROXY: liver and intrahepatic bile duct only; gallbladder and extrahepatic ducts not included"),
    "endometrial cancer": ("corp", "corpus and uterus NOS"),
    "ovarian cancer": ("ovary", "ovary"),
}

COLS = ["indication", "population_scope", "us_prevalence_n", "us_prevalence_pct", "prevalence_year", "annual_incidence_n",
        "incidence_year", "diagnosed_share", "diagnosed_n", "treated_share", "treated_note", "share_aged_65plus",
        "share_aged_65plus_basis", "five_year_survival_pct", "source_name", "source_url", "source_local", "source_page",
        "confidence", "note", "source", "source_row"]


def row(**k):
    r = {c: "" for c in COLS}
    r.update(k)
    return r


def build_epi(pg):
    L = lambda sid: (pg[sid][0], pg[sid][1])
    rows = []

    def add(ind, sid, name, local, **kw):
        page, url = L(sid) if sid in pg else (1, kw.pop("url", ""))
        kw.setdefault("source_url", url)
        kw["source_name"] = name
        kw["source_local"] = local
        kw["source_page"] = page
        kw["source"] = f"{kw['source_url']} | local {local} p{page}"
        kw["source_row"] = f"{ind}|{sid}"
        rows.append(row(indication=ind, **kw))

    add("type 2 diabetes", "cdc_diabetes", "CDC diabetes data page", "epi/sources/web_extracts.md",
        population_scope="all diabetes (type 1 + type 2), US population", us_prevalence_n=40100000, us_prevalence_pct=12.0,
        prevalence_year=2023, diagnosed_share=72.4, diagnosed_n=29100000,
        note="Total includes ~2M type 1; T2D is the large majority. Diagnosed share = 29.1/40.1 (derived). 65+ prediabetes 52.1% (31.3M). 65+ diabetes share not fetched",
        confidence="high", treated_note="treated share of diagnosed not collected (NHANES/MEPS needed)")
    add("obesity", "nchs_obesity_db508", "NCHS Data Brief 508 (NHANES Aug 2021-Aug 2023)", "epi/sources/web_extracts.md",
        population_scope="adults 20+", us_prevalence_n=108700000, us_prevalence_pct=40.3, prevalence_year="2021-2023",
        note="Count DERIVED (40.3% x 269.7M Census 18+; NHANES base is 20+): apply 40.3% to adults (Census 18+ about 269.7M gives ~108.7M, derived). Age 60+ 38.9%; severe obesity 9.4%. Wegovy/Zepbound label also covers overweight with comorbidity (not in this figure)",
        confidence="high", treated_note="share on anti-obesity medication not collected")
    add("atrial fibrillation (stroke prevention)", "pmc_af_cosmos",
        "Epic Cosmos AF cohort (Prevalence, Management, Comorbidities of AF in US 2019-2023) + CDC AF page", "epi/sources/pmc_af_prevalence_2019_2023.md",
        population_scope="adults 18+ in Epic Cosmos EHR", us_prevalence_n=10500000, us_prevalence_pct=3.89, prevalence_year="2019-2023", diagnosed_share=100,
        treated_share=70.4, treated_note="70.40% of AF patients had at least one anticoagulant prescription (Apixaban most common); about 30% not anticoagulated",
        share_aged_65plus=None, share_aged_65plus_basis="prevalence 12.49% at ages 65+; mean age of AF patients 76",
        source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC11686049/",
        note="EHR-diagnosed AF, so diagnosed by construction. 3.89% x 269.7M adults = ~10.5M (derived). CDC page only gives 12.1M by 2050 projection. CMS CCW FFS AF count 4.60M in 2022 (6.7% of FFS)",
        confidence="medium")
    add("hypercholesterolemia (incl. HeFH)", "nchs_chol_db363", "NCHS Data Brief 363 (NHANES 2015-2018) + Data Brief 177", "epi/sources/web_extracts.md",
        population_scope="adults 20+, total cholesterol >=240 mg/dL", us_prevalence_n=30700000, us_prevalence_pct=11.4, prevalence_year="2015-2018", treated_share=26,
        treated_note="statin use 26% of adults 40+ (2011-2012, NCHS DB177; old). CMS CCW hyperlipidemia 65.5% of FFS Medicare beneficiaries 2022",
        note="Count DERIVED 11.4% x 269.7M. PCSK9/siRNA addressable pool is the subset with ASCVD or HeFH above LDL-C goal, not all high-cholesterol adults; that subset share is not collected",
        confidence="medium")
    add("rheumatoid arthritis", "helmick_ra_2008", "Helmick et al. 2008 (CDC) via search summary", "epi/sources/web_extracts.md",
        population_scope="adults", us_prevalence_n=1300000, prevalence_year=2005,
        note="Old (2005 census base); claims-based commercial prevalence 0.41-0.54% (2004-2014) implies similar or higher. CCW 36.2% is RA+OA combined so not usable for RA alone. NIAMS RA page saved (niams_ra.md) holds no count",
        confidence="low")
    add("plaque psoriasis", "jama_derm_psoriasis_armstrong", "Armstrong et al. JAMA Dermatol 2021 (NHANES 2011-2014)", "epi/sources/web_extracts.md",
        population_scope="adults 20+, all psoriasis", us_prevalence_n=7550000, us_prevalence_pct=3.0, prevalence_year="2011-2014",
        note="All psoriasis; moderate-to-severe share that is systemic-eligible (label population) not collected (NPF/AAD ~20-30% is secondary)", confidence="high")
    add("Crohn's disease", "cdc_nchs_ibd_hestat122", "NCHS Health E-Stat 122 (NHIS 2023-2024)", "epi/sources/web_extracts.md",
        population_scope="adults 18+ ever diagnosed", us_prevalence_n=1300000, us_prevalence_pct=0.5, prevalence_year="2023-2024", diagnosed_share=100,
        share_aged_65plus_basis="ages 60-69 0.6%, 70+ 0.6%; MMWR 2021 Medicare FFS ages 67+: 0.40% have Crohn's (2018)",
        note="Self-reported ever diagnosed; moderate-to-severe share (label population) not collected", confidence="high")
    add("ulcerative colitis", "cdc_nchs_ibd_hestat122", "NCHS Health E-Stat 122 (NHIS 2023-2024)", "epi/sources/web_extracts.md",
        population_scope="adults 18+ ever diagnosed", us_prevalence_n=3100000, us_prevalence_pct=1.2, prevalence_year="2023-2024", diagnosed_share=100,
        share_aged_65plus_basis="ages 60-69 1.5%, 70+ 2.2%; MMWR 2021 Medicare FFS ages 67+: 0.64% have UC (2018)",
        note="Self-reported ever diagnosed; sum of CD+UC exceeds IBD total in the report because of overlap/rounding", confidence="high")
    add("HIV-1 treatment", "cdc_hiv_facts", "CDC HIV facts and stats (2022 data)", "epi/sources/web_extracts.md",
        population_scope="all ages, US + dependent areas", us_prevalence_n=1200000, prevalence_year=2022, annual_incidence_n=37981, incidence_year=2022,
        diagnosed_share=87, diagnosed_n=int(1200000 * 0.87), treated_share=None,
        treated_note="65% of people with diagnosed HIV are virally suppressed (proxy for effective ART, 2022); on-ART share not published on the page",
        share_aged_65plus=None, share_aged_65plus_basis="about 42% of people with HIV are 55+; 163,626 are 65+ (2022 age table)",
        note="diagnosed_n derived = 87% x 1.2M. Medicaid/Medicare coverage shares for HIV not collected", confidence="high")
    add("HIV PrEP", "cdc_mmwr_prep_2015", "CDC MMWR 2015 PrEP indications (search summary)", "epi/sources/web_extracts.md",
        population_scope="US adults with PrEP indication", us_prevalence_n=1232000, prevalence_year=2015,
        treated_share=26, treated_note="26% of those with an indication prescribed PrEP in 2022 (UW PrEP guidance, secondary); CDC has paused PrEP coverage reporting",
        note="Indication count is a 2015 estimate with wide CI (661K-1.8M); newer CDC estimate not collected", confidence="low")
    add("ATTR-CM", "attr_review_pmc11740649", "Systematic review of ATTR epidemiology (PMC11740649)", "epi/sources/pmc_attr_epidemiology_review.md",
        population_scope="diagnosed (claims-based)", us_prevalence_n=100000, us_prevalence_pct=None, prevalence_year="2018-2022",
        annual_incidence_n=None, share_aged_65plus_basis="prevalence 54.9 per million among 65+ vs 6.1 per million overall",
        note="prevalence 100,000 is the SECONDARY HFSA-abstract estimate (unverified); claims-diagnosed floor of about 2,050 = 6.1 per million x ~335M (claims floor, 2018 data) is a claims floor from one study and is far below the secondary ~100,000 true-prevalence estimate (1-2% diagnosed); use Part D beneficiaries on Vyndamax/Attruby as the treated floor",
        confidence="low", diagnosed_share="1-2 (secondary, unverified)")

    # SEER-based
    for ind, (slug, scope) in SEER_MAP.items():
        s = seer(slug)
        url = SEER.format(slug)
        rows.append(row(indication=ind, population_scope=scope, us_prevalence_n=s["prev"] or "", prevalence_year=2023,
                        annual_incidence_n=s["inc"] or "", incidence_year=f"{s['inc_year']} (estimated)", share_aged_65plus=s["p65"] or "",
                        share_aged_65plus_basis="share of new cases diagnosed at ages 65+ (65-74 + 75-84 + 85+), SEER 21 2019-2023; median age at diagnosis " + str(s["med"]),
                        five_year_survival_pct=s["surv"] or "", source_name="NCI SEER Cancer Stat Facts", source_url=url,
                        source_local=f"epi/sources/seer_{slug}.md", source_page=1, confidence="high" if "PROXY" not in scope else "medium",
                        note=scope, source=f"{url} | local epi/sources/seer_{slug}.md p1", source_row=f"{ind}|seer_{slug}"))
    return rows


def main():
    pg = write_extracts()
    rows = build_epi(pg)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
    write("epi", "tables/indication_epidemiology.csv", buf.getvalue(), group="epi", doc_type="epi_table",
          source_url="see per-row source")
    print(len(rows), "epidemiology rows")
    have = {r["indication"] for r in rows}
    m = pd.read_csv(OUT / "tables" / "indication_map.csv")
    for ind in sorted(set(m.indication) - have):
        note_gap("epi", ind, "indication_epidemiology", f"no primary epidemiology collected for '{ind}' (drugs: {', '.join(sorted(set(m[m.indication == ind].drug)))})")
    print("indications without epi:", sorted(set(m.indication) - have))


if __name__ == "__main__":
    main()
