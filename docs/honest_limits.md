# Honest limits

Pitch-ready. Each line states what we cannot see and the proxy we use instead. Model detail: `docs/quant_model.md` Section 9.

| Limit | Sentence for the pitch | Proxy we use |
|---|---|---|
| True net prices | "No product-level net price is public, so we never claim one." | Company-level gross-to-net disclosures, Medicare Part B ASP (net-like), Part D gross spend, NADAC (list-like) and Medicaid SDUD; a 50 / 60 / 70% GTN band labelled as inference |
| Ex-US volume | "Filings give ex-US revenue but not units or price, so our policy and patent math covers the US only." | US revenue from the filing's geographic split |
| Commercial formularies | "PBM formulary and rebate contracts are private." | Medicare Part D claims, company commentary and published coverage-lag studies (6 to 12 months) |
| Q3 2026 results | "Most Q3 results land after judging; our numbers run through Q2 2026." | Up to nine directional calls sealed by hash before the results (J&J reported before our cut-off) |
| Confidential MFN terms | "MFN deal terms are confidential. We score MFN as a direction, not a dollar amount, except where a company states its own effect." | The agreement, its date and the company's US revenue share; Pfizer's Medicaid base rate is used only to rank, never printed. Novo and BMS state their own effects, but both took effect before our cut-off, so they are already in reported numbers and score zero |
| No HIV MFP published | "No HIV drug has a negotiated Medicare price yet, so Gilead's Biktarvy exposure is a range, not a point." | The full range of published cuts (38%, 65.5% median, 85%) at the low-rebate rule; under the alternative formula Gilead's score moves about 10% and its rank does not change |
| Short interest not collected | "We have no short-interest data, so we cannot see whether short sellers already positioned on a finding." | The term is set to "no information" and flagged on every row, which makes obscurity optimistic for heavily shorted names |
| I/B/E/S is licensed | "Analyst consensus data are licensed; the numbers feed our math but are shown only in the local app." | The noise scale (σ) and consensus test run locally; public output shows the result, not the rows |
| Backtest raw panel not on disk | "Our signal track record comes from one 43-firm backtest whose summary we keep but whose raw panel we cannot re-run tonight." | The committed hit rates, haircut 26% for data mining, shown as tiers (within about a factor of two); peer-level outliers get no track-record credit until tested |
| Five of ten companies have no strict needle | "For five of ten companies no finding clears every Sharpest Needle condition; for those we name a provisional or floor-relaxed needle and label it." (league_v3: strict for AMGN, AZN, MRK, NVO and ABBV, at both a 3- and a 6-month half-life; LLY provisional; GILD, BMY, PFE floor relaxed; JNJ none) | The fallback pick: highest score among the company's less-discussed findings, labelled "provisional" or "floor relaxed" |
| Attention data are thin | "Analyst attention is measured from up to ten earnings calls, and outside nine scored topics it comes from a keyword match." | The priced-in scorecard for nine topics; a regex over analyst turns for the rest; the scorecard median, flagged, when nothing matches |
| No public page viewer | "Every footnote opens the source document, but the page-highlight viewer runs only in our local app." | SEC text-fragment links (Chrome and Edge highlight the quote), PDF page links, plain DailyMed label pages, and the file page and printed page in every footnote |

Further limits a judge may ask about:
- **Track records are tiers.** "Signal track records come from one 43-firm, between-firm backtest and published return studies; they rank evidence types to within about a factor of two and are shown as tiers, not exact probabilities."
- **Text and call findings.** "Text and call findings without a mapped dollar channel are shown with their evidence tier and no dollar figure, and stay out of the top-five table."
- **Noise scale.** "Materiality divides by the company's usual quarterly EPS miss, annualized by an assumed factor of two; impacts one to two years out are compared on that near-term scale."
- **Consensus test.** "When consensus for the affected year did not exist before the disclosure, we cannot test whether analysts priced it, and we assume a 50% chance they did."
- **Foreign filers.** "AstraZeneca and Novo Nordisk have no earnings release in our index, so their headline term is imputed from the other eight; Novo's dollar-based policy channels are not converted."
- **Coverage.** "Several signal families in the design (insider sales, 8-K items, misstatement scores, gross-to-net, footnotes) have no detector yet; patent-loss inputs are thin for four companies."
- **Ten companies.** "With ten companies no ranking can be statistically significant (minimum p = 0.10); we show the pick survives a published robustness table instead."
- **DECIDE.** "Scenario weights are a launch base rate applied to every move, and the bear and bull multipliers are boundary values, so the scenario spread is understated and the value leans optimistic."
- **Facts.** "69,553 facts in the store, 10,963 of them page-verified."
