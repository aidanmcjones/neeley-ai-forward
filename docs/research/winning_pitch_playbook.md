# Winning Pitch Playbook: AI Hackathons and Business-School Case Competitions

Research date: 2026-10-16. Note on sourcing: much of the hackathon advice online comes from blogs, vendor guides, and judge posts, not official rubrics. Source quality is flagged where it matters. Search found no public rubric for a "Neeley AI Forward" hackathon specifically; Neeley AI Forward is a TCU program that engaged 600+ students, faculty and industry partners in one semester ([Neeley news, June 2026](https://neeley.tcu.edu/news?tags=AI)). TCU's innovation office reported an inaugural AI-focused competition with $5,000 per winning team; winners included FrogOrg (AI for student org operations) and Procure.IQ (AI for contract and procurement work) ([TCU Innovation announcements](https://www.tcu.edu/innovation/announcements/index.php)). The search results did not say whether Neeley ran that competition. Get the actual rubric from the organizers and map every section of the pitch to it.

## 1. Judging rubrics and how judges weigh them in practice

### Takeaway
Rubrics usually have 4 to 5 roughly equal categories (innovation, technical execution, impact/business value, presentation, sometimes responsible AI or sponsor tech). In practice most teams score in the middle on every category, so the winners stand apart on a few things the rubric does not name: a working live demo, a narrow and well-built scope, a clear one-line identity, and honest answers in Q&A.

### Cited Findings
- Devpost has no universal rubric. Each organizer sets criteria and max scores in its own hackathon configuration, listed on the event's "Judging Criteria" page and in the official rules ([Devpost via MCP listing summary](https://www.mcpbundles.com/skills/devpost-mcp-1e5cf31d8c)).
- Example official structure (Okta hackathon): a pass/fail viability screen first, then three equally weighted criteria: creativity/originality, implementation, potential impact ([Okta dev forum](https://devforum.okta.com/t/what-are-the-judging-criteria-for-the-hackathon/15842)).
- Common AI hackathon split is about 25% each for innovation, technical depth, impact, and presentation (guide, not an official rubric) ([dev.to: What AI hackathon winners have in common](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla)). Another 2026 guide gives about 20% innovation, 25% technical implementation, 25% problem solving/impact, with the rest for presentation ([Masai School 2026 guide](https://www.masaischool.com/blog/how-to-win-an-ai-hackathon-in-2026-full-guide/)).
- Business-school AI hackathon example (Cal Poly Pomona College of Business, 2026): five criteria at 10 points each: Innovation and Creativity; Significance and Impact; Technical Viability ("sound, practical, and scalable"); Entrepreneurship and Organizational Strategy (can it be executed in a business setting and meet market needs); Storytelling (how well the 5-minute video explains problem, solution, impact). Diverse/interdisciplinary teams are used only as a tie-breaker. No technical background required ([CPP AI Hackathon 2026](https://www.cpp.edu/cba/ai-hackathon/index.shtml)).
- Responsible-AI rubric example (Claremont Graduate University Ethical AI Hackathon): five criteria at 20% each, scored 1 to 5: Socially Responsible Impact; Ease of Use, Transparency and Explainability (users can follow the reasoning behind AI answers); Innovative Technology; User Safety and Trust (explicitly discloses ethical risks, unintended consequences, misuse; protects user info; tested); Presentation and Storytelling, where presenters "demonstrate ethical thinking" ([CGU judging rubric](https://research.cgu.edu/hackathon/home/judging-rubric/)).
- lablab.ai's four dimensions: Presentation ("Judges reward clarity over production value"); Business Value (specific target user, rough TAM, at least one revenue model, why this needs AI); Application of Technology (demo works, GitHub repo is real, AI does more than wrap a chatbot around a form); Originality (an angle only this generation of models makes possible) ([lablab.ai guide](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- A graduate AI challenge brief expects lifecycle awareness (drift detection, updates, governance) and explicit treatment of tradeoffs and model limitations ([USAII graduate challenge brief](https://aihackathon.usaii.org/content/docs/graduate-challenge-brief-2.pdf)).
- A judge with a year of judging (July 2026 post) says scores on the four or five rubric categories "compress" because most teams land mid-range. The spread comes from two or three factors the rubric does not name. A live working demo was "the single largest score differentiator." Narrow projects built well scored higher; trying to build a platform in 36 hours signaled poor judgment. Polish beyond legibility, framework choice, team size, and credentials did not move scores ([Kurbaitaev, dev.to](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- Judges need a one-line identity for each project so they can recall it when the panel reconvenes ([Kurbaitaev, dev.to](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- Case competition rubrics are not standardized. One recalled rubric listed PowerPoint, content, presentation skills, recommendations, and Q&A ([UBC blog](https://blogs.ubc.ca/valeriesong/?p=112)).
- Corporate-style AI rubric guidance: score problem fit, evidence of execution, feasibility, adoption potential, and presentation clarity, and do not reward demos with no sponsor or path to production ([AI Beavers rubric comparison](https://ai-beavers.com/blog/internal-ai-hackathon-scoring-rubric)).

### What earns top marks, per category (synthesized from the sources above)
- Innovation: an angle that needs current AI, not a chatbot wrapped around a form (lablab.ai).
- Technical execution: a live end-to-end path that works, a deployed URL, a real repo with commits spread across the event (lablab.ai; Kurbaitaev).
- Business impact/viability: a specific user, a bottom-up market size, a revenue or savings model, an execution path inside a real organization (lablab.ai; CPP; YC below).
- Presentation: a clear one-liner, a story, clarity over production value (lablab.ai; Kurbaitaev).
- Use of AI: explain why AI is necessary and where it is and is not reliable (lablab.ai; Voltage Control in section 6).
- Responsible AI: explicitly disclose risks and misuse, show explainability and data protection, and show testing (CGU).

### Inferences
- For a business-school AI hackathon, expect the CPP pattern: equal weight on innovation, impact, technical viability, business strategy, and storytelling. That means about 40% to 60% of the score is non-technical, which suits a team with a finance major.
- Since rubric scores compress, the best investment is the factors judges talk about: a demo that works, a one-sentence identity, quantified impact, and a prepared "what breaks first" answer.

### Gaps
- No published Neeley AI Forward rubric was found. Get it from the organizers.
- No quantitative data (for example, studies of judge score distributions) was found on how judges weigh categories in practice. The evidence is judge testimony.

## 2. Pitch structure that wins, and timing for 3, 5, and 10 minute slots

### Takeaway
Lead with a plain one-sentence statement of what the product does and for whom, plus the answer or headline number. Then problem, a short live demo of the golden path, a brief "how the AI works," a quantified business case, risks, and the ask. Close by repeating the 3 or 4 key points. Do not spend the opening on background.

### Cited Findings
- Open with a plain statement of what the product does and for whom. One team lost about a third of its slot to context before the product appeared. "Rehearse the opening thirty seconds aloud" because "that is where the score is set" ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- YC: lead with your clearest sentence ("We deliver groceries to customers in their homes"); "Don't bury the lead"; pick 3 or 4 "vertebrae" (the points the audience will remember) and restate them at the close; size the market bottom-up (price times number of potential customers); explain the business model simply; avoid buzzwords; sometimes put impressive traction on the first slide ([YC Guide to Demo Day Pitches](https://ycombinator.com/blog/guide-to-demo-day-pitches/)). The YC post is from 2016, but it is still the primary source most later guides cite.
- Case competitions: open with the core business problem, the recommended solution, and the supporting logic. Teams that spend the opening on background "lose the room." Commit to one answer ("We recommend Option B, and here's why the other two don't hold up"); judges reward that over a menu of options. Build slides around the recommendation, not the analysis process ([Roadtooffer, updated Sep 2026](https://www.roadtooffer.com/blog/consulting-case-competition-guide)).
- Kellogg case-comp winners: judges are impressed when you cite conversations with people "living the problem" ([Poets&Quants](https://poetsandquants.com/2019/04/02/six-strategies-for-winning-case-competitions/)) (2019, older than the preferred window).
- People remember the first and last things you say, so finish strong. Judges hear five or six versions of the same case, so stand out and be human ([Think Insights](https://thinkinsights.net/insights/what-are-case-competitions)).
- Winner retrospective: the team opened with "Why," not features, and cut flashy features to stay on one core problem ([dev.to: AI hackathon winners](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla)). Tell a story, not a feature list ([RevenueCat Shipaton pitching](https://www.revenuecat.com/blog/engineering/how-to-win-shipaton-part-4-pitching-your-app)).
- lablab.ai 4 to 5 minute template: 0:00 to 0:30 problem and why now; 0:30 to 2:30 live demo; 2:30 to 4:00 business case, market size, revenue model; 4:00 to 5:00 team and roadmap ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- Judges should be able to follow the project in three minutes without the slides doing the talking ([dev.to](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla)).
- Executive AI pitches need a clear ask covering budget and timeline ([Voltage Control](https://voltagecontrol.com/articles/how-to-get-executive-buy-in-for-ai-initiatives-without-overselling/)).

### Inferences: recommended timing (derived from the lablab.ai template and the advice above; not a sourced standard)
- 3 minutes: 0:00 to 0:20 one-liner plus the headline number; 0:20 to 0:45 problem with a number and persona; 0:45 to 2:00 live golden-path demo; 2:00 to 2:40 business case (savings, payback, cost to run); 2:40 to 3:00 one risk you have covered, plus the ask. Mention how the AI works only in a sentence during the demo.
- 5 minutes: 0:00 to 0:30 hook and one-liner; 0:30 to 1:00 problem, number, persona; 1:00 to 2:45 demo; 2:45 to 3:15 how the AI works (one diagram); 3:15 to 4:15 business case (ROI, unit cost, market, implementation plan); 4:15 to 4:40 risks and responsible AI; 4:40 to 5:00 ask and recap of the 3 vertebrae.
- 10 minutes: 0:00 to 0:45 hook; 0:45 to 2:00 problem plus user research quotes; 2:00 to 5:00 demo (golden path plus one edge case where you handle a failure gracefully); 5:00 to 6:00 architecture and why AI is needed; 6:00 to 8:00 business case with a worked financial example, sensitivity, rollout plan; 8:00 to 9:15 risks, guardrails, evaluation results; 9:15 to 10:00 ask and recap.
- In every slot, the demo should start within the first third of the time. Several sources warn against long context before the product appears.

### Gaps
- Found no source with an evidence-based split for 3 and 10 minute slots. The timings above are inferences.

## 3. Live demo vs recorded demo, backup video, golden path

### Takeaway
Do the demo live when you can, because a working live demo is the biggest single differentiator. Script one golden path and fix bugs only on that path. Always carry a 60 second recorded screen capture and a screenshot slide as insurance, because venue wifi often fails.

### Cited Findings
- A live working demo was "the single largest score differentiator"; live software removes doubt for judges working under time pressure. "One complete path through the product beats four half-built paths." If only two of six architecture boxes work, demo those two and describe the rest in one sentence ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- Record a 60-second screen capture of the working flow as insurance; wifi failed at most events the author judged. The one slide worth having is a screenshot of the running product, as a fallback ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- Build only the "golden path" the demo video will show and fix bugs on that path first. Have something clickable within 24 hours or the scope is too big. Deploy to a URL judges can reach; a local-only demo "scores as if it doesn't work." Avoid chaining several LLM calls when one would do (latency and fragility) ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- At LeadDev's AI hackathon, one judge said it was the first hackathon they had attended where all the demos worked flawlessly, which shows that working demos are becoming the baseline with AI coding tools ([LeadDev](https://leaddev.com/ai/everything-that-got-built-at-leaddevs-first-ai-hackathon)).
- Hackathons reward demos that make an abstract model feel concrete or physical (analysis of the 2025 OpenAI open model hackathon winner RoboChef) ([dev.to](https://dev.to/jsb-securedme/what-ai-hackathon-winners-actually-have-in-common-1kla)).

### Inferences
- Golden-path script: seed realistic demo data, set fixed inputs that are known to produce a good output, pre-warm the model or API, keep the browser tabs open, and use a hotspot instead of venue wifi. Say what the judge is about to see before you click.
- Because LLM output varies, run the exact demo prompt many times beforehand. If output is unstable, cache or pin the response for the demo and say so honestly if asked.
- If a business-school panel is less technical, the live demo still matters most, but keep it to the user's view (the before and after for the persona), not the code.

### Gaps
- No controlled evidence was found comparing live and recorded demo scores. The evidence is judge testimony.

## 4. Devpost write-ups and demo videos that win

### Takeaway
Judges spend about five minutes per submission, so put the key information first and tailor every section to the published criteria. Keep the video to 2 to 3 minutes (check the rules), show the real working product rather than slides, and remember that production quality does not affect scores.

### Cited Findings
- Judges have "around five minutes" per project; if they cannot find key information "they're going to have to move onto the next one." Keep Devpost's default headings (Inspiration, What it does, How we built it, Challenges, Accomplishments, What we learned, What's next); hackers who delete them "tend to miss out key details." Tailor the write-up to the judging criteria, since some events decide winners entirely on those scores. For sponsor prizes, list the specific products used, what they do in the hack, and why you chose them. Confirm every required item before the deadline or "the judges will never even see your project." Many events require a "2-3 minute demo video." Author: Jacklyn Biggin, MLH Coach who has judged about 20 hackathons (edited July 2023) ([dev.to](https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0)).
- Highlight features that hit each judging criterion in both the video and the written description, because judges skim ([TRON hackathon guide](https://forum.trondao.org/t/tron-grand-hackathon-improving-your-devpost-judge-score/9393)).
- AI Tinkerers video guide: "Short and focused," "2-4 minutes maximum," aim for 2 to 3. Structure: about 30 seconds on what the project does; 1 to 2 minutes on 3 to 5 key features of the working demo; tech or sponsor highlights; who did what; optional next steps. "Production quality does not affect your judging score." "Show actual functionality, not just slides." Title format "[Hackathon Name] - [Project Name] Demo," uploaded as unlisted on YouTube ([AI Tinkerers video guide](https://aitinkerers.org/docs/public/video_production_guide.md?markdown=1)).
- Keep the video under 4 minutes and include a link where judges can try the app if one exists ([PingCAP forum](https://ask.pingcap.com/t/how-to-make-your-video-great/612)). Hook judges with the big picture first, then go into detail ([hackathon.com tips](https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know)).
- Split the video work: one person writes the script, one records the screen, one records the voiceover ([Biggin](https://dev.to/jacklyn/how-to-make-your-devpost-submissions-not-suck-37i0)). Record early so there is time to re-record, and submit with time to spare ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- A GitHub repo with commits spread across the event window matters; an empty repo with one final push is a red flag ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- Business-school variant: CPP's first round is judged entirely from a 5-minute team video, and storytelling is one of five scored criteria ([CPP](https://www.cpp.edu/cba/ai-hackathon/index.shtml)).

### Inferences
- What judges likely read first: the tagline, the thumbnail or gallery image, and the "What it does" section. Make the tagline your one-line identity and the first gallery image a screenshot of the product with the key result visible.
- Add a short "Business impact" or "Responsible AI" subsection inside the default headings if the rubric scores those areas, so each criterion has a findable paragraph.

### Gaps
- No source gave specific guidance on thumbnails or gallery images, or data on which section judges read first. The official Devpost post "6 Tips for Making a Hackathon Demo Video" (info.devpost.com) came up in search but its content was not retrieved.

## 5. Business-school judges vs engineering judges, and financial framing a finance major can own

### Takeaway
Executive and faculty judges reward a decisive recommendation, quantified impact with stated assumptions, a realistic implementation path inside an organization, and composure in Q&A. Engineering judges reward a working, real build and honesty about what you built. A finance major should own one worked financial example (savings, cost to run, payback) and be able to defend every number.

### Cited Findings
- Case competition panels are usually firm partners and senior managers who are also assessing you as a potential hire, so make eye contact with every judge ([Roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)).
- Quantify and disclose assumptions; rough estimates with stated assumptions beat vague claims like "improving profitability." Example framing: a margin gain of "3.2 percentage points over 18 months" worth about $47M. Pick the 3 most important supporting facts or calculations, cut analysis that does not support the recommendation, build one worked financial example, and make sure the presenter can defend every number on every slide. Common failure: 6 hours on analysis, 30 minutes on the presentation. "Judges see the presentation, not your spreadsheet." Practice at least twice, including Q&A ([Roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)).
- Executives push back on any AI pitch that cannot answer "how much will this make us, or how much will this save us, and by when?" Name one workflow, one team, one measurable outcome. Inflated promises (for example a 30% productivity lift with a six-month payback) backfire; specific, bounded ranges are more credible ([Voltage Control](https://voltagecontrol.com/articles/how-to-get-executive-buy-in-for-ai-initiatives-without-overselling/)).
- Start from the business outcome and work back to the data required (Crunchbase CRO Ann Davis) ([Agile Brand Guide](https://agilebrandguide.com/crunchbase-cro-ann-davis-on-the-pressure-to-show-roi-from-ai/)).
- Size the market bottom-up (price times number of customers) and explain the business model simply ([YC](https://ycombinator.com/blog/guide-to-demo-day-pitches/)).
- Business-school rubric criteria include "Entrepreneurship and Organizational Strategy" (execution in a business setting, market fit) ([CPP](https://www.cpp.edu/cba/ai-hackathon/index.shtml)).
- Engineering-leaning judges ask "What part did you build this weekend?" and reward clear answers, including "we wired existing pieces together" ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)). They also check that the repo is real and the AI is not just a chatbot wrapper ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).

### Inferences: a financial frame a finance major can own (formulas are standard finance; the numbers must come from the team's own case)
- Baseline cost: hours per task x tasks per year x loaded hourly cost (plus error or rework cost).
- AI run cost per task: tokens per task x price per token, plus hosting; scale it to annual volume. Show the unit economics as cost per task, before and after.
- Annual net savings = baseline cost minus (AI run cost + human review time + maintenance).
- Payback period = one-time implementation cost / monthly net savings. Also show a 3-year ROI.
- Sensitivity: show conservative, base, and upside cases (for example, adoption at 30/60/90%) so you can answer "what if your assumption is wrong."
- Implementation plan: a pilot with one team, the success metric, then rollout. This addresses the "path to production" that corporate judges look for.
- A good split: the finance person presents the business case slide and takes the cost and ROI questions; the builder takes the technical questions.

### Gaps
- No source directly compared scoring behavior of executive vs engineering judges on the same projects. The contrast is drawn from separate judge and coaching sources.
- Did not find published benchmarks for AI unit economics (cost per task) that would hold across use cases. Teams should compute their own from current API pricing.

## 6. Q&A handling: common judge questions for AI projects and strong answers

### Takeaway
Judges ask hard questions on purpose. Prepare about 10 likely questions, assign an owner to each, and answer with specifics. Naming your weakest point yourself raises credibility; claiming nothing will break lowers it.

### Cited Findings
- Three questions one judge almost always asked: (1) "Who is this for, specifically?" (specificity signals you talked to users); (2) "What part did you build this weekend?"; (3) "What breaks first at scale?" A specific, named weakness raised scores; saying nothing breaks cost credibility. Prepare the "what breaks first" answer in advance ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- Prepare about 10 hard questions, including "What's your biggest assumption risk?" and "Why not just cut costs instead?" Stumbling on a basic question, such as what happens if the revenue assumption is wrong, signals you do not understand your own analysis ([Roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)).
- Practice who presents, the handoffs, who flips slides, and who leads Q&A ([Think Insights](https://thinkinsights.net/insights/what-are-case-competitions)).
- Hallucination: businesses are far less forgiving of hallucination than consumers. Some use cases need reliability that generative AI may not provide, so be ready to show where the tool is and is not reliable ([Vin Vashishta](https://vinvashishta.substack.com/p/why-your-ceo-shouldnt-be-taking-ai)).
- Data privacy: executives ask where data goes and who can access it, especially client, financial, or regulated data. A pitch that skips this signals you have not thought it through ([Voltage Control](https://voltagecontrol.com/articles/how-to-get-executive-buy-in-for-ai-initiatives-without-overselling/)). Data integrity, security, and privacy are common executive questions ([The Artificial Intelligence Show ep. 156](https://podcastrex.com/shows/the-artificial-intelligence-show/156-ai-answers-data-privacy-ai-roadmaps-regulated-industries-selling-ai-to-the-c-suite-change-management)).
- Responsible AI judges look for explicit disclosure of ethical risks, unintended consequences, and misuse, plus testing that shows the system handles user data in a trustworthy way ([CGU](https://research.cgu.edu/hackathon/home/judging-rubric/)).
- "Why does this need AI?" is part of the business value score ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).

### Inferences: answer patterns (built from the findings above; tailor them to the real build)
- Hallucinations: "We ground answers in [source documents] and show the citation for each answer. We tested on N cases and got X% correct. When confidence is low or no source is found, it says so and routes to a human. A human approves anything [high-stakes]."
- Data privacy: "Data stays in [environment]. We use an API tier with no training on customer data, strip PII before the call, apply role-based access, and keep audit logs. Production would go through the client's security review."
- Cost at scale: "It costs about $X per task today, so $Y a year at Z volume, compared with $W in staff time. Costs fall further with caching, smaller models for simple steps, and batching."
- Adoption: "It fits into the tool they already use; we start with a pilot on one team, track [metric], and train champions. The human stays in the loop, so it supports their job instead of replacing it."
- Why not off-the-shelf: "We tried [ChatGPT/Copilot/vendor]. It lacks [workflow integration, domain data, guardrails, audit trail]. Our edge is [proprietary data or workflow fit], and we could build on a vendor model, so this is not a build-vs-buy bet on the model itself."
- What breaks first: name it (for example, unusual document formats, or rate limits at peak volume) and the mitigation.
- Biggest assumption risk: point to the sensitivity case and say what still pays back in the conservative scenario.

### Gaps
- No source provided vetted model answers for hallucination, privacy, cost, or off-the-shelf questions. The answer templates above are inferences.

## 7. Slide design norms for winners

### Takeaway
One idea per slide, about seven words or fewer, big fonts with key text near the top, the big numbers stated plainly, and images only when they support the point. Keep a short stage deck (about 8 to 10 slides for a 5-minute hackathon pitch) with a screenshot of the working product.

### Cited Findings
- "A slide should have one main point, never more." "If you have more than 7 words on a slide it is likely to be too many." Use large fonts and put key text near the top, since people in the back may not see the bottom. Use only pictures that directly support the point. Avoid cumulative graphs, which "cause immediate suspicion that there is no real growth" ([YC](https://ycombinator.com/blog/guide-to-demo-day-pitches/)).
- Hackathon deck of 8 to 10 slides: problem, solution, demo screenshot, market, revenue, team, next steps ([lablab.ai](https://lablab.ai/guide/how-to-win-an-ai-hackathon)).
- Slide decks "fill time" but do not persuade; the one slide worth having is a screenshot of the running product ([Kurbaitaev](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l)).
- Use clean, professional design with no clutter, and use charts, graphs, and images to carry the message ([Management Consulted](https://managementconsulted.com/?p=371563)).
- Several third-party YC guides suggest a short stage deck (about 6 slides for a short pitch) with a longer deck to send afterward; treat the slide counts as rough ([Flowjam](https://www.flowjam.com/blog/yc-demo-day-presentation-format-15-slide-script-that-wins-checks)).
- Build slides around the recommendation, not the analysis process ([Roadtooffer](https://www.roadtooffer.com/blog/consulting-case-competition-guide)).

### Inferences
- For business-school judges, use action titles (the headline sentence states the takeaway, for example "Cuts review time 70% and pays back in 4 months") and put the one big number on the slide in large type. Keep supporting detail in an appendix for Q&A.
- Prepare appendix slides for the predicted questions (cost model, sensitivity table, architecture, evaluation results, privacy design) so answers can point to evidence.

### Gaps
- Found no 2023 to 2026 primary source with data on slide design effects on judge scores. The YC guide (2016) remains the most cited primary source.
