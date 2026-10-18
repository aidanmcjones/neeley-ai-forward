"""Wave 3 epi verification (Opus verifier, 2026-10-17).

Part A: all 34 wave 3 rows (18 indication_epidemiology_wave3 + 16 indication_subset_shares) re-read on the primary page;
quotes in data/moat/epi/sources/primary_recheck_wave3.md (pe_w3_pages.PAGES). Part B: new primary rows for the open
indications and shares. Then the market_sizing_inputs funnel is extended for the newly covered indications using the
epi_market.py / pe_epi2.py formulas (denominator = diagnosed_n if present else us_prevalence_n; incidence-only rows
use annual_incidence_n with denominator_basis 'incident'; floor % = Part D floor / denominator x 100, 3 dp).
"""
import io
import json

import pandas as pd

from agent.moat.common import now, write
from agent.moat.verify.pe_lib import ROOT
from agent.moat.verify.pe_w3_pages import PAGE_NO, render

M = ROOT / "data/moat"
TOTAL = 341_784_857  # Census QuickFacts 2025 total (pe_epi.py, web_extracts p14)
ADULTS = TOTAL * (1 - 0.211)
COPY = "data/moat/epi/sources/primary_recheck_wave3.md#page {}"
COLS = list(pd.read_csv(M / "verified/epi/indication_epidemiology.csv", nrows=0).columns)

# wave 3 source key -> (primary url read, checks, field overrides)
EPI_FIX = {
    "cdc_heart_failure": ("https://www.cdc.gov/heart-disease/about/heart-failure.html",
                          "6.7M adults 20+ and 452,573 death certificates (2023) confirmed; year not on page (AHA 2024 cites NHANES 2017-2020, confirmed in AHA 2025 p: 6.7M)", {}),
    "cdc_ckd_2026": ("https://www.cdc.gov/kidney-disease/php/data-research/index.html",
                     "14% / 37M adults 18+, NHANES Aug 2021-Aug 2023, 87% unaware (20+ base), 65+ 34% confirmed; diagnosed_share 13 is DERIVED 100-87 on a 20+ base", {}),
    "cdc_vte": ("https://www.cdc.gov/blood-clots/data-research/facts-stats/index.html",
                "'Up to 900,000' per year, 60,000-100,000 deaths, 33% recur in 10 years confirmed; page dated Jan 27 2025; upper bound, not a point estimate", {}),
    "cdc_heart_disease_facts": ("https://www.cdc.gov/heart-disease/data-research/facts-stats/index.html",
                                "CAD about 5% of adults 20+, 805,000 heart attacks (605,000 first + 200,000 recurrent), 919,032 CVD deaths 2023 confirmed; page dated Oct 24 2024. Superseded for the funnel by the AHA 2025 row", {}),
    "gelfand_psa_2005": ("https://pubmed.ncbi.nlm.nih.gov/16198775/",
                         "0.25% (95% CI 0.18-0.31), 520,000, 11% of psoriasis confirmed in the abstract; no survey year in the abstract (table had 'about 2003')",
                         {"prevalence_year": "not stated in abstract (published 2005)"}),
    "karmacharya_psa_2021": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC8476658",
                             "incidence 8.5/100,000 (2000-2017) and point prevalence 181.8/100,000 (2015) confirmed in full text", {}),
    "reveille_weisman_axspa": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC4122314/", None, {}),
    "ad_in_america_2019": ("https://hsrc.himmelfarb.gwu.edu/smhs_derm_facpubs/409",
                           "abstract read on the GWU repository page: 7.3% (5.9-8.8) of 1,278 adults, 16.5M adults, 6.6M moderate-to-severe confirmed. Upgraded from secondary; adults only",
                           {"confidence": "medium", "source_name": "Chiesa Fuxench et al, J Invest Dermatol 2019 (abstract on GWU repository)"}),
    "garg_hs_2017": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC5710402/",
                     f"0.10% / 98 per 100,000 (women 137, men 58) confirmed in PMC text. Count DERIVED 0.10% x {TOTAL:,} total US = {round(0.001 * TOTAL):,} (EHR sample rate applied to all ages)",
                     {"us_prevalence_n": round(0.001 * TOTAL)}),
    "thorne_niu_2016": ("https://pubmed.ncbi.nlm.nih.gov/27608193/",
                        "121/100,000 adults, 29/100,000 children, anterior 81% confirmed; the abstract also states 298,801 adults (95% CI 290,512-307,324) and 21,879 children in 2015 (authors' extrapolation), now filled",
                        {"us_prevalence_n": 298801, "prevalence_year": "2015 (authors' extrapolation of 2012 claims rates)"}),
    "chandran_gca_2015": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC4431922",
                          "incidence 19.8 (95% CI 15.2-24.3) per 100,000 aged 50+ (2000-2009, 74 cases) confirmed; prevalence 204 (161-254) per 100,000 aged 50+ on 1 Jan 2015 now confirmed in the Crowson 2017 abstract (PMID 28551169), no longer secondary",
                          {"note": "Incidence 19.8 per 100,000 aged 50+ (74 cases 2000-2009). Prevalence 204 per 100,000 aged 50+ on 1 Jan 2015 (Crowson and Matteson, Semin Arthritis Rheum 2017, primary abstract read; adjusted to US white 2010 population 50+). Single-county, predominantly white; no national count"}),
    "niddk_nafld_nash": ("https://www.niddk.nih.gov/health-information/liver-disease/nafld-nash/definition-facts",
                         "24% NAFLD and 1.5%-6.5% NASH confirmed; page Last Reviewed April 2021. Superseded for the funnel by Estes 2018 (16.52M)", {}),
    "benjafield_osa_2019": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC7007763/",
                            "Table 3 USA row confirmed: population 30-69 163,246,772; AHI>=5 54,131,654 (33.2%); AHI>=15 23,678,109 (14.5%)", {}),
    "cdc_meso_brief": ("https://stacks.cdc.gov/view/cdc/115967",
                       "2,875 cases in 2018 confirmed; brief PDF Table 1 (1999-2018) gives pleura 82.1% of 62,550 cases, so pleural 2018 is about 2,360 (DERIVED, not stored)", {}),
    "paulson_mcc_jaad": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC5815902",
                         "0.7 per 100,000 person-years and 2,488 cases (2013), projections 2,835 (2020) and 3,284 (2025) confirmed", {}),
    "rogers_nmsc_2015": ("https://pubmed.ncbi.nlm.nih.gov/25928283/",
                         "5,434,193 NMSC tumors and 3,315,554 persons treated (2012), BCC:SCC 1.0 in Medicare confirmed. ALL NMSC, not cSCC: the funnel uses the Karia 2013 row instead", {}),
    "quock_al_2018": ("https://pubmed.ncbi.nlm.nih.gov/29748430/",
                      "40.5 per million (2015), 15.5 (2007), at least 12,000 adults confirmed; incidence 9.7-14.0 per million person-years IS in the abstract (table note said it was not)",
                      {"note": "40.5 cases per million in 2015 (15.5 per million in 2007); 'at least 12,000 adults'. Incidence 9.7 to 14.0 per million person-years, no significant trend (abstract). Prothena-funded claims study"}),
}
AXSPA_AMOR = (f"0.9% (95% CI 0.7-1.1) Amor and 1.4% ESSG confirmed in PMC text; the paper calls it 'definite and probable SpA' in the axial SpA section; "
              f"ages 20-69. Count DERIVED 0.9% x {ADULTS / 1e6:.1f}M adults 18+ = {round(0.009 * ADULTS):,} (age band mismatch: 20-69 rate on an 18+ base)")
