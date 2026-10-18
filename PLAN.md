# Plan

Track: **Advanced**. Case: **Pharmaceutical**. Full strategy: docs/game_plan.md. Kickoff call notes: docs/kickoff_summary.md.

## Fill in Saturday by 10:45 am (Parker)

Drafted Sat about 5 pm by Parker's agent. Parker: confirm or edit. Brackets are numbers we still have to measure.

- **One-liner:** A buy-side pharma analyst uses NEEDLE to turn a drugmaker's filings, calls and labels into
  page-verified, scored findings, cutting a first-pass forensic read of one company from [X hours, measured by hand
  on one 10-K] to [Y minutes, timed NEEDLE run], with every quote checked against its page.
- **Persona:** Pharma equity analyst at a buy-side fund (primary). Secondary: corporate strategy and investor
  relations at the drugmaker itself (the CEO-seat view in Part 2), and a distributor planning team (McKesson judges).
- **The one metric:** analyst hours to a defensible, cited findings table for one company. Supporting: share of AI
  claims that fail the page check and get blocked before a human sees them.
- **Golden path (exact screens the demo shows):** see demo_script.md
    1. Briefing: the chosen company's Sharpest Needle with its dollar math
    2. Click the citation: the exact filing page, quote highlighted
    3. AI caught: claims the verifier rejected, with the reason
    4. Proof: sealed forecast hash verified in the browser, honest backtest
    5. Live: a judge names a ticker, onboard runs
- **Cut list (things we will NOT build):**
- Live web search at demo time (everything runs offline from the corpus)
- Any trading signal or buy/sell call (findings are flags for human review; gate 2 showed ratios do not predict)
- More detectors. New nuggets come from the nugget-miner agent plus human review, not new code
- Any campaign material beyond one labelled, claims-mapped concept, if Part 2 needs it

## Devpost submission form (fill in tonight)

- Required fields:
- Video length limit:
- Other requirements:

## Key times

| When | What |
|---|---|
| Sat 9:00 am | Cases go live, Neeley 2303AB |
| Sat ~1:00 pm | Aidan arrives, 15-minute sync |
| Sat 5:30 pm | Progress check; golden path must run end to end |
| Sun 10:30 am | Feature freeze, tag demo-ready |
| Sun 1:00 pm | Submit on Devpost (deadline 2:00 pm) |
| Sun 2:00 to 4:00 pm | Live showcase judging at our table |
