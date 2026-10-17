import { Fragment } from "react";
import { CiteChip } from "../CiteChip";
import { NumericPill } from "../NumericCheck";
import { resolveCite } from "../../lib/data";
import { money } from "../../lib/format";
import type { Company, Decide, DecideFootnote, DecideMove, Evidence, KillSignal, NumericCheck } from "../../lib/types";

// CEO move valuation from stance.decide (agent.needle.quant.decide): the three moves with their
// five numbers, chosen move first, footnote cites, and the kill-signal table.

const usdM = (x: number | null | undefined) => (typeof x === "number" && Number.isFinite(x) ? money(x * 1e6) : "n/a");

/** Moves with the chosen one first, then by rank. */
export function orderedMoves(d: Decide | null | undefined): DecideMove[] {
  const ms = [...(d?.moves ?? [])];
  return ms.sort((a, b) => (a.status === "chosen" ? -1 : b.status === "chosen" ? 1 : (a.rank ?? 99) - (b.rank ?? 99)));
}

export function footnotesFor(d: Decide | null | undefined, move: string): DecideFootnote[] {
  return (d?.footnotes ?? []).filter((f) => f.move === move);
}

function Foot({ fs, onPreview }: { fs: DecideFootnote[]; onPreview?: (e: Evidence | null) => void }) {
  if (!fs.length) return null;
  return (
    <span className="memo-cite inline-flex flex-wrap gap-0.5 align-baseline">
      {fs.map((f) => <CiteChip key={f.n} label={`f${f.n}`} evidence={f.citation ?? null} onPreview={onPreview} />)}
    </span>
  );
}

function FindingChips({ company, ids, onPreview }: { company: Company; ids?: string[]; onPreview?: (e: Evidence | null) => void }) {
  const chips = (ids ?? []).map((id) => ({ id, ev: resolveCite(company, { finding_id: id, i: 0 }).evidence })).filter((x) => x.ev);
  if (!chips.length) return null;
  return (
    <span className="memo-cite inline-flex flex-wrap gap-0.5 align-baseline">
      {chips.map((c) => <CiteChip key={c.id} evidence={c.ev} label="finding" onPreview={onPreview} />)}
    </span>
  );
}

export function DecideTable({ company, decide, compact = false, onPreview }: {
  company: Company; decide: Decide; compact?: boolean; onPreview?: (e: Evidence | null) => void;
}) {
  const moves = orderedMoves(decide);
  const th = "px-1.5 py-1 text-right font-semibold";
  if (compact) return <DecideCards company={company} decide={decide} moves={moves} onPreview={onPreview} />;
  return (
    <div className="min-w-0">
      <table className={`w-full border-collapse tnum ${compact ? "text-[11.5px]" : "text-[12.5px]"}`}>
        <caption className="sr-only">CEO moves with expected value, cash at risk, payback month, scenario spread and MCDA score; chosen move first</caption>
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-wide text-muted">
            <th scope="col" className="px-1.5 py-1 text-left font-semibold">Move</th>
            <th scope="col" className={th} title="Expected value across bear / base / bull scenarios">EV</th>
            <th scope="col" className={th} title="Cash committed that could be lost">Cash at risk</th>
            <th scope="col" className={th} title="Month the move pays back its outlay">Payback</th>
            <th scope="col" className={th} title="Bull EV minus bear EV">Spread</th>
            <th scope="col" className={th} title="Multi-criteria score (0 to 1); used only when EV intervals overlap">MCDA</th>
          </tr>
        </thead>
        <tbody>
          {moves.map((m) => {
            const chosen = m.status === "chosen";
            const sc = m.ev_by_scenario;
            return (
              <Fragment key={m.name}>
                <tr className={`align-top ${chosen ? "bg-teal-soft/40" : ""}`}>
                  <th scope="row" className="px-1.5 pt-1.5 text-left font-semibold leading-snug">
                    {chosen && <span className="mr-1 inline-block rounded border border-teal bg-teal-soft px-1 text-[9.5px] font-bold uppercase tracking-wide text-teal align-middle">Chosen</span>}
                    <span className={chosen ? "" : "text-fg/90"}>{m.name}</span>{" "}
                    {m.numeric_check ? <><NumericPill check={m.numeric_check as NumericCheck} />{" "}</> : null}
                    <Foot fs={footnotesFor(decide, m.name)} onPreview={onPreview} />
                  </th>
                  <td className="px-1.5 pt-1.5 text-right font-mono" title={sc ? `bear ${usdM(sc.bear)} · base ${usdM(sc.base)} · bull ${usdM(sc.bull)}` : undefined}>{usdM(m.ev)}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{usdM(m.cash_at_risk)}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{m.payback_month != null ? `mo ${m.payback_month}` : "n/a"}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{usdM(m.spread)}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{m.mcda != null ? m.mcda.toFixed(2) : "n/a"}</td>
                </tr>
                <tr className={`border-b border-line ${chosen ? "bg-teal-soft/40" : ""}`}>
                  <td colSpan={6} className="px-1.5 pb-1.5 text-[11px] leading-snug text-muted">
                    {chosen ? m.why : <>Not chosen: {m.binding_reason || "lower rank"}.</>}{" "}
                    <FindingChips company={company} ids={m.finding_ids} onPreview={onPreview} />
                    {!compact && (m.flags?.length ?? 0) > 0 && <span className="block text-warn">⚠ {m.flags!.length} assumption{m.flags!.length > 1 ? "s" : ""} flagged (team inputs or uncited defaults)</span>}
                  </td>
                </tr>
              </Fragment>
            );
          })}
        </tbody>
      </table>
      <p className="mt-1 text-[10.5px] text-muted leading-snug">
        USD, from stance.decide ({(decide.source_files ?? []).join(", ") || "decide.json"}); cash on hand {usdM(decide.cash_and_equivalents)}. Footnote chips f1, f2 ... open each input's source (listed under Move inputs); dashed chips are external benchmarks whose quotes are withheld.
      </p>
    </div>
  );
}

