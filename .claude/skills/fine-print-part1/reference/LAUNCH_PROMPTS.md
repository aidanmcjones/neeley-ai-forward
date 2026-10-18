# Part 1 launch prompts, verbatim

These are the exact Agent launch prompts and SendMessage resume texts the orchestrating session (transcript e8d819f0, 2026-10-18 UTC) sent to the Part 1 workers, recovered from the session transcript. One example per role is shown (AMGN where the role is per company); the other companies' prompts differ only in ticker, company name and the company-specific checks the orchestrator pulled from that company's candidates.jsonl or skeptic files. Every launch was subagent_type general-purpose, model opus, no effort override. Round 2 skeptics were not new agents: the round 1 agent was resumed with the SendMessage text shown.

The paths inside the prompts are the paths of the original run (quant-model and gap-data worktrees, the scratchpad venv interpreter). Substitute your own.

## P1 blind reader (AMGN)

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T03:28:11 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally as you find them
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: You are the blind reader for ticker AMGN (Amgen). First read, in full, /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part1/BLIND_READER_BRIEF.md and follow every rule in it, especially the DO NOT READ list (no prior-run files, no league/findings/nuggets/needle/handoff docs, no other worktrees). Then read the case PDF and rubric it names. Then walk all eight hiding places for AMGN using the citation index and verified tables, and write out/part1/_blind/AMGN/candidates.jsonl and reader_summary.md exactly in the brief's output contract. Verify every quote with verify_quote before writing it. Report the file paths, the number of candidates and no-finding records, and any data gaps.
```

## P1 materiality skeptic round 1 (AMGN)

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T03:45:56 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Round 1 skeptic, lens MATERIALITY AND MATH, ticker AMGN. Read /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part1/SKEPTIC_BRIEF.md in full and follow it. Input: /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/AMGN/candidates.jsonl (and reader_summary.md). Assume every candidate is wrong until the cited page proves otherwise; open each cited page with get_page yourself. Check especially: the TAVNEOS intangible figure and the "5.6 times sales" and EPS math (is it a gross or net-of-tax number, what share count), the IRS Puerto Rico exposure vs accrual numbers and periods, whether the receivables conclusion (no finding) is right, whether net-price percentages come from a cited page or a raw table, and whether "52% of growth in Other products" is arithmetic on cited lines. Write out/part1/_blind/AMGN/skeptic_materiality_r1.json in the brief's shape. Report the count of refuted vs held and the single biggest math problem you found.
```

## P1 obviousness skeptic round 1 (AMGN)

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T03:46:03 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Round 1 skeptic, lens OBVIOUSNESS, ticker AMGN. Read /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part1/SKEPTIC_BRIEF.md in full and follow it. Input: /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/AMGN/candidates.jsonl (and reader_summary.md). For each candidate, search the transcripts, earnings releases, press releases and consensus tables in the citation index for the same point already being said or priced; cite what you find. The IRS Puerto Rico case and the FDA TAVNEOS action are public headlines; test whether the candidate's specific angle (the accrual gap, the intangible carrying value) goes beyond what a press-release skim gives. Write out/part1/_blind/AMGN/skeptic_obviousness_r1.json in the brief's shape. Report the count of refuted vs held and which candidate is least obvious.
```

## P1 synthesizer (AMGN)

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T04:01:56 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Synthesizer for ticker AMGN. Read /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part1/SYNTHESIZER_BRIEF.md in full and follow it. Inputs are in /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/AMGN/ (candidates.jsonl, reader_summary.md, the four skeptic files). Both skeptics converged on c06 (the $2.3B U.S. TAVNEOS intangible, about 5.2x FY2025 sales of $459M on 10-K p75, GAAP-only, with the Q1-to-Q2 10-Q wording change from "did not result in significant changes to the estimated future cash flows" to "observations with respect to new U.S. patient interest") and c02 narrowed (54% company-wide deduction rate, the $2.2B accrual build, about $1.07B of 2025 operating cash flow from deductions accrued but unpaid). They split on c03 (TEPEZZA Q1 2026 channel stocking: materiality now holds it as material within the quarter, about 1.1 of 4.4 growth points, while obviousness refutes it as small and reversed within one quarter) and c08 (materiality holds the $132M Q2 true-up ceiling plus the Q3 2026 $250M lap; obviousness refutes it as a comparison effect). Rule on both. Also check the materiality skeptic's correction that the FDA's voluntary-withdrawal request (January 16, 2026, 10-K p137) preceded the April 27 withdrawal proposal, and whether the Q1 call figure "$490 million in the U.S." is a global figure (10-Q 2026Q1 p37). The product pick is Repatha vs Praluent, Leqvio and Lipfendra; both skeptics call the stated edge management's own message, so rule on whether the pick stands with a different edge. Write synthesis.json and trace_part.jsonl exactly in the brief's shapes. Report the counts of survived / narrowed / killed, the best candidate id, and your one-line company verdict.
```

