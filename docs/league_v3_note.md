# League v3: what survived the review, and what to read before the pick

Source: `out/league_v3.md`, `out/league_v3.json` and `out/league_v3_robustness.json`, from `python -m agent.needle.quant.run --all` on branch quant-model (FIND after the two-round adversarial review, `scratchpad/review/synthesis.md`). The score itself is computed by code with no model call. Every row, with its components, citations, guard and "not quantified" reason, is in `out/<T>/findings_v2.jsonl` (rows that failed the citation gate or a drop guard are in `rejected_v2.jsonl`).

## The table

| Rank | Ticker | L | Top-5 sum | N_eff | Top finding (S) | Sharpest Needle | v2 L (rank) |
|---|---|---|---|---|---|---|---|
| 1 | AMGN | 0.0877 | 0.2047 | 1.29 | Receivables 10,227 vs 8,701 a year earlier (+17.5%, Q2 2026 vs Q2 2025) against quarterly revenue 10,054 vs 9,179 (+9.5%); gap +8.0 pts (S 0.1787, MEDIUM) | same row, strict (D 1.00, O 0.57) | 0.5432 (1) |
| 2 | GILD | 0.0511 | 0.1532 | 1.00 | Biktarvy Medicare negotiated price from Jan 2028, CMS spend $3,904.5M, assumed base list discount 65.5% (S 0.1531, HIGH) | Biktarvy, floor relaxed (D 0.40) | 0.4067 (2) |
| 3 | AZN | 0.0290 | 0.0674 | 1.29 | DSO 64 days vs 56 a year earlier (+13.5%, FY2025) (S 0.0237, MEDIUM) | same row, strict (D 1.00) | 0.1127 (4) |
| 4 | MRK | 0.0199 | 0.0597 | 1.00 | Gross margin 73.5% vs 77.5% (-4.0 pts, Q2 2026) (S 0.0597, MEDIUM) | same row, strict (D 1.00) | 0.0970 (5) |
| 5 | BMY | 0.0086 | 0.0257 | 1.00 | Pomalyst negotiated price from Jan 2027 (S 0.0165, HIGH) | Pomalyst, floor relaxed (D 0.30) | 0.0698 (7) |
| 6 | NVO | 0.0081 | 0.0243 | 1.00 | Gross margin 81.0% vs 84.7% (-3.7 pts, FY2025) (S 0.0140, MEDIUM) | same row, strict (D 0.90) | 0.0281 (10) |
| 7 | ABBV | 0.0066 | 0.0197 | 1.00 | Linzess negotiated price from Jan 2027 (S 0.0101, HIGH) | same row, strict (D 0.60) | 0.0881 (6) |
| 8 | LLY | 0.0051 | 0.0152 | 1.00 | Trulicity negotiated price from Jan 2028 (S 0.0086, HIGH) | Trulicity, provisional (D 0.25) | 0.0691 (8) |
| 9 | PFE | 0.0007 | 0.0020 | 1.00 | Xeljanz negotiated price from Jan 2028 (S 0.0020, HIGH) | Xeljanz, floor relaxed (D 0.25) | 0.0384 (9) |
| 10 | JNJ | 0.0001 | 0.0004 | 1.00 | Medicaid MFN agreement, direction only (S 0.0004, MEDIUM) | none | 0.1950 (3) |

L = (sum of the top-5 S, one row per underlying fact) x min(1, N_eff / 3). The scale is lower than v2 for every company because H is now 3 months (decay is stronger), untestable consensus terms are 0.5 instead of 0, MFN is at pi_min, and text and call rows without an impact channel no longer score. Compare ranks, not raw values, across versions.

## Robustness: who leads under each variant

