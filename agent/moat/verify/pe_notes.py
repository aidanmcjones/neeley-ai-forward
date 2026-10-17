"""Write NOTES.md for verified/peers and verified/epi and append the collector errors to verify/ai_wrong.jsonl (run once)."""
import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, log_wrong

V = ROOT / "data/moat/verified"


def E(stream, table, row_key, said, source, error_type, severity, how, count, example):
    return dict(stream=stream, table=table, row_key=row_key, what_the_ai_said=said, what_the_source_says=source,
                error_type=error_type, severity=severity, how_caught=how, count=count, example_source=example)


ERRORS = [
    E("peers", "rival_product_statements.csv", "maker=BBIO/ALNY/NVS/TAK/REGN transcripts, 19 rows",
      "statements by the maker on its earnings call (e.g. ALNY 'Negative Sentiment: Costs and margin pressures rose ... higher AMVUTTRA royalties'; BBIO 'Attruby Net Product Revenue -- $222.4 million')",
      "text was written by the transcript publisher, not the company: MarketBeat 'Key Takeaways' block marked 'AI Generated. May Contain Errors.', Fool/Webull TAKEAWAYS/SUMMARY blocks, NVS Webull 'Summary', and MarketBeat 'About <company>' boilerplate after the call",
      "publisher_text_as_company_statement", "high", "located every quote line against the transcript start marker (Presentation / Full Transcript / AI Generated line) and the last timestamp", 19,
      "data/corpus/peers/ALNY/transcripts/2026Q1_transcript.md lines 522-534"),
    E("peers", "rival_product_statements.csv", "speaker column, earnings_call rows",
      "speaker = 'Quarterly Report', 'Watch the full earnings call below', 'Drug Manufacturers', 'Annual Report', 'Do NOT Buy SpaceX', 'BridgeBio', 'Cabenuva', 'Chief Financial Officer'",
      "web page nav/ad lines, company names or a product name, not people; MarketBeat speaker is the name line above the title and timestamp (e.g. 'Tolga Tanguler / ... / 00:12:31')",
      "wrong_speaker", "medium", "re-derived speaker from timestamp blocks and 'Name :' prefixes", 224,
      "data/corpus/peers/BBIO/transcripts/2026Q1_transcript.md (Neil Kumar rows labelled 'Quarterly Report')"),
    E("peers", "rival_product_statements.csv", "topic column",
      "topic 'pricing' on 113 rows (e.g. Amvuttra 'Second, vutrisiran was associated with a lower risk of worsening ...' tagged pricing)",
      "regex 'IRA' with re.I and no word boundary matches 'vutrIRAn', 'zilebesIRAn', 'nucresIRAn', 'inclisIRAn'; '%' and 'expect' tag growth on boilerplate. Hand check of 100 random rows: 22 topic tags wrong. Fixed regex keeps 49 pricing rows",
      "keyword_tagging_bug", "medium", "read agent/moat/peers_statements.py TOPICS and hand-graded 100 rows", 64,
      "data/corpus/peers/ALNY/transcripts/2026Q1_transcript.md"),
    E("peers", "rival_product_statements.csv", "subject check",
      "rows filed under one product when the sentence is about another (e.g. Amvuttra row: 'We cannot predict the outcome of any litigation to enforce the Leqvio patents ...'; Apretude row whose sentence is about Cabenuva's 55% contribution)",
      "product is named but is not the main subject; 114 more rows are multi-product lists or combined totals (e.g. '$2.99 billion ... from sales of AMVUTTRA, ONPATTRO, GIVLAARI and OXLUMO')",
      "wrong_subject", "medium", "counted alias mentions of the product vs other products in each quote", 25,
      "data/corpus/peers/ALNY/10k_FY2025.md"),
    E("peers", "rival_product_statements.csv", "page column for GSK/SNY 20f_FY2025",
      "page 1 for 69 annual-report rows", "the source md has no page breaks (one page), so 'page 1' is not a usable citation; printed page unknown",
      "unusable_page_cite", "low", "page count per cited doc", 69, "data/corpus/peers/GSK/20f_FY2025.md"),
    E("peers", "rival_product_statements.csv", "period column", "period blank on every row",
      "collector's regex ran on the filename but the column was written empty for Roche docs and never back-filled; verified table fills FY/quarter from doc name", "missing_field", "low", "column audit", 852, "data/moat/tables/rival_product_statements.csv"),
    E("peers", "peer_product_revenue.csv", "NVS FY2022 (20 rows)",
      "FY2022 NVS top-20 products, e.g. product='Immunology' 2,516 ; 1,479 ; 3,995",
      "page 216 of the FY2022 20-F is the table 'top 20 ... brands in 2020'; the row is Cosentyx 2020 (US 2,516, RoW 1,479, total 3,995). The FY2022 table is page 214 (Cosentyx 2022 total 4,788)",
      "wrong_fiscal_year", "high", "re-read page headers; rebuilt all four top-20 tables and checked the 20 brand totals sum to the printed 'Top 20 brands total'", 20,
      "data/moat/companies/NVS/20f_FY2022.md page 216 (F-24)"),
    E("peers", "peer_product_revenue.csv", "NVS FY2022 product column",
      "product = 'Immunology', 'Established Brands', 'Hypertension', 'Chronic heart failure'",
      "these are the brand classification or key-indication columns; the brand names (Cosentyx, Gleevec, Afinitor, Diovan Group, Exforge Group, Entresto) were dropped, so two rows are both 'Established Brands' and two both 'Hypertension'",
      "column_misread", "high", "page re-read", 16, "data/moat/companies/NVS/20f_FY2022.md page 216"),
    E("peers", "peer_product_revenue.csv", "NVS FY2022 rows 18-20 and missing brands",
      "'Rest of portfolio', 'Retail Generics 1', 'Biopharmaceuticals' as top-20 products; Lucentis, Jakavi, Xolair, Galvus missing",
      "first three are a portfolio remainder and Sandoz franchise lines; the four missing brands have no US column (one value pair) and the parser skipped them",
      "non_product_rows_and_dropped_rows", "high", "page re-read", 7, "data/moat/companies/NVS/20f_FY2022.md page 216"),
    E("peers", "peer_product_revenue.csv", "NVS FY2023-FY2025 (59 rows)",
      "top-20 products from the 20-F, values_raw like '7 748 ; 7 822 ; 6 035 ; 30'",
      "rows come from the 'Net sales ... by core therapeutic area' table (pp 210, 188, 191), not the top-20 table; first_value (current-year total) is right for all 44 brands also in the top 20, but values_raw drops minus signs ('- 1' lost), mixing years and % changes; 3 'Other' rows are not products",
      "wrong_table_and_sign_loss", "medium", "matched each row to the rebuilt top-20 table", 59, "data/corpus/peers/NVS/20f_FY2025.md page 191 (F-20)"),
    E("peers", "peer_product_revenue_xbrl.csv", "concept column",
      "3,602 product revenue rows", "146 rows are not revenue: CostOfRevenue (98), ContractWithCustomerLiabilityRevenueRecognized (25), remaining performance obligation and milestone concepts (23); 1,049 rows are 6M/9M YTD with no period-type column; custom concepts re-prefixed 'company:'",
      "non_revenue_rows", "medium", "concept audit; 72 sampled rows re-found in the EDGAR XBRL instances, 72/72 exact match", 146, "https://www.sec.gov/Archives/edgar/data/872589/000180422023000008/regn-20221231_htm.xml"),
    E("peers", "manifests/peers.jsonl", "47 rows", "documents in the manifest", "files deleted from disk (tiny bogus 6-Ks) plus 7 duplicate path rows",
      "stale_manifest", "low", "path exists check", 54, "data/moat/companies/NVS/6k/2023-03-27_0001171843-23-001905.md"),
    E("peers", "companies/TAK file labels", "TAK 20-F vs transcripts",
      "20f_FY2025 and transcript 2024Q4 both for Takeda", "20f_FY2025 is the year ended March 31, 2025 (Takeda's own 'FY2024'); transcripts use Takeda's FY (2024Q4 = May 2025 call on FY2024). Same report year carries FY2025 on the filing and FY2024 on the call",
      "fiscal_label_inconsistency", "medium", "cover page 'fiscal year ended' vs call dates", 2, "data/moat/companies/TAK/20f_FY2025.md cover"),
    E("epi", "indication_epidemiology.csv", "type 2 diabetes", "diagnosed_share 72.4 (= 29.1/40.1, derived)", "29.1/40.1 = 72.6%",
      "arithmetic", "low", "recomputed", 1, "data/moat/epi/sources/primary_recheck.md#page 4"),
    E("epi", "epi/sources/pmc_psoriasis_armstrong.md", "plaque psoriasis source copy", "saved copy of Armstrong JAMA Dermatol 2021 psoriasis prevalence",
      "file is PMC8254764, 'Biomarkers of Potential Harm among Adult Cigarette and Smokeless Tobacco Users in the PATH Study'; numbers (3.0%, 7.55M) are right but only confirmed on the live JAMA page",
      "wrong_source_document", "high", "opened the saved file", 1, "data/moat/epi/sources/pmc_psoriasis_armstrong.md line 1"),
    E("epi", "indication_epidemiology.csv", "ATTR-CM us_prevalence_n", "100,000 US ATTR-CM patients (cites PMC11740649 review)",
      "the saved review never states 100,000; it gives 6.1 per million claims-diagnosed (about 2,044 at 335M) and 54.9 per million among 65+. 100,000 is an unverified HFSA abstract figure",
      "unsupported_number", "high", "searched the saved review", 1, "data/moat/epi/sources/pmc_attr_epidemiology_review.md line 254"),
    E("epi", "indication_epidemiology.csv", "hypercholesterolemia", "count 30.7M = 11.4% x 269.7M adults",
      "11.4% is the age-adjusted rate; a count needs the crude rate 11.5% (31.0M), and the NHANES base is 20+, not Census 18+. Same 20+ vs 18+ mismatch in the obesity count",
      "wrong_rate_for_count", "low", "re-read NCHS DB363 live", 2, "https://www.cdc.gov/nchs/products/databriefs/db363.htm"),
    E("epi", "indication_epidemiology.csv", "PrEP treated share, CCW shares", "26% of PrEP-indicated prescribed (2022); CCW hyperlipidemia 65.5%, RA+OA 36.2%, AF 4.60M/6.7%",
      "no primary copy reachable (UW guidance is secondary; CCW chart URL returns 404); kept only as low-confidence notes", "no_primary_copy", "medium",
      "attempted live fetch", 4, "https://www2.ccwdata.org/web/guest/medicare-charts/medicare-chronic-condition-charts"),
    E("epi", "medicare_market.csv", "keytruda, opdivo, darzalex, imfinzi, tecentriq, sarclisa, entyvio, leqvio rows",
      "Part D claims/beneficiaries and share of class claims for physician-administered drugs (e.g. Keytruda 11,882 Part D claims 2024)",
      "these drugs are billed mainly under Part B; the row note never says Part-D-only (the caveat is only in the README), so class shares compare a Part B drug's Part D residue with oral drugs",
      "missing_scope_label", "medium", "read row notes; Part D numbers themselves recomputed from the raw CMS DY2024 file: 15/15 drugs exact, 45/45 class shares exact", 8,
      "data/moat/tables/medicare_market.csv period=2024"),
    E("epi", "market_sizing_inputs.csv", "cancer funnel rows", "Medicare floor % of prevalent patients for NSCLC, HR+/HER2-, MSI-H CRC, HNSCC etc.",
      "denominator is the whole SEER site or a proxy site, so the % is understated for the labelled subset; 51 rows flagged subset_caveat. Collector said 124 funnel rows but only 95 carry a floor % (29 have no Part D beneficiary floor)",
      "denominator_scope", "medium", "recomputed all 95 floor % (95/95 arithmetic ok)", 51, "data/moat/tables/market_sizing_inputs.csv"),
    E("epi", "indication_map.csv", "label_section '1.0'", "label section 1.0 'INDICATIONS AND USAGE'",
      "labels with no subsections have section 1 only; '1.0' is not a label section number. 53/60 sampled rows matched heading exactly; 7 are section-1-only labels with a paraphrased sub_indication", "invented_section_number", "low",
      "sample of 60 vs DailyMed SPL copies in data/corpus/drugs", 7, "data/corpus/drugs/repatha/label_sections.md"),
    E("epi", "gaps/epi.jsonl", "64 lines", "64 gap entries", "22 distinct gaps; 42 lines repeat the same ticker/item/reason with a different timestamp (zero byte-exact duplicates)",
      "duplicate_rows", "low", "dedupe", 42, "data/moat/gaps/epi.jsonl"),
]


