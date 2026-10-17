import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useData } from "../lib/data";
import { date } from "../lib/format";
import { CiteRegistry, citeLabel, impactView, memoKey, weighOptions } from "../lib/stance";
import { AiMark, CiteChip, EmptyState, NumericPill, NumericSummary, ScoreBar, ScreenFrame } from "../components";
import type { NumericCheck } from "../lib/types";
import { Editable } from "../components/memo/Editable";
import { PinnedExhibits } from "../components/memo/PinnedExhibits";
import { MarkedSentence, hasMarked } from "../components/MarkedSentence";
import { derivedOperands, isDerived } from "../lib/cites";
import type { Evidence } from "../lib/types";
import { DecideFootnotes, DecideTable, KillSignalTable } from "../components/decide/Decide";

// CEO memo (/memo): one printable page drafted from company.stance. Text blocks are editable;
// edits persist to localStorage needle.memo.<ticker> and "Reset to draft" restores the export.

type Edits = Record<string, string>;

function readEdits(t: string): Edits {
  try {
    const raw = window.localStorage.getItem(memoKey(t));
    const o: unknown = raw ? JSON.parse(raw) : {};
    return o && typeof o === "object" && !Array.isArray(o) ? (o as Edits) : {};
  } catch { return {}; }
}
function writeEdits(t: string, e: Edits) {
  try {
    if (Object.keys(e).length) window.localStorage.setItem(memoKey(t), JSON.stringify(e));
    else window.localStorage.removeItem(memoKey(t));
  } catch { /* private mode: edits live only in this tab */ }
}

const PRINT_CSS = `
.memo-doc .exhibit-pin { display: none; }
@media print {
  @page { margin: 14mm; }
  .memo-doc { border: 0 !important; box-shadow: none !important; padding: 0 !important; max-width: none !important; }
  .memo-doc * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .memo-doc .memo-cite button { background: none !important; border: 0 !important; padding: 0 !important; color: #000 !important; }
  .memo-doc a { color: #000 !important; text-decoration: none !important; }
  .memo-keep, .memo-doc section { break-inside: avoid; }
  .memo-doc [data-edit-id] { outline: none !important; background: none !important; }
  .memo-doc .exhibit-card { box-shadow: none !important; break-inside: avoid; }
  .memo-doc svg[width], .memo-doc .recharts-wrapper, .memo-doc .recharts-responsive-container { max-width: 100% !important; }
  .memo-doc svg[width] { height: auto; }
  .memo-doc .memo-pins { grid-template-columns: 1fr !important; }
}`;

function H({ children }: { children: ReactNode }) {
  return <h3 className="text-[11px] font-bold uppercase tracking-[0.12em] text-purple-deep dark:text-purple border-b border-line pb-1 mb-2">{children}</h3>;
}