/** Narrow-panel layout: one card per move, the five numbers in a row under the name. */
function DecideCards({ company, decide, moves, onPreview }: {
  company: Company; decide: Decide; moves: DecideMove[]; onPreview?: (e: Evidence | null) => void;
}) {
  return (
    <div className="space-y-1.5">
      <ol className="space-y-1.5">
        {moves.map((m) => {
          const chosen = m.status === "chosen";
          const sc = m.ev_by_scenario;
          const nums: [string, string, string?][] = [
            ["EV", usdM(m.ev), sc ? `bear ${usdM(sc.bear)} · base ${usdM(sc.base)} · bull ${usdM(sc.bull)}` : undefined],
            ["At risk", usdM(m.cash_at_risk), "cash at risk"],
            ["Payback", m.payback_month != null ? `mo ${m.payback_month}` : "n/a"],
            ["Spread", usdM(m.spread), "bull EV minus bear EV"],
            ["MCDA", m.mcda != null ? m.mcda.toFixed(2) : "n/a", "multi-criteria score, used only when EV intervals overlap"],
          ];
          return (
            <li key={m.name} className={`rounded-md border px-2.5 py-2 ${chosen ? "border-teal/60 bg-surface shadow-card" : "border-line"}`}>
              <div className="text-[13px] font-semibold leading-snug">
                {chosen && <span className="mr-1 inline-block rounded border border-teal bg-teal-soft px-1 text-[9.5px] font-bold uppercase tracking-wide text-teal align-middle">Chosen</span>}
                {m.name}
                {m.numeric_check ? <> <NumericPill check={m.numeric_check as NumericCheck} /></> : null}
              </div>
              <dl className="mt-1 grid grid-cols-5 gap-1 tnum">
                {nums.map(([k, v, tip]) => (
                  <div key={k} title={tip} className="min-w-0">
                    <dt className="text-[9.5px] uppercase tracking-wide text-muted truncate">{k}</dt>
                    <dd className="font-mono text-[12px] font-semibold">{v}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-1 text-[11px] leading-snug text-muted">
                {chosen ? m.why : <>Not chosen: {m.binding_reason || "lower rank"}.</>}{" "}
                <FindingChips company={company} ids={m.finding_ids} onPreview={onPreview} />{" "}
                <Foot fs={footnotesFor(decide, m.name)} onPreview={onPreview} />
              </p>
            </li>
          );
        })}
      </ol>
      <p className="text-[10.5px] text-muted leading-snug">USD from stance.decide; cash on hand {usdM(decide.cash_and_equivalents)}. Dashed chips: benchmark inputs whose quotes are withheld.</p>
    </div>
  );
}

export function KillSignalTable({ signals, compact = false }: { signals: KillSignal[]; compact?: boolean }) {
  return (
    <table className={`w-full border-collapse ${compact ? "text-[11.5px]" : "text-[12.5px]"}`}>
      <caption className="sr-only">Kill signals: what would prove the chosen move wrong, the threshold, when to check and what to do</caption>
      <thead>
        <tr className="border-b border-line text-[10px] uppercase tracking-wide text-muted text-left">
          <th scope="col" className="px-1.5 py-1 font-semibold">Signal</th>
          <th scope="col" className="px-1.5 py-1 font-semibold">Threshold</th>
          <th scope="col" className="px-1.5 py-1 font-semibold">Check by</th>
          <th scope="col" className="px-1.5 py-1 font-semibold">Source (lag)</th>
          <th scope="col" className="px-1.5 py-1 font-semibold">Action</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((k) => (
          <tr key={k.id} className="border-b border-line align-top">
            <th scope="row" className="px-1.5 py-1 text-left font-semibold">{k.signal ?? k.id}</th>
            <td className="px-1.5 py-1">{k.threshold ?? "n/a"}</td>
            <td className="px-1.5 py-1 font-mono tnum whitespace-nowrap">{k.check_month != null ? `month ${k.check_month}` : "n/a"}</td>
            <td className="px-1.5 py-1 text-muted">{k.source ?? "n/a"}{k.lag ? ` (${k.lag})` : ""}</td>
            <td className={`px-1.5 py-1 font-semibold ${k.stop ? "text-bad" : "text-warn"}`}>{k.stop ? "stop" : k.action ?? "review"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Footnote list for the memo: each valuation input, its claim and its source. */
export function DecideFootnotes({ decide }: { decide: Decide }) {
  const fs = decide.footnotes ?? [];
  if (!fs.length) return <p className="text-muted text-sm">No footnotes in stance.decide.</p>;
  return (
    <ol className="space-y-0.5 text-[11px] leading-snug">
      {fs.map((f) => {
        const c = f.citation;
        return (
          <li key={f.n} className="grid grid-cols-[28px_1fr] gap-1">
            <span className="font-mono tnum">f{f.n}</span>
            <span className="min-w-0 break-words">
              {f.claim}{f.numeric_check ? <> <NumericPill check={f.numeric_check as NumericCheck} /></> : null}: <span className="font-mono">{c?.citation ?? c?.doc_title ?? c?.doc_id ?? "no source"}</span>
              {c?.withheld === true && <span className="text-warn"> · quote withheld ({c.license ? "licensed source" : "unverified citation"})</span>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
