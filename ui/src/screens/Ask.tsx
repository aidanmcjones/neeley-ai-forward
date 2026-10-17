import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { isWithheld, withheldReason, resolveCite, useData } from "../lib/data";
import type { CiteRef, Company, Evidence, Question } from "../lib/types";
import { retrieve } from "../lib/retrieve";
import type { AnswerSentence, DataRow, Exhibit, RetrieveResult } from "../lib/retrieve";
import { usePins } from "../lib/exhibits";
import { NumericPill, AiMark, CiteChip, ScreenFrame, StanceBadge, useSource } from "../components";
import { ExhibitView } from "../components/ask";
import { MarkedSentence, hasMarked } from "../components/MarkedSentence";
import { derivedOperands, formulaMarkedOf, isDerived } from "../lib/cites";

// Ask NEEDLE (docs/ui_spec.md screen 2, Option C): preset + session questions on the left,
// a cited answer with a visible trace, exhibit cards and source cards on the right.
// Offline by default (deterministic retriever over companies/<T>.json). Live mode only when
// ui/server.py answers /api/health with {live:true}; never faked.

const LIVE_BASE = "http://localhost:8787";

interface LiveAnswer { text: string; cites: string[]; trace: string[]; rejected_cites: string[]; removed_claims?: string[]; unsupported_numbers?: string[]; model?: string; cached?: boolean }
type LiveState = { status: "idle" } | { status: "loading" } | { status: "ok"; data: LiveAnswer } | { status: "error"; message: string };

interface Thread { id: string; q: string; own: boolean }

/* ------------------------------------------------------------- live health */

/** Live mode is opt-in (?live=1, remembered; ?live=0 forgets) so the default demo makes no network calls. */
function liveWanted(): boolean {
  const m = window.location.href.match(/[?&]live=([01])/);
  try {
    if (m) {
      if (m[1] === "1") window.localStorage.setItem("needle.live", "1");
      else window.localStorage.removeItem("needle.live");
    }
    return m ? m[1] === "1" : window.localStorage.getItem("needle.live") === "1";
  } catch { return m?.[1] === "1"; }
}

function useLiveHealth(): boolean {
  const [live, setLive] = useState(false);
  useEffect(() => {
    if (!liveWanted()) return;
    const ctl = new AbortController();
    const timer = window.setTimeout(() => ctl.abort(), 1000);
    fetch(`${LIVE_BASE}/api/health`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : { live: false }))
      .then((j: { live?: boolean }) => {
        const on = j?.live === true;
        setLive(on);
        (window as unknown as { __NEEDLE_LIVE__?: boolean }).__NEEDLE_LIVE__ = on;
      })
      .catch(() => setLive(false))
      .finally(() => window.clearTimeout(timer));
    return () => { ctl.abort(); window.clearTimeout(timer); };
  }, []);
  return live;
}

/* -------------------------------------------------------------- cite chips */

/** Number every distinct cite in order of first use, so chips read [1] [2] ... */
function useCiteNumbers(sentences: AnswerSentence[]) {
  return useMemo(() => {
    const m = new Map<string, number>();
    for (const s of sentences) for (const c of s.cites) {
      const k = `${c.finding_id}#${c.i ?? 0}`;
      if (!m.has(k)) m.set(k, m.size + 1);
    }
    return m;
  }, [sentences]);
}

function sourceEvidence(s: AnswerSentence, verdict?: string): Evidence | null {
  if (!s.source) return null;
  return { citation: s.source.label, url: s.source.url, doc_id: s.source.label, verdict };
}

/* ---------------------------------------------------------------- pieces */

function Bubble({ q }: { q: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-purple dark:bg-purple-deep text-white px-4 py-2.5 text-[15px] font-medium shadow-card">{q}</div>
    </div>
  );
}

