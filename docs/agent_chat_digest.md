# Agent-chat decisions digest

Source: GitHub issues #3 to #12 in aidanmcjones/neeley-ai-forward, read with `scripts/agent-chat read` on 2026-10-17 (threads 3, 4, 6, 7, 8, 9, 10, 11, 12). Read-only: nothing was sent, replied to, or closed.
"Aidan's agent" = aidanmcjones. "Parker's agent" = frogman826 (Parker). Latest message read: #12 at 19:25Z.

## 1. Company and product for the case

NOT PICKED. No thread records a chosen company, ticker set, or product for the case.
- #3 (frogman826, 16:44Z) sets the handoff due after the reveal: "After the 9:00 case reveal, reply here with `--kind handoff`: sponsor, the three companies (tickers), the named drugs, and any data the case provides." No such handoff appears in #3 to #12.
- #11 (19:16Z): "if the pick is one of those seven, every slide quote must be checked against Bloomberg." The pick was still open then.
- #4 (16:34Z): "re-fetch AZN Q1 2026 call only if AZN is chosen." Still conditional.
- #9 (19:13Z): "the case names this hiding spot" (products folded into Other). This names a theme, not a company.

## 2. CEO move (Part 2)

NOT CHOSEN. #3 says only: "Parker owns the money: revenue-at-risk model from `derived/loe_curves.csv` plus the CEO stance." No CEO stance or move is recorded in #3 to #12.

## 3. Ownership claims

Parker's agent (frogman826)
- #3 (16:44Z, claim): creating `agent/findings.py` and `eval/test_verifier.py` (new); adding pypdf, lxml, openpyxl to `requirements.txt`; 2-line change in `agent/llm.py` (answers cut at max_tokens not cached). Stated as NOT touching `corpus.py`, `drug_pack.py`, `ir_fetch.py`, `app/`, `data/corpus`.
- #6 (16:53Z, claim): `agent/needle/*`, `app/needle_app.py`, `tests/needle/*`, `docs/needle.md`. Reuses `agent/findings.py` verify()/load_docs() and `agent/llm.py` call().
- #7 (17:17Z): Streamlit UI at `app/needle_app.py` in progress.
- #4 (15:51Z, 16:34Z, 16:48Z): `docs/materiality_spec.md` (new); `data/corpus/GAPS.md`, `data/corpus/README.md`, `data/corpus/companies/AZN/GAPS.txt`, `data/corpus/companies/GILD/GAPS.txt`; `drugs/GAPS.txt`; manifest rows and label fixes in the drug pack; `agent/drug_pack.py` find_setid exclusion widened.

Aidan's agent (aidanmcjones)
- #8 (18:50Z, claim, branch `data-moat` off `needle`): `agent/moat/*`, `data/moat/*` (README, GAPS, manifest committed; bulk files to R2 `moat/`), one line in `.gitignore`. Stated as NOT touching `agent/needle/*`, `app/needle_app.py`, `tests/needle/*`, `data/corpus/*`, `agent/corpus.py`, `agent/drug_pack.py`.
- #9 to #12 deliverables: `data/moat/verified/filings/`, `data/moat/verified/policy/`, `data/moat/verified/calls/`, `data/moat/verified/market/`.

Under app/ or ui/
- `app/needle_app.py` is claimed by Parker's agent (#6) and in progress (#7). No `ui/` path is claimed by anyone in these threads.
- COLLISION: #3 says Parker's agent is not touching `app/`, then #6 claims `app/needle_app.py`. The later claim governs, but #3's statement is now stale.
- COLLISION: #3 says `drug_pack.py` is not being touched. #4 (16:48Z, commit 4d913fa) widened `find_setid` in drug_pack. Aidan's #8 also says `agent/drug_pack.py` is off-limits to moat work, so it is Parker-owned.
- UI ownership is contested: #3 says "Aidan builds the UI when he arrives about 1 pm," while #6 and #7 show Parker's agent building the Streamlit app.

## 4. Numbers corrected or changed

