import { useState } from "react";
import type { Loose } from "../../lib/types";
import { num } from "../../lib/format";
import { KpiTile, Panel } from "..";
import { Pill, SourceNote, parseBasis, signedPct, useTokens } from "./common";

// (c) calibration tiles, (d) J&J blind test, (e) sealed forecasts with in-browser seal check.

export function CalibrationPanel({ cal }: { cal: Loose | null | undefined }) {
  const c = (cal ?? {}) as { k?: number; coverage?: number; target?: number; n_cases?: number; median_abs_error_pts?: number; direction_accuracy_vs_last?: number };
  const gap = typeof c.coverage === "number" && typeof c.target === "number" ? (c.coverage - c.target) * 100 : null;
  return (
    <Panel title="(c) Revenue forecaster calibration" meta="historical firm-quarters, no LLM">
      <div className="grid grid-cols-5 gap-3">
        <KpiTile label="Interval width k" value={typeof c.k === "number" ? c.k.toFixed(1) : "n/a"} footnote="calibration.json" />
        <KpiTile hot label="80% interval coverage" value={typeof c.coverage === "number" ? `${(c.coverage * 100).toFixed(1)}%` : "n/a"}
          footnote={`target ${typeof c.target === "number" ? `${Math.round(c.target * 100)}%` : "n/a"} · ${gap == null ? "n/a" : `${gap > 0 ? "+" : ""}${gap.toFixed(1)} pts`}`} />
        <KpiTile label="Cases" value={num(c.n_cases)} footnote="firm-quarters" />
        <KpiTile label="Median abs error" value={typeof c.median_abs_error_pts === "number" ? `${c.median_abs_error_pts.toFixed(2)} pts` : "n/a"} footnote="YoY growth pts" />
        <KpiTile label="Direction accuracy" value={typeof c.direction_accuracy_vs_last === "number" ? `${(c.direction_accuracy_vs_last * 100).toFixed(1)}%` : "n/a"} footnote="vs last quarter" />
      </div>
      <p className="mt-3 text-[13px] text-muted">An 80% interval should contain the actual 80% of the time. Ours contained it in {typeof c.coverage === "number" ? `${(c.coverage * 100).toFixed(1)}%` : "n/a"} of {num(c.n_cases)} cases: calibrated, not just confident.</p>
      <SourceNote>proof.json · calibration (out/predictions/calibration.json)</SourceNote>
    </Panel>
  );
}

