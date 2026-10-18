"""Row specs for tables/policy_exposure.csv. Each row: quotes are verified against the doc text by policy_build."""

C = lambda t, f: f"data/corpus/companies/{t}/{f}"
G = lambda f: f"data/moat/policy_gov/{f}"
K = lambda t: C(t, "10k_FY2025.md")

ROWS = []  # (ticker, force, item, value, unit, effective_date, doc, [quote candidates], note)


def R(t, force, item, value, unit, date, doc, quotes, note=""):
    ROWS.append((t, force, item, value, unit, date, doc, quotes if isinstance(quotes, list) else [quotes], note))


# ---------------- MFN: agreement date, terms ----------------
R("PFE", "MFN", "MFN agreement announced", "2025-09-30", "date", "2025-09-30", G("wh/wh_fact_sheet_2025-09-30_first_deal_pfizer.md"),
  "Trump announced the first agreement with a major pharmaceutical company, Pfizer, to bring American drug prices in line with the lowest paid by other developed nations")
R("PFE", "MFN", "Medicaid MFN pricing", "yes", "flag", "2025-09-30", G("wh/wh_fact_sheet_2025-09-30_first_deal_pfizer.md"),
  "The agreement will provide every State Medicaid program in the country access to MFN drug prices on Pfizer products")
R("PFE", "MFN", "New-launch price commitment", "MFN price on all new medicines", "term", "2025-09-30", G("wh/wh_fact_sheet_2025-09-30_first_deal_pfizer.md"),
  "guaranteeing MFN prices on all new innovative medicines Pfizer brings to market")
R("PFE", "MFN", "TrumpRx / direct-to-patient discount", "avg 50%, up to 85%", "discount", "2026-02-05", C("PFE", "policy/press_2025-09-30_mfn_landmark_agreement.md"),
  "savings that will range as high as 85% and on average 50%")
R("AZN", "MFN", "MFN agreement announced", "2025-10-10", "date", "2025-10-10", G("wh/wh_fact_sheet_2025-10-10_second_deal_astrazeneca.md"),
  "Trump announced the second agreement with a major pharmaceutical company, AstraZeneca, to bring American drug prices in line with the lowest paid by other developed nations")
R("AZN", "MFN", "Medicaid MFN pricing", "yes", "flag", "2025-10-10", G("wh/wh_fact_sheet_2025-10-10_second_deal_astrazeneca.md"),
  "The agreement will provide every State Medicaid program in the country access to MFN drug prices on AstraZeneca products")
R("AZN", "MFN", "New-launch price commitment", "MFN price on all new medicines", "term", "2025-10-10", G("wh/wh_fact_sheet_2025-10-10_second_deal_astrazeneca.md"),
  "guaranteeing MFN prices on all new innovative medicines AstraZeneca brings to market")
R("AZN", "MFN", "TrumpRx / direct-to-patient discount", "up to 80%", "discount", "2025-10-10", C("AZN", "policy/press_2025-10-10_us_government_agreement.md"),
  "AstraZeneca will provide Direct-to-Consumer (DTC) sales to eligible patients with prescriptions for chronic diseases at a discount of up to 80% off list prices.")
R("LLY", "MFN", "MFN agreement announced", "2025-11-06", "date", "2025-11-06", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "unveiling agreements with pharmaceutical manufacturers Eli Lilly and Company and Novo Nordisk")
R("LLY", "MFN", "Medicaid MFN pricing", "yes (Zepbound/orforglipron access via Medicaid)", "flag", "2025-11-06", C("LLY", "policy/press_2025-11-06_us_govt_agreement.md"),
  "States will also have the ability to expand access to Zepbound and orforglipron through Medicaid.")
R("LLY", "MFN", "New-launch price commitment", "MFN price on all new medicines", "term", "2025-11-06", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "will guarantee MFN prices on all new medicines that they bring to market")
R("LLY", "MFN", "TrumpRx / direct-to-patient price", "Zepbound avg $346/mo; Trulicity $389/mo", "price", "2026-02-05", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "The price of Zepbound and Orforglipron, if approved, will fall from $1,086 per month to an average of $346 when purchased through TrumpRx")
R("NVO", "MFN", "MFN agreement announced", "2025-11-06", "date", "2025-11-06", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "unveiling agreements with pharmaceutical manufacturers Eli Lilly and Company and Novo Nordisk")
R("NVO", "MFN", "Medicaid MFN pricing", "yes (semaglutide in Medicare Part D, Medicaid, cash)", "flag", "2025-11-06", C("NVO", "policy/press_2025-11-06_us_administration_agreement.md"),
  "Medicare Part D and Medicaid and in direct-to-patient cash channel.")
