import { Fragment } from "react";
import { CiteChip } from "../CiteChip";
import { NumericPill } from "../NumericCheck";
import { Md } from "../chat/Md";
import { resolveCite } from "../../lib/data";
import { money } from "../../lib/format";
import type { Company, Decide, DecideFootnote, DecideMove, Evidence, KillSignal, NumericCheck } from "../../lib/types";

// CEO move valuation from stance.decide (agent.needle.quant.decide): the three moves with their
// five numbers, chosen move first, footnote cites, and the kill-signal table.

const usdM = (x: number | null | undefined) => (typeof x === "number" && Number.isFinite(x) ? money(x * 1e6) : "n/a");

/** Moves with why_passed filled from stance.alternatives (the exporter puts it there). */
export function withAlternatives(d: Decide, alts?: { name?: string; why_passed?: string | null }[] | null): Decide {
  if (!alts?.length || !d.moves) return d;
  return { ...d, moves: d.moves.map((m) => (m.why_passed ? m : { ...m, why_passed: alts.find((a) => a.name === m.name)?.why_passed ?? null })) };
}

/** True when DECIDE found no move that clears the hurdle (chosen: null with a least-bad move). */
export function noneClears(d: Decide | null | undefined): boolean {
  return !!d && "chosen" in d && d.chosen == null && !!d.least_bad;
}

const refName = (r: unknown) => (typeof r === "string" ? r : (r as { name?: string; code?: string } | null)?.name ?? (r as { code?: string } | null)?.code ?? "");

/** "chosen", "least_bad" or the move's own status. */
export function moveRole(d: Decide | null | undefined, m: DecideMove): "chosen" | "least_bad" | "other" {
  if (noneClears(d)) {
    const lb = refName(d!.least_bad);
    return m.status === "least_bad" || m.name === lb || (!!m.code && m.code === lb) ? "least_bad" : "other";
  }
  return m.status === "chosen" ? "chosen" : "other";
}

/** Moves with the chosen (or least-bad) one first, then by rank. */
export function orderedMoves(d: Decide | null | undefined): DecideMove[] {
  const ms = [...(d?.moves ?? [])];
  const top = (m: DecideMove) => (moveRole(d, m) !== "other" ? 0 : 1);
  return ms.sort((a, b) => top(a) - top(b) || (a.rank ?? 99) - (b.rank ?? 99));
}