export function BlindPanel({ blind }: { blind: Loose | null | undefined }) {
  const t = useTokens();
  const b = (blind ?? {}) as { prediction?: Loose & { basis?: unknown; outcome?: string; target_period?: string; ticker?: string; made_at?: string; metric?: string }; actual?: number; abs_error_pts?: number; answer_key?: { citation?: string; quote?: string; verifier?: string } };
  const p = b.prediction ?? {};
  const { point, lo, hi } = parseBasis(p.basis);
  const actual = typeof b.actual === "number" ? b.actual : null;
  const vals = [point, lo, hi, actual].filter((v): v is number => v != null);
  const ok = vals.length >= 3 && lo != null && hi != null;
  const dmin = ok ? Math.floor(Math.min(...vals) * 100 - 2) / 100 : 0;
  const dmax = ok ? Math.ceil(Math.max(...vals) * 100 + 4) / 100 : 1;
  const W = 640, L = 20, R = 20, X = (v: number) => L + ((v - dmin) / (dmax - dmin)) * (W - L - R);
  const ticks: number[] = [];
  for (let v = Math.ceil(dmin * 100); v <= Math.floor(dmax * 100); v += 2) ticks.push(v / 100);
  const hit = (p.outcome ?? "").toLowerCase() === "hit";

  return (
    <Panel title={`(d) Blind test: ${p.ticker ?? "JNJ"} ${p.target_period ?? ""} revenue growth`} meta={p.made_at ? `made with ${p.made_at}` : undefined}>
      <div className="flex items-center gap-3 flex-wrap">
        <Pill tone={hit ? "good" : "bad"}>{hit ? "HIT" : (p.outcome ?? "n/a").toUpperCase()}</Pill>
        <span className="text-[14px]">Forecast <strong className="font-mono">{signedPct(point)}</strong>, 80% interval <span className="font-mono">{signedPct(lo)} to {signedPct(hi)}</span>; actual <strong className="font-mono">{signedPct(actual)}</strong>
          {typeof b.abs_error_pts === "number" && <span className="text-muted"> · error {b.abs_error_pts.toFixed(2)} pts</span>}</span>
      </div>
      {ok ? (
        <svg viewBox={`0 0 ${W} 104`} className="mt-3 w-full max-w-[900px]" role="img"
          aria-label={`80% interval ${signedPct(lo)} to ${signedPct(hi)}, forecast ${signedPct(point)}, actual ${signedPct(actual)}`}>
          <line x1={L} x2={W - R} y1={70} y2={70} stroke={t.line} strokeWidth={1} />
          {ticks.map((v) => (
            <g key={v}>
              <line x1={X(v)} x2={X(v)} y1={66} y2={74} stroke={t.line} />
              <text x={X(v)} y={90} textAnchor="middle" fontSize={11} fontFamily="JetBrains Mono" fill={t.muted}>{`${Math.round(v * 100)}%`}</text>
            </g>
          ))}
          <rect x={X(lo!)} y={42} width={X(hi!) - X(lo!)} height={20} rx={4} fill={t.purple} opacity={0.18} />
          <rect x={X(lo!)} y={42} width={X(hi!) - X(lo!)} height={20} rx={4} fill="none" stroke={t.purple} strokeWidth={1} />
          <text x={X(hi!) + 8} y={56} fontSize={11} fontFamily="JetBrains Mono" fill={t.muted} textAnchor="start">80% interval</text>
          {point != null && (<>
            <line x1={X(point)} x2={X(point)} y1={38} y2={66} stroke={t.fg} strokeWidth={2} />
            <text x={X(point)} y={20} textAnchor="middle" fontSize={12} fontFamily="JetBrains Mono" fill={t.fg}>{`forecast ${signedPct(point)}`}</text>
          </>)}
          {actual != null && (<>
            <circle cx={X(actual)} cy={52} r={6} fill={t.purpleBright} stroke={t.surface} strokeWidth={2} />
            <text x={X(actual)} y={20} dx={actual < (point ?? 0) ? -8 : 8} textAnchor={actual < (point ?? 0) ? "end" : "start"} fontSize={12} fontWeight={700} fontFamily="JetBrains Mono" fill={t.fg}>{`actual ${signedPct(actual)}`}</text>
            <line x1={X(actual)} x2={X(actual)} y1={24} y2={45} stroke={t.purpleBright} strokeWidth={1} />
          </>)}
        </svg>
      ) : <p className="mt-2 text-sm text-muted">Interval not parseable from blind.prediction.basis.</p>}
      {b.answer_key?.quote && (
        <blockquote className="mt-3 border-l-4 border-purple pl-3 text-[13px]">
          <p>“{b.answer_key.quote}”</p>
          <footer className="mt-1 text-[11.5px] text-muted font-mono">{b.answer_key.citation ?? "citation n/a"} · page verifier: {b.answer_key.verifier ?? "n/a"}</footer>
        </blockquote>
      )}
      <SourceNote>proof.json · blind (out/predictions/blind_JNJ_2026Q3.json); forecast used data through 2026Q2 only, made before the 8-K</SourceNote>
    </Panel>
  );
}

/* --------------------------------------------------------------- sealed */

async function sha256Hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

