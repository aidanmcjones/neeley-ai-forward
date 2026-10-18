# Onboarding a new company or drug (stream `onboard`)

The case asks for "a reusable AI build that could be pointed at a different company and still produce useful
output." Before this stream, the moat dataset covered 10 companies and 52 drugs through a dozen collector scripts
with hard-coded ticker and drug lists. Now one command onboards a company and one onboards a drug. Both produce
the same page-marked documents, `source` / `source_row` tables and manifest rows as the original collectors, and
both register everything in the citation index (`data/moat/index/citations.sqlite`) incrementally.

## The two commands

```
python -m agent.moat.onboard_company <TICKER> [--years 5] [--quarters 10] [--products 6] [--budget 45] [--ibes]
                                             [--skip step,step] [--no-index]
python -m agent.moat.onboard_drug "<BRAND>" [--vs "ingredient,ingredient"] [--rivals 4] [--budget 20]
                                          [--op-timeout 90] [--skip step,step] [--no-index]
python -m agent.moat.index --add      # incremental index update (both commands run this at the end)
python -m agent.moat.progress         # coverage matrix, now includes every onboarded ticker and drug
```

Run them with `PYTHONPATH=.` from the repo root and with `SEC_USER_AGENT` and the R2 keys in `.env`.

What each command writes:

| Output | Where |
|---|---|
| Page-marked documents (`[[page N \| printed M]]`) | `data/moat/companies/<T>/...`, `data/moat/drugs/<slug>/label_sections.md` (also R2 `moat/<rel>.gz`) |
| Tables, every row with `source` and `source_row` | `data/moat/onboard/<T>/*.csv`, `data/moat/onboard/drug_<slug>/*.csv` |
| Manifest rows (standard columns + `stream`) | `data/moat/manifests/onboard_<T>.jsonl`, `onboard_drug_<slug>.jsonl` |
| Step log (start, done, failed, skipped, seconds, result) | `data/moat/onboard/<KEY>/steps.jsonl`, run summary in `summary.json` |
| Gaps (anything expected that could not be collected) | `data/moat/gaps/onboard.jsonl` |
| Company profile (CIK, names, exchange, aliases) | `data/moat/onboard/<T>/profile.json` |

Index facts from onboarded tables carry `verify_status = unverified_onboard`: they have source rows but no second
agent has re-verified them yet, unlike the `verified/` tables.

## Company steps

| Step | What it does | Reuses |
|---|---|---|
| resolve | CIK, registrant name, exchange, former names, foreign-issuer flag | `company_tickers_exchange.json`, `agent.corpus.filings` |
| subsidiaries | Exhibit 21 (10-K) or Exhibit 8 (20-F) entities; acquired-company names with a corporate suffix extend the alias list (VRTX: vertex, torreyana, viacyte, alpine) | `secx_subs` parsing logic |
| sec_filings | annual reports x `--years`, 10-Qs since 2023 (or results 6-Ks for 20-F filers), 8-Ks since 2023 (primary + EX-99/10/2, capped by `--max-8k`), DEF 14A since 2024 with incentive-metric rows, CORRESP/UPLOAD letters since 2019 with topic tags. URLs already collected by `data/corpus` or another moat stream are not refetched. | `agent.corpus.paged_text/render`, `secx_8k.EX`, `secx_proxy.metrics`, `secx_letters.TOPICS` |
| xbrl_panel | product revenue rows from every 10-Q/10-K/20-F XBRL instance since 2023 | `agent.gap_data.parse_product_revenue`, `filings_panel` columns |
| transcripts | last `--quarters` calls from MarketBeat (Quartr text): the ticker's earnings listing page gives the URL slug, and earnings 8-K (item 2.02) dates fill older quarters. Written as third-party, grade C unless a Bloomberg PDF for that call is in the inbox. | `calls_mb.get/parse/render/quarter_of` |
| attention | analyst Q&A turns per quarter and per topic, cited to the transcript page of the first hit | `market_topics.TOPIC_RE` |
| products | XBRL ProductOrServiceAxis members plus Orange/Purple Book products whose applicant matches the aliases (the `gap_data.company_for` logic with the aliases in place of the hard-coded table), ranked by Medicare 2024 spend, one per brand family | `gap_data.brand_products` |
| pricing | Part D and Part B 2024 spend rows and NADAC (2025, 2026) for the top products | `pricing_medicaid` dataset ids |
| policy | pages of the saved government documents (`data/moat/policy_gov`: CMS IRA, White House MFN, tariff) that name the company or its top brands, IRA selected-drug rows, FDA registered establishments by country | `policy_sites.country/EXCLUDE` |
| consensus | I/B/E/S on WRDS only with `--ibes` (WRDS sends a Duo push); otherwise a logged gap | `ibes.QUERIES` |
| insiders | Form 4 officer and director transactions since 2024 (US filers) | `secx_form4.parse` |
| index | `index --add`, then the coverage summary in `progress.py` bucket terms | |

