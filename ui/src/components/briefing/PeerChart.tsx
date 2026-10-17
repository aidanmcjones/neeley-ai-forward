import { Bar, BarChart, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel } from "..";
import { z } from "../../lib/format";
import { isShiftMetric, metricText } from "../../lib/stance";
import type { Finding } from "../../lib/types";
import { useChartColors } from "./chartTheme";
import { barLabel } from "./BarLabel";

// "This company vs peer median" for the selected finding. Emphasis encoding:
// purple = the company, frog-grey = the peer median. Both bars are direct-labeled.
export function PeerChart({ finding, ticker }: { finding: Finding | undefined; ticker: string }) {
  const c = useChartColors();
  const p = finding?.peer;
  const ok = p?.metric_value != null && p?.peer_median != null;
  const data = ok
    ? [
        { name: ticker, v: p!.metric_value as number, fill: c.purple },
        { name: "Peer median", v: p!.peer_median as number, fill: c["frog-grey"] },
      ]
    : [];
  const lo = Math.min(0, ...data.map((d) => d.v));
  const hi = Math.max(0, ...data.map((d) => d.v));
  const pad = (hi - lo || 1) * 0.62;

  return (
    <Panel title="This company vs peer median" bodyClassName="px-4 py-3">
      {!finding ? (
        <p className="text-sm text-muted">Select a finding in the grid.</p>
      ) : !ok ? (
        <p className="text-sm text-muted">
          No peer comparison for this signal: <code className="font-mono text-xs">peer.{p?.metric_value == null ? "metric_value" : "peer_median"}</code> is not exported in companies/{ticker}.json.
        </p>
      ) : (
        <>
          <div className="h-[118px]" role="img" aria-label={`${ticker} ${metricText(finding, data[0].v)} versus peer median ${metricText(finding, data[1].v)}, ${z(p?.z)}`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ top: 4, right: 8, bottom: 4, left: 0 }} barCategoryGap={10}>
                <XAxis type="number" hide domain={[lo < 0 ? lo - pad : 0, hi + pad]} />
                <YAxis type="category" dataKey="name" width={100} tickLine={false} axisLine={false}
                  tick={{ fill: c.fg, fontSize: 11, fontWeight: 600, fontFamily: "Montserrat" }} />
                {lo < 0 && <ReferenceLine x={0} stroke={c.line} />}
                <Tooltip
                  cursor={{ fill: c.line, opacity: 0.35 }}
                  formatter={(v: number) => [metricText(finding, v), "value"]}
                  contentStyle={{ background: c.surface, border: `1px solid ${c.line}`, borderRadius: 6, fontSize: 12, color: c.fg }}
                  labelStyle={{ color: c.fg, fontWeight: 600 }}
                />
                <Bar dataKey="v" barSize={22} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  {data.map((d) => <Cell key={d.name} fill={d.fill} />)}
                  <LabelList dataKey="v" content={barLabel(c.fg, (v) => metricText(finding, typeof v === "number" ? v : null), 12)} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[11px] text-muted">
            {finding.signal_kind ?? "signal"} · {p?.z != null ? `${z(p.z)} vs peers` : "no peer z exported"}{isShiftMetric(finding) ? " · company value is the year-over-year change, the median is the peer level" : ""} · companies/{ticker}.json peer
          </p>
          <table className="sr-only">
            <caption>Peer comparison values</caption>
            <tbody>{data.map((d) => <tr key={d.name}><th>{d.name}</th><td>{metricText(finding, d.v)}</td></tr>)}</tbody>
          </table>
        </>
      )}
    </Panel>
  );
}
