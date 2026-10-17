# Quant model specification: FIND and DECIDE

Version 1.0, 2026-10-17. Owner: quant-model worktree (`docs/quant_model.md`). Archive copy: `~/reports/Fine Print quant model design.md` (identical).
Readers: (a) engineers implementing tonight, (b) the pitch writer, (c) judges, including a quant reviewer.
Conventions: every constant carries a source (paper and number, or our backtest and number) or the label **inference** (our derivation, stated). Numbers are quoted exactly as the source states them. Dollar figures are USD millions unless marked. No constant in this document is meant to be tuned by eye; Section 11 lists every one with its sensitivity.

---

## 1. Purpose and what the case asks

The case ("The Fine Print: Find the Story, Then Make the Call") asks a team to:

- **Part 1, Find.** Pick one of ten pharma companies and explain why it beat the other nine; deliver at least five findings, each with a one-sentence finding, a source (filing and page, or speaker and exact quote), an impact estimate on revenue, operating income or EPS "with the math shown", a peer comparison, and a high/medium/low confidence "based on how solid the evidence is"; name the **Sharpest Needle**, "the single most material and least-discussed finding"; compare one product with its rivals and tie that to a financial finding.
- **Part 2, Decide.** Recommend one 24-month CEO move with a budget, the Part 1 findings that drive it, cost and return "with the math shown", the two strongest rejected alternatives, and early 6-to-12-month signals that would prove the move wrong.
- **Judging.** Seven equally weighted categories scored 1 to 4: Innovation, Technical Execution, Use of AI and Responsible Design, Completeness (including "limitations are stated clearly and honestly"), Design and Usability, Impact, Presentation. The rubric credits only what is demonstrated.

The case also states the constraint that drives this model: "Patent cliffs and exclusivity losses are public and priced in. The points go to signals a press-release skim would miss", and "AI tools invent page numbers, mix up figures from different years, and misquote executives."

So the model has to answer four quantitative questions on any pharma ticker:

1. How big is a finding relative to what the market usually gets wrong about this company? (materiality, M)
2. How likely is it that the market has not already priced it? (obscurity, O)
3. How sure are we that the documents say what we claim? (evidence, E)
4. How often does this kind of signal actually turn into the adverse outcome it implies? (prior, π)

Model 1 (**FIND**) multiplies those four. Model 2 (**DECIDE**) values candidate CEO moves on one 24-month cash scale whose inputs are the FIND findings. A citation contract makes every number and quote in either model's output clickable to its source page, and blocks any claim whose citation does not verify.

### The two equations

```
FIND    S_f = M_f · O_f · E_f · π_k(f)

        M_f = |ΔEPS_f| · (1 + r)^(-t_f) / σ_EPS
        O_f = (1 - z_f)(1 - h_f)(1 - a_f)(1 - c_f)(1 - s_f) · 2^(-age_f / H)
        E_f = min over key claims j of [ 1 - Π_{i in cites(j)} (1 - g_i) ]
        π_k = excess probability that signal family k is followed by its adverse outcome (Section 4.6)

DECIDE  EV_m = Σ_s p_s [ Σ_{τ=1..24} ( P_alive(τ)·CF^in_{m,s,τ} - P_reach(τ)·CF^out_{m,τ} ) / (1 + r_mo)^τ  +  TV_{m,s,24} / (1 + r_mo)^24 ]
```

Legend in Section 12. Exponents on M, O, E are 1 by design (Section 2, D3).

---

## 2. Design decisions

Each decision states what the orchestrator asked, what this spec does, and why. Where this spec departs from the brief it says so.

**D1. Two models, one data layer.** Adopted as briefed. FIND scores findings; DECIDE consumes FIND output objects (by `finding_id`) as its inputs, so every DECIDE parameter that came from Part 1 is traceable to a cited finding (Section 5.2).

**D2. Multiplicative, not additive in levels.** The case defines a finding conjunctively: material AND not obvious AND provable. A product encodes AND: any factor at zero zeroes the score (an unverifiable claim, E = 0, can never rank; a starter-thread item, O = 0, can never be the Sharpest Needle). A levels-additive score is compensatory and would let a perfectly obscure but unverified claim outrank a verified one, which is the failure the case warns about. Multiplicative and log-additive are the same ranking (log S = log M + log O + log E + log π), so the choice is not "multiplicative versus log-additive" but "conjunctive versus compensatory"; we compute in logs for numerical stability and report S in levels because S then has a meaning: **expected EPS impact attributable to the finding, in units of the company's usual EPS surprise, times the probability it is unpriced, times the probability the documents say what we claim.**

**D3. Exponents α = β = γ = 1.** Not tuned, and this is a deliberate choice, not a placeholder. (i) The expected-value reading of S in D2 holds only with unit exponents; any other value makes S a utility with a risk attitude we cannot justify. (ii) Estimating three exponents needs labeled outcomes on hundreds of findings; we have about 120 live firm-quarters (10 companies x about 12 quarters, audit Section 5) and 1,410 backtest firm-quarters that test only five accounting flags. DeMiguel, Garlappi and Uppal (RFS 2009) show sample-based weights need "about 3,000 months with 25 assets and about 6,000 months with 50 assets" to beat 1/N; Gu, Kelly and Xiu report monthly out-of-sample R2 of only 0.33-0.40% for the best ML models on 30,000 stocks. With our N, fitted exponents would fit noise. (iii) Section 11 reports what a ±50% change in each exponent does to the ranking.

**D4. Drop the old Z (peer z) and D (trend) multipliers and the constant T from S.** The old score `S = I_norm·P·T·O·E·(1+0.25 max(Z,0))·(1+0.25 D)` used 0.25 weights described in `docs/materiality_spec.md` as "a starting guess". Peer z is a MAD z across 10 business-model-heterogeneous firms (audit 1.14 items 2-3) and has no published link to fundamental outcomes; it moves to the peer-comparison column and to the confidence rule (diagnosticity). Trend D is folded into family selection (a "trend" signal is a different family with its own π). T was a constant 0.926 for every finding (audit 1.6), so it ranked nothing; timing now enters M as a real discount to the fiscal year the impact lands in, at Damodaran's January 2026 pharma WACC (7.85%).

