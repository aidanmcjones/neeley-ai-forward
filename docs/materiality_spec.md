# Materiality spec: what matters, and how we score it

Owner: Parker. Every detector, agent and screen writes to this contract. Works for any drug maker, not just our pick.

## 1. The rule

A finding matters when it is **big**, **likely**, **soon**, **unusual versus peers**, **not already priced in**, and **provable**. Everything else is noise. Macro and policy do not become findings on their own. They enter only through a **transmission channel** into a line item we can measure (section 4).

## 2. The quantification vector

Every finding carries this vector. Each component is computed in code except where marked LLM.

| # | Component | Symbol | What it measures | How it is computed | Range |
|---|---|---|---|---|---|
| 1 | Dollar impact | I | Effect on operating income over the next 24 months, base case | Detector formula on XBRL and filing numbers; bear and bull cases stored too | $ |
| 2 | Scale | I_norm | Impact relative to the company | abs(I) / trailing operating income (also report as EPS: I x (1 - tax rate) / diluted shares) | 0 to 1+ |
| 3 | Probability | P | Chance the impact happens in the window | Evidence-type prior (table in 5), adjusted by LLM with stated reason | 0 to 1 |
| 4 | Timing | T | How soon it hits | 1 / (1 + r)^(months/12), r from section 4 rates row | 0 to 1 |
| 5 | Peer abnormality | Z | How unusual versus the peer group | z-score of the same metric across the 10 companies plus rival makers, capped at 3 | -3 to 3 |
| 6 | Trend | D | Is it getting worse, flat, or reversing | Slope and acceleration over 3 or more periods (quarters or years) | -1, 0, 1 |
| 7 | Obscurity | O | Not priced in | 1 minus coverage score (section 3) | 0 to 1 |
| 8 | Evidence | E | Survived the verifier | verified high 1.0, medium 0.6, low 0.3, failed 0 | 0 to 1 |
| 9 | Intent | M | Why management is doing what it does now (LLM, cited) | Links the finding to a company action: M&A, BD deals, capex, buybacks, guidance change, segment change. Explanatory, not scored | text + cites |

**Score:**

```
S = I_norm x P x T x O x E x (1 + 0.25 x max(Z, 0)) x (1 + 0.25 x D)
```

- Sharpest Needle = highest S among findings with O >= 0.7 and E >= 0.6.
- Findings with E = 0 never reach the screen; they go to eval/rejections.jsonl.
- Weights (0.25) are a starting guess. Tune them with the backtest (section 7) and say so in the report.

## 3. Obscurity (is it priced in?)

Coverage score, 0 to 1, the max of:

| Check | Score if yes | Source |
|---|---|---|
| Part of the case's starter thread for this company | 1.0 | Case appendix |
| In the company's earnings press release headline or top bullets | 0.9 | 8-K EX-99.1 |
| An analyst asked about it on one of the last 4 calls | 0.7 | Transcripts |
| Management raised it in prepared remarks | 0.6 | Transcripts |
| Three or more news or analyst articles found | 0.6 | Web search (deep research, run only on finalists) |
| Only in 10-K or 10-Q body, footnote or exhibit | 0.1 | Corpus |

O = 1 - coverage. This is how the tool tells "material" from "material and missed".

## 4. Forces and transmission channels (every variable, each with a path to dollars)

The question for each force is: which line item moves, how exposed is this company, how big is a plausible shock. Impact = exposure x shock. Each force gets a company-specific exposure from the filings and a scenario shock we state and source.