R("NVO", "MFN", "New-launch price commitment", "MFN price on all new medicines", "term", "2025-11-06", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "will guarantee MFN prices on all new medicines that they bring to market")
R("NVO", "MFN", "TrumpRx / direct-to-patient price", "Ozempic/Wegovy $350/mo; NovoLog $35/mo", "price", "2026-02-05", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "The prices of Ozempic and Wegovy will fall from $1,000 and $1,350 per month, respectively, to $350 when purchased through TrumpRx")
R("NVO", "MFN", "Stated 2026 sales impact of agreement", "negative low single-digit % of global sales growth", "term", "2026-01-01", C("NVO", "policy/press_2025-11-06_us_administration_agreement.md"),
  "Novo Nordisk currently expects an estimated negative low single-digit impact on global sales growth in 2026")

for t, d, fs in [("MRK", "2025-12-19", None), ("BMY", "2025-12-19", None), ("AMGN", "2025-12-19", None), ("GILD", "2025-12-19", None)]:
    R(t, "MFN", "MFN agreement announced", d, "date", d, G("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md"),
      "The nine manufacturers include Amgen, Bristol Myers Squibb, Boehringer Ingelheim, Genentech, Gilead Sciences, GSK, Merck, Novartis, and Sanofi.")
    R(t, "MFN", "Medicaid MFN pricing", "yes", "flag", d, G("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md"),
      "The agreements will provide every State Medicaid program in the country access to MFN drug prices on products made by the nine companies")
R("MRK", "MFN", "TrumpRx / direct-to-patient price", "Januvia $330 -> $100", "price", "2026-02-05", G("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md"),
  "Merck will reduce the price of its diabetes medication, Januvia, from $330 to $100 for patients purchasing directly through TrumpRx")
R("MRK", "MFN", "New-launch price commitment", "all four July-letter asks addressed", "term", "2025-12-19", C("MRK", "policy/press_2025-12-19_mfn_agreement.md"),
  "Merck is voluntarily addressing all four components of the president’s July letter")
R("BMY", "MFN", "TrumpRx / direct-to-patient price", "Reyataz $1,449 -> $217; ~80% off for 5 brands", "price", "2026-02-05", G("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md"),
  "Bristol Myers Squibb will reduce the price of its HIV medication, Reyataz, from $1,449 to $217 for patients purchasing directly through TrumpRx")
R("BMY", "MFN", "Medicaid: Eliquis free", "Eliquis free to Medicaid from 2026-01-01", "term", "2026-01-01", C("BMY", "policy/press_2025-12-19_us-government-agreement.md"),
  "Make Eliquis available to Medicaid for free starting on January 1, 2026")
R("BMY", "MFN", "New-launch price commitment", "balanced pricing across developed nations", "term", "2025-12-19", C("BMY", "policy/press_2025-12-19_us-government-agreement.md"),
  "Launch new medicines with a more balanced pricing approach across developed nations.")
R("AMGN", "MFN", "TrumpRx / direct-to-patient price", "Repatha $573 -> $239/mo", "price", "2026-02-05", G("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md"),
  "Amgen will reduce the price of its cholesterol-lowering drug Repatha from $573 to $239 for patients purchasing directly through TrumpRx")
R("AMGN", "MFN", "New-launch price commitment", "satisfies all July MFN letter components", "term", "2025-12-19", K("AMGN"),
  "we announced that we are taking actions that satisfy the components outlined in the July MFN Letter")
R("GILD", "MFN", "TrumpRx / direct-to-patient price", "Epclusa $24,920 -> $2,425", "price", "2026-02-05", G("wh/wh_fact_sheet_2025-12-19_nine_deals_mrk_bmy_amgn_gild.md"),
  "Gilead Sciences will reduce the price of its Hepatitis C medication, Epclusa, from $24,920 to $2,425 for patients purchasing directly through TrumpRx")
