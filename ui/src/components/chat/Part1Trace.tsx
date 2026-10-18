import { useMemo } from "react";
import type { Evidence, Part1SkepticRounds, Part1Trace, Part1TraceStep } from "../../lib/types";
import { evidenceLabel, PART1_CATEGORIES, scrub } from "../../lib/part1";
import { CiteChip } from "../CiteChip";

// The reasoning trace under the Part 1 answer: the eight "Where findings hide" categories walked in
// order, what was read, and what the skeptics killed, narrowed and kept. Collapsed by default to the
// summary strip and the eight category headers.

const VERDICT_TONE: Record<string, string> = {
  survived: "border-good/50 bg-good/10 text-good",
  narrowed: "border-warn/50 bg-warn/10 text-warn",
  killed: "border-bad/50 bg-bad/10 text-bad",
};

export function VerdictBadge({ v }: { v?: string }) {
  const k = (v ?? "").toLowerCase();
  return <span className={`inline-block whitespace-nowrap rounded-full border px-2 py-px text-[10.5px] font-bold uppercase tracking-wide ${VERDICT_TONE[k] ?? "border-line text-muted"}`}>{k || "no verdict"}</span>;
}

function roundText(r: unknown): string {
  if (r == null) return "";
  if (typeof r === "string") return scrub(r);
  if (typeof r === "number" || typeof r === "boolean") return String(r);
  if (Array.isArray(r)) return r.map(roundText).filter(Boolean).join("; ");
  const o = r as Record<string, unknown>;
  const head = [o.verdict, o.call, o.decision].find((x) => typeof x === "string") as string | undefined;
  const body = [o.reason, o.text, o.argument, o.note].find((x) => typeof x === "string") as string | undefined;
  if (head || body) return scrub([head, body].filter(Boolean).join(": "));
  return scrub(Object.entries(o).filter(([, v]) => v != null && typeof v !== "object").map(([k, v]) => `${k}: ${v}`).join("; "));
}

const hasRounds = (s?: Part1SkepticRounds | null) => !!s && (s.round1 != null || s.round2 != null);

function Skeptic({ label, s }: { label: string; s?: Part1SkepticRounds | null }) {
  return (
    <div className="min-w-0">
      <div className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">{label}</div>
      {hasRounds(s) ? (
        <dl className="mt-0.5 space-y-0.5 text-[12.5px]">
          {(["round1", "round2"] as const).map((k) => s![k] != null && (
            <div key={k} className="flex gap-1.5"><dt className="shrink-0 font-semibold text-muted">{k === "round1" ? "Round 1" : "Round 2"}</dt><dd className="min-w-0 break-words">{roundText(s![k]) || "recorded, no text"}</dd></div>
          ))}
        </dl>
      ) : <p className="mt-0.5 text-[12.5px] text-muted">not recorded</p>}
    </div>
  );
}

function Candidate({ s, onFinding }: { s: Part1TraceStep; onFinding?: (n: number) => void }) {
  const cites: Evidence[] = (s.candidate?.cites ?? []).map(evidenceLabel);
  const text = scrub(s.candidate?.text) || "Candidate text not exported";
  const reason = scrub(s.verdict_reason);
  const skeptics = hasRounds(s.skeptic_materiality) || hasRounds(s.skeptic_obviousness);
  return (
    <li className="rounded-md border border-line bg-surface px-3 py-2 space-y-1.5">
      <div className="flex flex-wrap items-start gap-2">
        <VerdictBadge v={s.verdict} />
        <p className="min-w-0 flex-1 text-[13.5px] leading-snug">
          {text}
          {cites.length > 0 && <span className="ml-1 inline-flex flex-wrap gap-0.5 align-baseline">{cites.slice(0, 4).map((c, i) => <CiteChip key={i} evidence={c} n={i + 1} />)}</span>}
        </p>
      </div>
      {reason && <p className="text-[12.5px] text-muted"><span className="font-semibold">Why: </span>{reason}</p>}
      {s.finding_n != null && (
        <button type="button" onClick={() => onFinding?.(Number(s.finding_n))} className="text-[12px] font-semibold text-purple hover:underline">Became finding {s.finding_n}</button>
      )}
      {skeptics && (
        <details className="rounded border border-line bg-surface-2 px-2.5 py-1.5">
          <summary className="cursor-pointer select-none text-[12px] font-semibold text-purple">Skeptic rounds</summary>
          <div className="mt-1.5 grid gap-2 sm:grid-cols-2">
            <Skeptic label="Materiality skeptic" s={s.skeptic_materiality} />
            <Skeptic label="Obviousness skeptic" s={s.skeptic_obviousness} />
          </div>
        </details>
      )}
    </li>
  );
}