export default function Memo() {
  const { meta, company, ticker, loading, error } = useData();
  const nav = useNavigate();
  const t = company?.ticker ?? ticker ?? "";
  const s = company?.stance;
  const [editing, setEditing] = useState(false);
  const [edits, setEdits] = useState<Edits>({});
  const [version, setVersion] = useState(0);

  useEffect(() => { if (t) setEdits(readEdits(t)); setEditing(false); }, [t]);

  const editsRef = useRef<Edits>({});
  useEffect(() => { editsRef.current = edits; }, [edits]);
  // Keystrokes persist straight to storage (no re-render under the caret); blur syncs state.
  const saveDraft = useCallback((id: string, text: string) => { writeEdits(t, { ...editsRef.current, [id]: text }); }, [t]);
  const commit = useCallback((id: string, text: string) => {
    setEdits((prev) => { const next = { ...prev, [id]: text }; writeEdits(t, next); return next; });
  }, [t]);
  const reset = () => { setEdits({}); writeEdits(t, {}); setVersion((v) => v + 1); };

  const { points, sources } = useMemo(() => {
    const reg = new CiteRegistry(company);
    const pts = (s?.memo_points ?? []).slice(0, 3).map((p) => {
      const cites = reg.resolveAll(p.cites);
      const im = impactView(cites.find((c) => c.finding)?.finding);
      const f = cites.find((c) => c.finding)?.finding;
      return { text: p.text, cites, suspect: im.kind === "suspect" ? im.note ?? "impact flagged suspect by the exporter" : null, check: f?.numeric_check ?? null, hasFinding: !!f,
        marked: f && hasMarked(f) && p.text.startsWith(f.finding) ? { f, rest: p.text.slice(f.finding.length) } : null };
    });
    // Derived sources list their operands by footnote number; operands not cited directly are appended.
    type Src = { n: number; evidence?: Evidence; ops?: number[] };
    const list: Src[] = reg.list.map((c) => ({ n: c.n, evidence: c.evidence }));
    const byCite = new Map<string, number>();
    for (const c of list) if (c.evidence?.cite_id) byCite.set(c.evidence.cite_id, c.n);
    for (const c of [...list]) {
      if (!isDerived(c.evidence)) continue;
      c.ops = derivedOperands(company, c.evidence!).map((o) => {
        let n = byCite.get(o.id);
        if (n == null) { n = list.length + 1; list.push({ n, evidence: o.ev ?? { citation: `operand ${o.id} (not in this export)` } }); byCite.set(o.id, n); }
        return n;
      });
    }
    return { points: pts, sources: list };
  }, [company, s]);
  const { rows } = useMemo(() => weighOptions(s), [s]);

  const v = (id: string, draft: string) => edits[id] ?? draft;
  const ed = (id: string, draft: string, as: "span" | "p" | "div" | "h2" = "span", className = "") => (
    <Editable key={`${id}-${version}`} id={id} text={v(id, draft)} editing={editing} onCommit={commit} onDraft={saveDraft} as={as} className={className} />
  );
  const nEdits = Object.keys(edits).length;
  const decide = s?.decide?.moves?.length ? s.decide : null;
  const kills = s?.kill_signals ?? [];
  // Prove-wrong lines already shown in the kill-signal table are not repeated as bullets.
  const restProveWrong = (s?.prove_wrong ?? []).map((x, i) => ({ x, i }))
    .filter(({ x }) => !kills.some((k) => k.signal && x.startsWith(k.signal)));
  const byModel = s?.generated_by === "model";

  const btn = "rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-semibold hover:bg-surface-2";
  const actions = (
    <div className="no-print flex gap-2">
      <button type="button" onClick={() => nav("/cockpit")} className={btn}>Back to briefing</button>
      {nEdits > 0 && <button type="button" onClick={reset} className={btn}>Reset to draft</button>}
      <button type="button" onClick={() => setEditing((e) => !e)} aria-pressed={editing} className={btn}>{editing ? "Done" : "Edit"}</button>
      <button type="button" onClick={() => { setEditing(false); window.setTimeout(() => window.print(), 50); }} className="rounded-md bg-purple dark:bg-purple-deep px-3 py-1.5 text-sm font-semibold text-white hover:bg-purple-bright">Export PDF</button>
    </div>
  );

  return (
    <ScreenFrame title="CEO memo" printTitle={false} subtitle={<span className="no-print">{company?.name ?? t} · one page, printable{nEdits ? ` · ${nEdits} edit${nEdits > 1 ? "s" : ""} saved in this browser` : ""}</span>} loading={loading} error={error} actions={actions}>
      <style>{PRINT_CSS}</style>
      {company && !s && <EmptyState file={`companies/${t}.json`} message="No stance exported, so there is no memo draft" />}
      {company && s && (
        <article className="memo-doc mx-auto max-w-[820px] rounded-lg border border-line bg-surface shadow-card px-12 py-10 space-y-6 text-[14px] leading-relaxed">
          {editing && <p className="no-print -mt-4 text-xs text-purple font-semibold">Editing: click any dashed block to change it. Changes save when you leave the block.</p>}
          {decide?.demo === true && (
            <p role="note" className="memo-keep rounded-md border-l-4 border-line bg-surface-2 px-4 py-2 text-[12.5px] text-muted">
              {!/^pipeline demonstration/i.test(decide.note ?? "") && <span className="font-semibold text-fg">Pipeline demonstration. </span>}{decide.note || "This move was valued by rules on cited findings; it is not the team's recommendation."}
            </p>
          )}
          <header className="space-y-3">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b-2 border-purple pb-2 text-xs font-semibold uppercase tracking-wider">
              <span>TO: CEO · FROM: Competitive Intelligence (NEEDLE) · Draft 1</span>
              <span className="font-mono normal-case tracking-normal">As of {meta?.as_of ? date(meta.as_of) : "n/a"}</span>
            </div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">{company.name ?? t} ({t}) · recommended move: <span className="text-teal">{s.recommended ?? "n/a"}</span></div>
            {ed("headline", s.headline ?? "No headline exported", "h2", "block font-display text-[34px] leading-[1.05] tracking-wide text-purple-deep dark:text-purple")}
            <p className="memo-keep rounded-md border-l-4 border-purple bg-surface-2 px-4 py-2">
              <span className="font-bold">Decision needed: </span>{ed("decision", s.decision_needed ?? "Not exported")}
            </p>
          </header>

          <section>
            <H>Three points, each cited to the page</H>
            {points.length ? (
              <ol className="space-y-2">
                {points.map((p, i) => (
                  <li key={i} className="grid grid-cols-[22px_1fr] gap-1">
                    <span className="font-display text-[20px] leading-none text-purple pt-0.5">{i + 1}</span>
                    <span>
                      {p.marked && !editing && edits[`pt.${i}`] == null
                        ? <span><MarkedSentence finding={p.marked.f} />{p.marked.rest}</span>
                        : ed(`pt.${i}`, p.text)}{" "}
                      <span className="memo-cite whitespace-nowrap">{p.cites.map((c) => <CiteChip key={c.key} n={c.n} evidence={c.evidence} />).reduce<ReactNode[]>((a, el, j) => (j ? [...a, " ", el] : [el]), [])}</span>
                      {p.hasFinding && <>{" "}<NumericPill check={p.check} /></>}
                      {p.suspect && <span className="mt-0.5 block text-xs text-warn"><span className="font-semibold">⚠ Impact dollars flagged suspect:</span> {p.suspect}.</span>}
                    </span>
                  </li>
                ))}
              </ol>
            ) : <p className="text-muted">No memo points in stance.memo_points.</p>}
          </section>

          {decide ? (
            <section className="memo-keep">
              <H>Moves valued: chosen move first{decide.numeric_check ? <> <NumericSummary check={decide.numeric_check as NumericCheck} /></> : null}</H>
              <DecideTable company={company} decide={decide} />
            </section>
          ) : (
          <section>
            <H>Options weighed</H>
            <ul className="space-y-1">
              {rows.map((r) => (
                <li key={r.name} className="grid grid-cols-[200px_auto_1fr] items-center gap-3">
                  <span className={`font-semibold ${r.recommended ? "text-teal" : ""}`}>{r.recommended ? "▸ " : ""}{r.name}{r.recommended ? " (recommended)" : ""}</span>
                  <ScoreBar value={r.frac} tone="purple" width={150} label={r.valueLabel} />
                  <span className="text-xs text-muted">{r.nFindings != null ? `${r.nFindings} verified findings` : ""}{r.dollars == null ? " · no quantified $ in findings" : ""}</span>
                </li>
              ))}
            </ul>
          </section>
          )}

          <div className={decide ? "space-y-6" : "grid grid-cols-2 gap-6"}>
            <section>
              <H>Alternatives rejected</H>
              {(s.alternatives ?? []).length ? (
                <ul className="space-y-1.5 text-[13px]">
                  {s.alternatives!.map((a, i) => (
                    <li key={i}><span className="font-semibold">{a.name}: </span>{ed(`alt.${i}`, a.why_rejected ?? "")}</li>
                  ))}
                </ul>
              ) : <p className="text-muted">None exported.</p>}
            </section>
            <section>
              <H>What would prove us wrong in 6 to 12 months</H>
              {kills.length > 0 && <div className="memo-keep mb-2"><KillSignalTable signals={kills} /></div>}
              {restProveWrong.length ? (
                <ul className="list-disc pl-5 space-y-1 text-[13px]">
                  {restProveWrong.map(({ x, i }) => <li key={i}>{ed(`pw.${i}`, x)}</li>)}
                </ul>
              ) : !kills.length ? <p className="text-muted">None exported.</p> : null}
            </section>
          </div>

          <section>
            <H>Who decides its fate</H>
            {(s.deciders ?? []).length ? (
              <ul className="list-disc pl-5 space-y-0.5 text-[13px]">
                {s.deciders!.map((x, i) => <li key={i}>{ed(`dec.${i}`, x)}</li>)}
              </ul>
            ) : <p className="text-muted">None exported.</p>}
          </section>

          <section>
            <H>Pinned exhibits</H>
            <PinnedExhibits ticker={t} company={company} asOf={meta?.as_of} />
          </section>

          <section>
            <H>Sources</H>
            {sources.length ? (
              <ol className="space-y-0.5 text-[11px] leading-snug">
                {sources.map((c) => (
                  <li key={c.n} className="grid grid-cols-[28px_1fr] gap-1">
                    <span className="font-mono tnum">[{c.n}]</span>
                    <span className="min-w-0 break-words">
                      <span className="font-mono">{citeLabel(c.evidence)}</span>
                      {c.evidence?.withheld === true && <span className="text-warn"> · quote withheld ({c.evidence.license ? "licensed source" : "unverified citation"})</span>}
                      {c.ops?.length ? <span className="text-purple"> · derived from {c.ops.map((n) => `[${n}]`).join("")}</span> : null}
                      {c.evidence?.url && <> · <a href={c.evidence.url} target="_blank" rel="noreferrer" className="text-purple underline break-all">{c.evidence.url}</a></>}
                    </span>
                  </li>
                ))}
              </ol>
            ) : <p className="text-muted text-sm">No citations in stance.memo_points.</p>}
          </section>

          {decide && (
            <section>
              <H>Move inputs (footnotes f1 to f{(decide.footnotes ?? []).length})</H>
              <DecideFootnotes decide={decide} />
            </section>
          )}

          <footer className="space-y-2 border-t border-line pt-3">
            <div className="rounded-md border border-teal/40 bg-teal-soft/50 px-3 py-2 text-[11px] leading-snug">
              <AiMark label={byModel ? "Model-written draft" : decide?.demo === true ? "Pipeline demonstration (rules, no model)" : "Drafted from verified findings by rules"} />
              <p className="mt-1 text-fg">{s.note ?? "No drafting note exported."}{nEdits ? ` Edited by a person in this browser (${nEdits} block${nEdits > 1 ? "s" : ""}).` : ""}</p>
            </div>
            <p className="text-[10px] text-muted">Student concept, not actual promotional material. Built by TCU Neeley students. Source: companies/{t}.json stance.</p>
          </footer>
        </article>
      )}
    </ScreenFrame>
  );
}
