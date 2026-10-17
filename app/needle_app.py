"""NEEDLE demo UI. Read-only: renders files produced by the engine (no LLM calls).

Run:  streamlit run app/needle_app.py
"""

import html
import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "out"
DOCS = ROOT / "docs"

# Okabe-Ito palette (color-blind safe). Colors always accompany a text label.
BLUE, ORANGE, GREEN, VERM, SKY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9"
CONF_COLOR = {"high": GREEN, "medium": ORANGE, "low": VERM}
ZW = re.compile("[​‌‍﻿]")

st.set_page_config(page_title="NEEDLE", layout="wide", page_icon=None)
st.markdown(
    """<style>
html, body, [class*="css"] { font-size: 17px; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; color:#000; font-weight:600;
         font-size:0.9rem; border:2px solid #222; }
.srcpage { background:var(--secondary-background-color); padding:12px; border-radius:6px;
           white-space:pre-wrap; font-size:0.92rem; line-height:1.5; max-height:420px; overflow:auto;
           border:1px solid #888; }
.srcpage mark { background:#FFD54F; color:#000; padding:0 2px; border-bottom:3px solid #D55E00; font-weight:600; }
.pitch { font-size:1.25rem; margin:0 0 .3rem 0; }
</style>""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------- loaders
@st.cache_data(show_spinner=False)
def read_json(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def read_jsonl(rel):
    p = ROOT / rel
    rows = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


@st.cache_data(show_spinner=False)
def read_text(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None


@st.cache_data(show_spinner=False)
def chain_status():
    try:
        from agent.needle import audit

        ok, n, bad = audit.verify_chain()
        return bool(ok), n, bad
    except Exception:
        return None, 0, None


@st.cache_data(show_spinner=False)
def doc_source(doc_id, page):
    """Return (kind, text, label) for a cited doc. kind in {'page','label','missing'}."""
    try:
        if doc_id.startswith("drug:"):
            _, slug, fname = doc_id.split(":", 2)
            p = ROOT / "data" / "corpus" / "drugs" / slug / fname
            if p.exists():
                return "label", p.read_text(encoding="utf-8", errors="ignore"), f"{slug} label"
            return "missing", "", ""
        from agent.needle import pages

        row = pages.manifest().get(doc_id)
        if not row:
            return "missing", "", ""
        pg, _ = pages.parse(ROOT / row["path"])
        if page in pg:
            printed, text = pg[page]
            return "page", text, f"file page {page}" + (f" (printed {printed})" if printed else "")
    except Exception:
        pass
    return "missing", "", ""


# ----------------------------------------------------------------- helpers
def _pattern(quote):
    words = [w for w in re.split(r"\s+", ZW.sub(" ", quote).strip()) if w]
    return r"\s+".join(re.escape(w) for w in words) if words else None


def highlight(text, quote, label_mode=False, window=1500):
    """Escaped HTML of text with the quoted span in <mark>. Whitespace-normalized match."""
    text = ZW.sub("", text)
    q = ZW.sub("", quote)
    m = None
    for cand in (q, q[:80], q[:40]):
        pat = _pattern(cand)
        if pat:
            m = re.search(pat, text, flags=re.I)
            if m:
                break
    if not m:
        return None, text[:window]
    s, e = m.span()
    if label_mode:
        starts = [x.start() for x in re.finditer(r"^#{2,4} .*$", text, flags=re.M)]
        lo = max([x for x in starts if x <= s], default=0)
        hi = min([x for x in starts if x > e], default=len(text))
        lo, hi = max(lo, s - 2500), min(hi, e + 2500)
    else:
        lo, hi = max(0, s - window), min(len(text), e + window)
    out = html.escape(text[lo:s]) + "<mark>" + html.escape(text[s:e]) + "</mark>" + html.escape(text[e:hi])
    return out, None


def badge(label, color):
    return f'<span class="badge" style="background:{color}">{html.escape(label)}</span>'


def note(msg):
    st.info(msg)


def money(x):
    try:
        return f"${x/1e9:,.2f}B" if abs(x) >= 1e9 else f"${x/1e6:,.0f}M"
    except Exception:
        return "n/a"


# ----------------------------------------------------------------- data
def load_league():
    """out/league_v3.json if present, else league_v2.json, else league.json (review B22). FIND rows (v2/v3) are
    mapped onto the columns this page shows; the AI-rejected count still comes from the engine's league.json."""
    old = read_json("out/league.json") or []
    for name in ("out/league_v3.json", "out/league_v2.json"):
        rows = read_json(name)
        if rows:
            by = {r["ticker"]: r for r in old}
            return [{"ticker": r["ticker"], "score": r["L"], "n_findings": r.get("n_findings", 0),
                     "n_verified": r.get("n_findings", 0),
                     "n_rejected": by.get(r["ticker"], {}).get("n_rejected", r.get("n_withheld", 0)),
                     "high_confidence": sum(t.get("confidence") == "HIGH" for t in r.get("top", [])),
                     "sharpest_needle": (f"{r['needle']['sentence']} ({r.get('needle_status')})" if r.get("needle")
                                         else "none")} for r in rows]
    return old


league = load_league()
tickers = [r["ticker"] for r in league] or sorted(p.name for p in OUT.glob("*") if (p / "findings.jsonl").exists())
total_verified = sum(r.get("n_verified", 0) for r in league)
total_rejected = sum(r.get("n_rejected", 0) for r in league)

# ----------------------------------------------------------------- header
st.title("NEEDLE")
st.markdown(
    '<p class="pitch">Finds what the headlines miss in drug makers\' filings, proves every claim to the page, '
    "and checks itself.</p>",
    unsafe_allow_html=True,
)
ok, n_ledger, bad = chain_status()
c1, c2, c3 = st.columns(3)
if ok is None:
    c1.metric("Ledger", "unavailable")
else:
    c1.metric("Ledger", "Intact" if ok else "BROKEN", f"{n_ledger} entries" if ok else f"fails at seq {bad}", delta_color="off")
c2.metric("Findings verified", f"{total_verified:,}")
c3.metric("AI claims rejected", f"{total_rejected:,}")

if not tickers:
    note("No engine output found in out/. Run the NEEDLE pipeline to produce out/league.json.")
    st.stop()

selected = st.selectbox("Company (drives the Findings, Fine print and AI caught tabs)", tickers, key="company")

tab_league, tab_find, tab_labels, tab_ai, tab_proof = st.tabs(
    ["League table", "Findings", "Product fine print", "AI caught", "Proof"]
)

# ----------------------------------------------------------------- tab 1
with tab_league:
    st.subheader("Which companies hide the most in their filings?")
    if not league:
        note("out/league.json is missing.")
    else:
        df = pd.DataFrame(league).sort_values("score", ascending=False).reset_index(drop=True)
        df.insert(0, "Rank", df.index + 1)
        df = df.rename(
            columns={
                "ticker": "Company",
                "score": "Score",
                "n_findings": "Findings",
                "n_verified": "Verified",
                "n_rejected": "Rejected",
                "high_confidence": "High confidence",
                "sharpest_needle": "Sharpest needle",
            }
        )
        st.dataframe(
            df[["Rank", "Company", "Score", "Findings", "Verified", "Rejected", "High confidence", "Sharpest needle"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score (bar + number)", min_value=0.0, max_value=float(max(df["Score"].max(), 0.01)), format="%.3f"
                ),
                "Sharpest needle": st.column_config.TextColumn(width="large"),
            },
        )
        st.caption("Score = impact x peer outlier x timeliness x obscurity x evidence strength. Every finding is verified to a source page.")
        st.markdown("**Sharpest needle per company**")
        for _, r in df.iterrows():
            st.markdown(f"- **{r['Company']}** (score {r['Score']:.3f}): {r['Sharpest needle']}")

# ----------------------------------------------------------------- tab 2
with tab_find:
    st.subheader(f"{selected}: findings ranked by score")
    rows = read_jsonl(f"out/{selected}/findings.jsonl")
    if not rows:
        note(f"No findings file for {selected}.")
    else:
        rows = sorted(rows, key=lambda r: r.get("score", 0), reverse=True)
        confs = sorted({r.get("confidence", "") for r in rows})
        pick = st.multiselect("Confidence", confs, default=confs, key="conf_filter")
        shown = [r for r in rows if r.get("confidence", "") in pick]
        st.caption(f"{len(shown)} of {len(rows)} findings shown")
        top = max((r.get("score", 0) for r in rows), default=1) or 1
        for i, r in enumerate(shown[:60]):
            conf = r.get("confidence", "n/a")
            with st.container(border=True):
                st.markdown(f"**{r['finding']}**")
                a, b, c = st.columns([2, 1, 1])
                a.progress(max(0.0, min(1.0, r.get("score", 0) / top)), text=f"Score {r.get('score', 0):.3f}")
                b.markdown(
                    "Confidence: " + badge(conf.upper(), CONF_COLOR.get(conf, SKY)), unsafe_allow_html=True
                )
                c.markdown(f"Verdict: **{r.get('verdict', 'n/a')}**")
                imp = r.get("impact") or {}
                if imp.get("formula"):
                    st.markdown(f"Impact: **{money(imp.get('dollars', 0))}**. {imp['formula']}")
                pe = r.get("peer") or {}
                if pe.get("peer_median") is not None and pe.get("metric_value") is not None:
                    zt = f"z {pe['z']:+.2f}" if pe.get("z") is not None else "z n/a"
                    st.markdown(
                        f"Peer line: value {pe['metric_value']:+.3f} vs peer median {pe['peer_median']:+.3f} ({zt})"
                    )
                vec = r.get("vector") or {}
                if vec.get("obscurity_note"):
                    st.markdown(f"Obscurity: {vec['obscurity_note']}")
                with st.expander(f"Evidence and source pages ({len(r.get('evidence', []))})"):
                    for j, ev in enumerate(r.get("evidence", [])):
                        st.markdown(f"**Source {j+1}: {ev.get('citation') or ev['doc_id']}**")
                        st.markdown(f"Quote: *{ev['quote'][:400]}*")
                        if ev.get("speaker"):
                            st.caption(f"Speaker: {ev['speaker']}")
                        if ev.get("figures"):
                            st.caption("Figures checked on page: " + ", ".join(map(str, ev["figures"])))
                        kind, text, lab = doc_source(ev["doc_id"], ev.get("page"))
                        if kind == "missing":
                            st.caption(f"Source text unavailable locally for {ev['doc_id']} p.{ev.get('page')}.")
                            continue
                        marked, fallback = highlight(text, ev["quote"], label_mode=(kind == "label"))
                        st.caption(("Label section containing the quote" if kind == "label" else "Source page") + f": {lab}")
                        if marked:
                            st.markdown(f'<div class="srcpage">{marked}</div>', unsafe_allow_html=True)
                        else:
                            st.caption("Quote span not located after whitespace normalization; showing page start.")
                            st.markdown(f'<div class="srcpage">{html.escape(fallback)}</div>', unsafe_allow_html=True)
                hr = r.get("hit_rate") or {}
                if hr.get("margin_drop"):
                    m = hr["margin_drop"]
                    st.caption(
                        f"Historical: this signal preceded a margin drop in {m['hit_rate']:.0%} of cases "
                        f"vs {m['rate_when_not_fired']:.0%} when not fired (lift {m['lift']}). See Proof tab."
                    )
        if len(shown) > 60:
            st.caption(f"Showing the top 60 of {len(shown)}.")

# ----------------------------------------------------------------- tab 3
with tab_labels:
    st.subheader(f"{selected}: product fine print vs rivals")
    lt = read_json(f"out/{selected}/labels_table.json")
    if not lt or not lt.get("products"):
        note(f"No labels_table.json for {selected}.")
    else:
        for prod, d in lt["products"].items():
            st.markdown(f"#### {prod.title()}")
            rivals = d.get("rivals", [])
            recs = []
            for row in d.get("table", []):
                rec = {"Field": row["field"], prod.title(): str(row.get("product", ""))}
                srcs = [f"{prod}: {row.get('source', '')}"]
                for rv in rivals:
                    rec[rv.title()] = str(row.get("rivals", {}).get(rv, ""))
                    srcs.append(f"{rv}: {row.get('rival_sources', {}).get(rv, '')}")
                rec["Sources"] = "; ".join(srcs)
                recs.append(rec)
            st.dataframe(pd.DataFrame(recs), hide_index=True, use_container_width=True)
            st.caption("The Sources column names where each cell came from (label section or dataset file); it is shown inline, not only on hover.")

# ----------------------------------------------------------------- tab 4
with tab_ai:
    st.subheader("AI claims the verifier threw out")
    rej = read_jsonl(f"out/{selected}/rejected.jsonl")
    if rej:
        st.dataframe(
            pd.DataFrame(
                [{"Claim": r.get("finding", ""), "Why rejected": r.get("reason", ""), "Verdict": r.get("verdict", "")} for r in rej]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        note(
            f"No rejected claims recorded for {selected}. That means every claim the engine produced passed the verifier, "
            "not that nothing was checked. Totals across companies: "
            f"{total_verified} verified, {total_rejected} rejected."
        )
    st.markdown(
        """**What the verifier checks on every claim**
- The quote must appear on the cited page (whitespace-normalized).
- For call transcripts, the named speaker must appear before the quote.
- Every figure cited must appear on that page.
- LLM-written summaries (for example fool.com transcripts) are rejected as sources; only primary documents count."""
    )
    g2 = read_text("docs/needle_gate2.md")
    with st.expander("How adversarial review refuted our first backtest (docs/needle_gate2.md)"):
        if g2:
            st.markdown(g2)
        else:
            st.caption("docs/needle_gate2.md not found.")

# ----------------------------------------------------------------- tab 5
with tab_proof:
    st.subheader("Proof: does it hold up?")
    hr = read_json("out/backtest/hit_rates.json")
    st.markdown("### (a) Backtest v2")
    st.warning(
        "Forensic signals predict margin compression, not hard events (revenue drops or impairments). "
        "Lift on hard events is statistically indistinguishable from 1."
    )
    if not hr:
        note("out/backtest/hit_rates.json is missing.")
    else:
        st.caption(
            f"{hr.get('firm_quarters')} firm-quarters, {hr.get('companies_observed')} companies, {hr.get('period')}; "
            f"{hr.get('universe_note', '')}. Lift CI is clustered by firm."
        )
        recs = []
        for sig, s in hr["signals"].items():
            ev = s.get("events", {})
            h, m = ev.get("hard", {}), ev.get("margin_drop", {})
            wf = s.get("within_firm_hard") or {}
            ci = h.get("lift_ci95_firm_clustered")
            recs.append(
                {
                    "Signal": sig,
                    "Fired": s.get("n_fired"),
                    "Episodes": s.get("episodes"),
                    "Hard-event hit (fired)": h.get("hit_rate"),
                    "Hard-event hit (not fired)": h.get("rate_when_not_fired"),
                    "Hard lift": h.get("lift"),
                    "Hard lift 95% CI": f"{ci[0]} to {ci[1]}" if ci else "n/a",
                    "Margin lift": m.get("lift"),
                    "Margin lift 95% CI": (
                        f"{m['lift_ci95_firm_clustered'][0]} to {m['lift_ci95_firm_clustered'][1]}"
                        if m.get("lift_ci95_firm_clustered")
                        else "n/a"
                    ),
                    "Within-firm hard (pp)": (
                        f"{wf['mean_pp']:+.1f} [{wf['ci95_pp'][0]}, {wf['ci95_pp'][1]}]" if wf else "n/a"
                    ),
                }
            )
        st.dataframe(pd.DataFrame(recs), hide_index=True, use_container_width=True)
        dr = hr.get("dose_response_full_coverage")
        if dr:
            st.markdown("**Margin dose-response: more signals fired, more margin compression**")
            d = pd.DataFrame(
                {
                    "Signals fired": list(dr.keys()),
                    "Margin-drop rate": [v["margin_rate"] for v in dr.values()],
                    "Hard-event rate": [v["hard_rate"] for v in dr.values()],
                    "n": [v["n"] for v in dr.values()],
                }
            )
            st.bar_chart(d.set_index("Signals fired")[["Margin-drop rate", "Hard-event rate"]], color=[BLUE, ORANGE])
            st.dataframe(d, hide_index=True, use_container_width=True)
            st.caption("Blue: margin-drop rate rises with signal count. Orange: hard-event rate stays flat. Table gives exact values.")

    st.markdown("### (b) Forecaster calibration")
    cal = read_json("out/predictions/calibration.json")
    if not cal:
        note("calibration.json is missing.")
    else:
        a, b, c, d_ = st.columns(4)
        a.metric("Interval width k", cal["k"])
        b.metric("Coverage", f"{cal['coverage']:.1%}", f"target {cal['target']:.0%}", delta_color="off")
        c.metric("Back-test cases", f"{cal['n_cases']:,}")
        d_.metric("Median abs error", f"{cal['median_abs_error_pts']} pts")
        st.caption(f"Direction accuracy vs last period: {cal['direction_accuracy_vs_last']:.1%}. An honest 80% interval should cover about 80% of outcomes.")

    st.markdown("### (c) J&J blind test")
    bl = read_json("out/predictions/blind_JNJ_2026Q3.json")
    if not bl:
        note("blind_JNJ_2026Q3.json is missing.")
    else:
        p = bl["prediction"]
        with st.container(border=True):
            st.markdown(f"**{p['ticker']} {p['target_period']} {p['metric']}** ({p.get('made_at', '')})")
            a, b = st.columns(2)
            a.markdown("Forecast: " + "; ".join(p.get("basis", [])))
            b.markdown(
                f"Actual: **{bl['actual']:+.1%}**. Outcome: "
                + badge(p["outcome"].upper(), GREEN if p["outcome"] == "hit" else VERM),
                unsafe_allow_html=True,
            )
            st.caption(f"Absolute error {bl['abs_error_pts']} pts.")
            ak = bl.get("answer_key", {})
            st.markdown(f"Answer key: {ak.get('citation', '')}. Quote: *{ak.get('quote', '')}* (verifier: {ak.get('verifier', 'n/a')})")

    st.markdown("### (d) Sealed forecasts")
    sealed = read_json("out/predictions/sealed_2026Q3.json")
    if not sealed:
        note("sealed_2026Q3.json is missing.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Company": q["ticker"],
                        "Period": q["target_period"],
                        "Metric": q["metric"],
                        "Forecast": "; ".join(x for x in q["basis"] if x.startswith(("point", "80%"))),
                        "Outcome": q["outcome"],
                    }
                    for q in sealed["predictions"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"Sealed {sealed.get('made_at')} for {sealed.get('target')}. Stored sha256: {sealed.get('sha256')}")
        if st.button("Verify seal"):
            try:
                from agent.needle import audit

                body = {k: v for k, v in sealed.items() if k != "sha256"}
                calc = audit.seal(body)
                md = read_text("docs/needle_sealed.md") or ""
                m = re.search(r"sha256=([0-9a-f]{64}) file=out/predictions/sealed_2026Q3\.json", md)
                doc_hash = m.group(1) if m else None
                st.write(f"Recomputed: `{calc}`")
                st.write(f"Stored in file: `{sealed.get('sha256')}`")
                st.write(f"Committed in docs/needle_sealed.md: `{doc_hash}`")
                if calc == sealed.get("sha256") and calc == doc_hash:
                    st.success("SEAL VERIFIED: recomputed hash matches the file and the committed record.")
                else:
                    st.error("SEAL MISMATCH: the file differs from what was committed.")
            except Exception as e:  # pragma: no cover
                st.error(f"Could not verify: {e}")
