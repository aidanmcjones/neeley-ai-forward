"""Signals -> scored findings, per docs/materiality_spec.md, plus the Sharpest Needle and the 10-company league table.

S = I_norm x P x T x O x E x (1 + 0.25 x max(Z, 0)) x (1 + 0.25 x D)
  I_norm  dollar impact / trailing-4Q operating income (|value|, capped at 1). Dollar impact by signal kind:
          excess inventory or receivables vs revenue growth, gross-margin change x TTM revenue, impairment amount;
          kinds without a dollar path (drift, calls, labels) get a stated proxy and say so in impact["formula"].
  P       evidence-type prior from spec section 5 (contractual 0.9, trend 0.6, language drift 0.4, one quarter 0.3)
  T       1 / 1.08^(months/12), months = 12 unless the signal says otherwise
  O       1 - coverage: 0.9 if its topic is in the latest earnings-release first page, 0.7 if analysts asked about it
          on the last 4 calls, else 0.1 (only in the filing body). "Not priced in" is measured, not asserted.
  E       re-verified here, never trusted from the detector: verified 1.0, needs_human 0.6, data-only 0.3, failed 0
  Z, D    peer z-score (capped 3) and trend (-1/0/1)
Findings with E = 0 go to out/<T>/rejected.jsonl: the live "AI caught" log.
"""

import json
import math
import re
from pathlib import Path

from agent.needle import pages, xbrl
from agent.needle.detect import OUT, SHORTLIST
from agent.needle.schema import Evidence, Finding, Signal, read_jsonl, write_jsonl

ROOT = Path(__file__).resolve().parent.parent.parent
DETECTORS = ["forensics", "drift", "calls", "labels", "supply"]
BACKTEST = ROOT / "out" / "backtest" / "hit_rates.json"

PRIORS = {  # spec section 5
    "contractual": 0.9, "guidance": 0.7, "trend": 0.6, "drift": 0.4, "single": 0.3,
}
KIND_PRIOR = {
    "impairment": "contractual", "ira_exposed": "contractual", "exclusivity_earlier": "contractual",
    "boxed_warning_disadvantage": "contractual", "label_narrower": "contractual", "label_broader": "contractual",
    "dosing_burden": "contractual", "dosing_advantage": "contractual", "boxed_warning_advantage": "contractual",
    "spend_per_claim_gap": "trend", "qa_repeated_deflection": "guidance",
}
TOPIC_WORDS = {
    "inventory": r"inventor", "receivables": r"receivable", "gross_margin": r"gross margin|cost of (sales|products)",
    "impairment": r"impairment", "tax": r"tax rate", "rnd": r"research and development", "ira": r"Inflation Reduction|negotiat",
    "mfn": r"most.favou?red|MFN", "tariff": r"tariff", "gtn": r"gross.to.net|rebate|net price|pricing",
    "340b": r"340B", "generic": r"generic|biosimilar|exclusivity", "litigation": r"litigation|lawsuit|talc",
    "supply": r"supply|manufactur", "pricing": r"pric", "china": r"China", "guidance": r"guidance",
}


def _hit_rates():
    if not BACKTEST.exists():
        return {}
    s = json.loads(BACKTEST.read_text(encoding="utf-8"))["signals"]
    return {k: {"hard": v["events"]["hard"], "margin_drop": v["events"]["margin_drop"], "episodes": v["episodes"]}
            for k, v in s.items()}


def _proven(hr):
    """A backtest lift counts only when its firm-clustered 95% CI lies entirely above 1."""
    for ev in ("hard", "margin_drop"):
        ci = (hr or {}).get(ev, {}).get("lift_ci95_firm_clustered")
        if ci and ci[0] > 1:
            return True
    return False


def _topics(sig):
    t = set(sig.meta.get("topics") or [])
    if sig.meta.get("topic") and sig.meta["topic"] != "other":
        t.add(sig.meta["topic"])
    for key in TOPIC_WORDS:
        if key in sig.kind:
            t.add(key)
    return t or {"other"}


