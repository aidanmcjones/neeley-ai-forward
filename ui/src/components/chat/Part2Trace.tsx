import { useState } from "react";
import type { Evidence, Part2Trace, Part2TraceStep } from "../../lib/types";
import { evidenceLabel, scrub } from "../../lib/part1";
import { CiteChip } from "../CiteChip";

// The Part 2 reasoning trace, as Use-of-AI evidence: the candidate moves the strategist proposed, what the
// two skeptics (CFO/math and Decider/compliance) said in two rounds, and the verdict with its reason.
// Figures the gate never checked were withheld by the exporter before this file was written.

const VERDICT: Record<string, string> = { survived: "border-good/50 bg-good/10 text-good", narrowed: "border-warn/60 bg-warn/10 text-warn", killed: "border-bad/50 bg-bad/10 text-bad" };

const WITHHELD = "[figure withheld: not gated]";
/** Trace prose with each withheld-figure marker shown as a small pill instead of the literal bracket text. */
export function Withheld({ text }: { text: string }) {
  const parts = text.split(WITHHELD);
  return (
    <>
      {parts.map((p, i) => (
        <span key={i}>
          {p}
          {i < parts.length - 1 && <span title="Figure withheld: the numeric gate never checked it" className="mx-0.5 inline-block rounded border border-dashed border-muted/60 px-1 align-baseline font-mono text-[9.5px] leading-tight text-muted">withheld</span>}
        </span>
      ))}
    </>
  );
}

/** One skeptic round: a string, or {refuted, severity, argument, correction} as the Part 2 skeptics write it. */
function Round({ n, r }: { n: number; r: unknown }) {
  if (r == null) return null;
  const y = (typeof r === "object" ? r : {}) as Record<string, unknown>;
  const body = typeof r === "string" ? r : String(y.argument ?? y.text ?? y.reason ?? y.summary ?? y.verdict ?? y.note ?? "");
  const tag = typeof r === "object"
    ? [y.refuted === true ? "refuted" : y.refuted === false ? "not refuted" : "", typeof y.severity === "string" ? y.severity : ""].filter(Boolean).join(", ")
    : "";
  const fix = typeof y.correction === "string" ? y.correction : "";
  if (!body && !tag && !fix) return null;
  return (
    <p>
      <span className="font-mono text-[10.5px] text-muted">R{n} </span>
      {tag && <span className="mr-1 rounded border border-line px-1 text-[10px] uppercase tracking-wide text-muted">{tag}</span>}
      <Withheld text={scrub(body)} />
      {fix && <span className="block text-muted"><span className="font-semibold">Correction: </span><Withheld text={scrub(fix)} /></span>}
    </p>
  );
}

function Rounds({ title, r }: { title: string; r: unknown }) {
  const o = (r && typeof r === "object" ? r : {}) as Record<string, unknown>;
  if (o.round1 == null && o.round2 == null) return null;
  return (
    <div className="text-[12.5px] space-y-1">
      <div className="font-semibold text-muted">{title}</div>
      <Round n={1} r={o.round1} />
      <Round n={2} r={o.round2} />
    </div>
  );
}

function Step({ s }: { s: Part2TraceStep }) {
  const [open, setOpen] = useState(false);
  const v = String(s.verdict ?? "").toLowerCase();
  const cites = (Array.isArray(s.cites) ? s.cites : []).filter((e): e is Evidence => !!e && typeof e === "object");
  return (
    <li className="rounded-md border border-line px-3 py-2 space-y-1">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="font-mono text-[11px] text-muted">{s.candidate_id ?? `step ${s.step}`}</span>
        {v && <span className={`rounded border px-1.5 py-px text-[10.5px] font-semibold uppercase tracking-wide ${VERDICT[v] ?? "border-line text-muted"}`}>{v}</span>}
        {s.type && <span className="text-[11px] text-muted">{scrub(String(s.type)).replace(/^other:/, "").replace(/[_-]+/g, " ")}</span>}
      </div>
      {s.move && <p className="text-[13.5px] leading-snug"><Withheld text={scrub(s.move)} /></p>}
      {s.reason && <p className="text-[12.5px] text-muted"><span className="font-semibold">Verdict: </span><Withheld text={scrub(s.reason)} /></p>}
      {(s.skeptic_cfo || s.skeptic_decider || cites.length > 0) && (
        <button type="button" onClick={(e) => { e.stopPropagation(); setOpen((x) => !x); }} className="no-print text-[11px] text-purple underline">{open ? "Hide the skeptic rounds" : "Show the skeptic rounds"}</button>
      )}
      {open && (
        <div className="space-y-1.5 border-l-2 border-line pl-3">
          <Rounds title="CFO/math skeptic" r={s.skeptic_cfo} />
          <Rounds title="Decider/compliance skeptic" r={s.skeptic_decider} />
          {cites.length > 0 && <div className="flex flex-wrap gap-1">{cites.map((e, i) => <CiteChip key={e.cite_id ?? i} evidence={evidenceLabel(e)} n={i + 1} />)}</div>}
        </div>
      )}
    </li>
  );
}

export function Part2TraceView({ trace, summary, candidates, sample }: {
  trace: Part2Trace; summary?: { killed?: number; narrowed?: number; survived?: number } | null; candidates?: number | null; sample?: boolean;
}) {
  const steps = (Array.isArray(trace.steps) ? trace.steps : []).filter((s) => s && Number(s.step) > 0);
  const n = (x: unknown) => (typeof x === "number" && Number.isFinite(x) ? x : null);
  const sm = summary ?? trace.summary ?? {};
  const strip = [["candidates", n(candidates) ?? n(trace.summary?.candidates) ?? steps.length], ["survived", n(sm.survived)], ["narrowed", n(sm.narrowed)], ["killed", n(sm.killed)]] as const;
  const lenses = Array.isArray(trace.lenses) ? trace.lenses.filter((x) => typeof x === "string") : [];
  return (
    <section aria-label="How it decided" className="space-y-2">
      <details className="rounded-md border border-line bg-surface px-3 py-2">
        <summary className="cursor-pointer select-none text-[14px] font-semibold">
          How it decided
          <span className="ml-2 text-[12px] font-normal text-muted">
            {strip.filter(([, v]) => v != null).map(([k, v]) => `${v} ${k}`).join(" · ")}
            {lenses.length ? ` · skeptics: ${lenses.map(scrub).join(" and ")}` : ""}
          </span>
        </summary>
        {sample && <p className="mt-1 text-[11.5px] italic text-muted">Illustrative trace from sample data.</p>}
        {steps.length ? <ol className="mt-2 space-y-2">{steps.map((s) => <Step key={s.step} s={s} />)}</ol> : <p className="mt-2 text-[13px] text-muted">No candidate steps exported.</p>}
      </details>
    </section>
  );
}
