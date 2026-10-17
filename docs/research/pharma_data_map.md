# Pharma data map: LOE and pricing for a 3-company comparison

Prepared 2026-10-16 (Friday night) for the Sat-Sun build. Every URL below was fetched live on 2026-10-16 with curl (HTTP 200 or 206 unless noted). Sizes are measured, not guessed. All sources are free and need no API key unless stated.

The question the tool answers, per product: **"When does it lose exclusivity, and when does its price change?"** Then roll up to: which of the three companies has the most revenue at risk, how soon, and what the CEO should do.

---

## 0. TL;DR: pull tonight (ranked)

| # | Source | Must / Nice | Size | Minutes | Why |
|---|---|---|---|---|---|
| 1 | Orange Book data ZIP | MUST | 1.1 MB | <1 | Patent + exclusivity dates per small-molecule NDA. Core of LOE. |
| 2 | IRA Selected Drug List + MFP ZIP | MUST | 45 KB | <1 | The single best "when does pricing change" file. Has MFP, effective dates, and deselections caused by generic entry. |
| 3 | SEC 10-K XBRL instance (`*_htm.xml`) for each of the 3 companies, latest 10-K + latest 10-Q | MUST | ~6 MB each, ~40 MB total | 2 | Product-level revenue (ProductOrServiceAxis members). Not in companyfacts. |
| 4 | SEC `company_tickers.json` + submissions JSON for 3 CIKs | MUST | 0.8 MB + ~150 KB each | <1 | ticker to CIK to accession numbers. |
| 5 | CMS Medicare Part D Spending by Drug (annual, DY2024) CSV | MUST | 5.3 MB | <1 | Spend per dosage unit 2020-2024, YoY change and CAGR already computed. |
| 6 | Purple Book monthly CSV (Sept 2026) | MUST if any company has big biologics | 0.5 MB | <1 | Biologic reference product exclusivity, biosimilars, interchangeability. |
| 7 | FDA Paragraph IV certifications list (xlsx) | MUST | 160 KB | <1 | Which brands are challenged, first filing date, ANDA count, 180-day status, first commercial marketing. |
| 8 | openFDA NDC directory ZIP | MUST (it is the join bridge) | 28 MB | 1 | NDC to application number (NDA/BLA) to brand. Links CMS/IRA/NADAC (NDC-keyed) to FDA (application-keyed). |
| 9 | Drugs@FDA data ZIP | MUST | 6.1 MB | <1 | Sponsor names, approval dates, supplements (new indications = lifecycle extension signal). |
| 10 | CMS Part B Spending by Drug CSV | Nice (MUST if a company sells infused/oncology drugs) | 0.3 MB | <1 | ASP-based, near-net price per unit for physician-administered drugs. |
| 11 | CMS Quarterly Part D Spending (2025 Q1-Q4) CSV | Nice | small | <1 | Freshest Medicare spend (2025), no per-unit field. |
| 12 | NADAC 2026 weekly (API per drug, or full CSV) | Nice | 107 MB CSV, or a few KB per API call | 5 (CSV) | Pharmacy acquisition cost per unit, weekly; shows generic price collapse after LOE. |
| 13 | companyfacts JSON for 3 CIKs | Nice | ~4.5 MB each | <1 | Clean total revenue, R&D, margin history for the company-level slide. |
| 14 | ClinicalTrials.gov API v2, Phase 3 by sponsor | Nice | a few MB | 2 | Pipeline replacements for the "what fills the gap" recommendation. |
| 15 | Medicaid State Drug Utilization Data 2025 | Skip unless time | 509 MB | 14 | Medicaid units and reimbursement by NDC. Filter by NDC via API instead. |
| 16 | SEC Financial Statement and Notes data set (2026_02) | Skip | 329 MB | 10+ | Dimensional facts for all filers; overkill for 3 companies. |
| 17 | SEC bulk `companyfacts.zip` / `submissions.zip` | Skip | 1.4 GB / 1.6 GB | 20+ | You only need 3 CIKs. |

Total for items 1-11: about 90 MB, under 10 minutes on a home connection.

---

## 1. FDA Orange Book (small molecules, NDA patents and exclusivities)

- Landing page: https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files
- Direct ZIP: **https://www.fda.gov/media/76860/download** (1,099,838 bytes; unzips to products.txt 7.5 MB / 48,864 rows, patent.txt 1.2 MB / 22,437 rows, exclusivity.txt 78 KB / 2,420 rows). Current files are dated Oct 9, 2026.
- Format: ASCII, tilde (`~`) delimited, header row. Read with `encoding='latin-1'`, `sep='~'`.
- Cadence: monthly (daily patent/exclusivity updates appear only in the web search). openFDA mirror exists but the ZIP is simpler.
- Auth / limits: none.

**Fields (verified headers)**