## P1 ranker

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T04:10:15 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Ranker for the blind company selection. Read /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part1/RANKER_BRIEF.md in full and follow it exactly, including the DO NOT READ list until the seal is written and the sha256 procedure. All ten synthesis.json and reader_summary.md files are in /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/<T>/ for T in ABBV AMGN AZN BMY GILD JNJ LLY MRK NVO PFE. The synthesizers' survivor counts (material and non-obvious) are AMGN 3, AZN 2, MRK 2, PFE 2, and 1 each for ABBV, BMY, GILD, JNJ, LLY, NVO, but you must rank on the case's test as the brief describes, not on that count alone: weigh materiality and confidence of the best item, the product ruling, how many honest cited rows can fill a five-row table, and the data limits. Write out/part1/selection.md (sealed with the trailing sha256 line), out/part1/selection.json, and only afterwards out/part1/selection_appendix.md comparing the blind result to out/league_v3.md, docs/nuggets/best_needle.json and any docs/red_team*.md or docs/nuggets/NOTE.md in the quant-model worktree. No em dashes. Report the three picks in order, the sha256, and the file paths.
```

## P1 writer (AMGN)

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T04:14:34 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Part 1 writer for ticker AMGN (Amgen). Read, in full and in this order: /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part1/PART1_WRITER_BRIEF.md, docs/part1/UI_CONTRACT.md, docs/part1/HELPERS.md, docs/citations.md, then the AMGN blind folder (out/part1/_blind/AMGN/synthesis.json first, then candidates.jsonl, trace_part.jsonl and the four skeptic files). Use the synthesizer's corrected wording: c06 (TAVNEOS intangible, 5.2x FY2025 sales of $459M on 10-K p75, FDA voluntary-withdrawal request January 16 2026 preceding the April 27 proposal, Q1-to-Q2 10-Q wording change), c02 (54% deduction rate, $1.42/share per point pre-tax, $1.07B excess reserve build), c03 (TEPEZZA Q1 2026 channel stocking limited to Q1, U.S. $424M not $490M), then fill to five rows from cited, sized, killed-as-obvious candidates marked on the record (the IRS Puerto Rico case c05 and the profit-share c07 are natural candidates). Sharpest Needle: c06. Product: Repatha vs Praluent, Leqvio, Lipfendra with the synthesizer's label edges (coronary revascularization in the CV indication, HoFH from age 10, Lipfendra's 30-minute fast), tied to c02 through the 10-K's mid-single-digit 2026 net-price guide (p71). Run the per-number gate on every record; failed records go to rejected.jsonl. Write out/part1/AMGN/part1.json, part1.md, trace.jsonl (header line plus the trace_part lines renumbered with finding_n), rejected.jsonl. Validate JSON. No em dashes. Report counts (rows, gate passed/failed, needle id, product) and anything you could not source.
```

