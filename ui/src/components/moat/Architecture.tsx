import { Panel } from "..";
import { SourceNote, useTokens } from "../proof/common";

// Left-to-right architecture strip. Teal marks only the model step (LLM reading); everything else is code or data.

const SOURCES = ["SEC EDGAR", "FDA Orange/Purple Book", "CMS Part B/D, IRA", "DailyMed labels", "ClinicalTrials.gov", "WRDS I/B/E/S", "Tiingo prices"];

export function Architecture() {
  const t = useTokens();
  const H = 240, cy = 118;
  type Node = { x: number; w: number; y?: number; h?: number; title: string; sub: string[]; ai?: boolean };
  const nodes: Node[] = [
    { x: 194, w: 126, title: "Page-anchored", sub: ["corpus: 836 docs,", "every page keeps", "its printed number"] },
    { x: 342, w: 130, y: 28, h: 82, title: "Signals", sub: ["code: forensics,", "labels, forces"] },
    { x: 342, w: 130, y: 126, h: 82, title: "LLM reading", sub: ["drift, call Q&A,", "deflections"], ai: true },
    { x: 500, w: 116, title: "Verifier", sub: ["code: quote and", "figures on the", "cited page"] },
    { x: 644, w: 104, title: "Audit ledger", sub: ["hash-chained,", "append-only"] },
    { x: 776, w: 96, title: "Scorer", sub: ["impact, peer z,", "obscurity"] },
    { x: 900, w: 96, title: "This UI", sub: ["static JSON,", "offline"] },
  ];
  const box = (n: Node, i: number) => {
    const y = n.y ?? 48, h = n.h ?? 140;
    const stroke = n.ai ? t.teal : t.purple;
    return (
      <g key={i}>
        <rect x={n.x} y={y} width={n.w} height={h} rx={8} fill={t.surface} stroke={stroke} strokeWidth={n.ai ? 2 : 1.5} />
        {n.ai && <rect x={n.x} y={y} width={n.w} height={h} rx={8} fill={t.teal} opacity={0.08} />}
        <text x={n.x + n.w / 2} y={y + 24} textAnchor="middle" fontSize={13} fontWeight={700} fill={t.fg}>{n.ai ? "✦ " : ""}{n.title}</text>
        {n.sub.map((s, j) => (
          <text key={j} x={n.x + n.w / 2} y={y + 44 + j * 16} textAnchor="middle" fontSize={11.5} fill={t.muted}>{s}</text>
        ))}
      </g>
    );
  };
  const arrow = (x1: number, y1: number, x2: number, y2: number, k: string) => (
    <path key={k} d={`M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`} fill="none" stroke={t.muted} strokeWidth={1.5} markerEnd="url(#arch-arrow)" />
  );

  return (
    <Panel title="Where the data goes" meta="AI reads, code checks">
      <svg viewBox={`-2 0 1004 ${H}`} className="w-full" role="img"
        aria-label="Architecture: sources, page-anchored corpus, code detectors and LLM reading, code verifier, audit ledger, scorer, this UI">
        <defs>
          <marker id="arch-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill={t.muted} />
          </marker>
        </defs>
        <rect x={0} y={8} width={170} height={220} rx={8} fill={t.surface} stroke={t.purple} strokeWidth={1.5} />
        <text x={85} y={30} textAnchor="middle" fontSize={13} fontWeight={700} fill={t.fg}>Public sources</text>
        {SOURCES.map((s, i) => (
          <text key={s} x={14} y={54 + i * 24} fontSize={11.5} fill={t.fg}><tspan fill={t.purple}>■ </tspan>{s}</text>
        ))}
        {arrow(170, cy, 194, cy, "a0")}
        {nodes.map(box)}
        {arrow(320, cy, 342, 69, "a1")}
        {arrow(320, cy, 342, 167, "a2")}
        {arrow(472, 69, 500, cy, "a3")}
        {arrow(472, 167, 500, cy, "a4")}
        {arrow(616, cy, 644, cy, "a5")}
        {arrow(748, cy, 776, cy, "a6")}
        {arrow(872, cy, 900, cy, "a7")}
        <text x={558} y={226} textAnchor="middle" fontSize={11} fill={t.bad}>rejects logged</text>
        <path d={`M558,190 L558,212`} stroke={t.bad} strokeWidth={1.5} markerEnd="url(#arch-arrow)" />
      </svg>
      <p className="mt-2 text-[14px] font-semibold">AI reads, code checks.
        <span className="font-normal text-muted text-[13px]"> The model only proposes; a claim reaches the scorer only after the verifier finds its quote and figures on the cited page. Every step appends to the ledger. The cockpit reads precomputed JSON from <code className="font-mono text-[12px]">ui/public/data/</code> with no network at runtime. Teal marks the one model step.</span>
      </p>
      <SourceNote>pipeline as built in agent/needle (detect/, pages.py verifier, audit.py ledger, score.py) and agent/ui_export.py</SourceNote>
    </Panel>
  );
}
