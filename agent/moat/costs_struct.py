"""costs stream, table 1: company cost structure from XBRL companyfacts (annual, FY2021-2025)."""
import csv
import glob
import gzip
import io
import json
from collections import Counter
from datetime import date

from agent.moat.common import write

METRICS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenue", "SalesRevenueNet"],
    "cost_of_sales": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfSales"],
    "rnd": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"],
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "selling_and_marketing": ["SellingAndMarketingExpense", "SalesAndMarketingExpense", "MarketingAndAdvertisingExpense",
                              "DistributionCosts"],
    "general_admin": ["GeneralAndAdministrativeExpense", "AdministrativeExpense"],
    "advertising": ["AdvertisingExpense", "AdvertisingExpenseNet"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
              "PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets"],
    "headcount_year_end": ["NumberOfEmployees"],
    "headcount_average": ["AverageNumberOfEmployees"],
}
FORMS = {"10-K", "20-F", "10-K/A", "20-F/A"}


def run():
    rows = []
    for p in sorted(glob.glob("data/corpus/*/*/xbrl_companyfacts.json.gz")):
        grp, tk = p.split("/")[2], p.split("/")[3]
        if grp == "distributors":
            continue
        d = json.load(gzip.open(p))
        cik = int(d["cik"])
        for metric, concepts in METRICS.items():
            got = {}
            for ns, facts in d["facts"].items():
                for c in concepts:
                    if c not in facts:
                        continue
                    for unit, arr in facts[c]["units"].items():
                        if unit == "pure":
                            continue
                        for f in arr:
                            if f.get("form") not in FORMS or not f.get("end"):
                                continue
                            if metric.startswith("headcount"):
                                if f.get("start"):
                                    continue
                            else:
                                if not f.get("start"):
                                    continue
                                dd = (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days
                                if not 350 <= dd <= 380:
                                    continue
                            fy = int(f["end"][:4]) if f["end"][5:7] != "01" else int(f["end"][:4]) - 1
                            if not 2021 <= fy <= 2025:
                                continue
                            key = (fy, unit)
                            r0, r1 = concepts.index(c), f.get("filed", "")
                            if metric == "rnd":
                                r0 = 0
                            cur = got.get(key)
                            if metric == "rnd" and cur is not None and f["val"] != cur[2]["val"]:
                                if f["val"] > cur[2]["val"]:
                                    got[key] = (r0, r1, f, c, ns)
                                continue
                            if cur is None or r0 < cur[0] or (r0 == cur[0] and r1 > cur[1]):
                                got[key] = (r0, r1, f, c, ns)
            for (fy, unit), (r0, r1, f, c, ns) in sorted(got.items()):
                acc = f["accn"].replace("-", "")
                rows.append({"ticker": tk, "group": grp, "fiscal_year": fy, "metric": metric, "value": f["val"],
                             "unit": unit, "concept": f"{ns}:{c}", "period_end": f["end"], "form": f["form"],
                             "filed": f.get("filed"), "page_cite": "",
                             "source": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/ (XBRL companyfacts {ns}:{c})",
                             "source_row": f"{tk}|{ns}:{c}|{f['end']}|{f['accn']}"})
    return rows


if __name__ == "__main__":
    rows = run()
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    write("costs", "tables/company_cost_structure_xbrl.csv", buf.getvalue(), group="costs", doc_type="table",
          source_url="SEC XBRL companyfacts", upload=False)
    print(len(rows))
    have = {(r["ticker"], r["metric"]) for r in rows}
    for tk in sorted({r["ticker"] for r in rows}):
        print(tk, "missing", [m for m in METRICS if (tk, m) not in have])