| Variant | #1 | #2 | #3 | #4 | #5 | Strict needles |
|---|---|---|---|---|---|---|
| Base (v3 rules) | AMGN 0.0877 | GILD 0.0511 | AZN 0.0290 | MRK 0.0199 | BMY 0.0086 | 5 of 10 |
| No N_eff/3 multiplier (raw top-5 sum) | AMGN 0.2047 | GILD 0.1532 | AZN 0.0674 | MRK 0.0597 | BMY 0.0257 | 5 of 10 |
| MFN at the universal 0.65% with pi = 1 (v2 rule) | AMGN 0.1681 | GILD 0.0576 | AZN 0.0290 | JNJ 0.0265 | MRK 0.0199 | 10 of 10 |
| AMGN receivables row at pi_min, anchor kept | GILD 0.0511 | AZN 0.0290 | AMGN 0.0261 | MRK 0.0199 | BMY 0.0086 | 5 of 10 |
| AMGN receivables row as unfired (v3 rule: S = 0) | GILD 0.0511 | AZN 0.0290 | MRK 0.0199 | AMGN 0.0087 | BMY 0.0086 | 5 of 10 |
| H = 6 months | AMGN 0.1847 | GILD 0.1386 | AZN 0.0825 | BMY 0.0280 | MRK 0.0264 | 5 of 10 |
| IRA on the spec formula G x max(0, d - g_pre) | AMGN 0.0785 | GILD 0.0460 | AZN 0.0270 | MRK 0.0199 | ABBV 0.0118 | 5 of 10 |
| c = 0.5 on anchor rows too | AMGN 0.0591 | GILD 0.0511 | AZN 0.0197 | MRK 0.0100 | BMY 0.0086 | 4 of 10 |

What the table settles, and what it does not:

- **AMGN leads in 6 of 8 variants. GILD leads in the other 2,** and both of those are about one row. AMGN's L is 87% one finding: receivables growth beat revenue growth by +8.01 pts against a backtest trigger of 8.00 pts. If that row is read as below the trigger, GILD is first and AMGN falls to 3rd or 4th. **1st place is unsettled between AMGN and GILD.** It turns on a 0.01-pt margin and on whether the receivables build has a benign cause (see the caveats).
- **2nd place:** GILD in 6 variants, AZN in 2. **3rd place:** AZN in 6, AMGN in 1, MRK in 1. AZN at 3rd is the most stable place below the top two.
- The N_eff/3 multiplier no longer decides #1. Without it AMGN still leads (0.2047 vs 0.1532). In v2 it flipped AMGN and GILD.
- The MFN rule no longer decides anything at the top. Restoring the v2 universal rate puts JNJ back at 4th, from a single MFN row, but leaves the top three unchanged.
- The IRA formula choice moves GILD's value by about 10% and does not change the order.

## Sharpest Needle status per company

The floor now applies to the discussion term D = (1-z)(1-h)(1-a)(1-c)(1-s), not to O. Decay stays inside S (review R1). Because the half-life acts only on S, the count of strict needles is the same at H = 3 and H = 6.

| Status | H = 3 (base) | H = 6 |
|---|---|---|
| Strict | 5: AMGN, AZN, MRK, NVO, ABBV | 5: the same five |
| Provisional | LLY | LLY |
| Floor relaxed | GILD, BMY, PFE | GILD, BMY, PFE |
| None | JNJ (its only scored row is an MFN placeholder, which cannot be a needle) | JNJ |

GILD's Biktarvy row has D 0.40. Analysts asked about IRA in some quarters (a = 0.2), and the FY2028 consensus started after the selection, so c = 0.5 (untestable). Under v2's O floor, 5 of 10 had no strict needle. Under v3, 5 of 10 have one, and the set is different: AMGN, AZN, MRK, NVO, ABBV. With c = 0.5 on anchor rows as well, NVO drops to floor relaxed (4 of 10).

## What changed from v2, and which finding ids moved

