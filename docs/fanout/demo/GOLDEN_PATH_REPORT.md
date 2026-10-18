# Golden path report (demo stream)

Checked Sat Oct 17 2026, evening, branch `needle` at bcff214 plus the uncommitted working tree. Nothing in the repo
was edited or committed; every fix below is a proposal. No company has been picked: every screen was checked against
the four candidates (MRK, JNJ, AMGN, AZN), and the Streamlit render was checked for all 10 league companies.

## Verdict at a glance

| # | Screen | Verdict | Works for | One-line reason |
|---|---|---|---|---|
| 0 | Launch | FAIL (docs) | all | README and HANDOFF say `streamlit run app/main.py`, which is the old placeholder. The demo is `app/needle_app.py`. |
| 1 | Briefing: Sharpest Needle with dollar math | FAIL | none | No needle panel and no dollar figure on the League tab. The engine's needle string is not the team's needle, for every candidate. |
| 2 | Click citation: page with quote highlighted | PASS (data), RISK (render) | all 4 | 100% of quotes resolve and highlight for all 4 candidates. Page box likely renders `$` as math and breaks out of its `<div>`. Not a click: an expander. |
| 3 | AI caught | FAIL | none | 0 rejections for all 4 candidates; the 8 global rejections (LLY, NVO) are detector false positives, not AI claims. The real AI step (trial.py) has never run and needs an API key that is not set. |
| 4 | Proof: sealed hash + backtest | PASS, with wording fixes | company-neutral | Seal verifies (`c29a6793...6e67e65`), ledger intact (1915 entries). Hash is computed server-side in Python, not "in the browser". The refuted v1 backtest sits on tab 4, not Proof. Sealed forecast covers MRK and AMGN but not JNJ or AZN. |
| 5 | Live onboard | FAIL in the app | CLI only | No UI path. An onboarded ticker never appears in the selector (VRTX fallback included). Onboard writes into git-tracked `data/corpus`. RESULTS_ONBOARD |
| - | pytest | PASS | - | 49 passed, 0 failed, 0 skipped, 2m26s. No network, no API key. No onboarding test. |
| - | Streamlit smoke | PASS | all 10 | Headless start 11.5 s, health 200. AppTest: 0 exceptions on every company, every tab. |
| - | `.env`, API key, offline | PASS for demo, FAIL for `agent.llm` | - | Key absent. The demo path makes no LLM call, so it is fully offline. `python -m agent.llm` crashes with TypeError. |
| - | `python -m agent.needle.run` timing | PASS (slower than claimed) | - | `--ticker MRK` 69.7 s wall, `--all` 272.8 s (HANDOFF says about 50 s). Byte-identical findings for all 10; no network, no LLM. Positional `run MRK` errors. |

## Severity ranking against the Sun 10:30 am freeze

| Rank | Sev | Issue | Screen | Fix effort |
|---|---|---|---|---|
| 1 | P0 | The team's Sharpest Needle (docs/nuggets/<T>.jsonl, `-nugget-001`) is not shown anywhere in the app, for any candidate, and no dollar figure is on the Briefing screen | 1 | 30 min (diff 1B) |
| 2 | P0 | "AI was confidently wrong [N] times" has no honest N: 0 for every candidate; the 8 global rejections are code false positives | 3 | 15 min to reword the script; 45 min plus API key to run trial.py |
| 3 | P0 | Onboarded ticker and VRTX fallback are invisible in the app | 5 | 5 min (diff 5A) |
| 4 | P1 | Wrong launch command in README.md:14 and HANDOFF.md:54 | 0 | 2 min |
| 5 | P1 | Default company is the league leader (AZN), not the picked company | 1 | 2 min (diff 1A) |
| 6 | P1 | Source-page box: `$` amounts may render as LaTeX, blank lines may break the styled `<div>` | 2 | 10 min (diff 2A); needs a 1-minute eyeball check |
| 7 | P1 | Supply evidence citing distributor filings (CAH, COR) and the MRK needle's BMY evidence is rejected as "unknown source" because the re-check loads only the company's own docs | 3, 1 | 10 min (diff 3C), then rerun |
| 8 | P1 | Demo line "hash recomputed in the browser" is false (Python, server side); "skeptics refuted" backtest is on the AI caught tab, not Proof | 4 | 5 min script edit (diff 4A); 10 min to move the expander (4B) |
| 9 | P2 | Live onboard has no try/except around DailyMed/RxClass; one 5xx kills the run on venue Wi-Fi | 5 | 15 min (diff 5C) |
| 10 | P2 | JNJ's needle has 1 of 7 evidence items stuck at `needs_human` (call quote with no speaker) | 1, 2 | 5 min data fix if JNJ is picked |
| 11 | P2 | `python -m agent.llm` crashes (no key, no offline fallback, no timeout) | - | 10 min (diff 6A) plus add the key |
| 12 | P3 | `use_container_width` deprecation warnings (6 places); zero-width chars in quotes; quotes cut at 400 chars without "..." | 2 | 10 min |
| 13 | P3 | `run.py` rejects `python -m agent.needle.run MRK` (needs `--ticker MRK`); `--all` takes 4.5 min, not 50 s; labels exclusivity order varies with hash seed (AMGN, BMY) | - | 5 min (diffs 7A, 7B) |
| 14 | P3 | `out/` is gitignored: a fresh clone shows "No engine output found". Demo must run on this laptop | all | process only |

