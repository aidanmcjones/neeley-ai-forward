# Needle in the Haystack

Team Needle in the Haystack: Aidan Jones and Parker Kingsbury. Neeley AI Forward 2026, Advanced Track, case "The Fine Print: Find the Story, Then Make the Call".

Needle in the Haystack reads ten drugmakers' fine print, finds the material facts the headlines miss, and makes one CEO decision. Every number on the screen links to the filing or label page it came from.

- **Live demo (no login):** https://aidanmcjones.github.io/needle-demo/
- **Pitch deck:** [`deck/Needle_in_the_Haystack_Pitch_Deck.pptx`](deck/), talk track in the speaker notes
- **How we did it:** [`docs/how_we_did_it/Needle_in_the_Haystack_How_We_Did_It.pdf`](docs/how_we_did_it/)

## What it delivers

The demo is a chat page with two prompts taken from the case.

1. **Find the needle (Part 1).** A five-finding table with sources, impact math, peer comparisons and confidence, the Sharpest Needle, and a product comparison against the rivals the case names. Amgen came out first of the ten; Merck and Pfizer are also available.
2. **The CEO Move (Part 2).** One move for the next 24 months with a budget, the return math, two rejected alternatives, warning signs for months 6 to 12, and what the evidence can and cannot tell.

For Amgen, the Sharpest Needle is a $2.4B TAVNEOS intangible carried at about 5.2 times sales while the FDA has formally proposed withdrawing the drug. The CEO Move commits $12.5M and 12 people to offer the FDA a fully funded trial instead of withdrawal, with trial money spent only if the FDA agrees.

## How it works

1. **Our own citation database.** Collectors fetch filings, call transcripts, FDA labels, CMS data and more into page-marked text: 7,005 documents, 78,392 pages and 118,329 fact rows, searchable with full-text search. Nothing is pasted into a chat.
2. **Skill 1, Find the needle.** Ten blind readers, one per company, walk the case's eight "where findings hide" places. Two skeptic agents, one on materiality and one on obviousness, try to kill each candidate over two rounds. A synthesizer rules, and a ranker seals the company pick with a sha256 before it can see any other analysis. 141 candidates, 25 kept.
3. **Skill 2, The CEO Move.** A strategist proposes costed moves. A CFO skeptic and a decider-and-compliance skeptic try to kill them. A synthesizer picks one. 13 moves, 9 cut.
4. **The per-number citation gate.** Every figure must be inside a quoted span on its cited page, derived from cited operands, or labelled an assumption. Anything else is withheld. A fresh verifier agent re-checked all 503 Part 1 numbers and 261 citations.

Both skills are packaged under `.claude/skills/` (`fine-print-part1`, `fine-print-part2`) with every worker brief and launch prompt, so the run can be repeated on any company in the index.

## Repository map

Work happened on one branch per Claude Code session, each with one pull request.

| Branch (PR) | What it holds |
|---|---|
| `data-moat` (#16) | Collectors, the citation index builder, verified tables, `agent/moat/cite.py` (search, get_page, verify_quote) and the eight case retrieval helpers |
| `quant-model` (#21, this branch) | The citation gate (`agent/needle/cite/`), the Part 1 and Part 2 pipelines and briefs (`docs/part1`, `docs/part2`), their outputs (`out/part1`, `out/part2`), the skills, the deck and the How we did it report |
| `ui` (#22) | Exporters from `out/` to the chat's data files and the chat UI, including the theme and 3D structure add-ons (`ui/addon/`) |
| [`aidanmcjones/needle-demo`](https://github.com/aidanmcjones/needle-demo) | The public static copy of the demo served by GitHub Pages |

Key paths on this branch:

| Path | What |
|---|---|
| `out/part1/<TICKER>/part1.json`, `part1.md` | Part 1 deliverable per company, every number gated |
| `out/part1/selection.md` | The sealed blind company ranking (sha256 on its last line) |
| `out/part2/<TICKER>/part2.json`, `part2.md` | The CEO Move per company |
| `docs/case/` | The case PDF and judging rubric |
| `deck/` | Pitch deck, its build script, talk track and structure animations |
| `docs/how_we_did_it/` | The report (PDF and DOCX) and its build script |

## Honest limits

- The demo serves cached answers built by the pipeline; it makes no live model calls and needs no API key.
- Priced-in calls are inferences from analyst attention and stock reactions, rated medium confidence at best, because no product-level analyst estimates are in our data.
- The 3D structures are Protein Data Bank crystal structures, not AlphaFold models. Where a drug has no public structure, the card shows its target and says so.
- Policy and patent math covers the U.S. only. Results run through Q2 2026.
- Licensed sources (Bloomberg transcripts, I/B/E/S) were used locally and are cited by label, never displayed.

Pre-built resources are disclosed in `DISCLOSURE.md`.
