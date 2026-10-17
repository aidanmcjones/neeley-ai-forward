"""Time Machine: do NEEDLE's forensic signals precede real trouble? Code-only, point-in-time, no LLM.

v2, after adversarial review (gate 2). The reviewers refuted v1 and these fixes answer each finding:
  - Non-overlapping event windows. v1 compared trailing-4Q figures at t+1..t+3 that still contained quarters known
    at t, so ~41% of events were implied by t's own run-rate. Now: revenue_drop = revenue over the NEXT four
    quarters (t+1..t+4, or t+5..t+8) <= 95% of the trailing four quarters ending at t; margin_drop likewise.
  - As-of filter: a value counts only if it was filed within 135 days of its period end, so comparatives first
    published in a later year's 10-K are never used at t.
  - 52/53-week calendars: period ends within the first 7 days of a month are labelled with the prior month's quarter.
  - One concept per company series (the one covering most periods), so a tag switch is not a fake level change;
    impairment takes the largest reported component per quarter (no double counting).
  - Exits: companies that stop filing (acquired, bankrupt) keep their pre-exit quarters; events seen before the
    exit count, so the trouble right before an exit is not dropped (censoring disclosed).
  - Primary outcome is a HARD event (revenue_drop or impairment). margin_drop is reported separately because it
    shares the gross-margin series with the gross_margin_drop signal.
  - Statistics: hit rate vs non-fired quarters, lift with a firm-clustered bootstrap 95% CI, a within-firm
    (fixed-effect) estimate, episode counts, size terciles, dose-response on rows where all signals are computable.
Universe: 50 pharma / biotech filers incl. later-acquired or bankrupt ones, HAND-SELECTED (disclosed).

Usage:  python -m agent.needle.backtest [--start 2012 --end 2024]
"""

import argparse
import gzip
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
XBRL = ROOT / "data" / "backtest" / "xbrl"
OUT = ROOT / "out" / "backtest"

CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "Revenue", "SalesRevenueNet",
                "SalesRevenueGoodsNet", "RevenueFromContractsWithCustomers",
                "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfSales",
             "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization"],
    "inventory": ["InventoryNet", "Inventories"],
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "CurrentTradeReceivables",
                    "TradeAndOtherCurrentReceivables"],
    "assets": ["Assets"],
}
IMPAIRMENT = ["ImpairmentOfIntangibleAssetsExcludingGoodwill", "ImpairmentOfIntangibleAssetsFinitelived",
              "ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill", "GoodwillImpairmentLoss",
              "AssetImpairmentCharges", "ImpairmentOfIntangibleAssetsExcludingGoodwillAndFinancialAssets"]
STOCKS = {"inventory", "receivables", "assets"}
SIGNALS = ["inventory_outpaces_revenue", "receivables_outpace_revenue", "dso_rising", "dio_rising", "gross_margin_drop"]
EVENTS = ["revenue_drop", "impairment", "margin_drop", "hard"]
WINDOW = 8
MAX_LAG_DAYS = 135
EXITED = {"CELG", "AGN", "MYL", "MNK", "ENDP", "ALXN", "SGEN", "HZNP", "CTLT", "BLUE", "SAGE"}
LARGE_CAP = {"MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD", "NVS", "GSK", "SNY", "TAK",
             "REGN", "BIIB", "VRTX", "TEVA", "VTRS", "CELG", "AGN", "MYL", "ZTS", "ALXN", "BHC"}


# ---------------------------------------------------------------- quarters

def _qlabel(end):
    d = date.fromisoformat(end)
    if d.day <= 7:  # 52/53-week fiscal calendars end a few days into the next month
        d = d.replace(day=1) - timedelta(days=1)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _shift(q, n):
    y, k = int(q[:4]), int(q[5]) - 1
    t = y * 4 + k + n
    return f"{t // 4}Q{t % 4 + 1}"


def _prior_quarters(q, n):
    return [_shift(q, -i) for i in range(n, 0, -1)]


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


# ---------------------------------------------------------------- point-in-time panel

def _concept_values(node, stock):
    """{(quarter, kind): value} for one concept: first filing within MAX_LAG_DAYS of period end wins."""
    best = {}
    for unit, vals in node["units"].items():
        if not (unit.startswith("USD") or unit in ("DKK", "EUR", "GBP", "CHF", "JPY")):
            continue
        for v in vals:
            end, filed = v.get("end"), v.get("filed")
            if not end or not filed or _days(end, filed) > MAX_LAG_DAYS or _days(end, filed) < 0:
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
            if key not in best or filed < best[key][0]:
                best[key] = (filed, v["val"])
    return {k: val for k, (_, val) in best.items()}