export function RoleBadge({ role }: { role: "chosen" | "least_bad" | "other" }) {
  if (role === "chosen") return <span className="mr-1 inline-block rounded border border-teal bg-teal-soft px-1 text-[9.5px] font-bold uppercase tracking-wide text-teal align-middle">Chosen</span>;
  if (role === "least_bad") return <span className="mr-1 inline-block rounded border border-warn/60 bg-warn/10 px-1 text-[9.5px] font-bold uppercase tracking-wide text-warn align-middle" title="No candidate clears the hurdle; this is the least-bad option">Least-bad option</span>;
  return null;
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
            const role = moveRole(decide, m);
            const chosen = role !== "other";
            const sc = m.ev_by_scenario;
            return (
              <Fragment key={m.name}>
                <tr className={`align-top ${role === "chosen" ? "bg-teal-soft/40" : role === "least_bad" ? "bg-warn/10" : ""}`}>
                  <th scope="row" className="px-1.5 pt-1.5 text-left font-semibold leading-snug">
                    <RoleBadge role={role} />
                    <span className={chosen ? "" : "text-fg/90"}>{m.name}</span>{" "}
                    {m.numeric_check ? <><NumericPill check={m.numeric_check as NumericCheck} />{" "}</> : null}
                    <Foot fs={footnotesFor(decide, m.name)} onPreview={onPreview} />
                  </th>
                  <td className="px-1.5 pt-1.5 text-right font-mono" title={sc ? `bear ${usdM(sc.bear)} · base ${usdM(sc.base)} · bull ${usdM(sc.bull)}` : undefined}>{usdM(m.ev)}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono" title={m.cash_at_risk === 0 && m.cash_at_risk_note ? m.cash_at_risk_note : undefined}>{usdM(m.cash_at_risk)}{m.cash_at_risk === 0 && m.cash_at_risk_note && <span className="block max-w-[160px] whitespace-normal text-left font-body text-[10px] leading-snug text-muted">{m.cash_at_risk_note}</span>}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{m.payback_month != null ? `mo ${m.payback_month}` : "n/a"}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{usdM(m.spread)}</td>
                  <td className="px-1.5 pt-1.5 text-right font-mono">{m.mcda != null ? m.mcda.toFixed(2) : "n/a"}</td>
                </tr>
                <tr className={`border-b border-line ${role === "chosen" ? "bg-teal-soft/40" : role === "least_bad" ? "bg-warn/10" : ""}`}>
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
          const role = moveRole(decide, m);
          const chosen = role !== "other";
          const sc = m.ev_by_scenario;
          const nums: [string, string, string?][] = [
            ["EV", usdM(m.ev), sc ? `bear ${usdM(sc.bear)} · base ${usdM(sc.base)} · bull ${usdM(sc.bull)}` : undefined],
            ["At risk", usdM(m.cash_at_risk), m.cash_at_risk === 0 && m.cash_at_risk_note ? `cash at risk: ${m.cash_at_risk_note}` : "cash at risk"],
            ["Payback", m.payback_month != null ? `mo ${m.payback_month}` : "n/a"],
            ["Spread", usdM(m.spread), "bull EV minus bear EV"],
            ["MCDA", m.mcda != null ? m.mcda.toFixed(2) : "n/a", "multi-criteria score, used only when EV intervals overlap"],
          ];
          return (
            <li key={m.name} className={`rounded-md border px-2.5 py-2 ${role === "chosen" ? "border-teal/60 bg-surface shadow-card" : role === "least_bad" ? "border-warn/60 bg-surface shadow-card" : "border-line"}`}>
              <div className="text-[13px] font-semibold leading-snug">
                <RoleBadge role={role} />
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
                {chosen ? m.why : m.why_passed ? <>Why we passed: {m.why_passed}</> : <>Not chosen: {m.binding_reason || "lower rank"}.</>}{" "}
                {m.cash_at_risk === 0 && m.cash_at_risk_note ? <span className="block">Zero cash at risk: {m.cash_at_risk_note}</span> : null}
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

function KillBaseline({ k }: { k: KillSignal }) {
  const b = k.baseline as { value?: unknown; text?: string; cites?: Evidence[] } | string | null | undefined;
  const ctx = Array.isArray(k.context) ? (k.context as unknown[]) : [];
  const text = typeof b === "string" ? b : b?.text;
  const cites = typeof b === "object" && b && Array.isArray(b.cites) ? b.cites : [];
  if (!text && !cites.length && !ctx.length) return <span className="text-muted">n/a</span>;
  return (
    <span className="block">
      {text && <span>{text} </span>}
      {cites.map((ev, i) => <CiteChip key={i} evidence={ev} n={i + 1} />)}
      {ctx.map((row, i) => {
        const [v, ev] = Array.isArray(row) ? row : [null, row];
        const e = ev && typeof ev === "object" ? (ev as Evidence) : null;
        return (
          <span key={`x${i}`} className="mr-1.5 inline-flex items-baseline gap-0.5">
            {typeof v === "number" ? <span className="font-mono tnum">{v.toLocaleString("en-US")}</span> : v != null ? <span>{String(v)}</span> : null}
            {e && <CiteChip evidence={e} n={cites.length + i + 1} />}
          </span>
        );
      })}
    </span>
  );
}

export function KillSignalTable({ signals, compact = false }: { signals: KillSignal[]; compact?: boolean }) {
  const anyBase = signals.some((k) => k.baseline || (Array.isArray(k.context) && (k.context as unknown[]).length));
  return (
    <table className={`w-full border-collapse ${compact ? "text-[11.5px]" : "text-[12.5px]"}`}>
      <caption className="sr-only">Kill signals: what would prove the chosen move wrong, the baseline it must move from, the threshold, when to check and what to do</caption>
      <thead>
        <tr className="border-b border-line text-[10px] uppercase tracking-wide text-muted text-left">
          <th scope="col" className="px-1.5 py-1 font-semibold">Signal</th>
          {anyBase && <th scope="col" className="px-1.5 py-1 font-semibold">Baseline</th>}
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
            {anyBase && <td className="px-1.5 py-1"><KillBaseline k={k} /></td>}
            <td className="px-1.5 py-1">{k.threshold ?? "n/a"}</td>
            <td className="px-1.5 py-1 font-mono tnum whitespace-nowrap">{k.check_month == null ? "n/a" : Number(k.check_month) === 0 ? "now" : `month ${k.check_month}`}</td>
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


/** stance.decide.why_it_works_rows: the evidence each decider needs. Cells carry [n] / [derived: ...] /
 * [assumption] markers; [n] resolves to the row's own cites (footnotes, shown as f-chips). */
export function WhyItWorks({ company, decide, compact = false }: { company: Company; decide: Decide; compact?: boolean; onPreview?: (e: Evidence | null) => void }) {
  void company;
  const rows = (decide.why_it_works_rows ?? []).filter((r) => r && typeof r === "object") as Record<string, unknown>[];
  if (!rows.length) return null;
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))].filter((k) => !/^(cites?|footnotes?|citations?|evidence|markers?_unresolved|id|cite_id|finding_ids?)$/.test(k));
  const fn = new Map((decide.footnotes ?? []).map((f) => [f.n, f]));
  const evOf = (r: Record<string, unknown>) => (n: number): Evidence | undefined => {
    const c = (Array.isArray(r.cites) ? (r.cites as Record<string, unknown>[]) : []).find((x) => x?.n === n);
    if (c) {
      const page = c.page != null ? `p. ${String(c.page)}` : String(c.location ?? "");
      return { doc_id: String(c.doc_title ?? `footnote ${n}`), citation: [c.doc_title, page].filter(Boolean).join(", ") || `footnote ${n}`, doc_title: c.doc_title as string,
        location: c.location as string, quote: (c.quote as string) ?? "", url: (c.url as string) ?? undefined, withheld: c.withheld === true, withheld_reason: (c.withheld_reason as string) ?? null,
        verification: (typeof c.verification === "string" ? { status: c.verification } : c.verification) as Evidence["verification"], verdict: "verified" };
    }
    return fn.get(n)?.citation;
  };
  const head = (k: string) => k.replace(/_/g, " ");
  return (
    <div className="overflow-x-auto">
      <table className={`w-full border-collapse ${compact ? "text-[11.5px]" : "text-[12.5px]"}`}>
        <caption className="sr-only">Why it will work: the evidence each decider needs</caption>
        <thead><tr className="border-b border-line text-[10px] uppercase tracking-wide text-muted text-left">
          {cols.map((k) => <th key={k} scope="col" className="px-1.5 py-1 font-semibold">{head(k)}</th>)}
        </tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-line align-top">
            {cols.map((k, j) => {
              const v = r[k];
              const t = v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v);
              const cell = <Md md={t} cite={evOf(r)} prefix="f" />;
              return j === 0 ? <th key={k} scope="row" className="px-1.5 py-1 text-left font-semibold">{cell}</th> : <td key={k} className="px-1.5 py-1">{cell}</td>;
            })}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