R("GILD", "MFN", "New-launch price commitment", "parity with other key developed nations", "term", "2025-12-19", C("GILD", "policy/press_2025-12-19_mfn_agreement.md"),
  "Pricing future medicines at parity with other key developed nations.")
R("GILD", "MFN", "Repatriation of foreign revenue", "return portion of increased international revenue", "term", "2025-12-19", K("GILD"),
  "return a portion of increased international revenues to the U.S. if the U.S. government is successful in increasing drug prices abroad")
R("JNJ", "MFN", "MFN agreement announced", "2026-01-08", "date", "2026-01-08", C("JNJ", "policy/press_2026-01-08_us_government_agreement_mfn.md"),
  "The joint agreement meets the requests laid out by President Trump to the industry and provides the Company’s pharmaceutical products an exemption from tariffs")
R("JNJ", "MFN", "Medicaid MFN pricing", "Medicaid access at comparable prices to other developed countries", "term", "2026-01-08", C("JNJ", "policy/press_2026-01-08_us_government_agreement_mfn.md"),
  "Providing Medicaid program access at comparable prices to other developed countries.")
R("JNJ", "MFN", "TrumpRx listing", "participating", "flag", "2026-02-05", C("JNJ", "policy/press_2026-01-08_us_government_agreement_mfn.md"),
  "Participating in TrumpRx.gov, a direct to patient platform")
R("JNJ", "MFN", "New-launch price commitment", "comparable prices to other developed countries", "term", "2026-01-08", C("JNJ", "policy/press_2026-01-08_us_government_agreement_mfn.md"),
  "Enabling American patients to access medicines at comparable prices to other developed countries.")
R("ABBV", "MFN", "MFN agreement announced", "2026-01-12", "date", "2026-01-12", C("ABBV", "policy/press_2026-01-12_mfn_trump_agreement.md"),
  "The company will provide low prices in Medicaid while pledging $100 billion")
R("ABBV", "MFN", "Medicaid MFN pricing", "low prices in Medicaid", "term", "2026-01-12", C("ABBV", "policy/press_2026-01-12_mfn_trump_agreement.md"),
  "The company will provide low prices in Medicaid")
R("ABBV", "MFN", "TrumpRx listing", "Alphagan, Combigan, Humira, Synthroid", "flag", "2026-02-05", C("ABBV", "policy/press_2026-01-12_mfn_trump_agreement.md"),
  "AbbVie will also expand direct-to-patient offerings through TrumpRx for medicines used by millions of Americans, including ALPHAGAN®, COMBIGAN®, HUMIRA® and SYNTHROID®.")
R("ABBV", "MFN", "Scope", "all four presidential pricing priorities", "term", "2026-01-12", C("ABBV", "policy/press_2026-01-12_mfn_trump_agreement.md"),
  "AbbVie's agreement, which addresses all four of the President's drug pricing priorities")
for t in ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]:
    pass

# ---------------- manufacturing / capex pledges ----------------
R("MRK", "manufacturing", "US investment pledged (capex + R&D)", 70, "USD bn", "2025-12-19", C("MRK", "policy/press_2025-12-19_mfn_agreement.md"),
  "Over the next several years, Merck will invest more than $70 billion in capital and R&D spending, including at least $12 billion in capital expenditures")
R("MRK", "manufacturing", "US capex within pledge (minimum)", 12, "USD bn", "2025-12-19", C("MRK", "policy/press_2025-12-19_mfn_agreement.md"),
  "including at least $12 billion in capital expenditures")
R("MRK", "manufacturing", "Named sites", "Elkton VA $3B; Wilmington DE $1B; De Soto KS $895M; Durham NC $1B (done)", "sites", "2025-2030", C("MRK", "policy/press_2025-10_elkton_virginia_groundbreaking.md"),
  "announced today the start of construction for a $3 billion, 400,000-square-foot pharmaceutical manufacturing facility at its Elkton, Virginia, site")
R("BMY", "manufacturing", "US investment pledged", 40, "USD bn", "2025-2030", C("BMY", "policy/press_2025-12-19_us-government-agreement.md"),
  "invest $40 billion in the United States over the next five years")