| Change (review id) | Effect | Rows |
|---|---|---|
| MFN direction-only at pi_min, no universal dollar figure (R3, A9, B9) | JNJ's #1 row falls from S 0.2322 to 0.0004, and JNJ drops from 3rd to 10th. AMGN's #2 row falls from 0.2219 to 0.0004. ABBV's #1 falls from 0.0743 to 0.0001. NVO and BMY are sized from their own rows (stated low-single-digit growth impact; Eliquis free to Medicaid, about $1,093M upper bound via SDUD). Both took effect before as_of, so dEPS = 0 under the IRA timing rule (S2). | JNJ 00b6e9d6910d, AMGN e78dad58497e, ABBV 63ebf779aa7c, GILD f87b31bee9cb |
| Same-fact dedupe (S1) and guard 6 | AZN's second +14.7-pt receivables row is gone. | AZN a459fbf4164d dropped |
| Needle floor on D, H = 3, age from the first public date (R1, A11, B5) | All S fall (stronger decay). Needle eligibility no longer depends on age. Financial-statement rows date from the earnings release (AMGN 2026-08-04, not the 10-Q of 08-05). | all |
| Anchor only on fired backtest flags; text and call rows mapped or not quantified (R2, A20, B4) | Drift and call rows no longer score. In v2 they filled slots 4-5 for AMGN, GILD, JNJ, MRK and ABBV. Unfired peer outliers score 0 (JNJ inventory 0dbc04560b20; AMGN DSO peer outlier). | AMGN 4c3a0c3d5f1d, 9c705c10b1e3; GILD 573cebabc205; JNJ a177107eb269, 0dbc04560b20; MRK 11c157283e99 and others |
| One Lazy Prices table (A5) | pi for MD&A rises from 0.0081 to 0.0226 (Table II for all text families), and litigation pi applies only when litigation is the only topic. No league effect, because those rows are now not quantified. | text rows |
| Consensus term 0.5 when untestable (A12) | It halves S on IRA rows whose fiscal-year consensus started after selection: Biktarvy, Trulicity, Verzenio, Xeljanz, Orencia, Botox. | GILD 49af018377a3 and others |
| One IRA formula (S2, S3, A15) | G x max(0, k x d - m_avoided). Verzenio's base dRev is 500.0 (was 714.4 under the class rule and 428.6 under the spec formula). product.py and DECIDE now use the same implementation. | all IRA rows |
| Citation fixes D1, D11, D4 | See the next section. | AMGN bc852b02400d, GILD 49af018377a3 |
| Red-team guards 2-9 | See below. No L changes, because every guarded row already scored 0 under R2. They change which rows exist and which can be a needle. | see the guards section |

## What D1, D11 and D4 did to the top three

