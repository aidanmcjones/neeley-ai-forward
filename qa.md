# Likely judge questions

Fill the brackets with real numbers from the build. Rehearse twice.

| Question | Owner | Answer pattern |
|---|---|---|
| Who exactly is this for? | Parker | The persona, their current workflow, the pain number from the case |
| What did you build this weekend? | Aidan | Scaffold and LLM wrapper pre-built and disclosed; everything case-specific built here; point to commit history |
| Why does this need AI? | Aidan | Before and after: rules can't [read unstructured X / reason across Y] |
| How do you handle hallucinations? | Aidan | Grounded in [source], every claim cites a row, [X]% correct on [N] test cases, low confidence routes to a human |
| Where does the data go? | Aidan | No training on inputs, PII and PHI stripped, role-based access, audit log; HIPAA and GxP considerations for production |
| What does it cost at scale? | Parker | $[X] per task, $[Y] per year at [Z] volume vs $[W] in staff time |
| Biggest assumption risk? | Parker | Name it (adoption or accuracy), then show the conservative case still pays back |
| What breaks first? | Aidan | Name it (odd input formats, rate limits) and the mitigation |
| Why not ChatGPT or Copilot? | Aidan | Off-the-shelf lacks [workflow integration, case data, guardrails, audit trail]; the model is swappable |
| Will people adopt it? | Parker | Fits existing tools, one-team pilot, tracked metric, human stays in the loop |
