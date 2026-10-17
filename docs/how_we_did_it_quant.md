# How we did it: the quant team's section

Part of the team report. Parker's section covers the nugget miner and the company pick (`docs/how_we_did_it.md` on the needle branch). This section covers the model, the citation gate and how we checked both. Case study fields: tools, workflow, prompts, AI wrong, what we would change.

## 1. Tools and what each was for

| Tool | What it did |
|---|---|
| Claude Code agents, one role each | **Scraper** agents built the data layer (filings, labels, CMS files) and logged their own errors; **UI** agents built the app; **quant** agents wrote the detectors, FIND, DECIDE and the gate. Each worked in its own git worktree and branch. |
| Claude Opus (verifier agent) | Re-derived claims independently from the cited pages, with no sight of the author's reasoning, and checked gate output (verify2). |
| Adversarial review agents | Two skeptics with different lenses, a synthesizer, then independent re-verification (Section 2). |
| The citation index (`agent/needle/cite`) | Page-marked text of every document, a verification ladder (exact, normalized, fuzzy at 90 with a numeral guard) and the per-number gate. |
| WRDS I/B/E/S | Analyst consensus for the "was it priced in" test. Licensed, so run locally; public output shows the result, not the rows. |
| SEC EDGAR, DailyMed, Orange and Purple Book, CMS files (Part D, ASP, MFP, SDUD), NADAC | The sources. Fetched by code into the index. Never pasted into a chat. |
| Claude API through `agent/llm.py` (cached) | Planned for finding prose, the courtroom trial and the memo, one pass once the key is armed. Not yet run at the time of writing. |
| pytest | Every behavior change in this section has a test. |

## 2. Workflow

1. **Documents in.** Code fetches each filing, call transcript and label and writes page-marked text (`[[page N | printed P]]`) to the index. Facts carry their page.
2. **Detectors.** Deterministic code flags forensic ratios, filing-text drift, call patterns, labels and supply signals. No model runs.
3. **FIND.** Each flag becomes a finding with a dollar effect, a probability, a priced-in test against consensus and an evidence grade; the confidence label is a fixed rule. Red-team guards drop one-offs and level-as-change errors.
4. **DECIDE.** Candidate strategic moves are scored on the findings, with kill signals for months 6 to 12. Moves are chosen by people; the model is the stress test.
5. **The gate.** Every number in FIND, PRODUCT and DECIDE is checked one at a time against a cited page, a recomputed derivation or a labelled assumption. Failures are withheld, not softened (`docs/citations.md`).
6. **Review.** For each spec or build: two skeptic agents with different lenses review independently, then each reads the other's findings and concedes or defends; a synthesizer reconciles; then a fresh agent re-verifies the fixes against the code and the committed outputs. Severity is the post-exchange value. We ran this on the quant spec, the gate (two rounds, the second finding the any-numeral hole) and the backtest.

## 3. Who did what

- **Parker:** chose the company, found and wrote the findings (nugget miner and red-team passes), wrote Part 2.
- **Aidan:** the API key, the UI and the packaging.
- **Agents:** the rest of the code, tests, reviews and data layer.
- **Humans read every needle.** No finding reaches a slide until a person has opened the cited page. Several of our wrong results (table rows 4, 5, 9 and 16 in `docs/ai_in_the_build.md`) passed every code check and were caught only by that read.

## 4. The most important prompts

**The skeptic instruction.** Given to both reviewers:
> Assume the claim is WRONG until the code proves otherwise.

with the rule to cite file and line for every finding, to run the code rather than argue, and to rate severity P0 to P3. The same sentence, applied to the first backtest, killed the "59% vs 43%" result.

**The citation system rule** (`CITATION_SYSTEM_RULE` in `agent/needle/cite/llm.py`), appended to every cited model call:
> Every number and every quotation in your answer must carry a citation to one of the provided source blocks. Quote figures exactly as they appear in the source (same digits, same units). Write one claim per sentence and cite each sentence that contains a number or a factual assertion. If the sources do not contain the fact, write "not found in the provided sources" instead of guessing. Never compute or round a figure that is not printed on a source page unless you show the calculation with each operand cited. Never invent, infer, or state page numbers or document names yourself; page references come only from the citations. Any sentence containing a number or quote that has no citation will be deleted before the reader sees it.

The last sentence is true: the gate deletes it.

**The worker preamble.** Every spawned agent opened with the same frame: you are a worker, not an orchestrator; work only in your own worktree and branch; own only the files named; no em dashes; never call a paid LLM API; commit with the attribution line; do not push or merge; report file paths and counts, not a recap. Scope control mattered more than any clever wording: two agents never edited the same file.

## 5. Where the AI was confidently wrong

The full table, 26 cases with date, claim, how it was caught, fix and commit, is in `docs/ai_in_the_build.md`. Two for the deck:

1. **Lilly's league lead was a scorer bug.** Our own AI-built scorer put Lilly first on about $68B of "impact", 80% of its score. The number came from an 85.8% gross-margin level treated as a margin change. It looked plausible because Lilly's margins are high and its obesity story is real. A person traced the score row by row. Fix: a favorable margin level scores zero; Lilly moved from 1st to 8th. We now read the leader's top row by hand before we show a table.
2. **The gate that approved the wrong numbers.** Our first citation gate marked a number "verified" if any numeral on the cited page rounded to it. An independent re-check found four z-scores on the top findings "verified" by an EPS of 1.18, an I/B/E/S value of -0.13 and a page footer "- 3 -". The label said verified; the page did not support the number. We rewrote the rule so that a number must be in the quoted span or the citation's own value, and ran the re-check again.

Honorable mention: the AMGN and AZN receivables flags. The code was sure; the footnotes showed gross billing with a separate rebate liability at AMGN and factored receivables at AZN.

## 6. What we would do differently

- **Build the gate before the scorer.** The scorer ran for days on numbers nothing verified, and the first gate was wrong too.
- **Fix finding ids first.** Ids from Python `hash()` changed every run and broke joins across the league, the app and DECIDE.
- **Verify the league leader's top row by hand before publishing a table.** Lilly led on a bug.
- **Pick the company on human-read findings first**, with code ratios as corroboration, not the other way round.
- **Start from the case's deliverables** (findings table, Sharpest Needle, product comparison, Part 2, this report) and add a model only where it serves one. We built a larger model than the case needed and spent the weekend defending it.
- **Arm the API key earlier** so the LLM track runs and is checked, rather than shown as a plan.
