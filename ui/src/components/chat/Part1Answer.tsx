import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Evidence, NumericCheck, Part1Company, Part1Finding, Part1Trace } from "../../lib/types";
import type { Part1State } from "../../lib/part1";
import { evidenceLabel, loadPart1Company, loadPart1Trace, part1CiteIndex, PART1_ROWS, resolver, scrub } from "../../lib/part1";
import { registerCites } from "../../lib/cites";
import { CiteChip } from "../CiteChip";
import { ConfPill } from "../ConfPill";
import { NumericPill } from "../NumericCheck";
import { Md } from "./Md";
import { SelectionCard } from "./Part1Selection";
import { Part1TraceView } from "./Part1Trace";

// The Part 1 answer, in the case's "Minimum expectations" layout: header with the 1 / 2 / 3 switcher,
// why this company beat the other nine, the Findings table, the Sharpest Needle, Product fine print,
// then the reasoning trace. All three companies load at once so the switcher swaps instantly.

type Cite = (n: number) => Evidence | undefined;

const ROW_LABEL: Record<string, string> = {
  "approved uses": "Approved uses",
  "boxed warnings and safety": "Boxed warnings and safety fine print",
  "dosing and convenience": "Dosing and convenience",
  "patent and exclusivity timeline": "Patent and exclusivity timeline",
  "pricing and gross-to-net": "Pricing and gross-to-net exposure",
};

const passed = (c?: NumericCheck | null) => !c || c.status !== "failed";

function Math_({ math, cite, check }: { math?: string | null; cite: Cite; check?: NumericCheck | null }) {
  const m = scrub(math);
  return (
    <>
      {m && (
        <details className="mt-1 rounded border border-line bg-surface-2 px-2 py-1 text-[12px]">
          <summary className="cursor-pointer select-none font-semibold text-purple">Show the math</summary>
          <pre className="mt-1 whitespace-pre-wrap break-words font-mono text-[11.5px] leading-relaxed"><Md md={m} cite={cite} /></pre>
        </details>
      )}
      {check && <div className="mt-1"><NumericPill check={check} compact /></div>}
    </>
  );
}

function Th({ children }: { children: ReactNode }) {
  return <th scope="col" className="px-2.5 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-muted">{children}</th>;
}

function FindingsTable({ c, ix }: { c: Part1Company; ix: Map<string, Evidence> }) {
  const rows = c.findings ?? [];
  if (!rows.length) return <p className="text-[13px] text-muted">No findings exported for {c.ticker}.</p>;
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="w-full min-w-[720px] border-collapse text-[13px]">
        <thead className="bg-surface-2"><tr><Th>#</Th><Th>Finding</Th><Th>Source</Th><Th>Impact</Th><Th>Peer comparison</Th><Th>Confidence</Th></tr></thead>
        <tbody>{rows.map((f) => <FindingRow key={f.n} f={f} ix={ix} />)}</tbody>
      </table>
    </div>
  );
}

