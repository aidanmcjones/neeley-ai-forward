// Types mirroring the data contract in docs/ui_spec.md ("Data contract: ui/public/data/").
// Everything beyond identifiers is optional: the exporter is evolving, and the UI must
// tolerate missing or extra fields (index signatures keep unknown keys accessible).

export type Loose = { [k: string]: unknown };
export type Confidence = "high" | "medium" | "low" | string;

export interface CompanyRef { ticker: string; name?: string }

export interface MoatBucket { key: string; label?: string; why?: string }
export interface MoatCell { have?: number; need?: number; note?: string }
export interface MoatTable { name: string; rows?: number; what?: string; list_or_net?: string; source?: string }

export interface Meta extends Loose {
  as_of?: string;
  default_ticker?: string;
  companies: CompanyRef[];
  onboarded?: string[];
  totals?: { verified?: number; rejected?: number; findings?: number; high_confidence?: number } & Loose;
  ledger?: { ok?: boolean; n?: number; bad?: number } & Loose;
  corpus?: {
    docs?: number; companies?: number; peers?: number; drugs?: number;
    transcripts?: number; transcripts_official?: number; pages?: number;
  } & Loose;
  moat?: {
    as_of?: string;
    coverage?: Record<string, Record<string, MoatCell>>;
    buckets?: MoatBucket[];
    status?: Record<string, [string, string] | string[]>;
    tables?: MoatTable[];
    no_source?: string[][];
    stages?: string[][];
  } & Loose;
  case_sets?: Record<string, Record<string, string[]>>;
  verifier_rules?: string[];
  limits?: string[];
}

export interface LeagueRow extends Loose {
  ticker: string;
  name?: string;
  score?: number;
  n_findings?: number;
  n_verified?: number;
  n_rejected?: number;
  high_confidence?: number;
  sharpest_needle?: string;
  needle_id?: string;
  /** v2 engine: strict (row clears the obscurity floor), provisional or floor_relaxed. */
  needle_status?: NeedleStatus | string;
  needle_confidence?: Confidence;
  rank?: number;
  v2_rank?: number | null;
}

export type NeedleStatus = "strict" | "provisional" | "floor_relaxed" | "none";

export interface Excerpt { before?: string; match?: string; after?: string }

export interface Evidence extends Loose {
  doc_id?: string;
  page?: number | null;
  printed?: string;
  citation?: string;
  quote?: string;
  speaker?: string;
  figures?: unknown[];
  url?: string;
  doc_type?: string;
  source_quality?: string;
  grade?: string;
  excerpt?: Excerpt;
  /** Filled in by the UI when the evidence is opened from a finding. */
  verdict?: string;
  doc_title?: string;
  period?: string;
  location?: string;
  deep_link?: string;
  /** Public rule: unverified or licensed citations export no quote, excerpt or links. */
  withheld?: boolean;
  withheld_reason?: string | null;
  verification?: { status?: string; score?: number; checked_at?: string; detail?: string } | null;
  cite_id?: string;
  /** Derived citation: operand cite_ids (no quote of its own). withheld wins over derived. */
  derived_from?: string[] | null;
  /** number_match display note: "constructed from the cited value (no page); not a verbatim quote", or a page note. */
  quote_note?: string | null;
  viewer_link?: string | null;
  /** The computation as exported (e.g. "a / b"), when not withheld. */
  derived_expr?: string | null;
  /** Data-row cite (cite_id "row:..."): the JSON path it resolves to and how the value was checked. */
  row_ref?: string | null;
  row_check?: string | null;
  value?: unknown;
  unit?: string | null;
}

export interface Impact extends Loose {
  formula?: string; dollars?: number | null; base?: number | null; bear?: number | null;
  bull?: number | null; line?: string; eps?: number | null;
}

export interface Peer extends Loose { metric_value?: number | null; peer_median?: number | null; z?: number | null; note?: string }

export interface Vector extends Loose {
  I_norm?: number; P?: number; T?: number; Z?: number; D?: number; O?: number; E?: number;
  obscurity_note?: string; topics?: string[];
  v2?: VectorV2 | null;
}

export interface VectorV2 extends Loose { M?: number | null; O?: number | null; E?: number | null; pi?: number | null; S?: number | null; old_S?: number | null }

