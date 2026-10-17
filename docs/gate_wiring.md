# Wiring the numeric gate into the writers

Branch `quant-gate` built the per-number gate (`agent/needle/cite/gate.py`) and fixed the verify ladder, but did not
touch `agent/needle/quant/*`, `run.py`, `find.py`, `data.py`, `decide_cli.py`, `product_cli.py` or `app/` (another
worker owned them). This file is the exact list of changes for the pass that wires the gate in after the merge.
Line numbers are at `280bad8` and will drift after league_v3; search for the quoted code.

Hard rule being enforced: every number and quote the model outputs carries an in-text citation and a footnote that is
clickable and resolves to the source page, or is shown as derived from cited numbers, or is labelled an assumption.
Anything else is not emitted.

## 0. The API you are wiring

```python
from agent.needle.cite.gate import gate_record, gate_document, numeric_gate, derived_entry
from agent.needle.cite.facts import fact_status_grade, fact_citation_status

out, passed = gate_record(record, ["sentence", "impact.formula"], "citations")      # findings dicts
summary = gate_document({"five numbers": [...], "inputs": claims})                    # decide / product docs
```

- `numeric_check = {status: passed|no_numbers|failed|unchecked, checked, total, verified, derived, assumed,
  unsupported: [{value, where, reason}]}`; `passed` (and `gate.check_ok`) is True for `passed` and `no_numbers` (text
  with no number in it: not a failure, shown and ranked like a pass). `unchecked` (no text) is not shown either.
- A record's `derived` and `assumptions` keys are read by `gate_record` when present. Shapes are in the gate.py
  docstring; build derived entries with `derived_entry(value, expr, {name: Citation | (value, Citation) |
  {"value", "assumption": label} | {"derived": key}}, unit)`. `value` is in the units the text prints.
- `render_markdown(claims, public=False)` now marks each number. A `Claim` takes `derived=` and `assumptions=`.
- Fail closed: a gate error marks the number unsupported. Never catch the result and show the record anyway.

## 1. find.py and run.py (findings)

### find.py, `Finding.to_dict` (about line 459)

- `sentence_md`: replace
  `render_markdown([Claim(self.sentence, [c for c in self.citations if c.page is not None][:6])])`
  with `render_markdown([Claim(self.sentence, [c for c in self.citations if c.verification.ok], derived=self.derived,
  assumptions=self.assumptions)])`. Drop the `page is not None` filter and the `[:6]` cap: the renderer now places
  markers per number, so a fact, XBRL or derived citation that carries a number must be numbered too, and an
  unverified citation must never get a marker (review C3).