- `products.txt`: Ingredient, DF;Route, Trade_Name, Applicant (20-char short name, e.g. `MSD`), Strength, Appl_Type (N = NDA brand, A = ANDA generic), Appl_No, Product_No, TE_Code, Approval_Date, RLD, RS, Type (RX/OTC/DISCN), Applicant_Full_Name.
- `patent.txt`: Appl_Type, Appl_No, Product_No, Patent_No, Patent_Expire_Date_Text (includes PTE extensions), Drug_Substance_Flag, Drug_Product_Flag, Patent_Use_Code, Delist_Flag, Submission_Date.
  - **Pediatric extension**: a separate row with the patent number suffixed `*PED` (e.g. `7452872*PED`), date = base patent + 6 months. 2,337 such rows today.
- `exclusivity.txt`: Appl_Type, Appl_No, Product_No, Exclusivity_Code, Exclusivity_Date.
  - Code counts today: NCE 440, PED 345, NPP 170, NP 134, ODE* 94, PC 59, M-xx, GAIN 46, CGT 40, I-xxx (new indication), RTO, NS. NCE = 5-year new chemical entity, ODE = 7-year orphan, I-/NP = 3-year new clinical investigation, PC = 180-day generic exclusivity, PED = 6-month pediatric add-on. Full code list is in the Orange Book preface/appendix.

**Computing "earliest generic entry" per product (practical rule)**

Key = (Appl_No, Product_No) for Appl_Type = N.

1. `nce_block` = max NCE exclusivity date (+PED if present). An ANDA with a Paragraph IV can be filed at NCE minus 1 year, which triggers a 30-month stay, so while NCE runs, entry is usually not before NCE + 30 months unless litigation resolves.
2. `substance_patent` = max Patent_Expire_Date where Drug_Substance_Flag = Y, using the `*PED` row date if one exists for that patent. This "compound patent" date is the best single predictor of LOE.
3. `all_patents` = max of all listed patent dates (formulation and use patents). Upper bound; generics often design around or carve out use codes.
4. `other_excl` = max of ODE / I- / NP / M- exclusivity dates (may only block certain indications).
5. Estimated LOE = max(nce_block, substance_patent, other_excl relevant to the main indication). Report `all_patents` as "last listed patent".
6. **Override with the 10-K.** Settlements set the real date. Companies state it in Item 1 or the litigation note (e.g. "generic entry expected April 2028"). Show both: "Orange Book says X; company says Y; source: 10-K section".
7. Already-genericized check: count ANDA rows (`Appl_Type = A`) with the same Ingredient and DF;Route and Type = RX. If > 0, generics are approved (maybe not launched).

Sanity check run tonight (raw Orange Book only, no settlements applied):

| Brand | NDA | Applicant (short / full) | Last drug-substance patent | Last listed patent | Max exclusivity row | ANDA holders listed |
|---|---|---|---|---|---|---|
| ELIQUIS | 202155 | BRISTOL MYERS SQUIBB / BRISTOL MYERS SQUIBB CO PHARMACEUTICAL RESEARCH INSTITUTE | 6967208, Nov 21 2026 | 9326945*PED, Aug 24 2031 | PED, Oct 17 2028 | 13 |
| JANUVIA | 021995 | MSD / MERCK SHARP AND DOHME LLC | 7326708, Nov 24 2026 | 7326708*PED, May 24 2027 | none | 3 |
| VERZENIO | 208716 | ELI LILLY AND CO | 7855211, Sep 28 2031 | same | none | 0 |
| RINVOQ | 211675 | ABBVIE / ABBVIE INC | 9951080, Oct 17 2036 | 11607411, Mar 9 2038 | ODE-538, Apr 28 2032 | 0 |

This is why step 6 matters: ANDAs exist for Eliquis and Januvia, and the real entry dates come from settlements disclosed in the 10-K, not the patent list.

---

## 2. FDA Purple Book (biologics)

- Downloads page: https://purplebooksearch.fda.gov/downloads
- Latest file: **https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-September-data-download.csv** (487 KB, 2,276 lines). Also `.xlsx`. Pattern: `/PurpleBook/{YYYY}/purplebook-search-{Month}-data-download.csv` (capitalization is inconsistent: `january` lowercase, `February` onward capitalized). October 2026 not posted yet.
- Cadence: monthly. Auth: none.
- Layout: lines 1-25 are "changes this month" (N/R/U flag); **the full product list starts at line 26** (second header row). Parse from the second header.
- Columns: N/R/U, Applicant, BLA Number, Proprietary Name, Proper Name, License Type (`351(a)` = originator, `351(k)` = biosimilar, `351(k) Interchangeable`), Strength, Dosage Form, Route, Product Presentation, Marketing Status, Licensure, Approval Date, Inter. Approval Date, Ref. Product Proper Name, Ref. Product Proprietary Name, Supplement Number, Submission Type, Inter. Supplement Number, License Number, Product Number, Center, Date of First Licensure, Exclusivity Expiration Date, First Interchangeable Exclusivity Exp. Date, **Ref. Product Exclusivity Exp. Date** (12-year reference product exclusivity), Orphan Exclusivity Exp. Date, Patent List Provided.
- Biosimilar challengers per brand: filter rows where `Ref. Product Proprietary Name` = the brand (Humira, Stelara, etc.). Count 351(k) rows, earliest approval, any Interchangeable. (Example in September changes: Byooviz ranibizumab-nuna became interchangeable with Lucentis on Sep 4, 2026.)
- Caveat: reference exclusivity is often blank for older biologics, and biologic patents are not listed like Orange Book patents. For big biologics (Keytruda, Opdivo) use the 10-K stated LOE year.
- Companion page with biosimilar label links: https://www.fda.gov/drugs/biosimilars/biosimilar-product-information (HTML, current as of 10/05/2026).