function FindingRow({ f, ix }: { f: Part1Finding; ix: Map<string, Evidence> }) {
  const cite = resolver(ix, f.marker_map, f.cites);
  const s = f.source ?? {};
  const where = [scrub(s.doc_title), s.period && !(s.doc_title ?? "").includes(s.period) ? s.period : "", s.page != null && s.page !== "" ? `p. ${s.page}` : ""].filter(Boolean).join(", ");
  // The quote's chip: the finding's cite on the same page, else its first cite.
  const srcEv = (s.cite != null ? cite(Number(s.cite)) : undefined) ?? (f.cites ?? []).find((e) => s.page != null && String(e.page) === String(s.page)) ?? f.cites?.[0];
  const srcChip = srcEv ? (srcEv.cite_id && ix.get(srcEv.cite_id)) || evidenceLabel(srcEv) : undefined;
  const speaker = s.speaker ? scrub(s.speaker) : "";
  const imp = f.impact ?? {};
  return (
    <tr id={`p1-finding-${f.n}`} className="border-t border-line align-top">
      <td className="px-2.5 py-2 font-mono text-[12px] text-muted">{f.n}</td>
      <td className="px-2.5 py-2 min-w-[180px] leading-snug"><Md md={scrub(f.finding_marked ?? f.finding)} cite={cite} /></td>
      <td className="px-2.5 py-2 min-w-[150px]">
        <div className="font-semibold text-[12.5px]">{where || "Source not exported"}</div>
        {s.quote && !srcChip?.withheld && <p className="mt-0.5 text-[12px] italic text-muted break-words">{speaker ? `${speaker}: ` : ""}"{scrub(s.quote)}"</p>}
        {srcChip && <div className="mt-0.5"><CiteChip evidence={srcChip} label="source" /></div>}
      </td>
      <td className="px-2.5 py-2 min-w-[150px]">
        {passed(imp.numeric_check)
          ? <><Md md={scrub(imp.text_marked ?? imp.text) || "Not quantified"} cite={cite} /><Math_ math={imp.math_marked ?? imp.math} cite={cite} check={imp.numeric_check} /></>
          : <span className="text-muted">Withheld: failed the numeric gate</span>}
      </td>
      <td className="px-2.5 py-2 min-w-[120px]">{f.peer_marked || f.peer ? <Md md={scrub(f.peer_marked ?? f.peer)} cite={cite} /> : <span className="text-muted">No peer comparison exported</span>}</td>
      <td className="px-2.5 py-2"><ConfPill level={f.confidence} short /></td>
    </tr>
  );
}

function Needle({ c, ix }: { c: Part1Company; ix: Map<string, Evidence> }) {
  const nd = c.sharpest_needle;
  if (!nd) return null;
  const f = (c.findings ?? []).find((x) => Number(x.n) === Number(nd.finding_n));
  const fc = resolver(ix, f?.marker_map, f?.cites);
  const wc = resolver(ix, nd.marker_map ?? f?.marker_map, nd.cites ?? f?.cites);
  const why = scrub(nd.why_marked ?? nd.why);
  return (
    <section aria-label="Sharpest Needle" className="rounded-md border-l-4 border-purple bg-chip/60 px-4 py-3 space-y-1.5">
      <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-purple">Sharpest Needle{nd.finding_n != null ? ` · finding ${nd.finding_n}` : ""}</div>
      {f ? <p className="text-[15px] font-semibold leading-snug"><Md md={scrub(f.finding_marked ?? f.finding)} cite={fc} /></p> : <p className="text-[13px] text-muted">Needle finding {nd.finding_n ?? "?"} is not in the findings table.</p>}
      {why && <p className="text-[13.5px] text-muted"><span className="font-semibold text-fg">Why: </span><Md md={why} cite={wc} /></p>}
    </section>
  );
}

