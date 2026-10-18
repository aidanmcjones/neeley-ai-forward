// data/part1/: the cached Part 1 deliverable (sealed pick, findings table, product fine print) and the
// reasoning trace behind it. Same resolution as data.ts and memos.ts: the real export first, else the
// _sample fixture (the answer then shows a one-line sample banner). Company files load lazily.
import { useEffect, useState } from "react";
import { fetchJson, ROOT, SAMPLE } from "./data";
import { INTERNAL_TEXT } from "./cites";
import type { Evidence, Part1Company, Part1Index, Part1Selection, Part1Trace } from "./types";

export const PART1_PROMPT = "find material, non-obvious findings about one company and compare one of its key products against its rivals.";

/** The eight "Where findings hide" categories, verbatim and in the case's order. */
export const PART1_CATEGORIES = [
  "Language drift", "Gross-to-net", "Inventory and receivables growing faster than revenue",
  "Segment and product table changes", "Footnotes", "Earnings-call Q&A", "Product fine print", "Peer contrast",
];

/** The five product rows, exact keys, contract order. */
export const PART1_ROWS = ["approved uses", "boxed warnings and safety", "dosing and convenience", "patent and exclusivity timeline", "pricing and gross-to-net"];

export interface Part1State {
  index: Part1Index | null; selection: Part1Selection | null; prefix: string | null;
  sample: boolean; loading: boolean; error: string | null;
}

export function usePart1(): Part1State {
  const [st, setSt] = useState<Part1State>({ index: null, selection: null, prefix: null, sample: false, loading: true, error: null });
  useEffect(() => {
    let live = true;
    (async () => {
      for (const [base, sample] of [[`${ROOT}part1/`, false], [`${SAMPLE}part1/`, true]] as const) {
        let index: Part1Index;
        try { index = await fetchJson<Part1Index>(base, "index.json"); } catch { continue; }
        const picked = Array.isArray(index?.picked) ? index.picked.filter((t) => typeof t === "string") : [];
        let selection: Part1Selection | null = null;
        try { selection = await fetchJson<Part1Selection>(base, "selection.json"); } catch { selection = null; }
        if (live) setSt({ index: { ...index, picked }, selection, prefix: base, sample: sample || index.sample === true, loading: false, error: null });
        return;
      }
      if (live) setSt({ index: null, selection: null, prefix: null, sample: false, loading: false, error: "Could not load /data/part1/index.json" });
    })();
    return () => { live = false; };
  }, []);
  return st;
}

export const loadPart1Company = (prefix: string, t: string) => fetchJson<Part1Company>(prefix, `${t}.json`);
export const loadPart1Trace = (prefix: string, t: string) => fetchJson<Part1Trace>(prefix, `${t}_trace.json`);

/* Pitch rule: no league score, no S, no robustness words. Same scrub as Answer.tsx's INTERNAL, plus the
   shared INTERNAL_TEXT list, applied sentence by sentence to every string rendered from part1 files. */
const INTERNAL = /\bS ?= |score L\b|\bL ?= |robustness|scoring variants|vs v2|M x O x E|M × O × E|floor[_ ]relaxed|needle status|\bstatus (strict|provisional|floor relaxed|none)\b/i;
export const isInternal = (s: string) => INTERNAL.test(s) || INTERNAL_TEXT.test(s);
export function scrub(s: string | null | undefined): string {
  if (!s) return "";
  return s.split(/(?<=[.!?])\s+/).filter((x) => !isInternal(x)).join(" ");
}

/* Cite resolution. Markers [n] resolve through the nearest marker_map (n -> cite_id) against every
   evidence object in the company file; without a map, [n] is the n-th entry of the local cites. */
export function evidenceLabel(e: Evidence): Evidence {
  const page = e.page != null && (e.page as unknown) !== "" ? `p. ${e.page}` : "";
  const period = e.period && !(e.doc_title ?? "").includes(e.period) ? e.period : null;
  const citation = e.citation ?? ([e.doc_title, period, page].filter(Boolean).join(", ") || e.cite_id || e.doc_id || "Source");
  return { ...e, citation, location: e.location ?? (page || undefined), quote: e.quote ?? "" };
}

const IX = new WeakMap<object, Map<string, Evidence>>();
export function part1CiteIndex(c: Part1Company | null | undefined): Map<string, Evidence> {
  if (!c) return new Map();
  const hit = IX.get(c);
  if (hit) return hit;
  const m = new Map<string, Evidence>();
  const walk = (x: unknown, d: number) => {
    if (!x || typeof x !== "object" || d > 10) return;
    if (Array.isArray(x)) { for (const y of x) walk(y, d + 1); return; }
    const o = x as Record<string, unknown>;
    if (typeof o.cite_id === "string" && !m.has(o.cite_id) && (o.doc_id != null || o.quote != null || o.doc_title != null)) m.set(o.cite_id, evidenceLabel(o as Evidence));
    for (const v of Object.values(o)) if (v && typeof v === "object") walk(v, d + 1);
  };
  walk(c, 0);
  IX.set(c, m);
  return m;
}

export function resolver(ix: Map<string, Evidence>, map?: Record<string, string> | null, local?: Evidence[] | null) {
  return (n: number): Evidence | undefined => {
    const id = map?.[String(n)];
    if (id && ix.has(id)) return ix.get(id);
    const l = local?.find((e) => Number(e.n) === n) ?? local?.[n - 1];
    if (l) return l.cite_id && ix.has(l.cite_id) ? ix.get(l.cite_id) : evidenceLabel(l);
    return undefined;
  };
}

/* Routing: does a typed question ask for the Part 1 answer, or for the selection card? */
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9&]+/g, " ").trim();
export function isPart1Query(q: string): boolean {
  const n = norm(q);
  if (!n) return false;
  if (n === norm(PART1_PROMPT)) return true;
  if (/\bpart (1|one)\b/.test(n)) return true;
  if (/\bfind(ing)? material\b|\bmaterial non obvious\b|\bnon obvious finding/.test(n)) return true;
  if (/\bcompare\b/.test(n) && /\bproducts?\b/.test(n) && /\brivals?\b|\bcompetitors?\b/.test(n)) return true;
  // Term overlap with the prompt (matchMemo style), floor 0.6 of the prompt's content words.
  const stop = new Set(["a", "an", "the", "of", "its", "one", "about", "and", "against", "to", "for", "me"]);
  const pw = new Set(norm(PART1_PROMPT).split(" ").filter((w) => !stop.has(w)));
  const qw = n.split(" ").filter((w) => !stop.has(w));
  const hit = qw.filter((w) => pw.has(w)).length;
  return pw.size > 0 && hit / pw.size >= 0.6;
}

export function isWhyCompanyQuery(q: string, names: string[]): boolean {
  const n = norm(q);
  if (/\bwhy (this|that|the) (company|pick)\b|\bbeat the other nine\b|\bwhy did (it|they|this company) (win|beat)\b|\bwhy (was|did) .* (picked|chosen|win|beat)\b/.test(n)) return true;
  return names.some((x) => x && new RegExp(`^why (did |was |is )?${norm(x).replace(/ /g, " ")}\\b`).test(n));
}