**D5. A real bug drives the current league table, and the new model removes it.** Running the committed scorer locally (scratch copy, `python -m agent.needle.run --all`, reproduced `out/league.json` to 4 decimals for LLY 0.3034) shows LLY's lead is not the DIO finding the audit suspected. It is `gross_margin_peer_outlier` "Gross margin 85.8% (Q2 2026) vs peers; peer median 74.1%, z +1.8" with I_norm capped at 1.0 because `score._impact` multiplies the margin **level** (0.858) by TTM revenue (audit weakness 5). That one finding is S = 0.2437 of LLY's 0.3034 (80.3%). It is also favorable (LLY's margin is higher than peers). Under FIND it has no adverse scenario and π = 0 (Section 4.6). With only that row removed, LLY drops from 1st to 6th (Section 10.4). The pitch should not claim LLY "won" on the old league table.

**D6. π is an excess probability on a common outcome scale, derived three ways.** Our own backtest gives fired-vs-not-fired hit rates for five accounting flags on a fundamental outcome (gross-margin compression). The literature gives return alphas for text, insider and call signals. To put both on one scale we anchor on the one family that has both: inventory growth (Thomas and Zhang 2002 hedge return 11.39% and our backtest's +6.3 point excess margin-drop rate). Return-only families are converted by the ratio of their published hedge return to the anchor's (Section 4.6). This "return-to-probability" conversion is an **inference** and the most likely point of challenge; its defence is that Lazy Prices itself finds returns accrue only "when the information is later revealed through news or earnings", which is what proportionality assumes. Contractual or legally scheduled events (an IRA selection, a statutory exclusivity date, a booked liability) get π = 1 and carry their uncertainty in the impact range instead.

**D7. Post-publication haircuts cancel inside the anchor ratio, and the data-mining haircut does not.** McLean and Pontiff (JF 2016): "portfolios earned about 26% less out-of-sample and about 58% less post-publication". All return-based families we use are published, so the 58% applies to numerator and anchor alike and cancels in the ratio. Our own backtest rules and results were produced in one commit (gate 2, disclosed), so every backtest-derived excess rate is haircut by the 26% out-of-sample (data-mining upper bound) figure. Fundamental predictability is the thing we score, and it decays less than returns: Abarbanell and Bushee's signals lost their hedge return after publication "though predictive power for earnings held" (Dorey, Kim, Shin 2017). We therefore do not apply the 58% to fundamental outcomes.

**D8. Obscurity is a noisy-OR of independent "ways the market could already know".** O = probability that none of the channels (starter thread, headline page, analyst questions, consensus, short sellers) has priced the finding, times a decay in its age. Independence across channels is an **inference**; it makes O conservative when channels overlap (it double-penalizes rather than double-rewards).

**D9. Half-life H = 6 months.** Lazy Prices: negative alpha "persists and increases up to 6 months out, never reversing" and accrues "out to 18 months"; the priced-in note's calibration puts filing-only information at "a half-life on the order of 3 to 6 months". We take the upper end of that range because our companies are mega-caps whose 10-Ks are read by many, but Lazy Prices' value-weighted (large-cap-tilted) results are still significant. ±50% (3 or 9 months) is in Section 11.

**D10. Confidence is deterministic; the LLM never sets it.** ICD 203 separates confidence (sourcing quality) from likelihood. Our label is a fixed function of E, independent-source count, claim kind and diagnosticity. The LLM's verbalized confidence is used only to break exact ties (Section 4.7) and the adversarial trial can only lower a label, never raise it. Reason: verbalized confidence clusters at 80-100% and has ECE 0.18 to 0.52 across models (Xiong et al. 2023); legal LLMs "systematically overestimate their confidence" (Dahl et al. 2024).

**D11. League score with a concentration penalty at the evidence-block level.** Sum of the top five S, multiplied by min(1, N_eff / 3) where N_eff is the inverse Herfindahl of S across evidence blocks. Penalizing at block level, not finding level, follows the forensic note's warning that inventory, receivables and accruals "overlap heavily ... and should not be triple-counted". N* = 3 is the number of blocks the literature shows to be roughly orthogonal (accounting, text/disclosure, contractual/policy). Section 4.9.

**D12. DECIDE values cash, not stories.** One 24-month scenario-weighted rNPV with explicit monthly cash flows and a terminal value at month 24, so a trial that reads out in month 30 is still valued, and the two rejected moves get the same five numbers as the winner. Scenario probabilities come from published launch-outcome frequencies (Trinity 2023: 50% under, 39% over), scenario multipliers from the ZS success and failure definitions (≥120% and ≤80% of forecast). Disagreement with the brief: none, but note the multipliers are boundary values, so the spread is understated (Section 9).

**D13. Citation contract builds on the shipped index.** `agent/moat/cite.py` and `data/moat/index/citations.sqlite` (branch data-moat, commit 704741d: 3,118 docs, 39,940 pages, 69,553 verified facts) already resolve `cite(doc_id, page_no)` to a human citation string and a source URL, and `verify_quote()` rejects altered numbers. This spec defines the `Citation` object, the gate, deep links and rendering on top of that module rather than a second index (Section 6).

**D14. Where this spec disagrees with the brief.** (i) The brief's skeleton put T inside S as a separate factor; we fold it into M (D4). (ii) The brief suggested short-interest days-to-cover inside O; the moat has no short-interest data (audit 5), so the term is specified but defaults to 0 (no information) and is flagged on every row until FINRA data are added. (iii) The brief asked for a time decay "from the Lazy Prices evidence"; Lazy Prices gives an accrual horizon, not a half-life, so H is our **inference** from it (D9).

---

## 3. Data layer (shared by FIND and DECIDE)

Paths are relative to the repo root; the moat lives in the `gap-data` worktree (`data/moat`, gitignored, mirrored in R2 `moat/`). Every row the models read already carries `source` and `source_row`, and every page carries a `doc_id` and file page number, so every model input can be cited (Section 6).

| Input | Used for | Location | Company-specific? | Missing-data fallback |
|---|---|---|---|---|
| XBRL quarterly panel (revenue, COGS, pretax income, income tax, diluted shares, inventory, receivables) | Rev_TTM, t, D, anchor event, DIO/DSO families | `agent/needle/xbrl.py` over `data/corpus/*/<T>/xbrl_companyfacts.json.gz` | yes | 20-F filers: `xbrl.annual()` (FY vs prior FY) |
| Page store and citation index | every quote, every number, deep links | `data/moat/index/citations.sqlite` via `agent/moat/cite.py` | n/a | none: no citation, no claim |
| I/B/E/S quarterly EPS consensus and actuals | σ_EPS | `data/moat/tables/ibes_eps_quarterly.csv`, `ibes_actuals.csv` (join on `oftic`, not `ticker`: GIL1, ZEN quirks) | yes | FY1 dispersion `ibes_eps_consensus.csv` stdev; then peer median σ/EPS ratio (Section 7) |
| I/B/E/S FY consensus by `statpers` | consensus-embedding test c_f | `ibes_eps_consensus.csv`, `ibes_revenue_consensus.csv` | yes | c_f = 0, flagged "untestable" |
| Analyst topic attention | a_f | `data/moat/verified/market/priced_in_scorecard.csv` (`share_of_quarters_asked`, 10 tickers x 9 topics), `qa_turns.csv` for other topics | yes | peer median for the topic, flagged "imputed" |
| Latest earnings release, first page | h_f | citation index, `doc_type = earnings_release` | yes | h_f = 0, flagged |
| Press counts | optional extra channel | `news_mentions.csv` (MRK only) | yes | omitted (factor 1), flagged |
| Short interest (FINRA, 7 business-day lag) | s_f | not in moat | yes | s_f = 0, flagged on every row |
| Policy exposure (IRA, MFN, tariff) | IRA, MFN, tariff channels | `verified/policy/policy_exposure.csv`, `force_summary.csv`, `ira_cut_check.csv`, `policy_gov/cms/*` | yes | channel not scored |
| Pricing proxies (Part D, Part B ASP, NADAC, SDUD, WAC, company list vs net) | GTN channel, IRA base | `tables/partd_by_year.csv`, `partb_asp_quarterly.csv`, `verified/pricing/gtn_proxy.csv`, `company_list_vs_net.csv` | yes | class GTN priors (Section 4.3), flagged "inference" |
| Product revenue (XBRL product axis) | LOE, label, IRA exposure | `tables/product_revenue_quarterly.csv` (raw: YTD and quarter facts mixed, use `days`), `restatements_triaged.csv` | yes (US 10-K filers) | 20-F product tables (annual) |
| LOE dates and erosion | LOE channel | `agent/cache/company_stated_loe.jsonl` (159 rows), Orange/Purple Book packs, `loe_curves.json` | yes / universal curves | universal curves (Section 4.3) |
| Label facts | label channel | `data/corpus/drugs/<slug>/label_sections.md`, `verified/product/*` | yes | none |
| Backtest hit rates | π for accounting families | `out/backtest/hit_rates.json` (1,410 firm-quarters, 43 firms, 2012-2024) | universal | none needed (constants in Section 11) |
| Detector signals | candidate findings | `out/<T>/signals_<detector>.jsonl` | yes | detector yields nothing |
| Kill-signal data (SDUD, FAERS, 10-Q product revenue, Part D PUF) | DECIDE monitoring | `tables/medicaid_sdud.csv`, `data/outside/faers`, filings | yes | listed with lag (Section 5.6) |

Point-in-time rule: every input carries an as-of date (filing `filed`, I/B/E/S `statpers`, transcript `call_date`). The model run takes an `as_of` date and drops anything later. The live XBRL panel uses SEC `frame` values (latest restated), which is not point-in-time (audit 1.14 item 9); this is acceptable for live scoring and must not be used for backtests.

---

## 4. Model 1: FIND

### 4.1 Equation

```
S_f = M_f · O_f · E_f · π_k(f)
```

A finding f is one candidate row: a sentence, at least one verified citation, an assigned signal family k(f), an assigned impact channel, and a direction (adverse or favorable to EPS). Only adverse findings and favorable findings with a quantified upside get M > 0; a favorable level outlier with no scenario is context, not a finding (π = 0).

### 4.2 Materiality M: impact over noise

```
M_f = |ΔEPS_f| · (1 + r)^(-t_f) / σ_EPS
```

- **ΔEPS_f**: base-case EPS impact in the single fiscal year of largest impact that overlaps the 24-month window from `as_of` (24 months follows `docs/materiality_spec.md` §2 and the case's Part 2 horizon). Computed by the channel function in Section 4.3 and the EPS translation below.
- **t_f**: years from `as_of` to the midpoint of that fiscal year (for the anchor event, 0.5 years, the midpoint of the next four quarters).
- **r = 7.85%**: Damodaran, Drugs (Pharmaceutical), 228 firms, WACC as of January 2026.
- **σ_EPS**: the company's annual EPS surprise noise, "what the market usually misses by":

```
σ_EPS = 2 · sd( actual_q - consensus_mean_q ),  last 8 quarters
```

where `consensus_mean_q` is the I/B/E/S mean of the last `statpers` before the announcement date (`ibes_eps_quarterly.csv`, fpi 6) and `actual_q` is `ibes_actuals.csv` (pdicity QTR). The factor 2 = √4 annualizes four quarterly surprises assuming they are independent (**inference**). Standard deviation (not root-mean-square) is used so a habitual beat, which the market learns, does not count as noise. Fallbacks in order: (1) the latest FY1 forecast dispersion `stdev` (Diether, Malloy, Scherbina 2002 definition uses the same quantity); (2) 0.041 x |trailing EPS|, the median σ_EPS / FY1-EPS ratio across nine of the ten shortlist companies (computed below; GILD excluded because its FY1 mean is negative).

Reference values computed from local I/B/E/S (as of statpers 2026-08-20; script `scratchpad/qm/ibes_noise.py`):

| Ticker | sd of last 8 quarterly surprises | σ_EPS (annual) | FY1 mean | FY1 stdev | σ_EPS / FY1 |
|---|---|---|---|---|---|
| ABBV | 0.2614 | 0.5227 | 14.02 | 0.07 | 3.7% |
| AMGN | 0.1726 | 0.3452 | 23.02 | 0.38 | 1.5% |
| AZN | 0.2094 | 0.4189 | 10.31 | 0.24 | 4.1% |
| BMY | 0.2389 | 0.4778 | 6.88 | 0.21 | 6.9% |
| GILD | 0.2016 | 0.4031 | -0.44 | 0.14 | n/a |
| JNJ | 0.0729 | 0.1457 | 11.58 | 0.24 | 1.3% |
| LLY | 1.0147 | 2.0295 | 36.45 | 1.66 | 5.6% |
| MRK | 0.1277 | 0.2554 | 2.75 | 0.05 | 9.3% |
| NVO | 0.3080 | 0.6160 | 22.42 | 1.49 | 2.7% |
| PFE | 0.1255 | 0.2509 | 2.98 | 0.06 | 8.4% |

Caveats for engineers: NVO I/B/E/S values appear to be in DKK (FY1 mean 22.42); σ_EPS and ΔEPS must be in the same currency, so for NVO convert ΔEPS to DKK per share or use ADR-equivalent I/B/E/S. GILD and MRK FY1 means look distorted by one-time charges (GILD negative); σ from surprises is unaffected, the ratio fallback excludes them.

**EPS translation (every channel ends here):**

```
ΔEPS = ΔRev · CM · (1 - t) / D
```

| Parameter | Value | Source |
|---|---|---|
| CM, price, rebate, MFP or MFN change | 1.00 | pharma_impact_math KQ7: "Price/rebate/MFP/MFN change: dOI = dRev_net x 1.0 (no COGS or promotion change)"; Drug Channels: "for rebate-driven changes, net price moves flow directly" |
| CM, volume change (LOE of small molecules, warnings, share loss) | 0.70 | pharma_impact_math KQ7 default "CM = 0.70 for volume" from COGS 15-25% and variable selling 5-15% (inference in the note) |
| t | company non-GAAP rate from guidance if extracted with a verified citation; else TTM GAAP ETR = Σ income tax / Σ pretax income over the last 4 quarters (XBRL) | pharma_impact_math KQ7 (use guidance, not GAAP one-offs); fallback is our rule |
| D | latest quarter's weighted-average diluted shares (`WeightedAverageNumberOfDilutedSharesOutstanding`) | pharma_impact_math KQ7: "do not use a static table" |

Sanity check from the note: "$1B net revenue loss at CM 0.70, t 0.16, S 1.77B shares = $0.33 EPS".

### 4.3 Impact-math channels

Each finding maps to exactly one channel. If no channel applies, a statistical family (Section 4.6) uses the **anchor event**.

**(a) Anchor event (statistical flags without their own channel).** The backtest outcome that calibrates π: gross margin over the next four quarters down at least 3 points versus the trailing four quarters (`backtest.py` `margin_drop`).

```
ΔEPS_anchor = 0.03 · Rev_TTM · (1 - t) / D,   t_f = 0.5 years
```

0.03 is the event threshold, so this is a lower bound on the event's size (**inference**: conservative). Because π for these families is an excess probability of exactly this event, M x π is the expected EPS loss the flag reveals.

**(b) IRA negotiation (Medicare MFP).**

```
ΔRev_IPAY = G_Medicare · max(0, d - g_pre)        step on 1 January of the IPAY year
```

- G_Medicare: CMS gross Medicare Part B+D expenditure for the selected drug from the CMS selected-drug fact sheet (e.g. IPAY 2028 sheet, Nov 2024 to Oct 2025 spend). Held flat (base); **inference**.
- d: list-price discount of the MFP. If published, the CMS figure (verified rows in `verified/policy/ira_cut_check.csv`). If not yet published (IPAY 2028 during 2026), bull/base/bear = the smallest, same-class and largest published discount among cycle-1/2 drugs of the same class. Oncology orals: Imbruvica 38% (CMS IPAY 2026), Ibrance 50% (CMS IPAY 2027, same CDK4/6 class), Pomalyst 60% (CMS IPAY 2027). Headline range across cycles 1-2: 38% to 85%.
- g_pre: pre-MFP Medicare concession rate. Low-rebate classes (oncology, HIV, Part B): g_pre = m, the Manufacturer Discount Program rate the MFP replaces, 0.20 in the catastrophic phase and 0.10 in the initial phase (CMS MDP final guidance; Health Affairs Forefront). Specialty drugs above the out-of-pocket cap sit almost entirely in catastrophic, so m = 0.20 (**inference** on phase mix). Highly rebated classes: g_pre = company GTN anchor (Novo 69% of US gross sales 2024 from its 20-F; Lilly about 60% in 2024; BMS 53% in 2025; Drug Channels), class priors GLP-1 0.60-0.75, insulin about 0.75 pre-cut, immunology 0.50-0.65 (pharma_impact_math KQ1, marked inference there).
- Cross-check: cycle 1 CMS net savings were 22% against list discounts of 38-79%, i.e. "net hit ~= 0.3-0.5 x list discount for highly rebated classes, and near 1.0x for low-rebate oncology" (pharma_impact_math KQ2).
- CM = 1.00. Bear adds commercial spillover of 0-5% of the drug's commercial net revenue in the MFP year (**inference** in the note).

**(c) MFN (Medicaid) and TrumpRx.**

```
ΔRev = s_MFN · Rev_US,    s_MFN base 0.0065, range 0.003 to 0.010
```

Range from pharma_impact_math KQ3 (Pfizer's maximum annual Medicaid exposure about $280M, "<1% of Pfizer 2024 US net revenue"; default 0.3-1.0% of US net revenue); base is the midpoint (**inference**). TrumpRx cash prices are modeled as neutral (base 0) because "the TrumpRx price usually sits at or above the manufacturer's existing net" (KQ3 inference) except where a cited TrumpRx price is below the drug's estimated net. CM = 1.00.

**(d) Tariff (Section 232).** For MFN signers the duty is zero "until January 20, 2029" (Proclamation 11020, `policy_exposure.csv` R062), which is outside a 24-month window from 2026-10-17. FIND therefore reports tariff exposure as a beyond-window note, not a scored ΔEPS:

```
ΔCOGS_after_2029 = COGS_imported_patented · τ_rate,   τ_rate ∈ {0.15 (EU, Japan, Korea, Switzerland cap), 0.20 (onshoring plan, to 2030-04-02), 1.00}
```

Tariff applies to imported cost, not sales (KQ3). DECIDE uses it in terminal values for onshoring moves.

**(e) Loss of exclusivity.**

```
ΔRev_y = Rev_pre · (1 - R(y)),   CM = 1.00 for biologics (price-led), 0.70 for small molecules (volume-led)
R(y) years 1/2/3: biologic 0.65 / 0.35 / 0.20; small molecule 0.30 / 0.15 / 0.10; staggered volume-limited generic entry: year 1 0.60-0.75
```

Sources: pharma_impact_math KQ4 takeaway (Humira US -35% year 1, -38% global year 2, -57% US year 3; Stelara US -43% year 1, -56% to -60% per quarter in year 2; IQVIA "traditional 90% erosion" for generics; Humira "maintained brand share post-LOE but lost 60% of net sales due to steep discounting", which is why biologic CM is 1.00). Cross-check against the team's `loe_curves.json` medians (biologic 78.8, 71.6, 33.6 percent of peak at t = 0..2, n = 4, 3, 2; small molecule 64.8, 16.1, 17.1, n = 14, 12, 8). LOE dates come from the Orange/Purple Book pack or the 10-K patent table (`company_stated_loe.jsonl`). A starter-thread LOE (e.g. "Trulicity loses exclusivity in 2027" for LLY) gets z_f = 1, so O = 0.

**(f) Gross-to-net.**

```
ΔRev = -Rev_gross · ΔGTN,   Rev_gross = Rev_net / (1 - GTN),   CM = 1.00
```

"A 1-point widening of GTN on a $10B gross brand is -$100M net" (KQ1). ΔGTN from the company's own list-vs-net disclosure where it exists (`company_list_vs_net.csv`: MRK, SNY, TAK, PFE, BMY, GSK) or the drug-level proxy trend (`verified/pricing/gtn_proxy.csv`, Part B ASP being the most net-like). Industry context: 2025 average list +3.7%, net -1.8% across eight large makers (Drug Channels).

**(g) Inventory and receivables.** Statistical families scored on the anchor event (a). The row also shows the exposure, which is not the scored impact:

```
excess_X = X_t - X_{t-4} · (1 + g_rev)            X ∈ {inventory, receivables}
DIO = inventory / COGS_q · 91.25;  DSO = receivables / Rev_q · 91.25   (annual filers: 365 and FY figures)
```

Two mandatory diagnostics before the row can be "high" confidence: (i) **stage split**: compute finished-goods DIO from the inventory note; if the build is in work-in-process and raw materials, label it "capacity build, not channel stuffing" (KQ5: "Lilly/Novo inventory growth is capacity build ... split inventory by stage before flagging"); (ii) **channel-stuffing test** for receivables: `DSO_t - mean(DSO_{t-4..t-1}) > 7 days` and the wholesaler-inventory language changed; expected reversal = excess days x daily revenue (KQ5, BMS 2000-2001 base rate: $1.5B pulled forward over eight quarters on about $18-19B of sales, about 1% of annual revenue per quarter). If (ii) holds, the receivables row switches from the anchor to this reversal channel.

**(h) Label breadth and product fine print** (also the Part 1 product comparison).

| Label fact | ΔRev | Source |
|---|---|---|
| Boxed warning added | -10% to -25% of US volume over 12-18 months, near 0 if class-wide; CM 0.70 | pediatric antidepressants about -10% in a month and a further -10% by mid-2005 (Mayo Clin Proc); levofloxacin -31% relative risk for CAP (PMC8159769) |
| REMS with ETASU vs non-REMS rival | -5% to -15% of new starts | KQ6, marked inference (no published elasticity) |
| Once-weekly vs daily dosing | +10% to +15% revenue per starter over two years | persistence HR 0.80 (95% CI 0.71-0.90), 333 vs 269 days (Diabetes Therapy 2021) |
| Oral vs injectable at equal efficacy | 55-68% stated preference | DCE n=480: 68% (Pharmaceuticals 2026 review); survey 77% falling to just over half after dosing rules explained |
| Indication count gap | TAM_units = prevalence x diagnosed x treated x line-eligible x persistence x 12; Rev = TAM_units x share x net price | KQ6 |

**(i) Footnote items.**

| Item | ΔEPS | π |
|---|---|---|
| Contingent consideration, milestones owed | change in disclosed fair value (ASC 805 fair value is already probability-weighted) | 1 |
| Partner royalty split change | Δroyalty rate x product revenue | 1 |
| Litigation, accrued (ASC 450 probable) | already in reported numbers: ΔEPS = 0 unless the accrual is changed | 1 |
| Litigation, "reasonably possible" range disclosed | midpoint of the disclosed range | 0.5 (**inference**: the midpoint of "more than remote, less than likely") |
| Tax rate change guided as persistent | Δt x pretax_TTM / D | 1 if guided with a citation, else the no-evidence family |

### 4.4 Obscurity O: probability the finding is not priced in

```
O_f = (1 - z_f)(1 - h_f)(1 - a_f)(1 - c_f)(1 - s_f) · 2^(-age_f / H)
```

| Term | Meaning | Value rule | Source |
|---|---|---|---|
| z_f | case starter thread | 1 if the finding restates the company's starter thread in the case appendix, else 0 | case: "Restating it will not score well"; materiality_spec §3 coverage 1.0 |
| h_f | earnings-release headline | 0.9 if any topic pattern of the finding matches the first page of the latest earnings release, else 0 | case: "signals a press-release skim would miss"; 0.9 is the team rule in materiality_spec §3, not literature (sensitivity in §11) |
| a_f | analyst attention | `share_of_quarters_asked` for the finding's topic over the last up-to-10 calls (priced_in_scorecard) | Hong, Lim, Stein 2000 (negative information diffuses slowly in low-coverage names); Chen, Nagar, Schoenfeld 2018 (prices respond to analyst tone, so analyst questions are the attention channel) |
| c_f | consensus embedding | `clip(Δcons_dir / |ΔEPS_f|, 0, 1)` where Δcons_dir is the change in the affected fiscal year's I/B/E/S mean EPS from the last statpers before to the first statpers after the finding's first public date, signed in the finding's direction | inference (no published test exists; priced_in KQ3 "Gaps"); confounded by earnings in the same window, so flagged "confounded" when an earnings date falls between the two statpers, and "untestable" (c = 0) when the fiscal year's consensus first appears after the disclosure |
| s_f | short sellers positioned | `max(0, 2·(pct_rank(DTC_now in own 24-month history) - 0.5))` for adverse findings; 0 when no data | days-to-cover is the robust short measure (Hong et al. 2015: DTC L/S 1.19%/month, t = 6.67; short ratio alone weak post-2000; Boehmer et al. RFS 2022 across 38 countries). FINRA publishes 7 business days after settlement. Not in the moat: default 0, flagged |
| age_f | months since first public disclosure of the fact | filing `filed` date, call date, or agency release date | |
| H | half-life of obscurity | 6 months | Lazy Prices (accrual to 18 months, bulk by 6); priced_in KQ5 inference "3 to 6 months" (D9) |

Interpretation: each factor is the probability one channel has not priced the fact; the product assumes channels are independent (D8). A finding the company itself headlined, or that analysts ask about every quarter, cannot be the Sharpest Needle no matter how large it is.

### 4.5 Evidence E: probability the documents say what we claim

```
E_f = min over key claims j of [ 1 - Π_{i in cites(j)} (1 - g_i) ]
```

A key claim is a quoted fact or a number the finding's sentence or impact math depends on. The minimum makes E the weakest link (conjunctive). Within one claim, independent citations combine by noisy-OR (**inference**: independence). Citations from the same issuer and the same filing are one source (e.g. a 10-Q balance sheet and its own inventory note).

| Citation status (Section 6) | g | Source |
|---|---|---|
| `verified_exact`: normalized quote is a substring of the cited page AND every figure is re-extracted on that page | 1.00 | deterministic check; seeded errors (wrong page, altered number, foreign figure, invented quote) all caught in `tests/needle/test_trust.py` |
| `verified_fuzzy`: rapidfuzz partial_ratio ≥ threshold, numbers still exact | 0.90 | citation note KQ4 inference; to be replaced by the matcher's measured precision on the FinanceBench 150 regression set |
| `derived_code`: computed by deterministic code from operands that are each `verified_exact` | min(g of operands) | arithmetic in code has no extraction error |
| `derived_llm`: arithmetic done by the LLM, operands cited | 0.85 | FinanceBench oracle-evidence-pages setting: GPT-4-Turbo 85% correct, 15% incorrect (Islam et al. 2023) |
| `verified_entailed`: paraphrase judged entailed by an NLI or LLM judge from a different model family | 0.745 | "only 74.5% of citations support their associated sentence" (Liu et al. 2023) |
| `unsupported` or `contradicted` | 0 | the claim is not emitted (gate) |

Table rows from verified moat tables (`facts` in the citation index, `verify_status = verified`) are citations like any other: `verified_exact` when code re-reads the row value at render time.

### 4.6 Prior π_k: how often the signal family turns into its adverse outcome

π_k is the **excess probability** that the adverse outcome assumed by the finding's channel occurs, over the base rate without the signal. Four derivation routes, applied in this order:

1. **Type C, contractual or scheduled** (IRA selection or published MFP, signed MFN terms, statutory or company-stated LOE date, label facts, booked footnote amounts, business-reason trial terminations): π = 1. The event is not a forecast; the uncertainty is in the size (bull/base/bear ΔEPS), not the occurrence.
2. **Own backtest** (five accounting flags, 1,410 firm-quarters, 43 firms, 2012-2024, point-in-time):

```
π_k = (h_fired - h_not) · (1 - 0.26)
```

on the `margin_drop` outcome, haircut by McLean-Pontiff's 26% out-of-sample decay (D7). For `gross_margin_drop` we take the smaller of the margin and hard-event excess rates because gate 2 found margin-signal-to-margin-event is partly "persistence of one series".
3. **Literature return evidence, converted through the anchor** (D6):

```
π_k = π_anchor · [ α_k (1 - d_k) ] / [ α_TZ (1 - d_TZ) ]
π_anchor = π_inventory = 0.0466,  α_TZ = 11.39% (Thomas-Zhang 2002 inventory-change hedge, year t+1), d_k = d_TZ = 0.58
```

α_k is the family's published long-short (or one-sided where only that exists) abnormal return over the documented horizon. With every family published, the decay terms cancel.
4. **Directional or no evidence.** Families with a published direction but no usable magnitude get π_min, the smallest quantified π (0.0055). Families with no published evidence get π_min / 2 (one tier below, following the forensic note's tier halving 2 / 1 / 0.5).

| Family k | Block | Engine kinds | Route | Input | π_k | Diagnostic? |
|---|---|---|---|---|---|---|
| Inventory outpaces revenue | A | `inventory_outpaces_revenue`, `inv_gap_peer_outlier` | backtest | margin_drop 20.6% vs 14.3%, lift 1.44, CI [1.08, 1.90] | 0.0466 | yes |
| Days inventory | A | `dio_rising`, `dio_peer_outlier` | backtest | 21.7% vs 17.4%, lift 1.25, CI [0.88, 1.71] | 0.0318 | no |
| Receivables outpace revenue | A | `receivables_outpace_revenue`, `rec_gap_peer_outlier` | backtest | 22.8% vs 14.3%, lift 1.60, CI [1.00, 2.33] | 0.0629 | no (CI lower bound not > 1) |
| Days sales outstanding | A | `dso_rising`, `dso_peer_outlier` | backtest | 25.6% vs 14.1%, lift 1.81, CI [1.17, 2.60] | 0.0851 | yes |
| Gross margin drop | A | `gross_margin_drop` | backtest, min of outcomes | margin 28.5% vs 16.3%; hard 28.1% vs 22.4% (lift 1.25, CI [0.82, 1.76]); min excess 0.057 | 0.0422 | no |
| Misstatement score (Beneish M > -1.78 or Dechow F > 1.85) | A | new detector | anchor | Beneish-Lee-Nichols spread "just below 1% a month" risk-adjusted, taken as 1.0%/month x 12 = 12% (rounded up, inference) | 0.0491 | yes (Dechow F > 1.85: 32.6% of misstaters vs 10% of non-misstaters) |
| Risk-factor change (Item 1A added, intensified, removed) | T | `risk_added`, `risk_intensified`, `risk_removed`, `risk_modified` | anchor | Lazy Prices VW Q5-Q1 5-factor alpha, Jaccard, 0.46%/month (t = 3.44) x 12 = 5.52% | 0.0226 | yes |
| Litigation-language change | T | drift with topic `litigation` | anchor | Lazy Prices: "underperform the non-changers by over 71 basis points per month ... (t=3.29)", x 12 = 8.52% | 0.0349 | yes |
| MD&A change | T | `mdna_*` | anchor | Lazy Prices Table VII: MD&A "11-22 basis per month", midpoint 16.5 x 12 = 1.98% | 0.0081 | no |
| Opportunistic insider sales | G | new detector over `insider_open_market.csv` | anchor | Cohen-Malloy-Pomorski VW L/S 82 bps/month (t = 2.15), returns rise "for roughly six months ... then level off": 0.82 x 6 = 4.92% | 0.0201 | yes |
| Negative 8-K item (2.05, 2.06, 3.01, 4.02, off-balance-sheet acceleration) | T | new detector over 8-Ks | anchor | Lerman-Livnat drift -1.5% to -3.7% (lower end 1.5%) | 0.0061 | no |
| Zero- or few-question call | C | new | anchor | Chen-Hollander-Law (working paper) -1.34% to -1.59% over five days (lower end 1.34%) | 0.0055 | no |
| Non-answer rate above the 11% base rate; bleak manager tone change; late-year auditor dismissal; SEC comment letter on revenue recognition or with ≥2 letters | C, C, G, T | `qa_deflection`, new | directional | Gow-Larcker-Zakolyukina 2021 (11% base rate); Druz et al. 2020; Burks-Stevens (odds of restatement roughly doubled); Ryans 2021 | 0.0055 (π_min) | no |
| Repeated deflection, topic surge, metric dropped or product no longer broken out, segment reclassification, ETR shift not guided, R&D share shift, FAERS serious-report rise, demand divergence, distributor commentary | C, T, A, X | `qa_repeated_deflection`, `call_topic_surge`, `metric_dropped`, `tax_rate_shift`, `rnd_shift`, `faers_serious_rising`, `demand_divergence`, `distributor_commentary` | no evidence | forensic note KQ3/KQ5 "Gaps": no study found; FAERS "counts follow publicity" (audit 5) | 0.0028 | no |
| Contractual and scheduled | P, L, F | `ira_exposed`, `exclusivity_earlier`, `label_*`, `boxed_warning_*`, `dosing_*`, `impairment` (booked), footnote items, `trial_terminated` with business reason | type C | | 1.0 | yes |
| "Reasonably possible" litigation | F | footnote extractor | type C, half | ASC 450 midpoint (inference) | 0.5 | no |
| Favorable level outlier with no scenario | | e.g. `gross_margin_peer_outlier` above the peer median | none | | 0 | n/a |

Notes for the quant reviewer:
- The backtest tests only five flags with the engine's own thresholds; it is the only fundamental-outcome evidence we own, so it anchors everything else. If the backtest is re-run (raw data must be re-fetched, audit 1.7), π for these five rows and π_anchor update mechanically.
- π values are small for statistical families and 1 for contractual ones. That is correct, not a scaling error: a certain event and a 3-in-100 excess chance are different things. Contractual items are then disciplined by O (they are usually public) and by the starter-thread rule.
- Inventory, receivables, DSO, DIO, gross margin and the misstatement score share one block (A) because they overlap with accruals; the league penalty (4.9) prevents triple counting.

### 4.7 Confidence (high, medium, low): deterministic, ICD 203 style

Two axes are kept apart, as ICD 203 requires: **confidence** (sourcing) is the label below; **likelihood** of the impact is π and the bull/base/bear range, shown separately in the row.

```
HIGH    E_f ≥ 0.95
        AND ( n_ind ≥ 2  OR  the key quantity is quoted verbatim from a single official primary source: SEC filing financial statement or note, CMS, FDA, Orange/Purple Book )
        AND no key claim is derived_llm or verified_entailed
        AND the family is diagnostic (type C, or backtest lift CI lower bound > 1, or a published discriminant statistic)
        AND no citation is contradicted
        AND the row's mandatory diagnostics pass (e.g. inventory stage split, Section 4.3 g)
MEDIUM  E_f ≥ 0.745 AND no citation is contradicted
LOW     otherwise
```

- n_ind counts sources from different issuers or different document families (company filing, government agency, FDA label, rival's filing, transcript). Mapping per the priced-in note KQ7: "High = at least two independent primary sources state the fact, the number is quoted not derived, and no contradiction; Moderate = one primary source states it, or it is derived arithmetically from stated figures; Low = inferred from indirect language, from a single mention, or contradicted elsewhere", plus Heuer's diagnosticity test ("Non-diagnostic findings cannot be high confidence regardless of sourcing").
- 0.95 sits between the fuzzy (0.90) and exact (1.00) grades, so HIGH requires exact quotes or noisy-OR corroboration of fuzzy ones (1 - 0.1² = 0.99). 0.745 is the entailed grade, so MEDIUM admits a single entailed paraphrase.
- **LLM role.** (i) Tie-breaker only: when two findings compete for one slot (top-5 table, Sharpest Needle) and have the same label and S equal to two significant figures, the higher calibrated verbalized confidence wins. Raw verbalized confidence is never displayed as a probability. (ii) Veto only: if the courtroom trial (`agent/needle/trial.py`, prosecutor / CFO defense / judge, every quote page-verified) rules the finding "fails", the label drops to LOW and the row is ineligible for Sharpest Needle. The LLM can lower a label, never raise one.

### 4.8 Sharpest Needle

```
Needle = argmax_f S_f   subject to   O_f ≥ 0.5,  E_f ≥ 0.90,  confidence ≠ LOW,  z_f = 0,  direction adverse or quantified
```

- O ≥ 0.5: "more likely unpriced than priced", the upper edge of ICD 203's "roughly even chance" band (45-55%) rounded to its midpoint. Encodes "least-discussed".
- E ≥ 0.90: quoted (exact or fuzzy) evidence only; no paraphrase can be the headline. Encodes "evidence that holds up".
- If no finding passes, the app says so ("no finding clears the obscurity floor") and shows the argmax of S among findings with O at or above the company's median O, labelled **provisional**. It does not silently relax the rule.

### 4.9 League score: why this company beat the other nine

```
L_c = ( Σ_{f in top5(c)} S_f ) · min(1, N_eff,c / N*),     N_eff,c = ( Σ_b S_b )² / Σ_b S_b²,   S_b = Σ_{f in top5, block b} S_f,   N* = 3
```

Blocks b: A accounting, T text and disclosure (risk factors, MD&A, 8-K, comment letters), C calls, G governance and insiders, P policy and contractual (IRA, MFN, tariff, LOE), L label and product, X outside data, F footnote items.

- N_eff is the inverse Herfindahl (effective number) of score mass across blocks. One dominant block gives N_eff ≈ 1 and divides the sum by 3; three or more balanced blocks give no penalty.
- N* = 3 (**inference**): the number of evidence blocks the literature shows to be roughly orthogonal: text vs accounting (Lazy Prices similarity "unaffected by the inclusion of" tone change; M-score works "on every decile portfolio sorted by ... accruals"), plus contractual events that are deterministic and so uncorrelated with either.
- Why at block level: two accounting ratios on one inventory build are one finding, not two.
- Required companion output for the pitch: for each company, L_c, its top-5 table, N_eff, the share of L_c from its largest finding, and its Sharpest Needle (or "none"). "Why this company beat the other nine" is then a sentence about rank, diversity and needle, each with numbers.

### 4.10 Output row (one per finding)

```
Finding {
  id: sha256(ticker|kind|first citation_id)[:12]      # stable; replaces Python hash() (audit 1.6)
  ticker, family k, block b, channel, direction
  sentence: one plain-English sentence; every number carries a marker [n]
  impact: { channel, formula (text with operands and markers), dRev {bull, base, bear}, CM, t, D, dEPS {bull, base, bear}, fiscal_year, t_years }
  peer: { metric_value, peer_median, peer_z, named_peer_row (a cited row at a named peer) }
  vector: { M, sigma_EPS, O, z, h, a, c, s, age_months, H, E, n_ind, pi, pi_route }
  S, confidence, confidence_reasons[], flags[] (e.g. "s_f no data", "c_f untestable", "capacity build")
  citations: [Citation]  # Section 6
}
```

---

## 5. Model 2: DECIDE

### 5.1 Equation

For each candidate move m, scenario s ∈ {bear, base, bull}, month τ = 1..24:

```
EV_m = Σ_s p_s · [ Σ_{τ=1..24} ( P_alive(τ) · CF^in_{m,s,τ}  -  P_reach(τ) · CF^out_{m,τ} ) / (1 + r_mo)^τ   +   TV_{m,s,24} / (1 + r_mo)^24 ]

r_mo = 1.0785^(1/12) - 1                    Damodaran pharma WACC 7.85% (Jan 2026)
P_alive(τ)  = Π of phase-transition probabilities for readouts at or before τ          (BIO/Informa/QLS 2011-2020)
P_reach(τ)  = probability of reaching the phase in which the outflow at τ is spent    (Stewart, Allison, Johnson 2001 rNPV rule:
              "costs of a phase are multiplied by the probability of reaching that phase", not the probability of approval)
TV_{m,s,24} = rNPV at month 24 of all later cash flows of the position held at month 24, same rules, to LOE or 10 years after launch
CF^in       = incremental after-tax operating cash flow = ΔRev · CM · (1 - t)   (Section 4.2 translation, company t)
p_s         = (0.50, 0.11, 0.39) for (bear, base, bull)
scenario revenue multiplier = (0.8, 1.0, 1.2)
```

- p_s: Trinity, 2023 US launches: "50% ... underperformed first-year forecasts, 39% overperformed" (remaining 11% on forecast). Cross-checks: Deloitte 36% miss year one; McKinsey about two-thirds miss; IQVIA 30% hit the first-year forecast.
- Multipliers: ZS defines success as year-3 sales ≥ 120% of the prelaunch forecast and failure as ≤ 80%. Using the boundaries makes the bear and bull cases conservative (the true tails are wider; Section 9).
- Technical risk (P_alive) and commercial risk (p_s) are treated as independent (**inference**).
- An IRR hurdle above WACC is not added: DiMasi's 10.5% real is a capitalization rate, and the phase probabilities already carry project risk (strategic_move KQ1 inference); ±50% on r is in Section 11.

### 5.2 Inputs linked to Part 1

Every DECIDE input is either (a) a FIND output, referenced by `finding_id` and carrying its citations, (b) a benchmark constant in Section 11, or (c) a company number with its own citation. A DECIDE input object:

```
DecideInput { name, value, unit, kind: finding|benchmark|company, finding_id?, citation_ids[], note }
```

| DECIDE input | Comes from FIND | Example |
|---|---|---|
| Revenue at risk the move defends | LOE channel ΔRev_y (4.3 e), IRA ΔRev (4.3 b), GTN ΔRev (4.3 f) | "Verzenio IPAY 2028 hit $429M base" -> defend-or-replace moves |
| Addressable gap the move targets | label channel indication gap, dosing or warning difference (4.3 h) | rival has N more indications -> label-expansion move |
| Net price path | GTN, MFN, IRA findings | DTC cash-pay move uses the GTN finding's current net |
| Tariff exposure after 2029 | 4.3 d beyond-window note | onshoring move's terminal value |
| Strategic-fit score (MCDA) | Σ S of findings the move addresses / Σ S of the company's top 5 | Section 5.4 |

A move that addresses no Part 1 finding gets strategic fit 0 and cannot be recommended (the case asks which Part 1 findings drive the decision).

### 5.3 Move templates

Each template is a cash-flow generator. Inputs marked "Part 1" come from FIND; all others have the default shown and its source.

**M1. Acquire (M&A).**
- Committed outflow at τ = 1: equity value x (1 + premium); premium median 63%, mean 53%, range 17-102% (Evercore precedents for Merck/Cidara, 13 deals of $3-10B since 2022). Cross-check: EV / peak sales 0.5x-1.0x, comps mean about 0.69x, median about 0.56x (Credit Suisse, Furiex DEFM14A 2014). Stage price ladder: Phase I platform about $2B (AbbVie/Capstan), Phase III single asset $3-9B (Anthos, Akero, Merus, Cidara), approved single asset $10-15B (Verona, Intra-Cellular) (strategic_move KQ3 inference).
- CVRs: outflow = amount x P(trigger) at the trigger month; the market prices CVRs near zero (BioCentury 2025), so CVR value is not counted as a saving.
- Inflows: target revenue x P_alive (TA-specific BIO rates if unapproved) x uptake to peak over 13.3 quarters (IQVIA, 813 launches) or 5 years for oncology (21 drugs, median); CM = Damodaran pharma gross margin 71.73% less royalties.

**M2. In-license.**
- Upfront: 3.7% of total deal value early stage (Goodwin 2025 median; 1.5% in 2024), about 5-7% across all stages (Gowling 2024 about 5%; JPM/DealForma about 7%). Development milestones 33% of total value (Goodwin early stage), placed at readout months and weighted by P_reach. Royalties paid: 4.5-8% early stage tiers, 9.3-13% Phase 1+ tiers (Goodwin); LES 2014 flat royalties 10.2% late Phase II-III, 12.5% NDA-launch. China-sourced assets at 30-50% of Western prices (Capital.com 2025).

**M3. Label expansion (new indication for a marketed drug).**
- Trial cost: Moore et al. 2018 pivotal median $19M (IQR $12.2-33.1M), placebo-controlled mean $28.8M, active-comparator $48.9M; TA ranges Martin et al. 2017 Phase 3 $11.5M (dermatology) to $52.9M (pain). Default two pivotal trials.
- P_alive: non-NME phase rates 57.5% / 37.5% / 67.5% / 91.5% (BIO 2021 Figure 9), so from Phase III: 0.675 x 0.915 = 0.6176.
- Revenue: incremental TAM from the Part 1 label finding (4.3 h), share ramp to peak over 3.5-5 years; 24 months after launch expect 25-40% of peak (strategic_move KQ4 inference); 6-12 months to majority commercial coverage (Tufts/ICER: half of payers lacked policies for H2 2024 approvals by December 2024).
- CM 0.85 (inference: 80-90% incremental contribution for an existing brand, from Damodaran 71.73% gross margin and 21.91% SG&A/sales).

**M4. Pricing and access (list cut, rebate strategy, DTC cash-pay channel).**
- ΔRev = units x Δnet price (CM 1.00) + volume response (CM 0.70).
- DTC anchors: LillyDirect Zepbound vials $349-499 then $299/399/449 per month; NovoCare Wegovy $349 ($199 introductory); TrumpRx about $350, target $250 within two years; about 35% of new Zepbound prescriptions via LillyDirect self-pay in Q2 2025 (Walmart/Lilly release). Channel build cost is not disclosed anywhere (strategic_move KQ2 Gaps): model it as a net-price decision plus an operating cost the team must state and flag.
- Links: GTN, MFN, IRA findings (Part 1).

**M5. Portfolio shift and LOE defense.**
- Rebate-wall defense trades margin for volume: Humira year-one decline 25-40% "mostly from price" while holding about 90% formulary parity (AbbVie CFO; strategic_move KQ2). Retention curves from 4.3 e. Successor-brand offset precedent: Skyrizi +49%, Rinvoq +55% (9M 2024).
- Reallocation moves are valued as the difference between two rNPVs (assets funded vs defunded), each with BIO TA probabilities.

**M6. Commercial investment (sales force, DTC campaign).**
- Rep loaded cost $134,000-219,000 per year; 12-24 month ramp (Rework 2025, vendor estimate). Top-brand national TV $260-440M per year (iSpot via Fierce Pharma: Skyrizi about $440M in 2025).
- Response: ΔRev = ε · ΔSpend / 0.108, where 0.108 is promotion as a share of US sales (CBO, 2008 data) so ΔSpend / (0.108 · Rev_US) is the proportional spend increase. ε base 0.06 (physician-level detailing elasticity, Datta and Dave, NBER w19592), range 0.05-0.30 (strategic_move KQ4 inference). At ε = 0.06 each $1 of spend returns $0.56 of revenue, so a pure promotion move is EV-negative unless the evidence supports a higher ε; detailing beats DTC per dollar (Narayanan et al. 2004; Kremer et al. 2008).
- Compliance gate: any campaign material must follow the case's promotion rules (approved uses only, fair balance, head-to-head only where evidence exists, label "Student concept, not actual promotional material", claims map).

**M7. US manufacturing (tariff hedge).**
- Capex $1-6.5B per plant, 3-5 years (DCAT 2025; Lilly $6.5B Texas API site); depreciation drag about pledge/15 per year once in service (KQ3 inference). Benefit: avoided ΔCOGS_after_2029 (4.3 d) from 2029-01-20, almost entirely in TV.

### 5.4 The five numbers (every candidate, same scale)

| Number | Definition |
|---|---|
| **EV** | EV_m above, $M present value at `as_of` |
| **Downside cash at risk (CaR)** | undiscounted cumulative 24-month outflow in the bear scenario with technical failure at the first readout, net of any inflows received before that point and of contractually avoidable payments (milestones not triggered, CVRs not paid) |
| **Payback months** | first month at which cumulative discounted expected net cash flow ≥ 0, searched to 120 months; ">120" if never |
| **Scenario EV spread** | EV with p_bull = 1 minus EV with p_bear = 1 |
| **MCDA score** | Σ_j w_j x_j, j ∈ {strategic fit, capability, execution risk, stakeholder evidence}, x_j ∈ [0,1], w_j = 0.25 each |

MCDA criteria (ISPOR MCDA Task Force reports 1 and 2, Thokala et al. and Marsh et al. 2016, as the checklist; equal weights by the 1/N argument in D3):
- strategic fit = Σ S of Part 1 findings the move addresses / Σ S of the company's top 5;
- capability = share of the move's required assets the company already holds (approved label, commercial footprint in the TA, manufacturing), each a cited fact;
- execution risk = P_alive(end) x p-weighted commercial multiplier / 1.2 (so 1 means certain bull);
- stakeholder evidence = share of the move's deciders (prescribers, patients, payers, regulators, investors) for which the team has documented evidence (Part 2 "why it will work").

**Selection rule.** (1) Feasibility gate: CaR ≤ cash and equivalents at the latest balance sheet (a cited 10-Q number). (2) Choose argmax EV. (3) If the [EV_bear, EV_bull] intervals of the top two overlap, prefer the higher MCDA score and say so. The two rejected alternatives are the next two by this rule; each is shown with all five numbers and the single binding reason it lost (lower EV, CaR above cash, payback beyond 120 months, lower MCDA under overlap, or a kill signal already tripped).

### 5.5 Synthetic reference case (unit test for the DECIDE arithmetic)

Synthetic inputs, not a recommendation: label expansion of a marketed drug, two placebo-controlled pivotal trials at $28.8M each spread evenly over months 1-24, readout at month 24, approval at month 37, incremental peak sales $800M reached linearly over 42 months, CM 0.85, t 0.16, flat peak to 120 months after approval, no LOE.

| Output | Value |
|---|---|
| P(success from Phase III, non-NME) | 0.675 x 0.915 = 0.6176 |
| In-window PV (costs only) | -53.3 |
| EV bear / base / bull | 1,161.0 / 1,464.6 / 1,768.2 |
| EV (p = 0.50 / 0.11 / 0.39) | 1,431.2 |
| CaR | 57.6 |
| Payback | month 51 |
| Scenario spread | 607.2 |

Script: `scratchpad/qm/decide_ref.py` (to be ported to `tests/`). Engineers' implementation must reproduce these to 0.1.

### 5.6 Kill signals and the revised EV

Each recommended move ships with numeric kill signals, each with data source, publication lag and check month:

| Signal | Threshold | Source and lag | Check month | Likelihood used in the update |
|---|---|---|---|---|
| ZS breadth (share of priority-target prescribers with ≥1 new patient) | < 30% | paid claims (IQVIA/Symphony); no free equivalent | 6 (visible by 3) | P(breach \| bear) = 1.0 ("none of the unsuccessful" met each threshold), P(breach \| bull) = 0.10 ("~90% of successful launches met each threshold"), P(breach \| base) = 0.55 (**inference**, midpoint) |
| ZS return-writing rate | < 50% | paid claims | 6 | same |
| ZS depth (share of writers with ≥3 patients) | < 30% | paid claims | 6 | same; all three met: "nine times more likely to succeed" |
| Year-one net sales vs forecast | < 80% | company 10-Q product revenue (about 40 days after quarter end) | 12 | replace p_bear with 0.70 ("~70% of those keep missing", Deloitte 2022; McKinsey: misses "typically continue to underdeliver for the next two years") |
| Commercial coverage | < 50% of commercial lives | payer policy trackers (paid); proxy: company commentary | 6 | ICER pattern; treated as P(breach \| bear) = 1.0, P(breach \| bull) = 0.5 (**inference**) |
| Medicaid units vs plan | < 80% of plan | Medicaid SDUD (states submit within 60 days of each quarter; posting lags) | 6-9 | same as year-one sales rule |
| Safety | FAERS serious reports +50% YoY and above the rivals' median (engine threshold, `supply.py`) | FAERS quarterly files (lag about one quarter; counts follow publicity) | each quarter | no published likelihood: triggers human review, not an automatic EV update |
| Self-pay channel share (DTC moves) | < 35% of new scripts | company disclosure (LillyDirect precedent 35% in Q2 2025) | 6 | same as ZS rule |
| Trial enrollment pace | < 80% of plan | ClinicalTrials.gov (free, updated by sponsor) | 6 | review trigger |

Medicare Part D Prescriber PUF lags about 18 months after year end, so it can confirm but never trigger within 24 months.

**Revised EV after a breach** (Bayes on scenarios, then the real-options stop rule):

```
p'_s = p_s · L_s / Σ_u p_u · L_u              L_s = P(breach | s) from the table
EV'_m = Σ_s p'_s · EV^remaining_{m,s}         remaining cash flows from the check month on, sunk costs excluded
Stop if EV'_m < V_abandon = salvage - exit costs (avoidable milestones and committed spend that can be cancelled)
```

Example with the ZS likelihoods on one breach at month 6 from p = (0.50, 0.11, 0.39): p' = (0.50·1.0, 0.11·0.55, 0.39·0.10) / 0.5995 = (0.834, 0.101, 0.065). The continue-or-abandon framing follows OptFolio (each stage is a continue-or-abandon option).

---

## 6. Citation contract

Team-lead requirement: **every number and quote the models output carries an in-text citation and a footnote that is clickable and resolves to the source document page.** A claim without a verified citation is not emitted.

### 6.1 What already exists (build on it, do not rebuild)

`agent/moat/cite.py` over `data/moat/index/citations.sqlite` (branch data-moat, commit 704741d; docs in `docs/research/citation_index.md`):

- `cite(doc_id, page_no) -> (citation_string, source_url)`, e.g. `cite("LLY:10q_2026Q2.md", 15)` returns `("Eli Lilly 10-Q 2026-06-30, p. 15", "https://www.sec.gov/Archives/edgar/data/59478/000005947826000081/lly-20260630.htm")`. Raises `KeyError` for an unknown doc or page.
- `get_page(doc_id, page_no)` returns the page row (`text`, `printed`, `char_start`, `char_end`, `speakers`) plus `license`, `quote_grade`, `superseded_by`.
- `verify_quote(quote, doc_id, page_no)`: exact normalized substring on the one page (NFKC, curly quotes, dashes, whitespace, case), so an altered number fails.
- `search_pages(...)`, `search_facts(...)`: BM25 over pages and over 69,553 table facts (`table, row_key, field, value, unit, source, source_row, verify_status, row_json`).
- Page-id convention: `f"{doc_id}#p{page_no}"`, where `page_no` is the first number of the `[[page N | printed M]]` marker, the same id `agent.findings.verify()` and `agent/needle/pages.py` accept. Both id schemes resolve: corpus (`LLY:10q_2026Q2.md`) and moat (`LLY:companies/LLY/10q_2025Q2.md`). `page_scheme` ∈ {`marker`, `section` (FDA labels: one page per heading, printed = "5.2 Bleeding"), `pdf_page`, `none` (CSV tables)}.
- Trust rules: transcripts quotable only at grade A or B; `license = 'bloomberg_licensed'` text is cited, never copied into a public artifact; superseded docs hidden by default.

### 6.2 The Citation object

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

Status = Literal["verified_exact", "verified_fuzzy", "verified_entailed", "derived_code", "derived_llm",
                 "unsupported", "contradicted"]

@dataclass(frozen=True)
class Citation:
    # identity
    citation_id: str              # sha256(f"{doc_id}#p{page_no}|{norm(cited_text)}")[:16]  (stable across runs)
    marker: int                   # n in the rendered "[n]"; assigned at render time, per document
    kind: Literal["page", "fact", "derived"]
    # source (from the citation index; never typed by the LLM)
    doc_id: str                   # corpus or moat scheme, as stored in citations.sqlite docs.doc_id
    page_no: Optional[int]        # file page (None for kind="fact")
    printed: str                  # printed folio or section heading from pages.printed
    page_scheme: str              # marker | section | pdf_page | none
    cite_string: str              # cite(doc_id, page_no)[0], e.g. "Eli Lilly 10-Q 2026-06-30, p. 15"
    source_url: str               # cite(doc_id, page_no)[1]
    doc_type: str
    license: str = ""             # "bloomberg_licensed" -> never render cited_text publicly
    quote_grade: str = ""         # transcripts: A/B quotable
    # locator
    cited_text: str = ""          # verbatim span from the page (API cited_text or detector quote)
    char_start: Optional[int] = None   # offsets of cited_text within the page text (not the file)
    char_end: Optional[int] = None
    page_text_sha256: str = ""    # detects extractor drift between index build and render
    figures: tuple = ()           # every number the claim relies on, as printed on the page
    # fact rows (kind="fact")
    table: str = ""
    row_key: str = ""
    field: str = ""
    value: str = ""
    unit: str = ""
    source_row: str = ""
    # Anthropic API locator, copied verbatim when the citation came from a cited generation
    api_type: str = ""            # char_location | page_location | content_block_location | search_result_location
    document_index: Optional[int] = None
    search_result_index: Optional[int] = None
    start_block_index: Optional[int] = None
    end_block_index: Optional[int] = None
    start_page_number: Optional[int] = None   # 1-indexed, end exclusive
    end_page_number: Optional[int] = None
    # derived numbers (kind="derived")
    formula: str = ""             # e.g. "16,793 / 3,268 x 91.25 = 468.9 days"
    operand_ids: tuple = ()       # citation_ids of the operands, each itself verified
    # deep links
    url_viewer: str = ""          # app page viewer, always present
    url_canonical: str = ""       # source deep link (SEC text fragment, PDF #page, DailyMed section)
    url_search: str = ""          # EDGAR full-text search for the phrase (optional)
    # verification
    status: Status = "unsupported"
    match_score: float = 0.0      # 100 exact; rapidfuzz partial_ratio when fuzzy
    numbers_on_page: bool = False
    verifier_version: str = ""
    verified_at: str = ""
    g: float = 0.0                # evidence grade used by FIND E (Section 4.5)

@dataclass
class Claim:
    claim_id: str
    text: str                     # one sentence; the markers are inserted at render time
    claim_kind: Literal["quote", "number", "derived", "paraphrase"]
    value: Optional[float] = None
    unit: str = ""
    period: str = ""
    citations: list = field(default_factory=list)   # list[Citation]
    llm_confidence_raw: Optional[float] = None
    shown: bool = False           # set by gate()
```

Adapter from the engine: `Evidence(doc_id, page, quote, figures, speaker)` maps to `Citation(kind="page", doc_id, page_no=page, cited_text=quote, figures=tuple(figures))`; `cite_string`, `source_url`, `printed`, `page_scheme`, `license`, `quote_grade` are then filled from the index, never from the detector.

### 6.3 Interface the citation worker implements

```python
def resolve(doc_id: str, page_no: int | None) -> dict                 # cite(), get_page(), docs row
def from_evidence(ev: Evidence) -> Citation
def from_fact(table: str, row_key: str, field: str) -> Citation        # facts table lookup; value from row_json
def from_api(block_citation: dict, doc_map: list[tuple[str, int]]) -> Citation   # doc_map: API document/search_result index -> (doc_id, page_no)
def derived(formula: str, value: float, operands: list[Citation]) -> Citation
def verify(c: Citation) -> Citation                                     # sets status, match_score, numbers_on_page, g
def build_links(c: Citation) -> Citation                                # url_viewer, url_canonical, url_search
def gate(claims: list[Claim]) -> tuple[list[Claim], list[Claim]]        # (shown, withheld) ; withheld -> out/<T>/rejected.jsonl
def render_markdown(claims: list[Claim]) -> tuple[str, str]            # (body with [n] markers, footnotes)
def render_html(claims: list[Claim]) -> str                              # same, with hover cards
```

### 6.4 Verification and the gate

`verify(c)`:
1. `kind="page"`: `verify_quote(cited_text, doc_id, page_no)`; on a miss, rapidfuzz `partial_ratio` against the page with threshold 95 (start strict per the citation note KQ3, tune on the FinanceBench 150 set and on `data/moat/verify/ai_wrong.jsonl`, 61 logged error types). Every item of `figures` must appear on the page after number normalization (commas, currency symbols, parentheses negatives, scale words; the existing `agent.findings.verify()` step 5). Transcripts additionally: grade A or B, not inside a fool.com LLM-written summary header, speaker surname within the 4,000 characters before the quote (existing verifier steps 3-4).
2. `kind="fact"`: re-read the row from the index; `value` must equal the claimed value after unit normalization; rows with `verify_status` in {`dropped`, `False`, `no`} are rejected; `no_verified_copy` rows (I/B/E/S, prices) are allowed for internal math and never quoted in public output (licensed WRDS data).
3. `kind="derived"`: every operand verifies and the formula recomputes to `value` within rounding of the printed operands.
4. `paraphrase`: NLI or LLM-judge entailment by a model family different from the generator; result `verified_entailed` or `unsupported`. Never allowed for a number.

`gate(claims)` withholds a claim if any of: a citation is `unsupported` or `contradicted`; a number has `numbers_on_page = False`; a `paraphrase` carries a number; a transcript quote is below grade B; `page_text_sha256` changed since verification. "Partially supported claims count as ungrounded" (Google check-grounding rule, adopted). Withheld claims are logged with the reason and feed the "AI caught" panel and the How We Did It report.

### 6.5 Deep links by source type

| Source (detected from `source_url` and `page_scheme`) | `url_canonical` | Notes |
|---|---|---|
| EDGAR HTML filing (`sec.gov/Archives/...htm`) | `source_url + "#:~:text=" + enc(start) + "," + enc(end)` where start and end are the first and last 4-6 words of `cited_text`, each inside one block element | text fragments work in Chrome 81+, Edge 83+, Firefox 131+, Safari 16.1+ (caniuse 95.61%); "if no match, the whole fragment is ignored and the top of the document is shown", so the footnote also prints the printed page. For a tagged XBRL figure, optional `https://www.sec.gov/ixviewer-plus/ix.xhtml?doc=/Archives/edgar/data/{cik}/{acc}/{file}#{element id}` (behavior read from the viewer bundle, undocumented: smoke-test) |
| PDF (`.pdf` source: CMS fact sheets, MFP explanations, comment-letter PDFs, LSEG transcript PDFs) | `source_url + "#page=" + page_no` (1-based; Chromium parser "converts it to a 0-based pageIndex by subtracting 1"; PDF.js accepts `#page=N&zoom=page-width`) | build test must assert the index `n_pages` equals the PDF's page count for every PDF-sourced doc, else fall back to the viewer |
| DailyMed label (`page_scheme = section`) | `source_url + "#section-" + number` where number is the leading section number of `printed` (e.g. "5.2 Bleeding" -> `#section-5.2`); boxed warning or unnumbered headings: text fragment on the heading | anchor convention inferred from a live label page, not documented by NLM |
| Table fact (`kind="fact"`) | `source` if it is an http URL (CMS, data.medicaid.gov, api.fda.gov), else the viewer's row page | `source_row` printed in the footnote |
| Licensed (Bloomberg, I/B/E/S) | viewer only, private deployment | never render `cited_text` publicly |
| Always | `url_viewer = "/cite/{urlquote(doc_id)}/{page_no}?q={enc(cited_text[:200])}"` served from `get_page()`; highlights the span with the existing `highlight()` logic; for PDFs served same-origin, open PDF.js `viewer.html?file=...#page=N` and dispatch an `eventBus` `find` event with `phraseSearch: true, highlightAll: true` | the reliable path; text fragments are a convenience |
| Optional | `url_search = "https://efts.sec.gov/LATEST/search-index?q=%22" + enc(phrase) + "%22&forms=" + form` | undocumented API; secondary link only |

### 6.6 Rendering

- In text: the marker immediately follows the number or closing quote: `Inventories were $16,793M [1], of which work in process was $9,997M [2].` Derived numbers get one marker whose footnote shows the formula and the operand markers: `DIO 468.9 days [3]` with footnote `3. Derived: 16,793 [1] / 3,268 [4] x 91.25.`
- Footnote line: `n. {cite_string}: "{cited_text, at most 30 words}" ({status}). [source]({url_canonical}) · [page]({url_viewer})`. The footnote shows the verification status, which no reference product exposes (citation note KQ6), and which is the cheapest trust signal for judges.
- HTML: marker is a superscript link to the footnote with a hover card (cite_string, printed page, cited_text, status), per the Perplexity / NotebookLM pattern.

### 6.7 LLM path and the API constraint

"Citations cannot be used together with structured outputs ... the API returns a 400 error" (Anthropic citations docs). Therefore:
1. **Cited generation call.** Selected pages are sent as `search_result` blocks (`source` = `url_viewer`, `title` = `cite_string`, `content` = one text block per paragraph or table row, `citations: {"enabled": true}`), corpus blocks marked `cache_control`; system prompt: quote figures verbatim, one claim per sentence, cite every sentence with a number or factual assertion, say "not found in provided documents" instead of guessing, show operands for any computed number; temperature 0. The response's `search_result_location` objects (`search_result_index`, `start_block_index`, `end_block_index`, `cited_text`) map to `(doc_id, page_no)` through `doc_map`.
2. **Deterministic verification** (6.4) on every citation; `cited_text` from the API is ground truth for the span and is never regenerated.
3. **Optional structuring call** with `output_config.format` on the already-verified claim list only, never on raw documents.

Tonight without an API key, only the deterministic path runs: detector Evidence -> `from_evidence` -> `verify` -> `gate` -> render. The LLM path is additive and changes no FIND number.

---

## 7. Generalization to any ticker

### 7.1 What the data layer needs per company

Minimum to score (FIND runs, with flags): SEC companyfacts (XBRL), the latest two annual reports and latest quarterly report page-marked into the citation index (`agent/needle/onboard.py` already pulls filings by CIK), and product/rival packs (onboard builds them from Part D spend and RxClass). Each further bucket switches on a term:

| Bucket present | Term it enables | If missing |
|---|---|---|
| I/B/E/S quarterly EPS consensus and actuals | σ_EPS from surprises; c_f | σ_EPS fallback chain (4.2); c_f = 0 flagged |
| ≥ 4 earnings-call transcripts with speaker names | a_f; call families | a_f = peer median for the topic, flagged "imputed"; call families absent |
| Earnings release | h_f | h_f = 0, flagged |
| Form 4 (US filers only) | insider family | absent (foreign private issuers file none) |
| Proxy, comment letters, 8-Ks | governance and disclosure families | absent |
| CMS selected-drug lists, Part B/D spending | IRA channel | channel not scored |
| Quarterly product revenue | LOE and IRA exposure by quarter | annual product revenue from 20-F / annual report, annual granularity |
| FINRA short interest | s_f | s_f = 0, flagged (true for all ten today) |

### 7.2 Universal vs company-specific parameters

- **Universal** (Section 11, same for every ticker): r, H, the π table, the 26% haircut, the anchor threshold 0.03, CM by change type, LOE retention curves, boxed-warning and dosing elasticities, MFN share range, MDP rates, E grades, confidence thresholds, Needle floors, N*, all DECIDE benchmarks and scenario weights.
- **Company-specific** (computed, each cited): σ_EPS, t, D, Rev_TTM, US revenue share, product revenues, Medicare spend per selected drug, GTN anchor (if disclosed), analyst attention a_f by topic, earnings-release headline, starter thread (shortlist only; empty for other tickers), peer set.

### 7.3 Peer sets outside the shortlist

- **Product peers** (Part 1 comparison): the onboarder's rule, other-manufacturer brands in the same FDA Established Pharmacologic Class via NLM RxClass ranked by Part D spend; the team may add rivals with a stated reason (the case allows it). Fix before use: brand-to-manufacturer matching by `key[:6]` can mis-assign (audit 1.9).
- **Financial peers** (peer column and peer z): the k = 6 nearest companies among all filers with companyfacts in the corpus (the 10 shortlist, GSK, SNY, NVS, TAK, REGN, ALNY, BBIO, VRTX and onboarded tickers) by Euclidean distance on standardized (log TTM revenue, gross margin, R&D/revenue, US revenue share, biologic share of top-10 product revenue). k = 6 keeps the MAD z defined (the engine needs ≥ 4 peers) with headroom (**inference**). Replaces the hard-coded `SHORTLIST` peer set.
- `ANNUAL_ONLY` becomes a rule (filer's latest annual form is 20-F or 40-F) instead of the hand list {NVO, AZN}.

### 7.4 Graceful degradation (what the output says)

Every term that falls back writes a flag into `Finding.flags`, and the row and league output show them. A company is eligible for the league comparison only if σ_EPS comes from I/B/E/S or FY1 dispersion and a_f is measured (not imputed) for its top-5 topics; otherwise it is scored but marked "not comparable". This keeps the "why it beat the other nine" claim apples to apples. For 20-F filers (NVO, AZN today): no quarterly product revenue (bucket 4 is 0/0), no proxies or Form 4 (fine-print bucket 2/6); FIND runs on annual comparisons and the IRA and LOE channels use annual product revenue.

---

## 8. Validation protocol

### 8.1 Tonight, without an API key (deterministic parts only)

1. **Reference-answer tests.** Port Section 10's numbers into `tests/needle/test_find_reference.py`: σ_EPS for LLY = 2.0294 from the eight surprises listed; DIO 468.9; finished-goods DIO 73.4; S for the DIO and Verzenio rows to 4 significant figures; the gross-margin level outlier gets π = 0. Port Section 5.5 into `tests/needle/test_decide_reference.py`.
2. **Gate tests.** Seeded errors must all be withheld: wrong page, altered number, foreign figure, invented quote (already in `test_trust.py`), plus grade-C transcript quote, licensed text in public render, derived number with one unverified operand, paraphrase carrying a number.
3. **Rank-stability report.** For each constant in Section 11, recompute all ten companies' top-5 at x0.5 and x1.5 and report Spearman rank correlation of findings within company and of the league, and whether the Sharpest Needle changes. Ship the table in the appendix.
4. **League sanity.** Recompute the league with and without the concentration penalty and with the favorable-level-outlier rule, and publish both (Section 10.4 shows the effect on the old scores).

### 8.2 What the existing backtest supports, and what it does not

- Supports: five accounting flags (inventory, receivables, DSO, DIO, gross-margin drop), with the engine's thresholds, against gross-margin compression over the next 4 quarters, between-firm, 1,410 firm-quarters, 43 firms, 2012-2024, point-in-time, non-overlapping windows. Dose response on margin drops is monotonic (12.3% at 0 signals to 61.1% at 5, n = 18 at 5).
- Does not support: any claim that flags predict revenue drops or impairments (no CI entirely above 1 on hard events); any within-firm claim (within-firm CI includes 0 per gate 2); any text, call, label, policy or insider family; any return claim. The universe was hand-picked and rules and results were produced in one commit (disclosed), hence the 26% haircut.
- Known inconsistency to fix: `score._proven` counts `margin_drop` CIs, so four of five flags can be labelled "high" through the backtest though gate 2's headline outcome is hard events (audit 1.7). Under this spec, diagnosticity uses margin-drop CIs explicitly and says so.
- The raw backtest panel (`data/backtest/xbrl/`) is not in any worktree and has no fetch script; re-running needs a fetch of SEC companyfacts for the 50 filers.

### 8.3 Leave-one-year-out sign and rank check (when the panel is re-fetched)

For each year y in 2012-2024: estimate each family's excess rate (h_fired - h_not) on all other years; on year y, check (i) the sign of the held-out excess rate and (ii) the Spearman correlation between the training-year family ranking and the held-out ranking. Report the number of years with the same sign per family and a one-sided binomial sign test (13 years: all 13 agreeing gives p = 0.5^13 = 0.00012; 10 of 13 gives p = 0.046). Pre-register thresholds and families before running; log every discarded specification (priced-in note KQ6).

### 8.4 Why a fundamental-outcome test, not returns, and the minimum p-value with N = 10

- Power: "if the same abnormal performance occurs over six months, a sample size of 200 is required to detect the abnormal performance even 65% of the time" (Kothari and Warner). Our findings' effects are diffuse over months, and N = 10 companies.
- Mechanism: Lazy Prices returns arrive when the information "is later revealed through news or earnings", so the cleaner target is the fundamental event itself.
- Minimum attainable p-values: "is the top-ranked company the best of ten?" is one draw from ten, so p ≥ 1/10 = 0.10 under random ranking: no single-company claim can reach 0.05. A full-ranking Spearman test across ten companies can (minimum p = 1/10! ≈ 2.8e-7), but only if we have a defined fundamental outcome for all ten. A per-company direction call (e.g. "next quarter's gross margin or revenue surprise is below consensus") gives a sign test with minimum one-sided p = 0.5^10 = 0.00098 if all ten are right.
- Live test available now: Q3 2026 results arrive for MRK, BMY, LLY on Oct 29, AZN Oct 30, PFE Nov 3, NVO Nov 4-5 (audit 2.6). Before those dates, seal (hash) each company's top-finding direction call: sign of next-quarter gross-margin change and sign of revenue surprise vs I/B/E/S mean. This mirrors the existing sealed-forecast process (`docs/needle_sealed.md`).

### 8.5 Calibration report for the LLM confidence (once the key exists)

- Labeled set: FinanceBench open 150 (evidence page numbers and texts), `data/moat/verify/ai_wrong.jsonl` (61 logged error types), seeded errors from 8.1, and every gate decision tonight (verified vs withheld).
- Metrics: ECE with 10 equal-width bins and AUROC of verbalized confidence for predicting "verified", reported together because "ECE alone can hide poor failure prediction" (Xiong et al.: GPT-4 CoT reached ECE 0.064 by saying 100% to everything). Report per failure class (wrong page, altered number, misattributed speaker, unsupported paraphrase), since a judge can score 20/21 overall and 0/9 on the failure class (Galtea).
- Acceptance: the LLM confidence is used as a tie-breaker only if its AUROC on the held-out half exceeds 0.60 (**inference**; for reference GPT-4 vanilla verbalized AUROC was 0.627, "close to the 50% random guess threshold", Xiong et al.); otherwise ties break by E, then by n_ind.

---

## 9. Honest limits (pitch can lift this verbatim)

What the model cannot know, and the proxy it uses instead:

- **True net prices.** No product-level net price is public anywhere. We use company-level gross-to-net disclosures (Novo 69% of US gross sales in 2024, BMS 53% in 2025, Lilly about 60% in 2024), Medicare Part B ASP (net-like), Part D gross spend, NADAC (pharmacy acquisition, list-like) and Medicaid SDUD. Class GTN levels for oncology and HIV are our inference.
- **Ex-US volume and price.** Filings give ex-US revenue but not units or price; IRA, MFN and LOE channels are modeled on US revenue, with ex-US LOE erosion assumed at 0.8x the US speed (inference).
- **Commercial formularies.** PBM formulary decisions and rebate contracts are private. Coverage enters only through published Part D data, company commentary and published coverage-lag studies.
- **Q3 2026 results.** Most Q3 2026 reports land Oct 29 to Nov 5; FIND uses data through Q2 2026 (10-Qs filed in August). Sealed predictions (8.4) turn this limit into a test.
- **Future MFPs.** IPAY 2028 MFPs are not published; we bound them with the smallest, same-class and largest published discounts.
- **MFN deal texts.** The deals are confidential; impact uses the Pfizer Medicaid base rate (<1% of US net revenue).
- **Tariffs after January 20, 2029.** A scenario, outside the 24-month window.
- **Short interest, options, press.** Not in our data except press for MRK; the obscurity score treats them as "no information", which makes O optimistic for heavily shorted names.
- **Prior weights.** Statistical priors rest on one 43-firm backtest of five flags (margin compression only, between-firm, in-sample) and on published return studies converted through one anchor ratio. They rank evidence families; they are not forecasts.
- **Small N.** Ten companies cannot show statistically that our chosen company is the best (minimum p = 0.10); we show it is the best by a transparent rule and test direction calls out of sample.
- **LLM steps.** Semantic drift classification, deflection scoring and the courtroom trial need an API key; tonight's numbers are fully deterministic. The LLM can lower a confidence label, never raise it, and every LLM-cited quote passes the same page verifier.

---

## 10. Worked example: Eli Lilly (LLY), as of 2026-10-17

All inputs below are local (`gap-data/data/moat`, `quant-model/data/corpus`, citation index at commit 704741d). The current engine was re-run read-only in a scratch copy (`scratchpad/run`, `python -m agent.needle.run --all`, 18 s, no API key); its LLY score 0.3034 matches the committed `out/league.json`. Scripts: `scratchpad/qm/ibes_noise.py`, `lly_panel.py`, `worked.py`, `league_conc.py`. Engineers: these are the reference answers.

### 10.1 Company constants

| Symbol | Value | Derivation | Source (citation index id) |
|---|---|---|---|
| Rev_TTM | 79,665.0 | 17,600.8 + 19,291.2 + 19,799.0 + 22,974.0 (2025Q3 to 2026Q2) | XBRL `Revenues`; 2026Q2 22,974 on `LLY:10q_2026Q2.md#p5` ("Revenue $ 22,974 $ 15,558") |
| t | 0.2049 | Σ income tax 6,884.0 / Σ pretax 33,595.0, same four quarters | XBRL `IncomeTaxExpenseBenefit`, pretax concept; 2026Q2 "Income before income taxes 9,247 ... Income taxes 2,152" on `LLY:10q_2026Q2.md#p5`. (Q2 alone: "The effective tax rates were 23.3 percent and 16.5 percent", `#p15`.) |
| D | 893.7M | Q2 2026 diluted weighted shares | "Diluted 893.7 899.8" on `LLY:10q_2026Q2.md#p5` |
| σ_EPS | 2.0294 | 2 x sd of the last 8 quarterly surprises: -0.25, -0.10, -0.71, +0.80, +0.89, +0.43, +1.60, +2.37 (2024Q3 to 2026Q2; actual minus last pre-announcement I/B/E/S mean); sd = 1.0147 | `ibes_actuals.csv`, `ibes_eps_quarterly.csv` (WRDS, licensed: cite internally, do not publish rows) |
| r | 0.0785 | | Damodaran Jan 2026 |
| H | 6 months | | Section 2, D9 |

### 10.2 Finding A (current #1 driver): "Gross margin 85.8% (Q2 2026) vs peers; peer median 74.1%, z +1.8"

- Old engine: kind `gross_margin_peer_outlier`, I_norm = 1.0 (cap), P = 0.6, T = 0.926, O = 0.3, E = 1.0, Z = 1.85, D = 0 -> S = 1.0 x 0.6 x 0.926 x 0.3 x 1.0 x (1 + 0.25 x 1.85) = **0.2437**, which is 80.3% of LLY's league score 0.3034.
- Why the old number is wrong: `score._impact` routes every kind starting with `gross_margin` to `|value| x TTM revenue`, so the margin **level** 0.858 was treated as a margin **change** (audit weakness 5), giving about $68B of "impact", capped at 1.
- FIND: a margin above the peer median is favorable and has no adverse scenario; family "favorable level outlier", π = 0 -> **S = 0**. It may appear as context in the peer column, not as a finding.

### 10.3 Finding B: "Days inventory 469 days (Q2 2026) vs peers; peer median 187 days, z +2.9"

Inputs (each a `verified_exact` citation):
- Inventories $16,793M at June 30, 2026: `LLY:10q_2026Q2.md#p7` and the note on `#p15`: "Finished products $ 2,630 ... Work in process 9,997 ... Raw materials and supplies 4,128 ... Inventories $ 16,793".
- Cost of sales Q2 2026 $3,268M: `LLY:10q_2026Q2.md#p5` ("Cost of sales 3,268 2,448").
- Prior-year inventories $11,013.8M: `LLY:companies/LLY/10q_2025Q2.md#p7` ("Inventories (Note 6) 11,013.8"); prior-year revenue $15,558M: `LLY:10q_2026Q2.md#p5`.

Step by step:

| Step | Formula | Value |
|---|---|---|
| DIO | 16,793 / 3,268 x 91.25 | 468.9 days |
| Finished-goods DIO (stage split, 4.3 g) | 2,630 / 3,268 x 91.25 | **73.4 days** |
| Inventory YoY, revenue YoY | 16,793 / 11,013.8 - 1; 22,974 / 15,558 - 1 | +52.47%, +47.67% (gap +4.8 pts: below the engine's 5-pt `inventory_outpaces_revenue` threshold) |
| Excess inventory (exposure, not scored) | 16,793 - 11,013.8 x 1.4767 | 529.3 |
| Channel | anchor event (4.3 a), family DIO | |
| ΔEPS_anchor | 0.03 x 79,665.0 x (1 - 0.2049) / 893.7 | $2.1262 |
| Discount, t_f = 0.5 | 1.0785^-0.5 | 0.9629 |
| **M** | 2.1262 x 0.9629 / 2.0294 | **1.0089** |
| z, h | not starter thread; "inventor" absent from page 1 of the 2026-08-05 earnings release (`LLY:earnings/2026-08-05_lly-20260805.md#p1`) | 0, 0 |
| a | priced_in_scorecard LLY `inventory_channel`: asked in 6 of 10 quarters, last 2026Q1 | 0.6 |
| c | no consensus line item for an inventory flag | 0 (n/a) |
| s | no short-interest data | 0 (flag) |
| age, τ | 10-Q filed 2026-08-05 -> 73 days = 2.40 months; 2^(-2.40/6) | 0.7580 |
| **O** | (1 - 0.6) x 0.7580 | **0.3032** |
| **E** | operands all `verified_exact`; derived by code | **1.0** |
| **π** | DIO family: (0.217 - 0.174) x 0.74 | **0.0318** |
| **S** | 1.0089 x 0.3032 x 1.0 x 0.0318 | **0.00973** |
| Confidence | E = 1.0 but the key quantity is derived from one filing (n_ind = 1), the DIO family is not diagnostic (lift CI [0.88, 1.71]), and the stage split shows a work-in-process and raw-material build (84% of inventory), finished-goods DIO 73 days | **MEDIUM**, flag "capacity build, not channel stuffing" |
| Needle eligible? | O = 0.30 < 0.5 | no |

Peer comparison for the row: peer median DIO 187 days, LLY z +2.9 (engine). Plain-English finding the table should show: "Lilly holds 469 days of inventory against a peer median of 187, but 84% of it is work in process and raw materials; finished goods cover 73 days, which reads as GLP-1 capacity build rather than channel stuffing."

### 10.4 Finding C (new channel, not produced by the current engine): "Verzenio's Medicare price is set by negotiation from January 2028"

Inputs:
- Selection: "In January 2026, HHS selected Trulicity and Verzenio as additional medicines subject to government-set prices to be effective in 2028." (`LLY:10k_FY2025.md#p46`, Eli Lilly 10-K FY2025, p. 46).
- Medicare spend: "Verzenio Breast cancer $1,428,714,000" (Nov 2024 to Oct 2025 Part B+D expenditure), CMS IPAY 2028 selected-drug fact sheet p. 1 (`policy_gov:policy_gov/cms/cms_fact_sheet_selected_list_ipay2028.md#p1`; `url_canonical` = `https://www.cms.gov/files/document/factsheet-medicare-negotiation-selected-drug-list-ipay-2028.pdf#page=1`).
- Verzenio FY2025 revenue US 3,464, outside US 2,259, total 5,723 (`LLY:10k_FY2025.md#p49`).
- MFP analog discounts (CMS, verified in `ira_cut_check.csv`): Imbruvica 38% (IPAY 2026), Ibrance 50% ($7,871 vs $15,741, IPAY 2027, same CDK4/6 class; `policy_gov:policy_gov/cms/mfp_explanation_ibrance.md#p1`), Pomalyst 60% (IPAY 2027).

| Step | Formula | Value |
|---|---|---|
| Channel | IRA (4.3 b), oncology: g_pre = m = 0.20 | |
| ΔRev 2028 bull / base / bear | 1,428.714 x (d - 0.20), d = 0.38 / 0.50 / 0.60 | 257.2 / **428.6** / 571.5 |
| ΔEPS 2028 bull / base / bear | ΔRev x 1.00 x (1 - 0.2049) / 893.7 | $0.2288 / **$0.3813** / $0.5084 |
| Timing | 2026-10-17 to 2028-07-01 = 1.706 years; 1.0785^-1.706 | 0.8791 |
| **M** | 0.3813 x 0.8791 / 2.0294 | **0.1652** |
| z, h | not starter thread (LLY's thread is obesity pricing and Trulicity LOE); IRA terms absent from the 2026-08-05 release page 1 | 0, 0 |
| a | priced_in_scorecard LLY `IRA_negotiation`: asked in 5 of 10 quarters, last 2025Q4 | 0.5 |
| c | FY2028 I/B/E/S consensus first appears at statpers 2026-02-19, after the 2026-01-27 selection | 0, flag "untestable" |
| s | no data | 0 (flag) |
| age, τ | 2026-01-27 to 2026-10-17 = 8.64 months; 2^(-8.64/6) | 0.3685 |
| **O** | (1 - 0.5) x 0.3685 | **0.1843** |
| **E** | both key facts `verified_exact`; CMS and Lilly are independent issuers | **1.0** (n_ind = 2) |
| **π** | type C (statutory effective date) | **1.0** |
| **S** | 0.1652 x 0.1843 x 1.0 x 1.0 | **0.03044** |
| Confidence | quoted, two independent primary sources, type C | **HIGH** |
| Needle eligible? | O = 0.18 < 0.5 | no |

Peer comparison: Pfizer's Ibrance, the same class, takes a 50% list cut at its January 2027 MFP; a 50% Verzenio cut nets to about $429M of 2028 revenue (7.5% of Verzenio's FY2025 sales) because the MFP replaces the 20% catastrophic-phase discount Lilly already pays.

### 10.5 What changes at the league level

Concentration penalty applied to the **old** S values (scratch run, all ten companies), to isolate the effect of 4.9 before any re-scoring:

| Ticker | Old top-5 sum | Largest share | Blocks in top 5 | N_eff (blocks) | L with penalty | L, with the favorable level outlier removed |
|---|---|---|---|---|---|---|
| LLY | 0.3034 | 80.3% | A, L | 1.10 | 0.1116 | **0.0430** (6th) |
| AZN | 0.1900 | 66.3% | A, L | 1.57 | 0.0992 | 0.0992 (1st) |
| GILD | 0.1079 | 44.4% | A, L | 1.98 | 0.0710 | 0.0710 |
| MRK | 0.1398 | 47.2% | A, L | 1.51 | 0.0703 | 0.0703 |
| PFE | 0.0804 | 27.2% | A, L, T | 2.26 | 0.0606 | 0.0606 |
| AMGN | 0.0894 | 32.9% | A, L | 1.79 | 0.0534 | 0.0534 |
| BMY | 0.0508 | 29.5% | A, L, T | 2.28 | 0.0386 | 0.0386 |
| NVO | 0.0500 | 30.0% | L, T | 1.92 | 0.0321 | 0.0321 |
| JNJ | 0.0696 | 21.6% | A, L | 1.31 | 0.0304 | 0.0304 |
| ABBV | 0.0750 | 20.0% | L | 1.00 | 0.0250 | 0.0250 |

Reading: on the old scores, LLY's first place is entirely the margin-level bug; with that one row treated correctly LLY is 6th and AZN leads. The final league must be recomputed under the full FIND equation (new M, O, E, π for every finding), which needs the engineering work in this spec; this table is not the answer, it is the evidence that the old answer should not be pitched.

### 10.6 Sensitivity of the worked rows to ±50% on each constant

| Constant | S_B at x0.5 / x1.5 | S_C at x0.5 / x1.5 | Order C > B kept? |
|---|---|---|---|
| H (6 months) | 0.00738 / 0.01068 | 0.01122 / 0.04245 | yes |
| r (7.85%) | 0.00992 / 0.00956 | 0.03242 / 0.02864 | yes |
| haircut 0.26 | 0.01144 / 0.00802 | n/a | yes |
| anchor 0.03 | 0.00487 / 0.01460 | n/a | yes |
| m (0.20) | n/a | 0.04058 / 0.02029 | yes |

---

## 11. Weight derivation table (every constant in both models)

"Sensitivity" states what a ±50% move does to rankings; where it was computed, the numbers are from Section 10.6 or the script named. "Inference" marks our derivations.

### 11.1 FIND

| Symbol | Value | Meaning | Source | Sensitivity (±50%) |
|---|---|---|---|---|
| α, β, γ | 1, 1, 1 | exponents on M, O, E | D3: expected-value reading; DeMiguel et al. 2009 (1/N needs ~3,000-6,000 months to beat); Gu-Kelly-Xiu OOS R2 0.33-0.40% | worked rows: order kept at α, β ∈ {0.5, 1.5} (B 0.00968 / 0.00977 vs C 0.0749 / 0.0124 for α; B 0.0177 / 0.00536 vs C 0.0705 / 0.0131 for β); γ irrelevant when E = 1. Exponents < 1 favor obscure-but-small findings; > 1 favor large public ones |
| r | 7.85% | discount rate in M and DECIDE | Damodaran Drugs (Pharmaceutical), 228 firms, Jan 2026 (beta 0.98, cost of equity 8.33%) | S changes < 7% on worked rows; reorders only findings whose impact years differ by > 1 year |
| horizon | 24 months | impact window | materiality_spec §2; case Part 2 | 12 months drops all IPAY 2028 items to M = 0; 36 months admits post-2029 tariff |
| σ_EPS | 2 x sd(8 quarterly surprises) | noise denominator | inference (√4 annualization); DMS 2002 dispersion fallback | company-level scale: rescales all of a company's findings equally, so within-company ranks unchanged; league moves (LLY σ is 3-14x peers', so LLY findings shrink relative to peers) |
| 0.041 | 4.1% | σ_EPS / FY1-EPS fallback ratio | median of 9 shortlist ratios (table in 4.2) | used only for tickers without I/B/E/S; scales those companies' M |
| CM_price | 1.00 | flow-through of price, rebate, MFP, MFN changes | pharma_impact_math KQ7; Drug Channels | linear in M for those channels |
| CM_volume | 0.70 | flow-through of volume changes | pharma_impact_math KQ7 (COGS 15-25%, variable selling 5-15%) | linear for volume channels; ±50% swaps price vs volume findings of similar ΔRev |
| t | company TTM GAAP ETR (or guided) | tax | KQ7 | company-level scale |
| anchor | 0.03 | margin-compression size for statistical flags | backtest event threshold (`margin_drop` ≥ 3 pts) | linear for all statistical families: worked B 0.00487 / 0.01460; does not reorder statistical findings among themselves, reorders them vs channel findings |
| H | 6 months | obscurity half-life | Lazy Prices (alpha "persists and increases up to 6 months", accrues to 18); priced_in KQ5 inference 3-6 | B 0.00738 / 0.01068; C 0.01122 / 0.04245; order kept; shorter H favors recent filings |
| h value | 0.9 | headline-page coverage | materiality_spec §3 team rule; case "press-release skim" | affects only topics on the release's first page; at 0.45 such topics can return to the top 5 |
| z | 1 | starter thread | case appendix | binary by design |
| a_f | share of last ≤ 10 calls asked | analyst attention | priced_in_scorecard; Hong-Lim-Stein 2000; Chen-Nagar-Schoenfeld 2018 | measured, not a weight |
| c_f | clip(Δcons/ΔEPS, 0, 1) | consensus embedding | inference (no published test; priced_in KQ3 Gaps) | measured |
| s_f | 2(pct rank DTC - 0.5)+ | short positioning | Hong et al. 2015 DTC 1.19%/month (t 6.67); Boehmer et al. 2022 | 0 everywhere today |
| E grades | 1.00 / 0.90 / 0.85 / 0.745 / 0 | exact / fuzzy / LLM arithmetic / entailed / unsupported | test_trust seeded errors; citation note KQ4 (0.90 inference); FinanceBench oracle 85%; Liu et al. 74.5% | only rows with non-exact evidence move; exact rows unaffected |
| δ_oos | 0.26 | data-mining haircut on backtest excess rates | McLean-Pontiff 2016 out-of-sample decline | B 0.01144 / 0.00802; scales all five backtested families equally, so no reorder among them |
| d_k | 0.58 | post-publication decay | McLean-Pontiff 2016 | cancels in the anchor ratio (D7); no effect on ranks |
| π_inventory = π_anchor | 0.0466 | (20.6% - 14.3%) x 0.74 | backtest | scales every return-converted family: ±50% reorders literature families vs contractual and backtest families, not among themselves |
| α_TZ | 11.39% | anchor hedge return | Thomas-Zhang 2002 | inverse scale of all converted families |
| π_DIO | 0.0318 | (21.7% - 17.4%) x 0.74 | backtest | linear |
| π_receivables | 0.0629 | (22.8% - 14.3%) x 0.74 | backtest | linear |
| π_DSO | 0.0851 | (25.6% - 14.1%) x 0.74 | backtest | linear |
| π_gross_margin_drop | 0.0422 | min(margin 12.2 pts, hard 5.7 pts) x 0.74 | backtest; gate 2 persistence finding | linear |
| π_misstatement | 0.0491 | 0.0466 x 12 / 11.39 | Beneish-Lee-Nichols 2013 "just below 1% a month" (12%/yr is rounded up, inference) | linear |
| π_risk_factor | 0.0226 | 0.0466 x 5.52 / 11.39 | Lazy Prices VW Jaccard 0.46%/month (t 3.44) | linear |
| π_litigation_text | 0.0349 | 0.0466 x 8.52 / 11.39 | Lazy Prices 71 bps/month (t 3.29) | linear |
| π_MD&A | 0.0081 | 0.0466 x 1.98 / 11.39 | Lazy Prices Table VII 11-22 bps/month | linear |
| π_insider | 0.0201 | 0.0466 x 4.92 / 11.39 | Cohen-Malloy-Pomorski VW 82 bps/month x 6 months | linear |
| π_8K | 0.0061 | 0.0466 x 1.5 / 11.39 | Lerman-Livnat 2010 lower end -1.5% | linear |
| π_min | 0.0055 | 0.0466 x 1.34 / 11.39 | Chen-Hollander-Law (WP) zero-question calls 1.34% five-day | sets the floor for directional families |
| π_none | 0.0028 | π_min / 2 | forensic note tier halving (inference) | these rows rarely reach a top 5 at any value |
| π_contractual | 1.0 | scheduled or booked events | by definition; uncertainty in ΔEPS range | n/a |
| π_reasonably_possible | 0.5 | ASC 450 midpoint | inference | linear |
| d analogs | 0.38 / 0.50 / 0.60 | oncology MFP list discount bull/base/bear | CMS IPAY 2026-2027 (Imbruvica, Ibrance, Pomalyst; `ira_cut_check.csv`) | IRA rows linear in (d - g_pre); at base -50% (0.25) Verzenio ΔRev = 71.4 |
| m | 0.20 (0.10 initial phase) | MDP rate replaced by the MFP | CMS MDP final guidance; Health Affairs | C 0.04058 / 0.02029 |
| g_pre (rebated classes) | GLP-1 0.60-0.75; insulin ~0.75; immunology 0.50-0.65 | pre-MFP concession | Drug Channels (Novo 69%, Lilly ~60%, BMS 53%); class values inference | can zero an IRA finding when g_pre ≥ d |
| s_MFN | 0.0065 (0.003-0.010) | Medicaid MFN share of US revenue | Pfizer <1% of US net (Health Affairs; PMC); midpoint inference | small rows; rarely top 5 |
| R(y) biologic | 0.65 / 0.35 / 0.20 | LOE retention | Humira, Stelara, IQVIA (KQ4) | LOE rows linear in (1 - R) |
| R(y) small molecule | 0.30 / 0.15 / 0.10 | LOE retention | KQ4; IQVIA "traditional 90% erosion" | linear |
| boxed warning | -10% to -25% volume | label channel | Mayo Clin Proc; PMC8159769 | linear |
| REMS | -5% to -15% new starts | label channel | KQ6 inference | linear |
| weekly vs daily | +10% to +15% revenue per starter, 2 yrs | label channel | HR 0.80 (0.71-0.90) | linear |
| ΔDSO* | 7 days | DSO excess that switches receivables to the reversal channel | KQ5 inference from BMS base rate | switches channel only |
| E_high, E_med | 0.95, 0.745 | HIGH and MEDIUM E thresholds | between fuzzy and exact; the entailed grade; ICD 203 mapping (priced_in KQ7) | +50% pushes E_high above 1 (HIGH impossible); -50% (0.475, 0.37) admits single fuzzy or entailed claims to HIGH and weaker rows to MEDIUM |
| O ≥ 0.5 | Needle obscurity floor | "roughly even chance" midpoint | ICD 203 bands | at 0.25 LLY row B (O = 0.30) becomes eligible, row C (0.18) does not; at 0.75 only findings under 2.5 months old with almost no analyst questions qualify |
| E ≥ 0.90 | Needle evidence floor | quoted evidence only | case "evidence that holds up" | at 0.745 paraphrases could headline |
| N* | 3 | blocks for full league credit | Lazy Prices A-9; Beneish-Lee-Nichols; inference | at 1.5 the penalty bites only on single-block companies; at 4.5 every company is penalized, ranks close to N_eff order |
| top 5 | findings summed | case minimum of five findings | case | |
| k peers | 6 | nearest financial peers off-shortlist | inference (engine needs ≥ 4) | |

### 11.2 DECIDE

| Symbol | Value | Meaning | Source | Sensitivity (±50%) |
|---|---|---|---|---|
| r | 7.85% | WACC | Damodaran Jan 2026 | reference case EV falls as r rises; long-tail moves (M3, M7) most sensitive |
| p_s | 0.50 / 0.11 / 0.39 | bear / base / bull weights | Trinity 2023 US launches | swapping toward Deloitte (36% miss) raises EV of launch-type moves |
| multipliers | 0.8 / 1.0 / 1.2 | scenario revenue | ZS success/failure definitions | spread scales linearly |
| phase rates | BIO 2011-2020 by TA, modality, non-NME | P_alive | BIO/Informa/QLS 2021 | trial moves linear in P_alive |
| non-NME | 57.5 / 37.5 / 67.5 / 91.5% | label expansions | BIO Figure 9 | reference P = 0.6176 |
| pivotal cost | median $19M; placebo $28.8M; active $48.9M | trial cost | Moore et al. 2018 | small vs revenue; affects CaR and payback |
| premium | median 63% (17-102%) | M&A cost | Evercore / Cidara SC 14D9 | dominates M1 EV and CaR |
| EV/peak | 0.5-1.0x (median ~0.56x) | M&A cross-check | Furiex DEFM14A | |
| upfront share | 3.7% early; ~5-7% overall | licensing | Goodwin 2025; Gowling; JPM/DealForma | CaR of M2 |
| royalties | 4.5-8% early; 9.3-13% Phase 1+ | licensing | Goodwin 2025; LES 2014 | linear in M2 inflows |
| CM_existing brand | 0.85 | incremental margin | inference from Damodaran 71.73% GM, 21.91% SG&A | linear |
| CM_acquired | 0.7173 less royalty | new product margin | Damodaran Jan 2026 | linear |
| time to peak | 13.3 quarters; oncology 5 years; pioneers ~8 vs followers 3-4 | uptake | IQVIA 2021; Pharmaceutical Technology; Bauer-Fischer | in-window revenue |
| coverage lag | 6-12 months | payer uptake | Tufts/ICER; MMIT | in-window revenue |
| rep cost | $134-219K/yr | sales force | Rework 2025 (vendor) | M6 cost |
| promo share | 10.8% of US sales | spend base | CBO 2008 | M6 response |
| ε | 0.06 (0.05-0.30) | promotion elasticity | Datta-Dave NBER w19592; KQ4 inference | M6 sign flips between 0.06 and 0.30 |
| DTC TV | $260-440M/yr | campaign cost | iSpot via Fierce Pharma 2024-2025 | M6 cost |
| plant capex | $1-6.5B, 3-5 yrs | onshoring | DCAT 2025; Lilly releases | M7 CaR |
| MCDA w | 0.25 each | criteria weights | ISPOR 2016 checklist; 1/N (D3) | only matters when EV intervals overlap |
| ZS thresholds | 30% / 50% / 30% at month 6 | kill signals | ZS (18 specialty biologic launches) | thresholds are published; likelihoods below |
| P(breach \| s) | 1.0 / 0.55 / 0.10 | Bayes update | ZS ("none" / inference / "~90%") | base value 0.55 is inference: at 0.275 or 0.825 posterior bear moves 0.834 to 0.88 or 0.80 |
| year-one < 80% | p_bear -> 0.70 | persistence of misses | Deloitte 2022; McKinsey 2014 | |

---

## 12. One-slide version

```
FIND    S = M · O · E · π          M = |ΔEPS| / σ_EPS (discounted)      O = Π(1 - known_i) · 2^(-age/6mo)
DECIDE  EV = Σ_s p_s · rNPV_24m(move | s)    report EV, cash at risk, payback, scenario spread, MCDA for every move
```

1. **M, materiality:** the finding's EPS impact divided by how much Wall Street usually misses this company's EPS by.
2. **O, obscurity:** the chance nobody has priced it yet: not the starter thread, not in the press-release headline, not asked by analysts, not in consensus, and fading with a 6-month half-life.
3. **E, evidence:** the chance the documents say exactly what we claim; every number is re-found on its cited page or the claim is not shown.
4. **π, track record:** how often this kind of signal turned into the bad outcome it implies, from our 1,410-quarter backtest and published studies, haircut for decay.
5. **DECIDE:** every candidate move is valued on one 24-month cash scale using clinical-trial odds, deal comps and launch-miss rates, with numeric 6-to-12-month kill signals that update the value when they trip.

---

## 13. Sources

Case and team materials
- Case: `gap-data/docs/case/fine_print_case.pdf`; rubric: `gap-data/docs/case/judging_rubric.pdf`.
- Engine and moat audit: `~/research_notes/Fine Print quant model design/needle_engine_and_moat_audit.md`; research notes in the same folder: `filing_text_forensic_signals.md`, `pharma_impact_math.md`, `priced_in_and_attention_metrics.md`, `strategic_move_valuation.md`, `citation_grounded_llm_design.md`.
- Engine: `quant-model/agent/needle/score.py`, `schema.py`, `detect/*.py`, `docs/materiality_spec.md`, `docs/needle.md`, `docs/needle_gate2.md`; backtest results `out/backtest/hit_rates.json`.
- Citation index: `gap-data/agent/moat/cite.py`, `gap-data/data/moat/README.md`, `gap-data/docs/research/citation_index.md` (commit 704741d).

Forensic and text signals
- Cohen, Malloy, Nguyen, Lazy Prices, NBER w25084: https://www.nber.org/papers/w25084.pdf ; NBER Digest: https://www.nber.org/digest/nov18/are-investors-inattentive-sec-mandated-corporate-reports
- Thomas and Zhang 2002, RAST: https://www3.ntu.edu.sg/home/HuaiZhang/inventory%20paper-RAST.pdf
- Beneish 1999 M-score (handout): https://bpb-us-w2.wpmucdn.com/u.osu.edu/dist/3/40936/files/2016/12/M-Score-pa6gdy.pdf ; Beneish, Lee, Nichols 2013: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2241717 ; AAII interview: https://www.aaii.com/journal/article/83450-detecting-earnings-manipulation-with-the-m-score
- Dechow, Ge, Larson, Sloan 2011: https://www.thecaq.org/wp-content/uploads/2018/03/Dechow-et-al-2011-Contemporary_Accounting_Research.pdf
- Cohen, Malloy, Pomorski, Decoding Inside Information: https://www.nber.org/papers/w16454.pdf
- Lerman and Livnat 2010: https://archive.nyu.edu/bitstream/2451/27579/2/SSRN-id1126816.pdf
- Gow, Larcker, Zakolyukina 2021: https://onlinelibrary.wiley.com/doi/abs/10.1111/1475-679X.12371
- Chen, Hollander, Law (summary): https://www.aaii.com/journal/article/conference-calls-no-or-few-questions-are-costly
- Druz et al. 2020: https://www.sfi.ch/en/publications/n-15-02-tips-and-tells-from-managers-how-analysts-and-the-market-read-between-the-lines-of-conference-calls-m.-druz-a.-f.-wagner-and-j.-zeckhauser-2015.
- Burks and Stevens (auditor dismissals): https://www.cfo.com/news/fire-auditors-early-cfos-are-advised/660169/
- Ryans 2021, comment letters: https://ideas.repec.org/a/spr/reaccs/v26y2021i1d10.1007_s11142-020-09565-6.html
- Abarbanell-Bushee decay (Dorey, Kim, Shin 2017): https://www.emerald.com/insight/content/doi/10.1108/MF-05-2016-0142/full/html
- McLean and Pontiff 2016: https://Www.Gwern.net/doc/economics/2016-mclean.pdf
- DeMiguel, Garlappi, Uppal 2009: https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html
- Gu, Kelly, Xiu 2020: https://www.nber.org/papers/w25398.pdf
- Harvey, Liu, Zhu 2016: https://nber.org/papers/w20592

Priced-in, attention, validation
- Fang and Peress 2009: https://www.insead.edu/sites/insead/files/assets/faculty-personal-site/lily-hua-fang/documents/media-coverage-and-the-cross-section-of-stock-returns.pdf
- Hong, Lim, Stein 2000: https://www.nber.org/digest/nov98/bad-news-travels-slowly
- Chen, Nagar, Schoenfeld 2018: https://ideas.repec.org/a/spr/reaccs/v23y2018i4d10.1007_s11142-018-9453-3.html
- Diether, Malloy, Scherbina 2002: https://www.kellogg.northwestern.edu/faculty/mcdonald/ftp/practicum/papers/dms3.pdf
- Hong, Li, Ni, Scheinkman, Yan 2015 (days to cover): https://www.nber.org/papers/w21166.pdf ; Boehmer et al. RFS 2022: https://ideas.repec.org/a/oup/rfinst/v35y2022i5p2428-2463..html ; FINRA short interest: https://finra.org/filing-reporting/short-interest
- Kothari and Warner: https://www.bu.edu/econ/files/2011/01/KothariWarner2.pdf
- ICD 203 bands (secondary): https://www.cisecurity.org/ms-isac/services/words-of-estimative-probability-analytic-confidences-and-structured-analytic-techniques ; analytic confidence: https://en.wikipedia.org/wiki/Analytic_confidence ; ACH: https://en.wikipedia.org/wiki/Analysis_of_competing_hypotheses

Pharma impact math
- CMS IPAY 2026 negotiated prices: https://www.cms.gov/newsroom/fact-sheets/medicare-drug-price-negotiation-program-negotiated-prices-initial-price-applicability-year-2026
- CMS IPAY 2028 selected drugs: https://www.cms.gov/files/document/factsheet-medicare-negotiation-selected-drug-list-ipay-2028.pdf ; CMS press release 2026-01-27: https://www.cms.gov/newsroom/press-releases/cms-announces-selection-drugs-third-cycle-medicare-drug-price-negotiation-program-including-first
- IPAY 2027 prices: https://www.biopharmadive.com/news/medicare-price-negotiation-wegovy-ozempic-trelegy-2027/806526/
- KFF key facts: https://www.kff.org/medicare/key-facts-about-medicare-drug-price-negotiation/
- MDP interaction: https://www.healthaffairs.org/content/forefront/interaction-between-manufacturer-discount-program-and-medicare-drug-price-negotiation ; CMS MDP guidance: https://www.cms.gov/files/document/manufacturer-discount-program-final-guidance.pdf
- Drug Channels GTN: https://www.drugchannels.net/2026/07/2025-gross-to-net-realities-at-eight.html ; https://www.drugchannels.net/2025/10/2024-gross-to-net-realities-at-9-top.html
- MFN deals: https://www.healthaffairs.org/content/forefront/trump-administration-s-deals-pharma-policy-progress-political-theater ; Pfizer Medicaid MFN: https://pmc.ncbi.nlm.nih.gov/articles/PMC13119475/
- Section 232: https://www.crowell.com/en/insights/client-alerts/trump-administration-imposes-section-232-tariffs-on-patented-pharmaceutical-imports-tiered-rate-structure-takes-effect-beginning-july-31-2026
- LOE: https://www.iqvia.com/locations/united-states/blogs/2025/07/the-rules-of-loss-of-exclusivity-are-being-rewritten ; AbbVie FY2025: https://investors.abbvie.com/news-releases/news-release-details/abbvie-reports-full-year-and-fourth-quarter-2025-financial ; J&J 10-K FY2025: https://www.sec.gov/Archives/edgar/data/200406/000020040626000016/jnj-20251228.htm
- BMS channel stuffing: https://www.sec.gov/news/press/2004-105.htm
- Boxed warnings: https://www.mayoclinicproceedings.org/article/S0025-6196(11)61081-1/fulltext ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8159769/
- Weekly dosing persistence: https://link.springer.com/article/10.1007/s13300-021-01189-6

Strategic moves
- BIO/Informa/QLS 2021: https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf
- Stewart, Allison, Johnson 2001: https://www.nature.com/articles/nbt0901-813
- Damodaran WACC: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html ; margins: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html
- Moore et al. 2018 (summary): https://www.ajmc.com/view/more-than-100fold-cost-differences-found-for-pivotal-trials ; Martin et al. 2017: https://journals.sagepub.com/doi/10.1177/1740774515625964
- Evercore precedents (Cidara SC 14D9): https://www.sec.gov/Archives/edgar/data/1610618/000119312525309970/d59361dsc14d9.htm ; Furiex DEFM14A: https://www.sec.gov/Archives/edgar/data/0001484478/000119312514225775/d727381ddefm14a.htm
- Goodwin licensing 2025: https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals
- Datta and Dave: https://www.nber.org/papers/w19592 ; CBO promotion: https://www.thepharmaletter.com/biotech-news/usa-s-budget-office-reviews-promotional-spending-for-prescription-drugs
- iSpot TV spend: https://www.fiercepharma.com/marketing/abbvie-maintains-top-tv-ad-spend-spot-skyrizi-sees-rinvoq-fall-behind-jjs-tremfya-novos
- LillyDirect channel share: https://corporate.walmart.com/news/2025/10/29/lillydirect-and-walmart-pharmacy-launch-first-retail-pick-up-option-with-direct-to-consumer-pricing-for-zepbound
- DCAT plants: https://www.dcatvci.org/features/big-pharma-us-manufacturing-investment/
- IQVIA launch analogues: https://www.iqvia.com/blogs/2021/10/using-historical-analogues-to-forecast-new-product-launches
- Trinity launches: https://www.emarketer.com/content/50--of-us-drug-launches-2023-missed-first-year-revenue-targets ; Deloitte 2022: https://www.deloitte.com/content/dam/assets-shared/legacy/docs/insights/2022/DI_Key-factors-to-improve-drug-launches.pdf ; McKinsey 2014: https://mckinsey.com/~/media/McKinsey/Industries/Healthcare%20Systems%20and%20Services/Our%20Insights/The%20secret%20of%20successful%20drug%20launches/The_secret_of_successful_drug_launches.pdf
- ZS launch signals: https://www.zs.com/insights/pharma-product-launch-success-signals
- Payer coverage lag: https://www.beckerspayer.com/research-analysis/new-drugs-can-see-coverage-delays-of-up-to-1-year-report/
- ISPOR MCDA: https://www.ispor.org/heor-resources/good-practices-for-outcomes-research/article/multiple-criteria-decision-analysis-for-health-care-decision-making---emerging-good-practices
- OptFolio real options: https://pure.psu.edu/en/publications/real-options-based-analysis-of-optimal-pharmaceutical-research-an/
- SDUD: https://www.medicaid.gov/medicaid/prescription-drugs/state-drug-utilization-data/index.html ; FAERS files: https://www.fda.gov/drugs/fda-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-latest-quarterly-data-files

Citations and LLM reliability
- Anthropic citations: https://platform.claude.com/docs/en/build-with-claude/citations ; search results: https://platform.claude.com/docs/en/build-with-claude/search-results ; structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Text fragments: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Text_fragments ; support: https://caniuse.com/url-scroll-to-text-fragment
- Chromium PDF params: https://chromium.googlesource.com/chromium/src/+/main/chrome/browser/resources/pdf/open_pdf_params_parser.ts?format=TEXT ; PDF.js options: https://github.com/mozilla/pdf.js/wiki/Viewer-options
- DailyMed label anchors (example): https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c6e131fe-e7df-4876-83f7-9156fc4e8228
- FinanceBench: https://arxiv.org/abs/2311.11944 ; Liu et al. verifiability: https://arxiv.org/abs/2304.09848 ; ALCE: https://arxiv.org/abs/2305.14627
- Xiong et al. calibration: https://arxiv.org/html/2306.13063v2 ; Dahl et al. legal hallucination: https://arxiv.org/html/2401.01301v1 ; Google check grounding: https://docs.cloud.google.com/generative-ai-app-builder/docs/check-grounding


## Product fine print (appended; module `agent/needle/quant/product.py`)

The case requires a side-by-side product comparison, a financial tie, and a one-sentence growth limiter with a priced-in call. Section 4.3 h gave only the elasticities. The module adds:

- **Table.** Five rows (approved uses, boxed warnings and safety, dosing and convenience, patent and exclusivity timeline, pricing and gross-to-net) by product plus the appendix rivals (`APPENDIX`, all ten companies). Label cells cite a verbatim quote on the label section page (page = section in the `fda_label` index docs), so `verify()` and `gate()` accept them; this fixes the `page None` rejection of B1. Timeline cells cite the 10-K page for the company-stated LOE and carry Orange and Purple Book dates as table refs with the discrepancy printed. Pricing cells cite CMS and White House pages for IRA and TrumpRx rows and carry Part D, Part B ASP and NADAC proxies as table refs.
- **Tie to the numbers.** A product finding has `signal_family = "product"`, the FIND row shape of 4.10, and channels:
  - IRA selected: dRev = -Claims_PartD x max(0, List30 x (1 - GTN) - MFP30), GTN 0.50/0.60/0.70 (bear/base/bull).
  - IRA expected: dRev = -Spend_Medicare x cut, cut from the quartiles of the CMS cuts already set.
  - LOE: dRev = -Rev_US x (1 - pct_of_peak_{t=1}/100), US curves by modality from `loe_curves.csv`.
  - Label breadth: dRev = -(Claims_rival - Claims_own) x capture x GrossPerClaim_own x (1 - GTN), capture 0.50/0.35/0.20 (assumed).
  - Cash price: dRev = -Rev x share_moved x (1 - Cash/List), share 0.40/0.25/0.10 (assumed scenario).
  - Boxed warning: dRev = -Rev x 0.10 to 0.25, only when no listed rival carries one.
  dEPS = dRev x CM x (1 - t) / D is left to the scorer. Assumption-driven channels cap confidence at low and rank after data-driven ones.
- **Obscurity for product findings.** Label facts are years old, so O computed on the label date is about 0 (B6). The FIND scorer should compute O on the consequence: age from the date the revenue effect first shows (MFP effective date, LOE year), attention from the scorecard share for the consequence's topic (the `topic=` flag). Each record carries `obscurity_note`.
- **Growth limiter and priced-in.** `growth_limiter` takes the top-ranked finding and returns one sentence, a boolean, reasons and citations. Priced in = (scorecard share_of_quarters_asked >= 0.5 and the case starter thread names the consequence) or share >= 0.8; consensus is reported as untested at product level.

Honest limits are in `docs/product_fineprint.md`.
