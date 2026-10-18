"""NVO and AZN pay metrics from the Remuneration Report (NVO) and Directors' Remuneration Report (AZN 20-F ex 15.1),
FY2024 and FY2025, in the incentive_metrics.csv layout. Every quote is checked verbatim (whitespace-normalized) on
the cited page and the printed folio is checked against the page footer before a row is written.

python -m agent.moat.verify.g_foreign_incent
"""
import csv
import re
from pathlib import Path

from agent.moat.verify.pe_lib import norm, pages

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/moat/verified/secx/incentive_metrics_foreign.csv"
SUMMARY = ROOT / "data/moat/verified/secx/incentive_summary.csv"

DOCS = {  # key: (path, doc_id, source_url, footer regex with {p} for the printed folio)
    "NVO25": ("data/corpus/companies/NVO/6k/2026-02-04_novonordisk_remuneration.md",
              "NVO:6k/2026-02-04_novonordisk_remuneration.md",
              "https://www.sec.gov/Archives/edgar/data/353278/000035327826000009/novonordisk_remuneration.htm",
              r"Novo Nordisk Remuneration Report 2025 / [^\n]*? {p}\s*$"),
    "NVO24": ("data/moat/companies/NVO/6k/2025-02-05_novonordisk_remuneration.md",
              "NVO:companies/NVO/6k/2025-02-05_novonordisk_remuneration.md",
              "https://www.sec.gov/Archives/edgar/data/353278/000162828025003906/novonordiskremunerationr.htm",
              r"^\s*{p} "),
    "AZN25": ("data/moat/companies/AZN/20f_FY2025_ex15d1.md", "AZN:companies/AZN/20f_FY2025_ex15d1.md",
              "https://www.sec.gov/Archives/edgar/data/901832/000110465926019130/azn-20251231xex15d1.htm",
              r"AstraZeneca Annual Report & Form 20-F Information 2025 {p}\n"),
    "AZN24": ("data/moat/companies/AZN/20f_FY2024_ex15d1.md", "AZN:companies/AZN/20f_FY2024_ex15d1.md",
              "https://www.sec.gov/Archives/edgar/data/901832/000110465925014750/azn-20241231xex15d1.htm",
              r"(\n{p} AstraZeneca Annual Report & Form 20-F Information 2024|AstraZeneca Annual Report & Form 20-F Information 2024 {p}\n)"),
}

NVO_STI = "annual (STIP, corporate 75% + individual 25%)"
AZN_STI = "annual (Group scorecard bonus)"
R = []  # (ticker, year, plan, metric, weight, target, result, payout, doc, page_no, printed, quote, note)


def add(*a):
    R.append(a)


# ---------------- Novo Nordisk 2025 (Remuneration Report 2025)
y, d = 2025, "NVO25"
add("NVO", y, NVO_STI, "Sales growth (comparable exchange rates)", 25, "19.9% (min 15.1%, max 24.7%)", "10.6%",
    "0.0% of max", d, 14, 14, "Sales growth3 25% 15.1% 19.9% 24.7% 10.6% 0.0% 0.0% 0.0%", "below threshold; same outcome for CEO, CFO and former CEO")
add("NVO", y, NVO_STI, "Operating profit growth (comparable exchange rates)", 25, "22.3% (min 17.4%, max 27.1%)",
    "6.4%", "0.0% of max", d, 14, 14, "Operating profit growth4 25% 17.4% 22.3% 27.1% 6.4% 0.0% 0.0% 0.0%", "below threshold")
add("NVO", y, NVO_STI, "Achievement of strategic initiatives (Purpose & Sustainability, Innovation & Therapeutic Focus)",
    25, "8 out of 12 (min 4, max 12)", "10 out of 12", "18.8% of max", d, 14, 14,
    "Achievement of strategic initiatives 25% 4 out of 12 8 out of 12 12 out of 12 10 out of 12 18.8% 18.8% 18.8%",
    "target lowered from 9 of 13 to 8 of 12 when the gender balance target was removed (p13)")