def concept_series(facts, names, stock):
    """[{quarter: value}, ...] one dict per concept, in priority order. Comparisons later require a single concept
    to cover every period involved, so a tag switch (e.g. ASC 606) can never fake a level change.
    Q4 is derived as FY - (Q1+Q2+Q3) of the same concept when no direct quarter value exists."""
    out = []
    for ns in ("us-gaap", "ifrs-full"):
        for n in names:
            node = facts.get("facts", {}).get(ns, {}).get(n)
            if not node:
                continue
            vals = _concept_values(node, stock)
            s = {q: v for (q, kind), v in vals.items() if stock or kind == "Q"}
            if not stock:
                for (q, kind), fy in vals.items():
                    labels = _prior_quarters(q, 3)
                    if kind == "FY" and q not in s and all(l in s for l in labels):
                        s[q] = fy - sum(s[l] for l in labels)
            if s:
                out.append(s)
    return out


def pit_series(facts, names, stock):
    """{quarter: value} merged across concepts (first concept wins per period). For display / single-period use;
    comparisons go through _vals(), which enforces one concept per comparison."""
    merged = {}
    for s in concept_series(facts, names, stock):
        for q, v in s.items():
            merged.setdefault(q, v)
    return merged


def impairment_series(facts):
    """Largest reported impairment component per quarter (components overlap, so never summed)."""
    out = {}
    for n in IMPAIRMENT:
        node = facts.get("facts", {}).get("us-gaap", {}).get(n)
        if not node:
            continue
        for (q, kind), v in _concept_values(node, False).items():
            if kind == "Q":
                out[q] = max(out.get(q, 0), v)
    return out


def company_panel(path):
    """DataFrame with one column per (metric, concept): 'revenue|0', 'revenue|1', ... plus 'impairment|0'."""
    facts = json.loads(gzip.decompress(path.read_bytes()))
    cols = {}
    for m, names in CONCEPTS.items():
        for i, s in enumerate(concept_series(facts, names, m in STOCKS)):
            cols[f"{m}|{i}"] = s
    cols["impairment|0"] = impairment_series(facts)
    df = pd.DataFrame(cols)
    if df.empty or not any(c.startswith("revenue|") for c in df):
        return pd.DataFrame()
    df = df.sort_index()
    return df[df.index.str.match(r"^\d{4}Q[1-4]$")]


# ---------------------------------------------------------------- signals and events

def _cols(df, metric):
    return [c for c in df.columns if c.split("|")[0] == metric]


def _vals(df, metric, qs):
    """Values for every quarter in qs from the first concept that covers ALL of them, else None."""
    for c in _cols(df, metric):
        vals = [df.at[x, c] if x in df.index else None for x in qs]
        if all(v is not None and pd.notna(v) for v in vals):
            return vals
    return None


def _val(df, metric, q):
    v = _vals(df, metric, [q])
    return v[0] if v else None


def _yoy(df, col, q):
    v = _vals(df, col, [_shift(q, -4), q])
    return v[1] / v[0] - 1 if v and v[0] else None


def _sum4(df, col, qs):
    v = _vals(df, col, qs)
    return sum(v) if v else None


def signals_at(df, q):
    s, p = {}, _shift(q, -4)
    ry, iy, ay = _yoy(df, "revenue", q), _yoy(df, "inventory", q), _yoy(df, "receivables", q)
    if ry is not None and iy is not None:
        s["inventory_outpaces_revenue"] = (iy - ry) >= 0.10
    if ry is not None and ay is not None:
        s["receivables_outpace_revenue"] = (ay - ry) >= 0.08

    def ratios(num, den):
        """(prior, now) num/den with each metric's prior and current value from one concept."""
        a, b = _vals(df, num, [p, q]), _vals(df, den, [p, q])
        if a and b and b[0] and b[1]:
            return a[0] / b[0], a[1] / b[1]
        return None, None
    dso_prev, dso_now = ratios("receivables", "revenue")
    if dso_now and dso_prev:
        s["dso_rising"] = dso_now / dso_prev - 1 >= 0.10
    dio_prev, dio_now = ratios("inventory", "cogs")
    if dio_now and dio_prev:
        s["dio_rising"] = dio_now / dio_prev - 1 >= 0.15
    c_prev, c_now = ratios("cogs", "revenue")
    if c_now is not None and c_prev is not None and 0 < c_now < 1 and 0 < c_prev < 1:
        s["gross_margin_drop"] = (c_now - c_prev) >= 0.02
    return s


