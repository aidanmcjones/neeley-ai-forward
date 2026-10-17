# NEEDLE cockpit: UI spec and data contract (first pass, Sat Oct 17 2026)

Owner: Aidan's orchestrator session. Branch `ui`, worktree `.claude/worktrees/ui`. The app lives in `ui/` (Vite + React + TypeScript + Tailwind + Recharts). It reads precomputed JSON from `ui/public/data/` written by `agent/ui_export.py`. No network, no API key needed to demo. Works with Wi-Fi off.

## What judges must get in 10 seconds, then prove in one click

The case ("The Fine Print", Advanced track) asks for: one company and why it beat nine, five or more cited findings with page numbers and impact math, a Sharpest Needle (most material, least discussed), one product vs its rivals on label / safety / dosing / exclusivity / pricing and gross-to-net, a priced-in call, then one CEO move with budget, rejected alternatives, what would prove us wrong. Plus a reusable AI build that runs on any ticker, and a "how we did it" report with at least one case where the AI was confidently wrong.

The rubric (7 categories x 4 points, equal weight): Innovation, Technical Execution, Use of AI and Responsible Design (AI essential, risks tested, human oversight), Completeness (honest limits), Design and Usability (accessibility considered), Impact, Presentation. Judges score only what is demonstrated.

Our moat, which the UI must make visible without bragging:
- 835 page-anchored source documents (10 companies, 9 rival makers, 52 drugs), every number traceable to a printed page.
- 38 derived tables (data/moat/tables), each row carrying `source` and `source_row`, verified by a second model pass (data/moat/verified) with a written log of 45 cases where the AI was wrong (data/moat/verify/ai_wrong.jsonl).
- Deterministic page verifier: every quote must appear on the cited page; rejected claims are logged live (out/<T>/rejected.jsonl).
- Hash-chained audit ledger (out/ledger.jsonl), honest backtest (v1 refuted by our own adversarial review, v2 reported with firm-clustered CIs), a calibrated forecaster (80% interval covered 79.4% of 1,793 firm-quarters), a blind J&J Q3 2026 test (hit), and sealed sha256 forecasts for 7 companies reporting Oct 29 to Nov 5.
- Any-ticker onboarding (Vertex proven) with zero configuration.
- Three-forces exposure (IRA, MFN, tariffs) per company from CMS, White House and FDA registration files; priced-in scorecard from 101 call transcripts, IBES consensus and event returns.

## Mix: 60% AI-forward, 40% metrics (B + C blend)

- Option B gives the shell: one dense cockpit, KPIs on top, a cited findings grid, charts tied to the selected row, an AI panel on the right. Every number carries a citation chip; hovering/clicking opens the exact source page with the quote highlighted.
- Option C gives the Ask pane: a question composer, an answer with a stance badge, inline citations, a visible trace of what was checked, and exhibit cards that can be pinned into the memo. Offline retrieval over the exported JSON; a live-model mode only if `ANTHROPIC_API_KEY` exists (stub it cleanly, never fake it).
- AI-forward means: the screen leads with what the engine concluded (Sharpest Needle, stance, memo, trace, AI-caught counter, courtroom verdicts where present), with teal reserved for anything model-written. Metrics means: tiles, the findings grid, peer bars, price series, forecast intervals, coverage matrix.

## Theme (from last night's decision)

Purple leads: `--purple #4D1979` (TCU Horned Frog Purple), `--purple-deep #3C145F`, `--purple-bright #6A23A7`, `--frog-grey #A3A9AC`. Teal `#007B6E` (soft `#DDF1EE`) is used ONLY for AI-written marks and panels so judges can tell model output from sourced data. Good `#1E7F4F`, warn `#B26A00`, bad `#B3261E`. Fonts: Montserrat (body), Bebas Neue (display headlines, KPI numbers), JetBrains Mono (numbers, citations). Bundle fonts locally (@fontsource), no CDN at runtime. Light theme default with dark mode via `prefers-color-scheme` and `data-theme`. Color-blind-safe: every color is paired with a text label; keyboard navigable; focus rings visible; text labels on charts. "Built by TCU Neeley students" in plain text; no TCU logo. Chrome bar logo: `NEEDLE` in Bebas Neue with the tagline "Finds what the headlines miss. Proves every claim to the page. Checks itself."

Load the `dataviz` skill before writing any chart. Charts: Recharts, with text labels and tabular numbers; the palette above.

## Screens (left nav, single-page app, react-router, demo state preloaded)

Chrome bar on every screen: NEEDLE logo, company picker (10 tickers + "Onboarded: VRTX" if present), "As of <date>" pill, "⌘K Ask" button opening the Ask pane as a command palette.

