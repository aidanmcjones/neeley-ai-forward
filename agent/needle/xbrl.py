"""Quarterly financial panel per ticker from SEC XBRL companyfacts (data/corpus/<group>/<T>/xbrl_companyfacts.json.gz).

panel(ticker) -> pandas DataFrame indexed by quarter label ("2026Q2") with columns from METRICS.
- Flow metrics (revenue, cogs, ...) use SEC calendar frames CY####Q#. Q4 is derived as FY - (Q1+Q2+Q3)
  when only the annual frame exists (most 10-K filers).
- Stock metrics (inventory, receivables, assets) use instant frames CY####Q#I.
- Each metric merges several US-GAAP / IFRS concepts. Concepts are tried newest-first by their latest frame,
  so a company that switched tags (PFE, ABBV revenue) still gets current numbers.
- 20-F filers (NVO, AZN) mostly report annual and half-year values; quarters they never tag stay NaN.
Every value keeps its concept name in panel.attrs["concepts"] so a finding can cite the tag.
"""

import gzip
import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "data" / "corpus"

METRICS = {  # name: (kind, candidate concepts in priority order)
    "revenue": ("flow", ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "Revenue",
                         "SalesRevenueNet", "RevenueFromContractsWithCustomers"]),
    "cogs": ("flow", ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfSales"]),
    "gross_profit": ("flow", ["GrossProfit"]),
    "rnd": ("flow", ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
                     "ResearchAndDevelopmentExpenseRecognisedAsExpense"]),
    "sga": ("flow", ["SellingGeneralAndAdministrativeExpense", "SellingGeneralAndAdministrativeExpenses"]),
    "operating_income": ("flow", ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities"]),
    "net_income": ("flow", ["NetIncomeLoss", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss"]),
    "pretax_income": ("flow", ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                               "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
                               "ProfitLossBeforeTax"]),
    "income_tax": ("flow", ["IncomeTaxExpenseBenefit", "IncomeTaxExpenseContinuingOperations"]),
    "impairment": ("flow", ["ImpairmentOfIntangibleAssetsExcludingGoodwill", "ImpairmentOfIntangibleAssetsFinitelived",
                            "ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill", "GoodwillImpairmentLoss",
                            "ImpairmentLossRecognisedInProfitOrLossIntangibleAssetsOtherThanGoodwill"]),
    "eps_diluted": ("flow", ["EarningsPerShareDiluted", "DilutedEarningsLossPerShare"]),
    "shares_diluted": ("flow", ["WeightedAverageNumberOfDilutedSharesOutstanding",
                                "WeightedAverageNumberOfSharesOutstandingDiluted"]),
    "inventory": ("stock", ["InventoryNet", "Inventories", "InventoryGross"]),
    "receivables": ("stock", ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "CurrentTradeReceivables",
                              "TradeAndOtherCurrentReceivables"]),
    "assets": ("stock", ["Assets"]),
    "goodwill": ("stock", ["Goodwill"]),
}
NO_Q4_DERIVE = {"eps_diluted", "shares_diluted"}  # per-share and averages do not add up across quarters


def facts_path(ticker):
    hits = list(CORPUS.glob(f"*/{ticker.upper()}/xbrl_companyfacts.json.gz"))
    return hits[0] if hits else None


@lru_cache(maxsize=64)
def _facts(ticker):
    p = facts_path(ticker)
    if not p:
        raise FileNotFoundError(f"no companyfacts for {ticker} under {CORPUS}")
    return json.loads(gzip.decompress(p.read_bytes()))


def _frames(concept_node, instant):
    pat = re.compile(r"CY(\d{4})Q([1-4])I" if instant else r"CY(\d{4})(?:Q([1-4]))?")
    out = {}
    for unit, vals in concept_node["units"].items():
        if instant is False and not (unit.startswith("USD") or unit in ("DKK", "EUR", "GBP", "CHF", "JPY", "shares")
                                     or "/shares" in unit or unit.endswith("/share")):
            continue
        for v in vals:
            m = pat.fullmatch(v.get("frame", ""))
            if m:
                key = f"{m.group(1)}Q{m.group(2)}" if m.group(2) else f"{m.group(1)}FY"
                out[key] = (v["val"], unit)
    return out


def _metric_series(facts, kind, concepts):
    """{period: (value, concept, unit)} merged across concepts, newest-reporting concept first."""
    instant = kind == "stock"
    cands = []
    for ns in ("us-gaap", "ifrs-full"):
        for i, c in enumerate(concepts):
            node = facts["facts"].get(ns, {}).get(c)
            if node:
                fr = _frames(node, instant)
                if fr:
                    cands.append((max(fr), -i, c, fr))
    cands.sort(reverse=True)
    merged = {}
    for _, _, c, fr in cands:
        for k, (val, unit) in fr.items():
            merged.setdefault(k, (val, c, unit))
    return merged


def panel(ticker):
    facts = _facts(ticker)
    cols, concepts, units = {}, {}, {}
    for name, (kind, cands) in METRICS.items():
        s = _metric_series(facts, kind, cands)
        if not s:
            continue
        concepts[name] = sorted({c for _, c, _ in s.values()})
        units[name] = sorted({u for _, _, u in s.values()})
        q = {k: v for k, (v, _, _) in s.items() if not k.endswith("FY")}
        if kind == "flow" and name not in NO_Q4_DERIVE:
            for k, (fy, _, _) in s.items():
                if k.endswith("FY"):
                    y = k[:4]
                    parts = [q.get(f"{y}Q{n}") for n in (1, 2, 3)]
                    if f"{y}Q4" not in q and all(p is not None for p in parts):
                        q[f"{y}Q4"] = fy - sum(parts)
        cols[name] = q
    df = pd.DataFrame(cols).sort_index()
    df.index.name = "quarter"
    df.attrs["concepts"], df.attrs["units"], df.attrs["ticker"] = concepts, units, ticker.upper()
    return df


def annual(ticker):
    """FY values per metric (flows from the CY#### frame, stocks from Q4 instants)."""
    facts = _facts(ticker)
    rows = {}
    for name, (kind, cands) in METRICS.items():
        s = _metric_series(facts, kind, cands)
        rows[name] = ({k[:4]: v for k, (v, _, _) in s.items() if k.endswith("FY")} if kind == "flow"
                      else {k[:4]: v for k, (v, _, _) in s.items() if k.endswith("Q4")})
    return pd.DataFrame(rows).sort_index()


def yoy(df, col):
    """Year-over-year change for each quarter (same quarter prior year)."""
    out = {}
    for q in df.index:
        prior = f"{int(q[:4]) - 1}{q[4:]}"
        if prior in df.index and pd.notna(df.at[q, col]) and pd.notna(df.at[prior, col]) and df.at[prior, col]:
            out[q] = df.at[q, col] / df.at[prior, col] - 1
    return pd.Series(out, dtype=float)
