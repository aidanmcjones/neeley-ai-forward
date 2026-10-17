import { KpiTile } from "..";
import { num } from "../../lib/format";
import type { Company, Meta } from "../../lib/types";

// Four KPI tiles. Every footnote names the file its number came from.
function Foot({ lines }: { lines: string[] }) {
  return <>{lines.map((l, i) => <span key={i} className="block truncate" title={l}>{l}</span>)}</>;
}

export function KpiRow({ meta, company }: { meta: Meta | null; company: Company }) {
  const file = `companies/${company.ticker}.json`;
  const verified = company.findings.filter((f) => (f.verdict ?? "").toLowerCase().startsWith("verif")).length;
  const held = company.findings.filter((f) => f.verdict === "needs_human").length;
  const rejected = company.rejected?.length ?? 0;
  const led = meta?.ledger;
  const c = meta?.corpus;
  return (
    <div className="grid grid-cols-4 gap-3">
      <KpiTile
        hot
        label="Findings verified"
        value={<>{num(verified)} <span className="text-[22px] opacity-80">of {num(company.findings.length)}</span></>}
        footnote={<Foot lines={[file, `${num(meta?.totals?.verified)} all cos · meta.json totals`]} />}
      />
      <KpiTile
        label="AI claims rejected"
        value={num(rejected)}
        footnote={<Foot lines={[`held for human: ${num(held)}`, file]} />}
      />
      <KpiTile
        label="Ledger"
        value={led?.ok ? "Intact" : led ? "Broken" : "n/a"}
        footnote={<Foot lines={[`${num(led?.n)} hash-chained records`, "meta.json · ledger"]} />}
      />
      <KpiTile
        label="Sources"
        value={<>{num(c?.docs)} <span className="text-[22px] opacity-80">docs</span></>}
        footnote={<Foot lines={[`${num(c?.drugs)} drugs · ${num(c?.transcripts)} transcripts`, `${num(c?.transcripts_official)} official · meta.json corpus`]} />}
      />
    </div>
  );
}
