import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { matchMemo, useMemos } from "../lib/memos";
import type { MemoRecord, MemosFile } from "../lib/types";
import { Answer } from "../components/chat/Answer";

// The demo page (/): one column, a prompt box, cached answers. Part 1 (Find) questions answer as
// chat; Part 2 (Decide) arrives as a memo card. No model, no network: answers come from memos.json.

interface Turn { id: number; prompt: string; memo: MemoRecord | null }

const KIND_ORDER = ["needle", "findings", "finding", "product", "priced_in", "priced-in", "league", "decide", "memo", "ai_wrong", "proof"];
const kindRank = (k?: string) => { const i = KIND_ORDER.indexOf((k ?? "").toLowerCase()); return i < 0 ? 50 : i; };

function suggestionsFor(file: MemosFile | null, ticker: string | null): MemoRecord[] {
  if (!file) return [];
  const byId = new Map(file.memos.map((m) => [m.id, m]));
  const base = (file.suggested ?? []).map((id) => byId.get(id)).filter((m): m is MemoRecord => !!m);
  const out: MemoRecord[] = [];
  for (const s of base) {
    if (!s.ticker || !ticker || s.ticker === ticker) { out.push(s); continue; }
    const alt = file.memos.find((m) => m.ticker === ticker && m.kind === s.kind);
    if (alt) out.push(alt);
  }
  if (out.length < 6 && ticker) {
    for (const m of file.memos.filter((x) => x.ticker === ticker).sort((a, b) => kindRank(a.kind) - kindRank(b.kind))) {
      if (out.length >= 6) break;
      if (!out.includes(m)) out.push(m);
    }
  }
  return out.slice(0, 6);
}

