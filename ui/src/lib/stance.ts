// Stance and finding helpers shared by the Briefing and Memo screens.
// Everything here reads the exported JSON as-is; nothing invents a number.

import { resolveCite } from "./data";
import { money, num, pct } from "./format";
import type { CiteRef, Company, Evidence, Finding, Stance, StanceOption } from "./types";

/* ------------------------------------------------------------- options */

export type WeightBasis = "dollars" | "share" | "score" | "none";

export interface WeightedOption {
  option: StanceOption;
  name: string;
  recommended: boolean;
  /** 0..1 bar fraction relative to the largest option on the chosen basis. */
  frac: number;
  /** Text shown beside the bar. */
  valueLabel: string;
  dollars: number | null;
  nFindings: number | null;
  scoreSum: number | null;
}

const isNum = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);

/** Fields the exporter adds beyond the typed contract (JSON boundary). */
function optExtra(o: StanceOption): { n_findings?: unknown; score_sum?: unknown } {
  return o as unknown as { n_findings?: unknown; score_sum?: unknown };
}

/**
 * Order and weigh the stance options. Basis: stated dollars if any option has them, else
 * the exporter's share, else the summed materiality score the exporter ranked by.
 * Ordered by weight desc with the recommended option first.
 */
export function weighOptions(stance: Stance | null | undefined): { basis: WeightBasis; rows: WeightedOption[] } {
  const opts = stance?.options ?? [];
  const rec = (stance?.recommended ?? "").toLowerCase();
  const anyDollars = opts.some((o) => isNum(o.dollars) && o.dollars !== 0);
  const anyShare = opts.some((o) => isNum(o.share) && o.share > 0);
  const anyScore = opts.some((o) => isNum(optExtra(o).score_sum) && (optExtra(o).score_sum as number) > 0);
  const basis: WeightBasis = anyDollars ? "dollars" : anyShare ? "share" : anyScore ? "score" : "none";

  const weight = (o: StanceOption): number => {
    if (basis === "dollars") return isNum(o.dollars) ? Math.abs(o.dollars) : 0;
    if (basis === "share") return isNum(o.share) ? o.share : 0;
    if (basis === "score") { const s = optExtra(o).score_sum; return isNum(s) ? s : 0; }
    return 0;
  };
  const max = Math.max(0, ...opts.map(weight));

  const rows = opts.map<WeightedOption>((o) => {
    const w = weight(o);
    const n = optExtra(o).n_findings;
    const s = optExtra(o).score_sum;
    let valueLabel = "n/a";
    if (basis === "dollars") valueLabel = isNum(o.dollars) ? money(o.dollars) : "no direct $";
    else if (basis === "share") valueLabel = isNum(o.share) ? pct(o.share, { digits: 0 }) : "n/a";
    else if (basis === "score") valueLabel = isNum(s) ? s.toFixed(3) : "0.000";
    return {
      option: o,
      name: o.name,
      recommended: o.name.toLowerCase() === rec,
      frac: max > 0 ? w / max : 0,
      valueLabel,
      dollars: isNum(o.dollars) ? o.dollars : null,
      nFindings: isNum(n) ? n : null,
      scoreSum: isNum(s) ? s : null,
    };
  });
  rows.sort((a, b) => Number(b.recommended) - Number(a.recommended) || b.frac - a.frac);
  return { basis, rows };
}

export const BASIS_NOTE: Record<WeightBasis, string> = {
  dollars: "Bars: stated impact dollars from verified findings",
  share: "Bars: share of weight from stance.options",
  score: "Bars: summed materiality score of the verified findings behind each option (no option has a stated $)",
  none: "No weights exported for these options",
};

/* --------------------------------------------------------------- cites */

export interface ResolvedCite { key: string; n: number; ref: CiteRef; evidence?: Evidence; finding?: Finding }

const citeKey = (r: CiteRef) => `${r.finding_id}#${r.i ?? 0}`;
/** Same printed page = same number (two findings can cite one page); each chip still opens its own quote. */
const sourceKey = (ev: Evidence | undefined, r: CiteRef) =>
  ev ? `${ev.citation ?? ev.doc_id ?? ""}|${ev.page ?? ""}` : `missing|${citeKey(r)}`;

/**
 * A numbering registry for one document (screen or memo): each distinct source gets [n]
 * in order of first use, so the Sources list matches the chips.
 */
export class CiteRegistry {
  private byKey = new Map<string, ResolvedCite>();
  private bySource = new Map<string, number>();
  readonly list: ResolvedCite[] = [];
  constructor(private company: Company | null | undefined) {}

  resolve(ref: CiteRef): ResolvedCite {
    const k = citeKey(ref);
    const hit = this.byKey.get(k);
    if (hit) return hit;
    const { evidence, finding } = resolveCite(this.company, ref);
    const sk = sourceKey(evidence, ref);
    let n = this.bySource.get(sk);
    const isNew = n == null;
    if (n == null) { n = this.bySource.size + 1; this.bySource.set(sk, n); }
    const rc: ResolvedCite = { key: k, n, ref, evidence, finding };
    this.byKey.set(k, rc);
    if (isNew) this.list.push(rc);
    return rc;
  }

  resolveAll(refs: CiteRef[] | undefined): ResolvedCite[] {
    const seen = new Set<number>();
    return (refs ?? []).map((r) => this.resolve(r))
      .filter((c) => (seen.has(c.n) ? false : (seen.add(c.n), true)))
      .sort((a, b) => a.n - b.n);
  }
}

