import { useState } from "react";
import type { ReactNode } from "react";
import type { Company, Comparison, ComparisonRow } from "../../lib/types";
import { ConfPill } from "../ConfPill";
import { Flag, Src, drugName, isNum, makerOf, str } from "./util";

// Side-by-side label/pricing table: product vs each rival, every cell with its source note.

type Cell = { value?: unknown; source?: string; text?: string; confidence?: string };

const usd = (x: number) => `$${x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function get(rows: ComparisonRow[], field: string, slug: string): Cell | undefined {
  return rows.find((r) => r.field === field)?.values?.[slug] as Cell | undefined;
}

export function ComparisonTable({ comp, company }: { comp: Comparison; company: Company }) {
  const [showUses, setShowUses] = useState(false);
  const [showBox, setShowBox] = useState(false);
  const rows = comp.rows ?? [];
  const drugs = [comp.product, ...(comp.rivals ?? [])];
  const doseMax = Math.max(1, ...drugs.map((d) => get(rows, "dosing_frequency_per_year", d)?.value).filter(isNum));

  // CMS fact sheet / gtn_exposure MFP, used to flag when the label table's MFP differs.
  const mfpOther = (slug: string): { v: number; src: string } | null => {
    const cut = (company.ira_cut_check ?? []).find((r) => String(r.drug ?? "").toLowerCase() === slug);
    if (cut && isNum(cut.mfp_usd_30day)) return { v: cut.mfp_usd_30day, src: `CMS fact sheet IPAY ${cut.ipay ?? ""} p.${cut.page ?? "?"}` };
    const g = (company.gtn_exposure ?? []).find((r) => r.drug === slug);
    if (g && isNum(g.ira_mfp_per_30day)) return { v: g.ira_mfp_per_30day, src: "gtn_exposure.csv (CMS MFP)" };
    return null;
  };

  type Line = { key: string; label: ReactNode; cell: (slug: string) => ReactNode };

  const lines: Line[] = [
    {
      key: "uses",
      label: (
        <>
          Approved uses
          <button type="button" onClick={() => setShowUses((s) => !s)} className="mt-1 block text-[11px] font-semibold text-purple hover:underline" aria-expanded={showUses}>
            {showUses ? "collapse" : "show all"}
          </button>
        </>
      ),
      cell: (s) => {
        const n = get(rows, "indications_count", s);
        const list = get(rows, "indications", s);
        const items = Array.isArray(list?.value) ? (list!.value as unknown[]).map(String) : [];
        if (n?.value == null && !items.length) return <Missing src={n?.source ?? list?.source} />;
        return (
          <>
            <div className="font-semibold tnum">{String(n?.value ?? items.length)} uses</div>
            {items.length > 0 && (
              <ul className="mt-1 space-y-0.5 text-[12px] text-fg/90 list-disc pl-4">
                {(showUses ? items : items.slice(0, 2)).map((t, i) => <li key={i}>{t}</li>)}
                {!showUses && items.length > 2 && <li className="list-none -ml-4 text-muted">+{items.length - 2} more</li>}
              </ul>
            )}
            <Src>{n?.source ?? list?.source}</Src>
          </>
        );
      },
    },
    {
      key: "boxed",
      label: (
        <>
          Boxed warning
          <button type="button" onClick={() => setShowBox((s) => !s)} className="mt-1 block text-[11px] font-semibold text-purple hover:underline" aria-expanded={showBox}>
            {showBox ? "collapse" : "show text"}
          </button>
        </>
      ),
      cell: (s) => {
        const c = get(rows, "boxed_warning", s);
        const v = str(c?.value);
        if (!v) return <Missing src={c?.source} />;
        const yes = /^yes/i.test(v);
        const text = v.replace(/^yes:\s*/i, "");
        return (
          <>
            {yes ? <Flag tone="bad">Boxed warning</Flag> : <Flag tone="good">No boxed warning</Flag>}
            {yes && <p className={`mt-1 text-[12px] text-fg/90 ${showBox ? "" : "line-clamp-2"}`}>{text}…</p>}
            <Src>{c?.source}</Src>
          </>
        );
      },
    },
    {
      key: "rems",
      label: "REMS",
      cell: (s) => {
        const c = get(rows, "rems", s);
        if (typeof c?.value !== "boolean") return <Missing src={c?.source} />;
        return <>{c.value ? <Flag tone="bad">REMS required</Flag> : <Flag tone="good">No REMS</Flag>}<Src>{c.source}</Src></>;
      },
    },
    {
      key: "dose",
      label: "Doses per year",
      cell: (s) => {
        const c = get(rows, "dosing_frequency_per_year", s);
        if (!isNum(c?.value)) return <Missing src={c?.source} />;
        const own = s === comp.product;
        return (
          <>
            <div className="flex items-center gap-2">
              <span className="relative h-2 w-16 shrink-0 rounded-full bg-line overflow-hidden" aria-hidden="true">
                <span className={`absolute inset-y-0 left-0 rounded-full ${own ? "bg-purple" : "bg-frog-grey"}`} style={{ width: `${(c!.value as number) / doseMax * 100}%` }} />
              </span>
              <span className="font-mono text-[12px] tnum">{c!.value as number}/yr</span>
            </div>
            {c?.text && <div className="text-[12px] text-muted mt-0.5">{c.text}</div>}
            <Src>{c?.source}</Src>
          </>
        );
      },
    },
    {
      key: "route",
      label: "Route",
      cell: (s) => {
        const c = get(rows, "route", s);
        return str(c?.value) ? <><span>{String(c!.value).replace(/\//g, " / ")}</span><Src>{c?.source}</Src></> : <Missing src={c?.source} />;
      },
    },
    {
      key: "excl",
      label: (
        <>
          Exclusivity
          <span className="block text-[10px] font-normal normal-case tracking-normal text-muted mt-0.5">company-stated first, FDA data second</span>
        </>
      ),
      cell: (s) => {
        const cs = get(rows, "exclusivity_company_stated", s);
        const fda = get(rows, "exclusivity_fda_estimate", s);
        return (
          <div className="space-y-1.5">
            <div>
              <div className="text-[11px] text-muted">Company-stated</div>
              {str(cs?.value) ? <span className="font-mono tnum">{String(cs!.value)}</span> : <span className="text-muted italic">not in this export</span>}
              <Src>{cs?.value == null ? "company_stated_loe.jsonl not in checkout" : cs?.source}</Src>
            </div>
            <div>
              <div className="text-[11px] text-muted">FDA data</div>
              {str(fda?.value) ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="font-mono tnum">{String(fda!.value)}</span>
                  <Flag tone="neutral" dashed>estimate</Flag>
                </span>
              ) : <span className="text-muted italic">not in this export</span>}
              <Src>{fda?.source ? "latest Orange/Purple Book date: lower bound, not generic entry" : undefined}</Src>
            </div>
          </div>
        );
      },
    },
    {
      key: "generic",
      label: "Generic / biosimilar",
      cell: (s) => {
        const c = get(rows, "generic_or_biosimilar_status", s);
        return str(c?.value) ? <><span>{String(c!.value)}</span><Src>{c?.source}</Src></> : <Missing src={c?.source} />;
      },
    },
    {
      key: "ira",
      label: "IRA status + MFP",
      cell: (s) => {
        const st = get(rows, "ira_status", s);
        const m = get(rows, "mfp_per_30day", s);
        const sel = /selected/i.test(String(st?.value ?? "")) && !/not selected/i.test(String(st?.value ?? ""));
        const other = mfpOther(s);
        const differs = other && isNum(m?.value) && Math.abs(other.v - (m!.value as number)) > 0.5;
        return (
          <>
            {str(st?.value) ? (
              <div className="flex flex-wrap items-center gap-1.5">
                {sel ? <Flag tone="warn">Selected</Flag> : <Flag tone="neutral">Not selected</Flag>}
                <span className="text-[12px]">{String(st!.value).replace(/^Selected\s*/i, "").replace(/^Not selected$/i, "").replace(/,?\s*MFP \$[\d,.]+\/30 days/i, "")}</span>
              </div>
            ) : <Missing src={st?.source} />}
            {isNum(m?.value) && <div className="mt-0.5 font-mono text-[12px] tnum">MFP {usd(m!.value as number)} / 30 days</div>}
            <Src>{st?.source}</Src>
            {differs && (
              <div className="mt-1 text-[11px] text-warn">
                {other!.src}: {usd(other!.v)} / 30 days. Prefer this; the label-table MFP differs.
              </div>
            )}
          </>
        );
      },
    },
    {
      key: "partd",
      label: "Medicare spend (latest)",
      cell: (s) => {
        const c = get(rows, "partd_spend_latest", s);
        const v = str(c?.value);
        if (!v) return <Missing src={c?.source ?? "medicare_partd_spending.csv"} />;
        const [head, ...rest] = v.split(";").map((x) => x.trim());
        const m = head.match(/^(Part [BD] \d{4}):\s*(.*)$/);
        return (
          <>
            {m ? <><div className="text-[11px] text-muted">{m[1]}</div><div className="text-[12px] tnum">{m[2]}</div></> : <div className="text-[12px] tnum">{head}</div>}
            {rest.map((r, i) => <div key={i} className="text-[12px] text-muted tnum">{r}</div>)}
            <Src>{c?.source}</Src>
          </>
        );
      },
    },
    {
      key: "gtn",
      label: "Gross-to-net exposure",
      cell: (s) => {
        const c = get(rows, "gtn_exposure_call", s);
        const v = str(c?.value);
        if (!v) return <Missing src="data/moat/verified/pricing/gtn_exposure.csv" />;
        return (
          <>
            <div className="mb-1"><ConfPill level={c?.confidence} /></div>
            <div className="text-[12px]">{v}</div>
            <Src>{c?.source}</Src>
          </>
        );
      },
    },
  ];


  return (
    <div className="overflow-x-auto rounded-md border border-line bg-surface">
      <table className="w-full border-collapse text-[13px] table-fixed" style={{ minWidth: 120 + drugs.length * 150 }}>
        <caption className="sr-only">{drugName(comp.product)} vs rivals, label and pricing fine print</caption>
        <colgroup>
          <col style={{ width: 120 }} />
          {drugs.map((d) => <col key={d} />)}
        </colgroup>
        <thead className="bg-surface-2">
          <tr>
            <th scope="col" className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted border-b border-line">Field</th>
            {drugs.map((d, i) => {
              const maker = i === 0 ? company.ticker : makerOf(company, d);
              return (
                <th key={d} scope="col" className={`px-3 py-2 text-left border-b border-line align-bottom ${i === 0 ? "border-t-[3px] border-t-purple" : "border-t-[3px] border-t-frog-grey"}`}>
                  <div className="text-[14px] font-bold">{drugName(d)}</div>
                  <div className="text-[11px] font-normal text-muted">{i === 0 ? `product · ${maker}` : `rival · ${maker ?? "maker not in export"}`}</div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {lines.map((l) => (
            <tr key={l.key} className="border-b border-line last:border-0">
              <th scope="row" className="px-3 py-2 text-left align-top text-[11px] font-semibold uppercase tracking-wide text-muted">{l.label}</th>
              {drugs.map((d, i) => (
                <td key={d} className={`px-3 py-2 align-top min-w-0 [overflow-wrap:anywhere] ${i === 0 ? "bg-chip/40" : ""}`}>{l.cell(d)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Missing({ src }: { src?: string }) {
  return <><span className="text-muted italic">not in this export</span><Src>{src}</Src></>;
}
