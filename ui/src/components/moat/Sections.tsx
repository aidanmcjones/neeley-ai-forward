import type { Meta, MoatTable } from "../../lib/types";
import { money, num } from "../../lib/format";
import { DataTable, KpiTile, Panel } from "..";
import type { Column } from "..";
import { Pill, SourceNote, statusTone } from "../proof/common";

// Moat screen sections: headline tiles, pipeline strip, tables inventory, corpus trust, onboarding.

type Corpus = NonNullable<Meta["corpus"]> & {
  transcripts_graded?: number; transcript_grades?: Record<string, number>; source_quality?: Record<string, number>;
  doc_types?: Record<string, number>; drugs_with_label?: number;
};

export function MoatTiles({ meta, aiWrong }: { meta: Meta | null; aiWrong?: number }) {
  const c = (meta?.corpus ?? {}) as Corpus;
  const moat = meta?.moat ?? {};
  const tables = moat.tables ?? [];
  const rows = tables.reduce((s, t) => s + (t.rows ?? 0), 0);
  const status = Object.values(moat.status ?? {});
  const verified = status.filter((s) => (s[1] ?? "").toLowerCase() === "verified").length;
  const third = typeof c.transcripts === "number" && typeof c.transcripts_official === "number" ? c.transcripts - c.transcripts_official : null;
  const wrong = aiWrong ?? (typeof moat.ai_wrong_count === "number" ? (moat.ai_wrong_count as number) : null);
  return (
    <div className="grid grid-cols-4 gap-3">
      <KpiTile hot label="Source documents" value={num(c.docs)} footnote="meta.json · corpus.docs" />
      <KpiTile label="Pages, numbered as printed" value={num(c.pages)} footnote="meta.json · corpus.pages" />
      <KpiTile label="Companies + rival makers" value={`${num(c.companies)} + ${num(c.peers)}`} footnote="meta.json · corpus" />
      <KpiTile label="Drugs" value={num(c.drugs)} footnote={`${num(c.drugs_with_label)} with a DailyMed label`} />
      <KpiTile label="Call transcripts" value={num(c.transcripts)} footnote={`${num(c.transcripts_official)} official · ${num(third)} third-party`} />
      <KpiTile label="Derived tables" value={num(tables.length)} footnote={`${num(rows)} rows · moat.tables`} />
      <KpiTile label="Streams verified" value={`${verified}/${status.length}`} footnote="meta.json · moat.status" />
      <KpiTile label="AI-wrong cases logged" value={num(wrong)} footnote="data/moat/verify/ai_wrong.jsonl" />
    </div>
  );
}

export function PipelineStrip({ meta }: { meta: Meta | null }) {
  const stages = meta?.moat?.stages ?? [];
  const bar: Record<string, string> = { good: "bg-good", teal: "bg-teal", bad: "bg-bad", warn: "bg-warn", purple: "bg-purple", grey: "bg-frog-grey" };
  return (
    <Panel title="Data pipeline" meta={`${stages.filter((s) => s[1] === "done").length}/${stages.length} stages done`}>
      <div className="grid gap-2.5" style={{ gridTemplateColumns: `repeat(${Math.max(1, stages.length)}, minmax(0, 1fr))` }}>
        {stages.map(([name, status, text], i) => (
          <div key={i} className="relative rounded-lg border border-line bg-surface px-3 pt-3.5 pb-3 overflow-hidden">
            <span className={`absolute inset-x-0 top-0 h-1 ${bar[statusTone(status)]}`} aria-hidden="true" />
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-[13.5px] font-bold leading-tight">{name}</h3>
              <Pill tone={statusTone(status)}>{status}</Pill>
            </div>
            <p className="mt-1.5 text-[11.5px] text-muted leading-snug">{text}</p>
          </div>
        ))}
      </div>
      <SourceNote>meta.json · moat.stages (data/moat/progress.json, as of {meta?.moat?.as_of?.slice(0, 16).replace("T", " ") ?? "n/a"} UTC; stage notes are as the collectors wrote them)</SourceNote>
    </Panel>
  );
}