AXSPA_AS = "28 of 5,013 NHANES 2009-2010 participants reported an AS diagnosis confirmed (unweighted 0.56%); abstract range 0.52-0.55%"

SHARE_FIX = {
    "acs_lung_what_is": ("https://www.cancer.org/cancer/types/lung-cancer/about/what-is.html", "confirmed; ACS page Last Revised January 29, 2024", {}),
    "seer_breast_subtypes": ("https://seer.cancer.gov/statfacts/html/breast-subtypes.html", "confirmed to the SEER 21 2019-2023 subtype table cells", {}),
    "midha_egfr_2015": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC4633915", "Table 1 USA row confirmed: 16 studies, 1531/6663, 23% (range 3-42); 1531/6663 = 22.98%. Table cells quoted by the fetch tool (PMC XML has abstract only)", {}),
    "npf_psoriasis_statistics": ("https://www.psoriasis.org/psoriasis-statistics/", "'Nearly one-quarter' confirmed on the live NPF page (advocacy source)", {}),
    "gelfand_psa_2005": ("https://pubmed.ncbi.nlm.nih.gov/16198775/", "71 of 601, 11% (95% CI 9-14) confirmed in the abstract; no survey year in the abstract", {"year": "not stated (published 2005)"}),
    "hess_pcsk9_ahj_2017": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC5961484", "eligibility sentences confirmed (any statin 60.6%, high-intensity 23.3% at LDL-C >=70); the paper prints the same three numbers as the statin-use shares, so treat as ambiguous", {}),
    "cannon_pcsk9_esc2016_secondary": ("https://jamanetwork.com/journals/jamacardiology/fullarticle/2646531",
                                       "primary found: Cannon et al JAMA Cardiol 2017 abstract, 1 million simulated ASCVD patients: 67.3% statin, 18.7% statin + ezetimibe, 14% add-on PCSK9i to reach LDL-C <70",
                                       {"source": "cannon_jama_cardiol_2017", "source_url": "https://jamanetwork.com/journals/jamacardiology/fullarticle/2646531",
                                        "confidence": "medium", "year": "2017 simulation (claims-based model)",
                                        "note": "Simulation assumes no statin intolerance and full adherence; primary abstract read (was conference coverage)"}),
    "cdc_ndsr_table1a_secondary": ("https://stacks.cdc.gov/view/cdc/148231/cdc_148231_DS1.pdf",
                                   "Table 1a cell >=65 total 29.2 (26.4-32.1), diagnosed 24.4, undiagnosed 4.7 confirmed in the archived NDSR PDF (no longer secondary)",
                                   {"source": "cdc_ndsr_archived_pdf", "confidence": "medium",
                                    "note": "Archived NDSR edition (NHANES 2017-March 2020); diabetes prevalence WITHIN adults 65+, not the 65+ share of diabetics (that share is a separate row)"}),
    "SEER Cancer Stat Facts lung and bronchus": ("https://seer.cancer.gov/statfacts/html/lungb.html", "Distant (51%) confirmed on the saved Stat Facts copy", {}),
    "SEER Cancer Stat Facts female breast": ("https://seer.cancer.gov/statfacts/html/breast.html", "Distant (6%) confirmed on the saved Stat Facts copy", {}),
    "ad_in_america_2019": ("https://hsrc.himmelfarb.gwu.edu/smhs_derm_facpubs/409", "28.9% moderate + 11% severe confirmed in the repository abstract; 6.6M of 16.5M = 40.0% (abstract counts)",
                           {"confidence": "medium", "note": "Primary abstract read: 28.9% moderate + 11% severe (DERIVED sum 39.9%)"}),
    "nord_asps": ("https://rarediseases.org/rare-diseases/alveolar-soft-part-sarcoma/", "0.2%-1% confirmed on NORD and on the NCI rare tumor page", {}),
}


