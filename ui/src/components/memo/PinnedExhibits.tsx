import { ExhibitView } from "../ask";
import { removePin, usePins } from "../../lib/exhibits";
import type { Company } from "../../lib/types";
import type { ExhibitKind } from "../../lib/retrieve";

const KINDS = new Set<string>(["timeline", "h2h", "price", "peer"]);

// Exhibits pinned from Ask NEEDLE (localStorage needle.pins.<ticker>), rendered full size and
// updated live when pins change in Ask or another tab.
export function PinnedExhibits({ ticker, company, asOf }: { ticker: string; company: Company; asOf?: string }) {
  const pins = usePins(ticker);

  if (!pins.length) {
    return <p className="text-sm text-muted no-print">No exhibits pinned yet. Pin them from Ask NEEDLE.</p>;
  }
  return (
    <ol className="memo-pins space-y-3">
      {pins.map((p, i) => (
        <li key={`${p.kind}-${p.ref}`} className="memo-keep space-y-1">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Exhibit {i + 1}</span>
            <button type="button" onClick={() => removePin(ticker, p)} className="no-print shrink-0 rounded border border-line px-1.5 py-0.5 text-[11px] text-muted hover:text-bad hover:border-bad/50" aria-label={`Remove exhibit ${p.title}`}>
              Remove
            </button>
          </div>
          <div className="grid grid-cols-1 [&_.col-span-2]:col-span-1">
            {KINDS.has(p.kind) ? (
              <ExhibitView exhibit={{ kind: p.kind as ExhibitKind, ref: String(p.ref ?? ""), title: p.title }} company={company} asOf={asOf} />
            ) : (
              <div className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm"><span className="font-semibold">{p.title}</span> <span className="text-muted">(exhibit kind "{p.kind}" cannot be drawn)</span></div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
