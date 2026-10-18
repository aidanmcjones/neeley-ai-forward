# How we did it

Draft started Sat Oct 17. Owner: Parker. The case asks for tools, workflow, key prompts, at least one case where the
AI was confidently wrong, and what we would do differently. Aidan's data-moat branch logs 61 more caught errors;
merge that table into section 4 when it lands.

## 1. Tools and what each was for
| Tool | Job |
|---|---|
| Claude Code (Opus 5.5) | Wrote and reviewed all code; ran the adversarial review gates; the nugget-miner and red-team agents |
| Claude API via agent/llm.py (cached) | Finding prose, courtroom trial, CEO memo |
| Python: SEC EDGAR, XBRL companyfacts, FDA labels, Orange and Purple Book, CMS, NADAC, FAERS, ClinicalTrials.gov | The cited corpus (data/corpus) and outside corroboration |
| pytest plus a PostToolUse hook | Every edit under agent/needle re-runs the test suite automatically |
| Hash-chained audit ledger (agent/needle/audit.py) | Every signal, verdict and prediction is tamper-evident |
| Bloomberg (5 official transcripts), WRDS IBES | Transcript quality and consensus for the "priced in" call |

## 2. Workflow
- Documents in: filings and labels fetched by code into page-marked text (`[[page N | printed P]]`), never pasted.
- Split: code detectors flag numeric anomalies; the nugget-miner agent reads footnotes, risk language and call Q&A;
  humans pick, check and sign off every finding that reaches a slide.
- Checking: every quote passes `pages.check` (exact or fuzzy match on the cited page); every number reconciles to
  XBRL or the page; skeptic agents attack methods at three gates; the red-team agent scores us against the rubric.

## 3. Most important prompts
[Paste: the nugget-miner spec (.claude/agents/nugget-miner.md), the red-team spec, the trial prompts, and the two
skeptic prompts from gate 2.]

## 4. Where the AI was confidently wrong, and how we caught it
| # | What the AI-built system confidently said | What was true | How we caught it | Guard now |
|---|---|---|---|---|
| 1 | Backtest: gross-margin drops precede trouble 59% vs 43% (lift 1.39) | Event windows overlapped data already known; corrected, no signal significantly predicts hard events | Two adversarial skeptics, gate 2 (docs/needle_gate2.md) | Point-in-time filters; firm-clustered CI must clear 1 |
| 2 | LLY leads the league; its margin implies about $68B of impact | The 85.8% gross-margin *level* was scored as if it were a *change*; a high margin is a strength | Score looked implausible; traced in agent-chat #19 and on this branch | test_gross_margin_level_has_no_dollar_path; favorable outliers dropped |
| 3 | MRK needle: R&D jumped to 58.7% of revenue | A one-time $5.7B acquired IPR&D charge (Terns), $2.31 per share; it also drove a -95.8% tax rate "which had no tax benefit" (MRK 10-Q Q2 2026) | Red-team pass opened the 10-Q | test_ipr_and_d_charge_is_one_off; one-offs go to out/<T>/context.jsonl |
| 4 | LLY holds 469 days of inventory, a peer outlier | Days on cost of sales inflate at an 85% margin; on revenue LLY is not an outlier | Red-team pass | Peer days-inventory now on revenue |
| 5 | AZN impact: receivables 14,168M vs 11,047M, revenue +11.7% | The sentence used year-end FY2025 (10,237M vs 8,302M, +8.6%); the math silently used half-year 6-K figures on a broader concept | Sentence and formula disagreed during audit | test_impact_math_matches_the_sentence |
| 6 | GILD needle: new MD&A language | The paragraph was good news ("positive topline Phase 3 results"); the code cannot tell direction without the LLM | Audit of the rescored league | Undirected MD&A changes are not needle-eligible |
| 7 | Seven of ten needles were label facts ("Keytruda lists 21 indications") | FDA labels are public and read by everyone; not "least discussed" | Audit | Label findings floored at O = 0.5 |
| 8 | NVO needle was a table of contents parsed as a paragraph | Not text | Audit | Paragraph filter requires a sentence |
| 9 | AZN Sharpest Needle (code): receivables +23.3% vs revenue +8.6%, a collections red flag | Factorable receivables and China bank acceptance drafts went from $667m to $2,681m (20-F FY2025 p. F-29); without them trade receivables fell 0.8%. The real needle was US gross-to-net (p. 34) | The nugget-miner read the receivables footnote | Code ratios are flags for a human or agent read, never a needle on their own |

## 5. What we would do differently
- Write the red-team pass into the plan from hour one, not after the league table existed.
- Pick the company on human-read nuggets first, then use code ratios as corroboration.
- Time a manual analyst read of one 10-K early, so the Impact number is measured, not estimated.