## Company-neutral matrix (Parker's request)

Checked with read-only scripts against `out/<T>/`, `out/league.json`, `docs/nuggets/<T>.jsonl` and the page verifier.

| Check | MRK | JNJ | AMGN | AZN |
|---|---|---|---|---|
| League rank (engine score) | 2 (0.099) | 7 (0.043) | 5 (0.069) | 1 (0.133) |
| Selected by default in the app | no | no | no | yes (league leader) |
| Engine "sharpest needle" (league.json) | `MRK-calls-879939`: a truncated analyst question, no dollars | `JNJ-drift-013893`: MD&A wording drift, no dollars | `AMGN-forensics-004011`: receivables gap, $0.70B | `AZN-forensics-328835`: receivables gap, $1.22B |
| Team needle (`-nugget-001`) | Keytruda royalty ends 2026, $821M base, +$0.28 EPS | Genmab royalty disclosed, $1,382M base, +$0.47 EPS | Receivables flag is gross-to-net artifact, $382M, -$0.59 EPS | US gross-to-net squeeze, $1,804M base, +$0.93 EPS |
| Team needle shown in app | no | no | no | no |
| Team needle evidence verifies (all docs loaded) | 12/12 | 6/7 (1 `needs_human`) | 7/7 | 6/6 |
| ...with only the company's own docs (how score.py checks) | 8/12 (4 BMY pages "unknown source") | 6/7 | 7/7 | 6/6 |
| Findings with a dollar impact | 1/73 | 1/70 | 1/74 | 2/60 |
| Screen 2: findings that resolve to a page | 73/73 | 70/70 | 74/74 | 60/60 |
| Screen 2: evidence quotes that highlight in full | 64/64 | 72/72 | 73/73 | 59/59 |
| Screen 3: rejected.jsonl rows | 0 | 0 | 0 | 0 |
| Screen 3: ai_caught.jsonl exists | no | no | no | no |
| Screen 4: in sealed 2026Q3 forecast | yes | no (has the separate blind test, HIT) | yes | no |
| AppTest render, all 5 tabs | 0 exceptions | 0 exceptions | 0 exceptions | 0 exceptions |

Screens that only work for some candidates:
- Screen 1: the engine's needle carries a dollar figure only for AMGN and AZN. For MRK and JNJ the League tab
  needle is a non-dollar text signal. With fix 1B (show the team nugget) all four get dollar math.
- Screen 4: the sealed forecast names MRK and AMGN. If JNJ or AZN is picked, the "our forecast for your company is
  sealed" line does not apply (JNJ can use the blind test instead; AZN has neither).
- MRK only: its needle evidence cites BMY pages, which the current single-company re-check rejects. Harmless today
  (nuggets are not re-checked by the app), but it will bite if fix 1B adds a live verify badge without fix 3C.
- Screens 2, 3 and 5 behave the same for all four (2 passes, 3 and 5 fail).

---

## Screen 0: launch

**FAIL (docs only).** `README.md:14` and `HANDOFF.md:54` say `streamlit run app/main.py`. That file is the hello-world
"Pharma decision copilot" (title caption: "Placeholder title. Replace with the one-liner..."). Its Run button calls the
LLM and would crash with no key. The NEEDLE demo is `app/needle_app.py`.

Repro: `streamlit run app/main.py` and see "Pharma decision copilot".

```diff
--- a/README.md
+++ b/README.md
-streamlit run app/main.py   # opens the app at localhost:8501
+streamlit run app/needle_app.py   # opens the NEEDLE demo at localhost:8501
--- a/HANDOFF.md
+++ b/HANDOFF.md
-streamlit run app/main.py
+streamlit run app/needle_app.py
```

