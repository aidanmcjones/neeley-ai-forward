import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Company } from "../../lib/types";

// Shared helpers for the Product and Forces screens (local to these two screens).

export type Tokens = Record<"purple" | "purpleBright" | "grey" | "grey2" | "teal" | "good" | "warn" | "bad" | "fg" | "muted" | "line" | "surface", string>;

const VARS: Record<keyof Tokens, string> = {
  purple: "--purple", purpleBright: "--purple-bright", grey: "--frog-grey", grey2: "--muted", teal: "--teal",
  good: "--good", warn: "--warn", bad: "--bad", fg: "--fg", muted: "--muted", line: "--line", surface: "--surface",
};

function read(): Tokens {
  const cs = getComputedStyle(document.documentElement);
  const out = {} as Tokens;
  (Object.keys(VARS) as (keyof Tokens)[]).forEach((k) => {
    const v = cs.getPropertyValue(VARS[k]).trim();
    out[k] = v ? `rgb(${v.split(/\s+/).join(",")})` : "#888";
  });
  return out;
}

/** Resolved theme colors for SVG attributes (CSS vars do not work in SVG presentation attributes). */
export function useTokens(): Tokens {
  const [t, setT] = useState<Tokens>(() => read());
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setT(read());
    mq.addEventListener?.("change", update);
    const mo = new MutationObserver(update);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
    return () => { mq.removeEventListener?.("change", update); mo.disconnect(); };
  }, []);
  return t;
}

/** Tiny inline muted-mono source note: where a cell came from. */
export function Src({ children, className = "" }: { children?: ReactNode; className?: string }) {
  if (children == null || children === "") return null;
  return <span className={`block font-mono text-[10px] leading-tight text-muted break-words ${className}`}>{children}</span>;
}

/** Status pill with text (never color alone). */
export function Flag({ tone, children, dashed = false }: { tone: "good" | "warn" | "bad" | "neutral"; children: ReactNode; dashed?: boolean }) {
  const cls = {
    good: "bg-good/15 text-good border-good/40",
    warn: "bg-warn/15 text-warn border-warn/40",
    bad: "bg-bad/15 text-bad border-bad/40",
    neutral: "bg-chip text-muted border-line",
  }[tone];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap ${dashed ? "border-dashed" : ""} ${cls}`}>
      {children}
    </span>
  );
}

const PRETTY: Record<string, string> = {
  "opdivo-qvantig": "Opdivo Qvantig", "keytruda-qlex": "Keytruda Qlex", "darzalex-faspro": "Darzalex Faspro",
};
export const drugName = (slug: string) =>
  PRETTY[slug] ?? slug.split(/[-_]/).map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w)).join(" ");

/** Maker of a drug slug, from the company's gtn_exposure rows; the product itself belongs to the ticker. */
export function makerOf(company: Company | null | undefined, slug: string): string | null {
  const row = (company?.gtn_exposure ?? []).find((g) => g.drug === slug);
  return typeof row?.company === "string" ? row.company : null;
}

export const isNum = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);
export const str = (x: unknown): string | null => (typeof x === "string" && x.trim() ? x : null);

export const TOPIC_LABEL: Record<string, string> = {
  IRA_negotiation: "IRA negotiation", MFN: "MFN pricing", biosimilar_generic: "Biosimilar / generic entry",
  gross_to_net_price: "Gross-to-net / price", guidance: "Guidance", inventory_channel: "Inventory / channel",
  pipeline: "Pipeline", tariff: "Tariffs", top_products: "Top products",
};
export const topicLabel = (t: unknown) => (typeof t === "string" ? TOPIC_LABEL[t] ?? t.replace(/_/g, " ") : "n/a");

export const tierTone = (tier: unknown): "good" | "warn" | "bad" | "neutral" => {
  const s = String(tier ?? "").toLowerCase();
  if (s.startsWith("routine")) return "good";
  if (s.startsWith("some")) return "warn";
  if (s.startsWith("rare") || s.startsWith("never")) return "bad";
  return "neutral";
};

/** Segmented control (radio group semantics). */
export function Segmented<T extends string>({ options, value, onChange, label }: {
  options: { value: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-line bg-surface p-0.5">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={`rounded px-3 py-1 text-[13px] font-semibold ${on ? "bg-purple text-white dark:bg-purple-deep" : "text-muted hover:text-fg hover:bg-surface-2"}`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