def epi_row(**k):
    r = {c: "" for c in COLS}
    r.update(k)
    return r


NEW_EPI = [
    epi_row(indication="juvenile arthritis (JIA / JPsA / ERA)", population_scope="children and adolescents <18, parent-reported diagnosed arthritis (all types, not JIA only), NSCH",
            us_prevalence_n=220000, us_prevalence_pct=0.305, prevalence_year="2017-2021", source_name="Arthritis Among Children and Adolescents Aged <18 Years, MMWR 2023;72(29)",
            source_url="https://www.cdc.gov/mmwr/volumes/72/wr/mm7229a3.htm", confidence="medium",
            note="220,000 (95% CI 187,000-260,000), 305 per 100,000; 77 per 100,000 under 6 to 592 at 12-17. Parent report of any provider-diagnosed arthritis, so it includes non-JIA types; CDC childhood arthritis page 404s",
            source="cdc_mmwr_child_arthritis_2023"),
    epi_row(indication="hATTR polyneuropathy", population_scope="ATTR-FAP (hATTR-PN), US, literature-based estimate",
            us_prevalence_n=476, prevalence_year="2016 literature model", source_name="Schmidt et al, Muscle Nerve 2018 (Pfizer-funded)",
            source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC5947118/", confidence="low",
            note="US mid 476 (low 104, high 2,488); the US input is an anecdotal 1/100,000 Caucasian estimate rated very high risk of bias, so this is likely a large undercount. SECONDARY context: Alnylam 10-K FY2025 says hATTR-PN affects fewer than 30,000 people worldwide (company estimate, no US split)",
            source="schmidt_attr_fap_2018"),
    epi_row(indication="pediatric thromboprophylaxis (Fontan)", population_scope="persons living with Fontan circulation, US, all ages (model)",
            us_prevalence_n=27401, prevalence_year="2020 (model)", source_name="Plappert et al, Adv Ther 2022 (funded by Actelion, a Janssen company)",
            source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8866255/", confidence="medium",
            note="27,401 US (82.4 per million); 11-country pool 55% adults, 17% 12-17, 28% under 12, so under-18 is about 45% (not US-specific). About 1,024 US Fontan operations a year. AHA 2019 statement (Rychik): up to 70,000 alive worldwide; its US figure is not in the abstract (full text 403). Xarelto's Fontan label is pediatric, so the all-ages count overstates the label population",
            source="plappert_fontan_2022"),
    epi_row(indication="atopic dermatitis", population_scope="US children 0-17, parent-reported eczema in past 12 months (NSCH 2003)",
            us_prevalence_pct=10.7, prevalence_year="2003", source_name="Shaw, Currie, Koudelka, Simpson. J Invest Dermatol 2011",
            source_url="https://pubmed.ncbi.nlm.nih.gov/20739951/", confidence="medium",
            note="10.7% of 102,353 children; state range 8.7-18.1%. Dated (2003). Not scaled to a count; the adult row (16.5M) is the funnel row. The 'about 13%' figure in the brief was not found in a primary source read",
            source="shaw_nsch_eczema_2011"),
    epi_row(indication="cutaneous squamous cell carcinoma", population_scope="invasive cSCC, US white population, 2012 (literature regression)",
            annual_incidence_n=302850, incidence_year="2012 (range 186,157-419,543)", source_name="Karia, Han, Schmults. J Am Acad Dermatol 2013",
            source_url="https://pubmed.ncbi.nlm.nih.gov/23375456/", confidence="low",
            note="186,157 to 419,543 whites diagnosed with invasive cSCC in 2012; stored value is the DERIVED midpoint 302,850. Background sentence: 'over 700,000 new cases ... annually' (all cSCC incl. in situ, cited estimate). 3,932 to 8,791 deaths",
            source="karia_cscc_2013"),
    epi_row(indication="alveolar soft part sarcoma", population_scope="US, all ages", annual_incidence_n=80, incidence_year="not stated (page posted 2019)",
            source_name="NCI Pediatric and Adult Rare Tumor page: Alveolar Soft Part Sarcoma",
            source_url="https://www.cancer.gov/pediatric-adult-rare-tumor/rare-tumors/rare-soft-tissue-tumors/alveolar-soft-part-sarcomas", confidence="medium",
            note="'about 80 cases diagnosed per year in the United States'; 0.2% to 1% of soft tissue sarcomas. No prevalence", source="nci_asps"),
    epi_row(indication="MASH", population_scope="prevalent NASH (MASH), US, Markov model", us_prevalence_n=16520000, prevalence_year="2015 (model)",
            source_name="Estes, Razavi, Loomba, Younossi, Sanyal. Hepatology 2018", source_url="https://pubmed.ncbi.nlm.nih.gov/28802062/", confidence="medium",
            note="16.52M NASH (2015) rising to 27.00M (2030); 83.1M NAFLD. About 20% of NAFLD is NASH. SECONDARY: Madrigal 10-K FY2025 estimates 315,000 diagnosed F2-F3 MASH patients under specialist care (company estimate; the drug-eligible diagnosed pool). The Younossi 2023 Hepatology US figure was not located",
            source="estes_nash_2018"),
    epi_row(indication="established CVD risk reduction (MACE)", population_scope="adults 20+, CVD excluding hypertension (CHD, HF, stroke), NHANES 2017-March 2020",
            us_prevalence_n=28600000, us_prevalence_pct=9.9, prevalence_year="2020 (NHANES 2017-March 2020)",
            source_name="AHA 2025 Heart Disease and Stroke Statistics (Martin et al, Circulation 2025)", source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12256702/", confidence="high",
            note="CVD incl. hypertension 48.6% (127.9M). CHD 20.5M (7.1%); MI 3.2%; stroke 9.4M (3.3%); HF 6.7M; all adults 20+, NHANES 2017-2020. Label populations differ (Wegovy: established CVD with obesity/overweight; Repatha/Praluent: ASCVD; Xarelto: CAD/PAD), so this is an upper bound",
            source="aha_stats_2025"),
]

