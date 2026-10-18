"""verified/secx/comment_letter_findings.csv: one row per SEC staff comment exchange (2019+), read by hand.

Quotes are copied from data/moat/companies/<T>/sec_letters/*.md (whitespace collapsed); pages are the
[[page N]] markers in those files (CORRESP .htm files have only page markers inserted by the collector).
"""
from agent.moat.verify.s_write import out

L = "data/moat/companies/{t}/sec_letters/{f}"
COLS = ["ticker", "exchange_id", "staff_letter_date", "reply_date", "close_date", "filing_reviewed", "topic",
        "staff_ask", "company_answer", "next_filing_disclosure", "next_filing_cite", "why_it_matters",
        "impact_estimate", "finding_candidate", "confidence", "staff_quote", "staff_quote_cite", "reply_quote",
        "reply_quote_cite", "staff_url", "reply_url"]


def u(cik, acc, ext):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/filename1.{ext}"


R = []
# ---------------- MRK ----------------
R.append(dict(
    ticker="MRK", exchange_id="MRK-2025-10K", staff_letter_date="2025-04-10", reply_date="2025-04-16",
    close_date="2025-04-28", filing_reviewed="10-K FY2024", topic="license dependence (Keytruda)",
    staff_ask="Because Keytruda was 46% of 2024 revenue, staff asked Merck to file the Keytruda license agreements as exhibits or explain why it is not substantially dependent on them.",
    company_answer="Merck said it owns all rights to pembrolizumab, so it is not dependent on the two royalty-bearing licenses (6.5% falling to 2.5% in 2024 and ending 12/31/2026; plus 2% expiring by country), and filed nothing.",
    next_filing_disclosure="FY2025 10-K repeats the same royalty language (6.5% to 2.5%, through 2026, also applies to Keytruda Qlex; 2% royalty expired US Sep 2024 and major EU 2H25 but continues elsewhere); no agreement filed.",
    next_filing_cite="data/corpus/companies/MRK/10k_FY2025.md pdf 56 / printed 54; prior year data/corpus/companies/MRK/10k_FY2024.md pdf 55 / printed 53",
    why_it_matters="Royalty terms on the single product that is ~half of revenue sit in an MD&A paragraph, and the 2.5% royalty roll-off at end-2026 is a cost-of-sales tailwind that partly offsets Keytruda's 2028 LOE narrative.",
    impact_estimate="Estimate: 2.5% x ~$29-31B Keytruda sales = ~$0.7-0.8B/yr lower royalty expense from 2027 (Keytruda 2024 sales derived from 46% x total revenue; check product table).",
    finding_candidate="yes", confidence="high",
    staff_quote="We note that Keytruda accounted for 46% of your revenues in 2024. Please either file these agreements pursuant to Item 601(b)(10)(ii)(B) of Regulation S-K or explain why you believe your are not substantially dependent on licensing agreements providing you with the right to sell Keytruda.",
    staff_quote_cite=L.format(t="MRK", f="2025-04-10_UPLOAD_0000000000-25-003816.md") + " p1",
    reply_quote="As the Company owns all rights to Keytruda and does not rely on these agreements for its use or sale, the Company is not substantially dependent on any of these agreements and therefore does not believe that it is required to file any of these agreements pursuant to Item 601(b)(10)(ii)(B) of Regulation S-K.",
    reply_quote_cite=L.format(t="MRK", f="2025-04-16_CORRESP_0001628280-25-017960.md") + " p2",
    staff_url=u(310158, "0000000000-25-003816", "pdf"), reply_url=u(310158, "0001628280-25-017960", "htm")))
# ---------------- JNJ ----------------
R.append(dict(
    ticker="JNJ", exchange_id="JNJ-2025-10K", staff_letter_date="2025-04-16", reply_date="2025-04-23",
    close_date="2025-05-02", filing_reviewed="10-K FY2024", topic="license terms (Darzalex / Genmab)",
    staff_ask="Staff asked J&J to disclose the material terms of the Genmab license for Darzalex and Darzalex Faspro (aggregate paid, royalty rate range, term and termination) and to file the agreement as an exhibit.",
    company_answer="J&J said the license is ordinary course and need not be filed, but agreed to add the 12%-20% royalty range and annual royalty paid (about $2B in 2024) to future 10-Ks.",
    next_filing_disclosure="FY2025 10-K Item 1 now states: Darzalex franchise 15.0% of revenue; royalty 12% to 20% of total Darzalex net sales; royalties to Genmab ~$2.4B (2025) and ~$2.0B (2024); Genmab patent families expire US 2029, EU 2031/2032. Agreement still not filed as an exhibit.",
    next_filing_cite="data/corpus/companies/JNJ/10k_FY2025.md pdf 8 / printed 3",
    why_it_matters="A royalty of up to 20% on J&J's largest product (about $2.4B a year) was disclosed only because the SEC asked; it is a margin lever tied to 2029 patent expiry that the segment tables never showed.",
    impact_estimate="~$2.4B royalty paid FY2025 (10-K); implied Darzalex sales ~$14B+ at 15.0% of revenue; royalty stops on the Genmab families after US 2029 expiry if J&J's own Faspro patents hold.",
    finding_candidate="yes", confidence="high",
    staff_quote="In future filings, please revise to disclose the material terms of your licensing agreement with Genmab A/S relating to your Darzalex and Darzalex Faspro products or tell us why you believe such disclosure is not required.",
    staff_quote_cite=L.format(t="JNJ", f="2025-04-16_UPLOAD_0000000000-25-004012.md") + " p1",
    reply_quote="Although the Company does not believe that disclosure of the material terms of the License Agreement would be required in its annual report, the Company will add disclosure substantially similar to the following in its future Form 10-K filings to the extent still relevant:",
    reply_quote_cite=L.format(t="JNJ", f="2025-04-23_CORRESP_0001341004-25-000025.md") + " p2",
    staff_url=u(200406, "0000000000-25-004012", "pdf"), reply_url=u(200406, "0001341004-25-000025", "htm")))
