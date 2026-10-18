// Typed loaders for ui/public/data/ (written by `python -m agent.ui_export`).
//
// Resolution: the app first looks for data/meta.json. If it is missing, it falls back to
// data/_sample/ (a tiny smoke-test fixture) and every screen shows an amber "sample data"
// banner. A missing file after that is reported honestly by name, never silently blanked.

import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { CiteRef, Company, Evidence, Finding, LeagueRow, Meta, Proof } from "./types";
import { explainedByFootnote } from "./cites";

export type * from "./types";

export const ROOT = `${import.meta.env.BASE_URL}data/`;
export const SAMPLE = `${ROOT}_sample/`;

export class DataError extends Error {
  constructor(public readonly file: string, detail?: string) {
    super(`Could not load /data/${file}${detail ? ` (${detail})` : ""}`);
  }
}

const cache = new Map<string, Promise<unknown>>();

export async function fetchJson<T>(prefix: string, file: string): Promise<T> {
  const url = prefix + file;
  let p = cache.get(url) as Promise<T> | undefined;
  if (!p) {
    p = (async () => {
      let res: Response;
      try {
        res = await fetch(url, { headers: { Accept: "application/json" } });
      } catch {
        throw new DataError(file, "network error");
      }
      if (!res.ok) throw new DataError(file, `HTTP ${res.status}`);
      const text = await res.text();
      try {
        return JSON.parse(text) as T;
      } catch {
        // Dev servers answer missing files with index.html; treat as missing.
        throw new DataError(file, "not JSON");
      }
    })();
    cache.set(url, p);
    p.catch(() => cache.delete(url));
  }
  return p;
}

export interface Source { prefix: string; sample: boolean }

/** Find meta.json in the real export, else the sample fixture. */
export async function loadMeta(): Promise<{ meta: Meta; source: Source }> {
  try {
    const meta = await fetchJson<Meta>(ROOT, "meta.json");
    return { meta: normalizeMeta(meta), source: { prefix: ROOT, sample: false } };
  } catch (realErr) {
    try {
      const meta = await fetchJson<Meta>(SAMPLE, "meta.json");
      return { meta: normalizeMeta(meta), source: { prefix: SAMPLE, sample: true } };
    } catch {
      throw realErr;
    }
  }
}

function normalizeMeta(m: Meta): Meta {
  return { ...m, companies: Array.isArray(m?.companies) ? m.companies : [] };
}

export const loadLeague = (s: Source) =>
  fetchJson<LeagueRow[]>(s.prefix, "league.json").then((r) => (Array.isArray(r) ? r : []));
export const loadCompany = (s: Source, ticker: string) =>
  fetchJson<Company>(s.prefix, `companies/${ticker}.json`).then((c) => ({
    ...c,
    ticker: c?.ticker ?? ticker,
    findings: Array.isArray(c?.findings) ? c.findings : [],
  }));
export const loadProof = (s: Source) => fetchJson<Proof>(s.prefix, "proof.json");

/* ------------------------------------------------------------------ helpers */

/** Resolve a {finding_id, i} cite into its evidence (with the finding's verdict attached). */
export function resolveCite(company: Company | null | undefined, ref: CiteRef): { finding?: Finding; evidence?: Evidence } {
  const finding = company?.findings.find((f) => f.id === ref.finding_id);
  const ev = finding?.evidence?.[ref.i ?? 0];
  return { finding, evidence: ev ? { ...ev, verdict: ev.verdict ?? finding?.verdict } : undefined };
}

export function findNeedle(company: Company | null | undefined): Finding | undefined {
  if (!company) return undefined;
  // The pitch-facing needle (needle_id_rule) wins; the league needle (needle_id) is internal triage.
  const ok = (f: Finding | undefined) => (f && !explainedByFootnote(f) ? f : undefined);
  const rule = ok(typeof company.needle_id_rule === "string" ? company.findings.find((f) => f.id === company.needle_id_rule) : undefined);
  if (rule) return rule;
  const byId = ok(company.needle_id ? company.findings.find((f) => f.id === company.needle_id) : undefined);
  if (byId) return byId;
  if (company.needle_id_rule || company.needle_id) return undefined;
  // v3: needle status "none" means no row qualifies; never promote another row to needle.
  if (needleNone(company)) return undefined;
  return company.findings[0];
}

