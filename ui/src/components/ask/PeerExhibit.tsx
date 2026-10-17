import type { Company } from "../../lib/types";
import { fmtPeer, peerUnit, useThemeColors } from "../../lib/exhibits";
import { ExhibitCard } from "./ExhibitCard";

// Two horizontal bars from one finding's peer block: company metric (purple) vs peer median (grey).
export function PeerExhibit({ company, target: id, title }: { company: Company; target: string; title: string }) {
  const col = useThemeColors();
  const f = company.findings.find((x) => x.id === id);
  const p = f?.peer;
  const ev = f?.evidence?.[0];
  const source = <>findings[{id}].peer in companies/{company.ticker}.json{ev?.citation ? ` (${ev.citation})` : ""}</>;
  const pin = { kind: "peer", ref: id, title };
  if (!f || p?.metric_value == null || p?.peer_median == null) {
    return <ExhibitCard ticker={company.ticker} pin={pin} source={source}><p className="text-sm text-muted">No peer median exported for this finding.</p></ExhibitCard>;
  }
  // Shift-type signals compare a change with a peer level: drawing them on one scale would mislead.
  if (/_shift$|_drop$/.test(f.signal_kind ?? "")) {
    return (
      <ExhibitCard ticker={company.ticker} pin={pin} source={source} reading={f.finding}>
        <p className="text-sm text-muted">The metric is a year-over-year change and the peer median is a level, so no bar is drawn.</p>
      </ExhibitCard>
    );
  }
  const u = peerUnit(f);
  const a = p.metric_value, b = p.peer_median;
  const lo = Math.min(0, a, b), hi = Math.max(0, a, b);
  const W = 340, L = 92, R = 70, bar = 20, gap = 14, top = 6;
  const sx = (v: number) => L + ((v - lo) / (hi - lo || 1)) * (W - L - R);
  const zeroX = sx(0);
  const zTxt = p.z != null ? `z ${p.z > 0 ? "+" : ""}${p.z.toFixed(1)}` : "";
  const bars = [
    { label: company.ticker, v: a, color: col.purple },
    { label: "Peer median", v: b, color: col["frog-grey"] },
  ];
  const H = top + bars.length * (bar + gap) + 4;
  return (
    <ExhibitCard ticker={company.ticker} pin={pin} source={source}
      reading={`${company.ticker} ${fmtPeer(a, u)} vs peer median ${fmtPeer(b, u)}${zTxt ? `, ${zTxt}` : ""}.`}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[400px] h-auto" role="img" aria-label={`${company.ticker} ${fmtPeer(a, u)} vs peer median ${fmtPeer(b, u)}`}>
        {bars.map((r, i) => {
          const y = top + i * (bar + gap);
          const x0 = Math.min(zeroX, sx(r.v)), w = Math.max(2, Math.abs(sx(r.v) - zeroX));
          const neg = r.v < 0;
          // 4px rounded data end, square at the baseline.
          const d = neg
            ? `M${x0 + w},${y} H${x0 + 4} Q${x0},${y} ${x0},${y + 4} V${y + bar - 4} Q${x0},${y + bar} ${x0 + 4},${y + bar} H${x0 + w} Z`
            : `M${x0},${y} H${x0 + w - 4} Q${x0 + w},${y} ${x0 + w},${y + 4} V${y + bar - 4} Q${x0 + w},${y + bar} ${x0 + w - 4},${y + bar} H${x0} Z`;
          return (
            <g key={r.label}>
              <title>{`${r.label}: ${fmtPeer(r.v, u)}`}</title>
              <text x={0} y={y + bar / 2} dominantBaseline="middle" fontSize={12} fontWeight={i === 0 ? 700 : 500} fill={col.fg}>{r.label}</text>
              <path d={d} fill={r.color} />
              <text x={neg ? x0 - 4 : x0 + w + 4} y={y + bar / 2} dominantBaseline="middle" textAnchor={neg ? "end" : "start"} fontSize={11.5} fill={col.fg} className="tnum font-mono">{fmtPeer(r.v, u)}</text>
            </g>
          );
        })}
        <line x1={zeroX} x2={zeroX} y1={0} y2={H} stroke={col.muted} strokeWidth={1} />
      </svg>
      {zTxt && <div className="mt-1 text-[11px] text-muted">Peer z-score: <span className="font-mono tnum text-fg">{zTxt}</span> ({f.signal_kind?.replace(/_/g, " ")})</div>}
    </ExhibitCard>
  );
}