## Screen 1: Briefing (League tab), Sharpest Needle with dollar math

**FAIL for every candidate.** The tab renders without errors, but:

1. **No Sharpest Needle panel.** Tab 1 is a dataframe with a "Sharpest needle" text column (`app/needle_app.py`
   lines 202, 213) plus a bullet list of every company's needle (lines 217-219). `money()` is never called on this tab,
   so no dollar figure appears.
2. **Wrong needle.** The app shows `score.sharpest_needle()`, which needs O >= 0.7 and picks, for example, MRK's
   "Robert Davis deflected a question in 2025Q3 ('not going to get into'); asked: 'Hi everyone, thanks so much...'"
   (score 0.005, `impact.dollars = null`). The team's needles live in `docs/nuggets/<T>.jsonl` (`-nugget-001`), and
   `docs/red_team_v2_company_pick.md` line 136 already says the league needle strings are "Mechanical or truncated...
   League rank is not a selector". `needle_app.py` never reads `docs/nuggets/` (no match for "nugget").
3. **Default company is AZN** (line 180, no `index=`; `tickers` follows league order). The presenter must pick the
   company by hand. Tab 1 ignores `selected` entirely.
4. **"[COMPANY] on top"** in demo_script.md is only true if AZN is picked. Do not change scores to fake it.

Repro: `streamlit run app/needle_app.py`; the dropdown shows AZN; League tab; no $ figure; needle strings as above.
Read-only: `python -I -c "import json;print([(r['ticker'],r['score'],r['needle_id']) for r in json.load(open('out/league.json'))])"`

Unit trap for any fix: nugget impact is `base`/`bear`/`bull` in $M with no `dollars` key; `money()` expects dollars.

```diff
--- a/app/needle_app.py
+++ b/app/needle_app.py
@@ -177,7 +177,9 @@
-selected = st.selectbox("Company (drives the Findings, Fine print and AI caught tabs)", tickers, key="company")
+DEMO = os.environ.get("NEEDLE_DEMO", "")  # set to the picked ticker; empty keeps league order
+selected = st.selectbox("Company (drives the Findings, Fine print and AI caught tabs)", tickers,
+                        index=tickers.index(DEMO) if DEMO in tickers else 0, key="company")
@@ -187,6 +189,24 @@
 with tab_league:
+    nug = read_jsonl(f"docs/nuggets/{selected}.jsonl")
+    if nug:
+        n0 = next((r for r in nug if r.get("id", "").endswith("-001")), nug[0])
+        imp = n0.get("impact") or {}
+        st.subheader(f"{selected}: Sharpest Needle")
+        st.markdown(f"**{n0.get('finding', '')}**")
+        if imp.get("base") is not None:  # nugget impact is in $M
+            st.markdown(
+                f"Impact: **{money(imp['base'] * 1e6)}** base (bear {money((imp.get('bear') or 0) * 1e6)}, "
+                f"bull {money((imp.get('bull') or 0) * 1e6)})"
+                + (f", EPS {imp['eps']:+.2f}" if imp.get("eps") is not None else ""))
+        if imp.get("formula"):
+            st.caption(imp["formula"])
+        ev = (n0.get("evidence") or [{}])[0]
+        if ev.get("citation"):
+            st.caption(f"Source: {ev['citation']}")
+        st.divider()
     st.subheader("Which companies hide the most in their filings?")
```
(Needs `import os` at the top if not already imported.) Diff 1A is the selectbox hunk, 1B the nugget panel.

```diff
--- a/demo_script.md
+++ b/demo_script.md
-| 1 | Open Briefing for [COMPANY] (League tab) | All 10 companies ranked, [COMPANY] on top, its Sharpest Needle with impact math | ...
+| 1 | Open Briefing for [COMPANY] (League tab) | [COMPANY]'s Sharpest Needle with its dollar range and EPS and the page it comes from, then all 10 companies ranked by the engine | ...
```

## Screen 2: click the citation, see the page with the quote highlighted

**Data PASS for all four candidates; render RISK.** Script:
`C:\Users\parke\AppData\Local\Temp\claude\C--Users-parke-OneDrive-Desktop-Hackathon\e95f21fe-858a-4010-8a31-b2baa876196e\scratchpad\screen2_check.py`
(uses the real `agent.needle.pages`; copies `doc_source()` and `highlight()` verbatim). Run: `python -B <script> . <TICKER>`.

