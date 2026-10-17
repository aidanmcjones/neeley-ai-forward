import { useData } from "../lib/data";
import { date } from "../lib/format";
import { usePalette } from "./CommandPalette";

// Top bar: logo, tagline, company picker, As-of pill, ⌘K Ask.
export function Chrome() {
  const { meta, ticker, setTicker } = useData();
  const { openPalette } = usePalette();
  const companies = meta?.companies ?? [];
  const onboarded = (meta?.onboarded ?? []).filter((t) => !companies.some((c) => c.ticker === t));
  const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

  return (
    <header data-chrome className="no-print h-14 shrink-0 flex items-center gap-5 border-b border-line bg-surface px-5">
      <div className="flex items-baseline gap-3 min-w-0">
        <span className="font-display text-[30px] leading-none tracking-wide text-purple" aria-label="NEEDLE">
          NEE<span className="text-teal">DLE</span>
        </span>
        <span className="text-[11px] text-muted truncate hidden xl:inline">
          Finds what the headlines miss. Proves every claim to the page. Checks itself.
        </span>
      </div>
      <div className="ml-auto flex items-center gap-3 shrink-0">
        <label className="flex items-center gap-2 text-xs text-muted">
          <span className="font-semibold uppercase tracking-wide">Company</span>
          <select
            value={ticker ?? ""}
            onChange={(e) => setTicker(e.target.value)}
            className="rounded-md border border-line bg-surface-2 px-2 py-1.5 text-sm text-fg font-semibold"
            disabled={!companies.length}
          >
            {!companies.length && <option value="">No companies</option>}
            {companies.map((c) => (
              <option key={c.ticker} value={c.ticker}>{c.ticker}{c.name ? ` · ${c.name}` : ""}</option>
            ))}
            {onboarded.length > 0 && (
              <optgroup label="Onboarded">
                {onboarded.map((t) => <option key={t} value={t}>Onboarded: {t}</option>)}
              </optgroup>
            )}
          </select>
        </label>
        <span className="rounded-full bg-chip px-3 py-1 text-xs font-semibold text-purple whitespace-nowrap">
          As of <span className="font-mono tnum">{meta?.as_of ? date(meta.as_of) : "n/a"}</span>
        </span>
        <button
          type="button"
          onClick={openPalette}
          className="inline-flex items-center gap-2 rounded-md bg-purple dark:bg-purple-deep px-3 py-1.5 text-sm font-semibold text-white hover:bg-purple-bright dark:hover:bg-purple-bright dark:hover:text-fg"
          aria-keyshortcuts="Meta+K Control+K"
        >
          <kbd className="font-mono text-[11px] bg-white/15 rounded px-1">{isMac ? "⌘K" : "Ctrl K"}</kbd> Ask
        </button>
      </div>
    </header>
  );
}
