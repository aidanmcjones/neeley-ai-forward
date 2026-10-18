# Parker: Claude Code skills and hackathon handoff

Written Friday night, Oct 16, 2026. Aidan is offline until Saturday. You get the full case at 9:00 am in Neeley 2303AB; this file is everything built so far, where it lives, and the skills you can use to move fast.

## 1. Setup (10 minutes)

1. Install Claude Code and sign in: https://docs.claude.com/en/docs/claude-code/setup
2. Clone the repo (you already have access as `frogman826`):
   `git clone https://github.com/aidanmcjones/neeley-ai-forward.git`
   Tonight's work is on branch `gap-data` (draft PR #2, stacked on PR #1 `scaffold`). Check it out: `git checkout gap-data`.
3. Install the skills: unzip the attached `claude-skills-for-parker.zip` into your Claude folder so each skill has its own folder with a `SKILL.md` inside:
   - Windows: `C:\Users\<you>\.claude\skills\orchestrator\SKILL.md` (same for the others)
   - Mac: `~/.claude/skills/orchestrator/SKILL.md`
   Restart Claude Code. Type `/` and the skill names show up.
4. Data access: the data lives in the Cloudflare R2 bucket `neeley-ai-forward`. You get full read and write. Aidan will text you the keys (never by email). Make a file named `.env` at the repo root (it is gitignored; never commit it) with:
   ```
   SEC_USER_AGENT=Neeley AI Forward <your email>
   R2_ACCOUNT_ID=<from Aidan>
   R2_ACCESS_KEY_ID=<from Aidan>
   R2_SECRET_ACCESS_KEY=<from Aidan>
   R2_BUCKET=neeley-ai-forward
   ANTHROPIC_API_KEY=<optional, needed to extract 10-K dates for a new company>
   ```
   Then `pip install -r requirements.txt lxml openpyxl` and every `python -m agent....` command reads and writes R2. Until the keys arrive, the two CSVs attached to this email are enough to start the money math.
5. Agent chat: your Claude and Aidan's Claude can message each other through the repo (`scripts/agent-chat`, GitHub issues labeled `agent-chat`; run `gh auth login` once). When you open Claude Code in the repo, it sees unread messages automatically. A kickoff thread is waiting: https://github.com/aidanmcjones/neeley-ai-forward/issues/3. Tell your Claude "read the agent-chat inbox and reply"; on Windows it runs `python scripts/agent-chat inbox`. Protocol: `docs/agent-chat.md`.

## 2. How skills work

A skill is a saved playbook Claude follows. Two ways to use one:

- **Name it:** type `/orchestrator build X` (slash + skill name + what you want).
- **Describe the job:** Claude picks the skill whose description matches ("fan this out", "are you sure, verify this").

Skills spend more tokens because they run several agents. Use them for big or high-stakes work, not one-line questions.

## 3. Aidan's skills

### orchestrator
- **What it does:** turns Claude into a project manager. The main chat only plans, splits the work into tasks, launches worker agents in parallel, tracks them, and merges their results. It never does the grunt work itself, so it stays sharp on long jobs.
- **Use it when:** a job has 3 or more pieces that can run at once. Tonight it built the drug table, the 10-K exclusivity extraction and the decline curves in parallel in about 20 minutes.
- **Example for Saturday:** `/orchestrator once the case names the three companies: pull their 10-Ks, run the product table for those tickers, and draft the revenue-at-risk numbers per drug`

### parallel-dispatch
- **What it does:** a lighter version of the orchestrator: one agent per independent item (one per company, one per drug, one per source), then it merges the answers.
- **Use it when:** the same task repeats across a list. Example: "for each of the three companies, summarize what their 10-K says about their biggest LOE risk, with quotes."
- **Example:** `/parallel-dispatch for BMY, PFE and JNJ, pull the top 3 risks from each 10-K Item 1A and quote them`

### adversarial-review
- **What it does:** a fact checker built from disagreement. Two skeptic agents with different angles attack a claim, read each other's arguments, then a third agent writes the verdict: what survived, what was conceded, what is still disputed.
- **Use it when:** before anything goes in front of judges. Run it on the CEO memo, the revenue-at-risk math and any number on a slide. Judges will ask "how do you know?"; this is how we know.
- **Example:** `/adversarial-review check every number and claim in the CEO memo against the source files, and flag anything not cited`

### session-tracker
- **What it does:** a live status bar at the bottom of the terminal: model, how full the context window is, tokens and dollars spent, how many agents are running, and a progress bar for the current task.
- **Use it when:** long sessions, so you can see cost and when the context is close to full (start a fresh chat before it hits red).
- **Windows note:** the scripts are bash. Run Claude Code inside WSL or Git Bash for the status bar; the other skills work anywhere.
- **Example:** `/session-tracker install the tracker`

### scrape-god
- Aidan's skill for his work data platform. Not useful for the hackathon; skip it. Not included in the zip.

### Built-in skills worth knowing (already in Claude, no install)
- `/anthropic-skills:deep-research`: multi-source research with a cited report. Good for "what do analysts say about Eliquis's 2028 cliff?"
- `/anthropic-skills:pptx`: builds or edits a PowerPoint deck. Use for the pitch deck.
- `/anthropic-skills:xlsx`: builds a spreadsheet with formulas. Use for the revenue-at-risk model.
- `/anthropic-skills:docx`: Word documents, if the CEO memo needs to be a .docx.

