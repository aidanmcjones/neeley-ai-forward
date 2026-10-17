// Deterministic offline retriever for the Ask screen (docs/ui_spec.md, "Deterministic retriever").
//
// Never invents a number: every answer sentence is a finding sentence, an impact formula, or an
// obscurity note copied VERBATIM from companies/<T>.json, each with a {finding_id, i} cite.
// Non-finding hits (label comparison rows, forces fields, priced-in and never-asked rows) are
// returned as data rows whose values are shown as exported, with the file they came from.
//
// Scoring: query -> lowercase -> tokens (light stemming) minus stopwords -> synonym groups.
// Each indexed doc carries tokens + groups from its fields. score = sum over matched query
// terms of idf(term) x field weight x kind weight (token 1.0, synonym group 0.7), with a x2.5
// boost on drug names, x1.5 on the ticker / company name, and x0.6 for findings that are not
// verified (needs_human). Normalized by the query's own maximum score so the floor is
// comparable across questions. Preset questions are matched separately by weighted Jaccard;
// a close preset returns its precomputed answer (already composed from verbatim finding text).

import type { CiteRef, Company, Finding, Question } from "./types";

export type ExhibitKind = "timeline" | "h2h" | "price" | "peer";

export interface RetrievedFinding {
  finding: Finding;
  /** Term-overlap score with drug/ticker boosts; higher is better. */
  score: number;
  /** Query terms (after stopwords + synonym expansion) that matched. */
  matched: string[];
  /** Evidence refs this answer sentence cites. */
  cites: CiteRef[];
}

/** ref: drug slug for timeline / h2h / price, finding id for peer. */
export interface Exhibit { kind: ExhibitKind; ref: string; title?: string }

export interface TraceEntry {
  /** Document label, e.g. "BMY 10-K FY2025, p. 39". */
  label: string;
  doc_id?: string;
  /** Quote withheld under the public rule (unverified or licensed citation). */
  withheld?: boolean;
}

export interface AnswerSentence {
  /** Verbatim text from the export (finding sentence, "Impact: <formula>", or obscurity note). */
  text: string;
  cites: CiteRef[];
  kind: "finding" | "impact" | "obscurity";
  /** finding verdict, so the UI can flag needs_human sentences. */
  verdict?: string;
  /** Verbatim page quote, shown for findings whose sentence alone is generic (text drift). */
  quote?: string;
  /** For findings with no page evidence: the file or external URL they were computed from. */
  source?: { label: string; url?: string };
}

export interface DataRow {
  kind: "label" | "force" | "priced_in" | "never_asked";
  title: string;
  /** Field/value pairs exactly as exported (values stringified, never recomputed). */
  fields: [string, string][];
  /** File or table the row came from. */
  source: string;
  /** Short document label for the trace row. */
  trace: string;
  score: number;
}

export interface RetrieveResult {
  /** "preset": precomputed answer; "composed": built from top findings; "empty": nothing cited. */
  mode: "preset" | "composed" | "empty";
  preset?: Question;
  stance?: string | null;
  sentences: AnswerSentence[];
  /** Top matches (at most 5), best first. Empty means "no match": say so honestly. */
  findings: RetrievedFinding[];
  rows: DataRow[];
  exhibits: Exhibit[];
  /** Distinct documents behind the returned findings. */
  trace: TraceEntry[];
  /** Expanded query terms (shown in the trace as what was searched). */
  terms: string[];
  /** True when the preset was chosen as the nearest theme, not as a near-identical question. */
  presetFallback?: boolean;
  /** Three nearest presets, always filled (used by the empty state). */
  nearest: Question[];
}

/* ------------------------------------------------------------ text pipeline */

const STOP = new Set(`a an the and or but if then of to in on at by for with from into onto about as is are was were be been
being do does did doing have has had having it its this that these those there here what which who whom whose why how when
where i me my we our us you your he she they them their his her than so very can could should would will shall may might
must just also any all some more most much many such not no nor only own same too s t don now get got tell show give me
say says said vs versus please let lets explain describe company companys`.split(/\s+/));

