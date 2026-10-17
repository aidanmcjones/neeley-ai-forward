import type { KeyboardEvent } from "react";
import type { Evidence } from "../lib/types";
import { useSource } from "./SourceDrawer";

// Small mono citation chip: "[n]" or a label. Click / Enter / Space opens the SourceDrawer.
// onPreview fires on hover/focus so a live source card can show the quote.
export function CiteChip({ evidence, n, label, onPreview }: {
  evidence?: Evidence | null; n?: number; label?: string; onPreview?: (ev: Evidence | null) => void;
}) {
  const { open } = useSource();
  const text = label ?? (n != null ? `[${n}]` : "[src]");
  const title = evidence?.citation || evidence?.doc_id || "Source not exported";
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
      className="inline-block align-baseline font-mono text-[11px] leading-tight rounded px-1 py-px bg-chip text-purple hover:bg-purple dark:hover:bg-purple-deep hover:text-white border border-purple/20 tnum"
    >
      {text}
    </button>
  );
}