export function SealedPanel({ sealed }: { sealed: (Loose & { file?: unknown; canonical?: string; doc_hash?: string }) | null | undefined }) {
  const file = (sealed?.file ?? {}) as { target?: string; made_at?: string; predictions?: (Loose & { ticker?: string; target_period?: string; metric?: string; basis?: unknown; outcome?: string })[]; sha256?: string };
  const stored = file.sha256 ?? "";
  const docHash = sealed?.doc_hash ?? "";
  const canonical = sealed?.canonical ?? "";
  const [state, setState] = useState<{ computed: string; ok: boolean } | { error: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const verify = async () => {
    setBusy(true);
    try {
      if (!canonical) throw new Error("proof.json has no sealed.canonical string");
      if (!window.crypto?.subtle) throw new Error("SubtleCrypto unavailable (needs a secure context: localhost or https)");
      const computed = await sha256Hex(canonical);
      setState({ computed, ok: !!stored && computed === stored && computed === docHash });
    } catch (e) {
      setState({ error: (e as Error).message });
    } finally { setBusy(false); }
  };

  const Hash = ({ label, value, match }: { label: string; value: string; match?: boolean }) => (
    <div className="grid grid-cols-[170px_1fr_auto] gap-3 items-start py-1.5 border-b border-line last:border-0">
      <span className="text-[12px] text-muted">{label}</span>
      <code className="font-mono text-[12px] break-all">{value || "n/a"}</code>
      {match != null && (match ? <Pill tone="good">match</Pill> : <Pill tone="bad">differs</Pill>)}
    </div>
  );
  const computed = state && "computed" in state ? state.computed : null;

  return (
    <Panel title="(e) Sealed forecasts: committed before the results exist" meta={`target ${file.target ?? "n/a"} · sealed ${file.made_at?.slice(0, 16).replace("T", " ") ?? "n/a"} UTC`}>
      <div className="grid grid-cols-1 gap-4">
        <div className="overflow-auto rounded-md border border-line max-w-[820px]">
          <table className="w-full border-collapse text-[13px]">
            <thead className="bg-surface-2"><tr>
              {["Company", "Period", "Metric", "Point", "80% interval", "Outcome"].map((h, i) => (
                <th key={h} scope="col" className={`px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold whitespace-nowrap ${i >= 3 && i <= 4 ? "text-right" : "text-left"}`}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{(file.predictions ?? []).map((p, i) => {
              const b = parseBasis(p.basis);
              return (
                <tr key={i} className="border-b border-line last:border-0">
                  <th scope="row" className="text-left px-3 py-1.5 font-mono font-semibold">{p.ticker ?? "?"}</th>
                  <td className="px-3 py-1.5 font-mono">{p.target_period ?? "?"}</td>
                  <td className="px-3 py-1.5 font-mono text-[12px] text-muted">{p.metric ?? "?"}</td>
                  <td className="px-3 py-1.5 text-right font-mono tnum">{signedPct(b.point)}</td>
                  <td className="px-3 py-1.5 text-right font-mono tnum whitespace-nowrap">{signedPct(b.lo)} to {signedPct(b.hi)}</td>
                  <td className="px-3 py-1.5"><Pill tone="purple">{p.outcome ?? "open"}</Pill></td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
        <div className="min-w-0">
          <p className="text-[13px]">
            These forecasts resolve when the companies report, <strong>Oct 29 to Nov 5, 2026</strong>, and anyone can check them. The seal is sha256 over the canonical JSON
            (sorted keys, no spaces); the same hash was committed to <code className="font-mono text-[12px]">docs/needle_sealed.md</code> before any result was out.
          </p>
          <div className="mt-3 flex items-center gap-3">
            <button type="button" onClick={verify} disabled={busy}
              className="whitespace-nowrap rounded-md bg-purple dark:bg-purple-deep text-white px-4 py-2 text-[13px] font-semibold hover:bg-purple-bright disabled:opacity-60">
              {busy ? "Hashing…" : "Verify seal"}
            </button>
            <span aria-live="polite">
              {state && "error" in state && <Pill tone="bad">error</Pill>}
              {state && "computed" in state && (state.ok ? <Pill tone="good" className="text-[12px] px-3 py-1">VERIFIED</Pill> : <Pill tone="bad" className="text-[12px] px-3 py-1">MISMATCH</Pill>)}
            </span>
            <span className="text-[12px] text-muted">{state && "error" in state ? state.error : "computed in your browser with SubtleCrypto, nothing sent anywhere"}</span>
          </div>
          <div className="mt-3 rounded-md border border-line px-3 py-1">
            <Hash label="Computed now (browser)" value={computed ?? "press Verify seal"} />
            <Hash label="Stored in the sealed file" value={stored} match={computed ? computed === stored : undefined} />
            <Hash label="Committed in docs" value={docHash} match={computed ? computed === docHash : undefined} />
          </div>
        </div>
      </div>
      <SourceNote>proof.json · sealed.file (out/predictions/sealed_2026Q3.json) · sealed.canonical · sealed.doc_hash (docs/needle_sealed.md)</SourceNote>
    </Panel>
  );
}

/* --------------------------------------------------------------- limits */

export function LimitsPanel({ limits, noSource }: { limits: string[]; noSource: string[][] }) {
  const plain = limits.filter((l) => !/^No free source/i.test(l));
  const folded = limits.length - plain.length;
  return (
    <Panel title="(f) Limits we state plainly">
      <ul className="space-y-1.5 text-[13px] list-disc pl-5">
        {plain.map((l, i) => <li key={i}>{l}</li>)}
        {folded > 0 && <li className="text-muted">Plus {folded} data gaps with no free source for anyone, listed with our proxy below.</li>}
      </ul>
      <h3 className="mt-4 text-[12px] font-bold uppercase tracking-wide text-muted">No free source for anyone</h3>
      <div className="mt-2 overflow-auto rounded-md border border-line">
        <table className="w-full border-collapse text-[13px]">
          <thead className="bg-surface-2"><tr>
            {["Missing", "Who sells it", "Our proxy"].map((h) => <th key={h} scope="col" className="text-left px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold">{h}</th>)}
          </tr></thead>
          <tbody>{noSource.map((r, i) => (
            <tr key={i} className="border-b border-line last:border-0 align-top">
              <th scope="row" className="text-left px-3 py-2 font-semibold">{r[0]}</th>
              <td className="px-3 py-2 text-muted">{r[1]}</td>
              <td className="px-3 py-2">{r[2]}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <SourceNote>proof.json · limits (materiality spec section 8) · meta.json · moat.no_source</SourceNote>
    </Panel>
  );
}

/** meta.honest_limits (docs/honest_limits.md): what we cannot know, said plainly, with our proxy. */
export function HonestLimitsPanel({ rows }: { rows: { limit?: string; sentence?: string; proxy?: string; source?: string }[] }) {
  return (
    <Panel title="Honest limits" meta={<span className="font-mono">{rows.length} limits</span>}>
      <div className="overflow-auto rounded-md border border-line">
        <table className="w-full border-collapse text-[13px]">
          <thead className="bg-surface-2"><tr>
            {["Limit", "What we say", "Our proxy"].map((h) => <th key={h} scope="col" className="text-left px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold">{h}</th>)}
          </tr></thead>
          <tbody>{rows.map((r, i) => (
            <tr key={i} className="border-b border-line last:border-0 align-top">
              <th scope="row" className="text-left px-3 py-2 font-semibold">{r.limit ?? "n/a"}</th>
              <td className="px-3 py-2">{r.sentence ?? ""}</td>
              <td className="px-3 py-2 text-muted">{r.proxy ?? ""}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <SourceNote>meta.json · honest_limits ({[...new Set(rows.map((r) => r.source).filter(Boolean))].join(", ") || "docs/honest_limits.md"})</SourceNote>
    </Panel>
  );
}

/** proof.ai_wrong_cases (docs/ai_in_the_build.md): where the AI was confidently wrong in the build, and the fix. */
export function AiWrongCasesPanel({ rows }: { rows: { n?: number; date?: string; ai_claimed?: string; caught_by?: string; fix?: string; evidence?: string }[] }) {
  return (
    <Panel title="Where the AI was confidently wrong" meta={<span className="font-mono">{rows.length} cases</span>}>
      <div className="overflow-auto rounded-md border border-line max-h-[520px]">
        <table className="w-full border-collapse text-[13px]">
          <thead className="bg-surface-2 sticky top-0"><tr>
            {["#", "When", "What the AI claimed", "How we caught it", "What we changed", "Evidence"].map((h) => <th key={h} scope="col" className="text-left px-3 py-2 border-b border-line text-[11px] uppercase tracking-wide text-muted font-semibold">{h}</th>)}
          </tr></thead>
          <tbody>{rows.map((r, i) => (
            <tr key={i} className="border-b border-line last:border-0 align-top">
              <td className="px-3 py-2 font-mono text-muted">{r.n ?? i + 1}</td>
              <td className="px-3 py-2 whitespace-nowrap">{r.date ?? ""}</td>
              <td className="px-3 py-2">{r.ai_claimed ?? ""}</td>
              <td className="px-3 py-2">{r.caught_by ?? ""}</td>
              <td className="px-3 py-2">{r.fix ?? ""}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-muted [overflow-wrap:anywhere]">{(r.evidence ?? "").replace(/`/g, "")}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <SourceNote>proof.json · ai_wrong_cases (docs/ai_in_the_build.md)</SourceNote>
    </Panel>
  );
}
