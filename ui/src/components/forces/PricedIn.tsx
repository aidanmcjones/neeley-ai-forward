import { useState } from "react";
import type { Company, Evidence, Loose } from "../../lib/types";
import { CiteChip } from "../CiteChip";
import { DataTable } from "../DataTable";
import type { Column } from "../DataTable";
import { EmptyState } from "../EmptyState";
import { Panel } from "../Panel";
import { Flag, isNum, str, tierTone, topicLabel } from "../product/util";

// Priced-in scorecard: analyst attention per topic on earnings calls, plus event returns when asked vs not.

const pctS = (x: unknown) => (isNum(x) ? `${x > 0 ? "+" : ""}${(x * 100).toFixed(1)}%` : "n/a");
const TIER_RANK: Record<string, number> = { "routinely asked": 3, sometimes: 2, "rarely asked": 1 };

function exampleEvidence(r: Loose): Evidence | null {
  const file = str(r.latest_example_file);
  const quote = str(r.latest_example_quote);
  if (!file || !quote) return null;
  return {
    doc_id: file,
    citation: `${r.ticker ?? ""} ${r.latest_example_quarter ?? ""} call transcript, line ${isNum(r.latest_example_line) ? r.latest_example_line : "?"}`,
    quote,
    speaker: str(r.latest_example_speaker) ?? undefined,
    doc_type: "transcript",
    excerpt: { before: "", match: quote, after: "" },
  };
}

function Example({ r }: { r: Loose }) {
  const [open, setOpen] = useState(false);
  const q = str(r.latest_example_quote);
  if (!q) return <span className="text-muted italic text-[12px]">no example</span>;
  const ev = exampleEvidence(r);
  return (
    <div className="text-[12px] min-w-0">
      <button type="button" onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }} aria-expanded={open} className="text-left hover:text-purple">
        <span className="font-semibold">{String(r.latest_example_speaker ?? "Analyst")}</span>{" "}
        <span className="text-muted">({String(r.latest_example_quarter ?? "")})</span>:{" "}
        <span className={open ? "" : "line-clamp-2"}>“{q.trim()}…”</span>
      </button>
      {ev && <span className="ml-1" onClick={(e) => e.stopPropagation()}><CiteChip evidence={ev} label="src" /></span>}
    </div>
  );
}

export function PricedIn({ company }: { company: Company }) {
  const rows = company.priced_in ?? [];
  const never = company.never_asked ?? [];
  const flagOf = (topic: unknown) => str(never.find((n) => n.topic === topic)?.flag);

  if (!rows.length) {
    return (
      <Panel title="Priced-in scorecard">
        <EmptyState file={`companies/${company.ticker}.json · priced_in`} message={`No priced-in rows for ${company.ticker}`}>
          Source table: data/moat/verified/market/priced_in_scorecard.csv
        </EmptyState>
      </Panel>
    );
  }

  const cols: Column<Loose>[] = [
    { key: "topic", header: "Topic", width: "120px", sortValue: (r) => topicLabel(r.topic), render: (r) => <span className="font-semibold">{topicLabel(r.topic)}</span> },
    { key: "tier", header: "Analyst attention", sortValue: (r) => TIER_RANK[String(r.analyst_attention_tier)] ?? 0, render: (r) => <Flag tone={tierTone(r.analyst_attention_tier)}>{String(r.analyst_attention_tier ?? "n/a")}</Flag> },
    { key: "asked", header: "Asked / covered", align: "right", sortValue: (r) => (isNum(r.share_of_quarters_asked) ? r.share_of_quarters_asked : null), render: (r) => (
      <span className="tnum">{String(r.quarters_asked ?? "?")} / {String(r.quarters_covered ?? "?")}<span className="block text-[10px] text-muted">{String(r.quarter_range ?? "")}</span></span>
    ) },
    { key: "last", header: "Last asked", sortValue: (r) => str(r.last_quarter_asked), render: (r) => <span className="font-mono text-[12px]">{String(r.last_quarter_asked ?? "never")}</span> },
    { key: "streak", header: "Unasked streak", sortValue: (r) => (isNum(r.recent_unasked_streak) ? r.recent_unasked_streak : null), render: (r) => {
      const f = flagOf(r.topic);
      return (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="tnum font-semibold">{String(r.recent_unasked_streak ?? "?")}q</span>
          {f && <Flag tone="warn">{f}</Flag>}
        </div>
      );
    } },
    { key: "abn", header: "Abn. return 0 to +1d", sortValue: (r) => (isNum(r.mean_abn_0_to_1_when_asked) ? r.mean_abn_0_to_1_when_asked : null), render: (r) => (
      <div className="tnum text-[12px] whitespace-nowrap">
        <div>asked <span className="font-semibold">{pctS(r.mean_abn_0_to_1_when_asked)}</span> <span className="text-muted">(n={String(r.n_earnings_events_topic_asked ?? 0)})</span></div>
        <div>not <span className="font-semibold">{pctS(r.mean_abn_0_to_1_not_asked)}</span> <span className="text-muted">(n={String(r.n_earnings_events_not_asked ?? 0)})</span></div>
      </div>
    ) },
    { key: "ex", header: "Latest example", sortable: false, width: "34%", render: (r) => <Example r={r} /> },
  ];

  // Reading: least discussed = longest unasked streak, then lowest tier.
  const least = [...rows].sort((a, b) =>
    (Number(b.recent_unasked_streak ?? 0) - Number(a.recent_unasked_streak ?? 0)) ||
    ((TIER_RANK[String(a.analyst_attention_tier)] ?? 0) - (TIER_RANK[String(b.analyst_attention_tier)] ?? 0)));
  const top = least.filter((r) => Number(r.recent_unasked_streak ?? 0) > 0).slice(0, 2);

  return (
    <Panel title="Priced-in scorecard" meta={<span className="font-mono">{rows.length} topics · priced_in · never_asked</span>}>
      <DataTable columns={cols} rows={rows} rowKey={(r) => String(r.topic)} caption="Priced-in scorecard" maxHeight={2000} dense
        initialSort={{ key: "streak", dir: "desc" }} />
      <p className="mt-2 text-[13px]">
        <span className="font-semibold">Least discussed: </span>
        {top.length ? top.map((r, i) => (
          <span key={String(r.topic)}>{i > 0 && "; "}{topicLabel(r.topic)} ({String(r.analyst_attention_tier)}, unasked {String(r.recent_unasked_streak)} straight quarters, last {String(r.last_quarter_asked ?? "never")})</span>
        )) : "every topic was asked in the latest covered quarter"}.
        {" "}A topic analysts stop asking about is less likely to be in the price.
      </p>
      <p className="mt-1 text-[11px] text-muted">
        Abnormal returns are small-sample means (n shown) over 0 to +1 trading days around the call; read them as context, not proof.{" "}
        {str(rows[0].press_source) && <>Press coverage: {String(rows[0].press_source)}. </>}
        <span className="font-mono">{String(rows[0].source ?? "data/moat/verified/market/priced_in_scorecard.csv")}</span>
      </p>
    </Panel>
  );
}
