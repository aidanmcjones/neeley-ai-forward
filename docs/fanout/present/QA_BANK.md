# Judge Q&A bank (company-neutral)

**No company has been picked.** The main bank covers the method, the page checker, AI caught and Responsible AI, so
it works for any pick. Company-specific questions are in short appendices, one per candidate, in alphabetical order.
Same style as qa.md. Rehearse the top 5 twice.

Sources: docs/red_team_v2_company_pick.md ("RT2"), docs/how_we_did_it.md ("HWDI"), docs/needle_gate2.md ("Gate 2"),
docs/needle_sealed.md, DISCLOSURE.md, PLAN.md, agent/needle/onboard.py, the four docs/nuggets/*_ai_caught.jsonl
files. Rubric category names are from AI_Innovation_Competition_Judging_Rubric.pdf.

## Top 5 most likely

1. Q3: How do you stop the AI from making things up?
2. Q1: Why does this need AI?
3. Q4: What happens when the checker cannot confirm a quote?
4. Q14: What did you build this weekend versus before?
5. C1: Isn't your Sharpest Needle already priced in?

## Main bank

| # | Question | Owner | Answer (1 to 2 sentences) | Backup fact | Rubric |
|---|---|---|---|---|---|
| 1 | Why does this need AI? | Aidan | The useful signals are in sentences: a footnote that changed, an answer an executive dodged. Code can find numeric anomalies but cannot read those. | Our code flagged AZN receivables as a red flag; only a reading of the footnote showed it was factoring (HWDI row 9) | Use of AI |
| 2 | Why not just use ChatGPT or Copilot? | Aidan | A chat window answers from memory and cannot prove its page numbers. NEEDLE loads the real filings, checks every quote against its page and keeps an audit log; the model can be swapped. | Case PDF: "A model working from memory will get numbers and quotes wrong" | Use of AI, Innovation |
| 3 | How do you stop the AI from making things up? | Aidan | The AI only proposes; code then checks every quote against the page it cites, exact or close match, and every number against the filing data. | 238 of 238 evidence quotes across four companies pass the re-run (RT2, "How I tested") | Use of AI and Responsible Design |
| 4 | What happens when the checker cannot confirm a quote? | Aidan | It is marked "needs_human" and goes to a person. It never reaches a slide on its own. | MRK: 4 quotes where the speaker's name was too far above the quote were dropped or replaced (MRK_ai_caught.jsonl) | Use of AI and Responsible Design |
| 5 | Give me one time the AI was confidently wrong. | Aidan | Our own first backtest said a margin drop came before trouble 59% of the time vs 43%. Two AI skeptics showed the data overlapped what was already known; the honest result is no signal predicts hard events. | Gate 2; HWDI row 1 | Use of AI and Responsible Design, Completeness |
| 6 | How many errors did it catch? | Aidan | 43 logged catches across the four companies we deep-read, plus 9 errors in our own tool, each now covered by a test. | AMGN 15, JNJ 11, MRK 10, AZN 7 (row counts of *_ai_caught.jsonl); HWDI section 4 | Use of AI |
| 7 | Is this a trading signal? | Parker | No. Findings are flags for a person to review. Our backtest showed the ratios alone do not predict stock-relevant events. | 1,410 firm-quarters, 43 companies, 2012 to 2024, no signal significant (Gate 2) | Completeness, Responsible Design |
| 8 | So what does predict anything? | Aidan | The revenue forecaster is calibrated: its 80% range covered 79.4% of 1,793 past firm-quarters, and it called J&J Q3 2026 growth blind. | Forecast +7.3%, range +4.3% to +10.4%, actual +5.9% (Gate 2) | Technical Execution |
| 9 | How do we know you did not change the predictions after the fact? | Aidan | We sealed seven Q3 2026 predictions with a hash before results, and the app recomputes it live. | sha256 c29a6793...e67e65, sealed 2026-10-17 (docs/needle_sealed.md) | Technical Execution, Responsible Design |
| 10 | Can you point it at a different company? | Aidan | Yes: one command takes a ticker and builds the cited dataset with no hand edits. Name one. | `python -m agent.needle.onboard VRTX`; proven on VRTX (docs/red_team_v1.md) | Technical Execution, Impact |
| 11 | What breaks first? | Aidan | Earnings-call transcripts: company sites block scripts, so they are added by hand. Also third-party transcripts can hold AI-written summaries, which we reject. | agent/needle/onboard.py docstring; AMGN_ai_caught.jsonl (fool.com "takeaway" rows) | Completeness |
| 12 | Who is this for? | Parker | A buy-side pharma analyst who must turn filings, calls and labels into a defensible, cited findings table. Also corporate strategy at the drugmaker. | PLAN.md persona | Impact |
| 13 | How much time does it save? | Parker | [TBD: measure one manual 10-K read and one timed NEEDLE run before Sunday 10:30 am]. Until then: we have not timed it, so we will not quote a number. | PLAN.md one-liner has both numbers in brackets | Impact |
| 14 | What did you build this weekend versus before? | Aidan | Before: a repo scaffold, a generic Claude wrapper with caching, a placeholder page and an empty test harness. Everything case-specific was built during the event; the commit history shows it. | DISCLOSURE.md | Completeness, Presentation |
| 15 | Where does the data go? Any privacy risk? | Aidan | Inputs are public SEC filings, FDA labels and CMS data; no patient or personal data. Claude calls go through one wrapper and are cached; keys are never in code. | CLAUDE.md rules; DISCLOSURE.md | Use of AI and Responsible Design |
| 16 | What about bias in the AI's picks? | Parker | The AI's ranking is not trusted: we chose the company on human-read findings and a red-team score, and the code's league rank is not a selector. | RT2 section 10; HWDI section 5 | Responsible Design |
| 17 | What does a run cost? | Aidan | [TBD: no cost figure in the repo yet]. We would measure tokens per company from the cache logs. Most of the pipeline is code, not model calls. | agent/llm.py caches every call | Impact |
| 18 | How do you handle assumptions in your dollar math? | Parker | Every assumed input is labelled "(assumption)" and each finding shows a bear and bull case. Low-confidence findings stay off the main slides. | docs/nuggets/<TICKER>.md impact.formula fields | Completeness |
| 19 | How did you avoid counting the same dollars twice? | Parker | The red team checks for overlap, and overlapping findings are merged into one line in the bridge. | RT2 section 9, item 6 | Technical Execution |
| 20 | How do you check the AI's product facts? | Aidan | Labels come from FDA data; patent dates come from the 10-K patent table and the Orange or Purple Book. We caught our own code giving wrong exclusivity dates and overrode them. | RT2 section 10: Keytruda, Enbrel and Darzalex dates were wrong in the code's table | Completeness |
| 21 | Does Part 2 follow drug promotion rules? | Parker | Anything a doctor or patient would see uses approved uses only, shows risks as clearly as benefits, and is labelled "Student concept, not actual promotional material," with a claims map. [PLACEHOLDER: docs/fanout/part2/] | Case PDF rules | Use of AI and Responsible Design |
| 22 | The case says AI argues for any strategy. How did you stop that? | Parker | We picked the move ourselves; the model only stress-tested it, and we set dated kill signals that would prove us wrong. | docs/part2.md rule line | Responsible Design, Impact |
| 23 | Is it accessible and easy to use? | Aidan | Five tabs follow the analyst's day: league, findings, product fine print, AI caught, proof. Charts use text labels and a color-blind-safe palette. | app/needle_app.py tabs; deck/outline.md accessibility line | Design and Usability |
| 24 | Will analysts actually adopt it? | Parker | It fits how they already work: the output is a findings table with page citations they can paste into a note. Next step is a one-team pilot measuring hours per company. | PLAN.md metric | Impact |
| 25 | What would you do with another week? | Parker | Time the manual read, fetch transcripts automatically, fill every peer column, and run it on all ten companies with human review. | HWDI section 5 | Impact, Completeness |

## If you do not know

1. "I do not want to guess. Here is the page we would check." (Open the source.)
2. "That is outside what the documents say, so we did not claim it."
3. "Good question; that is on our limits slide." (Go to slide 15.)

## Appendix: company-specific questions (one per candidate, reference only)

From RT2 sections 1, 4, 7 and 8. Use only the appendix for the company the team picks.

### C-AMGN (Amgen)

| # | Question | Answer pattern | Backup |
|---|---|---|---|
| C1 | Your needle is $97M. Is that material? | It is about 1% of quarterly product sales; we would argue it as a signal of hidden price erosion, not size. | RT2 section 2 |
| C2 | Your transcripts are third-party. Can we trust them? | We rejected every line from the site's AI-written summary; only call-body quotes with a confirmed speaker are used. | AMGN_ai_caught.jsonl; RT2 section 7 |

### C-AZN (AstraZeneca)

| # | Question | Answer pattern | Backup |
|---|---|---|---|
| C1 | Isn't 2024 just an unusual year for gross-to-net? | Yes: the 2023 ratio (49.1%) almost equals 2025 (49.5%), so we frame it as "the 2024 improvement fully reversed." | RT2 section 2 |
| C2 | Your Q1 transcript looks like Q2. | It is a duplicate, so we do not cite it. | RT2 section 7 |

### C-JNJ (Johnson & Johnson)

| # | Question | Answer pattern | Backup |
|---|---|---|---|
| C1 | The CEO already talks about the Genmab royalty. | Agreed, so it is not our needle; ours is the $390M a quarter of US erosion beyond STELARA. | RT2 section 4 |
| C2 | Why rely on true-ups rising? | We do not: Q1 is seasonally high, so quarterly vs annual is not like for like. | RT2 section 2 |

### C-MRK (Merck)

| # | Question | Answer pattern | Backup |
|---|---|---|---|
| C1 | The royalty end has been public since 2017. Isn't it priced in? | The schedule is public. Our claim is that 2027 gets a one-time lift of about $0.8B, partly refilled by Winrevair's 22% royalty, the year before the 2028 cliff, so 2027 margin is not a run rate. "Royalt" appears 0 times on 4 calls. | RT2 section 8; MRK.md |
| C2 | Gardasil impact depends on a 40% guess. | Yes, it is labelled an assumption; we show it as a range ($330M to $660M) at Medium confidence. | MRK.md row 002 |
