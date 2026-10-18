# How we picked Merck (MRK)

One goal: find qualitative evidence that something about a company's drugs is mispriced. These steps show how we got from 10 candidate drugmakers to Merck.

## Steps

1. **Read the case.** `04 Advanced_Pharma_Fine_Print_Case.pdf` asks us to pick 1 of 10 drugmakers and deliver 5+ cited findings with page numbers, impact math and one Sharpest Needle; `AI_Innovation_Competition_Judging_Rubric.pdf` sets the scoring.
2. **Build the corpus.** `agent/corpus.py`, `agent/drug_pack.py` and `agent/ir_fetch.py` saved 835 page-marked documents for the 10 companies, their rivals and 52 drugs into `data/corpus/`, indexed in `data/corpus/manifest.jsonl`.
3. **Mine all 10 companies.** The `fineprint/agents/nugget-miner.md` prompt compared each company's FY24 and FY25 10-Ks, latest 10-Q, call transcripts and labels against each other to find fine print the market is not discussing.
4. **Verify every quote.** `fineprint/pages.py` and `fineprint/schema.py` confirm each quote sits on its cited page; misses go to `fineprint/out/MRK/MRK_ai_caught.jsonl` (19 caught).
5. **Red-team and score.** `fineprint/agents/red-team.md` attacked each company's best finding on 10 checks (already said on a call, priced in, stacked assumptions, untrusted transcript and others), and `fineprint/out/red_team_v3_final.md` scored all 10 out of 30.
6. **Merck ranked first at 25.5**, ahead of JNJ (24.5) and PFE (23.5). Its 2.5% Keytruda royalty to BMS and Ono ends Dec 31, 2026. That gives 2027 a one-year cost cut of about $0.54B to $0.79B net ($0.19 to $0.27 EPS) right before the Dec 2028 Keytruda cliff, and the word "royalty" appears on none of Merck's four calls.
7. **The evidence checks from both sides.** Merck's 10-K (p.54) and 10-Q (p.34) state the royalty terms, and BMS's 10-Q (p.10) shows the matching income; the two agree within 1%.

## Scores (red team v3)

| Rank | Company | Score /30 |
|---|---|---|
| 1 | MRK | 25.5 |
| 2 | JNJ | 24.5 |
| 3 | PFE | 23.5 |
| 4 | BMY | 22 |
| 5 | AMGN | 20.5 |
| 5 | NVO | 20.5 |
| 7 | LLY | 20 |
| 8 | ABBV | 19.5 |
| 9 | GILD | 19 |
| 10 | AZN | 17.5 |

Merck by criterion: Needle 4, Rows 5, Product 4.5, Part 2 4, Evidence 4, Distance 4. The Needle point was lost because the royalty end date has been public since 2017 (the priced-in check), so the slide must answer that: the date was public, but 2027 as a one-year margin peak before the cliff has not been priced.

## Re-verification run (Oct 17, 2026)

All 12 MRK findings in `fineprint/out/MRK/MRK.jsonl` were re-checked with `fineprint.pages.check`:

- 110 of 110 cited quotes found on their cited page.
- 14 of those quotes come from rival filings (BMS, Pfizer, J&J, GSK, AstraZeneca), so the rivals' documents must be loaded along with Merck's.

```
from fineprint.pages import docs, check
d = {}
for t in ["MRK", "BMY", "PFE", "JNJ", "GSK", "AZN"]:
    d.update(docs(t))
```

## Files used

- Case and rubric: `04 Advanced_Pharma_Fine_Print_Case.pdf`, `AI_Innovation_Competition_Judging_Rubric.pdf` (Hackathon folder)
- Merck sources: `data/corpus/companies/MRK/` (`10k_FY2024.md`, `10k_FY2025.md`, `10q_2026Q1.md`, `10q_2026Q2.md`, `transcripts/`)
- Rival sources for cross-checks: BMY 10-K and 10-Q, PFE 10-K, JNJ 10-K, AZN 20-F, GSK 6-K
- Pipeline: `fineprint/agents/nugget-miner.md`, `fineprint/pages.py`, `fineprint/schema.py`, `fineprint/agents/red-team.md`
- Outputs: `fineprint/out/red_team_v3_final.md`, `fineprint/out/MRK/MRK.md`, `fineprint/out/MRK/MRK.jsonl`, `fineprint/out/MRK/MRK_ai_caught.jsonl`

Note: the v3 audit builds on `docs/red_team_v2_company_pick.md`, which is on the `needle` branch, not in this folder.