add("NVO", y, NVO_STI, "Strategic initiatives detail: R&D pipeline milestones", "within 25",
    "10 R&D milestones (CagriSema REIMAGINE 3, amycretin, oral semaglutide obesity filing, Mim8 filing, HERMES, MASH filing, EVOKE, first human doses)",
    "9 of 10 met; EVOKE and EVOKE+ (semaglutide Alzheimer's) readout not successful; PPV process validation postponed (sustainability)",
    "", d, 15, 15, "Successful readout from phase 3a trial EVOKE and EVOKE+ for SemaAD By Q4 2025 Readout not successful No", "")
add("NVO", y, NVO_STI, "Individual targets", 25, "qualitative", "CEO 23.8% of max, CFO 22.5%, former CEO fixed at 50%",
    "CEO 5.9% of max", d, 14, 14,
    "Individual performance6 Individual targets 25% Qualitative assessment 23.8% of max (CEO) / 22.5% of max (CFO) / 50% of max (former CEO) 5.9% 5.6% 12.5%",
    "individual score 'negatively impacted by the challenges encountered in 2025 on financial and commercial performance' (p16)")
add("NVO", y, NVO_STI, "STIP total", 100, "max 12 months' base salary", "CEO 24.7%, CFO 24.4%, former CEO 31.3% of max",
    "CEO 24.7% of max", d, 14, 14, "Total 100% 24.7% 24.4% 31.3%", "both financial metrics paid zero; payout came only from non-financial and individual")
d = "NVO25"
LT23 = "LTI (LTIP 2023, performance 2023-2025, vests 2026)"
add("NVO", y, LT23, "3-year average sales growth (constant exchange rates)", 33.3, "14% (min 11%, max 17%)",
    "23.9% (2023 35.6%, 2024 25.7%, 2025 10.3%)", "33.3% (max)", d, 17, 17,
    "3-year average sales growth1 33.3% 35.6% 25.7% 10.3% 23.9% 11% 14% 17% 33.3%",
    "maximum paid although 2025 growth (10.3%) was below the 11% threshold; 2023 carried the average")
add("NVO", y, LT23, "3-year average operating profit growth (constant exchange rates)", 33.3, "14% (min 11%, max 17%)",
    "25.3% (2023 43.7%, 2024 26.2%, 2025 6.0%)", "33.3% (max)", d, 17, 17,
    "3-year average operating profit growth2 33.3% 43.7% 26.2% 6.0% 25.3% 11% 14% 17% 33.3%", "")
add("NVO", y, LT23, "Achievement of strategic initiatives (one-year targets each year)", 33.3,
    "10 in 2023, 10 in 2024, 8 in 2025", "12 of 13, 12 of 13, 10 of 12", "25.4%", d, 17, 17,
    "Achievement of strategic initiatives3 33.3 % 12 out of 13 12 out of 13 10 out of 12", "")
add("NVO", y, LT23, "LTIP 2023 total", 100, "", "92% of max; share price fell 32.4% (DKK 481.00 to 325.25)", "92% of max",
    d, 17, 17, "In total, this resulted in a pay-out of 92% of the maximum for LTIP 2023", "")
LT25 = "LTI (LTIP 2025, performance 2025-2027)"
add("NVO", y, LT25, "3-year average sales growth (constant exchange rates)", 33.3, "not disclosed",
    "2025 10.3%; tracking below target", "", d, 19, 19, "3-year average sales growth1 33.3% 10.3% N/A N/A Below target", "")
add("NVO", y, LT25, "3-year average operating profit growth (constant exchange rates)", 33.3, "not disclosed",
    "2025 6.0%; tracking below target", "", d, 19, 19,
    "3- year average operating profit growth2 33.3% 6.0% N/A N/A Below target", "")
add("NVO", y, LT25, "Achievement of strategic initiatives (three-year targets)", 33.3, "not disclosed",
    "tracking around target", "", d, 19, 19,
    "Purpose & Sustainability, and Innovation & Therapeutic Focus Achievement of strategic initiatives3 33.3% N/A Around target", "")

