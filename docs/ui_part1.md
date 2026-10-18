# ui/public/data/part1: the cached Part 1 answer for the judge-facing chat

The chat opens on the case's Part 1 prompt, verbatim: "find material, non-obvious findings about one company and
compare one of its key products against its rivals." It answers with a cached deliverable for the number one
company (the judge can switch to number two and three) in the case's format, plus a visible reasoning trace and a
"why this company beat the other nine" card. There is no model call, no network access and no API key.

The model session's blind reasoning pass writes `out/part1/**` (it has not run yet). `agent/ui_part1_export.py`
copies that output into `ui/public/data/part1/`, applying the public withholding rule and the hard checks.
`agent/ui_part1_fixture.py` writes a sample in the same four shapes to `ui/public/data/_sample/part1/`, built from
real gated data, so the UI can be built now. The UI should prefer `data/part1/` and fall back to `_sample/part1/`.

```
PYTHONPATH=. python -m agent.ui_part1_export                  # out/part1 -> ui/public/data/part1 (exits 0, writes nothing, if out/part1 is absent)
PYTHONPATH=. python -m agent.ui_part1_export --check          # validate ui/public/data/part1 (exit 1 on errors)
PYTHONPATH=. python -m agent.ui_part1_export --check --sample # also validate ui/public/data/_sample/part1
PYTHONPATH=. python -m agent.ui_part1_fixture                 # rewrite the sample from ui/public/data/companies
```

Python: the generators import only the standard library and `agent/` modules, but `agent/ui_memos.py` uses
Python 3.12 f-string syntax, so run them with a 3.12+ interpreter (`/opt/homebrew/bin/python3`, 3.14, on the
build Mac; `/usr/bin/python3` is 3.9 and fails on import). The repo has no checked-in venv.

## Source contract (out/part1, written by the model session)

1. `out/part1/selection.md`: prose; its last non-empty line is `sha256: <hex>`, the hash of everything above that
   line. `out/part1/selection.json`: `{picked: [T1, T2, T3], reasons: {T: text}, eliminated: {T: one line},
   sealed_at (ISO 8601 UTC), sha256}`. `out/part1/selection_appendix.md` (the comparison to the internal ranking and
   the red team) is not sealed and is never read by the exporter.
2. `out/part1/<T>/part1.json`:

```
{ticker, name,
 findings: [{n, finding, finding_marked, marker_map {n: cite_id},
             source: {doc_title, period, page, quote, url},
             cites: [company-file evidence objects: cite_id, doc_id, page, quote, url, verification, withheld, grade, ...],
             impact: {text, text_marked, math, direction,
                      numeric_check {status, checked, total, verified, derived, assumed, unsupported}},
             peer, peer_marked, confidence: high | medium | low}],
 sharpest_needle: {finding_n, why, why_marked?, cites},
 product_table: {product, rivals: [..],
                 rows: [{row: <one of the five keys>, cells: {<name>: {text, text_marked?, cites}}}],
                 financial_tie: {text, text_marked, math, cites},
                 growth_limiter: {sentence, sentence_marked, cites},
                 priced_in: {call: "priced in" | "not priced in" | "untestable", text, text_marked, cites}}}
```

   Row keys, exact and in this order: "approved uses", "boxed warnings and safety", "dosing and convenience",
   "patent and exclusivity timeline", "pricing and gross-to-net". Only text whose `numeric_check.status` is
   `passed` or `no_numbers` appears; failed records live in `out/part1/<T>/rejected.jsonl` and never in part1.json.
   Markers: `[n]`, `[derived: a, b]`, `[constant: NAME]`, `[assumption]`, `[assumption: reason]`,
   `[licensed source]`, as in docs/ui_memos.md. `priced_in.call` "untestable" renders as a plain statement (no
   consensus cite exists), not a verdict.
