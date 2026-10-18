import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Part1Selection } from "../../lib/types";
import { cardText, checkCardFigures, isInternal, loadSealedDoc, splitSentences } from "../../lib/part1";
import { Md } from "./Md";

// "Why <company> beat the other nine": the sealed pick's reason, the other nine in one line each, the seal
// (sha256 short form, sealed_at) and "Read the sealed selection". Prose comes only from the figure-free
// reasons_card / eliminated_card; the verbatim reasons / eliminated carry ungated figures and are used only
// as a figure-stripped fallback while the card fields are absent.

const ORD = ["number one", "number two", "number three"];
const firstSentence = (s: string) => splitSentences(s)[0] ?? "";
const noCite = () => undefined;
// Pitch rule on the sealed document too: drop any line naming league / scoring internals.
const pitchDoc = (md: string) => md.split("\n").filter((l) => !isInternal(l)).join("\n");

/** Minimal block markdown: headings, list items, table rows (monospace), paragraphs; inline via Md. */
function MdDoc({ text }: { text: string }) {
  const out: ReactNode[] = [];
  const blocks = text.replace(/\r/g, "").split(/\n{2,}/);
  blocks.forEach((b, i) => {
    const lines = b.split("\n").filter((l) => l.trim());
    if (!lines.length) return;
    if (lines.every((l) => l.trim().startsWith("|"))) {
      out.push(<pre key={i} className="overflow-x-auto whitespace-pre font-mono text-[11.5px] leading-relaxed">{lines.join("\n")}</pre>);
      return;
    }
    const h = lines[0].match(/^(#{1,6})\s+(.*)$/);
    if (h && lines.length === 1) {
      const lvl = h[1].length;
      out.push(<div key={i} className={lvl <= 1 ? "text-[18px] font-semibold" : lvl === 2 ? "text-[15.5px] font-semibold" : "text-[14px] font-semibold"}><Md md={h[2]} cite={noCite} /></div>);
      return;
    }
    if (lines.every((l) => /^\s*([-*]|\d+\.)\s+/.test(l))) {
      out.push(<ul key={i} className="list-disc space-y-1 pl-5">{lines.map((l, j) => <li key={j}><Md md={l.replace(/^\s*([-*]|\d+\.)\s+/, "")} cite={noCite} /></li>)}</ul>);
      return;
    }
    out.push(<p key={i}>{lines.map((l, j) => {
      const hh = l.match(/^(#{1,6})\s+(.*)$/);
      return <span key={j} className={hh ? "block font-semibold" : ""}><Md md={hh ? hh[2] : l} cite={noCite} />{j < lines.length - 1 ? " " : ""}</span>;
    })}</p>);
  });
  return <>{out}</>;
}

function SealedDoc({ text, error, sha, at, onClose }: { text: string | null; error: string | null; sha?: string; at?: string; onClose: () => void }) {
  const closeBtn = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeBtn.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); opener?.focus?.(); };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-fg/30" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Sealed selection" onClick={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-[640px] flex-col bg-bg shadow-drawer">
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="text-[15px] font-semibold">Sealed selection</h2>
          <button ref={closeBtn} type="button" onClick={onClose} className="rounded-md border border-line px-2 py-1 text-[12px] font-semibold hover:border-purple hover:text-purple">Close</button>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 text-[14px] leading-relaxed">
          <p className="rounded-md border border-line bg-surface-2 px-3 py-2 text-[12px] text-muted">
            Sealed before the gate on {at ?? "an unrecorded date"}. Figures in this document are the blind readers' sizing; the gated figures are in the findings table.
            {sha ? <> sha256 <span className="font-mono" title={sha}>{sha.slice(0, 12)}</span>.</> : null}
          </p>
          {error ? <p role="alert" className="text-[13px] text-bad">{error}</p>
            : text == null ? <p role="status" className="text-[13px] text-muted">Loading the sealed document…</p>
            : <MdDoc text={text} />}
        </div>
      </div>
    </div>
  );
}

export function SelectionCard({ selection, ticker, nameOf, seal, prefix }: {
  selection: Part1Selection; ticker: string; nameOf: (t: string) => string;
  seal?: { sha256?: string; sealed_at?: string } | null; prefix?: string | null;
}) {
  const picked = selection.picked ?? [];
  const rank = picked.indexOf(ticker);
  const name = nameOf(ticker);
  const title = rank <= 0 ? `Why ${name} beat the other nine` : `Why ${name} is the ${ORD[rank] ?? `number ${rank + 1}`} pick`;
  const reason = cardText(selection.reasons_card, selection.reasons, ticker);
  const elimKeys = Object.keys(selection.eliminated_card ?? selection.eliminated ?? {});
  const others = [
    ...picked.filter((t) => t !== ticker).map((t) => ({ t, line: firstSentence(cardText(selection.reasons_card, selection.reasons, t)), tag: `pick ${picked.indexOf(t) + 1}` })),
    ...elimKeys.filter((t) => t !== ticker && !picked.includes(t)).map((t) => ({ t, line: cardText(selection.eliminated_card, selection.eliminated, t), tag: "" })),
  ];
  useEffect(() => { checkCardFigures(ticker, [reason, ...others.map((o) => o.line)]); });
  const sha = seal?.sha256 ?? selection.sha256;
  const at = seal?.sealed_at ?? selection.sealed_at;

  const [open, setOpen] = useState(false);
  const [doc, setDoc] = useState<string | null>(null);
  const [docErr, setDocErr] = useState<string | null>(null);
  const canRead = !!(selection.sealed_doc_path || selection.selection_md);
  const read = () => {
    setOpen(true);
    if (doc != null) return;
    const fallback = () => {
      if (selection.selection_md) setDoc(pitchDoc(selection.selection_md));
      else setDocErr(`Could not load data/${selection.sealed_doc_path}.`);
    };
    if (selection.sealed_doc_path && prefix) loadSealedDoc(prefix, selection.sealed_doc_path).then((t) => setDoc(pitchDoc(t)), fallback);
    else fallback();
  };

  return (
    <section aria-label={title} data-selection-card={ticker} className="rounded-lg border border-line bg-surface px-4 py-3 shadow-card space-y-2">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      {reason ? <p className="text-[14px] leading-relaxed">{reason}</p> : <p className="text-[13px] text-muted">The reason for {name} is in the sealed selection.</p>}
      {others.length > 0 && (
        <details className="rounded-md border border-line bg-surface-2 px-3 py-1.5">
          <summary className="cursor-pointer select-none text-[13px] font-semibold text-purple">The other {others.length === 9 ? "nine" : others.length}</summary>
          <ul className="mt-1.5 space-y-1 text-[13px]">
            {others.map((o) => (
              <li key={o.t} className="flex gap-2">
                <span className="w-12 shrink-0 font-mono text-[12px] font-semibold">{o.t}</span>
                <span className="min-w-0 break-words">{o.tag && <span className="mr-1 text-[11px] font-semibold uppercase tracking-wide text-teal">{o.tag}</span>}{o.line || <span className="text-muted">see the sealed selection</span>}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line pt-1.5">
        {(sha || at) && (
          <p className="text-[11px] text-muted" title={sha ? `sha256 ${sha}` : undefined}>
            Selection sealed{sha ? <> · sha256 <span className="font-mono">{sha.slice(0, 12)}</span></> : null}{at ? ` · ${at}` : null}
          </p>
        )}
        {canRead && <button type="button" onClick={(e) => { e.stopPropagation(); read(); }} className="no-print ml-auto text-[12px] font-semibold text-purple hover:underline">Read the sealed selection</button>}
      </div>
      {open && <SealedDoc text={doc} error={docErr} sha={sha} at={at} onClose={() => setOpen(false)} />}
    </section>
  );
}