R.append(dict(
    ticker="JNJ", exchange_id="JNJ-2021-10K", staff_letter_date="2021-04-27", reply_date="2021-05-04",
    close_date="2021-05-27", filing_reviewed="10-K FY2020", topic="government agreements (COVID-19 vaccine / BARDA)",
    staff_ask="Staff asked whether J&J should disclose its BARDA and other government COVID-19 vaccine agreements, their terms, and how the amounts were recognized.",
    company_answer="J&J said the up-to-$1B BARDA cost-share was not material (booked as a reduction of R&D under ASC 730-20) and redacted the 2020 dollar amounts under Rule 83 confidential treatment.",
    next_filing_disclosure="Not checked (FY2021 10-K not in collection).", next_filing_cite="",
    why_it_matters="Shows R&D was reported net of government reimbursement with the amounts redacted from the public letter.",
    impact_estimate="Up to $1B reimbursement over 2020-2025 against $12.2B total 2020 R&D (reply); exact 2020 offset redacted.",
    finding_candidate="no", confidence="high",
    staff_quote="Please tell us your consideration of disclosing material agreements entered into with U.S. and other governments for the development and distribution of your COVID-19 vaccine, the significant terms of such agreements and how related amounts have been recognized in your financial statements.",
    staff_quote_cite=L.format(t="JNJ", f="2021-04-27_UPLOAD_0000000000-21-005337.md") + " p1",
    reply_quote="Consistent with the application of these factors we determined the above-referenced agreement with BARDA is not material and our disclosures are adequate as further outlined below.",
    reply_quote_cite=L.format(t="JNJ", f="2021-05-04_CORRESP_0001341004-21-000177.md") + " p2",
    staff_url=u(200406, "0000000000-21-005337", "pdf"), reply_url=u(200406, "0001341004-21-000177", "htm")))
R.append(dict(
    ticker="JNJ", exchange_id="JNJ-2019-10K", staff_letter_date="2019-07-18 (posted 2019-07-24)", reply_date="2019-08-22",
    close_date="2019-09-20", filing_reviewed="10-K FY2018 and 8-K 2019-01-22", topic="talc loss contingency; non-GAAP litigation exclusion; Syria/Sudan",
    staff_ask="Staff asked why J&J could not estimate a reasonably possible loss range for talc despite a $4.7B adverse verdict, why litigation charges are excluded from non-GAAP, and about Syria/Sudan sales.",
    company_answer="J&J said talc and opioid claims are too variable to estimate a range, defended excluding above-threshold litigation from non-GAAP, and described humanitarian sales; no disclosure change was committed.",
    next_filing_disclosure="Not checked (FY2019 10-K not in collection).", next_filing_cite="",
    why_it_matters="The company kept both a no-range talc contingency and a non-GAAP measure that strips the same litigation out, so adjusted EPS never carried the talc exposure the SEC flagged.",
    impact_estimate="$4.7B single verdict (July 2018) cited by staff; J&J accrued defense costs only at the time.",
    finding_candidate="yes", confidence="medium",
    staff_quote="Please explain to us whether you believe that it is at least reasonably possible that you will not prevail on appeal and would therefore be subject to the $4.7 billion judgment.",
    staff_quote_cite=L.format(t="JNJ", f="2019-07-24_UPLOAD_0000000000-19-011503.md") + " p2",
    reply_quote="The Company has been unable to estimate a range of reasonably possible loss for these matters for several reasons, including, among others, the following:",
    reply_quote_cite=L.format(t="JNJ", f="2019-08-22_CORRESP_0000200406-19-000055.md") + " p5",
    staff_url=u(200406, "0000000000-19-011503", "pdf"), reply_url=u(200406, "0000200406-19-000055", "htm")))
