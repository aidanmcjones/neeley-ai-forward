// memos.json: cached chat answers and CEO memos. Same loader pattern as data.ts (real export,
// else the _sample fixture). Matching: exact prompt/alias first, then term overlap with the
// retriever's synonym groups over prompt + aliases (floor 0.3).
import { useEffect, useState } from "react";
import { fetchJson, ROOT, SAMPLE } from "./data";
import { terms } from "./retrieve";
import type { Evidence, MemoCite, MemoRecord, MemosFile } from "./types";

export interface MemosState {
  file: MemosFile | null; sample: boolean; error: string | null; loading: boolean;
  /** Where the files live (real export or the _sample fixture). */
  prefix: string | null;
  /** True when `file` is the small index (memos_index.json): answers load one by one via loadMemo. */
  indexOnly: boolean;
}

const safeId = (id: string) => id.replace(/[^A-Za-z0-9_-]/g, "_");

/** Loads memos_index.json first (chips and matching paint at once); answers are fetched per memo.
 *  Without an index (plain static copy of public/), falls back to the full memos.json. */
export function useMemos(): MemosState {
  const [st, setSt] = useState<MemosState>({ file: null, sample: false, error: null, loading: true, prefix: null, indexOnly: false });
  useEffect(() => {
    let live = true;
    (async () => {
      for (const [prefix, sample] of [[ROOT, false], [SAMPLE, true]] as const) {
        try {
          const ix = await fetchJson<MemosFile>(prefix, "memos_index.json");
          if (live) setSt({ file: norm(ix), sample, error: null, loading: false, prefix, indexOnly: true });
          return;
        } catch {
          try {
            const f = await fetchJson<MemosFile>(prefix, "memos.json");
            if (live) setSt({ file: norm(f), sample, error: null, loading: false, prefix, indexOnly: false });
            return;
          } catch { /* try the next location */ }
        }
      }
      if (live) setSt({ file: null, sample: false, error: "Could not load /data/memos.json", loading: false, prefix: null, indexOnly: false });
    })();
    return () => { live = false; };
  }, []);
  return st;
}

/** One answer with its blocks and cites: data/memos/<id>.json, else the full memos.json. */
export async function loadMemo(prefix: string, id: string): Promise<MemoRecord | null> {
  try {
    return await fetchJson<MemoRecord>(prefix, `memos/${safeId(id)}.json`);
  } catch {
    const f = await fetchJson<MemosFile>(prefix, "memos.json");
    return f.memos.find((m) => m.id === id) ?? null;
  }
}

function norm(f: MemosFile): MemosFile {
  return { ...f, memos: Array.isArray(f?.memos) ? f.memos.filter((m) => m && m.id && m.prompt) : [], suggested: Array.isArray(f?.suggested) ? f.suggested : [] };
}

const normText = (s: string) => s.toLowerCase().replace(/[^a-z0-9&]+/g, " ").trim();

export interface MatchResult { memo: MemoRecord | null; score: number; how: "exact" | "fuzzy" | "none" }