R("PFE", "manufacturing", "US investment pledged (R&D + capital)", 70, "USD bn", "2025-2028", C("PFE", "policy/press_2025-09-30_mfn_landmark_agreement.md"),
  "additional $70 billion dedicated to U.S. research, development and capital projects in the next few years")
R("PFE", "manufacturing", "Current US footprint", "13 manufacturing/distribution sites, 7 R&D", "sites", "2025-09-30", C("PFE", "policy/press_2025-09-30_mfn_landmark_agreement.md"),
  "supported by 13 manufacturing and")
R("LLY", "manufacturing", "US manufacturing investment pledged", 50, "USD bn", "2025-11-06", C("LLY", "policy/press_2025-11-06_us_govt_agreement.md"),
  "investing more than $50 billion in U.S. manufacturing to boost domestic production in key therapeutic areas")
R("LLY", "manufacturing", "US manufacturing investment per White House", 27, "USD bn", "2025-11-06", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "Eli Lilly has announced at least $27 billion in new U.S. manufacturing investments")
R("NVO", "manufacturing", "US investment pledged (additional)", 10, "USD bn", "2025-11-06", G("wh/wh_fact_sheet_2025-11-06_lilly_novo.md"),
  "Novo Nordisk has committed an additional $10 billion investment to strengthen its domestic footprint")
R("ABBV", "manufacturing", "US R&D + capital pledge", 100, "USD bn", "2026-2036", C("ABBV", "policy/press_2026-01-12_mfn_trump_agreement.md"),
  "pledging $100 billion in U.S.-based research and development and capital investments, including manufacturing, over the next decade")
R("JNJ", "manufacturing", "US investment pledged", 55, "USD bn", "2025-2029", C("JNJ", "policy/press_2026-01-08_us_government_agreement_mfn.md"),
  "$55 billion investment to support U.S. manufacturing, research and development, and technology investments by early 2029")
R("AZN", "manufacturing", "US manufacturing + R&D pledge", 50, "USD bn", "2025-2030", C("AZN", "policy/press_2025-10-10_us_government_agreement.md"),
  "recently announced $50 billion investment in US medicines manufacturing and R&D over the next five years")
R("AMGN", "manufacturing", "US manufacturing capex announced 2025 (no overall pledge found)", 2.5, "USD bn", "2025", C("AMGN", "policy/press_2025-12-19_mfn_agreement.md"),
  "This year, Amgen announced an additional $2.5 billion in U.S. manufacturing capital investments")
R("AMGN", "manufacturing", "US manufacturing + R&D invested since 2018 (historic)", 40, "USD bn", "2018-2025", C("AMGN", "policy/press_2025-12-19_mfn_agreement.md"),
  "Since 2018, Amgen has invested more than $40 billion in manufacturing and research and development")
R("GILD", "manufacturing", "US investment pledged (mfg, R&D, infrastructure)", 32, "USD bn", "2025-2030", C("GILD", "policy/press_2025-12-19_mfn_agreement.md"),
  "Gilead also recently announced it will invest $32 billion in U.S.-based manufacturing, R&D, and infrastructure over the next five years")

# ---------------- tariff ----------------
PROC = G("tariff/wh_proclamation_11020_2026-04-02_section232_pharma.md")
for t in ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]:
    R(t, "tariff", "Statutory tariff-exemption end for MFN signers (Proclamation 11020)", "2029-01-20", "date", "2026-07-31", PROC,
      "the applicable ad valorem tariff rate for pharmaceuticals and associated pharmaceutical ingredients shall be zero until January 20, 2029")
R("ALL", "tariff", "Section 232 base rate on patented pharma imports", 100, "percent", "2026-07-31", PROC,
  "impose a 100 percent ad valorem duty rate on the import of patented pharmaceuticals and associated pharmaceutical ingredients")
R("ALL", "tariff", "Rate for onshoring-plan companies; rises to 100% on 2030-04-02", 20, "percent", "2026-07-31", PROC,
  "The aforementioned 20 percent rate shall increase to 100 percent on April 2, 2030.")
R("ALL", "tariff", "Rate for Japan, EU, Korea, Switzerland origin", 15, "percent", "2026-07-31", PROC,
  "shall be 15 percent for products of Japan, the European Union, the Republic of Korea, and Switzerland and Liechtenstein jointly")
