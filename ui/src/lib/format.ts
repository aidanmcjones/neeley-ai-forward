// Display formatters. All return "n/a" for null/undefined/NaN so missing data is visible.

const NA = "n/a";
const ok = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);

/** $1.2B, $340M, $12.5K, $950. Negative values keep the sign: -$1.2B. */
export function money(x: number | null | undefined, digits = 1): string {
  if (!ok(x)) return NA;
  const sign = x < 0 ? "-" : "";
  const a = Math.abs(x);
  const units: [number, string][] = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];
  for (const [v, s] of units) {
    if (a >= v) {
      const n = a / v;
      return `${sign}$${n.toFixed(n >= 100 ? 0 : digits)}${s}`;
    }
  }
  return `${sign}$${a.toFixed(a < 10 && a % 1 ? 2 : 0)}`;
}

/** Percent. By default x is a fraction (0.123 -> 12.3%); pass {fraction:false} if already in %. */
export function pct(x: number | null | undefined, opts: { digits?: number; fraction?: boolean; sign?: boolean } = {}): string {
  if (!ok(x)) return NA;
  const { digits = 1, fraction = true, sign = false } = opts;
  const v = fraction ? x * 100 : x;
  return `${sign && v > 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

const nfCache = new Map<string, Intl.NumberFormat>();
/** Grouped number with fixed decimals (render inside .tnum for tabular figures). */
export function num(x: number | null | undefined, digits = 0, opts: { sign?: boolean } = {}): string {
  if (!ok(x)) return NA;
  const key = `${digits}`;
  let nf = nfCache.get(key);
  if (!nf) { nf = new Intl.NumberFormat("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }); nfCache.set(key, nf); }
  return `${opts.sign && x > 0 ? "+" : ""}${nf.format(x)}`;
}

/** Signed z-score, e.g. z +2.9. */
export const z = (x: number | null | undefined) => (ok(x) ? `z ${x > 0 ? "+" : ""}${x.toFixed(1)}` : NA);

function toDate(d: string | number | Date | null | undefined): Date | null {
  if (d == null || d === "") return null;
  // Treat bare YYYY-MM-DD as a calendar date (no timezone shift).
  if (typeof d === "string" && /^\d{4}-\d{2}-\d{2}$/.test(d)) {
    const [y, m, day] = d.split("-").map(Number);
    return new Date(y, m - 1, day);
  }
  const dt = d instanceof Date ? d : new Date(d);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

/** "Oct 17, 2026". Unparseable strings are returned as-is. */
export function date(d: string | number | Date | null | undefined): string {
  const dt = toDate(d);
  if (!dt) return typeof d === "string" && d ? d : NA;
  return dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/** "2026-10-17". */
export function isoDate(d: string | number | Date | null | undefined): string {
  const dt = toDate(d);
  if (!dt) return NA;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}`;
}
