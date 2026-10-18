# Pre-existing resources (disclosed per competition rules)

Built before the competition started (Fri Oct 16, 2026):

- This repository scaffold: folder layout, agent/llm.py (a generic Claude API wrapper with caching), a placeholder Streamlit page, an empty eval harness, and planning documents.

Built during the competition, after the case was described on the Friday kickoff call (Fri Oct 16, 3:00 pm CT):

- 10-K text collection: started Fri Oct 16 at about 3:37 pm CT, right after the pharma case teaser, first in one of Aidan's existing data projects, then rewritten as the standalone collector agent/tenk.py in this repo Friday evening. All filing data comes from public SEC EDGAR.

Everything case-specific (data handling, prompts, analysis, UI, financial model, deck) is built during the competition; see the commit history.

AI tools used: Claude (Anthropic API, model claude-opus-5-5) inside the product; Claude Code for development.

Open-source libraries: anthropic, streamlit, pandas, python-dotenv.
