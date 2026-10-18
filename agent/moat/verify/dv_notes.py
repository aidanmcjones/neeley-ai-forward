"""Pass rates by field and tier from the hand judgments; writes verified/deals/NOTES.md. Run after dv_build."""
import json

import pandas as pd

from agent.moat.common import write, OUT
from agent.moat.verify.dv_judg import J
from agent.moat.verify.dv_lib import WORK, isnum

orig = pd.read_csv(OUT / "tables" / "deal_comps.csv").set_index("deal_id")
ver = pd.read_csv(OUT / "verified" / "deals" / "deal_comps.csv").set_index("deal_id")
st = json.load(open(WORK / "stats.json"))
bench = pd.read_csv(WORK / "bench_all_cells.csv")
pr = pd.read_csv(OUT / "verified" / "deals" / "pr_checks.csv")
FIELDS = {"upfront": "upfront_usd_m", "milestones": "milestones_usd_m", "total / deal value": "total_potential_usd_m",
          "stage": "stage_at_deal", "deal_type": "deal_type", "therapeutic_area": "therapeutic_area"}


def tier(k):
    o = str(orig.at[k, "origin"])
    return orig.at[k, "confidence"], ("10-K" if o.startswith("10k") else ("own 8-K" if "own_8k" in o else "8-K"))


def same(ov, nv):
    if not isnum(ov) and nv in (None, ""):
        return True
    if str(ov) == str(nv):
        return True
    try:
        return abs(float(ov) - float(nv)) < 0.01
    except (TypeError, ValueError):
        return False


rows = []
for k, jd in J.items():
    if k not in orig.index:
        continue
    if jd["s"] == "dropped" and (jd["dup"] or jd["et"] in (None, "duplicate")):
        continue  # duplicates are not field errors
    notdeal = jd["s"] == "dropped"
    rec = dict(id=k, conf=tier(k)[0], src=tier(k)[1], quote_on_page=int(ver.at[k, "quote_on_page"]))
    for name, f in FIELDS.items():
        ov = orig.at[k, f]
        if notdeal:
            rec[name] = 0 if (name == "deal_type" or isnum(ov)) else None
        elif f in jd["fix"]:
            rec[name] = 1 if same(ov, jd["fix"][f]) else 0
        else:
            rec[name] = 1 if (isnum(ov) or name == "deal_type" or (isinstance(ov, str) and ov)) else None
    rec["role"] = 0 if jd["role"] in ("swapped", "junk") else 1
    rec["row_ok"] = int(jd["s"] == "verified")
    rows.append(rec)
R = pd.DataFrame(rows)


def rate(df, c):
    x = df[c].dropna()
    return f"{x.mean() * 100:.0f}% ({int(x.sum())}/{len(x)})" if len(x) else "n/a"


