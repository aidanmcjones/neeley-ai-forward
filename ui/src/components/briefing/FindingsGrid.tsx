import { MarkedSentence } from "../MarkedSentence";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { NumericPill, CiteChip, ConfPill, DataTable, FlagPills } from "..";
import type { Column } from "..";
import { money, z } from "../../lib/format";
import { impactView } from "../../lib/stance";
import type { Company, Evidence, Finding, Rejected } from "../../lib/types";

// Findings grid with filters. Rejected claims (company.rejected) show as struck rows when on.

export type GridRow =
  | { kind: "finding"; id: string; f: Finding }
  | { kind: "rejected"; id: string; r: Rejected };

const CONFS = ["high", "medium", "low"] as const;
const VERDICTS = [
  { key: "verified", label: "Verified", short: "Verified" },
  { key: "needs_human", label: "Needs human", short: "Held" },
  { key: "rejected", label: "Rejected", short: "Rejected" },
] as const;
type VerdictKey = (typeof VERDICTS)[number]["key"];

function verdictKey(v?: string): VerdictKey {
  const s = (v ?? "").toLowerCase();
  if (s.startsWith("verif")) return "verified";
  if (s.startsWith("reject")) return "rejected";
  return "needs_human";
}

const VERDICT_TONE: Record<VerdictKey, string> = { verified: "text-good", needs_human: "text-warn", rejected: "text-bad" };
const VERDICT_ICON: Record<VerdictKey, string> = { verified: "✓", needs_human: "?", rejected: "✕" };

function rejectedEvidence(r: Rejected): Evidence | undefined {
  const ev = (r as { evidence?: unknown }).evidence;
  return Array.isArray(ev) && ev[0] && typeof ev[0] === "object" ? { ...(ev[0] as Evidence), verdict: "rejected" } : undefined;
}

