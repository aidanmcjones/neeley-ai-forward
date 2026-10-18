# AMGN data requests (Part 2 strategist)

Each gap was searched and not found. None was guessed: every affected number carries [assumption] in candidates.jsonl.

1. TAVNEOS confirmatory-trial cost (AMGN-m01).
   Needed: per-patient cost of a 52-week randomized trial in ANCA-associated vasculitis, or any indexed rare-autoimmune trial-cost benchmark.
   Queries: search_pages('TAVNEOS confirmatory study new trial'), ('TAVNEOS ADVOCATE trial patients randomized'); verified/costs/launch_and_marketing_benchmarks.csv (call statements only, no trial costs).
   Fill: a trial-cost benchmark table (for example sponsor 10-K R&D per-program disclosures) or a published cost-per-patient study.

2. FDA precedent for accepting a new confirmatory trial instead of withdrawal (AMGN-m01).
   Needed: cases where CDER's proposal to withdraw approval ended in postmarketing requirements rather than withdrawal.
   Queries: search_pages('proposal to withdraw approval hearing postmarketing requirement'); the only hits are Amgen's own 10-Q risk text.
   Fill: Federal Register withdrawal-hearing notices and outcomes, or FDA advisory or hearing records indexed as primary docs.

3. Profit-share or royalty buyout comps (AMGN-m03).
   Needed: prices paid to buy out a partner's 50% profit share on a marketed biologic, as a multiple of trailing payments.
   Queries: search_pages('acquire partner's remaining rights profit share buyout upfront payment'); verified/deals/deal_comps.csv filtered for buyout or remaining rights terms (no marketed-product profit-share buyouts; only royalty monetizations such as D1391 Royalty Pharma and BeOne, which is a different structure).
   Fill: P2-<ACQUIRER> deal 8-Ks for partner buyouts (the coordinator says more are arriving), plus UCB annual report pages on EVENITY revenue and profit share.

4. UCB-side EVENITY economics (AMGN-m03).
   Needed: UCB's EVENITY net sales in Europe, its share of the profit split, and any strategic statements.
   Queries: search_pages('UCB EVENITY') returns only Amgen documents; UCB is not in the index.
   Fill: index UCB's FY2025 annual report and its H1 2026 report.

5. Repatha label section 6 Adverse Reactions (AMGN-m02 promo fair balance).
   Needed: the common adverse reactions, for fair balance.
   Queries: pages of repatha:drugs/repatha/label_v30.md (only sections 1, 2, 4, 5 are indexed).
   Fill: index section 6 of the current Repatha label. The promo piece must not be used until it is added.

6. Repatha U.S. payer mix and commercial prior-auth rate (AMGN-m04).
   Needed: Medicare vs commercial share of U.S. Repatha volume, and the commercial PA rate.
   Queries: verified/rx/formulary_part2.csv (Part D only); tables/partd_by_year.csv (no Repatha rows found in the coordinator's list).
   Fill: Part D spend rows for Repatha in partd_by_year.csv; commercial formulary data (MMIT or similar), if licensed.

7. Promotion elasticity for cardiovascular campaigns (AMGN-m02).
   Needed: incremental sales per promotional dollar for a CV brand.
   Queries: verified/costs/launch_and_marketing_benchmarks.csv (qualitative call statements only).
   Fill: open_payments_by_drug.csv spend for Repatha vs prescriptions in partd_prescribers_by_drug.csv, as a correlational proxy.

8. Amgen cost of debt (AMGN-m03 financing cost).
   Needed: weighted average interest rate on Amgen debt.
   Queries: not pulled within time; the 10-K FY2025 debt note is indexed and could fill it.
   Fill: Amgen 10-K FY2025 debt note (weighted average rate), to replace the 4.5% [assumption].
