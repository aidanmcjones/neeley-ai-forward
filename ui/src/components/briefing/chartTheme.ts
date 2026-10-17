import { useEffect, useState } from "react";

// Resolve theme tokens to concrete colors for SVG attributes (Recharts sets fill as an
// attribute, where var() is unreliable). Re-reads on OS theme or data-theme changes.

const KEYS = ["purple", "frog-grey", "fg", "muted", "line", "surface"] as const;
export type ChartColors = Record<(typeof KEYS)[number], string>;

function read(): ChartColors {
  const cs = getComputedStyle(document.documentElement);
  const out = {} as ChartColors;
  for (const k of KEYS) {
    const v = cs.getPropertyValue(`--${k}`).trim().split(/\s+/).join(",");
    out[k] = v ? `rgb(${v})` : "#888";
  }
  return out;
}

export function useChartColors(): ChartColors {
  const [c, setC] = useState<ChartColors>(read);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const up = () => setC(read());
    mq.addEventListener("change", up);
    const mo = new MutationObserver(up);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq.removeEventListener("change", up); mo.disconnect(); };
  }, []);
  return c;
}
