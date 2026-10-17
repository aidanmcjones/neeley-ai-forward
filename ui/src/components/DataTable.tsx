import { useMemo, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";

// Generic sortable table: sticky header, tabular numbers, keyboard row selection.

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** Cell content; defaults to String(row[key]). */
  render?: (row: T) => ReactNode;
  /** Value used for sorting; defaults to row[key]. Return null to sort last. */
  sortValue?: (row: T) => number | string | null | undefined;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  /** CSS width, e.g. "120px" or "30%". */
  width?: string;
  /** Plain-text header for aria when header is a node. */
  title?: string;
}

type Dir = "asc" | "desc";

export function DataTable<T>({ columns, rows, rowKey, onSelect, selectedKey, maxHeight = 480, initialSort, empty, caption, dense = false }: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, i: number) => string;
  onSelect?: (row: T) => void;
  selectedKey?: string | null;
  maxHeight?: number | string;
  initialSort?: { key: string; dir: Dir };
  empty?: ReactNode;
  caption?: string;
  dense?: boolean;
}) {
  const [sort, setSort] = useState<{ key: string; dir: Dir } | null>(initialSort ?? null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const get = col.sortValue ?? ((r: T) => (r as Record<string, unknown>)[col.key] as number | string | null | undefined);
    const m = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = get(a), vb = get(b);
      const na = va == null || (typeof va === "number" && Number.isNaN(va));
      const nb = vb == null || (typeof vb === "number" && Number.isNaN(vb));
      if (na && nb) return 0;
      if (na) return 1;
      if (nb) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * m;
      return String(va).localeCompare(String(vb)) * m;
    });
  }, [rows, columns, sort]);

  const toggle = (key: string) =>
    setSort((s) => (s?.key === key ? { key, dir: s.dir === "desc" ? "asc" : "desc" } : { key, dir: "desc" }));

  const onRowKey = (e: KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect?.(row); }
    if (e.key === "ArrowDown") { e.preventDefault(); (e.currentTarget.nextElementSibling as HTMLElement | null)?.focus(); }
    if (e.key === "ArrowUp") { e.preventDefault(); (e.currentTarget.previousElementSibling as HTMLElement | null)?.focus(); }
  };

  const pad = dense ? "px-2 py-1" : "px-3 py-2";
  const alignCls = (a?: string) => (a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left");

  return (
    <div className="overflow-auto rounded-md border border-line bg-surface" style={{ maxHeight }}>
      <table className="w-full border-collapse text-[13px] tnum">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="sticky top-0 z-10 bg-surface-2">
          <tr>
            {columns.map((c) => {
              const active = sort?.key === c.key;
              const canSort = c.sortable !== false;
              return (
                <th
                  key={c.key}
                  scope="col"
                  style={{ width: c.width }}
                  aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}
                  className={`${pad} ${alignCls(c.align)} border-b border-line text-[11px] font-semibold uppercase tracking-wide text-muted whitespace-nowrap`}
                >
                  {canSort ? (
                    <button type="button" onClick={() => toggle(c.key)} className="inline-flex items-center gap-1 hover:text-fg uppercase">
                      {c.header}
                      <span aria-hidden="true" className="font-mono">{active ? (sort!.dir === "asc" ? "▲" : "▼") : "↕"}</span>
                    </button>
                  ) : c.header}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr><td colSpan={columns.length} className="px-3 py-6 text-center text-muted">{empty ?? "No rows"}</td></tr>
          )}
          {sorted.map((row, i) => {
            const k = rowKey(row, i);
            const sel = selectedKey != null && k === selectedKey;
            return (
              <tr
                key={k}
                tabIndex={onSelect ? 0 : undefined}
                aria-selected={onSelect ? sel : undefined}
                onClick={onSelect ? () => onSelect(row) : undefined}
                onKeyDown={onSelect ? (e) => onRowKey(e, row) : undefined}
                className={`border-b border-line last:border-0 ${onSelect ? "cursor-pointer hover:bg-surface-2 focus-visible:bg-surface-2" : ""} ${sel ? "bg-chip shadow-[inset_3px_0_0_rgb(var(--purple))]" : ""}`}
              >
                {columns.map((c) => (
                  <td key={c.key} className={`${pad} ${alignCls(c.align)} align-top`}>
                    {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? "")}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