---

## 3. Generic challenges: Paragraph IV list, first generics

**Paragraph IV Patent Certifications list**

- Page: https://www.fda.gov/drugs/abbreviated-new-drug-application-anda/patent-certifications-and-suitability-petitions
- XLSX: **https://www.fda.gov/media/194880/download?attachment** (161 KB, about 1,600 rows, "as of September 28, 2026")
- PDF copy: https://www.fda.gov/media/166048/download?attachment (3.2 MB)
- The old URL `/paragraph-iv-patent-certifications` is an archived 2019 page. Do not use it.
- Columns: DRUG NAME, DOSAGE FORM, STRENGTH, RLD/NDA (brand and NDA number in one cell separated by a newline, e.g. `Ziagen\n20977`), DATE OF SUBMISSION (first PIV ANDA received), NUMBER OF ANDAs SUBMITTED, 180-DAY STATUS, 180-DAY DECISION POSTING DATE, DATE OF FIRST APPLICANT APPROVAL, DATE OF FIRST COMMERCIAL MARKETING BY FTF, EXPIRATION DATE OF LAST QUALIFYING PATENT.
- It does NOT name the generic companies. Get names from the 10-K litigation note or ANDA holders in Orange Book products.txt.
- Cadence: roughly monthly. Join on NDA number (split the RLD/NDA cell, zero-pad to 6).
- Signal to show: "N generic filers challenged this patent estate since YYYY; first-filer 180-day status = X."

**First generic approvals**

- https://www.fda.gov/drugs/drug-and-biologic-approval-and-ind-activity-reports/first-generic-drug-approvals (HTML table, current as of 10/05/2026; `pandas.read_html`). Prior years linked from the same page.
- Use: confirms a brand already got its first generic and when.

---

## 4. Drugs@FDA (the regulatory join bridge)

- Page: https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files
- ZIP: **https://www.fda.gov/media/89850/download** (6.1 MB; files dated Oct 15, 2026). Tab-delimited.
- Files and keys:
  - `Applications.txt`: ApplNo, ApplType, ApplPublicNotes, **SponsorName**
  - `Products.txt`: ApplNo, ProductNo, Form, Strength, ReferenceDrug, **DrugName**, **ActiveIngredient**, ReferenceStandard
  - `Submissions.txt`: ApplNo, SubmissionClassCodeID, SubmissionType, SubmissionNo, SubmissionStatus, **SubmissionStatusDate**, ReviewPriority (ORIG-1 = original approval; efficacy SUPPLs = new indications)
  - `MarketingStatus.txt`, `TE.txt`, `ApplicationDocs.txt` (links to approval letters and labels), lookups.
- Cadence: weekly-ish. Covers NDAs, ANDAs, and CDER BLAs, so it also bridges Purple Book biologics.
- Indication text is not a field; get it from the label (openFDA drug label API) or the 10-K product description.

**openFDA NDC directory (the NDC bridge, strongly recommended)**

- Bulk: **https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip** (27.9 MB)
- API: `https://api.fda.gov/drug/ndc.json?search=brand_name:keytruda&limit=1` returned `product_ndc 0006-3026, labeler_name "Merck Sharp & Dohme LLC", application_number "BLA125514"`.
- Rate limits: 240 requests/min and 1,000/day per IP without a key; a free key raises it to 120,000/day.
- This is how NDC-keyed pricing files (IRA, NADAC, SDUD) join to NDA/BLA-keyed FDA files.

---

## 5. Pricing

### 5a. Medicare Part D Spending by Drug (annual)