# ---------------- Novo Nordisk 2024 (Remuneration Report 2024)
y, d = 2024, "NVO24"
add("NVO", y, NVO_STI, "Sales growth (comparable exchange rates)", 25, "22.2% (min 18.2%, max 26.2%)", "27.0%",
    "25.0% of max (max)", d, 15, 14, "Sales growth1 25.0% 18.2% 22.2% 26.2% 27.0% 25.0%", "same corporate scores for CEO and CFO")
add("NVO", y, NVO_STI, "Operating profit growth (comparable exchange rates)", 25, "25.7% (min 21.7%, max 29.7%)",
    "28.5%", "21.1% of max", d, 15, 14, "Operating profit growth2 25.0% 21.7% 25.7% 29.7% 28.5% 21.1%", "")
add("NVO", y, NVO_STI, "Achievement of strategic initiatives (Purpose & Sustainability, Innovation & Therapeutic Focus)",
    25, "10 out of 13 (min 7, max 13)", "12 out of 13", "20.8% of max", d, 15, 14,
    "Achievement of strategic initiatives 25.0% 7 out of 13 10 out of 13 13 out of 13 12 out of 13 20.8%", "")
add("NVO", y, NVO_STI, "Strategic initiatives detail: sustainability and R&D milestones", "within 25",
    "13 targets incl. 45 million patients reached, CO2e -36%, D&I progress, FlexTouch supply, 8 R&D milestones",
    "12 of 13 met; the D&I target was missed", "", d, 16, 15,
    "Sustainable employer: Progress towards Diversity & Inclusion (D&I) aspirational targets1 Progress Progress made but to a lesser extent than desired No",
    "all 8 Innovation & Therapeutic Focus milestones met (Mim8 FRONTIER-2, REDEFINE-3 recruitment, HERMES recruitment, first human doses)")
add("NVO", y, NVO_STI, "Individual targets", 25, "qualitative", "CEO 50% of max, CFO 67% of max", "CEO 12.5% of max",
    d, 15, 14, "Individual targets 25.0% Qualitative assessment 50% of max 12.5%", "")
add("NVO", y, NVO_STI, "STIP total", 100, "max 12 months' base salary",
    "CEO 69% of max, CFO 73%, after a discretionary 16% downward adjustment of group performance", "CEO 69% of max",
    d, 15, 14, "The discretionary downward adjustment of the group performance by 16% is included in the total.",
    "formula sum for the CEO is 25.0+21.1+20.8+12.5 = 79.4% before the Board's downward discretion")
LT22 = "LTI (LTIP 2022, performance 2022-2024, vests 2025)"
add("NVO", y, LT22, "3-year average sales growth (constant exchange rates)", 33.3, "10.0% (min 8.0%, max 12.0%)",
    "25.9% (2022 16.4%, 2023 35.6%, 2024 25.7%)", "33.3% (max)", d, 18, 17,
    "3-year average sales growth1 33.3% 16.4% 35.6% 25.7% 25.9% 8.0% 10.0% 12.0% 33.3%", "")
add("NVO", y, LT22, "3-year average operating profit growth (constant exchange rates)", 33.3,
    "9.0% (min 7.0%, max 11.0%)", "28.2% (2022 14.6%, 2023 43.7%, 2024 26.2%)", "33.3% (max)", d, 18, 17,
    "3-year average operating profit growth2 33.3% 14.6% 43.7% 26.2% 28.2% 7.0% 9.0% 11.0% 33.3%", "")
add("NVO", y, LT22, "Achievement of strategic initiatives (one-year targets each year)", 33.3,
    "9 in 2022, 10 in 2023, 10 in 2024", "9 of 12, 12 of 13, 12 of 13", "21.9%", d, 18, 17,
    "Achievement of strategic initiatives3 33.3% 9 out of 12 12 out of 13 12 out of 13", "")
add("NVO", y, LT22, "LTIP 2022 total", 100, "", "89% of max; share price rose 87% (DKK 334.5 to 624.2)", "89% of max",
    d, 18, 17, "In total, this resulted in a pay-out of 89% of the maximum for LTIP 2022", "")