# ---------------- AMGN ----------------
R.append(dict(
    ticker="AMGN", exchange_id="AMGN-2024-10K", staff_letter_date="2024-04-05", reply_date="2024-04-19 (filed 2024-04-22)",
    close_date="2024-05-10", filing_reviewed="10-K FY2023", topic="MD&A price vs volume drivers",
    staff_ask="Staff noted Amgen quantified volume growth and net selling price changes on earnings calls and releases but only described them qualitatively in the 10-K MD&A, and asked why.",
    company_answer="Amgen called its MD&A compliant, agreed to quantify price and volume at the total-portfolio level in future filings, and said it would cut back the detail in its earnings releases and calls.",
    next_filing_disclosure="FY2024 10-K MD&A now quantifies: product sales +19%, volume +23%, net selling price -2%, US volume +26%, ROW +17%, other brands volume +11%. FY2023 10-K said only 'volume growth for certain brands'.",
    next_filing_cite="data/corpus/companies/AMGN/10k_FY2024.md pdf 69 / printed 63 (also pdf 67 / printed 61); before: data/moat/companies/AMGN/10k_FY2023.md pdf 69 / printed 62",
    why_it_matters="Price erosion is now in the filing, but Amgen promised to cut earnings-call detail, so per-product price and volume figures may have stopped being reported after 2024 (a 'metric they stopped reporting' lead to check in transcripts).",
    impact_estimate="Net price -2% on ~$32B 2024 product sales = ~-$0.6B; volume +23% was mostly Horizon ($4.2B vs $0.95B).",
    finding_candidate="yes", confidence="high",
    staff_quote="Please tell us what consideration you gave to providing these discussions of changes in quantitative terms within MD&A in addition to your qualitative discussions of operating results in consideration of Item 303(b)(iii)(3) of Regulation S-K.",
    staff_quote_cite=L.format(t="AMGN", f="2024-04-05_UPLOAD_0000000000-24-003674.md") + " p1",
    reply_quote="Following our acquisition of Horizon in the fourth quarter of 2023 (and the overall evolution of our business), we have concluded that we should revisit our approach to our disclosures in our earnings press release and earnings call webcast, and we will accordingly refine the level of detail in these disclosures to better enable investors to focus on key items more easily.",
    reply_quote_cite=L.format(t="AMGN", f="2024-04-22_CORRESP_0001193125-24-105075.md") + " p3",
    staff_url=u(318154, "0000000000-24-003674", "pdf"), reply_url=u(318154, "0001193125-24-105075", "htm")))
R.append(dict(
    ticker="AMGN", exchange_id="AMGN-2021-S4", staff_letter_date="2021-02-18", reply_date="2021-02-09 / 2021-04-13",
    close_date="2021-04-13", filing_reviewed="S-4 note exchange offer (2.770% notes due 2053)", topic="procedural (no review)",
    staff_ask="Staff said it would not review the debt exchange S-4.", company_answer="Exxon Capital representations and an acceleration request.",
    why_it_matters="Procedural only.", finding_candidate="no", confidence="high",
    staff_quote="This is to advise you that we have not reviewed and will not review your registration statement.",
    staff_quote_cite=L.format(t="AMGN", f="2021-02-18_UPLOAD_0000000000-21-002057.md") + " p1",
    staff_url=u(318154, "0000000000-21-002057", "pdf"), reply_url=u(318154, "0001193125-21-114647", "htm")))
# ---------------- PFE ----------------
R.append(dict(
    ticker="PFE", exchange_id="PFE-2021-10K", staff_letter_date="2021-12-10", reply_date="2021-12-23; 2022-04-12",
    close_date="2022-04-14", filing_reviewed="10-K FY2020", topic="non-GAAP (full non-GAAP P&L; upfront and milestone exclusion)",
    staff_ask="Staff said Pfizer's reconciliation was effectively a full non-GAAP income statement and questioned excluding upfront and milestone payments on collaborations from Adjusted Income.",
    company_answer="Pfizer first defended the above-threshold exclusion, then after calls with staff agreed from Q1 2022 to include acquired IPR&D (upfronts, milestones, asset acquisitions) in non-GAAP and recast prior periods, and replaced the reconciliation tables.",
    next_filing_disclosure="FY2022 10-K shows Acquired IPR&D as its own line: $953M (2022), $3,469M (2021), $684M (2020); these now hit Adjusted income.",
    next_filing_cite="data/moat/companies/PFE/10k_FY2022.md pdf 39 / printed 34",
    why_it_matters="Before 2022 Pfizer's adjusted EPS (also a pay metric) excluded the largest licensing deals; the SEC forced them back in, which changes any multi-year adjusted EPS trend that crosses 2021.",
    impact_estimate="2021 acquired IPR&D $3.47B; at ~5.7B diluted shares ~$0.6/share pre-tax that the old policy could exclude (only above-threshold deals were excluded, so true recast is smaller).",
    finding_candidate="yes", confidence="high",
    staff_quote="Here you include in note I adjustments to exclude the upfront and milestone payments made for collaboration agreements from Research and developments expense and net income attributable to Pfizer Inc. common shareholders.",
    staff_quote_cite=L.format(t="PFE", f="2021-12-10_UPLOAD_0000000000-21-014850.md") + " p2",
    reply_quote="After consulting with the Staff, we hereby undertake to change our future filings to include in our externally reported Non-GAAP financial measures expenses for (a) acquired in-process research and development costs incurred in connection with upfront and milestone payments on collaboration and in-license agreements, including premiums on equity securities and (b) asset acquisitions of acquired in-process research and development.",
    reply_quote_cite=L.format(t="PFE", f="2022-04-12_CORRESP_0000078003-22-000055.md") + " p2",
    staff_url=u(78003, "0000000000-21-014850", "pdf"), reply_url=u(78003, "0000078003-22-000055", "htm")))
