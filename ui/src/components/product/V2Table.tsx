import { Fragment } from "react";
import type { Company, Evidence, Loose, NumericCheck } from "../../lib/types";
import { CiteChip } from "../CiteChip";
import { ConfPill } from "../ConfPill";
import { NumericPill } from "../NumericCheck";
import { money } from "../../lib/format";

// v2 product fine print (out/<T>/product_<slug>.json via labels.v2[slug]): five cited rows,
// one column per entity, a citation chip in every cell, the tied product findings, and the
// uncited-cell count stated as a footnote.

interface V2Cell extends Loose { value?: string | null; citations?: Evidence[]; empty_reason?: string | null; source?: string; uncited?: boolean }
interface V2Entity extends Loose { name: string; slug?: string; maker?: string; variant?: string; note?: string }
interface V2Finding extends Loose {
  id: string; finding: string; confidence?: string; direction?: string; channel?: string;
  impact?: { formula?: string; dollars?: number | null } & Loose; evidence?: Evidence[]; flags?: unknown[];
}
export interface ProductV2 extends Loose {
  product: string; entities?: V2Entity[]; row_titles?: Record<string, string>; rows?: Record<string, Record<string, V2Cell>>;
  findings?: V2Finding[]; uncited_cells?: { row: string; entity: string }[]; empty_cells?: { row: string; entity: string }[];
  growth_limiter?: { sentence?: string; priced_in?: boolean; reasons?: string[] } & Loose; source_file?: string;
}

/** Compact chip text: "§2.1" for label sections, "p. 26" for pages, else the index. */
function shortCite(ev: Evidence, j: number): string {
  const loc = String(ev.location ?? ev.printed ?? "");
  const sec = loc.match(/section\s+([0-9][0-9.]*)/i);
  if (sec) return `§${sec[1].replace(/\.$/, "")}`;
  if (/warning/i.test(loc)) return "§boxed";
  const pg = loc.match(/p\.\s*(\d+)/) ?? (ev.page != null ? [null, String(ev.page)] : null);
  if (pg) return `p. ${pg[1]}`;
  return `[${j + 1}]`;
}

export function productV2(company: Company, product: string): ProductV2 | null {
  const v2 = (company.labels as Loose | null | undefined)?.v2 as Record<string, ProductV2> | undefined;
  return v2?.[product] ?? null;
}

