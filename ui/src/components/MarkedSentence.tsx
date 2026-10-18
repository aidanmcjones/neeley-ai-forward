import { Fragment, useState } from "react";
import type { Company, Evidence, Finding } from "../lib/types";
import { useData } from "../lib/data";
import { citeIndex, markedOf, parseMarked } from "../lib/cites";
import { CiteChip } from "./CiteChip";

// A finding sentence with its exported inline markers: [n] -> cite chip for evidence n,
// [derived: a, b] -> operand chips, [assumption] -> amber pill. No sentence_marked -> the plain
// sentence, unchanged. Markers are only ever read from the data, never added here.

export function AssumptionPill({ reason }: { reason?: string }) {
  return (
    <>
      <span title={reason ? `Assumption: ${reason}` : "This number is an assumption (a stated input), not a sourced figure"}
        className="inline-block rounded border border-warn/60 bg-warn/10 px-1 py-px align-middle font-body text-[10px] font-semibold normal-case tracking-normal leading-tight text-warn">assumption</span>
      {reason && <span className="hidden print:inline font-body text-[9px] normal-case tracking-normal text-warn"> ({reason})</span>}
    </>
  );
}

export function ConstantPill({ name }: { name: string }) {
  return (
    <span title={`Constant: ${name} (a fixed model input, not a sourced figure)`}
      className="inline-block rounded border border-line px-1 py-px align-middle font-body text-[10px] font-semibold normal-case tracking-normal leading-tight text-muted">constant</span>
  );
}

export function hasMarked(f: Finding | null | undefined) { return !!markedOf(f); }

export function LicensedMark({ count = 1 }: { count?: number }) {
  return (
    <span title={`${count} licensed source${count > 1 ? "s" : ""} (data used as a model input; its text is not published)`}
      className="inline-block rounded border border-line px-1 py-px align-middle font-body text-[10px] font-semibold normal-case tracking-normal leading-tight text-muted">
      licensed source{count > 1 ? ` ×${count}` : ""}
    </span>
  );
}

type Group = { t: "text"; s: string } | { t: "cites"; ns: number[] } | { t: "derived"; ns: (number | "assumption")[] } | { t: "assumption"; reason?: string } | { t: "constant"; name: string };

/** Merge adjacent [n] markers (whitespace between them is dropped) into one run. */
function group(marked: string): Group[] {
  const out: Group[] = [];
  for (const tk of parseMarked(marked)) {
    const last = out[out.length - 1];
    if (tk.t === "cite") {
      if (last?.t === "cites") { last.ns.push(tk.n); continue; }
      if (last?.t === "text" && !last.s.trim() && out[out.length - 2]?.t === "cites") { out.pop(); (out[out.length - 1] as { ns: number[] }).ns.push(tk.n); continue; }
      out.push({ t: "cites", ns: [tk.n] });
    } else out.push(tk as Group);
  }
  return out;
}

const RUN_SHOWN = 3;

/** A run of cite markers: the first few as chips, licensed ones as one muted mark, the rest behind "+N". */
function CiteRun({ ns, chip, licensed }: { ns: number[]; chip: (n: number, k: string) => JSX.Element; licensed: (n: number) => boolean }) {
  const [open, setOpen] = useState(false);
  const pub = ns.filter((n) => !licensed(n));
  const lic = ns.length - pub.length;
  const shown = open ? pub : pub.slice(0, RUN_SHOWN);
  const hidden = pub.length - shown.length;
  return (
    <span className="inline-flex flex-wrap items-baseline gap-0.5 align-baseline font-body normal-case tracking-normal leading-none">
      {shown.map((n, j) => chip(n, `r${j}`))}
      {hidden > 0 && (
        <button type="button" onClick={(e) => { e.stopPropagation(); setOpen(true); }} title={`${hidden} more source${hidden > 1 ? "s" : ""}`}
          className="font-mono text-[10.5px] rounded px-1 py-px border border-line text-muted hover:text-purple hover:border-purple">+{hidden}</button>
      )}
      {lic > 0 && <LicensedMark count={lic} />}
    </span>
  );
}

export function MarkedSentence({ finding, text, onPreview, marked: markedIn, company: companyIn }: {
  finding: Finding; text?: string; onPreview?: (e: Evidence | null) => void; marked?: string | null; company?: Company | null;
}) {
  const ctx = useData();
  const company = companyIn ?? ctx.company;
  const marked = markedIn !== undefined ? markedIn : markedOf(finding);
  if (!marked) return <>{text ?? finding.finding}</>;
  const ev = finding.evidence ?? [];
  const map = (finding.marker_map ?? null) as Record<string, string> | null;
  const licSet = new Set(((finding.marker_licensed ?? []) as unknown[]).map(Number));
  const ix = map ? citeIndex(company) : null;
  const resolve = (n: number): Evidence | undefined => {
    if (map) { const id = map[String(n)]; return id ? ix!.get(id) ?? ev.find((e) => e.cite_id === id) : undefined; }
    return ev[n - 1];
  };
  const licensed = (n: number) => licSet.has(n);
  const chip = (n: number, key: string) => {
    if (licensed(n)) return <LicensedMark key={key} />;
    const e = resolve(n);
    return e
      ? <span key={key} className="inline-block align-baseline font-body normal-case tracking-normal leading-none"><CiteChip evidence={{ ...e, verdict: e.verdict ?? finding.verdict }} n={n} onPreview={onPreview} /></span>
      : <span key={key} className="font-mono text-[11px] text-muted" title="Marker has no matching evidence in this export">[{n}]</span>;
  };
  return (
    <>
      {group(marked).map((tk, i) => {
        if (tk.t === "text") return <Fragment key={i}>{tk.s}</Fragment>;
        if (tk.t === "cites") return <CiteRun key={i} ns={tk.ns} chip={chip} licensed={licensed} />;
        if (tk.t === "assumption") return <Fragment key={i}>{" "}<AssumptionPill reason={tk.reason} /></Fragment>;
        if (tk.t === "constant") return <Fragment key={i}>{" "}<ConstantPill name={tk.name} /></Fragment>;
        return <DerivedRun key={i} ns={tk.ns} chip={chip} />;
      })}
    </>
  );
}

function DerivedRun({ ns, chip }: { ns: (number | "assumption")[]; chip: (n: number, k: string) => JSX.Element }) {
  const [open, setOpen] = useState(false);
  const many = ns.length > 2;
  return (
    <span className="inline-flex flex-wrap items-baseline gap-0.5 align-baseline font-body normal-case tracking-normal text-[10.5px] leading-none text-purple" title={`Derived number: computed from ${ns.length} cited operand${ns.length > 1 ? "s" : ""}`}>
      {many && !open
        ? <button type="button" onClick={(e) => { e.stopPropagation(); setOpen(true); }} className="italic rounded px-1 py-px border border-purple/40 hover:bg-chip">derived ({ns.length})</button>
        : <><span className="italic">derived</span>{ns.map((x, j) => (x === "assumption" ? <AssumptionPill key={j} /> : chip(x, `d${j}`)))}</>}
    </span>
  );
}