R("MRK", "tariff", "Company-stated tariff relief", "3 years, Section 232 delayed", "term", "2025-12-19", K("MRK"),
  "Department of Commerce to delay Section 232 tariffs for three years, enabling the Company to make investments in the U.S. to reshore manufacturing for American patients.")
R("BMY", "tariff", "Company statement on what happens after Jan 2029", "relief until January 2029; exemptions may be terminated or not extended", "term", "2029-01", K("BMY"),
  "BMS will receive certain U.S. tariff relief until January 2029 and will not be subject to future pricing mandates in the U.S., however, such exemptions may be terminated or may not be extended.")
R("PFE", "tariff", "Company statement: conditions and risk after grace period", "3-year grace period conditional on added US manufacturing; binding final agreement pending", "term", "2025-09-30", K("PFE"),
  "We face risks and uncertainties associated with the agreement and negotiating the binding final agreement, including the possibility of, among other things, unfavorable terms and increased costs related to tariffs and investment requirements")
R("PFE", "tariff", "Company-stated tariff relief", "3-year grace period if further US manufacturing investment", "term", "2025-09-30", K("PFE"),
  "The September 2025 agreement also provides a three-year grace period during which time our products will not face Section 232 tariffs, provided the Company further invests in manufacturing in the U.S.")
R("LLY", "tariff", "Company-stated tariff relief", "3-year grace period conditional on meeting US manufacturing commitments", "term", "2025-11-06", K("LLY"),
  "The preliminary agreements also provide a three-year grace period during which time our products under a Section 232 investigation will not face tariffs, provided that we meet U.S. manufacturing investment commitments.")
R("NVO", "tariff", "Company-stated tariff relief", "3-year tariff exemption", "term", "2025-11-06", C("NVO", "policy/press_2025-11-06_us_administration_agreement.md"),
  "Novo Nordisk is expected to receive a three-year tariff exemption.")
R("NVO", "tariff", "Company statement on ongoing risk", "US admin continues to assess tariffs and reference pricing on pharma", "term", "2026-02-03", C("NVO", "20f_FY2025_d2.md"),
  "the US administration continues to assess a range of trade actions affecting US imports, including tariffs and reference pricing measures which may continue targeting pharmaceuticals")
R("ABBV", "tariff", "Company-stated tariff relief", "3-year exemption from tariffs and future price mandates", "term", "2026-01-12", K("ABBV"),
  "the U.S. government has agreed to provide AbbVie a three-year exemption from tariffs and future price mandates.")
R("JNJ", "tariff", "Company-stated tariff relief", "exemption from tariffs (no end date stated in release)", "term", "2026-01-08", C("JNJ", "policy/press_2026-01-08_us_government_agreement_mfn.md"),
  "provides the Company’s pharmaceutical products an exemption from tariffs")
R("AZN", "tariff", "Company-stated tariff relief", "Section 232 tariffs delayed 3 years", "term", "2025-10-10", C("AZN", "policy/press_2025-10-10_us_government_agreement.md"),
  "has also reached an agreement with the US Department of Commerce to delay Section 232 tariffs for three years, enabling the Company to fully onshore medicines manufacturing so that all of its medicines sold in America are made in America.")
R("AMGN", "tariff", "Company-stated tariff relief", "relief ~3 years pending final Section 232 determination", "term", "2025-12-19", K("AMGN"),
  "we received relief from Section 232 tariffs, pending final determination under such section of the Trade Expansion Act of 1962, for approximately the next three years.")
R("GILD", "tariff", "Company-stated tariff relief", "Section 232 paused 3 years, conditional on added US manufacturing investment", "term", "2025-12-19", C("GILD", "policy/press_2025-12-19_mfn_agreement.md"),
  "to be exempt from Section 232 pharmaceutical tariffs for three years, provided Gilead further invests in manufacturing in the United States.")

