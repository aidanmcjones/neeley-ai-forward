"""Verified company list-vs-net table: re-read each cited page; fix discount inversion, add skipped years, add scope column."""
from pathlib import Path

import pandas as pd

V = Path("data/moat/verified/pricing")
c = pd.read_csv("data/moat/tables/company_list_vs_net.csv")
c["scope"] = "all US portfolio"
c["verified"] = "matches page"
c["verify_note"] = ""
mrk18 = (c.ticker == "MRK") & (c.year == 2018)
c.loc[mrk18, "avg_net_price_change_pct"] = 2.99
c.loc[mrk18, "verified"] = "page prints 2.99"
c.loc[mrk18, "verify_note"] = ("page 1 prints '2.99'; every other cell has one decimal and the page has footnotes 1-6 only, so the "
                               "collector's 'footnote 9' does not exist. Kept as printed (2.99); if a stray glyph, true value is 2.9. Not confirmed elsewhere.")
c.loc[c.ticker == "MRK", "note"] = c.loc[c.ticker == "MRK", "note"].str.replace("; 2018 net printed 2.99 with footnote 9, read as 2.9", "", regex=False)
bmy = c.ticker == "BMY"
c.loc[bmy, "avg_discount_pct"] = 53.0
c.loc[bmy, "verified"] = "corrected"
c.loc[bmy, "verify_note"] = ("page 37: 'approximately 53 cents of each dollar of our company's U.S. gross sales were retained by the healthcare system' "
                             "and 'Over 53% of list prices were retained...' = 53% gross-to-net, not 47% (collector inverted)")
sny24 = (c.ticker == "SNY") & (c.year == 2024)
c.loc[sny24, "verify_note"] = "net +7.4% carries an asterisk: excluding insulin, gross +4.5% and net -3%"
sny25 = (c.ticker == "SNY") & (c.year == 2025)
c.loc[sny25, "verify_note"] = "39% is 'gross sales Sanofi paid as rebates' to payors, not a full GTN discount (fees, other concessions may be excluded)"
pfe = c.ticker == "PFE"
c.loc[pfe & c.note.str.startswith("net price excluding"), "scope"] = "excluding COMIRNATY and PAXLOVID"
c.loc[pfe & (c.year == 2025) & (c.avg_net_price_change_pct == -5.0), "scope"] = "excluding COMIRNATY and PAXLOVID"
c.loc[pfe & (c.year == 2025) & (c.avg_net_price_change_pct == -2.0), "scope"] = "all US portfolio (~79% of sales covered)"
add = []
for y, v in [(2023, 5.0), (2024, -2.0)]:
    add.append(dict(ticker="PFE", year=y, avg_list_price_change_pct=None, avg_net_price_change_pct=v, avg_discount_pct=None,
                    note="table row 'Percent change in average net price for U.S. portfolio': 5% / (2)% / (2)% for 2023/2024/2025; skipped by collector",
                    source="https://cdn.pfizer.com/pfizercom/Pfizer_2025_Impact_Report_02JUN2026.pdf", source_row="companies/PFE/pricing_report_2025.md#page 54",
                    scope="all US portfolio (~79% of sales covered)", verified="added from page", verify_note="year stated on page, missing from collector table"))
c = pd.concat([c, pd.DataFrame(add)], ignore_index=True).sort_values(["ticker", "year", "scope"])
c.loc[c.ticker == "TAK", "verify_note"] = "Takeda labels periods 'CY 2020-2021' etc.; year = later calendar year"
c.to_csv(V / "company_list_vs_net.csv", index=False)
print(c[["ticker", "year", "avg_list_price_change_pct", "avg_net_price_change_pct", "avg_discount_pct", "scope", "verified"]].to_string())