def events_after(df, q, exited=False):
    """Events strictly after t on windows that share no quarter with the information known at t.
    Returns None if the forward window is unobserved (a still-listed company near the data end)."""
    trail = [_shift(q, -i) for i in (3, 2, 1, 0)]
    nxt1 = [_shift(q, i) for i in (1, 2, 3, 4)]
    nxt2 = [_shift(q, i) for i in (5, 6, 7, 8)]
    observed = [x for x in nxt1 + nxt2 if _val(df, "revenue", x) is not None]
    if len(observed) < WINDOW and not (exited and len(observed) >= 4):
        return None
    ev = {}
    for win, label in ((nxt1, nxt1[-1]), (nxt2, nxt2[-1])):
        v = _vals(df, "revenue", trail + win)          # same concept for the baseline and the window
        if v and sum(v[:4]) and sum(v[4:]) <= 0.95 * sum(v[:4]):
            ev["revenue_drop"] = label
            break
    for f in nxt1 + nxt2:
        imp, a = _val(df, "impairment", f), _val(df, "assets", f) or _val(df, "assets", q)
        if imp and a and imp / a >= 0.02:
            ev["impairment"] = f
            break
    for win, label in ((nxt1, nxt1[-1]), (nxt2, nxt2[-1])):
        r, c = _vals(df, "revenue", trail + win), _vals(df, "cogs", trail + win)
        if r and c and sum(r[:4]) and sum(r[4:]):
            g0, g1 = 1 - sum(c[:4]) / sum(r[:4]), 1 - sum(c[4:]) / sum(r[4:])
            if 0 < g0 < 1 and g0 - g1 >= 0.03:
                ev["margin_drop"] = label
                break
    hard = [ev[k] for k in ("revenue_drop", "impairment") if k in ev]
    if hard:
        ev["hard"] = min(hard)
    return ev


# ---------------------------------------------------------------- statistics

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _lift(df, col, ev):
    fired, other = df[df[col] == True], df[df[col] == False]  # noqa: E712
    if not len(fired) or not len(other) or not other[f"e_{ev}"].mean():
        return None
    return fired[f"e_{ev}"].mean() / other[f"e_{ev}"].mean()


def clustered_ci(df, col, ev, reps=1000, seed=11):
    """Firm-clustered bootstrap 95% CI of lift (fired hit rate / non-fired hit rate)."""
    firms = list(df["ticker"].unique())
    groups = {t: g for t, g in df.groupby("ticker")}
    rng, lifts = random.Random(seed), []
    for _ in range(reps):
        sample = pd.concat([groups[rng.choice(firms)] for _ in firms])
        l = _lift(sample, col, ev)
        if l is not None:
            lifts.append(l)
    lifts.sort()
    if len(lifts) < 50:
        return None
    return [round(lifts[int(0.025 * len(lifts))], 2), round(lifts[int(0.975 * len(lifts)) - 1], 2)]


def within_firm(df, col, ev):
    """Mean over firms of (fired hit rate - own non-fired hit rate), with a firm bootstrap CI (pp)."""
    diffs = []
    for _, g in df.groupby("ticker"):
        f, o = g[g[col] == True], g[g[col] == False]  # noqa: E712
        if len(f) and len(o):
            diffs.append(f[f"e_{ev}"].mean() - o[f"e_{ev}"].mean())
    if len(diffs) < 5:
        return None
    rng = random.Random(5)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(1000))
    return {"firms": len(diffs), "mean_pp": round(100 * sum(diffs) / len(diffs), 1),
            "ci95_pp": [round(100 * boots[25], 1), round(100 * boots[974], 1)],
            "firms_positive": sum(d > 0 for d in diffs)}


def episodes(df, col):
    n = 0
    for _, g in df.sort_values("quarter").groupby("ticker"):
        prev = None
        for _, r in g.iterrows():
            if r[col] == True and not (prev and prev[0] == _shift(r["quarter"], -1) and prev[1]):  # noqa: E712
                n += 1
            prev = (r["quarter"], r[col] == True)  # noqa: E712
    return n