- Landing: https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug
- CSV (DY2024, released 2026-06-25): **https://data.cms.gov/sites/default/files/2026-06/98218f98-166c-4723-8438-c344a4ef96a6/DSD_PTD_RY26_P04_V10_DY24_BGM.csv** (5.3 MB)
- API: `https://data.cms.gov/data-api/v1/dataset/7e0b4365-fd63-4a29-8f5e-e0ac9f66a81b/data?keyword=Eliquis&size=10` (verified). Params: `filter[Brnd_Name]=`, `keyword=`, `size=` (max 5000), `offset=`. No key.
- Columns: Brnd_Name, Gnrc_Name, Tot_Mftr, Mftr_Name (one row per manufacturer plus an `Overall` row), then for each year 2020-2024: Tot_Spndng, Tot_Dsg_Unts, Tot_Clms, Tot_Benes, **Avg_Spnd_Per_Dsg_Unt_Wghtd**, Avg_Spnd_Per_Clm, Avg_Spnd_Per_Bene, Outlier_Flag; plus **Chg_Avg_Spnd_Per_Dsg_Unt_23_24** and **CAGR_Avg_Spnd_Per_Dsg_Unt_20_24**.
- Example: Eliquis Overall 2024 total spend $20.77B, $9.64 per unit, -1.1% per unit vs 2023.
- What it is: gross drug cost (ingredient + dispensing fee + tax) **before manufacturer rebates**. Closer to list than net. Free.
- Cadence: annual, about a 2-year lag (DY2025 likely mid-2027). Join on brand name + generic name; Mftr_Name helps confirm the company.

### 5b. Medicare Quarterly Part D Spending (fresher)

- CSV (2025 Q1-Q4, released 2026-07): **https://data.cms.gov/sites/default/files/2026-07/QDD_PTD_RQ2603_P01_V10_DQT2601_20260708.csv**
- API: `https://data.cms.gov/data-api/v1/dataset/4ff7c618-4e40-483a-b390-c8a58c94fa15/data`
- Columns: Brnd_Name, Gnrc_Name, Tot_Mftr, Mftr_Name, Year, Tot_Benes, Tot_Clms, Tot_Spndng, Avg_Spnd_Per_Bene, Avg_Spnd_Per_Clm, Drug_Uses. No per-unit field; use spend per claim.

### 5c. Medicare Part B Spending by Drug

- CSV (DY2024): **https://data.cms.gov/sites/default/files/2026-06/6616fc91-eb70-404c-9f27-1448e47a3a73/DSD_PTB_RY26_P06_V10_DYT24_HCPCS-%20260602.csv** (319 KB)
- API: `https://data.cms.gov/data-api/v1/dataset/76a714ad-3a2c-43ac-b76d-9dadf8f7d890/data`
- Quarterly Part B: CSV `https://data.cms.gov/sites/default/files/2026-07/6d9e955a-d199-42cf-9f73-7e0d93c33b3e/qddptb_r2603_p06_v10_dqt2601_260722.csv`, API dataset `bf6a5b3b-31ee-4abb-b1ad-2607a1e7510a`.
- Columns: HCPCS_Cd, HCPCS_Desc, Brnd_Name, Gnrc_Name, per-year spend/units/claims/benes, Avg_Spndng_Per_Dsg_Unt_YYYY, **Avg_DY24_ASP_Price**, Chg_Avg_Spndng_Per_Dsg_Unt_23_24, CAGR.
- What it is: payment based on ASP + 6%. ASP is the manufacturer's average sales price **net of most discounts and rebates** (excludes Medicaid rebates). Best free near-net price for infused drugs (Keytruda, Opdivo).

### 5d. Medicaid NADAC (weekly)

- Dataset (2026): data.medicaid.gov id `fbb83258-11c7-47f5-8b18-5f8e79f7e704`, modified 2026-10-13
- Full CSV: **https://download.medicaid.gov/data/nadac-national-average-drug-acquisition-cost-20261014.csv** (107 MB, 1.24M rows; the filename changes weekly, so read the current one from the metastore)
- API (verified):
  `https://data.medicaid.gov/api/1/datastore/query/fbb83258-11c7-47f5-8b18-5f8e79f7e704/0?limit=50&conditions[0][property]=ndc_description&conditions[0][value]=ELIQUIS%25&conditions[0][operator]=like`
  (URL-encode the brackets, or use `curl -G --data-urlencode`.) Returned 246 Eliquis rows, e.g. ELIQUIS 2.5 MG TABLET, NDC 00003089321, $9.68961 per EA, effective 2025-12-17.
- Prior year: 2025 dataset `f38d0706-1239-442c-a3cc-40ef1b686ac0`. "First Time NADAC Rates" `e3af839d-8175-5be0-b94e-4a302ed7a035` (new generics appearing, a nice LOE signal).
- Catalog of all dataset ids: https://data.medicaid.gov/api/1/metastore/schemas/dataset/items?show-reference-ids=false
- Columns: NDC Description, NDC (11-digit, no dashes), NADAC Per Unit, Effective Date, Pricing Unit, Pharmacy Type Indicator, OTC, Explanation Code, **Classification for Rate Setting** (B = brand, G = generic), Corresponding Generic Drug NADAC Per Unit, As of Date.
- What it is: retail pharmacy **invoice acquisition cost**, not list (WAC) and not manufacturer net. For brands it tracks WAC closely; after LOE the generic NADAC shows the price collapse. Weekly. Free, no key.

### 5e. Medicaid State Drug Utilization Data (SDUD)