function Toggle({ on, onClick, children, title }: { on: boolean; onClick: () => void; children: ReactNode; title?: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      title={title}
      className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${on ? "border-purple bg-purple text-white dark:bg-purple-deep" : "border-line bg-surface text-muted hover:text-fg"}`}
    >
      {on ? "✓ " : ""}{children}
    </button>
  );
}

export function FindingsGrid({ company, selectedId, onSelect }: {
  company: Company; selectedId: string | null; onSelect: (f: Finding) => void;
}) {
  const [confs, setConfs] = useState<Set<string>>(new Set(CONFS));
  const [verdicts, setVerdicts] = useState<Set<VerdictKey>>(new Set<VerdictKey>(["verified", "needs_human"]));
  const [detector, setDetector] = useState("all");

  const detectors = useMemo(
    () => Array.from(new Set(company.findings.map((f) => f.detector ?? "other"))).sort(),
    [company],
  );

  // findings_table (when exported): the engine's ranked table, e.g. by dollar impact, with its rank_basis.
  const { order, tableBasis } = useMemo(() => {
    const ft = company.findings_table as unknown;
    const rowsT = Array.isArray(ft) ? ft : Array.isArray((ft as { rows?: unknown })?.rows) ? (ft as { rows: unknown[] }).rows : null;
    if (!rowsT) return { order: null as Map<string, number> | null, tableBasis: null as string | null };
    const m = new Map<string, number>();
    rowsT.forEach((r, i) => {
      const o = r as { finding_id?: string; id?: string; rank?: number };
      const id = o.finding_id ?? o.id;
      if (id) m.set(id, typeof o.rank === "number" ? o.rank : i + 1);
    });
    const basis = (ft as { rank_basis?: unknown })?.rank_basis ?? company.rank_basis;
    return { order: m, tableBasis: typeof basis === "string" && basis ? basis : "ranked by dollar impact" };
  }, [company]);

  const rows = useMemo<GridRow[]>(() => {
    const fs = [...company.findings]
      .filter((f) => confs.has((f.confidence ?? "").toLowerCase()) || (!f.confidence && confs.size === CONFS.length))
      .filter((f) => verdicts.has(verdictKey(f.verdict)))
      .filter((f) => detector === "all" || (f.detector ?? "other") === detector)
      .sort((a, b) => (order ? (order.get(a.id) ?? 1e9) - (order.get(b.id) ?? 1e9) : (b.score ?? 0) - (a.score ?? 0)))
      .map<GridRow>((f) => ({ kind: "finding", id: f.id, f }));
    const rej = verdicts.has("rejected")
      ? (company.rejected ?? []).map<GridRow>((r, i) => ({ kind: "rejected", id: `rej-${i}`, r }))
      : [];
    return [...fs, ...rej];
  }, [company, confs, verdicts, detector, order]);

  const flip = <T,>(set: Set<T>, v: T, put: (s: Set<T>) => void) => {
    const n = new Set(set);
    if (n.has(v)) n.delete(v); else n.add(v);
    put(n);
  };

  const cols: Column<GridRow>[] = [
    {
      key: "finding", header: "Finding",
      sortValue: (r) => (r.kind === "finding" ? r.f.finding : r.r.finding ?? ""),
      render: (r) => {
        const text = r.kind === "finding" ? r.f.finding : r.r.finding ?? "";
        return (
          <span className="block">
            <span title={r.kind === "rejected" ? `${text}\nRejected: ${r.r.reason ?? ""}` : text} className={`line-clamp-2 [overflow-wrap:anywhere] ${r.kind === "rejected" ? "line-through text-muted" : ""}`}>
              {r.kind === "finding" ? <MarkedSentence finding={r.f} /> : text}
            </span>
            {r.kind === "finding" && <FlagPills finding={r.f} className="mt-0.5" />}
            {r.kind === "rejected" && r.r.reason && <span className="mt-0.5 block text-[10.5px] text-bad/90 line-clamp-1" title={r.r.reason}>{r.r.reason}</span>}
          </span>
        );
      },
    },
    {
      key: "impact", header: "Impact $", align: "right",
      sortValue: (r) => (r.kind === "finding" ? impactView(r.f).dollars : null),
      render: (r) => {
        if (r.kind === "rejected") return <span className="text-muted">n/a</span>;
        const im = impactView(r.f);
        if (im.kind === "dollars") return <span className="font-mono" title={im.formula}>{money(im.dollars)}</span>;
        if (im.kind === "suspect") return <s className="font-mono text-muted" title={`${im.formula}\nSuspect: ${im.note ?? ""}`}>{money(im.dollars)}</s>;
        if (im.kind === "proxy") return <span className="text-[11px] text-muted" title={im.formula}>proxy</span>;
        if (r.f.not_quantified) return <span className="text-[11px] text-muted" title={r.f.not_quantified}>not quant.</span>;
        return <span className="text-muted">n/a</span>;
      },
    },
    {
      key: "z", header: "z", title: "Peer z", align: "right",
      sortValue: (r) => (r.kind === "finding" ? r.f.peer?.z ?? null : null),
      render: (r) => <span className="font-mono">{r.kind === "finding" && r.f.peer?.z != null ? z(r.f.peer.z).replace("z ", "") : <span className="text-muted">n/a</span>}</span>,
    },
    {
      key: "conf", header: "Conf.", title: "Confidence",
      sortValue: (r) => (r.kind === "finding" ? ({ high: 3, medium: 2, low: 1 } as Record<string, number>)[(r.f.confidence ?? "").toLowerCase()] ?? 0 : null),
      render: (r) => (r.kind === "finding" ? <ConfPill short level={r.f.confidence} /> : <span className="text-muted">n/a</span>),
    },
    {
      key: "obsc", header: "Obsc.", title: "Obscurity (vector.O)",
      sortValue: (r) => (r.kind === "finding" ? r.f.vector?.O ?? null : null),
      render: (r) => {
        const o = r.kind === "finding" ? r.f.vector?.O : undefined;
        if (o == null) return <span className="text-muted">n/a</span>;
        return (
          <span className="inline-flex items-center gap-1.5" title={r.kind === "finding" ? r.f.vector?.obscurity_note : undefined}>
            <span aria-hidden="true" className="relative h-1.5 w-7 rounded-full bg-line overflow-hidden">
              <span className="absolute inset-y-0 left-0 rounded-full bg-purple" style={{ width: `${Math.max(0, Math.min(1, o)) * 100}%` }} />
            </span>
            <span className="font-mono text-[11px]">{o.toFixed(2)}</span>
          </span>
        );
      },
    },
    {
      key: "verdict", header: "Verdict",
      sortValue: (r) => verdictKey(r.kind === "finding" ? r.f.verdict : "rejected"),
      render: (r) => {
        const k = verdictKey(r.kind === "finding" ? r.f.verdict : "rejected");
        return (
          <span className="inline-flex flex-col items-start gap-0.5">
            <span className={`whitespace-nowrap text-[11px] font-semibold ${VERDICT_TONE[k]}`} title={[VERDICTS.find((v) => v.key === k)!.label, r.kind === "rejected" ? r.r.reason : r.f.reason].filter(Boolean).join(": ")}>
              <span aria-hidden="true">{VERDICT_ICON[k]} </span>{VERDICTS.find((v) => v.key === k)!.short}
            </span>
            {r.kind === "finding" && <NumericPill check={r.f.numeric_check} compact />}
          </span>
        );
      },
    },
    {
      key: "src", header: "Src", title: "Sources", align: "right",
      sortValue: (r) => (r.kind === "finding" ? r.f.evidence?.length ?? 0 : 0),
      render: (r) => {
        if (r.kind === "rejected") {
          const ev = rejectedEvidence(r.r);
          return ev ? <CiteChip evidence={ev} label="1" /> : <span className="text-muted">0</span>;
        }
        const ev = r.f.evidence ?? [];
        if (!ev.length) return <span className="text-[11px] text-warn" title="No page quote; held for human review">0</span>;
        return <CiteChip evidence={{ ...ev[0], verdict: ev[0].verdict ?? r.f.verdict }} label={`${ev.length}`} />;
      },
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs" role="group" aria-label="Filter findings">
        <span className="flex items-center gap-1.5">
          <span className="font-semibold uppercase tracking-wide text-muted">Confidence</span>
          {CONFS.map((c) => <Toggle key={c} on={confs.has(c)} onClick={() => flip(confs, c, setConfs)}>{c}</Toggle>)}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="font-semibold uppercase tracking-wide text-muted">Verdict</span>
          {VERDICTS.map((v) => (
            <Toggle key={v.key} on={verdicts.has(v.key)} onClick={() => flip(verdicts, v.key, setVerdicts)}
              title={v.key === "rejected" ? `${company.rejected?.length ?? 0} rejected claims from companies/${company.ticker}.json` : undefined}>
              {v.label}
            </Toggle>
          ))}
        </span>
        <label className="flex items-center gap-1.5">
          <span className="font-semibold uppercase tracking-wide text-muted">Detector</span>
          <select value={detector} onChange={(e) => setDetector(e.target.value)} className="rounded border border-line bg-surface px-1.5 py-0.5 text-xs font-semibold">
            <option value="all">All ({company.findings.length})</option>
            {detectors.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <span className="ml-auto font-mono text-[11px] text-muted">{rows.length} rows · {tableBasis ?? "ranked by the engine"}</span>
      </div>
      <DataTable<GridRow>
        dense
        caption={`Findings for ${company.ticker}`}
        columns={cols}
        rows={rows}
        rowKey={(r) => r.id}
        selectedKey={selectedId}
        onSelect={(r) => { if (r.kind === "finding") onSelect(r.f); }}
        maxHeight={360}
        empty={`No findings match these filters (companies/${company.ticker}.json has ${company.findings.length}).`}
      />
    </div>
  );
}
