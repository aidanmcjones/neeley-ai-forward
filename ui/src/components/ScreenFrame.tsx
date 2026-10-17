import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";

// Shared wrapper for screens: title row plus honest loading / error states.

export function SampleBanner() {
  return (
    <div role="note" className="rounded-md border border-warn/50 bg-warn/15 px-4 py-2 text-sm text-warn font-semibold">
      sample data: <span className="font-normal">ui/public/data/meta.json was not found, so this is the smoke-test fixture in
      <code className="font-mono text-xs"> public/data/_sample/</code>. Run <code className="font-mono text-xs">python -m agent.ui_export</code> for the real export.</span>
    </div>
  );
}

export function ScreenFrame({ title, subtitle, loading, error, actions, printTitle = true, children }: {
  title: string; subtitle?: ReactNode; loading?: boolean; error?: string | null; actions?: ReactNode;
  /** false hides the title row in print (e.g. the memo, which carries its own heading). */
  printTitle?: boolean; children?: ReactNode;
}) {
  const file = error?.match(/\/data\/[^\s)]+/)?.[0];
  return (
    <div className="space-y-4">
      <div className={`flex items-end justify-between gap-4 ${printTitle ? "" : "no-print"}`}>
        <div className="min-w-0">
          <h1 className="font-display text-[34px] leading-none tracking-wide text-purple-deep dark:text-purple">{title}</h1>
          {subtitle && <div className="mt-1 text-sm text-muted">{subtitle}</div>}
        </div>
        {actions && <div className="shrink-0 flex gap-2">{actions}</div>}
      </div>
      {error ? (
        <EmptyState file={file} message={error} />
      ) : loading ? (
        <div role="status" aria-live="polite" className="text-sm text-muted">Loading…</div>
      ) : (
        children
      )}
    </div>
  );
}
