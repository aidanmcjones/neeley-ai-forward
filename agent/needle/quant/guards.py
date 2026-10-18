"""Guards from the red-team of the old NEEDLE scorer (agent-chat thread #19), applied to detector signals before FIND
scores them. Each guard is a small rule that returns a reason when a row must not count as a finding.

Guard numbers follow the thread. Already handled elsewhere in FIND: 1 favourable outliers get pi = 0
(find.favorable_statistical), 6 same-fact dedupe in the league (league.dedupe_facts; the explicit twin drop is
here), 7 label rows M = 0 (impact.label_unquantified). The rest:

  2  days-inventory PEER comparison on revenue, not cost of sales (an 85% gross-margin company shows 469 days from its
     margin alone); the own-history DIO change (dio_rising) stays on cost of sales.
  3  tax rate on trailing four quarters, and no tax signal when the period's pre-tax income is under 5% of revenue.
  4  acquired IPR&D one-offs: R&D rows are context when the filing books an acquired IPR&D charge of at least 25% of the
     period's R&D, R&D rose, and R&D without the charge is within 3 points of revenue of last year; a tax row in the
     same window is a one-off only when the filing says the charge had no tax benefit.
  5  period consistency: the numbers in a growth row's sentence must match the operands re-derived for the signal's
     own period (annual table for annual signals) within 0.5 pts (find.yoy_basis does the re-derivation).
  6  rec_gap_peer_outlier / inv_gap_peer_outlier are dropped when their base signal fired with the same number.
  8  undirected MD&A drift rows cannot be the Sharpest Needle (risk-factor changes, intensified wording, new risk
     vocabulary and dropped hedges stay eligible).
  9  paragraph filter: a drift or call row needs at least one evidence quote that is a sentence (not a table of
     contents or a parsed table).

Actions: "drop" (not a finding: goes to rejected_v2 with the reason), "context" (kept in findings_v2 with S = 0 and the
reason), "no_needle" (scored, but never the Sharpest Needle).
"""

import re
import statistics

from . import data

PRETAX_MIN_SHARE = 0.05      # guard 3
TAX_SHIFT_MIN = 0.04         # forensics tax_rate_shift threshold, re-applied on the TTM basis
PEER_Z = 1.5                 # forensics peer-outlier threshold
IPRD_MIN_SHARE = 0.25        # guard 4
IPRD_RATIO_TOL = 0.03        # guard 4
PERIOD_TOL = 0.005           # guard 5 (0.5 pts)
ORDINAL = {"1": "first", "2": "second", "3": "third", "4": "fourth"}


# ------------------------------------------------------------------ helpers
def _ttm(p, per, col):
    """Sum of the four quarters ending at per (None when any is missing)."""
    idx = list(p.index)
    if per not in idx:
        return None
    i = idx.index(per)
    if i < 3:
        return None
    vals = [p.at[q, col] for q in idx[i - 3:i + 1]]
    if any(v is None or v != v for v in vals):
        return None
    return float(sum(vals))


def _prior(per):
    return f"{int(per[:4]) - 1}{per[4:]}"


def _robust_z(vals, x):
    xs = list(vals)
    med = statistics.median(xs)
    mad = statistics.median(abs(v - med) for v in xs)
    if mad > 0:
        z = 0.6745 * (x - med) / mad
    else:
        sd = statistics.pstdev(xs)
        z = (x - med) / sd if sd else 0.0
    return med, max(-3.0, min(3.0, z))


def _history(ticker):
    from agent.needle.detect import forensics
    return forensics._history(ticker)


def _latest_filing(ticker):
    r = data.db().execute("SELECT doc_id FROM docs WHERE ticker = ? AND doc_type IN ('quarterly_report', "
                          "'annual_report') ORDER BY filed DESC LIMIT 1", (ticker,)).fetchone()
    return r[0] if r else None


def _sentences(doc_id):
    if not doc_id:
        return []
    out = []
    for n, (_, text) in data.index().pages(doc_id).items():
        flat = " ".join(text.split())
        out += [(n, s) for s in re.split(r"(?<=[.;])\s+", flat)]
    return out


