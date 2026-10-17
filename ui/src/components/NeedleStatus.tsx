// Sharpest Needle status from the v2 league (docs/league_v2_note.md, docs/quant_model.md B5).
// strict = the top-S finding that clears the needle floor; the other two are labelled fallbacks.

const INFO: Record<string, { label: string; tip: string; warn: boolean; muted?: boolean }> = {
  none: {
    label: "None qualifies",
    tip: "None: no finding clears the strict floor, the provisional rule (O at or above the company median) or the relaxed top-quartile rule, so no Sharpest Needle is named.",
    warn: false,
    muted: true,
  },
  strict: {
    label: "Strict",
    tip: "Strict: the highest-S finding that clears the needle floor (obscurity O ≥ 0.5, evidence E ≥ 0.9, not low confidence).",
    warn: false,
  },
  provisional: {
    label: "Provisional",
    tip: "Provisional: no finding clears the obscurity floor (O ≥ 0.5), so this is the highest S among findings with O at or above the company median.",
    warn: true,
  },
  floor_relaxed: {
    label: "Floor relaxed",
    tip: "Floor relaxed: no strict or provisional pick, so the floor drops to the top quartile of obscurity within the company.",
    warn: true,
  },
};

export function needleStatusInfo(status?: string | null) {
  const k = (status ?? "").replace(/\s+/g, "_").toLowerCase();
  return INFO[k] ?? null;
}

export function NeedleStatusPill({ status, className = "" }: { status?: string | null; className?: string }) {
  const i = needleStatusInfo(status);
  if (!i) return null;
  return (
    <span
      tabIndex={0}
      title={i.tip}
      aria-label={`Needle status: ${i.tip}`}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ${
        i.muted ? "border-dashed border-muted/60 text-muted" : i.warn ? "border-warn/60 bg-warn/10 text-warn" : "border-good/50 bg-good/10 text-good"}${className ? ` ${className}` : ""}`}
    >
      {i.muted ? "∅ " : i.warn ? "⚠ " : "✓ "}Needle: {i.label}
    </span>
  );
}
