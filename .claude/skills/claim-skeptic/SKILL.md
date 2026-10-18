---
name: claim-skeptic
description: Rules and the JSON verdict format for a skeptic subagent that tries to refute one claim, finding or nugget row (lens A truth, lens B stakes). Use when you are given a CLAIM to check, or when writing prompts for skeptic or verifier subagents.
---

# Skeptic verdict

You get one CLAIM and one lens. Your job is to break it.

## Rules
- Assume the claim is WRONG until the files prove otherwise. Default to `refuted: true` when you are uncertain or cannot confirm it yourself.
- Read the real files yourself: the cited pages (use the `corpus-cite` skill to check quotes), the code, `docs/case/fine_print_case.pdf` and `docs/case/judging_rubric.pdf`. Do not trust the evidence quoted in the claim.
- Check every sub-claim separately. Recompute at least one number per finding: units, period, currency, sign, level vs change.
- Partly right claims are common: put the accurate half in `correction`.
- Read-only. Scratch files go in your own scratchpad subfolder. No commits, no em dashes.

## Lenses
- **Lens A, truth:** is every factual part true at the named commit and on disk? Verify the mechanism by reading the lines, running safe read-only commands and counting files (`git show <sha>:<path>`, `git ls-tree -r <sha>`).
- **Lens B, stakes and collateral:** assuming the facts, does it cost rubric or case points with the time left? Is the suggested fix the right size or over-engineering? What else would it touch (other sessions' files, Aidan's folders, the demo golden path)?
- **Finding attack order** (for a findings row): one-off dressed as a trend (acquired IPR&D, impairment, FX, tax settlement, tag switch); mechanically distorted ratio (DIO on 85%+ gross margin, tiny base); same fact counted twice; already said (starter thread, release headline, analyst question on the last four calls); baseline against two prior years; inside the 24-month window; peer cell filled; three or more stacked assumptions mean low confidence.

## Output: JSON only
```json
{"refuted": true, "confidence": "high|medium|low",
 "what_is_true": "", "what_is_false_or_overstated": "",
 "correction": "the narrowest accurate version of the claim",
 "matters_for_winning": "high|medium|low|no",
 "recommended_action": "smallest fix worth doing before the Sun 10:30 am freeze, or none",
 "evidence": ["file:line or command + output snippet"]}
```
