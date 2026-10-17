import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { loadCompany } from "../../lib/data";
import type { Source } from "../../lib/data";
import type { Company, Loose, Meta } from "../../lib/types";
import { DataTable } from "../DataTable";
import type { Column } from "../DataTable";
import { EmptyState } from "../EmptyState";
import { Panel } from "../Panel";
import { isNum, str, useTokens } from "../product/util";
import type { Tokens } from "../product/util";

// Ten-company comparison of the three forces (IRA, MFN, tariffs) from each company's `forces` row.
// Company files load lazily and are cached for the session.

const SRC = "data/moat/verified/policy/force_summary.csv";

type Row = { ticker: string; name?: string; f: Loose | null; err?: string };

const memo = new Map<string, Row>();

export function useAllForces(meta: Meta | null, source: Source | null, current: Company | null) {
  const [rows, setRows] = useState<Row[]>([]);
  const tickers = (meta?.companies ?? []).map((c) => c.ticker);
  const prefix = source?.prefix ?? null;
  useEffect(() => {
    if (!source) return;
    let live = true;
    const key = (t: string) => source.prefix + t;
    const pending = tickers.filter((t) => !memo.has(key(t)));
    if (current?.ticker && !memo.has(key(current.ticker))) memo.set(key(current.ticker), { ticker: current.ticker, name: current.name, f: current.forces ?? null });
    const push = () => live && setRows(tickers.map((t) => memo.get(key(t)) ?? { ticker: t, f: null, err: "loading" }));
    push();
    Promise.all(pending.map((t) =>
      loadCompany(source, t).then(
        (c) => { memo.set(key(t), { ticker: t, name: c.name, f: c.forces ?? null }); },
        (e) => { memo.set(key(t), { ticker: t, f: null, err: (e as Error).message }); },
      ).then(push),
    ));
    return () => { live = false; };
  }, [tickers.join(","), prefix]); // eslint-disable-line react-hooks/exhaustive-deps
  return rows;
}

const n = (r: Row, k: string) => (isNum(r.f?.[k]) ? (r.f![k] as number) : null);
const s = (r: Row, k: string) => str(r.f?.[k]);

