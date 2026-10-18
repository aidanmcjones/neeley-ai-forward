# Part 2 launch prompts, verbatim

These are the exact Agent launch prompts and SendMessage resume texts the orchestrating session (transcript e8d819f0, 2026-10-18 UTC) sent to the Part 2 workers, recovered from the session transcript. One example per role is shown (AMGN where the role is per company); the MRK and PFE prompts differ only in ticker, company name, candidate count and the company-specific clashes the orchestrator summarised from the skeptic files. Every launch was model opus with no subagent_type (the default general-purpose agent) and no effort override. Round 2 skeptics were not new agents: the round 1 agent was resumed with the SendMessage text shown. The mid-wave messages (scraper data inventory, rubric checks, number-anchor shortcut, refresh task and rulings) are included because the final files depend on them.

The paths inside the prompts are the paths of the original run (quant-model and gap-data worktrees, the scratchpad venv interpreter). Substitute your own.

One-token substitution: the AMGN synthesizer prompt's em-dash check was written with the literal em dash character as the grep pattern; it is reproduced here as `grep -c $'\xe2\x80\x94'` (the same byte sequence in ANSI-C quoting) so this file carries no em dash. Nothing else was changed.

## P2 strategist (AMGN)

Agent launch: subagent_type=None model=opus at 2026-10-18T05:07:46 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Write results to disk incrementally as you find them
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts
- No em dashes anywhere. Never set, read or rename ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_HOLD.

TASK: You are the Part 2 STRATEGIST for ticker AMGN (Amgen). First read, in full, /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part2/STRATEGIST_BRIEF.md and follow every rule in it: the READ ONLY list, the DO NOT READ list, the index interpreter and usage, the citation rules, the Python-only writing rule and the grep check. Then read the case PDF's Part 2 section and the rubric, then out/part1/AMGN/part1.json and part1.md in the quant-model worktree. Propose at least four candidate moves of at least two types, each costed with cited math, written to out/part2/_work/AMGN/candidates.jsonl in the brief's exact contract, plus strategist_summary.md and data_requests.md. Create the folder yourself (mkdir -p). The skeptics default to kill, so every number must trace to a cited page or carry [assumption]; a move management has already announced is obvious and must be marked so in already_announced_check. Work to disk as you go. Finish within about 40 minutes of work; depth on four well-evidenced moves beats six thin ones. Report the candidate ids, types, cost and return amounts, and the data gaps.
```

## P2 CFO/math skeptic round 1 (AMGN)

Agent launch: subagent_type=None model=opus at 2026-10-18T05:17:35 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts
- No em dashes anywhere. Never set, read or rename ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_HOLD.
- Keep any helper scripts in your own subfolder of the scratchpad (for example scratchpad/amgn_cfo/), never at the scratchpad root, because other workers write there too.

TASK: You are the CFO/math SKEPTIC, round 1, for ticker AMGN (Amgen) in Part 2. Read /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part2/SKEPTIC_BRIEF.md in full and follow it (your lens is CFO/math; read-only and forbidden lists, index usage, output shape). Inputs: out/part2/_work/AMGN/candidates.jsonl (4 candidates AMGN-m01 to m04) and out/part1/AMGN/part1.json in the quant-model worktree; the citation index in the gap-data worktree via agent/moat/cite.py with the interpreter named in the brief. Assume every move is WRONG until the cited page proves otherwise; default refuted: true when uncertain. For each candidate check: every cost and return operand traces to the cited page (open the page with get_page, do not trust the quote), deal comps are real and on the page and comparable (m03 prices a UCB profit-share buyout at 5x with no indexed comp; m01 sizes a trial on the 331-patient pivotal study), units and periods are right, no double counting (expected-value math on an assumed probability shift, impairment avoided vs operating income), the return beats a stated cost-of-capital hurdle (cite it or mark [assumption]), and the money arrives inside 24 months or the candidate says it does not. Always fill the correction field with the accurate half when a claim is partly right. Write out/part2/_work/AMGN/skeptic_cfo_r1.json in the brief's exact shape (from Python, never shell heredoc), then run the brief's grep and em-dash checks. You will be resumed for round 2 with the other skeptic's file, so keep your notes. Report refuted counts and the single strongest surviving candidate in your view.
```

