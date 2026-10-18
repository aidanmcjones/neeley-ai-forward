import type { Part1Selection } from "../../lib/types";
import { scrub } from "../../lib/part1";

// "Why <company> beat the other nine": the sealed pick's reason, the other nine in one line each,
// and the seal (sha256 short form, sealed_at) in a muted footer.

const ORD = ["number one", "number two", "number three"];

export function SelectionCard({ selection, ticker, nameOf, seal }: {
  selection: Part1Selection; ticker: string; nameOf: (t: string) => string;
  seal?: { sha256?: string; sealed_at?: string } | null;
}) {
  const picked = selection.picked ?? [];
  const rank = picked.indexOf(ticker);
  const name = nameOf(ticker);
  const title = rank <= 0 ? `Why ${name} beat the other nine` : `Why ${name} is the ${ORD[rank] ?? `number ${rank + 1}`} pick`;
  const reason = scrub(selection.reasons?.[ticker]);
  const others = [
    ...picked.filter((t) => t !== ticker).map((t) => ({ t, line: scrub(selection.reasons?.[t]).split(/(?<!\b(?:Co|Inc|Corp|Ltd|vs|No))(?<=[.!?])\s+/)[0] ?? "", tag: `pick ${picked.indexOf(t) + 1}` })),
    ...Object.entries(selection.eliminated ?? {}).filter(([t]) => t !== ticker && !picked.includes(t)).map(([t, line]) => ({ t, line: scrub(line), tag: "" })),
  ];
  const sha = seal?.sha256 ?? selection.sha256;
  const at = seal?.sealed_at ?? selection.sealed_at;
  return (
    <section aria-label={title} className="rounded-lg border border-line bg-surface px-4 py-3 shadow-card space-y-2">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      {reason ? <p className="text-[14px] leading-relaxed">{reason}</p> : <p className="text-[13px] text-muted">No reason exported for {ticker}.</p>}
      {others.length > 0 && (
        <details className="rounded-md border border-line bg-surface-2 px-3 py-1.5">
          <summary className="cursor-pointer select-none text-[13px] font-semibold text-purple">The other {others.length === 9 ? "nine" : others.length}</summary>
          <ul className="mt-1.5 space-y-1 text-[13px]">
            {others.map((o) => (
              <li key={o.t} className="flex gap-2">
                <span className="w-12 shrink-0 font-mono text-[12px] font-semibold">{o.t}</span>
                <span className="min-w-0 break-words">{o.tag && <span className="mr-1 text-[11px] font-semibold uppercase tracking-wide text-teal">{o.tag}</span>}{o.line || <span className="text-muted">no line exported</span>}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {(sha || at) && (
        <p className="border-t border-line pt-1.5 text-[11px] text-muted" title={sha ? `sha256 ${sha}` : undefined}>
          Selection sealed{sha ? <> · sha256 <span className="font-mono">{sha.slice(0, 12)}</span></> : null}{at ? ` · ${at}` : null}
        </p>
      )}
    </section>
  );
}
