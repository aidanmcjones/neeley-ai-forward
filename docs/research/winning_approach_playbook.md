# Winning approach playbook: one-day AI hackathons and business-school AI case competitions

Note on sources: most "how to win" material is self-published guides, practitioner blogs, and a few organizer pages. Actual judging rubrics found: Microsoft AI Agents Hackathon 2025, AI Tinkerers SF and Paris 2025, Cornell Corning case competition. No 2024-2026 interview with a named judge of a big AI hackathon (Anthropic, OpenAI, a16z, Cerebral Valley, AGI House) turned up. Treat claims tagged "guide" as practitioner opinion, not verified rules.

## 1. How winners pick among multiple cases/tracks

### Takeaway
Pick the track where (a) you can show one working end-to-end AI behavior on real or realistic data within half the time, (b) the judges' published rubric and sponsor interests line up, and (c) you can put a number on the business outcome. Read the rubric first: winners differ mostly on things the rubric doesn't spell out.

### Cited Findings
- Hackathons usually post judging criteria on the Devpost page. At some events the winner is decided entirely on those scores, so tailor the build and write-up to them. The official rules often give the weighting and stages in more detail than the summary. ([dev.to Devpost submissions guide](https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0); [Okta dev forum](https://devforum.okta.com/t/what-are-the-judging-criteria-for-the-hackathon/15842))
- Real 2025 rubrics: Microsoft AI Agents Hackathon (April 2025) judged innovation, impact, usability, solution quality and category alignment. Its overall winner, RiskWise, was a supply-chain risk system that orchestrated tools and data sources ([Microsoft AI Agents Hackathon winners](https://microsoft.github.io/AI_Agents_Hackathon/winners/)). AI Tinkerers SF Fullstack Agents (Sept 2025) judged code quality, architecture, observability and practical impact, and required working prototypes with real-world integration ([AI Tinkerers SF](https://sf.aitinkerers.org/p/copilot-kit-b-capital-hackathon)). AI Tinkerers x Anthropic Paris (Feb 2025) scored projects low for a "superficial connection to theme" and high for "clear and meaningful incorporation of AI agent principles" ([AI Tinkerers Paris](https://paris.aitinkerers.org/p/ai-tinkerers-and-anthropic-ai-agents-hackathon-in-paris)).
- OpenAI-style build events use a balanced matrix: technical implementation, design/UX, potential impact, quality of idea. One analyst's framing is that "the weakest variable limits the whole score." ([DEV: What AI hackathon winners have in common](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla))
- A judge who scored events through July 2026 says rubric categories compress most teams into the middle. Winners separate on things the rubric doesn't name: the demo runs, the team says what it is up front, scope fits the time, and the project has a memorable identity. ([Kurbaitaev, What Judges Actually Score](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l))
- Real-world impact can be up to 25% of a hackathon score ([freeCodeCamp checklist](https://www.freecodecamp.org/news/a-simple-checklist-to-help-you-win-or-have-fun-at-hackathons-98030be1a6c8/)). One AI guide puts the four axes (innovation, technical depth, impact, presentation) at about 25% each ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- Case competitions: know whether the judges are faculty, recruiters or industry professionals, and study past cases and winners ([BusinessBecause](https://businessbecause.com/news/mba-degree/5995/3-tips-to-winning-business-school-case-competition); [openskillindex hackathon-attendee guide](https://openskillindex.com/skills/neversight-learn-skills-dev-hackathon-attendee)). Sponsors expect research beyond the packet and expect teams to come back with clarifying questions ([DePaul Kellstadt](https://blogs.depaul.edu/inside-kellstadt/?p=1183)).
- Recent business-school AI cases are sponsor-specific operating problems. SEC MBA Case Competition (Texas A&M, Dell): 24 hours to build a strategy for applying generative AI to Dell's services organization ([Alabama Culverhouse](https://culverhouse.ua.edu/?p=32025)). KeyBank/Ohio State: genAI in commercial banking aimed at deposit growth and customer retention ([UT Haslam](https://haslam.utk.edu/news/uts-haslam-snags-first-ever-keybank-case-competition-first-place-win/); [Ohio State Fisher blog](https://fisher.osu.edu/blogs/gradlife/2024/02/27/my-mba-case-competition-best-presenter-awarded)).

### Inferences
- A track-selection scorecard (score each track 1-5): (1) rubric and sponsor fit; (2) whether data is supplied or easily synthesized, so you aren't blocked; (3) demo-ability, meaning can one screen show the AI doing something a human can't do in that time; (4) whether you can quantify dollars, hours or error rate; (5) whether the AI is necessary, not decorative. Pick the highest total, but treat demo-ability and quantifiable impact as must-pass gates.
- When a sponsor company owns a track, favor it if the team can speak to that sponsor's KPI (as in the Dell and KeyBank cases). Sponsor judges reward work aimed at their real metric.

### Gaps
- No source measured win rates by track type. "Pick the less crowded track" is common folklore, but I found no evidence for it.

## 2. How winners scope

### Takeaway
One sentence, one named user, one golden-path demo that runs end to end on realistic input, and one measurable business outcome. Narrow done well beats ambitious done halfway, across both hackathons and case competitions.

### Cited Findings
- One complete path beats four half-built ones. A narrow project built well "signals good decisions under a constraint." Name specific users ("a regional fighter with 40,000 followers and no manager," not "athletes"). Settle on a one-sentence identity before coding and check scope against it. ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l))
- A named persona beats a broad industry. Judges should see the value within 30 seconds of the opening screen. Build the "golden path" (the exact screens you'll show) and fix bugs on that path only. ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon))
- A problem a judge can follow in one sentence. A demo that works perfectly for one user journey will outscore ten half-working features. ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon); [Reskilll](https://blogs.reskilll.com/?p=136))
- Five-question scorecard: Can a judge explain the project to someone else after one minute? Does the demo show behavior, not slides? Is the AI necessary to the result? Is the target user clear? Are the limits named honestly? ([DEV: AI hackathon winners](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla))
- WorkOS one-day internal Claude hackathon (39 teams): scope to one workflow, because "many features seem urgent but aren't." Projects were tools participants had been frustrated by for months. ([WorkOS](https://workos.com/blog/claude-day-internal-hackathon))
- Case competitions: losing teams offer three options for the client to weigh. Winners commit to one and show why the others fail ([roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)). Too many recommendations dilute the message ([BusinessBecause](https://businessbecause.com/news/mba-degree/5995/3-tips-to-winning-business-school-case-competition)). Quantify: a specific margin projection beats "improves profitability," and rough estimates with stated assumptions beat vague directional language ([roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)).
- Cornell Corning rubric: recommendations must be practical, data-backed and logically tied to the analysis. Implementation is 30% of the content score: timeline, short- and long-term considerations, unforeseen risks, realistic mitigations. ([Cornell Corning Case Competition](https://business.cornell.edu/centers/ccem/conference/corning-case-competition/))
- Kellogg winners: citing interviews with people "living the problem" impresses judges ([Poets&Quants](https://poetsandquants.com/2019/04/02/six-strategies-for-winning-case-competitions/); 2019 source, older than preferred).

### Inferences
- For an AI case comp at a business school, the winning shape is a hybrid: a working AI demo on the golden path, plus a case-comp-grade business layer (one committed recommendation, a quantified impact model with stated assumptions, an implementation roadmap, and risks with mitigations). Most pure-tech teams skip the second half and most pure-business teams skip the first.
- Write the one-liner as: "[Persona] uses [product] to [action], cutting [metric] from X to Y." Every feature request gets checked against it.

### Gaps
- No source quantified the impact-model detail that business-school judges expect in a one-day AI event (for example a full P&L versus a back-of-envelope estimate).

## 3. What winning AI projects build in 2024-2026, and what separates them from wrappers

### Takeaway
Winners show multi-step AI behavior: agents that call tools or data, translate intent into action, or hold memory and workflow state, wired to real data or integrations. The AI must be necessary, visible and measurable. Wrapper entries are one model call behind a chat UI, with no data, no action and no evaluation.

### Cited Findings
- 2025 OpenAI Open Model Hackathon winners: RoboChef (Best Overall) turns natural language into robot-executable steps, the "translation" between human intent and machine action. Memory Palace (Best Local Agent) tracks decisions, changes, evidence and next steps. Dental Assessment GPT (Most Useful Fine-Tune) won because its domain is concrete and the user benefit is clear. ([DEV: AI hackathon winners](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla); the author notes several details are from thin public descriptions.)
- Microsoft AI Agents Hackathon 2025 winner RiskWise: a supply-chain risk system that orchestrates multiple tools and data sources ([Microsoft](https://microsoft.github.io/AI_Agents_Hackathon/winners/)).
- Anthropic x Forum Ventures hackathon (Sept 2025, Claude Code required on-site): the winners (Affaan Mustafa and David Rodriguez) built "PMF Probe," which validates startup ideas through synthetic user discovery, and later launched it as Zenith ([36kr](https://eu.36kr.com/en/p/3823966768943239); [thuliobittencourt](https://thuliobittencourt.com/everything-claude-code-setup-vencedor-anthropic/)). These are secondary sources and the prize amount and build time conflict across them.
- LBS AI Agent Cup 2025 (one day, MBA/MiM/EMBA teams, supported by Microsoft and Anthropic). Winners: an alumni-data enrichment agent that runs AI voice calls (Public Favourite); a faculty-productivity tutor agent that analyzes homework and generates practice material (Most Impactful); lecture materials turned into interactive business simulations with KPIs and market shocks (Best Innovation). ([London Business School](https://www.london.edu/news/lbs-ai-agent-cup-2025-highlights-lbs-growing-strength-in-applied-ai))
- AGI House SLM Build Day (Nov 2025) first place: a prompt-improvement engine for LLM and agent users ([AGI House newsletter](https://agihousecommunity.beehiiv.com)).
- Separators from guides: AI should do "more than a chatbot wrapper or form parsing," and the team should be able to say why AI is required ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)). "If you can build it without AI, it's not an AI project," so show a before/after comparison ([Reskilll](https://blogs.reskilll.com/?p=136)). Don't treat the model choice as decoration or claim impact without a user ([DEV](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla)).
- Torq's 2nd-place team in a 6-hour cyber hackathon (100k Sysmon events, token waste penalized) had Claude write comparison scripts that measured detections, token use and false positives, and iterated on those numbers ([Shirizly Substack](https://inbarshirizly.substack.com/p/coming-soon)).
- Pitfall: chaining many LLM calls where one would do adds latency and failure points ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).

### Inferences
- High-probability shapes for a business-school AI event: (a) an agent over the case data that produces a decision artifact (ranked recommendations, flagged risks, a draft memo) with citations back to source rows or documents; (b) workflow automation that replaces a named manual process, showing hours saved; (c) a decision dashboard where the AI explains the drivers and runs what-if scenarios. Each pairs naturally with a quantified business outcome.
- Anti-wrapper checklist: real or realistic data loaded; at least one tool call or action beyond text generation; output grounded and traceable to sources; a small eval or before/after metric on screen; a reason AI beats rules or spreadsheets here.

### Gaps
- No source analyzed a large Devpost winner gallery statistically by project type (agents vs RAG vs copilots), so the mix above comes from named winners, not a dataset.

## 4. Time management for a one-day event

### Takeaway
Lock the idea and one-liner in the first hour. Get one end-to-end path working by the halfway mark. Freeze features at about 75% of build time. Have the demo-ready build and backup video done by about 90%. Submit early. Time on the deck and story should run in parallel, not at the end.

### Cited Findings
- Get one end-to-end path working by the halfway mark. Record a 60-second screen capture as a backup and keep a screenshot in case Wi-Fi fails. Rehearse the first 30 seconds out loud. ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l))
- Feature freeze at 75% of the time, demo-ready at 90% ([GitScrum hackathon guide](https://docs.gitscrum.com/en/how-to/how-to-use-gitscrum-for-hackathon-projects)). A longer-event guide freezes 6 hours before the deadline, which doesn't fit a one-day event ([Reskilll checklist](https://blogs.reskilll.com/hackathon-preparation-checklist-2026-before-during-after/)).
- Split roughly 60% core build, 20% polish and debug, 20% presentation. Losing teams spend about 90% coding and 10% on a rushed demo. ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon))
- 72-hour template, scalable to a day: 0-8% pick one idea and one-sentence problem; 8-33% core loop end to end with real input and output; 33-67% golden path; 67-83% record the demo video early so you can re-record, 8-10 slides; 83-100% submit early and prep Q&A. Don't pivot after about the 17% mark (hour 12 of 72). Spread commits across the event; don't push everything at the end. ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon))
- Typical one-day format: doors 8:30, opening 9:00, hacking from 10:00, lunch, a "two hours left" checkpoint around 3:00, close around 4:30-5:00 ([Builderbase playbook ch. 14](https://intercom.help/builderbase/en/articles/14831458-hackathon-playbook-ch-14-schedule-design)).
- Judges often watch the video first, so keep it short and tied to the criteria ([dev.to Devpost guide](https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0)). Suggested 5-minute structure: problem 0:00-0:30, live demo 0:30-2:30, business case 2:30-4:00, team and roadmap 4:00-5:00 ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- The losing Opus 4.7 hackathon entrant submitted "with only seconds to spare" without knowing whether the code worked ([Human Inference Substack](https://humaninference.substack.com/p/why-i-didnt-win-the-opus-47-hackathon)).

### Inferences
- Example adaptation for a ~9:00 to ~5:00 build day (adjust to the real deadline):
  - 9:00-9:45: read cases and rubric, score tracks, pick one, write the one-liner and persona, list the golden-path screens and the one metric.
  - 9:45-10:15: repo, deploy skeleton (hello-world live URL), API keys in env, CLAUDE.md/AGENTS.md with constraints.
  - 10:15-12:30: core loop end to end on real case data (ugly is fine).
  - 12:30-1:00: halfway check. If the end-to-end path isn't working, cut scope now.
  - 1:00-3:00: golden-path polish, grounding/citations, metric on screen. Business teammate builds the impact model and deck in parallel.
  - ~3:00: feature freeze (about 75%). Tag a known-good commit and deployment.
  - 3:00-4:00: bug fixes on the golden path only. Record the backup demo video. Finish the deck.
  - 4:00-4:30: rehearse twice, write Q&A answers (what breaks first, cost, security, scale).
  - 4:30: submit at least 30 minutes before the deadline.

### Gaps
- No 2024-2026 source gave a validated one-day hour-by-hour plan with freeze and buffer together. The plan above is an inference built from the percentage rules.

## 5. Team role split for two people (AI builder + business/finance person who can drive Claude Code), parallel work, and handoff when one is absent until 1-2 pm

### Takeaway
Split by ownership of separate files or areas, not by task-of-the-moment. The builder owns the app and AI pipeline. The business person owns the problem framing, data prep, impact model, deck and story, and can drive Claude Code on separate, non-overlapping files. A written plan and constraints file in the repo let whoever is present keep going alone.

### Cited Findings
- WorkOS one-day Claude hackathon paired one developer with one non-technical teammate. The engineer's job was "to unblock, not take over," and the non-engineer made the product decisions. Pre-built scaffolding (one command for app plus CI plus secrets, so the first push deployed a live, authenticated app) removed the biggest early wall. A useful workflow was Claude for design, then chat to refine understanding and prompts, then code. ([WorkOS](https://workos.com/blog/claude-day-internal-hackathon))
- Torq: each parallel Claude session owned a file or folder. Two sessions editing the same file caused merge problems that cancelled the speedup. Parallelism only worked with modular, independent components. An AGENTS.md held hard constraints and "do not modify" files so every agent stayed aligned. ([Shirizly](https://inbarshirizly.substack.com/p/coming-soon))
- The Opus 4.7 hackathon loser ran multiple sessions on similar tasks and lost hours to git sync, worktree and branch conflicts. Relying on memory instead of a written backlog led to tangled multi-task prompts. ([Human Inference](https://humaninference.substack.com/p/why-i-didnt-win-the-opus-47-hackathon))
- Typical larger-team split: AI engineers, a frontend developer, a domain expert and a pitch lead ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)). SEC case comp: the Alabama team, which had never competed together, was praised for quickly building trust and "leverag[ing] complementary strengths"; two members won Best Presenter and Best Q&A ([Culverhouse](https://culverhouse.ua.edu/?p=32025)).

### Inferences
- Ownership map: builder owns `/app`, `/agent` (or pipeline), deployment and keys. Business partner owns `/data` (cleaned case data, seed examples), `/docs/impact_model` (spreadsheet or notebook), `/deck`, `/demo_script.md`, and UI copy strings. Each person, or each Claude session, edits only its own folders. Both read `PLAN.md` and `CLAUDE.md`/`AGENTS.md`.
- Morning (one person alone until 1-2 pm): the present teammate makes the track decision using the scorecard, writes `PLAN.md` (one-liner, persona, golden-path steps, metric, cut list, schedule), and gets the end-to-end skeleton deployed. Commit small and often with clear messages, and keep a `HANDOFF.md` at the top of the repo: what works, what's broken, next 3 tasks, how to run, where keys live (never the keys themselves).
- At 1-2 pm, run a 15-minute sync: walk the golden path live, agree on the freeze time, and assign the absent teammate's tasks by folder. If the absent person is the builder, the business person should aim for a deployed skeleton from a template or v0/Lovable plus the data and impact model, rather than deep AI pipeline work they would have to hand back. If the absent person is the business teammate, the builder should drop a stub deck outline and placeholder impact numbers in the repo so the business teammate can start straight away.
- Use one main branch plus short-lived feature branches merged quickly, or folder-isolated direct commits. Avoid long-running parallel branches on a one-day clock.

### Gaps
- No source specifically covered a two-person team with one member absent for half the day. The handoff guidance is inferred from the WorkOS and Torq practices.

## 6. Using AI coding agents (Claude Code, Cursor, v0, Lovable, Replit) fast and reliably; pitfalls

### Takeaway
Plan first, keep a constraints file, give agents one task at a time with a written backlog, verify every change on the golden path, and keep heavy scaffolding out. Biggest failure modes: over-engineered agent setups, parallel-session merge conflicts, last-minute breaking changes, exposed API keys, and builds judges can't reach.

### Cited Findings
- Torq's 5 hacks: think hard (ultrathink) before committing to an architecture, which saved more tokens than the planning cost; a multi-agent planning step (feature-dev) for anything touching more than about 2 files; a measurable feedback loop of scripts scoring outputs, dropping additions that don't converge after a few tries; parallel sessions on separate modules; AGENTS.md for shared constraints. ([Shirizly](https://inbarshirizly.substack.com/p/coming-soon))
- Opus 4.7 hackathon loss: a research-generated, "production-ready" repo scaffold brought documentation bloat, drift and context poisoning. Subagents did "just enough work to check the boxes." Many tasks per prompt meant Claude "struggles to complete 1 properly." Voice dictation inflated scope. "AI's great at doing what you tell it to - it doesn't mean it has judgement." ([Human Inference](https://humaninference.substack.com/p/why-i-didnt-win-the-opus-47-hackathon))
- The Anthropic x Forum Ventures winner later open-sourced his Claude Code setup (agents, skills, hooks, and on-demand skill loading so the context window isn't flooded) as "Everything Claude Code" ([36kr](https://eu.36kr.com/en/p/3823966768943239)). It's secondary reporting and the counts vary by source. Note the tension with the Opus 4.7 lesson: heavy setups help when built from experience and hurt when generated fresh on game day.
- WorkOS: the first wall is setup and early errors (for example Slack bot vs user tokens). Pre-provision access and secrets. Reading the docs is sometimes faster than re-prompting. ([WorkOS](https://workos.com/blog/claude-day-internal-hackathon))
- Exposed API keys in a vibe-coded app led to about $2,500 in Stripe fraud across about 175 cards. Keep secrets in .env and out of client code. A Lovable user reported one change breaking the whole site and three days spent getting back to working, so freeze a known-good version. v0 is simpler for non-developers and Cursor gives more code control; don't mix tools on one project. ([fuzen.io](https://www.fuzen.io/posts/vibe-coding-examples-2026); [Reskilll vibe coding 2026](https://blogs.reskilll.com/vibe-coding-hackathons-ai-first-teams-shipping-10x-faster-2026/); anecdotal sources)
- Ship a deployed, accessible demo URL. A local-only build that judges can't access is a pitfall. ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon))
- Speed benchmarks: at a Portland Claude event, 52 of about 120 hackers' teams submitted working prototypes in three hours ([Silicon Florist](https://siliconflorist.com/2026/03/12/back-in-my-day-hackathons-used-to-take-a-whole-weekend/)). Another summary says a solo winner built in about 8 hours with Claude Code (secondary source, details conflict) ([videohighlight](https://videohighlight.com/v/av2IvSGFu40)).

### Inferences
- Reliability protocol: deploy hello-world in the first hour (Vercel, Replit or Streamlit); put API keys only in the host's env vars and set spend limits; commit after every green golden-path run; tag `demo-ready` at freeze and only deploy from that tag; cache or precompute the AI outputs for the demo inputs so a slow or rate-limited API can't kill the live demo; keep the backup video.
- Use v0/Lovable only for a front-end shell if speed matters, then move to Claude Code in the repo. Don't round-trip between generators.

### Gaps
- No source reported head-to-head reliability numbers for Claude Code vs Cursor vs Lovable vs Replit at hackathons.

## 7. Common reasons strong teams lose

### Takeaway
They break the demo or replace it with slides, overscope, bury the product under context, can't say why AI is needed or what it's worth, hedge on the recommendation, or submit late or unverified.

### Cited Findings
- Demo fails or gets replaced by slides. Market size and backstory eat the time before the product appears. Trying to build a platform in 36 hours. Being vague about what was built at the event. Claiming nothing breaks (naming a weakness raised scores). Spending demo time on stack choices. Over-polished UI makes judges wonder where the backend time went. Framework choice, team credentials and slide decks didn't move scores. ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l))
- Hiding the demo behind long explanations, treating the model as decoration, claiming impact without a user, leaving judges unsure what changed, and adding features instead of clarity ([DEV: AI hackathon winners](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla)).
- Pivoting late, pushing all commits at the end, local-only builds, over-chained LLM calls ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)). Judges probe scalability, security, cost and edge cases ([Reskilll](https://blogs.reskilll.com/?p=136)).
- No working demo after heavy agent process, submitted at the last second unverified ([Human Inference](https://humaninference.substack.com/p/why-i-didnt-win-the-opus-47-hackathon)).
- Case comps: offering several options instead of committing ([roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)); creative ideas that can't be implemented lose points ([whereuelevate](https://whereuelevate.com/blogs/10-expert-tips-to-win-your-next-case-study-competition)); jargon and charts that don't hook the judges ([BusinessBecause](https://businessbecause.com/news/mba-degree/5995/3-tips-to-winning-business-school-case-competition)); missing implementation and risk plans (30% of content in the Cornell rubric) ([Cornell](https://business.cornell.edu/centers/ccem/conference/corning-case-competition/)).
- Judges blur demos together by mid-block, so unmemorable projects fade ([dev.to Devpost guide](https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0)).

### Inferences
- For a business-school AI event the most likely loss for a technical team is a strong demo with no quantified, committed business recommendation. For a business team it is a slide-based concept with no working AI behavior. The two-person split above is meant to prevent both.

### Gaps
- No source quantified how often each failure mode happens.