export function Part1TraceView({ trace, sample, onFinding }: { trace: Part1Trace; sample: boolean; onFinding?: (n: number) => void }) {
  const steps = useMemo(() => (trace.steps ?? []).filter((s) => s && s.category !== "header" && s.step !== 0), [trace]);
  const cats = trace.header?.categories?.length ? trace.header.categories : PART1_CATEGORIES;
  const byCat = useMemo(() => {
    const m = new Map<string, Part1TraceStep[]>();
    for (const c of cats) m.set(c, []);
    for (const s of steps) { if (!m.has(s.category)) m.set(s.category, []); m.get(s.category)!.push(s); }
    for (const v of m.values()) v.sort((a, b) => (a.step ?? 0) - (b.step ?? 0));
    return m;
  }, [steps, cats]);
  const docKey = (d: { doc_id?: string; doc_title?: string; page?: unknown }) => `${d.doc_id ?? d.doc_title ?? ""}|${d.page ?? ""}`;
  const count = (v: string) => steps.filter((s) => (s.verdict ?? "").toLowerCase() === v).length;
  const allDocs = new Set(steps.flatMap((s) => (s.documents ?? []).map(docKey)));
  const sum = trace.summary ?? {};
  const strip: [string, number][] = [
    ["candidates", sum.candidates ?? steps.filter((s) => s.candidate).length],
    ["survived", sum.survived ?? count("survived")],
    ["killed", sum.killed ?? count("killed")],
    ["narrowed", sum.narrowed ?? count("narrowed")],
    ["documents read", sum.documents ?? allDocs.size],
  ];
  const noSkeptic = steps.length > 0 && steps.every((s) => !hasRounds(s.skeptic_materiality) && !hasRounds(s.skeptic_obviousness));
  const illustrative = sample || trace.sample === true || noSkeptic;

  return (
    <section aria-label="Reasoning trace" className="space-y-2.5">
      <h3 className="text-[16px] font-semibold">How the answer was found</h3>
      <div className="flex flex-wrap gap-1.5" role="list" aria-label="Trace summary">
        {strip.map(([k, v]) => (
          <span key={k} role="listitem" className="inline-flex items-baseline gap-1 rounded-md border border-line bg-surface px-2.5 py-1 text-[12.5px]">
            <span className="font-semibold tnum text-purple-deep dark:text-purple">{v}</span><span className="text-muted">{k}</span>
          </span>
        ))}
      </div>
      {illustrative && <p className="text-[12px] text-muted">Illustrative trace from the engine's gate decisions; skeptic record not available.</p>}
      <ol className="space-y-1.5">
        {[...byCat.entries()].map(([cat, ss], i) => {
          const docs = new Map<string, { doc_title?: string; page?: unknown; doc_id?: string }>();
          for (const s of ss) for (const d of s.documents ?? []) if (!docs.has(docKey(d))) docs.set(docKey(d), d);
          const queries = [...new Set(ss.map((s) => scrub(s.query)).filter(Boolean))];
          const sv = ss.filter((s) => s.verdict === "survived").length, kl = ss.filter((s) => s.verdict === "killed").length, nr = ss.filter((s) => s.verdict === "narrowed").length;
          return (
            <li key={cat}>
              <details className="rounded-md border border-line bg-surface-2/60">
                <summary className="flex cursor-pointer select-none flex-wrap items-baseline gap-x-2 gap-y-0.5 px-3 py-2 text-[13.5px]">
                  <span className="font-mono text-[11px] text-muted">{i + 1}</span>
                  <span className="font-semibold">{cat}</span>
                  <span className="ml-auto text-[12px] text-muted tnum">
                    {ss.length ? `${ss.length} candidate${ss.length === 1 ? "" : "s"} · ${sv} survived · ${nr} narrowed · ${kl} killed · ${docs.size} doc${docs.size === 1 ? "" : "s"}` : "nothing recorded"}
                  </span>
                </summary>
                <div className="space-y-2 border-t border-line px-3 py-2.5">
                  {queries.length > 0 && (
                    <div>
                      <div className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">Query</div>
                      {queries.map((q, j) => <p key={j} className="font-mono text-[12px] break-words">{q}</p>)}
                    </div>
                  )}
                  {docs.size > 0 && (
                    <div>
                      <div className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">Documents read</div>
                      <ul className="mt-0.5 space-y-0.5 text-[12.5px]">
                        {[...docs.values()].map((d, j) => <li key={j} className="break-words">{scrub(d.doc_title) || d.doc_id || "Untitled document"}{d.page != null && d.page !== "" ? <span className="text-muted">, p. {String(d.page)}</span> : null}</li>)}
                      </ul>
                    </div>
                  )}
                  {ss.length > 0
                    ? <ul className="space-y-1.5">{ss.map((s, j) => <Candidate key={j} s={s} onFinding={onFinding} />)}</ul>
                    : <p className="text-[12.5px] text-muted">No candidate recorded in this category.</p>}
                </div>
              </details>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
