import type { NumericCheck } from "../lib/types";

// Second check, separate from "quote located": are the numbers in the sentence on the cited page?
// Driven by numeric_check (league_v3 uncited-claim gate). Absent or "unchecked" renders muted,
// so no number is presented as page-verified before the check has run.

const n = (x: unknown) => (typeof x === "number" && Number.isFinite(x) ? x : 0);

export function numericCheckText(c: NumericCheck | null | undefined, compact = false): { text: string; tone: "good" | "bad" | "muted"; tip: string } {
  if (c?.status === "passed") {
    const t = `${n(c.verified)} verified · ${n(c.derived)} derived · ${n(c.assumed)} assumed`;
    return { text: compact ? `nums ✓ ${n(c.verified)}/${n(c.derived)}/${n(c.assumed)}` : `numbers page-checked ${t}`, tone: "good",
      tip: `Numbers page-checked: ${t}${c.total != null ? ` (${n(c.checked)} of ${n(c.total)} checked)` : ""}.${c.note ? ` ${c.note}` : ""}` };
  }
  if (c?.status === "failed") {
    const u = c.unsupported ?? [];
    const k = u.length || Math.max(0, n(c.total) - n(c.checked));
    const list = u.map((x) => `${String(x.value ?? "?")}${x.where ? ` (${x.where})` : ""}${x.reason ? `: ${x.reason}` : ""}`).join("; ");
    return { text: compact ? `nums: ${k} unsupported` : `${k} number${k === 1 ? "" : "s"} unsupported`, tone: "bad",
      tip: `Numbers not found on the cited page: ${list || "list not exported"}.${c.note ? ` ${c.note}` : ""}` };
  }
  if (c?.status === "no_numbers") {
    return { text: compact ? "no numbers" : "no numbers to check", tone: "muted",
      tip: `The numeric gate ran and this record states no numbers to check.${c.note ? ` ${c.note}` : ""}` };
  }
  return { text: compact ? "nums unchecked" : "numbers not yet page-checked", tone: "muted",
    tip: "The quote was located on the page, but the numbers in this sentence have not been checked against the page yet (pending the v3 uncited-claim gate)." };
}

export function NumericPill({ check, compact = false, className = "" }: { check?: NumericCheck | null; compact?: boolean; className?: string }) {
  const { text, tone, tip } = numericCheckText(check, compact);
  const cls = tone === "good" ? "border-good/50 bg-good/10 text-good"
    : tone === "bad" ? "border-bad/50 bg-bad/10 text-bad"
    : "border-dashed border-muted/60 text-muted";
  return (
    <span tabIndex={0} title={tip} aria-label={tip}
      className={`inline-block whitespace-nowrap rounded border px-1 py-px align-middle font-mono text-[10px] leading-tight ${cls}${className ? ` ${className}` : ""}`}>
      {text}
    </span>
  );
}

/** Block-level summary (stance.decide, labels.v2) shown once in a panel header; null when absent. */
export function NumericSummary({ check }: { check?: NumericCheck | null }) {
  if (!check) return null;
  return <NumericPill check={check} />;
}
