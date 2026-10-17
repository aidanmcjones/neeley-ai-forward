import type { ReactNode } from "react";
import { togglePin, usePins } from "../../lib/exhibits";
import type { Pin } from "../../lib/exhibits";

// Shared shell for Ask exhibit cards: title, one-line reading, body, source footnote, Pin to memo.
export function ExhibitCard({ ticker, pin, reading, source, wide = false, children }: {
  ticker: string; pin: Pin; reading?: ReactNode; source: ReactNode; wide?: boolean; children: ReactNode;
}) {
  const pins = usePins(ticker);
  const pinned = pins.some((p) => p.kind === pin.kind && p.ref === pin.ref);
  return (
    <section className={`exhibit-card rounded-lg border border-line bg-surface shadow-card min-w-0 flex flex-col ${wide ? "col-span-2" : ""}`} aria-label={pin.title}>
      <header className="flex items-start justify-between gap-3 px-4 pt-3">
        <div className="min-w-0">
          <h3 className="text-[13px] font-bold leading-tight">{pin.title}</h3>
          {reading && <p className="mt-1 text-xs text-muted leading-snug">{reading}</p>}
        </div>
        <button
          type="button"
          onClick={() => togglePin(ticker, pin)}
          aria-pressed={pinned}
          className={`exhibit-pin no-print shrink-0 rounded border px-2 py-1 text-[11px] font-semibold ${pinned ? "border-purple bg-purple dark:bg-purple-deep text-white" : "border-purple/40 text-purple hover:bg-chip"}`}
        >
          {pinned ? "✓ Pinned" : "Pin to memo"}
        </button>
      </header>
      <div className="px-4 py-3 flex-1 min-w-0">{children}</div>
      <footer className="border-t border-line px-4 py-1.5 text-[10.5px] font-mono text-muted break-words">Source: {source}</footer>
    </section>
  );
}
