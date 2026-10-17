"""Time Machine: do NEEDLE's forensic signals precede real trouble? Code-only, point-in-time, no LLM.

Universe: 50 pharma / biotech filers, including companies later acquired or bankrupt (Celgene, Allergan, Mylan,
Mallinckrodt, Endo, ...) so the result is not survivorship-biased. Data: SEC XBRL companyfacts in
data/backtest/xbrl/ (fetched by the snippet in docs/needle.md).

Point in time: for every period the value used is the FIRST one filed, not later restatements.
No LLM anywhere: the model cannot "remember" outcomes, so there is no hindsight leakage.

Rules fixed before looking at results (signal at quarter t; event window t+1 .. t+8 quarters):
  signals  inventory_outpaces_revenue   inventory YoY - revenue YoY >= 10 pts
           receivables_outpace_revenue  receivables YoY - revenue YoY >= 8 pts
           dso_rising                   DSO up >= 10% YoY
           dio_rising                   DIO up >= 15% YoY
           gross_margin_drop            gross margin down >= 2 pts YoY
  events   revenue_drop    trailing-4Q revenue <= 95% of its level at t
           impairment      one quarter's intangible/goodwill impairment >= 2% of total assets
           margin_drop     trailing-4Q gross margin >= 3 pts below its level at t
           any             any of the three
Output: out/backtest/hit_rates.json (hit rate, base rate, lift, Wilson 95% CI, N per signal x event) and
out/backtest/examples.json (signal instances followed by an event, with lead time in months).

Usage:  python -m agent.needle.backtest [--start 2012 --end 2024]
"""

import argparse
import gzip
import json
import math
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
XBRL = ROOT / "data" / "backtest" / "xbrl"
OUT = ROOT / "out" / "backtest"

CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "Revenue", "SalesRevenueNet",
                "SalesRevenueGoodsNet", "RevenueFromContractsWithCustomers"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfSales",
             "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization"],
    "inventory": ["InventoryNet", "Inventories"],
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "CurrentTradeReceivables",
                    "TradeAndOtherCurrentReceivables"],
    "assets": ["Assets"],
    "impairment": ["ImpairmentOfIntangibleAssetsExcludingGoodwill", "ImpairmentOfIntangibleAssetsFinitelived",
                   "ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill", "GoodwillImpairmentLoss",
                   "AssetImpairmentCharges", "ImpairmentOfIntangibleAssetsExcludingGoodwillAndFinancialAssets"],
}
STOCKS = {"inventory", "receivables", "assets"}
SIGNALS = ["inventory_outpaces_revenue", "receivables_outpace_revenue", "dso_rising", "dio_rising", "gross_margin_drop"]
EVENTS = ["revenue_drop", "impairment", "margin_drop", "any"]
WINDOW = 8
LARGE_CAP = {"MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD", "NVS", "GSK", "SNY", "TAK",
             "REGN", "BIIB", "VRTX", "TEVA", "VTRS", "CELG", "AGN", "MYL", "ZTS", "ALXN", "BHC"}


