"""verified/secx/incentive_metrics.csv and incentive_summary.csv from the 2026 proxies (performance year 2025), read by hand.

pdf_page = [[page N]] marker in data/moat/companies/<T>/proxy_2026.md; printed_page = folio printed on that page
(read from the page text when the collector's marker says '?').
"""
from agent.moat.verify.s_write import out

P = "data/moat/companies/{t}/proxy_2026.md"
COLS = ["ticker", "year", "plan", "metric", "weight_pct", "target", "result", "pdf_page", "printed_page", "quote",
        "quote_file", "note"]
R = []


def add(t, plan, metric, w, target, result, pdf, printed, quote, note=""):
    R.append(dict(ticker=t, year=2025, plan=plan, metric=metric, weight_pct=w, target=target, result=result,
                  pdf_page=pdf, printed_page=printed, quote=quote, quote_file=P.format(t=t), note=note))


# MRK
q = "Revenue and Pre-Tax Income are equally weighted at 35%, each based on the C&MD Committee’s belief that they are the key financial measures of our success during the year."
add("MRK", "annual", "Revenue (adjusted: ex certain BD, budget FX)", 35, "$65.63B", "$63.86B adjusted (reported $65.01B); below target", 54, 52, q)
add("MRK", "annual", "Pre-Tax Income (non-GAAP, adjusted)", 35, "$27.43B", "$26.37B adjusted; below target", 54, 52, q)
add("MRK", "annual", "Pipeline goals (R&D discovery, late-stage, filings and approvals)", 20, "not disclosed", "", 54, 52,
    "The Pipeline goals are collectively weighted at 20% and are designed to ensure we are focused on internal and external early discovery opportunities, late-stage clinical development progression, and regulatory filings and approvals.")
add("MRK", "annual", "Sustainability (access, engagement)", 10, "not disclosed", "scorecard total 94%", 54, 52,
    "Our Sustainability goals are collectively weighted at 10%.")
q = "The financial targets for our currently outstanding PSUs are Earnings Per Share (“EPS”) and Relative Total Shareholder Return (“R-TSR”), with 50% of the payout tied to EPS and 50% tied to R-TSR."
add("MRK", "LTI (PSU)", "3-year cumulative EPS", 50, "not disclosed in advance", "2023-25 PSU paid 94%", 58, 56, q, "LTI mix PSU/RSU/options; RSUs added 2025; vehicle mix is an image")
add("MRK", "LTI (PSU)", "3-year relative TSR vs primary peer median", 50, "peer median; +/-5 pts payout per 1 pt", "", 58, 56, q)
# PFE
q = "40% Total Revenue 40% Adjusted Net Income 20% Cash Flow from Operations Up to +/- 25 Percentage Points based on performance against Pipeline goals"
add("PFE", "annual", "Total Revenue (budget FX, ex unbudgeted items)", 40, "$62.0B (threshold 58.0, max 66.0)", "$61.2B; below target (GAAP $62.6B)", 72, 64,
    "Total Revenue (2) (40%) 63.7 billion 58.0 billion 62.0 billion 66.0 billion 61.2 billion")
add("PFE", "annual", "Adjusted Net Income (excludes acquired IPR&D)", 40, "$16.4B (threshold 15.2, max 17.7)", "$19.3B; above max", 72, 64,
    "Adjusted Net Income (3) (40%) 18.0 billion 15.2 billion 16.4 billion 17.7 billion 19.3 billion",
    "footnote 3: excludes acquired in-process research and development expenses")
add("PFE", "annual", "Cash Flow from Operations (excludes acquired IPR&D)", 20, "$9.2B (threshold 6.4, max 12.0)", "$12.6B; above max", 72, 64,
    "Cash Flow from Operations (4) (20%) 13.0 billion 6.4 billion 9.2 billion 12.0 billion 12.6 billion")
