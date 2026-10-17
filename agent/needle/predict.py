"""Falsifiable predictions: a transparent revenue forecaster, calibrated on history, scored blind, then sealed.

Forecaster (deliberately simple so judges can audit it): next quarter's revenue YoY growth =
  0.5 x last quarter's YoY + 0.5 x the mean of the last 4 quarters' YoY,
with an interval of +/- k x (std of quarter-to-quarter changes in YoY over the last 8 quarters, floor 1 pt).
k is CALIBRATED, not chosen: calibrate() replays the forecaster over every firm-quarter of the 50-company
point-in-time backtest panel and picks the k whose interval contains the actual outcome 80% of the time.

  blind_test("JNJ")  J&J reported Q3 2026 on Oct 13. Using only data through Q2 2026, forecast Q3, then score it
                     against the page-cited figure in the Q3 earnings release (a real out-of-sample test).
  seal(tickers)      forecasts for Q3 2026 results not yet reported (Oct 29 - Nov 5), written to
                     out/predictions/sealed_2026Q3.json, hashed into the audit ledger and docs/needle_sealed.md.

Usage:  python -m agent.needle.predict [--calibrate] [--blind] [--seal]
"""

import argparse
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

from agent.needle import audit, backtest, pages, xbrl
from agent.needle.schema import Evidence, Prediction

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "out" / "predictions"
CAL = OUT / "calibration.json"
SEAL_TICKERS = ["MRK", "BMY", "LLY", "PFE", "ABBV", "AMGN", "GILD"]  # 10-K filers reporting Q3 after Oct 17


def yoy_series(rev):
    """{quarter: revenue YoY} from {quarter: revenue}."""
    return {q: rev[q] / rev[backtest._shift(q, -4)] - 1 for q in rev
            if backtest._shift(q, -4) in rev and rev[backtest._shift(q, -4)]}


def forecast(yoys, target, k):
    """(point, lo, hi) for target quarter using only YoY values for quarters before target."""
    hist = [yoys[q] for q in sorted(yoys) if q < target]
    if len(hist) < 8:
        return None
    last, mean4 = hist[-1], statistics.mean(hist[-4:])
    diffs = [b - a for a, b in zip(hist[-9:-1], hist[-8:])]
    spread = max(statistics.pstdev(diffs), 0.01)
    point = 0.5 * last + 0.5 * mean4
    return point, point - k * spread, point + k * spread


