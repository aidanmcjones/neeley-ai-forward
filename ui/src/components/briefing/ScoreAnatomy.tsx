import { Bar, BarChart, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel } from "..";
import { scoreFactors } from "../../lib/stance";
import type { Finding } from "../../lib/types";
import { useChartColors } from "./chartTheme";
import { barLabel } from "./BarLabel";

// Score anatomy: each vector component as its multiplier in S, on one axis (x1 = neutral).
const FORMULA = "S = I_norm × P × T × O × E × (1 + 0.25 max(Z,0)) × (1 + 0.25 D)";

export function ScoreAnatomy({ finding, ticker }: { finding: Finding | undefined; ticker: string }) {
  const c = useChartColors();
  const { factors, s } = scoreFactors(finding);
  const data = factors.map((f) => ({
    name: f.label,
    m: f.mult ?? 0,
    text: f.mult == null ? "n/a" : f.key === "Z" || f.key === "D" ? `${f.rawText} \u2192 \u00d7${f.mult.toFixed(2)}` : f.rawText,
    why: f.why,
  }));
  const max = Math.max(1.25, ...data.map((d) => d.m));

  return (
    <Panel title="Score anatomy" meta={<span className="font-mono tnum">S = {s != null ? s.toFixed(4) : "n/a"}</span>} bodyClassName="px-4 py-3">
      {!finding?.vector ? (
        <p className="text-sm text-muted">No score vector for this finding (vector missing in companies/{ticker}.json).</p>
      ) : (
        <>
          <p className="font-mono text-[10px] leading-snug text-muted tnum mb-1">{FORMULA}</p>
          <div className="h-[182px]" role="img" aria-label={`Score factors: ${data.map((d) => `${d.name} ${d.text}`).join(", ")}`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ top: 2, right: 8, bottom: 2, left: 0 }} barCategoryGap={4}>
                <XAxis type="number" hide domain={[0, max * 2]} />
                <YAxis type="category" dataKey="name" width={98} tickLine={false} axisLine={false}
                  tick={{ fill: c.fg, fontSize: 11, fontFamily: "JetBrains Mono" }} />
                <ReferenceLine x={1} stroke={c.muted} strokeDasharray="0" strokeOpacity={0.5} />
                <Tooltip
                  cursor={{ fill: c.line, opacity: 0.35 }}
                  formatter={(_v: number, _n: string, item: { payload?: { text: string; why: string } }) => [item.payload?.text ?? "", item.payload?.why ?? ""]}
                  contentStyle={{ background: c.surface, border: `1px solid ${c.line}`, borderRadius: 6, fontSize: 12, color: c.fg }}
                  labelStyle={{ color: c.fg, fontWeight: 600 }}
                />
                <Bar dataKey="m" fill={c.purple} barSize={14} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  <LabelList dataKey="text" content={barLabel(c.fg, (v) => String(v ?? ""))} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[11px] text-muted font-mono tnum">
            recomputed S = {s != null ? s.toFixed(4) : "n/a"} · exported score {finding.score != null ? finding.score.toFixed(4) : "n/a"} · rule = ×1 (neutral) · companies/{ticker}.json vector
          </p>
        </>
      )}
    </Panel>
  );
}