- **D1 (AMGN #1, bc852b02400d).** The row was re-derived from XBRL on one basis. Receivables were 10,227 at Jun 30 2026 vs 8,701 at Jun 30 2025 (+17.5%). Quarterly revenue was 10,054 vs 9,179 (+9.5%). The gap is +8.01 pts. The detector's numbers were already year on year and correct. The problem was citation: the cited balance sheet compares Jun 2026 with Dec 2025 (+6.9%), and the prior-year figure had no citation. All four operands are now cited as XBRL frames and as statement pages (including the Q2 2025 10-Q, p. 8 and p. 6). The gap is a derived citation, and the peer median and z are labelled as derived from the peer panel. **Score and rank are unchanged, and the row still fires its trigger, at +8.01 vs 8.00.**
- **D11 (constants for every company).** Q4 flows (revenue, tax, pretax for CY2025Q4) are now derived citations, "FY minus Q1-Q3", over the CY2025 frame and the three quarter frames, with status "derived", not "exact". No score changes.
- **D4 (GILD #2, 49af018377a3).** The sentence now says "assumed base list discount 65.5% (median of the 16 cycle 1-2 negotiated discounts; cited range 38% to 85%)". The range endpoints (Imbruvica 38%, Janumet 85%) are cited. Six other analog quotes, which never verified because they were under the 20-character floor, now verify. No score change.
- **AZN (#3)** is not touched by D1, D4 or D11. Its rows are annual 20-F rows, which guard 5 re-derives from the annual table with no mismatch.

## Guards from the red-team (agent-chat #19)

| Guard | Rows it changed |
|---|---|
| 2 DIO peer comparison on revenue | LLY "Days inventory 469 days vs peers" dropped: 67 days on revenue vs a peer median of 48, z +1.0 |
| 3 tax on TTM; no tax row when pre-tax < 5% of revenue | Dropped: PFE 2 rows (Q2 pre-tax -653M), MRK 2 (-683M), GILD 2 (-10,254M), LLY 1 and BMY 1 (TTM shift under 4 pts) |
| 4 acquired IPR&D one-off | MRK R&D shift and R&D-ratio outlier marked context (Terns $5.7B, 59% of Q2 R&D; ex-charge 24.3% vs 25.6%). MRK tax rows are one-offs because the filing says the charge had no tax benefit |
| 5 period consistency | AZN and NVO annual rows re-derived from the annual table. No row has a mismatch today |
| 6 twin peer-outlier drop | AZN rec_gap_peer_outlier |
| 8 undirected MD&A not a needle | 158 MD&A rows marked no-needle across the ten |
| 9 paragraph filter | 76 drift and call rows dropped (tables of contents and parsed tables), most in AZN (15) and NVO (14) |

Guard 1 (favourable outliers at pi = 0) and guard 7 (label rows M = 0) were already in FIND. `run.py --nuggets <file|dir>` loads nugget-miner rows through the same scoring, guards and citation gate. It has been tested on a two-row sample; Parker's real files are on his unpushed branch.

**Against Parker's needle-branch league (AZN 0.133, MRK 0.099, NVO 0.099, GILD 0.081, AMGN 0.069).** The two scales are not comparable, but the orderings can be compared. Both tables put AZN and MRK in the top four and GILD in the top four. They differ on AMGN and NVO. Parker's scorer has AMGN last of its five. FIND puts AMGN first, but only because of one receivables row that clears its trigger by 0.01 pts. When that row is treated as unfired, FIND's order (GILD, AZN, MRK, AMGN, BMY) is close to Parker's apart from NVO. NVO is 6th here for three reasons: its USD policy channels are not converted (no cited FX), its semaglutide IRA row restates the starter thread (z = 1), and guard 9 removed 14 table-of-contents drift rows. Parker's NVO score may rest partly on rows of that kind.

## Caveats a human must read before the pick

1. **AMGN's lead is one row on a trigger edge.** Before pitching it, read the Q2 2026 10-Q for a timing, acquisition or Part D redesign billing cause of the receivables build. The wholesaler-language half of the channel-stuffing test is not automated. If there is a benign cause, GILD leads.
2. **GILD's value rests on an assumption.** No HIV MFP has been published. The 65.5% discount is the median of the cycle 1-2 negotiated discounts, and the cited range is 38% to 85%. The row also sits next to GILD's starter thread (HIV durability), so a human check is needed.
3. **The top-5 tables are thin.** Most companies have 1 to 4 scored rows, because text, call and unfired peer rows are "not quantified" (R2). The case's five-findings deliverable should draw on the not-quantified rows in findings_v2 as qualitative findings, with their reason shown.
4. **MFN is a direction.** The internal placeholder M (0.65% of US revenue) is never printed and cannot be a needle. NVO and BMY have company-specific sizes, but those are already in reported numbers.
5. **20-F filers.** AZN and NVO have imputed headline terms. NVO's USD channels are zeroed.
6. **The consensus term.** c = 0.5 applies only where the test is defined but cannot run (type C and MFN rows). Anchor rows keep c = 0. The variant row shows the effect of giving them 0.5 as well.
7. **New tickers.** A ticker off the shortlist must be onboarded into the citation index before FIND can cite it (scraper side: `python -m agent.moat.onboard_company <TICKER>`, then `index.py --add`). The peer set for an off-shortlist ticker is still the ten-company shortlist; a dedicated peer set is not built.

## Constant names (for the spec writer)

- `weights.H_MONTHS = 3.0` (base) and `weights.H_MONTHS_SENSITIVITY = 6.0`.
- `weights.C_UNTESTABLE = 0.5`.
- `weights.K_LOW_REBATE = (1.0, 1.0, 1.0)`, `weights.K_NET = (0.3, 0.4, 0.5)` and `weights.M_MDP_AVOIDED = (0.20, 0.15, 0.10)`. The single formula is `impact.ira_class_rule`. The IRA price effect uses CM_PRICE = 1.00 everywhere, including product.py.
- `weights.TEXT_ALPHA_TABLE` ("Lazy Prices Table II (whole document)"). PI_MDNA is 0.0226.
- DECIDE: `moves.LABEL_RAMP_MONTHS = 60` (40% of peak at 24 months), `moves.LABEL_RAMP_MONTHS_ALT = 42`, and `decide.finding_weight` (M x E).
- Robustness knobs: `find.MFN_UNIVERSAL`, `find.FORCE_PI_MIN`, `find.IRA_MODE` and `find.C_ANCHOR_UNINFORMATIVE`.
