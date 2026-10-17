// Recharts LabelList content: a plain <text> to the right of a horizontal bar (no wrapping).
export interface BarLabelProps { x?: number | string; y?: number | string; width?: number | string; height?: number | string; value?: unknown }

export function barLabel(color: string, fmt: (v: unknown) => string, fontSize = 11) {
  return function BarLabel(p: BarLabelProps) {
    const x = Number(p.x ?? 0), y = Number(p.y ?? 0), w = Number(p.width ?? 0), h = Number(p.height ?? 0);
    const end = w >= 0 ? x + w + 6 : x + 6;
    return (
      <text x={end} y={y + h / 2} dy="0.35em" fill={color} fontSize={fontSize}
        style={{ fontFamily: "JetBrains Mono", fontVariantNumeric: "tabular-nums", whiteSpace: "pre" }}>
        {fmt(p.value)}
      </text>
    );
  };
}