- Every finding resolves (MRK 73/73, JNJ 70/70, AMGN 74/74, AZN 60/60), every evidence quote highlights on the full
  quote (64/64, 72/72, 73/73, 59/59), no missing docs, no out-of-range pages, labels highlight in label mode.
- Printed page numbers are right: e.g. "file page 49 (printed 47)" and the citation "MRK 10-K FY2025, p. 47" match the
  filing footer.
- Findings with no evidence (MRK: 25, all `needs_human`) show an empty "Evidence (0)" expander.
- **It is not a click on a citation.** The judge opens Findings, then expands "Evidence and source pages (N)". Say "open
  the evidence". Nothing links to the SEC original.
- **Render risk (not seen in a browser; AppTest only checks the markdown string):**
  1. `st.markdown(f'<div class="srcpage">{marked}</div>', unsafe_allow_html=True)`: a raw HTML block ends at the
     first blank line; cited pages have dozens, so the box styling and scroll may be lost and `#`, `*`, `_` become
     formatting.
  2. `html.escape` does not escape `$`. Pages like MRK 10-Q p.3 ("Sales $ 16,607 $ 15,806 ...") can render as LaTeX.
  3. The "Quote:" line has the same `$` issue, cuts at 400 chars with no "...", and shows zero-width characters.

**Pre-freeze check (1 minute):** pick each finalist company, Findings, expand the top finding's evidence, confirm the
text sits in the bordered scrolling box and "$ 16,607" is plain text.

```diff
--- a/app/needle_app.py
+++ b/app/needle_app.py
@@ def highlight(text, quote, label_mode=False, window=1500):
-    out = html.escape(text[lo:s]) + "<mark>" + html.escape(text[s:e]) + "</mark>" + html.escape(text[e:hi])
+    # one-line HTML so markdown never ends the <div> block; &#36; stops $...$ math rendering
+    esc = lambda x: html.escape(x).replace("$", "&#36;").replace("\n", "<br>")
+    out = esc(text[lo:s]) + "<mark>" + esc(text[s:e]) + "</mark>" + esc(text[e:hi])
     return out, None
@@ with tab_find:
-                        st.markdown(f"Quote: *{ev['quote'][:400]}*")
+                        q = ZW.sub("", ev["quote"])
+                        q = q[:400] + ("..." if len(q) > 400 else "")
+                        st.markdown("Quote: *" + q.replace("$", r"\$").replace("*", r"\*") + "*")
@@
-                            st.markdown(f'<div class="srcpage">{html.escape(fallback)}</div>', unsafe_allow_html=True)
+                            st.markdown('<div class="srcpage">' + html.escape(fallback).replace("$", "&#36;").replace("\n", "<br>") + "</div>", unsafe_allow_html=True)
```
(`ZW` is the zero-width regex already used in the file; if not, define `ZW = re.compile("[\u200b\u200c\u200d\ufeff]")`.)

## Screen 3: AI caught

**FAIL for every candidate.** Exact app text for MRK (same for JNJ, AMGN, AZN): "No rejected claims recorded for MRK.
That means every claim the engine produced passed the verifier, not that nothing was checked. Totals across companies:
473 verified, 8 rejected." The header tile says "AI claims rejected: 8".

- `out/<T>/rejected.jsonl` is empty for all four. The 8 global rows are LLY 4 and NVO 4.
- **None of the 8 is an AI claim.** All are `signal_kind=distributor_commentary` from the rule-based
  `agent/needle/detect/supply.py`, with template text ("CAH filing paragraph that discusses the GLP-1 class ...").
- **The 8 rejections are themselves wrong.** `score_ticker` loads only `pages.docs(ticker)` (`score.py` line 222). The
  quotes cite Cardinal Health and Cencora filings, so they fail with e.g. `unknown source 'CAH:10k_FY2026.md#p7'`.
  With the CAH/COR docs loaded, all 4 LLY quotes verify.
- **The real AI step has never run.** `agent/needle/trial.py` (prosecutor, defense, judge) is the only LLM caller; it
  writes `out/<T>/ai_caught.jsonl` and `trials.jsonl`. Neither exists for any company; the ledger has 0 `verdict`
  entries; the tab does not read `ai_caught.jsonl`. `ANTHROPIC_API_KEY` is not set, so it cannot run now.
  `python -m agent.needle.trial --ticker MRK --dry-run` passes (5 findings, about 21k to 24k chars of context each).

Repro: `wc -l out/*/rejected.jsonl`; `find out -name ai_caught.jsonl` (nothing); app, any candidate, AI caught tab.

