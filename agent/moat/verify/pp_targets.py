"""Pipeline verifier item 3: recompute target_profiles.csv from SEC companyfacts (cached by pp_fetch).

Fixes the collector's `latest()` bug (it returned the first concept with ANY data, so a concept last reported in
2019 beat a newer one), aligns cash, securities and debt to one balance-sheet date, checks dei shares staleness,
recomputes market cap, EV and runway, and checks name collisions between the CT.gov sponsor and the SEC filer.
Usage: python -m agent.moat.verify.pp_targets [path to target_profiles csv to verify]
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

C = Path("data/moat/verify/pp_cache/sec")
SRC = sys.argv[1] if len(sys.argv) > 1 else "data/moat/verify/pp_cache/target_profiles_orig.csv"
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"]
SECS = ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "ShortTermInvestments",
        "HeldToMaturitySecuritiesCurrent", "DebtSecuritiesAvailableForSaleCurrent"]
DEBT = ["LongTermDebt", "LongTermDebtNoncurrent", "ConvertibleNotesPayable", "ConvertibleDebtNoncurrent",
        "ConvertibleLongTermNotesPayable", "LongTermNotesPayable", "SeniorLongTermNotes", "NotesPayableNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations", "DebtLongtermAndShorttermCombinedAmount", "OtherLongTermDebtNoncurrent",
        "LongTermDebtCurrent", "NotesPayable", "DebtInstrumentCarryingAmount"]
OLD_DEBT = ["LongTermDebt", "LongTermDebtNoncurrent", "DebtInstrumentCarryingAmount", "NotesPayable"]


def facts(cik):
    f = C / f"cf_{cik}.json"
    return json.loads(f.read_text())["facts"] if f.exists() else {}


def sub(cik):
    f = C / f"sub_{cik}.json"
    return json.loads(f.read_text()) if f.exists() else {}


def series(cf, ns, concepts, unit="USD", annual=False, inst=True):
    """All values for the concepts, newest first: (end, filed, val, concept, form)."""
    out = []
    for c in concepts:
        for x in cf.get(ns, {}).get(c, {}).get("units", {}).get(unit, []):
            if annual and not (x.get("fp") == "FY" and x.get("form", "").startswith(("10-K", "20-F"))
                               and x.get("start") and (pd.Timestamp(x["end"]) - pd.Timestamp(x["start"])).days > 300):
                continue
            if not x.get("form", "").startswith(("10-K", "10-Q", "20-F", "6-K", "S-1", "10-KT")):
                continue
            out.append((x["end"], x.get("filed", ""), x["val"], c, x.get("form")))
    return sorted(out, reverse=True)


STALE = []


def at(cf, concepts, date, tol=0):
    """Value of the first concept (priority order) at this balance-sheet date; with tol, the newest value of any
    concept whose date is within tol days before it (debt is often tagged only in the annual notes)."""
    for c in concepts:
        v = [x for x in series(cf, "us-gaap", [c]) if x[0] == date]
        if v:
            return v[0][2], c
    if tol:
        v = series(cf, "us-gaap", concepts)
        if v:
            gap = (pd.Timestamp(date) - pd.Timestamp(v[0][0])).days
            if 0 < gap <= tol:
                return v[0][2], f"{v[0][3]} at {v[0][0]}"
            STALE.append((date, v[0][0], v[0][3]))
            return None, f"stale: newest {v[0][3]} is {v[0][0]}"
    return None, None


def toks(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s).lower())
    stop = {"inc", "corp", "corporation", "ltd", "llc", "plc", "co", "sa", "ag", "nv", "gmbh", "the", "and", "a",
            "pharmaceuticals", "pharmaceutical", "pharma", "therapeutics", "bio", "biosciences", "biotechnology",
            "holdings", "company", "limited", "wholly", "owned", "subsidiary", "of", "s"}
    return {w for w in s.split() if w not in stop and len(w) > 1}


t = pd.read_csv(SRC)
out, checks = [], []
for r in t.itertuples():
    cik = int(r.sponsor_cik)
    cf, sb = facts(cik), sub(cik)
    sec_name = sb.get("name", "")
    sec_tk = (sb.get("tickers") or [None])[0]
    overlap = toks(r.sponsor) & toks(sec_name)
    collision = not overlap
    cash_s = series(cf, "us-gaap", CASH)
    bs_date = cash_s[0][0] if cash_s else None
    cash, cash_c = at(cf, CASH, bs_date) if bs_date else (None, None)
    secs, secs_c = at(cf, SECS, bs_date, 200) if bs_date else (None, None)
    debt, debt_c = at(cf, DEBT, bs_date, 200) if bs_date else (None, None)
    ocf = series(cf, "us-gaap", ["NetCashProvidedByUsedInOperatingActivities"], annual=True)
    burn = -ocf[0][2] if ocf else None
    burn_end = ocf[0][0] if ocf else None
    sh = series(cf, "dei", ["EntityCommonStockSharesOutstanding"], unit="shares")
    sh_date = sh[0][0] if sh else None
    # multi-class filers report one dei fact per class at the same date: sum them
    shares = sum(x[2] for x in sh if x[0] == sh_date and x[1] == sh[0][1]) if sh else None
    gs = series(cf, "us-gaap", ["CommonStockSharesOutstanding"], unit="shares")
    shares_note = ""
    if gs and sh_date and gs[0][0] > sh_date and (pd.Timestamp(gs[0][0]) - pd.Timestamp(sh_date)).days > 180:
        shares_note = f"dei shares stale ({sh_date}); used us-gaap CommonStockSharesOutstanding {gs[0][0]}"
        shares, sh_date = gs[0][2], gs[0][0]
    price = r.price if pd.notna(r.price) else None
    mcap = price * shares if price and shares else None
    liq = (cash or 0) + (secs or 0)
    ev = mcap + (debt or 0) - liq if mcap else None
    runway = liq / burn if burn and burn > 0 else None
    notes = []
    if collision:
        notes.append(f"name collision: CT.gov sponsor '{r.sponsor}' vs SEC filer '{sec_name}'")
    if bs_date and r.cash_date and str(r.cash_date) != bs_date:
        notes.append(f"collector cash_date {r.cash_date} vs latest balance sheet {bs_date}")
    # where did the collector's debt and securities come from? (its latest() took the first concept with any data)
    for fld, val, cons in [("debt", r.debt, OLD_DEBT), ("securities", r.securities, SECS[:3])]:
        if pd.notna(val) and val and bs_date:
            hit = [x for x in series(cf, "us-gaap", cons) if x[2] == val]
            if hit and (pd.Timestamp(bs_date) - pd.Timestamp(hit[0][0])).days > 200:
                notes.append(f"collector {fld} {val:,.0f} is {hit[0][3]} dated {hit[0][0]} (stale)")
    if shares_note:
        notes.append(shares_note)
    if sh_date and pd.Timestamp(sh_date) < pd.Timestamp("2025-10-17"):
        notes.append(f"shares date {sh_date} older than 12 months")
    if sec_tk and r.ticker and sec_tk != r.ticker:
        notes.append(f"SEC ticker {sec_tk} vs table {r.ticker}")
    if not sb.get("tickers"):
        notes.append("SEC filer has no listed ticker (not exchange traded)")
    if burn is not None and burn <= 0:
        notes.append("operating cash flow positive: no burn, runway not applicable")

    def rel(a, b):
        if a is None or pd.isna(a):
            return b is None or pd.isna(b)
        if b is None or pd.isna(b):
            return False
        return abs(a - b) <= 0.01 * max(abs(a), abs(b), 1)

    chk = dict(ticker=r.ticker, asset=r.asset, has_mcap=pd.notna(r.market_cap),
               mcap_arith=rel(r.price * r.shares_outstanding if pd.notna(r.price) else None, r.market_cap),
               ev_arith=rel((r.market_cap + (0 if pd.isna(r.debt) else r.debt) - (0 if pd.isna(r.cash) else r.cash)
                             - (0 if pd.isna(r.securities) else r.securities)) if pd.notna(r.market_cap) else None,
                            r.enterprise_value),
               runway_arith=rel(((0 if pd.isna(r.cash) else r.cash) + (0 if pd.isna(r.securities) else r.securities))
                                / r.annual_operating_cash_burn if pd.notna(r.annual_operating_cash_burn)
                                and r.annual_operating_cash_burn > 0 else None, r.runway_years),
               cash_ok=rel(cash, r.cash), sec_ok=rel(secs, r.securities), debt_ok=rel(debt, r.debt),
               burn_ok=rel(burn, r.annual_operating_cash_burn), shares_ok=rel(shares, r.shares_outstanding),
               mcap_ok=rel(mcap, r.market_cap), ev_ok=rel(ev, r.enterprise_value), runway_ok=rel(runway, r.runway_years),
               collision=collision)
    checks.append(chk)
    d = r._asdict()
    d.pop("Index")
    d.update(sec_filer_name=sec_name, sec_ticker=sec_tk, shares_outstanding=shares, shares_date=sh_date,
             market_cap=mcap, cash=cash, cash_concept=cash_c, securities=secs, securities_concept=secs_c, debt=debt,
             debt_concept=debt_c, cash_date=bs_date, annual_operating_cash_burn=burn, burn_period_end=burn_end,
             runway_years=runway, enterprise_value=ev,
             ev_method="price x shares outstanding + debt - cash - current marketable securities, all at one balance-sheet date",
             verify_note="; ".join(notes))
    out.append(d)
v = pd.DataFrame(out)
ck = pd.DataFrame(checks)
v.to_csv("data/moat/verify/pp_cache/targets_recomputed.csv", index=False)
ck.to_csv("data/moat/verify/pp_cache/targets_checks.csv", index=False)
m = ck[ck.has_mcap]
print("rows", len(ck), "with mcap", len(m))
for c in [c for c in ck.columns if c.endswith("_ok") or c.endswith("_arith")]:
    print(f"{c:14s} all {ck[c].mean():.2%}  mcap78 {m[c].sum()}/{len(m)}")
print("collisions", ck.collision.sum())
print(v[v.verify_note.str.contains("collision")][["ticker", "sponsor", "sec_filer_name"]].drop_duplicates().to_string())
