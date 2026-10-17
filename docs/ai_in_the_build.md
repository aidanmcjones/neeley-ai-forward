# Where AI is in the build

For the pitch ("Use of AI and Responsible Design") and for judges. Spec: `docs/quant_model.md` Sections 4.7, 6.7 and 9.

**Pitch line:** "Every number you see was computed by deterministic code from a cited page. AI writes the words, argues the case and reads the calls, in one cached pass, and nothing it says reaches the screen until a page verifier has found it on the page it cites. When the AI was wrong, and it was, that is how we caught it."

## The deterministic track: no model runs

These run with no API key and give the same output every time:

| Step | Code | Output |
|---|---|---|
| Detectors (forensic ratios, filing-text drift, call patterns, labels, supply) | `agent/needle/detect/*.py`, `agent/needle/run.py` | `out/<T>/signals_*.jsonl` |
| FIND (M, O, E, π, confidence, Sharpest Needle) | `agent/needle/quant/find.py` and friends, `run.py` | `out/<T>/findings_v2.jsonl` (v3: `findings_v3`), `out/league_v2.json` (v3: `league_v3`) |
| League and robustness table | `agent/needle/quant/league.py`, `run.py` | `out/league_v3.md` |
| Product fine print | `agent/needle/quant/product.py` | `out/<T>/product_<p>.json` and `.md` |
| DECIDE and kill signals | `agent/needle/quant/decide.py`, `moves.py`, `kill.py` | `out/<T>/decide.json` and `.md` |
| Citations: verify, gate, deep links, footnotes | `agent/needle/cite/*.py` | markers and footnotes on every row |

Confidence labels are a fixed rule over evidence grades (spec 4.7). No score, rank, confidence label, page number or dollar figure comes from a model.

## The LLM track: one pass once the key is armed

| Step | Code | What the model does | What stands between it and the screen |
|---|---|---|---|
| Finding prose | `agent/needle/cite/llm.py`: `build_cited_request`, `parse_cited_response` | writes the plain-English sentence for each top finding from the cited pages | each page is a `search_result` block with `citations: {enabled: true}` on every block; the page number comes from our own `source` field, never the model; every citation goes through the verification ladder and the gate; a sentence with a number not in its cited text is downgraded (`strict_numbers=True`) |
| Courtroom trial | `agent/needle/trial.py` | prosecutor argues the finding is material and unpriced, the company's CFO defends from its own filings, a judge rules | every quote any role cites is checked on its page; invented, paraphrased or wrong-page quotes go to `out/<T>/ai_caught.jsonl`; a "fails" ruling can only lower confidence to LOW |
| Drift and call reading | planned on top of the deterministic drift and call detectors | classifies what changed in a risk factor or how an answer deflected | same cited-request path and gate |
| The memo | `app/main.py` over `agent/llm.py` | answers the reader's questions over the cited context | same gate before display |

Rules of the pass:
- **One pass, cached.** Every call goes through `agent/llm.py`, which caches each answer on disk keyed on (model, prompt, context, system, effort). A rerun reads the cache, so nothing is paid twice, and a demo never waits on the API. Refusals and truncated answers are not cached. Model: Claude Opus 5.5 with server-side fallback.
- **Citations on, structured outputs off.** The API rejects citations combined with structured outputs (HTTP 400), and citations must be on for all document blocks or none. So the cited call returns text with citations; if JSON is needed, a second, non-cited call structures the already-verified claims and carries their citation ids through.
- **Verify, then gate.** The verifier (exact, normalized, fuzzy at 90 with a numeral guard, number on page) and the gate sit between the model and anything shown. A claim with no verified citation is withheld and logged.
- **The model can lower confidence, never raise it.**

Two wiring items are open before the pass runs (see `docs/HANDOFF_quant.md`): `agent/llm.py` today sends context as plain document text, so the cited path needs a call variant that sends `build_cited_request`'s body through the same cache; and `trial.py` reads the old engine's `findings.jsonl`, so it must be pointed at the v3 findings for its veto to reach the league.

## When the AI was wrong, and how we caught it

1. **The first backtest overclaimed.** v1 said "gross-margin drop is followed by an adverse event 59% of the time vs a 43% base rate." Two AI skeptic agents, reviewing independently and then each other, refuted it: event windows overlapped data already known at the signal date (about 41% of events were implied by the quarter's own run-rate), a margin signal predicting a margin event was partly persistence of one series, and the lift was between firms only. v2 fixed each point; what survived is narrower: no forensic flag significantly predicts a revenue drop or impairment, but the flags do track future margin compression (12% with no flags to 61% with five). Caught by adversarial review before any judge saw the number (`docs/needle_gate2.md`, commit c3cf03d).
2. **Lilly's first place was a scorer bug.** The AI-built scorer treated Lilly's gross-margin level (85.8%) as a margin change, about $68B of "impact", which was 80.3% of Lilly's league score. Caught when the model designer re-ran the scorer and traced the score row by row; fixed in commit 4009a40. Lilly moved from 1st to 8th, and the margin row now scores zero because a margin above peers is good news.
3. **Wrong label variants.** The drug packs held the Ozempic oral-tablet label, the Sarclisa ESCENA subcutaneous label and the Janumet XR label in place of the products the case names. Caught by checking each label's product against the case; the right labels were re-pulled and the variants kept as separate files (commit 4d913fa).
4. **AI-written transcript summaries.** fool.com transcripts open with LLM-written "takeaways" and summary sections that read like call text. A quote from them is not something an executive said. The verifier rejects quotes from those sections (`agent/findings.py`), and the corpus flags them together with a mislabeled AstraZeneca Q1 transcript (commit 7964caa). Until that check is ported into the citation package, the deck uses no transcript quote as evidence.
5. **The data layer's own log.** Agents that built the data layer log every confident error they made and how it was caught in `data/moat/verify/ai_wrong.jsonl` (472 rows by the evening of 2026-10-17). Example: the AI reported 616 rows of "restated" product revenue; reconciliation found zero true restatements, 447 being recasts where a company moved products between reporting lines.
6. **Our own draft spec.** The reviewed draft of the quant model claimed things the code did not do (one universal MFN rate scored as certain, a needle rule that "does not silently relax" when the code did). The same adversarial review caught it; `docs/quant_model.md` Section 14 lists every correction by finding id.