function TraceRow({ trace, terms }: { trace: { label: string; withheld?: boolean }[]; terms: string[] }) {
  if (!trace.length && !terms.length) return null;
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">Trace: what was checked</div>
      <ul className="flex flex-wrap gap-1.5">
        {trace.map((t) => (
          <li key={t.label}>
            {t.withheld
              ? <span tabIndex={0} title="Quote withheld: unverified citation or licensed source" className="inline-block font-mono text-[11px] rounded border border-dashed border-muted/70 text-muted px-1.5 py-0.5">read {t.label} · quote withheld</span>
              : <span tabIndex={0} className="inline-block font-mono text-[11px] rounded border border-teal/30 bg-teal-soft text-teal px-1.5 py-0.5">read {t.label}</span>}
          </li>
        ))}
        {terms.length > 0 && (
          <li>
            <span tabIndex={0} className="inline-block font-mono text-[11px] rounded border border-teal/30 bg-teal-soft text-teal px-1.5 py-0.5"
              title="Query terms after stopwords; #group = synonym group">searched {terms.slice(0, 10).join(" ")}</span>
          </li>
        )}
      </ul>
    </div>
  );
}

function DataRows({ rows }: { rows: DataRow[] }) {
  if (!rows.length) return null;
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">Also matched in the exported data (values as exported)</div>
      <div className="grid grid-cols-2 gap-2">
        {rows.map((r) => (
          <div key={r.title} className="rounded-md border border-line bg-surface p-2.5 min-w-0">
            <div className="text-xs font-bold leading-tight">{r.title}</div>
            <dl className="mt-1 grid grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-[11px]">
              {r.fields.slice(0, 8).map(([k, v]) => (
                <Fragment key={k}>
                  <dt className="text-muted truncate">{k}</dt>
                  <dd className="font-mono tnum break-words line-clamp-2" title={v}>{v}</dd>
                </Fragment>
              ))}
            </dl>
            <div className="mt-1.5 font-mono text-[10px] text-muted break-words">Source: {r.source}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SourceCards({ company, refs, preview }: { company: Company; refs: CiteRef[]; preview: Evidence | null }) {
  const { open } = useSource();
  const evs = useMemo(() => {
    const seen = new Set<string>();
    const out: Evidence[] = [];
    for (const r of refs) {
      const { evidence } = resolveCite(company, r);
      if (!evidence) continue;
      const k = evidence.citation ?? `${evidence.doc_id}${evidence.page}`;
      if (seen.has(k)) continue;
      seen.add(k);
      out.push(evidence);
    }
    return out;
  }, [company, refs]);
  if (!evs.length && !preview) return null;
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">Sources</div>
      {preview && (
        <div className="mb-2 rounded-md border border-purple/30 bg-surface-2 p-3 text-xs" aria-live="polite">
          <div className="font-mono text-[11px] text-purple">{preview.citation ?? preview.doc_id}</div>
          {isWithheld(preview) ? <p className="mt-1 text-warn font-semibold">Quote withheld: {withheldReason(preview)}.</p>
            : isDerived(preview) ? <p className="mt-1 text-purple font-semibold">Derived from {preview.derived_from!.length} cited operand{preview.derived_from!.length > 1 ? "s" : ""}; click to see them.</p>
            : preview.quote ? <blockquote className="mt-1 leading-relaxed"><mark>{preview.quote}</mark></blockquote> : <p className="mt-1 text-muted">No page quote exported for this source.</p>}
        </div>
      )}
      <ul className="flex gap-2 overflow-x-auto pb-1">
        {evs.map((e) => {
          const isCall = /transcript|call/i.test(e.doc_type ?? "") || !!e.speaker;
          const wh = isWithheld(e);
          return (
            <li key={e.citation ?? e.doc_id} className="shrink-0 w-[220px]">
              <button type="button" onClick={() => open(e)}
                className={`w-full h-full text-left rounded-md border bg-surface p-2.5 hover:border-purple focus-visible:border-purple ${wh ? "border-dashed border-muted/70" : "border-line"}`}>
                <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">{(e.doc_type ?? "document").replace(/_/g, " ")}{e.source_quality ? ` · ${e.source_quality}` : ""}</div>
                <div className="mt-0.5 font-mono text-[11px] text-purple leading-snug line-clamp-2">{e.citation ?? e.doc_id}</div>
                {isCall && <div className="mt-1 text-[11px]">Transcript grade <span className="font-mono font-bold">{e.grade ?? "ungraded"}</span>{e.speaker ? <span className="text-muted"> · {e.speaker}</span> : null}</div>}
                {wh
                  ? <div className="mt-1 text-[10.5px] font-semibold text-warn">Quote withheld: {withheldReason(e)}</div>
                  : isDerived(e)
                  ? <div className="mt-1 text-[10.5px] font-semibold text-purple">derived from {derivedOperands(company, e).map((o, j) => `[${String.fromCharCode(97 + j)}] ${o.ev?.citation ?? o.id}`).join(" ")}</div>
                  : <div className={`mt-1 text-[10.5px] font-semibold ${e.verdict === "verified" ? "text-good" : "text-warn"}`}>{e.verdict === "verified" ? "✓ verified on page" : `⚠ ${e.verdict ?? "unverified"}`}</div>}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Sentences({ company, sentences, onPreview }: { company: Company; sentences: AnswerSentence[]; onPreview: (e: Evidence | null) => void }) {
  const nums = useCiteNumbers(sentences);
  return (
    <div className="space-y-2 text-[15px] leading-relaxed">
      {sentences.map((s, i) => (
        <p key={i}>
          <span>{(() => {
            const f = s.kind === "finding" && s.cites[0] ? resolveCite(company, s.cites[0]).finding : undefined;
            if (f && hasMarked(f) && f.finding === s.text) return <MarkedSentence finding={f} onPreview={onPreview} />;
            const fi = s.kind === "impact" && s.cites[0] ? resolveCite(company, s.cites[0]).finding : undefined;
            const fm = formulaMarkedOf(fi);
            if (fi && fm && s.text === `Impact: ${fi.impact?.formula ?? ""}`) return <>Impact: <MarkedSentence finding={fi} marked={fm} onPreview={onPreview} /></>;
            return s.text;
          })()}</span>{" "}
          {s.cites.map((c) => {
            const k = `${c.finding_id}#${c.i ?? 0}`;
            const { evidence } = resolveCite(company, c);
            return <Fragment key={k}><CiteChip evidence={evidence ?? null} n={nums.get(k)} onPreview={onPreview} />{" "}</Fragment>;
          })}
          {!s.cites.length && s.source && <CiteChip evidence={sourceEvidence(s, s.verdict)} label={`[${s.source.label}]`} onPreview={onPreview} />}
          {s.kind === "finding" && s.cites.length > 0 && <>{" "}<NumericPill check={resolveCite(company, s.cites[0]).finding?.numeric_check} /></>}
          {s.verdict && s.verdict !== "verified" && (
            <span className="ml-1 inline-block rounded border border-warn/50 bg-warn/10 px-1 text-[10px] font-semibold uppercase text-warn align-middle">⚠ needs human review</span>
          )}
          {s.quote && (
            <span className="mt-1 block border-l-2 border-line pl-2 text-xs text-muted italic">On the page: "{s.quote}"</span>
          )}
        </p>
      ))}
    </div>
  );
}

/** Live answer: replace [finding_id] markers with cite chips; unknown ids were already stripped server-side. */
function LiveText({ company, data, onPreview }: { company: Company; data: LiveAnswer; onPreview: (e: Evidence | null) => void }) {
  const order = new Map<string, number>();
  const parts: ReactNode[] = [];
  const re = /\[([A-Za-z0-9_.:-]+)\]/g;
  let last = 0, m: RegExpExecArray | null, k = 0;
  while ((m = re.exec(data.text))) {
    parts.push(<Fragment key={k++}>{data.text.slice(last, m.index)}</Fragment>);
    const id = m[1];
    if (!order.has(id)) order.set(id, order.size + 1);
    const { evidence } = resolveCite(company, { finding_id: id, i: 0 });
    parts.push(<CiteChip key={k++} evidence={evidence ?? null} n={order.get(id)} onPreview={onPreview} />);
    last = m.index + m[0].length;
  }
  parts.push(<Fragment key={k++}>{data.text.slice(last)}</Fragment>);
  return <div className="text-[15px] leading-relaxed whitespace-pre-wrap">{parts}</div>;
}

function EmptyAnswer({ nearest, onPick }: { nearest: Question[]; onPick: (q: string) => void }) {
  return (
    <div role="status" className="rounded-lg border border-dashed border-line bg-surface-2 px-4 py-4 text-sm">
      <p className="font-semibold">I found nothing cited for that.</p>
      <p className="text-muted mt-0.5">No finding, label row, forces field or priced-in row matched above the relevance floor, so there is no answer to give. Nearest questions:</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {nearest.map((q) => (
          <button key={q.id} type="button" onClick={() => onPick(q.q)} className="rounded-full border border-purple/40 bg-surface px-3 py-1 text-xs text-purple hover:bg-chip text-left">{q.q}</button>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ screen */

export default function Ask() {
  const { company, meta, ticker, loading, error } = useData();
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const liveAvailable = useLiveHealth();
  const [mode, setMode] = useState<"offline" | "live">("offline");
  const [own, setOwn] = useState<Thread[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<Evidence | null>(null);
  const [live, setLive] = useState<LiveState>({ status: "idle" });
  const input = useRef<HTMLInputElement>(null);
  const pins = usePins(ticker);
  const isLive = liveAvailable && mode === "live";

  const presets = company?.questions ?? [];

  const runLive = useCallback(async (q: string) => {
    if (!ticker) return;
    setLive({ status: "loading" });
    try {
      const r = await fetch(`${LIVE_BASE}/api/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker, question: q }) });
      const j = await r.json();
      if (!r.ok || j.error) throw new Error(j.error ?? `HTTP ${r.status}`);
      setLive({ status: "ok", data: j as LiveAnswer });
    } catch (e) {
      setLive({ status: "error", message: (e as Error).message });
    }
  }, [ticker]);

  const ask = useCallback((q: string) => {
    const t = q.trim();
    if (!t) return;
    setCurrent(t);
    setPreview(null);
    if (!presets.some((p) => p.q === t)) {
      setOwn((o) => (o.some((x) => x.q === t) ? o : [...o, { id: `own-${o.length + 1}`, q: t, own: true }]));
    }
    if (isLive) runLive(t); else setLive({ status: "idle" });
  }, [presets, isLive, runLive]);

  // ?q= from the URL (command palette) submits on load; reset when the company changes.
  const urlQ = params.get("q");
  useEffect(() => {
    if (!company) return;
    if (urlQ) { ask(urlQ); setText(""); }
    else if (!current && company.questions?.length) setCurrent(company.questions[0].q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company, urlQ]);
  useEffect(() => { setOwn([]); setCurrent(null); setLive({ status: "idle" }); }, [ticker]);
  useEffect(() => { input.current?.focus(); }, [loading]);

  // Switching to Live re-asks the current question; switching back shows the offline answer.
  useEffect(() => {
    if (isLive && current) runLive(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLive]);

  const result: RetrieveResult | null = useMemo(() => (company && current ? retrieve(current, company) : null), [company, current]);
  const allCites = useMemo(() => result?.sentences.flatMap((s) => s.cites) ?? [], [result]);
  const liveCites = useMemo<CiteRef[]>(() => (live.status === "ok" ? live.data.cites.map((id) => ({ finding_id: id, i: 0 })) : []), [live]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    if (urlQ) setParams((p) => { p.delete("q"); return p; }, { replace: true });
    ask(text);
    setText("");
  };
  const pick = (q: string) => {
    if (urlQ) setParams((p) => { p.delete("q"); return p; }, { replace: true });
    ask(q);
  };

  const threads: Thread[] = [...presets.map((p) => ({ id: p.id, q: p.q, own: false })), ...own];

  return (
    <ScreenFrame
      title="Ask NEEDLE"
      subtitle={<>Cited answers over {ticker ?? "n/a"}'s verified findings, label table, forces and priced-in rows. Works offline; never invents a number.</>}
      loading={loading}
      error={error}
      actions={
        <div className="flex items-center gap-2">
          {liveAvailable ? (
            <>
              <span className="rounded-full bg-teal text-white dark:text-black px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide">✦ Live model</span>
              <div role="group" aria-label="Answer mode" className="inline-flex rounded-md border border-line overflow-hidden text-xs">
                {(["offline", "live"] as const).map((m) => (
                  <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}
                    className={`px-2.5 py-1 font-semibold capitalize ${mode === m ? (m === "live" ? "bg-teal text-white dark:text-black" : "bg-purple dark:bg-purple-deep text-white") : "bg-surface text-muted hover:bg-surface-2"}`}>{m}</button>
                ))}
              </div>
            </>
          ) : (
            <span className="rounded-full border border-line bg-surface px-2.5 py-1 text-[11px] text-muted" title="Live mode: run PYTHONPATH=. python ui/server.py --port 8787 with ANTHROPIC_API_KEY set, then open /?live=1#/ask">Offline retriever · live model off</span>
          )}
        </div>
      }
    >
      {company && (
        <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-5 items-start">
          {/* Questions */}
          <nav aria-label="Questions" className="rounded-lg border border-line bg-surface shadow-card sticky top-0 max-h-[calc(100vh-180px)] overflow-y-auto">
            <h2 className="px-3 pt-3 pb-1 text-[12px] font-bold uppercase tracking-wide">Questions</h2>
            <ul className="px-1.5 pb-2">
              {threads.map((t, i) => {
                const firstOwn = t.own && (i === 0 || !threads[i - 1].own);
                return (
                  <Fragment key={t.id}>
                    {firstOwn && <li className="px-2 pt-3 pb-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted">This session</li>}
                    <li>
                      <button type="button" onClick={() => pick(t.q)} aria-current={current === t.q ? "true" : undefined}
                        className={`w-full text-left rounded-md px-2 py-1.5 text-[12.5px] leading-snug ${current === t.q ? "bg-chip text-purple font-semibold" : "hover:bg-surface-2"}`}>
                        {t.own && <span className="mr-1 text-muted" aria-hidden="true">›</span>}{t.q}
                      </button>
                    </li>
                  </Fragment>
                );
              })}
              {!threads.length && <li className="px-2 py-2 text-xs text-muted">No preset questions exported for {ticker} (companies/{ticker}.json has no questions).</li>}
            </ul>
          </nav>

          {/* Answer */}
          <div className="min-w-0 flex flex-col gap-4">
            {current && result ? (
              <>
                <Bubble q={current} />
                <section aria-label="Answer" className="rounded-lg border border-teal/40 bg-teal-soft/30 p-4 space-y-4 shadow-card">
                  <div className="flex flex-wrap items-center gap-2">
                    {isLive ? <AiMark label="Live model" /> : result.mode === "empty" ? <AiMark label="No cited answer" /> : <AiMark label="Answered from verified findings" />}
                    <StanceBadge stance={(isLive ? null : result.stance) ?? null} />
                    <span className="text-[11px] text-muted">
                      {isLive ? (live.status === "ok" ? `${live.data.model ?? "model"}${live.data.cached ? " · cached" : ""}` : "")
                        : result.mode === "preset" ? (result.presetFallback ? `No direct match; closest preset: "${result.preset?.q}"` : "Precomputed preset answer")
                        : result.mode === "composed" ? `Composed verbatim from ${usedCount(result) ? `${usedCount(result)} matching finding(s)` : "exported data rows"}` : ""}
                    </span>
                  </div>

                  {isLive ? (
                    live.status === "loading" ? <p role="status" className="text-sm text-muted">Asking the live model with {ticker}'s findings as the only context…</p>
                    : live.status === "error" ? <p role="alert" className="text-sm text-warn">Live model failed ({live.message}). Switch to Offline for the deterministic answer.</p>
                    : live.status === "ok" ? (
                      <>
                        <LiveText company={company} data={live.data} onPreview={setPreview} />
                        {(live.data.rejected_cites.length > 0 || (live.data.removed_claims?.length ?? 0) > 0 || (live.data.unsupported_numbers?.length ?? 0) > 0) && (
                          <p className="text-xs rounded border border-warn/40 bg-warn/10 px-2 py-1 text-warn font-semibold">
                            {(live.data.removed_claims?.length ?? 0) > 0 && <>The verifier removed {live.data.removed_claims!.length} uncited claim(s). </>}
                            {live.data.rejected_cites.length > 0 && <>Stripped {live.data.rejected_cites.length} cite(s) to findings that do not exist ({live.data.rejected_cites.join(", ")}). </>}
                            {(live.data.unsupported_numbers?.length ?? 0) > 0 && <>Numbers not found in the provided findings: {live.data.unsupported_numbers!.join(", ")}.</>}
                          </p>
                        )}
                      </>
                    ) : <p className="text-sm text-muted">Press Ask to send this question to the live model.</p>
                  ) : result.mode === "empty" ? (
                    <EmptyAnswer nearest={result.nearest} onPick={pick} />
                  ) : (
                    <>
                      {result.sentences.length ? <Sentences company={company} sentences={result.sentences} onPreview={setPreview} />
                        : <p className="text-sm">No finding sentence matched; the exported data rows below did. Values are shown as exported, not restated.</p>}
                    </>
                  )}

                  <TraceRow trace={isLive && live.status === "ok" ? live.data.trace.map((label) => ({ label })) : result.trace} terms={isLive ? [] : result.mode === "preset" ? [] : result.terms} />
                </section>

                {result.exhibits.length > 0 && (
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">Exhibits</div>
                    <div className="grid grid-cols-2 gap-3">
                      {dedupeExhibits(result.exhibits).map((e) => <ExhibitView key={`${e.kind}-${e.ref}`} exhibit={e} company={company} asOf={meta?.as_of} />)}
                    </div>
                  </div>
                )}

                {!isLive && <DataRows rows={result.rows} />}

                <SourceCards company={company} refs={isLive ? liveCites : allCites} preview={preview} />
              </>
            ) : (
              <p className="text-sm text-muted">Pick a question on the left or type one below.</p>
            )}

            {/* Composer */}
            <form onSubmit={submit} className="sticky bottom-0 z-10 -mx-1 rounded-lg border border-line bg-surface p-2 shadow-card flex items-center gap-2">
              <label htmlFor="ask-input" className="sr-only">Ask a question about {ticker}</label>
              <input id="ask-input" ref={input} autoFocus value={text} onChange={(e) => setText(e.target.value)}
                placeholder={`Ask about ${company.name ?? ticker}: inventory, IRA, exclusivity, label vs rivals…`}
                className="flex-1 min-w-0 bg-transparent px-2 py-2 text-[14px] outline-none placeholder:text-muted" />
              <button type="submit" className="rounded-md bg-purple dark:bg-purple-deep text-white px-4 py-2 text-sm font-semibold hover:bg-purple-bright disabled:opacity-50" disabled={!text.trim()}>Ask</button>
              <button type="button" onClick={() => nav("/cockpit/memo")} className="rounded-md border border-purple/40 text-purple px-3 py-2 text-sm font-semibold hover:bg-chip whitespace-nowrap">
                Draft CEO memo from pins{pins.length ? ` (${pins.length})` : ""}
              </button>
            </form>
          </div>
        </div>
      )}
    </ScreenFrame>
  );
}

function usedCount(r: RetrieveResult): number {
  return new Set(r.sentences.flatMap((s) => (s.cites.length ? s.cites.map((c) => c.finding_id) : s.source ? [s.text] : []))).size;
}

function dedupeExhibits(xs: Exhibit[]): Exhibit[] {
  const seen = new Set<string>();
  return xs.filter((e) => { const k = `${e.kind}-${e.ref}`; if (seen.has(k)) return false; seen.add(k); return true; });
}
