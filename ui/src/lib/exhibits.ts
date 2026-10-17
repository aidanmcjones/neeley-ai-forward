// Exhibit data shaping, memo pins and theme colors for Ask exhibit cards.
// Every value here is read from companies/<T>.json as exported; nothing is recomputed except
// the parsing of a year that is already printed in a source string (e.g. "Selected IPAY 2027").

import { useEffect, useRef, useState } from "react";
import type { Company, Comparison, ComparisonRow, Finding, PricePoint } from "./types";
import type { Exhibit, ExhibitKind } from "./retrieve";

/* --------------------------------------------------------------------- pins */

export interface Pin { kind: ExhibitKind | string; ref: string; title: string }
const pinKey = (t: string) => `needle.pins.${t}`;
const PIN_EVENT = "needle-pins";

export function readPins(ticker: string): Pin[] {
  try {
    const raw = window.localStorage.getItem(pinKey(ticker));
    const v = raw ? JSON.parse(raw) : [];
    return Array.isArray(v) ? v.filter((p) => p && typeof p.kind === "string") : [];
  } catch { return []; }
}

export function togglePin(ticker: string, pin: Pin): boolean {
  const pins = readPins(ticker);
  const i = pins.findIndex((p) => p.kind === pin.kind && p.ref === pin.ref);
  if (i >= 0) pins.splice(i, 1); else pins.push(pin);
  try {
    window.localStorage.setItem(pinKey(ticker), JSON.stringify(pins));
    window.dispatchEvent(new CustomEvent(PIN_EVENT));
  } catch { /* private mode: pin lives only for this render */ }
  return i < 0;
}

export function removePin(ticker: string, pin: Pin): void {
  const pins = readPins(ticker).filter((p) => !(p.kind === pin.kind && p.ref === pin.ref));
  try {
    window.localStorage.setItem(pinKey(ticker), JSON.stringify(pins));
    window.dispatchEvent(new CustomEvent(PIN_EVENT));
  } catch { /* private mode */ }
}

/** Live pin list for a ticker (updates on toggle and across tabs). */
export function usePins(ticker: string | null): Pin[] {
  const [pins, setPins] = useState<Pin[]>(() => (ticker ? readPins(ticker) : []));
  useEffect(() => {
    if (!ticker) return;
    const sync = () => setPins(readPins(ticker));
    sync();
    window.addEventListener(PIN_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(PIN_EVENT, sync); window.removeEventListener("storage", sync); };
  }, [ticker]);
  return pins;
}

/* ------------------------------------------------------------- theme colors */

const TOKENS = ["purple", "purple-bright", "frog-grey", "fg", "muted", "line", "surface", "warn"] as const;
export type ThemeColors = Record<(typeof TOKENS)[number], string>;

function readColors(): ThemeColors {
  const cs = getComputedStyle(document.documentElement);
  return Object.fromEntries(TOKENS.map((t) => [t, `rgb(${cs.getPropertyValue(`--${t}`).trim() || "0 0 0"})`])) as ThemeColors;
}

/** Resolved token colors for SVG/Recharts (CSS variables are unreliable in presentation attributes). */
export function useThemeColors(): ThemeColors {
  const [c, setC] = useState<ThemeColors>(readColors);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const sync = () => setC(readColors());
    mq.addEventListener("change", sync);
    const mo = new MutationObserver(sync);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq.removeEventListener("change", sync); mo.disconnect(); };
  }, []);
  return c;
}

/* ---------------------------------------------------------------- shaping */

export const titleCase = (s: string) => s.replace(/\b[a-z]/g, (m) => m.toUpperCase());

export function comparisonFor(c: Company, product: string): Comparison | undefined {
  const p = product.toLowerCase();
  const cmps = c.labels?.comparison ?? [];
  return cmps.find((x) => x.product.toLowerCase() === p) ?? cmps.find((x) => (x.rivals ?? []).some((r) => r.toLowerCase() === p));
}

