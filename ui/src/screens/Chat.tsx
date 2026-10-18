import { useCallback, useEffect, useRef, useState } from "react";
import type React from "react";
import { useSearchParams } from "react-router-dom";
import { isPart1Query, isWhyCompanyQuery, PART1_PROMPT, useCompanyNames, usePart1 } from "../lib/part1";
import { Part1Answer } from "../components/chat/Part1Answer";
import type { FollowChip } from "../components/chat/Part1Answer";
import { SelectionCard } from "../components/chat/Part1Selection";

// The demo page (/): one column, one question. The only option is the case's Part 1 prompt, answered
// from data/part1 (the sealed pick, findings, product fine print and the reasoning trace). No memos load
// here; the cockpit keeps its own routes.

// kind "part1": the cached Part 1 deliverable; "selection": the why-this-company card alone; "other": anything else.
interface Turn { id: number; prompt: string; kind: "part1" | "selection" | "other"; ticker?: string }

const noFollow = (): FollowChip[] => [];

export default function Chat() {
  const part1 = usePart1();
  const { names, loading: metaLoading } = useCompanyNames();
  const nameOf = useCallback((t: string) => names[t] ?? t, [names]);
  const [params] = useSearchParams();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);
  const sentQ = useRef<string | null>(null);

  const send = useCallback((prompt: string) => {
    const p = prompt.trim();
    if (!p) return;
    let turn: Turn = { id: nextId.current++, prompt: p, kind: "other" };
    if (part1.index?.picked.length && isPart1Query(p)) turn = { ...turn, kind: "part1" };
    else if (part1.selection?.picked?.length) {
      const pk = part1.selection.picked;
      if (isWhyCompanyQuery(p, Object.entries(names).flat())) {
        const lower = p.toLowerCase();
        const named = pk.find((t) => new RegExp(`\\b${t.toLowerCase()}\\b`).test(lower) || lower.includes(nameOf(t).toLowerCase()));
        turn = { ...turn, kind: "selection", ticker: named ?? pk[0] };
      }
    }
    setTurns((ts) => [...ts, turn]);
    setText("");
  }, [part1.index, part1.selection, names, nameOf]);

  // ?q= sends on load (judge links open on an answer).
  const q = params.get("q");
  useEffect(() => {
    if (!q || sentQ.current === q || metaLoading || part1.loading) return;
    sentQ.current = q;
    send(q);
  }, [q, send, metaLoading, part1.loading]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns.length]);

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(text); }
  };

  const ready = !!part1.index?.picked.length;
  const hero = (
    <button type="button" onClick={() => send(PART1_PROMPT)} data-hero
      className="rounded-2xl border-2 border-purple bg-purple dark:bg-purple-deep px-4 py-3 text-left text-[15.5px] font-semibold leading-snug text-white shadow-card hover:opacity-95">
      <span className="mb-0.5 block text-[10.5px] font-bold uppercase tracking-[0.14em] text-white/80">Part 1</span>{PART1_PROMPT}
    </button>
  );

  return (
    <div className="chat-page min-h-screen flex flex-col bg-bg">
      <header data-chat-chrome className="no-print mx-auto w-full max-w-[760px] px-4 pt-8 sm:pt-12 pb-4">
        <h1 className="font-display text-[40px] sm:text-[48px] leading-none tracking-wide text-purple" aria-label="NEEDLE">NEE<span className="text-teal">DLE</span></h1>
        <p className="mt-2 text-[15px] text-muted">Every number is cited to the page.</p>
      </header>

      <main id="main" className="mx-auto w-full max-w-[760px] flex-1 px-4 pb-6">
        {part1.loading && <p role="status" className="text-sm text-muted">Loading…</p>}
        {part1.error && !ready && <p role="alert" className="text-sm text-bad">{part1.error}</p>}
        {ready && turns.length === 0 && (
          <section aria-label="Suggested question" className="no-print pt-6">
            <div className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-muted">Start here</div>
            <div className="flex flex-col items-start gap-2">{hero}</div>
          </section>
        )}
        <ol className="space-y-8 pt-4" aria-live="polite">
          {turns.map((t, i) => (
            <li key={t.id} data-turn={t.id} className="space-y-4">
              <div className="no-print flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-purple dark:bg-purple-deep px-4 py-2.5 text-[15px] text-white">{t.prompt}</div>
              </div>
              {t.kind === "part1" ? (
                <Part1Answer part1={part1} instant={i < turns.length - 1} nameOf={nameOf} followFor={noFollow} />
              ) : t.kind === "selection" && part1.selection ? (
                <div className="space-y-2">
                  {part1.sample && <p role="note" className="text-[12px] text-muted">Sample data: the blind reasoning pass has not run yet</p>}
                  <SelectionCard selection={part1.selection} ticker={t.ticker ?? part1.selection.picked[0]} nameOf={nameOf} seal={part1.index?.sealed} prefix={part1.prefix} />
                  {ready && <div className="no-print flex flex-col items-start gap-2">{hero}</div>}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-[14px] text-muted">This demo answers the case's Part 1 prompt. Click the chip above.</p>
                  {ready && <div className="no-print flex flex-col items-start gap-2">{hero}</div>}
                </div>
              )}
            </li>
          ))}
        </ol>
        <div ref={endRef} />
      </main>

      <div data-chat-chrome className="no-print sticky bottom-0 bg-bg/95 backdrop-blur border-t border-line">
        <form className="mx-auto w-full max-w-[760px] px-4 py-3" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <div className="flex items-end gap-2 rounded-xl border border-line bg-surface px-3 py-2 shadow-card focus-within:border-purple">
            <label htmlFor="chat-input" className="sr-only">Ask NEEDLE</label>
            <textarea id="chat-input" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} rows={1}
              placeholder="Ask the Part 1 question"
              className="flex-1 resize-none bg-transparent py-1.5 text-[15px] outline-none placeholder:text-muted max-h-40" />
            <button type="submit" disabled={!text.trim()} className="rounded-lg bg-purple dark:bg-purple-deep px-3.5 py-1.5 text-[14px] font-semibold text-white disabled:opacity-40">Send</button>
          </div>
          <div className="mt-1.5 text-[11px] text-muted">
            Cached answer{part1.index?.generated_at ? ` · ${part1.index.generated_at.slice(0, 10)}` : ""} · Enter to send, Shift+Enter for a new line
          </div>
        </form>
      </div>
    </div>
  );
}