## Drug steps

identify (Orange/Purple Book applicant, ingredient, application, owner ticker), label (DailyMed SPL via
`drug_pack.find_setid`, section-marked), versions (DailyMed SPL history), reference (Orange Book products, patents,
exclusivity, Purple Book, Paragraph IV, IRA rows via `drug_pack.Bulk`), pricing (Part D, Part B, NADAC 2024 to 2026,
Medicaid SDUD national 2023 to 2025), policy (government document pages), rivals (`--vs`, else the same ATC class
via RxClass, else the same FDA EPC class, branded products only, ranked by Medicare spend), head_to_head
(ClinicalTrials.gov and PubMed via `product_h2h.ct/design/pubmed`), open_payments (general payments by nature of
payment, PY2023 and PY2024, same datastore query as the `rx` stream's `rx_openpay.py`), index.

## Proof runs (Sat Oct 17, 2026)

Exact commands, run from the worktree root:

```
PYTHONPATH=. python -m agent.moat.onboard_company REGN --budget 30 --no-index
PYTHONPATH=. python -m agent.moat.onboard_company NVS  --budget 30 --no-index
PYTHONPATH=. python -m agent.moat.onboard_company VRTX --budget 30 --no-index
PYTHONPATH=. python -m agent.moat.onboard_drug Dupixent --no-index
PYTHONPATH=. python -m agent.moat.onboard_drug Xtandi --no-index
PYTHONPATH=. python -m agent.moat.index --add
```

`--no-index` was used only because the five runs overlapped; a single `index --add` then registered all of them.
After the alias and brand-family fixes below, the alias-dependent steps were rerun for each company with
`--skip sec_filings,xbrl_panel,transcripts,attention,consensus,insiders` (between 6 and 22 seconds each).

### Timings and output

| Entity | Wall time | New docs | New pages | Tables | Table rows | Facts in index |
|---|---|---|---|---|---|---|
| REGN | 147 s | 77 | 1,567 | 12 | 2,758 | 2,789 |
| NVS | 93 s | 14 | 370 | 11 | 3,444 | 3,465 |
| VRTX | 190 s | 85 | 1,724 | 11 | 1,298 | 1,141 |
| Dupixent | 561 s (17 s without Open Payments) | 1 label (146 sections) | 146 | 10 | 916 | 916 |
| Xtandi | 576 s (18 s without Open Payments) | 1 label (42 sections) | 42 | 13 | 430 | 430 |

`index --add` for all five (plus the docs other streams had written since the last full build): 3,529 new docs,
31,727 new pages, 10,035 new facts in 5.1 seconds, against 2 to 4 minutes for a full rebuild. A second run inserted
only rows a concurrent stream had just written; a third inserted nothing. Existing page and fact ids are unchanged.

A citation lookup on the new company works the same as on the original ten:

```
python -m agent.moat.cite "Trikafta net product revenue" --ticker VRTX -k 3
VERTEX PHARMACEUTICALS INC / MA 10-Q 2024-03-31, p. 26  <VRTX:companies/VRTX/10q_2024Q1.md#p27>
```

### Coverage (progress.py buckets)

| Bucket | REGN | NVS | VRTX |
|---|---|---|---|
| Annual reports, 5 years | 5/5 | 5/5 | 5/5 |
| Quarterly since 2023 | 11/11 | 14/14 (6-Ks) | 11/11 |
| Earnings calls, 10 quarters | 10/10 | 10/10 | 9/10 |
| Product revenue panel | 12/12 | 4 annual filings (20-F) | 12/12 |
| Three forces exposure | 4/5 | 4/5 | 3/5 |
| Net price series, top products | 6/6 | 6/6 | 4/4 |
| Consensus (I/B/E/S) | 0/1 (needs `--ibes`) | 0/1 | 0/1 |
| Analyst attention | 10/10 | 10/10 | 10/10 |
| SEC fine print | 6/6 | 3/6 (no proxy for a 20-F filer) | 6/6 |
| Label and head-to-head packs | 2/6 | 2/6 | 0/4 |

Drug packs: Dupixent 8 of 12 items (no Orange Book, Paragraph IV or Part B rows because it is a Part D biologic;
not IRA selected), Xtandi 10 of 12 (no Purple Book because it is a small molecule; no NADAC because it is
specialty-pharmacy dispensed). Xtandi has 3 IRA rows, 47 Orange Book patents, 3 Paragraph IV rows and 34 trials
with separate arms against apalutamide, darolutamide, bicalutamide or flutamide.

### Compared with the peer data that already existed

- **REGN**: the corpus and the `peers` stream already held FY2022 to FY2025 10-Ks, two 10-Qs and six 2024 to 2025
  transcripts. Onboarding added FY2021, ten more 10-Qs, 45 8-K documents, three proxies, 14 comment letters, four
  more transcripts (2025Q4 to 2026Q2), the full XBRL product panel (1,216 rows, 39 product members), 781 Form 4
  rows and the pricing and policy tables. It refetched none of the 22 documents it found already collected.
- **NVS**: four 20-Fs and 14 results 6-Ks were already collected by `peers`. Onboarding added FY2021, nine comment
  letters, four transcripts, the 20-F XBRL panel (1,556 rows), 57 IRA rows (Entresto), 21 FDA sites and 24
  government document pages.
- **VRTX**: no prior data anywhere. Everything above came from the one command in about three minutes.

## What failed or was skipped, and why

- **I/B/E/S** was skipped for all three because WRDS needs a Duo push. `--ibes` runs the same `ibes.QUERIES` for
  the one ticker into `onboard/<T>/ibes_*.csv`; it was not tested live.
- **NVS subsidiaries**: Novartis's 20-F has no Exhibit 8 (it lists subsidiaries in the notes), so the alias list
  stays `novartis`. Logged as a gap.
- **REGN subsidiaries** failed on the first run because Regeneron names the file `regn-ex_211x...htm`. The pattern
  now accepts `ex_21`, and the rerun parsed 34 entities.
- **Insider trades for NVS**: a foreign private issuer files no Form 4.
- **VRTX 2025Q2 call**: not found on MarketBeat inside the date window, so 2023Q4 filled the tenth slot.
- **Policy 4/5 or 3/5**: the saved tariff documents do not name Regeneron or Novartis, and the MFN fact sheets do not
  name Vertex. The rows are correct; the gap is in the source documents.
- **Open Payments** is slow: each query takes about 50 seconds, and it was 95 percent of each drug run. The step
  stops at its first timeout (`--op-timeout`); use `--skip open_payments` for a fast run.
- **Rival inference for Dupixent** uses ATC D11AH (agents for dermatitis), so it returns topical ruxolitinib and
  tacrolimus, labeled with their best-selling brands (Jakafi, Envarsus XR) rather than the topical ones. Pass
  `--vs tralokinumab,lebrikizumab` when the class is broad. Xtandi's inferred set (apalutamide, darolutamide,
  bicalutamide, flutamide) is right.