R.append(dict(
    ticker="PFE", exchange_id="PFE-2024-TOI", staff_letter_date="2024-08-15", reply_date="2024-08-22", close_date="",
    filing_reviewed="Schedule TO-I (PSA/TSRU Modification Offer)", topic="employee equity award modification offer",
    staff_ask="Staff said the offer to modify employee PSAs and TSRUs could not exclude holders by jurisdiction or by hire date without a compensatory purpose.",
    company_answer="Pfizer revised the eligibility disclosure on pages 1, 7, 8 and 17.",
    why_it_matters="Pfizer re-cut outstanding performance awards in 2024; relevant context for pay-for-performance in task 2 but not a disclosure finding.",
    finding_candidate="no", confidence="medium",
    staff_quote="While you need not disseminate offer materials in jurisdictions where you may not legally do so, you must accept elections to participate from all eligible holders who elect to participate in the Modification Offer.",
    staff_quote_cite=L.format(t="PFE", f="2024-08-15_UPLOAD_0000000000-24-009384.md") + " p1",
    reply_quote="Pfizer respectfully acknowledges the Staff's comment and has revised the relevant disclosure regarding the eligible participants on pages 1, 7, 8, and 17 accordingly.",
    reply_quote_cite=L.format(t="PFE", f="2024-08-22_CORRESP_0000930413-24-002370.md") + " p2",
    staff_url=u(78003, "0000000000-24-009384", "pdf"), reply_url=u(78003, "0000930413-24-002370", "htm")))
# ---------------- LLY ----------------
R.append(dict(
    ticker="LLY", exchange_id="LLY-2021-NONGAAP", staff_letter_date="2021-12-09", reply_date="2022-01-10; 2022-04-07",
    close_date="2022-04-08", filing_reviewed="10-K FY2020 and Q3 2021 earnings release 8-K", topic="non-GAAP (acquired IPR&D exclusion)",
    staff_ask="Staff asked why Lilly excluded upfront payments for acquired IPR&D (asset deals and licenses) from non-GAAP when they look like normal recurring cash operating expenses.",
    company_answer="Lilly argued at length the charges were unpredictable 'buy-in' investments, then after calls agreed that from Q1 2022 non-GAAP would include acquired IPR&D upfronts and development milestones, recasting prior periods.",
    next_filing_disclosure="FY2022 10-K highlights acquired IPR&D and development milestones of $908.5M (2022) and $970.1M (2021); from 2022 these are no longer adjusted out of non-GAAP EPS.",
    next_filing_cite="data/moat/companies/LLY/10k_FY2022.md pdf 38 / printed 38",
    why_it_matters="Lilly's own letter warned it might stop giving non-GAAP guidance without the adjustment; the change lowers adjusted EPS by every BD deal and matters to any EPS-based bonus (see incentive_metrics).",
    impact_estimate="Acquired IPR&D in non-GAAP: 2018 $1.98B, 2019 $0.24B, 2020 $0.66B, 9M 2021 $0.50B (reply table); 2021 full year $970M ~ $1.07/share pre-tax at ~0.9B shares.",
    finding_candidate="yes", confidence="high",
    staff_quote="For each type of acquired IPR&D transaction (i.e., asset acquisitions, license agreements, etc.), explain to us why you believe it is appropriate to include non- GAAP adjustments for these upfront payments given that these expenditures appear to be normal, recurring, cash operating expenses necessary to operate your business.",
    staff_quote_cite=L.format(t="LLY", f="2021-12-09_UPLOAD_0000000000-21-014789.md") + " p2",
    reply_quote="In response to the Staff's comment and as discussed with the Staff, beginning with Lilly's earnings release for the quarter ended March 31, 2022, Lilly will not include adjustments for upfront charges and developmental milestones related to acquired in-process research and development projects acquired in a transaction other than a business combination in presentations of its non-GAAP measures.",
    reply_quote_cite=L.format(t="LLY", f="2022-04-07_CORRESP_0000059478-22-000113.md") + " p2",
    staff_url=u(59478, "0000000000-21-014789", "pdf"), reply_url=u(59478, "0000059478-22-000113", "htm")))
R.append(dict(
    ticker="LLY", exchange_id="LLY-2023-CLIMATE", staff_letter_date="2023-09-06; 2023-09-29; 2023-11-01",
    reply_date="2023-09-20; 2023-10-26; 2023-11-09", close_date="2023-11-15", filing_reviewed="10-K FY2022",
    topic="climate disclosure vs ESG/CDP reports",
    staff_ask="Staff asked why the 10-K had less climate detail than Lilly's ESG and CDP reports, and pressed three rounds for weather damages, water risk, insurance cost and carbon credits.",
    company_answer="Lilly said none was material: no tracked weather loss events of $100,000 or more in 2020-2022, property insurance about 0.08% of costs, and no change to the filing.",
    next_filing_disclosure="No new 10-K disclosure committed beyond 'will continue to evaluate'.", next_filing_cite="",
    why_it_matters="Low case value: the ESG-vs-filing gap was closed by immaterial numbers, no hidden economics.",
    impact_estimate="Immaterial per company (property insurance 0.078% / 0.077% / ~0.08% of COGS+opex 2020-2022).",
    finding_candidate="no", confidence="high",
    staff_quote="We note that you provided more expansive disclosure in your 2022 ESG Report, CDP 2022 Climate response and 2022 CDP Water Security response than you provided in your SEC filings.",
    staff_quote_cite=L.format(t="LLY", f="2023-09-06_UPLOAD_0000000000-23-009838.md") + " p1",
    reply_quote="For each of the years ended December 31, 2022, 2021 and 2020, there were no tracked damage or loss events affecting our property and operations from weather related events that met or exceeded that threshold.",
    reply_quote_cite=L.format(t="LLY", f="2023-11-09_CORRESP_0000059478-23-000288.md") + " p2",
    staff_url=u(59478, "0000000000-23-009838", "pdf"), reply_url=u(59478, "0000059478-23-000288", "htm")))
R.append(dict(
    ticker="LLY", exchange_id="LLY-2019-ELANCO", staff_letter_date="2019-02-15 (posted 2019-03-22)", reply_date="2019-02-19",
    close_date="", filing_reviewed="Elanco S-4 / Lilly Schedule TO-I (Elanco split-off exchange offer)", topic="M&A procedural",
    staff_ask="Staff asked whether Lilly should quantify the 'material adverse change in stock price' termination condition in the Elanco exchange offer.",
    company_answer="Lilly's counsel defended the pricing mechanism by analogy to the CBS-Entercom exchange offer.",
    why_it_matters="Tender-offer mechanics; no economics hidden.", finding_candidate="no", confidence="high",
    staff_quote="Disclosure on page 86 indicates that Lilly may terminate the exchange offer if there occurs, or Lilly reasonably expects there may occur, a material adverse change in the stock price of Elanco or the stock price of Lilly.",
    staff_quote_cite=L.format(t="LLY", f="2019-03-22_UPLOAD_0000000000-19-005567.md") + " p1",
    staff_url=u(59478, "0000000000-19-005567", "pdf"), reply_url=u(59478, "0001104659-19-009289", "htm")))
R.append(dict(
    ticker="LLY", exchange_id="LLY-2021-PREVAIL", staff_letter_date="2020-12-31 (not collected)", reply_date="2021-01-05",
    close_date="", filing_reviewed="Schedule TO-T for Prevail Therapeutics", topic="CVR as security (M&A)",
    staff_ask="Staff asked for a legal analysis of whether the Prevail contingent value rights are securities requiring registration (staff letter itself not in collection).",
    company_answer="Lilly argued the CVRs are not securities.",
    why_it_matters="CVR milestone payments are acquisition contingent consideration; the economics are in the TO-T, not this letter.",
    finding_candidate="no", confidence="medium",
    reply_quote="described in the Offer to Purchase are not",
    reply_quote_cite=L.format(t="LLY", f="2021-01-05_CORRESP_0001193125-21-001454.md") + " p2",
    reply_url=u(59478, "0001193125-21-001454", "htm")))
# ---------------- NVO ----------------
R.append(dict(
    ticker="NVO", exchange_id="NVO-2023-CLIMATE", staff_letter_date="2023-08-31; 2023-09-27; 2023-11-03",
    reply_date="2023-09-13; 2023-10-20; 2023-11-24", close_date="2023-12-01", filing_reviewed="20-F FY2022",
    topic="climate disclosure vs Annual Report/CDP",
    staff_ask="Staff asked why the 20-F had less climate detail than Novo's Annual Report and CDP reports, then pressed on water, weather damage, insurance and reputational risk.",
    company_answer="Novo said no climate effect was material, it bought or sold no carbon credits, and it named one ERM risk ('Inability to reduce emissions and plastic footprint may impact our reputation negatively') judged not material.",
    next_filing_disclosure="No 20-F change committed.", next_filing_cite="",
    why_it_matters="Low case value; same SEC climate sweep as LLY.", impact_estimate="None quantified.",
    finding_candidate="no", confidence="high",
    staff_quote="We note that you provided more expansive disclosure in your Annual Report 2022, CDP Climate Change 2022 Report, CDP Water Security 2022 Report and on your website than you provided in your SEC filings.",
    staff_quote_cite=L.format(t="NVO", f="2023-08-31_UPLOAD_0000000000-23-009666.md") + " p1",
    reply_quote="The Company acknowledges the Staff's comment and respectfully advises the Staff that the Company has not acquired or sold any carbon credits or offsets in any of the periods presented in the 2022 Form 20-F, nor do we have any concrete plans for acquiring or selling such credits or offsets in the foreseeable future.",
    reply_quote_cite=L.format(t="NVO", f="2023-09-13_CORRESP_0000950103-23-013525.md") + " p1",
    staff_url=u(353278, "0000000000-23-009666", "pdf"), reply_url=u(353278, "0000950103-23-013525", "htm")))
