"""Write verified/policy/definitions.md (stream verify_policy) and append ai_wrong.jsonl lines once."""
import json
import sys

from agent.moat.common import ROOT, write

DEFS = """# Policy force_summary: definitions (verified 2026-10-17)

All figures come from rows in verified/policy/policy_exposure.csv (status verified, fixed or added); traceable_row_ids lists them.

- ira_drug_fy2025_revenue: FY2025 net revenue, as reported by the company, of the drugs selected for IPAY 2026, 2027 and 2028
  for which the company is the CMS-named manufacturer (IPAY 2026/2027 fact sheets) or the brand owner (IPAY 2028 list has no
  manufacturer column). Revenue basis is GLOBAL product revenue for every company, including collaboration revenue the
  company books on that product (AbbVie Imbruvica = US 2,048 + collaboration 821). No company needed a US-only fallback.
  Combination selections count the whole family: Januvia/Janumet (one MRK line), Ozempic + Wegovy + Rybelsus (semaglutide),
  Fiasp + NovoRapid/NovoLog (Novo 'Fast-acting insulin' line, NovoMix excluded), Botox Therapeutic + Botox Cosmetic (CMS selected
  'Botox; Botox Cosmetic').
- ira_share_of_total_revenue_pct: ira_drug_fy2025_revenue / FY2025 total revenue (company total revenues; Novo = group net sales DKK 309,064m).
  Same currency in numerator and denominator (DKK for NVO), so the % is currency-neutral.
- ira_share_incl_partnered_pct: adds selected drugs named to a partner where the company books revenue: PFE Eliquis 7,961 and
  Xtandi 2,194, JNJ Imbruvica 2,823, MRK Lenvima alliance revenue 1,053, LLY Jardiance 3,431. These double count across companies
  (BMY also reports Eliquis), so never sum this column across companies.
- expected_*: MRK only. Keytruda/Keytruda Qlex FY2025 sales 31,680 / total 65,011, from Merck's own statement that it expects
  Keytruda to be selected in 2027 with a price effective 2029-01-01 (quote in expected_quote). Not a CMS selection.
- us_investment_pledge_usd_bn: the forward US total pledged, as stated by the company (or White House for NVO). Horizons differ
  (pledge_horizon), so do not compare pledges as annual rates. pledge_capex_usd_bn / pledge_rd_usd_bn are filled only where the
  source states the split (MRK capex at least 12; LLY 50 is manufacturing-only). AMGN has no forward pledge: blank, not 2.5.
- tariff_exempt_until: Proclamation 11020 clause (e): zero rate until 2029-01-20 for companies eligible under clause 3(b) that have
  MFN agreements with HHS. The proclamation's Annex III list (who is effective 2026-07-31) is not in the local text.
- mfg_sites_total / non_us: FDA CDER drug-establishment registrations (drls_reg.txt) with a MANUFACTURE or API MANUFACTURE
  operation, matched by firm or registrant name, after removing verified false positives (Organon, Kenvue, Meridian, Upjohn/Viatris,
  Biohaven, a supplement firm) and adding the two Catalent Bloomington sites now owned by Novo. CDER-only: CBER biologics, vaccine
  and cell-therapy sites are under-covered, so counts are a floor. See mfg_sites_confidence. US = USA + Puerto Rico.
- us_revenue_share_pct: US revenue / total revenue on the same basis. AMGN uses product sales for both (geography is disclosed only
  for product sales). NVO uses group sales to external US customers (173,166) / group net sales (309,064).
"""