# ------------------------------------------------------------------ guard 2
def dio_peer_on_revenue(sig):
    """Days inventory vs peers on revenue (inventory / annualised revenue x 365). Reason when not an outlier."""
    from agent.needle.detect import SHORTLIST
    vals = {}
    for t in SHORTLIST:
        ps, hist, df, mult, ann, _ = _history(t)
        L = ps[0]
        inv = df.at[L, "inventory"] if "inventory" in df.columns else None
        rev = df.at[L, "revenue"]
        if inv is not None and inv == inv and rev:
            vals[t] = float(inv) / (float(rev) * mult) * 365
    x = vals.get(sig.ticker)
    if x is None or len(vals) < 4:
        return None
    med, z = _robust_z(vals.values(), x)
    if abs(z) < PEER_Z:
        return ("drop", f"guard 2: days inventory on revenue {x:.0f} vs peer median {med:.0f} (z {z:+.1f}) is not a "
                        "peer outlier; the cost-of-sales DIO reflects the gross margin, not the inventory build")
    return None


# ------------------------------------------------------------------ guard 3
def tax_guard(sig):
    """Tax rows: no signal when the period's pre-tax income is under 5% of revenue; otherwise re-test on TTM."""
    from agent.needle import xbrl
    per = str(sig.period or "")
    if re.fullmatch(r"\d{4}Q[1-4]", per):
        p = xbrl.panel(sig.ticker)
        try:
            pre, rev = float(p.at[per, "pretax_income"]), float(p.at[per, "revenue"])
        except Exception:
            return None
        if rev and pre < PRETAX_MIN_SHARE * rev:
            return ("drop", f"guard 3: pre-tax income {pre / 1e6:,.0f}M is under 5% of revenue {rev / 1e6:,.0f}M in "
                            f"{per}: the rate is not meaningful (loss or near-zero base)")
        tx, pt = _ttm(p, per, "income_tax"), _ttm(p, per, "pretax_income")
        tx0, pt0 = _ttm(p, _prior(per), "income_tax"), _ttm(p, _prior(per), "pretax_income")
        rv = _ttm(p, per, "revenue")
        if pt is None or not pt or rv is None:
            return None
        if pt < PRETAX_MIN_SHARE * rv:
            return ("drop", f"guard 3: TTM pre-tax income {pt / 1e6:,.0f}M is under 5% of TTM revenue")
        etr = tx / pt
        if sig.kind == "tax_rate_shift" and pt0:
            etr0 = tx0 / pt0
            if abs(etr - etr0) < TAX_SHIFT_MIN:
                return ("drop", f"guard 3: on trailing four quarters the rate moved {etr0:.1%} -> {etr:.1%} "
                                f"({(etr - etr0) * 100:+.1f} pts), under the 4-pt shift threshold")
        if sig.kind == "etr_peer_outlier":
            from agent.needle.detect import SHORTLIST
            vals = {}
            for t in SHORTLIST:
                try:
                    pp = xbrl.panel(t)
                    q = pp["pretax_income"].dropna().index[-1]
                    a, b = _ttm(pp, q, "income_tax"), _ttm(pp, q, "pretax_income")
                    if a is not None and b:
                        vals[t] = a / b
                except Exception:
                    continue
            vals[sig.ticker] = etr
            if len(vals) >= 4:
                med, z = _robust_z(vals.values(), etr)
                if abs(z) < PEER_Z:
                    return ("drop", f"guard 3: TTM effective tax rate {etr:.1%} vs peer median {med:.1%} "
                                    f"(z {z:+.1f}) is not a peer outlier")
    return None


# ------------------------------------------------------------------ guard 4
def iprd_charge(ticker, per):
    """(charge in USD m, sentence, no_tax_benefit) for an acquired IPR&D charge booked in quarter per, from the
    latest filing's text, or None."""
    if not re.fullmatch(r"\d{4}Q[1-4]", str(per)):
        return None
    sents = _sentences(_latest_filing(ticker))
    ordinal = ORDINAL[per[-1]] + " quarter"
    total, hit = 0.0, None
    seen = set()
    for _, s in sents:
        m = re.search(r"charge of \$\s?([\d.,]+)\s?(billion|million) to Research and development", s, re.I)
        if not m or not re.search(r"IPR&D|in-process research", s, re.I) or ordinal not in s.lower():
            continue
        v = float(m.group(1).replace(",", "")) * (1000 if m.group(2).lower() == "billion" else 1)
        if v in seen:
            continue
        seen.add(v)
        total += v
        hit = hit or s
    if not total:
        return None
    no_tax = any(re.search(r"had no tax benefits?", s, re.I) and ordinal in s.lower() for _, s in sents)
    return total, hit, no_tax


def iprd_guard(sig):
    """Guard 4 on R&D rows (rnd_shift, rnd_pct_peer_outlier) and tax rows in the same window."""
    from agent.needle import xbrl
    per = str(sig.period or "")
    hit = iprd_charge(sig.ticker, per)
    if hit is None:
        return None
    charge, sent, no_tax = hit
    if sig.kind in ("tax_rate_shift", "etr_peer_outlier"):
        if no_tax:
            return ("context", f"guard 4: one-off: the {per} acquired IPR&D charge ${charge:,.0f}M had no tax "
                               "benefit (filing), which moves the rate")
        return None
    p = xbrl.panel(sig.ticker)
    try:
        rnd, rev = float(p.at[per, "rnd"]) / 1e6, float(p.at[per, "revenue"]) / 1e6
        rnd0, rev0 = float(p.at[_prior(per), "rnd"]) / 1e6, float(p.at[_prior(per), "revenue"]) / 1e6
    except Exception:
        return None
    if charge >= IPRD_MIN_SHARE * rnd and rnd > rnd0 and abs((rnd - charge) / rev - rnd0 / rev0) <= IPRD_RATIO_TOL:
        return ("context", f"guard 4: one-off: acquired IPR&D charge ${charge:,.0f}M is {charge / rnd:.0%} of {per} "
                           f"R&D; without it R&D is {(rnd - charge) / rev:.1%} of revenue vs {rnd0 / rev0:.1%} a "
                           "year earlier")
    return None


# ------------------------------------------------------------------ guard 6
TWIN = {"rec_gap_peer_outlier": "receivables_outpace_revenue", "inv_gap_peer_outlier": "inventory_outpaces_revenue"}


def twin_guard(sig, sigs):
    base = TWIN.get(sig.kind)
    if not base:
        return None
    for s in sigs:
        if s.kind == base and s.ticker == sig.ticker and s.period == sig.period and s.value is not None \
                and sig.value is not None and abs(s.value - sig.value) < 1e-9:
            return ("drop", f"guard 6: same number as the fired {base} row ({sig.value * 100:+.1f} pts)")
    return None


# ------------------------------------------------------------------ guard 8
DIRECTED_MDNA = re.compile(r"new risk vocabulary|dropped hedge|hedge dropped|stronger wording", re.I)


def needle_direction_guard(sig):
    if sig.detector == "drift" and sig.kind.startswith("mdna_") and not DIRECTED_MDNA.search(sig.detail or ""):
        return ("no_needle", "guard 8: undirected MD&A change: not eligible as the Sharpest Needle until a direction "
                             "is read")
    return None


# ------------------------------------------------------------------ guard 9
def is_prose(quote):
    """At least one sentence: 8+ words of mostly letters ending in . ? or !, not a dotted contents line."""
    q = " ".join(str(quote or "").split())
    if re.search(r"\.{4,}|(?:\. ){4,}", q):
        return False
    for s in re.split(r"(?<=[.?!])\s+", q):
        words = re.findall(r"[A-Za-z][A-Za-z'-]+", s)
        if len(words) >= 8 and s.rstrip().endswith((".", "?", "!")) and \
                sum(c.isalpha() for c in s) >= 0.6 * max(1, len(s.replace(" ", ""))):
            return True
    return False


def paragraph_guard(sig):
    if sig.detector not in ("drift", "calls") or not sig.evidence:
        return None
    if not any(is_prose(ev.quote) for ev in sig.evidence):
        return ("drop", "guard 9: no evidence quote is a sentence (table of contents or parsed table)")
    return None


# ------------------------------------------------------------------ all
def check(sig, sigs):
    """[(action, reason)] for one signal; empty when no guard applies."""
    out = []
    if sig.kind == "dio_peer_outlier":
        out.append(dio_peer_on_revenue(sig))
    if sig.kind in ("tax_rate_shift", "etr_peer_outlier"):
        out.append(tax_guard(sig))
    if sig.kind in ("rnd_shift", "rnd_pct_peer_outlier", "tax_rate_shift", "etr_peer_outlier"):
        out.append(iprd_guard(sig))
    out.append(twin_guard(sig, sigs))
    out.append(needle_direction_guard(sig))
    out.append(paragraph_guard(sig))
    return [g for g in out if g]


