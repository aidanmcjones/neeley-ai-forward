"""Financial-forensics detector: XBRL panel trends and peer comparison across the shortlist.

Signals: inventory/receivables outpacing revenue, DIO/DSO rising, gross-margin drop, tax-rate shift,
impairments, R&D shift, and peer outliers (|z| >= 1.5). Numbers come from xbrl.panel (10-K filers, quarterly) or
xbrl.annual (NVO, AZN: 20-F, FY2025 vs FY2024). Each signal cites the filing page where the figure appears.
"""

import re
import statistics
from functools import lru_cache

import pandas as pd

from agent.needle import pages, xbrl
from agent.needle.detect import SHORTLIST, cli
from agent.needle.schema import Evidence, Signal

ANNUAL_ONLY = {"NVO", "AZN"}
NAME = "forensics"
PEER_METRICS = {
    "inv_gap": "inventory-vs-revenue growth gap", "rec_gap": "receivables-vs-revenue growth gap",
    "dio": "days inventory", "dso": "days sales outstanding", "gross_margin": "gross margin",
    "etr": "effective tax rate", "rnd_pct": "R&D % of revenue",
}
# XBRL columns behind each metric (for evidence and meta)
COLS = {"inv_gap": ["inventory", "revenue"], "rec_gap": ["receivables", "revenue"], "dio": ["inventory", "cogs"],
        "dso": ["receivables", "revenue"], "gross_margin": ["revenue", "cogs"], "etr": ["income_tax", "pretax_income"],
        "rnd_pct": ["rnd", "revenue"], "impairment": ["impairment"]}


def _lab(p):
    return f"Q{p[-1]} {p[:4]}" if "Q" in p else f"FY{p}"


def _prior(p):
    return str(int(p[:4]) - 1) + p[4:]


def _g(df, p, col):
    v = df.at[p, col] if p in df.index and col in df.columns else None
    return None if v is None or pd.isna(v) else float(v)


def _frame(ticker):
    if ticker in ANNUAL_ONLY:
        df, mult = xbrl.annual(ticker), 1
    else:
        df, mult = xbrl.panel(ticker), 4
    df = df[df["revenue"].notna()].astype(float)
    return df, mult, ticker in ANNUAL_ONLY


def _metrics(df, p, mult):
    """Metrics for one period p; None where inputs are missing."""
    rev, cogs, inv, rec = (_g(df, p, c) for c in ("revenue", "cogs", "inventory", "receivables"))
    pr = _prior(p)
    out = {}
    for name, col in (("rev_yoy", "revenue"), ("inv_yoy", "inventory"), ("rec_yoy", "receivables")):
        a, b = _g(df, p, col), _g(df, pr, col)
        out[name] = a / b - 1 if a is not None and b else None
    out["inv_gap"] = None if out["inv_yoy"] is None or out["rev_yoy"] is None else out["inv_yoy"] - out["rev_yoy"]
    out["rec_gap"] = None if out["rec_yoy"] is None or out["rev_yoy"] is None else out["rec_yoy"] - out["rev_yoy"]
    out["dio"] = inv / (cogs * mult) * 365 if inv is not None and cogs else None
    out["dso"] = rec / (rev * mult) * 365 if rec is not None and rev else None
    out["gross_margin"] = 1 - cogs / rev if cogs is not None and rev else None
    tax, pre = _g(df, p, "income_tax"), _g(df, p, "pretax_income")
    out["etr"] = tax / pre if tax is not None and pre else None
    rnd = _g(df, p, "rnd")
    out["rnd_pct"] = rnd / rev if rnd is not None and rev else None
    imp, assets = _g(df, p, "impairment"), _g(df, p, "assets")
    out["impairment_pct"] = imp / assets if imp is not None and assets else None
    return out


@lru_cache(maxsize=32)
def _history(ticker):
    """(periods newest first [4], {period: metrics}, df, mult, annual?, prior-year metrics of newest)."""
    df, mult, ann = _frame(ticker)
    ps = list(df.index)[-4:][::-1]
    hist = {p: _metrics(df, p, mult) for p in ps}
    return ps, hist, df, mult, ann, _metrics(df, _prior(ps[0]), mult)