export function TablesInventory({ meta }: { meta: Meta | null }) {
  const tables = meta?.moat?.tables ?? [];
  const total = tables.reduce((s, t) => s + (t.rows ?? 0), 0);
  const cols: Column<MoatTable>[] = [
    { key: "name", header: "Table", width: "19%", render: (r) => <span className="font-mono text-[12px] font-semibold break-all">{r.name}</span> },
    { key: "rows", header: "Rows", align: "right", width: "8%", render: (r) => <span className="font-mono">{num(r.rows)}</span> },
    { key: "what", header: "What it is", width: "36%", render: (r) => <span className="text-[12.5px]">{r.what ?? "n/a"}</span> },
    { key: "list_or_net", header: "List or net", width: "14%", render: (r) => r.list_or_net ? <span className="text-[12px]">{r.list_or_net}</span> : <span className="text-muted">·</span> },
    { key: "source", header: "Source", width: "23%", render: (r) => r.source
      ? <span className="font-mono text-[10.5px] text-muted break-all line-clamp-2" title={r.source}>{r.source}</span>
      : <span className="text-[11px] text-muted">derived (see table)</span> },
  ];
  return (
    <Panel title="Derived tables inventory" meta={`${tables.length} tables · ${num(total)} rows`}>
      <p className="text-[13px] text-muted mb-2">Every row carries <code className="font-mono text-[12px]">source</code> and <code className="font-mono text-[12px]">source_row</code>; a second model pass re-checked each table against its source (data/moat/verified). Click a header to sort.</p>
      <DataTable columns={cols} rows={tables} rowKey={(r) => r.name} maxHeight={520} initialSort={{ key: "rows", dir: "desc" }} dense caption="Derived tables with row counts and sources" />
      <SourceNote>meta.json · moat.tables (data/moat/tables/*.csv)</SourceNote>
    </Panel>
  );
}

function ShareBar({ parts }: { parts: { label: string; n: number; cls: string; note?: string }[] }) {
  const total = parts.reduce((s, p) => s + p.n, 0) || 1;
  return (
    <div>
      <div className="flex h-3 rounded overflow-hidden gap-[2px] bg-surface" aria-hidden="true">
        {parts.map((p) => <i key={p.label} className={`${p.cls} h-full first:rounded-l last:rounded-r`} style={{ width: `${(100 * p.n) / total}%` }} />)}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[12px]">
        {parts.map((p) => (
          <span key={p.label} className="inline-flex items-center gap-1.5">
            <i className={`inline-block w-2.5 h-2.5 rounded-sm ${p.cls}`} aria-hidden="true" />
            <b>{p.label}</b> <span className="font-mono tnum">{num(p.n)}</span>
            <span className="text-muted font-mono tnum">({Math.round((100 * p.n) / total)}%)</span>
            {p.note && <span className="text-muted">{p.note}</span>}
          </span>
        ))}
      </div>
    </div>
  );
}

export function CorpusTrust({ meta }: { meta: Meta | null }) {
  const c = (meta?.corpus ?? {}) as Corpus;
  const g = c.transcript_grades ?? { A: 22, B: 5, C: 72 };
  const fromMeta = !!c.transcript_grades;
  const sq = c.source_quality;
  const known = (meta as { known_bad?: unknown } | null)?.known_bad;
  const docTypes = Object.entries(c.doc_types ?? {}).sort((a, b) => b[1] - a[1]);
  const maxDt = docTypes[0]?.[1] ?? 1;
  return (
    <Panel title="Corpus trust: what we will and will not quote">
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">Transcript grades ({num((g.A ?? 0) + (g.B ?? 0) + (g.C ?? 0))} graded)</h3>
            <div className="mt-2"><ShareBar parts={[
              { label: "A", n: g.A ?? 0, cls: "bg-purple", note: "quotable" },
              { label: "B", n: g.B ?? 0, cls: "bg-purple-bright", note: "quotable" },
              { label: "C", n: g.C ?? 0, cls: "bg-frog-grey", note: "context only" },
            ]} /></div>
            <p className="mt-1.5 text-[12.5px]">Quotability rule: only A or B quotes go on a slide. C transcripts (duplicates, no speaker names, garbled text) can inform a search but are never quoted.</p>
          </div>
          {sq && (
            <div>
              <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">Documents by source quality</h3>
              <div className="mt-2"><ShareBar parts={[
                { label: "Official", n: sq.official ?? 0, cls: "bg-purple", note: "filings, labels, company sites" },
                { label: "Third-party", n: sq.third_party ?? 0, cls: "bg-frog-grey", note: "transcript vendors" },
              ]} /></div>
            </div>
          )}
          <div className="rounded-md border border-line bg-surface-2 px-3 py-2 text-[12.5px]">
            <b>Page-marker rule:</b> cite the printed page number. Every corpus page keeps the number printed on it (e.g. file page 31, printed 26), so a judge can open the PDF and find the line.
          </div>
          <div className="text-[12.5px] text-muted">
            <b className="text-fg">Known-bad files:</b>{" "}
            {Array.isArray(known) && known.length
              ? (known as string[]).join(", ")
              : "the export does not list them individually. They are filtered at source: LLM-written summaries (for example fool.com) are rejected by the verifier, and C-grade transcripts are flagged unquotable."}
          </div>
        </div>
        <div>
          <h3 className="text-[12px] font-bold uppercase tracking-wide text-muted">Documents by type ({num(c.docs)})</h3>
          <ul className="mt-2 space-y-1">
            {docTypes.map(([k, n]) => (
              <li key={k} className="grid grid-cols-[150px_1fr_44px] items-center gap-2 text-[12px]">
                <span className="truncate" title={k}>{k.replace(/_/g, " ")}</span>
                <span className="h-2 rounded bg-line relative overflow-hidden" aria-hidden="true"><i className="absolute inset-y-0 left-0 rounded bg-purple" style={{ width: `${(100 * n) / maxDt}%` }} /></span>
                <span className="font-mono tnum text-right">{num(n)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <SourceNote>meta.json · corpus.transcript_grades{fromMeta ? "" : " (fallback 22/5/72)"}, corpus.source_quality, corpus.doc_types (data/corpus/manifest.csv)</SourceNote>
    </Panel>
  );
}

interface Pending { ticker: string; name?: string; packs?: { slug: string; label?: boolean; spend_2024?: number }[]; note?: string }

export function OnboardingCard({ meta }: { meta: Meta | null }) {
  const list = ((meta as { onboarding_pending?: Pending[] } | null)?.onboarding_pending ?? []);
  return (
    <Panel title="Any ticker, no hand configuration" meta={`${list.length} pending`}>
      {list.length === 0 && <p className="text-sm text-muted">meta.json has no onboarding_pending entries.</p>}
      {list.map((p) => (
        <div key={p.ticker} className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-2 items-start">
          <div>
            <div className="font-display text-[40px] leading-none tracking-wide text-purple-deep dark:text-purple">{p.ticker}</div>
            <div className="text-[12px] text-muted">{p.name}</div>
            <Pill tone="warn" className="mt-2">data collected, findings pending</Pill>
          </div>
          <div className="min-w-0">
            <code className="block font-mono text-[12.5px] bg-surface-2 rounded px-2.5 py-1.5 break-words">python -m agent.needle.onboard {p.ticker}</code>
            <p className="mt-1.5 text-[13px]">CIK, filings, products from XBRL, Orange/Purple Book, DailyMed label, rivals by class, outside data; no hand configuration.</p>
            {p.packs && p.packs.length > 0 && (
              <table className="mt-2 text-[12.5px] border-collapse">
                <thead><tr className="text-[10.5px] uppercase tracking-wide text-muted">
                  <th scope="col" className="text-left pr-5 font-semibold">Drug</th><th scope="col" className="text-left pr-5 font-semibold">Label</th><th scope="col" className="text-right font-semibold">Medicare spend 2024</th>
                </tr></thead>
                <tbody>{p.packs.map((k) => (
                  <tr key={k.slug}>
                    <td className="pr-5 font-mono">{k.slug}</td>
                    <td className="pr-5">{k.label ? "DailyMed found" : "missing"}</td>
                    <td className="text-right font-mono tnum">{money(k.spend_2024)}</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
            {p.note && <p className="mt-2 text-[11.5px] text-muted">{p.note}</p>}
          </div>
        </div>
      ))}
      <SourceNote>meta.json · onboarding_pending (out/VRTX/case_set.json)</SourceNote>
    </Panel>
  );
}