ERRORS = [
    dict(table="policy_exposure", what_the_ai_said="NVO FY2025 US revenue DKK 159,077m and total DKK 289,015m (used for us_revenue_share 55.0%)",
         what_the_source_says="those are Novo Nordisk A/S parent-company note figures (2024 comparative 261,712 vs group 290,403); group US external sales are DKK 173,166m of 309,064m (56.0%)",
         how_caught="checked the 2024 comparative against group net sales on another page", count=2, example_source="data/corpus/companies/NVO/20f_FY2025_d2.md"),
    dict(table="policy_exposure", what_the_ai_said="AbbVie Imbruvica FY2025 revenue 2,048 (labelled US only) used in the global IRA share",
         what_the_source_says="Imbruvica Total $2,869 (US 2,048 + collaboration revenues 821)", how_caught="read the rows under the quoted US line", count=1,
         example_source="data/corpus/companies/ABBV/10k_FY2025.md p.40"),
    dict(table="policy_exposure", what_the_ai_said="Novo 'Fast-acting insulin' 18,583 is a category upper bound including non-selected insulins",
         what_the_source_says="Fast-acting insulin = Fiasp 2,818 + NovoRapid 15,765 exactly; the selected drug is Fiasp/NovoLog (NovoMix is a separate line)", how_caught="read the 'of which' sub-rows", count=1,
         example_source="data/corpus/companies/NVO/20f_FY2025_d2.md"),
    dict(table="force_summary", what_the_ai_said="ABBV Botox exposure = Botox Therapeutic only (3,769)",
         what_the_source_says="CMS selected 'Botox; Botox Cosmetic' as one drug; Botox Cosmetic adds 2,602 (ABBV share 16.9% -> 22.5% with the Imbruvica fix)", how_caught="compared drug name on the CMS IPAY 2028 list", count=1,
         example_source="data/moat/policy_gov/cms/cms_fact_sheet_selected_list_ipay2028.md"),
    dict(table="policy_exposure", what_the_ai_said="quote cited supports a different claim than the value (e.g. LLY 'Medicaid MFN pricing' quoted a Zepbound Medicaid access sentence; AMGN 'IRA effect' quoted a generic MFN sentence with value 'see 10-K')",
         what_the_source_says="the MFN Medicaid term is in the White House fact sheet; the AMGN row has no datum", how_caught="read each quote against its item", count=3,
         example_source="data/corpus/companies/LLY/policy/press_2025-11-06_us_govt_agreement.md"),
    dict(table="policy_exposure", what_the_ai_said="numeric value shown as worldwide while the quote shows only the US row (Linzess, Vraylar, Botox, Stelara, Erleada, Xarelto) or the quote is cut before the numbers (PFE 13 sites)",
         what_the_source_says="worldwide totals are a few cells later; values were right but did not follow from the quote", how_caught="value-in-quote check", count=7,
         example_source="data/corpus/companies/JNJ/10k_FY2025.md p.84"),
    dict(table="force_summary", what_the_ai_said="selected drugs where the company books revenue but CMS names a partner were silently omitted (PFE Eliquis/Xtandi, JNJ Imbruvica, MRK Lenvima, LLY Jardiance)",
         what_the_source_says="PFE 10-K: 'Ibrance and Xtandi were included'; MRK 10-K: Lenvima selected for 2028. PFE share 8.3% -> 24.6% incl. partnered", how_caught="read each company's own IRA paragraph", count=5,
         example_source="data/corpus/companies/PFE/10k_FY2025.md"),
    dict(table="force_summary", what_the_ai_said="AMGN US investment pledge $2.5B",
         what_the_source_says="$2.5B is 2025 manufacturing capex already announced; no forward total pledge exists", how_caught="read the pledge sentence tense and scope", count=1,
         example_source="data/corpus/companies/AMGN/policy/press_2025-12-19_mfn_agreement.md"),
    dict(table="policy_exposure", what_the_ai_said="unsupported dates/scope on pledges (PFE window 2025-2028; MRK named sites list incl. Wilmington/De Soto/Durham from an Elkton-only quote)",
         what_the_source_says="PFE: 'in the next few years'; the MRK quote names only Elkton $3B", how_caught="value-in-quote check", count=2,
         example_source="data/corpus/companies/PFE/policy/press_2025-09-30_mfn_landmark_agreement.md"),
    dict(table="manufacturing_sites", what_the_ai_said="name-alias matches counted as company sites: 5 Organon (MRK), 2 Kenvue McNeil (JNJ), 6 Meridian + Upjohn Ireland + Biohaven (PFE), 1 supplement firm 'Natural Immunogenics' (ABBV)",
         what_the_source_says="these firms are spun off, divested or unrelated; 12 MANUFACTURE-op sites removed. Missed: 2 Catalent Bloomington sites owned by Novo",
         how_caught="read every matched firm/registrant name against FDA lines and company 10-K/20-F", count=18, example_source="drls_reg.txt lines via data/moat/tables/manufacturing_sites_detail.csv"),
    dict(table="policy_exposure", what_the_ai_said="item labels mismatched to quote (MRK/AMGN 'New-launch price commitment' for an all-four-asks scope sentence)",
         what_the_source_says="the quotes describe deal scope", how_caught="read quote vs item", count=2, example_source="data/corpus/companies/MRK/policy/press_2025-12-19_mfn_agreement.md"),
]

if __name__ == "__main__":
    write("verify_policy", "verified/policy/definitions.md", DEFS, group="policy", doc_type="note")
    if "--log" in sys.argv:
        p = ROOT / "data/moat/verify/ai_wrong.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            for e in ERRORS:
                f.write(json.dumps(dict(stream="policy", **e)) + "\n")
        print("logged", len(ERRORS))
    print("ok")