NEW_SHARES = [
    dict(indication="type 2 diabetes", subset="adults 65+ share of all adults with diabetes (diagnosed + undiagnosed)", share_pct=43.3, numerator=16.5e6, denominator=38.1e6, year="2021",
         source="cdc_ndsr_archived_pdf", source_url="https://stacks.cdc.gov/view/cdc/148231/cdc_148231_DS1.pdf", confidence="medium",
         note="DERIVED 16.5M / 38.1M from Table 1b (number in millions, 2021); diagnosed only 13.8 / 29.4 = 46.9%. Archived NDSR edition; the live page has no age split"),
    dict(indication="type 2 diabetes", subset="adults 65+ share of adults with diagnosed diabetes", share_pct=46.9, numerator=13.8e6, denominator=29.4e6, year="2021",
         source="cdc_ndsr_archived_pdf", source_url="https://stacks.cdc.gov/view/cdc/148231/cdc_148231_DS1.pdf", confidence="medium",
         note="DERIVED 13.8M / 29.4M from Table 1b"),
    dict(indication="colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H", subset="dMMR share of advanced (metastatic) sporadic colorectal cancer", share_pct=3.5, numerator=18, denominator=515, year="phase III trial cohort (CAIRO, published 2009)",
         source="koopman_dmmr_2009", source_url="https://pubmed.ncbi.nlm.nih.gov/19165197/", confidence="medium",
         note="Dutch phase III trial cohort, sporadic only (excludes Lynch), IHC + MSI; not US population"),
    dict(indication="colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H", subset="dMMR share of sporadic colorectal cancer, all stages", share_pct="10-20", numerator="", denominator="", year="cited background",
         source="koopman_dmmr_2009", source_url="https://pubmed.ncbi.nlm.nih.gov/19165197/", confidence="low",
         note="SECONDARY within a primary paper: background sentence of Koopman 2009 citing earlier work; the 15% overall figure was not read in a primary US cohort"),
    dict(indication="malignant pleural mesothelioma", subset="pleural share of all malignant mesothelioma cases", share_pct=82.1, numerator=51338, denominator=62550, year="1999-2018",
         source="cdc_meso_brief", source_url="https://stacks.cdc.gov/view/cdc/115967", confidence="high",
         note="USCS Data Brief 27 Table 1; 47 registries, 97% of US population. Applied to 2,875 cases in 2018 gives about 2,360 pleural (DERIVED)"),
    dict(indication="pediatric thromboprophylaxis (Fontan)", subset="under-18 share of persons living with Fontan (11-country pool)", share_pct=45, numerator="", denominator="", year="2020 (model)",
         source="plappert_fontan_2022", source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8866255/", confidence="medium",
         note="DERIVED 17% adolescents + 28% children; pooled across 11 countries, not US-specific"),
]

