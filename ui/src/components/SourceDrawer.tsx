import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type React from "react";
import type { Evidence } from "../lib/types";
import { isWithheld, withheldReason } from "../lib/data";
import { derivedOperands, isConstructed, isDerived, isRowCite, pitchEvidence, pitchLine } from "../lib/cites";

// Global right-side source drawer. Any CiteChip calls useSource().open(evidence).
// Esc closes, focus is trapped while open and restored to the opener on close.

interface SourceCtx { open: (ev: Evidence) => void; close: () => void; current: Evidence | null }
const Ctx = createContext<SourceCtx>({ open: () => {}, close: () => {}, current: null });
export const useSource = () => useContext(Ctx);

export function SourceProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<Evidence | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const open = useCallback((ev: Evidence) => {
    opener.current = document.activeElement as HTMLElement | null;
    setCurrent(ev);
  }, []);
  const close = useCallback(() => {
    setCurrent(null);
    opener.current?.focus?.();
  }, []);
  const value = useMemo(() => ({ open, close, current }), [open, close, current]);
  return (
    <Ctx.Provider value={value}>
      {children}
      {current && <SourceDrawer evidence={current} onClose={close} />}
    </Ctx.Provider>
  );
}

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"]), input, select, textarea';

function Row({ k, children }: { k: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-2 py-1.5 border-b border-line last:border-0">
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted pt-0.5">{k}</dt>
      <dd className="text-sm min-w-0 break-words">{children}</dd>
    </div>
  );
}

function verdictTone(v?: string) {
  const s = (v ?? "").toLowerCase();
  if (s.startsWith("verif") || s === "pass" || s === "ok") return "text-good";
  if (s.startsWith("reject") || s === "fail") return "text-bad";
  return "text-warn";
}