# ---------------- US revenue base (FY2025) ----------------
REV = [
    ("MRK", "US revenue", 36510, "USD m", K("MRK"), "United States $ 36,510 $ 32,277 $ 28,480"),
    ("MRK", "Total revenue", 65011, "USD m", K("MRK"), "Total Sales $ 65,011 $ 64,168 $ 60,115"),
    ("BMY", "US revenue", 33279, "USD m", K("BMY"), "U.S. 33,279 34,105"),
    ("BMY", "Total revenue", 48194, "USD m", K("BMY"), "Total Revenues $ 48,194 $ 48,300 $ 45,006"),
    ("PFE", "US revenue", 37078, "USD m", K("PFE"), "Total revenues $ 62,579 $ 63,627 $ 59,553 $ 37,078"),
    ("PFE", "Total revenue", 62579, "USD m", K("PFE"), "Total revenues $ 62,579 $ 63,627 $ 59,553"),
    ("LLY", "US revenue", 43481, "USD m", K("LLY"), "U.S. $ 43,481 $ 30,375 43 Outside U.S. 21,698 14,668 48 Revenue $ 65,179"),
    ("LLY", "Total revenue", 65179, "USD m", K("LLY"), "Revenue $ 65,179 $ 45,043 45"),
    ("NVO", "US revenue (US Operations net sales, geographic segment)", 159077, "DKK m", C("NVO", "20f_FY2025_d2.md"), "US Operations 159,077 155,197"),
    ("NVO", "Total revenue (geographic-segment total; group net sales DKK 309,064m)", 289015, "DKK m", C("NVO", "20f_FY2025_d2.md"), "Total net sales 289,015 261,712"),
    ("ABBV", "US revenue", 46603, "USD m", K("ABBV"), "United States $ 46,603 $ 43,029"),
    ("ABBV", "Total revenue", 61160, "USD m", K("ABBV"), "Net revenues $ 61,160 $ 56,334"),
    ("JNJ", "US revenue (worldwide 94,193 less international 40,441 = 53,752)", 53752, "USD m", K("JNJ"), "International 40,441 38,519 38,715 5.0 ( 0.5 ) Worldwide $ 94,193"),
    ("JNJ", "Total revenue", 94193, "USD m", K("JNJ"), "Worldwide $ 94,193 88,821 85,159"),
    ("AZN", "US revenue", 23970, "USD m", C("AZN", "20f_FY2025.md"), "US 23,970 21,806 18,121"),
    ("AZN", "Total revenue", 58739, "USD m", C("AZN", "20f_FY2025.md"), "Total Revenue 58,739 54,073 45,811"),
    ("AMGN", "US revenue (US product sales)", 25656, "USD m", K("AMGN"), "U.S. $ 25,656 73 % $ 23,301 73 %"),
    ("AMGN", "Total revenue", 36751, "USD m", K("AMGN"), "Total revenues $ 36,751 10 % $ 33,424"),
    ("GILD", "US revenue", 20876, "USD m", K("GILD"), "Total revenues $ 20,876 $ 5,064 $ 3,503 $ 29,443"),
    ("GILD", "Total revenue", 29443, "USD m", K("GILD"), "Total revenues $ 29,443 $ 28,754"),
]
for t, item, v, u, doc, q in REV:
    R(t, "exposure_base", "FY2025 " + item, v, u, "2025-12-31", doc, q)