function ProductBlock({ c, ix }: { c: Part1Company; ix: Map<string, Evidence> }) {
  const p = c.product_table;
  if (!p) return <p className="text-[13px] text-muted">No product table exported for {c.ticker}.</p>;
  const cols = [p.product, ...(p.rivals ?? [])];
  const byRow = new Map((p.rows ?? []).map((r) => [r.row, r]));
  const tie = p.financial_tie, gl = p.growth_limiter, pi = p.priced_in;
  const call = (pi?.call ?? "").toLowerCase();
  return (
    <section aria-label="Product fine print" className="space-y-3">
      <h3 className="text-[16px] font-semibold">Product fine print: {p.product}{p.rivals?.length ? <span className="font-normal text-muted"> vs {p.rivals.join(", ")}</span> : null}</h3>
      <div className="overflow-x-auto rounded-md border border-line">
        <table className="w-full border-collapse text-[13px]" style={{ minWidth: `${160 + cols.length * 190}px` }}>
          <thead className="bg-surface-2"><tr><Th>&nbsp;</Th>{cols.map((x, i) => <Th key={i}>{x}</Th>)}</tr></thead>
          <tbody>
            {PART1_ROWS.map((rk) => {
              const r = byRow.get(rk);
              return (
                <tr key={rk} className="border-t border-line align-top">
                  <th scope="row" className="px-2.5 py-2 text-left text-[12px] font-semibold w-[160px]">{ROW_LABEL[rk]}</th>
                  {cols.map((col, j) => {
                    const cell = r?.cells?.[col];
                    const txt = scrub(cell?.text_marked ?? cell?.text);
                    const needs = !txt || cell?.status === "needs citation" || /^needs citation\.?$/i.test(scrub(cell?.text).trim());
                    return (
                      <td key={j} title={needs && cell?.note ? cell.note : undefined} className={`px-2.5 py-2 leading-snug ${j === 0 ? "bg-chip/30" : ""}`}>
                        {needs ? <span className="text-muted italic">{cell ? "needs citation" : "not exported"}</span> : <Md md={txt} cite={resolver(ix, cell?.marker_map, cell?.cites)} />}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {tie && (scrub(tie.text_marked ?? tie.text)) && (
        <div className="space-y-1">
          <h4 className="text-[13px] font-semibold uppercase tracking-wide text-muted">Tie to the numbers</h4>
          {passed(tie.numeric_check) ? (
            <div className="text-[14px] leading-relaxed">
              <Md md={scrub(tie.text_marked ?? tie.text)} cite={resolver(ix, tie.marker_map, tie.cites)} />
              <Math_ math={tie.math_marked ?? tie.math} cite={resolver(ix, tie.marker_map, tie.cites)} check={tie.numeric_check} />
            </div>
          ) : <p className="text-[13px] text-muted">Withheld: failed the numeric gate</p>}
        </div>
      )}
      {gl && scrub(gl.sentence_marked ?? gl.sentence) && (
        <p className="text-[14px] leading-relaxed"><span className="font-semibold">What limits growth: </span><Md md={scrub(gl.sentence_marked ?? gl.sentence)} cite={resolver(ix, gl.marker_map, gl.cites)} />{gl.numeric_check && <> <NumericPill check={gl.numeric_check} compact /></>}</p>
      )}
      {pi && (
        <p className="text-[14px] leading-relaxed">
          <span className="font-semibold">Priced in? </span>
          {call && call !== "untestable" && (
            <span className={`mr-1.5 inline-block rounded-full border px-2 py-px align-middle text-[11px] font-bold uppercase tracking-wide ${call === "not priced in" ? "border-warn/50 bg-warn/10 text-warn" : "border-line bg-surface-2 text-fg"}`}>{call}</span>
          )}
          <Md md={scrub(pi.text_marked ?? pi.text) || (call === "untestable" ? "Not testable: no consensus estimate is cited." : "")} cite={resolver(ix, pi.marker_map, pi.cites)} />
        </p>
      )}
    </section>
  );
}

export interface FollowChip { key: string; label: string; onClick: () => void }

export function Part1Answer({ part1, instant, nameOf, followFor, startTicker }: {
  part1: Part1State; instant: boolean; nameOf: (t: string) => string;
  /** ask_next chips for a ticker (the memo prompts for that company). */
  followFor: (t: string) => FollowChip[];
  startTicker?: string;
}) {
  const picked = part1.index?.picked ?? [];
  const [active, setActive] = useState<string>(startTicker && picked.includes(startTicker) ? startTicker : picked[0] ?? "");
  const [cos, setCos] = useState<Map<string, Part1Company | Error>>(new Map());
  const [trs, setTrs] = useState<Map<string, Part1Trace | Error>>(new Map());
  const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [stage, setStage] = useState(instant || reduce ? 2 : 0);
  const topRef = useRef<HTMLDivElement>(null);

  // Load all three company files at once (instant swap); traces load with them.
  useEffect(() => {
    const prefix = part1.prefix;
    if (!prefix) return;
    let live = true;
    for (const t of picked) {
      loadPart1Company(prefix, t).then((c) => live && setCos((m) => new Map(m).set(t, { ...c, ticker: c?.ticker ?? t })), (e) => live && setCos((m) => new Map(m).set(t, e as Error)));
      loadPart1Trace(prefix, t).then((x) => live && setTrs((m) => new Map(m).set(t, x)), (e) => live && setTrs((m) => new Map(m).set(t, e as Error)));
    }
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [part1.prefix, picked.join(",")]);

  const co = cos.get(active);
  const company = co && !(co instanceof Error) ? co : null;
  const tr = trs.get(active);
  const trace = tr && !(tr instanceof Error) ? tr : null;
  const ix = useMemo(() => part1CiteIndex(company), [company]);
  useEffect(() => { registerCites([...ix.values()]); }, [ix]);

  // Header and Findings first, then the rest at once.
  useEffect(() => {
    if (stage >= 2 || !company) return;
    const t = window.setTimeout(() => setStage(2), 700);
    return () => window.clearTimeout(t);
  }, [stage, company]);

  const goFinding = (n: number) => {
    const el = document.getElementById(`p1-finding-${n}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("bg-chip");
    window.setTimeout(() => el.classList.remove("bg-chip"), 1400);
  };

  const name = company?.name ?? nameOf(active);
  const follow = [
    ...picked.filter((t) => t !== active).map((t) => ({ key: `co:${t}`, label: `Show pick ${picked.indexOf(t) + 1}: ${nameOf(t)} (${t})`, onClick: () => { setActive(t); topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); } })),
    ...followFor(active),
  ];

  return (
    <div ref={topRef} className="min-w-0 space-y-5 text-[15px] leading-relaxed" onClick={() => { if (stage < 2) setStage(2); }}>
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-purple">Financial forensics</div>
          <h2 className="text-[22px] font-semibold leading-tight">{name} <span className="font-mono text-[15px] text-muted">{active}</span></h2>
        </div>
        {picked.length > 1 && (
          <div role="tablist" aria-label="Picked companies" className="ml-auto inline-flex rounded-full border border-line bg-surface p-0.5">
            {picked.map((t, i) => (
              <button key={t} type="button" role="tab" aria-selected={t === active} onClick={(e) => { e.stopPropagation(); setActive(t); }}
                className={`rounded-full px-3 py-1 text-[12.5px] font-semibold ${t === active ? "bg-purple text-white dark:bg-purple-deep" : "text-muted hover:text-purple"}`}>
                {i + 1} <span className="font-mono">{t}</span>
              </button>
            ))}
          </div>
        )}
        {part1.sample && <p role="note" title={part1.index?.sample_note} className="w-full text-[12px] text-muted">Sample data: the blind reasoning pass has not run yet</p>}
      </header>

      {co instanceof Error && <p role="alert" className="text-[14px] text-bad">Could not load data/part1/{active}.json.</p>}
      {!co && <p role="status" className="text-[14px] text-muted">Loading the cited answer…</p>}

      {company && (
        <>
          {part1.selection && <SelectionCard selection={part1.selection} ticker={active} nameOf={nameOf} seal={part1.index?.sealed} />}
          <section aria-label="Findings" className="space-y-2">
            <h3 className="text-[16px] font-semibold">Findings</h3>
            <FindingsTable c={company} ix={ix} />
          </section>
          {stage >= 2 ? (
            <>
              <Needle c={company} ix={ix} />
              <ProductBlock c={company} ix={ix} />
              {trace
                ? <Part1TraceView trace={trace} sample={part1.sample} onFinding={goFinding} />
                : tr instanceof Error ? <p className="text-[13px] text-muted">Reasoning trace not exported (data/part1/{active}_trace.json).</p> : null}
            </>
          ) : <button type="button" onClick={() => setStage(2)} className="no-print text-[11px] text-muted underline">Show all</button>}
        </>
      )}

      {stage >= 2 && follow.length > 0 && (
        <div className="no-print flex flex-wrap gap-2" aria-label="Ask next">
          {follow.map((f) => (
            <button key={f.key} type="button" onClick={(e) => { e.stopPropagation(); f.onClick(); }}
              className="rounded-full border border-purple/40 bg-surface px-3 py-1.5 text-[13px] text-purple hover:bg-chip text-left">{f.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