/** Numbers-on-the-page check (league_v3 uncited-claim gate). Absent = not yet run. */
export interface NumericCheck extends Loose {
  status: "passed" | "failed" | "unchecked" | "no_numbers" | string;
  checked?: number; total?: number;
  verified?: number; derived?: number; assumed?: number;
  unsupported?: { value?: unknown; where?: string; reason?: string }[];
  note?: string;
}

export interface Finding extends Loose {
  id: string;
  numeric_check?: NumericCheck | null;
  flags?: string[];
  /** Sentence with inline markers [n] (evidence n, 1-based), [derived: a, b] and [assumption]. */
  sentence_marked?: string | null;
  /** Impact formula with the same inline markers ([n], [derived: a, b], [constant: NAME], [assumption]). */
  formula_marked?: string | null;
  /** Marker number -> cite_id (resolve anywhere in the company file). */
  marker_map?: Record<string, string> | null;
  /** Marker numbers that point at licensed sources: shown as a muted mark, never a chip. */
  marker_licensed?: number[] | null;
  guard_reason?: string | null;
  /** Receivables-style row whose movement a filing footnote explains; never the needle. */
  explained_by_footnote?: boolean | null;
  explained_by_footnote_note?: string | null;
  footnote_note?: string | null;
  footnote_read?: { status?: string; doc?: string; net?: number; term?: string } | null;
  /** Gated plain-language peer comparison (findings_table rows). */
  peer_text?: string | null;
  peer_comparison?: string | null;
  not_quantified?: string | null;
  corroborates?: string | null;
  fact_key?: string | null;
  impact_channel?: string | null;
  finding: string;
  signal_kind?: string;
  detector?: string;
  score?: number;
  score_norm?: number;
  confidence?: Confidence;
  verdict?: string;
  reason?: string;
  impact?: Impact;
  peer?: Peer;
  vector?: Vector;
  hit_rate?: unknown;
  outside?: unknown;
  evidence?: Evidence[];
}

export interface Rejected extends Loose { finding?: string; reason?: string; verdict?: string; signal_kind?: string }

/** Evidence reference into company.findings[].evidence[]. */
export interface CiteRef { finding_id: string; i?: number }

export interface ComparisonRow { field: string; label?: string; values?: Record<string, { value?: unknown; source?: string }> }
export interface Comparison { product: string; rivals?: string[]; rows?: ComparisonRow[] }

export interface PricePoint extends Loose {
  year: number; partd_per_unit?: number | null; nadac_brand?: number | null; asp?: number | null;
  mfp_per_unit?: number | null; mfp_per_30day?: number | null;
}

export interface StanceOption { name: string; dollars?: number | null; share?: number | null; rationale?: string }
export interface Stance extends Loose {
  headline?: string;
  confidence?: Confidence;
  bullets?: { text: string; cites?: CiteRef[] }[];
  options?: StanceOption[];
  recommended?: string;
  decision_needed?: string;
  memo_points?: { text: string; cites?: CiteRef[] }[];
  alternatives?: { name: string; why_rejected?: string }[];
  prove_wrong?: string[];
  deciders?: string[];
  generated_by?: "template" | "model" | string;
  note?: string;
  decide?: Decide | null;
  kill_signals?: KillSignal[] | null;
}

export interface DecideMove extends Loose {
  name: string; code?: string; template?: string; status?: "chosen" | "rejected" | string; rank?: number;
  ev?: number | null; ev_by_scenario?: { bear?: number; base?: number; bull?: number } | null;
  cash_at_risk?: number | null; payback_month?: number | null; spread?: number | null; mcda?: number | null;
  binding_reason?: string; why?: string; flags?: string[]; finding_ids?: string[]; kill_signal_ids?: string[];
  budget?: Record<string, number> | null; units?: string;
  why_passed?: string | null; cash_at_risk_note?: string | null;
}
export interface DecideFootnote extends Loose { n: number; move?: string; claim?: string; citation?: Evidence }
export interface Decide extends Loose {
  /** Pipeline demonstration, not the team's recommendation; `note` explains it. */
  demo?: boolean | null; note?: string | null;
  /** null when no candidate clears the hurdle; then `least_bad` names the move shown, `selection_rule` says why. */
  chosen?: string | { name?: string; code?: string } | null;
  least_bad?: string | { name?: string; code?: string } | null;
  selection_rule?: string | null;
  /** "Why it will work": the evidence each decider needs (cited rows). */
  why_it_works_rows?: Loose[] | null;
  as_of?: string; cash_and_equivalents?: number; units?: string; moves?: DecideMove[];
  footnotes?: DecideFootnote[]; finding_cites?: CiteRef[]; source_files?: string[];
}
export interface KillSignal extends Loose {
  id: string; signal?: string; threshold?: string; source?: string; lag?: string; check_month?: number;
  action?: string; basis?: string; stop?: boolean;
}

