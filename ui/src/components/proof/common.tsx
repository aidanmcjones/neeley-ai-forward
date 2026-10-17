import { useEffect, useState } from "react";
import type { ReactNode } from "react";

// Small helpers shared by the Proof and Moat screens (kept local so shared components stay untouched).

/** Footnote naming the file a panel's numbers came from. */
export function SourceNote({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-[11px] text-muted font-mono leading-snug">Source: {children}</p>;
}

type Tone = "good" | "warn" | "bad" | "purple" | "grey" | "teal";
const PILL: Record<Tone, string> = {
  good: "bg-good/15 text-good border-good/40",
  warn: "bg-warn/15 text-warn border-warn/40",
  bad: "bg-bad/15 text-bad border-bad/40",
  purple: "bg-chip text-purple border-purple/30",
  grey: "bg-surface-2 text-muted border-line",
  teal: "bg-teal-soft text-teal border-teal/40",
};

/** Status pill: color is always paired with its text. */
export function Pill({ tone, children, className = "" }: { tone: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide whitespace-nowrap ${PILL[tone]} ${className}`}>
      {children}
    </span>
  );
}

/** Map a pipeline/collect/verify status word to a tone. */
export function statusTone(s?: string | null): Tone {
  const v = (s ?? "").toLowerCase();
  if (["done", "ready", "verified", "complete"].includes(v)) return "good";
  if (["running", "verifying"].includes(v)) return "purple";
  if (["blocked", "gap", "missing", "failed"].includes(v)) return "bad";
  if (["collecting", "human", "partial"].includes(v)) return "warn";
  if (["collected", "queued"].includes(v)) return "purple";
  return "grey";
}

export interface Tokens {
  purple: string; purpleBright: string; purpleDeep: string; grey: string; teal: string;
  good: string; warn: string; bad: string; fg: string; muted: string; line: string; surface: string;
}

function readTokens(): Tokens {
  const cs = getComputedStyle(document.documentElement);
  const g = (n: string, fb: string) => {
    const v = cs.getPropertyValue(`--${n}`).trim();
    return v ? `rgb(${v.split(/\s+/).join(",")})` : fb;
  };
  return {
    purple: g("purple", "#4D1979"), purpleBright: g("purple-bright", "#6A23A7"), purpleDeep: g("purple-deep", "#3C145F"),
    grey: g("frog-grey", "#A3A9AC"), teal: g("teal", "#007B6E"), good: g("good", "#1E7F4F"), warn: g("warn", "#B26A00"),
    bad: g("bad", "#B3261E"), fg: g("fg", "#1F1630"), muted: g("muted", "#5E566C"), line: g("line", "#E2DCEA"),
    surface: g("surface", "#FFFFFF"),
  };
}

/** Theme colors resolved from the CSS variables (SVG attributes cannot read var()), re-read on theme change. */
export function useTokens(): Tokens {
  const [t, setT] = useState<Tokens>(() => readTokens());
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setT(readTokens());
    mq.addEventListener?.("change", update);
    const mo = new MutationObserver(update);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq.removeEventListener?.("change", update); mo.disconnect(); };
  }, []);
  return t;
}

/** "+7.3%" -> 0.073. Returns null when absent. */
export function parsePct(s: string | undefined | null): number | null {
  if (!s) return null;
  const m = s.match(/([+-]?\d+(?:\.\d+)?)%/);
  return m ? Number(m[1]) / 100 : null;
}

/** Pull point and interval out of a forecast's basis strings ("point +4.9%", "80% interval -0.5% to +10.2%"). */
export function parseBasis(basis: unknown): { point: number | null; lo: number | null; hi: number | null; k: string | null; through: string | null } {
  const arr = Array.isArray(basis) ? basis.map(String) : [];
  const pointS = arr.find((b) => /^point/i.test(b));
  const intS = arr.find((b) => /interval/i.test(b));
  let lo: number | null = null, hi: number | null = null;
  if (intS) {
    const m = intS.match(/interval\s+([+-]?\d+(?:\.\d+)?)%\s+to\s+([+-]?\d+(?:\.\d+)?)%/i);
    if (m) { lo = Number(m[1]) / 100; hi = Number(m[2]) / 100; }
  }
  return {
    point: parsePct(pointS?.replace(/^point\s*/i, "")),
    lo, hi,
    k: arr.find((b) => /k=/.test(b))?.match(/k=([\d.]+)/)?.[1] ?? null,
    through: arr.find((b) => /through/i.test(b))?.replace(/^data through\s*/i, "") ?? null,
  };
}

export const signedPct = (x: number | null | undefined, d = 1) =>
  typeof x === "number" && Number.isFinite(x) ? `${x > 0 ? "+" : ""}${(x * 100).toFixed(d)}%` : "n/a";