def _coverage(ticker, topics, cache={}):
    """Obscurity input: where (if anywhere) the market already hears about this topic."""
    if ticker not in cache:
        d = pages.docs(ticker)
        rel = sorted((x for x in d.values() if x["row"]["doc_type"] == "earnings_release"),
                     key=lambda x: str(x["row"].get("filed")), reverse=True)
        headline = " ".join(t for _, t in list(rel[0]["pages"].values())[:1]) if rel else ""
        qa = " ".join(t for x in d.values() if x["row"]["doc_type"] == "transcript" for _, t in x["pages"].values())
        cache[ticker] = (headline, qa)
    headline, qa = cache[ticker]
    pats = [TOPIC_WORDS[t] for t in topics if t in TOPIC_WORDS]
    if any(re.search(p, headline, re.I) for p in pats):
        return 0.9, "in the latest earnings-release headline page"
    if any(len(re.findall(p, qa, re.I)) >= 3 for p in pats):
        return 0.7, "raised on recent earnings calls"
    return 0.1, "only in filings / data, not in headlines or call Q&A"


def _recheck(sig, docs):
    """Re-verify every Evidence. Returns E and the per-evidence verdicts."""
    if not sig.evidence:
        return (0.3 if sig.meta.get("data") or sig.meta.get("series") else 0.0), []
    verdicts = []
    for ev in sig.evidence:
        if ev.doc_id.startswith("drug:"):
            from agent.needle.detect.labels import verify_label
            ok = verify_label(ev)
            verdicts.append(("verified" if ok else "rejected", "" if ok else "label quote not found"))
        else:
            verdicts.append(pages.check(ev, docs))
    worst = min({"verified": 1.0, "needs_human": 0.6, "rejected": 0.0}[v] for v, _ in verdicts)
    return worst, verdicts


def _trend(t):
    """-1 / 0 / 1. Detectors give either a number or {period: metric}; worsening = latest above the earlier mean."""
    if isinstance(t, dict) and len(t) >= 2:
        vals = [t[k] for k in sorted(t) if isinstance(t[k], (int, float))]
        if len(vals) >= 2:
            earlier = sum(vals[:-1]) / len(vals[:-1])
            return 1 if vals[-1] > earlier * 1.1 + 1e-9 else -1 if vals[-1] < earlier * 0.9 else 0
        return 0
    try:
        return max(min(int(t or 0), 1), -1)
    except (TypeError, ValueError):
        return 0


def _impact(sig, p, ttm_oi):
    """(dollars, formula) for kinds with a dollar path; (None, proxy note) otherwise."""
    try:
        q = max(p["revenue"].dropna().index)
        if not str(sig.period).startswith(q[:4]) or len(p["revenue"].dropna()) < 8:
            # 20-F filers (annual data only): compare fiscal years from the annual table
            p = xbrl.annual(sig.ticker)
            q = max(p["revenue"].dropna().index)
        if sig.kind.startswith("inventory_outpaces") or sig.kind.startswith("receivables_outpace"):
            col = "inventory" if sig.kind.startswith("inventory") else "receivables"
            prior = f"{int(q[:4]) - 1}{q[4:]}"
            rev_g = p.at[q, "revenue"] / p.at[prior, "revenue"] - 1
            excess = p.at[q, col] - p.at[prior, col] * (1 + rev_g)
            return excess, (f"excess {col} = {col} now {p.at[q, col] / 1e6:,.0f}M - prior {p.at[prior, col] / 1e6:,.0f}M "
                            f"x (1 + revenue growth {rev_g:+.1%}) = {excess / 1e6:,.0f}M at risk of write-down or "
                            f"channel destocking")
        if sig.kind.startswith("gross_margin"):
            rev4 = p["revenue"].dropna().iloc[-4:].sum()
            dollars = abs(sig.value or 0) * rev4
            return dollars, f"gross-margin change {sig.value:+.1%} x TTM revenue {rev4 / 1e9:,.1f}B = {dollars / 1e6:,.0f}M"
        if sig.kind == "impairment":
            return abs(sig.value or 0) * (p["assets"].dropna().iloc[-1] if "assets" in p else 0), "impairment as disclosed"
    except Exception:
        pass
    return None, "no direct dollar path; scored on a stated proxy of 2% of operating income"