add("PFE", "annual", "Pipeline modifier", "+/-25 pts", "three-stage pipeline goals", "pool funded at 150%", 70, 62, q)
q = "Type/Weighting 5-Year Total Shareholder Return Units (TSRUs) (50% of value at grant) Performance Share Awards (PSAs)* (50% of value at grant)"
add("PFE", "LTI (TSRU)", "5-year absolute TSR", 50, "n/a (value = price gain + dividends)", "", 74, 66, q, "2026 grants shift to 25% TSRU / 75% PSA (pdf 75)")
add("PFE", "LTI (PSA)", "Adjusted Diluted EPS, three one-year periods (excludes acquired IPR&D), relative TSR vs DRG Index modifier +/-25 pts", 50, "not disclosed", "", 74, 66, q,
    "2025: Adjusted Net Income replaced by Adjusted Diluted EPS for PSAs")
# LLY
q = "The Committee maintained the Bonus Plan’s three equally weighted measures for 2025: product revenue, EPS, and pipeline progress."
add("LLY", "annual", "Product revenue of 7 key products (Kisunla, Ebglyss, Omvoh, Jaypirca, Verzenio, Mounjaro, Zepbound)", 33.3, "not disclosed (competitive harm)", "", 53, 50, q)
add("LLY", "annual", "EPS (non-GAAP, adjustments may include acquired IPR&D)", 33.3, "not disclosed here", "", 53, 50, q,
    "pdf 56: adjustments 'may include acquired IPR&D charges ... and share repurchases that differ significantly from the business plan'")
add("LLY", "annual", "Pipeline progression scorecard", 33.3, "not disclosed", "", 53, 50, q)
q = "Each NEO’s stock target is allocated equally between SVAs (50%) and RVAs (50%)."
add("LLY", "LTI (SVA)", "Share price vs cost of capital (3-yr)", 50, "start $787.73 compounded at 9.48% cost of capital minus 0.78% dividend yield", "", 56, 53, q)
add("LLY", "LTI (RVA)", "3-yr relative TSR vs peer median", 50, "median peer TSR = 100%", "", 56, 53, q)
# JNJ
q = "Performance against our enterprise 2025 financial goals (70% weight)"
add("JNJ", "annual", "Operational sales", "23.3 (1/3 of 70%, derived)", "$91,300M", "$92,872M; 134.4%", 61, 60,
    "Operational sales ($ millions) $86,735 $91,300 $95,865 $92,872 134.4 % 44.8 %", "weight column not in text layer; 1/3 derived from weighted/calculated payout")
add("JNJ", "annual", "Adjusted operational EPS", "23.3 (1/3 of 70%, derived)", "$10.85", "$10.94; 116.6%", 61, 60,
    "Adjusted operational EPS $10.31 $10.85 $11.39 $10.94 116.6 % 38.9 %")
add("JNJ", "annual", "Free cash flow", "23.3 (1/3 of 70%, derived)", "$19,500M", "$19,830M; 116.9%", 61, 60,
    "Free cash flow ($ millions) $17,550 $19,500 $21,450 $19,830 116.9 % 39.0 %")
add("JNJ", "annual", "Strategic goals (pipeline, supply, commercial, people; discretionary)", 30, "qualitative", "108.0%", 63, 62,
    "The 2025 annual incentive payouts for our named executive officers were based 70% on enterprise financial goals and 30% on enterprise strategic goals.")
q = "1/2 Earnings per share: three-year cumulative adjusted operational EPS. • 1/2 Relative total shareholder return (TSR): three-year compound annual growth rate versus the competitor composite peer group."
add("JNJ", "LTI (PSU)", "3-yr cumulative adjusted operational EPS", 50, "not disclosed in advance (2023-25 target $29.20)", "2023-25 actual $30.99", 60, 59, q, "PSU/option/RSU mix is an image")
add("JNJ", "LTI (PSU)", "3-yr relative TSR CAGR vs competitor composite (55th pct target from 2025)", 50, "55th percentile", "", 60, 59, q)
# AMGN
add("AMGN", "annual", "Revenues", 30, "$35,388M", "$36,751M; 155.3%", 76, 71, "Revenues 30% $32,911 $ 35,388 $37,865 $36,751 155.3%")
add("AMGN", "annual", "Non-GAAP net income", 30, "$11,144M", "$11,837M; 132.9%", 76, 71, "Non-GAAP Net Income (1) 30% $9,438 $11,144 $12,851 $11,837 132.9%")
add("AMGN", "annual", "Execute key clinical studies and regulatory filings", 20, "qualitative", "", 77, 72,
    "Execute Key Clinical Studies and Regulatory Filings— Designed to reward speed and effectiveness to maximize the value of our assets and deliver on our mission to serve patients 20%")
