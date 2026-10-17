import { useEffect, useState } from "react";
import { findNeedle, useData } from "../lib/data";
import type { Evidence } from "../lib/types";
import { EmptyState, ScreenFrame } from "../components";
import { KpiRow } from "../components/briefing/KpiRow";
import { NeedleHero } from "../components/briefing/NeedleHero";
import { FindingsGrid } from "../components/briefing/FindingsGrid";
import { PeerChart } from "../components/briefing/PeerChart";
import { ScoreAnatomy } from "../components/briefing/ScoreAnatomy";
import { StancePanel } from "../components/briefing/StancePanel";

// Briefing (/): KPI row, Sharpest Needle hero, findings grid driving two charts, AI stance panel.
export default function Briefing() {
  const { meta, company, ticker, rank, league, loading, error } = useData();
  const needle = findNeedle(company);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [preview, setPreview] = useState<Evidence | null>(null);

  // New company: reset the selection to its needle.
  useEffect(() => { setSelectedId(null); setPreview(null); }, [ticker]);

  const selected = company?.findings.find((f) => f.id === selectedId) ?? needle;
  const t = company?.ticker ?? ticker ?? "";

  return (
    <ScreenFrame
      title="Briefing"
      subtitle={company ? <>{company.name ?? t} <span className="font-mono">({t})</span>{rank ? <> · league rank <span className="font-mono tnum">#{rank} of {league?.length ?? "?"}</span> (league.json)</> : null}</> : ticker ?? undefined}
      loading={loading}
      error={error}
    >
      {company && (
        <div className="space-y-4">
          <KpiRow meta={meta} company={company} />
          {needle ? (
            <NeedleHero needle={needle} ticker={t} onPreview={setPreview} />
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
              {selected && (
                <div className="text-[11px] text-muted -mb-2">
                  Charts follow the selected row: <span className="text-fg font-semibold">{selected.finding.slice(0, 110)}{selected.finding.length > 110 ? "…" : ""}</span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <PeerChart finding={selected} ticker={t} />
                <ScoreAnatomy finding={selected} ticker={t} />
              </div>
            </div>
            <StancePanel company={company} preview={preview} onPreview={setPreview} />
          </div>
        </div>
      )}
    </ScreenFrame>
  );
}
