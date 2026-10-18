"""Pipeline verifier: NOTES.md, ai_wrong entries for items 1, 2, 4, 5, 6, gap note. Run once after the other pp_ steps."""
import pandas as pd

from agent.moat.common import note_gap, write
from agent.moat.verify.pe_lib import log_wrong

C = "data/moat/verify/pp_cache/"
mis = pd.read_csv(C + "land_misclass.csv")
hand = pd.read_csv(C + "land_hand_labels.csv")
land = pd.read_csv("data/moat/verified/pipeline/pipeline_landscape.csv")
mt = "\n".join(f"| {r.collector_label} | {r.n} | {r.wrong} | {r.misclassification_rate:.0%} |" for r in mis.itertuples())
wrong = hand[~hand.collector_correct]
wl = "\n".join(f"| {r.nct_id} | {r.collector_label} | {r.hand_label} | {r.hand_note} |" for r in wrong.itertuples())

NOTES = f"""# Pipeline stream: Opus verification (2026-10-17)

Scripts: `agent/moat/verify/pp_*.py` (fetch, targets, targets_write, loe, ct, land, hand, fda, assets, notes).
Cache: `data/moat/verify/pp_cache/` (SEC companyfacts and submissions, 150 CT.gov JSONs, Orange and Purple Book).
Errors logged to `data/moat/verify/ai_wrong.jsonl` (stream=pipeline).

## Use these, in this order of trust

| File | Rows | Status column | Trust |
|---|---|---|---|
| target_profiles.csv | 199 (5 dropped to target_profiles_dropped.csv) | verify_status: pass 28, recomputed 51, no_price 120 | recomputed from SEC companyfacts; use the verified values, not the collector's |
| loe_calendar.csv | 452 | verify_status: pass 268, check 80, not_stated 104; rule_method | stated dates re-found in the FY2025 10-K with page (tenk_page) |
| pipeline_landscape.csv | 3,383 | verify_status (150 sampled), primary_indication_epi, stale_registry_date, hand_indication | CT.gov fields 150/150 on 5 of 6 fields |
| pipe_indication_to_epi.csv | collector label x epi label | share_of_collector_label, in_epi_vocab | whole-table crosswalk |
| fda_calendar.csv | 921 | verify_status on the 213 quotes; exposure_not_sponsor on Drugs@FDA rows | quotes 74 pass, 116 check, 23 fail |
| pipeline_assets.csv | 2,222 (177 to pipeline_assets_dropped.csv) | verify_status, asset_flag | partial check only (see item 2) |

## Item 3, target_profiles (priority)

The 78 priced rows (46 tickers): arithmetic is right (market cap = price x shares 78/78, EV 78/78, runway 78/78),
but the inputs are often wrong. Field pass rates against SEC companyfacts:

| Field | Pass (78 priced rows) |
|---|---|
| shares outstanding | 78/78 |
| market cap | 78/78 |
| cash | 73/78 |
| current securities | 60/78 |
| debt | 35/78 |
| annual operating burn | 76/78 |
| enterprise value | 46/78 |
| runway years | 65/78 |

Root cause: `latest()` in `pipe_targets.py` returns the newest fact of the FIRST concept in its list that has ANY
data, so a concept last tagged in 2010 beats the current one. 20 priced tickers carry stale debt (NKTR $133.5M is
LongTermDebt at 2015-06-30; ENTA $2.0M at 2010-11-30; KPTI $169.3M at 2021-12-31), 8 carry stale securities (VNDA
$382.6M at 2022-06-30, ENTA $193.7M at 2016-06-30), 3 carry stale cash (SNGX 2022-03-31, ARWR 2024-06-30, ALDX).
The verified file re-derives cash, securities and debt at one balance-sheet date (debt or securities accepted up to
200 days older, else blank with a note), and names the concept used (`cash_concept`, `debt_concept`).
Caveat: 23 priced tickers have no debt fact within 200 days of the balance sheet, so EV assumes zero debt; real
convertible notes exist at some (KPTI, IOVA, CHRS). Check the 10-K debt note before pricing those. 6 rows show
negative EV.

Other findings: ANAB burn of $52.6M is a 6-month 10-KT transition period, not a year. SGMT dei shares are dated
2024-11-08 (stale). Name collisions, hand-checked against SEC submissions names: PTC (PTC Inc., software), COMP
(Compass Inc., real estate), VIK (Viking Holdings, cruises), MGIH (Millennium Group, packaging). 5 rows dropped.
Parent or subsidiary matches kept with a note: GRFS, GPCR, NVCR. 10-K excerpts: 144/144 come from the right CIK and
name the asset, 143/144 are from the latest annual filing (ANAB since filed a 10-KT). None of them is a balance sheet
or cash flow statement: they are asset passages, so cash, debt and burn rest on XBRL only.
Assets that are not the sponsor's pipeline drug sit in some target rows (Crizotinib (Xalkori) at IDYA and NUVB,
Apremilast at ALMS, Valacyclovir at CADL, BYL719 at CELC, platinum chemotherapy at NVCR and AVBP), and some are
already marketed (MGL-3196 = Rezdiffra, Tebentafusp = Kimmtrak, Lifileucel = Amtagvi, KPT-330 = Xpovio).

Tiingo resume run: 429 on the first new ticker (PTC), so nothing was filled. 120 rows still have no price.

## Item 5, loe_calendar (priority)

348 rows carry a company-stated date (160 US). Quote re-found in the company FY2025 10-K: 339 verbatim, 2 across a
page break, 6 not found, 1 with no 10-K text (BLCO). US: stated date appears in the quote 155/160, page found 154/160.
Reconciled with `agent/cache/company_stated_loe.jsonl` (159 rows): 142 agree, 14 have no jsonl row, 4 disagree.
Disagreements and failures:
- STELARA 2025, ZYTIGA 2018, HUMIRA 2023: the quotes are from older 10-Ks, and "not before January 1, 2025" is a
  floor, not an LOE date. The jsonl has no US date for these.
- ENBREL (PFE row) 11/22/2028: the quote is Amgen's 10-K patent table, credited to Pfizer.
- SPRYCEL 2024: the quote says only that generics have entered, with no date; 2024 was inferred.
- EYLEA "May 2024 (expired)" and Trodelvy or Livdelzi composite strings: the date column mixes several dates.
- 80 rows marked `check`: most are table quotes where my brand-in-quote test misses split names
  (Mounjaro/Zepbound); the quote and page are verbatim.

Orange Book rule flags (5 of 105 small-molecule rule dates): XARELTO 2025-03-03 is the first ANDA for 2.5 mg only
(10, 15 and 20 mg first ANDA 2025-05-14). CONCERTA 1988-06-01 predates the brand NDA (2000): the generic of an
older methylphenidate product with the same form. ZITHROMAX, PREMARIN and BORTEZOMIB follow the same pattern.
Biologics: the collector's rule_output_loe was filled for only 15 of 65 US biologic rows, and those were first
biosimilar approval dates (Remicade 2016, Enbrel 2016, Stelara 2023), not LOE. All 65 are now
BLA first licensure + 12 years, labelled in `rule_method`. Purple Book exclusivity agrees for 5 of 6 that have it.
EYLEA differs: 2023-11-18 by the rule against 2024-05-18 in the Purple Book (pediatric exclusivity adds 6 months).

## Item 1, landscape

CT.gov v2 re-pull of 150 trials (6 per indication, phases spread): sponsor 150/150, phase 150/150, status 150/150,
enrollment 150/150, primary completion 150/150, conditions 146/150 (the collector keeps only the first 6 conditions).
Collector primary_indication wrong in 12 of 150 (8%), by hand from the full title and conditions:

| Collector label | Sampled | Wrong | Rate |
|---|---|---|---|
{mt}

Regex failures found:

| NCT | Collector | Hand label | Why |
|---|---|---|---|
{wl}

Other regex classes seen in the whole table: "psoriasis" catches PsA trials that list both (16 rows move to PsA);
"breast" defaults to HR+ even for HER2+ trials; "cardiovascular" in the lipid bucket catches obesity and HF
outcome trials; "esophag" catches varices; "bladder cancer" catches gallbladder; "weight" or "eczema" pull in
non-target trials.
The new classifier (`pp_land.py`, epi vocabulary, combined conditions and title) is wrong in 1 of 150 (a HER2 GI
basket trial). Every row now has `primary_indication_epi`. 9 rows match nothing. Labels marked "(no epi row)" are
out of scope (hand eczema, DME, ILD, PAD, type 1 diabetes, breast with no stated subtype).

## Item 6, stale dates

433 of 1,712 active trials (recruiting, active not recruiting, not yet recruiting, enrolling by invitation) have
primary completion before 2026-10-17: `stale_registry_date=1`. A YYYY-MM date counts as month end.

## Item 4, fda_calendar (partial)

213 PDUFA or decision quotes: 74 pass (verbatim on the cited page, date in the quote), 116 verbatim but the date
column is not stated at that precision in the quote or holds several dates in one string, 23 not found in the
cited doc. 389 of 545 Drugs@FDA rows have a sponsor that is not the ticker (generics of the company's ingredient, or
partner products): `exposure_not_sponsor`. They are not errors, but the ticker column does not mean sponsor.
Not done: the 60 Drugs@FDA actions against openFDA, and the 153 biosimilar rows against the Purple Book.

## Item 2, assets (partial)

177 rows dropped as trial arm or regimen labels, or as another company's marketed drug (comparator or backbone).
9 assets flagged as already marketed. 47 dose-variant rows ("MWN109 1/2/3") merged to one asset.
Pairs of assets in one sponsor that share trials: 991. Almost all are combination regimens, not duplicates.
Not done: the 80-asset owner and phase re-derivation, and code name vs INN merges beyond dose variants.
"""
write("verify_pipeline", "verified/pipeline/NOTES.md", NOTES, group="pipeline", doc_type="notes", quality="verified")