/** Synonym groups. Multi-word phrases are matched on the raw lowercased text. */
const GROUPS: Record<string, string[]> = {
  ira: ["ira", "negotiation", "negotiated", "negotiate", "medicare price", "mfp", "maximum fair price", "cms", "ipay", "inflation reduction"],
  loe: ["loe", "exclusivity", "exclusive", "generic", "generics", "biosimilar", "biosimilars", "patent", "patents", "cliff", "expiry", "expire", "expires", "paragraph iv", "loss of exclusivity", "protection"],
  gtn: ["gtn", "rebate", "rebates", "net price", "gross-to-net", "gross to net", "discount", "discounts", "340b", "pricing", "price", "prices", "nadac", "wac"],
  inventory: ["inventory", "inventories", "channel", "stocking", "stock", "days", "dio", "wholesaler", "wholesalers", "destocking"],
  receivables: ["receivables", "receivable", "dso", "collections"],
  call: ["call", "calls", "q&a", "qa", "deflect", "deflected", "deflection", "analyst", "analysts", "asked", "ask", "transcript", "earnings call"],
  label: ["label", "labels", "indication", "indications", "boxed warning", "boxed", "dosing", "dose", "doses", "rems", "route", "safety", "contraindication"],
  mfn: ["mfn", "most favored nation", "most-favored-nation", "most favoured nation"],
  tariff: ["tariff", "tariffs", "manufacturing", "sites", "site", "plants", "onshoring", "reshoring", "supply"],
  forecast: ["forecast", "forecasts", "predict", "prediction", "q3", "quarter", "guidance", "consensus"],
  wrong: ["wrong", "rejected", "reject", "caught", "verifier", "error", "errors", "mistake", "hallucination"],
  priced: ["priced", "priced-in", "market", "headline", "headlines", "obscure", "obscurity", "discussed", "investors"],
  margin: ["margin", "margins", "gross margin", "profitability", "cost of sales"],
  tax: ["tax", "etr", "effective tax"],
  rnd: ["r&d", "rnd", "research", "development", "pipeline"],
  ceo: ["ceo", "should", "recommend", "recommendation", "move", "decision", "stance", "defend", "attack", "reprice", "partner", "strategy"],
};
// Topic slugs from vector.topics / priced_in topics that map onto groups.
const TOPIC_GROUP: Record<string, string> = {
  ira: "ira", ira_negotiation: "ira", gtn: "gtn", gross_to_net_price: "gtn", pricing: "gtn", "340b": "gtn",
  generic: "loe", biosimilar_generic: "loe", tariff: "tariff", supply: "tariff", mfn: "mfn", inventory_channel: "inventory",
  gross_margin: "margin", tax: "tax", rnd: "rnd", pipeline: "rnd", guidance: "forecast", china: "tariff",
};

const PHRASES = Object.entries(GROUPS).flatMap(([g, ws]) => ws.filter((w) => /[\s&-]/.test(w)).map((w) => [w, g] as const));
const WORD_GROUP = new Map<string, string>();
for (const [g, ws] of Object.entries(GROUPS)) for (const w of ws) if (!/[\s&-]/.test(w)) WORD_GROUP.set(stem(w), g);

function stem(w: string): string {
  if (w.length > 5 && w.endsWith("ing")) return w.slice(0, -3);
  if (w.length > 4 && w.endsWith("ies")) return w.slice(0, -3) + "y";
  if (w.length > 4 && w.endsWith("es") && !w.endsWith("ses")) return w.slice(0, -2);
  if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1);
  if (w.length > 5 && w.endsWith("ed")) return w.slice(0, -2);
  return w;
}

/** Lowercase, keep q&a / r&d, split, drop stopwords and 1-char tokens, stem. */
export function tokens(text: string): string[] {
  const low = text.toLowerCase().replace(/q\s*&\s*a/g, " qa ").replace(/r\s*&\s*d/g, " rnd ").replace(/[_/]/g, " ");
  return low.split(/[^a-z0-9.]+/).map((t) => t.replace(/^\.+|\.+$/g, ""))
    .filter((t) => t.length > 1 && !STOP.has(t)).map(stem);
}