PB_PAGE = {"cdc_mmwr_child_arthritis_2023": "https://www.cdc.gov/mmwr/volumes/72/wr/mm7229a3.htm", "schmidt_attr_fap_2018": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5947118/",
           "plappert_fontan_2022": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8866255/", "shaw_nsch_eczema_2011": "https://pubmed.ncbi.nlm.nih.gov/20739951/",
           "karia_cscc_2013": "https://pubmed.ncbi.nlm.nih.gov/23375456/",
           "nci_asps": "https://www.cancer.gov/pediatric-adult-rare-tumor/rare-tumors/rare-soft-tissue-tumors/alveolar-soft-part-sarcomas",
           "estes_nash_2018": "https://pubmed.ncbi.nlm.nih.gov/28802062/", "aha_stats_2025": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12256702/",
           "cdc_ndsr_archived_pdf": "https://stacks.cdc.gov/view/cdc/148231/cdc_148231_DS1.pdf", "koopman_dmmr_2009": "https://pubmed.ncbi.nlm.nih.gov/19165197/",
           "cdc_meso_brief": "https://stacks.cdc.gov/view/cdc/115967"}
PB_EXTRA = {"schmidt_attr_fap_2018": "https://www.sec.gov/Archives/edgar/data/1178670/000162828026007497/alny-20251231.htm",
            "plappert_fontan_2022": "https://pubmed.ncbi.nlm.nih.gov/31256636/", "estes_nash_2018": "https://www.sec.gov/Archives/edgar/data/1157601/000162828026009514/mdgl-20251231.htm"}

# indication -> source key of the row the funnel uses
FUNNEL_PICK = {"psoriatic arthritis": "gelfand_psa_2005", "ankylosing spondylitis / axSpA": "reveille_weisman_axspa|Amor",
               "atopic dermatitis": "ad_in_america_2019", "MASH": "estes_nash_2018", "established CVD risk reduction (MACE)": "aha_stats_2025",
               "cutaneous squamous cell carcinoma": "karia_cscc_2013"}
SUBSET = {"juvenile arthritis (JIA / JPsA / ERA)": "denominator is all parent-reported childhood arthritis, not JIA only",
          "malignant pleural mesothelioma": "denominator is all-site mesothelioma incidence (pleural about 82%)",
          "cutaneous squamous cell carcinoma": "denominator is invasive cSCC incidence in whites (midpoint), not prevalence",
          "established CVD risk reduction (MACE)": "denominator is all CVD excluding hypertension (CHD, HF, stroke), broader than each label",
          "hATTR polyneuropathy": "denominator is a low-quality US estimate (likely undercount); Amvuttra floor also covers ATTR-CM",
          "obstructive sleep apnea (with obesity)": "denominator is moderate-severe OSA ages 30-69, not OSA with obesity",
          "pediatric thromboprophylaxis (Fontan)": "denominator is all-ages Fontan; label is pediatric",
          "atopic dermatitis": "denominator is adults only",
          "ankylosing spondylitis / axSpA": "denominator DERIVED from a 20-69 rate on an 18+ base",
          "hidradenitis suppurativa": "denominator DERIVED from an EHR-sample rate",
          "venous thromboembolism (DVT/PE)": "denominator is an upper-bound annual incidence ('up to 900,000')",
          "MASH": "denominator is all modelled NASH (2015); diagnosed F2-F3 pool is about 315,000 (Madrigal 10-K, secondary)",
          "alveolar soft part sarcoma": "denominator is annual incidence (about 80 cases)",
          "Merkel cell carcinoma": "denominator is 2013 annual incidence"}