- 2025: **https://download.medicaid.gov/data/sdud2025_updatedjuly2026.csv** (509 MB). 2026 partial: `https://download.medicaid.gov/data/sdud2026_updated072026.csv`. Dataset ids: 2025 `158a1baa-5506-400a-8ec3-97756f0b0536`, 2024 `61729e5a-7aa8-448c-8903-ba3e0cd0ea3c`.
- Columns: Utilization Type, State, NDC, Labeler Code, Product Code, Package Size, Year, Quarter, Suppression Used, Product Name, Units Reimbursed, Number of Prescriptions, Total Amount Reimbursed, Medicaid Amount Reimbursed, Non Medicaid Amount Reimbursed.
- What it is: Medicaid reimbursement **before** statutory rebates. Quarterly. Query the datastore API with an NDC or Labeler Code filter instead of the full file. Labeler Code = first 5 digits of NDC (e.g. 00006 Merck, 00003 BMS, 00002 Lilly, 00069 Pfizer, 00074 AbbVie; confirm against openFDA labeler_name).

### 5f. Inflation Reduction Act: Medicare Drug Price Negotiation

- Page: https://www.cms.gov/priorities/medicare-prescription-drug-affordability/overview/medicare-drug-price-negotiation-program/selected-drugs-and-negotiated-prices
- **Data file ZIP: https://www.cms.gov/files/zip/selected-drug-list-negotiated-prices-also-known-maximum-fair-prices-statutezip.zip** (45 KB; CSV and XLSX dated 20260921, 560 rows)
- Columns: IPAY, Selected Drug Name, Active Ingredient, NDC-9, NDC-11, XREF NDC-11, HCPCS Code, **MFP Effective Date, MFP End Date, Single MFP per 30 DES** (30-day equivalent supply), **NDC-9 MFP per Unit Price**, HCPCS Code Dosage Price, As of Date, Type of Update (New IPAY, Inflation, Deselect, End Date, Recalc, New NDC), Remarks.
- Contents verified:
  - **IPAY 2026 (MFP live since 1/1/2026)**: Eliquis, Enbrel, Entresto, Farxiga, Imbruvica, Januvia, Jardiance, NovoLog/Fiasp, Stelara, Xarelto. Example: Eliquis MFP $231 per 30 days, inflation-adjusted to $237.25 from 1/1/2027.
  - **IPAY 2027 (MFP effective 1/1/2027, prices published)**: Austedo, Breo Ellipta, Calquence, Ibrance, Janumet, Linzess, Ofev, Otezla, Ozempic/Rybelsus/Wegovy, Pomalyst, Tradjenta, Trelegy Ellipta, Vraylar, Xifaxan, Xtandi. Example: Austedo $4,093 per 30 days.
  - **IPAY 2028 (first cycle with Part B drugs; listed 01/27/2026, no MFP in the file yet)**: Anoro Ellipta, Biktarvy, Botox, Cimzia, Cosentyx, Entyvio, Erleada, Kisqali, Lenvima, Orencia, Rexulti, Trulicity, Verzenio, Xeljanz, Xolair. By statute CMS publishes IPAY 2028 MFPs by Nov 30, 2026, after the hackathon. The page also links a fact sheet on drugs selected for renegotiation.
  - **Deselections**: Entresto, Stelara, and Xarelto NDCs deselected with end date 12/31/2026; NovoLog/Fiasp also has deselect rows. Generic or biosimilar entry ends IRA eligibility, so this is a ready-made demo story linking LOE to pricing.
- Per-drug "MFP explanation" ZIPs are linked on the same page (e.g. `https://www.cms.gov/files/zip/mfp-explanation-eliquis.zip`).
- What it is: a statutory **net** ceiling price for Medicare. Free.

### 5g. List vs net, and what is free

| Source | Price concept | Free? |
|---|---|---|
| Part D Spending by Drug | Gross pre-rebate pharmacy cost (list-like) | Yes |
| Part B Spending / ASP | Manufacturer net sales price (near-net) | Yes |
| NADAC | Pharmacy invoice acquisition cost (near WAC for brands) | Yes |
| SDUD | Medicaid pre-rebate reimbursement | Yes |
| IRA MFP | Government negotiated net price | Yes |
| WAC list price | Manufacturer list price | No (Medi-Span, First Databank, AnalySource). Proxy with NADAC for brands. |
| True net price per product | After all rebates | No. Proxies only: 10-K language ("lower net price", "gross-to-net"), and company US pricing transparency reports (several big pharmas publish average list vs net change yearly; not verified tonight). |

---

## 6. SEC EDGAR

**Rules**: every request must send a `User-Agent` with name + email (e.g. `"Aidan Jones aidan@justinianhq.com"`); max 10 requests/second per IP or you get blocked for about 10 minutes. No key. Sleep about 0.12 s between calls. Missing User-Agent returns 403.