/** Tokens plus "#group" synonym ids. */
function terms(text: string, extraTopics: string[] = []): Set<string> {
  const out = new Set<string>();
  const low = text.toLowerCase();
  for (const [p, g] of PHRASES) if (low.includes(p)) out.add(`#${g}`);
  for (const t of tokens(text)) {
    out.add(t);
    const g = WORD_GROUP.get(t);
    if (g) out.add(`#${g}`);
  }
  for (const tp of extraTopics) {
    const g = TOPIC_GROUP[tp.toLowerCase()];
    if (g) out.add(`#${g}`);
    for (const t of tokens(tp)) out.add(t);
  }
  return out;
}

/* ------------------------------------------------------------------- index */

interface Doc {
  kind: "finding" | DataRow["kind"];
  /** field terms with weights */
  fields: { terms: Set<string>; w: number }[];
  all: Set<string>;
  drugs: Set<string>;
  finding?: Finding;
  row?: Omit<DataRow, "score">;
}

interface Index {
  docs: Doc[];
  idf: Map<string, number>;
  drugs: string[];
  products: string[];
  presets: { q: Question; terms: Set<string> }[];
  nameTerms: Set<string>;
}

const cache = new Map<string, { company: Company; index: Index }>();

const str = (v: unknown): string => {
  if (v == null) return "n/a";
  if (Array.isArray(v)) return v.map(str).join("; ");
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
};

export function caseDrugs(c: Company): { drugs: string[]; products: string[] } {
  const set = new Set<string>();
  const products: string[] = [];
  for (const cmp of c.labels?.comparison ?? []) {
    products.push(cmp.product.toLowerCase());
    set.add(cmp.product.toLowerCase());
    for (const r of cmp.rivals ?? []) set.add(r.toLowerCase());
  }
  const cs = c.case_set as Record<string, string[]> | undefined;
  if (cs && typeof cs === "object") for (const [p, rs] of Object.entries(cs)) { set.add(p.toLowerCase()); if (!products.includes(p.toLowerCase())) products.push(p.toLowerCase()); for (const r of rs ?? []) set.add(String(r).toLowerCase()); }
  for (const k of Object.keys(c.price_series ?? {})) set.add(k.toLowerCase());
  return { drugs: [...set], products };
}

function drugsIn(text: string, drugs: string[]): Set<string> {
  const low = text.toLowerCase();
  return new Set(drugs.filter((d) => new RegExp(`\\b${d.replace(/[^a-z0-9]/g, ".")}\\b`).test(low)));
}

const FORCE_LABELS: Record<string, string> = {
  ira_drugs: "IRA-selected drugs", ira_share_of_total_revenue_pct: "IRA share of revenue (%)", ira_share_incl_partnered_pct: "IRA share incl. partnered (%)",
  ira_partnered_drugs_not_counted: "Partnered IRA drugs not counted", mfn_date: "MFN agreement date", us_investment_pledge_usd_bn: "US investment pledge ($bn)",
  pledge_scope: "Pledge scope", pledge_note: "Pledge note", tariff_exempt_until: "Tariff exempt until", pct_mfg_sites_outside_us: "Manufacturing sites outside US (%)",
  mfg_sites_total: "Manufacturing sites matched", mfg_sites_confidence: "Site count confidence", us_revenue_share_pct: "US revenue share (%)",
};
const FORCE_TEXT: Record<string, string> = {
  ira_drugs: "ira negotiation medicare price selected drugs", ira_share_of_total_revenue_pct: "ira share revenue exposure negotiation",
  ira_share_incl_partnered_pct: "ira share partnered", ira_partnered_drugs_not_counted: "ira partnered", mfn_date: "mfn most favored nation date deal",
  us_investment_pledge_usd_bn: "us investment pledge tariff manufacturing", pledge_scope: "pledge manufacturing", pledge_note: "pledge manufacturing",
  tariff_exempt_until: "tariff exemption date", pct_mfg_sites_outside_us: "tariff manufacturing sites outside us", mfg_sites_total: "manufacturing sites",
  mfg_sites_confidence: "manufacturing sites", us_revenue_share_pct: "us revenue share tariff mfn exposure",
};
const PRICED_FIELDS = ["topic", "analyst_attention_tier", "quarter_range", "quarters_asked", "quarters_covered", "last_quarter_asked", "recent_unasked_streak",
  "mean_abn_0_to_1_when_asked", "mean_abn_0_to_1_not_asked", "latest_example_quarter", "latest_example_speaker"];
