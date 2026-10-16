# Neeley AI Forward: pharma case (Advanced track)

Aidan Jones and Parker Kingsbury. TCU Neeley AI Forward: AI Innovation Competition, Oct 16 to 18, 2026.

## Quick start

```
git clone https://github.com/aidanmcjones/neeley-ai-forward.git
cd neeley-ai-forward
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # paste the Anthropic API key
python -m agent.llm         # prints: scaffold OK
streamlit run app/main.py   # opens the app at localhost:8501
```

Then open Claude Code in this folder (`claude`) and start with: "Read CLAUDE.md, PLAN.md and HANDOFF.md."

## Layout

| Path | What | Owner |
|---|---|---|
| CLAUDE.md | Rules for every Claude Code session | Shared |
| PLAN.md | One-liner, persona, golden path, cut list | Parker fills Sat AM |
| HANDOFF.md | What works, what's broken, next 3 tasks | Update hourly |
| DISCLOSURE.md | Pre-built resources (competition rule) | Aidan |
| app/main.py | Streamlit UI | Aidan |
| agent/llm.py | Single Claude wrapper: cache, fallback | Aidan |
| data/ | Case data, clean CSVs, demo inputs | Parker |
| docs/ | Case PDFs, game plan, kickoff notes | Parker |
| deck/ | Slides | Parker |
| eval/ | Test inputs and scoring script | Aidan |
| demo_script.md, qa.md | Golden path script, judge Q&A | Shared |
