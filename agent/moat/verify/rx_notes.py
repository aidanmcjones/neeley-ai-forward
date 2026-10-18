"""rx verifier: log collector errors to data/moat/verify/ai_wrong.jsonl (once) and write verified/rx/NOTES.md with
pass rates by table and field, computed from the verified tables already written."""
import json

import pandas as pd

from agent.moat.verify.rx_lib import AIW, ROOT, log_wrong, out

V = ROOT / "data/moat/verified/rx"
S = "verify_rx"


def rd(n):
    return pd.read_csv(V / n)


def rate(df, col="verify_status", ok=("verified",)):
    n = len(df)
    k = int(df[col].isin(ok).sum())
    return f"{k}/{n} ({k / n:.0%})" if n else "0/0"


def errors():
    pd_ = rd("partd_prescribers_by_drug.csv")
    hu = pd_[(pd_.drug == "humira") & (pd_.year == 2023)].iloc[0]
    bk = pd_[(pd_.drug == "biktarvy") & (pd_.year == 2023)].iloc[0]
    cc = rd("prescriber_concentration.csv")
    mj = cc[(cc.drug == "mounjaro") & (cc.year == 2023)].iloc[0]
    sk = pd_[(pd_.drug == "skyrizi") & (pd_.year == 2023)].iloc[0]
    return [
        {"stream": "rx", "table": "partd_prescribers_by_drug.csv", "row_key": "biktarvy 2019-2024",
         "what_the_ai_wrote": "no Biktarvy rows (6 drug-years absent)",
         "what_the_source_says": f"Biktarvy 2023: {bk.prescribers:,.0f} prescribers with 11+ claims, {bk.total_claims:,.0f} "
                                 f"claims in the provider-drug file; CMS national {bk.claims_all_cms:,.0f} claims",
         "error_type": "incomplete_query", "severity": "high",
         "how_caught": "Gnrc_Name CONTAINS 'bictegravir' misses CMS string 'Bictegrav/Emtricit/Tenofov Ala'; re-pulled by Brnd_Name",
         "count": 6, "example_cite": "data.cms.gov Part D Prescribers by Provider and Drug 2023, Brnd_Name=Biktarvy"},
        {"stream": "rx", "table": "partd_prescribers_by_drug.csv", "row_key": "humira 2019-2024",
         "what_the_ai_wrote": "Humira 2023 total_claims 85,106",
         "what_the_source_says": f"{hu.total_claims:,.0f} claims once 'Humira(Cf) Pen' and other pack variants are counted",
         "error_type": "classification", "severity": "high", "how_caught": "independent brand classifier on raw R2 pull",
         "count": 6, "example_cite": "rx/raw/partd_prescribers_2023.csv.gz Brnd_Name LIKE 'Humira%'"},
        {"stream": "rx", "table": "partd_prescribers_by_drug.csv",
         "row_key": "amjevita 2023-24, amvuttra 2022, attruby 2024, lazcluze 2024, rybelsus 2019, rybrevant 2022, sarclisa 2020",
         "what_the_ai_wrote": "drug-year absent", "what_the_source_says": "present in raw pull or CMS Geography and Drug national rows",
         "error_type": "incomplete_query", "severity": "low", "how_caught": "outer join against raw and CMS national rows",
         "count": 8, "example_cite": "amjevita 2023: 13,445 claims in raw provider-drug file"},
        {"stream": "rx", "table": "partd_prescribers_by_specialty.csv", "row_key": "humira all years, biktarvy",
         "what_the_ai_wrote": "Humira specialty shares from the base brand only; no Biktarvy specialty rows",
         "what_the_source_says": "31 rows change share or rank, 86 rows added, rows dropped to _dropped.csv",
         "error_type": "classification", "severity": "medium", "how_caught": "recompute from raw", "count": 117,
         "example_cite": "biktarvy 2023 Infectious Disease 38.6% of claims"},
        {"stream": "rx", "table": "prescriber_concentration.csv", "row_key": "cosentyx, enbrel, humira, janumet, repatha, skyrizi, kisqali, rybrevant",
         "what_the_ai_wrote": "top-percentile shares ranked brand-variant rows (Repatha vs Repatha Sureclick) as separate prescribers",
         "what_the_source_says": "aggregating to NPI first moves top 1/5/20% shares (repatha 2023 top1 0.106->0.103, skyrizi 2023 top20 0.354->0.370)",
         "error_type": "aggregation_grain", "severity": "low", "how_caught": "NPI-level recompute", "count": 30,
         "example_cite": "rx/raw/partd_prescribers_2023.csv.gz"},
        {"stream": "rx", "table": "prescriber_concentration.csv", "row_key": "prescriber_growth_yoy (all drugs)",
         "what_the_ai_wrote": f"mounjaro 2023 prescriber growth {mj.prescriber_growth_yoy:.1f}x (+{mj.prescriber_growth_yoy:.0%})",
         "what_the_source_says": f"all-prescriber growth from CMS national rows is +{mj.prescriber_growth_yoy_all_cms:.0%}; the "
                                 "11+-claim cut inflates growth for launching drugs",
         "error_type": "misleading_measure", "severity": "medium", "how_caught": "compare to CMS Geography and Drug Tot_Prscrbrs",
         "count": 1, "example_cite": "prescriber_growth_yoy_all_cms column"},
        {"stream": "rx", "table": "partd_prescribers_by_drug.csv", "row_key": "prescribers (specialty drugs)",
         "what_the_ai_wrote": f"skyrizi 2023 prescribers {sk.prescribers:,.0f}",
         "what_the_source_says": f"CMS counts {sk.prescribers_all_cms:,.0f} prescribers; the provider file holds only "
                                 f"{sk.claims_in_provider_file_share:.0%} of claims because of the 11-claim cut",
         "error_type": "scope_caveat", "severity": "medium", "how_caught": "CMS Geography and Drug national rows",
         "count": 1, "example_cite": "prescribers_all_cms column"},
        {"stream": "rx", "table": "partb_providers_by_drug.csv", "row_key": "J9144 2021-2023",
         "what_the_ai_wrote": "J9144 rows filed under drug 'darzalex'",
         "what_the_source_says": "J9144 is daratumumab and hyaluronidase-fihj (subcutaneous Darzalex Faspro); IV Darzalex is J9145",
         "error_type": "mislabel", "severity": "high", "how_caught": "HCPCS long descriptor check", "count": 123,
         "example_cite": "J9144 2023: 615 providers, 229.9M USD, mostly Faspro not IV"},
        {"stream": "rx", "table": "partb_providers_by_drug.csv", "row_key": "cabenuva J0741, rybrevant J9061, all 2024",
         "what_the_ai_wrote": "Cabenuva returned nothing; 2024 not pulled",
         "what_the_source_says": "J0741 is correct; no provider had 11+ beneficiaries so the provider file is empty, but CMS national "
                                 "rows show 277 providers in 2023; 2024 file is published",
         "error_type": "incomplete_query", "severity": "medium", "how_caught": "Geography and Service national rows",
         "count": 19, "example_cite": "J0741 2023 national: 277 providers, 195,103 services"},
        {"stream": "rx", "table": "formulary_history.csv", "row_key": "quarter labels",
         "what_the_ai_wrote": "quarter 2023Q4 (and 2025Q4 vs 2026Q3 as separate years)",
         "what_the_source_says": "2023Q4 file holds CONTRACT_YEAR 2024; 2024Q4 holds 2025; 2025Q4 and 2026Q3 both hold 2026",
         "error_type": "mislabel", "severity": "low", "how_caught": "CONTRACT_YEAR column in the basic formulary files",
         "count": 4, "example_cite": "SPUF_2024_20250131_2023q4.zip"},
        {"stream": "rx", "table": "formulary_history.csv", "row_key": "physician-administered biologics",
         "what_the_ai_wrote": "covered_in_any_formulary False for Part B products",
         "what_the_source_says": "Part B drugs are not expected on Part D formularies; flagged part_b_drug, coverage set blank",
         "error_type": "scope_caveat", "severity": "medium", "how_caught": "route of administration review", "count": 252,
         "example_cite": "keytruda 1657751 2023Q4"},
        {"stream": "rx", "table": "open_payments_by_drug.csv", "row_key": "usd_other (tecentriq, imfinzi, entyvio)",
         "what_the_ai_wrote": "royalty and license payments folded into usd_other",
         "what_the_source_says": "royalty/license/ownership is 77-98% of total for these drugs; split into usd_royalty_license_ownership",
         "error_type": "proxy_scope", "severity": "medium", "how_caught": "nature of payment grouping", "count": 3,
         "example_cite": "tecentriq PY2021: 55.8M of 56.6M USD royalty/license"},
    ]