add("AMGN", "annual", "Advance early pipeline", 10, "qualitative", "113.2%", 77, 72,
    "Advance Early Pipeline— Focused on incentivizing early-stage innovation discovery activities important to our long-term success 10%")
add("AMGN", "annual", "Technology & workforce", 10, "qualitative", "156.8%", 78, 73, "Deliver Annual Priorities (10% weighting)")
q = "80% of our annual equity award value continued to be delivered as performance-based LTI equity awards consisting of performance units (50%) and stock options (30%)."
add("AMGN", "LTI (performance units)", "Non-GAAP EPS growth and ROIC, equally weighted each year; relative TSR modifier +/-30 pts", 50, "not disclosed in advance", "", 70, 65, q,
    "metrics from pdf 73 / printed 68; options 30%, RSUs 20%")
# BMY
add("BMY", "annual", "Non-GAAP operating income", 30, "$16,850M", "", 64, 59, "Non-GAAP Operating Income ($M) $16,850 30%")
add("BMY", "annual", "Growth Portfolio revenue ex-FX (excludes Revlimid, Eliquis, Pomalyst, Sprycel, Abraxane)", 35, "$24,850M", "", 64, 59,
    "Growth Portfolio Revenue (Ex-FX) ($M) $24,850 35%")
add("BMY", "annual", "Pipeline (scale 1-5)", 25, "3", "", 64, 59, "Pipeline (1) 3 25%")
add("BMY", "annual", "Sustainability & Social Impact scorecard (scale 1-5)", 10, "3", "company factor 157.66% (pdf 74)", 64, 59, "SSI Scorecard (1) 3 10%")
q = "Non-GAAP Operating Income: 25% • Growth Portfolio Revenue (Ex-FX): 40% • 3-Year Relative TSR CAGR: 35%"
add("BMY", "LTI (PSU, 60% of grant)", "3-yr Non-GAAP operating income", 25, "not disclosed in advance", "", 67, "62 (derived)", q, "MSUs 40% of grant (total return)")
add("BMY", "LTI (PSU, 60% of grant)", "3-yr cumulative Growth Portfolio revenue ex-FX", 40, "not disclosed in advance", "", 67, "62 (derived)", q)
add("BMY", "LTI (PSU, 60% of grant)", "3-yr relative TSR CAGR", 35, "", "", 67, "62 (derived)", q)
# GILD
q = "For purposes of the 2025 annual incentive plan, the Committee approved adjusted net product revenue and adjusted operating income performance goals that excluded Veklury revenue, consistent with the approach used in 2021 through 2024."
add("GILD", "annual", "Adjusted net product revenue (ex Veklury)", "35 (derived)", "not in text layer", "150%", 60, 58, q,
    "weights are an image; derived: resulting 52.5% / factor 150%")
add("GILD", "annual", "Adjusted operating income (ex Veklury)", "25 (derived)", "not in text layer", "150%", 60, 58, q, "derived: 37.5% / 150%")
add("GILD", "annual", "Pipeline (9 NMEs and milestones)", "20 (derived)", "9 NMEs", "110%", 61, 59,
    "Introduce nine new molecular entities (“NMEs”) into the Development portfolio and achieve key pipeline milestones", "derived: 22% / 110%")