1. `/` **Briefing** (the cockpit, opens here). KPI row: Findings verified | AI claims rejected | Ledger (intact, N records) | Sources (835 docs, 52 drugs). Left (60% width): the findings grid for the selected company (columns: Finding, Impact $, Peer z, Confidence, Obscurity, Verdict, Source chips), sortable, row select drives two charts below (peer comparison bar: this company vs peer median; trend or impact bear/base/bull). Right (40%): the AI panel: AI mark, "Sharpest Needle" headline (the needle finding sentence), confidence pill, three "why" bullets with citation chips, the stance block (Defend / Attack / Reprice / Partner rows with $ bars from `stance.options`), "Generate CEO memo" and "Ask a follow-up" buttons, and a live source card showing the quote for the hovered chip.
2. `/ask` **Ask NEEDLE** (Option C). Left: question threads (presets from `questions.json` per company plus the user's own). Main: the question bubble, the answer (stance badge + prose with inline cite chips), the trace chips (documents checked), exhibit cards (timeline, head-to-head table, chart) each with "Pin to memo", source cards, composer at the bottom with "Draft CEO memo from pins". Offline answers: a client-side retriever over findings, label table, forces and priced-in rows (token match + topic/drug synonyms) composes an answer from matching findings, always citing. If no match, say so honestly and suggest the nearest presets. If `window.__NEEDLE_LIVE__` (set when `ui/server.py` is running with a key), send the question to `/api/ask` and stream; show a "live model" pill in teal.
3. `/product` **Product fine print**. Product picker (the company's case-set products). Side-by-side table product vs rivals: approved uses (count + list), boxed warning, REMS, dosing frequency per year, route, exclusivity best estimate (company-stated vs FDA), biosimilar/generic status, IRA status + MFP, Medicare Part D/B spend, GTN exposure call. Below: price series chart per drug (Part D gross per unit, NADAC brand, ASP, MFP line) from `price_series`; "What limits growth" one-sentence verdict with the priced-in call; label-linked findings list (signals from the labels detector).
4. `/forces` **Three forces and priced-in**. Top: the 10-company comparison (small multiples or a sortable table) of IRA share of revenue, MFN date, US investment pledge, tariff exemption, share of manufacturing sites outside the US, US revenue share. Middle: priced-in scorecard for the selected company: topic x (analyst attention tier, quarters asked, unasked streak, abnormal return when asked vs not). Bottom: consensus vs guidance gap, IRA cut check table (CMS % cut recomputed and matched).
5. `/proof` **Proof: does it hold up?** The responsible-AI screen. (a) Verifier: what it checks, counts verified/rejected per company, the AI-caught table (rejected claims + the 45 `ai_wrong` rows grouped by stream, with "how caught"). (b) Backtest: the refuted v1 claim and the v2 table with lifts and firm-clustered CIs; dose-response bar chart (margin-drop rate vs signals fired). (c) Forecaster calibration tiles. (d) J&J blind test card (forecast interval vs actual, hit). (e) Sealed forecasts table with the stored sha256 and a "Verify seal" button that recomputes sha256 in the browser (SubtleCrypto) over `proof.sealed.canonical` and compares to the file and the committed docs hash. (f) Limits we state plainly (from materiality spec section 8 and the no-free-source table).
6. `/moat` **Data moat**. Coverage matrix (companies x 10 buckets, from progress.json, same bar style as the tracker), the 38 tables with row counts, what each is and its source, the "No free source for anyone" table with our proxy, the corpus trust levels (official vs third-party transcripts, grades A/B/C), and the any-ticker onboarding card (VRTX). This screen answers "what did you build this weekend" and "where does the data go".
7. `/memo` **CEO memo**. One page: TO/FROM line, decision headline (the move in one sentence), "Decision needed", three cited points, the stance options with $ bars, rejected alternatives, what would prove us wrong in 6 to 12 months, who decides its fate. Pinned exhibits render inline. Print stylesheet for Export PDF (window.print). Memo text comes from `stance` in the company JSON; the user can edit it inline (contentEditable) and pins persist in localStorage (wrapped in try/catch).
8. Source drawer (global): opens from any citation chip. Shows citation label (e.g. "BMY 10-K FY2025, p. 39"), the EDGAR/DailyMed URL, the page excerpt with the quote highlighted, speaker for calls, figures checked, the verifier status, and the transcript grade when it is a call.

## Data contract: `ui/public/data/`

All numbers in JSON are plain numbers; dollars in USD. Strings never contain HTML.

`meta.json`
```
{ as_of, default_ticker, companies:[{ticker,name}], onboarded:[ticker],
  totals:{verified, rejected, findings, high_confidence},
  ledger:{ok, n, bad},
  corpus:{docs, companies, peers, drugs, transcripts, transcripts_official, pages},
  moat:{as_of, coverage:{<ticker>:{<bucket>:{have,need,note}}}, buckets:[{key,label,why}], status:{<bucket>:[collect,verify]},
        tables:[{name, rows, what, list_or_net, source}], no_source:[[missing, who_sells, proxy]], stages:[[name,status,text]]},
  case_sets:{<ticker>:{<product>:[rivals]}},
  verifier_rules:[string], limits:[string] }
```

`league.json`: `[{ticker, name, score, n_findings, n_verified, n_rejected, high_confidence, sharpest_needle, needle_id}]` sorted by score.

`companies/<TICKER>.json`
```
{ ticker, name, needle_id,
  findings:[{ id, finding, signal_kind, detector, score, score_norm, confidence, verdict, reason,
              impact:{formula, dollars, base, bear, bull, line, eps}, peer:{metric_value, peer_median, z, note},
              vector:{I_norm,P,T,Z,D,O,E, obscurity_note, topics:[]}, hit_rate, outside,
              evidence:[{ doc_id, page, printed, citation, quote, speaker, figures, url, doc_type, source_quality, grade,
                          excerpt:{before, match, after} }] }],
  rejected:[{finding, reason, verdict, signal_kind}],
  labels: <out/<T>/labels_table.json as-is, plus a normalized `comparison` array: [{product, rivals:[...], rows:[{field, label, values:{<slug>:{value, source}}}]}]>,
  forces:{...force_summary row...},
  priced_in:[rows from verified/market/priced_in_scorecard.csv for ticker],
  never_asked:[rows], consensus_vs_guidance:{row}, ira_cut_check:[rows], comment_letters:[rows],
  discontinued_breakouts:[rows], transcript_grades:[rows],
  gtn_exposure:[rows for the company's case-set drugs and rivals],
  price_series:{<slug>:[{year, partd_per_unit, nadac_brand, asp, mfp_per_unit, mfp_per_30day}]},
  stance:{ headline, confidence, bullets:[{text, cites:[evidence ref {finding_id, i}]}],
           options:[{name, dollars, share, rationale}], recommended, decision_needed, memo_points:[{text, cites}],
           alternatives:[{name, why_rejected}], prove_wrong:[string], deciders:[string], generated_by:"template|model", note },
  questions:[{id, q, answer:{stance, text, cites:[{finding_id, i}], trace:[doc labels], exhibits:[{kind, ref}]}}] }
```
`stance` is deterministic and templated from the top verified findings when no API key is present; `generated_by` says so and the UI shows "Drafted from verified findings" (teal AI mark) rather than pretending a model wrote prose.

`proof.json`
```
{ backtest:{ hit_rates: <out/backtest/hit_rates.json>, gate2_md: <docs/needle_gate2.md text>, examples },
  calibration: <out/predictions/calibration.json>, blind: <blind_JNJ_2026Q3.json>,
  sealed:{ file: <sealed_2026Q3.json>, canonical: <exact string audit.seal hashes>, doc_hash: <from docs/needle_sealed.md> },
  ai_wrong:[rows of data/moat/verify/ai_wrong.jsonl], verifier_rules:[...], limits:[...] }
```

## Deterministic retriever for Ask (offline)

Index each finding (text, topics, signal_kind, drug slugs mentioned, evidence citations), each label comparison row, each forces field, each priced-in row. Query handling: lowercase, strip stopwords, expand synonyms (IRA ~ negotiation ~ Medicare price; LOE ~ exclusivity ~ generic ~ biosimilar ~ patent; GTN ~ rebate ~ net price; inventory ~ channel ~ stocking; call ~ Q&A ~ deflect). Score by term overlap with boosts for drug names and ticker; return top 5 findings. Compose: stance badge if a matching stance exists, 2 to 4 sentences each citing a finding, trace = the distinct documents behind those findings, exhibits = timeline if the question mentions dates/exclusivity, head-to-head table if it names two drugs, peer chart otherwise. Never invent numbers: every sentence reuses a finding sentence or an impact formula string verbatim.

## Non-negotiables

- Every number on screen has a citation chip or a tile footnote naming the file it came from.
- Teal only for model output. Purple for sourced data and navigation.
- No external network at runtime. Fonts bundled. `npm run build` must produce a static `ui/dist` that opens via `npx serve` or `python -m http.server`.
- Keyboard: tab through chips, Enter opens the drawer, Esc closes, ⌘K opens Ask.
- Phone width does not matter; the demo laptop is 13 to 16 inches at 1280 to 1728 px wide. Must not break at 1280.
- Honest empty states: if a file is missing say which file, never silently blank.
