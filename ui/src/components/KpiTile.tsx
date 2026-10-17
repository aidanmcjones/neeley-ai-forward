import type { ReactNode } from "react";

// KPI tile: label, big Bebas number, footnote naming the file it came from. `hot` = emphasized.
// `footnote` is one truncated line; `footnote2` adds a second line, or set `wrap` to let the
// footnote wrap to two lines instead of truncating.
export function KpiTile({ label, value, footnote, footnote2, wrap = false, hot = false }: {
  label: string; value: ReactNode; footnote?: ReactNode; footnote2?: ReactNode; wrap?: boolean; hot?: boolean;
}) {
  const foot = `text-[11px] font-mono ${hot ? "text-white/75" : "text-muted"}`;
  return (
    <div className={`rounded-lg border px-4 py-3 min-w-0 ${hot ? "bg-purple dark:bg-purple-deep text-white border-purple dark:border-purple-deep" : "bg-surface border-line shadow-card"}`}>
      <div className={`text-[11px] font-semibold uppercase tracking-wider ${hot ? "text-white/80" : "text-muted"}`}>{label}</div>
      <div className="font-display text-[40px] leading-none mt-1 tnum truncate">{value}</div>
      {footnote != null && (
        <div className={`mt-1 ${foot} ${wrap ? "leading-snug line-clamp-2" : "truncate"}`}>{footnote}</div>
      )}
      {footnote2 != null && <div className={`${foot} truncate`}>{footnote2}</div>}
    </div>
  );
}
