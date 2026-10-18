import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Evidence, NumericCheck, Part2Block, Part2Company, Part2RulesCheck, Part2Trace } from "../../lib/types";
import type { Part1State } from "../../lib/part1";
import { evidenceLabel, part1CiteIndex, resolver, scrub } from "../../lib/part1";
import type { Part2State } from "../../lib/part2";
import { asArray, blockText, field, loadPart2Company, loadPart2Trace, moveType, PART2_BANNER, part2Ready } from "../../lib/part2";
import { registerCites } from "../../lib/cites";
import { CiteChip } from "../CiteChip";
import { NumericPill } from "../NumericCheck";
import { Md } from "./Md";
import { Math_ } from "./Part1Answer";
import { Part2TraceView } from "./Part2Trace";

// The Part 2 answer in the case's "Decide" order: the move in one sentence; the case for it (the Part 1
// findings that drive it, the cost, the return, the math step by step); the two rejected alternatives; the
// kill signals for months 6 to 12; why it will work and what the evidence cannot tell us; any doctor- or
// patient-facing piece under the student-concept label with its claims map; the numeric pill; the trace.
// Every string comes from data/part2/<T>.json; nothing here is written by the UI.

type Ix = Map<string, Evidence>;
const failed = (c?: NumericCheck | null) => c?.status === "failed" || c?.status === "unchecked";

/** One cited block: marked text with chips, the math on demand, the numeric pill when the block carries one. */
function Block({ b, ix, lead, empty = "Not exported", className = "" }: { b?: Part2Block | null; ix: Ix; lead?: ReactNode; empty?: string; className?: string }) {
  if (!b) return <div className={`text-muted ${className}`}>{lead}{empty}</div>;
  if (failed(b.numeric_check)) return <div className={`text-muted ${className}`}>{lead}Withheld: this block did not pass the numeric gate</div>;
  const cite = resolver(ix, b.marker_map, b.cites);
  const t = scrub(blockText(b));
  // Paragraph breaks in the data stay paragraphs; the pill shows only when the block states numbers.
  const paras = t.split(/\n+/).map((x) => x.trim()).filter(Boolean);
  const check = b.numeric_check && b.numeric_check.status !== "no_numbers" ? b.numeric_check : null;
  return (
    <div className={className}>
      {paras.length === 0 ? <>{lead}<span className="text-muted">{empty}</span></>
        : paras.length === 1 ? <>{lead}<Md md={paras[0]} cite={cite} /></>
        : paras.map((x, i) => <p key={i} className={i ? "mt-2" : ""}>{i === 0 && lead}<Md md={x} cite={cite} /></p>)}
      <Math_ math={null} cite={cite} check={check} />
    </div>
  );
}

function Section({ n, title, sub, children }: { n: number; title: string; sub?: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="space-y-2">
      <h3 className="text-[16px] font-semibold leading-tight"><span className="mr-2 font-mono text-[12px] text-muted">{n}</span>{title}{sub && <span className="ml-2 text-[12.5px] font-normal text-muted">{sub}</span>}</h3>
      {children}
    </section>
  );
}

function Th({ children }: { children: ReactNode }) {
  return <th scope="col" className="px-2.5 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-muted">{children}</th>;
}

const Label = ({ children }: { children: ReactNode }) => <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-muted">{children}</div>;

function Rules({ rc }: { rc?: Part2RulesCheck | null }) {
  const rules: [string, string][] = [
    ["approved_uses_only", "claims only for approved uses"], ["risks_prominent", "risks as prominent as benefits"],
    ["h2h_only", "comparisons only with head-to-head evidence"], ["no_testimonials", "no invented testimonials or likenesses"],
    ["labelled", "labelled as a student concept"], ["claims_map_present", "claims map present"],
  ];
  const r = (rc ?? {}) as Record<string, unknown>;
  return (
    <ul className="flex flex-wrap gap-1.5 text-[11.5px]" aria-label="Promotion rules check">
      {rules.map(([k, label]) => {
        const v = r[k];
        const ok = v === true;
        return (
          <li key={k} className={`rounded border px-1.5 py-px ${ok ? "border-good/50 bg-good/10 text-good" : "border-bad/50 bg-bad/10 text-bad"}`}>
            <span aria-hidden="true">{ok ? "✓" : "✗"}</span> {label}{v == null ? " (not checked)" : ""}
          </li>
        );
      })}
    </ul>
  );
}

