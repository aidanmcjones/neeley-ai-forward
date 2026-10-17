import { useEffect, useRef, useState } from "react";
import type { Company, Comparison } from "../../lib/types";
import { drugName, str, useTokens } from "./util";

// Exclusivity timeline strip, 2024 to 2032: FDA-derived dates dashed ("estimate"), IRA MFP effective dates solid,
// today's line. Dates outside the axis are pinned to the edge with an arrow and their full date.

const START = new Date(2024, 0, 1).getTime();
const END = new Date(2033, 0, 1).getTime();
const YEARS = Array.from({ length: 10 }, (_, i) => 2024 + i);

type Mark = { date: string; label: string; kind: "fda" | "ob" | "ira" };

const parse = (d: string) => { const [y, m, dd] = d.split("-").map(Number); return new Date(y, (m || 1) - 1, dd || 1).getTime(); };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(900);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(500, Math.floor(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

function marksFor(company: Company, comp: Comparison, slug: string): Mark[] {
  const rows = comp.rows ?? [];
  const v = (f: string) => rows.find((r) => r.field === f)?.values?.[slug]?.value;
  const out: Mark[] = [];
  const fda = str(v("exclusivity_fda_estimate"));
  if (fda && /^\d{4}-\d{2}-\d{2}$/.test(fda)) out.push({ date: fda, label: `FDA est. ${fda}`, kind: "fda" });
  // Orange Book regulatory exclusivity (latest code) from the raw labels table.
  const prod = (company.labels as { products?: Record<string, { table?: { field: string; product?: unknown; rivals?: Record<string, unknown> }[] }> } | null)?.products?.[comp.product];
  const obRow = prod?.table?.find((r) => r.field === "Orange Book exclusivity");
  const obStr = str(slug === comp.product ? obRow?.product : obRow?.rivals?.[slug]);
  if (obStr) {
    const items = obStr.split(";").map((s) => s.trim().match(/^(\S+)\s+(\d{4}-\d{2}-\d{2})$/)).filter(Boolean) as RegExpMatchArray[];
    const last = items.sort((a, b) => a[2].localeCompare(b[2])).pop();
    if (last && last[2] !== fda) out.push({ date: last[2], label: `OB excl. ${last[1]} ${last[2]}`, kind: "ob" });
  }
  const g = (company.gtn_exposure ?? []).find((r) => r.drug === slug);
  const eff = str(g?.ira_mfp_effective);
  if (eff) out.push({ date: eff, label: `IRA MFP ${eff}`, kind: "ira" });
  else {
    const m = String(v("ira_status") ?? "").match(/Selected IPAY (\d{4})/);
    if (m) out.push({ date: `${m[1]}-01-01`, label: `IRA MFP IPAY ${m[1]}`, kind: "ira" });
  }
  return out.sort((a, b) => a.date.localeCompare(b.date));
}

export function ExclusivityStrip({ company, comp, asOf }: { company: Company; comp: Comparison; asOf?: string }) {
  const t = useTokens();
  const [ref, w] = useWidth<HTMLDivElement>();
  const drugs = [comp.product, ...(comp.rivals ?? [])];
  const LEFT = 130, RIGHT = 24, ROW = 58, TOP = 26;
  const H = TOP + drugs.length * ROW + 24;
  const x = (ms: number) => LEFT + ((Math.min(Math.max(ms, START), END) - START) / (END - START)) * (w - LEFT - RIGHT);
  const today = asOf && /^\d{4}-\d{2}-\d{2}/.test(asOf) ? parse(asOf.slice(0, 10)) : Date.now();
  const todayStr = new Date(today).toISOString().slice(0, 10);

  return (
    <div ref={ref} className="w-full">
      <svg width={w} height={H} role="img" aria-label={`Exclusivity and IRA timeline, ${drugs.map(drugName).join(", ")}, 2024 to 2032`}>
        {YEARS.map((y) => {
          const xx = x(new Date(y, 0, 1).getTime());
          return (
            <g key={y}>
              <line x1={xx} x2={xx} y1={TOP - 6} y2={H - 22} stroke={t.line} strokeWidth={1} />
              {y < 2033 && <text x={xx + 3} y={TOP - 10} fill={t.muted} fontSize={11} className="tnum">{y}</text>}
            </g>
          );
        })}
        <line x1={x(today)} x2={x(today)} y1={TOP - 6} y2={H - 16} stroke={t.fg} strokeWidth={1.5} />
        <text x={x(today)} y={H - 3} textAnchor="middle" fill={t.fg} fontSize={11} fontWeight={600}>today {todayStr}</text>
        {drugs.map((d, i) => {
          const y = TOP + i * ROW + ROW / 2;
          const own = i === 0;
          const color = own ? t.purple : t.grey;
          const marks = marksFor(company, comp, d);
          return (
            <g key={d}>
              <text x={8} y={y - 2} fill={t.fg} fontSize={13} fontWeight={700}>{drugName(d)}</text>
              <text x={8} y={y + 13} fill={t.muted} fontSize={10}>{own ? "product" : "rival"} · co.-stated: n/a</text>
              <line x1={LEFT} x2={w - RIGHT} y1={y} y2={y} stroke={color} strokeWidth={own ? 3 : 2} strokeLinecap="round" opacity={own ? 1 : 0.8} />
              {marks.map((m, j) => {
                const ms = parse(m.date);
                const off = ms >= END ? "right" : ms < START ? "left" : null;
                const xx = x(ms);
                const above = j % 2 === 0;
                const ty = above ? y - 10 : y + 20;
                const anchor = xx > w - RIGHT - 120 ? "end" : xx < LEFT + 60 ? "start" : "middle";
                const label = off === "right" ? `${m.label} →` : off === "left" ? `← ${m.label}` : m.label;
                const est = m.kind !== "ira";
                return (
                  <g key={j}>
                    {m.kind === "ira" ? (
                      <rect x={xx - 5} y={y - 5} width={10} height={10} fill={t.fg} stroke={t.surface} strokeWidth={2} transform={`rotate(45 ${xx} ${y})`} />
                    ) : (
                      <circle cx={xx} cy={y} r={5.5} fill={t.surface} stroke={color === t.grey ? t.muted : color} strokeWidth={2} strokeDasharray="2.5 2" />
                    )}
                    <text x={xx} y={ty} textAnchor={anchor} fill={est ? t.muted : t.fg} fontSize={11} fontStyle={est ? "italic" : "normal"} className="tnum" stroke={t.surface} strokeWidth={4} strokeLinejoin="round" style={{ paintOrder: "stroke" }}>
                      {label}{est ? " (estimate)" : ""}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-muted">
        <span className="inline-flex items-center gap-1.5">
          <svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke={t.muted} strokeWidth="2" strokeDasharray="2.5 2" /></svg>
          FDA-derived date, dashed = estimate (latest Orange Book patent / exclusivity or Purple Book 12-year date: a lower bound on protection, not a generic-entry date)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <svg width="14" height="14" aria-hidden="true"><rect x="3" y="3" width="8" height="8" fill={t.fg} transform="rotate(45 7 7)" /></svg>
          IRA maximum fair price effective (CMS)
        </span>
        <span>Company-stated LOE dates: not in this export (company_stated_loe.jsonl not in this checkout). Arrows mark dates beyond the 2024 to 2032 axis.</span>
      </div>
      <div className="font-mono text-[10px] text-muted mt-1">labels.comparison (orange_book_patents.csv, orange_book_exclusivity.csv, purple_book.csv) · gtn_exposure.csv (ira_mfp_effective) · ira_negotiation.csv</div>
    </div>
  );
}