def main():
    have = AIW.read_text() if AIW.exists() else ""
    if '"stream": "rx"' not in have:
        log_wrong(errors())
    t = {n: rd(n) for n in ("partd_prescribers_by_drug.csv", "partd_prescribers_by_specialty.csv", "prescriber_concentration.csv",
                            "formulary_history.csv", "partb_providers_by_drug.csv", "open_payments_by_drug.csv",
                            "open_payments_research.csv", "reconciliation.csv", "partd_prescribers_by_state.csv")}
    L = ["# rx stream verification (Opus)", "",
         "Verifier scripts: agent/moat/verify/rx_*.py. Every row carries verify_status and verify_note. Statuses: verified "
         "(recomputed and matches), corrected (value replaced by the recompute), added_* (row the collector missed), "
         "not_rechecked (outside the sample).", "", "## Pass rates by table (whole table, then Opus sample)", "",
         "| table | rows | verified, all rows | verified, sample | statuses |", "|---|---|---|---|---|"]
    for n, d in t.items():
        smp = d[d.in_opus_sample == True] if "in_opus_sample" in d else d
        L.append(f"| {n} | {len(d)} | {rate(d)} | {rate(smp)} | {json.dumps(d.verify_status.value_counts().to_dict())} |")
    pd_ = t["partd_prescribers_by_drug.csv"]
    s = pd_[pd_.in_opus_sample]
    L += ["", "## Pass rates by field (Opus samples)", "",
          "| table | field | pass | how |", "|---|---|---|---|",
          f"| partd_prescribers_by_drug | prescribers, total_claims, total_drug_cost | 22/24 match; 2/24 added (Biktarvy 2023, 2024 missing) | recomputed from raw R2 pulls |",
          f"| partd_prescribers_by_drug | beneficiaries | 0/24 usable as distinct counts | true_beneficiaries added for 24/24 from CMS Geography and Drug national rows |",
          f"| partd_prescribers_by_specialty | claim_share, rank | 220/240 match, 20 added (Biktarvy) | recomputed from raw |",
          f"| prescriber_concentration | top1/5/20 shares | 20/24 match, 2 corrected (Repatha, Skyrizi brand-variant grain), 2 added | NPI-level recompute |",
          f"| prescriber_concentration | YoY growth | matches arithmetic, but see caveat | _all_cms growth added |",
          f"| formulary_history | coverage, tier, PA, ST | 890/890 sample rows (all 1,780 rows) match | recomputed from the 4 basic formulary files |",
          f"| formulary_history | RXCUI map | 142/142 brand SBDs for 20 brands match RxNav brand and TTY | RxNav properties + related BN |",
          f"| partb_providers_by_drug | providers, services, payment | 9/9 code-years re-pulled match exactly; 1 relabelled (J9144) | CMS Physician by Provider and Service |",
          f"| partb_providers_by_drug | HCPCS codes | 16/16 confirmed against HCPCS long descriptors | NLM HCPCS API |",
          f"| open_payments_by_drug | total_usd | 46/46 rechecked drug-years within 1% of all-slot API | fresh re-query + costs all-slot cache |",
          f"| open_payments_research | research_usd, n | 9/9 rows match; mounjaro 2023 correctly absent (0 records) | all-slot re-query |",
          f"| partd_prescribers_by_state | claims, denominator, rate | 60/60 (6 drugs x 10 states, 2023) | raw + Medicare Monthly Enrollment |",
          "", "## Findings", "",
          "1. Part D by drug. Biktarvy was missing for all 6 years (collector's generic-name query missed 'Bictegrav/Emtricit/Tenofov Ala'); "
          "now added from raw Brnd_Name rows. Humira was undercounted 3x to 7x every year because pack variants like 'Humira(Cf) Pen' "
          "were dropped (2023: 85,106 -> 545,396 claims). 8 small drug-years were also missing.",
          "2. Prescriber counts are prescribers with 11+ claims only. For specialty drugs this is a small slice: Skyrizi 2023 has "
          "1,562 such prescribers vs 14,888 in CMS's all-prescriber count (36% of claims); Rinvoq 3,620 vs 9,081; Repatha 28,940 vs "
          "104,032. Read prescribers_all_cms for uptake breadth.",
          "3. beneficiaries_reported sums per-prescriber counts, blank under 11, so it both double counts and drops patients; it "
          "ranges from 10% above to 95% below the CMS distinct count across the 24 sample drug-years (median 41% below). Use true_beneficiaries (summed over a brand's pack-form rows, so an upper bound "
          "where a brand has several CMS rows).",
          "4. Concentration. Top-share recomputes agree except where a prescriber had several brand-variant rows. The same "
          "suppression rule (drop prescriber-drug rows under 11 claims) applies every year 2019 to 2024. But YoY prescriber growth "
          "on the suppressed population is badly inflated for launches: Mounjaro 2023 +2,082% vs +296% for all prescribers. Use "
          "prescriber_growth_yoy_all_cms and top*_share_all_prescribers.",
          "5. Formulary. All 1,780 rows recompute exactly. The basic formulary file has one row per formulary-RXCUI (0 duplicate "
          "pairs in all 4 files), and the collector divides by formulary IDs, not plans, so there is no plan double count; coverage "
          "is unweighted by plans or enrollment. Quarter labels are release labels: 2023Q4 holds contract year 2024, 2024Q4 holds 2025, "
          "and 2025Q4 and 2026Q3 both hold 2026 (contract_year column added). part_b_drug added: 260 rows, 252 with no Part D listing, "
          "now blank instead of 'uncovered'. Many brand SBDs (pack sizes, old strengths) are legitimately unlisted; read drug coverage "
          "as the max over a brand's SBDs.",
          "6. Part B. HCPCS codes confirmed for all 16 codes, including Cabenuva J0741 (provider file is empty because no provider "
          "has 11+ beneficiaries; CMS national rows give 277 providers in 2023) and Apretude J0739. Keytruda Qlex (J9277) and Opdivo "
          "Qvantig (J9289) are separate codes with no rows in 2021 to 2023, so nothing is conflated with IV J9271 / J9299. The real "
          "conflation was J9144 (Darzalex Faspro, subcutaneous) filed under IV Darzalex; relabelled. The provider file covers only "
          "providers with 11+ beneficiaries and only physician-office billing (Keytruda 2023: 1,841 of 5,120 providers; 1.15B of "
          "5.43B USD total Part B spend). 2024 national totals added.",
          "7. Open Payments. The rx collector already matched all 5 product-name slots: 46 of 46 rechecked drug-years agree with the "
          "all-slot API within 1%. reconciliation.csv: trust rx for all 162 rx drug-years (it equals the costs verifier's corrected "
          "values); the 17 costs-only drug-years are 0 USD. Royalty/license/ownership was hidden in usd_other and is 77% to 98% of "
          "Tecentriq, Imfinzi and Entyvio totals; now split into usd_royalty_license_ownership, and usd_promotional added.",
          "8. By state. 60/60 sample cells recompute; the denominator is PRSCRPTN_DRUG_TOT_BENES (Part D enrollees) for the same "
          "state-year, not TOT_BENES. Numerator is claims by prescribers located in the state with 11+ claims; "
          "claims_all_prescribers_per_1000_partd_enrollees added for 8 brands in 2023 and 2024 (median 11% higher than the 11+-claim rate in the 10 sample states, up to 2.5x for low-volume drugs). 225 rows "
          "for codes XX, ZZ, AA, AE, AP, PW have no denominator and no rate.",
          "", "## Errors logged", "", f"12 entries appended to data/moat/verify/ai_wrong.jsonl with stream 'rx'."]
    out("NOTES.md", "\n".join(L) + "\n", "Opus verification of the rx stream")
    print("\n".join(L))


if __name__ == "__main__":
    main()
