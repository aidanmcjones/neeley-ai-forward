// data/part2/: the cached Part 2 ("Decide") response per picked company, exported by agent/ui_part2_export.py
// from out/part2/<T>/part2.json under docs/part2/UI_CONTRACT.md. Same resolution as part1.ts: the real
// export first, else the _sample fixture (none ships today), else no Part 2 chip at all. Company files
// load lazily; the cite index and marker resolver are shared with Part 1.
import { useEffect, useState } from "react";
import { fetchJson, ROOT, SAMPLE } from "./data";
import type { Part2Block, Part2Company, Part2Index, Part2Trace } from "./types";

/** The case's own Part 2 sentence, used as the chip and as the cached prompt. */
export const PART2_PROMPT = "recommend one strategic move for the next 24 months, with a specific budget or commitment of people behind it.";
/** The label the case requires on anything a doctor or patient would see; printed from this constant, never from data. */
export const PART2_BANNER = "Student concept, not actual promotional material.";

export interface Part2State {
  index: Part2Index | null; prefix: string | null; sample: boolean; loading: boolean; error: string | null;
}

export function usePart2(): Part2State {
  const [st, setSt] = useState<Part2State>({ index: null, prefix: null, sample: false, loading: true, error: null });
  useEffect(() => {
    let live = true;
    (async () => {
      for (const [base, sample] of [[`${ROOT}part2/`, false], [`${SAMPLE}part2/`, true]] as const) {
        let index: Part2Index;
        try { index = await fetchJson<Part2Index>(base, "index.json"); } catch { continue; }
        const picked = Array.isArray(index?.picked) ? index.picked.filter((t) => typeof t === "string") : [];
        if (live) setSt({ index: { ...index, picked }, prefix: base, sample: sample || index.sample === true, loading: false, error: null });
        return;
      }
      // No Part 2 export yet: not an error, the chat simply offers no Part 2 chip.
      if (live) setSt({ index: null, prefix: null, sample: false, loading: false, error: null });
    })();
    return () => { live = false; };
  }, []);
  return st;
}

/** Picks with a Part 2 file on disk, in the Part 1 order. */
export function part2Ready(index: Part2Index | null | undefined): string[] {
  if (!index) return [];
  const avail = Array.isArray(index.available) ? index.available : index.picked;
  const missing = new Set((index.missing ?? []).map((m) => m?.ticker));
  return index.picked.filter((t) => avail.includes(t) && !missing.has(t));
}

export const loadPart2Company = (prefix: string, t: string) => fetchJson<Part2Company>(prefix, `${t}.json`);
export const loadPart2Trace = (prefix: string, t: string) => fetchJson<Part2Trace>(prefix, `${t}_trace.json`);

const str = (x: unknown) => (typeof x === "string" ? x : null);
/** The printable text of a block: the marked form when present. */
export const blockText = (b: Part2Block | null | undefined) => (b ? str(b.text_marked) ?? str(b.text) ?? "" : "");
/** A field of a record as its own block, inheriting the record's cites and marker map (the pill only when asked). */
export function field(rec: Record<string, unknown> | null | undefined, key: string, withCheck = false): Part2Block | null {
  if (!rec) return null;
  const text = str(rec[key]);
  const marked = str(rec[`${key}_marked`]);
  if (text == null && marked == null) return null;
  return {
    text, text_marked: marked,
    marker_map: (rec.marker_map as Record<string, string> | null | undefined) ?? null,
    cites: Array.isArray(rec.cites) ? (rec.cites as Part2Block["cites"]) : undefined,
    numeric_check: withCheck ? (rec.numeric_check as Part2Block["numeric_check"]) : undefined,
  };
}
export const asArray = <T,>(x: unknown): T[] => (Array.isArray(x) ? (x as T[]) : []);

/** A plain English name for the contract's move type. */
export function moveType(t: string | null | undefined): string {
  if (!t) return "";
  const m: Record<string, string> = {
    license_or_acquire: "License or acquire", pricing_or_coverage: "Pricing or coverage", portfolio_shift: "Portfolio shift",
    new_indication: "New indication", campaign: "Campaign",
  };
  if (m[t]) return m[t];
  if (t.startsWith("other:")) return t.slice(6).replace(/[_-]+/g, " ").trim();
  return t.replace(/[_-]+/g, " ");
}

/* Routing: does a typed question ask for the Part 2 answer? */
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9&]+/g, " ").trim();
export function isPart2Query(q: string): boolean {
  const n = norm(q);
  if (!n) return false;
  if (n === norm(PART2_PROMPT)) return true;
  if (/\bpart (2|two)\b/.test(n)) return true;
  if (/\bceo s? ?(move|seat|call|decision)\b|\bwhat should (the )?(ceo|management|they|it) do\b|\bstrategic move\b|\bone move\b|\bnext 24 months\b|\b24 months\b/.test(n)) return true;
  if (/\bdecide\b|\brecommend(ation)?\b|\bkill signals?\b|\bprove (you|us|it|me|them) wrong\b|\brejected alternatives?\b|\bclaims map\b|\bbudget\b/.test(n)) return true;
  return false;
}