def calibrate(target_coverage=0.80):
    """Replay the forecaster over the point-in-time backtest panel; pick k for the target coverage."""
    cases = []
    for path in sorted(backtest.XBRL.glob("*.json.gz")):
        df = backtest.company_panel(path)
        if df.empty or "revenue" not in df:
            continue
        rev = {q: v for q, v in df["revenue"].dropna().items()}
        yoys = yoy_series(rev)
        for q in sorted(yoys):
            f = forecast(yoys, q, 1.0)
            if f and abs(yoys[q]) < 2:  # skip launch-year growth explosions
                point, lo, _ = f
                cases.append((yoys[q], point, point - lo))   # actual, point, unit spread
    def coverage(k):
        return sum(1 for a, p, s in cases if abs(a - p) <= k * s) / len(cases)
    ks = [x / 20 for x in range(10, 81)]
    k = min(ks, key=lambda x: abs(coverage(x) - target_coverage))
    abs_err = sorted(abs(a - p) for a, p, _ in cases)
    out = {"k": k, "coverage": round(coverage(k), 3), "target": target_coverage, "n_cases": len(cases),
           "median_abs_error_pts": round(100 * abs_err[len(abs_err) // 2], 2),
           "direction_accuracy_vs_last": round(sum(1 for a, p, _ in cases if (p >= 0) == (a >= 0)) / len(cases), 3)}
    OUT.mkdir(parents=True, exist_ok=True)
    CAL.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def _k():
    return json.loads(CAL.read_text())["k"] if CAL.exists() else calibrate()["k"]


def _panel_yoys(ticker, asof):
    p = xbrl.panel(ticker)
    rev = {q: v for q, v in p["revenue"].dropna().items() if q <= asof}
    return yoy_series(rev), max(rev)


def _pred(ticker, target, f, made_at, basis):
    point, lo, hi = f
    return Prediction(id=f"{ticker}-{target}-revenue_yoy", ticker=ticker, target_period=target, metric="revenue_yoy",
                      direction="within", threshold=None, probability=0.80,
                      basis=basis + [f"point {point:+.1%}", f"80% interval {lo:+.1%} to {hi:+.1%}"],
                      made_at=made_at, actual=None)


def blind_test(ticker="JNJ", target="2026Q3"):
    asof = backtest._shift(target, -1)
    yoys, latest = _panel_yoys(ticker, asof)
    assert latest == asof, f"{ticker} panel must stop at {asof} for a blind test, got {latest}"
    k = _k()
    f = forecast(yoys, target, k)
    pred = _pred(ticker, target, f, f"data through {asof} only", [f"calibrated k={k}"])
    # the answer key: reported growth in the target quarter's earnings release, page-cited and verified
    d = pages.docs(ticker, ("earnings_release",))
    hit = None
    for doc_id, doc in sorted(d.items(), reverse=True):
        for n, (_, text) in doc["pages"].items():
            m = re.search(r"(Third|Second|First|Fourth)-Quarter reported sales growth of (-?[\d.]+)%[^.\n]{0,40}", text)
            if m and m.group(1).lower() == {"1": "first", "2": "second", "3": "third", "4": "fourth"}[target[-1]]:
                quote = " ".join(text[m.start():m.start() + 160].split())
                ev = Evidence(doc_id, n, " ".join(quote.split()[:14]), figures=[m.group(2)])
                status, reason = pages.check(ev, d)
                hit = (float(m.group(2)) / 100, ev, status)
                break
        if hit:
            break
    if not hit:
        raise SystemExit("answer key not found in earnings releases")
    actual, ev, status = hit
    point, lo, hi = f
    pred.actual = actual
    pred.outcome = "hit" if lo <= actual <= hi else "miss"
    result = {"prediction": pred.__dict__, "actual": actual, "abs_error_pts": round(100 * abs(actual - point), 2),
              "answer_key": {"citation": ev.citation, "quote": ev.quote, "verifier": status}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"blind_{ticker}_{target}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    audit.append("prediction", {"blind_test": result})
    return result


def seal(tickers=SEAL_TICKERS, target="2026Q3"):
    k = _k()
    made = datetime.now(timezone.utc).isoformat()
    preds = []
    for t in tickers:
        yoys, latest = _panel_yoys(t, backtest._shift(target, -1))
        if latest != backtest._shift(target, -1):
            continue
        f = forecast(yoys, target, k)
        if f:
            preds.append(_pred(t, target, f, made, [f"calibrated k={k}", f"data through {latest}"]).__dict__)
    body = {"target": target, "made_at": made, "predictions": preds}
    digest = audit.seal(body)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"sealed_{target}.json").write_text(json.dumps({**body, "sha256": digest}, indent=2), encoding="utf-8")
    audit.append("prediction", {"sealed": target, "sha256": digest, "n": len(preds)})
    doc = ROOT / "docs" / "needle_sealed.md"
    lines = doc.read_text(encoding="utf-8").splitlines() if doc.exists() else [
        "# NEEDLE sealed predictions", "",
        "Each line is the sha256 of a predictions file, committed before the outcome was known.",
        "Recompute with agent.needle.audit.seal() on the file's body (all keys except sha256).", ""]
    lines.append(f"- {made} {target} n={len(preds)} sha256={digest} file=out/predictions/sealed_{target}.json")
    doc.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return body, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--seal", action="store_true")
    a = ap.parse_args()
    if a.calibrate or not CAL.exists():
        print("calibration:", calibrate())
    if a.blind:
        r = blind_test()
        p = r["prediction"]
        print(f"blind JNJ 2026Q3: {p['basis'][-2]}, {p['basis'][-1]}; actual {r['actual']:+.1%} -> {p['outcome']} "
              f"(error {r['abs_error_pts']} pts); answer key: {r['answer_key']['citation']} [{r['answer_key']['verifier']}]")
    if a.seal:
        body, digest = seal()
        for p in body["predictions"]:
            print(f"  {p['ticker']} {p['basis'][-2]}, {p['basis'][-1]}")
        print("sealed sha256:", digest)


if __name__ == "__main__":
    main()