# ------------------------------------------------------------------ receivables footnote read (thread #19 (c))
RECEIVABLE_KINDS = {"receivables_outpace_revenue", "rec_gap_peer_outlier", "dso_rising", "dso_peer_outlier"}
FOOTNOTE_TERMS = {
    "factoring": r"\bfactor(?:ing|ed)?\b|option to factor",
    "FVOCI receivables": r"FVOCI|fair value through other comprehensive income",
    "bank acceptance drafts": r"bank acceptance drafts?",
    "gross billing with a separate rebate liability": r"(?:sales deductions?|rebates?|chargebacks?)[^.]{0,160}"
                                                       r"(?:accrued|liabilit|balance as of)",
}
# Notes that give the net movement, read by hand from the cited pages and re-verified on every run. The receivables
# change and the explaining balance change are both quoted; the net is derived from them.
FOOTNOTE_NET = {
    "AMGN": {"doc": "AMGN:10k_FY2025.md", "term": "gross billing with a separate rebate liability",
             "rec": (109, "Trade receivables, net 9,570 6,782", 9570.0, 6782.0),
             "offset": [(83, "Balance as of December 31, 2024 6,817 1,162 426 8,405", 8405.0),
                        (83, "Balance as of December 31, 2025 $ 8,839 $ 1,298 $ 469 $ 10,606", 10606.0)],
             "what": "the sales-deduction (rebate and chargeback) liability",
             "period": "FY2025 (10-K; the 10-Q does not give the quarterly deduction balance)"},
    "AZN": {"doc": "AZN:20f_FY2025.md", "term": "factoring, FVOCI receivables and bank acceptance drafts",
            "rec": (88, "Trade receivables 10,289 8,335", 10289.0, 8335.0),
            "offset": [(88, "Trade receivables include $ 2,681 m (2024: $ 667 m) measured at FVOCI", 667.0),
                       (88, "Trade receivables include $ 2,681 m (2024: $ 667 m) measured at FVOCI", 2681.0)],
            "what": "receivables held at FVOCI because the Group can factor them or holds China bank acceptance drafts",
            "period": "FY2025 (20-F p. F-29)"},
}


def _filing_pages(doc_ids):
    out = []
    idx = data.index()
    for d in doc_ids:
        try:
            pages = idx.pages(d)
        except Exception:
            continue
        for n, (printed, text) in pages.items():
            flat = " ".join(text.replace("​", " ").split())
            if re.search(r"receivable|sales deduction|rebate|chargeback", flat, re.I):
                out.append((d, n, printed, flat))
    return out


def receivables_read(sig, cited_docs=()):
    """Footnote read for a receivables-gap row: search the cited filing and the latest annual report's receivables and
    revenue-deduction pages for factoring, FVOCI receivables, bank acceptance drafts, or gross billing with a separate
    rebate liability. Returns {"hits": [(term, doc, page, printed, sentence)], "net": FOOTNOTE_NET spec or None}."""
    if sig.kind not in RECEIVABLE_KINDS:
        return None
    docs = [d for d in cited_docs if d]
    ann = data.db().execute("SELECT doc_id FROM docs WHERE ticker = ? AND doc_type = 'annual_report' ORDER BY filed "
                            "DESC LIMIT 1", (sig.ticker,)).fetchone()
    if ann:
        docs.append(ann[0])
    hits, seen = [], set()
    for d, n, printed, flat in _filing_pages(dict.fromkeys(docs)):
        for s in re.split(r"(?<=[.;])\s+", flat):
            for term, pat in FOOTNOTE_TERMS.items():
                if term in seen or not re.search(pat, s, re.I):
                    continue
                if term != "gross billing with a separate rebate liability" and not re.search(r"receivable", s, re.I):
                    continue
                if 30 <= len(s) <= 600:
                    hits.append((term, d, n, printed, s))
                    seen.add(term)
    return {"hits": hits, "net": FOOTNOTE_NET.get(sig.ticker)}