# ---------------- ABBV ----------------
R.append(dict(
    ticker="ABBV", exchange_id="ABBV-2020-10K", staff_letter_date="2020-12-22; 2021-03-16", reply_date="2021-01-15; 2021-03-19",
    close_date="2021-05-04", filing_reviewed="10-K FY2019 (Item 11, by reference to 2020 proxy)", topic="buybacks and non-GAAP pay metrics; forum selection",
    staff_ask="Staff asked how stock repurchases affected executive pay given non-GAAP EPS goals, and why the proxy did not reconcile non-GAAP income before taxes or name the 'specific items'.",
    company_answer="AbbVie said 2019 buybacks added $0.03 to EPS but did not change pay because EPS was already above the maximum, and committed to reconcile non-GAAP pretax income and name the adjustments in future proxies.",
    next_filing_disclosure="2026 proxy contains no discussion of share repurchases (grep 'repurchase', 'buyback' = 0 hits); the commitment was 'to the extent material'.",
    next_filing_cite="data/moat/companies/ABBV/proxy_2026.md (0 hits)",
    why_it_matters="AbbVie pays on adjusted EPS and non-GAAP pretax income that exclude 'specified items'; the SEC had to ask for the reconciliation, which connects to any Humira-erosion or IPR&D adjustments flowing into bonus metrics.",
    impact_estimate="$0.03 EPS from 2019 buybacks (reply); payout capped at maximum.",
    finding_candidate="yes", confidence="medium",
    staff_quote="Please tell us the impact of stock repurchases, if any, on levels of executive compensation and confirm that you will discuss the impact in future filings.",
    staff_quote_cite=L.format(t="ABBV", f="2020-12-22_UPLOAD_0000000000-20-012305.md") + " p1",
    reply_quote="EPS exceeded the maximum range for the 2019 Fiscal Year and would still have done so if the Company had disregarded the favorable $0.03 impact.",
    reply_quote_cite=L.format(t="ABBV", f="2021-01-15_CORRESP_0001104659-21-004698.md") + " p1",
    staff_url=u(1551152, "0000000000-20-012305", "pdf"), reply_url=u(1551152, "0001104659-21-004698", "htm")))
R.append(dict(
    ticker="ABBV", exchange_id="ABBV-2022-PROXY", staff_letter_date="2022-09-20", reply_date="2022-10-04", close_date="2022-10-20",
    filing_reviewed="DEF 14A 2022", topic="board leadership and risk oversight",
    staff_ask="Staff asked AbbVie to expand on its combined leadership structure, the Lead Independent Director's role and how the board oversees risk.",
    company_answer="AbbVie said existing disclosure complied but promised enhanced disclosure.",
    why_it_matters="Governance boilerplate (part of an SEC sweep).", finding_candidate="no", confidence="high",
    staff_quote="Please expand your discussion of the reasons you believe that your leadership structure is appropriate, addressing your specific characteristics or circumstances.",
    staff_quote_cite=L.format(t="ABBV", f="2022-09-20_UPLOAD_0000000000-22-010309.md") + " p1",
    reply_quote="However, we confirm that, in future filings, we will enhance our disclosure regarding the board's administration of its risk oversight function.",
    reply_quote_cite=L.format(t="ABBV", f="2022-10-04_CORRESP_0001104659-22-105695.md") + " p1",
    staff_url=u(1551152, "0000000000-22-010309", "pdf"), reply_url=u(1551152, "0001104659-22-105695", "htm")))
R.append(dict(
    ticker="ABBV", exchange_id="ABBV-2020-S4", staff_letter_date="2020-10-08", reply_date="2020-10-14", close_date="2020-10-14",
    filing_reviewed="S-4 note exchange (Allergan-related notes)", topic="procedural (no review)",
    staff_ask="Staff said it would not review the debt exchange S-4.", company_answer="Acceleration request and Exxon Capital representations.",
    why_it_matters="Procedural only.", finding_candidate="no", confidence="high",
    staff_quote="This is to advise you that we have not reviewed and will not review your registration statement.",
    staff_quote_cite=L.format(t="ABBV", f="2020-10-09_UPLOAD_0000000000-20-009552.md") + " p1",
    staff_url=u(1551152, "0000000000-20-009552", "pdf"), reply_url=u(1551152, "0001104659-20-114900", "htm")))
# ---------------- BMY ----------------
R.append(dict(
    ticker="BMY", exchange_id="BMY-2021-NONGAAP", staff_letter_date="2021-12-16", reply_date="2022-01-18; 2022-04-06",
    close_date="2022-04-08", filing_reviewed="10-K FY2020", topic="non-GAAP (licensing and asset acquisition R&D charges)",
    staff_ask="Staff said BMS's own wording ('similar charges ... will likely occur in future periods') showed upfront and milestone R&D charges are recurring, and asked BMS to justify excluding them from non-GAAP.",
    company_answer="BMS first defended the exclusion, then agreed that from Q1 2022 non-GAAP would no longer adjust for upfront or contingent milestone payments on asset acquisitions or licenses.",
    next_filing_disclosure="Not checked in 10-K (non-GAAP sits in earnings releases); the Jan 2022 reply gives the excluded amounts.", next_filing_cite="",
    why_it_matters="Same SEC sweep as PFE and LLY: big pharma's adjusted EPS excluded the cost of buying pipeline until 2022, flattering EPS-based pay and guidance.",
    impact_estimate="Licensing and asset acquisition R&D charges $1.1B (2020), $25M (2019), $1.0B (2018) = 9%, 0%, 18% of GAAP R&D (reply); quarterly up to 44% of R&D.",
    finding_candidate="yes", confidence="high",
    staff_quote="In this regard, your statement that \"similar charges or gains were recognized in prior periods and will likely occur in future periods\" appears to indicate that these R&D charges are inherently recurring in nature.",
    staff_quote_cite=L.format(t="BMY", f="2021-12-16_UPLOAD_0000000000-21-015053.md") + " p1",
    reply_quote="In response to the Staff's comment and as discussed with the Staff, beginning with BMS' earnings release for the quarter ended March 31, 2022, BMS will not include adjustments for R&D charges or other income resulting from upfront or contingent milestone payments in connection with asset acquisitions or licensing of third-party intellectual property rights in presentations of its non-GAAP measures.",
    reply_quote_cite=L.format(t="BMY", f="2022-04-06_CORRESP_0001140361-22-013376.md") + " p2",
    staff_url=u(14272, "0000000000-21-015053", "pdf"), reply_url=u(14272, "0001140361-22-013376", "htm")))