export function V2Table({ data, onPreview }: { data: ProductV2; onPreview?: (e: Evidence | null) => void }) {
  const ents = data.entities ?? [];
  const rowKeys = Object.keys(data.rows ?? {});
  const titles = data.row_titles ?? {};
  const uncited = data.uncited_cells ?? [];
  const isUncited = (row: string, ent: string) => data.rows?.[row]?.[ent]?.uncited === true || uncited.some((u) => u.row === row && u.entity === ent);
  const nUncited = Object.entries(data.rows ?? {}).reduce((a, [rk, r]) => a + Object.keys(r).filter((e) => isUncited(rk, e)).length, 0);
  const uncitedList = Object.entries(data.rows ?? {}).flatMap(([rk, r]) => Object.keys(r).filter((e) => isUncited(rk, e)).map((e) => ({ row: rk, entity: e })));
  return (
    <div className="min-w-0">
      <table className="w-full table-fixed border-collapse text-[12.5px]">
        <caption className="sr-only">{data.product} versus rivals, five rows, each cell cited</caption>
        <thead>
          <tr className="border-b border-line bg-surface-2 text-left">
            <th scope="col" className="w-[150px] px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted">Row</th>
            {ents.map((e, i) => (
              <th key={e.name} scope="col" className={`px-3 py-2 text-[13px] font-bold ${i === 0 ? "text-purple" : ""}`}>
                {i === 0 && <span aria-hidden="true">● </span>}{e.name}
                {e.maker && <span className="block text-[10.5px] font-normal text-muted">{e.maker}{e.ingredient ? ` · ${String(e.ingredient)}` : ""}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowKeys.map((rk) => (
            <tr key={rk} className="border-b border-line align-top">
              <th scope="row" className="px-3 py-2 text-left text-[12px] font-semibold">{titles[rk] ?? rk.replace(/_/g, " ")}</th>
              {ents.map((e) => {
                const c = data.rows?.[rk]?.[e.name];
                const unc = isUncited(rk, e.name);
                const cites = unc ? [] : c?.citations ?? [];
                return (
                  <td key={e.name} className="px-3 py-2 break-words">
                    {c?.value ? <span className={`leading-snug ${unc ? "text-muted" : ""}`}>{c.value}</span> : <span className="text-muted italic">{c?.empty_reason || "not exported"}</span>}
                    {unc && c?.value && <span className="mt-1 block text-[10px] font-semibold uppercase tracking-wide text-warn" title="No page backs this cell yet">needs citation</span>}
                    <span className="mt-1 flex flex-wrap gap-1">
                      {cites.map((ev, j) => <CiteChip key={j} evidence={ev} label={shortCite(ev, j)} onPreview={onPreview} />)}
                      {c?.numeric_check ? <NumericPill check={c.numeric_check as NumericCheck} /> : null}
                      {!unc && !cites.length && c?.value && (
                        <span className="rounded border border-dashed border-warn/60 px-1 text-[10px] font-semibold text-warn" title="No citation attached to this cell">uncited</span>
                      )}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-3 py-2 text-[11px] text-muted">
        {nUncited
          ? <><span className="font-semibold text-warn">{nUncited} cell{nUncited > 1 ? "s" : ""} need{nUncited > 1 ? "" : "s"} a citation</span> ({uncitedList.map((u) => `${titles[u.row] ?? u.row} · ${u.entity}`).join("; ")}): shown muted, no page backs them yet.</>
          : <>Every cell carries a citation.</>}
        {" "}Source: labels.v2.{data.product} ({data.source_file ?? "product_v2"}).
      </p>
    </div>
  );
}

function baseDollars(f: V2Finding): number | null {
  const im = f.impact as Loose | undefined;
  if (typeof im?.dollars === "number") return im.dollars;
  const d = (im?.dRev ?? im?.dOI) as { base?: unknown } | undefined;
  return typeof d?.base === "number" ? d.base : null;
}

export function V2Findings({ data, onPreview }: { data: ProductV2; onPreview?: (e: Evidence | null) => void }) {
  const fs = data.findings ?? [];
  const gl = data.growth_limiter;
  return (
    <div className="space-y-3">
      {gl?.sentence && (
        <p className="rounded-md border-l-4 border-purple bg-surface-2 px-3 py-2 text-sm">
          <span className="font-semibold">What limits growth: </span>{gl.sentence}
          {gl.priced_in != null && <span className={`ml-2 rounded px-1.5 py-0.5 text-[10.5px] font-semibold ${gl.priced_in ? "bg-chip text-purple" : "bg-warn/15 text-warn"}`}>{gl.priced_in ? "priced in" : "not priced in"}</span>}
        </p>
      )}
      {fs.length ? (
        <ul className="space-y-2">
          {fs.map((f) => (
            <li key={f.id} className="rounded-md border border-line px-3 py-2 text-sm">
              <div className="flex items-start justify-between gap-3">
                <span className="leading-snug">{f.finding}{" "}
                  {(f.evidence ?? []).map((ev, j) => <Fragment key={j}><CiteChip evidence={ev} n={j + 1} onPreview={onPreview} />{" "}</Fragment>)}
                </span>
                <span className="flex shrink-0 items-center gap-1.5">
                  <NumericPill check={f.numeric_check as NumericCheck | undefined} />
                  {f.confidence && <ConfPill level={f.confidence} />}
                </span>
              </div>
              {f.impact?.formula && (
                <p className="mt-1 font-mono text-[11px] text-muted leading-snug">
                  {baseDollars(f) != null ? <span className="text-fg font-semibold">{money(baseDollars(f))} base · </span> : null}{f.impact.formula}
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-muted">No product finding is tied to this label table (labels.v2.{data.product}.findings is empty).</p>}
    </div>
  );
}
