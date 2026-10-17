# DECIDE: valuing the 24-month CEO move

For the pitch writer. Spec: `docs/quant_model.md` Section 5 (v2.1 on branch quant-spec, matching quant-model ee7846c). Code: `agent/needle/quant/{moves,decide,kill,decide_cli}.py`. Dollars are USD millions.

## The equation

```
EV_m = sum_s p_s [ sum_{tau=1..24} ( P_alive(tau) CF_in - P_reach(tau) CF_out ) / (1 + r_mo)^tau  +  TV_24 / (1 + r_mo)^24 ]
```

- Scenarios bear / base / bull weigh 0.50 / 0.11 / 0.39 (Trinity 2023 US launches) and scale revenue by 0.8 / 1.0 / 1.2 (ZS failure and success definitions).
- r = 7.85% a year (Damodaran pharma WACC, Jan 2026), converted to a monthly rate.
- P_alive is the product of phase probabilities for readouts already passed (BIO 2021). P_reach is the probability of reaching the phase in which an outflow is spent (Stewart, Allison, Johnson 2001).
- TV is everything after month 24 for the position held at month 24, valued with the same rules, to loss of exclusivity or 10 years after launch.
- Ramp to peak: v2 templates ramp differently (label expansion 42 months, acquired or licensed 39.9, pricing 12, commercial 18). Label expansion now defaults to a 60-month ramp, 40% of peak at month 24, consistent with the 25-40% research default (commit 9a1932c); 42 months is kept as `LABEL_RAMP_MONTHS_ALT`. In-window value (months 1-24) and terminal value are reported separately for every move.
- Correctness oracle, 60-month default ramp: EV 1,265.2 (bear 1,025.3, base 1,294.9, bull 1,564.5), in-window PV -53.3, cash at risk 57.6, payback month 54, spread 539.3.
- Correctness oracle, 42-month alternative ramp (v2): the synthetic label-expansion case gives EV 1,431.2 (bear 1,161.0, base 1,464.6, bull 1,768.2), cash at risk 57.6, payback month 51, spread 607.2. `tests/needle/test_decide.py` asserts all of it.

## The five numbers and how to read them