| What | Old | New | Where verified / thread |
|---|---|---|---|
| ABBV IRA share (Imbruvica was US-only; CMS selected Botox and Botox Cosmetic) | 16.9% | 22.5% | #10; `data/moat/verified/policy/force_summary.csv`, quotes in `policy_exposure.csv` |
| NVO US revenue share (old figure came from parent-company note, not group) | 55.0 | 56.0 | #10; force_summary |
| AMGN US share | 69.8 | 73.0 | #10; force_summary |
| AMGN forward US pledge | "$2.5bn" treated as a forward pledge | None. The $2.5bn was 2025 capex already spent | #10 |
| MRK IRA share | not stated | 3.9% today; 48.7% if Keytruda is selected in 2027 (price effective 2029-01-01) | #10; quote in table |
| PFE IRA share | 8.3% (own drugs) | 24.6% including partnered Eliquis and Xtandi. Do not sum across companies | #10 |
| NVO IRA share (group basis) | not stated | 79.9% (semaglutide alone 73.9%) | #10 |
| Manufacturing sites, spun-off or divested firms removed (Organon, Kenvue, Meridian, Upjohn) | not stated | MRK 22 sites / 68% non-US; PFE 26 / 62%; JNJ 20 / 75%. BMY, LLY, AMGN counts are floors (CBER sites not covered) | #10 |
| All 16 IRA percent cuts | n/a | Re-derived from CMS MFP and list price: all match | #10 |
| Xarelto LOE date in product table | 2025-03-03 | Wrong. Do not use on a slide. Correct date not given | #3 (Aidan's kickoff) |
| Ozempic label | oral tablet | injection, `adec4fd2` | #4 (16:48Z, commit 4d913fa) |
| Sarclisa label | ESCENA SC | IV, `a0473462` | #4 (16:48Z) |
| Janumet label | XR | `d19c7ed0` | #4 (16:48Z) |
| BMY 2025Q3 call date | (old not stated) | 2025-10-30 | #11; call_date_verified |
| NVO 2025Q3 call date | (old not stated) | 2025-11-05 | #11; call_date_verified |
| AZN 2026Q1 transcript | Corpus file is the Q2 2026 call | Real Q1 at `data/moat/companies/AZN/transcripts/` | #11; flagged in #4 (16:34Z) |
| JNJ and PFE 10-Q quarter labels | Calendar label, one quarter off fiscal | Fiscal mapping in `data/moat/verified/filings/jnj_fiscal_quarters.csv` | #9 |
| AZN consensus ticker | ZEN (stale per-ADR) | AZN only (per ordinary share; EPS 2x apart) | #12 |
| LLY FY2026 revenue | Company guidance 85 to 87 | Street consensus 88.3 (I/B/E/S Aug 20) sits above range. GILD above-guidance is definitional (IBES includes royalties) | #12; `consensus_vs_guidance.csv` |
| Restatement rows | 616 rows | 0 true restatements; 447 disclosed recasts; 157 rounding; 12 parse artifacts | #9; `restatements_triaged.csv` |
| `product_revenue_quarterly.csv` | Unverified | 448 of 448 match XBRL; 80 of 80 found on a printed page. Caveat: 3,768 rows are percent-change or milestone concepts; filter to revenue | #9 |
| MarketBeat machine transcripts (third-party errors, not our tables) | MRK Litchfield "$6.6"; JNJ Wolk "$93.7"; PFE Bourla "2030" | Official: "$3.6"; "$90"; "2023" | #11 |

Finding candidates from #9 (Opus-verified against filing text; file `data/moat/verified/filings/discontinued_breakouts.csv`)

| Candidate | Evidence (what changed) | Where verified |
|---|---|---|
| AMGN Neulasta | Gone from FY2023 10-K revenue note (printed F-20) but still in MD&A table (printed 68). FY2022 total $1,126M | #9; discontinued_breakouts.csv |
| LLY FY2025 10-K | About 12 legacy products folded into Other: Humalog US $1,503M (FY2024), Olumiant $957M, Basaglar $677M, plus Humulin, Erbitux, Emgality, Cyramza, Tyvyt. Other Cardiometabolic up about $2.5B | #9 |
| PFE FY2024 10-K | About 20 products into Other lines: Ig portfolio $584M, Zirabev $424M, Ruxience $390M, Xalkori $374M. FY2025 drops BeneFIX, Premarin, BMP2 | #9 |
| ABBV Restasis | $224M (FY2024) moved into Other Eye Care in FY2025 10-K; 2026 10-Qs collapse Other into All other | #9 |
| MRK Other Pharmaceutical | Keeps absorbing: Invanz, Cancidas (FY2023), Vaqta, Primaxin (FY2024), Noxafil (2025), Pneumovax 23, Belsomra, Pifeltro (2026 10-Qs) | #9 |

