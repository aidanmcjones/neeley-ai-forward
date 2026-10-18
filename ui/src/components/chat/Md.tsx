import { Fragment, useState } from "react";
import type { ReactNode } from "react";
import type { Evidence } from "../../lib/types";
import { CiteChip } from "../CiteChip";
import { AssumptionPill, ConstantPill } from "../MarkedSentence";

// Minimal inline markdown for memo blocks: **bold**, *italic*, `code`, and the citation markers
// [n], [derived: a, b], [assumption]. Markers come only from the data.

const TOKEN = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[\d+\]|\[derived:\s*[^\]]+\]|\[constant:\s*[^\]]+\]|\[assumption(?::\s*[^\]]+)?\])/g;

function Run({ ns, chip }: { ns: number[]; chip: (n: number, k: string) => ReactNode }) {
  const [open, setOpen] = useState(false);
  const shown = open ? ns : ns.slice(0, 3);
  return (
    <span className="inline-flex flex-wrap items-baseline gap-0.5 align-baseline">
      {shown.map((n, j) => chip(n, `r${j}`))}
      {ns.length > shown.length && (
        <button type="button" onClick={(e) => { e.stopPropagation(); setOpen(true); }} title={`${ns.length - shown.length} more sources`}
          className="font-mono text-[10.5px] rounded px-1 py-px border border-line text-muted hover:text-purple hover:border-purple">+{ns.length - shown.length}</button>
      )}
    </span>
  );
}

export function Md({ md, cite, prefix }: { md: string; cite: (n: number) => Evidence | undefined; prefix?: string }) {
  const parts = md.split(TOKEN).filter((x) => x !== "");
  const chip = (n: number, k: string) => {
    const ev = cite(n);
    return ev
      ? <span key={k} className="inline-block align-baseline leading-none">{prefix ? <CiteChip evidence={ev} label={`${prefix}${n}`} /> : <CiteChip evidence={ev} n={n} />}</span>
      : <span key={k} className="font-mono text-[11px] text-muted" title="No source exported for this marker">[{n}]</span>;
  };
  // Runs of adjacent [n] markers collapse to three chips and "+N" (expand on click).
  const merged: (string | number[])[] = [];
  for (const p of parts) {
    const m = p.match(/^\[(\d+)\]$/);
    const last = merged[merged.length - 1];
    if (m) {
      if (Array.isArray(last)) { last.push(Number(m[1])); continue; }
      if (typeof last === "string" && !last.trim() && Array.isArray(merged[merged.length - 2])) { merged.pop(); (merged[merged.length - 1] as number[]).push(Number(m[1])); continue; }
      merged.push([Number(m[1])]);
    } else merged.push(p);
  }
  const out: ReactNode[] = merged.map((p, i) => {
    if (Array.isArray(p)) return <Run key={i} ns={p} chip={chip} />;
    let m: RegExpMatchArray | null;
    if ((m = p.match(/^\[(\d+)\]$/))) return chip(Number(m[1]), `c${i}`);
    if ((m = p.match(/^\[assumption(?::\s*([^\]]+))?\]$/))) return <Fragment key={i}>{" "}<AssumptionPill reason={m[1]?.trim()} /></Fragment>;
    if ((m = p.match(/^\[constant:\s*([^\]]+)\]$/))) return <Fragment key={i}>{" "}<ConstantPill name={m[1].trim()} /></Fragment>;
    if ((m = p.match(/^\[derived:\s*([^\]]+)\]$/))) {
      const ns = m[1].split(",").map((x) => x.trim());
      return (
        <span key={i} className="inline-flex items-baseline gap-0.5 text-[11px] text-purple" title="Derived number: computed from the cited operands">
          <span className="italic">derived</span>
          {ns.map((x, j) => (/^\d+$/.test(x) ? chip(Number(x), `d${i}-${j}`) : <AssumptionPill key={j} />))}
        </span>
      );
    }
    if (p.startsWith("**") && p.endsWith("**")) return <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`")) return <code key={i} className="font-mono text-[0.9em]">{p.slice(1, -1)}</code>;
    if (p.length > 2 && p.startsWith("*") && p.endsWith("*")) return <em key={i}>{p.slice(1, -1)}</em>;
    return <Fragment key={i}>{p}</Fragment>;
  });
  return <>{out}</>;
}

/** Plain text of a markdown string (markers and emphasis stripped), for the typewriter and copy. */
export const plainMd = (md: string) => md.replace(/\[(\d+)\]|\[derived:[^\]]+\]|\[constant:[^\]]+\]|\[assumption(?::[^\]]+)?\]/g, "").replace(/\*\*|`/g, "").replace(/\s+([.,;:])/g, "$1");
