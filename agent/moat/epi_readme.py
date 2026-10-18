import pandas as pd

from agent.moat.common import OUT, write

m = pd.read_csv(OUT / "tables" / "indication_map.csv")
e = pd.read_csv(OUT / "tables" / "indication_epidemiology.csv")
have = set(e.indication)
vocab = m.groupby("indication").drug.apply(lambda s: ", ".join(sorted(set(s)))).reset_index()
lines = ["# epi stream: indication market sizing", "",
         "Keyed by indication, not company, so the engine can size any drug. Built by agent/moat/epi_map.py, epi_build.py, epi_market.py.", "",
         "## Tables (data/moat/tables)", "",
         "- indication_map.csv: drug -> controlled-vocabulary indication, with the label section number and heading (source: DailyMed label in data/corpus/drugs/<drug>/label_sections.md, section 1).",
         "- indication_epidemiology.csv: per indication US prevalence, incidence, diagnosed and treated share, share aged 65+, 5-year survival, source name, URL, local page-marked copy and page.",
         "- medicare_market.csv: per drug and class, Medicare Part D claims, spend and beneficiaries by period (benes floor = largest presentation; sum = ceiling), joined to Medicaid SDUD prescriptions.",
         "- market_sizing_inputs.csv: per drug x indication funnel with `method_note` showing the math. Medicare beneficiaries are drug-level and cannot be split by indication.", "",
         "## Source documents (data/moat/epi/sources, page-marked)", "",
         "- seer_*.md: NCI SEER Cancer Stat Facts pages (18 sites), fetched 2026-10-17 (estimates for 2026, prevalence as of 2023, survival 2016-2022). Page 1 cited.",
         "- web_extracts.md: one page per source for cdc.gov pages the shell cannot download (cdc.gov returns 403 to curl); read through a web fetch tool and transcribed with the exact numbers and URL. Each epidemiology row cites the page number here. These are extracts, not full copies.",
         "- niddk_diabetes.md (2021 diabetes statistics), niddk_obesity.md (no counts), niams_ra.md (no counts), pmc_af_prevalence_2019_2023.md (Epic Cosmos AF), pmc_ibd_medicare_mmwr.md (MMWR Medicare IBD), pmc_attr_epidemiology_review.md.", "",
         "## Primary sources used", "",
         "- NCI SEER Cancer Stat Facts (cancers); CDC diabetes data page (2023); NCHS Data Brief 508 (obesity, NHANES 2021-2023); NCHS Data Brief 363 and 177 (cholesterol, statin use); CDC HIV facts and stats (2022); NCHS Health E-Stat 122 (IBD, NHIS 2023-2024); Armstrong JAMA Dermatol 2021 (psoriasis, NHANES); Helmick 2008 (RA, CDC authors); Census QuickFacts (population base); CMS CCW chronic condition charts (via search summary only); CMS Part D spending by drug and Medicaid SDUD (already in the moat).",
         "- Secondary and flagged: Epic Cosmos AF cohort (peer-reviewed EHR study, not a CDC count), ATTR-CM literature, PrEP indication estimate (CDC MMWR 2015).", "",
         "## Controlled vocabulary (indication -> case drugs; E = epidemiology row present)", ""]
for _, r in vocab.iterrows():
    lines.append(f"- {r.indication} [{'E' if r.indication in have else 'no epi'}]: {r.drug}")
lines += ["", "## Caveats", "",
          "- Derived counts (obesity, AF, high cholesterol) multiply a published rate by Census 18+ population (269.7M, derived from QuickFacts); marked DERIVED in the note column.",
          "- Cancer rows give whole-site prevalence and incidence; stage, line of therapy and biomarker subset shares (NSCLC share of lung, HR+/HER2- share of breast, EGFR-mutant share, MSI-H share) are not collected.",
          "- Part D floors count Medicare Part D beneficiaries only (no Medicare Advantage medical-benefit drugs such as Part B oncology infusions); Part B oncology drugs (Keytruda, Opdivo, Darzalex IV) are far understated in Part D data and need Part B counts.",
          "- Prevalence years differ across sources (2005 to 2023)."]
write("epi", "epi/README.md", "\n".join(lines) + "\n", group="epi", doc_type="epi_doc")
print("ok")
