import type { Meta, MoatCell } from "../../lib/types";
import { Panel } from "..";
import { Pill, SourceNote, statusTone } from "../proof/common";

// Coverage matrix in the tracker.html style: companies down, buckets across, one bar per cell.
// complete = purple, partial = amber, missing = red, not applicable = hatched. Labels always carry have/need and %.

const HATCH = "repeating-linear-gradient(135deg, rgb(var(--line)) 0 4px, rgb(var(--surface)) 4px 8px)";

function CellBar({ c }: { c?: MoatCell }) {
  if (!c || !c.need) {
    return (
      <div className="grid gap-1 min-w-[50px]" title={c?.note || "not applicable"}>
        <div className="h-2 rounded" style={{ background: HATCH }} aria-hidden="true" />
        <div className="text-[10.5px] text-muted truncate">n/a</div>
      </div>
    );
  }
  const have = c.have ?? 0;
  const pct = Math.min(100, Math.round((100 * have) / c.need));
  const fill = pct >= 100 ? "bg-purple" : pct > 0 ? "bg-warn" : "bg-bad";
  const state = pct >= 100 ? "complete" : pct > 0 ? "partial" : "missing";
  return (
    <div className="grid gap-1 min-w-[50px]" title={`${have}/${c.need} ${state}${c.note ? ` · ${c.note}` : ""}`}>
      <div className="relative h-2 rounded bg-line overflow-hidden" aria-hidden="true">
        <i className={`absolute inset-y-0 left-0 rounded ${fill}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex justify-between gap-1 text-[10px] text-muted tnum">
        <b className="font-mono font-semibold text-fg tracking-tight">{have}/{c.need}</b>
        <span className="font-mono tracking-tight">{pct}%</span>
      </div>
      <span className="sr-only">{state}</span>
    </div>
  );
}

export function CoverageMatrix({ meta }: { meta: Meta | null }) {
  const moat = meta?.moat ?? {};
  const buckets = moat.buckets ?? [];
  const cov = moat.coverage ?? {};
  const tickers = Object.keys(cov);
  const names = new Map((meta?.companies ?? []).map((c) => [c.ticker, c.name ?? ""]));
  const keys = buckets.map((b) => b.key);
  const cell = (t: string, k: string) => cov[t]?.[k];
  const sum = (cs: (MoatCell | undefined)[]) => cs.reduce<[number, number]>((a, c) => [a[0] + Math.min(c?.have ?? 0, c?.need ?? 0), a[1] + (c?.need ?? 0)], [0, 0]);
  const rowTot = Object.fromEntries(tickers.map((t) => [t, sum(keys.map((k) => cell(t, k)))]));
  const colTot = Object.fromEntries(keys.map((k) => [k, sum(tickers.map((t) => cell(t, k)))]));
  const all = sum(tickers.flatMap((t) => keys.map((k) => cell(t, k))));
  const allPct = all[1] ? Math.round((100 * all[0]) / all[1]) : 0;

  const legend = (
    <div className="flex flex-wrap gap-3 text-[11.5px] text-muted normal-case tracking-normal font-normal">
      <span className="inline-flex items-center gap-1.5"><i className="inline-block w-5 h-2 rounded bg-purple" />complete</span>
      <span className="inline-flex items-center gap-1.5"><i className="inline-block w-5 h-2 rounded bg-warn" />partial</span>
      <span className="inline-flex items-center gap-1.5"><i className="inline-block w-5 h-2 rounded bg-bad" />missing</span>
      <span className="inline-flex items-center gap-1.5"><i className="inline-block w-5 h-2 rounded" style={{ background: HATCH }} />not applicable</span>
    </div>
  );

  return (
    <Panel title="Coverage by company and data bucket" meta={legend}>
      <p className="text-[13px] text-muted mb-3">
        <strong className="text-fg font-display text-[22px] tracking-wide align-[-2px] mr-1">{allPct}%</strong>
        collected: {all[0]} of {all[1]} required items across {tickers.length} companies and {buckets.length} buckets. Column pills show collection and verifier status.
      </p>
      <div className="overflow-x-auto rounded-md border border-line bg-surface">
        <table className="border-separate border-spacing-0 w-full text-[12px]">
          <thead>
            <tr>
              <th scope="col" className="sticky left-0 z-20 bg-surface-2 px-1.5 py-2 text-left align-bottom border-b border-line text-[10.5px] uppercase tracking-wide text-muted font-semibold">Company</th>
              {buckets.map((b, i) => {
                const st = moat.status?.[b.key] ?? [];
                return (
                  <th key={b.key} scope="col" title={b.why} className="bg-surface-2 px-1.5 py-2 text-left align-top border-b border-line text-[10px] uppercase tracking-wide text-muted font-semibold leading-tight">
                    <span className="font-mono text-purple mr-1">{String(i + 1).padStart(2, "0")}</span>{b.label ?? b.key}
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {st.map((s, j) => <Pill key={j} tone={statusTone(s)} className="!text-[8.5px] !px-1 !py-0 !tracking-normal">{s}</Pill>)}
                    </div>
                  </th>
                );
              })}
              <th scope="col" className="bg-surface-2 px-1.5 py-2 text-left align-bottom border-b border-line text-[10.5px] uppercase tracking-wide text-muted font-semibold">Total</th>
            </tr>
          </thead>
          <tbody>
            {tickers.map((t) => {
              const [h, n] = rowTot[t];
              const pct = n ? Math.round((100 * h) / n) : 0;
              return (
                <tr key={t}>
                  <th scope="row" className="sticky left-0 z-10 bg-surface px-1.5 py-2 text-left align-top border-b border-line whitespace-nowrap">
                    <span className="font-display text-[20px] leading-none tracking-wide">{t}</span>
                    <small className="block text-[10px] text-muted font-normal max-w-[64px] truncate">{names.get(t)}</small>
                  </th>
                  {keys.map((k) => <td key={k} className="px-1 py-2 align-top border-b border-line"><CellBar c={cell(t, k)} /></td>)}
                  <td className="px-1.5 py-2 align-top border-b border-line">
                    <div className="grid gap-1 min-w-[58px]">
                      <div className="relative h-2.5 rounded bg-line overflow-hidden" aria-hidden="true">
                        <i className={`absolute inset-y-0 left-0 rounded ${pct >= 100 ? "bg-purple" : "bg-warn"}`} style={{ width: `${pct}%` }} />
                      </div>
                      <div className="grid text-[10.5px] tnum leading-tight">
                        <b className="font-display text-[18px] leading-none text-purple">{pct}%</b>
                        <span className="font-mono text-muted">{h}/{n}</span>
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" className="sticky left-0 z-10 bg-surface-2 px-1.5 py-2 text-left text-[12px] font-semibold border-t-2 border-line">All {tickers.length}</th>
              {keys.map((k) => {
                const [h, n] = colTot[k];
                return <td key={k} className="bg-surface-2 px-1.5 py-2 font-mono tnum text-[11.5px] border-t-2 border-line">{h}/{n}</td>;
              })}
              <td className="bg-surface-2 px-1.5 py-2 font-mono tnum font-bold border-t-2 border-line">{allPct}%</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <h3 className="mt-4 text-[12px] font-bold uppercase tracking-wide text-muted">Bucket key</h3>
      <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12.5px]">
        {buckets.map((b, i) => (
          <div key={b.key} className="grid grid-cols-[22px_1fr] gap-1.5 items-baseline">
            <span className="font-mono text-[11px] text-purple">{String(i + 1).padStart(2, "0")}</span>
            <span><b>{b.label ?? b.key}</b> <code className="font-mono text-[10.5px] text-muted">{b.key}</code>. <span className="text-muted">{b.why}</span></span>
          </div>
        ))}
      </div>
      <SourceNote>meta.json · moat.coverage, moat.buckets, moat.status (data/moat/progress.json, rebuilt by agent/moat/progress.py) · as of {moat.as_of?.slice(0, 16).replace("T", " ") ?? "n/a"} UTC</SourceNote>
    </Panel>
  );
}
