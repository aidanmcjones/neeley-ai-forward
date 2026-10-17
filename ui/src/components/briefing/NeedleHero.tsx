import { MarkedSentence } from "../MarkedSentence";
import { AiMark, CiteChip, ConfPill, FlagPills, NeedleStatusPill, NumericPill } from "..";
import { money, z } from "../../lib/format";
import { externalSources, impactView, isShiftMetric, metricText } from "../../lib/stance";
import type { Evidence, Finding } from "../../lib/types";

// Full-width hero band: the Sharpest Needle as the engine's verdict.
export function NeedleHero({ needle, ticker, onPreview, status, v2 = false, none = false }: {
  needle: Finding; ticker: string; onPreview?: (ev: Evidence | null) => void;
  /** league needle_status (strict / provisional / floor_relaxed). */
  status?: string | null;
  /** v2 engine export: floor is O ≥ 0.5, E ≥ 0.9. */
  v2?: boolean;
  /** No row qualifies as the needle: `needle` is the highest-scored finding, shown as such. */
  none?: boolean;
}) {
  const im = impactView(needle);
  const peer = needle.peer;
  const ev = needle.evidence ?? [];
  const ext = externalSources(needle);
  const hasPeer = peer?.metric_value != null && peer?.peer_median != null;

  return (
    <section aria-labelledby="needle-h" className={`rounded-lg border shadow-card px-5 pt-3 pb-4 ${none ? "border-line border-t-4 border-t-frog-grey bg-surface" : "border-teal/40 border-t-4 border-t-teal bg-teal-soft/40"}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <AiMark label="Sharpest Needle · engine verdict" />
          <NeedleStatusPill status={status} />
        </div>
        <span className="text-[11px] text-muted font-mono">{v2 ? "highest S = M·O·E·π with O ≥ 0.5, E ≥ 0.9" : "highest S with O ≥ 0.7, E ≥ 0.6"} · companies/{ticker}.json · league.json</span>
      </div>
      {none ? (
        <>
          <h2 id="needle-h" className="mt-1.5 font-display text-[34px] leading-[1.02] tracking-wide text-muted">No row qualifies as the Sharpest Needle</h2>
          <p className="mt-1 text-[15px] leading-snug">
            <span className="mr-1.5 rounded border border-line px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-muted">Highest-scored finding</span>
            <span className="font-semibold"><MarkedSentence finding={needle} onPreview={onPreview} /></span>
          </p>
        </>
      ) : (
        <h2 id="needle-h" className={`mt-1.5 font-display leading-[1.02] tracking-wide text-fg ${needle.finding.length > 150 ? "text-[32px]" : "text-[40px]"}`}>
          <MarkedSentence finding={needle} onPreview={onPreview} />
        </h2>
      )}
      <div className="mt-2.5 grid grid-cols-[auto_1fr_auto] items-start gap-x-6 gap-y-2 text-sm">
        <div className="flex flex-col items-start gap-1.5 pt-0.5">
          <div className="flex items-center gap-2">
            <ConfPill level={needle.confidence} />
            {needle.verdict && <span className="text-[11px] font-semibold uppercase tracking-wide text-muted" title="Verifier verdict: the quote was located on the cited page">{needle.verdict === "verified" ? "quote located" : needle.verdict.replace("_", " ")}</span>}
          </div>
          <NumericPill check={needle.numeric_check} />
          <FlagPills finding={needle} />
        </div>
        <dl className="min-w-0 grid grid-cols-[86px_1fr] gap-x-3 gap-y-1">
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted pt-0.5">Why unseen</dt>
          <dd>{needle.vector?.obscurity_note ?? "no obscurity note exported"}</dd>
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted pt-0.5">Impact</dt>
          <dd className="min-w-0">
            {im.kind === "dollars" && <span className="font-display text-[22px] leading-none text-purple mr-2 tnum">{money(im.dollars)}</span>}
            {im.kind === "suspect" && (
              <span className="mr-2"><s className="font-display text-[22px] leading-none text-muted tnum">{money(im.dollars)}</s> <span className="text-warn font-semibold text-xs">suspect: {im.note}</span></span>
            )}
            {im.kind === "proxy" && <span className="mr-2 rounded bg-chip px-1.5 py-0.5 text-[11px] font-semibold text-purple">proxy, no direct $</span>}
            <span className="font-mono text-xs text-muted">{im.formula || "no formula exported"}</span>
          </dd>
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted pt-0.5">Peers</dt>
          <dd className="tnum">
            {hasPeer ? (
              <>
                <span className="font-semibold">{ticker} {metricText(needle, peer!.metric_value)}</span>
                <span className="text-muted"> vs peer median </span>
                <span className="font-semibold">{metricText(needle, peer!.peer_median)}</span>
                {peer?.z != null && <span className="ml-2 font-mono text-xs rounded bg-chip px-1.5 py-0.5">{z(peer.z)}</span>}
                {isShiftMetric(needle) && <span className="ml-2 text-xs text-muted">(value is the year-over-year change)</span>}
              </>
            ) : <span className="text-muted">No peer median exported for this signal</span>}
          </dd>
        </dl>
        <div className="flex flex-col items-end gap-1.5 max-w-[280px]">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">Proof on the page</span>
          {ev.length > 0 ? (
            <div className="flex flex-wrap justify-end gap-1.5">
              {ev.map((e, i) => <CiteChip key={i} evidence={{ ...e, verdict: e.verdict ?? needle.verdict }} label={`[${i + 1}] ${(e.citation ?? e.doc_id ?? "source").replace(/\s*\(file page \d+\)$/, "")}`} onPreview={onPreview} />)}
            </div>
          ) : (
            <div className="text-right text-xs">
              <div className="rounded border border-dashed border-warn/60 bg-warn/10 px-2 py-1 font-semibold text-warn">No page quote; held for human review</div>
              {ext.map((u, i) => (
                <a key={i} href={u} target="_blank" rel="noreferrer" className="mt-1 block truncate text-purple underline max-w-[280px]" title={u}>external source {i + 1}</a>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