const NEVER_FIELDS = ["topic", "quarter_range", "quarters_asked", "quarters_covered", "last_asked", "recent_unasked_streak", "flag"];

function buildIndex(c: Company): Index {
  const { drugs, products } = caseDrugs(c);
  const docs: Doc[] = [];
  const mk = (kind: Doc["kind"], fields: { text: string; w: number; topics?: string[] }[], extra: Partial<Doc>): Doc => {
    const fs = fields.map((f) => ({ terms: terms(f.text, f.topics), w: f.w }));
    const all = new Set<string>();
    for (const f of fs) for (const t of f.terms) all.add(t);
    const dr = drugsIn(fields.map((f) => f.text).join(" "), drugs);
    for (const d of dr) all.add(d);
    return { kind, fields: fs, all, drugs: dr, ...extra };
  };

  for (const f of c.findings) {
    const ev = f.evidence ?? [];
    docs.push(mk("finding", [
      { text: f.finding ?? "", w: 1.0 },
      { text: [f.signal_kind ?? "", f.detector ?? ""].join(" "), w: 0.8 },
      { text: "", w: 1.0, topics: f.vector?.topics ?? [] },
      { text: [f.impact?.formula ?? "", f.vector?.obscurity_note ?? ""].join(" "), w: 0.5 },
      { text: ev.map((e) => `${e.citation ?? ""} ${e.doc_type ?? ""} ${e.speaker ?? ""}`).join(" "), w: 0.4 },
      { text: ev.map((e) => e.quote ?? "").join(" "), w: 0.35 },
    ], { finding: f }));
  }
  for (const cmp of c.labels?.comparison ?? []) {
    for (const r of cmp.rows ?? []) {
      const vals = Object.entries(r.values ?? {});
      const fields: [string, string][] = vals.map(([slug, v]) => [slug, str(v?.value)]);
      const srcs = [...new Set(vals.map(([, v]) => v?.source).filter(Boolean))];
      docs.push(mk("label", [
        { text: `${r.label ?? ""} ${r.field}`, w: 1.0 },
        { text: `${cmp.product} ${(cmp.rivals ?? []).join(" ")} label`, w: 0.6 },
        { text: fields.map((x) => x[1]).join(" "), w: 0.3 },
      ], { row: { kind: "label", title: `${r.label ?? r.field}: ${cmp.product} vs ${(cmp.rivals ?? []).join(", ")}`, fields,
        source: `labels.comparison (out/${c.ticker}/labels_table.json${srcs.length ? `; ${srcs.slice(0, 2).join("; ")}` : ""})`,
        trace: "FDA labels + Orange / Purple Book (labels_table.json)" } }));
    }
  }
  const forces = c.forces ?? {};
  for (const [k, label] of Object.entries(FORCE_LABELS)) {
    if (!(k in forces)) continue;
    docs.push(mk("force", [{ text: `${label} ${FORCE_TEXT[k] ?? ""}`, w: 1.0 }, { text: str(forces[k]), w: 0.4 }],
      { row: { kind: "force", title: label, fields: [[label, str(forces[k])]], source: "forces (data/moat/verified/policy/force_summary.csv)",
      trace: "CMS, White House and FDA site files (force_summary.csv)" } }));
  }
  for (const r of c.priced_in ?? []) {
    const topic = str(r.topic);
    docs.push(mk("priced_in", [{ text: `${topic.replace(/_/g, " ")} priced analyst attention market return`, w: 1.0, topics: [topic] },
      { text: str(r.latest_example_quote), w: 0.25 }],
      { row: { kind: "priced_in", title: `Priced-in scorecard: ${topic}`, fields: PRICED_FIELDS.filter((f) => f in r).map((f) => [f, str(r[f])]),
        source: str(r.source ?? "data/moat/verified/market/priced_in_scorecard.csv"),
        trace: "Call transcripts + event returns (priced_in_scorecard.csv)" } }));
  }
  for (const r of c.never_asked ?? []) {
    const topic = str(r.topic);
    docs.push(mk("never_asked", [{ text: `${topic.replace(/_/g, " ")} never asked analyst call unasked`, w: 1.0, topics: [topic] }],
      { row: { kind: "never_asked", title: `Never asked: ${topic}`, fields: NEVER_FIELDS.filter((f) => f in r).map((f) => [f, str(r[f])]),
        source: "data/moat/verified/market/never_asked.csv", trace: "Call transcripts (never_asked.csv)" } }));
  }

  const df = new Map<string, number>();
  for (const d of docs) for (const t of d.all) df.set(t, (df.get(t) ?? 0) + 1);
  const N = Math.max(1, docs.length);
  const idf = new Map<string, number>();
  for (const [t, n] of df) idf.set(t, Math.log(1 + N / n));

  const presets = (c.questions ?? []).map((q) => ({ q, terms: terms(q.q) }));
  const nameTerms = terms(`${c.ticker} ${c.name ?? ""}`);
  return { docs, idf, drugs, products, presets, nameTerms };
}