# ---------------- IRA drug revenue (FY2025, company-reported) ----------------
IRAREV = [
    ("MRK", "Januvia/Janumet", 2544, "USD m", K("MRK"), "Januvia/Janumet 2,544 2,268 3,366", "worldwide"),
    ("BMY", "Eliquis", 14443, "USD m", K("BMY"), "Legacy Portfolio Eliquis 14,443 13,333 12,206", "worldwide"),
    ("BMY", "Pomalyst/Imnovid", 2733, "USD m", K("BMY"), "Pomalyst/Imnovid 2,733 3,545 3,441", "worldwide"),
    ("BMY", "Orencia", 3705, "USD m", K("BMY"), "Orencia 3,705 3,682 1 %", "worldwide"),
    ("PFE", "Ibrance", 4122, "USD m", K("PFE"), "Ibrance $4,122 Down 6% (operationally)", "worldwide"),
    ("PFE", "Xeljanz", 1087, "USD m", K("PFE"), "Xeljanz $1,087 Down 7% (operationally)", "worldwide"),
    ("LLY", "Trulicity (US 2,914 + outside US 1,362)", 4276, "USD m", K("LLY"), "Trulicity 2,914 3,694 5,433 1,362 1,560 1,699", "worldwide, computed"),
    ("LLY", "Verzenio", 5723, "USD m", K("LLY"), "Verzenio 3,464 2,259 5,723 5,307 8", "worldwide"),
    ("NVO", "Ozempic", 127089, "DKK m", C("NVO", "20f_FY2025.md"), "Ozympic ® 127,089 88,467 38,622", "worldwide"),
    ("NVO", "Wegovy", 79106, "DKK m", C("NVO", "20f_FY2025.md"), "Wegovy ® 79,106 51,015 28,091", "worldwide"),
    ("NVO", "Rybelsus", 22093, "DKK m", C("NVO", "20f_FY2025.md"), "Rybelsus ® 22,093 8,833 13,260", "worldwide"),
    ("NVO", "Fast-acting insulin (category incl. NovoLog/Fiasp and non-selected products)", 18583, "DKK m", C("NVO", "20f_FY2025_d2.md"), "Fast-acting insulin 8,245 7,773 5,265 10,338 10,749 10,684", "worldwide, upper bound"),
    ("ABBV", "Imbruvica (US net revenues only)", 2048, "USD m", K("ABBV"), "Imbruvica United States $ 2,048 $ 2,448 $ 2,665", "US only"),
    ("ABBV", "Linzess/Constella (US 864 + intl 43)", 907, "USD m", K("ABBV"), "Linzess/Constella United States $ 864 $ 916 $ 1,073", "worldwide, computed"),
    ("ABBV", "Vraylar", 3621, "USD m", K("ABBV"), "Vraylar United States $ 3,612 $ 3,260 $ 2,755", "worldwide (US 3,612 + intl 9)"),
    ("ABBV", "Botox Therapeutic (excl. Botox Cosmetic)", 3769, "USD m", K("ABBV"), "Botox Therapeutic United States $ 3,151 $ 2,718 $ 2,476", "worldwide (US 3,151 + intl 618)"),
    ("JNJ", "Xarelto", 2633, "USD m", K("JNJ"), "XARELTO U.S. 2,633 2,373 2,365", "worldwide = US"),
    ("JNJ", "Stelara", 6078, "USD m", K("JNJ"), "STELARA U.S. 3,847 6,720 6,966", "worldwide (US 3,847)"),
    ("JNJ", "Erleada", 3574, "USD m", K("JNJ"), "ERLEADA U.S. 1,453 1,282 1,065", "worldwide (US 1,453)"),
    ("AZN", "Farxiga", 8400, "USD m", C("AZN", "20f_FY2025.md"), "Farxiga 8,400 10 9 1,730", "worldwide product sales"),
    ("AZN", "Calquence", 3518, "USD m", C("AZN", "20f_FY2025.md"), "Calquence 3,518 12 12 2,339", "worldwide product sales"),
    ("AMGN", "Enbrel", 2226, "USD m", K("AMGN"), "ENBREL 2,226 (33) % 3,316", "worldwide"),
    ("AMGN", "Otezla", 2265, "USD m", K("AMGN"), "Otezla 2,265 7 % 2,126", "worldwide"),
    ("GILD", "Biktarvy", 14334, "USD m", K("GILD"), "Biktarvy $ 11,467 $ 1,676 $ 1,190 $ 14,334", "worldwide"),
]
for t, d, v, u, doc, q, basis in IRAREV:
    R(t, "IRA", f"FY2025 revenue of selected drug: {d}", v, u, "2025-12-31", doc, q, basis)