LT24 = "LTI (LTIP 2024, performance 2024-2026)"
add("NVO", y, LT24, "3-year average sales growth (constant exchange rates)", 33.3, "not disclosed",
    "2024 25.7%; tracking above target", "", d, 19, 18, "3-year average sales growth1 33.3% 25.7% N/A N/A Above target",
    "one year later the 2025 report has the same LTIP 2024 sales metric tracking below target (2025 report p18)")
add("NVO", y, LT24, "3-year average operating profit growth (constant exchange rates)", 33.3, "not disclosed",
    "2024 26.2%; tracking above target", "", d, 19, 18,
    "3- year average operating profit growth2 33.3% 26.2% N/A N/A Above target", "now tracking below target (2025 report p18)")
add("NVO", y, LT24, "Achievement of strategic initiatives (three-year targets)", 33.3, "not disclosed",
    "3 out of 6; tracking around target", "", d, 19, 18, "Achievement of strategic initiatives3 33.3% 3 out of 6 N/A N/A Around target",
    "target later cut from 3 of 6 to 3 of 5 when the gender balance target was removed (2025 report p18)")

# ---------------- AstraZeneca 2025 (Directors' Remuneration Report, Annual Report and Form 20-F Information 2025)
y, d = 2025, "AZN25"
add("AZN", y, AZN_STI, "Pipeline progression events", 15, "29 (threshold 15, max 44)", "36", "22% of target bonus",
    d, 101, 99, "Pipeline progression events 15% 15 29 44 36 22%", "Phase II starts and progressions plus positive pivotal investment decisions")
add("AZN", y, AZN_STI, "Regulatory events", 15, "54 (threshold 38, max 70)", "69", "29% of target bonus", d, 101, 99,
    "Regulatory events 15% 38 54 70 69 29%", "NME and major LCM regional submissions and approvals")
add("AZN", y, AZN_STI, "Total Revenue ($bn, budget exchange rates)", 30, "58.2 (threshold 56.5, max 60.0)", "59.0",
    "43% of target bonus", d, 101, 99, "Total Revenue ($bn) 30% 56.5 58.2 60.0 59.0 43%",
    "scored at budget FX: 59.0 vs reported Total Revenue $58.7bn (p100)")
add("AZN", y, AZN_STI, "Cash flow ($bn)", 20, "11.3 (threshold 9.6, max 13.0)", "11.9", "27% of target bonus", d, 101, 99,
    "Cash flow ($bn) 20% 9.6 11.3 13.0 11.9 27%", "operating cash flow less capex plus intangible disposal proceeds")
add("AZN", y, AZN_STI, "Core EPS ($, budget exchange rates)", 20, "9.10 (threshold 8.65, max 9.56)", "9.24",
    "26% of target bonus", d, 101, 99, "Core EPS ($) 20% 8.65 9.10 9.56 9.24 26%", "")
add("AZN", y, AZN_STI, "Group scorecard total (formulaic)", 100, "100% of target", "147% of target", "147% of target",
    d, 101, 99, "Total 100% 147%", "")
add("AZN", y, AZN_STI, "Final bonus outturn (Committee determination)", 100, "CEO 150%, CFO 100% of base pay at target",
    "CEO 184% of target (92% of max), CFO 162% of target (81% of max)", "CEO 92% of max", d, 103, 101,
    "the Committee determined the bonus outturns for the Executive Directors should be 184% of target (or 92% of maximum) to Mr Pascal Soriot and 162% of target (or 81% of maximum) to Dr Aradhana Sarin.",
    "Committee raised both outturns above the 147% formulaic scorecard; half deferred into shares for 3 years")