| Number | Read it as |
|---|---|
| Expected value | Present value today of the move, in dollars, after weighting scenarios and technical risk. Mostly terminal value for long-dated moves, so read it next to payback. |
| Downside cash at risk | What the company has spent and cannot recover if the bear case holds and the first trial fails, net of inflows and of payments it can avoid (uncalled milestones, CVRs). Compare it with cash on the balance sheet: that is the feasibility gate. |
| Payback month | First month the cumulative discounted expected cash turns positive, searched to 120 months. `None` means not within 120. |
| Scenario EV spread | EV if the bull case is certain minus EV if the bear case is certain. It is the commercial uncertainty in dollars. It is understated: the multipliers are the ZS boundary values, the true tails are wider. |
| MCDA score | 0 to 1, four criteria at 0.25 each: strategic fit (share of the company's top-five Part 1 M x E the move addresses; v2 used S, which contains obscurity, so a well-known material problem scored 0; `decide.finding_weight`, commit 9a1932c), capability (share of required assets held), execution risk (P_alive x probability-weighted multiplier / 1.2), stakeholder evidence (share of deciders with documented evidence). It only decides between moves whose EV intervals overlap. |

Selection: drop moves whose cash at risk exceeds cash and equivalents; take the highest EV; if the top two [EV bear, EV bull] intervals overlap, take the higher MCDA. The next two moves are the reported rejected alternatives, each with the one reason that cost it the choice. A move whose base-case EV is at or below zero is never chosen: when no eligible move has EV above zero, decide.md heads "No candidate clears the hurdle; least-bad option: <move> (EV x)" over the unchanged five-number table, and decide.json carries `chosen: null`, `least_bad` and `selection_rule`. Every run prints the rule it applied in one sentence under the headline ("Selected on EV", "EV ranges overlap (a vs b); selected on MCDA score x vs y", "Cash gate excluded <move>" or the strategic-fit exclusion), so the reader sees why the top-EV move was or was not picked.

## Move templates (`moves.py`)

| Code | Case move | Probability structure | Part 1 findings that feed it |
|---|---|---|---|
| M1 | Acquire a drug | Deal-comp price (premium median 63%, EV/peak 0.5x to 1.0x), BIO rates if unapproved, CVR at payout probability | LOE finding sizes the gap to replace (fit only) |
| M2 | License a drug | Upfront ~6% of deal, development milestones 33% (avoidable on failure), royalties 9.3% to 13%, BIO rates | LOE finding (fit only) |
| M3 | Seek approval for a new indication | rNPV: costs at P_reach, revenue at Phase III x NDA (non-NME 0.675 x 0.915) | label finding sets incremental peak sales |
| M4 | Change pricing or coverage, cash-pay or MFN channel | No clinical event. Baseline moves with the LOE retention curve and the IRA/MFN step | IRA, MFN, GTN finding DeltaRevenue sets `baseline_delta_rev_annual`; LOE finding sets `loe_month` |
| M5 | Shift investment, LOE defense | Difference of two erosion paths (biologic 0.65/0.35/0.20, small molecule 0.30/0.15/0.10) | LOE or IRA finding sets `rev_at_risk_annual` |
| M6 | Launch a marketing campaign | Response elasticity 0.06 (range 0.05 to 0.30), promotion 10.8% of US sales | label or share-loss findings (fit only) |
| M7 | Build or reshore manufacturing | Capex $1B to $6.5B over 3 to 5 years, benefit weighted by P(tariff applies after 2029-01-20) | tariff finding sets `imported_cogs_annual` |

Each template is a cash-flow generator over the decision window plus a tail (horizon in months is a parameter). Every parameter has a default with a source in the `decide_weights` block of `moves.py`. A finding feeds a parameter automatically only when its `impact` carries a dollar value; otherwise the move lists the finding in `finding_ids` and it counts for strategic fit only.

## Kill signals (`kill.py`)

| Signal | Threshold | Source and lag | Check month | Effect |
|---|---|---|---|---|
| ZS breadth, return-writing, depth | < 30% / < 50% / < 30% | paid claims (IQVIA, Symphony) | 6 | Bayes on scenarios, P(breach given bear, base, bull) = 1.0, 0.55, 0.10 |
| Year-one net sales | < 80% of forecast | company 10-Q, ~40 days after quarter end | 12 | p_bear set to at least 0.70 |
| Commercial coverage | < 50% of lives | payer trackers (paid) or company commentary | 6 | Bayes, 1.0, 0.75, 0.50 |
| Medicaid units | < 80% of plan | Medicaid SDUD, 60 days plus posting lag | 9 | same as year-one |
| Self-pay share (DTC moves) | < 35% of new scripts | company disclosure | 6 | ZS likelihoods |
| Safety | FAERS serious reports +50% YoY and above rivals | FAERS quarterly, ~1 quarter lag | 3 | human review, no EV change |
| Trial enrollment | < 80% of plan | ClinicalTrials.gov | 6 | human review, no EV change |

Revised EV: p'_s = p_s L_s / sum(p_u L_u); EV' = sum p'_s x (PV of expected cash after the check month, sunk cost excluded); stop if EV' is below salvage less exit costs. With one ZS breach from (0.50, 0.11, 0.39) the posterior is (0.834, 0.101, 0.065), the spec's worked example. Medicare Part D PUF lags about 18 months, so it can confirm but never trigger inside the window.

## Benchmark versus company data

- Benchmarks (phase rates, trial cost, premiums, royalties, WACC, scenario weights, elasticities, plant capex, ZS thresholds) come from the research notes. Each becomes a `Citation` with `claim_type "number"`, the source URL as `source_url` and `deep_link`, verification status `unverified` and `confidence_note "external benchmark"`. They are not page-verified against a filing, and the gate sees that explicitly.
- Company numbers (Zepbound and Trulicity US revenue, cash and equivalents) carry a page citation to the 10-K or 10-Q, currently `unverified` until `agent.needle.cite.verify` runs against the index.
- Finding inputs carry the finding's own citations (`citations` in v2 rows, `evidence` in old rows).
- Team inputs (price delta, volume gain, uplift, channel cost) are labeled `assumption`, listed as flags in `decide.md`, and never presented as facts.

## Sample run (LLY, `docs/examples/moves_LLY.json`, old-shape findings)

| Move | EV | Cash at risk | Payback | Spread | MCDA |
|---|---|---|---|---|---|
| Seek new Zepbound indications (M3, outcomes trials) | 1,551.3 | 251.2 | month 73 | 751.1 | 0.532 |
| Defend Trulicity through LOE, switch to Mounjaro (M5) | 597.8 | 0.0 | month 9 | 520.6 | 0.571 |
| Expand LillyDirect cash-pay Zepbound channel (M4) | 233.8 | 22.9 | month 23 | 236.8 | 0.677 |

These are a pipeline demonstration, not a recommendation. The winner's EV rests on the assumption that closing the label gap adds 8% to Zepbound US revenue (peak 1,079), which the label finding does not yet quantify.

## Honest limits

- No product-level net price, channel build cost, or PBM formulary data is public; those are team inputs and flagged.
- Scenario weights are a launch-outcome base rate (Trinity) applied to every move, including ones that are not launches. The bear and bull multipliers are boundary values, so the spread is understated.
- Scenario weights (Trinity: any year-one miss) and multipliers (ZS: year-three boundaries) come from different bases, so the bear case is optimistic and EV leans up.
- Technical and commercial risk are treated as independent (inference). A 7.85% WACC is the team's choice, with no project hurdle above it; the research note says hurdles are commonly higher (DiMasi's 10.5% real). EV at 10.5% is not yet shown.
- The base-case kill likelihood (0.55) and the coverage likelihoods are inferences. Only the bear and bull ZS values are published.
- A kill signal that needs paid claims data cannot be checked from free sources; the free ones (SDUD, FAERS, 10-Q, ClinicalTrials.gov) lag 1 to 18 months.
- MCDA capability and stakeholder inputs are only as good as the facts the team documents; missing facts score 0.
- Findings with no dollar path in `impact` (all LLY old-shape rows) cannot feed a parameter; they only raise strategic fit.

