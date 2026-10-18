# Demo script v2 (company-neutral: 3 minutes, 90 seconds, 30 seconds)

**No company has been picked.** Slots: [COMPANY], [NEEDLE], [NEEDLE $], [PAGE], [SECOND SOURCE], [N CAUGHT],
[CAUGHT EXAMPLE], [MOVE]. Fill them from the needle, AI-caught and Part 2 streams once the team decides
(docs/fanout/needle/, docs/fanout/part2/). Candidate fills are in the table at the end, as reference only.

Screen names are the real tabs in app/needle_app.py: League table, Findings, Product fine print, AI caught, Proof.
Speaking pace is about 150 words a minute. Method numbers come from docs/red_team_v2_company_pick.md ("RT2"), the four
docs/nuggets/*_ai_caught.jsonl files, docs/needle_gate2.md and docs/needle_sealed.md.

## Pre-demo checklist (Sunday 1:45 pm)

- [ ] `streamlit run app/main.py` is open, with the NEEDLE page loaded and [COMPANY] selected
- [ ] Cache warm: click every tab once, so nothing waits on the API (CLAUDE.md caching rule)
- [ ] Every tab loads with Wi-Fi off (tested once)
- [ ] out/predictions/sealed_2026Q3.json is present; its hash starts c29a6793 (docs/needle_sealed.md)
- [ ] A second browser tab has the needle's source page open, in case the click-through fails
- [ ] The deck is open on the Sharpest Needle slide on the second screen
- [ ] No API key or .env visible on any screen
- [ ] A saved VRTX onboard run is ready as the fallback for live onboarding

## A. The 3-minute version (about 420 words when filled)

| Time | Speaker | Screen | Exact words | Rubric |
|---|---|---|---|---|
| 0:00 to 0:15 | Parker | League table | "Wall Street reads the headline. We read the footnote, and we prove every quote. We are Parker and Aidan, Advanced track, pharma case. We built NEEDLE for the analyst who has to read a drugmaker's filings fast and get them right." | Presentation, Impact |
| 0:15 to 0:40 | Parker | League table | "The tool screened all ten companies on the shortlist. We deep-read four and checked all 238 quotes against their pages. We picked [COMPANY] because [one reason, slide 2]." | Innovation |
| 0:40 to 1:10 | Parker | Findings, needle row | "Here is our Sharpest Needle. [NEEDLE in two plain sentences]. That is worth about [NEEDLE $]. Here is why nobody is talking about it: [one line]." | Innovation, Impact |
| 1:10 to 1:35 | Aidan | Findings: click the citation | "Every number opens to its page. This is [FILING], page [PAGE], quote highlighted. And we checked it a second way: [SECOND SOURCE]." | Technical Execution |
| 1:35 to 2:00 | Aidan | AI caught | "The AI was confidently wrong [N CAUGHT] times on [COMPANY], and 43 times across the four companies we read. Our code caught it before we did. Here is one: [CAUGHT EXAMPLE]. Anything the checker cannot confirm goes to a person." | Use of AI and Responsible Design |
| 2:00 to 2:20 | Aidan | Proof | "Our first backtest looked great. Two AI skeptics broke it. The honest version: no forensic signal predicts a revenue drop on its own, so our findings are flags for people, not trading calls. What does hold: we sealed seven Q3 forecasts before the results came out. Here is the hash, recomputed in the browser." | Completeness, Use of AI |
| 2:20 to 2:50 | Parker | Part 2 slides | "So what would we do as CEO? [MOVE]. It costs [COST] and should return [RETURN]. We will know within months if we are wrong: [KILL SIGNAL 1] and [KILL SIGNAL 2]." | Impact |
| 2:50 to 3:00 | Parker | League table | "Point it at any drugmaker and it builds the same cited table. Want to name a ticker?" | Technical Execution, Presentation |

Optional step 5, only if the judge has time: ask for a ticker and run `python -m agent.needle.onboard <TICKER>`. If it
stalls, switch to the saved VRTX run: "Here is one we ran earlier with zero hand edits." Say up front that call
transcripts are not fetched automatically (agent/needle/onboard.py).

### If a screen fails

| Step | Fallback |
|---|---|
| League table will not load | Deck slide 2 |
| Citation click fails | Second browser tab with the source page |
| AI caught tab empty | Deck slide 14, or open docs/nuggets/[TICKER]_ai_caught.jsonl |
| Proof hash will not compute | Read it from docs/needle_sealed.md: c29a6793...e67e65, 7 predictions, sealed 2026-10-17 |
| Onboard fails | Saved VRTX run |

### The "priced in?" pivot (fill per company)

"You are right that [the public fact] is known. Our claim is narrower: [what the market misses, in one sentence], and
management has not said it on [N] calls." (RT2 section 8 has the MRK version; write one for the chosen company.)

## B. The 90-second table pitch (about 220 words when filled)

| Time | Speaker | Screen | Exact words |
|---|---|---|---|
| 0:00 to 0:10 | Parker | League table | "Wall Street reads the headline. We read the footnote, and we prove every quote." |
| 0:10 to 0:35 | Parker | Findings, needle row | "We picked [COMPANY]. [NEEDLE in two plain sentences.] That is about [NEEDLE $]." |
| 0:35 to 0:55 | Aidan | Click citation | "Every number opens to its page. Here is page [PAGE]. [SECOND SOURCE in one line.]" |
| 0:55 to 1:10 | Aidan | AI caught | "The AI was confidently wrong [N CAUGHT] times on [COMPANY]. The code caught every one before it reached a slide." |
| 1:10 to 1:30 | Parker | Part 2 slide | "As CEO, [MOVE]. If [KILL SIGNAL] happens, we change course." |

Plain words for terms a judge may not know (say once, only if needed):
- Royalty: a cut of sales paid to whoever owns a patent.
- EPS (earnings per share): profit divided by the number of shares.
- Gross-to-net: the gap between list price and what the company actually collects.

## C. The 30-second version (for a judge who is leaving)

Parker: "We built NEEDLE. AI reads a drugmaker's filings, and code checks every quote against its page. For
[COMPANY], it found [NEEDLE in one line], worth about [NEEDLE $]. And it caught the AI being wrong [N CAUGHT] times
before any of that reached a slide."

## D. Alternate opening hooks (company-neutral)

1. "Our AI was wrong 43 times this weekend. That is why you can trust the rest of what we show you."
2. "Every number on our slides opens to its page. Pick one."
3. "Wall Street reads the headline. We read the footnote, and we prove every quote."

## E. If everything else fails, land one sentence

- Parker: "[NEEDLE in one sentence with its dollar figure], and the source page is one click away."
- Aidan: "The AI reads, the code checks every quote against its page, and anything it cannot confirm goes to a person."

## Who says what

Parker opens, gives the needle and closes with Part 2. Aidan drives the mouse and speaks for the click-through, AI
caught and Proof (demo_script.md "Table pitch"). If one of us is with another judge, the other runs version B alone.

## Candidate fills (reference only, not a pick)

From RT2 sections 4 and 8 and the *_ai_caught.jsonl row counts.

| Slot | AMGN | AZN | JNJ | MRK |
|---|---|---|---|---|
| [NEEDLE] | Enbrel Q2 2026 decline flattered by a 16-point favorable true-up | US gross-to-net give-back | Second-wave US erosion beyond STELARA | 2.5% Keytruda royalty to BMS and Ono ends after Dec 31, 2026 |
| [NEEDLE $] | $97M in one quarter | $1,804m | $390M a quarter | About $821M pretax, +$0.28 EPS in 2027 |
| [PAGE] | 10-Q Q2 2026 p.35 | 20-F FY2025 p.34 | Q3 2026 8-K schedule | 10-K FY2025 p.54 |
| [SECOND SOURCE] | None; bridges do not reconcile | None; 2023 ratio about equals 2025 | Product rows add up: OPSUMIT, REMICADE, SIMPONI, IMBRUVICA = -$390M vs STELARA -$654M (RT2) | BMS 10-K FY2025 p.89, within 1% |
| [N CAUGHT] | 15 | 7 | 11 | 10 |
| [CAUGHT EXAMPLE] | A "CFO quote" was an AI-written summary on a transcript site | Receivables "red flag" was factoring | Teammate lead about an SEC comment letter was not in any document | Court date moved from Q2 2026 to Nov 19, 2026 in the newer 10-Q |