AI_WRONG = [
    ("indication_epidemiology_wave3", "psoriatic arthritis|gelfand_psa_2005", "prevalence_year 'about 2003 survey'", "abstract gives no survey year (published 2005)", "unsupported_value", "low", "re-read PubMed abstract"),
    ("indication_epidemiology_wave3", "AL amyloidosis|quock_al_2018", "'Incidence reported stable but the value is not in the saved abstract text'", "abstract: 'The incidence ranged from 9.7 to 14.0 cases per million person-years'", "omission", "low", "re-read PubMed abstract"),
    ("indication_epidemiology_wave3", "uveitis|thorne_niu_2016", "'not scaled to a US count' (us_prevalence_n blank)", "abstract: NIU affected approximately 298 801 American adults ... and 21 879 children in 2015", "omission", "low", "re-read PubMed abstract"),
    ("indication_subset_shares", "hypercholesterolemia|cannon_pcsk9_esc2016_secondary", "14% cited to MDedge conference coverage, 'page not read'", "primary JAMA Cardiol 2017 abstract (1 million simulated patients) states the 14%", "secondary_when_primary_available", "low", "web search then JAMA abstract"),
    ("gaps/epi.jsonl", "hATTR polyneuropathy", "Alnylam 10-K 'about 50,000 hATTR, about 10,000 predominantly polyneuropathy'", "Alnylam 10-K FY2025: 'hATTR amyloidosis with polyneuropathy affects fewer than 30,000 people worldwide' (50,000 is the FY2018 filing)", "stale_value", "low", "read current 10-K"),
    ("gaps/epi.jsonl", "MASH", "brief asked for 'Younossi et al 2023 Hepatology US NASH prevalence'", "PubMed search for that citation returns a J Hepatol research-agenda paper (Lazarus 2023) with no US prevalence; the US model figure is Estes et al, Hepatology 2018", "citation_mismatch", "low", "PubMed esearch + abstract"),
]


