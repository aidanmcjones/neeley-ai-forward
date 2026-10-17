import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Company, PricePoint } from "../../lib/types";
import { EmptyState } from "../EmptyState";
import { Segmented, drugName, isNum, useTokens } from "./util";
import type { Tokens } from "./util";

// Price series small multiples: one panel per drug (product + one chosen rival), same y-scale when units match.
// Part D gross per unit and NADAC brand per unit are list-like; the MFP is a net-like statutory ceiling.

function niceTicks(max: number): number[] {
  const raw = max / 4;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = ([1, 2, 2.5, 5, 10].find((k) => k * p >= raw) ?? 10) * p;
  const top = Math.ceil(max / step) * step;
  return Array.from({ length: Math.round(top / step) + 1 }, (_, i) => +(i * step).toFixed(6));
}
const tick = (x: number) => (Number.isInteger(x) ? `$${x.toLocaleString("en-US")}` : `$${x.toFixed(2)}`);
const fmt = (x: number) => (x >= 100 ? `$${Math.round(x).toLocaleString("en-US")}` : `$${x.toFixed(2)}`);

export function PriceSeries({ company, product, rivals }: { company: Company; product: string; rivals: string[] }) {
  const ps = company.price_series ?? {};
  const withData = rivals.filter((r) => (ps[r] ?? []).length > 0);
  const [rival, setRival] = useState<string>(withData[0] ?? "none");
  useEffect(() => { setRival(withData[0] ?? "none"); }, [product]); // eslint-disable-line react-hooks/exhaustive-deps
  const t = useTokens();

  const own = ps[product] ?? [];
  const shown = [product, ...(rival !== "none" ? [rival] : [])];
  const unitOf = (s: string) => (ps[s] ?? []).map((p) => p.nadac_unit).find((u) => typeof u === "string") as string | undefined;
  const sameUnit = shown.length === 2 && unitOf(shown[0]) && unitOf(shown[0]) === unitOf(shown[1]);
  const shared = useMemo(() => {
    if (!sameUnit) return undefined;
    const vals = shown.flatMap((s) => (ps[s] ?? []).flatMap((p) => [p.partd_per_unit, p.nadac_brand, p.mfp_per_unit])).filter(isNum);
    return vals.length ? niceTicks(Math.max(...vals)) : undefined;
  }, [sameUnit, shown.join(","), ps]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!own.length) {
    return <EmptyState file={`companies/${company.ticker}.json · price_series.${product}`} message={`No price series exported for ${drugName(product)}`} />;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[12px] font-semibold text-muted">Compare {drugName(product)} with</span>
        <Segmented
          label="Rival for price comparison"
          value={rival}
          onChange={setRival}
          options={[...withData.map((r) => ({ value: r, label: drugName(r) })), { value: "none", label: "Product only" }]}
        />
        {rivals.length > withData.length && (
          <span className="text-[11px] text-muted">No price series: {rivals.filter((r) => !withData.includes(r)).map(drugName).join(", ")}</span>
        )}
      </div>
      <Legend t={t} />
      <div className={`grid gap-4 ${shown.length === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
        {shown.map((s) => (
          <DrugPanel key={s} slug={s} pts={ps[s] ?? []} color={s === product ? t.purple : t.grey} t={t} ticks={shared} own={s === product} />
        ))}
      </div>
      <p className="text-[12px] text-muted">
        <span className="font-semibold text-fg">List-like vs net-like.</span> Part D gross per unit (pre-rebate pharmacy cost) and NADAC brand
        per unit (pharmacy acquisition, near WAC) are list-like. ASP and the IRA MFP are net-like. A true product-level net price is not free
        anywhere; these are proxies.{" "}
        {shown.length === 2 && !sameUnit && <span className="text-warn">Units differ between these drugs, so each panel has its own scale.</span>}
        <span className="block font-mono text-[10px] mt-1">
          companies/{company.ticker}.json · price_series (partd_by_year.csv, nadac_history.csv, partb_asp_quarterly.csv, ira_negotiation.csv) · wording from data/moat/tables/README_pricing.md
        </span>
      </p>
    </div>
  );
}

function Legend({ t }: { t: Tokens }) {
  const item = (dash: string | undefined, shape: "circle" | "square", text: string) => (
    <span className="inline-flex items-center gap-1.5">
      <svg width="28" height="10" aria-hidden="true">
        <line x1="0" y1="5" x2="28" y2="5" stroke={t.fg} strokeWidth="2" strokeDasharray={dash} />
        {shape === "circle" ? <circle cx="14" cy="5" r="3.5" fill={t.fg} /> : <rect x="10.5" y="1.5" width="7" height="7" fill={t.fg} />}
      </svg>
      {text}
    </span>
  );
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 text-[12px] text-muted">
      {item(undefined, "circle", "Part D gross per unit (list-like)")}
      {item("5 3", "square", "NADAC brand per unit (list-like)")}
      <span className="inline-flex items-center gap-1.5">
        <svg width="28" height="10" aria-hidden="true"><line x1="0" y1="5" x2="28" y2="5" stroke={t.muted} strokeWidth="1.5" strokeDasharray="2 2" /></svg>
        IRA MFP per unit (net-like ceiling, flat line)
      </span>
      <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-purple" aria-hidden="true" />product</span>
      <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-frog-grey" aria-hidden="true" />rival</span>
    </div>
  );
}

function DrugPanel({ slug, pts, color, t, ticks: sharedTicks, own }: { slug: string; pts: PricePoint[]; color: string; t: Tokens; ticks?: number[]; own: boolean }) {
  const data = [...pts].sort((a, b) => a.year - b.year);
  const own_vals = data.flatMap((p) => [p.partd_per_unit, p.nadac_brand, p.mfp_per_unit]).filter(isNum);
  const ticks = sharedTicks ?? (own_vals.length ? niceTicks(Math.max(...own_vals)) : [0, 1]);
  const mfp = data.find((p) => isNum(p.mfp_per_unit));
  const mfpLater = data.filter((p) => isNum(p.mfp_per_unit)).slice(1);
  const unit = data.map((p) => p.nadac_unit).find((u) => typeof u === "string") as string | undefined;
  const hasAny = data.some((p) => isNum(p.partd_per_unit) || isNum(p.nadac_brand));
  const hasAsp = data.some((p) => isNum(p.asp));
  const lastOf = (k: "partd_per_unit" | "nadac_brand") => [...data].reverse().find((p) => isNum(p[k]));
  const lp = lastOf("partd_per_unit"), ln = lastOf("nadac_brand");

  return (
    <figure className="rounded-md border border-line p-3 min-w-0" style={{ borderTop: `3px solid ${color}` }}>
      <figcaption className="flex items-baseline justify-between gap-2">
        <span className="font-bold">{drugName(slug)} <span className="text-[11px] font-normal text-muted">{own ? "product" : "rival"}</span></span>
        <span className="text-[11px] text-muted">$ per {unit === "EA" ? "unit (tablet/pen, EA)" : unit === "ML" ? "mL" : "dosage unit"}</span>
      </figcaption>
      {hasAny ? (
        <div className="h-[220px] mt-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 16, bottom: 4, left: 4 }}>
              <CartesianGrid stroke={t.line} vertical={false} />
              <XAxis dataKey="year" tick={{ fill: t.muted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: t.line }} />
              <YAxis tick={{ fill: t.muted, fontSize: 11 }} tickLine={false} axisLine={false} width={56} domain={[0, ticks[ticks.length - 1]]} ticks={ticks} interval={0} tickFormatter={(v: number) => tick(v)} />
              <Tooltip content={<Tip t={t} />} cursor={{ stroke: t.muted, strokeWidth: 1 }} />
              {mfp && (
                <ReferenceLine
                  y={mfp.mfp_per_unit as number}
                  stroke={t.muted}
                  strokeDasharray="2 2"
                  label={{ value: `MFP ${fmt(mfp.mfp_per_unit as number)} (${mfp.year})`, position: "insideBottomLeft", fill: t.fg, fontSize: 11 }}
                />
              )}
              <Line type="linear" dataKey="partd_per_unit" name="Part D gross per unit" stroke={color} strokeWidth={2} connectNulls={false} isAnimationActive={false}
                dot={{ r: 4, fill: color, stroke: t.surface, strokeWidth: 2 }} activeDot={{ r: 5, stroke: t.surface, strokeWidth: 2 }} />
              <Line type="linear" dataKey="nadac_brand" name="NADAC brand per unit" stroke={color} strokeWidth={2} strokeDasharray="5 3" connectNulls={false} isAnimationActive={false}
                dot={<SquareDot fill={color} ring={t.surface} />} activeDot={{ r: 5, stroke: t.surface, strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="mt-2 text-[12px] text-muted italic">No Part D or NADAC per-unit rows for this drug (it may be Part B only).</div>
      )}
      <div className="mt-1 text-[11px] text-muted tnum">
        {lp && <>Part D {lp.year}: {fmt(lp.partd_per_unit as number)}. </>}
        {ln && <>NADAC {ln.year}: {fmt(ln.nadac_brand as number)}. </>}
        {mfp ? <>MFP effective {mfp.year}: {fmt(mfp.mfp_per_unit as number)}/unit{isNum(mfp.mfp_per_30day) ? `, $${(mfp.mfp_per_30day as number).toFixed(2)} per 30 days` : ""}
          {mfpLater.map((p) => `; ${p.year}: ${fmt(p.mfp_per_unit as number)}`).join("")}.</> : <>No MFP (not selected for IPAY 2026/2027).</>}
      </div>
      {hasAsp && (
        <div className="mt-1 text-[11px] text-muted tnum">
          Part B ASP payment limit per HCPCS unit (net-like, not comparable per unit with the lines above):{" "}
          {data.filter((p) => isNum(p.asp)).map((p) => `${p.year} ${fmt(p.asp as number)}`).join(" · ")}
        </div>
      )}
    </figure>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function SquareDot(props: any) {
  const { cx, cy, fill, ring, value } = props;
  if (!isNum(value) || cx == null || cy == null) return <g />;
  return <rect x={cx - 4} y={cy - 4} width={8} height={8} fill={fill} stroke={ring} strokeWidth={2} />;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function Tip({ active, payload, label, t }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload as PricePoint;
  const row = (k: string, v: unknown) => (isNum(v) ? <div key={k} className="flex justify-between gap-4"><span>{k}</span><span className="font-mono tnum">{fmt(v)}</span></div> : null);
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-[12px] shadow-card" style={{ color: t.fg }}>
      <div className="font-semibold mb-1">{label}</div>
      {row("Part D gross / unit", p.partd_per_unit)}
      {row("NADAC brand / unit", p.nadac_brand)}
      {row("MFP / unit", p.mfp_per_unit)}
      {row("Part D per claim", p.partd_per_claim)}
    </div>
  );
}