Other candidate angles (not numbers): #10 PFE partnered IRA exposure (about 3x its own-drug figure), MRK Keytruda cliff, tariff exposure where non-US site share is high and the exemption ends 2029-01-20 (MRK, JNJ, NVO). #12 AMGN SEC comment letter (2024, volume vs net price drivers) paired with AMGN being asked about gross-to-net once in 10 quarters.

## 5. Transcript quotability rule (#11)

Grades in `data/moat/verified/calls/transcript_grades.csv`:
- A = official LSEG copy, or matches one (22 transcripts)
- B = two third-party copies agree (4)
- C = single third-party copy (73)
- D = unquotable (2)

Rule as written: "Quote only from A or B, or have Parker check the quote against the Bloomberg transcript first."
- Quote from the official PDF in `data/moat/verified/calls/src/`, not third-party text. Official PDFs exist for PFE 2024Q1 to 2025Q2, MRK 2025Q2, JNJ 2024Q3 and 2025Q2 only.
- ABBV, AMGN, AZN, BMY, GILD, LLY, NVO have no official copy. Any slide quote from these must be checked against Bloomberg.
- Related rules from #4: never quote fool.com TAKEAWAYS or SUMMARY (LLM-written); GILD 2025Q3 is garbled and not quotable; AZN 2025Q3 has no speaker names.

## 6. Open requests addressed to Aidan's agent (unanswered as of #12, 19:25Z)

- #3 (Parker's handoff): sponsor, three tickers, named drugs, and case data after the 9:00 reveal. Not posted in any thread read.
- #8 (Aidan's agent to Parker's agent): "Reply here if any of this collides with your plan." No reply seen.
- #12: SEC comment-letter cross-check "verifier running now." No result posted.
- #11: Parker is pulling Bloomberg transcripts for ABBV, AMGN, AZN, BMY, GILD, LLY, NVO. Not reported done.
- Blocked, waiting on Aidan (not agent-addressed): ANTHROPIC_API_KEY in Parker's `.env` for the live `findings.py` run (#4 16:48Z), NEEDLE LLM steps (#6, #7). Per #3, R2 keys come from Aidan by text, never in threads.
- #4 (15:51Z): "Parker to review weights and priors" in `docs/materiality_spec.md`.
- Addressed to Aidan's agent and answered: work-log protocol (#3 request) is followed by Parker's agent in #4 and #7. The claim requested in #3 is posted in #3.

## 7. UI, demo, deck, video

- No thread mentions the deck, the video, or a demo script.
- UI: #3 says the UI choice is open. The options page is linked from the plan doc, with recommendation B (analyst cockpit). Aidan builds the UI when he arrives about 1 pm. Ownership conflicts with #6/#7 (Parker's agent building `app/needle_app.py`). Unresolved.
- #3: Parker owns the revenue-at-risk model.
- #6: NEEDLE is "a forensic engine for drug makers," reusable for any ticker. Every finding is page-verified, backtested on FY2020-23 filings, and turned into sealed predictions.
- #7 (17:17Z) results usable for a demo: 50-filer backtest; forensic flags predict margin compression, not revenue drops or impairments, so they are scored as review flags (`docs/needle_gate2.md`). Forecaster calibrated: 80% interval covered 79.4% of 1,793 cases. J&J Q3 2026 blind test: +7.3% forecast vs +5.9% actual. Seven Q3 2026 forecasts sealed before results (sha256 c29a6793..., `docs/needle_sealed.md`).
- #7 blocked on ANTHROPIC_API_KEY for finding prose, courtroom trial, and semantic reading steps.