| Force | Transmission channel | Company exposure (from filings) | Shock scenario | Data source |
|---|---|---|---|---|
| **IRA negotiation** | Net price on selected drugs from the effective date | Medicare share of each selected drug's US sales | Published maximum fair price vs current net | CMS selected drug list and MFP files (data/external) |
| **IRA Part D redesign** | Manufacturer discounts in Part D, out-of-pocket cap changes demand and liability | Part D share of US sales | Discount rate on Part D spend; verify current percentages against CMS | CMS Part D spending (data/external), 10-K MD&A |
| **IRA inflation rebates** | Rebate owed when price increases beat inflation | List price increase history for Medicare drugs | Price increase above CPI-U x Medicare units | 10-K, CMS, BLS CPI-U |
| **MFN deal** | US net price cuts toward international reference prices | Drugs and channels covered by the deal | Deal terms as disclosed | 8-Ks and press releases on the deal, 10-Q |
| **Tariffs** | 100% tariff on imported patented drugs after the January 2029 exemption ends | Share of US product made outside the US; promised US capex | Tariff cost if US build-out slips; capex already committed | 10-K properties and manufacturing, MFN 8-Ks |
| **Payers and PBMs** | Gross-to-net widens through rebates, formulary exclusions | GTN accrual rollforward, rebate reserves growth vs revenue | Observed GTN trend extended | 10-K revenue recognition footnote |
| **Medicaid and coverage** | Covered lives shrink or shift, Medicaid best-price rebates | Medicaid share of US sales | Enrollment change scenario | 10-K, CMS enrollment |
| **340B** | Discounts on drugs bought by covered entities | 340B share, any rebate-model disputes | Disclosed amounts | 10-K risk factors, litigation footnote |
| **FDA and HHS policy** | Approval timing, label changes, advisory committee use, vaccine policy, review staffing | Pending decision dates (PDUFA), vaccine revenue share | Delay of N months on key launch revenue | FDA announcements, company pipeline tables, Federal Register |
| **Interest rates** | Discount rate (T), interest expense on floating debt, cost of funding M&A for Part 2 | Floating-rate debt, maturities in window, cash | +/- 100 bp on 10-year Treasury | 10-K debt footnote, FRED DGS10 |
| **Inflation** | COGS and SG&A cost growth; IRA rebate threshold | Cost base | CPI change scenario | 10-K, BLS |
| **FX** | Ex-US revenue translated to USD (critical for 20-F filers) | Ex-US revenue share, hedging disclosed | +/- 10% USD | 10-K or 20-F market risk section |
| **Competition and class trends** | Share loss to rivals, generics, biosimilars | Product revenue and growth vs rival products | Decline curve (agent/loe_curves.py) or observed share trend | Product table, rival 10-Ks, Orange and Purple Book |
| **Company events** | Acquisitions, licensing deals, contingent payments, restructuring, litigation | Contingent consideration, reserves, milestones owed | As disclosed | 10-K footnotes, 8-Ks |

Two outputs from this table:
1. **Tornado chart per company:** EPS swing from each force under its shock, largest first. That chart answers "what matters for this company" visually.
2. **Force-adjusted impact:** a finding's I is recomputed under the bear case of the forces that touch it, so a GTN finding on a drug also selected for IRA negotiation is scored on both.

## 5. Probability priors by evidence type

| Evidence | P prior |
|---|---|
| Contractual or legal certainty (signed MFN terms, published MFP, patent expiry with generic approved) | 0.9 |
| Management guidance or stated plan | 0.7 |
| Trend in reported numbers over 3 or more periods | 0.6 |
| Language drift or new risk factor wording | 0.4 |
| Single-quarter anomaly | 0.3 |

The LLM may move P by up to 0.2 from the prior, and must cite why.

## 6. Finding schema (JSON, one per finding)

```json
{
  "id": "<TICKER>-2026-001",
  "ticker": "<TICKER>",
  "detector": "gtn_rollforward",
  "finding": "One plain-English sentence.",
  "source": {"doc": "10-K FY2025", "page_printed": "87", "quote": "exact text"},
  "numbers": [{"name": "rebate_accrual", "value": 0, "period": "FY2025", "xbrl_tag": ""}],
  "impact": {"formula": "text with the math", "base": 0, "bear": 0, "bull": 0, "line": "operating_income", "eps": 0},
  "peer": {"metric_value": 0, "peer_median": 0, "z": 0, "note": "how it looks at a named peer"},
  "forces": ["ira_negotiation", "payers_pbm"],
  "vector": {"I_norm": 0, "P": 0, "T": 0, "Z": 0, "D": 0, "O": 0, "E": 0},
  "intent": {"text": "", "cites": []},
  "score": 0,
  "confidence": "high | medium | low",
  "verifier": {"status": "verified | rejected | needs_human", "reason": ""}
}
```

## 7. How we prove the scoring works

- **Backtest:** run the engine on FY2021 and FY2022 filings (already in R2 `tenk/`). For each top-10 finding, check whether a reported revenue, guidance or write-down event followed within 24 months. Report hits and misses honestly.
- **Generality:** run it live on a ticker outside the shortlist.
- **Human check:** Parker reviews every finding that goes on a slide; adversarial review on the final 10 and the Part 2 math.

## 8. Limits we will state

- Probabilities and weights are judgment calls, tuned on a small backtest.
- Obscurity depends on transcript and news coverage we can actually gather.
- Policy shocks (MFN terms after 2029, FDA timing) are scenarios, not forecasts.
