import { useCallback, useEffect, useRef, useState } from "react";
import type React from "react";
import { useSearchParams } from "react-router-dom";
import { isPart1Query, isWhyCompanyQuery, PART1_PROMPT, useCompanyNames, usePart1 } from "../lib/part1";
import { isPart2Query, PART2_PROMPT, part2Ready, usePart2 } from "../lib/part2";
import { Part1Answer } from "../components/chat/Part1Answer";
import type { FollowChip } from "../components/chat/Part1Answer";
import { Part2Answer } from "../components/chat/Part2Answer";
import { SelectionCard } from "../components/chat/Part1Selection";

// The demo page (/): one column, two questions. The chips are the case's own Part 1 and Part 2 prompts,
// answered from data/part1 (the sealed pick, findings, product fine print, reasoning trace) and data/part2
// (the CEO move, its case, the rejected options, kill signals, evidence, any promo piece with its claims
// map). The Part 2 chip appears only when data/part2/index.json lists a finished company.

// kind "part1": the cached Part 1 deliverable; "part2": the cached Part 2 move; "selection": the
// why-this-company card alone; "other": anything else.
interface Turn { id: number; prompt: string; kind: "part1" | "part2" | "selection" | "other"; ticker?: string; finding?: number }

export default function Chat() {
  const part1 = usePart1();
  const part2 = usePart2();
  const { names, loading: metaLoading } = useCompanyNames();
  const nameOf = useCallback((t: string) => names[t] ?? t, [names]);
  const [params] = useSearchParams();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);
  const sentQ = useRef<string | null>(null);

  const ready = !!part1.index?.picked.length;
  const ready2 = part2Ready(part2.index).length > 0;

  // The pick a typed question names, by ticker or company name.
  const namedPick = useCallback((p: string): string | undefined => {
    const pk = part1.selection?.picked ?? part1.index?.picked ?? [];
    const lower = p.toLowerCase();
    return pk.find((t) => new RegExp(`\\b${t.toLowerCase()}\\b`).test(lower) || lower.includes(nameOf(t).toLowerCase()));
  }, [part1.selection, part1.index, nameOf]);

  const push = useCallback((turn: Omit<Turn, "id">) => {
    setTurns((ts) => [...ts, { ...turn, id: nextId.current++ }]);
  }, []);

  const send = useCallback((prompt: string) => {
    const p = prompt.trim();
    if (!p) return;
    let turn: Omit<Turn, "id"> = { prompt: p, kind: "other" };
    if (ready2 && isPart2Query(p)) turn = { ...turn, kind: "part2", ticker: namedPick(p) };
    else if (ready && isPart1Query(p)) turn = { ...turn, kind: "part1", ticker: namedPick(p) };
    else if (part1.selection?.picked?.length && isWhyCompanyQuery(p, Object.entries(names).flat())) {
      turn = { ...turn, kind: "selection", ticker: namedPick(p) ?? part1.selection.picked[0] };
    }
    push(turn);
    setText("");
  }, [ready, ready2, part1.selection, names, namedPick, push]);

  // ?q= sends on load (judge links open on an answer).
  const q = params.get("q");
  useEffect(() => {
    if (!q || sentQ.current === q || metaLoading || part1.loading || part2.loading) return;
    sentQ.current = q;
    send(q);
  }, [q, send, metaLoading, part1.loading, part2.loading]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns.length]);

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(text); }
  };

  // Cross links between the two answers: Part 1 offers the move for its company; Part 2 opens the findings.
  const openPart2 = useCallback((t: string) => push({ prompt: PART2_PROMPT, kind: "part2", ticker: t }), [push]);
  const openPart1 = useCallback((t: string, n?: number) => push({ prompt: PART1_PROMPT, kind: "part1", ticker: t, finding: n }), [push]);
  const followFor = useCallback((t: string): FollowChip[] => (
    ready2 ? [{ key: `p2:${t}`, label: `Part 2: the CEO move for ${nameOf(t)}`, onClick: () => openPart2(t) }] : []
  ), [ready2, nameOf, openPart2]);

  const chip = (part: "Part 1" | "Part 2", prompt: string) => (
    <button key={part} type="button" onClick={() => send(prompt)} data-hero
      className="rounded-2xl border-2 border-purple bg-purple dark:bg-purple-deep px-4 py-3 text-left text-[15.5px] font-semibold leading-snug text-white shadow-card hover:opacity-95">
      <span className="mb-0.5 block text-[10.5px] font-bold uppercase tracking-[0.14em] text-white/80">{part}{part === "Part 2" ? ": CEO move" : ""}</span>{prompt}
    </button>
  );
  const chips = (
    <div className="no-print flex flex-col items-start gap-2">
      {ready && chip("Part 1", PART1_PROMPT)}
      {ready2 && chip("Part 2", PART2_PROMPT)}
    </div>
  );
  const both = ready && ready2;

  return (
    <div className="chat-page min-h-screen flex flex-col bg-bg">
      <header data-chat-chrome className="no-print mx-auto w-full max-w-[760px] px-4 pt-8 sm:pt-12 pb-4">
        <h1 className="font-display text-[40px] sm:text-[48px] leading-none tracking-wide text-purple" aria-label="NEEDLE">NEE<span className="text-teal">DLE</span></h1>
        <p className="mt-2 text-[15px] text-muted">Every number is cited to the page.</p>
      </header>

      <main id="main" className="mx-auto w-full max-w-[760px] flex-1 px-4 pb-6">
        {(part1.loading || part2.loading) && <p role="status" className="text-sm text-muted">Loading…</p>}
        {part1.error && !ready && <p role="alert" className="text-sm text-bad">{part1.error}</p>}
        {ready && turns.length === 0 && (
          <section aria-label="Suggested questions" className="no-print pt-6">
            <div className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-muted">Start here</div>
            {chips}
          </section>
        )}
        <ol className="space-y-8 pt-4" aria-live="polite">
          {turns.map((t, i) => (
            <li key={t.id} data-turn={t.id} className="space-y-4">
              <div className="no-print flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-purple dark:bg-purple-deep px-4 py-2.5 text-[15px] text-white">{t.prompt}</div>
              </div>
              {t.kind === "part1" ? (
                <Part1Answer part1={part1} instant={i < turns.length - 1} nameOf={nameOf} followFor={followFor} startTicker={t.ticker} focusFinding={t.finding} />
              ) : t.kind === "part2" ? (
                <Part2Answer part2={part2} part1={part1} instant={i < turns.length - 1} nameOf={nameOf} startTicker={t.ticker} onPart1={openPart1} />
              ) : t.kind === "selection" && part1.selection ? (
                <div className="space-y-2">
                  {part1.sample && <p role="note" className="text-[12px] text-muted">Sample data: the blind reasoning pass has not run yet</p>}
                  <SelectionCard selection={part1.selection} ticker={t.ticker ?? part1.selection.picked[0]} nameOf={nameOf} seal={part1.index?.sealed} prefix={part1.prefix} />
                  {chips}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-[14px] text-muted">This demo answers the case's {both ? "Part 1 and Part 2 prompts. Click a chip" : "Part 1 prompt. Click the chip"} above.</p>
                  {chips}
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
              placeholder={both ? "Ask the Part 1 or Part 2 question" : "Ask the Part 1 question"}
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
