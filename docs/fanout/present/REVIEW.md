# Review of the five presentation drafts

Reviewed Sat Oct 17 2026 against AI_Innovation_Competition_Judging_Rubric.pdf, "04 Advanced_Pharma_Fine_Print_Case.pdf",
the live app (app/needle_app.py and the files it reads in out/), and the repo docs the drafts cite. Nothing else was
edited. No company is picked; every fix below keeps the [COMPANY]-style slots.

Every "old" string below is copied exactly from the draft so it can be pasted into a find-and-replace.

## What the live app can and cannot show today

The rubric says "do not give credit for features that were only described or planned." These are the gaps between
what the deck and demo claim and what app/needle_app.py shows. docs/fanout/demo/GOLDEN_PATH_REPORT.md found the same
gaps independently.

| Claim in the drafts | What the app shows | Evidence |
|---|---|---|
| Demo launches with `streamlit run app/main.py` (DEMO line 13, DEVPOST line 112) | app/main.py is the old "Pharma decision copilot" placeholder. The NEEDLE app is app/needle_app.py | app/main.py lines 17 to 18; app/needle_app.py line 3 |
| "Findings, needle row": the Sharpest Needle with its dollar figure (DEMO 0:40, 1:10; VIDEO 0:55) | The app never reads docs/nuggets/. None of the four candidate needles (royalty, true-up, $1,804m GTN, $390M erosion) is in out/<T>/findings.jsonl (grep: 0 hits for each). The League tab shows no dollar figure | app/needle_app.py tab 1 and tab 2; GOLDEN_PATH_REPORT.md screen 1 |
| "AI caught" tab shows [N CAUGHT] / 43 errors (DEMO 1:35; VIDEO 1:40, 0:40) | Tab reads out/<T>/rejected.jsonl, which has 0 rows for AMGN, AZN, JNJ and MRK. It prints "No rejected claims recorded". The 43 live only in docs/nuggets/*_ai_caught.jsonl, which the app does not read | `wc -l out/{AMGN,AZN,JNJ,MRK}/rejected.jsonl` = 0 each |
| "AI: Claude through agent/llm.py" reads and proposes (DECK slide 13; DEVPOST "How we built it") | The demo app makes no model call. The only product LLM caller, agent/needle/trial.py, has never run (no ai_caught.jsonl or trials.jsonl in out/). The AI reading was done by Claude Code nugget-miner agents, offline | app/needle_app.py docstring "no LLM calls"; GOLDEN_PATH_REPORT.md screen 3 |
| "Click the citation, the page opens" | It is an expander that shows the page text with the quote highlighted. Works for 100% of quotes, but it is not a click-through | app/needle_app.py lines 256 to 274 |
| "Here is the hash, recomputed in the browser" (DEMO 2:00) | The "Verify seal" button recomputes it in Python on the server. It does match | app/needle_app.py lines 450 to 463 |
| Live onboarding "builds the same cited table" (DEMO 2:50, VIDEO 2:30) | Command line only. An onboarded ticker (including VRTX) never appears in the app's company list, because the list comes from out/league.json | app/needle_app.py lines 152 and 180 |
| Product fine print tab supports the product slide | Tab shows "Protection ends (latest)", which RT2 section 10 says is wrong for Keytruda, Enbrel and Darzalex. No gross-to-net per product; Medicare spend is the only pricing row | out/MRK/labels_table.json fields |
| "Two AI skeptics broke it" shown on the Proof tab | The refuted v1 story sits in an expander on the AI caught tab. Proof shows the v2 backtest | app/needle_app.py lines 333 to 337 |

What does work live: all five tabs render for all ten companies; every quote resolves to its page and highlights;
the seal verifies; the ledger is intact; v2 backtest, calibration and the J&J blind test show on Proof; color-blind
palette and inline sources (GOLDEN_PATH_REPORT.md: AppTest 0 exceptions, pytest 49 passed).

---

## Pass 1: rubric judge

Scored as a strict judge watching the deck and the demo as drafted today, with the app as it stands. "Ceiling" is the
likely score after the ten edits below plus the pending streams (needle, product table, Part 2) being filled.

| Category | Score now | Ceiling | Weakest slide or line | Why |
|---|---|---|---|---|
| Innovation and Creativity | 3 | 4 | DECK slide 3: every line is a slot ("[STARTER THREAD]", "[NEEDLE in plain words]") | The method is fresh: AI reads, code checks every quote on its page, sealed forecasts, skeptics attack your own result. But the one slide that proves you beat the starter thread is empty, and the case says restating it "will not score well." |
| Technical Execution | 2 | 3 | DEMO 1:10 "Findings: click the citation" on the needle | The verifier, ledger and seal are sound. But the demo's centrepiece (needle row, its page, its dollars) is not in the app, so the judge sees a slide where the build should be. "Components work together but with notable gaps." |
| Use of AI and Responsible Design | 3 | 4 | DEMO 1:35 "The AI was confidently wrong [N CAUGHT] times..." over an AI caught tab that says "No rejected claims recorded" | Risk handling is the team's strength (needs_human, page checks, refuted backtest shown honestly). Two problems: the tab contradicts the line, and the live product has no visible AI step, so "AI is essential" is asserted, not shown. If a judge asks "where is the AI on this screen?" this drops to 2. |
| Completeness | 2 | 3 | DECK slide 4 findings table row "1 to 5+ \| [from docs/nuggets/[TICKER].md ...]" | Findings table, product table and Part 2 are all slots today. Slide 15 is honest, but it omits the live app's own gaps (wrong exclusivity row, onboard not in the app, AI caught tab empty). |
| Design and Usability | 3 | 3 | DECK slide 13: no slide walks the analyst's day through the five tabs | The app is clean: Okabe-Ito palette, text on every color, sources inline, 17px base font. The deck never shows it as a workflow, and the app opens on AZN, not [COMPANY] (GOLDEN_PATH_REPORT.md 1A). |
| Impact | 2 | 3 | DECK slide 1 one-liner "[TBD: timed NEEDLE run] instead of [TBD: timed manual read]" | Users are specific (buy-side pharma analyst), but the only value metric is unmeasured, slides 8 to 12 are empty, and there is no evidence of need. |
| Presentation | 2 | 4 | DEMO 2:00 "Here is the hash, recomputed in the browser." and the 2:50 ticker offer | Scripts are tight and the Q&A bank is strong. But four lines would fail on screen (wrong launch command, missing needle row, empty AI caught tab, onboarded ticker not in the app). One visible false line costs more than the line earns. |
| **Total** | **17 / 28** | **24 / 28** | | |

### Top 10 edits, ranked by points gained

Points are rubric points protected or gained, across categories, if the edit lands.

**1. Fix the launch command (protects about 2: Completeness, Presentation).** Launching main.py on stage shows the
placeholder page and its Run button crashes with no API key.

DEMO_SCRIPT_v2.md line 13. Old:
```
- [ ] `streamlit run app/main.py` is open, with the NEEDLE page loaded and [COMPANY] selected
```
New:
```
- [ ] `streamlit run app/needle_app.py` is open, [COMPANY] is selected in the company box (the app opens on AZN by default)
```
DEVPOST.md line 112, same fix. Old:
```
- Run locally: `pip install -r requirements.txt`, then `streamlit run app/main.py`
```
New:
```
- Run locally: `pip install -r requirements.txt`, then `streamlit run app/needle_app.py`
```

**2. Make the AI caught line match the screen (+1 Use of AI, +1 Presentation).** The tab is empty for every candidate.
The 43 also include three teammate leads (JNJ two, MRK one) and some tool issues, so "the AI was confidently wrong 43
times" is not what the files say. Source: kind fields in docs/nuggets/JNJ_ai_caught.jsonl and MRK_ai_caught.jsonl.

DEMO_SCRIPT_v2.md line 30. Old:
```
| 1:35 to 2:00 | Aidan | AI caught | "The AI was confidently wrong [N CAUGHT] times on [COMPANY], and 43 times across the four companies we read. Our code caught it before we did. Here is one: [CAUGHT EXAMPLE]. Anything the checker cannot confirm goes to a person." | Use of AI and Responsible Design |
```
New:
```
| 1:35 to 2:00 | Aidan | Deck slide 14 (the app's AI caught tab is empty until trial.py runs; see GOLDEN_PATH_REPORT.md fix 3) | "Across the four companies we read, 43 claims failed a check and were fixed or dropped, [N CAUGHT] of them on [COMPANY]. Here is one: [CAUGHT EXAMPLE]. Anything the checker cannot confirm goes to a person." | Use of AI and Responsible Design |
```

**3. Stop sending the demo to a needle row that does not exist (+1 Technical Execution).** Until the app shows the
team's needle (GOLDEN_PATH_REPORT.md fix 1B), show it on the slide and open its page in the backup browser tab.

DEMO_SCRIPT_v2.md line 28. Old:
```
| 0:40 to 1:10 | Parker | Findings, needle row |
```
New:
```
| 0:40 to 1:10 | Parker | Findings, needle row (only if fix 1B has landed; otherwise deck slide 5) |
```
DEMO_SCRIPT_v2.md line 29. Old:
```
| 1:10 to 1:35 | Aidan | Findings: click the citation | "Every number opens to its page. This is [FILING], page [PAGE], quote highlighted.
```
New:
```
| 1:10 to 1:35 | Aidan | Findings: open "Evidence and source pages" on the needle (or the backup browser tab on [PAGE]) | "Every quote opens to its page. This is [FILING], page [PAGE], quote highlighted.
```

**4. Make the slide 14 headline true (+1 Use of AI, protects Presentation).** Same reason as edit 2.

DECK_CONTENT.md line 162. Old:
```
**Headline:** The AI was confidently wrong 43 times. The checks caught every one before a slide did.
```
New:
```
**Headline:** 43 claims failed our checks and were fixed or dropped. None reached a slide.
```

**5. Describe the AI step as it really ran (protects 1 Use of AI, 1 Technical Execution).** A judge who asks to see
the Claude call will find none in the app. Saying where the AI ran is honest and still scores.

DECK_CONTENT.md line 148. Old:
```
| Read and propose | AI: Claude through agent/llm.py, cached | nugget-miner agent |
```
New:
```
| Read and propose | AI: Claude Code nugget-miner agents read the filings offline and wrote each finding with its quote | docs/nuggets/[TICKER].jsonl; the app shows these results and makes no live model call |
```

**6. Add the live app's own limits to slide 15 (+1 Completeness).** Level 4 needs "limitations are stated clearly
and honestly." Naming the gaps before a judge finds them turns a weakness into evidence.

DECK_CONTENT.md line 213. Old:
```
- Call transcripts are not fetched automatically; they are added by hand (agent/needle/onboard.py).
```
New:
```
- Call transcripts are not fetched automatically; they are added by hand (agent/needle/onboard.py).
- A new company is added from the command line; it does not yet appear in the app's company list.
- The app's "Protection ends" row is wrong for some drugs, so patent dates on our slides come from the 10-K
  patent tables (RT2 section 10).
```

**7. Give slide 1 a value claim you can show today (+1 Impact).** The time saving is unmeasured. Lead with the
measured result and keep the timing as a stated next step, so the judge is not handed two blanks.

DECK_CONTENT.md lines 31 to 32. Old:
```
- One-liner: a buy-side pharma analyst gets a cited, page-checked findings table for one drugmaker in [TBD: timed
  NEEDLE run] instead of [TBD: timed manual read] (PLAN.md; both still to be measured)
```
New:
```
- One-liner: an investment analyst who covers drug companies gets a findings table where every quote is checked on
  its page. All 238 of 238 quotes passed across four companies (RT2, "How I tested").
- Time saved: [fill only if both timings are measured before Sunday 10:30 am; otherwise say "not yet measured"]
```

**8. Make the closing offer something the app can do (protects 1 Technical Execution, 1 Presentation).** An onboarded
ticker does not appear in the app, and transcripts are manual, so "the same cited table" overclaims.

DEMO_SCRIPT_v2.md line 33. Old:
```
"Point it at any drugmaker and it builds the same cited table. Want to name a ticker?"
```
New:
```
"One command points it at another drugmaker and builds the same page-checked dataset. We ran it on Vertex, which is not on the shortlist. Want to name a ticker?"
```

**9. Show the analyst's workflow and accessibility on slide 13 (+0.5 to 1 Design and Usability).** Nothing in the deck
earns this category today; the app already has the features.

DECK_CONTENT.md line 158. Old:
```
Rubric: Technical Execution, Use of AI and Responsible Design. Case: reusable build.
```
New:
```
- The analyst's day in five tabs: rank the companies (League table), read the findings with their pages (Findings),
  compare the drug with its rivals (Product fine print), see what was thrown out (AI caught), check the track record
  (Proof).
- Built for every viewer: color-blind-safe colors, a text label on every color, sources shown on screen, not on hover.

Rubric: Technical Execution, Use of AI and Responsible Design, Design and Usability. Case: reusable build.
```

**10. Remove the one false technical line (protects 0.5 Presentation).** The hash is computed in Python on the server.

DEMO_SCRIPT_v2.md line 31. Old:
```
Here is the hash, recomputed in the browser."
```
New:
```
Press Verify seal: it recomputes the fingerprint and it matches the one we saved before the results came out."
```

---

## Pass 2: plain language

No em or en dashes were found in any of the five drafts (searched for U+2013 and U+2014). Items are grouped by issue;
each gives old and new text. Internal planning notes (file headers, checklists) are skipped unless a judge will see
them.

### Jargon a non-finance judge would not follow

DECK_CONTENT.md line 85. Old:
```
- How much: [pretax $, EPS, year]
```
New:
```
- How much: [dollars before tax, earnings per share, year]
```

DECK_CONTENT.md lines 153 to 154. Old:
```
- Every signal, verdict and prediction is written to a hash-chained audit log, so tampering shows
  (agent/needle/audit.py; docs/how_we_did_it.md).
```
New:
```
- Every result is written to a log where each entry is locked to the one before it, so any later edit shows
  (agent/needle/audit.py; docs/how_we_did_it.md).
```

DECK_CONTENT.md line 149. Old:
```
| Check the page | Code: `agent.needle.pages.check`, exact or fuzzy match on the cited page |
```
New:
```
| Check the page | Code: `agent.needle.pages.check`, exact or near-exact match on the cited page |
```

DECK_CONTENT.md lines 184 to 186. Old:
```
Best example, any company: our code flagged AstraZeneca's receivables rising 23.3% vs revenue 8.6% as a collections
red flag. The footnote showed it was factoring; without it receivables fell 0.8% (AZN 20-F FY2025 p.F-29;
docs/how_we_did_it.md row 9).
```
New:
```
Best example: our code saw AstraZeneca's unpaid customer bills rise 23.3% while revenue rose 8.6%, which can mean
customers are slow to pay. The footnote showed the company had sold some bills to banks (factoring). Without those,
unpaid bills fell 0.8% (AZN 20-F FY2025 p.F-29; docs/how_we_did_it.md row 9).
```

DECK_CONTENT.md lines 188 to 189. Old:
```
Our own biggest error: the first backtest claimed a 59% vs 43% hit rate. Two AI skeptics found the data overlapped
what was already known. The honest version shows no signal predicts hard events (docs/needle_gate2.md).
```
New:
```
Our own biggest error: our first test on past data said a falling profit margin came before trouble 59% of the time,
against 43% normally. Two AI reviewers found the test used data that was not public yet at the time. Fixed, no
warning sign predicted a revenue drop or a write-down (docs/needle_gate2.md).
```

DECK_CONTENT.md line 181. Old:
```
- An older filing was superseded by a newer one (e.g. a court date that moved)
```
New:
```
- A newer filing replaced an older fact (e.g. a court date that moved)
```

DECK_CONTENT.md lines 206 to 207. Old:
```
- It does not predict stock moves. After the skeptics' fixes, no forensic signal significantly predicts a revenue
  drop or impairment (1,410 firm-quarters, 43 companies, 2012 to 2024; docs/needle_gate2.md).
```
New:
```
- It does not predict stock moves. After the fixes, no accounting warning sign reliably predicted a revenue drop or
  a write-down (tested on 1,410 company-quarters, 43 companies, 2012 to 2024; docs/needle_gate2.md).
```

DECK_CONTENT.md line 210. Old:
```
- Seven Q3 2026 predictions were sealed with a hash before results came out (docs/needle_sealed.md).
```
New:
```
- We locked seven Q3 2026 predictions with a digital fingerprint (a hash) before results came out, so we cannot
  change them later (docs/needle_sealed.md).
```

DEMO_SCRIPT_v2.md line 31. Old:
```
The honest version: no forensic signal predicts a revenue drop on its own, so our findings are flags for people, not trading calls.
```
New:
```
The honest version: no accounting warning sign predicts a revenue drop on its own. So our findings are flags for a person to check, not trading calls.
```

QA_BANK.md line 30. Old:
```
The revenue forecaster is calibrated: its 80% range covered 79.4% of 1,793 past firm-quarters, and it called J&J Q3 2026 growth blind.
```
New:
```
The revenue forecaster gives a range it expects to be right 80% of the time, and on 1,793 past company-quarters it was right 79.4% of the time. It also called J&J's Q3 2026 growth before the results.
```

QA_BANK.md line 41. Old:
```
The red team checks for overlap, and overlapping findings are merged into one line in the bridge.
```
New:
```
The red team checks for overlap, and overlapping findings are merged into one line when we add up the total.
```

DEVPOST.md line 22. Old:
```
get material, cited findings, plus a log of every time the AI was wrong.
```
New:
```
get important findings, each tied to its page, plus a log of every error caught.
```
(New pitch is 195 characters, under the 200 limit.)

DEVPOST.md lines 61 to 62. Old:
```
- Our code once flagged a company's receivables as a red flag. The footnote showed it was factoring, and without it
  receivables fell 0.8%. Code ratios are now flags for a reader, never findings on their own.
```
New:
```
- Our code once flagged a company's unpaid customer bills as a warning sign. The footnote showed it had sold some
  bills to banks; without those, unpaid bills fell 0.8%. Code ratios are now flags for a reader, never findings on
  their own.
```

DEVPOST.md lines 59 to 60. Old:
```
data that was already known. After the fixes, no forensic signal significantly predicts a revenue drop or
  impairment (1,410 firm-quarters, 43 companies). We show the honest version.
```
New:
```
data that was already known. After the fixes, no accounting warning sign reliably predicts a revenue drop or a
  write-down (1,410 company-quarters, 43 companies). We show the honest version.
```

DEVPOST.md line 72. Old:
```
- A revenue forecaster whose 80% range covered 79.4% of 1,793 past firm-quarters.
```
New:
```
- A revenue forecaster that aims to be right 80% of the time and was right 79.4% of the time on 1,793 past
  company-quarters.
```

### Sentences over 30 words (audience-facing only)

DECK_CONTENT.md lines 70 to 71 (42 words). Old:
```
- A row survives only if every quote verifies, it is not a one-off, it is outside the starter thread, it has a dollar
  effect, it is at least Medium confidence, and it is not waiting on a person (RT2 section 3).
```
New:
```
- A row stays only if it passes six tests (RT2 section 3). Every quote checks out. It is not a one-off. It is not the
  starter thread. It has a dollar effect. It is at least Medium confidence. No person still has to confirm it.
```

DECK_CONTENT.md lines 208 to 209 (32 words). Old:
```
- What does hold: the revenue forecaster's 80% range covered 79.4% of 1,793 past firm-quarters, and it called J&J's
  Q3 2026 growth blind (+7.3% forecast, range +4.3% to +10.4%, actual +5.9%) (docs/needle_gate2.md).
```
New:
```
- What does hold: our revenue forecaster aims to be right 80% of the time and was right 79.4% of the time on 1,793
  past company-quarters. Before results, it forecast J&J's Q3 2026 growth at +7.3% (range +4.3% to +10.4%); the
  actual was +5.9% (docs/needle_gate2.md).
```

QA_BANK.md line 84 (32 words). Old:
```
Our claim is that 2027 gets a one-time lift of about $0.8B, partly refilled by Winrevair's 22% royalty, the year before the 2028 cliff, so 2027 margin is not a run rate.
```
New:
```
Our claim is that 2027 gets a one-time lift of about $0.8B, partly offset by Winrevair's 22% royalty. It lands the year before the 2028 patent cliff, so 2027 profit is not a level Merck can repeat.
```

DEVPOST.md lines 91 to 93 (36 words). Old:
```
- Built before the competition (before Fri Oct 16, 2026): the repository scaffold, meaning the folder layout,
  agent/llm.py (a generic Claude API wrapper with caching), a placeholder Streamlit page, an empty eval harness and
  planning documents.
```
New:
```
- Built before the competition (before Fri Oct 16, 2026): the repository scaffold. That means the folder layout,
  agent/llm.py (a generic Claude API wrapper with caching), a placeholder Streamlit page, an empty eval harness and
  planning documents.
```

### Unsupported or overstated numbers

Each figure was traced. Most trace cleanly; these do not.

| Draft and line | Figure | Problem | Fix (old to new) |
|---|---|---|---|
| DECK line 174; DEVPOST line 69; QA line 28 (#6) | "9 errors in our own tool, each now guarded by a test" | docs/how_we_did_it.md section 4 has 9 rows, but its column is "Guard now" (a rule change), not a test. No test-per-row is in the repo. Row 1 and row 9 are also the two examples shown elsewhere, so they are not extra | DECK old: `Plus 9 errors in our own tool, each now guarded by a test (docs/how_we_did_it.md section 4).` new: `Plus 9 errors in our own tool, each now guarded by a rule in the code (docs/how_we_did_it.md section 4).` DEVPOST old: `plus 9 errors in our own tool, each now` / `covered by a test.` new: `plus 9 errors in our own tool, each now` / `guarded by a rule in the code.` QA old: `plus 9 errors in our own tool, each now covered by a test.` new: `plus 9 errors in our own tool, each now guarded by a rule in the code.` |
| VIDEO line 20; VIDEO line 36; DEVPOST line 69; DEMO line 77 | "confidently wrong 43 times", "43 confident AI errors" | The 43 is the row count of the four docs/nuggets/*_ai_caught.jsonl files (AMGN 15, AZN 7, JNJ 11, MRK 10). But 3 rows are teammate leads, not AI claims, and several are tool or format issues (JNJ `code_vs_filing`, `unstable_ids`; AZN zero-width spaces). "The code caught every one" is also wrong: MRK `memory_check` and `lead_correction` rows were caught by reading | VIDEO 1:40 old: `"The AI was confidently wrong [N CAUGHT] times on [COMPANY], and 43 times across the four companies. The code caught each one. Anything it cannot confirm goes to a person, never straight to a slide."` new: `"Across four companies, 43 claims failed a check and were fixed or dropped, [N CAUGHT] of them on [COMPANY]. Anything we cannot confirm goes to a person, never straight to a slide."` VIDEO 60s old: `"The AI was confidently wrong 43 times. The code caught every one."` new: `"43 claims failed our checks. None reached a slide."` DEVPOST old: `- 43 confident AI errors caught and logged across those four companies,` new: `- 43 claims that failed a check, logged across those four companies,` DEMO hook old: `"Our AI was wrong 43 times this weekend. That is why you can trust the rest of what we show you."` new: `"43 claims failed our checks this weekend. That is why you can trust the rest of what we show you."` |
| DEMO line 61 (version B) | "The code caught every one before it reached a slide." | Same as above | old: `"The AI was confidently wrong [N CAUGHT] times on [COMPANY]. The code caught every one before it reached a slide."` new: `"On [COMPANY], [N CAUGHT] claims failed our checks. None reached a slide."` |
| DEMO line 72 (version C) | "caught the AI being wrong [N CAUGHT] times" | Same as above | old: `And it caught the AI being wrong [N CAUGHT] times` new: `And [N CAUGHT] claims failed its checks` |
| DEVPOST line 50; DECK line 150 | "AI skeptic agents that attacked our methods at three review gates" | Only gate 2 has a write-up (docs/needle_gate2.md). Gate 3 appears only as a planned stretch step in docs/needle.md line 65. Gate 1 has no doc | DEVPOST old: `- AI skeptic agents that attacked our methods at three review gates,` new: `- AI skeptic agents that attacked our methods at review gates (gate 2 is written up in docs/needle_gate2.md),` DECK old: `| Attack | AI skeptics at three gates |` new: `| Attack | AI skeptics at review gates |` (or keep "three" once gate 1 and gate 3 records are in the repo) |
| DEVPOST line 48; line 99 | "Claude ... through one cached wrapper (agent/llm.py) for reading and drafting"; "inside the product" | The demo app makes no model call; agent/needle/trial.py, the only product caller, has never run (GOLDEN_PATH_REPORT.md screen 3). The reading was done by Claude Code agents | line 48 old: `- Claude (claude-opus-5-5) through one cached wrapper (agent/llm.py) for reading and drafting.` new: `- Claude Code agents (claude-opus-5-5) read the filings and wrote each finding with its quote; product code calls Claude only through one cached wrapper (agent/llm.py).` line 99 old: `- AI tools: Claude (Anthropic API, model claude-opus-5-5) inside the product; Claude Code for development.` new: `- AI tools: Claude Code (model claude-opus-5-5) for the reading agents and for development; the Anthropic API through agent/llm.py in the product code. The demo app itself makes no live model call.` |
| DEMO line 8; VIDEO line 5 | "about 150 words a minute" | No repo source. It is a planning assumption | DEMO old: `Speaking pace is about 150 words a minute.` new: `Speaking pace is about 150 words a minute (our assumption; time one rehearsal to check).` |
| DECK line 7 | "Every number is cited." | True for the method numbers. The candidate-fill numbers cite RT2 and docs/nuggets/<TICKER>.md, which is fine. No change needed, but keep this promise when the slots are filled | none |

Figures that trace cleanly: 238 (docs/red_team_v2_company_pick.md line 5); red-team scores 20, 16.5, 23.5, 24.5 and
product scores (RT2 section 8); 15, 7, 11, 10 (row counts of the four *_ai_caught.jsonl files); 23.3%, 8.6%, 0.8%,
p.F-29 (docs/how_we_did_it.md row 9); 59% vs 43% (docs/needle_gate2.md line 6); 1,410, 43 companies, 2012 to 2024
(docs/needle_gate2.md; out/backtest/hit_rates.json); 79.4%, 1,793, +7.3%, +4.3% to +10.4%, +5.9% (docs/needle_gate2.md
line 30); seven predictions and c29a6793...e67e65 (docs/needle_sealed.md line 6); VRTX onboard (docs/red_team_v1.md
line 33); $97M and 16 points, about 1% of quarterly sales (RT2 line 50); $1,804m, 49.1%, 49.5% (RT2 line 26); $390M
and STELARA -$654M (RT2, JNJ.md); $821M, $0.28, $588M / 0.75 = $784M vs $792M, p.54, p.89 (RT2 line 34); Winrevair 22%
(RT2 line 36); zero "royalt" hits on 4 calls (RT2 line 34); Gardasil 40% and $330M to $660M (docs/nuggets/MRK.md).

### Anything that implies a company pick

| Draft and line | Problem | Fix (old to new) |
|---|---|---|
| DEMO lines 64 to 67 | The "plain words" list leads with Royalty, which is only the MRK needle's term. A judge hearing it first will guess the pick, and it is useless for the other three | old: `- Royalty: a cut of sales paid to whoever owns a patent.` new: `- [TERM IN THE NEEDLE]: [plain definition; e.g. royalty, true-up, gross-to-net]` |
| DEMO line 52 | "(RT2 section 8 has the MRK version; write one for the chosen company.)" names one candidate in the main script | old: `(RT2 section 8 has the MRK version; write one for the chosen company.)` new: `(RT2 section 8 has a worked example; write one for the chosen company.)` |
| DECK lines 250 to 251 | "RT2 recommends one company" points readers to RT2, whose line 16 says "Pick: MRK" | old (wraps across lines 250 to 251): `(RT2 section 8). RT2` / `recommends one company, but the team has not decided.` new: `(RT2 section 8). The team has not decided.` Also delete the whole "Candidate fills" section from DECK, DEMO and QA before anything is exported to slides or Devpost |
| DECK line 184; DEVPOST line 61 | The AZN factoring story is the "best example". Fine as method evidence, but on a [COMPANY] deck it can read as a hint | Keep, but label it: old `Best example, any company:` new `Best example, from a company we screened:` (merge with the plain-language rewrite above) |
| DECK line 208; QA line 30 | The J&J blind test is the only forecast example, and the sealed forecast covers only MRK and AMGN (GOLDEN_PATH_REPORT.md screen 4). If AZN or JNJ is picked, do not say "our forecast for your company is sealed" | No text change. Add to the demo checklist: `- [ ] If [COMPANY] is not MRK or AMGN, do not claim its forecast is in the sealed file` |
| DEMO line 13 (current) | The app opens on AZN by default (league order), which looks like a pick on screen | Covered by top edit 1 (select [COMPANY] before the judge arrives) |
