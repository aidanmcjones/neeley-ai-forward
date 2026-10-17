# Quant model specification: FIND and DECIDE

Version 2.0, 2026-10-17. Branch quant-spec (docs only), written against the code committed on quant-model at ca12339 plus the changes landing in league_v3. Archive copy: `~/reports/Fine Print quant model design.md` (identical).
Readers: (a) the pitch writer, (b) judges, including a quant reviewer, (c) engineers.

Conventions:
- Every constant carries a source (paper and number, or our backtest and number) or the label **inference** (our derivation, stated). Every constant in the code has a row in Section 11, under its code name.
- Dollar figures are USD millions unless marked.
- **Status markers.** Text with no marker describes what the committed code does at ca12339. Text marked **[landing in league_v3]** describes a change being made on quant-model now; the code and this spec must agree once it lands. Numbers that depend on the v3 re-run are written `[v3: pending] (v2 X)`, where X is the committed league_v2 value.
- This document replaces the reviewed draft (spec_frozen.md, sha1 57f3effb). What changed and why, by review finding id, is in Section 14.

---

## 1. Purpose and what the case asks

The case ("The Fine Print: Find the Story, Then Make the Call") asks a team to:

- **Part 1, Find.** Pick one of ten pharma companies and explain why it beat the other nine; deliver at least five findings, each with a one-sentence finding, a source (filing and page, or speaker and exact quote), an impact estimate on revenue, operating income or EPS "with the math shown", a peer comparison, and a high/medium/low confidence "based on how solid the evidence is"; name the **Sharpest Needle**, "the single most material and least-discussed finding"; compare one product with its rivals and tie that to a financial finding.
- **Part 2, Decide.** Recommend one 24-month CEO move with a budget, the Part 1 findings that drive it, cost and return "with the math shown", the two strongest rejected alternatives, and early 6-to-12-month signals that would prove the move wrong.
- **Judging.** Seven equally weighted categories scored 1 to 4: Innovation, Technical Execution, Use of AI and Responsible Design, Completeness (including "limitations are stated clearly and honestly"), Design and Usability, Impact, Presentation. The rubric credits only what is demonstrated.

The case also states the constraint that drives this model: "Patent cliffs and exclusivity losses are public and priced in. The points go to signals a press-release skim would miss", and "AI tools invent page numbers, mix up figures from different years, and misquote executives."

So the model answers four quantitative questions on any pharma ticker:

1. How big is a finding relative to what the market usually gets wrong about this company? (materiality, M)
2. How likely is it that the market has not already priced it? (obscurity, O)
3. How sure are we that the documents say what we claim? (evidence, E)
4. How often does this kind of signal actually turn into the adverse outcome it implies? (prior, π)

Model 1 (**FIND**) multiplies those four. Model 2 (**DECIDE**) values candidate CEO moves on one 24-month cash scale whose inputs are FIND findings. A citation contract (Section 6) makes every number and quote in either model's output carry a footnote to its source page, and withholds any claim whose citation does not verify.

### The two equations

```
FIND    S_f = M_f · O_f · E_f · π_k(f)

        M_f = |ΔEPS_f| · (1 + r)^(-t_f) / σ_EPS
        O_f = D_f · τ_f
        D_f = (1 - z_f)(1 - h_f)(1 - a_f)(1 - c_f)(1 - s_f)      discussion term: has anyone priced it?
        τ_f = 2^(-age_f / H)                                     decay term: H = 3 months base, 6 as sensitivity
        E_f = min over key claims j of [ 1 - Π_{i in cites(j)} (1 - g_i) ]
        π_k = excess probability that signal family k is followed by its adverse outcome (Section 4.6)

        Sharpest Needle = argmax_f S_f  subject to  D_f ≥ 0.5, E_f ≥ 0.90, confidence ≠ LOW, z_f = 0
        League          L_c = ( Σ_{top 5} S_f ) · min(1, N_eff,c / 3)

DECIDE  EV_m = Σ_s p_s [ Σ_{τ=1..24} ( P_alive(τ)·CF^in_{m,s,τ} - P_reach(τ)·CF^out_{m,τ} ) / (1 + r_mo)^τ  +  TV_{m,s,24} / (1 + r_mo)^24 ]
```

The split of O into D and τ, the needle floor on D only and H = 3 are **[landing in league_v3]**. At ca12339 the code computes the same O as one product with H = 6 and puts the needle floor on the whole O (O ≥ 0.5). Exponents on M, O, E are 1 by design (Section 2, D3). One-slide legend in Section 12.

---

## 2. Design decisions

Each decision states what this spec does and why. Where it departs from the original brief it says so.

**D1. Two models, one data layer.** FIND scores findings; DECIDE consumes FIND output rows (by `id`) as inputs, so every DECIDE parameter that came from Part 1 is traceable to a cited finding (Section 5.2).

**D2. Multiplicative, not additive in levels.** The case defines a finding conjunctively: material AND not obvious AND provable. A product encodes AND: any factor at zero zeroes the score (an unverifiable claim, E = 0, can never rank; a starter-thread item, z = 1 so O = 0, can never be the Sharpest Needle). A levels-additive score is compensatory and would let a perfectly obscure but unverified claim outrank a verified one. Multiplicative and log-additive give the same ranking, so the real choice is "conjunctive versus compensatory". S has a reading: **expected EPS impact attributable to the finding, in units of the company's usual EPS surprise, times the probability it is unpriced, times the probability the documents say what we claim.** Because π is uncertain to about a factor of two (D6), the pitch shows S as a tier and ΔEPS in dollars, not S as a precise point value (Section 12).

**D3. Exponents α = β = γ = 1.** Not tuned, by design. (i) The expected-value reading of S holds only with unit exponents. (ii) Estimating three exponents needs labelled outcomes on hundreds of findings; we have about 120 live firm-quarters (10 companies x about 12 quarters) and 1,410 backtest firm-quarters that test only five accounting flags. That small N is the decisive argument. DeMiguel, Garlappi and Uppal (RFS 2009), who show sample-based portfolio weights need "about 3,000 months with 25 assets" to beat 1/N, and Gu, Kelly and Xiu (monthly out-of-sample R2 0.33-0.40%), support it by analogy only: they are about portfolio weights and return prediction, not finding scores.

**D4. Drop the old Z (peer z) and D (trend) multipliers and the constant T from S.** The old score `S = I_norm·P·T·O·E·(1+0.25 max(Z,0))·(1+0.25 D)` used 0.25 weights described in `docs/materiality_spec.md` as "a starting guess". Peer z moves to the peer column. T was a constant 0.926 for every finding, so it ranked nothing; timing now enters M as a discount to the fiscal year the impact lands in. Cost of this choice (review A20): statistical findings lose their only magnitude signal, because every anchor-routed row in one company has the same M. Section 4.3 a limits the anchor to backtested flags that fired, and Section 9 states the rest as a limit.

**D5. The old league lead was a scorer bug, fixed in commit 4009a40.** The old scorer's `score._impact` treated LLY's gross-margin **level** (85.8%) as a margin **change**, about $68B of "impact", capped at 1.0. That one row was 0.2437 of LLY's old 0.3034 (80.3%). It is also favourable to LLY. Under FIND it has no adverse scenario and π = 0. Two further rules from the review are in code:
- **A backtest π applies only when the row meets that flag's backtest trigger** (`find.backtest_fired`, `ANNUAL_TRIGGER`). A peer-level outlier that does not fire the flag got π_min in v2 and is "not quantified" in v3 (Section 4.3 a) (review A1).
- **A statistical row whose sign is good for EPS** (receivables or inventory growing slower than revenue, ETR falling, margin rising) goes to the favourable family with π = 0 (`find.favorable_statistical`).