def main():
    q = pd.read_csv(V / "peers/rival_product_statements.csv")
    tl = pd.read_csv(V / "peers/transcript_labels.csv")
    pk = pd.read_csv(V / "peers/annual_report_page_checks.csv")
    raw_n = 852
    per = q.groupby("product").size()
    rawp = pd.read_csv(ROOT / "data/moat/tables/rival_product_statements.csv").groupby("product").size()
    pr = "\n".join(f"| {p} | {rawp[p]} | {per.get(p, 0)} | {per.get(p, 0) / rawp[p]:.1%} |" for p in rawp.index)
    peers = f"""# verified/peers NOTES (Opus verifier, 2026-10-17)

Scripts: agent/moat/verify/pe_quotes.py, pe_nvs.py, pe_xbrl.py, pe_transcripts.py, pe_pages.py, pe_manifest.py.

## rival_product_statements.csv
- {raw_n} raw rows; every quote is verbatim on its cited page (852/852, whitespace-normalized) and every printed folio matches. The collector extracted mechanically, so quote text was never the problem.
- Dropped 19 rows (rival_product_statements_dropped.csv): publisher-written text inside third-party transcript pages (MarketBeat 'Key Takeaways' marked AI generated, Fool/Webull TAKEAWAYS/SUMMARY, 'About <company>' boilerplate). Kept {len(q)}.
- 25 kept rows are `verified_secondary_subject` (another product is the main subject); 114 more are `subject=shared` (product named in a list or combined total). Do not use a shared row as a product-specific number.
- Speaker re-derived: 224 junk speakers removed or replaced (MarketBeat name/title/timestamp blocks, 'Name :' prefixes). `speaker_status` says how each was set.
- Topic: hand check of 100 random rows found 22 wrong tags (keyword regex: 'IRA' matched every '-siran' drug name). `topic_fixed` holds a corrected regex tag; treat both as hints only.
- New columns: verify_status, maker_is_source (Jardiance = partner: BI is the maker, Lilly co-commercializes), source_role (focal_company_doc for AZN/LLY/MRK/AMGN docs: Imfinzi, Jardiance, Lipfendra, Wezlana, Amjevita come from those makers' own filings), true_maker, page_granularity (GSK/SNY 20f_FY2025 are one-page files, so page 1 is not a usable cite), fragment (166 quotes cut at a line break or table rows).

| product | raw | kept | pass rate |
|---|---|---|---|
{pr}

## peer_product_revenue.csv (NVS)
- Rebuilt from the four 20-F 'top 20 brands' tables (FY2022 p214 F-22, FY2023 p211 F-18, FY2024 p189 F-20, FY2025 p192 F-21): 80 rows, US / RoW / total in USD millions, each year's 20 brand totals sum exactly to the printed 'Top 20 brands total'.
- The collector table was wrong: FY2022 rows were the 2020 table with class/indication in the product column; FY2023-25 rows came from the therapeutic-area table (current-year value right for all 44 matched brands, other columns sign-corrupted). Mapping in peer_product_revenue_collector_map.csv.

## peer_product_revenue_xbrl_checks.csv
- 72 rows checked against the EDGAR XBRL instances (30 10-K product, 24 10-Q product, 18 other): 72/72 exact value, period and full dimension set. No Q4 derivation exists in the table (Q4 must be FY minus 9M YTD); 1,049 rows are 6M/9M YTD with no period-type column; 146 rows are non-revenue concepts (CostOfRevenue etc.); there is no mapped product-name column, product is the raw member name.

## transcript_labels.csv
- 45 peer transcripts (NVS 10, GSK 6, SNY 6, TAK 6, REGN 10, ALNY 6, BBIO 1, ROCHE 0): 45/45 labels match the call date. TAK uses Takeda's fiscal year consistently (call in May = prior FY Q4; Jul = Q1). But TAK 20-F files are named by the March year end (20f_FY2025 = Takeda FY2024), so filings and calls for the same year carry different FY labels.

## annual_report_page_checks.csv
- 16 docs (2 per peer). FY labels: all match the cover (TAK by year-end convention). Folio on page: 8/8 for all SEC filings with folios; Roche annual_report_2023 page count equals the PDF (184) with 5/6 sampled pages text-matched, finance_report_2024 199 = 199 pages, 6/6. GSK 20f_FY2024 has no page breaks (1 page); SNY 20f_FY2024 has only 31 page breaks for a full 20-F; NVS 20-Fs have folios on only 32-36 of ~250 pages.

## manifest_clean.jsonl
- 162 manifest rows -> 108: 47 rows point to deleted files (the bogus 6-Ks), 7 duplicate path rows.
"""
    epi = """# verified/epi NOTES (Opus verifier, 2026-10-17)

Scripts: agent/moat/verify/pe_epi.py, pe_epi2.py.

## indication_epidemiology.csv (all 30 rows)
- 19 SEER rows: prevalence, 2026 new cases, 5-year survival and 65+ share (65-74 + 75-84 + >84 of new cases) re-parsed from the saved Stat Facts pages: 19/19 exact. 13 cancer rows carry a whole-site or proxy denominator (see checks column).
- 9 web rows re-read live on the primary page (WebFetch for cdc.gov, EuropePMC REST for Helmick) and the verbatim sentences saved page-marked in data/moat/epi/sources/primary_recheck.md (8 pages). All headline numbers confirmed.
- Fixed: diabetes diagnosed_share 72.4 -> 72.6. Confidence lowered: ATTR-CM 'low, no primary copy (100,000)' (the saved review never says 100,000), RA 'low, dated (2005 base)', PrEP 'low (2015 estimate; treated share has no primary copy)'.
- Wrong source file: epi/sources/pmc_psoriasis_armstrong.md is a tobacco biomarker paper (PMC8254764), not Armstrong; the numbers are confirmed via the live JAMA page instead.
- Derived counts: 269.7M = 341,784,857 x (1 - 21.1%) checks. Obesity 108.7M, AF 10.49M, cholesterol 30.7M arithmetic correct; but cholesterol should use crude 11.5% (31.0M), and obesity/cholesterol apply NHANES 20+ rates to an 18+ base. AF 3.89% is a 5-year EHR period prevalence (Epic Cosmos), not a survey.
- No primary copy reachable: CMS CCW shares (hyperlipidemia 65.5%, RA+OA 36.2%, AF 4.60M / 6.7%; chart URL 404s) and the PrEP 26% prescribed share. Kept only inside notes, low confidence.

## indication_map.csv (sample of 60)
- 53 exact section-and-heading matches against the DailyMed SPL copies, 7 section-1-only labels where the collector wrote '1.0' with a paraphrased sub_indication; setid matches the cited URL 60/60. 1 sampled indication is accelerated approval in the label text (Keytruda Qlex 1.16 TMB-H). No withdrawn indication in the sample.

## medicare_market_checks.csv
- 15 drugs recomputed from the raw CMS Part D DY2024 file (R2 public/partd_spending_dy24.csv): claims, spend and beneficiary floor 15/15 exact. Class totals and drug share of class claims 45/45 exact.
- Physician-administered drugs (Keytruda, Opdivo, Darzalex, Imfinzi, Tecentriq, Sarclisa, Entyvio IV, Leqvio) are not labelled Part-D-only in their rows; the checks file adds part_b_administered.

## market_sizing_inputs.csv
- 173 rows; 124 have a funnel note but only 95 carry a Medicare floor % (29 have no Part D beneficiary floor). All 95 recomputed: 95/95 match. New columns: denominator_n, floor_pct_recomputed, subset_caveat (51 rows whose denominator is a whole cancer site or proxy), epi_confidence, part_b_drug_floor_understated (56 funnel rows).

## gaps/epi.jsonl
- Deduped in place: 64 -> 22. There were no byte-exact duplicates; 42 lines repeated the same ticker/item/reason with only a new timestamp, kept first occurrence in order.
"""
    write("verify_peers", "verified/peers/NOTES.md", peers, group="notes", doc_type="notes", quality="verified")
    write("verify_epi", "verified/epi/NOTES.md", epi, group="notes", doc_type="notes", quality="verified")
    log_wrong(ERRORS)
    print(len(ERRORS), "ai_wrong entries;", "kept", len(q), "transcripts", len(tl), "page docs", len(pk))


if __name__ == "__main__":
    main()
