import { Bar, BarChart, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel } from "..";
import { scoreFactors } from "../../lib/stance";
import type { Finding } from "../../lib/types";
import { useChartColors } from "./chartTheme";
import { barLabel } from "./BarLabel";

// Score anatomy: each vector component as its multiplier in S, on one axis (x1 = neutral).
const FORMULA = "S = I_norm × P × T × O × E × (1 + 0.25 max(Z,0)) × (1 + 0.25 D)";

const num = (x: unknown): number | null => (typeof x === "number" && Number.isFinite(x) ? x : null);

/** v2 engine (FIND, docs/quant_model.md): S = M × O × E × π, with the v1 score struck through. */
function ScoreAnatomyV2({ finding, ticker }: { finding: Finding; ticker: string }) {
  const v = finding.vector!.v2!;
  const S = num(v.S);
  const old = num(v.old_S) ?? num(finding.old_score);
  const rows: { k: string; label: string; val: number | null; frac: number | null; why: string }[] = [
    { k: "M", label: "M magnitude", val: num(v.M), frac: null, why: "EPS impact ÷ the company's usual EPS surprise (σ)" },
    { k: "O", label: "O obscurity", val: num(v.O), frac: num(v.O), why: "1 = unseen by headlines and analysts; needle floor 0.5" },
    { k: "E", label: "E evidence", val: num(v.E), frac: num(v.E), why: "quoted, page-verified evidence; needle floor 0.9" },
    { k: "pi", label: "π not priced", val: num(v.pi), frac: num(v.pi), why: "probability the market has not priced it" },
  ];
  return (
    <Panel title="Score anatomy v2" meta={<span className="font-mono tnum">S = {S != null ? S.toFixed(4) : "n/a"}</span>} bodyClassName="px-4 py-3">
      <p className="font-mono text-[10px] leading-snug text-muted tnum mb-2">S = M × O × E × π</p>
      <dl className="space-y-1.5">
        {rows.map((r) => (
          <div key={r.k} className="grid grid-cols-[98px_1fr_64px] items-center gap-2" title={r.why}>
            <dt className="font-mono text-[11px]">{r.label}</dt>
            <dd className="h-3 rounded bg-line/60 overflow-hidden" aria-hidden="true">
              {r.frac != null
                ? <div className="h-full bg-purple" style={{ width: `${Math.max(0, Math.min(1, r.frac)) * 100}%` }} />
                : <div className="h-full bg-purple/60" style={{ width: `${Math.min(1, (r.val ?? 0) / 2) * 100}%` }} />}
            </dd>
            <dd className="font-mono text-[11px] tnum text-right">{r.val != null ? (r.val !== 0 && Math.abs(r.val) < 0.01 ? r.val.toFixed(4) : r.val.toFixed(2)) : "n/a"}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[11px] text-muted font-mono tnum leading-snug">
        S = {S != null ? S.toFixed(4) : "n/a"}{old != null ? <> · v1 score <s>{old.toFixed(4)}</s> (replaced)</> : " · no v1 score"}{typeof v.pi_route === "string" ? ` · π route ${v.pi_route}` : ""} · companies/{ticker}.json vector.v2
      </p>
    </Panel>
  );
}

export function ScoreAnatomy({ finding, ticker }: { finding: Finding | undefined; ticker: string }) {
  if (finding?.vector?.v2) return <ScoreAnatomyV2 finding={finding} ticker={ticker} />;
  return <ScoreAnatomyV1 finding={finding} ticker={ticker} />;
}

function ScoreAnatomyV1({ finding, ticker }: { finding: Finding | undefined; ticker: string }) {
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