| Endpoint | URL pattern | Verified |
|---|---|---|
| Ticker to CIK | https://www.sec.gov/files/company_tickers.json (799 KB); with exchange: https://www.sec.gov/files/company_tickers_exchange.json | yes |
| Submissions | `https://data.sec.gov/submissions/CIK##########.json` (10-digit zero pad). Merck CIK0000310158: 157 KB; `filings.recent` arrays: accessionNumber, filingDate, reportDate, form, items (8-K item codes), primaryDocument, isXBRL. | yes |
| Company facts | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (Merck 4.5 MB, 775 us-gaap concepts) | yes |
| Concept / frames | `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/Revenues.json`, `https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2025.json` | standard pattern |
| Full-text search | `https://efts.sec.gov/LATEST/search-index?q=%22loss%20of%20exclusivity%22&forms=10-K&ciks=0000310158&dateRange=custom&startdt=2025-01-01&enddt=2026-10-16` (JSON hits with accession:file, entity, file_date). Coverage 2001 onward. | yes |
| Filing index | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/index.json` | yes |
| XBRL instance | e.g. https://www.sec.gov/Archives/edgar/data/310158/000031015826000063/mrk-20251231_htm.xml (6.1 MB) | yes |

Recent Merck filings from submissions: 10-K 2026-02-24 (0000310158-26-000063), 10-Q 2026-05-04, 10-Q 2026-08-07 (0000310158-26-000212). Q3 2026 10-Qs land late Oct / early Nov, after the hackathon.

**Does product-level revenue appear in XBRL?**

- **Not in companyfacts.** companyfacts and frames carry only non-dimensional facts. Merck companyfacts has `Revenues` FY2025 = $65,011M and nothing per product.
- **Yes in the filing's XBRL instance.** Merck's 10-K instance has 364 `ProductOrServiceAxis` references and members such as `mrk:KeytrudaMember`, `mrk:KeytrudaQlexMember`, `mrk:LenvimaMember`, `mrk:BridionMember`, `mrk:WinrevairMember`, `mrk:WeliregMember`, `mrk:VaxneuvanceMember`, `mrk:AlliancerevenueLynparzaMember`. Facts are `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` (or `Revenues`) whose context sets `srt:ProductOrServiceAxis`, often with `srt:StatementGeographicalAxis` for US vs international. Parse with lxml: map context id to dimension members, then pull values. Other big pharmas tag product revenue the same way.
- Easier fallback: the `R*.htm` pages in the same filing folder (FilingSummary.xml says which R page is the revenue-by-product note) are clean HTML tables.
- Bulk alternative (skip tonight): Financial Statement and Notes data sets, monthly, e.g. https://www.sec.gov/files/dera/data/financial-statement-notes-data-sets/2026_02_notes.zip (329 MB; February holds most calendar-year 10-Ks).

**Where big pharma 10-Ks put the data you need** (section names from recent 10-K structure; confirm in your scraped copies)

| Company | LOE / patent table (Item 1) | Product sales | Litigation / settlements |
|---|---|---|---|
| Merck (MRK, CIK 310158) | Item 1 "Patents, Trademarks and Licenses": table of key products with US/EU/Japan patent expiry incl. PTE and PED | Revenue note product sales table (US / International); Item 7 product discussion | Contingencies note, Patent Litigation subsection |
| BMS (BMY, CIK 14272) | Item 1 "Intellectual Property": table of **estimated minimum market exclusivity dates** US/EU/Japan per product (the cleanest LOE table in the industry) | Revenue note by product, US vs non-US | Legal Proceedings and Contingencies note, Intellectual Property |
| Pfizer (PFE, CIK 78003) | Item 1 "Patents and Other Intellectual Property Rights": table of basic product patent expiry for major products, US/EU/Japan | Revenue by product (note and Item 7) | Contingencies note, patent litigation (names ANDA filers) |
| AbbVie (ABBV, CIK 1551152) | Item 1 "Intellectual Property Protection and Regulatory Exclusivity": narrative plus expected exclusivity for key products | Segment and geographic note: net revenues for key products | Legal Proceedings and Contingencies note |
| Lilly (LLY, CIK 59478) | Item 1 "Patents, Trademarks, and Other Intellectual Property Rights": table of compound patent and data protection expiry, US/EU/Japan | Revenue note by product | Contingencies note, Patent Litigation |

Since the team already has 20,000 10-Ks, search those for these headings rather than refetching.

**10-Q and 8-K value**

- 10-Q: quarterly product revenue (same XBRL tagging) shows erosion in the first quarters after LOE, plus updated LOE language.
- 8-K: Items 2.02 (earnings, EX-99.1 has product sales), 7.01 / 8.01 (patent settlements, at-risk generic launches, IRA selection and MFP statements). Filter submissions `items` for those codes, then full-text search "settlement" or "generic" within the CIK.

---

## 7. ClinicalTrials.gov API v2 (optional pipeline)

- Base: https://clinicaltrials.gov/api/v2/studies (no key; stay around 50 requests/min)
- Verified query: `https://clinicaltrials.gov/api/v2/studies?query.spons=Merck%20Sharp%20%26%20Dohme&filter.overallStatus=RECRUITING&query.term=AREA%5BPhase%5DPHASE3&countTotal=true&pageSize=100&fields=NCTId,BriefTitle,Phase,Condition,InterventionName,PrimaryCompletionDate` returned 63 recruiting Phase 3 studies.
- Paginate with `pageToken=` from `nextPageToken`.
- Use: for each LOE-exposed franchise, count Phase 3 programs in the same condition. "Franchise X loses exclusivity in 2028; N Phase 3 programs in the same area read out before then" is the replacement story.

