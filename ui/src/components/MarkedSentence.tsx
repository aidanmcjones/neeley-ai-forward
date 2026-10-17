import { Fragment } from "react";
import type { Evidence, Finding } from "../lib/types";
import { markedOf, parseMarked } from "../lib/cites";
import { CiteChip } from "./CiteChip";

// A finding sentence with its exported inline markers: [n] -> cite chip for evidence n,
// [derived: a, b] -> operand chips, [assumption] -> amber pill. No sentence_marked -> the plain
// sentence, unchanged. Markers are only ever read from the data, never added here.

export function AssumptionPill() {
  return (
    <span title="This number is an assumption (a stated input), not a sourced figure"
      className="inline-block rounded border border-warn/60 bg-warn/10 px-1 py-px align-middle font-body text-[10px] font-semibold normal-case tracking-normal leading-tight text-warn">assumption</span>
  );
}

export function hasMarked(f: Finding | null | undefined) { return !!markedOf(f); }

export function MarkedSentence({ finding, text, onPreview }: { finding: Finding; text?: string; onPreview?: (e: Evidence | null) => void }) {
  const marked = markedOf(finding);
  if (!marked) return <>{text ?? finding.finding}</>;
  const ev = finding.evidence ?? [];
  const chip = (n: number, key: string) => {
    const e = ev[n - 1];
    return e
      ? <span key={key} className="inline-block align-baseline font-body normal-case tracking-normal leading-none"><CiteChip evidence={{ ...e, verdict: e.verdict ?? finding.verdict }} n={n} onPreview={onPreview} /></span>
      : <span key={key} className="font-mono text-[11px] text-muted" title="Marker has no matching evidence in this export">[{n}]</span>;
  };
  return (
    <>
      {parseMarked(marked).map((tk, i) => {
        if (tk.t === "text") return <Fragment key={i}>{tk.s}</Fragment>;
        if (tk.t === "cite") return chip(tk.n, `c${i}`);
        if (tk.t === "assumption") return <Fragment key={i}>{" "}<AssumptionPill /></Fragment>;
        return (
          <span key={i} className="inline-flex items-baseline gap-0.5 align-baseline font-body normal-case tracking-normal text-[10.5px] leading-none text-purple" title="Derived number: computed from the cited operands">
            <span className="italic">derived</span>
            {tk.ns.map((x, j) => (x === "assumption" ? <AssumptionPill key={j} /> : chip(x, `d${i}-${j}`)))}
          </span>
        );
      })}
    </>
  );
}
