import { useEffect, useState } from "react";
import { findNeedle, needleNone, topFinding, useData } from "../lib/data";
import type { Evidence } from "../lib/types";
import { EmptyState, ScreenFrame } from "../components";
import { FindingDetail } from "../components/briefing/FindingDetail";
import { KpiRow } from "../components/briefing/KpiRow";
import { NeedleHero } from "../components/briefing/NeedleHero";
import { FindingsGrid } from "../components/briefing/FindingsGrid";
import { PeerChart } from "../components/briefing/PeerChart";
import { StancePanel } from "../components/briefing/StancePanel";

// Briefing (/): KPI row, Sharpest Needle hero, findings grid driving two charts, AI stance panel.
export default function Briefing() {
  const { meta, company, ticker, league, leagueRow, loading, error } = useData();
  const leagueRowStatus = (t?: string) => String(league?.find((r) => r.ticker === t)?.needle_status ?? "");
  const hasRule = typeof company?.needle_id_rule === "string" && !!company.needle_id_rule;
  const none = needleNone(company) || (!hasRule && leagueRowStatus(company?.ticker) === "none");
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
      subtitle={company ? <>{company.name ?? t} <span className="font-mono">({t})</span></> : ticker ?? undefined}
      loading={loading}
      error={error}
    >
      {company && (
        <div className="space-y-4">
          <KpiRow meta={meta} company={company} />
          {needle || top ? (
            <NeedleHero needle={(needle ?? top)!} none={!needle} ticker={t} onPreview={setPreview} status={hasRule ? null : leagueRow?.needle_status ?? (company.needle_status as string | undefined)} rule={typeof company.needle_rule === "string" ? company.needle_rule : (company.findings_table as { needle_rule?: string } | undefined)?.needle_rule} source={typeof company.needle_source === "string" ? company.needle_source : null} v2={company.engine !== "v1" && !!(needle ?? top)!.vector?.v2} />
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
              <PeerChart finding={selected} ticker={t} />
            </div>
            <StancePanel company={company} preview={preview} onPreview={setPreview} />
          </div>
        </div>
      )}
    </ScreenFrame>
  );
}