export default function Chat() {
  const { file, sample, error, loading } = useMemos();
  const [params] = useSearchParams();
  const [ticker, setTicker] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sentQ = useRef<string | null>(null);

  useEffect(() => { if (file && ticker == null) setTicker(file.default_ticker ?? null); }, [file, ticker]);

  const tickers = useMemo(() => [...new Set((file?.memos ?? []).map((m) => m.ticker).filter((t): t is string => !!t))].sort(), [file]);
  const suggested = useMemo(() => suggestionsFor(file, ticker), [file, ticker]);
  const byId = useMemo(() => new Map((file?.memos ?? []).map((m) => [m.id, m])), [file]);
  const labelFor = useCallback((id: string) => byId.get(id)?.prompt ?? null, [byId]);

  const send = useCallback((prompt: string, memo?: MemoRecord) => {
    const p = prompt.trim();
    if (!p) return;
    const m = memo ?? matchMemo(file, p, ticker).memo;
    setTurns((ts) => [...ts, { id: nextId.current++, prompt: p, memo: m }]);
    setText("");
  }, [file, ticker]);

  const askId = useCallback((id: string) => { const m = byId.get(id); if (m) send(m.prompt, m); }, [byId, send]);

  // ?q= sends on load (judge links open on an answer).
  const q = params.get("q");
  useEffect(() => {
    if (!file || !q || sentQ.current === q) return;
    sentQ.current = q;
    send(q);
  }, [file, q, send]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns.length]);

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(text); }
  };

  const chip = (m: MemoRecord) => (
    <button key={m.id} type="button" onClick={() => send(m.prompt, m)}
      className="rounded-full border border-line bg-surface px-3.5 py-2 text-left text-[14px] leading-snug hover:border-purple hover:text-purple shadow-card">
      {m.format === "memo" && <span className="mr-1.5 text-[10px] font-bold uppercase tracking-wide text-purple">Memo</span>}{m.prompt}
    </button>
  );

  const grouped = useMemo(() => {
    const g = new Map<string, MemoRecord[]>();
    for (const m of file?.memos ?? []) { const k = m.kind ?? "other"; if (!g.has(k)) g.set(k, []); g.get(k)!.push(m); }
    return [...g.entries()].sort((a, b) => kindRank(a[0]) - kindRank(b[0]));
  }, [file]);

  return (
    <div className="chat-page min-h-screen flex flex-col bg-bg">
      <header data-chat-chrome className="no-print mx-auto w-full max-w-[760px] px-4 pt-8 sm:pt-12 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="font-display text-[40px] sm:text-[48px] leading-none tracking-wide text-purple" aria-label="NEEDLE">NEE<span className="text-teal">DLE</span></h1>
            <p className="mt-2 text-[15px] text-muted">Ask for a memo. Every number is cited to the page.</p>
          </div>
          {tickers.length > 0 && (
            <label className="shrink-0 mt-1 inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-[12px] font-semibold text-muted">
              <span className="sr-only">Company</span>
              <select value={ticker ?? ""} onChange={(e) => setTicker(e.target.value || null)} className="bg-transparent text-fg font-semibold outline-none">
                {tickers.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
          )}
        </div>
        {sample && <p role="note" className="mt-3 rounded-md border border-warn/50 bg-warn/10 px-3 py-1.5 text-[12px] text-warn">Sample answers: ui/public/data/memos.json was not found, so this is the 3-memo fixture in public/data/_sample/.</p>}
      </header>

      <main id="main" className="mx-auto w-full max-w-[760px] flex-1 px-4 pb-6">
        {loading && <p role="status" className="text-sm text-muted">Loading…</p>}
        {error && !file && <p role="alert" className="text-sm text-bad">{error}</p>}
        {file && turns.length === 0 && (
          <section aria-label="Suggested questions" className="no-print pt-6">
            <div className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-muted">Start here: find, then decide</div>
            <div className="flex flex-col items-start gap-2">{suggested.map(chip)}</div>
          </section>
        )}
        <ol className="space-y-8 pt-4" aria-live="polite">
          {turns.map((t, i) => (
            <li key={t.id} data-turn={t.id} className="space-y-4">
              <div className="no-print flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-purple dark:bg-purple-deep px-4 py-2.5 text-[15px] text-white">{t.prompt}</div>
              </div>
              {t.memo ? (
                <Answer memo={t.memo} instant={i < turns.length - 1} onAsk={askId} labelFor={labelFor} />
              ) : (
                <div className="space-y-3 text-[15px]">
                  <p>I can write these memos:</p>
                  <div className="flex flex-col items-start gap-2">{suggested.map(chip)}</div>
                  <details className="no-print rounded-md border border-line bg-surface px-3 py-2">
                    <summary className="cursor-pointer text-[13px] font-semibold">Show all prompts ({file?.memos.length ?? 0})</summary>
                    <div className="mt-2 space-y-3">
                      {grouped.map(([k, ms]) => (
                        <div key={k}>
                          <div className="text-[11px] font-semibold uppercase tracking-wide text-muted">{k.replace(/_/g, " ")}</div>
                          <ul className="mt-1 space-y-1">
                            {ms.map((m) => (
                              <li key={m.id}><button type="button" onClick={() => send(m.prompt, m)} className="text-left text-[13px] text-purple hover:underline">{m.prompt}{m.ticker ? <span className="text-muted"> · {m.ticker}</span> : null}</button></li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </details>
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
            <textarea id="chat-input" ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} rows={1}
              placeholder="Ask about a company, a finding, or for the CEO memo"
              className="flex-1 resize-none bg-transparent py-1.5 text-[15px] outline-none placeholder:text-muted max-h-40" />
            <button type="submit" disabled={!text.trim()} className="rounded-lg bg-purple dark:bg-purple-deep px-3.5 py-1.5 text-[14px] font-semibold text-white disabled:opacity-40">Send</button>
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted">
            <span>Cached answers{file?.generated_at ? ` · ${file.generated_at.slice(0, 10)}` : ""} · Enter to send, Shift+Enter for a new line</span>
            <Link to="/cockpit" className="underline hover:text-purple">Full cockpit</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