- Add `derived: dict` and `assumptions: dict` fields to `Finding` (default empty) and emit them in `to_dict()` so
  `gate_record` sees them (use `Claim(...).to_dict()`'s `_jsonable` or `c.to_dict()` for Citation operands).

### find.py, impact math (D2): how numbers in `impact.formula` are counted

The gate tokenizes `impact.formula` like any sentence. Every number in it must classify:

| Formula token | What to supply |
|---|---|
| `Rev_TTM 38,095.0`, `Rev_US 27,809.3`, `t 0.1501` (computed) | `derived` entry: `expr` over the four quarterly XBRL or 10-Q operands (e.g. `"q1 + q2 + q3 + q4"`), each operand `(value, citation)` |
| `D 544.0` (shares), `G 1,428.714` (CMS spend) | the operand citation itself, in `citations`, with `value`/`unit` set |
| `0.03` (generic anchor), `k 0.3/0.4/0.5`, `d 0.38/0.655/0.85`, `s_MFN (0.003, 0.0065, 0.01)`, weights constants | `assumptions` entry with a label (`"0.03": "generic anchor placeholder (3% margin event)"`). Where the value is a cited analog (Imbruvica 38%, Janumet 85%, Otezla 65%), the decimal in the formula does not match the page's "38%" (census reason "unit differs (plain vs %)"): add a `derived` entry `{"value": 0.38, "expr": "p / 100", "operands": {"p": (38, cms_citation)}}` |
| the printed result (`$319M`, dRev bull/base/bear if shown) | `derived` entry whose `expr` re-computes it from the operands above |
| `1` in `(1 - t)`, `100` in `x 100`, `0` | nothing: in a block whose `where` contains formula / math / impact the gate treats bare 0, 1, 100 as arithmetic constants (labelled assumptions) |

Years, quarter labels (`Q2 2026`, `CY2025Q2I`), dates, form names, page and item numbers and footnote markers are not
counted. `data.derived_citation` (data.py:116) cannot be re-computed by the gate (it stores a formula string, not an
expression); keep it for the JSON, but also add the matching `derived` entry.

Peer statistics (`peer median -0.3 pts, z +1.2`, `gap +8.0 pts`) are numbers: the gap needs a derived entry from the
four YoY operands (find.py `yoy_basis` already has `ops` and `gap`: pass `derived_entry(round(gap*100, 1), "((a/b-1)-(c/d-1))*100", {"a": (m_now/1e6, ops[0]), ...}, unit="pts")`). The peer median and z need a derived entry over the peer panel, or an `assumptions` label such as "shortlist peer panel statistic (not page-cited)". A label is honest; leaving them bare fails the gate.

### run.py, `score_ticker` (lines 58-80)

After the existing split (`(shown if f.vector["E"] > 0 else withheld)`) and before writing:

```python
from agent.needle.cite.gate import gate_record
TEXT = ["sentence", "impact.formula"]          # add any other prose field the UI renders
rows_shown, rows_rejected = [], []
for f in shown:
    rec, ok = gate_record(f.to_dict(), TEXT, "citations")
    (rows_shown if ok else rows_rejected).append((f, rec))
```

- Write `rows_shown` to `findings_v3.jsonl` (each row carries `numeric_check`).
- Write every failed record to `out/<T>/rejected_v3.jsonl` with its `numeric_check` and `"rejected_by": "numeric_gate"`,
  together with the E = 0 rows (`"rejected_by": "no page evidence"`).
- Return only the passing Findings as `shown`: failed records are excluded from the top 5, from `league.league_score`
  and from `sharpest_needle` (run.py:92-93). Do not re-rank failed rows back in.
- Print per ticker `gate: <passed>/<total> passed, <n> numbers unsupported`.

Census on the committed findings_v2 at quant-model (372 rows, sentence + impact.formula, no derived or assumption maps
supplied yet): 258 rows carry no numbers and pass; 286 of 372 pass overall; only 14 of the 50 top-5 rows pass. 599
numbers: 231 verified, 28 assumed (arithmetic constants), 340 unsupported. The top reasons are "no passing citation,
derivation or assumption carries this number" (115) and analog decimals vs page percents (about 120). The derived and
assumption maps above are what turns the top 5 back on; expect the league to be empty for a ticker until they exist.

### app

`app/needle_app.py` reads `out/<T>/findings.jsonl`; point it at the v3 file and show `numeric_check.status`. Never
display a row from `rejected_v3.jsonl` as a finding.

## 2. data.py (C4)

### `fact_citation`, line 84

Replace

```python
ok = value is None or _num_eq(r["value"], value)
status = "exact" if ok and r["verify_status"] not in ("dropped", "False", "no") else "unverified"
note = f"facts row {r['row_key']} re-read ({r['verify_status']})"
```

with

```python
from agent.needle.cite.facts import fact_citation_status, fact_status_grade
reread = value is not None and _num_eq(r["value"], value)
status = fact_citation_status(r["verify_status"], reread)
grade, label = fact_status_grade(r["verify_status"])
note = f"facts row {r['row_key']} re-read ({r['verify_status']}: {label})"
```

and set the Verification score to `grade if status != "unverified" else 0.0` (exact 1.0, machine data 0.6). Note
`value is None` is no longer a pass: callers that want a fact citation must pass the value they print. `table_citation`
(data.py:386) stays `unverified` by design; a number it carries can pass only through a `derived` or `assumptions`
entry. `evidence.py` docstring lines
12-13 and the `exact -> g 1.0` map at line 27 then hold again.

### `xbrl_citation`, line 105

It hard-codes `Verification("exact", ...)` without re-reading the value (C4) and links the whole companyfacts JSON
(D11). Re-read the value from the companyfacts file inside the function and set `number_match` only when it equals
the cited value; use status `unverified` for frames that do not exist (`CY2025Q4`: Q4 is FY minus 9M, so give it a
`derived` entry over the FY and three quarter frames instead, D11).

## 3. decide.py and decide_cli.py (C2, D7)

- decide.py:100-110 `citation_from_dict`: drop any caller-supplied verification
  (`ver = d.pop("verification", None)` must be discarded, never passed to `Verification(**ver)`) and run
  `agent.needle.cite.verify.verify(Citation(**d))` on every company citation. A moves JSON that says
  `"verification": {"status": "exact"}` must not produce "verified: exact" (decide.py:106-109). Delete
  test_decide.py:162 (`md.count("verified: unverified") >= 1`) and assert the opposite for company numbers.
- decide.py:82-87 `benchmark_citation`: benchmarks are external pages, not in the index, so they stay `unverified`
  and the gate will not count them as support. Either ingest the benchmark pages into the index (then they verify
  like any page) or list them in the document's `assumptions` map with the label "external benchmark: <name>, <url>"
  so the number prints `[assumption]`. Fix the dead and homepage URLs listed in review D7.
- decide.py:401-414: the `Claim("scenario weights 0.50 / 0.11 / 0.39, ...")` numbers are assumptions unless the
  benchmark verifies; give that Claim `assumptions={...}`.
- decide_cli.py `build_md` (line 85): build the document as sections and gate it before writing:

```python
from agent.needle.cite.gate import gate_document
sections = {
  "budget": [{"where": f"budget/{k}", "text": f"{k} {f1(v)}", "citations": [], "derived": d_budget[k]} for k, v in ...],
  "scenarios": [...one item per table cell: PV, EV per scenario, with derived entries over the cash-flow rows...],
  "five numbers": [{"where": f"five/{r.name}/EV", "text": f1(r.ev), "derived": {...}} ...],
  "kill signals": [...thresholds as assumptions...],
  "inputs": claims,                      # the existing Inputs and Sources claims
}
summary = gate_document(sections)
```

  Every table cell is an item: EV, CaR, payback month, spread, MCDA, each scenario PV, each of the 24 quarterly
  cash-flow rows, P(success) 0.6176 (derived: `a * b` over BIO 67.5% and 91.5%), budget lines, kill thresholds.
  Render each cell with its marker (`render.claim_markup([Claim(text, cits, derived=..., assumptions=...)])[0][0]`).
  Write `summary["numeric_check"]` into decide.json. If `summary["passed"]` is False, do not write decide.md as a
  recommendation: write `decide_rejected.md` listing `summary["failed"]` and each unsupported number, and exit 2.
- Resolve `finding_ids` against the findings file and fail when they do not resolve (D8).

## 4. product.py and product_cli.py (C5, D9)

- product.py:1050 `cites = [c for c in ch["citations"] if c.verification.ok]; if not cites: continue` keeps a claim
  when any one citation verifies. Replace with the per-number gate over the sentence and the math:

```python
from agent.needle.cite.gate import numeric_gate
res = numeric_gate([("sentence", sent), ("impact.formula", ch["formula"])], cites,
                   derived=ch.get("derived"), assumptions=ch.get("assumptions"))
if not res.passed:
    cmp_.notes.append(f"{ch['channel']}: withheld by numeric gate: {res.numeric_check['unsupported']}")
    continue
```

  and attach the Part D, NADAC, CMS MFP and Orange Book table refs as `fact_citation`s (with values) or CMS PDF page
  citations so their numbers can verify (D9: 211,575 claims, NADAC $526.45, MFP 274/959/71%).
- product.py:241-243 `uncited()`: a cell is uncited when `numeric_gate([(cell_where, cell.value)], cell.citations)`
  does not pass, not when its citations list is empty.
- product_cli.py `build` (line 27): gate the whole document with `gate_document({"cells": [...one item per row x
  entity...], "findings": finds, "math": [...each math / dRev / priced-in line...], "growth limiter": [...]})`, put
  `summary["numeric_check"]` and per-item results in the JSON, list failed items under "Cells with values but no
  verified page citation", and do not print a failed line as a finding. Fix the AMGN LOE year parse (D10:
  `int(re.search(r"\d{4}", str(cs_val)).group())` in place of `int(str(cs_val)[:4])` at product.py:561).
- test_product.py:150-160 asserts the label_breadth claim passes the old gate although its citations do not carry its
  numbers; change it to assert the numeric gate's verdict.

## 5. All three CLIs

- Add `--public` and pass it to every `render_markdown(..., public=a.public)` call (find.py:460, decide_cli.py:156,
  product_cli.py:42) so licensed text (Bloomberg, WRDS) is withheld in public builds (C18, D12).
- Start the viewer before sharing links: `python -m agent.needle.cite.viewer_server --port 8765` (or set
  `VIEWER_BASE` to wherever ui/server.py mounts `viewer_server.viewer_response`).
- A rendered footnote whose links are all empty (no deep link, no viewer) must not be emitted (C14); with
  VIEWER_BASE set every citation with a canonical_id has a viewer link.
