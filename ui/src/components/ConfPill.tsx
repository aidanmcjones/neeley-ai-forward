// Confidence pill. Color is always paired with a text label.
const TONE: Record<string, string> = {
  high: "bg-good/15 text-good border-good/40",
  medium: "bg-warn/15 text-warn border-warn/40",
  low: "bg-bad/15 text-bad border-bad/40",
};

export function ConfPill({ level, short = false }: { level?: string | null; short?: boolean }) {
  const l = (level ?? "").toLowerCase();
  const tone = TONE[l] ?? "bg-chip text-muted border-line";
  const text = l ? `${l[0].toUpperCase()}${l.slice(1)}${short ? "" : " confidence"}` : "Confidence n/a";
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap ${tone}`}>{text}</span>;
}