export function needleNone(company: Company | null | undefined): boolean {
  if (typeof company?.needle_id_rule === "string" && company.needle_id_rule) return false;
  return String(company?.needle_status ?? "").replace(/\s+/g, "_").toLowerCase() === "none";
}

/** Highest-scored finding (shown instead of a needle when none qualifies). */
export function topFinding(company: Company | null | undefined): Finding | undefined {
  if (!company?.findings.length) return undefined;
  return [...company.findings].filter((f) => !explainedByFootnote(f)).sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0];
}

/* ------------------------------------------------------------- base context */

interface BaseState {
  meta: Meta | null;
  league: LeagueRow[] | null;
  source: Source | null;
  loading: boolean;
  error: string | null;
}

const BaseContext = createContext<BaseState>({ meta: null, league: null, source: null, loading: true, error: null });

/* ---------------------------------------------------------- company context */

export interface CompanyCtx { ticker: string | null; setTicker: (t: string) => void }
export const CompanyContext = createContext<CompanyCtx>({ ticker: null, setTicker: () => {} });
export const useCompany = () => useContext(CompanyContext);

const LS_KEY = "needle.ticker";

function readUrlTicker(): string | null {
  // HashRouter: the query may sit before the hash (/?t=BMY#/) or inside it (#/briefing?t=BMY).
  const fromSearch = new URLSearchParams(window.location.search).get("t");
  const hashQ = window.location.hash.split("?")[1];
  const fromHash = hashQ ? new URLSearchParams(hashQ).get("t") : null;
  return (fromHash || fromSearch)?.toUpperCase() ?? null;
}

function readStoredTicker(): string | null {
  try { return window.localStorage.getItem(LS_KEY); } catch { return null; }
}

function storeTicker(t: string) {
  try { window.localStorage.setItem(LS_KEY, t); } catch { /* private mode: ignore */ }
}

/** Keep a ?t= in the URL in step with the picked company, so a hard reload keeps the choice. */
function syncUrlTicker(t: string) {
  const { pathname, search, hash } = window.location;
  const sp = new URLSearchParams(search);
  const [hpath, hq] = hash.split("?");
  const hp = new URLSearchParams(hq ?? "");
  const inSearch = sp.has("t") && sp.get("t")!.toUpperCase() !== t;
  const inHash = hp.has("t") && hp.get("t")!.toUpperCase() !== t;
  if (!inSearch && !inHash) return;
  if (inSearch) sp.set("t", t);
  if (inHash) hp.set("t", t);
  const s = sp.toString(), h = hp.toString();
  const href = `${pathname}${s ? `?${s}` : ""}${hpath}${h ? `?${h}` : ""}`;
  // Search-only change: rewrite in place. Hash change: replace so the router sees it.
  if (inHash) window.location.replace(href);
  else window.history.replaceState(window.history.state, "", href);
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [base, setBase] = useState<BaseState>({ meta: null, league: null, source: null, loading: true, error: null });
  const [ticker, setTickerState] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const { meta, source } = await loadMeta();
        let league: LeagueRow[] | null = null;
        let error: string | null = null;
        try { league = await loadLeague(source); } catch (e) { error = (e as Error).message; }
        if (!live) return;
        const known = new Set([...meta.companies.map((c) => c.ticker), ...(meta.onboarded ?? [])]);
        const pick = [readUrlTicker(), readStoredTicker(), meta.default_ticker, meta.companies[0]?.ticker]
          .find((t): t is string => !!t && known.has(t));
        setTickerState(pick ?? meta.default_ticker ?? null);
        setBase({ meta, league, source, loading: false, error });
      } catch (e) {
        if (live) setBase({ meta: null, league: null, source: null, loading: false, error: (e as Error).message });
      }
    })();
    return () => { live = false; };
  }, []);

  const setTicker = useCallback((t: string) => {
    const up = t.toUpperCase();
    setTickerState(up);
    storeTicker(up);
    syncUrlTicker(up);
  }, []);

  const companyValue = useMemo(() => ({ ticker, setTicker }), [ticker, setTicker]);

  return createElement(BaseContext.Provider, { value: base },
    createElement(CompanyContext.Provider, { value: companyValue }, children));
}

