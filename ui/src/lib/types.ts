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
}

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
}

export interface Impact extends Loose {
  formula?: string; dollars?: number | null; base?: number | null; bear?: number | null;
  bull?: number | null; line?: string; eps?: number | null;
}

export interface Peer extends Loose { metric_value?: number | null; peer_median?: number | null; z?: number | null; note?: string }

export interface Vector extends Loose {
  I_norm?: number; P?: number; T?: number; Z?: number; D?: number; O?: number; E?: number;
  obscurity_note?: string; topics?: string[];
}

export interface Finding extends Loose {
  id: string;
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