- **Dupixent's label** is Sanofi's SPL (Sanofi is the labeler; Regeneron is the BLA applicant). That is the current
  label, so it is kept.

## Fixes found by the proof runs

1. Importing helpers from `filings_panel`, `secx_8k`, `secx_form4`, `secx_proxy` and `product_h2h` ran their whole
   collection, because each called `main()` at module level. They now run `main()` only under
   `if __name__ == "__main__"`; `python -m` behavior is unchanged. The first REGN attempt started rebuilding the
   10-company panel and was stopped before it wrote anything.
2. Exhibit 21 header rows ("Document") became an alias and matched every government page (VRTX: 158 false policy
   rows). Subsidiary aliases now need a corporate suffix (Inc, LLC, Ltd, GmbH, AG, B.V. and so on); VRTX dropped to
   one true row.
3. Brand variants (ENTRESTO and ENTRESTO SPRINKLE, EYLEA and EYLEA HD) share spend rows, so the top-product list keeps
   one product per brand family and prefers the base name.

## Code

- `agent/moat/onboard_company.py`, `agent/moat/onboard_drug.py`, `agent/moat/onboard_lib.py` (shared: aliases, run
  log, table writer, Medicaid, CMS spend, government-document search, RxClass)
- `agent/moat/index.py`: `add()` and `--add`. The build loop is factored into `doc_record` and `insert_doc`, so a
  full build and an add index a document the same way. `data/moat/onboard/*/*.csv` are indexed as facts, and an
  onboarded ticker's registrant name fills `docs.company`.
- `agent/moat/progress.py`: `onboarded_tickers()`, `onboard_buckets(t)`, `onboard_drug_buckets(slug)`; `main()`
  adds every onboarded ticker and drug automatically.
- `agent/moat/onboard_cov.py` prints the coverage for one entity; `agent/moat/onboard_restore.py` restores a
  manifest's files from R2 with a sha256 check.
- `tests/moat/test_onboard.py`: CIK resolution, aliases, product member names, exhibit names, subsidiary parsing,
  manifest schema, and `index --add` idempotence with stable ids on a small fixture.