Options, in order of preference:
- **A (needs key, about 45 min):** add the key, run `python -m agent.needle.trial --ticker <PICK> --top 5` once online
  (fills `agent/cache/`, writes `ai_caught.jsonl`), apply diff 3B, quote N = its line count. If N is 0, use the reword.
- **Reword (2 min, no key):** "Every quote the AI or the engine cites is re-checked against its page; here is what the
  checker tests." Do not say N = 8.

```diff
--- a/app/needle_app.py
+++ b/app/needle_app.py
@@ -173,2 +173,2 @@
-c3.metric("AI claims rejected", f"{total_rejected:,}")
+c3.metric("Claims rejected by the verifier", f"{total_rejected:,}")
@@ -307,17 +307,29 @@
 with tab_ai:
     st.subheader("AI claims the verifier threw out")
-    rej = read_jsonl(f"out/{selected}/rejected.jsonl")
-    if rej:
+    caught = read_jsonl(f"out/{selected}/ai_caught.jsonl")
+    if caught:
+        st.markdown(f"**The AI was confidently wrong {len(caught)} times for {selected}.**")
         st.dataframe(
             pd.DataFrame(
-                [{"Claim": r.get("finding", ""), "Why rejected": r.get("reason", ""), "Verdict": r.get("verdict", "")} for r in rej]
+                [{"Role": r.get("role", ""), "Quoted": r.get("quote", ""), "Cited": r.get("source", ""),
+                  "Why rejected": r.get("reason", ""), "Verdict": r.get("verdict", "rejected")} for r in caught]
             ),
             hide_index=True,
             use_container_width=True,
         )
     else:
-        note(...)
+        note(f"No AI trial log (out/{selected}/ai_caught.jsonl) for {selected} yet.")
+    rej = read_jsonl(f"out/{selected}/rejected.jsonl")
+    if rej:
+        with st.expander(f"Detector evidence that failed the page re-check ({len(rej)})"):
+            st.dataframe(pd.DataFrame([{"Claim": r.get("finding", ""), "Why rejected": r.get("reason", "")} for r in rej]),
+                         hide_index=True, use_container_width=True)
```