export function ForcesCompare({ rows, selected, onSelect }: { rows: Row[]; selected: string | null; onSelect: (t: string) => void }) {
  const t = useTokens();
  const ok = rows.filter((r) => r.f);
  const loading = rows.some((r) => r.err === "loading");
  const failed = rows.filter((r) => r.err && r.err !== "loading");

  const cols: Column<Row>[] = useMemo(() => [
    { key: "ticker", header: "Company", width: "90px", render: (r) => (
      <span className={`font-bold ${r.ticker === selected ? "text-purple" : ""}`}>{r.ticker}{r.ticker === selected && <span className="ml-1 text-[10px] font-semibold uppercase text-purple">selected</span>}</span>
    ) },
    { key: "ira", header: "IRA share %", align: "right", sortValue: (r) => n(r, "ira_share_of_total_revenue_pct"), render: (r) => (
      <div className="tnum">
        <div className="font-semibold">{n(r, "ira_share_of_total_revenue_pct")?.toFixed(1) ?? "n/a"}%</div>
        {n(r, "ira_share_incl_partnered_pct") != null && n(r, "ira_share_incl_partnered_pct") !== n(r, "ira_share_of_total_revenue_pct") && (
          <div className="text-[11px] text-muted">{n(r, "ira_share_incl_partnered_pct")!.toFixed(1)}% incl. partnered</div>
        )}
        {n(r, "expected_share_pct") != null && <div className="text-[11px] text-warn">{n(r, "expected_share_pct")!.toFixed(1)}% if expected selection</div>}
      </div>
    ) },
    { key: "drugs", header: "IRA drugs", sortable: false, width: "26%", render: (r) => <span className="text-[12px]">{s(r, "ira_drugs") ?? <i className="text-muted">none listed</i>}</span> },
    { key: "mfn", header: "MFN date", sortValue: (r) => s(r, "mfn_date"), render: (r) => <span className="font-mono text-[12px]">{s(r, "mfn_date") ?? "n/a"}</span> },
    { key: "pledge", header: "US pledge $bn", align: "right", sortValue: (r) => n(r, "us_investment_pledge_usd_bn"), render: (r) => (
      <div className="tnum">
        <div className="font-semibold">{n(r, "us_investment_pledge_usd_bn") != null ? `$${n(r, "us_investment_pledge_usd_bn")}bn` : <i className="text-muted font-normal">none stated</i>}</div>
        {s(r, "pledge_horizon") && <div className="text-[11px] text-muted">{s(r, "pledge_horizon")}</div>}
      </div>
    ) },
    { key: "tariff", header: "Tariff exempt until", sortValue: (r) => s(r, "tariff_exempt_until"), render: (r) => <span className="font-mono text-[12px]">{s(r, "tariff_exempt_until") ?? "n/a"}</span> },
    { key: "sites", header: "Sites outside US", align: "right", sortValue: (r) => n(r, "pct_mfg_sites_outside_us"), render: (r) => (
      <div className="tnum">
        <div className="font-semibold">{n(r, "pct_mfg_sites_outside_us")?.toFixed(1) ?? "n/a"}%</div>
        <div className="text-[11px] text-muted">{n(r, "mfg_sites_non_us") ?? "?"} of {n(r, "mfg_sites_total") ?? "?"} sites{/^low/i.test(s(r, "mfg_sites_confidence") ?? "") ? " (floor)" : ""}</div>
      </div>
    ) },
    { key: "us", header: "US revenue %", align: "right", sortValue: (r) => n(r, "us_revenue_share_pct"), render: (r) => <span className="tnum font-semibold">{n(r, "us_revenue_share_pct")?.toFixed(1) ?? "n/a"}%</span> },
  ], [selected]);

  if (!rows.length) return <EmptyState file="meta.json · companies" message="No companies listed in meta.json" />;

  return (
    <Panel title="Three forces across the 10" meta={<span className="font-mono">{loading ? "loading company files…" : `${ok.length} of ${rows.length} companies · forces`}</span>}>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <SmallBars title="IRA share of revenue (%)" sub="selected drugs' global product revenue / total revenue, FY2025" rows={ok} k="ira_share_of_total_revenue_pct" selected={selected} t={t} />
        <SmallBars title="Manufacturing sites outside the US (%)" sub="CDER-registered sites; a floor where CBER sites are missing" rows={ok} k="pct_mfg_sites_outside_us" selected={selected} t={t} />
      </div>
      <DataTable
        columns={cols}
        rows={rows.filter((r) => r.f || r.err !== "loading")}
        rowKey={(r) => r.ticker}
        selectedKey={selected}
        onSelect={(r) => onSelect(r.ticker)}
        initialSort={{ key: "ira", dir: "desc" }}
        caption="Three forces by company"
        maxHeight={2000}
        dense
        empty="No forces rows loaded"
      />
      {failed.length > 0 && (
        <div className="mt-2 text-[12px] text-warn">Not loaded: {failed.map((r) => `${r.ticker} (${r.err})`).join("; ")}</div>
      )}
      {ok.length < rows.length && !loading && (
        <div className="mt-1 text-[12px] text-muted">Missing `forces` row: {rows.filter((r) => !r.f && !r.err).map((r) => r.ticker).join(", ") || "none"}</div>
      )}
      <p className="mt-2 text-[11px] text-muted leading-relaxed">
        <span className="font-mono">{SRC}</span> (one row per company, exported to <span className="font-mono">companies/&lt;T&gt;.json · forces</span>; trace ids in <span className="font-mono">traceable_row_ids</span>).
        IRA share basis: global product revenue of the selected drugs / total revenue, own drugs only; partnered share shown separately, never summed across companies.
        Pledges have different horizons and scopes, so do not compare them as annual rates. Site counts come from the CDER registration file and are a floor (cell-therapy and biologics sites under CBER are missing).
        Click a row to switch company.
      </p>
    </Panel>
  );
}

function SmallBars({ title, sub, rows, k, selected, t }: { title: string; sub: string; rows: Row[]; k: string; selected: string | null; t: Tokens }) {
  const data = rows.map((r) => ({ ticker: r.ticker, v: n(r, k) })).filter((d) => d.v != null).sort((a, b) => (b.v as number) - (a.v as number));
  if (!data.length) return <EmptyState file={`companies/*.json · forces.${k}`} message={`No ${title} values`} />;
  return (
    <figure className="min-w-0">
      <figcaption className="text-[12px] font-semibold">{title}<span className="block text-[11px] font-normal text-muted">{sub}</span></figcaption>
      <div style={{ height: data.length * 24 + 28 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 44, bottom: 4, left: 0 }} barCategoryGap={3}>
            <CartesianGrid stroke={t.line} horizontal={false} />
            <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fill: t.muted, fontSize: 10 }} tickLine={false} axisLine={{ stroke: t.line }} />
            <YAxis type="category" dataKey="ticker" width={44} tick={{ fill: t.fg, fontSize: 11, fontWeight: 600 }} tickLine={false} axisLine={false} interval={0} />
            <Tooltip cursor={{ fill: t.line, opacity: 0.4 }} formatter={(v: number) => [`${v.toFixed(1)}%`, title]} contentStyle={{ background: t.surface, border: `1px solid ${t.line}`, color: t.fg, fontSize: 12 }} />
            <Bar dataKey="v" radius={[0, 4, 4, 0]} maxBarSize={16} isAnimationActive={false}>
              {data.map((d) => <Cell key={d.ticker} fill={d.ticker === selected ? t.purple : t.grey} />)}
              <LabelList dataKey="v" position="right" formatter={(v: number) => `${v.toFixed(1)}%`} style={{ fill: t.fg, fontSize: 11 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