/** Exact prompt/alias match, then weighted term overlap (prefers the active ticker on ties). */
export function matchMemo(file: MemosFile | null, query: string, ticker?: string | null): MatchResult {
  if (!file?.memos.length || !query.trim()) return { memo: null, score: 0, how: "none" };
  const q = normText(query);
  const exact = file.memos.filter((m) => [m.prompt, ...(m.aliases ?? [])].some((a) => normText(a) === q));
  if (exact.length) return { memo: exact.find((m) => m.ticker === ticker) ?? exact[0], score: 1, how: "exact" };

  const docs = file.memos.map((m) => ({ m, t: terms([m.prompt, ...(m.aliases ?? []), m.ticker ?? ""].join(" . ")) }));
  const df = new Map<string, number>();
  for (const d of docs) for (const t of d.t) df.set(t, (df.get(t) ?? 0) + 1);
  const idf = (t: string) => Math.log(1 + docs.length / (df.get(t) ?? 0.5));
  const qt = terms(query);
  // Tickers and company names named in the query.
  const named = new Set<string>();
  for (const m of file.memos) if (m.ticker && new RegExp(`\\b${m.ticker.toLowerCase()}\\b`).test(query.toLowerCase())) named.add(m.ticker);
  let qw = 0;
  for (const t of qt) qw += idf(t);
  let best: MatchResult = { memo: null, score: 0, how: "none" };
  for (const d of docs) {
    let inter = 0, dw = 0;
    for (const t of d.t) dw += idf(t);
    for (const t of qt) if (d.t.has(t)) inter += idf(t);
    if (!inter && ![d.m.prompt, ...(d.m.aliases ?? [])].some((a) => normText(a).split(" ").length >= 2 && ` ${q} `.includes(` ${normText(a)} `))) continue;
    const coverage = qw ? inter / qw : 0;          // how much of the question the memo answers
    const precision = dw ? inter / dw : 0;         // how much of the memo the question asks for
    let s = 0.7 * coverage + 0.3 * Math.min(1, precision * 3);
    // A multi-word alias said verbatim inside the question ("which company ...") is strong evidence.
    const padded = ` ${q} `;
    for (const a of [d.m.prompt, ...(d.m.aliases ?? [])]) {
      const na = normText(a);
      const nw = na.split(" ").length;
      if (nw >= 2 && padded.includes(` ${na} `)) { s = Math.max(s, 0.55) + 0.4; break; }
    }
    if (named.size) s *= d.m.ticker && named.has(d.m.ticker) ? 1.1 : d.m.ticker ? 0.6 : 1;
    else if (ticker) s *= d.m.ticker === ticker ? 1.25 : d.m.ticker ? 0.8 : 1.1;
    if (s > best.score) best = { memo: d.m, score: s, how: "fuzzy" };
  }
  return best.score >= 0.3 ? best : { memo: null, score: best.score, how: "none" };
}

/** Memo cite -> the Evidence shape the CiteChip / SourceDrawer already render. */
export function citeEvidence(c: MemoCite, all: MemoCite[]): Evidence {
  const page = c.page != null && c.page !== "" ? `p. ${c.page}` : "";
  const period = c.period && !(c.doc_title ?? "").includes(c.period) ? c.period : null;
  const label = [c.doc_title, period, page].filter(Boolean).join(", ") || c.cite_id || `source ${c.n}`;
  const ops = (c.derived_from ?? []).map((x) => (typeof x === "number" ? all.find((o) => o.n === x)?.cite_id : x)).filter((x): x is string => !!x);
  const ver = typeof c.verification === "string" ? { status: c.verification } : c.verification ?? null;
  const isRow = (c.cite_id ?? "").startsWith("row:");
  return {
    quote_note: (c.quote_note as string | undefined) ?? null, doc_type: (c.doc_type as string | undefined) ?? undefined,
    viewer_link: (c.viewer_link as string | undefined) ?? null, unit: (c.unit as string | undefined) ?? null,
    row_ref: isRow ? c.ref ?? null : null,
    row_check: isRow ? (typeof c.verification === "string" ? c.verification : c.verification?.detail ?? c.verification?.status ?? null) : null,
    value: c.value ?? undefined,
    doc_id: c.cite_id ?? `memo-cite-${c.n}`, cite_id: c.cite_id, citation: label, doc_title: c.doc_title ?? undefined,
    period: c.period ?? undefined, page: typeof c.page === "number" ? c.page : null, printed: c.page != null ? String(c.page) : undefined,
    location: page || undefined, quote: c.quote ?? "", excerpt: c.excerpt ?? undefined, url: c.url ?? undefined,
    withheld: c.withheld === true, withheld_reason: c.withheld_reason ?? null, verification: ver,
    derived_from: ops.length ? ops : null, derived_expr: c.derived_expr ?? null,
    verdict: isRow ? "data row" : ver?.status && ver.status !== "unverified" ? "verified" : undefined,
  };
}