@lru_cache(maxsize=1)
def _peers():
    return {t: _history(t)[1][_history(t)[0][0]] for t in SHORTLIST}


def _zscore(metric, ticker):
    vals = {t: m.get(metric) for t, m in _peers().items() if m.get(metric) is not None}
    x = vals.get(ticker)
    if x is None or len(vals) < 4:
        return None, None
    xs = list(vals.values())
    med = statistics.median(xs)
    mad = statistics.median(abs(v - med) for v in xs)
    if mad > 0:
        z = 0.6745 * (x - med) / mad
    else:
        sd = statistics.pstdev(xs)
        z = (x - med) / sd if sd else 0.0
    return med, max(-3.0, min(3.0, z))


def _fmt_m(v):
    return f"{abs(v) / 1e6:,.0f}"


def _doc_pool(ticker):
    ds = pages.docs(ticker)
    form = "20-F" if ticker in ANNUAL_ONLY else "10-Q"
    cand = [(k, d) for k, d in ds.items() if d["row"]["form"] == form]
    if form == "20-F":
        cand = [c for c in cand if "2025" in c[1]["row"]["period"]] or cand
        cand.sort(key=lambda c: -len(c[1]["pages"]))
    else:
        cand.sort(key=lambda c: c[1]["row"]["period"], reverse=True)
        cand = cand[:1]
    return ds, cand


def _find_quote(cands, fig, prefer):
    """(doc_id, page, quote): best page holding fig (preferring statement pages), ~30 words around it."""
    pat = re.compile(r"(?<![\d,.])" + re.escape(fig) + r"(?![\d,]|\.\d)")
    best = None
    for doc_id, d in cands:
        for n, (_, text) in d["pages"].items():
            toks = text.split()
            idx = next((i for i, t in enumerate(toks) if pat.search(t)), None)
            if idx is None:
                continue
            score = sum(1 for k in prefer if k.lower() in text.lower())
            if best is None or score > best[0]:
                best = (score, doc_id, n, toks, idx)
        if best and best[0] > 0:
            break
    if not best:
        return None
    _, doc_id, n, toks, idx = best
    start = max(0, min(idx - 14, len(toks) - 30))
    return doc_id, n, " ".join(toks[start:start + 30])


def _evidence(ticker, cols, values):
    """Evidence for the columns behind a signal; quotes that fail pages.check are dropped."""
    ds, cands = _doc_pool(ticker)
    evs, seen = [], set()
    for col in cols:
        v = values.get(col)
        if v is None:
            continue
        fig = _fmt_m(v)
        prefer = ["Balance Sheet", "Financial Position"] if col in ("inventory", "receivables", "assets") \
            else ["Statements of", "Income Statement"]
        hit = _find_quote(cands, fig, prefer)
        if not hit or (hit[0], hit[1], fig) in seen:
            continue
        seen.add((hit[0], hit[1], fig))
        ev = Evidence(doc_id=hit[0], page=hit[1], quote=hit[2], figures=[fig])
        if pages.check(ev, ds)[0] == "verified":
            evs.append(ev)
    return evs


def _pp(x):
    return f"{x * 100:+.1f} pts"


def _fmt_metric(m, v):
    if m in ("dio", "dso"):
        return f"{v:.0f} days"
    if m in ("inv_gap", "rec_gap"):
        return _pp(v)
    return f"{v:.1%}"