function getIndex(c: Company): Index {
  const hit = cache.get(c.ticker);
  if (hit && hit.company === c) return hit.index;
  const index = buildIndex(c);
  cache.set(c.ticker, { company: c, index });
  return index;
}

/* ------------------------------------------------------------------- query */

const DATE_RE = /\b(when|date|dates|timeline|year|years|20\d\d|exclusiv\w*|cliff|generic\w*|biosimilar\w*|patent\w*|loe|expir\w*|lose|loss)\b/;
const COMPARE_RE = /\b(compare|comparison|vs\.?|versus|rival\w*|against|head[- ]to[- ]head|competitor\w*|beat)\b/;
const PRICE_RE = /\b(price|prices|pricing|gtn|gross[- ]to[- ]net|net price|medicare|mfp|rebate\w*|nadac|wac|cost|ira|negotiat\w*|part d)\b/;
const CEO_RE = /\b(ceo|should|recommend\w*|what (would|should) .* do|move|decision|stance|strategy|action)\b/;
const PRICED_RE = /\b(priced|priced[- ]in|market|headline\w*|consensus|investors?)\b/;

function weightedJaccard(a: Set<string>, b: Set<string>, idf: Map<string, number>): number {
  let inter = 0, uni = 0;
  const w = (t: string) => idf.get(t) ?? 2.5;
  for (const t of new Set([...a, ...b])) {
    const x = w(t);
    uni += x;
    if (a.has(t) && b.has(t)) inter += x;
  }
  return uni ? inter / uni : 0;
}

function scoreDoc(d: Doc, q: Set<string>, ix: Index, qDrugs: Set<string>): { score: number; matched: string[] } {
  let score = 0;
  const matched: string[] = [];
  for (const t of q) {
    let best = 0;
    for (const f of d.fields) if (f.terms.has(t)) best = Math.max(best, f.w);
    if (!best && d.drugs.has(t)) best = 1;
    if (!best) continue;
    const kindW = t.startsWith("#") ? 0.7 : 1.0;
    let boost = 1;
    if (qDrugs.has(t)) boost = 2.5;
    else if (ix.nameTerms.has(t)) boost = 1.5;
    score += (ix.idf.get(t) ?? 1) * best * kindW * boost;
    matched.push(t);
  }
  // Only group-level matches (no shared word) count for less: synonyms alone are weak evidence.
  if (matched.length && matched.every((m) => m.startsWith("#"))) score *= 0.75;
  if (d.finding && d.finding.verdict && d.finding.verdict !== "verified") score *= 0.6;
  if (d.finding && !d.finding.evidence?.length) score *= 0.85;
  return { score, matched };
}

