# PFE data requests (Part 2 strategist)

Each item: what I needed, the queries I ran, what would fill it. None of these were guessed; each gap is carried as an [assumption] in candidates.jsonl.

1. Vyndaqel/Vyndamax product-level gross-to-net (drives m01 net per patient, m02 return).
   Queries: search_pages("Vyndaqel revenue", ticker=PFE); read PFE:10q_2026Q2.md p.38 and PFE:10k_FY2025.md p.38; tables/gtn_proxy.csv rows vyndaqel and vyndamax (Part D spend per unit only, no net).
   Found: only the qualitative "net price erosion in the U.S. as a result of new payer contracts". Used the company-wide 41.3% deduction rate as a proxy.
   Fill: SSR Health or IQVIA net price series for tafamidis; or Pfizer's U.S. pricing transparency report if it breaks out the product.

2. U.S. undiagnosed ATTR-CM pool and campaign response rates (m01 incremental patients).
   Queries: tables/indication_epidemiology.csv and market_sizing_inputs.csv (only a secondary, unverified 100,000 prevalence and a 1 to 2% diagnosed figure flagged unverified); search_pages("ATTR-CM diagnosis awareness campaign", ticker=PFE) (Pfizer 2024Q1 call p.23 says U.S. diagnosis rates near the top of 30% to 50%).
   Fill: a peer-reviewed U.S. claims-based ATTR-CM incidence study; published DTC or HCP-campaign lift benchmarks for rare cardiomyopathy (none in tables/launch_and_marketing_benchmarks.csv for ATTR-CM).

3. Medicare Part D claims for Q2 2026 onward (m01 and m02 kill signals; seasonality check on the Q1 2026 decline).
   Queries: tables/medicare_market.csv and partd_by_year.csv (latest is 2026 Q1).
   Fill: CMS quarterly Part D spending release covering 2026 Q2.

4. Enrollment-weighted formulary coverage and rebate per listing (m02).
   Queries: facts rx/formulary_history.csv rows #954, #1399, #1774 (unweighted formulary counts).
   Fill: CMS plan-level enrollment joined to formulary IDs; MMIT or Fingertip formulary-lives data.

5. Amvuttra U.S. revenue split ATTR-CM vs hATTR-PN, and Part B ASP trend (sizes how much of finding 1's share loss is Part B, out of reach of Part D contracting).
   Queries: ALNY:10q_2026Q2.md p.38 (U.S. total only); tables/partb_asp_quarterly.csv not used for revenue.
   Fill: Alnylam indication-level disclosure or Part B claims by diagnosis code.

6. Intellia filings and gene-editing deal comps (m03 price and burn split).
   Queries: search_pages("MAGNITUDE clinical hold", ticker=NTLA) returned nothing; the doc NTLA:pipeline/NTLA/10k_NTLA_2001.md is listed as "file missing on disk"; verified/deals/deal_comps.csv has only the 2021 AstraZeneca/Ionis eplontersen licence in ATTR (coordinator confirms ATTR-CM comp set not indexed yet).
   Fill: Intellia 10-K FY2025 and Q2 2026 10-Q pages (R&D by program, cash); 8-Ks for gene-editing licence deals; the reason for and resolution of the nex-z clinical hold. Watch for doc_ids "<ACQUIRER>:deals/8k/..." with deal_id "P2-...".

7. Ibrance brand-level promotional spend (m04 savings).
   Queries: tables/launch_and_marketing_benchmarks.csv (company-total advertising only: $2.7B FY2025); open_payments_by_drug.csv (HCP payments only).
   Fill: Kantar/Vivvix brand ad spend for Ibrance; Pfizer segment or brand SI&A (not disclosed in filings).

8. Vyndamax IRA negotiation selection status for initial price applicability year 2029 (affects m01 tail and m02 price math).
   Queries: search_pages("Vyndamax Vyndaqel tafamidis selected drug negotiation"); search_pages("Vyndaqel Medicare price negotiation 2028", ticker=PFE); PFE:10q_2026Q2.md p.35 names only Eliquis, Ibrance, Xtandi and Xeljanz.
   Fill: CMS selected-drug list for IPAY 2029 when published; an IRA selected-drug table (coordinator says none yet).

9. Head-to-head evidence for any tafamidis vs acoramidis or vutrisiran claim (m01 promo).
   Queries: tables/head_to_head.csv rows for tafamidis pairs are all "mentioned_not_compared"; coordinator directs that only true_head_to_head = yes rows support a comparison.
   Result: no comparative claim used in the promo piece; no fill needed unless a comparative message is wanted.
