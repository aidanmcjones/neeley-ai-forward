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
# Peer days-inventory uses revenue, not cost of sales: on cost of sales an 85%-margin company (LLY) shows 469
# days vs a 74% median purely from its margin. Own-history DIO (dio_rising) still uses cost of sales.
PEER_METRICS = {
    "inv_gap": "inventory-vs-revenue growth gap", "rec_gap": "receivables-vs-revenue growth gap",
    "dis": "inventory in days of sales", "dso": "days sales outstanding", "gross_margin": "gross margin",
    "etr": "effective tax rate (trailing 4Q)", "rnd_pct": "R&D % of revenue",
}
# Which direction is a risk: +1 high is bad, -1 low is bad, 0 either. A favorable outlier (LLY's high margin)
# is a strength, not a finding.
ADVERSE = {"inv_gap": 1, "rec_gap": 1, "dis": 1, "dso": 1, "gross_margin": -1, "etr": 1, "rnd_pct": 0}
# XBRL columns behind each metric (for evidence and meta)
COLS = {"inv_gap": ["inventory", "revenue"], "rec_gap": ["receivables", "revenue"], "dio": ["inventory", "cogs"],
        "dis": ["inventory", "revenue"], "dso": ["receivables", "revenue"], "gross_margin": ["revenue", "cogs"],
        "etr": ["income_tax", "pretax_income"], "rnd_pct": ["rnd", "revenue"], "impairment": ["impairment"]}
# A charge this text describes makes an R&D jump a one-off (context, not a finding), when it is >= 25% of R&D
ONE_OFF_RND = re.compile(
    r"\$\s*([\d.,]+)\s*(billion|million)[^$]{0,200}?acquired in-process research and development"
    r"|acquired (?:in-process research and development|IPR&D)[^$]{0,120}?\$\s*([\d.,]+)\s*(billion|million)", re.I)
# ...and a tax-rate move is the same one-off when the filing says that charge carried no tax benefit
ONE_OFF_TAX = re.compile(r"[^.]{0,200}(?:had no tax benefit|not (?:tax )?deductible|non-deductible)[^.]{0,160}", re.I)


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


def _etr(df, p, mult):
    """Effective tax rate over the trailing 4 quarters (one quarter swings on discrete items: PFE's 62.3% in
    Q2 2026 was a tax benefit on impairment losses). None when pre-tax income is under 5% of revenue, where
    the ratio means nothing (MRK's -95.8% after a $5.7B IPR&D charge)."""
    ps = [p]
    if mult == 4:
        from agent.needle.backtest import _shift
        ps = [_shift(p, -i) for i in range(4)]
    sums = {}
    for c in ("income_tax", "pretax_income", "revenue"):
        vals = [_g(df, q, c) for q in ps]
        sums[c] = None if None in vals else sum(vals)
    tax, pre, rev = sums["income_tax"], sums["pretax_income"], sums["revenue"]
    if tax is None or pre is None or not rev or abs(pre) < 0.05 * rev:
        return None
    return tax / pre


def _first_verified(ticker, pattern):
    """First verified Evidence for a regex match in the latest filing, else None."""
    ds, cands = _doc_pool(ticker)
    for doc_id, d in cands:
        for n, (_, text) in d["pages"].items():
            m = pattern.search(" ".join(text.split()))
            if m:
                ev = Evidence(doc_id=doc_id, page=n, quote=m.group(0).strip())
                if pages.check(ev, ds)[0] == "verified":
                    return ev
    return None


def _one_off_rnd(ticker, rnd):
    """Verified Evidence of an acquired-IPR&D charge >= 25% of the period's R&D in the latest filing, else None."""
    if not rnd:
        return None
    ds, cands = _doc_pool(ticker)
    for doc_id, d in cands:
        for n, (_, text) in d["pages"].items():
            flat = " ".join(text.split())
            for m in ONE_OFF_RND.finditer(flat):
                amt, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
                dollars = float(amt.replace(",", "")) * (1e9 if unit.lower() == "billion" else 1e6)
                if dollars < 0.25 * rnd:
                    continue
                ev = Evidence(doc_id=doc_id, page=n, quote=m.group(0))
                if pages.check(ev, ds)[0] == "verified":
                    return ev, dollars
    return None


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
    out["dis"] = inv / (rev * mult) * 365 if inv is not None and rev else None
    out["dso"] = rec / (rev * mult) * 365 if rec is not None and rev else None
    out["gross_margin"] = 1 - cogs / rev if cogs is not None and rev else None
    out["etr"] = _etr(df, p, mult)
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
    if m in ("dio", "dis", "dso"):
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

    # An IPR&D charge is a one-off only when R&D rose and removing it lands R&D back near last year's level
    # (LLY books acquired IPR&D on its own line, so its R&D fell and its charge explains nothing)
    one_off = _one_off_rnd(ticker, values.get("rnd"))
    if one_off and c.get("rnd_pct") is not None and bc.get("rnd_pct") is not None:
        ex = (values["rnd"] - one_off[1]) / values["revenue"]
        if not (c["rnd_pct"] - bc["rnd_pct"] >= 0.03 and abs(ex - bc["rnd_pct"]) < 0.03):
            one_off = None
    else:
        one_off = None
    tax_one_off = _first_verified(ticker, ONE_OFF_TAX) if one_off else None

    def add(kind, value, detail, cols, metric=None):
        med, z = _zscore(metric, ticker) if metric else (None, None)
        evs = _evidence(ticker, cols, values)
        meta = {"concepts": {x: concepts.get(x) for x in cols if x in concepts},
                "series": {p: {x: _g(df, p, x) for x in cols} for p in ps}}
        if metric == "rnd_pct" and one_off:
            ev, dollars = one_off
            evs.append(ev)
            meta["one_off"] = {"what": "acquired IPR&D charge", "dollars": dollars}
            ex = (values["rnd"] - dollars) / values["revenue"]
            detail += f" (one-off: {dollars / 1e9:,.1f}B acquired IPR&D; {ex:.1%} of revenue without it)"
        if metric == "etr" and tax_one_off:
            evs.append(tax_one_off)
            meta["one_off"] = {"what": "acquired IPR&D charge with no tax benefit", "dollars": one_off[1]}
            detail += " (one-off: the acquired IPR&D charge carried no tax benefit)"
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
        add("tax_rate_shift", a - b, f"Effective tax rate {a:.1%} vs {b:.1%} a year earlier ({_pp(a - b)}) "
                                     f"({'trailing 4Q to ' if not ann else ''}{lab})",
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
        if x is None or z is None or abs(z) < 1.5 or ADVERSE[m] * z < 0:
            continue
        add(f"{m}_peer_outlier", x, f"{label.capitalize()} {_fmt_metric(m, x)} ({lab}) vs peers",
            COLS[m], m)
    return sigs


if __name__ == "__main__":
    cli("forensics", run)
