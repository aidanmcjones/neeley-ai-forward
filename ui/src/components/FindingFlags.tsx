import { onTriage } from "../lib/cites";
import type { Finding } from "../lib/types";

// v3 finding flags as small labelled pills (text plus color, never color alone).
const FLAG: Record<string, { label: string; tone: "good" | "warn" | "muted"; tip: string }> = {
  needle_eligible: { label: "needle eligible", tone: "good", tip: "Clears the Sharpest Needle floor (obscurity, evidence and confidence)." },
  provisional: { label: "provisional", tone: "warn", tip: "Picked by the provisional rule: no row cleared the strict floor." },
  one_off: { label: "one-off", tone: "warn", tip: "One-off item: not expected to recur, so it is not scored as a run-rate change." },
  not_quantified: { label: "not quantified", tone: "muted", tip: "No dollar impact is computed for this row (see the reason in the detail)." },
  not_league_comparable: { label: "not league-comparable", tone: "warn", tip: "Inputs are imputed for this company, so its score is not compared like-for-like in the league." },
};

export function flagInfo(f: string) {
  return FLAG[f] ?? { label: f.replace(/_/g, " "), tone: "muted" as const, tip: f };
}

export function findingFlags(f: Finding | null | undefined): string[] {
  const fl = f?.flags;
  return Array.isArray(fl) ? fl.filter((x): x is string => typeof x === "string" && !!x) : [];
}

// League-selection flags are internal triage; they show only on /cockpit/triage.
const LEAGUE_FLAGS = new Set(["provisional", "needle_eligible", "not_league_comparable"]);

export function FlagPills({ finding, flags, className = "" }: { finding?: Finding | null; flags?: string[]; className?: string }) {
  const all = flags ?? findingFlags(finding);
  const list = onTriage() ? all : all.filter((f) => !LEAGUE_FLAGS.has(f));
  if (!list.length) return null;
  return (
    <span className={`inline-flex flex-wrap gap-1 ${className}`}>
      {list.map((x) => {
        const i = flagInfo(x);
        const cls = i.tone === "good" ? "border-good/50 text-good" : i.tone === "warn" ? "border-warn/60 text-warn" : "border-line text-muted";
        return <span key={x} title={i.tip} className={`rounded border px-1 py-px text-[10px] font-semibold leading-tight whitespace-nowrap ${cls}`}>{i.label}</span>;
      })}
    </span>
  );
}
