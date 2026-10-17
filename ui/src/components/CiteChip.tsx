import type { KeyboardEvent } from "react";
import type { Evidence } from "../lib/types";
import { useSource } from "./SourceDrawer";
import { isWithheld, withheldReason } from "../lib/data";
import { isDerived, isRowCite } from "../lib/cites";

// Small mono citation chip: "[n]" or a label. Click / Enter / Space opens the SourceDrawer.
// onPreview fires on hover/focus so a live source card can show the quote.
export function CiteChip({ evidence, n, label, onPreview }: {
  evidence?: Evidence | null; n?: number; label?: string; onPreview?: (ev: Evidence | null) => void;
}) {
  const { open } = useSource();
  const text = label ?? (n != null ? `[${n}]` : "[src]");
  const withheld = isWithheld(evidence);
  const base = evidence?.citation || evidence?.doc_title || evidence?.doc_id || "Source not exported";
  const derived = isDerived(evidence);
  const row = isRowCite(evidence);
  const title = withheld && evidence ? `${base} (quote withheld: ${withheldReason(evidence)})`
    : row ? `${base} (data row: ${evidence!.row_ref ?? evidence!.cite_id})`
    : derived ? `${base} (derived from ${evidence!.derived_from!.length} cited operand${evidence!.derived_from!.length > 1 ? "s" : ""})` : base;
  if (!evidence) {
    return <span className="inline-block font-mono text-[11px] rounded px-1 py-px bg-line text-muted line-through" title="Source not exported">{text}</span>;
  }
  const go = () => open(evidence);
  const onKey = (e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } };
  return (
    <button
      type="button"
      onClick={go}
      onKeyDown={onKey}
      onMouseEnter={() => onPreview?.(evidence)}
      onFocus={() => onPreview?.(evidence)}
      onMouseLeave={() => onPreview?.(null)}
      title={title}
      aria-label={`Open source: ${title}`}
      data-withheld={withheld || undefined}
      data-derived={derived || undefined}
      data-row={row || undefined}
      className={withheld
        ? "inline-block align-baseline font-mono text-[11px] leading-tight rounded px-1 py-px bg-transparent text-muted border border-dashed border-muted/70 hover:text-fg hover:border-fg tnum"
        : row
        ? "inline-block align-baseline font-mono text-[11px] leading-tight rounded-sm px-1 py-px bg-surface-2 text-fg border border-line border-b-2 border-b-purple/50 hover:bg-chip tnum"
        : derived
        ? "inline-block align-baseline font-mono text-[11px] italic leading-tight rounded px-1 py-px bg-surface text-purple border border-purple/60 hover:bg-chip tnum"
        : "inline-block align-baseline font-mono text-[11px] leading-tight rounded px-1 py-px bg-chip text-purple hover:bg-purple dark:hover:bg-purple-deep hover:text-white border border-purple/20 tnum"}
    >
      {derived ? <><span aria-hidden="true">ƒ</span>{text}</> : row ? <><span aria-hidden="true" className="text-purple">▦</span>{text}</> : text}
    </button>
  );
}