3. `out/part1/<T>/trace.jsonl`, one JSON object per line. Line 1 is the header:
   `{step: 0, category: "header", categories: [the eight strings], ticker, generated_at}`. Then one line per step:
   `{step, category, query, documents: [{doc_id, doc_title, page?}], candidate: {text, cites?},
   skeptic_materiality: {round1, round2}, skeptic_obviousness: {round1, round2},
   verdict: survived | killed | narrowed, verdict_reason, finding_n?}` (`finding_n` when survived or narrowed and used).

The eight categories, verbatim from the case's "Where findings hide" list, in this order:

1. Language drift
2. Gross-to-net
3. Inventory and receivables growing faster than revenue
4. Segment and product table changes
5. Footnotes
6. Earnings-call Q&A
7. Product fine print
8. Peer contrast

## UI files (ui/public/data/part1 and ui/public/data/_sample/part1)

| file | shape |
|---|---|
| `index.json` | `{generated_at, engine, prompt, picked: [T1, T2, T3], tickers: [..], sealed: {sha256, sealed_at}, sample: false}`; the sample adds `sample: true` and `sample_note` |
| `selection.json` | `{picked, reasons, eliminated, sealed_at, sha256, selection_md}` where `selection_md` is selection.md's text above the hash line |
| `<T>.json` | part1.json as above after withholding |
| `<T>_trace.json` | `{header, steps: [...], summary: {candidates, survived, killed, narrowed, documents}}` |

Exporter transforms:

- Withholding, on every dict in any `cites` list at any depth (the rule of docs/citations.md and
  `agent/ui_export.withhold_reason`): a licensed (Bloomberg) cite always loses quote, excerpt, url, deep_link,
  viewer_link and value; a `machine_data` cite loses quote, excerpt and links, and keeps `value` and `viewer_link`;
  an unverified (or any non-public status) cite loses quote, excerpt and links; a `number_match` cite never shows
  its quote (the excerpt, which locates the number on the page, is kept, with `quote_note`). Withheld cites carry
  `withheld: true` and a `withheld_reason`. A finding's `source.quote` is kept only when a non-withheld verbatim
  cite on the same record carries that quote.
- Markers: every `[n]` and every `[derived: a, b]` operand in any `*_marked` field must resolve to a cite on its
  record (the nearest object that holds `cites`): through that record's `marker_map` when it has one, else by the
  cite's `n`. On export, markers that do not resolve are dropped and the number stays, as in ui_memos.
- Trace: steps are grouped by category in the contract's order (stable within a category), each step's
  `documents` are deduplicated on (doc_id, page), and `summary` is recomputed: `candidates` = steps, the three
  verdict counts, `documents` = distinct doc_id count. A killed candidate was never gated, so every digit-bearing
  token in its text is replaced by `[figure withheld: not gated]`.

Hard checks (export writes nothing, `--check` exits 1):

1. No record carries `numeric_check.status` "failed" or "unchecked"; "passed" carries `checked > 0` and the
   verified/derived/assumed breakdown; "no_numbers" counts no numbers.
2. Every marker resolves (above). Every `marker_map` value is a cite_id on its record.
3. No "Citation(" or "Claim(" substring anywhere.
4. Pitch language: the ui_memos `--check` list ("score L", "S = ", "materiality score", "robustness") plus
   "league" fail anywhere.
5. The trace header's `categories` equal the eight strings above, verbatim and in order; every step's category is
   one of them and steps are grouped in that order; verdicts are survived, killed or narrowed; the skeptic fields
   are `{round1, round2}` records (the sample may carry null); a killed candidate prints no digits.
6. `selection.json.sha256` equals sha256 (UTF-8) of selection.md's text above its `sha256:` line (one trailing
   newline either way is accepted); the hash on that line equals selection.json's; `index.sealed` matches.
