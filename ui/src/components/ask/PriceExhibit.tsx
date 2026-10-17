import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Company } from "../../lib/types";
import { pricePanels, titleCase, useThemeColors } from "../../lib/exhibits";
import { ExhibitCard } from "./ExhibitCard";

// Small multiples, one per drug, shared y scale: Part D gross per unit (solid line, dots),
// NADAC brand per unit (lighter line of the same hue), MFP per unit as a flat reference line.
// Product in purple, rivals in frog-grey; series identity is also in the legend and end labels.

const usd = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? `$${v.toFixed(2)}` : "n/a");

export function PriceExhibit({ company, target: product, title }: { company: Company; target: string; title: string }) {
  const col = useThemeColors();
  const panels = pricePanels(company, product);
  const pin = { kind: "price", ref: product, title };
  const source = <>price_series in companies/{company.ticker}.json (CMS Part D spending, NADAC history, CMS negotiated prices file; data/moat/tables/gtn_proxy.csv)</>;
  if (!panels.length) {
    return <ExhibitCard ticker={company.ticker} pin={pin} wide source={source}><p className="text-sm text-muted">No price series exported for {titleCase(product)}.</p></ExhibitCard>;
  }
  const yMax = Math.max(...panels.flatMap((p) => p.points.flatMap((x) => [x.partd_per_unit ?? 0, x.nadac_brand ?? 0])), ...panels.map((p) => p.mfpUnit ?? 0));
  const top = Math.ceil((yMax * 1.1) / 100) * 100;
  const own = panels.find((p) => p.own) ?? panels[0];
  const lastOf = (key: "partd_per_unit" | "nadac_brand") => [...own.points].reverse().find((x) => x[key] != null);
  const lp = lastOf("partd_per_unit"), ln = lastOf("nadac_brand");
  const parts = [
    lp ? `Part D gross ${usd(lp.partd_per_unit)}/unit (${lp.year})` : "no Part D gross per unit exported",
    ln ? `NADAC brand ${usd(ln.nadac_brand)}/unit (${ln.year})` : "no NADAC brand price exported",
  ];
  const reading = `${titleCase(own.slug)}: ${parts.join(", ")}${own.mfpUnit != null ? `, MFP ${usd(own.mfpUnit)}/unit` : ""}${panels.some((p) => p.mfpUnit != null && !p.own) ? `; rival MFP: ${panels.filter((p) => !p.own && p.mfpUnit != null).map((p) => `${titleCase(p.slug)} ${usd(p.mfpUnit)}`).join(", ")}` : ""}.`;
  const years = panels.flatMap((p) => p.points.map((x) => x.year));
  const x0 = Math.min(...years), x1 = Math.max(...years);
  return (
    <ExhibitCard ticker={company.ticker} pin={pin} wide reading={reading} source={source}>
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted" aria-label="Legend">
        <li className="flex items-center gap-1.5"><svg width="22" height="10" aria-hidden="true"><line x1="0" x2="22" y1="5" y2="5" stroke={col.purple} strokeWidth="2" /><circle cx="11" cy="5" r="3.5" fill={col.purple} /></svg>Part D gross / unit</li>
        <li className="flex items-center gap-1.5"><svg width="22" height="10" aria-hidden="true"><line x1="0" x2="22" y1="5" y2="5" stroke={col.purple} strokeOpacity="0.4" strokeWidth="2" /></svg>NADAC brand / unit</li>
        <li className="flex items-center gap-1.5"><svg width="22" height="10" aria-hidden="true"><line x1="0" x2="22" y1="5" y2="5" stroke={col.fg} strokeWidth="1.5" strokeDasharray="4 3" /></svg>IRA MFP / unit (reference)</li>
        <li className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full bg-purple" />{titleCase(own.slug)}</li>
        <li className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full bg-frog-grey" />Rivals</li>
      </ul>
      <div className={`grid gap-3 ${panels.length >= 3 ? "grid-cols-3" : panels.length === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
        {panels.map((p) => {
          const c = p.own ? col.purple : col["frog-grey"];
          return (
            <figure key={p.slug} className="min-w-0">
              <figcaption className="text-xs font-bold mb-0.5">{titleCase(p.slug)}{p.unit ? <span className="font-normal text-muted"> · per {p.unit}</span> : null}</figcaption>
              <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={p.points} margin={{ top: 14, right: 12, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke={col.line} vertical={false} />
                    <XAxis dataKey="year" type="number" domain={[x0, x1]} ticks={[...new Set(years)].sort()} tick={{ fontSize: 10, fill: col.muted }} stroke={col.line} tickLine={false} allowDecimals={false} />
                    <YAxis domain={[0, top]} tick={{ fontSize: 10, fill: col.muted }} stroke={col.line} tickLine={false} width={42} tickFormatter={(v: number) => `$${v}`} />
                    <Tooltip
                      formatter={(v: unknown, name: string) => [usd(v), name]}
                      labelFormatter={(y) => `${titleCase(p.slug)} ${y}`}
                      contentStyle={{ background: col.surface, border: `1px solid ${col.line}`, borderRadius: 6, fontSize: 11, color: col.fg }}
                    />
                    {p.mfpUnit != null && (
                      <ReferenceLine y={p.mfpUnit} stroke={col.fg} strokeWidth={1.5} strokeDasharray="4 3"
                        label={{ value: `MFP ${usd(p.mfpUnit)}`, position: "insideBottomLeft", fontSize: 10, fill: col.fg }} />
                    )}
                    <Line name="NADAC brand / unit" dataKey="nadac_brand" stroke={c} strokeOpacity={0.4} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
                    <Line name="Part D gross / unit" dataKey="partd_per_unit" stroke={c} strokeWidth={2} dot={{ r: 4, fill: c, stroke: col.surface, strokeWidth: 2 }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </figure>
          );
        })}
      </div>
      <details className="mt-2 text-[11px]">
        <summary className="cursor-pointer text-muted">Table view</summary>
        <table className="mt-1 w-full tnum font-mono">
          <thead><tr className="text-muted text-left"><th className="pr-2">Drug</th><th className="pr-2">Year</th><th className="pr-2">Part D gross/unit</th><th className="pr-2">NADAC brand</th><th>MFP/unit</th></tr></thead>
          <tbody>
            {panels.flatMap((p) => p.points.map((x) => (
              <tr key={`${p.slug}-${x.year}`}><td className="pr-2">{titleCase(p.slug)}</td><td className="pr-2">{x.year}</td><td className="pr-2">{usd(x.partd_per_unit)}</td><td className="pr-2">{usd(x.nadac_brand)}</td><td>{usd(x.mfp_per_unit)}</td></tr>
            )))}
          </tbody>
        </table>
      </details>
    </ExhibitCard>
  );
}