def _qlabel(end):
    d = date.fromisoformat(end)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _days(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def pit_series(facts, names, stock):
    """{quarter: value} using the first-filed value per period; concepts merged newest-reporting first."""
    best = {}
    for ns in ("us-gaap", "ifrs-full"):
        for rank, n in enumerate(names):
            node = facts.get("facts", {}).get(ns, {}).get(n)
            if not node:
                continue
            for unit, vals in node["units"].items():
                if not (unit.startswith("USD") or unit in ("DKK", "EUR", "GBP", "CHF", "JPY")):
                    continue
                for v in vals:
                    end, filed = v.get("end"), v.get("filed", "9999")
                    if not end:
                        continue
                    if stock:
                        key = (_qlabel(end), "I")
                    else:
                        if "start" not in v:
                            continue
                        dd = _days(v["start"], end)
                        kind = "Q" if 80 <= dd <= 100 else "FY" if 350 <= dd <= 380 else None
                        if not kind:
                            continue
                        key = (_qlabel(end), kind)
                    cur = best.get(key)
                    cand = (filed, rank, v["val"])
                    # earliest filing wins; within one filing, prefer the higher-priority concept
                    if cur is None or (filed, rank) < (cur[0], cur[1]):
                        best[key] = cand
    out = {}
    for (q, kind), (_, _, val) in best.items():
        if stock or kind == "Q":
            out[q] = val
    if not stock:  # derive Q4 = FY - Q1..Q3 where only the annual figure exists
        for (q, kind), (_, _, fy) in best.items():
            if kind == "FY":
                labels = _prior_quarters(q, 3)
                if q not in out and all(l in out for l in labels):
                    out[q] = fy - sum(out[l] for l in labels)
    return out


def _shift(q, n):
    y, k = int(q[:4]), int(q[5]) - 1
    t = y * 4 + k + n
    return f"{t // 4}Q{t % 4 + 1}"


def _prior_quarters(q, n):
    return [_shift(q, -i) for i in range(n, 0, -1)]


def company_panel(path):
    facts = json.loads(gzip.decompress(path.read_bytes()))
    cols = {m: pit_series(facts, c, m in STOCKS) for m, c in CONCEPTS.items()}
    df = pd.DataFrame(cols)
    if df.empty or "revenue" not in df:
        return df
    df = df.sort_index()
    df = df[df.index.str.match(r"^\d{4}Q[1-4]$")]
    return df


def _yoy(df, col, q):
    p = _shift(q, -4)
    if p in df.index and pd.notna(df.at[q, col]) and pd.notna(df.at[p, col]) and df.at[p, col]:
        return df.at[q, col] / df.at[p, col] - 1
    return None


def _ttm(df, col, q):
    qs = [_shift(q, -i) for i in range(4)]
    if all(x in df.index and pd.notna(df.at[x, col]) for x in qs):
        return sum(df.at[x, col] for x in qs)
    return None


def signals_at(df, q):
    s = {}
    ry, iy, ay = _yoy(df, "revenue", q), _yoy(df, "inventory", q), _yoy(df, "receivables", q)
    if ry is not None and iy is not None:
        s["inventory_outpaces_revenue"] = (iy - ry) >= 0.10
    if ry is not None and ay is not None:
        s["receivables_outpace_revenue"] = (ay - ry) >= 0.08
    p = _shift(q, -4)
    def ratio(num, den, x):
        if x in df.index and pd.notna(df.at[x, num]) and pd.notna(df.at[x, den]) and df.at[x, den]:
            return df.at[x, num] / df.at[x, den]
        return None
    dso_now, dso_prev = ratio("receivables", "revenue", q), ratio("receivables", "revenue", p)
    if dso_now and dso_prev:
        s["dso_rising"] = dso_now / dso_prev - 1 >= 0.10
    if "cogs" in df:
        dio_now, dio_prev = ratio("inventory", "cogs", q), ratio("inventory", "cogs", p)
        if dio_now and dio_prev:
            s["dio_rising"] = dio_now / dio_prev - 1 >= 0.15
        gm_now = 1 - ratio("cogs", "revenue", q) if ratio("cogs", "revenue", q) is not None else None
        gm_prev = 1 - ratio("cogs", "revenue", p) if ratio("cogs", "revenue", p) is not None else None
        if gm_now is not None and gm_prev is not None and 0 < gm_now < 1 and 0 < gm_prev < 1:
            s["gross_margin_drop"] = (gm_prev - gm_now) >= 0.02
    return s


def events_after(df, q):
    """{event: first quarter it occurs in t+1..t+8} or None if the forward window is not fully observed."""
    fwd = [_shift(q, i) for i in range(1, WINDOW + 1)]
    if fwd[-1] not in df.index or _ttm(df, "revenue", fwd[-1]) is None:
        return None
    ev = {}
    r0 = _ttm(df, "revenue", q)
    if r0:
        for f in fwd:
            r = _ttm(df, "revenue", f)
            if r is not None and r <= 0.95 * r0:
                ev["revenue_drop"] = f
                break
    for f in fwd:
        if f in df.index and "impairment" in df and "assets" in df:
            imp, a = df.at[f, "impairment"], df.at[f, "assets"]
            if pd.notna(imp) and pd.notna(a) and a and imp / a >= 0.02:
                ev["impairment"] = f
                break
    if "cogs" in df:
        def gm(x):
            r, c = _ttm(df, "revenue", x), _ttm(df, "cogs", x)
            return 1 - c / r if r and c is not None else None
        g0 = gm(q)
        if g0 is not None and 0 < g0 < 1:
            for f in fwd:
                g = gm(f)
                if g is not None and g0 - g >= 0.03:
                    ev["margin_drop"] = f
                    break
    if ev:
        ev["any"] = min(ev.values())
    return ev


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def run(start=2012, end=2024):
    rows = []
    for path in sorted(XBRL.glob("*.json.gz")):
        ticker = path.name.split(".")[0]
        df = company_panel(path)
        if df.empty:
            continue
        for q in df.index:
            if not (start <= int(q[:4]) <= end):
                continue
            ev = events_after(df, q)
            if ev is None:
                continue
            sig = signals_at(df, q)
            if not sig:
                continue
            rows.append({"ticker": ticker, "quarter": q, **{f"s_{k}": v for k, v in sig.items()},
                         **{f"e_{k}": (k in ev) for k in EVENTS}, **{f"when_{k}": ev.get(k) for k in EVENTS}})
    obs = pd.DataFrame(rows)
    stats = {"universe": len(list(XBRL.glob('*.json.gz'))), "firm_quarters": len(obs),
             "companies_observed": int(obs["ticker"].nunique()) if len(obs) else 0,
             "window_quarters": WINDOW, "period": f"{start}-{end}", "signals": {}}
    for s in SIGNALS:
        col = f"s_{s}"
        if col not in obs:
            continue
        valid = obs[obs[col].notna()]
        fired = valid[valid[col] == True]  # noqa: E712
        stats["signals"][s] = {"n_fired": int(len(fired)), "n_observed": int(len(valid)), "events": {}}
        for e in EVENTS:
            base = valid[f"e_{e}"].mean() if len(valid) else 0.0
            k, n = int(fired[f"e_{e}"].sum()), int(len(fired))
            hit = k / n if n else 0.0
            lo, hi = wilson(k, n)
            stats["signals"][s]["events"][e] = {"hits": k, "n": n, "hit_rate": round(hit, 3),
                                                "base_rate": round(float(base), 3),
                                                "lift": round(hit / base, 2) if base else None,
                                                "ci95": [round(lo, 3), round(hi, 3)]}
    # exploratory (looked at after the primary results; reported as such): dose-response and large caps
    sig_cols = [f"s_{s}" for s in SIGNALS if f"s_{s}" in obs]
    nsig = obs[sig_cols].fillna(False).astype(bool).sum(axis=1)
    stats["exploratory"] = {
        "dose_response": {label: {"n": int(m.sum()), "any_event_rate": round(float(obs.loc[m, "e_any"].mean()), 3)}
                          for label, m in [("0 signals", nsig == 0), ("1+", nsig >= 1), ("2+", nsig >= 2),
                                           ("3+", nsig >= 3)]},
        "large_cap": {},
    }
    big = obs[obs["ticker"].isin(LARGE_CAP)]
    for c in sig_cols:
        f = big[big[c] == True]  # noqa: E712
        stats["exploratory"]["large_cap"][c[2:]] = {"n": int(len(f)), "hit_rate": round(float(f["e_any"].mean()), 3),
                                                    "base_rate": round(float(big[big[c].notna()]["e_any"].mean()), 3)}
    examples = []
    for s in SIGNALS:
        col = f"s_{s}"
        if col not in obs:
            continue
        hit = obs[(obs[col] == True) & (obs["e_any"] == True)]  # noqa: E712
        for _, r in hit.iterrows():
            q0, q1 = r["quarter"], r["when_any"]
            lead = (int(q1[:4]) * 4 + int(q1[5])) - (int(q0[:4]) * 4 + int(q0[5]))
            examples.append({"ticker": r["ticker"], "signal": s, "quarter": q0, "event_quarter": q1,
                             "events": [e for e in EVENTS[:-1] if r[f"e_{e}"]], "lead_months": lead * 3})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hit_rates.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    (OUT / "examples.json").write_text(json.dumps(examples, indent=1), encoding="utf-8")
    obs.to_csv(OUT / "observations.csv", index=False)
    return stats, examples


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=2012)
    ap.add_argument("--end", type=int, default=2024)
    a = ap.parse_args()
    stats, ex = run(a.start, a.end)
    print(f"universe {stats['universe']}, observed {stats['companies_observed']} companies, "
          f"{stats['firm_quarters']} firm-quarters with a full {WINDOW}-quarter forward window")
    for s, v in stats["signals"].items():
        e = v["events"]["any"]
        print(f"  {s:30s} fired {e['n']:4d}  hit {e['hit_rate']:.0%}  base {e['base_rate']:.0%}  "
              f"lift {e['lift']}  CI {e['ci95']}")
    print(f"{len(ex)} signal->event examples -> {OUT}")


if __name__ == "__main__":
    main()
