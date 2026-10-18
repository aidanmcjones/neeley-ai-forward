// Shared fetch for ui/public/data/ (real export first, else the _sample fixture, decided by each loader)
// and the public withholding rule the citation chips and the source drawer apply.

import type { Evidence } from "./types";

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