P23 = "LTI (PSP 2023, performance 2023-2025)"
for metric, w, tgt, res, pay, q in [
        ("Science and Innovation: NME Phase III/registrational volume", 12, "threshold 10, max 20", "20", "12% (max)", "NME Phase III/registrational volume 12% 10 20 20 12%"),
        ("Science and Innovation: regulatory events (first approvals)", 18, "threshold 13, max 26", "30", "18% (max)", "Regulatory events 18% 13 26 30 18%"),
        ("Growth and Therapy Area Leadership: Total Revenue ($bn)", 20, "threshold 43, max 50.5", "59", "20% (max)", "Leadership ($bn) 20% 43 50.5 59 20%"),
        ("Cash flow ($bn, cumulative)", 20, "threshold 22, max 31", "31.5", "20% (max)", "Cash flow ($bn) 20% 22 31 31.5 20%"),
        ("Relative TSR vs 18 global pharma peers", 20, "median (threshold), upper quartile (max)", "ranked 6th", "17%", "Total shareholder return 20% Median UQ2 6th 17%"),
        ("ESG: Ambition Zero Carbon (Scope 1 and 2 GHG)", 10, "threshold 142 ktCO2e, max 91 ktCO2e", "73 ktCO2e", "10% (max)", "Ambition Zero Carbon 10% 142 ktCO2e 91 ktCO2e 73ktCO2e 10%"),
        ("PSP 2023 total", 100, "", "97% vesting", "97%", "Total1 100% 97%")]:
    add("AZN", y, P23, metric, w, tgt, res, pay, d, 105, 103, q, "")
P25 = "LTI (PSP 2025 grant, performance 2025-2027)"
add("AZN", y, P25, "Relative TSR vs 18 global pharma peers", 20, "median 20% vesting, upper quartile 100%", "", "", d, 105, 103,
    "Relative total shareholder return (TSR) (20% of award)", "CEO grant 850% of base pay, CFO 550%")
add("AZN", y, P25, "Cash flow ($bn, cumulative)", 20, "$27.5bn 20%, $31.5bn 75%, $35.5bn 100%", "", "", d, 106, 104,
    "Between $27.5bn and $31.5bn Pro rata", "")
add("AZN", y, P25, "Growth and Therapy Area Leadership: Total Revenue", 20, "commercially sensitive, disclosed in 2027 report",
    "", "", d, 106, 104, "The Growth and Therapy Area Leadership (Total Revenue) measure is thus considered to be commercially sensitive and will be disclosed following the end of the performance period, in the 2027 Directors' Remuneration Report.", "")
add("AZN", y, P25, "Science and Innovation: NME Phase III/registrational volume", 12, "14 (20%), 21 (75%), 28 (100%)", "", "",
    d, 106, 104, "Between 14 and 21 Pro rata", "")
add("AZN", y, P25, "Science and Innovation: regulatory events", 18, "18 (20%), 26 (75%), 35 (100%)", "", "", d, 106, 104,
    "Between 18 and 26 Pro rata", "")
add("AZN", y, P25, "ESG: Ambition Zero Carbon (Scope 3: NGP transition, distribution, travel)", 10,
    "1,846 ktCO2e (20%), 1,632 (75%), 1,434 (100%)", "", "", d, 106, 104, "Ambition Zero Carbon (10% of award)", "")

# ---------------- AstraZeneca 2024 (Annual Report and Form 20-F Information 2024)
y, d = 2024, "AZN24"
add("AZN", y, AZN_STI, "Pipeline progression events", 15, "27 (threshold 14, max 41)", "24", "12% of target bonus",
    d, 123, 121, "Pipeline progression events 15% 14 27 41 24 12%", "below target")
add("AZN", y, AZN_STI, "Regulatory events", 15, "42 (threshold 29, max 55)", "52", "27% of target bonus", d, 123, 121,
    "Regulatory events 15% 29 42 55 52 27%", "")
add("AZN", y, AZN_STI, "Total Revenue ($bn, budget exchange rates)", 30, "52.1 (threshold 50.5, max 53.7)", "53.8",
    "60% of target bonus (max)", d, 123, 121, "Total Revenue ($bn) 30% 50.5 52.1 53.7 53.8 60%", "")