add("GILD", "annual", "Product launch milestones (Len4PrEP 8,700 US patients, Livdelzi 5,400)", "10 (derived)", "8,700 / 5,400 patients", "104%", 61, 59,
    "Achieve Len4PrEP total U.S. patients of 8,700 as of November 2025", "derived: 10% / 104%")
add("GILD", "annual", "People (engagement)", "10 (derived)", "", "120%", 61, 59, "Foster employee engagement and inclusion", "derived: 12% / 120%")
add("GILD", "annual", "Veklury modifier", "0.75x-1.25x", "", "1.00x", 60, 58, q)
q = "50% delivered in performance shares earned over three years based on relative Total Shareholder Return (“TSR”) and a multi-year earnings per share (“EPS”) growth metric"
add("GILD", "LTI (performance shares)", "Relative TSR and multi-year EPS growth", 50, "not disclosed in advance", "", 15, 13, q, "options 25%, RSUs 25%")
# ABBV
q = "The committee retained for 2025 the use of Platform Revenue, first introduced as a performance metric within the PIP in 2022, to reinforce management’s focus on growth opportunities to offset anticipated revenue decline associated with U.S. Humira loss of exclusivity (LOE)."
add("ABBV", "annual (CEO)", "Platform Revenue (net revenues less Humira, ex FX)", 20, "$53.7B", "$56.3B; 105%", 43, 40, q,
    "per-NEO weight table IS in the text layer (collector said image); column placement of the trailing 10% values inferred from the ESG-10% sentence")
add("ABBV", "annual (CEO)", "Non-GAAP income before taxes, operating margin, return on assets (equally weighted)", 60, "IBT $25.7B; op margin $27.9B; ROA 24.0%", "IBT $26.9B; 105%", 43, 40,
    "Financial goals are equally weighted.", "excludes IPR&D and milestones expense (pdf 44)")
add("ABBV", "annual (CEO)", "ESG goal", 10, "qualitative", "", 44, 41, "The ESG goal was weighted 10% within the short-term incentive program for each NEO.")
add("ABBV", "annual (CEO)", "Other strategic/leadership (inferred column)", 10, "qualitative", "payout matrix capped at 200%", 43, 40, "Financial goals are equally weighted.")
add("ABBV", "annual (R&D head Thakkar)", "R&D/Innovation", 50, "qualitative", "", 43, 40, "Roopal B. Thakkar", "row: 10% 10% 50% 20% 10%")
add("ABBV", "LTI (performance shares)", "Adjusted diluted EPS with 3-yr relative TSR modifier", 40, "$9.46 (threshold 9.41, max 9.66)", "$10.00; 200%", 46, 43,
    "40% Performance Shares ​ Adjusted Diluted EPS, 3 ‑ Year Relative TSR Modifier")
add("ABBV", "LTI (PVRSU)", "Relative ROIC vs pharma/biotech index constituents", 40, "50th-65th percentile", "95th percentile; 200%", 46, 43,
    "40% Performance ‑ Vested Restricted Stock Units ​ Relative Return on Invested Capital")
add("ABBV", "LTI (options)", "Stock price appreciation", 20, "", "", 46, 43, "20% Non ‑ Qualified Stock Options ​ Stock Price Appreciation")

