import { Fragment } from "react";
import type { Company, Evidence, Loose } from "../../lib/types";
import { CiteChip } from "../CiteChip";
import { EmptyState } from "../EmptyState";
import { Panel } from "../Panel";
import { Flag, isNum, str } from "../product/util";

// Consensus vs guidance and the IRA cut check (CMS % cut recomputed from MFP and list).

const bn = (m: unknown) => (isNum(m) ? `$${(m / 1000).toFixed(2)}B` : "n/a");

export function GuidancePanel({ company }: { company: Company }) {
  const g = company.consensus_vs_guidance as Loose | null | undefined;
  if (!g || (!isNum(g.consensus_mean_m) && !isNum(g.guidance_low_m))) {
    return <Panel title="Consensus vs guidance"><EmptyState file={`companies/${company.ticker}.json · consensus_vs_guidance`} message="No consensus vs guidance row">Source table: consensus_vs_guidance.csv</EmptyState></Panel>;
  }
  const mid = isNum(g.guidance_low_m) && isNum(g.guidance_high_m) ? (g.guidance_low_m + g.guidance_high_m) / 2 : null;
  const range = String(g.consensus_vs_range ?? "");
  const tone = range === "within" ? "good" : range ? "warn" : "neutral";
  const ev: Evidence | null = str(g.guidance_quote) ? {
    doc_id: String(g.guidance_file ?? ""), citation: `${company.ticker} guidance, ${String(g.guidance_page ?? "")}`,
    quote: String(g.guidance_quote), excerpt: { before: "", match: String(g.guidance_quote), after: "" }, doc_type: "earnings release",
  } : null;
  const lo = Math.min(...[g.consensus_low_m, g.guidance_low_m].filter(isNum) as number[]);
  const hi = Math.max(...[g.consensus_high_m, g.guidance_high_m].filter(isNum) as number[]);
  const pad = (hi - lo) * 0.15 || 1;
  const X = (v: number) => ((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100;

  return (
    <Panel title="Consensus vs guidance" meta={<span className="font-mono">FY ending {String(g.fiscal_period_end ?? "?")} · revenue</span>}>
      <div className="grid grid-cols-3 gap-3 tnum">
        <Stat label={`I/B/E/S mean (${String(g.n_estimates ?? "?")} est., ${String(g.consensus_date ?? "")})`} value={bn(g.consensus_mean_m)} />
        <Stat label="Guidance midpoint" value={bn(mid)} sub={`range ${bn(g.guidance_low_m)} to ${bn(g.guidance_high_m)}`} />
        <Stat label="Gap (mean vs mid)" value={isNum(g.gap_pct) ? `${g.gap_pct > 0 ? "+" : ""}${(g.gap_pct as number).toFixed(2)}%` : "n/a"} sub={isNum(g.gap_mean_minus_guidance_mid_m) ? `${g.gap_mean_minus_guidance_mid_m > 0 ? "+" : ""}$${Math.round(g.gap_mean_minus_guidance_mid_m as number).toLocaleString("en-US")}M` : undefined} />
      </div>
      {isFinite(lo) && isFinite(hi) && (
        <div className="mt-4" aria-label="Consensus range vs guidance range">
          <div className="relative h-12">
            {isNum(g.guidance_low_m) && isNum(g.guidance_high_m) && (
              <div className="absolute top-1 h-3 rounded-sm bg-purple/80" style={{ left: `${X(g.guidance_low_m)}%`, width: `${X(g.guidance_high_m) - X(g.guidance_low_m)}%` }} />
            )}
            {isNum(g.consensus_low_m) && isNum(g.consensus_high_m) && (
              <div className="absolute top-6 h-3 rounded-sm bg-frog-grey" style={{ left: `${X(g.consensus_low_m)}%`, width: `${X(g.consensus_high_m) - X(g.consensus_low_m)}%` }} />
            )}
            {isNum(g.consensus_mean_m) && <div className="absolute top-0 h-11 w-0.5 bg-fg" style={{ left: `${X(g.consensus_mean_m)}%` }} title="consensus mean" />}
          </div>
          <div className="flex flex-wrap gap-x-4 text-[11px] text-muted">
            <span className="inline-flex items-center gap-1"><span className="h-2.5 w-4 rounded-sm bg-purple/80" />company guidance range (top)</span>
            <span className="inline-flex items-center gap-1"><span className="h-2.5 w-4 rounded-sm bg-frog-grey" />analyst low to high (bottom)</span>
            <span className="inline-flex items-center gap-1"><span className="h-3 w-0.5 bg-fg" />consensus mean</span>
          </div>
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[13px]">
        <Flag tone={tone}>{range ? `consensus ${range} guidance range` : "range position n/a"}</Flag>
        {str(g.note) && <span className="text-[12px] text-muted">{String(g.note)}</span>}
      </div>
      {ev && (
        <blockquote className="mt-3 border-l-2 border-purple pl-3 text-[13px]">
          “{String(g.guidance_quote)}” <CiteChip evidence={ev} label="src" />
          <span className="block font-mono text-[10px] text-muted mt-0.5 break-all">{String(g.guidance_file)} · {String(g.guidance_page ?? "")}</span>
        </blockquote>
      )}
      <div className="mt-2 font-mono text-[10px] text-muted break-all">{String(g.source ?? "")} · {String(g.source_row ?? "")}</div>
    </Panel>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-md border border-line bg-surface-2 px-3 py-2 min-w-0">
      <div className="text-[11px] text-muted leading-tight">{label}</div>
      <div className="text-[20px] font-semibold">{value}</div>
      {sub && <div className="text-[11px] text-muted">{sub}</div>}
    </div>
  );
}

export function IraCutCheck({ company }: { company: Company }) {
  const rows = company.ira_cut_check ?? [];
  const forces = company.forces as Loose | null | undefined;
  return (
    <Panel title="IRA cut check" meta={<span className="font-mono">CMS % cut recomputed from MFP and list</span>}>
      {rows.length === 0 ? (
        <EmptyState message={`No CMS fact-sheet rows to check for ${company.ticker}`}>
          <code className="font-mono text-xs">companies/{company.ticker}.json · ira_cut_check</code> is empty. The check covers the IPAY 2026 and 2027 CMS fact sheets in this export.{" "}
          {str(forces?.ira_drugs) ? (/\(202[67]\)/.test(String(forces!.ira_drugs))
            ? <>forces lists {String(forces!.ira_drugs)}, so rows are expected here: treat this as a gap in the export.</>
            : <>forces lists {String(forces!.ira_drugs)}: no IPAY 2026/2027 drug, so there is no CMS MFP and list pair to recompute.</>) : "No IRA drugs listed in forces either."}
        </EmptyState>
      ) : (
        <>
          <div className="overflow-x-auto rounded-md border border-line">
            <table className="w-full text-[13px] tnum border-collapse">
              <caption className="sr-only">IRA cut check</caption>
              <thead className="bg-surface-2 text-[11px] uppercase tracking-wide text-muted">
                <tr>
                  {["Drug", "MFP $/30d", "List $/30d", "CMS cut", "Recomputed", "Match", "Source"].map((h, i) => (
                    <th key={h} scope="col" className={`px-2 py-1.5 font-semibold whitespace-nowrap border-b border-line ${i > 0 && i < 5 ? "text-right" : "text-left"}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const ev: Evidence = { doc_id: String(r.doc ?? ""), page: isNum(r.page) ? r.page : null, citation: `CMS fact sheet IPAY ${String(r.ipay ?? "")}, p. ${String(r.page ?? "?")}`, quote: String(r.quote ?? ""), excerpt: { before: "", match: String(r.quote ?? ""), after: "" }, doc_type: "government" };
                  const yes = String(r.match).toLowerCase() === "yes";
                  return (
                    <Fragment key={i}>
                    <tr className="align-top">
                      <td className="px-2 py-1.5 font-semibold">{String(r.drug)}<span className="block text-[11px] font-normal text-muted">IPAY {String(r.ipay ?? "?")}</span></td>
                      <td className="px-2 py-1.5 text-right">{isNum(r.mfp_usd_30day) ? `$${r.mfp_usd_30day.toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "n/a"}</td>
                      <td className="px-2 py-1.5 text-right">{isNum(r.list_usd_30day) ? `$${r.list_usd_30day.toLocaleString("en-US")}` : "n/a"}<span className="block text-[11px] text-muted">{String(r.list_price_year ?? "")} list</span></td>
                      <td className="px-2 py-1.5 text-right">{isNum(r.cms_pct_cut) ? `${r.cms_pct_cut}%` : "n/a"}</td>
                      <td className="px-2 py-1.5 text-right">{isNum(r.recomputed_pct_cut) ? `${r.recomputed_pct_cut}%` : "n/a"}{isNum(r.recomputed_exact) && <span className="block text-[11px] text-muted">{(r.recomputed_exact as number).toFixed(2)}%</span>}</td>
                      <td className="px-2 py-1.5">{yes ? <Flag tone="good">match: yes</Flag> : <Flag tone="bad">match: {String(r.match ?? "no")}</Flag>}</td>
                      <td className="px-2 py-1.5"><CiteChip evidence={ev} label={`p.${String(r.page ?? "?")}`} /></td>
                    </tr>
                    <tr className="border-b border-line last:border-0">
                      <td colSpan={7} className="px-2 pb-2 pt-0 font-mono text-[10px] text-muted [overflow-wrap:anywhere]">
                        CMS fact sheet IPAY {String(r.ipay ?? "")} p.{String(r.page ?? "?")}: “{String(r.quote ?? "")}”
                      </td>
                    </tr>
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-muted">Recomputed % = 1 − MFP / list, both per 30 days, from the CMS fact sheet. <span className="font-mono">data/moat/policy_gov/cms/cms_fact_sheet_negotiated_prices_ipay*.md</span></p>
        </>
      )}
    </Panel>
  );
}