add("AZN", y, AZN_STI, "Cash flow ($bn)", 20, "10.2 (threshold 8.7, max 11.7)", "10.1", "18% of target bonus", d, 123, 121,
    "Cash flow ($bn) 20% 8.7 10.2 11.7 10.1 18%", "just below target")
add("AZN", y, AZN_STI, "Core EPS ($, budget exchange rates)", 20, "7.82 (threshold 7.43, max 8.21)", "8.22",
    "40% of target bonus (max)", d, 123, 121, "Core EPS ($) 20% 7.43 7.82 8.21 8.22 40%", "")
add("AZN", y, AZN_STI, "Group scorecard total (formulaic)", 100, "100% of target", "157% of target", "157% of target",
    d, 123, 121, "Total 100% 157%", "")
add("AZN", y, AZN_STI, "Final bonus outturn (Committee determination)", 100, "CEO 150%, CFO 100% of base pay at target",
    "157% of target (78.5% of max) for both", "78.5% of max", d, 125, 123,
    "both Executive Directors should be 157% of target (or 78.5% of maximum), in line with the formulaic Group scorecard outcome.",
    "no discretion in 2024 (contrast 2025, when the Committee went above the formula)")
P22 = "LTI (PSP 2022, performance 2022-2024)"
for metric, w, tgt, res, pay, q in [
        ("Science and Innovation: NME Phase III/registrational volume", 12, "threshold 7, max 14", "19", "12% (max)", "NME Phase III/registrational volume 12% 7 14 19 12%"),
        ("Science and Innovation: regulatory events (first approvals)", 18, "threshold 14, max 28", "28", "18% (max)", "Regulatory events 18% 14 28 28 18%"),
        ("Growth and Therapy Area Leadership: Total Revenue ($bn)", 20, "threshold 40.5, max 47.5", "59.5", "20% (max)", "Leadership ($bn) 20% 40.5 47.5 59.5 20%"),
        ("Cash flow ($bn, cumulative)", 20, "threshold 20.0, max 28.5", "28.5", "20% (max)", "Cash flow ($bn) 20% 20.0 28.5 28.5 20%"),
        ("Relative TSR vs 18 global pharma peers", 20, "median (threshold), upper quartile (max)", "ranked 10th", "4%", "Total shareholder return 20% Median UQ2 10th 4%"),
        ("ESG: Ambition Zero Carbon (Scope 1 and 2 GHG)", 10, "threshold 207 ktCO2e, max 155 ktCO2e", "140 ktCO2e", "10% (max)", "Ambition Zero Carbon 10% 207 ktCO2e 155 ktCO2e 140ktCO2e 10%"),
        ("PSP 2022 total", 100, "", "84% vesting", "84%", "Total1 100% 84%")]:
    add("AZN", y, P22, metric, w, tgt, res, pay, d, 127, 125, q, "")
P24 = "LTI (PSP 2024 grant, performance 2024-2026)"
add("AZN", y, P24, "Relative TSR vs 18 global pharma peers", 20, "median 20% vesting, upper quartile 100%", "", "", d, 127, 125,
    "Relative total shareholder return (TSR) (20% of award)", "CEO grant 850% of base pay, CFO 550%")
add("AZN", y, P24, "Cash flow ($bn, cumulative)", 20, "$23.0bn 20%, $28.0bn 75%, $33.0bn 100%", "", "", d, 128, 126,
    "Between $23.0bn and $28.0bn Pro rata", "")
add("AZN", y, P24, "Growth and Therapy Area Leadership: Total Revenue", 20, "commercially sensitive, disclosed in 2026 report",
    "", "", d, 128, 126, "The Growth and Therapy Area Leadership (Total Revenue) measure is thus considered to be commercially sensitive and will be disclosed following the end of the performance period, in the 2026 Directors' Remuneration Report.", "")
add("AZN", y, P24, "Science and Innovation: NME Phase III/registrational volume", 12, "14 (20%), 21 (75%), 28 (100%)", "", "",
    d, 128, 126, "Between 14 and 21 Pro rata", "")
