import { isWithheld, withheldReason } from "../../lib/data";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AiMark, CiteChip, ConfPill, EmptyState, NumericSummary, Panel, ScoreBar, StanceBadge } from "..";
import { BASIS_NOTE, CiteRegistry, citeLabel, weighOptions } from "../../lib/stance";
import type { Company, Evidence, NumericCheck } from "../../lib/types";
import { DecideTable } from "../decide/Decide";

// Right-hand AI panel: the template-drafted stance, options, cited bullets, live source card.
export function StancePanel({ company, preview, onPreview }: {
  company: Company; preview: Evidence | null; onPreview: (ev: Evidence | null) => void;
}) {
  const nav = useNavigate();
  const s = company.stance;
  const [hoverOpt, setHoverOpt] = useState<string | null>(null);
  const { basis, rows } = useMemo(() => weighOptions(s), [s]);
  const bullets = useMemo(() => {
    const reg = new CiteRegistry(company);
    return (s?.bullets ?? []).slice(0, 4).map((b) => ({ text: b.text, cites: reg.resolveAll(b.cites) }));
  }, [company, s]);

  if (!s) {
    return (
      <Panel ai title="Draft stance">
        <EmptyState file={`companies/${company.ticker}.json`} message="No stance exported for this company">The stance block is missing from the company file.</EmptyState>
      </Panel>
    );
  }
  const byModel = s.generated_by === "model";
  const byline = byModel ? "Model-written from verified findings"
    : s.decide?.moves?.length ? "Move valued and chosen by rules (quant.decide, no model)" : "Drafted from verified findings by rules (template, no model)";
  const hover = rows.find((r) => r.name === hoverOpt);
  const decide = s.decide?.moves?.length ? s.decide : null;

  return (
    <Panel ai className="border-t-4 border-t-teal" bodyClassName="p-4 space-y-4"
      title={<span title={s.note}><AiMark label="Draft stance" /></span>}
      meta={<span className="font-mono text-[10px]">companies/{company.ticker}.json stance</span>}>
      <div>
        <p className="mb-1.5 text-[11px] font-semibold text-teal" title={s.note}>{byline}</p>
        <p className="text-[15px] font-semibold leading-snug">{s.headline ?? "No headline exported"}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">{decide ? "CEO move" : "Recommended"}</span>
          {decide ? <span className="text-sm font-semibold text-teal">{s.recommended}</span> : <StanceBadge stance={s.recommended} />}
          {s.confidence && <ConfPill level={s.confidence} />}
        </div>
      </div>

      {decide ? (
        <div>
          <h3 className="mb-1.5 flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted">Moves valued (stance.decide){decide.numeric_check ? <NumericSummary check={decide.numeric_check as NumericCheck} /> : null}</h3>
          <DecideTable company={company} decide={decide} compact onPreview={onPreview} />
        </div>
      ) : (
      <div>
        <div className="mb-1.5 flex items-baseline justify-between gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Options weighed</h3>
          <span className="text-[10px] text-muted text-right">{BASIS_NOTE[basis]}</span>
        </div>
        <ul className="space-y-1" onMouseLeave={() => setHoverOpt(null)}>
          {rows.map((r) => (
            <li key={r.name}
              tabIndex={0}
              onMouseEnter={() => setHoverOpt(r.name)}
              onFocus={() => setHoverOpt(r.name)}
              onBlur={() => setHoverOpt(null)}
              title={r.option.rationale}
              className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 rounded px-2 py-1 ${r.recommended ? "bg-surface shadow-card" : ""} ${hoverOpt === r.name ? "ring-1 ring-teal/50" : ""}`}>
              <span className="min-w-0">
                <span className="flex items-center gap-1 text-sm font-semibold truncate">
                  {r.recommended && <span aria-hidden="true" className="text-teal">▸</span>}{r.name}
                  {r.recommended && <span className="sr-only"> (recommended)</span>}
                </span>
                <span className="block text-[11px] text-muted truncate">
                  {r.nFindings != null ? `${r.nFindings} findings` : ""}
                  {r.dollars == null ? <span className="italic">{r.nFindings != null ? " · " : ""}no direct $ in findings</span> : null}
                </span>
              </span>
              <ScoreBar value={r.frac} max={1} tone="purple" width={84} label={r.valueLabel} />
            </li>
          ))}
        </ul>
        <p className="mt-1.5 min-h-[2.6em] text-[11px] leading-snug text-muted line-clamp-3">
          {hover?.option.rationale ?? "Hover an option for the rule that ranked it."}
        </p>
      </div>
      )}

      <div>
        <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">Why</h3>
        {bullets.length ? (
          <ul className="space-y-1.5">
            {bullets.map((b, i) => (
              <li key={i} className="flex gap-2 text-sm leading-snug">
                <span aria-hidden="true" className="text-teal">✦</span>
                <span className="min-w-0">
                  {b.text}{" "}
                  {b.cites.map((c) => <CiteChip key={c.key} n={c.n} evidence={c.evidence} onPreview={onPreview} />).reduce<ReactNode[]>((a, el, j) => (j ? [...a, " ", el] : [el]), [])}
                </span>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted">No bullets in stance.bullets.</p>}
      </div>

      <div aria-live="polite" className="rounded-md border border-line bg-surface px-3 py-2 min-h-[92px]">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-muted">Live source card</div>
        {preview ? (
          <>
            <div className="mt-0.5 font-mono text-xs text-purple truncate" title={citeLabel(preview)}>{citeLabel(preview)}</div>
            {isWithheld(preview)
              ? <p className="mt-1 text-xs font-semibold text-warn">Quote withheld: {withheldReason(preview)}.</p>
              : (preview.excerpt?.match || preview.quote)
                ? <blockquote className="mt-1 text-xs leading-snug line-clamp-3"><mark>{preview.excerpt?.match || preview.quote}</mark></blockquote>
                : <p className="mt-1 text-xs text-muted">No quote exported for this citation.</p>}
          </>
        ) : <p className="mt-1 text-xs text-muted">Hover or focus a citation chip to see its page quote. Click it to open the page.</p>}
      </div>

      <div className="flex gap-2">
        <button type="button" onClick={() => nav("/memo")}
          className="flex-1 rounded-md bg-purple dark:bg-purple-deep px-3 py-2 text-sm font-semibold text-white hover:bg-purple-bright">
          Generate CEO memo
        </button>
        <button type="button" onClick={() => nav("/ask")}
          className="flex-1 rounded-md border border-purple/40 bg-surface px-3 py-2 text-sm font-semibold text-purple hover:bg-chip">
          Ask a follow-up
        </button>
      </div>
      {s.note && <p className="text-[10px] leading-snug text-teal"><span aria-hidden="true">✦ </span>{s.note}</p>}
    </Panel>
  );
}
