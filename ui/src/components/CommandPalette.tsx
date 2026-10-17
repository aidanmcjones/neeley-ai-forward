import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useData } from "../lib/data";

// ⌘K / Ctrl-K command palette: the company's preset questions plus "Jump to <ticker>".
// Enter on a question goes to /ask?q=..., on a ticker switches company. Free text asks it.

interface PaletteCtx { openPalette: () => void }
const Ctx = createContext<PaletteCtx>({ openPalette: () => {} });
export const usePalette = () => useContext(Ctx);

type Item = { kind: "ask"; id: string; label: string; q: string } | { kind: "jump"; id: string; label: string; ticker: string };

export function PaletteProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const openPalette = useCallback(() => setOpen(true), []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const value = useMemo(() => ({ openPalette }), [openPalette]);
  return (
    <Ctx.Provider value={value}>
      {children}
      {open && <CommandPalette onClose={() => setOpen(false)} />}
    </Ctx.Provider>
  );
}

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const { meta, company, ticker, setTicker } = useData();
  const nav = useNavigate();
  const [text, setText] = useState("");
  const [idx, setIdx] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(document.activeElement as HTMLElement | null);

  useEffect(() => {
    input.current?.focus();
    const back = opener.current;
    return () => back?.focus?.();
  }, []);

  const items = useMemo<Item[]>(() => {
    const qs: Item[] = (company?.questions ?? []).map((q) => ({ kind: "ask", id: `q-${q.id}`, label: q.q, q: q.q }));
    const tickers = [...(meta?.companies ?? []).map((c) => ({ t: c.ticker, name: c.name })), ...(meta?.onboarded ?? []).map((t) => ({ t, name: "Onboarded" }))];
    const jumps: Item[] = tickers
      .filter((c, i, a) => c.t !== ticker && a.findIndex((x) => x.t === c.t) === i)
      .map((c) => ({ kind: "jump", id: `t-${c.t}`, label: `Jump to ${c.t}${c.name ? ` · ${c.name}` : ""}`, ticker: c.t }));
    const all = [...qs, ...jumps];
    const needle = text.trim().toLowerCase();
    const hits = needle ? all.filter((i) => i.label.toLowerCase().includes(needle)) : all;
    if (needle) hits.push({ kind: "ask", id: "free", label: `Ask: "${text.trim()}"`, q: text.trim() });
    return hits;
  }, [company, meta, ticker, text]);

  useEffect(() => setIdx(0), [text]);

  const run = (it: Item | undefined) => {
    if (!it) return;
    onClose();
    if (it.kind === "ask") nav(`/ask?q=${encodeURIComponent(it.q)}`);
    else setTicker(it.ticker);
  };

  const onKey = (e: ReactKeyboardEvent) => {
    if (e.key === "Escape") { e.preventDefault(); onClose(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(items.length - 1, i + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); run(items[idx]); }
    else if (e.key === "Tab") { e.preventDefault(); }
  };

  const activeId = items[idx] ? `pal-${items[idx].id}` : undefined;

  return (
    <div className="fixed inset-0 z-[60] no-print flex items-start justify-center pt-[12vh]">
      <div className="absolute inset-0 bg-fg/30" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-label="Ask NEEDLE command palette" className="relative w-[640px] rounded-xl border border-line bg-surface shadow-drawer overflow-hidden" onKeyDown={onKey}>
        <div className="flex items-center gap-2 border-b border-line px-4">
          <span aria-hidden="true" className="text-teal">✦</span>
          <input
            ref={input}
            value={text}
            onChange={(e) => setText(e.target.value)}
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-list"
            aria-activedescendant={activeId}
            placeholder={`Ask about ${ticker ?? "a company"}, or jump to a ticker…`}
            className="flex-1 bg-transparent py-3 text-[15px] outline-none placeholder:text-muted"
          />
          <kbd className="font-mono text-[11px] text-muted border border-line rounded px-1.5 py-0.5">Esc</kbd>
        </div>
        <ul id="palette-list" role="listbox" className="max-h-[50vh] overflow-y-auto py-1">
          {items.length === 0 && <li className="px-4 py-3 text-sm text-muted">No presets for {ticker}. Type a question and press Enter.</li>}
          {items.map((it, i) => (
            <li
              key={it.id}
              id={`pal-${it.id}`}
              role="option"
              aria-selected={i === idx}
              onMouseEnter={() => setIdx(i)}
              onClick={() => run(it)}
              className={`flex items-center gap-3 px-4 py-2 cursor-pointer text-sm ${i === idx ? "bg-chip" : ""}`}
            >
              <span className={`font-mono text-[10px] uppercase w-10 shrink-0 ${it.kind === "ask" ? "text-teal" : "text-purple"}`}>{it.kind === "ask" ? "Ask" : "Go"}</span>
              <span className="truncate">{it.label}</span>
            </li>
          ))}
        </ul>
        <div className="border-t border-line px-4 py-2 text-[11px] text-muted font-mono">↑↓ move · Enter run · Esc close</div>
      </div>
    </div>
  );
}
