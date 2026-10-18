# Blind reader brief (Phase A, company selection)

You are one of ten readers. Each reads one company, cold, from primary sources only. Your output is the raw
material for a blind company selection. Nothing you write may lean on prior runs.

## Hard rules

1. READ ONLY these: the case PDF (docs/case/fine_print_case.pdf), the rubric (docs/case/judging_rubric.pdf),
   the citation index through `agent/moat/cite.py`, and the verified tables under data/moat/verified/ and
   data/moat/tables/. All paths are in the gap-data worktree:
   /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data
2. DO NOT open, grep, or list: any out/ directory, any file named league_v*, findings_v*, findings.jsonl,
   docs/nuggets, docs/red_team*, docs/needle*, docs/quant_model.md, docs/parker_handoff.md, HANDOFF*,
   docs/agent-chat.md, docs/kickoff*, docs/game_plan.md, docs/materialit*, docs/research, ~/reports,
   ~/research_notes, GitHub issues, or any other worktree. If a search result points at a "notes", "memo",
   "note", "report" or "verified_table_prior" doc_type, skip it: those are derived, not primary.
3. Use the index from the gap-data worktree with this interpreter:
   /private/tmp/claude-501/-Users-aidanjones/e8d819f0-5924-4fae-a529-36fd52188c9e/scratchpad/venv/bin/python
   `cd <gap-data> && <python> -m agent.moat.cite "<query>" --ticker <T> [--doc-type annual_report] [--facts] [-k 20]`
   or in Python: `from agent.moat.cite import search_pages, search_facts, get_page, cite, verify_quote`.
   `get_page(doc_id, page_no)` returns the page text; `cite(doc_id, page_no)` returns (label, url);
   `verify_quote(quote, doc_id, page_no)` checks a quote is on the page. Transcripts carry a quote_grade:
   use only grade A or B transcripts for speaker quotes (official or graded), and never copy text from a page
   whose license is 'bloomberg_licensed' into your output (cite it by label and url only).
4. Every number you write must come from a page or fact row you cite, or be arithmetic on cited numbers
   with the operands shown. No numbers from memory. No API key exists; you are the reasoner.
5. Write to disk as you go. Append each candidate to your output file as soon as it is evidenced.

## The case's test (from the case PDF, read it yourself first)

The points go to findings that are material enough to change an investor's view AND not obvious: not the
starter thread, not a patent cliff or exclusivity loss (those are public and priced in), not something a
press-release skim would catch, not something already said plainly on a call.

Sources the case names: the two latest annual reports, the last four earnings calls, the latest 10-Q,
rival makers' annual report and call statements, current product labels, the Orange or Purple Book, and the
10-K patent table.

Walk every one of these eight hiding places for your company. Use the category strings exactly:

1. "Language drift": wording about risks, results, or guidance that changed between the two latest annual
   reports, especially in Risk Factors and MD&A. Diff the two years; quote both versions.
2. "Gross-to-net": a widening gap between list price and net price.
3. "Inventory and receivables growing faster than revenue": softening demand, pre-launch stocking, or
   channel stuffing. Compute the growth rates from cited balance sheet and revenue lines.
4. "Segment and product table changes": past numbers revised or reclassified, products quietly no longer
   broken out.
5. "Footnotes": litigation reserves, partner royalty splits, payments owed on past acquisitions, tax-rate
   changes.
6. "Earnings-call Q&A": deflected questions, new phrases, metrics the company stopped reporting.
7. "Product fine print": label details that widen or narrow a product's market vs its listed rivals
   (approved uses, boxed warnings, required safety programs, dosing).
8. "Peer contrast": something the company or product does differently (pricing, geography, manufacturing
   footprint, label breadth, exposure to IRA negotiation, MFN pricing, tariffs) that the market has not
   priced in. Unequal exposure across the shortlist counts.

For each category, record at least one search you ran even if it yielded nothing (a "no finding" record
with the documents you checked). Aim for 4 to 8 real candidates per company. A thin company is a valid
result; do not pad.

## Output contract

Write JSON lines to: <quant-model>/out/part1/_blind/<T>/candidates.jsonl
where <quant-model> = /Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/quant-model

First line, a header:
{"kind":"header","ticker":"T","company":"name","reader_started":"ISO","sources_available":{"annual_reports":[doc_ids],"transcripts":[doc_ids with grade],"quarterly":[doc_ids],"labels":[doc_ids]}}

One line per candidate or no-finding:
{"kind":"candidate"|"no_finding",
 "id":"T-c01",
 "category":"<one of the eight exact strings>",
 "query":"the search(es) you ran",
 "documents":[{"doc_id":"...","doc_title":"<label from cite()>","page":N,"url":"..."}],
 "candidate":"one plain English sentence",
 "evidence":[{"doc_id":"...","page":N,"quote":"verbatim span, verified with verify_quote","label":"...","url":"...","quote_grade":"A|B|null","speaker":"name or null"}],
 "impact":{"metric":"revenue|operating income|EPS","direction":"up|down","math":"show operands with [doc_id p.N] after each","estimate":"text"},
 "peer":"how the same item looks at another shortlist company or a rival's maker, with its citation",
 "not_obvious_because":"why this is not the starter thread, a patent cliff, or already said on a call; name the call pages you checked",
 "confidence":"high|medium|low",
 "confidence_reason":"..."}

Last line:
{"kind":"product","ticker":"T","product":"<one product from the company's competitive set in the case>","rivals":[...from the case...],"why_this_product":"...","label_docs":[doc_ids],"fine_print_edge":"one sentence on where the label differs from rivals, cited"}

Then write a short <quant-model>/out/part1/_blind/<T>/reader_summary.md: the company in five lines, the
three strongest candidates, and what you could not find in the index (data gaps, with the queries you tried).
