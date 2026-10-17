import type { Company } from "../../lib/types";
import { timelineLanes, titleCase, useThemeColors, useWidth } from "../../lib/exhibits";
import type { TimelineMark } from "../../lib/exhibits";
import { ExhibitCard } from "./ExhibitCard";

// Exclusivity / IRA timeline: one lane per drug (product purple, rivals frog-grey).
// Circle = FDA estimate (open ring + "≥" when a biologic 12-year lower bound), diamond =
// company-stated, square = IRA MFP effective date. Vertical rule = as-of date.
export function TimelineExhibit({ company, target: product, title, asOf }: { company: Company; target: string; title: string; asOf?: string }) {
  const col = useThemeColors();
  const [box, width] = useWidth<HTMLDivElement>();
  const lanes = timelineLanes(company, product);
  const today = asOf ? new Date(asOf) : new Date();
  const all = lanes.flatMap((l) => l.marks);
  if (!lanes.length || !all.length) {
    return (
      <ExhibitCard ticker={company.ticker} pin={{ kind: "timeline", ref: product, title }} wide source={`labels.comparison in companies/${company.ticker}.json`}>
        <p className="text-sm text-muted">No exclusivity or IRA dates exported for {titleCase(product)}.</p>
      </ExhibitCard>
    );
  }
  const years = [...all.map((m) => m.date.getFullYear()), today.getFullYear()];
  const y0 = Math.min(...years) - 1, y1 = Math.max(...years) + 2;
  const W = width, L = 92, R = 16, laneH = 50, top = 34;
  const H = top + lanes.length * laneH + 26;
  const x = (d: Date) => L + ((d.getFullYear() + d.getMonth() / 12 + d.getDate() / 365 - y0) / (y1 - y0)) * (W - L - R);
  const step = y1 - y0 > 14 ? 4 : 2;
  const ticks: number[] = [];
  for (let y = Math.ceil(y0 / step) * step; y <= y1; y += step) ticks.push(y);

  const own = lanes.find((l) => l.own);
  const reading = lanes.map((l) => {
    const f = l.marks.find((m) => m.kind === "fda");
    const m = l.marks.find((m) => m.kind === "mfp");
    return `${titleCase(l.slug)}: FDA ${f ? `${f.lowerBound ? "≥ " : ""}${f.iso}` : "n/a"}${m ? `, ${m.label}` : ""}`;
  }).join(" · ");
  const sources = [...new Set(all.map((m) => m.source).filter(Boolean))];

  const mark = (m: TimelineMark, color: string, cy: number) => {
    const cx = x(m.date);
    const ring = col.surface;
    if (m.kind === "company") return <rect x={cx - 5} y={cy - 5} width={10} height={10} transform={`rotate(45 ${cx} ${cy})`} fill={color} stroke={ring} strokeWidth={2} />;
    if (m.kind === "mfp") return <rect x={cx - 5} y={cy - 5} width={10} height={10} rx={1} fill={color} stroke={ring} strokeWidth={2} />;
    return m.lowerBound
      ? <circle cx={cx} cy={cy} r={5.5} fill={col.surface} stroke={color} strokeWidth={2.5} />
      : <circle cx={cx} cy={cy} r={5.5} fill={color} stroke={ring} strokeWidth={2} />;
  };

  return (
    <ExhibitCard ticker={company.ticker} pin={{ kind: "timeline", ref: product, title }} wide reading={reading}
      source={<>labels.comparison in companies/{company.ticker}.json ({sources.join("; ")})</>}>
      <div ref={box} className="w-full min-w-0"><svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block max-w-full h-auto" role="img" aria-label={`Timeline: ${reading}`}>
        {ticks.map((t) => {
          const tx = x(new Date(t, 0, 1));
          return (
            <g key={t}>
              <line x1={tx} x2={tx} y1={top - 6} y2={H - 22} stroke={col.line} strokeWidth={1} />
              <text x={tx} y={H - 8} textAnchor="middle" fontSize={11} fill={col.muted} className="tnum font-mono">{t}</text>
            </g>
          );
        })}
        <line x1={x(today)} x2={x(today)} y1={top - 18} y2={H - 22} stroke={col.fg} strokeWidth={1.5} />
        <text x={x(today) + 4} y={top - 30} fontSize={10} fill={col.muted} dominantBaseline="hanging">as of {today.toISOString().slice(0, 10)}</text>
        {lanes.map((l, i) => {
          const cy = top + i * laneH + laneH / 2;
          const color = l.own ? col.purple : col["frog-grey"];
          const sorted = l.marks.slice().sort((a, b) => a.date.getTime() - b.date.getTime());
          return (
            <g key={l.slug}>
              <text x={0} y={cy} dominantBaseline="middle" fontSize={12} fontWeight={l.own ? 700 : 500} fill={col.fg}>{titleCase(l.slug)}</text>
              <line x1={L} x2={W - R} y1={cy} y2={cy} stroke={col.line} strokeWidth={1} />
              {sorted.length > 1 && <line x1={x(sorted[0].date)} x2={x(sorted[sorted.length - 1].date)} y1={cy} y2={cy} stroke={color} strokeWidth={2} />}
              {sorted.map((m, j) => {
                const cx = x(m.date);
                const anchor = cx > W - 150 ? "end" : "start";
                const dy = j % 2 === 0 ? -11 : 15;
                return (
                  <g key={`${m.kind}-${j}`}>
                    <title>{`${titleCase(l.slug)} · ${m.label}: ${m.iso}${m.source ? ` (${m.source})` : ""}`}</title>
                    {mark(m, color, cy)}
                    <text x={anchor === "end" ? cx - 8 : cx + 8} y={cy + dy} textAnchor={anchor} fontSize={10.5} fill={col.fg} className="tnum">
                      {m.kind === "fda" ? `${m.lowerBound ? "≥ " : ""}${m.iso} ${m.lowerBound ? "FDA (biologic lower bound)" : "FDA est."}` : m.kind === "company" ? `${m.iso} company-stated` : m.label}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg></div>
      {lanes.some((l) => l.notes.length) && (
        <p className="mt-1 text-[11px] text-muted">{lanes.filter((l) => l.notes.length).map((l) => `${titleCase(l.slug)}: ${l.notes.join(", ")}`).join(" · ")}</p>
      )}
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted" aria-label="Legend">
        <li className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full bg-purple" />{own ? titleCase(own.slug) : "Company"} (company)</li>
        <li className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full bg-frog-grey" />Rivals</li>
        <li>● FDA estimate</li><li>○ ≥ biologic lower bound (12 years from licensure)</li><li>◆ company-stated</li><li>■ IRA MFP effective</li>
      </ul>
    </ExhibitCard>
  );
}