---

## 8. Join strategy

```
ticker --(company_tickers.json)--> CIK --(submissions)--> 10-K / 10-Q accessions
   |                                          \--> XBRL instance: ProductOrServiceAxis member (KeytrudaMember) -> revenue
   |
   +--> company alias list (hand-built, 10-20 strings per company; seed from 10-K Exhibit 21)
            |
            +--> Orange Book Applicant / Applicant_Full_Name --> Appl_No (NDA) --> patent.txt, exclusivity.txt, PIV list
            +--> Drugs@FDA Applications.SponsorName           --> ApplNo (NDA/BLA) --> Products.DrugName
            +--> Purple Book Applicant                        --> BLA Number --> biosimilars by Ref. Product name
            +--> openFDA NDC labeler_name                     --> application_number <-> product_ndc
                                                                    |
                                    NDC-9 / NDC-11 <----------------+
                                       |-> IRA MFP file (NDC-9, NDC-11)
                                       |-> NADAC (NDC-11, no dashes)
                                       |-> SDUD (NDC, Labeler Code)
   brand name (normalized) --> CMS Part D/B (Brnd_Name + Mftr_Name), PIV list (RLD cell), 10-K text mentions
```

Practical keys:

- **Primary product key: brand (trade name) + application number.** Build a `products` table from Orange Book (N rows) + Purple Book (351(a) rows) filtered to the company alias list. That table drives everything else.
- **NDC normalization**: 10-digit NDCs come in 4-4-2, 5-3-2, 5-4-1 shapes. Normalize to 11-digit 5-4-2 by left-padding the short segment. NDC-9 = labeler + product (first 9 of the 11-digit form).
- **Brand name match to CMS**: uppercase, strip `*` and punctuation, exact match first; fall back to generic name + manufacturer.

