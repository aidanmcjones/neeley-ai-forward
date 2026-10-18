---
name: fanout-worker
description: Standard brief for a hackathon worker subagent (project context, deadlines, repo and write rules, scratch space, final report shape). Load it first when you were spawned as a worker; orchestrators reference it instead of pasting the preamble into every prompt.
---

# Worker brief

## Project
Neeley AI Forward hackathon, Advanced track, pharma case "The Fine Print". Team: Aidan Jones (AI build, GitHub aidanmcjones) and Parker Kingsbury (finance, frogman826). The judges include McKesson people, finance faculty, a Gartner analyst, a PwC Responsible AI lead and a bank CISO. Feature freeze Sun 10:30 am; submit on Devpost Sun 1:00 pm (deadline 2:00 pm). Case: `docs/case/fine_print_case.pdf`. Rubric: `docs/case/judging_rubric.pdf`.

## Repo
- `neeley-needle` (branch `needle`) is a git worktree: run commands from its root and never `cd` to another checkout. `neeley-ai-forward` is Aidan's main checkout (branch quant-model work lives in its `.claude/worktrees/quant-model`).
- Bash is Git Bash on Windows. Use `python` (not python3), `python -I` for scripts outside the repo, and `PYTHONIOENCODING=utf-8` when printing corpus text.

## Rules (unless your prompt says otherwise)
- You are a worker: do the work directly, do not spawn agents.
- Write only to the paths your prompt names. Do not edit existing repo files, do not commit, push or run other git write commands.
- Scratch files go in your own subfolder of the scratchpad, `<scratchpad>/<your task or ticker>/`, never its root: parallel workers share it.
- Folder owners: `app/`, `agent/`, `eval/` are Aidan's; `data/`, `docs/`, `deck/` are Parker's. `CLAUDE.md`, `.claude/agents/*`, `.claude/conductor/*` are not yours to change.
- Never use em dashes. Never put secrets in output. Never pass a recommendation off as a decision: only Parker picks the company or changes a slide number.
- For corpus quotes use the `corpus-cite` skill; for collecting documents, `collect-source`; for refuting a claim, `claim-skeptic`.

## Final message
Return everything in your final message (the orchestrator sees nothing else). End with a five-line summary: what you produced and where (paths), counts kept and dropped, the top result, the biggest gap or risk, and the suggested next step.
