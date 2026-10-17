# League v2: what changed and what to read first (for the 4:30 pick)

Source: `out/league_v2.md` / `.json`, from `python -m agent.needle.quant.run --all` (FIND, `docs/quant_model.md`). It is deterministic and needs no API key. Every finding row, with all its components and citations, is in `out/<T>/findings_v2.jsonl`.

## New top 3

| Rank | Ticker | L (old L, old rank) | Top finding (S) | Sharpest Needle |
|---|---|---|---|---|
| 1 | AMGN | 0.543 (0.089, #5) | Receivables +17.5% YoY vs revenue +9.5% (Q2 2026), gap +8.0 pts. Fires the backtest flag (S 0.238, MEDIUM) | Same row, strict (O 0.76, E 1.0). Next: Medicaid MFN at the base rate (S 0.222) and Otezla IRA 2027 (S 0.217, HIGH) |
| 2 | GILD | 0.407 (0.108, #4) | Biktarvy Medicare negotiated price from Jan 2028; CMS spend $3,904.5M (S 1.078, HIGH) | Biktarvy, **provisional** (O 0.29 < 0.5: no GILD row clears the floor) |
| 3 | JNJ | 0.195 (0.070, #8) | Medicaid MFN at the Pfizer base rate on US revenue (S 0.232, MEDIUM) | Inventory +12.9% vs revenue +6.6% (S 0.024, O 0.66). Strict, but weak: pi was cut to pi_min |

Then AZN 0.113, MRK 0.097, ABBV 0.088, BMY 0.070, LLY 0.069 (old #1), PFE 0.038, NVO 0.028.

The top two hold under every variant I ran: the spec's IRA formula in place of the class rule, no MFN rows, no drift/call placeholders. Without the concentration penalty, GILD and AMGN swap places. The 3rd place moves (JNJ, AZN or MRK), so treat 3rd as unsettled.

## What changed versus the old table, and why

1. **The bug (fixed in commit 4009a40, which can be cherry-picked).** `score._impact` treated a gross-margin **level** as a margin **change**. For LLY it computed 0.858 x TTM revenue, about $68B of "impact", which capped at 1.0. That one row, "Gross margin 85.8% vs peer median 74.1%", gave LLY 80.3% of its old score (0.2437 of 0.3034). The row is also favourable to LLY. Under FIND it has pi = 0 and S = 0. **LLY's old first place came entirely from this row.** The concentration penalty did not cause it: on these scores N_eff never reaches 3 (max 2.19), so the penalty only multiplies each company by N_eff/3.
2. **New scale.** S = M x O x E x pi. M is the EPS impact divided by the company's usual EPS surprise. This rewards companies with low surprise noise (JNJ sigma 0.146, AMGN 0.345). It penalises LLY (sigma 2.03, 3 to 14 times its peers).
3. **New channels.** The old engine had no IRA or MFN dollar math. IRA rows now use the CMS spend and the published or analog discounts. MFN rows apply 0.65% of US revenue.
4. **Review fixes applied.** (a) A backtest prior applies only when the row meets that flag's trigger. LLY's DIO (+14.2% YoY, trigger 15%) drops from 0.00973 to 0.00168. (b) AZN's I/B/E/S figures mixed per-ADR and per-share data. sigma is now 0.541, not 0.419. (c) The IRA net hit uses the KQ2 class rule: 1.0x the list discount for oncology and HIV, 0.3 to 0.5x for rebated classes. Verzenio is S 0.0507 under the rule and 0.0304 under the spec formula. (d) Drift and call rows carry a generic 3%-of-revenue placeholder. Their E is capped at 0.745.

## Read these before using the ranking

- **GILD Biktarvy (S 1.08) is the single largest S anywhere, and it rests on an assumption.** No HIV drug has a published MFP, so the discount is the cycle 1-2 range: 38% / 65.5% (median) / 85%, at 1.0x for a low-rebate class. If HIV Part D rebates are material, it falls sharply. It also sits next to GILD's starter thread (how long HIV dominance lasts), and analysts asked about IRA. It is not needle-eligible.
- **AMGN receivables and DSO (93 days vs peer median 72).** The receivables flag meets the backtest trigger (gap >= 8 pts). Check the 10-Q for a timing or acquisition cause, or for Medicare Part D redesign billing, before calling it channel stuffing. The wholesaler-language half of the stuffing test is not automated.
- **MFN rows (AMGN, JNJ, ABBV, BMY, GILD).** These use Pfizer's Medicaid rate (0.65% of US revenue) for every company, because the deal texts are confidential. Medicaid MFN started in 2026, so part of the effect may already be in reported numbers. Dropping MFN keeps AMGN and GILD on top, and AZN replaces JNJ at 3rd.
- **Ratio flags that may be capacity build or pre-launch stocking:**
  - LLY DIO 469 days: 84% is work in process and raw materials, and finished goods cover 73 days. Flag: "capacity build, not channel stuffing".
  - AZN inventory +24% vs revenue +8.6% (FY2025, 20-F, annual): check for launch stocking.
  - JNJ inventory gap +6.3 pts: below the 10-pt backtest trigger, so it gets pi_min.
- **Needle floor.** 5 of 10 companies (GILD, AZN, ABBV, BMY, NVO) have no row with O >= 0.5. With a 6-month half-life, February 10-K and 20-F items decay below the floor. The needle column labels these picks "provisional".
- **20-F filers.** NVO and AZN have no earnings release in the index, so their headline term is imputed. NVO I/B/E/S data is in DKK and is matched to DKK XBRL. NVO's semaglutide IRA row is the starter thread, so O = 0.
- **Tax inputs.** MRK, PFE and GILD TTM GAAP effective tax rates are distorted by one-off charges (0.467, -0.039, -0.657). They use the peer median, 0.185.