R.append(dict(
    ticker="BMY", exchange_id="BMY-2020-10K-FORUM", staff_letter_date="2020-12-22", reply_date="2021-01-06", close_date="2021-02-01",
    filing_reviewed="10-K FY2019", topic="exclusive forum bylaw",
    staff_ask="Staff asked BMS to describe its Delaware exclusive-forum bylaw and whether it covers federal securities claims.",
    company_answer="BMS agreed to add the disclosures.", why_it_matters="Governance boilerplate.",
    finding_candidate="no", confidence="high",
    staff_quote="In future filings, please prominently describe the provision, including the relevant forum for litigation and any subject matter jurisdiction carve out, and whether this provision applies to actions arising under the Securities Act or Exchange Act.",
    staff_quote_cite=L.format(t="BMY", f="2020-12-22_UPLOAD_0000000000-20-012335.md") + " p1",
    reply_quote="The Company acknowledges the Staff's comment and will include these disclosures in future filings.",
    reply_quote_cite=L.format(t="BMY", f="2021-01-06_CORRESP_0001140361-21-000350.md") + " p2",
    staff_url=u(14272, "0000000000-20-012335", "pdf"), reply_url=u(14272, "0001140361-21-000350", "htm")))
R.append(dict(
    ticker="BMY", exchange_id="BMY-2019-STARBOARD", staff_letter_date="2019-03-11 (posted 2019-03-12)", reply_date="", close_date="",
    filing_reviewed="PREC14A filed by Starboard Value (activist), not by BMS", topic="activist proxy on Celgene merger",
    staff_ask="Staff told Starboard's counsel to support claims in its anti-Celgene-deal proxy, including its claim that BMS's base case was a 90% Revlimid revenue decline in 2026.",
    company_answer="No BMS reply: the letter is addressed to Starboard's counsel (Olshan Frome Wolosky), so it is not a BMS disclosure exchange.",
    why_it_matters="Context only: an outside claim that BMS modeled a 90% Revlimid revenue drop in 2026; Starboard, not BMS, made it.",
    finding_candidate="no", confidence="high",
    staff_quote="On page 6, you state that based on your discussions with BSM management, you believe that their \"base-case scenario\" for the anticipated decline in REVLIMID revenues in 2026 is 90%.\"",
    staff_quote_cite=L.format(t="BMY", f="2019-03-12_UPLOAD_0000000000-19-004490.md") + " p2",
    staff_url=u(14272, "0000000000-19-004490", "pdf")))
R.append(dict(
    ticker="BMY", exchange_id="BMY-2020-S4", staff_letter_date="2020-05-29", reply_date="2020-06-10", close_date="2020-06-10",
    filing_reviewed="S-4 note exchange (Celgene notes)", topic="procedural (no review)",
    staff_ask="Staff said it would not review the debt exchange S-4.", company_answer="Acceleration request and Exxon Capital representations (two CORRESP).",
    why_it_matters="Procedural only.", finding_candidate="no", confidence="high",
    staff_quote="This is to advise you that we have not reviewed and will not review your registration statement.",
    staff_quote_cite=L.format(t="BMY", f="2020-05-29_UPLOAD_0000000000-20-004815.md") + " p1",
    staff_url=u(14272, "0000000000-20-004815", "pdf"), reply_url=u(14272, "0001140361-20-013531", "htm")))
R.append(dict(
    ticker="BMY", exchange_id="BMY-2024-RAYZEBIO", staff_letter_date="2024-02-14 (not collected)", reply_date="2024-02-16", close_date="",
    filing_reviewed="Schedule TO-T for RayzeBio", topic="tender offer mechanics",
    staff_ask="Staff asked BMS to disclose alternative financing plans and to stop reserving the right to waive offer conditions 'at any time' (staff letter not in collection).",
    company_answer="BMS revised the Offer to Purchase.", why_it_matters="Procedural.", finding_candidate="no", confidence="medium",
    reply_quote="Parent and Purchaser respectfully acknowledge the Staff's comment and advise the Staff that the TO Amendment sets forth revised disclosure on pages 2 and 24 of the Offer to Purchase in response to the Staff's comment.",
    reply_quote_cite=L.format(t="BMY", f="2024-02-16_CORRESP_0001140361-24-008303.md") + " p1",
    reply_url=u(14272, "0001140361-24-008303", "htm")))