const rowOf = (cmp: Comparison, field: string): ComparisonRow | undefined => cmp.rows?.find((r) => r.field === field);
const val = (r: ComparisonRow | undefined, slug: string) => r?.values?.[slug];

export interface TimelineMark {
  date: Date;
  iso: string;
  kind: "fda" | "company" | "mfp";
  label: string;
  source: string;
  lowerBound?: boolean;
}
export interface TimelineLane { slug: string; own: boolean; marks: TimelineMark[]; notes: string[] }

function parseDate(v: unknown): Date | null {
  if (typeof v !== "string") return null;
  const m = v.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

/** Is this drug a biologic? Only when the export itself says it came from the Purple Book. */
function isBiologic(cmp: Comparison, slug: string): boolean {
  const route = val(rowOf(cmp, "route"), slug);
  const gen = val(rowOf(cmp, "generic_or_biosimilar_status"), slug);
  return /purple_book/i.test(String(route?.source ?? "")) || /biosimilars? referencing/i.test(String(gen?.value ?? ""));
}

export function timelineLanes(c: Company, product: string): TimelineLane[] {
  const cmp = comparisonFor(c, product);
  if (!cmp) return [];
  const slugs = [cmp.product, ...(cmp.rivals ?? [])];
  const fdaRow = rowOf(cmp, "exclusivity_fda_estimate");
  const coRow = rowOf(cmp, "exclusivity_company_stated");
  const iraRow = rowOf(cmp, "ira_status");
  const mfpRow = rowOf(cmp, "mfp_per_30day");
  return slugs.map((slug) => {
    const marks: TimelineMark[] = [];
    const notes: string[] = [];
    const fda = val(fdaRow, slug);
    const fd = parseDate(fda?.value);
    const bio = isBiologic(cmp, slug);
    if (fd) marks.push({ date: fd, iso: String(fda!.value), kind: "fda", label: bio ? "FDA estimate (lower bound, biologic)" : "FDA estimate", source: String(fda?.source ?? ""), lowerBound: bio });
    const co = val(coRow, slug);
    const cd = parseDate(co?.value);
    if (cd) marks.push({ date: cd, iso: String(co!.value), kind: "company", label: "Company-stated", source: String(co?.source ?? "") });
    else notes.push("company-stated LOE not exported");
    const ira = val(iraRow, slug);
    const ipay = String(ira?.value ?? "").match(/IPAY (\d{4})/);
    if (ipay) {
      const mfp = val(mfpRow, slug)?.value;
      marks.push({ date: new Date(Number(ipay[1]), 0, 1), iso: `${ipay[1]}-01-01`, kind: "mfp",
        label: `IRA MFP effective ${ipay[1]}${typeof mfp === "number" ? ` ($${mfp.toFixed(2)}/30 days)` : ""}`, source: String(ira?.source ?? "") });
    } else if (ira?.value) notes.push(`IRA: ${String(ira.value)}`);
    return { slug, own: slug.toLowerCase() === cmp.product.toLowerCase(), marks, notes };
  });
}

export interface H2HRow { label: string; cells: { slug: string; text: string; source?: string }[] }
const H2H_FIELDS = ["indications_count", "boxed_warning", "rems", "dosing_frequency_per_year", "route", "exclusivity_fda_estimate",
  "generic_or_biosimilar_status", "ira_status", "partd_spend_latest", "gtn_exposure_call"];

export function h2hRows(c: Company, product: string): { slugs: string[]; rows: H2HRow[] } {
  const cmp = comparisonFor(c, product);
  if (!cmp) return { slugs: [], rows: [] };
  const slugs = [cmp.product, ...(cmp.rivals ?? [])];
  const rows: H2HRow[] = [];
  for (const f of H2H_FIELDS) {
    const r = rowOf(cmp, f);
    if (!r) continue;
    rows.push({
      label: r.label ?? r.field,
      cells: slugs.map((s) => {
        const v = r.values?.[s] as ({ value?: unknown; source?: string; text?: string } | undefined);
        let text: string;
        if (v?.value == null) text = "not exported";
        else if (typeof v.value === "boolean") text = v.value ? "Yes" : "No";
        else if (f === "dosing_frequency_per_year" && v.text) text = `${String(v.value)} (${v.text})`;
        else text = Array.isArray(v.value) ? v.value.join("; ") : String(v.value);
        return { slug: s, text, source: v?.source };
      }),
    });
  }
  return { slugs, rows };
}

export interface PricePanel { slug: string; own: boolean; points: PricePoint[]; mfpUnit: number | null; unit?: string }

export function pricePanels(c: Company, product: string): PricePanel[] {
  const cmp = comparisonFor(c, product);
  const slugs = cmp ? [cmp.product, ...(cmp.rivals ?? [])] : [product];
  return slugs
    .map((slug) => {
      const pts = (c.price_series?.[slug] ?? []).slice().sort((a, b) => a.year - b.year);
      const mfp = pts.find((p) => typeof p.mfp_per_unit === "number")?.mfp_per_unit ?? null;
      const unit = pts.find((p) => p.nadac_unit)?.nadac_unit as string | undefined;
      return { slug, own: !!cmp && slug.toLowerCase() === cmp.product.toLowerCase(), points: pts, mfpUnit: mfp, unit };
    })
    .filter((p) => p.points.some((x) => x.partd_per_unit != null || x.nadac_brand != null));
}

export type PeerUnit = "pct" | "pts" | "days" | "per_year" | "num";
export function peerUnit(f: Finding): PeerUnit {
  const t = f.finding.toLowerCase();
  if (/\bdays\b/.test(t)) return "days";
  if (/\/yr\b/.test(t)) return "per_year";
  if (/\bpts\b/.test(t) && !/margin \d|rate \d|% of revenue/.test(t)) return "pts";
  const v = Math.abs(f.peer?.metric_value ?? 0), m = Math.abs(f.peer?.peer_median ?? 0);
  if (/%/.test(t) && v <= 2 && m <= 2) return "pct";
  return "num";
}

export function fmtPeer(x: number | null | undefined, u: PeerUnit): string {
  if (x == null || !Number.isFinite(x)) return "n/a";
  switch (u) {
    case "pct": return `${(x * 100).toFixed(1)}%`;
    case "pts": return `${x > 0 ? "+" : ""}${(x * 100).toFixed(1)} pts`;
    case "days": return `${Math.round(x)} days`;
    case "per_year": return `${x}/yr`;
    default: return Number.isInteger(x) ? String(x) : x.toFixed(2);
  }
}

/** Default card title for an exhibit (also stored with the pin). */
export function exhibitTitle(e: Exhibit, c: Company): string {
  const drug = titleCase(e.ref);
  const cmp = comparisonFor(c, e.ref);
  const rivals = (cmp?.rivals ?? []).map(titleCase).join(", ");
  switch (e.kind) {
    case "timeline": return `${titleCase(cmp?.product ?? e.ref)} exclusivity and IRA timeline${rivals ? ` vs ${rivals}` : ""}`;
    case "h2h": return `${titleCase(cmp?.product ?? e.ref)} vs ${rivals || "rivals"}: label head-to-head`;
    case "price": return `${titleCase(cmp?.product ?? e.ref)} price per unit${rivals ? ` vs ${rivals}` : ""}`;
    case "peer": {
      const f = c.findings.find((x) => x.id === e.ref);
      const head = f?.finding.split(/ \(|;/)[0].replace(/\s+\d[\d.,%]*\s*(days|pts|%)?$/, "").trim();
      return f ? `${c.ticker} vs peer median: ${head || f.signal_kind?.replace(/_/g, " ") || "metric"}` : `Peer comparison`;
    }
    default: return drug;
  }
}

/** Measured content width of an element (so SVG text stays at its pixel size instead of scaling). */
export function useWidth<T extends HTMLElement>(fallback = 640) {
  const ref = useRef<T>(null);
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(320, Math.floor(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}