/* ------------------------------------------------------------------ useData */

export interface DataState {
  meta: Meta | null;
  league: LeagueRow[] | null;
  /** Selected company's JSON (null while loading or on error). */
  company: Company | null;
  /** proof.json, only fetched when useData({ proof: true }). */
  proof: Proof | null;
  ticker: string | null;
  setTicker: (t: string) => void;
  /** League row for the selected ticker. */
  leagueRow: LeagueRow | null;
  /** 1-based league rank for the selected ticker. */
  rank: number | null;
  loading: boolean;
  /** Honest error, e.g. "Could not load /data/companies/BMY.json (HTTP 404)". */
  error: string | null;
  /** True when serving the _sample fixture instead of the real export. */
  sample: boolean;
  /** Where data files resolve from ({prefix: "<base>data/" or "<base>data/_sample/", sample}); null while loading. */
  source: Source | null;
}

export function useData(opts: { proof?: boolean } = {}): DataState {
  const base = useContext(BaseContext);
  const { ticker, setTicker } = useCompany();
  const [company, setCompany] = useState<{ t: string; c: Company | null; err: string | null } | null>(null);
  const [proof, setProof] = useState<{ p: Proof | null; err: string | null } | null>(null);

  useEffect(() => {
    if (!base.source || !ticker) return;
    let live = true;
    loadCompany(base.source, ticker).then(
      (c) => live && setCompany({ t: ticker, c, err: null }),
      (e) => live && setCompany({ t: ticker, c: null, err: (e as Error).message }),
    );
    return () => { live = false; };
  }, [base.source, ticker]);

  useEffect(() => {
    if (!opts.proof || !base.source) return;
    let live = true;
    loadProof(base.source).then(
      (p) => live && setProof({ p, err: null }),
      (e) => live && setProof({ p: null, err: (e as Error).message }),
    );
    return () => { live = false; };
  }, [opts.proof, base.source]);

  const current = company && company.t === ticker ? company : null;
  const idx = base.league && ticker ? base.league.findIndex((r) => r.ticker === ticker) : -1;
  const loading = base.loading || (!!ticker && !!base.source && !current) || (!!opts.proof && !!base.source && !proof);

  return {
    meta: base.meta,
    league: base.league,
    company: current?.c ?? null,
    proof: proof?.p ?? null,
    ticker,
    setTicker,
    leagueRow: idx >= 0 ? base.league![idx] : null,
    rank: idx >= 0 ? idx + 1 : null,
    loading,
    error: base.error ?? current?.err ?? (opts.proof ? proof?.err ?? null : null),
    sample: !!base.source?.sample,
    source: base.source,
  };
}

/* ------------------------------------------------------------ withheld cites */

/** True when the public rule withheld this citation's quote, excerpt and links. */
export function isWithheld(ev: Evidence | null | undefined): boolean {
  return ev?.withheld === true;
}

/** Short reason for a withheld citation: "licensed source" or "unverified citation". */
export function withheldReason(ev: Evidence): string {
  const lic = ev.license;
  const r = String(ev.withheld_reason ?? "");
  if ((lic != null && lic !== "") || /licen[sc]ed|bloomberg|wrds/i.test(r)) return "licensed source";
  if (ev.doc_type === "machine_data" || ev.verification?.status === "machine_data" || /machine data/i.test(r)) return "machine-readable data row";
  return "unverified citation";
}
