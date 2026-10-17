// Horizontal bar with a text value. value/max clamps to [0,1]. Tone picks the token color.
type Tone = "purple" | "teal" | "good" | "warn" | "bad" | "grey";
const FILL: Record<Tone, string> = {
  purple: "bg-purple", teal: "bg-teal", good: "bg-good", warn: "bg-warn", bad: "bg-bad", grey: "bg-frog-grey",
};

export function ScoreBar({ value, max = 1, label, tone = "purple", width = 96 }: {
  value: number | null | undefined; max?: number; label?: string; tone?: Tone; width?: number;
}) {
  const ok = typeof value === "number" && Number.isFinite(value) && max > 0;
  const frac = ok ? Math.max(0, Math.min(1, value! / max)) : 0;
  const text = label ?? (ok ? value!.toFixed(2) : "n/a");
  return (
    <span className="inline-flex items-center gap-2 align-middle" title={text}>
      <span className="relative h-2 rounded-full bg-line overflow-hidden" style={{ width }} aria-hidden="true">
        <span className={`absolute inset-y-0 left-0 rounded-full ${FILL[tone]}`} style={{ width: `${frac * 100}%` }} />
      </span>
      <span className="font-mono text-[11px] tnum text-muted">{text}</span>
    </span>
  );
}