const FLOOR = 0.22;           // normalized score below which a doc does not count as a hit
const PRESET_THRESHOLD = 0.55; // weighted Jaccard at which a preset's precomputed answer is returned

export function presets(company: Company | null | undefined): Question[] {
  return company?.questions ?? [];
}

function citeOf(f: Finding): CiteRef[] {
  return f.evidence?.length ? [{ finding_id: f.id, i: 0 }] : [];
}

function traceFromFindings(fs: Finding[]): TraceEntry[] {
  const seen = new Map<string, TraceEntry>();
  for (const f of fs) for (const e of (f.evidence ?? []).slice(0, 2)) {
    const label = e.citation || [e.doc_id, e.page != null ? `p. ${e.printed || e.page}` : ""].filter(Boolean).join(", ");
    if (label && !seen.has(label)) seen.set(label, { label, doc_id: e.doc_id, withheld: e.withheld === true });
  }
  return [...seen.values()];
}

function pickProduct(ix: Index, c: Company, qDrugs: Set<string>): string | undefined {
  const cmps = c.labels?.comparison ?? [];
  const named = [...qDrugs];
  const asProduct = named.find((d) => ix.products.includes(d) && cmps.some((x) => x.product.toLowerCase() === d));
  if (asProduct) return asProduct;
  const viaRival = cmps.find((x) => (x.rivals ?? []).some((r) => qDrugs.has(r.toLowerCase())));
  if (viaRival) return viaRival.product.toLowerCase();
  return cmps[0]?.product.toLowerCase();
}

function chooseExhibits(query: string, ix: Index, c: Company, qDrugs: Set<string>, top: Finding[]): Exhibit[] {
  const low = query.toLowerCase();
  const out: Exhibit[] = [];
  const product = pickProduct(ix, c, qDrugs);
  const hasCmp = !!(c.labels?.comparison ?? []).length;
  if (product && hasCmp && DATE_RE.test(low)) out.push({ kind: "timeline", ref: product });
  if (product && hasCmp && (qDrugs.size >= 2 || COMPARE_RE.test(low))) out.push({ kind: "h2h", ref: product });
  if (product && (c.price_series?.[product]?.length ?? 0) > 0 && PRICE_RE.test(low)) out.push({ kind: "price", ref: product });
  if (!out.length) {
    const peer = top.find((f) => f.peer?.metric_value != null && f.peer?.peer_median != null && !!f.peer?.z);
    if (peer) out.push({ kind: "peer", ref: peer.id });
    else if (product && qDrugs.size) out.push({ kind: "h2h", ref: product });
  }
  return out;
}

/** Source for a finding that carries no page evidence (label table rows, openFDA / registry pulls). */
function fallbackSource(f: Finding, _c: Company): AnswerSentence["source"] {
  if (f.evidence?.length) return undefined;
  const ext = Array.isArray(f.external_sources) ? (f.external_sources as unknown[]).map(String) : [];
  if (ext.length) {
    const u = ext[0];
    const label = /api\.fda\.gov\/drug\/event/.test(u) ? "openFDA FAERS adverse-event query" : /clinicaltrials\.gov/.test(u) ? "ClinicalTrials.gov record" : "External source";
    return { label, url: u };
  }
  if (f.detector === "labels") return { label: "FDA labels + Orange / Purple Book (labels_table.json)" };
  return { label: `${f.detector ?? "detector"} output (no page evidence exported)` };
}

const GENERIC_SENTENCE = /^(new paragraph|paragraph dropped|reworded paragraph|paragraph)/i;