export function SourceDrawer({ evidence: evRaw, onClose }: { evidence: Evidence; onClose: () => void }) {
  const ev = pitchEvidence(evRaw);
  const { open } = useSource();
  const ref = useRef<HTMLDivElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);

  useEffect(() => { closeBtn.current?.focus(); }, [ev]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); onClose(); return; }
      if (e.key !== "Tab" || !ref.current) return;
      const els = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!els.length) return;
      const first = els[0], last = els[els.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !ref.current.contains(active))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (active === last || !ref.current.contains(active))) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const label = ev.citation || [String(ev.doc_id ?? "").startsWith("row:") ? "" : ev.doc_id, ev.page != null ? `p. ${ev.printed || ev.page}` : ""].filter(Boolean).join(", ") || "Source";
  const figures = Array.isArray(ev.figures) ? ev.figures.map(String).filter(Boolean) : [];
  const ex = ev.excerpt;
  const hasExcerpt = !!(ex && (ex.before || ex.match || ex.after));
  const isCall = !!ev.speaker || /call|transcript/i.test(ev.doc_type ?? "");
  const withheld = isWithheld(ev);
  const vdetail = ev.verification?.detail;

  if (isRowCite(ev)) {
    const title = String(ev.doc_title || ev.citation || "Data row");
    const val = ev.value != null && ev.value !== "" ? String(ev.value) : null;
    return (
      <DrawerShell refEl={ref} closeBtn={closeBtn} onClose={onClose} label={title}>
        <dl>
          <Row k="Source">{title}</Row>
          {ev.row_ref && <Row k="Data row"><span className="font-mono text-xs break-all">{ev.row_ref}</span></Row>}
          {val && <Row k="Value"><span className="font-mono tnum">{val}</span></Row>}
          {ev.row_check && <Row k="Check"><span className="font-semibold text-good">{ev.row_check}</span></Row>}
        </dl>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">Row text</div>
          {ev.quote
            ? <blockquote className="rounded-md bg-surface-2 border border-line p-3 text-sm leading-relaxed whitespace-pre-wrap">{ev.quote}</blockquote>
            : <p className="text-sm text-muted">No row text exported for this cite.</p>}
        </div>
        <p className="text-xs text-muted">A data-row cite points at a value in the exported JSON (a table row, a score or a count), not at a printed page. The path above is the exact row it was read from.</p>
      </DrawerShell>
    );
  }

  if (!withheld && isDerived(ev)) {
    const ops = derivedOperands(ev);
    const title = String(ev.doc_title || ev.doc_label || ev.citation || ev.doc_id || "Derived figure");
    const val = ev.value != null && ev.value !== "" ? `${String(ev.value)}${ev.unit ? ` ${ev.unit}` : ""}` : null;
    return (
      <DrawerShell refEl={ref} closeBtn={closeBtn} onClose={onClose} label={title}>
        <dl>
          <Row k="Document">{title}</Row>
          {(ev.location || ev.printed || ev.page != null) && <Row k="Page"><span className="font-mono tnum">{ev.location || ev.printed || ev.page}</span></Row>}
          {val && <Row k="Value"><span className="font-mono tnum">{val}</span></Row>}
          {ev.derived_expr && <Row k="Computed as"><span className="font-mono text-xs">{ev.derived_expr}</span></Row>}
          <Row k="Derived from">
            <span className="flex flex-wrap gap-1">
              {ops.map((o, i) => o.ev
                ? <button key={o.id} type="button" onClick={() => open(o.ev!)} title={o.ev.citation ?? o.id}
                    className="font-mono text-[11px] rounded px-1 py-px bg-chip text-purple border border-purple/20 hover:bg-purple hover:text-white dark:hover:bg-purple-deep">[{String.fromCharCode(97 + i)}] {pitchLine(o.ev.citation) ?? pitchLine(o.ev.doc_title) ?? "operand"}</button>
                : <span key={o.id} className="font-mono text-[11px] text-muted" title="Operand not in this export">[{String.fromCharCode(97 + i)}] {o.id}</span>)}
            </span>
          </Row>
          <Row k="Verifier"><span className="font-semibold text-good">derived{ev.verification?.status && ev.verification.status !== "derived" ? ` (${ev.verification.status})` : ""}</span> <span className="text-muted text-xs">operands must pass their own checks</span></Row>
        </dl>
        <p className="text-sm text-muted">A derived figure has no quote of its own: it is computed from the operand citations above. Open each operand to see its page.</p>
      </DrawerShell>
    );
  }

  if (withheld) {
    const title = ev.doc_title || ev.doc_label as string || ev.citation || ev.doc_id || "Source";
    return (
      <DrawerShell refEl={ref} closeBtn={closeBtn} onClose={onClose} label={String(title)}>
        <dl>
          <Row k="Document">{String(title)}</Row>
          {ev.period && <Row k="Period">{ev.period}</Row>}
          {(ev.page != null || ev.printed || ev.location) && <Row k="Page"><span className="font-mono tnum">{ev.location || ev.printed || ev.page}</span></Row>}
          {ev.value != null && ev.value !== "" && <Row k="Value"><span className="font-mono tnum">{String(ev.value)}{ev.unit ? ` ${ev.unit}` : ""}</span></Row>}
          {ev.viewer_link && /^https?:|^\//.test(ev.viewer_link) && <Row k="Viewer"><a href={ev.viewer_link} target="_blank" rel="noreferrer" className="text-purple underline break-all">{/^https?:/.test(ev.viewer_link) ? "open the source dataset" : "open in the local viewer"}</a></Row>}
        </dl>
        <p className="rounded-md border border-dashed border-warn/60 px-3 py-2 text-sm">
          <span className="font-semibold text-warn">Quote withheld: {withheldReason(ev)}.</span>{" "}
          <span className="text-muted">{withheldReason(ev) === "licensed source"
            ? "Licensed data is used as a model input but its text and links are not published."
            : withheldReason(ev) === "machine-readable data row"
            ? "This is a machine-readable data row: the cited value is shown above; there is no printed page to quote."
            : ev.doc_type === "benchmark"
              ? "External benchmark input (team assumption source); it is not in the page-anchored corpus, so nothing could be checked against a page."
              : `The quote could not be confirmed on the cited page${vdetail ? ` (${vdetail})` : ""}, so the quote and links are not shown.`}</span>
        </p>
      </DrawerShell>
    );
  }

  return (
    <DrawerShell refEl={ref} closeBtn={closeBtn} onClose={onClose} label={label}>
          <dl>
            <Row k="Document">
              {ev.url ? (
                <a href={ev.url} target="_blank" rel="noreferrer" className="text-purple underline break-all">{ev.url}</a>
              ) : <span className="font-mono text-xs">{ev.doc_id ?? "n/a"}</span>}
            </Row>
            {(ev.page != null || ev.printed) && <Row k="Page"><span className="font-mono tnum">{ev.printed || ev.page}</span></Row>}
            {ev.speaker && <Row k="Speaker">{ev.speaker}</Row>}
            <Row k="Figures checked">
              {figures.length ? (
                <span className="flex flex-wrap gap-1">{figures.map((f, i) => <span key={i} className="font-mono text-xs bg-chip rounded px-1.5 py-0.5 tnum">{f}</span>)}</span>
              ) : <span className="text-muted">none listed</span>}
            </Row>
            <Row k="Verifier"><span className={`font-semibold ${verdictTone(ev.verdict || (ev.verification?.status && ev.verification.status !== "unverified" ? "verified" : ev.verification?.status))}`}>{ev.verdict || ev.verification?.status || "not recorded"}</span>{ev.verdict && ev.verification?.status ? <span className="text-muted text-xs"> · quote check: {ev.verification.status}</span> : null}</Row>
            {(isCall || ev.grade) && <Row k="Transcript grade">{ev.grade ? <span className="font-mono">{ev.grade}</span> : <span className="text-muted">ungraded</span>}{ev.source_quality ? <span className="text-muted"> · {ev.source_quality}</span> : null}</Row>}
          </dl>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted mb-1.5">{isConstructed(ev) ? "Cited value" : ev.quote_note && !ev.quote ? ev.quote_note : "Page excerpt"}</div>
            {isConstructed(ev) ? (
              <div>
                <code className="block rounded-md bg-surface-2 border border-line p-3 font-mono text-[12.5px] break-all">{ev.quote || (ev.value != null ? String(ev.value) : "")}</code>
                <p className="mt-1 text-[11.5px] text-muted">constructed from the cited value, not a verbatim quote</p>
              </div>
            ) : hasExcerpt ? (
              <blockquote className="rounded-md bg-surface-2 border border-line p-3 text-sm leading-relaxed whitespace-pre-wrap">
                {ex!.before}<mark>{ex!.match}</mark>{ex!.after}
              </blockquote>
            ) : ev.quote ? (
              <blockquote className="rounded-md bg-surface-2 border border-line p-3 text-sm leading-relaxed"><mark>{ev.quote}</mark></blockquote>
            ) : (
              <p className="text-sm text-muted">{ev.quote_note ? `${ev.quote_note}.` : "No excerpt exported for this citation."}{ev.value != null && ev.value !== "" ? <> Cited value: <span className="font-mono">{String(ev.value)}</span>.</> : null}</p>
            )}
          </div>
    </DrawerShell>
  );
}

function DrawerShell({ refEl, closeBtn, onClose, label, children }: {
  refEl: React.RefObject<HTMLDivElement>; closeBtn: React.RefObject<HTMLButtonElement>; onClose: () => void; label: string; children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 no-print">
      <div className="absolute inset-0 bg-fg/30" onClick={onClose} aria-hidden="true" />
      <div
        ref={refEl}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-drawer-title"
        className="absolute right-0 top-0 h-full w-[480px] max-w-[92vw] bg-surface shadow-drawer border-l border-line flex flex-col"
      >
        <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-line">
          <div className="min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">Source</div>
            <h2 id="source-drawer-title" className="font-mono text-sm font-medium mt-0.5 break-words">{label}</h2>
          </div>
          <button ref={closeBtn} onClick={onClose} className="rounded border border-line px-2 py-1 text-xs hover:bg-surface-2" aria-label="Close source drawer (Esc)">
            Esc ✕
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">{children}</div>
      </div>
    </div>
  );
}
