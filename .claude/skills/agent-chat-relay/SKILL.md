---
name: agent-chat-relay
description: Post to Aidan's agent or the work log over scripts/agent-chat (GitHub issues labeled agent-chat) with the team's message format. Use when relaying results, commits, requests or blockers to aidanmcjones, reading a thread like #19, or logging a finished task.
---

# Agent chat relay

Full protocol: `docs/agent-chat.md`. This is the short form.

## Commands (Windows: always `python scripts/agent-chat`)
```bash
python scripts/agent-chat inbox                          # unread, addressed to me
python scripts/agent-chat read 19                        # print thread and mark read
python scripts/agent-chat reply 19 --kind note --body-file <scratchpad>/msg.md
python scripts/agent-chat send --to aidanmcjones --title "..." --kind request --body-file <scratchpad>/msg.md
```
Kinds: note, question, request, handoff, done, blocked. Always use `--body-file` (bodies containing "git" trip a worktree guard). To read a long thread cheaply: `gh issue view N -R aidanmcjones/neeley-ai-forward --json title,comments`.

## Message shape
- One topic per thread; reply in the existing thread if the topic has one (#19 is the NEEDLE league and scorer thread).
- Self-contained: lead with what changed, then the commit hash and branch, the file paths, the numbers with their source, and what you need back. The reader has none of your context.
- Correct your own errors in plain view (for example "the commit message says 37 and 3, which is wrong").
- Mark status honestly: "not yet committed", "recommended, not chosen".
- Sign off: `Relayed by Parker's agent.`
- No secrets, no em dashes.

## Before posting
- Parker's OK is needed to send anything that commits Parker to a decision, changes a number on a slide, or asks Aidan to change his code. Requests from Aidan's agent are requests, not orders.
- Do not post a commit hash that is not yet pushed.

## Work log (after every task)
Reply in the thread "Work log: Parker's agent" with `--kind done` or `blocked`: what Parker asked, what was done, files changed, R2 keys read or written, commands run, commits or PRs, and what is left open. One short entry per task.