# ---------------------------------------------------------------- run

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
            ev = events_after(df, q, ticker in EXITED)
            if ev is None:
                continue
            sig = signals_at(df, q)
            if not sig:
                continue
            ttm = _sum4(df, "revenue", [_shift(q, -i) for i in (3, 2, 1, 0)])
            rows.append({"ticker": ticker, "quarter": q, "ttm_revenue": ttm, "revenue_yoy": _yoy(df, "revenue", q),
                         **{f"s_{k}": v for k, v in sig.items()},
                         **{f"e_{k}": (k in ev) for k in EVENTS}, **{f"when_{k}": ev.get(k) for k in EVENTS}})
    obs = pd.DataFrame(rows)
    stats = {"version": 2, "universe": len(list(XBRL.glob("*.json.gz"))), "universe_note":
             "hand-selected 50 pharma/biotech filers incl. later-acquired or bankrupt companies",
             "firm_quarters": len(obs), "companies_observed": int(obs["ticker"].nunique()),
             "window_quarters": WINDOW, "period": f"{start}-{end}", "primary_event": "hard (revenue_drop or impairment)",
             "signals": {}}
    terc = obs["ttm_revenue"].quantile([1 / 3, 2 / 3]).tolist() if len(obs) else [0, 0]
    obs["size"] = obs["ttm_revenue"].apply(lambda r: "small" if r <= terc[0] else "mid" if r <= terc[1] else "large")
    for s in SIGNALS:
        col = f"s_{s}"
        if col not in obs:
            continue
        valid = obs[obs[col].notna()].copy()
        valid[col] = valid[col].astype(bool)
        fired, other = valid[valid[col]], valid[~valid[col]]
        entry = {"n_fired": int(len(fired)), "episodes": episodes(valid, col), "firms": int(fired["ticker"].nunique()),
                 "events": {}}
        for e in EVENTS:
            k, n = int(fired[f"e_{e}"].sum()), int(len(fired))
            hit = k / n if n else 0.0
            base = float(other[f"e_{e}"].mean()) if len(other) else 0.0
            entry["events"][e] = {"hits": k, "n": n, "hit_rate": round(hit, 3), "rate_when_not_fired": round(base, 3),
                                  "lift": round(hit / base, 2) if base else None,
                                  "lift_ci95_firm_clustered": clustered_ci(valid, col, e) if e in ("hard", "margin_drop") else None,
                                  "wilson_ci95_hit_rate": [round(x, 3) for x in wilson(k, n)]}
        entry["within_firm_hard"] = within_firm(valid, col, "hard")
        entry["by_size_hard"] = {sz: {"hit": round(float(g[g[col]]["e_hard"].mean()), 3) if g[col].any() else None,
                                      "not_fired": round(float(g[~g[col]]["e_hard"].mean()), 3) if (~g[col]).any() else None}
                                 for sz, g in valid.groupby("size")}
        stats["signals"][s] = entry
    full = obs.dropna(subset=[f"s_{s}" for s in SIGNALS if f"s_{s}" in obs])
    nsig = full[[f"s_{s}" for s in SIGNALS]].astype(bool).sum(axis=1)
    stats["dose_response_full_coverage"] = {str(k): {"n": int((nsig == k).sum()),
                                                     "hard_rate": round(float(full.loc[nsig == k, "e_hard"].mean()), 3),
                                                     "margin_rate": round(float(full.loc[nsig == k, "e_margin_drop"].mean()), 3)}
                                            for k in sorted(nsig.unique())}
    examples = []
    for s in SIGNALS:
        col = f"s_{s}"
        if col not in obs:
            continue
        for _, r in obs[(obs[col] == True) & (obs["e_hard"] == True)].iterrows():  # noqa: E712
            q0, q1 = r["quarter"], r["when_hard"]
            lead = (int(q1[:4]) * 4 + int(q1[5])) - (int(q0[:4]) * 4 + int(q0[5]))
            examples.append({"ticker": r["ticker"], "signal": s, "quarter": q0, "event_quarter": q1,
                             "events": [e for e in ("revenue_drop", "impairment") if r[f"e_{e}"]],
                             "lead_months": lead * 3})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hit_rates.json").write_text(json.dumps(stats, indent=2, default=lambda o: o.item()), encoding="utf-8")
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
          f"{stats['firm_quarters']} firm-quarters")
    for s, v in stats["signals"].items():
        h = v["events"]["hard"]
        wf = v["within_firm_hard"] or {}
        print(f"  {s:28s} fired {h['n']:4d} ({v['episodes']} episodes)  hard {h['hit_rate']:.0%} vs {h['rate_when_not_fired']:.0%}"
              f"  lift {h['lift']} CI {h['lift_ci95_firm_clustered']}  within-firm {wf.get('mean_pp')}pp {wf.get('ci95_pp')}")
    print("dose-response (full coverage):", stats["dose_response_full_coverage"])
    print(f"{len(ex)} examples -> {OUT}")


if __name__ == "__main__":
    main()