export function citeLabel(ev: Evidence | undefined): string {
  if (!ev) return "Source not exported";
  return ev.citation || [ev.doc_id, ev.page != null ? `p. ${ev.printed || ev.page}` : ""].filter(Boolean).join(", ") || "Source";
}

/* ------------------------------------------------------------ findings */

export interface ImpactView { kind: "dollars" | "suspect" | "proxy" | "none"; dollars: number | null; formula: string; note?: string }

export function impactView(f: Finding | undefined): ImpactView {
  const im = f?.impact;
  const formula = im?.formula ?? "";
  const suspect = im?.suspect === true;
  const note = typeof im?.suspect_note === "string" ? im.suspect_note : undefined;
  const d = isNum(im?.dollars) ? im!.dollars! : null;
  if (d != null && suspect) return { kind: "suspect", dollars: d, formula, note };
  if (d != null) return { kind: "dollars", dollars: d, formula };
  if (/proxy/i.test(formula)) return { kind: "proxy", dollars: null, formula };
  return { kind: "none", dollars: null, formula };
}

export function externalSources(f: Finding | undefined): string[] {
  const x = f?.external_sources;
  return Array.isArray(x) ? x.filter((s): s is string => typeof s === "string" && !!s) : [];
}

/** Format a peer metric in the units the finding sentence uses. */
export function metricText(f: Finding | undefined, v: number | null | undefined): string {
  if (!isNum(v)) return "n/a";
  const text = f?.finding ?? "";
  const kind = f?.signal_kind ?? "";
  if (/days/i.test(text) || /^dio|dso|dpo/.test(kind)) return `${num(v)} days`;
  if (Number.isInteger(v) && Math.abs(v) < 1000) return num(v);
  if (Math.abs(v) <= 2 && /%|pts|margin|rate|share/i.test(text + kind)) return pct(v, { digits: 1 });
  return num(v, Math.abs(v) < 10 ? 2 : 0);
}

/** Shift signals store the change as metric_value but the peer level as peer_median. */
export function isShiftMetric(f: Finding | undefined): boolean {
  return /_shift$|_change$/.test(f?.signal_kind ?? "") || /a year earlier/i.test(f?.finding ?? "");
}

export interface Factor { key: string; label: string; raw: number | null; mult: number | null; rawText: string; why: string }

/** The seven score factors as their multiplier in S (materiality_spec.md section 2). */
export function scoreFactors(f: Finding | undefined): { factors: Factor[]; s: number | null } {
  const v = f?.vector ?? {};
  const g = (k: "I_norm" | "P" | "T" | "O" | "E" | "Z" | "D") => (isNum(v[k]) ? (v[k] as number) : null);
  const I = g("I_norm"), P = g("P"), T = g("T"), O = g("O"), E = g("E"), Z = g("Z"), D = g("D");
  const two = (x: number | null) => (x == null ? "n/a" : x.toFixed(2));
  const factors: Factor[] = [
    { key: "I_norm", label: "I_norm scale", raw: I, mult: I, rawText: two(I), why: "impact / trailing operating income" },
    { key: "P", label: "P probability", raw: P, mult: P, rawText: two(P), why: "chance it happens in the window" },
    { key: "T", label: "T timing", raw: T, mult: T, rawText: two(T), why: "discount for how soon it hits" },
    { key: "O", label: "O obscurity", raw: O, mult: O, rawText: two(O), why: "1 minus coverage: not priced in" },
    { key: "E", label: "E evidence", raw: E, mult: E, rawText: two(E), why: "survived the page verifier" },
    { key: "Z", label: "Z peer z", raw: Z, mult: Z == null ? null : 1 + 0.25 * Math.max(Z, 0), rawText: Z == null ? "n/a" : `${Z > 0 ? "+" : ""}${Z.toFixed(1)}`, why: "1 + 0.25 max(Z,0)" },
    { key: "D", label: "D trend", raw: D, mult: D == null ? null : 1 + 0.25 * D, rawText: D == null ? "n/a" : `${D > 0 ? "+" : ""}${D}`, why: "1 + 0.25 D" },
  ];
  const ms = factors.map((x) => x.mult);
  const s = ms.every((m) => m != null) ? ms.reduce<number>((a, m) => a * (m as number), 1) : null;
  return { factors, s };
}

/* --------------------------------------------------------------- pins */

export interface Pin { kind: string; ref: unknown; title: string }

export const pinsKey = (t: string) => `needle.pins.${t}`;
export const memoKey = (t: string) => `needle.memo.${t}`;

export function readPins(ticker: string | null): Pin[] {
  if (!ticker) return [];
  try {
    const raw = window.localStorage.getItem(pinsKey(ticker));
    const arr: unknown = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(arr)) return [];
    return arr
      .filter((p): p is Record<string, unknown> => !!p && typeof p === "object")
      .map((p) => ({ kind: String(p.kind ?? "exhibit"), ref: p.ref, title: String(p.title ?? p.kind ?? "Exhibit") }));
  } catch {
    return [];
  }
}

export function writePins(ticker: string, pins: Pin[]) {
  try { window.localStorage.setItem(pinsKey(ticker), JSON.stringify(pins)); } catch { /* private mode */ }
}