cols = ["quote_on_page"] + list(FIELDS) + ["role", "row_ok"]
lines = ["| tier | rows | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 2)]
groups = [("all hand-checked", R)] + [(t, R[R.conf == t]) for t in ("high", "medium", "medium:role", "low:role")] + \
    [(f"source {s}", R[R.src == s]) for s in ("8-K", "own 8-K", "10-K")]
for name, g in groups:
    lines.append(f"| {name} | {len(g)} | " + " | ".join(rate(g, c) for c in cols) + " |")
table = "\n".join(lines)
R.to_csv(WORK / "field_checks.csv", index=False)
vs = ver.verify_status.value_counts().to_dict()
et = pd.Series([j["et"] for k, j in J.items() if j["et"] and k in orig.index]).value_counts()
etx = ", ".join(f"{k} {v}" for k, v in et.head(18).items())
rs = st["role_stats"]
b = bench


def f1(v):
    return "" if pd.isna(v) or v == "" else f"{float(v):,.1f}"


def mk(stage, metric, seg="licensing/option/co-dev"):
    r = b[(b.segment == seg) & (b.stage_at_deal == stage) & (b.therapeutic_area == "ALL") & (b.metric == metric)].iloc[0]
    cn = "" if pd.isna(r.collector_n) or r.collector_n == "" else int(float(r.collector_n))
    return (f"| {seg.split('/')[0]} | {stage} | {metric} | {f1(r.collector_median)} (n={cn}) | {f1(r['median'])} (verified_n={int(r.verified_n)}) | "
            f"{f1(r.median_incl_unchecked)} (n={int(r.n)}) |")


shift = ["| segment | stage | metric | collector median | verified median | median incl. unchecked (not dropped) |", "|---|---|---|---|---|---|"]
for stg in ["preclinical", "Ph1", "Ph2", "Ph3", "filed", "marketed", "ALL"]:
    for m in ("upfront_usd_m", "total_potential_usd_m"):
        shift.append(mk(stg, m))
for stg in ["Ph3", "filed", "marketed", "ALL"]:
    shift.append(mk(stg, "deal_value_usd_m", "acquisition"))
prk = pr[pr.keep == 1]
nchecked = len([k for k in J if k in orig.index])
md = f"""# Deal comps: Opus verification notes (2026-10-17)

Input: `data/moat/tables/deal_comps.csv` (1,611 rows, regex-built by the Sonnet collector with no LLM) and `deal_benchmarks.csv` (151 cells).
Output (this folder): `deal_comps.csv` (all 1,611 rows, corrected values in place, plus `verify_status`, `role_unverified`, `verify_note`,
`quote_on_page`, `numbers_on_page`), `deal_benchmarks.csv`, `duplicates.csv`, `pr_checks.csv`.
Errors are logged one per row in `data/moat/verify/ai_wrong.jsonl` (stream "deals"). Scripts: `agent/moat/verify/dv_*.py`
(judgments with a reason for every hand-checked row are in `dv_judg.py`).

## What was checked

- **Hand check (Opus read of the cited page): {nchecked} rows.** Stratified sample of 467: all 32 own-8-K rows of the case companies
  (28 own_8k + 4 edgar_8k+own_8k), 60 high, 60 medium, 60 low:role, all 28 medium:role, 40 extra 10-K-origin rows, every row feeding a
  benchmark cell with n < 10 (248) and the 24 price-to-revenue rows. Then every remaining acquisition row (86), so acquisition medians rest
  on checked rows only. Core rows were read with about 600 characters of page context; feeder and acquisition rows at quote level, with the
  page opened where the quote was ambiguous.
- **Mechanical check on all 1,611 rows:** quote found verbatim (whitespace-normalized) on the cited page and each number found in the
  document (`quote_on_page`, `numbers_on_page`). 10-K rows were re-read from R2 `catalyst-lab-archive` at the cited offset.
- **Auto screens on unchecked rows** (pattern hits / hand-judged hits / judged hits that were dropped): {json.dumps(st['screen_prec'])}.
- **Duplicates** across the whole table: same counterparty within 30 days, same upfront within 400 days with an overlapping party name, and
  10-K restatements of an 8-K deal (same upfront and party, up to 1,500 days). Greedy pairwise merge (no transitive chains) with a veto when
  the two rows name different big-pharma counterparties. {st['n_auto_dups']} automatic merges plus the hand-identified ones, all in
  `duplicates.csv` with the shared name tokens. Spot check of 45 automatic merges: about 40 were true duplicates; the rest were junk rows
  (bank loans, CVR boilerplate) that would otherwise also be dropped.

## Status of the 1,611 rows

{vs}. `unchecked` rows passed the mechanical and auto screens but were not read; they carry their mechanical result in `verify_note` and
are excluded from the verified medians (shown separately as `median_incl_unchecked`).

## Pass rates by field and tier (hand-checked rows, duplicates excluded)

A field passes when the collector's value matched the document. Rows dropped as not a deal count as a fail on deal_type and on every
non-blank number. `role` fails when parties were swapped or a slot held a non-party string (e.g. "Exchange Commission", "Section 13").
`row_ok` means the row needed no change at all. Stage and therapeutic area are scored only where the collector filled them.

{table}

Most frequent error types (hand-checked rows): {etx}.

## Role direction

- low:role hand-checked: {rs['low:role']['n']} rows; licensor and licensee **swapped in {rs['low:role']['swapped']}
  ({rs['low:role']['swapped'] / rs['low:role']['n'] * 100:.1f}%)**, a non-party string in a role slot in {rs['low:role']['junk']} more;
  any role correction {st['low_any'] * 100:.1f}%.
- medium:role (all 28 own-8-K rows): 0 swapped, but every one had both parties blank, and most were merger closings typed `license`.
- All hand-checked rows: {rs['all_checked']['swapped']} swapped, {rs['all_checked']['junk']} junk party strings out of {rs['all_checked']['n']}.
- The combined low:role correction rate is above 15%, so every unchecked low:role or medium:role row has `role_unverified=1`. Do not cite a
  licensor or licensee direction from those rows.

## Benchmark shifts (stage x metric, therapeutic area ALL; USD millions)

Verified medians use only `verified` or `corrected` rows. Cells are kept when verified_n >= 5; `thin=1` marks verified_n 5 to 9. The
verified licensing set over-represents small cells (every n<10 feeder was checked), so read the verified and incl.-unchecked medians together.
Every acquisition row was checked, so the acquisition medians are fully verified (10-K-origin acquisitions are now included).

{chr(10).join(shift)}

Acquisition price-to-trailing-revenue: collector median 3.92x on 24 rows. Re-derivation kept **{len(prk)} of 24**
({", ".join(f"{r.deal_id} {r.multiple_x}x" for r in prk.itertuples())}); the other {24 - len(prk)} used a CVR sales threshold, a milestone,
the acquirer's own sales, a forward forecast or a royalty cap as "revenue". With n = {len(prk)} the cell is in the file but flagged
`below_min_n`; do not use it as a benchmark.

## Units

- All values are USD millions. Rows whose quote carries a USD conversion (RMB, EUR, JPY, GBP, CHF) were kept. D1340 had AU$48m and AU$892m
  read as USD (corrected to US$30m and US$560m). Any unchecked row with a non-US dollar prefix or a value equal to a per-share price was
  dropped; every flag is in `data/moat/verify/deals_work/unit_flags.csv`.
- Thousands read as millions: D0425 ($5,099 thousand of milestones read as a $5.1bn upfront).
- Market size as deal value: D1127 ($100bn obesity market as an upfront), D0669 ($25bn dysmenorrhea market).
- Acquisition convention is equity value at signing excluding CVRs. Rows that took enterprise value, CVR-inclusive "up to" values, debt
  payoff or bridge-loan size were corrected where the page gives the equity value; otherwise the basis is in `verify_note`.

## Known limits

- 10-K rows are dated by the first month-year in the paragraph; many describe pre-2020 deals (dropped as `historical_deal_misdated`) or
  carry a later event date. Dates of kept 10-K rows are approximate.
- `unchecked` rows ({vs.get('unchecked', 0)}) still contain errors at roughly the hand-sample rates above; treat them as leads, not comps.
- Stage is blank for most rows; it was filled only where the page states it.
"""
write("verify_deals", "verified/deals/NOTES.md", md, group="deals", doc_type="notes", quality="verified")
print(table)
print("\n".join(shift))
