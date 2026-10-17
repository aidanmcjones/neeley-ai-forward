import type { Company } from "../../lib/types";
import { h2hRows, titleCase } from "../../lib/exhibits";
import { ExhibitCard } from "./ExhibitCard";

// Compact label comparison table (labels.comparison rows) for the product and its rivals.
export function HeadToHeadExhibit({ company, target: product, title }: { company: Company; target: string; title: string }) {
  const { slugs, rows } = h2hRows(company, product);
  const differs = rows.filter((r) => new Set(r.cells.map((c) => c.text)).size > 1).map((r) => r.label);
  return (
    <ExhibitCard ticker={company.ticker} pin={{ kind: "h2h", ref: product, title }} wide
      reading={rows.length ? (differs.length ? `Differs on: ${differs.join(", ")}.` : "No differences in the exported fields.") : undefined}
      source={<>labels.comparison in companies/{company.ticker}.json (FDA labels via DailyMed, Orange / Purple Book, CMS Part D, gtn_exposure.csv)</>}>
      {!rows.length ? <p className="text-sm text-muted">No label comparison exported for {titleCase(product)}.</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse table-fixed">
            <colgroup><col className="w-[150px]" />{slugs.map((s) => <col key={s} />)}</colgroup>
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className="text-left py-1.5 pr-2 font-semibold text-muted">Field</th>
                {slugs.map((s, i) => (
                  <th key={s} scope="col" className="text-left py-1.5 pr-2 font-bold">
                    <span className={`mr-1.5 inline-block h-2 w-2 rounded-full align-middle ${i === 0 ? "bg-purple" : "bg-frog-grey"}`} aria-hidden="true" />
                    {titleCase(s)}{i === 0 ? <span className="sr-only"> (company product)</span> : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label} className="border-b border-line last:border-0 align-top">
                  <th scope="row" className="text-left py-1.5 pr-2 font-medium text-muted">{r.label}</th>
                  {r.cells.map((c) => (
                    <td key={c.slug} className="py-1.5 pr-2 tnum" title={c.source ? `${c.text}\n(${c.source})` : c.text}>
                      <span className={`line-clamp-2 break-words ${c.text === "not exported" ? "text-muted italic" : ""}`}>{c.text}</span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ExhibitCard>
  );
}
