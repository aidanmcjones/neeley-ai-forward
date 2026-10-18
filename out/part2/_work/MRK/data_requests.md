# MRK data requests (Part 2 strategist)

Each item: what was needed, the queries run, what would fill it. None of these was guessed; each is tagged [assumption] in candidates.jsonl.

1. IV-to-SC conversion response to a funded field program or price change (MRK-m01, MRK-m03)
   - Needed: any benchmark of how much a field or price program lifts SC share (Darzalex Faspro, Phesgo, Opdivo Qvantig, Tecentriq Hybreza conversion curves).
   - Queries: search_pages 'Keytruda Qlex nurse educators field force site of care practices' (MRK); grep tables/launch_and_marketing_benchmarks.csv (only advertising totals, NVS field force size, call statements). The coordinator confirms SC formulation comps are not indexed yet.
   - Fill: J&J Darzalex SC share disclosures, Roche Phesgo/Hybreza share, BMS Qvantig share by quarter.

2. Merck Keytruda sales by country (MRK-m02)
   - Needed: Germany plus the eight Dutch-counterclaim markets as a share of international Keytruda.
   - Queries: search_pages 'subcutaneous Keytruda launch Europe Germany injunction Halozyme' (MRK); 10-Q p.28 table gives only U.S. vs international.
   - Fill: not disclosed by Merck; IQVIA country sales or EU national reimbursement data.

3. Halozyme MDASE/ENHANZE settlement or license terms (MRK-m02)
   - Needed: royalty and upfront for a litigation settlement license, not a new collaboration.
   - Queries: search_pages 'Halozyme ENHANZE royalty', 'Halozyme royalty subcutaneous', 'hyaluronidase license royalty percent'; tables/deal_comps.csv rows D0532, D1151 (not on indexed pages, so unusable under rule 5). Only indexed comp: Oruka 'mid-single digit royalties' and Vertex $15M upfront for Hypercon (deals:deals/2026-08-06_0001159036-26-000103.md p.2).
   - Fill: Halozyme 10-K royalty-rate disclosure by partner, any Halozyme settlement 8-K, the incoming P2-<ACQUIRER> deal docs.

4. Loaded cost per oncology field FTE (MRK-m01, MRK-m04, MRK-m05)
   - Queries: search_pages 'sales representative cost per representative' (MRK); launch_and_marketing_benchmarks.csv.
   - Fill: a peer 10-K or call statement giving field force cost and headcount together.

5. Whether IRA price setting for Keytruda covers Keytruda Qlex (MRK-m01, MRK-m03)
   - Queries: search_pages 'Keytruda Qlex IRA price setting subcutaneous'; 10-K FY2025 p.31 and p.33 speak of Keytruda only. The coordinator notes no IRA selected-drug table is indexed.
   - Fill: CMS guidance on qualifying single source drug grouping by active moiety; Merck statement on Qlex.

6. Practice economics: Part B add-on and SC vs IV administration fees (MRK-m01, MRK-m03)
   - Needed: the payment-limit add-on and CPT administration fee gap that drives practice incentives.
   - Queries: partb_asp_quarterly.csv has payment limits only; Part 1 notes the lower SC administration fee without a cited amount.
   - Fill: CMS physician fee schedule rates for CPT 96401/96413.

7. Composition of the $5.9B long-dated inventory pool (MRK-m04)
   - Queries: search_pages 'inventories not expected to be sold within one year', 'reduce inventory levels free cash flow working capital 2026', 'inventory tariff drug substance build inventory ahead'; only grade C calls (2024 to 2025Q1) discuss tariff staging, so not quotable.
   - Fill: a management answer on the pool by product, or 10-K inventory detail by franchise.

8. IRS appeals outcomes for penalties and the underpayment interest rate (MRK-m05)
   - Queries: search_pages 'transition tax NOPA IRS appeals', 'IRS audit transition tax appeals settlement'; transcripts 2025Q4 p.16 and 2026Q2 p.13 read, no mention.
   - Fill: IRS Data Book appeals statistics; IRS quarterly underpayment rate notices.

9. U.S. Keytruda-family forecast to 2029 (all Keytruda moves)
   - Used Q2 2026 x4 as a flat run-rate. Fill: I/B/E/S product revenue consensus (cite by locator only) if a Keytruda line exists.