## Deviations from the spec

1. The spec was untracked when DECIDE was built; it is now committed (quant-spec, v2.0).
2. `rank_moves` sorts by EV only. The feasibility gate and the MCDA tiebreak live in `select_move`, which returns the chosen move and the two rejected alternatives with a binding reason.
3. Several kill-signal breaches from one evidence family (the three ZS metrics, and self-pay share which reuses the ZS rule) count as one Bayes update, because they are one observation. The spec shows a single breach only.
4. Spec gives no base likelihood for commercial coverage: 0.75 (midpoint of 1.0 and 0.5), an inference. A year-one or SDUD miss sets p_bear to at least 0.70 and splits the rest over base and bull in proportion to their updated weights.
5. Kill check months are measured from launch or move start. ZS, coverage and year-one signals are not attached to trial-stage templates (M2, M3), whose launch is outside the first 24 months; those carry enrollment and safety only. `revise_ev` takes whatever signal ids it is given.
6. Cash at risk treats inflows received before the first readout as certain (P_alive = 1 before failure); a negative inflow (net price given up) increases cash at risk. With no trial the window is the full 24 months.
7. Strategic fit ignores findings of kind `gross_margin_peer_outlier` in the top-five denominator (spec D5: favorable level outlier, pi = 0), and uses the old engine's `score` as S until `findings_v2.jsonl` supplies `S`.
8. The sample findings file `docs/examples/findings_LLY_old.jsonl` is copied from the ui worktree because `out/LLY/findings.jsonl` does not exist on this branch.
9. The Trulicity exclusivity finding says protection ends 2026-09-18, while the case and the FY2025 10-K patent table say 2027. The sample move uses January 2027 (month 3 from 2026-10-17).
10. Effective tax rate 0.2049 (spec 10.1) is entered without a page quote and shows as an uncited-input flag. Trinity and several spec constants have no deep URL (Trinity cites its homepage); they stay `unverified`.
11. M1 and M2 defaults (equity value, peak sales, deal value) are placeholders to be replaced per target; M2's Phase III and approval probabilities default to the BIO metabolic row.
12. PyYAML is not installed in the venv, so the CLI reads JSON by default and YAML only if the package exists.
