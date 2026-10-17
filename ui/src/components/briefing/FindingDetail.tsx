import type React from "react";
import type { Company, Finding } from "../../lib/types";
import { FlagPills } from "../FindingFlags";
import { NumericPill } from "../NumericCheck";

// Detail strip for the selected grid row: flags, why it is not quantified, guard reason,
// what it corroborates (jumps to that row), fact key and impact channel.
export function FindingDetail({ company, finding: f, onSelect }: { company: Company; finding: Finding; onSelect: (id: string) => void }) {
  const corr = f.corroborates ? company.findings.find((x) => x.id === f.corroborates) : undefined;
  const rows: [string, React.ReactNode][] = [];
  if (f.not_quantified) rows.push(["Not quantified", f.not_quantified]);
  if (f.guard_reason) rows.push(["Guard", f.guard_reason]);
  if (f.corroborates) rows.push(["Corroborates", corr
    ? <button type="button" onClick={() => onSelect(corr.id)} className="text-purple underline text-left" title={corr.finding}>corroborates {f.corroborates.slice(0, 6)}: {corr.finding.slice(0, 80)}{corr.finding.length > 80 ? "…" : ""}</button>
    : <span className="font-mono">corroborates {f.corroborates.slice(0, 6)} (row not in this export)</span>]);
  if (f.impact_channel) rows.push(["Impact channel", <span className="font-mono">{f.impact_channel}</span>]);
  if (f.fact_key) rows.push(["Fact key", <span className="font-mono break-all">{f.fact_key}</span>]);
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-[12px]" aria-live="polite">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[10.5px] font-semibold uppercase tracking-wide text-muted">Selected row</span>
        <span className="font-mono text-[10.5px] text-muted">{f.id.slice(0, 12)}</span>
        <NumericPill check={f.numeric_check} compact />
        <FlagPills finding={f} />
      </div>
      <p className="mt-0.5 font-semibold leading-snug line-clamp-2 [overflow-wrap:anywhere]" title={f.finding}>{f.finding}</p>
      {rows.length > 0 && (
        <dl className="mt-1 grid grid-cols-[110px_1fr] gap-x-2 gap-y-0.5">
          {rows.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-[10.5px] font-semibold uppercase tracking-wide text-muted pt-px">{k}</dt>
              <dd className="min-w-0 leading-snug">{v}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-1 text-[10.5px] text-muted">Charts below follow this row.</p>
    </div>
  );
}