export function Part2Answer({ part2, part1, instant, nameOf, startTicker, onPart1 }: {
  part2: Part2State; part1: Part1State; instant: boolean; nameOf: (t: string) => string;
  startTicker?: string;
  /** Open the Part 1 answer for a ticker, at a finding when n is given. */
  onPart1: (t: string, n?: number) => void;
}) {
  const picked = part2.index?.picked?.length ? part2.index.picked : part1.index?.picked ?? [];
  const ready = part2Ready(part2.index);
  const missing = new Set(picked.filter((t) => !ready.includes(t)));
  const [active, setActive] = useState<string>(startTicker && ready.includes(startTicker) ? startTicker : ready[0] ?? picked[0] ?? "");
  const [cos, setCos] = useState<Map<string, Part2Company | Error>>(new Map());
  const [trs, setTrs] = useState<Map<string, Part2Trace | Error>>(new Map());
  const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [stage, setStage] = useState(instant || reduce ? 2 : 0);
  const topRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefix = part2.prefix;
    if (!prefix) return;
    let live = true;
    for (const t of ready) {
      loadPart2Company(prefix, t).then((c) => live && setCos((m) => new Map(m).set(t, { ...c, ticker: c?.ticker ?? t })), (e) => live && setCos((m) => new Map(m).set(t, e as Error)));
      loadPart2Trace(prefix, t).then((x) => live && setTrs((m) => new Map(m).set(t, x)), (e) => live && setTrs((m) => new Map(m).set(t, e as Error)));
    }
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [part2.prefix, ready.join(",")]);

  const co = cos.get(active);
  const c = co && !(co instanceof Error) ? co : null;
  const tr = trs.get(active);
  const trace = tr && !(tr instanceof Error) ? tr : null;
  const ix = useMemo(() => part1CiteIndex(c as never), [c]);
  useEffect(() => { registerCites([...ix.values()]); }, [ix]);

  useEffect(() => {
    if (stage >= 2 || !c) return;
    const t = window.setTimeout(() => setStage(2), 700);
    return () => window.clearTimeout(t);
  }, [stage, c]);

  const name = c?.company ?? nameOf(active);
  const move = c?.move ?? null;
  const budget = move?.budget ?? null;
  const drivers = asArray<NonNullable<Part2Company["drivers"]>[number]>(c?.drivers);
  const cf = c?.case_for ?? null;
  const steps = asArray<NonNullable<NonNullable<Part2Company["case_for"]>["math_steps"]>[number]>(cf?.math_steps);
  const rejected = asArray<NonNullable<Part2Company["rejected"]>[number]>(c?.rejected);
  const kills = asArray<NonNullable<Part2Company["kill_signals"]>[number]>(c?.kill_signals);
  const ev = c?.evidence ?? null;
  const unresolved = asArray<NonNullable<Part2Company["unresolved"]>[number]>(c?.unresolved);
  const promo = c?.promo ?? null;
  const pieces = asArray<NonNullable<NonNullable<Part2Company["promo"]>["pieces"]>[number]>(promo?.pieces);
  const claims = asArray<NonNullable<NonNullable<Part2Company["promo"]>["claims_map"]>[number]>(promo?.claims_map);
  const hasMaterial = promo?.has_material === true;
  const risksOk = promo?.rules_check?.risks_prominent === true;
  const labelledOk = promo?.rules_check?.labelled === true;
  const budgetOk = !!budget && !failed(budget.numeric_check) && (budget.numeric_check?.status === "passed");
  const budgetLine = budgetOk ? [
    typeof budget?.amount_usd === "number" && Number.isFinite(budget.amount_usd) ? `$${budget.amount_usd.toLocaleString("en-US")}` : "",
    budget?.people != null && budget.people !== "" ? `${budget.people} people` : "",
    budget?.period ? scrub(String(budget.period)) : "",
  ].filter(Boolean).join(" · ") : "";

  const follow = [
    ...ready.filter((t) => t !== active).map((t) => ({ key: `co:${t}`, label: `Show pick ${picked.indexOf(t) + 1}: ${nameOf(t)} (${t})`, onClick: () => { setActive(t); topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); } })),
    { key: "p1", label: `Part 1 findings for ${name}`, onClick: () => onPart1(active) },
  ];

  return (
    <div ref={topRef} className="min-w-0 space-y-5 text-[15px] leading-relaxed" onClick={() => { if (stage < 2) setStage(2); }}>
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-teal">Part 2: Decide</div>
          <h2 className="text-[22px] font-semibold leading-tight">{name} <span className="font-mono text-[15px] text-muted">{active}</span></h2>
        </div>
        {picked.length > 1 && (
          <div role="tablist" aria-label="Picked companies" className="ml-auto inline-flex rounded-full border border-line bg-surface p-0.5">
            {picked.map((t, i) => (
              <button key={t} type="button" role="tab" aria-selected={t === active} disabled={missing.has(t)}
                title={missing.has(t) ? `Pick ${i + 1} (${t}) is still being written` : undefined}
                onClick={(e) => { e.stopPropagation(); setActive(t); }}
                className={`rounded-full px-3 py-1 text-[12.5px] font-semibold ${t === active ? "bg-purple text-white dark:bg-purple-deep" : missing.has(t) ? "cursor-not-allowed text-muted/60" : "text-muted hover:text-purple"}`}>
                {i + 1} <span className="font-mono">{t}</span>{missing.has(t) && <span className="ml-1 text-[10px] font-normal italic">writing</span>}
              </button>
            ))}
          </div>
        )}
        {!ready.length && <p role="note" className="w-full text-[12px] text-muted">The Part 2 answers are still being written.</p>}
        {startTicker && missing.has(startTicker) && ready.length > 0 && (
          <p role="note" className="w-full text-[12px] text-muted">The move for {nameOf(startTicker)} is still being written; showing {nameOf(active)}.</p>
        )}
        {part2.sample && <p role="note" title={part2.index?.sample_note} className="w-full text-[12px] text-muted">Sample data: the Part 2 pass has not run yet</p>}
      </header>

      {co instanceof Error && <p role="alert" className="text-[14px] text-bad">Could not load data/part2/{active}.json.</p>}
      {!co && ready.length > 0 && <p role="status" className="text-[14px] text-muted">Loading the cited answer…</p>}

      {c && (
        <>
          <section aria-label="The move" className="rounded-md border-l-4 border-teal bg-chip/60 px-4 py-3 space-y-2">
            <div className="flex flex-wrap items-baseline gap-x-3 text-[11px] font-bold uppercase tracking-[0.12em] text-teal">
              <span>1 · The move</span>
              {move?.type && <span className="font-semibold normal-case tracking-normal text-muted">{moveType(move.type)}</span>}
            </div>
            <Block b={move} ix={ix} className="text-[17px] font-semibold leading-snug" empty="The move has not been exported" />
            {budget && (
              <div className="text-[13.5px] text-muted">
                <Block b={budget} ix={ix} lead={<span className="font-semibold text-fg">Budget: </span>} empty="not exported" />
                {budgetLine && <div className="mt-0.5 font-mono text-[12px]">{budgetLine}</div>}
              </div>
            )}
          </section>

          <Section n={2} title="The case for it">
            {drivers.length > 0 && (
              <div className="space-y-1.5">
                <Label>Driven by these Part 1 findings</Label>
                <ul className="space-y-1">
                  {drivers.map((d, i) => {
                    const n = Number(d.finding_n);
                    const why = field(d as Record<string, unknown>, "why");
                    return (
                      <li key={i} className="flex flex-wrap items-baseline gap-x-2 text-[13.5px]">
                        <button type="button" onClick={(e) => { e.stopPropagation(); onPart1(active, Number.isFinite(n) ? n : undefined); }}
                          className="rounded-full border border-purple/40 bg-surface px-2 py-px font-mono text-[12px] text-purple hover:bg-chip">Finding {Number.isFinite(n) ? n : "?"}</button>
                        {why && <Block b={why} ix={ix} className="min-w-0 flex-1" />}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border border-line p-3"><Label>What it costs</Label><Block b={cf?.cost} ix={ix} className="text-[14px]" /></div>
              <div className="rounded-md border border-line p-3"><Label>What it should return</Label><Block b={cf?.return} ix={ix} className="text-[14px]" /></div>
            </div>
            {steps.length > 0 && (
              <details open className="rounded-md border border-line bg-surface-2 px-3 py-2">
                <summary className="cursor-pointer select-none text-[13px] font-semibold text-purple">The math, step by step</summary>
                <ol className="mt-2 space-y-2 pl-1">
                  {steps.map((s, i) => (
                    <li key={i} className="flex gap-2 text-[13.5px]">
                      <span className="mt-px shrink-0 font-mono text-[12px] text-muted">{s.step ?? i + 1}.</span>
                      <Block b={s} ix={ix} className="min-w-0 flex-1" />
                    </li>
                  ))}
                </ol>
              </details>
            )}
            {cf?.net && <Block b={cf.net} ix={ix} lead={<span className="font-semibold">Net: </span>} className="text-[14px]" />}
            {!cf && <p className="text-[13px] text-muted">The case (cost, return, math) has not been exported.</p>}
          </Section>

          {stage >= 2 ? (
            <>
              <Section n={3} title="Alternatives rejected" sub="the two strongest options considered">
                <div className="grid gap-3 sm:grid-cols-2">
                  {rejected.map((r, i) => (
                    <div key={r.id ?? i} className="rounded-md border border-line p-3 space-y-1.5">
                      <div className="flex flex-wrap items-baseline gap-x-2 text-[11px] font-bold uppercase tracking-[0.12em] text-muted"><span>Option {i + 1}</span>{r.type && <span className="font-semibold normal-case tracking-normal">{moveType(r.type)}</span>}</div>
                      {r.move && <div className="font-semibold leading-snug text-[14.5px]">{scrub(r.move)}</div>}
                      <Block b={r.why_passed} ix={ix} lead={<span className="font-semibold">Why we passed: </span>} className="text-[13.5px]" empty="reason not exported" />
                      {r.skeptic_lens && <div className="text-[11px] text-muted">Pressed by the {scrub(r.skeptic_lens)} skeptic</div>}
                    </div>
                  ))}
                </div>
                {rejected.length !== 2 && <p className="text-[12px] text-muted">The case asks for two rejected options; {rejected.length} exported.</p>}
              </Section>

              <Section n={4} title="What would prove it wrong" sub="early signals, months 6 to 12">
                {kills.length ? (
                  <div className="overflow-x-auto rounded-md border border-line">
                    <table className="w-full min-w-[600px] table-fixed border-collapse text-[13px]">
                      <colgroup><col className="w-[30%]" /><col className="w-[26%]" /><col className="w-[14%]" /><col className="w-[30%]" /></colgroup>
                      <thead className="bg-surface-2"><tr><Th>Signal</Th><Th>Threshold</Th><Th>When</Th><Th>Reading</Th></tr></thead>
                      <tbody>
                        {kills.map((k, i) => {
                          const rec = k as Record<string, unknown>;
                          const bad = failed(k.numeric_check);
                          return (
                            <tr key={i} className="border-t border-line align-top">
                              <td className="px-2.5 py-2 font-semibold break-words">{bad ? <span className="font-normal text-muted">Withheld: failed the numeric gate</span> : scrub(k.signal) || <span className="font-normal text-muted">not exported</span>}</td>
                              <td className="px-2.5 py-2 break-words">{bad ? "" : <Block b={field(rec, "threshold")} ix={ix} empty="not exported" />}</td>
                              <td className="px-2.5 py-2 break-words text-muted">{scrub(k.month_window) || ""}</td>
                              <td className="px-2.5 py-2 break-words"><Block b={k} ix={ix} empty="" /></td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : <p className="text-[13px] text-muted">No kill signals exported.</p>}
              </Section>

              <Section n={5} title="Why it will work" sub={ev?.decider ? `the people who decide: ${scrub(ev.decider)}` : undefined}>
                <Block b={ev?.lands_because} ix={ix} className="text-[14px]" empty="Evidence not exported" />
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-md border border-line p-3"><Label>What it can tell us</Label><Block b={ev?.can_tell} ix={ix} className="text-[13.5px]" /></div>
                  <div className="rounded-md border border-line p-3"><Label>What it cannot tell us</Label><Block b={ev?.cannot_tell} ix={ix} className="text-[13.5px]" /></div>
                </div>
                {unresolved.length > 0 && (
                  <div className="rounded-md border border-dashed border-line px-3 py-2 space-y-1.5">
                    <Label>Where the two skeptics still disagree</Label>
                    {unresolved.map((u, i) => (
                      <div key={i} className="text-[13px]">
                        {u.topic && <div className="font-semibold">{scrub(u.topic)}</div>}
                        {u.cfo_position && <div><span className="text-muted">CFO lens: </span>{scrub(u.cfo_position)}</div>}
                        {u.decider_position && <div><span className="text-muted">Decider lens: </span>{scrub(u.decider_position)}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </Section>

              <Section n={6} title="Anything a doctor or patient would see">
                {hasMaterial ? (
                  <div className="space-y-3">
                    <div role="note" className="rounded-md border-2 border-warn bg-warn/10 px-3 py-2 text-[13.5px] font-semibold text-warn">{PART2_BANNER}</div>
                    {!risksOk || !labelledOk ? (
                      <p className="text-[13.5px] text-muted">Concept withheld: the compliance check did not confirm {!risksOk ? "that risks are shown as prominently as benefits" : "the student-concept label"}.</p>
                    ) : pieces.length ? pieces.map((p, i) => (
                      <article key={i} className="rounded-md border border-line p-4 space-y-2">
                        {p.title && <h4 className="text-[16px] font-semibold leading-snug">{scrub(p.title)}</h4>}
                        <Block b={field(p as Record<string, unknown>, "body", true)} ix={ix} className="text-[14px]" empty="body not exported" />
                        <div className="text-[11px] text-muted">{PART2_BANNER}</div>
                      </article>
                    )) : <p className="text-[13px] text-muted">No piece exported.</p>}
                    <Rules rc={promo?.rules_check} />
                  </div>
                ) : <p className="text-[13.5px] text-muted">This move includes no campaign, messaging or other material a doctor or patient would see.</p>}
              </Section>

              <Section n={7} title="Claims map">
                {claims.length ? (
                  <div className="overflow-x-auto rounded-md border border-line">
                    <table className="w-full min-w-[560px] table-fixed border-collapse text-[13px]">
                      <colgroup><col className="w-[46%]" /><col className="w-[34%]" /><col className="w-[20%]" /></colgroup>
                      <thead className="bg-surface-2"><tr><Th>Claim</Th><Th>Label section or study</Th><Th>Source</Th></tr></thead>
                      <tbody>
                        {claims.map((r, i) => {
                          const e = (Array.isArray(r.cites) ? r.cites[0] : null) ?? r.cite ?? null;
                          const chip = e ? (e.cite_id && ix.get(e.cite_id)) || evidenceLabel(e) : null;
                          return (
                            <tr key={i} className="border-t border-line align-top">
                              <td className="px-2.5 py-2 break-words">{scrub(r.claim) || <span className="text-muted">not exported</span>}</td>
                              <td className="px-2.5 py-2 break-words">{scrub(r.support_section) || <span className="text-muted">not exported</span>}</td>
                              <td className="px-2.5 py-2">{chip ? <CiteChip evidence={chip} label="source" /> : <span className="text-muted">none</span>}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : <p className="text-[13px] text-muted">{hasMaterial ? "No claims map exported." : "No doctor- or patient-facing material, so no claims map."}</p>}
              </Section>

              <Section n={8} title="Numbers">
                <div className="flex flex-wrap items-center gap-2 text-[13px]">
                  <NumericPill check={c.numeric_summary} />
                  {typeof c.figures_withheld === "number" && c.figures_withheld > 0 && <span className="text-muted">{c.figures_withheld} figure{c.figures_withheld === 1 ? "" : "s"} withheld because the gate never checked {c.figures_withheld === 1 ? "it" : "them"}.</span>}
                  {c.numeric_summary?.note && <span className="text-muted">{scrub(c.numeric_summary.note)}</span>}
                </div>
              </Section>

              {trace
                ? <Part2TraceView trace={trace} summary={c.skeptic_summary} candidates={c.candidates_considered} sample={part2.sample} />
                : tr instanceof Error ? <p className="text-[13px] text-muted">Reasoning trace not exported (data/part2/{active}_trace.json).</p> : null}
            </>
          ) : <button type="button" onClick={() => setStage(2)} className="no-print text-[11px] text-muted underline">Show all</button>}
        </>
      )}

      {stage >= 2 && c && follow.length > 0 && (
        <div className="no-print flex flex-wrap gap-2" aria-label="Ask next">
          {follow.map((f) => (
            <button key={f.key} type="button" onClick={(e) => { e.stopPropagation(); f.onClick(); }}
              className="rounded-full border border-purple/40 bg-surface px-3 py-1.5 text-[13px] text-purple hover:bg-chip text-left">{f.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}
