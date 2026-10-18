// Derived citations and marked sentences (agent/needle/cite/render.py marker grammar).
import type { Company, Evidence, Finding } from "./types";

/** Data-row cite (cite_id "row:..."): a value read from a JSON row, not a page. Withheld and derived win. */
export function isRowCite(ev: Evidence | null | undefined): boolean {
  return !!ev && ev.withheld !== true && !isDerived(ev) && (String(ev.cite_id ?? "").startsWith("row:") || !!ev.row_ref);
}

/** Derived citation: computed from operand citations (derived_from: [cite_id, ...]). Withheld wins. */
export function isDerived(ev: Evidence | null | undefined): boolean {
  return !!ev && ev.withheld !== true && Array.isArray(ev.derived_from) && ev.derived_from.length > 0;
}

const INDEX = new WeakMap<object, Map<string, Evidence>>();

/** Every citation-like object in the company file, keyed by cite_id (findings, data_citations, decide, labels.v2). */
export function citeIndex(company: Company | null | undefined): Map<string, Evidence> {
  if (!company) return new Map();
  const hit = INDEX.get(company);
  if (hit) return hit;
  const m = new Map<string, Evidence>();
  const seen = new Set<object>();
  const walk = (x: unknown, depth: number) => {
    if (!x || typeof x !== "object" || depth > 12 || seen.has(x as object)) return;
    seen.add(x as object);
    if (Array.isArray(x)) { for (const y of x) walk(y, depth + 1); return; }
    const o = x as Record<string, unknown>;
    if (typeof o.cite_id === "string" && (typeof o.doc_id === "string" || typeof o.citation === "string") && !m.has(o.cite_id)) {
      m.set(o.cite_id, o as Evidence);
    }
    for (const v of Object.values(o)) if (v && typeof v === "object") walk(v, depth + 1);
  };
  walk(company, 0);
  INDEX.set(company, m);
  return m;
}

/** Citations registered by pages that are not company-file screens (the chat), keyed by cite_id. */
const EXTRA = new Map<string, Evidence>();
export function registerCites(evs: Evidence[]) {
  for (const e of evs) if (e.cite_id) EXTRA.set(e.cite_id, e);
}

export function derivedOperands(company: Company | null | undefined, ev: Evidence): { id: string; ev?: Evidence }[] {
  const ix = citeIndex(company);
  return (ev.derived_from ?? []).map((id) => ({ id, ev: EXTRA.get(id) ?? ix.get(id) }));
}

export type MarkToken =
  | { t: "text"; s: string }
  | { t: "cite"; n: number }
  | { t: "derived"; ns: (number | "assumption")[] }
  | { t: "assumption" }
  | { t: "constant"; name: string };

/** Parse "[1]", "[1][2]", "[derived: 1, 3]", "[assumption]" markers; anything else stays text. */
export function parseMarked(s: string): MarkToken[] {
  const out: MarkToken[] = [];
  const re = /\[(\d+)\]|\[derived:\s*([^\]]+)\]|\[constant:\s*([^\]]+)\]|\[assumption\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push({ t: "text", s: s.slice(last, m.index) });
    if (m[1]) out.push({ t: "cite", n: Number(m[1]) });
    else if (m[2]) out.push({ t: "derived", ns: m[2].split(",").map((x) => x.trim()).map((x) => (/^\d+$/.test(x) ? Number(x) : "assumption")) });
    else if (m[3]) out.push({ t: "constant", name: m[3].trim() });
    else out.push({ t: "assumption" });
    last = re.lastIndex;
  }
  if (last < s.length) out.push({ t: "text", s: s.slice(last) });
  return out;
}

export function formulaMarkedOf(f: Finding | null | undefined): string | null {
  const s = f?.formula_marked ?? (f?.impact as { formula_marked?: unknown } | undefined)?.formula_marked;
  return typeof s === "string" && s.trim() ? s : null;
}

export function markedOf(f: Finding | null | undefined): string | null {
  const s = f?.sentence_marked;
  return typeof s === "string" && s.trim() ? s : null;
}

/* --------------------------------------------------------------- pitch filter */

/** League / scoring internals that never show outside /cockpit/triage. */
export const INTERNAL_TEXT = /\bscore L\b|\bL \d*\.\d+|\bS ?=|\bS \d*\.\d+|obscurity|robustness|floor[_ ]relaxed|\bprovisional\b|\bstrict\b|league(_v\d)?\b|scoring variant/i;

export function onTriage(): boolean {
  return typeof window !== "undefined" && /^#\/cockpit\/triage/.test(window.location.hash);
}

/** The text, or null when it names league / scoring internals (outside the triage route). */
export function pitchLine(s: string | null | undefined): string | null {
  if (s == null) return null;
  if (onTriage()) return s;
  return INTERNAL_TEXT.test(s) ? null : s;
}

/** Drop the lines (and "; " clauses) of a block of text that name internals. */
export function pitchText(s: string | null | undefined): string {
  if (!s) return "";
  if (onTriage()) return s;
  return s.split("\n").map((line) => line.split(/;\s+/).filter((c) => !INTERNAL_TEXT.test(c)).join("; ")).filter((l) => l.trim()).join("\n");
}

/** Evidence with league / scoring internals stripped from every text field (outside triage). */
export function pitchEvidence(ev: Evidence): Evidence {
  if (onTriage()) return ev;
  const L = (x: unknown) => (typeof x === "string" ? pitchLine(x) ?? undefined : (x as undefined));
  const T = (x: unknown) => (typeof x === "string" ? pitchText(x) : (x as undefined));
  const ex = ev.excerpt ? { before: T(ev.excerpt.before), match: T(ev.excerpt.match), after: T(ev.excerpt.after) } : ev.excerpt;
  const ver = ev.verification ? { ...ev.verification, detail: L(ev.verification.detail), status: L(ev.verification.status) } : ev.verification;
  return {
    ...ev,
    citation: L(ev.citation), doc_title: L(ev.doc_title), doc_label: L(ev.doc_label), doc_id: L(ev.doc_id),
    row_ref: pitchLine(ev.row_ref ?? null), row_check: pitchLine(ev.row_check ?? null), quote: T(ev.quote) ?? "",
    excerpt: ex, verification: ver, withheld_reason: pitchLine(ev.withheld_reason ?? null), derived_expr: pitchLine(ev.derived_expr ?? null),
    confidence_note: L(ev.confidence_note),
  };
}