Diff 3C, stop the false rejections (also makes the MRK needle's BMY evidence verify):
```diff
--- a/agent/needle/score.py
+++ b/agent/needle/score.py
@@ def score_ticker(ticker):
     docs = pages.docs(ticker)
+    cited = {e.doc_id.split(":")[0] for f in findings for e in f.evidence}  # adapt to the local variable names
+    for t in cited - {ticker}:
+        docs.update(pages.docs(t))
```
Then rerun `python -m agent.needle.run --all`; the global rejected count should go from 8 to 0.

## Screen 4: Proof

**PASS, with two wording fixes.** Company-neutral.

- Seal: method `audit.seal(body)` = sha256 of `json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",",":"))`
  in UTF-8, body = all keys except `sha256`.
  - recomputed `c29a6793953a388544c9bfd613e367f32b4e26729e730051238ddd8bd6e67e65` = the file's `sha256` = docs/needle_sealed.md = ledger seq 3.
  - One commit (c1b6cd2, 17:05Z, 15 s after `made_at`); `git diff` empty; all 7 outcomes still open
    (MRK, BMY, LLY, PFE, ABBV, AMGN, GILD). JNJ and AZN are not in the sealed forecast.
  - The "Verify seal" button prints "SEAL VERIFIED".
  - `chain_status()` returns `(True, 1915, None)`; header shows "Ledger Intact".
- **"Recomputed in the browser" is false.** No JavaScript or `crypto.subtle` anywhere; the button runs Python on the
  server.
- **CRLF trap:** working copy is CRLF, commit is LF (`core.autocrlf=true`). `sha256sum` of the file gives
  `6142a43d...` (CRLF) or `a5cbab2e...` (LF), neither the documented hash. If a judge runs sha256sum, the answer is
  "canonical JSON, not file bytes".
- **Cache trap:** `read_json`, `read_text`, `chain_status` use `@st.cache_data`; a live tamper demo while the app runs
  would still say VERIFIED.
- Backtest renders (5 signals, hard-event lift 0.82 to 1.25, every 95% CI includes 1; calibration k 1.4, 79.4%
  coverage, 1,793 cases; J&J blind test HIT, +5.9%). The v1 "skeptics refuted it" story is in an expander on the AI
  caught tab (lines 333-338), not on Proof.

Repro:
```
python -c "import json;from agent.needle import audit;d=json.load(open('out/predictions/sealed_2026Q3.json'));print(audit.seal({k:v for k,v in d.items() if k!='sha256'}), d['sha256']);print(audit.verify_chain())"
```

Diff 4A (script):
```diff
--- a/demo_script.md
+++ b/demo_script.md
-| 4 | Open Proof | Sealed Q3 2026 forecast hash recomputed in the browser; the backtest that our own skeptics refuted |
+| 4 | Open Proof | Sealed Q3 2026 forecast: click Verify seal to recompute its hash live against the git-committed record; the backtest our own skeptics refuted |
```
Diff 4B (app):
```diff
--- a/app/needle_app.py
+++ b/app/needle_app.py
@@ tab 5, after the backtest v2 st.warning(...)
+    g2p = read_text("docs/needle_gate2.md")
+    if g2p:
+        with st.expander("Backtest v1, and how our AI skeptics refuted it"):
+            st.markdown(g2p)
@@ if st.button("Verify seal"):
-                body = {k: v for k, v in sealed.items() if k != "sha256"}
+                sealed = json.loads((ROOT / "out/predictions/sealed_2026Q3.json").read_text(encoding="utf-8"))  # bypass cache
+                body = {k: v for k, v in sealed.items() if k != "sha256"}
                 calc = audit.seal(body)
-                md = read_text("docs/needle_sealed.md") or ""
+                md = (ROOT / "docs/needle_sealed.md").read_text(encoding="utf-8")
```
Diff 4C (docs/needle_sealed.md): add "sha256 of canonical JSON (sort_keys, compact separators, UTF-8), not of the file
bytes, which change with CRLF/LF checkout." Optional `.gitattributes`: `out/predictions/*.json text eol=lf`.

## Screen 5: Live onboard

**FAIL in the app; CLI works.** RESULTS_ONBOARD_DETAIL

Static review:
- **No UI path.** `needle_app.py` is read-only (no text input, no subprocess). Presenter command, repo root:
  `python -m agent.needle.onboard <TICKER> --products 2 --rivals 1` (it runs `agent.needle.run --ticker` itself).
  Needs `SEC_USER_AGENT` (present in `.env`); does **not** need the Anthropic key.
- **The new ticker never shows in the app.** Line 156:
  `tickers = [r["ticker"] for r in league] or sorted(glob out/*/findings.jsonl)`; the glob only runs if league.json is
  empty, and `run.py` rewrites the league only for multi-ticker runs. Same for the VRTX fallback: `out/VRTX` exists
  (27 findings) but the app never offers it. "Already proven" is true for the CLI only.
- **Writes into git-tracked files:** `data/corpus/onboarded/<T>/`, `data/corpus/drugs/<slug>/`,
  `data/corpus/manifest.jsonl` (all tracked), plus `out/<T>/` and `out/ledger.jsonl` (ignored). Run `git stash` or
  `git checkout -- data/corpus` after the demo.
- **Network:** SEC EDGAR (8 req/s throttle, `company_tickers_exchange.json` fetched fresh each run), NLM RxClass,
  DailyMed. CMS, Orange Book, Purple Book, IRA come from gitignored `data/external/` (present on this laptop only).
  RxClass and DailyMed calls have no try/except.
- **Edge tickers:** unknown ticker exits cleanly ("unknown ticker X"). 20-F filers other than NVO/AZN go down the 10-Q
  path in forensics (`ANNUAL_ONLY` is hardcoded) and get no forensics signals. Products match on a Part D manufacturer
  name prefix, so ADR names that differ from CMS names (GSK) find 0 products. A non-pharma ticker downloads minutes of
  filings and ends with an empty case set. Steer judges to US 10-K drugmakers.

Diff 5A (required, 5 min):
```diff
--- a/app/needle_app.py
+++ b/app/needle_app.py
@@ -155,3 +155,5 @@
 league = read_json("out/league.json") or []
-tickers = [r["ticker"] for r in league] or sorted(p.name for p in OUT.glob("*") if (p / "findings.jsonl").exists())
+_ranked = [r["ticker"] for r in league]
+_onboarded = sorted(p.name for p in OUT.glob("*") if (p / "findings.jsonl").exists() and p.name not in _ranked)
+tickers = _ranked + _onboarded  # onboarded companies (VRTX, live picks) are selectable though not in the league
```
Diff 5B (optional, onboarding box in the app):
```diff
+with st.expander("Onboard any drug maker (live)"):
+    new_t = st.text_input("Ticker", max_chars=6, key="onboard_ticker").strip().upper()
+    if st.button("Build cited dataset", disabled=not re.fullmatch(r"[A-Z.\-]{1,6}", new_t or "")):
+        import subprocess
+        with st.status(f"Onboarding {new_t}: SEC filings, FDA labels, Part D, detectors...", expanded=True) as s:
+            p = subprocess.run([sys.executable, "-m", "agent.needle.onboard", new_t, "--products", "2", "--rivals", "1"],
+                               cwd=ROOT, capture_output=True, text=True, timeout=900)
+            st.code((p.stdout or "")[-3000:] + (p.stderr or "")[-1500:])
+            s.update(label=f"{new_t} done" if p.returncode == 0 else f"{new_t} failed (exit {p.returncode})",
+                     state="complete" if p.returncode == 0 else "error")
+        if p.returncode == 0:
+            st.cache_data.clear()
+            st.session_state["company"] = new_t
+            st.rerun()
+
 selected = st.selectbox(...)
```
Diff 5C (survive a flaky DailyMed/RxClass call):
```diff
--- a/agent/needle/onboard.py
+++ b/agent/needle/onboard.py
     for p in prods:
-        pslug, ok = build_pack(manifest, bulk, p["Brnd_Name"], p["Gnrc_Name"], key, ticker)
+        try:
+            pslug, ok = build_pack(manifest, bulk, p["Brnd_Name"], p["Gnrc_Name"], key, ticker)
+        except Exception as e:
+            print(f"  skip {p['Brnd_Name']}: {type(e).__name__}: {e}"); continue
         packs.append({"slug": pslug, "label": ok, "spend_2024": p["spend"]})
         rs = []
-        for r in rivals(d, key, p, n_rivals):
-            rslug, rok = build_pack(manifest, bulk, r["Brnd_Name"], r["Gnrc_Name"],
-                                    company_key(r["Mftr_Name"]), r["Mftr_Name"])
+        try:
+            rv = rivals(d, key, p, n_rivals)
+        except Exception as e:
+            print(f"  rivals skipped for {p['Brnd_Name']}: {e}"); rv = []
+        for r in rv:
+            try:
+                rslug, rok = build_pack(manifest, bulk, r["Brnd_Name"], r["Gnrc_Name"],
+                                        company_key(r["Mftr_Name"]), r["Mftr_Name"])
+            except Exception as e:
+                print(f"  skip rival {r['Brnd_Name']}: {e}"); continue
```
RESULTS_ONBOARD_DIFFS

## Supporting checks

### pytest: PASS
`python -m pytest tests -q -p no:cacheprovider`: **49 passed, 0 failed, 0 errors, 0 skipped**, 145.85 s. HANDOFF says
48 (stale). No test needs the network or the API key. `test_app.py` drives `app/needle_app.py` via AppTest (5 tabs,
10 companies, switch to AZN). No test covers onboarding, and no test pins the stored sealed hash. `test_supply.py`
skips (not fails) on a fresh clone without `data/outside/faers`. Budget 2.5 minutes to rerun before the freeze.

### Streamlit smoke: PASS
Streamlit 1.65.0. `app/needle_app.py` headless on :8599: health OK in 11.5 s, `/` 200, `/_stcore/health` "ok"; killed,
port free. AppTest: first render 18 to 23 s, rerun 2.4 s; 0 exceptions for all 10 companies on all 5 tabs; header
Ledger Intact, 473 verified, 8 rejected; Verify seal returns SEAL VERIFIED. `app/main.py` renders too (Run not
clicked). Warnings only: `use_container_width` deprecated (lines 208, 304, 316, 381, 394, 447; replace with
`width="stretch"`).

### .env, API key, offline: demo PASS, `agent.llm` FAIL
- `.env` exists, gitignored, untracked. It holds only `SEC_USER_AGENT`. **`ANTHROPIC_API_KEY` is absent** from `.env`,
  the process, user and machine environments; no `.streamlit/secrets.toml`. `R2_*` also absent (collector falls back
  to local).
- `python -m agent.llm` does not print "scaffold OK". Exact error: `TypeError: "Could not resolve authentication
  method. Expected one of api_key, auth_token, or credentials to be set..."`. Network down gives
  `anthropic.APIConnectionError: Connection error.` after 3 retries. No timeout set (SDK default, about 10 min).
  Importing the module creates `agent/cache/` (gitignored, harmless).
- The demo path (`needle_app.py`, detectors, score, onboard, predict, backtest) makes **no** LLM call, so the demo is
  fully offline-safe. Only `trial.py` (and the old `app/main.py`, `agent/findings.py`, `agent/stated_loe.py`) call it.

Diff 6A (graceful offline in `agent/llm.py`):
```diff
-    response = _get_client().beta.messages.create(
+    try:
+        response = _get_client().with_options(timeout=120).beta.messages.create(
             ...
-    )
+        )
+    except (TypeError, anthropic.APIConnectionError, anthropic.APITimeoutError,
+            anthropic.AuthenticationError) as e:
+        return {"text": f"[LLM unavailable: {type(e).__name__}; no cached answer for this input]",
+                "model": MODEL, "cached": False, "offline": True}
```
and in `agent/needle/trial.py`, only write `trials.jsonl` when some call came back non-offline.

### `python -m agent.needle.run` timing
**PASS.** Run in a full copy at `C:\Users\parke\AppData\Local\Temp\needle_run` (paths are built from `__file__`, so
the copy writes only to itself). Network blocked with a dead proxy: no failures, no warnings, no LLM calls.

| Run | Wall clock | Script timer |
|---|---|---|
| `python -m agent.needle.run --ticker MRK` | 69.7 s | 57 s |
| `python -m agent.needle.run --all` | 272.8 s | 259 s |

- `python -m agent.needle.run MRK` (positional) fails: `run.py: error: unrecognized arguments: MRK`.
- HANDOFF's "about 50 s for --all" did not reproduce (5x slower here). Do not rerun `--all` in the last 10 minutes
  before the freeze.
- **Deterministic:** all 9 files in `out/MRK/` byte-identical to the repo; `findings.jsonl` and `rejected.jsonl` match
  for all 10 tickers; `league.json` matches (AZN 0.1327, MRK 0.0993). Top MRK finding `MRK-forensics-380276`;
  league needle `MRK-calls-879939`.
- Only difference: `out/AMGN/` and `out/BMY/` `labels_table.json` and `signals_labels.jsonl` reorder exclusivity
  codes that share a date (`NP; NS; NPP` vs `NP; NPP; NS`), confirmed with PYTHONHASHSEED 1 to 4. Findings unaffected.
- Ledger: `--ticker MRK` appends 11 records (1 run, 10 findings); chain verifies after `--ticker` and after `--all`.
  Every rerun grows the real ledger; fine while the chain stays intact.
- Side note: during this check someone else wrote a JNJ blind-test ledger record (seq 1916) and modified
  `docs/nuggets/JNJ.jsonl` and `docs/nuggets/JNJ_ai_caught.jsonl`. The app does not read that AI-caught file.

Diff 7A (deterministic labels):
```diff
--- a/agent/needle/detect/labels.py
+++ b/agent/needle/detect/labels.py
@@ -399 +399 @@
-        pairs = sorted({(r["Exclusivity_Code"], _iso(r["_d"])) for _, r in ex.iterrows()}, key=lambda x: x[1])
+        pairs = sorted({(r["Exclusivity_Code"], _iso(r["_d"])) for _, r in ex.iterrows()}, key=lambda x: (x[1], x[0]))
```
Diff 7B (accept a positional ticker):
```diff
--- a/agent/needle/run.py
+++ b/agent/needle/run.py
-    ap.add_argument("--ticker")
+    ap.add_argument("ticker_pos", nargs="?", metavar="TICKER")
+    ap.add_argument("--ticker")
     ap.add_argument("--all", action="store_true")
     ap.add_argument("--skip-detect", action="store_true")
     a = ap.parse_args()
+    a.ticker = a.ticker or a.ticker_pos
```
Optional: `LEDGER = Path(os.environ.get("NEEDLE_LEDGER", ROOT / "out" / "ledger.jsonl"))` in `audit.py` so test runs
can point the ledger elsewhere.

## Freeze checklist (in order)

1. Pick the company. Set the default selector to it (1A).
2. Fix the launch command (README, HANDOFF).
3. Add the Sharpest Needle panel from `docs/nuggets/<T>.jsonl` (1B). Update demo_script step 1.
4. Make onboarded tickers selectable (5A). Rehearse step 5 once with VRTX in the app.
5. Decide the AI caught story: run trial.py with a key (A + 3B), or reword the line. Never say N = 8.
6. Script edits for step 2 ("open the evidence") and step 4 ("Verify seal", not "in the browser").
7. Apply 2A, then eyeball one evidence box for `$` and box styling.
8. Rerun `python -m pytest tests -q -p no:cacheprovider` and click through all 5 screens for the picked company.
9. After any live onboard: `git checkout -- data/corpus` (or stash) before committing.