export function retrieve(query: string, company: Company): RetrieveResult {
  const ix = getIndex(company);
  const q = terms(query);
  const qDrugs = drugsIn(query, ix.drugs);
  for (const d of qDrugs) q.add(d);
  const termList = [...new Set([...query.toLowerCase().split(/[^a-z0-9&]+/).filter((w) => w.length > 1 && !STOP.has(w)), ...[...q].filter((t) => t.startsWith("#"))])];

  // Nearest presets (always computed) and exact-ish preset match.
  const ranked = ix.presets
    .map((p) => ({ p, s: weightedJaccard(q, p.terms, ix.idf) + (p.q.q.trim().toLowerCase() === query.trim().toLowerCase() ? 1 : 0) }))
    .sort((a, b) => b.s - a.s);
  const nearest = ranked.slice(0, 3).map((r) => r.p.q);
  const base: Omit<RetrieveResult, "mode"> = { sentences: [], findings: [], rows: [], exhibits: [], trace: [], terms: termList, nearest };

  if (!q.size) return { ...base, mode: "empty" };

  const best = ranked[0];
  if (best && best.s >= PRESET_THRESHOLD && best.p.q.answer) {
    return presetResult(best.p.q, company, base);
  }

  // Max achievable score for this query: every term matched at weight 1 with its boost.
  let maxScore = 0;
  for (const t of q) maxScore += (ix.idf.get(t) ?? 1) * (t.startsWith("#") ? 0.7 : 1) * (qDrugs.has(t) ? 2.5 : 1);
  maxScore = Math.max(maxScore, 1e-9);

  const scored = ix.docs.map((d) => ({ d, ...scoreDoc(d, q, ix, qDrugs) }))
    .map((x) => ({ ...x, norm: x.score / maxScore }))
    .filter((x) => x.norm >= FLOOR)
    .sort((a, b) => b.norm - a.norm || (b.d.finding?.score ?? 0) - (a.d.finding?.score ?? 0));

  // Findings: dedupe identical sentences, keep top 5.
  const seenText = new Set<string>();
  const fhits: RetrievedFinding[] = [];
  for (const x of scored) {
    const f = x.d.finding;
    if (!f) continue;
    const key = f.finding.trim().toLowerCase();
    if (seenText.has(key)) continue;
    seenText.add(key);
    fhits.push({ finding: f, score: Number(x.norm.toFixed(3)), matched: x.matched, cites: citeOf(f) });
    if (fhits.length >= 5) break;
  }
  const rowHits = scored.filter((x) => x.d.row);
  const rowTop = rowHits[0]?.norm ?? 0;
  const rows: DataRow[] = rowHits.filter((x) => x.norm >= 0.6 * rowTop).slice(0, 4).map((x) => ({ ...x.d.row!, score: Number(x.norm.toFixed(3)) }));

  if (!fhits.length && !rows.length) {
    // Nothing indexed matched, but a preset on the same theme is close: answer with it, flagged.
    if (best && best.s >= 0.25 && best.p.q.answer) return { ...presetResult(best.p.q, company, base), presetFallback: true };
    return { ...base, mode: "empty" };
  }

  // Compose 2 to 4 verbatim sentences from the top findings.
  const sentences: AnswerSentence[] = [];
  const low = query.toLowerCase();
  const wantsPriced = PRICED_RE.test(low);
  const topScore = fhits[0]?.score ?? 0;
  for (const [n, h] of fhits.slice(0, 3).entries()) {
    if (sentences.length >= 4) break;
    // Keep follow-on sentences only when they are nearly as relevant as the lead.
    if (n > 0 && h.score < 0.6 * topScore) break;
    const f = h.finding;
    const generic = GENERIC_SENTENCE.test(f.finding);
    const quote = generic ? f.evidence?.[0]?.quote : undefined;
    sentences.push({ text: f.finding, cites: h.cites, kind: "finding", verdict: f.verdict, quote, source: fallbackSource(f, company) });
    const formula = f.impact?.formula;
    if (sentences.length < 4 && formula && !/^no direct dollar path/i.test(formula) && !f.impact?.suspect) {
      sentences.push({ text: `Impact: ${formula}`, cites: h.cites, kind: "impact", verdict: f.verdict });
    }
  }
  const lead = fhits[0]?.finding;
  if (wantsPriced && lead?.vector?.obscurity_note && sentences.length < 4) {
    sentences.push({ text: `Why it may not be priced in: ${lead.vector.obscurity_note}`, cites: citeOf(lead), kind: "obscurity", verdict: lead.verdict });
  }

  const stance = CEO_RE.test(low) ? company.stance?.recommended ?? null : null;
  const usedIds = new Set(sentences.flatMap((s) => s.cites.map((x) => x.finding_id)));
  const used = fhits.map((h) => h.finding).filter((f) => usedIds.has(f.id) || sentences.some((s) => s.text === f.finding));
  const trace = traceFromFindings(used);
  for (const s of sentences) if (s.source && !trace.some((t) => t.label === s.source!.label)) trace.push({ label: s.source.label });
  for (const r of rows) if (!trace.some((t) => t.label === r.trace)) trace.push({ label: r.trace });

  return {
    ...base,
    mode: "composed",
    stance,
    sentences,
    findings: fhits,
    rows,
    exhibits: chooseExhibits(query, ix, company, qDrugs, fhits.map((h) => h.finding)),
    trace,
  };
}