**D6. π is an excess probability on a common outcome scale, derived four ways.** (1) Contractual or scheduled events: π = 1. (2) Our own backtest: fired-vs-not-fired hit rates for five accounting flags on gross-margin compression. (3) Literature return alphas converted to the same scale through one anchor, inventory growth, the one family with both a published hedge return (Thomas and Zhang 2002, 11.39%) and a backtest excess rate (+6.3 points). (4) Directional or no evidence: π_min or π_min / 2. The return-to-probability conversion in route 3 is an **inference** and the most likely point of challenge; its defence is that Lazy Prices returns accrue as information is later revealed through news or earnings (the priced-in note's paraphrase of Cohen, Malloy and Nguyen), which is what proportionality assumes. **π = 1 is reserved for statute-dated or booked amounts**: an IRA selection with a CMS effective date, a company-stated LOE date, a booked footnote amount. Label differences, MFN terms and business-reason trial stops are not scheduled amounts and do not get π = 1 as scored rows (review R3; Section 4.6).

**D7. Post-publication haircuts cancel inside the anchor ratio; the data-mining haircut does not.** McLean and Pontiff (JF 2016): "portfolios earned about 26% less out-of-sample and about 58% less post-publication". All return-based families we use are published, so the 58% applies to numerator and anchor alike and cancels in the ratio. Our backtest rules and results were produced in one commit (gate 2, disclosed), so every backtest excess rate is haircut by the 26% out-of-sample figure. We do not apply the 58% to fundamental outcomes: Dorey, Kim and Shin (2017) report that Abarbanell and Bushee's signals lost their hedge return after publication while their predictive power for earnings held (our paraphrase; the clause is not a quote).

**D8. Obscurity is a noisy-OR of independent "ways the market could already know", times a decay.** D = probability that none of the channels (starter thread, headline page, analyst questions, consensus, short sellers) has priced the finding; τ = decay in its age. Independence across channels is an **inference**; it makes D conservative when channels overlap.

**D9. Half-life H = 3 months base, 6 months as the sensitivity [landing in league_v3].** Lazy Prices: negative alpha "persists and increases up to 6 months out, never reversing" and accrues "out to 18 months"; the priced-in note puts filing-only information at "a half-life on the order of 3 to 6 months". v2 used H = 6. Both skeptics agreed that decay inside the needle floor made "least discussed" mean "recent" (review R1). The fix has two parts that land together: the needle floor moves to the discussion term D, so decay no longer decides needle eligibility, and H moves to 3, the lower end of the range, because decay now only ranks findings by S. H = 6 is reported as the sensitivity row. Age runs from the latest filing that states the fact (D1 in Section 5 of the review, our named default); age from the first public date is a sensitivity.

**D10. Confidence is deterministic; the LLM never sets it.** ICD 203 separates confidence (sourcing quality) from likelihood. Our label is a fixed function of E, independent-source count, claim kind and diagnosticity (`evidence.confidence`). The courtroom trial (`agent/needle/trial.py`) can only lower a label, never raise it. Reason: verbalized confidence clusters at 80-100% and has ECE 0.18 to 0.52 across models (Xiong et al. 2023); legal LLMs "systematically overestimate their confidence" (Dahl et al. 2024).

**D11. League score: one dominant evidence block counts as one finding.** L = sum of the top five S, times min(1, N_eff / 3), where N_eff is the inverse Herfindahl of S across evidence blocks. Said plainly: on these ten companies N_eff never reaches 3 (v2 maximum 2.19, AMGN), so the cap never binds and **L = top-5 sum x N_eff / 3** for every company. The term is a design choice, not a tested parameter, and it decides #1 in v2 (AMGN on L, GILD on the raw sum). The league output prints the raw top-5 sum beside L, and league_v3 ships a robustness table (Section 4.9, 10.5) so the pick is made only on what survives.

**D12. DECIDE values cash, not stories.** One 24-month scenario-weighted rNPV with explicit monthly cash flows and a terminal value at month 24, so a trial that reads out in month 30 is still valued, and the two rejected moves get the same five numbers as the winner. In-window value (months 1-24) and terminal value are reported separately. Scenario weights come from Trinity (2023 US launches: 50% under first-year forecast, 39% over); multipliers from the ZS success and failure boundaries (≥120% and ≤80% of forecast). These are two different bases (any year-one miss versus a year-three boundary), so the bear case is not conservative and EV is biased upward (review A22; Section 9).

**D13. One citation index, one verifier.** The scraper's `data/moat/index/citations.sqlite` (data-moat commit 704741d; 3,118 docs, 39,940 pages) is read through `agent/moat/cite.py` only. Its facts table holds 69,553 table facts, of which 10,963 carry `verify_status = verified` (review B20 corrected the earlier "69,553 verified facts"). The package `agent/needle/cite/` adds the Citation contract, the verification ladder, the gate, deep links and rendering on top of it (Section 6).

**D14. Where this spec departs from the original brief.** (i) T is folded into M (D4). (ii) Short-interest days-to-cover is specified inside D but the moat has no short-interest data, so s_f = 0 on every row with a flag. (iii) H is our inference from the Lazy Prices accrual horizon and the priced-in note (D9). (iv) MFN is scored as a direction, not a dollar amount (Section 4.3 c).

---

## 3. Data layer (shared by FIND and DECIDE)

The moat is gitignored. FIND reads it from env `NEEDLE_MOAT` (default: the gap-data worktree, `data/moat`) and the citation index from env `CITATIONS_DB` (else the repo copy, else the gap-data copy). Nothing is copied into the repo. Every row the models read carries `source` and `source_row`, and every page carries a `doc_id` and file page number, so every model input can be cited (Section 6).

| Input | Used for | Location | Missing-data rule (as coded) |
|---|---|---|---|
| XBRL quarterly panel (revenue, COGS, pretax income, income tax, diluted shares, inventory, receivables) | Rev_TTM, t, D, ratio flags | `agent/needle/xbrl.py` over `data/corpus/*/<T>/xbrl_companyfacts.json.gz` | 20-F filers (a `20f_*` or `40f_*` file in the corpus): latest fiscal year via `xbrl.annual()`, flagged |
| Page store and citation index | every quote, every number, deep links | `citations.sqlite` via `agent/moat/cite.py` and `agent/needle/cite/index.py` | no citation, no claim (gate) |
| I/B/E/S quarterly EPS consensus and actuals | σ_EPS | `tables/ibes_eps_quarterly.csv`, `ibes_actuals.csv`, joined on `oftic`. AZN's I/B/E/S ticker ZEN is a per-ADR history and is put on the per-share basis by `data.PER_SHARE = {"ZEN": 2.0}` (review A2). A gap of more than one quarter in the 8-quarter window is flagged | FY1 dispersion, then 0.041 x a proxy EPS; both marked "not league-comparable" (Section 4.2). No shortlist company uses a fallback |
| I/B/E/S FY consensus by `statpers` | consensus term c_f | `ibes_eps_consensus.csv` | untestable: c_f = 0.5 with a flag **[landing in league_v3]** (v2: 0) |
| Analyst topic attention | a_f | `verified/market/priced_in_scorecard.csv` (10 tickers x 9 topics), else a regex over analyst turns in `qa_turns.csv` (last up to 10 quarters) | scorecard median, flagged "imputed" |
| Latest earnings release, page 1 | h_f | citation index, `doc_type = earnings_release` | NVO and AZN have none in the index: h_f = shortlist median of h for the same topics, flagged (review B8) |
| Short interest | s_f | not collected | s_f = 0, flagged on every row |
| Policy exposure (IRA, MFN, tariff) | IRA, MFN, tariff | `verified/policy/policy_exposure.csv`, `force_summary.csv`, `ira_cut_check.csv`, CMS fact sheets in `policy_gov/cms/` | channel not scored |
| Pricing proxies (Part D, Part B ASP, NADAC, SDUD, list vs net) | product table, GTN band | `tables/partd_by_year.csv`, `partb_asp_quarterly.csv`, `verified/pricing/gtn_proxy.csv`, `company_list_vs_net.csv` | "no free net series" printed in the cell |
| Product revenue (XBRL product axis) | LOE size | `tables/product_revenue_quarterly.csv`, full-year rows (`days >= 360`), US geography when split | LOE row not quantified, flagged |
| Company-stated LOE dates | LOE date | `agent/cache/company_stated_loe.jsonl` (10-K patent tables), ahead of Orange/Purple Book dates from the detector | detector's regulatory date, flagged with its source |
| Label facts | product table | `data/corpus/drugs/<slug>/label_sections.md` (one page per label section in the index) | empty cell with a stated reason |
| Backtest hit rates | π for five accounting flags | `out/backtest/hit_rates.json` (summary only) | the raw panel (`data/backtest/xbrl/`) is not on disk in any worktree and has no fetch script (Section 8.2) |
| Detector candidates | candidate findings | `out/<T>/signals_<detector>.jsonl` (forensics, drift, calls, labels, supply) | detector yields nothing |
| Effective tax rate | t | TTM GAAP ETR from XBRL | outside [0, 0.40] (MRK 0.467, PFE -0.039, GILD -0.657 at ca12339): the shortlist median of in-range ETRs, 0.185, flagged. No guided non-GAAP rate is extracted |
| Kill-signal data (SDUD, FAERS, 10-Q product revenue) | DECIDE monitoring | `tables/medicaid_sdud.csv`, FAERS files, filings | listed with lag (Section 5.6) |

Point-in-time rule: every input carries an as-of date (filing `filed`, I/B/E/S `statpers`, transcript call date). `data.AS_OF = 2026-10-17`. The live XBRL panel uses SEC `frame` values (latest restated), which is not point-in-time; acceptable for live scoring, never for backtests.

Currency: NVO reports in DKK in both XBRL and I/B/E/S, so its M is unit-free. USD-denominated channels (IRA, MFN) on NVO are not converted because no FX rate is cited; their ΔEPS is set to 0 with a flag (review R4).

---

## 4. Model 1: FIND

Code: `agent/needle/quant/` (`find.py`, `impact.py`, `obscurity.py`, `evidence.py`, `league.py`, `weights.py`, `data.py`, `run.py`). Tests: `tests/needle/test_quant_find.py`. Output: `out/<T>/findings_v2.jsonl`, `out/<T>/rejected_v2.jsonl`, `out/league_v2.json` and `.md` (v3: `league_v3`).

### 4.1 Equation and what counts as a finding

```
S_f = M_f · O_f · E_f · π_k(f)            (find.score; S = 0 if any factor ≤ 0)
```

A finding f is one candidate row: a sentence, at least one page citation, a signal family k(f), an impact channel and a direction. Candidates come from the five existing detectors plus two generators the old engine lacked: IRA (one row per CMS-selected shortlist drug with IPAY 2027 or 2028, `find.IRA_DRUGS`) and MFN (one row per company with a Medicaid MFN term in `policy_exposure.csv`).

Rows enter the scored list only when E > 0; the others go to `rejected_v2.jsonl` with the reason. Before scoring, rows are de-duplicated by (kind, sentence, first source). **[landing in league_v3]** A second de-duplication by (ticker, period, underlying metric) removes one fact counted twice: in v2, AZN's rows 3 and 4 (`receivables_outpace_revenue` and `rec_gap_peer_outlier`, both +14.7 pts FY2025, S 0.0427 each) were the same receivables fact (review S1).

Only adverse rows and favourable rows with a quantified upside can have S > 0. A favourable level outlier with no scenario is context for the peer column, not a finding (π = 0).

### 4.2 Materiality M: impact over noise

```
M_f = |ΔEPS_f| · (1 + r)^(-t_f) / σ_EPS            (find.materiality)
```

- **ΔEPS_f**: base-case EPS impact in the single fiscal year of largest impact that overlaps the 24-month window from `as_of` (`HORIZON_MONTHS = 24`). Computed by the channel function (4.3) and the EPS translation below.
- **t_f**: years from `as_of` to 1 July of that fiscal year; 0.5 years for the anchor event (`ANCHOR_T_YEARS`).
- **r = 7.85%** (`R`): Damodaran, Drugs (Pharmaceutical), 228 firms, WACC as of January 2026.
- **σ_EPS**: the company's annual EPS surprise noise, "what the market usually misses by":

```
σ_EPS = 2 · sd( actual_q - consensus_mean_q ),   last 8 quarters    (data.sigma_eps)
```

`consensus_mean_q` is the I/B/E/S mean of the last `statpers` before the announcement; `actual_q` from `ibes_actuals.csv`. The factor 2 = √4 annualizes four quarterly surprises assuming independence (`SIGMA_ANNUALIZE`, **inference**). Standard deviation (not root-mean-square) is used so a habitual beat, which the market learns, does not count as noise. Two known weaknesses, stated as limits (review A3): the 2x is unsourced, and σ is a near-term surprise scale while many impacts land one to two years out.

Fallbacks as coded, each marking the company "not league-comparable":
1. Latest FY1 forecast dispersion `stdev` (Diether, Malloy, Scherbina 2002). Dispersion is 1.2x to 7.5x smaller than surprise noise on the ten (review A3), which is why it is not comparable.
2. `SIGMA_FY1_RATIO` 0.041 x |Rev_TTM x 0.2 / D|, that is, the ratio applied to a proxy EPS at an assumed 20% net margin (**inference**). The 0.041 median was computed on the reviewed draft's table, which carried AZN on the per-ADR basis; the review recomputes 5.2% (3.9% excluding MRK). The constant is kept as printed because no shortlist company uses this fallback.

Reference values (local I/B/E/S as of statpers 2026-08-20; AZN on the per-share basis):

| Ticker | σ_EPS (annual) | FY1 mean | Note |
|---|---|---|---|
| ABBV | 0.5227 | 14.02 | |
| AMGN | 0.3452 | 23.02 | |
| AZN | 0.5408 | 10.31 | ZEN per-ADR history x 2.0 (`PER_SHARE`); window-gap flag |
| BMY | 0.4778 | 6.88 | |
| GILD | 0.4031 | -0.44 | FY1 distorted by one-time charges; σ from surprises unaffected |
| JNJ | 0.1457 | 11.58 | |
| LLY | 2.0295 | 36.45 | 2 x sd 1.01474 of the eight surprises in 10.1 |
| MRK | 0.2554 | 2.75 | |
| NVO | 0.6160 | 22.42 | DKK, matched to DKK XBRL |
| PFE | 0.2509 | 2.98 | |

LLY's σ is 3 to 14 times its peers', so LLY findings shrink relative to peers; JNJ (0.146) and AMGN (0.345) are rewarded. This is the intended reading ("relative to what the market usually misses on this company"), and it is a company-level scale: it never reorders findings within a company.

**EPS translation (every channel ends here):**

```
ΔEPS = ΔRev · CM · (1 - t) / D            ΔOI = ΔRev · CM            (impact.eps)
```

| Parameter | Value | Source |
|---|---|---|
| CM, price, rebate, MFP or MFN change (`CM_PRICE`) | 1.00 | pharma_impact_math KQ7 inference: "CM = 0.70 for volume, 1.00 for price"; Drug Channels |
| CM, volume change (`CM_VOLUME`) | 0.70 | same. Note (review A16): the same note's takeaway gives 75% for price, 65% for volume and 100% for rebate or MFP changes when product margin is undisclosed. We use 1.00 / 0.70; the 0.75 / 0.65 alternative is a sensitivity row not yet run |
| t | TTM GAAP ETR = Σ income tax / Σ pretax income over the last 4 quarters (XBRL); outside [0, 0.40] replaced by the shortlist median of in-range ETRs (0.185), flagged | our rule; no guided rate is extracted yet |
| D | latest quarter's weighted-average diluted shares (20-F filers: ifrs-full `AdjustedWeightedAverageShares`) | pharma_impact_math KQ7: "do not use a static table" |

Sanity check from the note: "$1B net revenue loss at CM 0.70, t 0.16, S 1.77B shares = $0.33 EPS" (reproduces: 1,000 x 0.70 x 0.84 / 1,770 = 0.332).

### 4.3 Impact-math channels

Each finding maps to exactly one channel (`impact.py`). Bull is the scenario least harmful to the company, bear the most harmful.

**(a) Anchor event: only for backtested accounting flags that fired.** The backtest outcome that calibrates π is gross margin over the next four quarters down at least 3 points versus the trailing four (`backtest.py` `margin_drop`):

```
ΔEPS_anchor = 0.03 · Rev_TTM · (1 - t) / D,   t_f = 0.5 years            (impact.anchor; ANCHOR = 0.03)
```

0.03 is the event threshold, so this is a lower bound on the event's size (**inference**). Because π for these families is an excess probability of exactly this event, M x π is the expected EPS loss the flag reveals. The size is the same for every flag in a company: strength of the flag changes only whether it counts, not how much (review D3, stated as a limit).

Who may use the anchor:
- **v2 (ca12339).** Every statistical row: the five backtested families, drift (risk-factor, MD&A, litigation-language) rows, call rows, directional and no-evidence rows. Drift and call rows carried it as a flagged generic placeholder with E capped at 0.745 (`G_ENTAILED`), so they could not be HIGH. Backtest-family rows that did not fire the flag took π_min.
- **[landing in league_v3]** Only rows in the five backtested families **whose backtest flag fired** use the anchor. Every other statistical row (drift, calls, directional, no evidence, and backtest-family rows that did not fire) is **"not quantified"**: M = 0, no dollar figure, its π tier shown, and it cannot enter the top-5 table or the league sum. Where a topic maps to a real channel (IRA, MFN, LOE), that channel's generator carries the dollars instead (review R2).

**(b) IRA negotiation (Medicare MFP): the one IRA formula.** This is the formula FIND, the product table (4.11) and DECIDE (5.2) all use **[landing in league_v3: product.py and DECIDE import it; FIND already uses it]**:

```
ΔRev_IPAY = G_Medicare · d · k          CM = 1.00, step on 1 January of the IPAY year        (find.ira_findings -> impact.ira with k_factor)

k = (1.0, 1.0, 1.0)       low-rebate classes: oncology and HIV (LOW_REBATE = Verzenio, Erleada, Pomalyst, Ibrance, Calquence, Biktarvy)
k = (0.3, 0.4, 0.5)       highly rebated classes, bull / base / bear (K_NET)
```

- **G_Medicare**: CMS gross Medicare Part B+D spend for the selected drug from the CMS selected-drug fact sheet (IPAY 2027 or IPAY 2028), verified on its page, held flat (**inference**).
- **d**: the MFP's list-price discount. Published (IPAY 2027): the CMS figure, page-cited (Pomalyst 60%, Ibrance 50%, Calquence 40%, Linzess 75%, Vraylar 44%, Otezla 65%, Janumet 85%, semaglutide 71%). Not yet published (IPAY 2028): bull / base / bear = the smallest / same-class / largest published discount in the class: oncology `ONC_D_*` 0.38 / 0.50 / 0.60 (Imbruvica, Ibrance, Pomalyst); immunology `IMM` 0.65 / 0.66 / 0.67 (Otezla, Stelara, Enbrel); diabetes `DIAB` 0.66 / 0.71 / 0.85 (Jardiance, Ozempic, Janumet). With no same-class analog (Biktarvy, Botox): `ALL_CUTS` 0.38 / 0.655 / 0.85, the cycle 1-2 smallest, median of the 16 in `ira_cut_check.csv`, and largest.
- **k**: the KQ2 cross-check, now the rule: cycle 1 CMS net savings were 22% against list discounts of 38-79%, i.e. "net hit ~= 0.3-0.5 x list discount for highly rebated classes, and near 1.0x for low-rebate oncology" (pharma_impact_math KQ2, marked inference there). HIV is treated as low-rebate (**inference**; no HIV MFP is published).
- **Timing.** IPAY 2026 drugs are already effective before `as_of`: ΔEPS = 0, flagged ("already in reported numbers"). An effective date outside the 24-month window: ΔEPS = 0.
- **Not added:** the bear-case commercial spillover of 0-5% of commercial net revenue (inference in the note). Not calibrated: k is not fitted to reproduce the CMS 22% cycle-1 net savings (stated as a limit).
- **Comparison field only.** Each IRA row also carries the reviewed draft's formula, ΔRev = G · max(0, d - g_pre), as `dRev_spec_formula`, `M_spec_formula` and `S_spec_formula` (g_pre = `M_MDP_CATASTROPHIC` 0.20 for low-rebate classes; `G_PRE_GLP1` and `G_PRE_IMMUNOLOGY` priors for rebated classes; where no g_pre prior exists, Botox, Linzess and Vraylar, the comparison field equals the league value). It is never the league value. Reason (review A15): the draft formula gives a net hit of 0.6x the list discount for oncology, not the "near 1.0x" its own cross-check states, and near zero for rebated classes because company-wide GTN is not a Part D concession rate. Example: Verzenio S 0.0507 under the rule, 0.0304 under the comparison formula (v2, H = 6).
- **Biktarvy band.** GILD's v2 L is 92% one Biktarvy row (S 1.078). Its d is the all-cycle band 38 / 65.5 / 85%, at k = 1.0. The league_v3 robustness table shows GILD with Biktarvy on the comparison formula (d - 0.20).

**(c) MFN (Medicaid): direction only, at π_min [landing in league_v3].**

At ca12339 the MFN generator scores every company with a Medicaid MFN term at one universal rate, ΔRev = s_MFN · Rev_US (s_MFN 0.0065, Pfizer's Medicaid base rate, `S_MFN`), with π = 1, and prints "about $X M a year" in the sentence. Both skeptics rejected this: deal texts are confidential, one rate is applied to everyone, and Medicaid MFN has been effective since 2026, so part of it may already be in reported numbers. In v2 it was JNJ's #1 row (71% of its L) and AMGN's #2.

The v3 rule:
- An MFN row is **directional**: π = π_min (0.0055), and the sentence states the agreement, its date and the direction of the effect with no dollar figure.
- The base-rate size Rev_TTM x US share x s_MFN stays inside the row only as the internal M used to rank it; it is never printed as an estimate.
- A dollar figure is printed only where the company itself states a quantified MFN effect, cited to its own page. Two candidates exist (NVO's stated effect on sales growth; BMY's Eliquis free to Medicaid, computable from SDUD). Neither is built: NVO's term is in DKK and growth terms and is zeroed by the USD-only rule, and the SDUD computation for BMY is not coded. So in v3 every MFN row is direction-only.
- TrumpRx cash prices are neutral in FIND (base 0), because "the TrumpRx price usually sits at or above the manufacturer's existing net" (KQ3 inference). The product table (4.11) shows a cash-price scenario separately and labels it an assumption.

**(d) Tariff (Section 232): exposure proxy, never scored.** MFN signers pay no duty "until January 20, 2029" (Proclamation 11020, `policy_exposure.csv` R062), outside the 24-month window. FIND reports `tariff_exposure` = pct_mfg_sites_outside_us x us_revenue_share (`force_summary.csv`) with the 2029-01-20 date, in the league output and the row flags. For DECIDE's onshoring move only:

```
ΔCOGS_after_2029 = COGS_imported_patented · τ_rate,   τ_rate ∈ {0.15 (EU, Japan, Korea, Switzerland cap), 0.20 (onshoring plan), 1.00}   (impact.tariff_note)
```

Tariff applies to imported cost, not sales (KQ3).

**(e) Loss of exclusivity.** π = 1 only because the date is company-stated or statutory.

```
ΔRev_y = Rev_pre · (1 - R(y)) · frac_y,   CM = 1.00 biologic (price-led), 0.70 small molecule (volume-led)        (impact.loe)
R(y) years 1/2/3: biologic 0.65 / 0.35 / 0.20 (R_BIOLOGIC); small molecule 0.30 / 0.15 / 0.10 (R_SMALL_MOLECULE)
bull / bear = 0.8 / 1.2 x base (inline in impact.loe; inference)
```

- The scored year is the fiscal year of largest in-window impact; year 1 is pro-rated for the part of the year after the LOE date (frac_y).
- Dates: company-stated LOE (10-K patent table, `company_stated_loe.jsonl`) ahead of the detector's Orange/Purple Book date, with the source in the flags. LOE outside the window gives ΔEPS = 0 (Darzalex 2029, Repatha 2029).
- LOE rows whose disclosure date is unknown use age 24 months (`LOE_AGE_MONTHS_DEFAULT`, **inference**: patent dates are long public).
- A starter-thread LOE (e.g. "Trulicity loses exclusivity in 2027" for LLY) gets z = 1, so O = 0.
- Sources: pharma_impact_math KQ4 (Humira US -35% year 1, -38% global year 2, -57% US year 3; Stelara US -43% year 1; IQVIA "traditional 90% erosion"). Cross-check: the team's `loe_curves.json` medians (biologic 78.8, 71.6, 33.6% of peak at t = 0..2, n = 4, 3, 2; small molecule 64.8, 16.1, 17.1%, n = 14, 12, 8). LOE inputs are thin for NVO, AZN, ABBV and JNJ (review B14).

**(f) Gross-to-net.** No GTN detector exists (`find.MISSING_DETECTORS`), so FIND scores no GTN row. The formula is kept for the product table and DECIDE:

```
ΔRev = -Rev_gross · ΔGTN,   Rev_gross = Rev_net / (1 - GTN),   CM = 1.00        (impact.gtn)
```

**(g) Inventory and receivables.** Backtested statistical families scored on the anchor (a) when the flag fires. The row also shows the exposure, which is not the scored impact:

```
excess_X = X_t - X_{t-4} · (1 + g_rev),   X ∈ {inventory, receivables}
DIO = inventory / COGS_q · 91.25;  DSO = receivables / Rev_q · 91.25   (annual filers: 365 and FY figures)
```

Mandatory diagnostics before a row can be HIGH:
- **Inventory stage split** (`find.stage_split`): finished-goods share from the inventory note on the cited filing. Share below 0.5, or no stage split found, makes the row non-diagnostic; below 0.5 also adds the flag "capacity build, not channel stuffing" (KQ5: "Lilly/Novo inventory growth is capacity build ... split inventory by stage before flagging"). The 0.5 cut-off is ours (**inference**).
- **Receivables and DSO:** the channel-stuffing test needs a change in wholesaler-inventory language, which is not automated, so every receivables and DSO row fails the diagnostic and cannot be HIGH. The reversal channel (`impact.dso_reversal`: DSO excess above `DSO_STAR` 7 days x daily revenue, BMS 2000-2001 base rate) is coded but not wired into the run.

**(h) Label breadth and product fine print.** Static label differences (indication count, an existing boxed warning, dosing, REMS, Part D spend per claim) have no in-window change and no new-start or TAM inputs in the data. Their M is 0 (`impact.label_unquantified`) and they are context for the product table (4.11), not scored findings (review B6). Only a dated label change could become a scored finding, and no dated-label-change detector exists. The elasticities below are coded (`impact.boxed_warning_added`, `rems_vs_rival`, `dosing`) for the product table and DECIDE, and are the research note's inferences, not the cited papers' own numbers (review A26):

| Label fact | ΔRev | Basis |
|---|---|---|
| Boxed warning added (`BOXED_WARNING`) | -10% to -25% of US volume over 12-18 months, near 0 if class-wide; CM 0.70 | inference from pediatric antidepressants (Mayo Clin Proc) and levofloxacin (PMC8159769) |
| REMS with ETASU vs non-REMS rival (`REMS`) | -5% to -15% of new starts | KQ6 inference (no published elasticity) |
| Once-weekly vs daily dosing (`WEEKLY_VS_DAILY`) | +10% to +15% revenue per starter over two years | inference from persistence HR 0.80 (95% CI 0.71-0.90) (Diabetes Therapy 2021) |

**(i) Footnote items and trial stops.** No footnote extractor exists. Booked impairments use the "accrued: already in reported numbers" rule (ΔEPS = 0). Business-reason trial terminations get ΔEPS = 0 (pipeline asset, no in-window revenue); trial terminations without a business reason are not scored. `impact.footnote` codes the remaining items for when an extractor exists: contingent consideration (change in disclosed fair value), royalty change, reasonably-possible litigation (midpoint of the disclosed range at π 0.5), guided tax-rate change.

### 4.4 Obscurity O: the discussion term and the decay term

```
O_f = D_f · τ_f
D_f = (1 - z_f)(1 - h_f)(1 - a_f)(1 - c_f)(1 - s_f)        discussion: the probability no channel has priced it
τ_f = 2^(-age_f / H)                                        decay
```

At ca12339, `obscurity.obscurity` computes the same product in one expression with H = 6. **[landing in league_v3]** D and τ are separated so the needle floor (4.8) applies to D only, and H = 3.

| Term | Rule as coded | Source |
|---|---|---|
| z_f | 1 if the finding restates the company's case-appendix starter thread: a fixed per-company list of (product regex, topic set) in `obscurity.STARTER` (e.g. LLY: Mounjaro or Zepbound with pricing, GTN or MFN topics; any pill; Trulicity with LOE). GILD has none | case: "Restating it will not score well" |
| h_f | 0.9 (`H_VALUE`) if any topic regex of the finding matches page 1 of the latest earnings release; 0 otherwise. No release in the index (NVO, AZN): the shortlist median of h for the same topics, flagged | case: "a press-release skim would miss"; 0.9 is the team rule from materiality_spec §3, not literature |
| a_f | share of the last up-to-10 quarters (`ATTENTION_QUARTERS`) in which analysts asked about the topic: the scorecard for its nine topics; a regex over analyst turns in `qa_turns.csv` for other topics; the product name for product rows; the most-asked of the finding's topics wins. No measurable topic: scorecard median, flagged "imputed" | Hong, Lim, Stein 2000; Chen, Nagar, Schoenfeld 2018 |
| c_f | type C rows only: clip(Δcons_dir / abs(ΔEPS_f), 0, 1), where Δcons_dir is the change in the affected fiscal year's I/B/E/S mean EPS from the last `statpers` before to the first after the disclosure, signed in the finding's direction; flagged "confounded" when earnings were announced between the two. When the fiscal year's consensus first appears after the disclosure ("untestable"): **c_f = 0.5 with a flag [landing in league_v3]** (v2: 0, the most optimistic value; review A12). Families with no consensus line item (accounting, text, call rows): c_f = 0, flagged "n/a" | inference: no published test exists (priced_in KQ3 "Gaps") |
| s_f | 0 on every row, flagged "no data". The specified form max(0, 2·(pct_rank(days-to-cover in its own 24-month history) - 0.5)) is not implemented | Hong et al. 2015 (DTC); not collected |
| age_f | months from the latest cited document's `filed` date to `as_of` (our named default: age runs from the latest filing that states the fact). Transcripts with no date: quarter end plus about 30 days. Unknown: 24 months | review D1 |
| H | **3 months base [landing in league_v3]**, 6 months as the sensitivity (v2: 6) | D9 |

Interpretation: each factor of D is the probability one channel has not priced the fact; channels are assumed independent (D8). A finding the company headlined, or that analysts ask about every quarter, cannot be the Sharpest Needle however large it is. Because c_f = 0.5 on an untestable type C row, such a row has D at most 0.5 and clears the needle floor only when h = a = s = 0 (stated so the pick is not a surprise).

### 4.5 Evidence E: probability the documents say what we claim

```
E_f = min over key claims j of [ 1 - Π_{i in cites(j)} (1 - g_i) ]        (evidence.evidence_score)
```

A key claim is a page citation the finding's sentence depends on. E is computed from those page citations only; the citations behind the impact constants (XBRL Rev_TTM, t, D, I/B/E/S rows) are attached to the row but do not enter E, so a derived noise denominator never withholds a finding. Within one claim, independent citations combine by noisy-OR (**inference**: independence); citations of the same document count once.

The grade g comes from the citation package's verification status (Section 6.3):

| Status (`cite.verify`) | g (`evidence.GRADE`) | Basis |
|---|---|---|
| `exact` (byte substring of the cited page) | 1.00 (`G_EXACT`) | deterministic; seeded errors caught in `tests/needle/test_trust.py` |
| `substring` (equal after normalization: NFKC, quotes, dashes, case, whitespace) | 1.00 | deterministic |
| `fuzzy` (rapidfuzz partial_ratio ≥ 90 and every numeral in the quote present in the matched span) | 0.90 (`G_FUZZY`) | inference (citation note KQ4) |
| `number_match` (number claim: the value is on the cited page but the quote did not verify) | 0.745 (`G_ENTAILED`) | one rung below fuzzy. 0.745 is Liu et al. 2023's share of generative-engine citations that support their sentence, borrowed as a rung value, not a measured precision (review A26) |
| `unverified` | 0 (`G_NONE`) | the claim is withheld by the gate |

Table and XBRL values re-read by code at run time count as `exact` (XBRL values are cited as companyfacts concept plus frame; licensed WRDS rows carry `license = wrds_licensed`). `G_LLM` (0.85, FinanceBench oracle-page answer accuracy, Islam et al. 2023) is defined for LLM-derived arithmetic; no run path uses it today.

### 4.6 Prior π_k: how often the signal family turns into its adverse outcome

π_k is the **excess probability** that the adverse outcome assumed by the finding's channel occurs, over the base rate without the signal (`find.FAM`, constants in `weights.py`). Four routes, in this order:

1. **Type C, statute-dated or booked** (IRA selection with a CMS effective date, company-stated or statutory LOE date, booked footnote amount): π = 1 (`PI_CONTRACTUAL`). The event is not a forecast; uncertainty is in the size (bull / base / bear ΔEPS). Label rows, trial stops and booked impairments keep the type C family name in code but have M = 0, so they never score. MFN is not type C in v3 (route 4).
2. **Own backtest** (five accounting flags, 1,410 firm-quarters, 43 firms, 2012-2024, point-in-time), applied **only when the row meets the flag's backtest trigger** (`find.backtest_fired`): quarterly rows re-evaluate `backtest.signals_at` on the XBRL panel at the row's quarter; annual rows compare the row's own value with `ANNUAL_TRIGGER` (inventory gap 0.10, receivables gap 0.08, DIO growth 0.15, DSO growth 0.10; gross-margin drop 2 points). Peer-level DIO and DSO outliers never fire.

```
π_k = (h_fired - h_not) · (1 - 0.26)            (weights.backtest_pi; DELTA_OOS = 0.26)
```

   on the `margin_drop` outcome, haircut by McLean-Pontiff's 26% (D7). For `gross_margin_drop` the smaller of the margin and hard-event excess rates (gate 2 found margin-to-margin is partly persistence of one series).

3. **Literature return evidence, converted through the anchor** (D6):

```
π_k = π_anchor · [ α_k (1 - d_k) ] / [ α_TZ (1 - d_TZ) ]        (weights.anchor_pi)
π_anchor = π_inventory = 0.0466,  α_TZ = 11.39%,  d_k = d_TZ = 0.58 (cancels)
```

4. **Directional or no evidence.** Published direction but no usable magnitude: π_min = 0.0055 (`PI_MIN`). No published evidence: π_none = 0.0028 (`PI_NONE`, π_min / 2 rounded up, the forensic note's tier halving).

**π tiers for display.** π is uncertain to about a factor of two (horizons and sidedness differ across the converted studies, review A4), so the pitch shows the tier, not four decimals: **Scheduled** (1.0); **Tested flag** (0.03 to 0.09, backtest); **Published return evidence** (0.006 to 0.05); **Direction only** (0.0055); **No evidence** (0.0028).

| Family k | Block | Engine kinds | Route | Input | π_k | Diagnostic | Built |
|---|---|---|---|---|---|---|---|
| Inventory outpaces revenue | A | `inventory_outpaces_revenue`, `inv_gap_peer_outlier` | backtest, if fired | margin_drop 20.6% vs 14.3%, lift 1.44, CI [1.08, 1.90] | 0.0466 | yes | yes |
| Days inventory | A | `dio_rising`, `dio_peer_outlier` | backtest, if fired | 21.7% vs 17.4%, lift 1.25, CI [0.88, 1.71] | 0.0318 | no | yes |
| Receivables outpace revenue | A | `receivables_outpace_revenue`, `rec_gap_peer_outlier` | backtest, if fired | 22.8% vs 14.3%, lift 1.60, CI [1.00, 2.33] | 0.0629 | no | yes |
| Days sales outstanding | A | `dso_rising`, `dso_peer_outlier` | backtest, if fired | 25.6% vs 14.1%, lift 1.81, CI [1.17, 2.60] | 0.0851 | yes | yes |
| Gross margin drop | A | `gross_margin_drop` | backtest, min of outcomes | margin 28.5% vs 16.3%; hard 28.1% vs 22.4%; min excess 0.057 | 0.0422 | no | yes |
| Backtest family, flag not fired | A | as above | v2: π_min; **v3: not quantified** | review A1, D5 | 0.0055 | no | yes |
| Misstatement score (Beneish M, Dechow F) | A | none | anchor | Beneish-Lee-Nichols "just below 1% a month", taken as 12%/yr (inference) | 0.0491 | yes | **no** |
| Risk-factor change | T | `risk_*` | anchor; **v3: not quantified, tier shown** | Lazy Prices VW Q5-Q1 5-factor alpha 0.46%/month (t = 3.44) x 12 = 5.52% | 0.0226 | yes | yes |
| Litigation-language change | T | drift row with "litigation" among its topics | anchor; **v3: not quantified, tier shown** | Lazy Prices 71 bps/month (t = 3.29) x 12 = 8.52% | 0.0349 | yes | yes |
| MD&A change | T | `mdna_*` | anchor; **v3: not quantified, tier shown** | Lazy Prices Table VII 11-22 bps/month, midpoint x 12 = 1.98% | 0.0081 | no | yes |
| Opportunistic insider sales | G | none | anchor | Cohen-Malloy-Pomorski 82 bps/month x 6 = 4.92% | 0.0201 | yes | **no** |
| Negative 8-K item | T | none | anchor | Lerman-Livnat lower end 1.5% | 0.0061 | no | **no** |
| Zero- or few-question call | C | none | anchor | Chen-Hollander-Law (WP) 1.34% over five days | 0.0055 | no | **no** |
| Non-answer / deflection | C | `qa_deflection` | directional; **v3: not quantified** | Gow-Larcker-Zakolyukina 2021 (11% base rate) | 0.0055 | no | yes |
| **MFN agreement** | P | `mfn_medicaid` (generator) | **v3: directional** (v2: type C, π = 1) | deal terms confidential (review R3, D2) | 0.0055 | no | yes |
| No evidence: repeated deflection, topic surge, ETR or R&D shift or level outlier, FAERS rise, demand divergence, distributor commentary | C, A, X | `qa_repeated_deflection`, `call_topic_surge`, `tax_rate_shift`, `etr_peer_outlier`, `rnd_shift`, `rnd_pct_peer_outlier`, `faers_serious_rising`, `demand_divergence`, `distributor_commentary` | none; **v3: not quantified** | no study found | 0.0028 | no | yes |
| IRA negotiation | P | `ira_selected` (generator); `ira_exposed` rows for drugs not in `IRA_DRUGS` are already effective (ΔEPS 0) | type C | CMS effective date | 1.0 | yes | yes |
| Loss of exclusivity | P | `exclusivity_earlier` | type C | company-stated or statutory date | 1.0 | yes | yes |
| Label fact | L | `label_*`, `boxed_warning_*`, `dosing_*`, `spend_per_claim_gap` | M = 0, product-table context | review B6 | (1.0, unused) | n/a | yes |
| Booked footnote item, business-reason trial stop | F | `impairment`, `trial_terminated` with business reason | M = 0 | already in reported numbers / no in-window revenue | (1.0, unused) | n/a | partial (no footnote extractor) |
| Reasonably-possible litigation | F | none | type C, half | ASC 450 midpoint (inference) | 0.5 | no | **no** |
| Favourable row with no scenario | A | `gross_margin_peer_outlier` above the peer median; any statistical row with a good sign | none | | 0 | n/a | yes |

Notes for the quant reviewer:
- **Families with no detector** are listed in `find.MISSING_DETECTORS` (misstatement score, insider sales, negative 8-K items, zero-question calls, GTN widening, footnote extractor) and every row carries `has_detector`. The design covers more than the build (review B3).
- **Litigation and text-table choice (review A5, open).** In code the litigation π applies whenever "litigation" is any one of a drift row's topics, and the risk-factor π uses the whole-document Lazy Prices result while MD&A uses the section-level Table VII. In v3 these rows are not quantified, so the choice changes only the tier label shown, not any S.
- The backtest tests only five flags with the engine's own thresholds, between firms. If the raw panel is re-fetched, π for these five rows and π_anchor update mechanically (Section 8.2).
- π is small for statistical families and 1 for scheduled ones. That is correct: a scheduled event and a 3-in-100 excess chance are different things. Scheduled items are then disciplined by O (they are usually public) and by the starter-thread rule.

### 4.7 Confidence (high, medium, low): deterministic, ICD 203 style

Two axes are kept apart: **confidence** (sourcing) is the label below; **likelihood** of the impact is π and the bull / base / bear range, shown separately.

```
HIGH    E_f ≥ 0.95 (E_HIGH)
        AND ( n_ind ≥ 2  OR  the key quantity is quoted verbatim (exact or substring) from an official primary source
              (SEC annual or quarterly report, CMS fact sheet or MFP explanation, FDA label) on a type C row )
        AND no key claim is a placeholder (v2: drift and call rows on the generic anchor)
        AND the family is diagnostic
        AND the row's mandatory diagnostics pass (inventory stage split; receivables test)
MEDIUM  E_f ≥ 0.745 (E_MED)
LOW     otherwise; also any row the courtroom trial rules "fails"
```

- n_ind counts different document families among verified page citations (company filing, transcript, government agency, FDA label); XBRL and table citations do not count (`evidence.n_independent`).
- 0.95 sits between the fuzzy (0.90) and exact (1.00) grades, so HIGH needs exact quotes or two corroborating fuzzy ones (1 - 0.1² = 0.99). 0.745 is the number_match grade, so MEDIUM admits a single number found on its page.
- No contradiction detector exists; the `contradicted` input is always false today.
- **LLM role.** Veto only: if the courtroom trial (`agent/needle/trial.py`: prosecutor, CFO defense, judge; every quote page-verified) rules a finding "fails", the label drops to LOW and the row cannot be the Sharpest Needle (`evidence.confidence(trial_fails=True)`). The FIND run does not call the trial; it runs in the LLM pass (Section 6.6, `docs/ai_in_the_build.md`). The LLM can lower a label, never raise one. No LLM tie-breaker is used.

### 4.8 Sharpest Needle

```
Needle = argmax_f S_f   subject to   D_f ≥ 0.5 (NEEDLE_O),  E_f ≥ 0.90 (NEEDLE_E),  confidence ≠ LOW,  z_f = 0,  adverse or quantified,  S_f > 0
```

- D ≥ 0.5: "more likely unpriced than priced" by the discussion channels, 0.5 being the midpoint of ICD 203's "roughly even chance" band (45-55%). **[landing in league_v3]** the floor is on D. In v2 it was on O = D · τ, so with a 6-month half-life every February 10-K item decayed below the floor and "least discussed" meant "recent" (review R1).
- E ≥ 0.90: quoted (exact, substring or fuzzy) evidence only; a number found on its page without the quote verifying (0.745) cannot headline.

**Fallbacks, as coded (`league.sharpest_needle`), each labelled in the output:**
1. **strict**: the rule above.
2. **provisional**: if no row passes, the highest S among rows with z = 0, S > 0, confidence not LOW and O at or above the company's median O.
3. **floor relaxed**: if that pool is empty, the highest S among rows with z = 0, S > 0 and O at or above the company's top-quartile O (no confidence condition).
4. **none**: "no finding clears the obscurity floor".

v2: 5 of 10 companies had no strict needle (GILD, AZN, ABBV, BMY, NVO). v3: [v3: pending] (v2 5 of 10). The app and deck print the status word next to every needle.

### 4.9 League score: why this company beat the other nine

```
L_c = ( Σ_{f in top5(c)} S_f ) · min(1, N_eff,c / N*)        N* = 3 (N_STAR)        (league.league_score)
N_eff,c = ( Σ_b S_b )² / Σ_b S_b²,   S_b = Σ_{f in top5, block b} S_f
```

Blocks b: A accounting, T text and disclosure, C calls, G governance and insiders, P policy and scheduled (IRA, MFN, LOE), L label and product, X outside data, F footnote items.

- **What the term does on these data.** N_eff never reaches 3 (v2 maximum 2.19), so min(1, ·) never binds and L = top-5 sum x N_eff / 3 for every company. It is a scaling by diversification, not a penalty with a threshold. N* is inert: ranks are identical for any N* at or above the largest N_eff (review A18).
- **Why keep it.** It encodes one stated design choice: one dominant evidence block counts as one finding, so a company whose case rests on one row does not outrank one with several independent pieces. The cost is that it decides #1 in v2 (AMGN 0.543 on L; GILD 1.166 vs AMGN 0.745 on the raw sum).
- **Required output.** For each company: L, the raw top-5 sum, N_eff, blocks, the share of the sum from its largest finding, the top-5 table and the Sharpest Needle with its status. All are in `league_v2.json` (`L`, `top5_sum`, `N_eff`, `blocks`, `largest_share`, `top`, `needle`, `needle_status`).
- **Robustness table [landing in league_v3].** `league_v3.md` publishes the top five companies under: as computed; no N_eff term (raw top-5 sum); IRA rows at π 0.5; Biktarvy on the comparison formula; AMGN's receivables row (gap +8.0 pts, exactly on the 8-point trigger) at π_min; H = 6. The pick and the pitch's "why it beat the other nine" claim are made only from what survives every row (Section 10.5).

### 4.10 Output row (one per finding, `findings_v2.jsonl`)

```
{ id                 sha256(ticker|kind|first cite_id)[:12]
  ticker, signal_kind, signal_family, has_detector, detector, block, channel, direction (adverse | favorable | favorable-quantified)
  sentence           one plain-English sentence
  sentence_md        the sentence with [n] markers and footnotes (cite.render_markdown, up to 6 page citations)
  impact             { channel, formula (operands written out), d_rev, d_oi, d_eps {bull, base, bear}, cm, tax, shares,
                       fiscal_year, t_years, flags, adverse, quantified, citation_ids }
  peer               { metric_value, peer_median, peer_z, rival }   or, for IRA rows, { analogs: [CMS quotes] }
  vector             { M, sigma_EPS, sigma_currency, dEPS_base, t_years, O, z, h, headline_doc, a, a_source, c, s,
                       age_months, H, disclosed, E, E_pages, n_ind, pi, pi_route, topics }
                     IRA rows add dRev_spec_formula, M_spec_formula, S_spec_formula (comparison only)
  S, confidence, confidence_reasons[], flags[], needle_eligible, old_S
  citations          [Citation.to_dict()]   key page citations first, then the impact constants' citations }
```

**[landing in league_v3]** The vector carries D (discussion term) and τ (decay term) beside O. Where the peer column is empty the deck prints "no peer analogue" rather than a blank (review B7).

### 4.11 Product fine print (the Part 1 product comparison)

Module `agent/needle/quant/product.py`, CLI `python -m agent.needle.quant.product_cli --ticker LLY --product zepbound`. Output `out/<T>/product_<product>.json` and `.md`. No API call; every number is computed from files and every quote is checked against the shared index. Pitch-writer notes: `docs/product_fineprint.md`.

**The table.** Five rows, exactly the case's: approved uses; boxed warnings and safety fine print; dosing and convenience; patent and exclusivity timeline; pricing and gross-to-net exposure. Columns are the product and each rival the case appendix lists (`product.APPENDIX`, all ten companies; Lilly's set includes the Wegovy pill as a tablet variant). A rival with no label in the drug packs is an empty column with a stated reason. Empty cells are never filled with a guess.

How a cell is cited:
- **Label rows**: a verbatim label quote located on its label-section page (`fda_label` documents, one page per section), verified by `cite.verify`. The deep link is the plain DailyMed setid page, never a `#section-N` anchor (test_product.py asserts no link contains `#section`). An absent boxed warning is cited to the Warnings and Precautions section, and the cell says so.
- **Timeline**: the company-stated US LOE from the 10-K or 20-F is a cited page; Orange Book and Purple Book dates are table references with no page. The cell prints the discrepancy when the regulatory date is later and why (the 10-K gives the compound patent; Orange Book lists the latest patent of any kind).
- **Pricing**: IRA MFP, list and cut rows and TrumpRx cash prices cite the CMS or White House page; Part D per claim, Part B ASP, NADAC and list-vs-net trends are table references. The cell says "no free net series" where true.

**Tie to the numbers** (`product.tie_to_financials`). Every channel whose inputs exist becomes a finding in the FIND row shape (`signal_family = "product"`, sentence, citations, impact with formula and bull / base / bear, peer, confidence, `obscurity_note`), and each passes the gate. Data-driven channels rank before assumption-driven ones.

| Channel | Equation | Status |
|---|---|---|
| IRA, selected drug | **the one IRA formula, ΔRev = G · d · k, CM 1.00 (4.3 b)** | **[landing in league_v3]**. v2 used Part D claims x max(0, list30 x (1 - GTN) - MFP30) with GTN 50 / 60 / 70% and CM 0.70, a third formula that could print a different dollar figure for the same drug than its FIND row (review S3). That figure is kept only as a comparison field |
| IRA, expected selection | ΔRev = G · d · k with d = the quartiles of the CMS cuts already set (q25 / median / q75) | **[landing in league_v3]** (v2: G x cut, no k) |
| LOE | ΔRev = Rev_US · (1 - pct_of_peak at t = 1 / 100), US curves by modality (`loe_curves.csv`); CM 1.00 biologic, 0.70 small molecule | built |
| Label breadth (Medicare) | ΔRev = (rival claims - own claims) · capture · own gross per claim · (1 - GTN); capture 50 / 35 / 20% (**assumed**) | built; confidence capped at LOW, `assumed_parameters` |
| Cash price / TrumpRx scenario | ΔRev = Rev · share moved · (1 - cash / list); share 40 / 25 / 10% (**assumed scenario**) | built; capped at LOW. Under the MFN rule (4.3 c) this is shown as a scenario, never as an estimate of MFN cost |
| Boxed warning | ΔRev = Rev · 10% to 25%, only when no listed rival carries one | built; capped at LOW |

ΔEPS = ΔRev · CM · (1 - t) / D is applied by the FIND scorer.

**Obscurity for product findings.** Label facts are years old, so O computed on the label date is about 0. Product findings compute O on the consequence: age from the date the revenue effect first shows (MFP effective date, LOE year), attention from the scorecard share for the consequence's topic (the `topic=` flag). Every record carries `obscurity_note`.

**Growth limiter and the priced-in call** (`product.growth_limiter`). The limiter is the highest-ranked channel (data-driven first, then by base abs(ΔRev)), written as one sentence with its base-case dollars a year. **Priced in** = (scorecard share of quarters asked about the consequence's topic ≥ 0.5 AND the case starter thread names the consequence) OR share ≥ 0.8. Consensus is reported as untested at product level (I/B/E/S revenue consensus is company-level only). If no channel has its inputs, the sentence says the data do not support a call and priced-in is false.

Product limits (also in Section 9): true net price is unavailable; capture, cash-share and boxed-warning elasticities are assumptions; Part D data stop at 2024, so label changes after that are not in the claims; ex-US is out; rival makers' own statements are not yet in the table.

---

## 5. Model 2: DECIDE

Code: `agent/needle/quant/moves.py` (templates and the `decide_weights` block), `decide.py` (arithmetic, five numbers, selection), `kill.py` (kill signals and revised EV), `decide_cli.py`. Tests: `tests/needle/test_decide.py`. Pitch-writer notes and the list of deviations from the reviewed draft: `docs/decide.md`.

### 5.1 Equation

For each candidate move m, scenario s ∈ {bear, base, bull}, month τ = 1..horizon (τ ≤ 24 is the decision window; later months are the terminal value of the position held at month 24, valued under the same rules):

```
EV_m = Σ_s p_s · [ Σ_{τ=1..24} ( P_alive(τ) · CF^in_{m,s,τ}  -  P_reach(τ) · CF^out_{m,τ} ) / (1 + r_mo)^τ   +   TV_{m,s,24} / (1 + r_mo)^24 ]

r_mo        = 1.0785^(1/12) - 1                     Damodaran pharma WACC 7.85% (Jan 2026), the team's choice
P_alive(τ)  = product of phase-transition probabilities for readouts at or before τ     (BIO/Informa/QLS 2021)
P_reach(τ)  = probability of reaching the phase in which the outflow at τ is spent       (Stewart, Allison, Johnson 2001)
TV          = PV of all later cash flows of the position held at month 24, to LOE or 10 years after launch
CF^in       = incremental after-tax operating cash flow = ΔRev · CM · (1 - t), scaled by the scenario multiplier
p_s         = (0.50, 0.11, 0.39) for (bear, base, bull)          Trinity 2023 US launches
multiplier  = (0.8, 1.0, 1.2)                                     ZS failure and success boundaries
```

- **Scenario basis (review A22).** Trinity's bear weight counts every year-one miss of any size; ZS's 0.8 is the boundary of a year-three failure. Pairing them makes the bear case optimistic, not conservative, and with p_bear > p_bull the boundary choice biases EV upward (p-weighted multiplier 0.978). Stated as a limit; the scenario spread is understated.
- **Discount rate (review A21).** 7.85% is the team's choice. The research note says internal R&D hurdle rates are commonly set higher (DiMasi's 10.5% real) to reflect project risk beyond what phase probabilities capture; the reviewed draft cited that note in reverse. EV at 10.5% is not computed in code and is stated as a sensitivity to add.
- Technical risk (P_alive) and commercial risk (p_s) are treated as independent (**inference**).
- `decide.py` reports in-window PV (months 1-24) and terminal value separately for every move. Long-dated moves are mostly terminal value, so the deck shows both.

### 5.2 Inputs linked to Part 1

Every DECIDE input is a FIND row (by `id`, carrying its citations), a benchmark constant (Section 11.2) or a company number with its own citation:

```
DecideInput { name, value, unit, kind: finding | benchmark | inference | company | assumption | design, finding_id?, citation_ids[], note }
```

A finding feeds a parameter automatically only when its `impact` carries a dollar value; otherwise it is listed in the move's `finding_ids` and counts for strategic fit only. `decide.normalize_findings` reads both v2 rows (`findings_v2.jsonl`, key `S`) and old engine rows.

| DECIDE input | From FIND |
|---|---|
| Revenue at risk the move defends (M5) | LOE ΔRev (4.3 e) or IRA ΔRev (4.3 b, the one IRA formula) |
| Baseline price step (M4) | IRA ΔRev (one formula); MFN is direction-only (4.3 c), so an MFN-driven M4 needs a team-stated, flagged dollar input |
| Addressable gap (M3) | product-table label difference (4.11); the team states the uplift as an assumption |
| Tariff exposure after 2029 (M7) | 4.3 d note |
| Strategic fit (MCDA) | see 5.4 |

A move that addresses no Part 1 finding gets strategic fit 0. Benchmarks whose source is a URL become Citations with status `unverified` and `confidence_note = "external benchmark"`, so the gate sees them explicitly. Team inputs are labelled `assumption` and listed as flags; unsourced defaults are flagged "state it or replace it".

### 5.3 Move templates (`moves.py`)

| Code | Case move | Probability structure | Defaults (Section 11.2 names) |
|---|---|---|---|
| M1 | Acquire | deal-comp price (`PREMIUM_MEDIAN` 63%; `EV_PEAK_LOW` / `EV_PEAK_HIGH` 0.5x-1.0x peak sales), BIO TA rates if unapproved, CVR at payout probability | `CM_ACQUIRED` 0.7173 less royalty; uptake `UPTAKE_MONTHS` 39.9 or `UPTAKE_MONTHS_ONC` 60 |
| M2 | In-license | upfront `UPFRONT_SHARE` 6%, development milestones `DEV_MILESTONE_SHARE` 33% (avoidable on failure), royalties `ROYALTY_EARLY` / `ROYALTY_LATE` | BIO TA rates (metabolic default) |
| M3 | Label expansion | rNPV: trial costs at P_reach, revenue at P(Phase III) x P(NDA) non-NME 0.675 x 0.915 = 0.6176 | `TRIAL_COST_PLACEBO` 28.8 per pivotal trial; `CM_EXISTING` 0.85; ramp to peak (below) |
| M4 | Pricing, coverage, cash-pay channel | no clinical event; baseline moves with the LOE curve and the IRA step | channel ramp 12 months; horizon 60 |
| M5 | Portfolio shift, LOE defense | difference of two erosion paths (`LOE_RETENTION`) | switch capture 0.15 (inference; Skyrizi/Rinvoq precedent `SKYRIZI_OFFSET`) |
| M6 | Commercial investment | ΔRev = ε · ΔSpend / 0.108 (`EPS_PROMO` 0.06, `PROMO_SHARE` 0.108); at ε = 0.06 each $1 of spend returns $0.56 of revenue | `REP_COST`, `REP_RAMP_MONTHS`, `DTC_TV_LOW` / `DTC_TV_HIGH`; compliance gate: approved uses only, fair balance, "Student concept, not actual promotional material" |
| M7 | US manufacturing | capex `PLANT_CAPEX_LOW`-`PLANT_CAPEX_HIGH` over `PLANT_BUILD_MONTHS`; benefit from `TARIFF_START_MONTH` 27 at `TARIFF_RATE` 0.15 | depreciation pledge / `PLANT_DEPR_YEARS` 15 (inference) |

**Ramp to peak: one constant for every template [landing in league_v3].** At ca12339 the templates ramp differently: M3 uses `LABEL_RAMP_MONTHS` 42 (57% of peak 24 months after launch, against the research note's 25-40% default; review A23), M1 and M2 use `UPTAKE_MONTHS` 39.9 (IQVIA 13.3 quarters), M4 12 months, M6 18 months. v3 uses one consistent 24-month ramp across the templates, so in-window value is comparable between moves. A 24-month linear ramp reaches 100% of peak at month 24, above the 25-40% research default; the deck states which ramp each number uses and shows the reference case under both.

### 5.4 The five numbers (every candidate, same scale)

| Number | Definition (`decide.py`) |
|---|---|
| **EV** | EV_m above, $M present value at `as_of`, with in-window PV and TV shown separately |
| **Downside cash at risk (CaR)** | undiscounted outflow through min(24, first readout) in the bear scenario with technical failure at the first readout, net of inflows received before then (treated as certain) and of contractually avoidable payments (milestones not triggered, CVRs) |
| **Payback month** | first month at which cumulative discounted expected net cash flow ≥ 0, searched to 120 months (`PAYBACK_SEARCH`); "none" if never |
| **Scenario EV spread** | EV with p_bull = 1 minus EV with p_bear = 1 |
| **MCDA score** | Σ_j w_j x_j over strategic fit, capability, execution risk, stakeholder evidence; x_j ∈ [0,1]; w_j = 0.25 each (`MCDA_WEIGHTS`, **inference**: ISPOR's weighting text was not retrieved, so equal weights are our choice) |

MCDA criteria:
- **strategic fit [landing in league_v3]** = Σ (M · E) of the Part 1 findings the move addresses / Σ (M · E) of the company's top five findings by M · E, capped at 1. v2 used S, which contains O: a move addressing the most material known problem (z = 1, so S = 0) scored fit 0, which is backwards for a CEO decision (review A24). Materiality and evidence matter for the decision; novelty to the market does not.
- capability = share of the move's required assets the company holds, each a cited fact;
- execution risk = P_alive(end) x p-weighted multiplier / 1.2 (`COMMERCIAL_MULT_CAP`), so 1 means certain bull;
- stakeholder evidence = share of the move's deciders (prescribers, patients, payers, regulators, investors) with documented evidence. The deck adds a hand-built decider-evidence table for the picked move (review B15), because a share alone does not say why the move will work.

**Selection rule** (`decide.select_move`). (1) Feasibility gate: CaR ≤ cash and equivalents at the latest balance sheet (a cited 10-Q number). (2) Highest EV. (3) If the [EV_bear, EV_bull] intervals of the top two overlap, prefer the higher MCDA and say so. The two rejected alternatives are the next two, each with all five numbers and the single binding reason it lost.

### 5.5 Synthetic reference case (unit test for the DECIDE arithmetic)

Synthetic inputs, not a recommendation: label expansion of a marketed drug, two placebo-controlled pivotal trials at $28.8M each spread evenly over months 1-24, readout at month 24, approval at month 37, incremental peak sales $800M, CM 0.85, t 0.16, flat peak to 120 months after approval, no LOE.

| Output | 42-month ramp (v2 oracle, `tests/needle/test_decide.py`) | 24-month ramp (v3) |
|---|---|---|
| P(success from Phase III, non-NME) | 0.675 x 0.915 = 0.6176 | 0.6176 |
| In-window PV (costs only) | -53.3 | [v3: pending] (v2 -53.3) |
| EV bear / base / bull | 1,161.0 / 1,464.6 / 1,768.2 | [v3: pending] (v2 1,161.0 / 1,464.6 / 1,768.2) |
| EV (p = 0.50 / 0.11 / 0.39) | 1,431.2 | [v3: pending] (v2 1,431.2) |
| CaR | 57.6 | [v3: pending] (v2 57.6) |
| Payback | month 51 | [v3: pending] (v2 month 51) |
| Scenario spread | 607.2 | [v3: pending] (v2 607.2) |

For scale, the review recomputed the same case at a 60-month ramp (40% of peak at 24 months): EV 1,265.2, payback month 54.

### 5.6 Kill signals and the revised EV (`kill.py`)

| Signal | Threshold | Source and lag | Check month | Effect |
|---|---|---|---|---|
| ZS breadth, return-writing, depth | < 30% / < 50% / < 30% | paid claims (IQVIA, Symphony); no free equivalent | 6 | Bayes on scenarios with P(breach given bear, base, bull) = 1.0, 0.55, 0.10 (`ZS_LIKELIHOOD`; base 0.55 is inference). Several ZS breaches count as **one** update (one observation) |
| Year-one net sales | < 80% of forecast | company 10-Q product revenue, about 40 days after quarter end | 12 | p_bear set to at least 0.70 (`P_BEAR_AFTER_MISS`), the rest renormalized over base and bull in proportion |
| Commercial coverage | < 50% of commercial lives | payer trackers (paid) or company commentary | 6 | Bayes with 1.0, 0.75, 0.50 (`COVERAGE_LIKELIHOOD`; 0.75 and 0.50 inference) |
| Medicaid units vs plan | < 80% of plan | Medicaid SDUD, 60 days plus posting lag | 9 | as year-one |
| Self-pay share (DTC moves) | < 35% of new scripts (`SELF_PAY_SHARE`) | company disclosure | 6 | ZS likelihoods |
| Safety | FAERS serious reports +50% YoY and above rivals | FAERS quarterly, about one quarter lag | 3 | human review, no EV change |
| Trial enrollment | < 80% of plan | ClinicalTrials.gov | 6 | human review, no EV change |

Check months run from launch or move start. ZS, coverage and year-one signals are not attached to trial-stage templates (M2, M3), whose launch is outside the first 24 months; those carry enrollment and safety only.

```
p'_s = p_s · L_s / Σ_u p_u · L_u              L_s = P(breach | s)
EV'_m = Σ_s p'_s · EV^remaining_{m,s}         remaining cash flows after the check month, sunk costs excluded
Stop if EV'_m < V_abandon = salvage - exit costs
```

Example: one ZS breach at month 6 from p = (0.50, 0.11, 0.39) gives p' = (0.834, 0.101, 0.065). Medicare Part D Prescriber PUF lags about 18 months, so it can confirm but never trigger inside the window.

**Run status.** DECIDE has been run only on old-shape LLY findings (`docs/examples/moves_LLY.json`). It must be re-run on the picked company's `findings_v3.jsonl` rows before its numbers go in the deck (Section 9; `docs/HANDOFF_quant.md`).

---

## 6. Citation contract

Hard requirement: every number and quote the models output carries an in-text marker and a footnote that resolves to the source page, and a claim without a verified citation is not shown. Code: `agent/needle/cite/` (no API calls anywhere in the package). Tests: `tests/needle/test_cite.py` (23 tests on a synthetic sqlite with the index schema, plus one on the real index). Full plumbing notes: `docs/citations.md`. This section states the contract the code implements; it is not a second design.

### 6.1 The shared index

One index, one verifier. The canonical index is the scraper's `data/moat/index/citations.sqlite` (tables docs, pages, facts, turns, meta; page id `doc_id#p<page_no>`, where page_no is the first number of the `[[page N | printed M]]` marker). `agent/moat/cite.py`, `agent/moat/index.py` and `tests/moat/test_cite.py` are copied verbatim from data-moat commit 704741d, with two changes: `cite.DB` resolves from env `CITATIONS_DB`, else the repo-local file, else the gap-data copy; and two data-tree tests skip when `data/moat` is absent. Used from `agent/moat/cite.py`, not reimplemented: `db()`, `label()`, `where()`, `get_page()`, `cite()`, `verify_quote()`, `search_pages`, `search_facts`. `agent/needle/cite/index.py` is an adapter only (alias resolution for documents stored under both id schemes, doc_type vocabulary, `location()`). Both schemes resolve: `NVO:6k/2025-08-06_caq22025.md` (corpus) and `NVO:companies/NVO/6k/2025-08-06_0001628280-25-038087.md` (moat) are one record. The index contract is frozen at 704741d until the scraper's Sunday freeze.

### 6.2 The Citation object (`locator.py`)

```
Citation
  cite_id            stable hash of (canonical_id, page, normalized quote): identical evidence gets one footnote
  canonical_id, ticker, doc_type (10-K | 10-Q | 20-F | 8-K | call transcript | label | proxy | comment letter | press | other)
  doc_title          "MRK 10-K FY2025"
  period
  location           moat where() string: "p. 58", "Item 1A", "section Warnings", "PDF p. 3", "file page N (no printed page number)"
  speaker, raw_doc_type, page_scheme, license
  page               file page (the [[page N]] marker; what the verifier checks)
  folio              printed page, verbatim
  char_start/char_end span of the quote inside the page text (None until located)
  quote              verbatim text from that page
  claim_type         quote | number | paraphrase
  value, unit        the number as emitted, for number claims
  source_url         whole-document URL from the manifest
  deep_link          see 6.5 ("" if the document has no http source)
  viewer_link        /viewer?doc=<canonical_id>&page=<n>&q=<quote>
  verification       { status, score 0..1, checked_at, detail }
  confidence_note    why a citation failed or what was approximated
Claim(text, citations)
```

`Citation.to_dict()` and `from_dict()` round-trip through JSON.

### 6.3 Verification ladder (`verify.py`): five statuses

| Rung | Status | Test | Ladder score | FIND grade g (4.5) |
|---|---|---|---|---|
| 1 | `exact` | quote is a byte substring of the cited page | 1.0 | 1.00 |
| 2 | `substring` | equal after normalization (NFKC, smart quotes and dashes, case, whitespace) via `agent.moat.cite.verify_quote` | 0.98 | 1.00 |
| 3 | `fuzzy` | `rapidfuzz.fuzz.partial_ratio ≥ 90` (`FUZZY_THRESHOLD`), and every numeral in the quote appears in the matched span | ratio / 100 | 0.90 |
| 4 | `number_match` | number claims only: the emitted value (parentheses negative, percent, thousand / million / billion, table-header scale) is among the numbers on the cited page although the quote did not verify | 0.6 | 0.745 |
| 5 | `unverified` | none of the above; a note says if the quote is on another page. Wrong pages are never silently corrected | 0 | 0 |

The fuzzy threshold is 90 because markdown-conversion noise scores 93-99 and real paraphrases 60-80; there is no published threshold (**inference**). The numeral guard exists because one altered digit in a long quote still scores about 98. For number claims whose quote does verify, the value must also appear in the matched span, else the citation is `unverified` (quote right, number wrong).

**Transcript speaker check [landing in league_v3].** At ca12339 the package does not apply the speaker rule or the fool.com exclusion from `agent/findings.verify()` (the speaker's name must precede the quote; quotes from the LLM-written fool.com "takeaways" and summary sections are rejected). v3 ports both into `cite.verify`, so a transcript quote is shown only if the speaker check passes. Until it lands, the deck uses no transcript quote as evidence (review B12).

### 6.4 The gate

`gate(claims) -> (passed, rejected)`. A claim passes only if at least one of its citations is not `unverified`; passed claims keep only their verified citations. Claims with no citations are rejected. FIND puts rows with E = 0 in `rejected_v2.jsonl`. A `number_match` citation passes the gate but grades 0.745 in E, so it can support a MEDIUM row and can never be the Sharpest Needle (E ≥ 0.90).

### 6.5 Deep links by document type (`deeplink.py`)

Rules branch on `docs.source_url`, raw `doc_type`, `page_scheme` and `license`. EDGAR has no page anchors, so the file page and printed folio live in the footnote and the viewer link.

| Source | Rule |
|---|---|
| SEC filings (annual, quarterly, 8-K, 6-K, earnings release, EDGAR press release) | EDGAR primary .htm + `#:~:text=` + the first 8 words of the quote, percent-encoded (`-`, `,`, `&` too). Chrome and Edge honour it; Safari lands at the top. No quote: plain URL |
| SEC comment letter | .htm: text fragment. .pdf: `#page=N` (PDF page) |
| CMS, White House, Federal Register and other PDFs | URL + `#page=N` |
| FDA label (`fda_label`) | the DailyMed setid page, plain. **No `#section-N` anchors** (unstable across label versions); the section title is in the footnote |
| FDA label version (`fda_label_version`, a getFile zip URL) | the DailyMed history page for the setid |
| Transcript on a third-party page | plain page; footnote shows speaker and quote |
| Bloomberg-licensed (`license = bloomberg_licensed`), LSEG PDFs under `verified/calls/src/`, anything without an http URL, R2 keys | no deep link; viewer route only |
| Facts rows | `fact_link(source)`: http sources (cms.gov, data.medicaid.gov) link directly; R2 keys and WRDS ids use the local route |

Text fragments cannot be validated server side: the browser matches them and skips the highlight on a miss, and the hit rate on SEC HTML is unmeasured. Smoke test (read-only `curl -sI`, SEC user agent): EDGAR htm x3, an SEC comment-letter PDF, a Novo IR PDF and a DailyMed setid page returned 200; an AstraZeneca IR PDF returned 403 to a script user agent.

### 6.6 Rendering, the licence gate and the viewer (`render.py`, `viewer.py`)

- `render_markdown(claims)`: `claim text[1][2]` in order of first appearance, then one footnote per citation:
  `[n] <doc_title>, p. <folio> (file page <page>) -- "<quote>" -- [open](deep_link) · [viewer](viewer_link) · verified: <status>`.
  Identical citations share one number. Transcript footnotes show `speaker: quote`. `render_html` uses `<sup><a href="#fn-n">[n]</a></sup>` and `<li id="fn-n">`.
- **Bloomberg licence gate.** `render_markdown(claims, public=True)` withholds the quote text and the viewer link of Bloomberg-licensed citations. I/B/E/S rows (WRDS, `license = wrds_licensed`) are used for internal math and never quoted in public output.
- **Viewer.** `/viewer?doc=<canonical_id>&page=<n>&q=<quote, first 400 chars>` is produced for every citation. `viewer.render_viewer(doc, page, q, public=False)` returns the page HTML with the span highlighted and refuses licensed documents when `public=True`. **There is no public page viewer**: the app serves local files, R2 is private, and the corpus is not in R2. External readers get the source deep link only.

### 6.7 LLM path and the API constraint (`llm.py`)

- `build_cited_request(system, question, pages)` returns a Messages API body: one `search_result` block per page (`source` = viewer link, `title` = "<doc_title> p. <folio>", content = one text block per paragraph, `citations: {enabled: true}` on every block), `cache_control: ephemeral` on the last block, `temperature: 0`, and `CITATION_SYSTEM_RULE` appended to the system prompt.
- `parse_cited_response(...)` turns every text block into a Claim and each `search_result_location`, `char_location` or `page_location` into a Citation that is then verified by the ladder. The page number comes from our own `source`, never from model output. With `strict_numbers=True`, a claim containing a number absent from all its cited texts is downgraded to `unverified`.
- Citations cannot be combined with structured outputs (`output_config.format` returns 400) and must be enabled on all or none of a request's blocks. If JSON is needed, a second, non-cited call runs on the already-verified claims and carries their `cite_id`s through.
- Not live-tested against the API (no key yet). How and when this runs: Section 9 and `docs/ai_in_the_build.md`.

### 6.8 Still missing

- A public host for the viewer (6.6).
- EDGAR iXBRL fact anchors are not generated; derived numbers cite the filing page of the base figure, not the XBRL concept.
- Facts rows link via `fact_link` but are not yet full Citations; `page_scheme = none` documents have no pages.
- Two indexed paths are listed in manifests but absent on disk.

---

## 7. Generalization to any ticker

### 7.1 What the data layer needs per company

Minimum to score (FIND runs, with flags): SEC companyfacts (XBRL), the latest two annual reports and the latest quarterly report page-marked into the citation index (`agent/needle/onboard.py` pulls filings by CIK), and product and rival packs. Each further bucket switches on a term:

| Bucket present | Term it enables | If missing |
|---|---|---|
| I/B/E/S quarterly EPS consensus and actuals | σ_EPS from surprises; c_f | σ fallback chain (4.2), "not league-comparable"; c_f untestable |
| ≥ 4 call transcripts with speaker names | a_f by regex; call families | a_f = scorecard median, "imputed" |
| Earnings release | h_f | shortlist median for the topics, flagged |
| Form 4 (US filers only) | insider family | absent (no detector today in any case) |
| CMS selected-drug lists, Part B/D spending | IRA channel | channel not scored |
| Quarterly product revenue | LOE size | annual product revenue (20-F), annual granularity |
| FINRA short interest | s_f | s_f = 0, flagged (true for all ten today) |

### 7.2 Universal vs company-specific parameters

- **Universal** (Section 11): r, H, the π table and tiers, the 26% haircut, the anchor 0.03, CM by change type, LOE retention curves, label elasticities, the IRA k factors and analog discounts, E grades, confidence thresholds, needle floors, N*, all DECIDE benchmarks and scenario weights.
- **Company-specific** (computed, each cited): σ_EPS, t, D, Rev_TTM, US revenue share, product revenues, Medicare spend per selected drug, a_f by topic, earnings-release headline, starter thread (shortlist only; empty for other tickers).

### 7.3 Peer sets outside the shortlist

- **Product peers**: the onboarder's rule, other-manufacturer brands in the same FDA Established Pharmacologic Class via NLM RxClass, ranked by Part D spend; the team may add rivals with a stated reason. Brand-to-manufacturer matching by `key[:6]` can mis-assign.
- **Financial peers**: the peer median and z in the peer column come from the existing detectors over the ten shortlist companies. The k = 6 nearest-neighbour peer rule for non-shortlist tickers (`K_PEERS`) is specified but not built.

### 7.4 Comparability rule (as coded)

Every term that falls back writes a flag into the row's `flags`, and the league output shows company flags. A company is league-comparable only if σ_EPS comes from I/B/E/S surprises (`data.company`: any σ fallback sets `comparable = False`). At ca12339 all ten shortlist companies are comparable. a_f imputation is flagged on the row but does not change comparability (the reviewed draft said it would). 20-F filers (NVO, AZN): annual comparisons, no quarterly product revenue, no proxies or Form 4, imputed headline term, and for NVO no conversion of USD channels.

### 7.5 New-ticker path (demo)

A live new-ticker run is not part of the demo. The demo shows a pre-recorded onboarding run for VRTX (`out/VRTX/`, onboarding commit 563097d): `python -m agent.needle.onboard VRTX`, then `python -m agent.needle.run --ticker VRTX` (detectors) and `python -m agent.needle.quant.run --ticker VRTX` (FIND). VRTX has no case starter thread, so z = 0 for all its rows, and it is not league-comparable if its σ falls back.

---

## 8. Validation protocol

### 8.1 What is tested today (deterministic, no API key)

1. **Reference answers** (`tests/needle/test_quant_find.py`): LLY σ_EPS 2.0294 within 2e-4 (2 x 1.01474); DIO 468.9 and finished-goods DIO 73.4; Verzenio S 0.0507 under the class rule and 0.0304 under the comparison formula; LLY DIO row S 0.00168 at π_min with confidence MEDIUM. **[landing in league_v3]** the H = 3 and c = 0.5 changes move the O-dependent reference values; the tests are updated with the v3 commit. `tests/needle/test_decide.py` pins the Section 5.5 oracle (42-month ramp).
2. **Gate and verifier** (`test_trust.py`, `test_cite.py`): seeded errors are withheld (wrong page, altered number, foreign figure, invented quote), the ladder rungs, the numeral guard, the licence gate in public render, and deep-link rules (`test_product.py` asserts no DailyMed `#section` link).
3. **League robustness [landing in league_v3]**: the robustness table in `league_v3.md` (4.9). The full rank-stability report (every Section 11 constant at x0.5 and x1.5) from the reviewed draft is **not built**; the robustness table is the shipped subset.

### 8.2 What the backtest supports, and what it does not

- **Supports:** five accounting flags, with the engine's thresholds, against gross-margin compression over the next four quarters, between firms, 1,410 firm-quarters, 43 firms, 2012-2024, point-in-time, non-overlapping windows. Dose response on margin drops is monotonic on full-coverage rows (12% at 0 signals to 61% at 5, n = 18 at 5).
- **Does not support:** any claim that flags predict revenue drops or impairments (no firm-clustered CI entirely above 1 on hard events); any within-firm claim; any text, call, label, policy or insider family; any return claim; any peer-level trigger. The universe was hand-picked and rules and results were produced in one commit (disclosed), hence the 26% haircut. The excess rates are between-firm and the outcome rule differs across the five flags (review A10).
- **The raw panel is not on disk.** Only the summary `out/backtest/hit_rates.json` exists; `data/backtest/xbrl/` is in no worktree and has no fetch script. What that means: the five π values cannot be re-estimated or re-tested; peer-level outliers cannot be tested, so they get no backtest prior (D5); the dose response cannot be used to scale the anchor by flag strength (review D3); and the leave-one-year-out check (8.3) cannot run. Re-running needs a fetch of SEC companyfacts for the 50 filers.

### 8.3 Leave-one-year-out sign and rank check (next step, needs the panel)

For each year 2012-2024, estimate each family's excess rate on the other years with an 8-quarter purge gap around the held-out year (forward windows otherwise leak), then check the held-out sign and the Spearman correlation of the family ranking. Report power with it: the review estimates about 45% power to reach 10 of 13 years for the inventory flag (held-out SE about 0.114 against an effect of 0.063). Pre-register thresholds and log every discarded specification.

### 8.4 Out-of-sample test with ten companies

- Ten companies cannot show statistically that the chosen company is the best of ten: under random ranking p ≥ 1/10 = 0.10.
- **Sealed direction calls.** Before Q3 2026 results, each company's top-finding direction (sign of next-quarter gross-margin change; sign of revenue surprise against the I/B/E/S mean) is sealed by hash, as in `docs/needle_sealed.md`. JNJ reported on 2026-10-13, before `as_of`, so **N ≤ 9** calls. The null for surprise signs is the **base rate** of beats among large caps, not 0.5. Results arrive after judging (MRK, BMY, LLY Oct 29; AZN Oct 30; PFE Nov 3; NVO Nov 4-5), so the sealed hash is the only demo item.
- Power: "if the same abnormal performance occurs over six months, a sample size of 200 is required to detect the abnormal performance even 65% of the time" (Kothari and Warner); we target the fundamental event, not returns.

### 8.5 Calibration of LLM confidence (once the key is armed)

- Labelled set: FinanceBench open 150, `data/moat/verify/ai_wrong.jsonl` (a live log: 61 rows when the review read it, 472 by the evening of 2026-10-17), the seeded errors, and every gate decision.
- Metrics: AUROC and ECE of verbalized confidence for predicting "verified", with **equal-mass** bins (confidences cluster at 80-100%, so equal-width bins are mostly empty) and a bootstrap CI on AUROC (about ±0.1 on 100-150 held-out items). Reported per failure class.
- Use: none in the score. LLM confidence is not a tie-breaker; the LLM's only scoring role is the trial veto (4.7).

---

## 9. Honest limits (pitch can lift this verbatim)

Pitch-ready sentences with the proxy used for each: `docs/honest_limits.md`. The model-level limits:

**Data the model cannot see**
- **True net prices.** No product-level net price is public. We use company-level gross-to-net disclosures, Medicare Part B ASP (net-like), Part D gross spend, NADAC (list-like) and Medicaid SDUD; the GTN band in the product table is an inference.
- **Ex-US volume and price.** IRA, MFN and LOE are modelled on US revenue; ex-US is out of the product table.
- **Commercial formularies.** PBM formulary decisions and rebate contracts are private; coverage enters only through Part D data, company commentary and coverage-lag studies.
- **Q3 2026 results.** FIND uses data through Q2 2026. Results arrive after judging; sealed calls turn this into a test (8.4).
- **MFN (open disagreement D2).** "MFN deal terms are confidential. We score MFN as a direction, not a dollar amount, except where a company states its own effect." No company-stated term is built yet, so every MFN row is direction-only.
- **IRA for HIV.** No HIV drug has a published MFP. Biktarvy's discount is the cycle 1-2 range (38 / 65.5 / 85%) at the low-rebate rule, and the class rule is not calibrated to CMS's 22% cycle-1 net savings.
- **Short interest, options, press.** Not collected (press only for MRK). s_f = 0 makes D optimistic for heavily shorted names.
- **Licensed data.** "I/B/E/S numbers are licensed and shown only in the local app." Bloomberg text is cited, never shown publicly.
- **Facts.** "69,553 facts in the store, 10,963 of them page-verified."

**Statistics and priors**
- **Priors (A4, A10).** "Signal track records come from one 43-firm, between-firm backtest and published return studies; they rank evidence types to within about a factor of two and are shown as tiers, not exact probabilities."
- **Peer-level outliers (A1, D5).** "A ratio that is unusual against peers but has not crossed our backtested trigger gets no backtest prior until it is tested." In v3 such rows are not quantified.
- **Generic impact (R2).** "Text and call findings without a mapped channel are not given a dollar impact; they show their evidence tier and stay out of the top-five table."
- **One margin-event size (D3, open).** "Accounting rows use one margin-event size; the strength of the flag changes only whether it counts."
- **Noise scale (A3).** "Materiality divides by the company's usual quarterly EPS miss, annualized by an assumed factor of two; impacts one to two years out are compared on that near-term scale."
- **Consensus test (A12).** "When consensus for the affected year did not exist before the disclosure, we cannot test whether analysts priced it, and we assume a 50% chance they did."
- **Backtest panel.** The raw backtest panel is not on disk, so the five tested priors cannot be re-estimated, peer-level triggers cannot be tested, and the leave-one-year-out check cannot run (8.2).
- **Validation (A25).** "Q3 results arrive after judging. We sealed up to nine directional calls by hash; with ten companies no ranking can be statistically significant (minimum p = 0.10)."

**Choices stated as choices (open disagreements, with the default named)**
- **Age clock (D1).** Default: age runs from the latest filing that states the fact. Sensitivity: age from the first public date (Lazy Prices finds verbatim repeats are not news).
- **Half-life (B-3).** Default: H = 3 months, with the needle floor on the discussion term only. Sensitivity: H = 6 (robustness table).
- **Concentration (B-4, A18).** Default: one dominant evidence block counts as one finding (L = top-5 sum x N_eff / 3). The raw sum is printed beside L; GILD leads on the raw sum in v2.
- **Scheduled events dominate (B-2).** π = 1 rows (IRA) can dominate a company's sum; the robustness table shows IRA at π 0.5.
- **How S is shown (D6).** ΔEPS in dollars and π as a tier; the ranking slide carries the robustness table.
- **AMGN's receivables row.** In v2 the #1 row in the league, at a gap of +8.0 pts, exactly on the 8-point backtest trigger. Shown at π_min in the robustness table; the 10-Q should be checked for an acquisition, timing or Part D redesign billing cause before calling it channel stuffing.

**Coverage**
- **Needle.** "Five of ten companies have no finding that clears every needle condition; for those we name a provisional needle and label it." v3 count: [v3: pending] (v2 5 of 10).
- **Detectors (B3, B14).** "Several signal families in the design (insider sales, 8-K items, misstatement scores, gross-to-net, footnotes) have no detector yet; LOE inputs are thin for four companies (NVO, AZN, ABBV, JNJ)."
- **Foreign filers (R4).** "AstraZeneca and Novo Nordisk have no earnings release in our index, so their headline term is imputed from the other eight; Novo's dollar-based policy channels are not converted."
- **Attention.** a_f outside the nine scorecard topics is a regex over analyst turns, and the attention bucket is thin (up to 10 quarters, fewer for some companies).
- **Transcripts.** Until the speaker check lands in the citation package, no transcript quote is used as evidence in the deck.
- **Viewer.** There is no public page viewer; external readers get source deep links only, and DailyMed and EDGAR have no page anchors.

**DECIDE**
- **Scenario basis (A22).** "Scenario weights are a launch base rate applied to every move, and the bear and bull multipliers are boundary values, so the scenario spread is understated and EV leans optimistic."
- **Discount rate (A21).** 7.85% WACC with no project hurdle; EV at 10.5% is not yet shown.
- **Inputs.** No product-level net price, channel build cost or formulary data is public; those are team inputs, flagged. DECIDE has run only on old-shape LLY findings so far.

**Where AI runs.** The deterministic track (detectors, FIND, DECIDE, product table, citations, league) runs with no model. The LLM track runs in one pass once the key is armed, and every model output passes the page verifier and the gate before anything is shown. Details: `docs/ai_in_the_build.md`.

---

## 10. Worked example: Eli Lilly (LLY), as of 2026-10-17

LLY is the worked example because the reviewed draft used it and because its old first place was the scorer bug (D5); it is 8th in league_v2. Inputs are local (gap-data `data/moat`, the citation index at 704741d). The component arithmetic is pinned in `tests/needle/test_quant_find.py`.

### 10.1 Company constants

| Symbol | Value | Derivation | Source |
|---|---|---|---|
| Rev_TTM | 79,665.0 | 17,600.8 + 19,291.2 + 19,799.0 + 22,974.0 (2025Q3 to 2026Q2) | XBRL `Revenues`; 2026Q2 "Revenue $ 22,974 $ 15,558" on `LLY:10q_2026Q2.md#p5` |
| t | 0.2049 | Σ income tax 6,884.0 / Σ pretax 33,595.0, same quarters | XBRL; 2026Q2 "Income before income taxes 9,247 ... Income taxes 2,152" on `LLY:10q_2026Q2.md#p5` |
| D | 893.7M | Q2 2026 diluted weighted shares | "Diluted 893.7 899.8" on `LLY:10q_2026Q2.md#p5` |
| σ_EPS | 2.0295 | 2 x sd (1.01474) of the last 8 quarterly surprises: -0.25, -0.10, -0.71, +0.80, +0.89, +0.43, +1.60, +2.37 (2024Q3 to 2026Q2) | `ibes_actuals.csv`, `ibes_eps_quarterly.csv` (WRDS, licensed: internal only) |
| r | 0.0785 | | Damodaran Jan 2026 |
| H | 3 months **[landing in league_v3]** (v2: 6) | | D9 |

### 10.2 Finding A (the old #1 driver): "Gross margin 85.8% (Q2 2026) vs peers; peer median 74.1%, z +1.8"

- Old engine: kind `gross_margin_peer_outlier`, I_norm = 1.0 (cap), P = 0.6, T = 0.926, O = 0.3, E = 1.0, Z = 1.85 -> S = 1.0 x 0.6 x 0.926 x 0.3 x 1.0 x (1 + 0.25 x 1.85) = **0.2437**, 80.3% of LLY's old 0.3034.
- Why it was wrong: `score._impact` routed every `gross_margin*` kind to abs(value) x TTM revenue, so the margin level 0.858 was treated as a change (about $68B), capped at 1. Fixed in 4009a40.
- FIND: a margin above the peer median is favourable with no adverse scenario: favourable family, π = 0, **S = 0**. It appears only as context in the peer column.

### 10.3 Finding B: "Days inventory 469 days (Q2 2026) vs peers; peer median 187 days, z +2.9"

Inputs (each verified `exact`):
- Inventories $16,793M at June 30, 2026, note on `LLY:10q_2026Q2.md#p15`: "Finished products $ 2,630 ... Work in process 9,997 ... Raw materials and supplies 4,128 ... Inventories $ 16,793".
- Cost of sales Q2 2026 $3,268M: `LLY:10q_2026Q2.md#p5` ("Cost of sales 3,268 2,448").
- Prior-year inventories $11,013.8M: `LLY:companies/LLY/10q_2025Q2.md#p7`; prior-year revenue $15,558M: `LLY:10q_2026Q2.md#p5`.

| Step | Formula | Value |
|---|---|---|
| DIO | 16,793 / 3,268 x 91.25 | 468.9 days |
| Finished-goods DIO (stage split) | 2,630 / 3,268 x 91.25 | **73.4 days**; finished share 15.7% < 0.5: flag "capacity build, not channel stuffing", non-diagnostic |
| Inventory YoY, revenue YoY | 16,793 / 11,013.8 - 1; 22,974 / 15,558 - 1 | +52.47%, +47.67% (gap +4.8 pts, below the 10-pt inventory trigger) |
| Backtest flag fired? | DIO growth +14.2% YoY vs the 15% `dio_rising` trigger | **no** |
| Excess inventory (exposure, not scored) | 16,793 - 11,013.8 x 1.4767 | 529.3 |
| ΔEPS_anchor (for reference) | 0.03 x 79,665.0 x (1 - 0.2049) / 893.7 | $2.1263 |
| M (for reference) | 2.1263 x 1.0785^-0.5 / 2.0295 | 1.0089 |
| D | z = 0, h = 0 ("inventor" absent from page 1 of the 2026-08-05 release), a = 0.6 (scorecard `inventory_channel`, 6 of 10 quarters), c = 0 (n/a), s = 0 (flag) | **0.40** |
| τ | age 2.40 months (10-Q filed 2026-08-05) | [v3: pending] (v2 0.7580 at H = 6; 0.5743 at H = 3) |
| O | D x τ | [v3: pending] (v2 0.3032) |
| E | operands all `exact`, derived by code | **1.0** |
| π | flag not fired | v2: π_min 0.0055. **v3: not quantified** (anchor only for fired flags) |
| **S** | | [v3: pending] (v2 0.00168; the reviewed draft printed 0.00973 using the DIO backtest π, which the row does not earn) |
| Confidence | E = 1.0, n_ind = 1, family not diagnostic, stage split fails | **MEDIUM** |
| Needle eligible? | D = 0.40 < 0.5 | **no** |

Plain-English line for the deck: "Lilly holds 469 days of inventory against a peer median of 187, but 84% of it is work in process and raw materials; finished goods cover 73 days, which reads as GLP-1 capacity build rather than channel stuffing."

### 10.4 Finding C: "Verzenio's Medicare price is set by negotiation from January 2028"

Inputs:
- Selection: "In January 2026, HHS selected Trulicity and Verzenio as additional medicines subject to government-set prices to be effective in 2028." (`LLY:10k_FY2025.md#p46`).
- Medicare spend: "Verzenio Breast cancer $1,428,714,000" (Nov 2024 to Oct 2025 Part B+D), CMS IPAY 2028 selected-drug fact sheet p. 1 (`policy_gov:policy_gov/cms/cms_fact_sheet_selected_list_ipay2028.md#p1`; deep link `...factsheet-medicare-negotiation-selected-drug-list-ipay-2028.pdf#page=1`).
- Analog discounts (CMS, verified): Imbruvica 38% (IPAY 2026), Ibrance 50% ($7,871 vs $15,741, IPAY 2027, same CDK4/6 class), Pomalyst 60% (IPAY 2027).
- Verzenio FY2025 revenue: US 3,464, outside US 2,259, total 5,723 (`LLY:10k_FY2025.md#p49`).

| Step | Formula | Value |
|---|---|---|
| Channel | IRA, the one formula (4.3 b); oncology is low-rebate, k = 1.0 | |
| ΔRev 2028 bull / base / bear | 1,428.714 x d x 1.0, d = 0.38 / 0.50 / 0.60 | 542.9 / **714.4** / 857.2 |
| ΔEPS 2028 bull / base / bear | ΔRev x 1.00 x (1 - 0.2049) / 893.7 | $0.4830 / **$0.6355** / $0.7627 |
| Timing | 2026-10-17 to 2028-07-01 = 1.706 years; 1.0785^-1.706 | 0.8791 |
| **M** | 0.6355 x 0.8791 / 2.0295 | **0.2753** |
| z, h | not LLY's starter thread; IRA terms absent from the release page 1 | 0, 0 |
| a | scorecard LLY `IRA_negotiation`: 5 of 10 quarters | 0.5 |
| c | FY2028 consensus first appears at statpers 2026-02-19, after the 2026-01-27 selection: untestable | v2: 0. **v3: 0.5** |
| s | no data | 0 (flag) |
| D | (1 - 0.5)(1 - c) | v2 0.50; **v3 0.25** |
| τ | age 8.64 months | [v3: pending] (v2 0.3685 at H = 6) |
| **O** | D x τ | [v3: pending] (v2 0.1843) |
| **E** | both key facts `exact`; CMS and Lilly are independent issuers (n_ind = 2) | **1.0** |
| **π** | type C (statutory effective date) | **1.0** |
| **S** | M x O x E x π | [v3: pending] (v2 0.0507) |
| Comparison field | G x (d - 0.20): ΔRev 428.6, M 0.1652 | S_spec_formula [v3: pending] (v2 0.0304) |
| Confidence | quoted, two independent primary sources, type C | **HIGH** |
| Needle eligible? | v3: D = 0.25 < 0.5 (v2: O 0.18 < 0.5) | **no** |

Peer line: Pfizer's Ibrance, the same class, took a 50% list cut at its January 2027 MFP. At the same cut and the low-rebate rule, Verzenio loses about $714M of 2028 Medicare revenue (12.5% of its FY2025 sales); under the draft formula, which nets out the 20% catastrophic-phase discount Lilly already pays, about $429M.

### 10.5 The league: v2 as committed, and the robustness table

League v2 (`out/league_v2.json`, ca12339; H = 6, MFN at π = 1, drift and call rows on the placeholder anchor):

| Rank | Ticker | L | Raw top-5 sum | N_eff | Blocks | Largest share | Needle status | L v3 |
|---|---|---|---|---|---|---|---|---|
| 1 | AMGN | 0.543 | 0.745 | 2.19 | A, P, T | 32% | strict | [v3: pending] (v2 0.543) |
| 2 | GILD | 0.407 | 1.166 | 1.05 | P, T | 92% | provisional | [v3: pending] (v2 0.407) |
| 3 | JNJ | 0.195 | 0.326 | 1.79 | A, P, T | 71% | strict | [v3: pending] (v2 0.195) |
| 4 | AZN | 0.113 | 0.219 | 1.55 | A, P | 26% | provisional | [v3: pending] (v2 0.113) |
| 5 | MRK | 0.097 | 0.147 | 1.98 | A, T | 55% | strict | [v3: pending] (v2 0.097) |
| 6 | ABBV | 0.088 | 0.232 | 1.14 | P, T | 32% | provisional | [v3: pending] (v2 0.088) |
| 7 | BMY | 0.070 | 0.183 | 1.14 | P, T | 43% | provisional | [v3: pending] (v2 0.070) |
| 8 | LLY | 0.069 | 0.186 | 1.11 | P, T | 53% | strict | [v3: pending] (v2 0.069) |
| 9 | PFE | 0.038 | 0.078 | 1.48 | P, T | 32% | strict | [v3: pending] (v2 0.038) |
| 10 | NVO | 0.028 | 0.070 | 1.20 | A, T, X | 52% | provisional | [v3: pending] (v2 0.028) |

v2 top rows: AMGN receivables +17.5% vs revenue +9.5% (S 0.238, gap +8.0 pts on the 8-pt trigger), AMGN MFN (0.222) and Otezla IRA 2027 (0.217); GILD Biktarvy IRA 2028 (1.078); JNJ MFN (0.232). In v3 the MFN rows drop to π_min and every drift (T) row leaves the top five, so every company's top five changes.

Robustness on v2 (lower bounds computed by the review on the committed top-5 rows, no backfill from a sixth row):

| Variant | Rank 1-5 |
|---|---|
| As committed | AMGN 0.543, GILD 0.407, JNJ 0.195, AZN 0.113, MRK 0.097 |
| No N_eff term (raw top-5 sum) | GILD 1.166, AMGN 0.745, JNJ 0.326, ABBV 0.232, AZN 0.219 |
| MFN rows at π_min | AMGN 0.442, GILD 0.386, AZN 0.113, MRK 0.097, ABBV 0.064 |
| MFN at π_min, IRA rows at π 0.5 | AMGN 0.328, GILD 0.207, MRK 0.097, AZN 0.083, JNJ 0.053 |
| MFN at π_min, Biktarvy on the comparison formula (d - 0.20) | AMGN 0.442, GILD 0.277, AZN 0.113, MRK 0.097, ABBV 0.064 |
| MFN at π_min, AMGN receivables row at π_min | GILD 0.386, AMGN 0.184, AZN 0.113, MRK 0.097, ABBV 0.064 |

What v2 shows: AMGN and GILD are the top two in every variant; which is first depends on the concentration rule and on one row at a trigger edge; JNJ's third place was entirely its MFN row.

League v3 robustness table (`out/league_v3.md`, **[landing in league_v3]**; rows as published there):

| Variant | Rank 1-5 |
|---|---|
| As computed (v3 rules, H = 3) | [v3: pending] |
| No N_eff term (raw top-5 sum) | [v3: pending] |
| IRA rows at π 0.5 | [v3: pending] |
| Biktarvy on the comparison formula | [v3: pending] |
| AMGN receivables row at π_min | [v3: pending] |
| H = 6 | [v3: pending] |

The pick is made only from what survives every row of this table, and the pitch's "why it beat the other nine" sentence names rank, diversity (N_eff and the raw sum) and needle status, each with its number.

### 10.6 Sensitivity of the worked rows

The reviewed draft's ±50% table was computed on superseded values (DIO at the backtest π, Verzenio on the draft formula, H = 6) and is withdrawn. On the v3 values: H = 6 vs 3 for Verzenio S [v3: pending] (v2 0.0507 at H = 6); Verzenio at d = 0.38 / 0.60 scales S linearly with ΔRev (bull and bear rows of 10.4); r ±50% moves S by under 7% on both rows (reviewed draft, unchanged by v3). The league-level sensitivities are the robustness table in 10.5.

---

## 11. Weight derivation table (every constant, by code name)

Every constant in `agent/needle/quant/weights.py` and in the `decide_weights` block of `moves.py` has a row, under its code name; every row names its constant. "Used" says whether a scoring path reads the constant at ca12339 ("defined" means the family or channel it belongs to has no caller yet). Sensitivity is stated where it was computed; "inference" marks our derivations.

### 11.1 FIND (`weights.py` unless another module is named)

| Constant | Value | Meaning | Source | Used | Sensitivity |
|---|---|---|---|---|---|
| `ALPHA`, `BETA`, `GAMMA` | 1, 1, 1 | exponents on M, O, E | D3 (small-N argument; DeMiguel et al. and Gu-Kelly-Xiu by analogy) | yes (`find.score`) | exponents < 1 favour obscure-but-small findings, > 1 large public ones |
| `R` | 0.0785 | discount rate in M | Damodaran Drugs (Pharmaceutical), 228 firms, Jan 2026 | yes | S changes < 7% on the worked rows |
| `HORIZON_MONTHS` | 24 | impact window | case Part 2; materiality_spec §2 | yes | 12 months drops all IPAY 2028 rows to ΔEPS 0 |
| `ANCHOR_T_YEARS` | 0.5 | t_f for the anchor event | midpoint of the next four quarters (inference) | yes | small |
| `SIGMA_QUARTERS` | 8 | surprises in σ_EPS | our rule | yes | company-level scale |
| `SIGMA_ANNUALIZE` | 2.0 | √4 annualization | inference (independence) | yes | rescales every company equally; no rank change |
| `SIGMA_FY1_RATIO` | 0.041 | σ / EPS fallback ratio | median of 9 ratios on the draft table (review recomputes 5.2%) | fallback only; no shortlist company | scales a fallback company's M |
| `CM_PRICE` | 1.00 | flow-through of price, rebate, MFP, MFN | pharma_impact_math KQ7 inference; Drug Channels | yes | linear; 0.75 alternative (A16) not run |
| `CM_VOLUME` | 0.70 | flow-through of volume changes | KQ7 inference | yes | linear; 0.65 alternative not run |
| `ANCHOR` | 0.03 | margin-event size for fired accounting flags | backtest `margin_drop` threshold | yes | linear for anchor rows; reorders them against channel rows |
| `H_MONTHS` | v2 6.0; **3.0 [landing in league_v3]** | obscurity half-life | Lazy Prices; priced_in KQ5 "3 to 6 months" | yes | H = 6 is the sensitivity row of the robustness table |
| `H_VALUE` | 0.9 | headline-page coverage | materiality_spec §3 team rule | yes | at 0.45 headline topics can return to the top 5 |
| `Z_VALUE` | 1.0 | starter thread | case appendix; binary | defined (code uses the literal 1.0 in `obscurity.starter_thread`) | binary |
| `ATTENTION_QUARTERS` | 10 | quarters in a_f | priced_in_scorecard window | yes | |
| `LOE_AGE_MONTHS_DEFAULT` | 24.0 | age when disclosure date unknown | inference: patent dates are long public | yes | |
| `C_UNTESTABLE` (name to confirm in the v3 commit) | **0.5 [landing in league_v3]** (v2: 0) | c_f when the consensus test cannot run | inference: an even chance analysts priced it (review A12) | v3 | halves D on untestable type C rows |
| `G_EXACT` | 1.00 | grade, exact and substring | deterministic check | yes | |
| `G_FUZZY` | 0.90 | grade, fuzzy | citation note KQ4 inference | yes | only non-exact rows move |
| `G_LLM` | 0.85 | grade, LLM-derived arithmetic | FinanceBench oracle-page accuracy (Islam et al. 2023) | defined | |
| `G_ENTAILED` | 0.745 | grade for number_match; E cap on v2 placeholder rows | Liu et al. 2023 (a citation-support share, used as a rung value) | yes | |
| `G_NONE` | 0.0 | unverified | gate | yes | |
| `DELTA_OOS` | 0.26 | data-mining haircut on backtest excess rates | McLean-Pontiff 2016 | yes | scales the five backtest families equally |
| `D_PUB` | 0.58 | post-publication decay | McLean-Pontiff 2016 | yes (cancels) | none on ranks |
| `ALPHA_TZ` | 11.39 | anchor hedge return, % | Thomas-Zhang 2002 | yes | inverse scale of converted families |
| `PI_INVENTORY` = `PI_ANCHOR` | 0.0466 | (20.6% - 14.3%) x 0.74 | backtest | yes | scales every converted family |
| `PI_DIO` | 0.0318 | (21.7% - 17.4%) x 0.74 | backtest | yes, if fired | linear |
| `PI_RECEIVABLES` | 0.0629 | (22.8% - 14.3%) x 0.74 | backtest | yes, if fired | linear; AMGN row at π_min in the robustness table |
| `PI_DSO` | 0.0851 | (25.6% - 14.1%) x 0.74 | backtest | yes, if fired | linear |
| `PI_GROSS_MARGIN_DROP` | 0.0422 | min(margin, hard) excess 0.057 x 0.74 | backtest; gate 2 | yes, if fired | linear |
| `PI_MISSTATEMENT` | 0.0491 | anchor x 12 / 11.39 | Beneish-Lee-Nichols 2013 (12%/yr rounded up, inference) | defined (no detector) | |
| `PI_RISK_FACTOR` | 0.0226 | anchor x 5.52 / 11.39 | Lazy Prices VW 0.46%/month | yes (v3: tier only) | |
| `PI_LITIGATION_TEXT` | 0.0349 | anchor x 8.52 / 11.39 | Lazy Prices 71 bps/month | yes (v3: tier only) | |
| `PI_MDNA` | 0.0081 | anchor x 1.98 / 11.39 | Lazy Prices Table VII | yes (v3: tier only) | |
| `PI_INSIDER` | 0.0201 | anchor x 4.92 / 11.39 | Cohen-Malloy-Pomorski | defined (no detector) | |
| `PI_8K` | 0.0061 | anchor x 1.5 / 11.39 | Lerman-Livnat 2010 | defined (no detector) | |
| `PI_MIN` | 0.0055 | anchor x 1.34 / 11.39 | Chen-Hollander-Law (WP) | yes: directional rows, MFN (v3) | floor for directional families |
| `PI_NONE` | 0.0028 | π_min / 2 | forensic note tier halving (inference) | yes (v3: tier only) | |
| `PI_CONTRACTUAL` | 1.0 | statute-dated or booked | by definition | yes: IRA, LOE | IRA at 0.5 in the robustness table |
| `PI_REASONABLY_POSSIBLE` | 0.5 | ASC 450 midpoint | inference | defined (no extractor) | |
| `PI_FAVORABLE_LEVEL` | 0.0 | favourable row, no scenario | 4.1 | yes | |
| `ONC_D_BULL`, `ONC_D_BASE`, `ONC_D_BEAR` | 0.38 / 0.50 / 0.60 | oncology MFP list discount for IPAY 2028 | CMS IPAY 2026-2027 (Imbruvica, Ibrance, Pomalyst) | yes | linear |
| `M_MDP_CATASTROPHIC` | 0.20 | MDP rate the MFP replaces | CMS MDP final guidance | comparison field only | |
| `M_MDP_INITIAL` | 0.10 | initial-phase MDP rate | CMS MDP final guidance | defined | |
| `G_PRE_GLP1` | 0.60 / 0.675 / 0.75 | pre-MFP concession, GLP-1 | inference from company GTN (Novo 69% from its 20-F; Lilly about 60%) | comparison field only | |
| `G_PRE_INSULIN` | 0.75 | insulin | inference | defined | |
| `G_PRE_IMMUNOLOGY` | 0.50 / 0.575 / 0.65 | immunology | inference | comparison field only | |
| `IRA_HEADLINE_RANGE` | 0.38 to 0.85 | cycle 1-2 discount range | CMS | defined | |
| `find.K_NET` | 0.3 / 0.4 / 0.5 | IRA net hit / list discount, rebated classes | pharma_impact_math KQ2 inference | yes (the IRA formula) | IRA rows linear in k |
| `find.LOW_REBATE` | Verzenio, Erleada, Pomalyst, Ibrance, Calquence, Biktarvy | k = 1.0 classes (oncology, HIV) | KQ2 "near 1.0x for low-rebate oncology"; HIV by inference | yes | Biktarvy on the comparison formula in the robustness table |
| `find.ALL_CUTS` | 0.38 / 0.655 / 0.85 | d with no same-class analog | `ira_cut_check.csv` smallest / median of 16 / largest | yes (Biktarvy, Botox) | |
| `find.IMM` | 0.65 / 0.66 / 0.67 | immunology analog d | CMS (Otezla, Stelara, Enbrel) | yes | |
| `find.DIAB` | 0.66 / 0.71 / 0.85 | diabetes analog d | CMS (Jardiance, Ozempic, Janumet) | yes | |
| `find.ANNUAL_TRIGGER` | inventory 0.10, receivables 0.08, DIO 0.15, DSO 0.10 | backtest flag triggers for annual rows | `backtest.signals_at` thresholds | yes | AMGN's 8.0-pt row sits on the 0.08 edge |
| `S_MFN` | 0.003 / 0.0065 / 0.010 | Medicaid MFN share of US revenue | Pfizer "<1% of US net"; midpoint inference | v2 dollars; **v3 internal M only, never printed** | |
| `R_BIOLOGIC` | 0.65 / 0.35 / 0.20 | LOE retention years 1-3 | Humira, Stelara, IQVIA (KQ4) | yes | linear in (1 - R) |
| `R_SMALL_MOLECULE` | 0.30 / 0.15 / 0.10 | LOE retention years 1-3 | KQ4; IQVIA | yes | linear |
| `impact.loe` inline | 0.8 / 1.2 x base | LOE bull / bear band | inference | yes | |
| `BOXED_WARNING` | -0.10 to -0.25 | US volume after a new boxed warning | research-note inference | defined (product table) | |
| `REMS` | -0.05 to -0.15 | new starts vs non-REMS rival | KQ6 inference | defined | |
| `WEEKLY_VS_DAILY` | +0.10 to +0.15 | revenue per starter, 2 years | inference from HR 0.80 | defined | |
| `DSO_STAR` | 7.0 days | DSO excess that switches receivables to the reversal channel | KQ5 inference (BMS base rate) | defined (`dso_reversal` not wired) | |
| `impact.tariff_note` default `rates` | 0.15 / 0.20 / 1.00 | Section 232 rates after 2029-01-20 | Proclamation 11020; Crowell | note only | |
| `E_HIGH` | 0.95 | HIGH threshold | between fuzzy and exact | yes | |
| `E_MED` | 0.745 | MEDIUM threshold | the number_match grade | yes | |
| `NEEDLE_O` | 0.5 | needle floor (v2 on O; **v3 on D**) | ICD 203 "roughly even chance" midpoint | yes | at 0.25 more rows qualify; strict-needle count in league_v3 |
| `NEEDLE_E` | 0.90 | needle evidence floor | quoted evidence only | yes | at 0.745 number_match rows could headline |
| `N_STAR` | 3 | blocks for full league credit | design choice (D11) | yes | inert at or above max N_eff (2.19 in v2) |
| `TOP_N` | 5 | findings summed | case minimum of five | yes | |
| `K_PEERS` | 6 | nearest financial peers off-shortlist | inference (engine needs ≥ 4) | defined (rule not built) | |
| `data.PER_SHARE` | ZEN x 2.0 | I/B/E/S per-ADR to per-share | AZN ADR ratio (review A2) | yes | AZN σ 0.5408 |
| `data.company` ETR band | [0, 0.40] -> peer median 0.185 | ETR fallback | our rule | yes (MRK, PFE, GILD) | company-level scale |
| `find.stage_split` cut-off | finished share < 0.5 | "capacity build" | inference | yes | |
| `cite.verify.FUZZY_THRESHOLD` | 90 | fuzzy rung | inference (noise 93-99, paraphrase 60-80) | yes | |

### 11.2 DECIDE (`moves.py` `decide_weights` and the other `moves.py` / `kill.py` constants)

| Constant | Value | Meaning | Source | Sensitivity |
|---|---|---|---|---|
| `WACC` | 0.0785 | discount rate | Damodaran Jan 2026 (team choice; DiMasi 10.5% real as the hurdle alternative) | long-tail moves (M3, M7) most sensitive |
| `P_SCENARIO` | bear 0.50 / base 0.11 / bull 0.39 | scenario weights | Trinity 2023 US launches | toward Deloitte (36% miss) raises launch-move EV |
| `MULT_SCENARIO` | 0.8 / 1.0 / 1.2 | revenue multipliers | ZS failure / success boundaries | spread scales linearly; EV biased up (A22) |
| `WINDOW` | 24 | decision window, months | case | |
| `PAYBACK_SEARCH` | 120 | payback search, months | spec 5.4 | |
| `POST_LAUNCH_MONTHS` | 120 | TV horizon after launch | spec 5.1 | |
| `NON_NME` | 0.575 / 0.375 / 0.675 / 0.915 | non-NME phase rates | BIO 2021 Figure 9 | reference P 0.6176 |
| `BIO_TA` | by TA (e.g. oncology 0.488 / 0.246 / 0.477 / 0.920) | phase rates by therapeutic area | BIO 2021 Figure 1 | trial moves linear in P_alive |
| `TRIAL_COST_PLACEBO` | 28.8 | per pivotal trial, $M | Moore et al. 2018 | CaR and payback |
| `TRIAL_COST_ACTIVE` | 48.9 | active-comparator trial | Moore et al. 2018 | |
| `TRIAL_COST_MEDIAN` | 19.0 | median pivotal trial | Moore et al. 2018 | |
| `TRIAL_COST_CARDIO` | 157.0 | cardiovascular pivotal trial mean | Moore et al. 2018 | |
| `REP_COST` | 176.5 ($K per rep-year) | loaded rep cost | Rework 2025, vendor estimate | M6 cost |
| `REP_RAMP_MONTHS` | 18 | rep ramp | Rework 2025 | M6 |
| `PROMO_SHARE` | 0.108 | promotion share of US sales | CBO 2008 | M6 response |
| `EPS_PROMO` | 0.06 (0.05-0.30) | promotion elasticity | Datta-Dave NBER w19592; range inference | M6 sign flips between 0.06 and 0.30 |
| `PLANT_CAPEX_HIGH` | 6,500 | plant capex | DCAT 2025; Lilly Texas API site | M7 CaR |
| `PLANT_BUILD_MONTHS` | 48 | build time | DCAT 2025 (3-5 years) | M7 |
| `PREMIUM_MEDIAN` | 0.63 | M&A premium | Evercore precedents, Cidara SC 14D9 | dominates M1 EV and CaR |
| `EV_PEAK_LOW`, `EV_PEAK_HIGH` | 0.5x, 1.0x peak sales | M&A price cross-check | Furiex DEFM14A | |
| `UPFRONT_SHARE` | 0.06 | licensing upfront | Goodwin 2025 3.7% early, about 5-7% overall (6% is our midpoint) | M2 CaR |
| `CM_EXISTING` | 0.85 | existing-brand incremental margin | inference from Damodaran 71.73% GM, 21.91% SG&A | linear |
| `CM_ACQUIRED` | 0.7173 | acquired-product margin | Damodaran Jan 2026 | linear |
| `CM_VOLUME` | 0.70 | volume flow-through | KQ7 inference | |
| `CM_PRICE` | 1.0 | price flow-through | KQ7 | |
| `UPTAKE_MONTHS` | 39.9 (v3: one 24-month ramp, **[landing in league_v3]**) | months to peak | IQVIA 2021, 813 launches | in-window revenue |
| `LOE_RETENTION` | biologic 0.65 / 0.35 / 0.20; small molecule 0.30 / 0.15 / 0.10 | LOE curves | 4.3 e | M5 |
| `MFN_SHARE` | 0.0065 | Medicaid MFN share (registered; no template reads it) | Pfizer base rate, inference | none; MFN is direction-only in FIND |
| `TARIFF_RATE` | 0.15 | tariff on imported cost | Proclamation 11020; Crowell | M7 benefit |
| `MCDA_WEIGHTS` | 0.25 each | MCDA criteria | inference (ISPOR weighting text not retrieved; 1/N) | matters only when EV intervals overlap |
| `COMMERCIAL_MULT_CAP` | 1.2 | execution-risk divisor | spec 5.4 | |
| `DTC_TV_LOW`, `DTC_TV_HIGH` | 260, 440 ($M/yr) | DTC TV spend | iSpot via Fierce Pharma | M6 cost |
| `PLANT_CAPEX_LOW` | 1,000 | plant capex low | DCAT 2025 | |
| `PLANT_DEPR_YEARS` | 15 | depreciation life | inference | |
| `DEV_MILESTONE_SHARE` | 0.33 | development milestones | Goodwin 2025 | M2 |
| `SALES_MILESTONE_SHARE` | 0.64 | sales milestones | Goodwin 2025 | M2 |
| `ROYALTY_EARLY`, `ROYALTY_LATE` | 0.065, 0.113 | royalty midpoints | Goodwin 2025; LES 2014 | linear in M2 inflows |
| `UPTAKE_MONTHS_ONC` | 60 | oncology months to peak | 21 drugs, median | |
| `LABEL_RAMP_MONTHS` | 42 (v3: 24, **[landing in league_v3]**) | M3 ramp to peak | v2 reference case; v3 one ramp | 60 months gives EV 1,265.2 on the reference case |
| `COVERAGE_LAG` | 9 | months to majority coverage | Tufts/ICER (6-12) | in-window revenue |
| `TARIFF_START_MONTH` | 27 | months from as_of to 2029-01-20 | Proclamation 11020 | |
| `SELF_PAY_SHARE` | 0.35 | self-pay share threshold | LillyDirect Q2 2025 | kill signal |
| `SKYRIZI_OFFSET` | 0.49 | successor-brand growth precedent | AbbVie 10-Q Q3 2024 | M5 |
| `FAVORABLE_LEVEL_KINDS` | `gross_margin_peer_outlier` | excluded from the fit denominator | D5 | |
| `kill.ZS_LIKELIHOOD` | bear 1.0 / base 0.55 / bull 0.10 | P(breach given s) | ZS; base 0.55 inference | base at 0.275 or 0.825 moves posterior bear 0.834 to 0.88 or 0.80 |
| `kill.COVERAGE_LIKELIHOOD` | 1.0 / 0.75 / 0.50 | coverage breach | inference | |
| `kill.P_BEAR_AFTER_MISS` | 0.70 | p_bear after a year-one miss | Deloitte 2022; McKinsey 2014 | |

### 11.3 Product table (`product.py`)

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `GTN_BAND` | bear 0.50 / base 0.60 / bull 0.70 | v2 IRA-MFP channel GTN (comparison field after v3) | inference from company GTN anchors |
| `CM_DEFAULT` | 0.70 | product-channel CM (volume channels); the IRA channel uses `CM_PRICE` 1.00 after v3 | KQ7 |
| inline capture | 0.50 / 0.35 / 0.20 | label-breadth capture | assumed |
| inline share moved | 0.40 / 0.25 / 0.10 | cash-price scenario | assumed |
| inline boxed-warning share | 0.25 / 0.10 / 0 | boxed-warning channel | inference |
| priced-in thresholds | share ≥ 0.5 with starter match, or ≥ 0.8 | growth-limiter call | our rule |

---

## 12. One-slide version

```
FIND    S = M · O · E · π        M = |ΔEPS| / σ_EPS (discounted)        O = D · 2^(-age/3mo),  D = Π (1 - known_i)
DECIDE  EV = Σ_s p_s · rNPV_24m(move | s)      reported for every move: EV (in-window + TV), cash at risk, payback, spread, MCDA
```

| S tier | Reads as |
|---|---|
| **High** | a scheduled or booked event, material against this company's usual EPS miss, quoted on two independent primary sources |
| **Medium** | a tested accounting flag that fired, or a scheduled event the market already discusses |
| **Low** | quantified but small, or heavily discussed |
| **Not quantified** | real and cited, shown with its evidence tier, no dollar figure |

1. **M, materiality:** the finding's EPS impact in dollars, divided by how much Wall Street usually misses this company's EPS by.
2. **O, obscurity:** the chance nobody has priced it: not the case's starter thread, not on the press-release front page, not asked by analysts, not in consensus; fading with a 3-month half-life. The Sharpest Needle must clear the "not discussed" part on its own.
3. **E, evidence:** the chance the documents say what we claim; every quote and number is re-checked on its cited page, and anything that fails is withheld.
4. **π, track record:** how often this kind of signal turns into the bad outcome, shown as a tier (scheduled, tested flag, published evidence, direction only).
5. **League and DECIDE:** a company's score is its top five findings, scaled down when one block of evidence carries it (L = sum x N_eff / 3); the pick survives a published robustness table. Every move is valued on one 24-month cash scale with numeric 6-to-12-month kill signals.

---

## 13. Sources

Case and team materials
- Case: `gap-data/docs/case/fine_print_case.pdf`; rubric: `gap-data/docs/case/judging_rubric.pdf`.
- Research notes: `~/research_notes/Fine Print quant model design/` (`needle_engine_and_moat_audit.md`, `filing_text_forensic_signals.md`, `pharma_impact_math.md`, `priced_in_and_attention_metrics.md`, `strategic_move_valuation.md`, `citation_grounded_llm_design.md`). Where this spec cites "KQn", the number is the note's key question, and the note's own inferences are labelled inference here.
- Code: `agent/needle/quant/*.py`, `agent/needle/cite/*.py`, `agent/moat/cite.py`; docs `docs/citations.md`, `docs/decide.md`, `docs/product_fineprint.md`, `docs/needle_gate2.md`, `docs/league_v2_note.md`; backtest summary `out/backtest/hit_rates.json`.
- Adversarial review of the draft: scratchpad `review/synthesis.md`, `r1_A.md`, `r1_B.md`, `r2_A.md`, `r2_B.md`.

Forensic and text signals
- Cohen, Malloy, Nguyen, Lazy Prices, NBER w25084: https://www.nber.org/papers/w25084.pdf ; NBER Digest: https://www.nber.org/digest/nov18/are-investors-inattentive-sec-mandated-corporate-reports
- Thomas and Zhang 2002, RAST: https://www3.ntu.edu.sg/home/HuaiZhang/inventory%20paper-RAST.pdf
- Beneish 1999 M-score: https://bpb-us-w2.wpmucdn.com/u.osu.edu/dist/3/40936/files/2016/12/M-Score-pa6gdy.pdf ; Beneish, Lee, Nichols 2013: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2241717
- Dechow, Ge, Larson, Sloan 2011: https://www.thecaq.org/wp-content/uploads/2018/03/Dechow-et-al-2011-Contemporary_Accounting_Research.pdf
- Cohen, Malloy, Pomorski, Decoding Inside Information: https://www.nber.org/papers/w16454.pdf
- Lerman and Livnat 2010: https://archive.nyu.edu/bitstream/2451/27579/2/SSRN-id1126816.pdf
- Gow, Larcker, Zakolyukina 2021: https://onlinelibrary.wiley.com/doi/abs/10.1111/1475-679X.12371
- Chen, Hollander, Law (summary): https://www.aaii.com/journal/article/conference-calls-no-or-few-questions-are-costly
- Abarbanell-Bushee decay (Dorey, Kim, Shin 2017): https://www.emerald.com/insight/content/doi/10.1108/MF-05-2016-0142/full/html
- McLean and Pontiff 2016: https://Www.Gwern.net/doc/economics/2016-mclean.pdf
- DeMiguel, Garlappi, Uppal 2009 (cited by analogy): https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html
- Gu, Kelly, Xiu 2020 (cited by analogy): https://www.nber.org/papers/w25398.pdf

Priced-in, attention, validation
- Hong, Lim, Stein 2000: https://www.nber.org/digest/nov98/bad-news-travels-slowly
- Chen, Nagar, Schoenfeld 2018: https://ideas.repec.org/a/spr/reaccs/v23y2018i4d10.1007_s11142-018-9453-3.html
- Diether, Malloy, Scherbina 2002: https://www.kellogg.northwestern.edu/faculty/mcdonald/ftp/practicum/papers/dms3.pdf
- Hong, Li, Ni, Scheinkman, Yan 2015 (days to cover): https://www.nber.org/papers/w21166.pdf ; FINRA short interest: https://finra.org/filing-reporting/short-interest
- Kothari and Warner: https://www.bu.edu/econ/files/2011/01/KothariWarner2.pdf
- ICD 203 bands (secondary): https://www.cisecurity.org/ms-isac/services/words-of-estimative-probability-analytic-confidences-and-structured-analytic-techniques

Pharma impact math
- CMS IPAY 2026 negotiated prices: https://www.cms.gov/newsroom/fact-sheets/medicare-drug-price-negotiation-program-negotiated-prices-initial-price-applicability-year-2026
- CMS IPAY 2028 selected drugs: https://www.cms.gov/files/document/factsheet-medicare-negotiation-selected-drug-list-ipay-2028.pdf
- MDP interaction: https://www.healthaffairs.org/content/forefront/interaction-between-manufacturer-discount-program-and-medicare-drug-price-negotiation ; CMS MDP guidance: https://www.cms.gov/files/document/manufacturer-discount-program-final-guidance.pdf
- Drug Channels GTN: https://www.drugchannels.net/2026/07/2025-gross-to-net-realities-at-eight.html (the Novo 69% figure is from Novo's 20-F)
- MFN: https://www.healthaffairs.org/content/forefront/trump-administration-s-deals-pharma-policy-progress-political-theater ; Pfizer Medicaid MFN: https://pmc.ncbi.nlm.nih.gov/articles/PMC13119475/ (the 0.3-1.0% range is the research note's inference)
- Section 232: https://www.crowell.com/en/insights/client-alerts/trump-administration-imposes-section-232-tariffs-on-patented-pharmaceutical-imports-tiered-rate-structure-takes-effect-beginning-july-31-2026
- LOE: https://www.iqvia.com/locations/united-states/blogs/2025/07/the-rules-of-loss-of-exclusivity-are-being-rewritten
- Boxed warnings: https://www.mayoclinicproceedings.org/article/S0025-6196(11)61081-1/fulltext ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8159769/
- Weekly dosing persistence: https://link.springer.com/article/10.1007/s13300-021-01189-6

Strategic moves
- BIO/Informa/QLS 2021: https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf
- Stewart, Allison, Johnson 2001: https://www.nature.com/articles/nbt0901-813
- Damodaran WACC: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html
- Moore et al. 2018 (summary): https://www.ajmc.com/view/more-than-100fold-cost-differences-found-for-pivotal-trials
- Cidara SC 14D9: https://www.sec.gov/Archives/edgar/data/1610618/000119312525309970/d59361dsc14d9.htm ; Furiex DEFM14A: https://www.sec.gov/Archives/edgar/data/0001484478/000119312514225775/d727381ddefm14a.htm
- Goodwin licensing 2025: https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals
- Datta and Dave: https://www.nber.org/papers/w19592
- Trinity launches: https://www.emarketer.com/content/50--of-us-drug-launches-2023-missed-first-year-revenue-targets ; ZS launch signals: https://www.zs.com/insights/pharma-product-launch-success-signals
- AbbVie Humira LOE: the CFO's words were "the vast majority of the impact ... is going to be price"; "mostly from price" is the research note's paraphrase.

Citations and LLM reliability
- Anthropic citations: https://platform.claude.com/docs/en/build-with-claude/citations ; search results: https://platform.claude.com/docs/en/build-with-claude/search-results ; structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Text fragments: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Text_fragments
- FinanceBench: https://arxiv.org/abs/2311.11944 ; Liu et al. verifiability: https://arxiv.org/abs/2304.09848
- Xiong et al. calibration: https://arxiv.org/html/2306.13063v2 ; Dahl et al.: https://arxiv.org/html/2401.01301v1

---

## 14. Changes from the reviewed draft

Finding ids are from the adversarial review (synthesis.md). "Code" means the change is in ca12339; "v3" means it is landing in league_v3; "spec" means text only.

1. **A1, D5.** Backtest π only when the row meets the flag's trigger (code); unfired rows not quantified (v3). LLY DIO S 0.00973 withdrawn (10.3).
2. **R3, A9, B6, B9, S2, D2.** π = 1 reserved for statute-dated or booked amounts (spec); label rows and trial stops M = 0 (code); MFN direction-only at π_min with no dollar figure (v3).
3. **A15, S3.** One IRA formula, ΔRev = G · d · k (code in FIND; v3 in product and DECIDE); the draft's G · (d - g_pre) kept only as `S_spec_formula`.
4. **R1, A11, B5, B-3.** O split into discussion D and decay τ; needle floor on D; H = 3 base, 6 sensitivity (v3). "Does not silently relax" deleted; the coded fallbacks (provisional, floor relaxed) stated (spec).
5. **R2, A20, B4, B7.** Anchor only for fired backtest flags; everything else "not quantified" and out of the top five (v3); "no peer analogue" in the deck (spec).
6. **A12.** c_f = 0.5 when untestable (v3).
7. **A18, B-4, B21.** League term described as N_eff / 3 scaling; raw sum shown; robustness table (v3).
8. **S1.** Same-fact de-duplication; AZN duplicate receivables row removed (v3).
9. **B10, B11, B12, B13.** Section 6 rewritten to match `agent/needle/cite` and `docs/citations.md`: five statuses, fuzzy 90, number_match graded 0.745, gate rule, deep links per document type with plain DailyMed setid pages, Bloomberg licence gate, no public viewer (spec); transcript speaker check ported (v3).
10. **A2, A3, R4, B8.** AZN per-share σ (code); fallbacks "not league-comparable" (code); 2x labelled inference; imputed headline for 20-F filers (code); NVO USD channels not converted (code).
11. **A16, A17, A26, A27.** CM conflict disclosed; σ_LLY 2.0295; source attributions corrected (DeMiguel by analogy, Novo 69% from its 20-F, Lazy Prices paraphrase, ICD 203 midpoint, MFN range as inference, label elasticities as inference, "four routes", 10-pt inventory trigger, CFO quote); every code constant in Section 11 by name (spec).
12. **A21, A22, A23, A24, B15, B16.** DECIDE: 7.85% stated as the team's choice; scenario-basis bias stated; one consistent 24-month ramp and the reference case labelled by ramp (v3); strategic fit on M · E (v3); decider-evidence table in the deck (spec); DECIDE to run on the picked company's v3 findings (open).
13. **A25, A10, D5.** Validation: N ≤ 9 sealed calls, base-rate null, backtest panel absent and what that blocks (spec).
14. **B1.** Product fine print integrated as Section 4.11 with the one IRA formula (spec; v3 for the formula import).
15. **B2.** "Where AI is in the build" in `docs/ai_in_the_build.md`, summarized in Section 9 (spec).
16. **B3, B14.** Built / not-built column in the π table from `MISSING_DETECTORS` (spec).
17. **B17.** New-ticker path as a recorded VRTX run (spec).
18. **B19, B20.** Honest limits replaced by the review's limit sentences plus the open disagreements (spec; also `docs/honest_limits.md`); facts count 69,553 total, 10,963 verified.
19. The reviewed draft's "Implementation notes" appendix is folded into the body and removed; its "Product fine print (appended)" section is now Section 4.11.