## P1 independent verifier

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T04:26:46 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Independent verifier for the three Part 1 deliverables. Assume every number is WRONG until the cited page proves it. Do not read the writers' reports or scripts; read only the output files and the sources. Files: /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/{AMGN,MRK,PFE}/part1.json. Sources: the citation index via agent/moat/cite.py from the gap-data worktree (/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data, interpreter /private/tmp/claude-501/-Users-aidanjones/e8d819f0-5924-4fae-a529-36fd52188c9e/scratchpad/venv/bin/python; get_page(doc_id, page) and verify_quote). For each company: (1) for every finding row, open every cite in cites and confirm the quote is on the page (verify_quote) and that each number in finding, impact.text and impact.math is either inside a quoted span, equal to a cite's own value, labelled [derived] with operands that are themselves cited and whose arithmetic you reproduce, or labelled [assumption]; (2) for the Sharpest Needle "why" and the product_table financial_tie, growth_limiter and priced_in texts, do the same; (3) sample 6 product cells per company (at least one per row key) and check the quoted label or table text is on the page; (4) check that no sentence states as fact a number the blind skeptics refuted (read out/part1/_blind/<T>/synthesis.json rulings for the ids used); (5) check currency labels and that no Bloomberg-licensed page is quoted. Write /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/verify_report.md with a table per company (row or cell, what you checked, pass or fail, the exact defect) and a summary line with counts. Do not edit the part1 files. Report the fail count per company and the single worst defect.
```

## P1 priced-in calls

Agent launch: subagent_type=general-purpose model=opus at 2026-10-18T04:27:39 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally, from Python only (never heredoc or echo; "$2" expansion corrupts figures)
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts

TASK: Replace the "untestable" priced-in call in the three Part 1 files with an evidence-graded inference, for AMGN, MRK and PFE. Files: /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/<T>/part1.json and part1.md. The case asks for one sentence on whether the market has already priced the item in. Product-level consensus does not exist in the index, so build the call for each company's Sharpest Needle (and, in one clause, the product growth limiter) from four sources in the gap-data worktree (/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data, interpreter /private/tmp/claude-501/-Users-aidanjones/e8d819f0-5924-4fae-a529-36fd52188c9e/scratchpad/venv/bin/python): (a) analyst attention: was the item asked on the last four to ten calls (data/moat/verified/market/priced_in_scorecard.csv, never_asked.csv, and the qa_turns or transcript turns in the index via agent.moat.cite search_pages / the calls helper agent.moat.case_calls.call_qa); (b) press attention: GDELT mention counts (look under data/moat/verified/market and data/moat/tables for a gdelt file); (c) company-level I/B/E/S consensus revisions around the disclosure date (ibes tables; these rows are licensed: use them to state direction only, never quote values or deep-link; verify_status no_verified_copy means machine_data); (d) event returns around the filing or call date (event_returns in verified/market). Read docs/part1/HELPERS.md for helper signatures and docs/citations.md for the gate statuses. Write the sentence in the form "Likely not priced in: never asked on N calls, no consensus revision after the 10-Q" or "Likely priced in: ..." with the evidence named, set priced_in.call to one of "priced in" | "not priced in" (keep "untestable" only if all four sources are empty for that item), add priced_in.confidence (high|medium|low), priced_in.evidence (a list of {source, finding, cites}) and priced_in.limit naming the missing product-level consensus. Every number in the sentence goes through the per-number gate (agent/needle/cite/gate.py in the quant-model worktree) with a text_marked twin and marker_map, exactly like the other fields; counts from fact rows are cited by locator. Update part1.md's priced-in line to match. Do not change any other field. Validate JSON, then run grep -nE '[ (\"]\.[0-9][0-9]*[BMbnmk%]' on the six files (must be empty) and an em-dash check. Report, per company: the call, the confidence, the sources that had data, and the gate status.
```

## P1 materiality skeptic round 2 resume (AMGN)

SendMessage to a running agent (resume) at 2026-10-18T03:58:09 UTC