add("AZN", y, P24, "Science and Innovation: regulatory events", 18, "16 (20%), 24 (75%), 32 (100%)", "", "", d, 128, 126,
    "Between 16 and 24 Pro rata", "")
add("AZN", y, P24, "ESG: Ambition Zero Carbon (Scope 1 and 2 GHG)", 10, "26 ktCO2e (20%), 19 (75%), 13 (100%)", "", "", d, 128, 126,
    "Between 26 ktCO2e and 19 ktCO2e Pro rata", "")

COLS = ["ticker", "year", "plan", "metric", "weight_pct", "target", "result", "pdf_page", "printed_page", "quote",
        "quote_file", "note", "payout", "source", "source_row", "verify_status"]

SUMMARY_ROWS = [
    ["NVO", "STIP (2024, 2025): sales growth 25%, operating profit growth 25%, strategic initiatives 25% (sustainability + R&D milestones), individual 25%; LTIP: 3-yr avg sales growth, 3-yr avg operating profit growth, strategic initiatives, 1/3 each",
     "Pay is all growth rates at constant/comparable FX with no absolute-level, net-price or pipeline-value metric. 2025 shows the formula working: both financial STIP metrics paid 0% (sales +10.6% vs 19.9% target, operating profit +6.4% vs 22.3%) and CEO STIP fell to 24.7% of max, but the LTIP 2023 still paid 92% because the 3-year average carried 2023's 35.6% growth, and the Board cut the non-financial targets (9 of 13 to 8 of 12) by deleting the gender target. In 2024 the Board applied a 16% discretionary downward adjustment (CEO 69% of max vs ~79% formula).",
     "Remuneration Report 2025 p13-19; Remuneration Report 2024 p14-18 (6-K 2025-02-05); incentive_metrics_foreign.csv"],
    ["AZN", "Group scorecard bonus (2024, 2025): pipeline progression events 15%, regulatory events 15%, Total Revenue 30%, Cash flow 20%, Core EPS 20%; PSP: NME Phase III volume 12%, regulatory events 18%, Total Revenue 20%, Cash flow 20%, relative TSR 20%, Ambition Zero Carbon 10%",
     "30% of the bonus and 30% of the PSP are count metrics of pipeline and regulatory events, which a deal-heavy strategy can buy; revenue and Core EPS are scored at budget FX (2025 bonus revenue $59.0bn vs reported $58.7bn), and PSP revenue hurdles are withheld as 'commercially sensitive' until the period ends. In 2025 the Committee lifted the CEO bonus to 184% of target vs a 147% formulaic scorecard; in 2024 it paid the formula (157%). PSP 2023 vested 97% and PSP 2022 84%, with every operating metric at maximum and only relative TSR short.",
     "Annual Report and Form 20-F Information 2025 p99-104 and 2024 p121-126 (20-F exhibit 15.1); incentive_metrics_foreign.csv"],
]


def check_row(r):
    tic, y, plan, metric, w, tgt, res, pay, d, pno, printed, q, note = r
    path, doc_id, url, foot = DOCS[d]
    pg = pages(path)
    _, txt = pg[pno]
    assert norm(q) in norm(txt), (d, pno, q[:60])
    assert re.search(foot.format(p=printed), txt, re.M), (d, pno, printed)
    return dict(ticker=tic, year=y, plan=plan, metric=metric, weight_pct=w, target=tgt, result=res, pdf_page=pno,
                printed_page=printed, quote=q, quote_file=path, note=note, payout=pay, source=url,
                source_row=f"{doc_id}#p{pno}", verify_status="verified_at_source")


def main():
    rows = [check_row(r) for r in R]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(OUT, len(rows))
    with SUMMARY.open(newline="") as f:
        cur = list(csv.reader(f))
    cur = [r for r in cur if r[0] not in ("NVO", "AZN")]
    with SUMMARY.open("w", newline="") as f:
        csv.writer(f).writerows(cur + SUMMARY_ROWS)
    print(SUMMARY, len(cur) - 1 + len(SUMMARY_ROWS))


if __name__ == "__main__":
    main()