/** A preset's precomputed answer, split into its verbatim sentences and paired with its cites. */
function presetResult(p: Question, c: Company, base: Omit<RetrieveResult, "mode">): RetrieveResult {
  const a = p.answer!;
  const cites = a.cites ?? [];
  const byId = new Map(c.findings.map((f) => [f.id, f]));
  // Pair each cited finding's verbatim sentence with its cite; fall back to the stored text.
  const sentences: AnswerSentence[] = [];
  let rest = a.text ?? "";
  for (const ref of cites) {
    const f = byId.get(ref.finding_id);
    if (!f) continue;
    const at = rest.indexOf(f.finding);
    if (at < 0) continue;
    rest = rest.slice(0, at) + rest.slice(at + f.finding.length);
    sentences.push({ text: f.finding, cites: [ref], kind: "finding", verdict: f.verdict });
    const formula = f.impact?.formula;
    if (formula && rest.includes(formula)) {
      rest = rest.replace(`Impact: ${formula}`, "").replace(formula, "");
      sentences.push({ text: `Impact: ${formula}`, cites: [ref], kind: "impact", verdict: f.verdict });
    }
  }
  const leftover = rest.replace(/\s+/g, " ").replace(/(?:\s*\.){2,}\s*/g, ". ").replace(/^[\s.;]+|[\s;]+$/g, "");
  if (leftover.length > 3) {
    // Text the exporter composed (obscurity note, rejected-claim log): cite the first ref if any.
    sentences.push({ text: leftover.endsWith(".") ? leftover : `${leftover}.`, cites: cites.slice(0, 1), kind: "obscurity" });
  }
  const fs = cites.map((r) => byId.get(r.finding_id)).filter((f): f is Finding => !!f);
  const docTrace = traceFromFindings(fs);
  const trace: TraceEntry[] = [...docTrace];
  for (const t of a.trace ?? []) if (!trace.some((x) => x.label.startsWith(t))) trace.push({ label: t });
  const refs = Array.isArray(a.data_refs) ? (a.data_refs as string[]) : [];
  for (const r of refs) if (!trace.some((x) => x.label === r)) trace.push({ label: r });
  const exhibits: Exhibit[] = (a.exhibits ?? [])
    .map((e) => ({ kind: e.kind as ExhibitKind, ref: String(e.ref ?? "") }))
    .filter((e) => ["timeline", "h2h", "price", "peer"].includes(e.kind) && e.ref);
  return {
    ...base,
    mode: "preset",
    preset: p,
    stance: a.stance ?? null,
    sentences,
    findings: fs.map((f) => ({ finding: f, score: 1, matched: [], cites: citeOf(f) })),
    exhibits,
    trace,
  };
}
