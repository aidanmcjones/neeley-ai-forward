# Devpost submission text (company-neutral draft)

**No company has been picked.** [COMPANY] and [NEEDLE] slots stay open until the team decides.
Submit by Sun Oct 18, 1:00 pm (our target; the Devpost deadline is 2:00 pm CDT per docs/kickoff_summary.md).

Fields we know of (docs/kickoff_summary.md line 36): project name (60 characters), elevator pitch (200 characters),
thumbnail (JPG, PNG or GIF, 5 MB, 3:2), "About the project" in Markdown, image gallery, video demo link, contribution
by each member, Terms checkbox. Video length: not stated (kickoff_summary line 37). The Devpost overview asks the
video to introduce the team, name the track and case, explain problem and solution, demo the project and its AI use,
and cover impact plus limitations or next steps (docs/game_plan.md). Our existing Devpost draft is titled "Advanced
Pharmaceuticals"; rename it.

---

## Project name (60 max)

NEEDLE: Page-Verified Fine Print for Pharma

## Elevator pitch (200 max)

AI reads a drugmaker's filings, earnings calls and drug labels. Code checks every quote against its page. Analysts
get material, cited findings, plus a log of every time the AI was wrong.

## About the project

### Inspiration

The case told us that Wall Street reads the headline and the story is buried in the footnotes. It also warned that
"a model working from memory will get numbers and quotes wrong." We wanted a tool that uses AI to find what is buried,
then refuses to trust the AI until code has checked every quote against the page it came from.

### What it does

- Loads a drugmaker's 10-K, 10-Q, earnings calls and FDA labels into page-marked text from public sources (SEC
  EDGAR, FDA, Orange and Purple Book, CMS).
- An AI reader proposes findings in footnotes, risk language and call Q&A, each with exact quotes and dollar math.
- Code checks every quote against its cited page. Anything it cannot confirm goes to a person ("needs_human").
- Builds the case's findings table: finding, source with page, impact math, peer comparison, confidence.
- Compares a product with its rivals on approved uses, boxed warnings, dosing, patents and pricing.
- Logs every time the AI was confidently wrong, so the analyst sees what was caught.
- For [COMPANY], our Sharpest Needle: [NEEDLE in one sentence with its dollar figure and source page].
- Part 2: [MOVE, budget, kill signals] ([PLACEHOLDER: docs/fanout/part2/]).

### How we built it

- Python pipeline: collectors for SEC filings, XBRL financial data, FDA labels, Orange and Purple Book, and CMS
  Medicare data.
- Claude (claude-opus-5-5) through one cached wrapper (agent/llm.py) for reading and drafting.
- A page checker (`agent.needle.pages.check`) that matches every quote to its cited page, exactly or closely.
- AI skeptic agents that attacked our methods at three review gates, and a red-team agent that scored us against the
  rubric.
- A hash-chained audit log for every signal, verdict and prediction.
- A Streamlit app with five tabs: League table, Findings, Product fine print, AI caught, Proof.
- One command onboards a new company: `python -m agent.needle.onboard <TICKER>`.

### Challenges we ran into

- Our first backtest looked strong: a 59% vs 43% hit rate. Two AI skeptics showed the test windows overlapped
  data that was already known. After the fixes, no forensic signal significantly predicts a revenue drop or
  impairment (1,410 firm-quarters, 43 companies). We show the honest version.
- Our code once flagged a company's receivables as a red flag. The footnote showed it was factoring, and without it
  receivables fell 0.8%. Code ratios are now flags for a reader, never findings on their own.
- Third-party transcript sites mix AI-written summaries into the page. We reject those lines.
- Our code's patent and exclusivity dates were wrong for some products, so we use the 10-K patent tables.

### Accomplishments that we're proud of

- 238 of 238 evidence quotes across four deep-read companies pass the page check (red-team re-run).
- 43 confident AI errors caught and logged across those four companies, plus 9 errors in our own tool, each now
  covered by a test.
- Seven Q3 2026 forecasts sealed with a hash before the results came out.
- A revenue forecaster whose 80% range covered 79.4% of 1,793 past firm-quarters.

### What we learned

- AI is good at reading and bad at remembering. Make it quote, then check the quote.
- Choose the company on findings a person has read; use code ratios only as support.
- Let skeptics attack your best result first.

### What's next for NEEDLE

- Time a manual analyst read against a NEEDLE run, so the time saving is measured: [TBD].
- Fetch call transcripts automatically.
- Fill every peer comparison and run all ten shortlist companies with human review.
- Pilot with one analyst team, tracking hours per company.

### Pre-existing resources and AI disclosure

Restated from DISCLOSURE.md:

- Built before the competition (before Fri Oct 16, 2026): the repository scaffold, meaning the folder layout,
  agent/llm.py (a generic Claude API wrapper with caching), a placeholder Streamlit page, an empty eval harness and
  planning documents.
- 10-K text collection started Fri Oct 16 at about 3:37 pm CT, after the pharma case teaser on the kickoff call. It
  began in one of Aidan's existing data projects and was rewritten Friday evening as the standalone collector
  agent/tenk.py in this repo. All filing data comes from public SEC EDGAR.
- Everything case-specific (data handling, prompts, analysis, UI, financial model, deck) was built during the
  competition; see the commit history.
- AI tools: Claude (Anthropic API, model claude-opus-5-5) inside the product; Claude Code for development.
- Open-source libraries: anthropic, streamlit, pandas, python-dotenv. [FLAG: requirements.txt also lists requests,
  boto3, pypdf, lxml and openpyxl, and docs/how_we_did_it.md names pytest, Bloomberg transcripts and WRDS IBES.
  Update DISCLOSURE.md first, then this section, so the two match.]

## Built with

python, claude, anthropic-api, claude-code, streamlit, pandas, sec-edgar, xbrl, openfda

## Try it

- Repo: [LINK: confirm; README.md shows github.com/aidanmcjones/neeley-ai-forward]
- Video: [LINK]
- Run locally: `pip install -r requirements.txt`, then `streamlit run app/main.py`

## Contributions

- Aidan Jones: [TBD]
- Parker Kingsbury: [TBD]