```
Round 2, same lens (MATERIALITY AND MATH), ticker AMGN. The other skeptic, on the OBVIOUSNESS lens, has written /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/AMGN/skeptic_obviousness_r1.json. Read their argument AGAINST THE SOURCES (open the pages they cite with get_page). Concede what they got right, hold what you still believe with a reason, and narrow your claim if it was too broad. Do not restate round 1. In particular: they held c03 (TEPEZZA: the Q1 2026 10-Q says 22 of 29 growth points were channel inventory while the call credited demand) as least obvious, which you refuted as too small and contradicted by Q2; settle whether a channel-inventory-vs-demand discrepancy on a roughly $2B product is material. They held c06 narrowed (TAVNEOS carrying value about 5x sales, GAAP-only, FDA withdrawal request reported on the 2026Q2 call but not in the 10-Q note), c02 narrowed to the filings-only 54% deduction rate and 30% accrual build with new "timing of payments" wording, and c08 narrowed to the unflagged $130M Q2 2026 true-ups; they killed c05 (the accrual gap was answered in 2024Q2 and 2026Q1 Q&A) and c10 (the $2.5B U.S. capex undercuts "no pledge"). Size the narrowed c02, c06 and c08 versions on your math. Write out/part1/_blind/AMGN/skeptic_materiality_r2.json in the SKEPTIC_BRIEF round-2 shape (each verdict carries round2: {conceded, held, narrowed}). Report what changed between your rounds.
```

## P1 obviousness skeptic round 2 resume (AMGN)

SendMessage to a running agent (resume) at 2026-10-18T03:58:17 UTC

```
Round 2, same lens (OBVIOUSNESS), ticker AMGN. The other skeptic, on the MATERIALITY AND MATH lens, has written /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/_blind/AMGN/skeptic_materiality_r1.json. Read their argument AGAINST THE SOURCES (open the pages they cite with get_page). Concede what they got right, hold what you still believe with a reason, and narrow your claim if it was too broad. Do not restate round 1. In particular: they found TAVNEOS sales ARE in the filings (10-K FY2025 p75: U.S. $423M plus ROW $36M; Q2 2026 10-Q p44), so the carrying-value ratio is about 5.2x 2025 sales or 4.0x the Q2 run rate, and the "Other products" table is broken out product by product (which kills c04 on a different ground); they held c05 on the math but you killed it as answered in Q&A; they refuted c03 as too small and contradicted by Q2. Say whether your held c03 survives their size objection, and whether c05's filings-only timing update (decision slipped, NOPA reissued twice, 2019-2022 audit opened) is a finding or just a status note. Write out/part1/_blind/AMGN/skeptic_obviousness_r2.json in the SKEPTIC_BRIEF round-2 shape (each verdict carries round2: {conceded, held, narrowed}). Report what changed between your rounds.
```

## P1 priced-in: scraper source list relayed to the agent

SendMessage to a running agent (resume) at 2026-10-18T04:29:13 UTC

```
Exact sources from the scraper, use these. Caveat first: the topic-keyed tables (priced_in_scorecard, never_asked, analyst_topics, news_mentions) use a fixed vocabulary of 9 topics (IRA_negotiation, MFN, tariff, gross_to_net_price, inventory_channel, biosimilar_generic, pipeline, guidance, top_products), so none of our six items is a topic there; analyst attention on the specific item must come from full text. Nearest proxies only as context: inventory_channel for MRK long-dated inventory, top_products for PFE Vyndaqel (its GDELT query is "Pfizer" (Ibrance OR Vyndaqel)), gross_to_net_price for the AMGN deduction rate.
(a) Analyst attention, item-level: data/moat/verified/calls/qa_turns.csv (6,556 rows; columns ticker, quarter, speaker, role, firm, grade, quotable, text, path, page; covers 2024Q1 to 2026Q2 for the 10 tickers, except the new moat copies of AMGN 2026Q2 which you reach through the index turns table or case_calls.call_qa). Filter role == analyst and grep text for "Tavneos"/"avacopan", "transition tax"/"TCJA"/"IRS", "inventory", "Vyndaqel"/"tafamidis"/"share", "legal"/"litigation". Attention share = analyst questions naming the item over the last 8 quarters divided by analyst_turns from data/moat/verified/market/analyst_topics.csv for the same quarters. Topic-level context: data/moat/verified/market/priced_in_scorecard.csv (ticker, topic, quarters_asked, share_of_quarters_asked, analyst_turns_on_topic, recent_unasked_streak, analyst_attention_tier, gdelt_articles_total, n_earnings_events_topic_asked, mean_abn_0_to_1_when_asked, latest_example_quarter/speaker/example) and never_asked.csv.
(b) GDELT: data/moat/tables/news_mentions.csv (ticker, topic, month, article_count, query, source, source_row), monthly, raw table: cite by the GDELT query string and month, never as a page. No item-level queries exist; if you need one, say so in your report and keep the call conservative.
(c) I/B/E/S (licensed, local use only, never quote or deep-link; state direction only): data/moat/tables/ibes_revenue_consensus.csv (measure SAL), ibes_eps_consensus.csv (annual EPS), ibes_eps_quarterly.csv. Key on oftic (MRK, AMGN, PFE), not ticker. statpers = monthly consensus date, fpi 1 = current FY, 2 = next FY, 6 to 9 = next quarters, fpedats, numest, meanest, medest. Revision = diff of meanest across consecutive statpers for the same oftic, fpi, fpedats, around the disclosure date (10-Q filing or call). Id map: data/moat/verified/market/ibes_ids.csv.
(d) Event returns: data/moat/verified/market/event_returns.csv (doc_id, ticker, doc_type, period, filed, day0_date, abn_day0, abn_0_to_1, abn_m1_to_5, event_group, is_primary; use is_primary == True). Use the verified file, not tables/event_returns.csv. Disclosure dates: AMGN TAVNEOS wording change = 10-Q 2026Q2 filing; AMGN deduction rate = 10-K FY2025; MRK IRS = 10-K FY2025 and 10-Q 2026Q2; MRK inventory = 10-K FY2025 and 10-Q 2026Q2; PFE Vyndaqel = 10-Q 2026Q2 and the Q2 call; PFE legal charge = 10-Q 2026Q2 and the Q2 release.
Carry on with the same output contract; cite counts by fact locator (file#row or the index's turns) and keep the sentence to one line per company.
```