def main():
    retrieved = now()
    write("verify_epi", "epi/sources/primary_recheck_wave3.md", render(retrieved), group="epi", doc_type="source_quotes",
          quality="verified", source_url="multiple primary pages (see each page)")

    # ---- Part A: indication_epidemiology_wave3 ----
    w = pd.read_csv(M / "tables/indication_epidemiology_wave3.csv", dtype=str, keep_default_na=False)
    out = []
    for _, r in w.iterrows():
        d = {c: r.get(c, "") for c in COLS}
        url, chk, fix = EPI_FIX[r.source]
        if r.source == "reveille_weisman_axspa":
            if "Amor" in r.population_scope:
                chk, fix = AXSPA_AMOR, {"us_prevalence_n": round(0.009 * ADULTS)}
            else:
                chk = AXSPA_AS
        d.update({k: v for k, v in fix.items()})
        d["checks"] = "re-read on the live primary page | " + chk
        d["source_copy"] = COPY.format(PAGE_NO[url])
        d["source"] = f"{url} | local data/moat/epi/sources/primary_recheck_wave3.md p{PAGE_NO[url]}"
        d["source_row"] = f"{r.indication}|{r.source}" + ("|Amor" if "Amor" in r.population_scope else ("|AS" if r.source == "reveille_weisman_axspa" else ""))
        d["source_local"], d["source_page"] = "epi/sources/primary_recheck_wave3.md", PAGE_NO[url]
        errs = [e for e in AI_WRONG if e[0] == "indication_epidemiology_wave3" and e[1].split("|")[1] == r.source]
        d["n_errors"] = len(errs)
        d["errors"] = "; ".join(f"{e[2]} vs source {e[3]}" for e in errs)
        out.append(d)
    n_epi_a = len(out)
    for d in NEW_EPI:
        key = d["source"]
        url = PB_PAGE[key]
        d = dict(d)
        extra = f"; also p{PAGE_NO[PB_EXTRA[key]]}" if key in PB_EXTRA else ""
        d["checks"] = f"Part B: new row from the primary page read 2026-10-17{extra}"
        d["source_copy"] = COPY.format(PAGE_NO[url])
        d["source_local"], d["source_page"] = "epi/sources/primary_recheck_wave3.md", PAGE_NO[url]
        d["source_row"] = f"{d['indication']}|{key}"
        d["source"] = f"{url} | local data/moat/epi/sources/primary_recheck_wave3.md p{PAGE_NO[url]}"
        d["n_errors"], d["errors"] = 0, ""
        out.append(d)
    new = pd.DataFrame(out, columns=COLS)
    base = pd.read_csv(M / "verified/epi/indication_epidemiology.csv", dtype=str, keep_default_na=False)
    base = base.iloc[:30]  # the 30 verified wave 1-2 rows, untouched
    allv = pd.concat([base, new.astype(str).replace({"nan": ""})], ignore_index=True)
    buf = io.StringIO()
    allv.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/indication_epidemiology.csv", buf.getvalue(), group="tables", doc_type="table", quality="verified",
          source_url="data/moat/tables/indication_epidemiology.csv + indication_epidemiology_wave3.csv + Part B primary pages")
    empty = io.StringIO()
    pd.DataFrame(columns=COLS + ["drop_reason"]).to_csv(empty, index=False)
    write("verify_epi", "verified/epi/indication_epidemiology_dropped.csv", empty.getvalue(), group="tables", doc_type="table", quality="verified",
          source_url="data/moat/tables/indication_epidemiology_wave3.csv")

    # ---- Part A: subset shares ----
    s = pd.read_csv(M / "tables/indication_subset_shares.csv", dtype=str, keep_default_na=False)
    rows = []
    for _, r in s.iterrows():
        d = r.to_dict()
        url, chk, fix = SHARE_FIX[r.source]
        d.update(fix)
        d["checks"] = "re-read on the live primary page | " + chk
        d["source_copy"] = COPY.format(PAGE_NO[url])
        d["page"] = PAGE_NO[url]
        errs = [e for e in AI_WRONG if e[0] == "indication_subset_shares" and e[1].split("|")[1] == r.source]
        d["n_errors"], d["errors"] = len(errs), "; ".join(f"{e[2]} vs source {e[3]}" for e in errs)
        rows.append(d)
    n_sh_a = len(rows)
    for d in NEW_SHARES:
        d = dict(d)
        url = PB_PAGE[d["source"]]
        d.update(checks="Part B: new row from the primary page read 2026-10-17", source_copy=COPY.format(PAGE_NO[url]), page=PAGE_NO[url], n_errors=0, errors="")
        rows.append(d)
    sh = pd.DataFrame(rows)
    buf = io.StringIO()
    sh.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/indication_subset_shares.csv", buf.getvalue(), group="tables", doc_type="table", quality="verified",
          source_url="data/moat/tables/indication_subset_shares.csv + Part B primary pages")
    opened = pd.DataFrame([
        dict(indication="Crohn's disease / ulcerative colitis", subset="moderate-to-severe share", drop_reason="no US primary cohort read: the only open-access severity table found is a Canadian self-rated activity survey (Hilsden 2003, PMC166136); treatment-defined claims studies give incidence, not a share"),
        dict(indication="HR+/HER2- breast cancer", subset="metastatic (distant) share of HR+/HER2-", drop_reason="not published on SEER subtype page (gives distant-stage survival only); all-breast distant 6% kept"),
        dict(indication="NSCLC", subset="stage IV share of NSCLC only", drop_reason="not published by SEER Stat Facts (all lung distant 51% kept)"),
    ])
    buf = io.StringIO()
    opened.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/indication_subset_shares_dropped.csv", buf.getvalue(), group="tables", doc_type="table", quality="verified",
          source_url="Part B share requests not confirmable")

    # ---- funnel extension ----
    msi = pd.read_csv(M / "verified/epi/market_sizing_inputs.csv", dtype=object, keep_default_na=False)  # rerun-safe: only "no collected epidemiology" rows are filled
    before = int(msi.method_note.str.startswith("funnel", na=False).sum())
    before_pct = int((msi.medicare_floor_pct_of_denominator != "").sum())
    pick = {}
    for ind, grp in new.groupby("indication", sort=False):
        want = FUNNEL_PICK.get(ind)
        cand = [e for _, e in grp.iterrows() if (want is None or want in e.source_row)]
        cand = [e for e in cand if str(e.us_prevalence_n) not in ("", "nan") or str(e.annual_incidence_n) not in ("", "nan")]
        if cand:
            pick[ind] = cand[0]
    filled = 0
    for i, r in msi.iterrows():
        if not str(r.method_note).startswith("no collected epidemiology") or r.indication not in pick:
            continue
        e = pick[r.indication]
        num = lambda v: float(v) if str(v) not in ("", "nan") else None  # noqa: E731
        prev, inc, diag = num(e.us_prevalence_n), num(e.annual_incidence_n), num(e.diagnosed_n)
        if prev is None and inc is None:
            continue
        denom, basis = (diag, "diagnosed") if diag else ((prev, "prevalent") if prev else (inc, "incident"))
        floor = num(r.medicare_partd_benes_on_drug_2024_floor)
        note = [f"funnel: prevalence {int(prev):,} ({e.prevalence_year}); diagnosed {e.diagnosed_share or 'n/a'}%; treated {e.treated_share or 'n/a'}%" if prev else
                f"funnel: prevalence n/a; annual incidence {int(inc):,} ({e.incidence_year}); diagnosed n/a%; treated n/a%"]
        if floor:
            note.append(f"Medicare Part D 2024 beneficiaries on {r.drug} (floor) {int(floor):,} = {floor / denom * 100:.2f}% of {basis} US patients")
        rest = str(r.method_note).split(" | ")[1:]
        note += [x for x in rest if not x.startswith("Medicare Part D 2024")]
        note.append(f"wave 3 epi (verified): {e.source_copy}")
        msi.loc[i, ["us_prevalence_n", "prevalence_year", "annual_incidence_n", "diagnosed_share_pct", "diagnosed_n", "class_treated_share_pct", "share_aged_65plus"]] = [
            prev, e.prevalence_year or None, inc, num(e.diagnosed_share), diag, num(e.treated_share), num(e.share_aged_65plus)]
        pct = round(floor / denom * 100, 3) if floor else None
        msi.loc[i, "medicare_floor_pct_of_denominator"] = pct
        msi.loc[i, "denominator_basis"] = basis
        msi.loc[i, "denominator_n"] = denom
        msi.loc[i, "floor_pct_recomputed"] = pct
        msi.loc[i, "floor_pct_ok"] = True if floor else None
        msi.loc[i, "denominator_matches_verified_epi"] = True
        msi.loc[i, "method_note"] = " | ".join(note)
        msi.loc[i, "source"] = e.source_url + " ; " + str(r.source).split(" ; ", 1)[-1]
        msi.loc[i, "subset_caveat"] = SUBSET.get(r.indication, "")
        msi.loc[i, "epi_confidence"] = e.confidence
        filled += 1
    for i, r in msi[msi.method_note.str.contains("wave 3 epi", na=False)].iterrows():
        p = pd.to_numeric(r.medicare_floor_pct_of_denominator, errors="coerce")
        tag = "floor exceeds the denominator: the drug-level Part D floor is dominated by other indications, do not read as penetration"
        if pd.notna(p) and p > 100 and tag not in str(r.subset_caveat):
            msi.loc[i, "subset_caveat"] = (str(r.subset_caveat) + "; " if str(r.subset_caveat) else "") + tag
    after = int(msi.method_note.str.startswith("funnel", na=False).sum())
    after_pct = int(msi.medicare_floor_pct_of_denominator.fillna("").astype(str).ne("").sum())
    buf = io.StringIO()
    msi.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/market_sizing_inputs.csv", buf.getvalue(), group="tables", doc_type="table", quality="verified",
          source_url="data/moat/tables/market_sizing_inputs.csv + verified/epi/indication_epidemiology.csv (wave 3)")

    # ---- ai_wrong ----
    aw = M / "verify/ai_wrong.jsonl"
    have = aw.read_text() if aw.exists() else ""
    with aw.open("a") as f:
        for t, k, a, src, et, sev, how in AI_WRONG:
            if f'"row_key": "{k}"' in have and '"stream": "epi"' in have:
                continue
            f.write(json.dumps(dict(stream="epi", table=t, row_key=k, what_the_ai_wrote=a, what_the_source_says=src, error_type=et, severity=sev,
                                    how_caught=how, count=1, example_cite="data/moat/epi/sources/primary_recheck_wave3.md")) + "\n")
    stats = dict(epi_a=n_epi_a, shares_a=n_sh_a, epi_new=len(NEW_EPI), shares_new=len(NEW_SHARES), funnel_before=before, funnel_after=after,
                 floor_pct_before=before_pct, floor_pct_after=after_pct, filled=filled, picked=sorted(pick), pages=len(PAGE_NO))
    print(json.dumps(stats, indent=1))
    print(msi[msi.method_note.str.contains("wave 3 epi", na=False)][["drug", "indication", "denominator_basis", "denominator_n", "medicare_floor_pct_of_denominator"]].to_string())
    return stats


if __name__ == "__main__":
    main()