export interface Question {
  id: string;
  q: string;
  answer?: {
    stance?: string; text?: string; cites?: CiteRef[]; trace?: string[];
    exhibits?: { kind: string; ref?: unknown }[];
  } & Loose;
}

export interface Company extends Loose {
  ticker: string;
  name?: string;
  needle_id?: string;
  findings: Finding[];
  rejected?: Rejected[];
  labels?: ({ comparison?: Comparison[] } & Loose) | null;
  forces?: Loose | null;
  priced_in?: Loose[];
  never_asked?: Loose[];
  consensus_vs_guidance?: Loose | null;
  ira_cut_check?: Loose[];
  comment_letters?: Loose[];
  discontinued_breakouts?: Loose[];
  transcript_grades?: Loose[];
  gtn_exposure?: Loose[];
  price_series?: Record<string, PricePoint[]>;
  stance?: Stance | null;
  questions?: Question[];
}

export interface Proof extends Loose {
  backtest?: { hit_rates?: unknown; gate2_md?: string; examples?: unknown } & Loose;
  calibration?: Loose;
  blind?: Loose;
  sealed?: { file?: unknown; canonical?: string; doc_hash?: string } & Loose;
  ai_wrong?: Loose[];
  verifier_rules?: string[];
  limits?: string[];
}

/* ------------------------------------------------------------ memos.json (chat) */

export interface MemoCite extends Loose {
  n: number; cite_id?: string; finding_id?: string | null; ticker?: string | null;
  doc_title?: string | null; period?: string | null; page?: number | string | null; quote?: string | null;
  excerpt?: Excerpt | null; url?: string | null; withheld?: boolean; withheld_reason?: string | null;
  verification?: { status?: string; score?: number; detail?: string } | string | null;
  ref?: string | null; finding_ids?: string[] | null; doc_title_raw?: string | null; value?: unknown;
  /** Operand cite_ids (or footnote numbers) of a derived figure. */
  derived_from?: (string | number)[] | null; derived_expr?: string | null;
  numeric_check?: NumericCheck | null;
}

export type MemoBlock =
  | { type: "h"; text: string }
  | { type: "p"; md: string }
  | { type: "kpi"; items: { label: string; value: string; cite?: number | null }[] }
  | { type: "table"; columns: string[]; rows: string[][] }
  | { type: "list"; items: string[] }
  | { type: "callout"; tone: "ok" | "warn" | "muted" | string; md: string }
  | { type: "math"; label?: string; text: string; text_marked?: string | null; cite?: number | null };

export interface MemoRecord extends Loose {
  id: string; prompt: string; aliases?: string[]; ticker?: string | null; kind?: string;
  /** "chat" answers in the thread; "memo" renders a document card. */
  format?: "chat" | "memo" | string;
  memo_header?: { to?: string; from?: string; re?: string; date?: string } | null;
  /** Pipeline demonstration (a decide run that is not the team's pick); the note opens the memo. */
  demo?: boolean | null; demo_note?: string | null;
  least_bad?: string | null; selection_rule?: string | null;
  generated_by?: "template" | "decide_v2" | "data" | string;
  summary?: string; blocks?: MemoBlock[]; cites?: MemoCite[]; numeric_check?: NumericCheck | null; ask_next?: string[];
}

export interface MemosFile extends Loose {
  generated_at?: string; mode?: string; engine?: string; default_ticker?: string | null;
  suggested?: string[]; memos: MemoRecord[];
  /** Per-company suggested flow, used once a company is picked in the pill. */
  suggested_by_ticker?: Record<string, string[]>;
}
