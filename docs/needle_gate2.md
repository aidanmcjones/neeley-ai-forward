# Gate 2: adversarial review of the NEEDLE backtest

Method: `/adversarial-review`. Two skeptics with different lenses read the committed code (025b89c) and the raw data, each wrote an independent verdict, then each read the other's verdict and conceded, held or narrowed. Scratch scripts are under the skeptics' temp folders.

## The claim that was reviewed (v1)
"Gross-margin drop is followed by an adverse event 59% of the time vs a 43% base rate (lift 1.39), and 3+ signals give 54% vs 37%. That is credible evidence that NEEDLE's signals predict trouble."

## Verdict: refuted by both skeptics

| Finding | Lens | Severity | Status after round 2 |
|---|---|---|---|
| Event windows overlapped data already known at t: trailing-4Q figures at t+1..t+3 still contained t's quarters, so about 41% of events were implied by t's own run-rate | Leakage | high | Conceded by both: it inflates fired and non-fired rates alike and mostly hits the margin event. Fixed (non-overlapping windows) |
| Gross-margin signal vs margin-drop event is persistence of one series | Statistics | high | Agreed. Primary outcome is now hard events (revenue drop or impairment) |
| Lift is between firms, not within a firm (within-firm CI includes 0); 303 firings are only 147 episodes | Statistics | high | Held by statistics skeptic. Now reported: firm-clustered CI, within-firm estimate, episode counts |
| Dose-response rests on margin drop only; zero-signal group mixed in uncomputable rows | Statistics | high | Held. Now computed only on rows where all signals are observable |
| 2.9% of inputs first filed long after t (next year's comparatives) | Leakage | medium | Held. Fixed: values count only if filed within 135 days of period end |
| 52/53-week calendars mislabel quarters (JNJ, PFE, EXEL, PRGO) | Leakage | medium | Fixed: early-month period ends snap to the prior quarter |
| Concept switching (ASC 606 revenue tags, impairment components) creates fake level changes | Leakage | medium | Fixed: every comparison uses a single concept covering all its periods; impairment takes the largest component |
| Pre-exit quarters of acquired/bankrupt firms dropped; Mallinckrodt's revenue tag missing | Leakage | medium | Fixed: exited firms keep partial windows (>= 4 quarters); tag added |
| Universe hand-picked; rules and results in one commit | Leakage | low | Disclosed in the code docstring and here |

## What survived (v2, after the fixes)
1,410 firm-quarters, 43 companies, 2012-2024, point-in-time, no LLM:
- **No forensic signal significantly predicts a revenue drop or impairment** within 8 quarters. The gross-margin drop is closest (lift 1.25, firm-clustered CI 0.82-1.76); inventory outpacing revenue is 1.17 (CI 0.83-1.69); receivables, DSO and DIO are at or below 1.
- **The signals do track future margin compression**, with a monotonic dose-response on full-coverage rows: 12% (0 signals), 18%, 23%, 33%, 29%, 61% (5 signals, n = 18).
- The skeptics' own corrected estimate on v1 data (non-overlapping windows, before the stricter point-in-time filter) was a lift of about 1.4-1.6, CI just above 1, between-firm. That estimate does not survive the stricter v2 filters, so we do not claim it.

## How NEEDLE uses this
- Forensic signals are **flags for human review**, not predictions. A backtest lift raises a finding's confidence only when its firm-clustered CI lies entirely above 1 (`score._proven`). None currently does on hard events.
- The **revenue forecaster** is the calibrated predictive piece: its 80% interval covered 79.4% of 1,793 historical firm-quarters, and it called J&J's Q3 2026 revenue growth blind (+7.3% forecast, interval +4.3% to +10.4%, actual +5.9%).
- This record is the How We Did It report's "AI was confidently wrong" case. The confident error was ours, in the first backtest, and AI skeptics caught it before any judge saw the number.
