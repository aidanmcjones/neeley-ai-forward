"""Run NEEDLE end to end: detectors -> scorer -> league table, every step written to the audit ledger.

  python -m agent.needle.run --ticker AZN      one company
  python -m agent.needle.run --all             all 10 shortlist companies + league table
  python -m agent.needle.run --all --skip-detect   rescore saved signals only (fast)
"""

import argparse
import importlib
import time

from agent.needle import audit, score
from agent.needle.detect import SHORTLIST, save

DETECTORS = ["forensics", "drift", "calls", "labels"]


def detect(ticker):
    counts = {}
    for name in DETECTORS:
        mod = importlib.import_module(f"agent.needle.detect.{name}")
        try:
            sigs = mod.run(ticker)
        except Exception as e:
            print(f"  {ticker} {name}: FAILED {type(e).__name__}: {e}")
            continue
        save(ticker, name, sigs)
        counts[name] = len(sigs)
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticker")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--skip-detect", action="store_true")
    a = ap.parse_args()
    tickers = SHORTLIST if a.all or not a.ticker else [a.ticker.upper()]
    t0 = time.time()
    for t in tickers:
        counts = {} if a.skip_detect else detect(t)
        fs, rj = score.score_ticker(t)
        audit.append("run", {"ticker": t, "signals": counts, "findings": len(fs), "rejected": len(rj),
                             "top": [f.id for f in fs[:5]]})
        for f in fs[:10]:
            audit.append("finding", {"id": f.id, "score": f.score, "verdict": f.verdict,
                                     "evidence": [e.citation for e in f.evidence]})
        needle = score.sharpest_needle(fs)
        print(f"{t}: {sum(counts.values()) if counts else '-'} signals -> {len(fs)} findings, {len(rj)} rejected; "
              f"needle: {needle.finding[:90] if needle else 'none'}")
    if len(tickers) > 1:
        for r in score.league(tickers):
            print(f"  {r['ticker']:5s} {r['score']:.4f}  findings {r['n_findings']:3d}  high-conf {r['high_confidence']}")
    ok, n, bad = audit.verify_chain()
    print(f"ledger intact: {ok} ({n} records); {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