def run(ticker):
    ticker = ticker.upper()
    ps, hist, df, mult, ann, bc = _history(ticker)
    L = ps[0]
    c = hist[L]
    lab = _lab(L)
    concepts = xbrl.panel(ticker).attrs["concepts"]
    values = {col: _g(df, L, col) for col in df.columns}
    sigs = []

    def add(kind, value, detail, cols, metric=None):
        med, z = _zscore(metric, ticker) if metric else (None, None)
        evs = _evidence(ticker, cols, values)
        meta = {"concepts": {x: concepts.get(x) for x in cols if x in concepts},
                "series": {p: {x: _g(df, p, x) for x in cols} for p in ps}}
        if metric:
            meta["trend"] = {p: hist[p].get(metric) for p in ps}
        if med is not None:
            detail += f"; peer median {_fmt_metric(metric, med)}, z {z:+.1f}"
        if not evs:
            meta["evidence"] = "xbrl_only"
            detail += " (xbrl_only: figure not found in filing text)"
        sigs.append(Signal(ticker, NAME, kind, L, value, med, z, detail, evs, meta))

    # >= 10 pts is the alert; >= 5 pts with inventory up 10%+ is kept as a "watch" level (e.g. JNJ Q2 2026)
    if c["inv_gap"] is not None and (c["inv_gap"] >= 0.10 or (c["inv_gap"] >= 0.05 and c["inv_yoy"] >= 0.10)):
        add("inventory_outpaces_revenue", c["inv_gap"],
            f"Inventory {c['inv_yoy']:+.1%} YoY vs revenue {c['rev_yoy']:+.1%} ({lab}); gap {_pp(c['inv_gap'])}",
            COLS["inv_gap"], "inv_gap")
    if c["rec_gap"] is not None and c["rec_gap"] >= 0.08:
        add("receivables_outpace_revenue", c["rec_gap"],
            f"Receivables {c['rec_yoy']:+.1%} YoY vs revenue {c['rev_yoy']:+.1%} ({lab}); gap {_pp(c['rec_gap'])}",
            COLS["rec_gap"], "rec_gap")
    for m, kind, thr, name in (("dio", "dio_rising", 0.15, "DIO"), ("dso", "dso_rising", 0.10, "DSO")):
        a, b = c.get(m), bc.get(m)
        if a is not None and b and a / b - 1 >= thr:
            add(kind, a / b - 1, f"{name} {a:.0f} days vs {b:.0f} a year earlier ({a / b - 1:+.1%}) ({lab})",
                COLS[m], m)
    a, b = c.get("gross_margin"), bc.get("gross_margin")
    if a is not None and b is not None and b - a >= 0.02:
        add("gross_margin_drop", a - b, f"Gross margin {a:.1%} vs {b:.1%} a year earlier ({_pp(a - b)}) ({lab})",
            COLS["gross_margin"], "gross_margin")
    a, b = c.get("etr"), bc.get("etr")
    if a is not None and b is not None and abs(a - b) >= 0.04:
        add("tax_rate_shift", a - b, f"Effective tax rate {a:.1%} vs {b:.1%} a year earlier ({_pp(a - b)}) ({lab})",
            COLS["etr"], "etr")
    a, b = c.get("rnd_pct"), bc.get("rnd_pct")
    if a is not None and b is not None and abs(a - b) >= 0.03:
        add("rnd_shift", a - b, f"R&D {a:.1%} of revenue vs {b:.1%} a year earlier ({_pp(a - b)}) ({lab})",
            COLS["rnd_pct"], "rnd_pct")
    for p in (ps[:1] if ann else ps):
        ip = hist[p].get("impairment_pct")
        if ip is None or ip < 0.005:
            continue
        iv = _g(df, p, "impairment")
        evs = _evidence(ticker, ["impairment"], {"impairment": iv})
        meta = {"concepts": {"impairment": concepts.get("impairment")},
                "series": {q: {"impairment": _g(df, q, "impairment"), "assets": _g(df, q, "assets")} for q in ps}}
        det = f"Impairment {_fmt_m(iv)}M = {ip:.2%} of assets ({_lab(p)})"
        if not evs:
            meta["evidence"] = "xbrl_only"
            det += " (xbrl_only: figure not found in filing text)"
        sigs.append(Signal(ticker, NAME, "impairment", p, ip, None, None, det, evs, meta))
    for m, label in PEER_METRICS.items():
        x = c.get(m)
        med, z = _zscore(m, ticker)
        if x is None or z is None or abs(z) < 1.5:
            continue
        add(f"{m}_peer_outlier", x, f"{label.capitalize()} {_fmt_metric(m, x)} ({lab}) vs peers",
            COLS[m], m)
    return sigs


if __name__ == "__main__":
    cli("forensics", run)
