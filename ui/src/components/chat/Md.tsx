import { Fragment } from "react";
import type { ReactNode } from "react";
import type { Evidence } from "../../lib/types";
import { CiteChip } from "../CiteChip";
import { AssumptionPill } from "../MarkedSentence";

// Minimal inline markdown for memo blocks: **bold**, *italic*, `code`, and the citation markers
// [n], [derived: a, b], [assumption]. Markers come only from the data.

const TOKEN = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[\d+\]|\[derived:\s*[^\]]+\]|\[assumption\])/g;

export function Md({ md, cite }: { md: string; cite: (n: number) => Evidence | undefined }) {
  const parts = md.split(TOKEN).filter((x) => x !== "");
  const chip = (n: number, k: string) => {
    const ev = cite(n);
    return ev
      ? <span key={k} className="inline-block align-baseline leading-none"><CiteChip evidence={ev} n={n} /></span>
      : <span key={k} className="font-mono text-[11px] text-muted" title="No source exported for this marker">[{n}]</span>;
  };
  const out: ReactNode[] = parts.map((p, i) => {
    let m: RegExpMatchArray | null;
    if ((m = p.match(/^\[(\d+)\]$/))) return chip(Number(m[1]), `c${i}`);
    if (p === "[assumption]") return <Fragment key={i}>{" "}<AssumptionPill /></Fragment>;
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
export const plainMd = (md: string) => md.replace(/\[(\d+)\]|\[derived:[^\]]+\]|\[assumption\]/g, "").replace(/\*\*|`/g, "").replace(/\s+([.,;:])/g, "$1");
