import { useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { num } from "../../lib/format";
import { Panel } from "..";
import { Markdown } from "./Markdown";
import { Pill, SourceNote, useTokens } from "./common";

// (b) Backtest, honestly: the refuted v1 claim, the v2 table with firm-clustered CIs, dose-response.

interface Ev { hits?: number; n?: number; hit_rate?: number; rate_when_not_fired?: number; lift?: number; lift_ci95_firm_clustered?: number[] | null }
interface Sig { n_fired?: number; episodes?: number; firms?: number; events?: Record<string, Ev> }
interface HitRates {
  version?: number; universe?: number; firm_quarters?: number; companies_observed?: number; window_quarters?: number; period?: string;
  primary_event?: string; signals?: Record<string, Sig>; dose_response_full_coverage?: Record<string, { n?: number; hard_rate?: number; margin_rate?: number }>;
}

const LABEL: Record<string, string> = {
  inventory_outpaces_revenue: "Inventory outpaces revenue",
  receivables_outpace_revenue: "Receivables outpace revenue",
  dso_rising: "Days sales outstanding rising",
  dio_rising: "Days inventory rising",
  gross_margin_drop: "Gross margin drop",
};
const pct1 = (x?: number) => (typeof x === "number" ? `${(x * 100).toFixed(1)}%` : "n/a");

function LiftCell({ ev }: { ev?: Ev }) {
  if (!ev || typeof ev.lift !== "number") return <span className="text-muted">n/a</span>;
  const ci = ev.lift_ci95_firm_clustered;
  const proven = Array.isArray(ci) && ci.length === 2 && ci[0] > 1;
  return (
    <div className="flex flex-col items-end gap-1 whitespace-nowrap">
      <span><span className="font-mono tnum">{ev.lift.toFixed(2)}</span>{" "}
        <span className="font-mono tnum text-[11px] text-muted">{Array.isArray(ci) ? `[${ci[0].toFixed(2)}, ${ci[1].toFixed(2)}]` : "CI n/a"}</span></span>
      {proven ? <Pill tone="good">proven</Pill> : <Pill tone="grey">not proven</Pill>}
    </div>
  );
}

export function BacktestPanel({ hitRates, gate2 }: { hitRates: unknown; gate2?: string }) {
  const t = useTokens();
  const hr = (hitRates ?? {}) as HitRates;
  const sigs = Object.entries(hr.signals ?? {});
  const dose = Object.entries(hr.dose_response_full_coverage ?? {})
    .map(([k, v]) => ({ k: Number(k), label: `${k}`, n: v.n ?? 0, margin: v.margin_rate ?? null, hard: v.hard_rate ?? null }))
    .sort((a, b) => a.k - b.k);
  const [open, setOpen] = useState(false);

  const capLabel = (p: { x?: number | string; y?: number | string; width?: number | string; value?: number | string }) => {
    const v = Number(p.value);
    if (!Number.isFinite(v)) return null;
    return <text x={Number(p.x) + Number(p.width) / 2} y={Number(p.y) - 5} textAnchor="middle" fontSize={11} fontFamily="JetBrains Mono" fill={t.fg}>{`${Math.round(v * 100)}%`}</text>;
  };
  const tickN = (p: { x?: number | string; y?: number | string; payload?: { value?: string } }) => {
    const row = dose.find((d) => d.label === p.payload?.value);
    return (
      <g transform={`translate(${p.x},${p.y})`}>
        <text dy={12} textAnchor="middle" fontSize={12} fill={t.fg} fontFamily="JetBrains Mono">{p.payload?.value}</text>
        <text dy={26} textAnchor="middle" fontSize={10.5} fill={t.muted} fontFamily="JetBrains Mono">n={row?.n ?? "?"}</text>
      </g>
    );
  };

  return (
    <Panel title="(b) Backtest, honestly" meta={`v${hr.version ?? "?"} · ${num(hr.firm_quarters)} firm-quarters · ${hr.companies_observed ?? "?"} companies · ${hr.period ?? ""}`}>
      <div role="note" className="rounded-md border-l-4 border-bad bg-bad/10 px-4 py-3">
        <div className="flex items-center gap-2"><Pill tone="bad">refuted</Pill><span className="font-semibold text-[15px]">Our first backtest claimed lift 1.39. Our own adversarial review refuted it.</span></div>
        <p className="mt-1 text-[13px] text-muted">
          Two skeptics found overlapping event windows (leakage), a signal scored against its own series, and lift that was between firms rather than within one.
          v2 below fixes all of it: point-in-time inputs (filed within 135 days), non-overlapping {hr.window_quarters ?? 8}-quarter windows, firm-clustered 95% CIs, no LLM.
        </p>
      </div>

      <div className="mt-4 overflow-auto rounded-md border border-line">
        <table className="w-full border-collapse text-[13px]">
          <thead className="bg-surface-2">
            <tr>
              {["Signal", "Fired", "Episodes", "Hard-event hit: fired vs not", "Hard-event lift [95% CI]", "Margin-drop lift [95% CI]"].map((h, i) => (
                <th key={h} scope="col" className={`px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sigs.map(([k, s]) => {
              const hard = s.events?.hard, mg = s.events?.margin_drop;
              return (
                <tr key={k} className="border-b border-line last:border-0">
                  <th scope="row" className="text-left px-3 py-2 font-semibold">{LABEL[k] ?? k}<div className="font-mono text-[10.5px] text-muted font-normal">{k}</div></th>
                  <td className="px-3 py-2 text-right font-mono tnum">{num(s.n_fired)}</td>
                  <td className="px-3 py-2 text-right font-mono tnum">{num(s.episodes)}<div className="text-[10.5px] text-muted">{s.firms ?? "?"} firms</div></td>
                  <td className="px-3 py-2 text-right font-mono tnum">{pct1(hard?.hit_rate)} <span className="text-muted">vs</span> {pct1(hard?.rate_when_not_fired)}</td>
                  <td className="px-3 py-2"><LiftCell ev={hard} /></td>
                  <td className="px-3 py-2"><LiftCell ev={mg} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[12.5px] text-muted">
        Materiality rule (<code className="font-mono text-[11.5px]">score._proven</code>): a lift counts as proven only when its whole firm-clustered CI lies above 1.
        No signal is proven on hard events (revenue drop or impairment), so forensic signals are flags for human review, not predictions. Some are proven on future margin compression.
      </p>

      <div className="mt-5 grid grid-cols-[minmax(0,7fr)_minmax(0,5fr)] gap-5 items-start">
        <div className="min-w-0">
          <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">Dose-response: event rate by number of signals fired (full-coverage rows)</h3>
          <div style={{ height: 270 }} className="mt-1" role="img" aria-label="Margin-drop rate and hard-event rate by number of signals fired">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dose} margin={{ top: 22, right: 8, bottom: 18, left: 0 }} barGap={2} barCategoryGap="22%">
                <CartesianGrid vertical={false} stroke={t.line} />
                <XAxis dataKey="label" tick={tickN} interval={0} axisLine={{ stroke: t.line }} tickLine={false} height={34}
                  label={{ value: "signals fired", position: "insideBottom", offset: -14, fontSize: 11, fill: t.muted }} />
                <YAxis tickFormatter={(v: number) => `${Math.round(v * 100)}%`} domain={[0, 0.7]} ticks={[0, 0.2, 0.4, 0.6]} tick={{ fontSize: 11, fill: t.muted, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} width={40} />
                <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} labelFormatter={(l: string) => `${l} signals fired (n=${dose.find((d) => d.label === l)?.n ?? "?"})`}
                  contentStyle={{ fontSize: 12, borderRadius: 6, borderColor: t.line, background: t.surface, color: t.fg }} cursor={{ fill: t.line, opacity: 0.4 }} />
                <Legend verticalAlign="top" align="right" height={22} iconType="square" wrapperStyle={{ fontSize: 12, top: -4 }} formatter={(v: string) => <span style={{ color: t.fg }}>{v}</span>} />
                <Bar dataKey="margin" name="Margin drop within 8Q" fill={t.purpleBright} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false}>
                  <LabelList dataKey="margin" content={capLabel} />
                </Bar>
                <Bar dataKey="hard" name="Hard event within 8Q" fill={t.grey} radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false}>
                  <LabelList dataKey="hard" content={capLabel} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="text-[13px] space-y-2 pt-5">
          <p><strong>Margin compression climbs with the signal count</strong>: 12% with no signals to 61% with all five (n = 18, a small group).</p>
          <p><strong>Hard events stay flat</strong> at about 23% to 28% whatever fires. That is why the scorer never lets a forensic signal raise a hard-event claim.</p>
          <p className="text-muted">The skeptics' corrected v1 estimate (lift about 1.4 to 1.6) did not survive the stricter v2 filters, so we do not claim it.</p>
        </div>
      </div>

      {gate2 && (
        <div className="mt-4 rounded-md border border-line">
          <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)}
            className="w-full flex items-center justify-between px-4 py-2.5 text-left text-[13px] font-semibold hover:bg-surface-2">
            <span>Read the gate 2 review (the adversarial verdict, in full)</span>
            <span aria-hidden="true" className="font-mono">{open ? "−" : "+"}</span>
          </button>
          {open && <div className="border-t border-line px-4 py-3"><Markdown source={gate2} /></div>}
        </div>
      )}
      <SourceNote>proof.json · backtest.hit_rates (out/backtest/hit_rates.json) · backtest.gate2_md (docs/needle_gate2.md)</SourceNote>
    </Panel>
  );
}
