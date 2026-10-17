import type { Company, Finding, Loose } from "../../lib/types";
import { AiMark } from "../AiMark";
import { CiteChip } from "../CiteChip";
import { ConfPill } from "../ConfPill";
import { Panel } from "../Panel";
import { Flag, drugName, isNum, str, tierTone, topicLabel } from "./util";

// "What limits growth": the engine's label-derived findings for this product plus a priced-in line
// built from the analyst-attention rows for biosimilar/generic and IRA topics. Template-written: teal.

const LIMITS = new Set(["exclusivity_earlier", "dosing_burden", "ira_exposed", "boxed_warning_disadvantage", "label_narrower"]);
const ADVANTAGES = new Set(["dosing_advantage", "label_broader", "boxed_warning_advantage"]);
const kindOf = (f: Finding) => (LIMITS.has(f.signal_kind ?? "") ? "limit" : ADVANTAGES.has(f.signal_kind ?? "") ? "advantage" : "context");
const cap = (s: string) => s.replace(/^\w/, (c) => c.toUpperCase());
const pctS = (x: number) => `${x > 0 ? "+" : ""}${(x * 100).toFixed(1)}%`;

export function productFindings(company: Company, product: string): Finding[] {
  const p = product.toLowerCase();
  return company.findings
    .filter((f) => f.detector === "labels")
    .filter((f) => f.finding.toLowerCase().startsWith(p) || (f.evidence ?? []).some((e) => String(e.doc_id ?? "").includes(`drug:${p}:`) && f.finding.toLowerCase().includes(p)))
    .sort((a, b) => (b.score_norm ?? b.score ?? 0) - (a.score_norm ?? a.score ?? 0));
}