Pitfalls (seen in tonight's data):

- **Subsidiary and historical applicant names.** Merck appears as `MSD`, `MERCK SHARP AND DOHME LLC`, `MERCK SHARP AND DOHME CORP`, `MERCK AND CO INC`, `MERCK RESEARCH LABORATORIES DIV MERCK CO INC`, `MERCK SHARP AND DOHME LLC A SUB OF MERCK AND CO INC`. BMS appears as `BRISTOL MYERS SQUIBB`, `...CO`, `...CO PHARMACEUTICAL RESEARCH INSTITUTE`, `APOTHECON INC DIV BRISTOL MYERS SQUIBB`, plus acquired names (Celgene, Juno, MyoKardia, Karuna). Pfizer includes Wyeth (several variants), Pfizer Laboratories Div, Hospira, Seagen. AbbVie includes Allergan (several), Pharmacyclics (Imbruvica). Lilly includes Loxo, ImClone.
- **Not the same company**: Merck KGaA / EMD Serono vs Merck & Co; Organon (Merck spin-off) and Viatris (former Pfizer Upjohn) now hold old brands.
- **Partnered products**: the NDA holder may not book the revenue. Eliquis is a BMS NDA with Pfizer sharing profits; Lenvima is Eisai's with Merck alliance revenue; Lynparza is AstraZeneca's with Merck alliance revenue; Xarelto is J&J in the US and Bayer elsewhere. Keep `nda_holder` and `revenue_booker` separate.
- **One brand, many applications**: tablets, sprinkle, XR, pens. Aggregate LOE at brand level from the main NDA; keep row-level detail for citations.
- **Orange Book dates are not LOE**: settlements, at-risk launches, use-code carve-outs. Always show the 10-K stated date next to the computed one.
- **Biologics**: no Orange Book patents. Reference exclusivity is 12 years from first licensure; real LOE is set by biosimilar settlements. Use 10-K text.
- **CMS Part D rows by manufacturer**: use the `Overall` row for brand totals; per-manufacturer rows are where generics show up.
- **NADAC and SDUD are big**: filter by NDC via API if memory is tight.
- **SEC throttling**: stay under 10 req/s.

---

## 9. Minimal schema

### `product_loe_pricing` (one row per company x brand)

| Column | Type | Source |
|---|---|---|
| company, ticker, cik | text | company_tickers.json |
| product (brand) | text | Orange Book Trade_Name / Purple Book Proprietary Name |
| ingredient | text | Orange Book Ingredient / Purple Book Proper Name |
| modality | text (small molecule / biologic) | NDA vs BLA |
| appl_no | text | Orange Book / Purple Book / Drugs@FDA |
| nda_holder, revenue_booker | text | Applicant_Full_Name; 10-K |
| indication | text | 10-K Item 1 product description, or openFDA label `indications_and_usage` |
| revenue_latest_fy, revenue_prior_fy, revenue_yoy | numeric | XBRL instance ProductOrServiceAxis |
| revenue_us_share | numeric | XBRL StatementGeographicalAxis |
| pct_of_company_revenue | numeric | product revenue / companyfacts Revenues |
| loe_orange_book_substance | date | patent.txt (Drug_Substance_Flag = Y, with *PED) |
| loe_last_listed_patent | date | patent.txt max |
| exclusivity_latest_code, exclusivity_latest_date | text, date | exclusivity.txt / Purple Book Ref. Product Exclusivity |
| loe_company_stated | text/date | 10-K Item 1 table or litigation note |
| loe_best_estimate | date | rule in section 1 |
| piv_first_submission, piv_anda_count, piv_180day_status | date, int, text | PIV xlsx |
| generic_anda_holders_count | int | Orange Book products.txt Appl_Type = A |
| biosimilar_count, interchangeable_flag | int, bool | Purple Book 351(k) rows |
| partd_spend_2024, partd_spend_per_unit_2024 | numeric | Part D Spending |
| partd_per_unit_chg_23_24, partd_per_unit_cagr_20_24 | numeric | Part D Spending |
| partb_asp_2024 | numeric | Part B Spending |
| nadac_per_unit_latest, nadac_effective_date | numeric, date | NADAC |
| ira_ipay, ira_mfp_30day, ira_mfp_effective, ira_deselected | int, numeric, date, bool | IRA MFP file |
| pipeline_ph3_same_area | int | ClinicalTrials.gov |
| revenue_at_risk_by_2030 | numeric | derived: revenue where LOE or MFP falls before 2030 |
| citations | json list | see below |

### `citations` (one row per fact, so every AI output can cite)

`fact_id, product_key, field, value, source_name, url, file_name, row_key (e.g. "patent.txt N~202155~001~6967208"), sec_accession, sec_section, retrieved_at`

The LLM gets a pre-joined product row plus its citation rows and writes prose only about values it was handed. That satisfies the "every AI output cites its source document or row" rule cheaply.

### Derived "price change" timeline per product

Dated events: IRA selection, MFP effective date, MFP inflation adjustments, deselection, first PIV filing, 30-month stay end, estimated generic/biosimilar entry, Part D per-unit trend direction. One sorted list of `(date, event, source)` per product is what the CEO slide needs.

---

## 10. Friday night download script

```bash
UA="Aidan Jones aidan@justinianhq.com"
mkdir -p raw && cd raw
curl -L -A "$UA" -o orange_book.zip https://www.fda.gov/media/76860/download
curl -L -A "$UA" -o drugsatfda.zip https://www.fda.gov/media/89850/download
curl -L -A "$UA" -o purple_book_2026_09.csv https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-September-data-download.csv
curl -L -A "$UA" -o piv_list.xlsx "https://www.fda.gov/media/194880/download?attachment"
curl -L -A "$UA" -o ira_mfp.zip https://www.cms.gov/files/zip/selected-drug-list-negotiated-prices-also-known-maximum-fair-prices-statutezip.zip
curl -L -A "$UA" -o partd_dy24.csv https://data.cms.gov/sites/default/files/2026-06/98218f98-166c-4723-8438-c344a4ef96a6/DSD_PTD_RY26_P04_V10_DY24_BGM.csv
curl -L -A "$UA" -o partb_dy24.csv "https://data.cms.gov/sites/default/files/2026-06/6616fc91-eb70-404c-9f27-1448e47a3a73/DSD_PTB_RY26_P06_V10_DYT24_HCPCS-%20260602.csv"
curl -L -A "$UA" -o partd_q2025.csv https://data.cms.gov/sites/default/files/2026-07/QDD_PTD_RQ2603_P01_V10_DQT2601_20260708.csv
curl -L -A "$UA" -o openfda_ndc.zip https://download.open.fda.gov/drug/ndc/drug-ndc-0001-of-0001.json.zip
curl -A "$UA" -o company_tickers.json https://www.sec.gov/files/company_tickers.json
for c in 0000310158 0000014272 0000078003; do   # MRK, BMY, PFE: swap for your three
  curl -A "$UA" -o sub_$c.json  https://data.sec.gov/submissions/CIK$c.json;          sleep 0.2
  curl -A "$UA" -o facts_$c.json https://data.sec.gov/api/xbrl/companyfacts/CIK$c.json; sleep 0.2
done
# Then for each company's latest 10-K and 10-Q accession: fetch index.json and the *_htm.xml instance.
# Optional: NADAC 2026 full CSV (107 MB)
# curl -L -o nadac_2026.csv https://download.medicaid.gov/data/nadac-national-average-drug-acquisition-cost-20261014.csv
```

Per the project rules, raw data goes in `data/` (Parker's folder) and LLM outputs for demo inputs get cached in `agent/cache/` so the demo never waits on a live API.
