import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Company, LeagueRow, Loose, Meta } from "../../lib/types";
import { num } from "../../lib/format";
import { KpiTile, Panel } from "..";
import { Pill, SourceNote, useTokens } from "./common";

// (a) Verifier: what it checks, per-company verdict counts, and the AI-caught log.

interface VRow { ticker: string; verified: number; needs_human: number; rejected: number }

function verdictRows(league: LeagueRow[]): VRow[] {
  return league.map((r) => ({
    ticker: r.ticker,
    verified: r.n_verified ?? 0,
    // Findings are verified or needs_human; rejected claims are logged separately (company.rejected).
    needs_human: Math.max(0, (r.n_findings ?? 0) - (r.n_verified ?? 0)),
    rejected: r.n_rejected ?? 0,
  }));
}

export function VerifierPanel({ meta, league, rules }: { meta: Meta | null; league: LeagueRow[] | null; rules: string[] }) {
  const t = useTokens();
  const rows = useMemo(() => verdictRows(league ?? []), [league]);
  const derivedHuman = rows.reduce((s, r) => s + r.needs_human, 0);
  const totals = meta?.totals ?? {};
  const needsHuman = typeof totals.needs_human === "number" ? (totals.needs_human as number) : derivedHuman;
  const ledger = meta?.ledger;

  // Inside-segment labels only when the segment is wide enough to hold the text.
  const insideLabel = (fill: string) => (p: { x?: number | string; y?: number | string; width?: number | string; height?: number | string; value?: number | string }) => {
    const x = Number(p.x), y = Number(p.y), w = Number(p.width), h = Number(p.height), v = Number(p.value);
    if (!v || w < 26) return null;
    return <text x={x + w / 2} y={y + h / 2} dy={4} textAnchor="middle" fontSize={11} fontFamily="JetBrains Mono" fill={fill}>{v}</text>;
  };
  const endLabel = (p: { x?: number | string; y?: number | string; width?: number | string; height?: number | string; index?: number }) => {
    const r = rows[p.index ?? 0];
    if (!r) return null;
    const x = Number(p.x) + Number(p.width) + 6, y = Number(p.y) + Number(p.height) / 2 + 4;
    return <text x={x} y={y} fontSize={11} fontFamily="JetBrains Mono" fill={t.muted}>{r.rejected ? `${r.rejected} rejected` : "0 rejected"}</text>;
  };

  return (
    <Panel title="(a) Verifier: code checks every claim against the page" meta="deterministic, no model">
      <div className="grid grid-cols-4 gap-3">
        <KpiTile hot label="Findings verified" value={num(totals.verified)} footnote={`of ${num(totals.findings)} · meta.json`} />
        <KpiTile label="Claims rejected" value={num(totals.rejected)} footnote="meta.json · totals" />
        <KpiTile label="Held for a human" value={num(needsHuman)} footnote={typeof totals.needs_human === "number" ? "needs_human · meta.json" : "league.json"} />
        <KpiTile label="Audit ledger" value={ledger?.ok ? "Intact" : ledger ? "Broken" : "n/a"} footnote={`${num(ledger?.n)} records · meta.json`} />
      </div>

      <div className="mt-4 grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-5">
        <div>
          <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">What the verifier checks</h3>
          <ol className="mt-2 space-y-1.5 text-[13px]">
            {rules.map((r, i) => (
              <li key={i} className="grid grid-cols-[22px_1fr] gap-1">
                <span className="font-mono text-[11px] text-purple pt-px">{String(i + 1).padStart(2, "0")}</span>
                <span>{r}</span>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-[12.5px] text-muted">
            Verified means every rule passed. Held for a human means no automatic check could confirm it: shown, labelled, and never used for stance dollars.
            Rejected claims never reach a screen except this one.
          </p>
        </div>
        <div className="min-w-0">
          <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">Verdicts per company (findings)</h3>
          <div style={{ height: 300 }} className="mt-1" role="img" aria-label="Stacked bars of verified, held for human, and rejected findings per company">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 78, bottom: 0, left: 0 }} barCategoryGap={6}>
                <CartesianGrid horizontal={false} stroke={t.line} />
                <XAxis type="number" tick={{ fontSize: 11, fill: t.muted, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="ticker" width={46} tick={{ fontSize: 12, fill: t.fg, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: t.line, opacity: 0.4 }} contentStyle={{ fontSize: 12, borderRadius: 6, borderColor: t.line, background: t.surface, color: t.fg }} />
                <Legend verticalAlign="top" height={24} iconType="square" wrapperStyle={{ fontSize: 12 }} formatter={(v: string) => <span style={{ color: t.fg }}>{v}</span>} />
                <Bar dataKey="verified" name="Verified" stackId="v" fill={t.purpleBright} stroke={t.surface} strokeWidth={2} maxBarSize={20} isAnimationActive={false}>
                  <LabelList dataKey="verified" content={insideLabel(t.surface)} />
                </Bar>
                <Bar dataKey="needs_human" name="Held for human" stackId="v" fill={t.grey} stroke={t.surface} strokeWidth={2} maxBarSize={20} isAnimationActive={false}>
                  <LabelList dataKey="needs_human" content={insideLabel("#1F1630")} />
                </Bar>
                <Bar dataKey="rejected" name="Rejected" stackId="v" fill={t.bad} stroke={t.surface} strokeWidth={2} maxBarSize={20} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  <LabelList content={endLabel} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      <SourceNote>meta.json (totals, ledger, verifier_rules) · league.json (n_findings, n_verified, n_rejected; held for human = findings minus verified)</SourceNote>
    </Panel>
  );
}

/* -------------------------------------------------------------- AI caught */

type Wrong = Loose & { stream?: string; table?: string; what_the_ai_said?: string; what_the_source_says?: string; how_caught?: string; count?: number; example_source?: string };

export function AiCaughtPanel({ company, ticker, league, aiWrong, onPick }: {
  company: Company | null; ticker: string | null; league: LeagueRow[] | null; aiWrong: Loose[]; onPick: (t: string) => void;
}) {
  const rows = aiWrong as Wrong[];
  const streams = useMemo(() => {
    const m = new Map<string, number>();
    rows.forEach((r) => m.set(r.stream ?? "other", (m.get(r.stream ?? "other") ?? 0) + 1));
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [rows]);
  const [stream, setStream] = useState<string>("all");
  const shown = stream === "all" ? rows : rows.filter((r) => (r.stream ?? "other") === stream);
  const grouped = streams.filter(([s]) => stream === "all" || s === stream).map(([s]) => [s, shown.filter((r) => (r.stream ?? "other") === s)] as const);
  const itemsTotal = rows.reduce((s, r) => s + (typeof r.count === "number" ? r.count : 0), 0);
  const rejected = company?.rejected ?? [];
  const withRejections = (league ?? []).filter((r) => (r.n_rejected ?? 0) > 0);

  return (
    <Panel title="AI caught: claims stopped before any judge saw them" meta={`${rows.length} logged cases`}>
      <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">Rejected by the page verifier · {ticker ?? "n/a"}</h3>
      {rejected.length ? (
        <div className="mt-2 overflow-auto rounded-md border border-line">
          <table className="w-full border-collapse text-[13px]">
            <thead className="bg-surface-2"><tr>
              <th scope="col" className="text-left px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold w-[58%]">Claim</th>
              <th scope="col" className="text-left px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold">Why rejected</th>
            </tr></thead>
            <tbody>{rejected.map((r, i) => (
              <tr key={i} className="border-b border-line last:border-0 align-top">
                <td className="px-3 py-2">{r.finding ?? "n/a"} {r.signal_kind && <span className="ml-1 font-mono text-[11px] text-muted">{r.signal_kind}</span>}</td>
                <td className="px-3 py-2"><Pill tone="bad">rejected</Pill> <span className="font-mono text-[12px] break-all">{r.reason ?? "n/a"}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : (
        <p className="mt-2 text-[13px] text-muted">
          No claims rejected for {ticker ?? "this company"} in companies/{ticker}.json.{" "}
          {withRejections.length > 0 && <>Rejections exist for{" "}
            {withRejections.map((r, i) => (
              <span key={r.ticker}>{i > 0 && ", "}<button type="button" onClick={() => onPick(r.ticker)} className="font-mono text-purple underline underline-offset-2">{r.ticker} ({r.n_rejected})</button></span>
            ))}.</>}
        </p>
      )}

      <div className="mt-5 rounded-lg border border-purple/30 bg-chip px-4 py-3 flex items-baseline gap-3 flex-wrap">
        <span className="font-display text-[44px] leading-none text-purple-deep dark:text-purple tnum">{rows.length}</span>
        <span className="text-[15px] font-semibold">cases where the AI was confidently wrong, caught before any judge saw them</span>
        <span className="text-[12px] text-muted">{num(itemsTotal)} affected items in all (sum of the count column); each fixed or dropped before export.</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by stream">
        <span className="text-[11px] uppercase tracking-wide text-muted font-semibold mr-1">Stream</span>
        {[["all", rows.length] as const, ...streams].map(([s, n]) => (
          <button key={s} type="button" aria-pressed={stream === s} onClick={() => setStream(s)}
            className={`rounded-full border px-2.5 py-0.5 text-[12px] ${stream === s ? "bg-purple text-white border-purple dark:bg-purple-deep" : "bg-surface border-line hover:bg-surface-2"}`}>
            {s} <span className="font-mono text-[11px] opacity-80">{n}</span>
          </button>
        ))}
      </div>

      <div className="mt-2 overflow-auto rounded-md border border-line" style={{ maxHeight: 560 }}>
        <table className="w-full border-collapse text-[12.5px] table-fixed">
          <colgroup><col style={{ width: "24%" }} /><col style={{ width: "30%" }} /><col style={{ width: "18%" }} /><col style={{ width: "7%" }} /><col style={{ width: "21%" }} /></colgroup>
          <thead className="sticky top-0 z-10 bg-surface-2"><tr>
            {["What the AI said", "What the source says", "How caught", "Count", "Example source"].map((h, i) => (
              <th key={h} scope="col" className={`px-2.5 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold ${i === 3 ? "text-right" : "text-left"}`}>{h}</th>
            ))}
          </tr></thead>
          {grouped.map(([s, rs]) => (
            <tbody key={s}>
              <tr className="bg-surface-2/60"><th colSpan={5} scope="colgroup" className="text-left px-2.5 py-1.5 border-b border-line text-[12px]">
                <span className="font-bold uppercase tracking-wide">{s}</span> <span className="text-muted font-normal">· {rs.length} cases</span>
              </th></tr>
              {rs.map((r, i) => (
                <tr key={i} className="border-b border-line align-top">
                  <td className="px-2.5 py-2 break-words">{r.what_the_ai_said ?? "n/a"}{r.table && <div className="mt-0.5 font-mono text-[10.5px] text-muted break-all">{r.table}</div>}</td>
                  <td className="px-2.5 py-2 break-words">{r.what_the_source_says ?? "n/a"}</td>
                  <td className="px-2.5 py-2 break-words text-muted">{r.how_caught ?? "n/a"}</td>
                  <td className="px-2.5 py-2 text-right font-mono tnum">{typeof r.count === "number" ? num(r.count) : "n/a"}</td>
                  <td className="px-2.5 py-2 font-mono text-[10.5px] break-all text-muted">{r.example_source ?? "n/a"}</td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <SourceNote>companies/{ticker}.json · rejected (page verifier) · proof.json · ai_wrong (from data/moat/verify/ai_wrong.jsonl, written by the second-pass table verifier)</SourceNote>
    </Panel>
  );
}