7. Withholding holds on every cite (above).
8. Shape: each `<T>.json` has `n, finding, finding_marked, marker_map, source, cites, impact (with
   numeric_check), peer, confidence` per finding; `sharpest_needle.finding_n` is one of the findings; the product
   table has the five row keys in order and a cell for the product and every rival in every row;
   `priced_in.call` is one of the three strings. Fewer than five findings is a warning.

## The sample fixture (ui/public/data/_sample/part1)

Built by `agent/ui_part1_fixture.py` from `ui/public/data/companies/<T>.json` (the exporter's gated company files),
`out/<T>/findings_v3.jsonl` and `rejected_v3.jsonl` (block, detector and nugget ids) and `docs/nuggets/<T>.jsonl`
(obscurity rung), through the same renderers `agent/ui_memos.py` uses, then through the exporter's transforms and
checks. What is real: every finding sentence, number, impact formula, peer clause, source page, product cell,
growth limiter, financial tie and priced-in call. What is illustrative: the pick order, the selection text and its
hash, and the trace.

- `picked = ["LLY", "GILD", "MRK"]` (illustrative order; stated in `sample_note` and in each reason).
  `reasons` and `eliminated` are short sentences built from `meta.json:evidence_located` (verified and
  high-confidence counts), `needle_source` (red-team read or plain rule) and whether `stance.decide` carries moves
  (DECIDE run, pipeline demonstration or valued move); no scores. The marked versions with row cites are in
  `reason_records` and `eliminated_records` (`{T: {text, text_marked, cites}}`). `selection_md` is the fixture's
  own text; `sha256` is its hash; `sealed_note` says it is not sealed by the model session.
- Findings: `ui_memos.ranked_findings` (the findings_table rows by rank, cited findings whose numeric check did
  not fail, needle first), top five. `finding_marked` is the row's `sentence_marked` renumbered to the record's own
  cites by `ui_memos.sentence` (markers in `marker_unresolved` dropped); `finding` is that text with markers
  stripped. `source` is the first non-withheld verbatim page cite (doc_title, period, page, quote, url, speaker,
  plus `cite`, its marker number). `impact.text` / `text_marked` is `ui_memos.impact_cell` (the plain-English reading
  of the gated impact text, never `impact.dollars`) with the impact cites; `impact.math` is the plain formula and
  `impact.math_marked` the row's `impact_marked` renumbered; `impact.numeric_check` is the row's. `peer` is the row's
  `peer_text` via `ui_memos.peer_cell`; `confidence` is the row's. `marker_map` maps each marker number to its
  cite_id; `cites` are the company file's evidence objects with `n`, `doc_label` and `finding_ids` added.
- `sharpest_needle`: the finding whose id is `needle_id_rule`; `why` is `needle_reason` read as ui_memos reads it
  (a reviewer reason that carries ungated figures is replaced by a plain clause saying so), cited to
  `companies/<T>.json:needle_reason`.
- `product_table`: LLY zepbound, GILD biktarvy, MRK keytruda, from `companies/<T>.json:labels.v2.<slug>` (the
  exporter's copy of `out/<T>/product_<slug>.json`, already withheld). A cell prints its value only when it is not
  `uncited`, is `verified`, its numeric check passed or has no numbers, and at least one non-withheld verbatim page
  cite backs it; otherwise it prints "needs citation" (never the value) and keeps its cites. Dosing cells print
  every regimen in the label quotes. `financial_tie` is the first `tie_to_financials` finding whose gate passed
  (gated text only, its formula as `math`); `growth_limiter` is the engine sentence through ui_memos' money gate;
  `priced_in.call` maps `growth_limiter.priced_in` true / false to "priced in" / "not priced in", and to
  "untestable" when the engine's reasons say the test could not run, cited to the reasons row and to the
  analyst-attention scorecard row for the topic.
- Trace: header per contract plus `sample: true`, `note` ("Illustrative trace assembled from the engine's gate and
  red-team decisions; the blind skeptic pass has not run"), `trimmed` counts and `sources`. One step per company
  finding (survived when it is one of the five, with `finding_n`; narrowed otherwise) and per rejected row (killed,
  `verdict_reason` = the gate's reason in plain words, no figures). `skeptic_materiality` and `skeptic_obviousness`
  are null (the UI shows "no skeptic record in the sample"). About 40 steps per company: every survived row, every
  killed row with a distinct (signal kind, reason) pair, then narrowed rows by table rank to fill. Extra step keys:
  `signal_kind`, `detector`, `block`, `source_id`, `nugget_id`, `obscurity_rung`, `table_rank`, `category_note`.

### Category mapping (fixture trace)

A red-team nugget row is placed by its nugget `signal_family`; every other row by its `signal_kind`, first match
wins.

| source | match | category |
|---|---|---|
| nugget family | language_drift | Language drift |
| nugget family | gtn | Gross-to-net |
| nugget family | inventory_receivables | Inventory and receivables growing faster than revenue |
| nugget family | segment_change | Segment and product table changes |
| nugget family | footnotes | Footnotes |
| nugget family | call_qa | Earnings-call Q&A |
| nugget family | label_fine_print | Product fine print |
| signal_kind | `risk_*`, `mdna_*`, `*drift*`, `*contradiction*` (block T) | Language drift |
| signal_kind | `qa_*`, `call_*`, `*dodge*`, `*deflection*` (block C) | Earnings-call Q&A |
| signal_kind | `*_peer_outlier` (ETR, R&D share, gross margin, days inventory vs the peer median) | Peer contrast |
| signal_kind | `label_*`, `boxed_*`, `dosing_*`, `exclusivity_*`, `faers_*`, `*patent*`, `paragraph_iv*`, `spend_per_claim*` (blocks L, P, X) | Product fine print |
| signal_kind | `*gtn*`, `*rebate*`, `*net_price*`, `ira_*`, `mfn_*`, `ira_selection*`, `program_cliff*` (block P and forces nuggets) | Gross-to-net |
| signal_kind | `dio_*`, `dso_*`, `*inventory*`, `*receivable*`, `distributor_commentary` (distributor filings on channel inventory) | Inventory and receivables growing faster than revenue |
| signal_kind | `*segment*`, `revenue_quality`, `demand_divergence`, `gross_margin_drop`, `*discontinued*` | Segment and product table changes |
| signal_kind | `impairment`, `trial_terminated`, `*footnote*`, `*royalty*`, `*collaboration*`, `*contingent*`, `expense_offset*`, `*litigation*` (block F) | Footnotes |
| signal_kind | `tax_rate_shift`, `rnd_shift` | Footnotes, with `category_note` (read from the income-statement footnotes; no closer case category) |
| anything else | a peer finding (`peer` in the kind, or a comparable peer) | Peer contrast |
| anything else | not a peer finding (e.g. the forces nugget `conditional_tariff_relief`) | Footnotes, with `category_note` "no case category matches this signal" |

Killed reasons in plain words: numeric gate ("a number in the sentence matches a cited figure only in a different
unit", "has the opposite sign to the cited figure", "is carried by no passing citation, derivation or
assumption"); review guards 2, 3, 8 and 9 by what they test, and "dropped (the guard recorded no further reason)"
when the engine recorded only `drop`; evidence gate ("no page-verified citation backs it").

## Swap procedure when out/part1 lands

1. Pull the model session's `out/part1/**` into this checkout (selection.json, selection.md, `<T>/part1.json`,
   `<T>/trace.jsonl`).
2. `PYTHONPATH=. python -m agent.ui_part1_export`. It refuses to write on any hard-check failure and prints each
   one; fix the source, never the check.
3. `PYTHONPATH=. python -m agent.ui_part1_export --check --sample` must report 0 errors for both directories.
4. The UI prefers `data/part1/index.json` over `data/_sample/part1/index.json`; no UI change is needed. Leave the
   sample in place as the fallback.
5. Commit `ui/public/data/part1/` and republish the artifact.
