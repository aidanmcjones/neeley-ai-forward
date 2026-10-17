import { Fragment } from "react";
import type { LeagueRow, Meta } from "../lib/types";

// League robustness (meta.league_robustness = out/league_v3_robustness.json): rank of each ticker
// under each scoring variant, the selected company highlighted, and who leads how often.

interface Variant { label?: string; ranking?: [string, number][]; strict?: number; needles?: Record<string, string> }

const TINY: Record<string, string> = {
  base: "Base", raw_sum: "Raw", mfn_universal: "MFN", amgn_rec_pi_min: "Rec π", amgn_rec_not_fired: "Rec off",
  H6: "H6", ira_spec: "IRA", c_anchor_half: "Anc ½",
};

const SHORT: Record<string, string> = {
  base: "Base", raw_sum: "Raw sum", mfn_universal: "MFN 0.65%", amgn_rec_pi_min: "AMGN rec π min",
  amgn_rec_not_fired: "AMGN rec off", H6: "H = 6", ira_spec: "IRA spec", c_anchor_half: "Anchor ½",
};

export function robustnessData(meta: Meta | null | undefined) {
  const raw = (meta?.league_robustness ?? null) as Record<string, Variant> | null;
  if (!raw || typeof raw !== "object") return null;
  const keys = Object.keys(raw).filter((k) => Array.isArray(raw[k]?.ranking) && raw[k].ranking!.length);
  if (!keys.length) return null;
  const rank = (k: string, t: string) => {
    const i = raw[k].ranking!.findIndex((r) => r[0] === t);
    return i >= 0 ? i + 1 : null;
  };
  const base = keys.includes("base") ? "base" : keys[0];
  const tickers = raw[base].ranking!.map((r) => r[0]);
  const leads = new Map<string, number>();
  for (const k of keys) { const top = raw[k].ranking![0][0]; leads.set(top, (leads.get(top) ?? 0) + 1); }
  const leaders = [...leads.entries()].sort((a, b) => b[1] - a[1]);
  const reading = leaders.map(([t, n], i) => `${t} leads in ${n} of ${keys.length}${i === 0 ? " variants" : ""}`).join("; ");
  return { raw, keys, tickers, rank, reading };
}

export function RankChange({ row }: { row?: LeagueRow | null }) {
  const now = typeof row?.rank === "number" ? row.rank : null;
  const v2 = typeof row?.v2_rank === "number" ? row.v2_rank : null;
  if (now == null || v2 == null) return null;
  const d = v2 - now;
  const txt = d > 0 ? `▲${d}` : d < 0 ? `▼${-d}` : "=";
  const tone = d > 0 ? "text-good" : d < 0 ? "text-bad" : "text-muted";
  return <span className={`font-mono text-[11px] ${tone}`} title={`v3 rank #${now}; v2 rank #${v2}`}>{txt} <span className="text-muted">vs v2 #{v2}</span></span>;
}

export function RobustnessTable({ meta, league, selected, onPick, compact = false }: {
  meta: Meta | null; league?: LeagueRow[] | null; selected?: string | null; onPick?: (t: string) => void; compact?: boolean;
}) {
  const d = robustnessData(meta);
  if (!d) return <p className="text-sm text-muted">No robustness table exported (meta.json · league_robustness).</p>;
  const { raw, keys, tickers, rank, reading } = d;
  const v2 = (t: string) => league?.find((r) => r.ticker === t)?.v2_rank;
  return (
    <div className="min-w-0 space-y-1.5">
      <p className="text-[12px] font-semibold leading-snug">{reading}.</p>
      <div className="overflow-x-auto">
        <table className={`w-full border-collapse tnum ${compact ? "text-[11px]" : "text-[12px]"}`}>
          <caption className="sr-only">League rank of each company under {keys.length} scoring variants; {reading}</caption>
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wide text-muted">
              <th scope="col" className="px-1 py-1 text-left font-semibold">Co.</th>
              {!compact && <th scope="col" className="px-1 py-1 text-right font-semibold" title="Rank under the v2 engine">v2</th>}
              {keys.map((k) => (
                <th key={k} scope="col" title={raw[k].label ?? k} className="px-1 py-1 text-center font-semibold">
                  {compact ? TINY[k] ?? k.slice(0, 5) : SHORT[k] ?? k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickers.map((t) => {
              const sel = t === selected;
              return (
                <tr key={t} className={`border-b border-line ${sel ? "bg-chip font-semibold" : ""}`}>
                  <th scope="row" className="px-1 py-0.5 text-left">
                    {onPick ? <button type="button" onClick={() => onPick(t)} className={`font-mono ${sel ? "text-purple" : "hover:text-purple"}`}>{t}</button> : <span className="font-mono">{t}</span>}
                  </th>
                  {!compact && <td className="px-1 py-0.5 text-right font-mono text-muted">{v2(t) ?? "n/a"}</td>}
                  {keys.map((k) => {
                    const r = rank(k, t);
                    const st = raw[k].needles?.[t];
                    return (
                      <Fragment key={k}>
                        <td className={`px-1 py-0.5 text-center font-mono ${r === 1 ? "text-purple font-bold" : ""}`}
                          title={`${t} under "${raw[k].label ?? k}": rank ${r ?? "n/a"}${st ? `; needle ${st}` : ""}`}>
                          {r ?? "n/a"}{st === "none" ? <sup className="text-muted">∅</sup> : null}
                        </td>
                      </Fragment>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[10.5px] text-muted leading-snug">
        Rank 1 in purple; ∅ = no row qualifies as the needle under that variant. Hover a column for its rule. Source: meta.json · league_robustness (out/league_v3_robustness.json).
      </p>
    </div>
  );
}
