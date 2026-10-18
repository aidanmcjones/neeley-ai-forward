import pandas as pd
from agent.moat.common import write

R = []
def add(tk, year, list_chg, net_chg, disc, doc, page, url, note=""):
    R.append(dict(ticker=tk, year=year, avg_list_price_change_pct=list_chg, avg_net_price_change_pct=net_chg, avg_discount_pct=disc,
                  note=note, source=url, source_row=f"companies/{tk}/{doc}#page {page}"))

M = "https://www.merck.com/wp-content/uploads/sites/124/2024/02/PricingAction_TransparencyReport_2023.pdf"
lst = [7.4, 9.5, 9.2, 9.6, 10.5, 9.8, 9.6, 6.6, 5.5, 4.3, 3.1, 4.4, 4.4, 4.5]
net = [3.4, 5.1, 6.2, 5.5, 3.7, 5.5, 5.5, -1.9, 2.9, 1.8, -0.9, 1.7, 4.3, 4.4]
dis = [27.3, 28.9, 29.9, 32.1, 37.0, 38.2, 40.9, 45.1, 44.3, 43.7, 45.5, 43.5, 39.7, 37.0]
for i, y in enumerate(range(2010, 2024)):
    add("MRK", y, lst[i], net[i], dis[i], "pricing_report_2023.md", 1, M, "US product portfolio, WAC-weighted; 2018 net printed 2.99 with footnote 9, read as 2.9")
S = "https://www.sanofi.us/assets/dot-us/pages/images/our-company/Social-impact/responsible-business-values/pricing-principles/Sanofi-Pricing-Principles-2026-Continued-Transparency-in-the-US.pdf"
sl = [4.0, 1.6, 4.6, 2.9, 0.2, 1.5, 2.6, 4.3, 1.1, 2.8]
sn = [-2.1, -8.4, -8.0, -11.1, -7.8, -1.3, -0.4, -15.7, 7.4, -3.4]
for i, y in enumerate(range(2016, 2026)):
    add("SNY", y, sl[i], sn[i], 39 if y == 2025 else None, "pricing_report_2026.md", 2, S,
        "aggregate U.S. portfolio; 2025 discount is rebates as % of gross sales" if y == 2025 else ("2024 excluding insulin: list +4.5, net -3.0" if y == 2024 else ""))
T = "https://assets-dam.takeda.com/image/upload/LOC/en-us/pricing-philosophy/2025_Pricing_Transparency.pdf"
tl, tn, td = [4.1, 4.5, 4.4, 4.6, 4.5], [1.0, 2.7, 3.5, 5.8, -2.8], [42, 43, 44, 43, 46]
for i, y in enumerate(range(2021, 2026)):
    add("TAK", y, tl[i], tn[i], td[i], "pricing_report_2025.md", 1, T, f"CY {y-1}-{y}")
add("BMY", 2025, 3.6, -4.2, 47, "pricing_report_2025.md", 37, "https://www.esg.bms.com/assets/bms-esg/us/documents/BMS-Impact-Report-2025.pdf",
    "$38.0B discounts; approx 53 cents of each gross dollar retained by healthcare system, so discount read as 47%; inflation 2.7%")
add("PFE", 2025, None, -2.0, None, "pricing_report_2025.md", 54, "https://cdn.pfizer.com/pfizercom/Pfizer_2025_Impact_Report_02JUN2026.pdf",
    "net -2%; excluding COMIRNATY and PAXLOVID: 2023 +1, 2024 -3, 2025 -5; list change not disclosed")
for y, n in ((2023, 1.0), (2024, -3.0), (2025, -5.0)):
    add("PFE", y, None, n, None, "pricing_report_2025.md", 54, "https://cdn.pfizer.com/pfizercom/Pfizer_2025_Impact_Report_02JUN2026.pdf", "net price excluding COMIRNATY and PAXLOVID")
add("GSK", 2025, 3.8, -0.1, None, "pricing_report_2025.md", 10, "https://www.gsk.com/media/di5bk40q/responsible-business-report.pdf", "industry list +3.5 per GSK; 5-yr avg net +2.5/yr, list +3.2/yr")
df = pd.DataFrame(R)
write("pricing", "tables/company_list_vs_net.csv", df.to_csv(index=False), group="pricing", doc_type="table",
      source_url="company pricing transparency reports (see source column)")
print(len(df))