# ---------------- GILD ----------------
R.append(dict(
    ticker="GILD", exchange_id="GILD-2023-10K", staff_letter_date="2023-03-29", reply_date="2023-04-25", close_date="2023-05-05",
    filing_reviewed="10-K FY2022", topic="R&D by project",
    staff_ask="Staff asked Gilead to disclose R&D cost by key project, or say it does not track R&D by project and explain why.",
    company_answer="Gilead said it does not track total R&D by project, product candidate, therapeutic area or phase, refused per-candidate external spend as misleading and competitively harmful, and added a two-line cost-type table.",
    next_filing_disclosure="FY2023 and FY2025 10-K MD&A carry the new sentence and a two-line table (Personnel/infrastructure $3,427M vs Clinical studies $2,372M in 2025).",
    next_filing_cite="data/moat/companies/GILD/10k_FY2023.md pdf 42 / printed 41; data/corpus/companies/GILD/10k_FY2025.md pdf 42 / printed 41",
    why_it_matters="Investors cannot see how much of ~$5.8B R&D goes to Trodelvy or any pipeline asset, so failed-program spend is invisible until an impairment.",
    impact_estimate="R&D $5.8B (2025) undisclosed by program; Trodelvy and Arcus named only as qualitative drivers.",
    finding_candidate="yes", confidence="medium",
    staff_quote="As part of your response, disclose the costs incurred during each period presented for each of your key research and development projects.",
    staff_quote_cite=L.format(t="GILD", f="2023-03-29_UPLOAD_0000000000-23-003172.md") + " p1",
    reply_quote="We currently do not track total R&D expenses by R&D project because these costs generally do not provide a direct indication of the future success or failure of the project.",
    reply_quote_cite=L.format(t="GILD", f="2023-04-25_CORRESP_0000882095-23-000011.md") + " p1",
    staff_url=u(882095, "0000000000-23-003172", "pdf"), reply_url=u(882095, "0000882095-23-000011", "htm")))
R.append(dict(
    ticker="GILD", exchange_id="GILD-2020-IMMUNOMEDICS", staff_letter_date="2020-09-30 (not collected)", reply_date="2020-10-02", close_date="",
    filing_reviewed="Schedule TO-T for Immunomedics", topic="tender offer mechanics",
    staff_ask="Staff questioned the subsequent offering period language and offer conditions that Gilead could trigger itself.",
    company_answer="Gilead revised the Offer to Purchase (Amendment No. 2).", why_it_matters="Procedural.", finding_candidate="no", confidence="medium",
    reply_quote="\"Purchaser will not provide for any subsequent offering period following the Expiration Date.\"",
    reply_quote_cite=L.format(t="GILD", f="2020-10-02_CORRESP_0001104659-20-111767.md") + " p1",
    reply_url=u(882095, "0001104659-20-111767", "htm")))
R.append(dict(
    ticker="GILD", exchange_id="GILD-2024-CYMABAY", staff_letter_date="2024-03-01 (not collected)", reply_date="2024-03-11", close_date="",
    filing_reviewed="Schedule TO-T for CymaBay", topic="tender offer; director overlap; confidential treatment",
    staff_ask="Staff asked about a Gilead executive (Ms. Dorling) who was also a CymaBay director, among other comments.",
    company_answer="Gilead answered with portions redacted under a Rule 83 confidential treatment request.",
    why_it_matters="Redacted deal background; not a filing disclosure gap we can quantify.", finding_candidate="no", confidence="low",
    reply_quote="CERTAIN PORTIONS OF THIS LETTER HAVE BEEN OMITTED FROM THE VERSION FILED VIA EDGAR.",
    reply_quote_cite=L.format(t="GILD", f="2024-03-11_CORRESP_0001104659-24-032743.md") + " p1",
    reply_url=u(882095, "0001104659-24-032743", "htm")))
# ---------------- AZN ----------------
R.append(dict(
    ticker="AZN", exchange_id="AZN-2021-F4", staff_letter_date="2021-03-01", reply_date="2021-04-08", close_date="2021-04-08",
    filing_reviewed="F-4 (Alexion acquisition)", topic="procedural (no review)",
    staff_ask="Staff said it would not review the F-4.", company_answer="Acceleration request.",
    why_it_matters="Procedural only.", finding_candidate="no", confidence="high",
    staff_quote="This is to advise you that we have not reviewed and will not review your registration statement.",
    staff_quote_cite=L.format(t="AZN", f="2021-03-01_UPLOAD_0000000000-21-002401.md") + " p1",
    staff_url=u(901832, "0000000000-21-002401", "pdf"), reply_url=u(901832, "0001104659-21-047875", "htm")))
R.append(dict(
    ticker="AZN", exchange_id="AZN-2024-ICOSAVAX", staff_letter_date="2024-01-04 (not collected)", reply_date="2024-01-10", close_date="",
    filing_reviewed="Schedule TO-T for Icosavax", topic="CVR milestone risk disclosure",
    staff_ask="Staff asked AstraZeneca to disclose supporting-stockholder ownership and the specific risks to CVR milestone payments, including IVX-A12 status and AZ's required efforts.",
    company_answer="AstraZeneca revised the Offer to Purchase (Amendment No. 1).",
    why_it_matters="CVR contingent payments are acquisition economics but sit in the TO-T, not the 20-F.", finding_candidate="no", confidence="medium",
    reply_quote="AstraZeneca Response : In response to the Staff's comment, AstraZeneca has revised the disclosures on pages 5 and 55 of the Offer to Purchase.",
    reply_quote_cite=L.format(t="AZN", f="2024-01-10_CORRESP_0001104659-24-003086.md") + " p1",
    reply_url=u(901832, "0001104659-24-003086", "htm")))

if __name__ == "__main__":
    out("comment_letter_findings.csv", COLS, R, "derived: SEC EDGAR CORRESP/UPLOAD letters (staff_url, reply_url columns)")