# ---------------- IRA selected drugs: (ticker, drug, IPAY, MFP, list, pct, quotes) ----------------
F26 = G("cms/cms_fact_sheet_negotiated_prices_ipay2026.md")
F27 = G("cms/cms_fact_sheet_negotiated_prices_ipay2027.md")
IRA = [
    ("MRK", "Januvia", 2026, 113, 527, 79, F26, "Januvia Merck Sharp Dohme Diabetes $113.00 $527.00 79%"),
    ("BMY", "Eliquis", 2026, 231, 521, 56, F26, "Eliquis Bristol Myers Squibb Prevention and treatment of blood clots $231.00 $521.00 56%"),
    ("JNJ", "Xarelto", 2026, 197, 517, 62, F26, "$197.00 $517.00 62%"),
    ("JNJ", "Stelara", 2026, 4695, 13836, 66, F26, "$4,695.00 $13,836.00 66%"),
    ("ABBV", "Imbruvica", 2026, 9319, 14934, 38, F26, "Imbruvica Pharmacyclics LLC Blood cancers $9,319.00 $14,934.00 38%"),
    ("AZN", "Farxiga", 2026, 178.5, 556, 68, F26, "$178.50 $556.00 68%"),
    ("NVO", "Fiasp/NovoLog", 2026, 119, 495, 76, F26, "Novo Nordisk Inc Diabetes $119.00 $495.00 76%"),
    ("AMGN", "Enbrel", 2026, 2355, 7106, 67, F26, "$2,355.00 $7,106.00 67%"),
    ("NVO", "Ozempic/Rybelsus/Wegovy", 2027, 274, 959, 71, F27, "$274 $959 71%"),
    ("BMY", "Pomalyst", 2027, 8650, 21744, 60, F27, "$8,650 $21,744 60%"),
    ("PFE", "Ibrance", 2027, 7871, 15741, 50, F27, "Ibrance Pfizer Inc. Breast cancer $7,871 $15,741 50%"),
    ("ABBV", "Linzess", 2027, 136, 539, 75, F27, "$136 $539 75%"),
    ("ABBV", "Vraylar", 2027, 770, 1376, 44, F27, "$770 $1,376 44%"),
    ("AZN", "Calquence", 2027, 8600, 14228, 40, F27, "$8,600 $14,228 40%"),
    ("MRK", "Janumet/Janumet XR", 2027, 80, 526, 85, F27, "Janumet; Janumet XR Merck Sharp & Dohme LLC Type 2 diabetes $80 $526 85%"),
    ("AMGN", "Otezla/Otezla XR", 2027, 1650, 4722, 65, F27, "$1,650 $4,722 65%"),
]
for t, d, ipay, mfp, lst, pct, doc, q in IRA:
    eff = f"{ipay}-01-01"
    R(t, "IRA", f"IRA {d} (IPAY {ipay}): MFP per 30-day supply", mfp, "USD", eff, doc, q)
    R(t, "IRA", f"IRA {d} (IPAY {ipay}): list price per 30-day supply", lst, "USD", eff, doc, q, "list price = WAC reference year per CMS note")
    R(t, "IRA", f"IRA {d} (IPAY {ipay}): % cut of MFP vs list", pct, "percent", eff, doc, q)

F28 = G("cms/cms_fact_sheet_selected_list_ipay2028.md")
IRA28 = [
    ("LLY", "Trulicity", "$4,898,378,000"), ("GILD", "Biktarvy", "$3,904,486,000"), ("BMY", "Orencia", "$2,450,065,000"),
    ("JNJ", "Erleada", "$1,947,504,000"), ("LLY", "Verzenio", "$1,428,714,000"), ("ABBV", "Botox; Botox Cosmetic", "$1,143,070,000"),
    ("PFE", "Xeljanz; Xeljanz XR", "$1,013,332,000"),
]
for t, d, spend in IRA28:
    amt = int(spend.replace("$", "").replace(",", "")) / 1e6
    R(t, "IRA", f"IRA {d} (IPAY 2028): selected 2026-01-27; MFP not yet published; Medicare Part B+D expenditure Nov 2024-Oct 2025", amt, "USD m", "2028-01-01", F28,
      [spend, "$1,143,070,000", spend.replace("$", "$")], "MFP due after negotiation ends in 2026")
R("MRK", "IRA", "Keytruda expected IRA selection in 2027, MFP effective 2029-01-01; US sales expected to decline materially", "2029-01-01", "date", "2029-01-01", K("MRK"),
  "Furthermore, the Company expects that Keytruda will be selected in 2027 for government price setting, which would become effective on January 1, 2029")
R("AMGN", "IRA", "Enbrel/Otezla IRA effect disclosed", "see 10-K", "term", "2026-01-01", K("AMGN"),
  "In addition to the IRA, other proposed U.S. policy actions focus on drug pricing")