log_wrong([
    dict(stream="pipeline", table="loe_calendar.csv", row_key="STELARA, ZYTIGA, HUMIRA US",
         what_the_ai_said="company-stated LOE 2025 / 2018 / 2023",
         what_the_source_says="quotes are not in the FY2025 10-K (taken from older filings); STELARA quote says only "
                              "'does not anticipate ... before January 1, 2025' (a floor)",
         error_type="stale_source_quote", severity="medium", how_caught="re-found every quote in data/corpus 10k_FY2025",
         count=3, example_source="data/corpus/companies/JNJ/10k_FY2025.md"),
    dict(stream="pipeline", table="loe_calendar.csv", row_key="PFE ENBREL US",
         what_the_ai_said="Pfizer stated US LOE 11/22/2028", what_the_source_says="quote is Amgen's patent table "
         "(Amgen sells Enbrel in the US); not in Pfizer's 10-K", error_type="wrong_company_attribution",
         severity="medium", how_caught="quote search across 10-Ks", count=1,
         example_source="data/corpus/companies/AMGN/10k_FY2025.md"),
    dict(stream="pipeline", table="loe_calendar.csv", row_key="biologic rule_output_loe",
         what_the_ai_said="rule LOE for 15 biologics, e.g. REMICADE 2016-04-05, ENBREL 2016-08-30, STELARA 2023-10-31",
         what_the_source_says="those are first biosimilar approval dates (Purple Book 351(k)), not exclusivity end; 50 "
                              "biologics blank. Replaced by BLA first licensure + 12 years for all 65",
         error_type="wrong_rule", severity="medium", how_caught="Purple Book export", count=15,
         example_source="R2 public/purple_book_2026_09.csv"),
    dict(stream="pipeline", table="loe_calendar.csv", row_key="XARELTO, CONCERTA, ZITHROMAX, PREMARIN, BORTEZOMIB",
         what_the_ai_said="Orange Book rule LOE e.g. XARELTO 2025-03-03, CONCERTA 1988-06-01",
         what_the_source_says="rule took the first ANDA of one strength (Xarelto 2.5 mg; main strengths 2025-05-14) or "
                              "of an older product with the same ingredient (Concerta NDA approved 2000)",
         error_type="wrong_strength_generic", severity="medium", how_caught="Orange Book products.txt by strength",
         count=5, example_source="R2 public/orange_book.zip products.txt"),
    dict(stream="pipeline", table="pipeline_landscape.csv", row_key="primary_indication",
         what_the_ai_said="regex primary indication, e.g. biliary trial as bladder, varices trial as esophageal cancer, "
                          "HS trial as obesity, pertuzumab biosimilar as HR+ breast",
         what_the_source_says="12 of 150 hand-checked trials misclassified (8%); HR+ breast 2/6, esophageal 2/6, T2D 2/6",
         error_type="regex_misclassification", severity="medium", how_caught="hand read of 150 titles and CT.gov conditions",
         count=12, example_source="https://clinicaltrials.gov/api/v2/studies/NCT05506943"),
    dict(stream="pipeline", table="pipeline_landscape.csv", row_key="active trials, primary_completion",
         what_the_ai_said="status RECRUITING/ACTIVE with primary completion in the past",
         what_the_source_says="433 of 1,712 active trials have a registry primary completion before 2026-10-17 "
                              "(sponsor has not updated the record); flagged stale_registry_date",
         error_type="stale_registry_date", severity="low", how_caught="date compare", count=433,
         example_source="https://clinicaltrials.gov/api/v2/studies"),
    dict(stream="pipeline", table="fda_calendar.csv", row_key="PDUFA/decision quotes",
         what_the_ai_said="213 quotes with doc and page",
         what_the_source_says="23 not found in the cited doc; 116 verbatim but the date column is a multi-date string "
                              "or more precise than the quote",
         error_type="quote_not_found", severity="medium", how_caught="loose-normalized search of the cited page", count=23,
         example_source="data/moat/verified/pipeline/fda_calendar.csv"),
    dict(stream="pipeline", table="pipeline_assets.csv", row_key="asset names",
         what_the_ai_said="trial arms and comparators counted as sponsor assets (e.g. 'Platinum based chemotherapy', "
                          "'Crizotinib (Xalkori)' at IDYA, 'Prior failed checkpoint inhibitor'); dose variants as separate assets",
         what_the_source_says="177 are not drug assets of the sponsor; 47 rows are dose labels of one drug",
         error_type="non_asset_rows", severity="medium", how_caught="name patterns + read", count=224,
         example_source="data/moat/verified/pipeline/pipeline_assets_dropped.csv"),
])
note_gap("verify_pipeline", None, "target_profiles.price", "Tiingo still 429 at first new ticker on 2026-10-17 resume; 120 rows unpriced")
note_gap("verify_pipeline", None, "fda_calendar/pipeline_assets", "timeboxed: 60 Drugs@FDA vs openFDA, 153 biosimilars vs Purple Book, 80-asset phase re-derivation not done")
print("ok")