## P2 decider/compliance skeptic round 1 (AMGN)

Agent launch: subagent_type=None model=opus at 2026-10-18T05:17:44 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts
- No em dashes anywhere. Never set, read or rename ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_HOLD.
- Keep any helper scripts in your own subfolder of the scratchpad (for example scratchpad/amgn_decider/), never at the scratchpad root, because other workers write there too.

TASK: You are the DECIDER/COMPLIANCE SKEPTIC, round 1, for ticker AMGN (Amgen) in Part 2. Read /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model/docs/part2/SKEPTIC_BRIEF.md in full and follow it (your lens is decider/compliance; read-only and forbidden lists, index usage, output shape). Inputs: out/part2/_work/AMGN/candidates.jsonl (4 candidates AMGN-m01 to m04) and out/part1/AMGN/part1.json in the quant-model worktree; the citation index in the gap-data worktree via agent/moat/cite.py with the interpreter named in the brief. Assume every move is WRONG until the cited page proves otherwise; default refuted: true when uncertain. For each candidate check: would the named decider (regulator for m01: would the FDA accept a new trial as a postmarketing commitment in a withdrawal proceeding, with page evidence; payer for m04; doctor for m02; UCB as counterparty for m03) actually accept it; is the move obvious or already announced by management (search transcripts, 10-K and 10-Q strategy sections and press releases yourself; do not trust the strategist's already_announced_check); do all six promo rules pass for any material (m02 has a doctor-facing Repatha piece and claims map from label sections 1, 2.1, 4 and 5.1; the repatha label is indexed as doc_type fda_label_version with section pages, open each cited section and confirm the claim is there; the strategist says section 6 adverse reactions is not indexed, so test whether "risks as prominent as benefits" can pass without it; comparisons only with head-to-head evidence in verified/product/head_to_head.csv; no testimonials or likenesses; the student-concept label on every piece); are the kill signals measurable with thresholds and a reporting source. Always fill the correction field. Write out/part2/_work/AMGN/skeptic_decider_r1.json in the brief's exact shape (from Python, never shell heredoc), then run the brief's grep and em-dash checks. You will be resumed for round 2 with the other skeptic's file, so keep your notes. Report refuted counts and the single strongest surviving candidate in your view.
```

## P2 synthesizer (AMGN)

Agent launch: subagent_type=None model=opus at 2026-10-18T05:25:43 UTC

```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Write results to disk incrementally
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts
- No em dashes anywhere. Never set, read or rename ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_HOLD.
- Keep helper scripts in your own scratchpad subfolder (scratchpad/amgn_synth/), never at the scratchpad root.
- Write every output file from Python, never shell heredoc or echo.

TASK: You are the Part 2 SYNTHESIZER for ticker AMGN (Amgen). Quant-model worktree: /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model (use absolute paths). Read in full, in this order: docs/part2/SYNTHESIZER_BRIEF.md, docs/part2/UI_CONTRACT.md (including the "Exporter checks the UI enforces" section at the end; every one is a hard check your part2.json must pass), out/part1/AMGN/part1.json (copy its layout for text, text_marked, marker_map, cites, derived, assumptions, numeric_check), out/part2/_work/AMGN/candidates.jsonl, skeptic_cfo_r1.json, skeptic_cfo_r2.json, skeptic_decider_r1.json, skeptic_decider_r2.json, and out/part2/_work/data_wave_db7f01f.md (what the index now holds, including the tavneos label at tavneos:drugs/tavneos/label_v16.md and verified/product/label_claims.csv, plus the rules on unverified rows, none_found pairs and missing deal terms). Index: gap-data worktree /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data, interpreter and usage in the brief, rebuilt at db7f01f. Gate: agent/needle/cite/gate.py and render.py in the quant-model worktree (read them and docs/citations.md; Part 1 used gate_record).

What the skeptics concluded (verify against their files, do not trust this summary): all four AMGN candidates refuted as written; after round 2 both lenses name the same narrowed survivor: m01 in gated form, a $10M to $15M [assumption] hearing-record offer to the FDA (a designed confirmatory randomized trial with independent endpoint adjudication plus a U.S. liver-safety registry, filed into the TAVNEOS hearing record, with the roughly $75M trial budget released only if the FDA signals it will accept postmarketing commitments in lieu of withdrawal; 10-Q Q2 p.59 lists postmarketing commitments among the FDA's alternatives, p.21 carries the "untrue statements" ground no trial can cure). Math: first-half run-rate $514M a year times about 80.4 percent non-GAAP margin (CFO Griffith, 2026Q2 transcript p.8, grade B; the proxy p.137 gives 81.7 percent for FY2025) is about $414M of contribution exposed from month 12; break-even about 3 points of retention probability at the $12.5M midpoint; loss capped at the offer cost. m04 (rebate for prior authorization) dies on the gross-vs-net unit error and payer precedent; m02 (Repatha campaign) dies as management's existing primary-care push plus a promo fair-balance failure (section 6.1 omitted); m03 (UCB buyout) fatal. Unresolved: whether the FDA's postmarketing-requirement path has real probability given the untrue-statements ground; whether m02's lift is unsourced or uncreditable; gross vs net rebate basis; UCB's walk-away price. Record them in unresolved[] as the two positions, never averaged. Rejected alternatives: pick the two strongest (likely m04 narrowed and m02 narrowed, or m03) with the skeptic lens and reason that killed each.

Produce, per the brief and contract: out/part2/AMGN/part2.json, part2.md, trace.jsonl (header lenses exactly ["CFO/math", "Decider/compliance"], one step per candidate with both skeptics' round 1 and round 2 positions, verdict survived|narrowed|killed, reason in words with no ungated figures, candidate cites stamped with verify_status via verify_quote), rejected.jsonl (blocks that failed the gate, with why). The move is one sentence a CEO could sign naming the budget and people, with the gated structure explicit. case_for shows cost and return math step by step with every operand cited or [assumption]; the budget block must pass the gate so amount_usd and people publish (an [assumption] budget is allowed if marked; show the cited exposure math). Exactly two rejected alternatives with skeptic_lens and figure-free move text. Kill signals with thresholds and month_window strings (FDA hearing grant or denial, summary judgment, TAVNEOS quarterly sales from the 10-Q, intangible recoverability wording). Evidence section names the decider (regulator) and what the evidence can and cannot tell. Promo: the chosen move has no doctor or patient material, so has_material false with empty pieces and claims_map and null rules_check (do not carry the Repatha piece into the chosen move). Every gated block must end with numeric_check status passed or no_numbers; fix or drop any that fails. Every cites[] entry is a full evidence object (cite_id, doc_id, page, quote, label, url, verify_status, withheld, grade). No league, score, "S =" or robustness words. After writing run: json load on all files, `grep -nE '[ ("]\.[0-9][0-9]*[BMbnmk%]' out/part2/AMGN/*`, and `grep -c $'\xe2\x80\x94' out/part2/AMGN/*`; all must be clean. Report: the move sentence, the two rejected, killed/narrowed/survived counts, gate results per block, absolute paths.
```

## P2 strategists: scraper data inventory (sent to all three)

SendMessage to a running agent (resume) at 2026-10-18T05:10:40 UTC

```
Data inventory from the scraper, use while you work (all paths under the gap-data worktree): deal comps live in verified/deals/deal_comps.csv (facts table deals/deal_comps.csv, row key deal_id; only 9 rows in ATTR, amyloid, vasculitis or tafamidis areas, so ATTR-CM, oral PCSK9, SC formulation and anti-FcRn comp sets are NOT indexed yet; more arrive within the hour as doc_id "<ACQUIRER>:deals/8k/..." with deal_id "P2-<ACQUIRER>-<YYYYMMDD>"; Merck 10-K FY2025 pages describe LaNova, Harpoon and Verona terms via search_pages("upfront payment", ticker="MRK", doc_type="annual_report")). FDA labels with section pages are indexed for vyndaqel, vyndamax, amvuttra, repatha, praluent, leqvio, keytruda, keytruda-qlex, opdivo, opdivo-qvantig, imfinzi, tecentriq (doc_type fda_label_version, use search_pages(q, ticker=<drug>, doc_type="fda_label_version"); section headings like "1 INDICATIONS AND USAGE", "14 CLINICAL STUDIES" are citable pages). NOT indexed yet: tavneos, tepezza, evenity, tezspire, uplizna, rituxan. CMS Part D spend: tables/partd_by_year.csv (read the CSV directly; rows for keytruda, keytruda-qlex, opdivo, opdivo-qvantig, vyndaqel, vyndamax, attruby, amvuttra); Part B: tables/partb_asp_quarterly.csv, tables/partb_providers_by_drug.csv. No IRA selected-drug table yet; company-level IRA exposure with quotes in verified/policy/policy_exposure.csv and force_summary.csv. Head-to-head: verified/product/head_to_head.csv (row key nct_id, columns true_head_to_head, h2h_tier) is the only comparative table; treat any pair not marked true_head_to_head = yes as "not supported". Anything missing goes in data_requests.md, not guessed.
```

## P2 PFE CFO skeptic: scraper note on CMS Part D

SendMessage to a running agent (resume) at 2026-10-18T05:19:05 UTC

```
Scraper note for your PFE math checks: CMS Part D claims data is annual and ends at data year 2024; there is no public quarterly Part D claims series for 2026, so the strategist's "Q1 2026 combined tafamidis Part D claims 44,532 vs 2025 quarterly average 46,381" (PFE-m02) is from a non-CMS source. Open the cited page and judge whether it supports the number; if not, refute that operand. Q2 2026 Vyndaqel family revenue is on PFE:earnings/2026-08-04_pfe-6282026xex99.md pages 4 and 24 and PFE:10q_2026Q2.md p.35. Neither Vyndaqel nor Vyndamax appears in any published IRA cohort (2026 to 2028). Full replies in out/part2/_work/PFE/data_replies.md.
```

## P2 PFE decider skeptic: scraper note on formulary counts

SendMessage to a running agent (resume) at 2026-10-18T05:19:09 UTC

```
Scraper note for your PFE checks: formulary counts in the index are plan-count shares, not enrollment weighted, and there is no public enrollment-weighted series; the strategist's PFE-m02 "Part D claims Q1 2026" figure is from a non-CMS source (CMS claims data ends at data year 2024). Neither Vyndaqel nor Vyndamax appears in any published IRA cohort for 2026 to 2028, and the 2029 list is unpublished, so 2029 status is an [assumption]. The 100,000 ATTR-CM prevalence row in verified/epi/indication_epidemiology.csv is verified against the primary paper PMC11740649. Full replies in out/part2/_work/PFE/data_replies.md.
```

## P2 CFO/math skeptic round 2 resume (AMGN)

SendMessage to a running agent (resume) at 2026-10-18T05:23:16 UTC

```
Round 2. The decider/compliance skeptic reviewed the same four AMGN candidates through a different lens; their verdicts are in out/part2/_work/AMGN/skeptic_decider_r1.json. Read that file in full, then read their arguments AGAINST THE CITED PAGES (open them with get_page). Concede what they got right, hold what you still believe with a reason, and narrow your claim if it was too broad. The key clash: you named m01 (TAVNEOS trial) the strongest survivor once restated as option value; they say the FDA's proposal alleges untrue statements in the original application so a new trial cannot cure it, and the only precedent (LUMAKRAS) shows the FDA imposing studies rather than bargaining, so they narrow m01 to a $10M to $15M gated hearing-record offer and prefer m04 narrowed to a $30M to $50M prior-authorization pilot with one or two PBMs. Give the inside-24-month math for both narrowed versions (the gated m01 offer and the m04 pilot) and say which has the better cost-of-capital case. Write out/part2/_work/AMGN/skeptic_cfo_r2.json in the brief's shape with round2 {conceded, held, narrowed} filled per verdict and an overall naming the unresolved disagreements. From Python, run the grep and em-dash checks. Report what you conceded, held, and what remains unresolved.
```

## P2 decider/compliance skeptic round 2 resume (AMGN)

SendMessage to a running agent (resume) at 2026-10-18T05:23:23 UTC

```
Round 2. The CFO/math skeptic reviewed the same four AMGN candidates through a different lens; their verdicts are in out/part2/_work/AMGN/skeptic_cfo_r1.json. Read that file in full, then read their arguments AGAINST THE CITED PAGES (open them with get_page). Concede what they got right, hold what you still believe with a reason, and narrow your claim if it was too broad. The key clash: they name m01 the strongest survivor as option value protecting the $2.3B U.S. TAVNEOS intangible (operands well sourced, about 1 percent of R&D, patent to 2034), corrected to the Q1 plus Q2 run-rate and the 80.5 percent non-GAAP margin, with the 15-point probability shift unsourced; you narrowed m01 to a cheap gated hearing-record offer and prefer the m04 prior-authorization pilot. State whether the FDA, as decider, gives the gated offer any chance (what page supports or refutes it), and whether your m04 pilot survives their unit correction (rebate points apply to gross sales, so the cost is about $423.9M gross for 5 points and the net return is $103.3M at best). Also confirm or correct their non-GAAP margin cite. Write out/part2/_work/AMGN/skeptic_decider_r2.json in the brief's shape with round2 {conceded, held, narrowed} filled per verdict and an overall naming the unresolved disagreements. From Python, run the grep and em-dash checks. Report what you conceded, held, and what remains unresolved.
```

## P2 PFE synthesizer: data wave correction

SendMessage to a running agent (resume) at 2026-10-18T05:24:37 UTC

```
Correction and inventory: the full list of what the db7f01f data wave indexed is in out/part2/_work/data_wave_db7f01f.md (read it before citing). Two of the files I named in your brief do NOT exist yet (verified/epi/attr_cm_prevalence_sources.csv and verified/pricing/vyndaqel_net_price_sources.csv are in the scraper's next commit); use what is on disk and keep those items [assumption]. Rules from the watcher: coverage_policy_docs_part2.csv rows are unverified snippets and can never carry a claim; tafamidis has no Section 5 or boxed warning, so the PFE promo piece must present risks from Adverse Reactions (section 6) as prominently as benefits; tafamidis vs Attruby and Amvuttra are none_found pairs, so no comparative claim of any kind; 2029 IRA status is [assumption].
```

## P2 synthesizers: two rubric checks (AMGN/MRK form)

SendMessage to a running agent (resume) at 2026-10-18T05:25:51 UTC

```
Two rubric checks to apply before you finalize. (1) Specific commitment: the case asks for "a specific budget or commitment of people behind it". State the committed resource as one number in the move sentence and budget block: the cost and headcount of the diagnosis team ($7.5M, 15 people as the skeptics sized it, or whatever the pages support), who owns it (name the role, e.g. CFO and head of manufacturing) and when it decides (a month). The $0 to $1.0B release goes on the return side as scenarios with the math and the scenario weights shown and marked [assumption] where they are. (2) Tie to Part 1: MRK's sealed Sharpest Needle is finding 1, the IRS transition-tax NOPAs of about $1.56B. Since the move is built on finding 2 (the $5.9B long-dated inventory), the case_for must say in one gated sentence why the Sharpest Needle does not drive the CEO move (the skeptics killed m05 as not incremental, multi-year and a reserve release), and show how the move's cash plan accounts for the IRS exposure (released cash vs the potential cash tax and interest, cited to the 10-Q and 10-K pages Part 1 used). Put that in drivers[] (finding 1 with a "why" explaining the non-driver role, finding 2 as the driver) and in case_for.net.
```

## P2 PFE synthesizer: two rubric checks (PFE form)

SendMessage to a running agent (resume) at 2026-10-18T05:26:01 UTC

```
Two rubric checks to apply before you finalize. (1) Specific commitment: $50M in two $25M tranches with control sites is fine, but the move sentence must carry one committed number and the people or team behind it, who owns it and when the tranche decision is made (month). Make sure the return math is cited all the way to the dollar (verified 2024 CMS row, Q2 2026 Vyndaqel family revenue page, deduction rate from Part 1 finding 4), with every assumption marked. (2) Tie to Part 1: PFE's sealed Sharpest Needle is finding 1 (U.S. ATTR-CM class growth going to rivals while U.S. Vyndaqel is flat); the move must trace to it explicitly in drivers[] and case_for, and say in one gated sentence how the move answers that finding (growing the diagnosed pool where Pfizer still captures starts, with the leakage to Attruby and Amvuttra priced in as an assumption).
```

## P2 synthesizers: number anchors shortcut

SendMessage to a running agent (resume) at 2026-10-18T05:31:07 UTC

```
Shortcut for citing filing numbers: the scraper's audit file gap-data data/moat/verified/filings/part2_number_anchors.csv (325 rows, 306 verified with verify_quote) has doc_id, page_no, citation, url and verified text for MRK Keytruda U.S., international and total by quarter 2024 to 2026Q2, Keytruda Qlex, the patent table, the IRS NOPAs in the 10-K FY2025 (the approximately $1.3 billion transition tax at MRK:10k_FY2025.md#p131) and every 10-Q, inventory and non-current inventory, totals, guidance. Read the CSV directly and reuse its doc_id and page_no for your cites (still run verify_quote yourself on each quote you use). Also: the citable Part B rows are in verified/rx/cms_spend_part2.csv, not tables/partd_by_year.csv.
```

## P2 MRK synthesizer: fills note

SendMessage to a running agent (resume) at 2026-10-18T05:31:53 UTC

```
MRK fills from the scraper are on disk at gap-data data/moat/verified/filings/part2_fills_MRK.csv (138 rows; 71 verified against the index, 60 pending_index for new docs you can only cite after get_page finds them, otherwise [assumption]). Useful for the chosen move: the inventory-not-expected-to-be-sold-within-one-year series with page anchors ($2.4B FY2022, $2.6B FY2023, $3.8B FY2024, $5.5B FY2025, $5.8B 2026Q1, $5.9B 2026Q2, quarterly rows from 2024Q1, and a launch-preparation inventory row per period naming MK-3475A subcutaneous pembrolizumab in 2025Q2), five grade A transcript rows on reserves and the CDC stockpile; a Keytruda-specific long-dated amount is not public (so the pool split stays undisclosed, which supports the diagnose-first framing). For the IRS tie-in: transition-tax notices about $1.3B tax plus about $260M penalties for 2017 and 2018, received April 2025, contested, 14 rows across 10-K FY2025 (p65, p131) and the 10-Qs 2025Q1 to 2026Q2; IRS large corporate underpayment rate 9 percent in every 2025 quarter (doc policy:policy/irs_interest_rates_2026.md, pending_index). For rejected alternatives: Halozyme 10-K FY2025 (HALO:peers/HALO/10k_FY2025.md, pending_index) with the Merck MDASE suit p38 and p53 and ENHANZE royalty "on average mid-single digit percent" p95; SC conversion comps (Phesgo 55 percent 2026Q1 from Roche docs, Opdivo Qvantig over 10 percent U.S. conversion, BMY 2026Q1 grade B). Use the verified rows freely; pending_index rows only if get_page returns the page.
```

## P2 AMGN refresh: task

SendMessage to a running agent (resume) at 2026-10-18T05:39:54 UTC

```
Targeted refresh, not a rewrite. The scraper's AMGN fills are now indexed and citable (data-moat d92e501; index on disk in the gap-data worktree is current): data/moat/verified/filings/part2_fills_AMGN.csv (235 rows, same columns as the MRK fills file). Replace [assumption] items in out/part2/AMGN with cited facts where a row or page now supports them, keep everything else as is, re-gate every block you touch, and keep the two post-synthesis edits already in the files (the move names "the head of R&D", not a person; the driver why says "the sealed Sharpest Needle from the findings pass"). Specifically: (1) FDA precedents: docs policy:policy/fda_makena_proposal_hearing_2022.md, fda_makena_final_decision_2023.md, fda_pepaxto_proposal_2023.md, fda_pepaxto_final_decision_2024.md, fda_avastin_breast_proposal_2011.md, fda_avastin_breast_final_decision_2012.md, fda_ukoniq_withdrawal_2022.md, fda_truseltiq_withdrawal_2024.md, fda_blenrep_license_revocation_2023.md, fda_leqembi_conversion_2023.md, fda_exondys51_approval_letter_2016.md, plus fda_tavneos_approval_letter_2021.md (PMR 4155-1 five-year RCT and 4155-2 required, 4155-3 a commitment) and fda_tavneos_proposal_to_withdraw_2026.md (14 pages, the dated withdrawal steps as filed, drug stays on the market during the process). Use these to rewrite evidence.lands_because, can_tell and cannot_tell with page cites: what the record shows about hearings granted or denied, whether a sponsor's new-trial offer ever changed the outcome, and the existing PMR trial status; this is the central unresolved question, so cite both sides. If no precedent shows acceptance in lieu of withdrawal, say so with the pages. (2) Trial cost: ASPE 2014 and Sertkaya 2024 immunomodulation rows by facts locator (no vasculitis category exists); replace the $150,000 per patient [assumption] with the cited per-patient or per-trial figure if one applies, else keep the assumption and cite the nearest row as the reference. ADVOCATE N=330 per label Section 14, 331 per Amgen 10-K; cite whichever you use. (3) Cost of capital: replace the bare 8 percent [assumption] hurdle with Amgen's cited effective rates (6.3, 5.6 and 5.2 percent on the 2048, 2051 and 2053 notes, 10-K FY2025 p140 to p141; interest expense net FY2025 p77 and p150) as the floor, keeping 8 percent as the [assumption] hurdle above it. (4) Month 12 as the earliest withdrawal effect: check the dated steps in fda_tavneos_proposal_to_withdraw_2026.md and cite the timeline instead of assuming if it supports a date. (5) For the rejected m02 and m04 text nothing changes. For m03 in the trace, the profit-share buyout comps now exist in deal_comps.csv (Regeneron and Sanofi Praluent 2020, Gilead and Galapagos filgotinib, AbbVie and Boehringer risankizumab) and UCB docs (UCB:peers/UCB/annual_report_2025.md p184: Evenity Europe net sales EUR 137M FY2025; Amgen collaboration net earnings contribution EUR 632M FY2025); add one gated sentence to the m03 trace reason or unresolved entry only if it changes the ruling, otherwise leave it. Rerun all checks (json load, decimal grep, em-dash count, no digits in rejected move or driver why, every block passed or no_numbers, full evidence objects on every cite), rebuild part2.md and trace.jsonl from the same build, and report what moved from assumption to cited, with the page for each.
```

## P2 AMGN refresh: watcher constraint

SendMessage to a running agent (resume) at 2026-10-18T05:40:15 UTC

```
One constraint on the refresh from the watcher: keep the move sentence, the rulings, the rejected alternatives and the kill signals unchanged. Only (a) turn assumptions into cited figures where a page now supports the same number, (b) rewrite the evidence section (lands_because, can_tell, cannot_tell) with the FDA precedent pages, and (c) update unresolved[] if a precedent settles or sharpens a position. If any existing published number FAILS against its new primary source (for example the per-patient trial cost or a note rate differs from what the page says), do not change it: stop, write the discrepancy to out/part2/_work/AMGN/refresh_discrepancies.md, and report it to me before editing that figure.
```

## P2 AMGN refresh: rulings applied

SendMessage to a running agent (resume) at 2026-10-18T05:45:23 UTC

```
Rulings on your three discrepancies. (1) APPLY: swap the $150,000 per-patient [assumption] for the cited Sertkaya 2024 immunomodulation Phase 3 figure of $54,909 per patient, stating it is in 2018 dollars, that no vasculitis category exists so this is the nearest benchmark, and (unless a cited inflation index exists in the store, do not adjust) one sentence that the 2018 basis understates today's cost. Recompute through the gate: the conditional program (about $43.2M with the $25M registry [assumption]), the conditional release (about $30.7M), and the full-program break-even (about 10.4 points). The committed $12.5M offer, its people, and its 3.0-point break-even stay as they are. (2) HOLD: month 12 stays [assumption] with the precedent range in can_tell. (3) APPLY: reword the move sentence so the offer is to "fully fund and independently adjudicate the FDA-required five-year randomized trial (PMR 4155-1)" plus the U.S. liver-safety registry, citing the 2021 approval letter (p.3 to p.5) and the CDER notice p.8 (21 of 300 enrolled) in the move's cites; budget, people, owner, gating and decision timing unchanged. Carry the same wording into case_for and kill signals wherever the trial is described, and confirm cannot_tell still carries the "precedents cut against the move" point. Rebuild part2.json, part2.md and trace.jsonl from the same build, re-gate every touched block, rerun all checks (json load, decimal grep, em-dash count, no digits in rejected move or driver why, every block passed or no_numbers, full evidence objects), and report the changed figures with their pages.
```

