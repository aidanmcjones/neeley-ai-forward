import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Evidence, MemoBlock, MemoRecord } from "../../lib/types";
import { citeEvidence } from "../../lib/memos";
import { registerCites } from "../../lib/cites";
import { AiMark } from "../AiMark";
import { NumericPill } from "../NumericCheck";
import { Md, plainMd } from "./Md";

// One cached answer. format "chat" = assistant prose bubble; format "memo" = a paper document card
// with a TO / FROM / RE / DATE header. Both reveal with a short skippable typewriter.

const BLOCK_WEIGHT = 60; // chars a kpi/table/list "costs" in the reveal

function blockText(b: MemoBlock): string {
  if (b.type === "h") return b.text;
  if (b.type === "p" || b.type === "callout") return plainMd(b.md);
  return "";
}
function blockLen(b: MemoBlock) { return b.type === "h" || b.type === "p" || b.type === "callout" ? blockText(b).length : BLOCK_WEIGHT; }

/** Reveal progress in characters; `skip()` finishes at once. Reduced motion or `instant` = no animation. */
function useReveal(total: number, instant: boolean) {
  const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [shown, setShown] = useState(instant || reduce ? total : 0);
  const done = shown >= total;
  const raf = useRef<number>();
  useEffect(() => {
    if (instant || reduce || total === 0) { setShown(total); return; }
    const dur = Math.max(1500, Math.min(2500, total * 4));
    const t0 = performance.now();
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / dur);
      setShown(Math.round(total * k));
      if (k < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [total, instant, reduce]);
  const skip = () => { if (raf.current) cancelAnimationFrame(raf.current); setShown(total); };
  return { shown, done, skip };
}

const RULES: Record<string, string> = { template: "Drafted by rules, no model", decide_v2: "Valued by decide rules, no model", data: "Read from the data, no model" };

export function toMarkdown(m: MemoRecord): string {
  const out: string[] = [];
  const h = m.memo_header;
  if (m.format === "memo" && h) out.push(`**TO:** ${h.to ?? ""}  `, `**FROM:** ${h.from ?? ""}  `, `**RE:** ${h.re ?? ""}  `, `**DATE:** ${h.date ?? ""}`, "");
  else out.push(`**${m.prompt}**`, "");
  for (const b of m.blocks ?? []) {
    if (b.type === "h") out.push(`## ${b.text}`, "");
    else if (b.type === "p") out.push(b.md, "");
    else if (b.type === "callout") out.push(`> ${b.md}`, "");
    else if (b.type === "list") out.push(...b.items.map((x) => `- ${x}`), "");
    else if (b.type === "kpi") out.push(...b.items.map((x) => `- ${x.label}: ${x.value}${x.cite ? ` [${x.cite}]` : ""}`), "");
    else if (b.type === "math") out.push(`${b.label ? `**${b.label}**\n` : ""}\`\`\`\n${b.text}\n\`\`\`${b.cite ? ` [${b.cite}]` : ""}`, "");
    else if (b.type === "table") out.push(`| ${b.columns.join(" | ")} |`, `|${b.columns.map(() => " --- ").join("|")}|`, ...b.rows.map((r) => `| ${r.join(" | ")} |`), "");
  }
  const cites = m.cites ?? [];
  if (cites.length) {
    out.push("Sources", "");
    for (const c of cites) {
      const where = [c.doc_title, c.period, c.page != null ? `p. ${c.page}` : ""].filter(Boolean).join(", ");
      const tail = c.withheld ? " (quote withheld)" : String(c.cite_id ?? "").startsWith("row:") ? ` (data row ${c.ref ?? c.cite_id})${c.quote ? `: "${c.quote}"` : ""}` : c.derived_from?.length ? ` (derived from ${c.derived_from.join(", ")})` : c.quote ? `: "${c.quote}"` : "";
      out.push(`[${c.n}] ${where}${tail}${c.url && !c.withheld ? ` ${c.url}` : ""}`);
    }
  }
  return out.join("\n");
}

export function Answer({ memo, instant, onAsk, labelFor }: {
  memo: MemoRecord; instant: boolean; onAsk: (id: string) => void; labelFor: (id: string) => string | null;
}) {
  const cites = memo.cites ?? [];
  const evs = useMemo(() => new Map(cites.map((c) => [c.n, citeEvidence(c, cites)] as const)), [cites]);
  useEffect(() => { registerCites([...evs.values()]); }, [evs]);
  const cite = (n: number): Evidence | undefined => evs.get(n);
  const blocks = memo.blocks ?? [];
  const lens = blocks.map(blockLen);
  const total = lens.reduce((a, b) => a + b, 0);
  const { shown, done, skip } = useReveal(total, instant);
  const [copied, setCopied] = useState(false);
  const isMemo = memo.format === "memo";
  const cardRef = useRef<HTMLDivElement>(null);

  const rendered: ReactNode[] = [];
  let at = 0;
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];
    if (at >= shown && !done) break;
    const partial = !done && at + lens[i] > shown;
    const cut = shown - at;
    rendered.push(<Block key={i} b={b} cite={cite} partial={partial ? blockText(b).slice(0, cut) : null} memo={isMemo} />);
    at += lens[i];
  }

  const copy = async () => {
    try { await navigator.clipboard.writeText(toMarkdown(memo)); setCopied(true); window.setTimeout(() => setCopied(false), 1500); } catch { setCopied(false); }
  };
  const print = () => {
    skip();
    const el = cardRef.current;
    if (!el) return;
    el.querySelectorAll("details").forEach((d) => { d.open = true; }); // the printed memo shows its math
    const turn = el.closest("[data-turn]");
    el.classList.add("print-target");
    turn?.classList.add("print-turn");
    document.body.classList.add("print-one");
    const clean = () => { el.classList.remove("print-target"); turn?.classList.remove("print-turn"); document.body.classList.remove("print-one"); window.removeEventListener("afterprint", clean); };
    window.addEventListener("afterprint", clean);
    window.setTimeout(() => window.print(), 30);
  };

  const byModel = memo.generated_by && !RULES[memo.generated_by];
  const byline = (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[12px] text-muted">
      {byModel ? <AiMark label="Model-written" /> : <span>{RULES[memo.generated_by ?? "template"] ?? "Rules, no model"}</span>}
      <NumericPill check={memo.numeric_check} />
      <span className="no-print ml-auto flex gap-1.5">
        <button type="button" onClick={copy} className="rounded-md border border-line px-2 py-1 text-[12px] font-semibold text-fg hover:border-purple hover:text-purple">{copied ? "Copied" : "Copy as markdown"}</button>
        {isMemo && <button type="button" onClick={print} className="rounded-md border border-line px-2 py-1 text-[12px] font-semibold text-fg hover:border-purple hover:text-purple">Print</button>}
      </span>
    </div>
  );
  const follow = (memo.ask_next ?? []).map((id) => ({ id, label: labelFor(id) })).filter((x): x is { id: string; label: string } => !!x.label);
  const h = memo.memo_header;

  return (
    <div className="space-y-3">
      <div ref={cardRef} onClick={() => { if (!done) skip(); }}
        className={isMemo
          ? "memo-card rounded-lg border border-line bg-white dark:bg-surface text-fg shadow-card px-6 py-6 sm:px-9 sm:py-8 space-y-4"
          : "space-y-3 text-[15.5px] leading-relaxed"}
        aria-busy={!done}>
        {isMemo && (
          <header className="border-b-2 border-purple pb-3">
            <div className="mb-2 font-display text-[22px] tracking-wide text-purple-deep dark:text-purple">Memorandum</div>
            <dl className="grid grid-cols-[64px_1fr] gap-y-0.5 text-[13px]">
              {([["To", h?.to], ["From", h?.from], ["Re", h?.re], ["Date", h?.date]] as const).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="font-semibold uppercase tracking-wide text-[11px] text-muted pt-0.5">{k}</dt>
                  <dd className={k === "Re" ? "font-semibold" : ""}>{v || "n/a"}</dd>
                </div>
              ))}
            </dl>
          </header>
        )}
        {rendered}
        {!done && <button type="button" onClick={skip} className="no-print text-[11px] text-muted underline">Show all</button>}
        {done && isMemo && byline}
      </div>
      {done && !isMemo && byline}
      {done && follow.length > 0 && (
        <div className="no-print flex flex-wrap gap-2" aria-label="Ask next">
          {follow.map((f) => (
            <button key={f.id} type="button" onClick={() => onAsk(f.id)}
              className="rounded-full border border-purple/40 bg-surface px-3 py-1.5 text-[13px] text-purple hover:bg-chip text-left">{f.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function Block({ b, cite, partial, memo }: { b: MemoBlock; cite: (n: number) => Evidence | undefined; partial: string | null; memo: boolean }) {
  if (b.type === "h") return <h3 className={`font-semibold ${memo ? "text-[13px] uppercase tracking-[0.1em] text-purple-deep dark:text-purple pt-1" : "text-[16px]"}`}>{partial ?? b.text}</h3>;
  if (b.type === "p") {
    if (partial != null) return <p>{partial}</p>;
    return <>{b.md.split(/\n{2,}/).map((para, i) => <p key={i}><Md md={para} cite={cite} /></p>)}</>;
  }
  if (b.type === "callout") {
    const tone = b.tone === "warn" ? "border-warn/60 bg-warn/10" : b.tone === "ok" ? "border-good/50 bg-good/10" : "border-line bg-surface-2";
    return <div className={`rounded-md border-l-4 px-3 py-2 text-[14px] ${tone}`}>{partial ?? <Md md={b.md} cite={cite} />}</div>;
  }
  if (partial != null) return null;
  if (b.type === "kpi") {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {b.items.map((k, i) => (
          <div key={i} className="rounded-md border border-line bg-surface px-3 py-2 min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-muted truncate">{k.label}</div>
            <div className="mt-0.5 flex items-baseline gap-1.5">
              <span className={`leading-tight tnum text-purple-deep dark:text-purple ${String(k.value).length > 14 ? "text-[15px] font-semibold" : "font-display text-[28px] leading-none"}`}>{k.value}</span>
              {k.cite != null && <Md md={`[${k.cite}]`} cite={cite} />}
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (b.type === "table") {
    return (
      <div className="overflow-x-auto rounded-md border border-line">
        <table className="w-full border-collapse text-[13px] tnum">
          <thead className="bg-surface-2"><tr>{b.columns.map((c, i) => <th key={i} scope="col" className="px-2.5 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-muted">{c}</th>)}</tr></thead>
          <tbody>{b.rows.map((r, i) => <tr key={i} className="border-t border-line align-top">{r.map((cell, j) => <td key={j} className="px-2.5 py-1.5"><Md md={String(cell ?? "")} cite={cite} /></td>)}</tr>)}</tbody>
        </table>
      </div>
    );
  }
  if (b.type === "math") {
    return (
      <details className="rounded-md border border-line bg-surface-2 px-3 py-2 text-[13px]">
        <summary className="cursor-pointer select-none font-semibold text-purple">Show the math{b.label ? `: ${b.label}` : ""}</summary>
        <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-[12px] leading-relaxed">{b.text}</pre>
        {b.cite != null && <div className="mt-1"><Md md={`[${b.cite}]`} cite={cite} /></div>}
      </details>
    );
  }
  if (b.type === "list") return <ul className="list-disc pl-5 space-y-1">{b.items.map((x, i) => <li key={i}><Md md={x} cite={cite} /></li>)}</ul>;
  return null;
}
