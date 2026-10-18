# Part 2 framework: one CEO move, built from a Part 1 finding

Status: company-neutral. No company is picked. The four worked examples use only `docs/red_team_v2_company_pick.md` section 6 (plus that file's section 8 scores for context). They show how the template fills in. They are not a recommendation.

Date anchor: today is Sat Oct 17, 2026. The case asks for failure signals "in the first 6 to 12 months", so the kill-signal window runs to **Oct 2027**. Anything dated later is context, not a kill signal.

Ground rule from the case: "AI will argue convincingly for almost any strategy." So the team picks the move. The model only stress-tests it: it checks the money, the dates and the failure signals. The slide should show this split.

---

## 1. The move, in one sentence

Template (from `docs/part2.md`):

> Over the next 24 months, [COMPANY] will [action] with [$ budget] and [N people], to [measurable outcome].

Checks before you accept the sentence:

| Check | Pass when |
|---|---|
| One action | One verb, one asset or program. "And" joining two moves is a fail |
| Budget is a number | A dollar figure with a named source (section 2), not "invest significantly" |
| People are a number | FTEs or a named team size (assumption is fine if labelled) |
| Outcome is measurable | A KPI that shows up in a public filing or data set within 24 months |
| Tied to Part 1 | At least one finding id drives it (case: "which Part 1 findings drive the decision") |
| Inside the CEO's control | The company can do it. If a counterparty decides (a court, a partner, CMS), say so and plan for both outcomes |

---

## 2. Sourcing the budget from a finding's dollar impact

Most strong Part 1 findings carry a dollar figure. The move is more defensible when the budget comes from that figure rather than from "corporate cash".

Step by step:

1. **Start with the finding's gross impact.** Take the base, bear and bull numbers already in the nugget row. Do not recompute from memory.
2. **Net out offsets.** Subtract any other finding that refills or drains the same line (example: a royalty that ends while another royalty grows). Never count two findings twice in one bridge.
3. **Match the timing.** The money must arrive inside the 24-month plan. A finding that pays out after the window cannot fund the move. Flag it and find a current-year source.
4. **Cash vs accounting.** Say whether the dollars are cash, a cost-of-sales change, a reserve or an accounting reclassification. A reserve or one-off credit is not a recurring fund.
5. **Haircut what is at risk.** If the pool depends on an event (a partner option, a court ruling), hold that slice back as contingency until the event clears.
6. **Admit fungibility.** Money is fungible. "Fund the move with X" is a sizing and framing device: it says the move costs no more than a windfall the market may misread. Say this plainly when asked.

Budget waterfall template:

| Line | $ | Source (doc, page or nugget id) | Assumption? |
|---|---|---|---|
| Gross impact of the driving finding | | | |
| Less: offsetting finding(s) | | | |
| Less: at-risk slice held as contingency | | | |
| **Free pool for the move** | | | |

Uses template (24 months, by period):

| Bucket | Q4 2026 | 2027 | 2028 | People (FTE) | Assumption? |
|---|---|---|---|---|---|
| Core action (deal, license, launch, reserve) | | | | | |
| Execution (field, access, medical, manufacturing) | | | | | |
| Contingency (released only when kill signals clear) | | | | | |
| **Total** | | | | | |

Return template: state the return in the same units as the risk (revenue kept, operating income, EPS), give bear, base and bull, discount at a labelled cost of capital, and show payback. Every input gets a citation or an "(assumption)" tag.

---

## 3. Plan structure (24 months, four phases)

| Phase | Window | What happens | Gate to the next phase |
|---|---|---|---|
| 1. Commit | Q4 2026 | Board approval, team stood up, first dated events observed | First kill signals read (section 5) |
| 2. Execute | 1H 2027 | Core action launched or signed | KPI on or above the plan path |
| 3. Scale or resize | 2H 2027 | Contingency released or cut | 6 to 12 month kill-signal review (Oct 2027) |
| 4. Harvest | 2028 | Outcome measured against the one-sentence target | Final read vs the original math |

---

## 4. KPI types

Use one of each. Every KPI needs a public source so a judge (or an investor) can check it.

| Type | What it measures | Typical source | Example form |
|---|---|---|---|
| Leading (adoption) | Is the action landing with doctors, patients, payers | Quarterly product revenue line, Part D or Part B claims, formulary status | "Product X share of franchise sales at or above Y% by Qn" |
| Lagging (financial) | Is it paying back | 10-Q segment or product table | "Revenue retained vs counterfactual" |
| Spend discipline | Is the budget held | Internal; disclosed as R&D or SG&A lines | "Spend at or below plan per phase" |
| Risk event | Did the binary event go our way | Court dockets, CMS lists, partner notices, 8-Ks | "Ruling X by date Y" |

---

## 5. Building the kill-signal table

A good kill signal has five parts. Missing any one, it is a talking point, not a signal.

1. **Dated.** A known date or a known reporting cycle (quarterly results, a CMS list release). "Sometime in 2027" is weak.
2. **Inside the window.** On or before Oct 2027. Later events go in a "context" row.
3. **Observable.** Leadership and outsiders can see it in a public source.
4. **Pre-committed threshold.** The number or outcome that counts as failure, written down before the event.
5. **Pre-committed action.** Stop, resize, or continue. Decide now, not after the fact.

Also tag each signal:

- **Thesis signal:** tells you the move itself is wrong (adoption, a ruling on the asset).
- **Funding signal:** shrinks the pool but does not disprove the move (a partner option that cancels a payment).

Template:

| Date | Signal | Type (thesis / funding) | Where we see it | Kill threshold | Action |
|---|---|---|---|---|---|
| | | | | | stop / resize / continue |

Rule of thumb: at least two thesis signals inside 6 months and at least one at 6 to 12 months.

---

## 6. Two rejected alternatives

Always test the move against:

- **The do-less option:** bank the money as margin, buy back stock, or simply wait. It is the hardest to beat, so the move must explain why it does better.
- **The strongest different-direction option:** spend the same money elsewhere in the portfolio, or on a deal.

| Alternative | Why it was strong | Why we passed (one decisive reason) |
|---|---|---|
| 1. Do less | | |
| 2. Different direction | | |

---

## 7. Why it will work (case requirement)

| Who decides its fate | Evidence (cited) | What it can tell us | What it cannot tell us |
|---|---|---|---|
| Doctors | Label breadth, dosing, head-to-head status | | |
| Patients | Label convenience, administration | | |
| Payers | Part D or Part B spend, formulary, IRA maximum fair price | | |
| Regulators and courts | FDA label, PDUFA dates, rulings | | |
| Investors | Call Q&A themes (speaker + quote) | | |

If any material is doctor or patient facing: FDA-approved uses only, risks as prominent as benefits, competitor comparisons only with head-to-head evidence, no invented testimonials, and the label "Student concept, not actual promotional material."

---

## 8. Rubric-alignment checklist

Case minimum expectations for Part 2 (from `docs/case/fine_print_case.pdf`):

- [ ] The move in one sentence (section 1)
- [ ] Specific budget or commitment of people (section 2)
- [ ] Which Part 1 findings drive it, by id
- [ ] Cost and return, with the math shown, every input cited or labelled as an assumption
- [ ] Two strongest rejected alternatives and why (section 6)
- [ ] Early failure signals in the first 6 to 12 months (section 5)
- [ ] Why it will work, with what the evidence can and cannot tell us (section 7)
- [ ] Promotion rules followed if anything is doctor or patient facing

Rubric (7 categories, 4 points each, `AI_Innovation_Competition_Judging_Rubric.pdf`):

| Category | What Part 2 must show to reach 4 |
|---|---|
| Innovation and Creativity | The move uses a non-obvious Part 1 finding, not the starter thread |
| Technical Execution | The numbers flow from the tool's cited findings into the budget math |
| Use of AI and Responsible Design | Human picks the move; AI stress-tests it; one example where the AI was wrong and got caught |
| Completeness | Every case requirement above is present; limitations stated honestly |
| Design and Usability | One slide, readable in 30 seconds: move, money, dates |
| Impact | A real decision-maker (CEO, analyst) could act on it; dated signals make it testable |
| Presentation | One spoken sentence carries the move; answers to the hard questions are ready |

Hard questions to prepare for any company: "Isn't this the starter thread?", "Who actually controls the outcome?", "Is the budget real money or framing?", "What would make you stop, and when?", "How did the AI help, and where did it mislead you?"

---

## 9. Worked examples (from red_team_v2 section 6 only)

Each example fills the template with what section 6 says. Numbers and dates are as section 6 states them; they still need page citations from `docs/nuggets/<TICKER>.md` before they reach a slide. Section 6 score is shown for reference only.

### 9.1 MRK (section 6 score 4 of 5)

- **Move:** Over the next 24 months, Merck will use the ~$0.8B 2027 Keytruda royalty roll-off as a one-year fund to secure Keytruda Qlex (settle or license Halozyme's European rights and push subcutaneous conversion ahead of the Dec 2028 biosimilar window), rather than book it as margin. [N people: to fill]
- **Budget source:** nugget 001 ($821M base), net of nugget 003 (Winrevair 22% royalty).
- **Kill signals:**

| Date | Signal | Type | Inside window? |
|---|---|---|---|
| About end Oct 2026 | Dutch Halozyme decision | Thesis | Yes |
| Nov 19, 2026 | German appeal hearing | Thesis | Yes |
| Quarterly | Qlex quarterly sales vs the 30% to 40% adoption path | Thesis | Yes |
| Jan 2027 | AstraZeneca's Koselugo option | Funding | Yes |
| Not dated in section 6 | Gardasil First Circuit ruling | Funding | Unknown date |

- **How it fills the template:** budget source is current-year and dated; three thesis signals fall inside 6 months. Gaps to close: people count, uses split, return math, and the control question (Halozyme, not Merck, decides whether to settle).

### 9.2 JNJ (section 6 score 3.5 of 5)

- **Move:** Over the next 24 months, J&J will size business development to the combined STELARA plus second-wave gap (~$4.2B annualized), or fund ICOTYDE access. [Pick one: the template requires a single action.]
- **Budget source:** section 6 notes nugget 001 is 2029 cash, outside the window. It needs a current-year source (step 3 of section 2 fails as written).
- **Kill signals:**

| Date | Signal | Type | Inside window? |
|---|---|---|---|
| Dec 8, 2026 | Enterprise Business Review | Thesis (strategy framing) | Yes |
| Early 2027 | CMS selected-drug list (DARZALEX) | Funding / context | Yes |
| 2027 | First ICOTYDE sales line | Thesis | Likely, date not fixed |
| Not dated in section 6 | Talc 95% participation | Funding | Unknown date |

- **How it fills the template:** strong signals, but the one-sentence move has an "or" and the budget source sits outside the 24-month window. Both must be fixed before it passes section 1 and section 2.

### 9.3 AMGN (section 6 score 3 of 5)

- **Move:** Over the next 24 months, Amgen will hold a $3B to $7B tax reserve before any debt-funded deal, and defend Repatha with direct-to-consumer pricing. [Two actions: pick one.]
- **Budget source:** nugget 006.
- **Kill signals:**

| Date | Signal | Type | Inside window? |
|---|---|---|---|
| Early Nov 2026 (Q3 10-Q) | Q3 2026 Enbrel year over year | Thesis | Yes |
| 2H 2026 | Tax Court decision | Thesis / funding | Yes |

- **How it fills the template:** the dated signals land fast. Section 6 calls the move defensive: a reserve is not a fund that buys an outcome, so the measurable-outcome check in section 1 is the weak point.

### 9.4 AZN (section 6 score 3 of 5)

- **Move:** Over the next 24 months, AstraZeneca will price new launches for MFN from day one and fund US capex with the ~$0.9B freed BMS earn-out. [Two actions: pick one.]
- **Budget source:** nugget 005 (~$0.9B freed BMS earn-out).
- **Kill signals:**

| Date | Signal | Type | Inside window? |
|---|---|---|---|
| Not dated in section 6 | Shenzhen trial date | Thesis / risk | Unknown |
| Oct 2028 | Virginia plant | Context | No (outside 12 months) |

- **How it fills the template:** the budget source is named, but section 6 notes most signals fall outside 12 months. Section 5 needs at least two dated thesis signals inside the window before this example passes.

### 9.5 Side-by-side: how completely each example fills the template

This table rates the fill, not the company. It is not a recommendation.

| Template part | MRK | JNJ | AMGN | AZN |
|---|---|---|---|---|
| One action in the sentence | Yes | No ("or") | No (two actions) | No (two actions) |
| Budget source named | Yes (001 net of 003) | Outside window | Yes (006) | Yes (005) |
| Budget inside 24 months | Yes | No | Yes (reserve) | Yes |
| Dated thesis signals inside 6 months | 3 | 1 to 2 | 2 | 0 |
| Signals at 6 to 12 months | Quarterly sales, Jan 2027 | Early 2027, 2027 | None listed | None listed |
| Control question (who decides) | Halozyme, courts | CMS, courts | Tax Court | Courts, CMS |
| Section 6 score (of 5) | 4 | 3.5 | 3 | 3 |

Fields every example still needs, whichever company is picked: people count, uses split by period, return math with discounting, the two rejected alternatives, the "why it will work" table with page citations, and the AI-caught example for the Responsible Design score.