## 4. The case, as decoded from kickoff

- **What it is:** loss-of-exclusivity (LOE) competitive intelligence. Compare a company's drug (product A) to companies B and C on two things: when exclusivity ends and when pricing changes. Then give the CEO a cited stance: defend, attack, reprice, or partner/buy.
- **Sponsor:** a pharma company tied to an AI Forward board member. Best guess McKesson (about 60%), then Alcon (about 25%), then a branded drug maker. We built everything to work for any company.
- **Our edge:** live public data (FDA, Medicare, SEC) beyond what is in the case, every claim cited, and a dollar number most teams will not have.
- **The 2026 pricing story most teams will miss:** Medicare drug price negotiation. Eliquis is $231 per 30 days in 2026 ($237.25 in 2027). Entresto, Stelara, Xarelto and NovoLog leave negotiation on 12/31/2026 because generics or biosimilars arrived.

## 5. What we built tonight and where it lives

Plan doc (everything, kept current): https://claude.ai/code/artifact/d14b13ab-bf52-46f8-96e2-07b43ca4de73
UI options (pick one Saturday): https://claude.ai/artifact/ESySwBVnAfDxN5x8yjn9TE (Aidan may need to share these links with you from the page's Share menu)

| Piece | What it is | Where |
|---|---|---|
| 10-K collector | Pulls any company's annual reports and indexes sections | `agent/tenk.py` |
| Public data | FDA Orange Book, Purple Book, generic patent challenges, Medicare negotiation, Part D/B spending, NADAC prices, first generics, formulary | R2 `public/`, `formulary/`; code `agent/public_data.py`, `agent/gap_data.py` |
| Annual reports | 96 10-Ks (2020 to 2026) for 14 candidates | R2 `tenk/` |
| Product revenue | Every drug's yearly sales from those 10-Ks (Keytruda 2025: $31.6B) | R2 `xbrl_product/` |
| Company-stated exclusivity | 159 dates with exact 10-K quotes (Eliquis: generics April 1, 2028 per Pfizer) | R2 `derived/company_stated_loe.jsonl`; code `agent/stated_loe.py` |
| Decline curves | How fast sales fall after LOE, from 18 real cases | R2 `derived/loe_curves.csv`; code `agent/loe_curves.py`; attached CSV |
| Per-drug table | One row per drug: revenue, FDA vs company LOE, Medicare price, generic filers, competitors, pipeline, revenue at risk, all cited | R2 `derived/product_table/`; code `agent/product_table.py`; attached BMS/Pfizer/J&J CSV |
| Pipeline | 2,366 Phase 2/3 trials for the drug makers | R2 `trials/` |
| 8-Ks | 723 earnings and event filings since 2020 | R2 `8k/` |
| Data map | Every source, join key and pitfall | `docs/research/pharma_data_map.md`, `docs/research/product_table.md` |

### The decline curves (your main input)

Median sales as a % of the pre-LOE peak:

| Year after LOE | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Biologic (4 drugs) | 79% | 72% | 34% | 38% | 24% |
| Small molecule (14 drugs) | 65% | 16% | 17% | 12% | 8% |

Humira US: $18.62B (2022), then $12.16B, $7.14B, $3.06B. Revenue at risk = drug's sales x (1 - curve %) for each year after its LOE date. Example: a $10B small-molecule drug losing exclusivity in 2028 loses about $3.5B in 2028 and $8.4B a year after. Biologic years 3 and 4 rest on one drug, so call them indicative.

### Known issues (do not get caught by these)

- Xarelto's LOE shows March 2025 in the table; that is wrong (it is the first generic of one strength only). Fix by hand.
- AbbVie and J&J give few product dates in their 10-Ks; Humira (2023) and Stelara (2025) come from verified quotes in the curve file.
- Eliquis appears twice (BMS sales and Pfizer alliance revenue). Do not add them together.
- If the sponsor is McKesson, there is no public drug-by-drug data for a distributor; the "distributor impact" view is an estimate. If it is Alcon, its products are mostly devices, which the FDA drug data does not cover.

## 6. What to do Saturday

1. **9:00 am, Neeley 2303AB:** read the full case. Score it against the plan doc's case scorecard.
2. **By 10:00:** text Aidan the sponsor, the three companies and the drugs named. That is the only input the engine needs.
3. **If the companies are in our 14** (McKesson, Cencora, Cardinal, Alcon, Bausch + Lomb, AbbVie, Merck, BMS, Pfizer, Lilly, J&J, Regeneron, Amgen, Gilead): the table runs in a minute: `python -m agent.product_table --tickers X,Y,Z`. If not, `python -m agent.tenk --tickers X` pulls their 10-Ks first (about 5 minutes). Needs the R2 token.
4. **Your piece, the money:** build the revenue-at-risk model in a spreadsheet from the decline-curve CSV and each drug's sales and LOE date. Then the stance: which of defend, attack, reprice, partner wins for the CEO, in dollars.
5. **Validate one assumption** with our mentor or the sponsoring board member and get a quote for the video.
6. **Aidan arrives about 1 pm:** pick the UI option together (recommendation: B, the analyst cockpit) and build the demo on the table.
7. **Before anything is shown:** run `/adversarial-review` on the memo and the numbers.

Judging is live at our table Sunday 2 to 4 pm. Business problem first, tech second: a working demo plus a dollar number.