## P1 verifier fixes: second task to the priced-in agent

SendMessage to a running agent (resume) at 2026-10-18T04:35:57 UTC

```
Second task, after you finish the priced_in replacement and before you report: apply the fixes from the independent verifier's report at /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/out/part1/verify_report.md (read it in full). The seven fails, all attribution or scoping, none arithmetic: AMGN (1) sharpest_needle.why is false ("the only surviving ruling that both skeptics held through both rounds with materiality high and obviousness low" also describes AMGN-c02): rewrite the why truthfully (c06 is the larger and less discussed of the two, say why), add its marker_map, and add the cite for TAVNEOS sales (10-K p75) that the 5.2x depends on; (2) finding 5 restates the refuted "about a third of $1,043M incremental sales" ratio: drop that clause and keep only the cited profit-share dollars and growth; (3) financial_tie applies the mid-single-digit guide to U.S. Repatha only ($1,663M) though the guide is in the global paragraph: restate on the global base ($3,016M, about $151M at a labelled 5% midpoint) or label the U.S.-only choice as an assumption; (4) growth_limiter and the Lipfendra pricing cell say Lipfendra "launches with" a direct-to-patient cash channel, but Merck's Q2 2026 10-Q says it "will be expanding the program in the future to include Lipfendra": fix the wording and drop any implied Lipfendra price pressure (blind c09 refuted it). MRK (5) the Tecentriq patent cell cites pipeline/loe_calendar.csv#617 company_stated_loe, a field that does not exist; the only fact row is biosimilar_count = 0: cite what exists and say plainly that no exclusivity date is in the index. PFE minor notes, fix cheaply: (6) marker "$1 billion[5]" in finding 4 points to the wrong cite, and the financial_tie marker list includes a non-operand cite; (7) finding 4's "partly COVID-product mix" has no cite (cite the 10-Q sentence or drop the clause), and finding 1 should note BridgeBio's page states no geography for its product revenue. Re-run the gate on every text you touch, keep the no-heredoc rule and the grep check, and report per fix what changed.
```

## P1 verifier fixes: acceptance note

SendMessage to a running agent (resume) at 2026-10-18T04:36:37 UTC

```
Priced-in work accepted and committed as is (growth-limiter clauses are fine; no rerun). When you apply the seven verifier fixes from verify_report.md, also edit the stale AMGN not_sourced entry and its md bullet to "Consensus Repatha estimate (product-level consensus absent; priced-in call is an inference)". Then report per fix.
```