export function LimitsPanel({ company, product }: { company: Company; product: string }) {
  const fs = productFindings(company, product);
  const pi = (company.priced_in ?? []).filter((r) => r.topic === "biosimilar_generic" || r.topic === "IRA_negotiation");
  const gtn = (company.gtn_exposure ?? []).find((g) => g.drug === product);
  const cut = (company.ira_cut_check ?? []).find((r) => String(r.drug ?? "").toLowerCase() === product);
  const name = drugName(product);

  // One-sentence verdict, built only from exported values.
  const limits = fs.filter((f) => kindOf(f) === "limit");
  const lead = limits.find((f) => f.verdict === "verified") ?? limits[0];
  const nAdv = fs.filter((f) => kindOf(f) === "advantage").length;
  const iraBit = cut && isNum(cut.mfp_usd_30day)
    ? `IRA sets ${name}'s Medicare price at $${(cut.mfp_usd_30day as number).toFixed(2)} per 30 days from IPAY ${cut.ipay}, ${cut.cms_pct_cut}% below list (CMS fact sheet p.${cut.page})`
    : gtn && isNum(gtn.ira_mfp_per_30day)
      ? `IRA sets ${name}'s Medicare price at $${(gtn.ira_mfp_per_30day as number).toFixed(2)} per 30 days from ${gtn.ira_mfp_effective ?? `IPAY ${gtn.ira_ipay}`}`
      : null;
  const limitText = [iraBit, lead ? cap(lead.finding.replace(/\s*\(\{[^}]*\}\)/g, "")) : null].filter(Boolean).join("; ");

  return (
    <Panel ai title={<span className="inline-flex items-center gap-2"><AiMark label="Engine verdict" /> What limits growth</span>}
      meta={<span className="font-mono">labels detector · priced_in</span>}>
      {limitText ? (
        <p className="text-[15px] font-semibold leading-snug">
          <span className="text-muted font-normal">What limits {name}: </span>{limitText}.
        </p>
      ) : (
        <p className="text-sm">
          <span className="text-muted">What limits {name}: </span>no label-derived limit and no IRA price in this export
          {nAdv > 0 ? `; its ${nAdv} label signal${nAdv > 1 ? "s are" : " is an"} advantage${nAdv > 1 ? "s" : ""} over rivals` : ""}.
        </p>
      )}
      <PricedInLine rows={pi} file={`companies/${company.ticker}.json · priced_in`} />
      <p className="mt-1 text-[11px] text-muted">Drafted from verified findings by template (no model prose). Teal marks engine output; every number below has its source.</p>

      <h3 className="mt-4 mb-2 text-[11px] font-bold uppercase tracking-wide text-muted">Label-derived findings for {name} ({fs.length})</h3>
      {fs.length === 0 ? (
        <div className="rounded-md border border-dashed border-line bg-surface-2 px-3 py-3 text-sm text-muted">
          No findings with detector <code className="font-mono text-xs">labels</code> mention {name} in <code className="font-mono text-xs">companies/{company.ticker}.json · findings</code>.
        </div>
      ) : (
        <ul className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
          {fs.map((f) => (
            <li key={f.id} className="rounded-md border border-teal/30 bg-surface px-3 py-2">
              <div className="text-[13px]">{f.finding}</div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {kindOf(f) === "limit" ? <Flag tone="warn">limits growth</Flag> : kindOf(f) === "advantage" ? <Flag tone="good">advantage</Flag> : <Flag tone="neutral">context</Flag>}
                <ConfPill level={f.confidence} />
                {f.verdict && <Flag tone={f.verdict === "verified" ? "good" : f.verdict === "rejected" ? "bad" : "warn"}>{f.verdict.replace(/_/g, " ")}</Flag>}
                {(f.evidence ?? []).map((e, i) => (
                  <CiteChip key={i} evidence={{ ...e, verdict: e.verdict ?? f.verdict }} label={str(e.citation)?.split(" (")[0] ?? `[${i + 1}]`} />
                ))}
              </div>
              {f.vector?.obscurity_note && <div className="mt-1 text-[11px] text-muted">Obscurity: {f.vector.obscurity_note}</div>}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function PricedInLine({ rows, file }: { rows: Loose[]; file: string }) {
  if (!rows.length) {
    return <div className="mt-2 text-[13px] text-muted">Priced in? No analyst-attention rows for IRA or biosimilar topics (<code className="font-mono text-xs">{file}</code>).</div>;
  }
  const least = [...rows].sort((a, b) => Number(b.recent_unasked_streak ?? 0) - Number(a.recent_unasked_streak ?? 0))[0];
  const tone = tierTone(least.analyst_attention_tier);
  const call = tone === "good" ? "likely priced in: analysts ask about it most quarters"
    : tone === "bad" || Number(least.recent_unasked_streak ?? 0) >= 4 ? `possibly not priced in: ${topicLabel(least.topic)} has gone unasked`
    : "partly priced in: asked in some quarters, not all";
  return (
    <div className="mt-2 space-y-1">
      <div className="text-[13px]"><span className="font-semibold">Priced in? </span>{call}.</div>
      <ul className="space-y-0.5">
        {rows.map((r) => (
          <li key={String(r.topic)} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px]">
            <span className="font-semibold">{topicLabel(r.topic)}</span>
            <Flag tone={tierTone(r.analyst_attention_tier)}>{String(r.analyst_attention_tier ?? "tier n/a")}</Flag>
            <span className="tnum text-muted">
              asked {String(r.quarters_asked ?? "?")}/{String(r.quarters_covered ?? "?")} quarters ({String(r.quarter_range ?? "")}), unasked streak {String(r.recent_unasked_streak ?? "?")}
              {isNum(r.mean_abn_0_to_1_when_asked) && <>, abn. return 0 to +1d {pctS(r.mean_abn_0_to_1_when_asked)} when asked</>}
              {isNum(r.mean_abn_0_to_1_not_asked) && <> vs {pctS(r.mean_abn_0_to_1_not_asked)} not</>}
            </span>
          </li>
        ))}
      </ul>
      <div className="font-mono text-[10px] text-muted">{String(rows[0].source ?? file)}</div>
    </div>
  );
}
