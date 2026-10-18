import { findNeedle, topFinding, useData } from "../lib/data";
import { NeedleStatusPill, Panel, RankChange, RobustnessTable, ScreenFrame } from "../components";
import { ScoreAnatomy } from "../components/briefing/ScoreAnatomy";

// Internal triage (/cockpit/triage, not in the side nav): the league score, its robustness across
// scoring variants, rank vs v2 and the score anatomy. Used to pick a company; not part of the pitch.
export default function Triage() {
  const { meta, league, company, ticker, setTicker, loading, error } = useData();
  const needle = findNeedle(company) ?? topFinding(company);
  return (
    <ScreenFrame title="Internal triage" subtitle="League score, robustness and score anatomy used to pick the company" loading={loading} error={error}>
      <p role="note" className="rounded-md border border-line bg-surface-2 px-4 py-2 text-sm text-muted">Internal triage view, not part of the pitch.</p>
      <Panel title="League" meta={<span className="font-mono">league.json</span>} bodyClassName="p-0">
        <table className="w-full border-collapse text-[13px] tnum">
          <thead className="bg-surface-2 text-[11px] uppercase tracking-wide text-muted">
            <tr>{["#", "Company", "Score L", "Needle", "League needle", "Rank vs v2", "Findings"].map((h) => <th key={h} scope="col" className="px-3 py-2 text-left font-semibold">{h}</th>)}</tr>
          </thead>
          <tbody>
            {(league ?? []).map((r, i) => (
              <tr key={r.ticker} className={`border-t border-line ${r.ticker === ticker ? "bg-chip font-semibold" : ""}`}>
                <td className="px-3 py-1.5 font-mono">{r.rank ?? i + 1}</td>
                <td className="px-3 py-1.5"><button type="button" onClick={() => setTicker(r.ticker)} className="hover:text-purple"><span className="font-mono">{r.ticker}</span> {r.name}</button></td>
                <td className="px-3 py-1.5 font-mono">{typeof r.score === "number" ? r.score.toFixed(4) : "n/a"}</td>
                <td className="px-3 py-1.5"><NeedleStatusPill status={r.needle_status} /></td>
                <td className="px-3 py-1.5 text-[12px] max-w-[320px]"><span className="line-clamp-2" title={r.sharpest_needle}>{r.sharpest_needle ?? "none"}</span></td>
                <td className="px-3 py-1.5"><RankChange row={r} /></td>
                <td className="px-3 py-1.5 font-mono">{r.n_verified ?? "n/a"} verified / {r.n_rejected ?? "n/a"} rejected</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
      {meta?.league_robustness ? (
        <Panel title="Does the ranking hold?" meta={<span className="font-mono">meta.json · league_robustness</span>}>
          <RobustnessTable meta={meta} league={league} selected={ticker} onPick={setTicker} />
        </Panel>
      ) : null}
      <div className="max-w-[560px]"><ScoreAnatomy finding={needle} ticker={company?.ticker ?? ticker ?? ""} /></div>
    </ScreenFrame>
  );
}
