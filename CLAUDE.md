# Rules for every Claude Code session

Project: Neeley AI Forward hackathon, Advanced track, pharmaceutical case. Team: Aidan Jones (AI build) and Parker Kingsbury (finance, business case).

- Read PLAN.md and HANDOFF.md first. Do one task per prompt. Stop and report when done.
- Only edit files in the folder named in the task. Never touch another owner's folder.
- The golden path in demo_script.md must still run after every change. Run it before committing.
- Never put API keys in code or commit .env. Read keys from environment variables or Streamlit secrets.
- All Claude calls go through agent/llm.py. Model is claude-opus-5-5. Do not add other providers.
- Cache LLM responses for the demo inputs (agent/cache/) so the demo never waits on the API.
- Every AI output shown to the user must cite its source document or row.
- Prefer one LLM call over a chain. No new frameworks without asking.
- Commit small with clear messages. Update HANDOFF.md at the end of every task.
- Never use em dashes in any text, slide, or write-up.

## Folder owners

| Folder | Owner |
|---|---|
| app/, agent/, eval/ | Aidan (Parker drives in the morning) |
| data/, docs/, deck/ | Parker |
| PLAN.md, demo_script.md, qa.md | Shared |
