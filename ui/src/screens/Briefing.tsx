import { useEffect, useState } from "react";
import { findNeedle, needleNone, topFinding, useData } from "../lib/data";
import type { Evidence } from "../lib/types";
import { EmptyState, Panel, RankChange, RobustnessTable, ScreenFrame } from "../components";
import { FindingDetail } from "../components/briefing/FindingDetail";
import { KpiRow } from "../components/briefing/KpiRow";
import { NeedleHero } from "../components/briefing/NeedleHero";
import { FindingsGrid } from "../components/briefing/FindingsGrid";
import { PeerChart } from "../components/briefing/PeerChart";
import { ScoreAnatomy } from "../components/briefing/ScoreAnatomy";
import { StancePanel } from "../components/briefing/StancePanel";

// Briefing (/): KPI row, Sharpest Needle hero, findings grid driving two charts, AI stance panel.
export default function Briefing() {
  const { meta, company, ticker, rank, league, leagueRow, setTicker, loading, error } = useData();
  const leagueRowStatus = (t?: string) => String(league?.find((r) => r.ticker === t)?.needle_status ?? "");
  const none = needleNone(company) || leagueRowStatus(company?.ticker) === "none";
  const needle = none ? undefined : findNeedle(company);
  const top = none ? topFinding(company) : undefined;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [preview, setPreview] = useState<Evidence | null>(null);

  // New company: reset the selection to its needle.
  useEffect(() => { setSelectedId(null); setPreview(null); }, [ticker]);

  const selected = company?.findings.find((f) => f.id === selectedId) ?? needle ?? top;
  const t = company?.ticker ?? ticker ?? "";

  return (
    <ScreenFrame
      title="Briefing"
      subtitle={company ? <>{company.name ?? t} <span className="font-mono">({t})</span>{rank ? <> · league rank <span className="font-mono tnum">#{rank} of {league?.length ?? "?"}</span> <RankChange row={leagueRow} /> (league.json)</> : null}</> : ticker ?? undefined}
      loading={loading}
      error={error}
    >
      {company && (
        <div className="space-y-4">
          <KpiRow meta={meta} company={company} />
          {needle || top ? (
            <NeedleHero needle={(needle ?? top)!} none={!needle} ticker={t} onPreview={setPreview} status={leagueRow?.needle_status ?? (company.needle_status as string | undefined)} v2={company.engine !== "v1" && !!(needle ?? top)!.vector?.v2} />
          ) : (
            <EmptyState file={`companies/${t}.json`} message="No Sharpest Needle: the company file has no findings" />
          )}
          <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-4 items-start">
            <div className="space-y-4 min-w-0">
              {company.findings.length ? (
                <FindingsGrid company={company} selectedId={selected?.id ?? null} onSelect={(f) => setSelectedId(f.id)} />
              ) : (
                <EmptyState file={`companies/${t}.json`} message="No findings exported for this company" />
              )}
              {selected && <FindingDetail company={company} finding={selected} onSelect={(id) => setSelectedId(id)} />}
              <div className="grid grid-cols-2 gap-4">
                <PeerChart finding={selected} ticker={t} />
                <ScoreAnatomy finding={selected} ticker={t} />
              </div>
              {meta?.league_robustness ? (
                <Panel title="Does the ranking hold?" meta={<span className="font-mono">rank under each scoring variant</span>} bodyClassName="px-3 py-2.5">
                  <RobustnessTable meta={meta} league={league} selected={t} onPick={setTicker} compact />
                </Panel>
              ) : null}
            </div>
            <StancePanel company={company} preview={preview} onPreview={setPreview} />
          </div>
        </div>
      )}
    </ScreenFrame>
  );
}