SUM = [
    dict(ticker="MRK", rewards="Revenue 35% + pre-tax income 35% (annual), EPS 50% + rel TSR 50% (PSU); pipeline 20% annual only",
         connection="Pay is revenue-heavy while Keytruda is ~half of sales; revenue and pre-tax income are 'adjusted to exclude the effect of certain business development transactions', and the Keytruda royalty roll-off end-2026 (comment letter) lifts pre-tax income and EPS without any operating change.",
         cite="proxy_2026 pdf 54-56, 58; comment_letter_findings MRK-2025-10K"),
    dict(ticker="PFE", rewards="Revenue 40%, adjusted net income 40%, CFO 20%, pipeline +/-25 pts (annual); TSRU 50% / PSA (adj EPS + rel TSR) 50%",
         connection="Revenue missed target ($61.2B vs $62.0B) yet the pool funded at 150% on adjusted net income; both the bonus and PSA EPS exclude acquired IPR&D, the exact item the SEC made Pfizer put back into reported non-GAAP in 2022.",
         cite="proxy_2026 pdf 72, 74; comment_letter_findings PFE-2021-10K"),
    dict(ticker="LLY", rewards="Equal thirds: revenue of 7 newer products, EPS, pipeline (annual); share price vs cost of capital 50%, rel TSR 50% (LTI)",
         connection="Revenue metric counts only 7 growth products (Mounjaro, Zepbound, etc.), so Trulicity or legacy erosion cannot reduce the bonus; EPS adjustments may exclude acquired IPR&D even though the SEC forced it into reported non-GAAP from Q1 2022.",
         cite="proxy_2026 pdf 53, 56; comment_letter_findings LLY-2021-NONGAAP"),
    dict(ticker="JNJ", rewards="Operational sales, adj operational EPS, FCF (1/3 each of 70%) + strategic 30% (annual); PSU 1/2 cumulative adj operational EPS, 1/2 rel TSR",
         connection="Mostly EPS and sales; adjusted EPS excludes above-threshold litigation (talc) per the 2019 SEC exchange, and the ~$2.4B Genmab royalty sits inside sales/EPS with no carve-out.",
         cite="proxy_2026 pdf 60-63; comment_letter_findings JNJ-2019-10K, JNJ-2025-10K"),
    dict(ticker="AMGN", rewards="Revenues 30%, non-GAAP net income 30%, pipeline 30%, tech/workforce 10% (annual); perf units on non-GAAP EPS growth + ROIC with rel TSR modifier",
         connection="Total-revenue metric ($36.8B vs $35.4B target) was helped by Horizon volume while net price fell 2% (10-K FY2024 MD&A), the driver split the SEC had to ask for.",
         cite="proxy_2026 pdf 76-78, 70, 73; comment_letter_findings AMGN-2024-10K"),
    dict(ticker="BMY", rewards="Growth Portfolio revenue 35% annual / 40% PSU, non-GAAP OI 30% / 25%, pipeline 25% annual, rel TSR 35% PSU",
         connection="Strongest link: revenue pay is on the Growth Portfolio, which excludes Revlimid, Eliquis, Pomalyst, Sprycel and Abraxane, so legacy LOE erosion is outside the revenue metric while the company paid a 157.66% factor and 5-yr TSR was 4.8% vs peers 98.4%.",
         cite="proxy_2026 pdf 64, 67, 74"),
    dict(ticker="GILD", rewards="Adj product revenue ~35% and adj operating income ~25% (both ex Veklury), pipeline ~20%, product ~10%, people ~10% (derived); perf shares on rel TSR + EPS growth",
         connection="Bonus revenue excludes Veklury (COVID) since 2021 with a separate 0.75-1.25x modifier, so Veklury's decline does not hit the main metric; R&D is not disclosed by program (2023 comment letter).",
         cite="proxy_2026 pdf 60-61, 15; comment_letter_findings GILD-2023-10K"),
    dict(ticker="ABBV", rewards="CEO: Platform Revenue (ex-Humira) 20%, non-GAAP IBT/op margin/ROA 60%, ESG 10%, other 10%; LTI: adj EPS 40%, rel ROIC 40%, options 20%",
         connection="Platform Revenue excludes Humira by design, so Humira LOE erosion is removed from the revenue bonus; financial results exclude IPR&D and milestones expense, and the SEC had to ask (2020) for the non-GAAP pretax income reconciliation. Weights are in the text layer, not only an image.",
         cite="proxy_2026 pdf 43-46; comment_letter_findings ABBV-2020-10K"),
]

if __name__ == "__main__":
    out("incentive_metrics.csv", COLS, R, "derived: DEF 14A 2026 proxies (data/moat/companies/<T>/proxy_2026.md)")
    out("incentive_summary.csv", ["ticker", "rewards", "connection", "cite"], SUM, "derived: incentive_metrics.csv + comment_letter_findings.csv")