def score_signal(sig, docs, p, ttm_oi, hits):
    E, verdicts = _recheck(sig, docs)
    dollars, formula = _impact(sig, p, ttm_oi)
    i_norm = min(abs(dollars) / ttm_oi, 1.0) if dollars is not None and ttm_oi else 0.02
    prior_key = KIND_PRIOR.get(sig.kind) or ("drift" if sig.detector == "drift" else
                                             "trend" if (sig.meta.get("trend") or 0) else "single")
    P = PRIORS[prior_key]
    T = 1 / 1.08 ** (12 / 12)
    topics = _topics(sig)
    cov, cov_note = _coverage(sig.ticker, topics)
    O = 1 - cov
    Z = max(min(sig.peer_z or 0, 3), -3)
    D = _trend(sig.meta.get("trend"))
    S = i_norm * P * T * O * E * (1 + 0.25 * max(Z, 0)) * (1 + 0.25 * D)
    hr = hits.get(sig.kind.replace("_peer_outlier", ""))
    conf = "high" if E == 1.0 and (P >= 0.6 or _proven(hr)) else \
           "medium" if E >= 0.6 else "low"
    status = "verified" if E == 1.0 else "needs_human" if E >= 0.3 else "rejected"
    return Finding(
        id=f"{sig.ticker}-{sig.detector}-{abs(hash((sig.kind, sig.detail))) % 10**6:06d}", ticker=sig.ticker,
        finding=sig.detail, signal_kind=sig.kind, evidence=sig.evidence,
        impact={"dollars": dollars, "formula": formula, "i_norm": round(i_norm, 4), "ttm_operating_income": ttm_oi},
        peer={"metric_value": sig.value, "peer_median": sig.peer_median, "z": sig.peer_z},
        vector={"I_norm": round(i_norm, 4), "P": P, "T": round(T, 3), "O": round(O, 2), "E": E, "Z": Z, "D": D,
                "obscurity_note": cov_note, "prior": prior_key, "topics": sorted(topics)},
        score=round(S, 6), confidence=conf, verdict=status,
        reason="; ".join(r for v, r in verdicts if v != "verified"), hit_rate=hr or {},
    )


def ttm_operating_income(ticker, p):
    """Sum of the last 4 consecutive quarters when available (10-K filers), else the latest fiscal year (20-F)."""
    if "operating_income" in p:
        s = p["operating_income"].dropna()
        if len(s) >= 4:
            last4 = list(s.index[-4:])
            from agent.needle.backtest import _shift
            if last4 == [_shift(last4[-1], -i) for i in (3, 2, 1, 0)]:
                return float(s.iloc[-4:].sum())
    a = xbrl.annual(ticker)
    if "operating_income" in a and a["operating_income"].notna().any():
        return float(a["operating_income"].dropna().iloc[-1])
    return 0.0


def scale_base(ticker, p):
    """Denominator for I_norm: TTM operating income, floored at 10% of TTM revenue so a one-off loss quarter
    (e.g. a large IPR&D charge) cannot flip the sign or explode the ratio."""
    oi = ttm_operating_income(ticker, p)
    rev = p["revenue"].dropna()
    rev4 = float(rev.iloc[-4:].sum()) if len(rev) >= 4 else float(xbrl.annual(ticker)["revenue"].dropna().iloc[-1])
    return max(oi, 0.10 * rev4)


def score_ticker(ticker):
    docs = pages.docs(ticker)
    p = xbrl.panel(ticker)
    oi = scale_base(ticker, p)
    hits = _hit_rates()
    findings, rejected = [], []
    for det in DETECTORS:
        for sig in read_jsonl(OUT / ticker / f"signals_{det}.jsonl", Signal):
            f = score_signal(sig, docs, p, oi or 0, hits)
            (rejected if f.verdict == "rejected" else findings).append(f)
    seen, unique = set(), []
    for f in findings:  # one finding per (kind, sentence, first citation)
        key = (f.signal_kind, f.finding, f.evidence[0].citation if f.evidence else "")
        if key not in seen:
            seen.add(key)
            unique.append(f)
    findings = sorted(unique, key=lambda f: -f.score)
    write_jsonl(OUT / ticker / "findings.jsonl", findings)
    write_jsonl(OUT / ticker / "rejected.jsonl", rejected)
    return findings, rejected


def sharpest_needle(findings):
    pool = [f for f in findings if f.vector.get("O", 0) >= 0.7 and f.vector.get("E", 0) >= 0.6]
    return max(pool, key=lambda f: f.score) if pool else None


def league(tickers=SHORTLIST):
    rows = []
    for t in tickers:
        fs, rj = score_ticker(t)
        top = fs[:5]
        needle = sharpest_needle(fs)
        rows.append({"ticker": t, "score": round(sum(f.score for f in top), 4), "n_findings": len(fs),
                     "n_verified": sum(f.verdict == "verified" for f in fs), "n_rejected": len(rj),
                     "high_confidence": sum(f.confidence == "high" for f in fs),
                     "sharpest_needle": needle.finding if needle else None,
                     "needle_id": needle.id if needle else None})
    rows.sort(key=lambda r: -r["score"])
    (OUT / "league.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows
