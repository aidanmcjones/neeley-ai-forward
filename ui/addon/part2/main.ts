/* NEEDLE Part 2 add-on for Parker's page.
 *
 * One self-contained script, loaded after his bundle by a single <script> line in his index.html. It does not
 * touch his bundle, his styles or his state. It watches the chat for a finished Part 1 answer, adds one
 * follow-up chip, "Part 2: CEO move", to that answer's "Ask next" row, and on click appends a new chat turn
 * (user bubble, a short thinking state built from the Part 2 reasoning trace, then the cached Part 2 answer)
 * rendered with his house classes: nd-lead, nd-sec, nd-list, nd-facts, nd-verdict, sup.cite-n footnotes and
 * details.cite-notes source lists. Every string comes from data/part2/<T>.json (agent/ui_part2_export.py,
 * docs/part2/UI_CONTRACT.md); the only sentence this file writes is the student-concept label the case requires.
 *
 * Source: ui/addon/part2/main.ts (PR #22). Build: cd ui && npx vite build --config addon/part2/vite.config.ts
 */

type Rec = Record<string, any>;

const PROMPT = "recommend one strategic move for the next 24 months, with a specific budget or commitment of people behind it.";
const BANNER = "Student concept, not actual promotional material.";
const DATA = "./data/part2/";
const WITHHELD = "[figure withheld: not gated]";
const CHIP_CLS = "rounded-full border border-purple/40 bg-surface px-3 py-1.5 text-[13px] text-purple hover:bg-chip text-left";
const INTERNAL = /\bS ?= |score L\b|\bL ?= |\bL \d*\.\d+|\bS \d*\.\d+|robustness|obscurity|scoring variants?|vs v2|M x O x E|M × O × E|floor[_ ]relaxed|needle status|\bstatus (strict|provisional|floor relaxed|none)\b|\bprovisional\b|\bstrict\b|league(_v\d)?\b/i;
const TOKEN = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[\d+\]|\[derived:\s*[^\]]+\]|\[constant:\s*[^\]]+\]|\[assumption(?::\s*[^\]]+)?\])/g;
const MOVE_TYPES: Rec = { license_or_acquire: "License or acquire", pricing_or_coverage: "Pricing or coverage", portfolio_shift: "Portfolio shift", new_indication: "New indication", campaign: "Campaign" };

const STYLE = `
.p2-eyebrow{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:rgb(var(--purple))}
.p2-h2{margin:2px 0 0;font-size:22px;font-weight:600;line-height:1.2;color:rgb(var(--fg))}
.p2-h2 span{font-size:15px;font-weight:600;color:rgb(var(--muted))}
.p2-p{margin:0;max-width:68ch;font-size:14px;line-height:1.6;color:rgb(var(--fg))}
.p2-muted{color:rgb(var(--muted))}
.p2-withheld{font-style:italic;color:rgb(var(--muted))}
.p2-link{background:none;border:0;padding:0;font:inherit;font-size:13px;font-weight:600;color:rgb(var(--purple));cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.p2-link:hover{color:rgb(var(--fg))}
.p2-steps{margin:8px 0 0;padding:0 0 0 1.5em;display:grid;gap:8px;font-size:13.5px;line-height:1.6;color:rgb(var(--fg))}
.p2-steps li{padding-left:2px}
.p2-steps li::marker{color:rgb(var(--muted));font-variant-numeric:tabular-nums}
.p2-banner{border:2px solid rgb(var(--warn));background:rgb(var(--warn)/.1);color:rgb(var(--warn));font-weight:600;border-radius:6px;padding:8px 12px;font-size:13.5px;line-height:1.5}
.p2-piece{border:1px solid rgb(var(--line));border-radius:8px;padding:14px 16px;display:grid;gap:8px;background:rgb(var(--surface))}
.p2-piece h4{margin:0;font-size:16px;font-weight:700;line-height:1.35;color:rgb(var(--fg))}
.p2-piece .p2-tag{font-size:11px;color:rgb(var(--muted))}
.p2-rules{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px;font-size:11.5px}
.p2-rules li{border:1px solid;border-radius:4px;padding:1px 6px}
.p2-rules .is-ok{color:rgb(var(--good));border-color:rgb(var(--good)/.5);background:rgb(var(--good)/.1)}
.p2-rules .is-no{color:rgb(var(--bad));border-color:rgb(var(--bad)/.5);background:rgb(var(--bad)/.1)}
.p2-scroll{overflow-x:auto;border:1px solid rgb(var(--line));border-radius:8px;background:rgb(var(--surface));max-width:100%}
.p2-table{width:100%;min-width:560px;border-collapse:collapse;table-layout:fixed;font-size:13px;line-height:1.5}
.p2-table th{text-align:left;padding:8px 10px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:rgb(var(--muted));background:rgb(var(--surface-2));border-bottom:1px solid rgb(var(--line))}
.p2-table td{padding:8px 10px;vertical-align:top;border-top:1px solid rgb(var(--line));overflow-wrap:anywhere;color:rgb(var(--fg))}
.p2-table tbody tr:first-child td{border-top:0}
.p2-pill{display:inline-block;border:1px solid;border-radius:4px;padding:1px 7px;font-size:12px;font-weight:600;line-height:1.5;font-variant-numeric:tabular-nums}
.p2-pill.is-good{color:rgb(var(--good));border-color:rgb(var(--good)/.5);background:rgb(var(--good)/.1)}
.p2-pill.is-bad{color:rgb(var(--bad));border-color:rgb(var(--bad)/.5);background:rgb(var(--bad)/.1)}
.p2-pill.is-muted{color:rgb(var(--muted));border-style:dashed;border-color:rgb(var(--muted)/.6)}
.p2-verdict{display:inline-block;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;border:1px solid;border-radius:4px;padding:0 5px;line-height:1.6}
.p2-verdict.is-survived{color:rgb(var(--good));border-color:rgb(var(--good)/.5);background:rgb(var(--good)/.1)}
.p2-verdict.is-narrowed{color:rgb(var(--warn));border-color:rgb(var(--warn)/.6);background:rgb(var(--warn)/.1)}
.p2-verdict.is-killed{color:rgb(var(--bad));border-color:rgb(var(--bad)/.5);background:rgb(var(--bad)/.1)}
.p2-rounds{display:grid;gap:6px;margin-top:8px;padding-left:10px;border-left:2px solid rgb(var(--line));font-size:12.5px;line-height:1.55;color:rgb(var(--fg))}
.p2-rounds .p2-lens{font-weight:600;color:rgb(var(--muted))}
.p2-rounds .p2-rtag{display:inline-block;margin-right:4px;border:1px solid rgb(var(--line));border-radius:3px;padding:0 4px;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:rgb(var(--muted))}
.p2-numbers{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:13px;color:rgb(var(--muted))}
sup.cite-n.p2-a{color:rgb(var(--warn))}
.p2-turn .nd-lead-why p{color:rgb(var(--fg))}
.p2-turn .nd-facts dd .cite-notes,.p2-turn .nd-verdict dd .cite-notes{margin-top:.35em}
@media (max-width:640px){.p2-h2{font-size:20px}}
`;

/* ---------- small DOM helpers ---------- */
function h(tag: string, attrs: Rec | null = null, ...kids: Array<Node | string | null | undefined | false>): HTMLElement {
  const e = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = String(v);
    else if (k === "text") e.textContent = String(v);
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2), v as EventListener);
    else e.setAttribute(k, v === true ? "" : String(v));
  }
  for (const k of kids) if (k != null && k !== false) e.append(k as Node | string);
  return e;
}
const str = (x: unknown) => (typeof x === "string" ? x : null);
const arr = <T = Rec,>(x: unknown): T[] => (Array.isArray(x) ? (x as T[]) : []);
const num = (x: unknown) => (typeof x === "number" && Number.isFinite(x) ? x : null);
/** Pitch rule: drop any sentence that names league or scoring internals. */
function scrub(s: unknown): string {
  const t = str(s);
  if (!t) return "";
  return t.split(/(?<=[.!?])\s+/).filter((x) => !INTERNAL.test(x)).join(" ");
}
function moveType(t: unknown): string {
  const s = str(t);
  if (!s) return "";
  if (MOVE_TYPES[s]) return MOVE_TYPES[s];
  return (s.startsWith("other:") ? s.slice(6) : s).replace(/[_-]+/g, " ").trim();
}
const reduceMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

/* ---------- data ---------- */
async function getJson(name: string): Promise<Rec | null> {
  try {
    const r = await fetch(DATA + name, { cache: "no-cache" });
    if (!r.ok) return null;
    return (await r.json()) as Rec;
  } catch { return null; }
}
const companyCache = new Map<string, Promise<{ co: Rec | null; trace: Rec | null }>>();
function loadCompany(t: string) {
  if (!companyCache.has(t)) companyCache.set(t, Promise.all([getJson(`${t}.json`), getJson(`${t}_trace.json`)]).then(([co, trace]) => ({ co, trace })));
  return companyCache.get(t)!;
}

/* ---------- citations in Parker's footnote style ---------- */
interface Ev extends Rec { cite_id?: string }
function citeLabel(e: Ev): string {
  if (str(e.citation)) return scrub(e.citation);
  if (str(e.label)) return scrub(e.label);
  const page = e.page != null && e.page !== "" ? (/^p/i.test(String(e.page)) ? String(e.page) : `p. ${e.page}`) : str(e.location) ?? "";
  return [str(e.doc_title), str(e.period) && !(str(e.doc_title) ?? "").includes(e.period) ? e.period : null, page].filter(Boolean).join(", ") || str(e.doc_id) || str(e.cite_id) || "Source";
}
/** Public link for a source: the document URL, else a public dataset link; never a local viewer. */
function citeHref(e: Ev): string | null {
  for (const k of ["url", "deep_link", "viewer_link", "source_url"]) {
    const v = str(e[k]);
    if (v && /^https:\/\//i.test(v)) return v;
  }
  return null;
}
/** Every evidence object in the company file by cite_id. */
function citeIndex(co: Rec): Map<string, Ev> {
  const m = new Map<string, Ev>();
  const walk = (x: unknown, d: number) => {
    if (!x || typeof x !== "object" || d > 10) return;
    if (Array.isArray(x)) { for (const y of x) walk(y, d + 1); return; }
    const o = x as Rec;
    if (typeof o.cite_id === "string" && !m.has(o.cite_id) && (o.doc_id != null || o.quote != null || o.doc_title != null)) m.set(o.cite_id, o as Ev);
    for (const v of Object.values(o)) if (v && typeof v === "object") walk(v, d + 1);
  };
  walk(co, 0);
  return m;
}

/** Footnote numbers for one answer, in first-appearance order (Parker numbers Part 1 the same way). */
class Notes {
  private n = new Map<string, number>();
  unresolved = 0;
  sups = 0;
  constructor(readonly ix: Map<string, Ev>) {}
  number(e: Ev): number {
    const key = str(e.cite_id) ?? `${e.doc_id}|${e.page}|${e.quote}`;
    let v = this.n.get(key);
    if (!v) { v = this.n.size + 1; this.n.set(key, v); }
    return v;
  }
  resolver(rec: Rec | null | undefined) {
    const map = (rec?.marker_map ?? null) as Rec | null;
    const local = arr<Ev>(rec?.cites);
    return (k: number): Ev | undefined => {
      const id = map?.[String(k)];
      if (typeof id === "string" && this.ix.has(id)) return this.ix.get(id);
      const l = local.find((e) => Number(e.n) === k) ?? local[k - 1];
      if (l) return l.cite_id && this.ix.has(l.cite_id) ? this.ix.get(l.cite_id) : l;
      return undefined;
    };
  }
}

interface Marked { frag: DocumentFragment; used: Ev[]; assumed: boolean }
/** Marked text to inline nodes: [n] becomes a footnote number, runs are joined with commas, the rest is minimal markdown. */
function renderMarked(text: string, resolve: (k: number) => Ev | undefined, notes: Notes): Marked {
  const frag = document.createDocumentFragment();
  const used: Ev[] = [];
  const seen = new Set<Ev>();
  let assumed = false;
  let lastWasSup = false;
  const sup = (label: string, title: string, cls = "") => {
    if (lastWasSup) frag.append(h("sup", { class: "cite-n", text: "," }));
    frag.append(h("sup", { class: `cite-n${cls ? ` ${cls}` : ""}`, title, text: label }));
    notes.sups += 1;
    lastWasSup = true;
  };
  const cite = (k: number) => {
    const e = resolve(k);
    if (!e) { notes.unresolved += 1; sup("?", "No source exported for this marker"); return; }
    if (!seen.has(e)) { seen.add(e); used.push(e); }
    sup(String(notes.number(e)), citeLabel(e));
  };
  const parts = text.replace(new RegExp(WITHHELD.replace(/[[\]]/g, "\\$&"), "g"), "\u0000").split(TOKEN).filter((x) => x !== "");
  for (const p of parts) {
    let m: RegExpMatchArray | null;
    if ((m = p.match(/^\[(\d+)\]$/))) { cite(Number(m[1])); continue; }
    if ((m = p.match(/^\[assumption(?::\s*([^\]]+))?\]$/))) { assumed = true; sup("a", m[1] ? `Assumption: ${m[1].trim()}` : "Assumption: a stated input, not a sourced figure", "p2-a"); continue; }
    if ((m = p.match(/^\[constant:\s*([^\]]+)\]$/))) { sup("c", `Constant: ${m[1].trim()} (a fixed model input, not a sourced figure)`); continue; }
    if ((m = p.match(/^\[derived:\s*([^\]]+)\]$/))) {
      for (const x of m[1].split(",").map((s) => s.trim())) {
        if (/^\d+$/.test(x)) cite(Number(x));
        else { assumed = true; sup("a", "Assumption: a stated input, not a sourced figure", "p2-a"); }
      }
      continue;
    }
    lastWasSup = false;
    const withheldParts = p.split("\u0000");
    withheldParts.forEach((w, i) => {
      if (i > 0) frag.append(h("span", { class: "p2-withheld", title: "Figure withheld: the numeric gate never checked it", text: "figure withheld" }));
      if (!w) return;
      if (w.startsWith("**") && w.endsWith("**") && w.length > 4) frag.append(h("strong", { text: w.slice(2, -2) }));
      else if (w.startsWith("`") && w.endsWith("`") && w.length > 2) frag.append(h("code", { text: w.slice(1, -1) }));
      else if (w.length > 2 && w.startsWith("*") && w.endsWith("*")) frag.append(h("em", { text: w.slice(1, -1) }));
      else frag.append(document.createTextNode(w));
    });
    // A trailing space after a marker keeps the next marker from joining the run.
    if (/\S/.test(p)) lastWasSup = false;
  }
  return { frag, used, assumed };
}

/** The "Sources (n)" note under a paragraph: numbered links, plus the assumptions the record states. */
function sourceNotes(used: Ev[], notes: Notes, rec: Rec | null | undefined, assumed: boolean): HTMLElement | null {
  const asm = rec?.assumptions && typeof rec.assumptions === "object" ? Object.values(rec.assumptions as Rec).filter((a) => a && typeof a === "object") as Rec[] : [];
  if (!used.length && !(assumed && asm.length)) return null;
  const d = h("details", { class: "cite-notes" }, h("summary", { text: used.length ? `Sources (${used.length})` : "Assumptions" }));
  for (const e of used) {
    const href = citeHref(e);
    const label = citeLabel(e);
    d.append(h("span", { class: "cite-note" }, h("span", { class: "cite-note-n", text: String(notes.number(e)) }),
      href ? h("a", { href, target: "_blank", rel: "noopener noreferrer", text: label }) : h("span", { text: label })));
  }
  if (assumed && asm.length) {
    d.append(h("span", { class: "cite-note" }, h("span", { class: "cite-note-n", text: "a" }),
      h("span", { text: `Assumptions: ${asm.map((a) => [str(a.value), scrub(a.label)].filter(Boolean).join(", ")).join("; ")}` })));
  }
  return d;
}

const failed = (c: Rec | null | undefined) => c?.status === "failed" || c?.status === "unchecked";
const blockText = (b: Rec | null | undefined) => (b ? str(b.text_marked) ?? str(b.text) ?? "" : "");
/** A field of a record as its own block, inheriting the record's cites, marker map and assumptions. */
function field(rec: Rec | null | undefined, key: string): Rec | null {
  if (!rec) return null;
  const text = str(rec[key]);
  const marked = str(`${key}_marked` in rec ? rec[`${key}_marked`] : null);
  if (text == null && marked == null) return null;
  return { text, text_marked: marked, marker_map: rec.marker_map ?? null, cites: rec.cites, assumptions: rec.assumptions };
}

/** One cited block into a container: paragraphs with footnote numbers, then its Sources note. */
function block(b: Rec | null | undefined, notes: Notes, opts: { tag?: string; cls?: string; lead?: string; empty?: string } = {}): HTMLElement {
  const tag = opts.tag ?? "p";
  const cls = opts.cls ?? "p2-p";
  if (!b) return h(tag, { class: `${cls} p2-muted` }, opts.lead ? h("strong", { text: opts.lead }) : null, opts.empty ?? "Not exported");
  if (failed(b.numeric_check)) return h(tag, { class: `${cls} p2-muted` }, opts.lead ? h("strong", { text: opts.lead }) : null, "Withheld: this block did not pass the numeric gate");
  const paras = scrub(blockText(b)).split(/\n+/).map((x) => x.trim()).filter(Boolean);
  // No doubled lead when the data already opens with it ("Net: ...").
  if (opts.lead && paras[0] && paras[0].toLowerCase().startsWith(opts.lead.trim().toLowerCase())) opts = { ...opts, lead: undefined };
  const resolve = notes.resolver(b);
  const wrap = h("div", { class: "p2-block" });
  const used: Ev[] = [];
  let assumed = false;
  if (!paras.length) wrap.append(h(tag, { class: `${cls} p2-muted` }, opts.lead ? h("strong", { text: opts.lead }) : null, opts.empty ?? "Not exported"));
  paras.forEach((t, i) => {
    const r = renderMarked(t, resolve, notes);
    for (const e of r.used) if (!used.includes(e)) used.push(e);
    assumed = assumed || r.assumed;
    const p = h(tag, { class: cls, style: i ? "margin-top:8px" : undefined });
    if (i === 0 && opts.lead) p.append(h("strong", { text: opts.lead }));
    p.append(r.frag);
    wrap.append(p);
  });
  const n = sourceNotes(used, notes, b, assumed);
  if (n) wrap.append(n);
  return wrap;
}

/* ---------- sections ---------- */
function section(label: string, title: string, sub?: string): { sec: HTMLElement; body: HTMLElement } {
  const head = h("div", { class: "nd-sec-head" }, h("h3", { class: "nd-h3", text: title }), sub ? h("span", { class: "p2-muted", style: "font-size:13px", text: sub }) : null);
  const sec = h("section", { "aria-label": label, class: "nd-sec" }, head);
  return { sec, body: sec };
}
function facts(rows: Array<[string, Node | string | null]>): HTMLElement {
  const dl = h("dl", { class: "nd-facts" });
  for (const [k, v] of rows) if (v != null) dl.append(h("div", null, h("dt", { text: k }), h("dd", null, v)));
  return dl;
}
function verdictPill(v: string): HTMLElement | null {
  const s = v.toLowerCase();
  return s ? h("span", { class: `p2-verdict is-${s}`, text: s }) : null;
}
function numericPill(c: Rec | null | undefined): HTMLElement {
  const n0 = (x: unknown) => num(x) ?? 0;
  if (c?.status === "passed") {
    const t = `${n0(c.verified)} verified · ${n0(c.derived)} derived · ${n0(c.assumed)} assumed`;
    return h("span", { class: "p2-pill is-good", tabindex: "0", title: `Numbers page-checked: ${t}${c.total != null ? ` (${n0(c.checked)} of ${n0(c.total)} checked)` : ""}.`, text: `numbers page-checked · ${t}` });
  }
  if (c?.status === "failed") {
    const u = arr<Rec>(c.unsupported);
    const k = u.length || Math.max(0, n0(c.total) - n0(c.checked));
    return h("span", { class: "p2-pill is-bad", tabindex: "0", title: `Numbers not found on the cited page: ${u.map((x) => String(x.value ?? "?")).join("; ") || "list not exported"}.`, text: `${k} number${k === 1 ? "" : "s"} unsupported` });
  }
  if (c?.status === "no_numbers") return h("span", { class: "p2-pill is-muted", text: "no numbers to check" });
  return h("span", { class: "p2-pill is-muted", text: "numbers not yet page-checked" });
}

function roundLine(n: number, r: unknown): HTMLElement | null {
  if (r == null) return null;
  const y = (typeof r === "object" ? r : {}) as Rec;
  const body = typeof r === "string" ? r : str(y.argument) ?? str(y.text) ?? str(y.reason) ?? str(y.summary) ?? "";
  const tag = typeof r === "object" ? [y.refuted === true ? "refuted" : y.refuted === false ? "not refuted" : "", str(y.severity) ?? ""].filter(Boolean).join(", ") : "";
  const fix = str(y.correction);
  if (!body && !tag && !fix) return null;
  const p = h("p", { style: "margin:0" }, h("span", { class: "p2-rtag", text: `R${n}${tag ? ` · ${tag}` : ""}` }), plainWithheld(scrub(body)));
  if (fix) p.append(h("span", { class: "p2-muted", style: "display:block" }, h("strong", { text: "Correction: " }), plainWithheld(scrub(fix))));
  return p;
}
function plainWithheld(t: string): DocumentFragment {
  const f = document.createDocumentFragment();
  t.split(WITHHELD).forEach((s, i) => {
    if (i > 0) f.append(h("span", { class: "p2-withheld", title: "Figure withheld: the numeric gate never checked it", text: "figure withheld" }));
    if (s) f.append(document.createTextNode(s));
  });
  return f;
}

function traceSection(trace: Rec | null, co: Rec): HTMLElement | null {
  if (!trace) return null;
  const steps = arr<Rec>(trace.steps).filter((s) => s && Number(s.step) > 0);
  const sm = (co.skeptic_summary ?? trace.summary ?? {}) as Rec;
  const strip = [["candidates", num(co.candidates_considered) ?? num(trace.summary?.candidates) ?? steps.length], ["survived", num(sm.survived)], ["narrowed", num(sm.narrowed)], ["killed", num(sm.killed)]]
    .filter(([, v]) => v != null).map(([k, v]) => `${v} ${k}`).join(" · ");
  const lenses = arr<string>(trace.lenses).filter((x) => typeof x === "string").map(scrub);
  const det = h("details", { class: "nd-more", "aria-label": "How it decided" }, h("summary", { text: `How it decided${strip ? ` · ${strip}` : ""}${lenses.length ? ` · skeptics: ${lenses.join(" and ")}` : ""}` }));
  const ol = h("ol", { class: "nd-list", style: "margin-top:8px" });
  steps.forEach((s, i) => {
    const v = String(s.verdict ?? "").toLowerCase();
    const meta = h("div", { class: "nd-meta" }, h("span", { text: str(s.candidate_id) ?? `step ${s.step}` }), moveType(s.type) ? h("span", { text: moveType(s.type) }) : null, verdictPill(v));
    const body = h("div", { class: "nd-body" }, meta);
    if (str(s.move)) body.append(h("p", { class: "nd-finding" }, plainWithheld(scrub(s.move))));
    if (str(s.reason)) body.append(h("p", { class: "p2-p p2-muted", style: "font-size:13px" }, h("strong", { text: "Verdict: " }), plainWithheld(scrub(s.reason))));
    const rounds = h("div", { class: "p2-rounds" });
    for (const [lens, key] of [["CFO/math skeptic", "skeptic_cfo"], ["Decider/compliance skeptic", "skeptic_decider"]] as const) {
      const o = (s[key] && typeof s[key] === "object" ? s[key] : null) as Rec | null;
      if (!o || (o.round1 == null && o.round2 == null)) continue;
      rounds.append(h("div", { class: "p2-lens", text: lens }));
      const r1 = roundLine(1, o.round1); if (r1) rounds.append(r1);
      const r2 = roundLine(2, o.round2); if (r2) rounds.append(r2);
    }
    if (rounds.childElementCount) body.append(h("details", { class: "nd-more" }, h("summary", { text: "Skeptic rounds" }), rounds));
    ol.append(h("li", { class: "nd-item" }, h("div", { class: "nd-num", "aria-hidden": "true", text: String(i + 1) }), body));
  });
  det.append(steps.length ? ol : h("p", { class: "p2-p p2-muted", text: "No candidate steps exported." }));
  return det;
}

/* ---------- the answer ---------- */
interface Ctx { ready: string[]; picked: string[]; nameOf: (t: string) => string; open: (t: string) => void; part1: (t: string, n?: number) => void }

function renderAnswer(co: Rec, trace: Rec | null, t: string, ctx: Ctx): { root: HTMLElement; notes: Notes } {
  const notes = new Notes(citeIndex(co));
  const name = scrub(co.company) || ctx.nameOf(t);
  const root = h("div", { class: "min-w-0 space-y-5 text-[15px] leading-relaxed p2-answer" });

  root.append(h("header", null, h("div", { class: "p2-eyebrow", text: "The CEO Move" }), h("h2", { class: "p2-h2" }, `${name} `, h("span", { class: "font-mono", text: t }))));

  // 1. The move, in the lead position Parker gives the Sharpest Needle.
  const move = (co.move ?? null) as Rec | null;
  const budget = (move?.budget ?? null) as Rec | null;
  const lead = h("section", { "aria-label": "The move", class: "nd-lead" },
    h("div", { class: "nd-eyebrow" }, "The move", moveType(move?.type) ? h("span", { class: "nd-eyebrow-sub", text: moveType(move?.type) }) : null),
    block(move, notes, { cls: "nd-lead-text", empty: "The move has not been exported" }));
  if (budget) {
    const ok = budget.numeric_check?.status === "passed";
    const line = ok ? [num(budget.amount_usd) != null ? `$${(budget.amount_usd as number).toLocaleString("en-US")}` : "", budget.people != null && budget.people !== "" && Number(budget.people) !== 0 ? `${budget.people} people` : "", scrub(budget.period)].filter(Boolean).join(" · ") : "";
    const why = h("div", { class: "nd-lead-why" }, block(budget, notes, { lead: "Budget: ", empty: "not exported" }));
    if (line) why.append(h("p", { class: "font-mono", style: "font-size:12.5px", text: line }));
    lead.append(why);
  }
  root.append(lead);

  // 2. The case for it.
  const cf = (co.case_for ?? null) as Rec | null;
  const drivers = arr<Rec>(co.drivers);
  const s2 = section("The case for it", "The case for it");
  if (drivers.length) {
    const ul = h("div", { style: "display:grid;gap:8px" }, h("div", { class: "nd-meta" }, h("span", { text: "Driven by these Part 1 findings" })));
    for (const d of drivers) {
      const n = num(Number(d.finding_n));
      const row = h("div", { style: "display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline" },
        h("button", { type: "button", class: "p2-link", text: `Finding ${n ?? "?"}`, title: "Open this finding in the Part 1 answer above", onclick: () => ctx.part1(t, n ?? undefined) }));
      const why = field(d, "why");
      if (why) row.append(h("div", { style: "flex:1 1 20ch;min-width:0" }, block(why, notes, { cls: "p2-p", empty: "" })));
      ul.append(row);
    }
    s2.body.append(ul);
  }
  s2.body.append(facts([["What it costs", block(cf?.cost, notes)], ["What it should return", block(cf?.return, notes)]]));
  const steps = arr<Rec>(cf?.math_steps);
  if (steps.length) {
    const ol = h("ol", { class: "p2-steps" });
    steps.forEach((s) => ol.append(h("li", null, block(s, notes, { cls: "p2-p" }))));
    s2.body.append(h("details", { class: "nd-more", open: true }, h("summary", { text: "The math, step by step" }), ol));
  }
  if (cf?.net) s2.body.append(block(cf.net, notes, { lead: "Net: " }));
  if (!cf) s2.body.append(h("p", { class: "p2-p p2-muted", text: "The case (cost, return, math) has not been exported." }));
  root.append(s2.sec);

  // 3. Alternatives rejected.
  const rejected = arr<Rec>(co.rejected);
  const s3 = section("Alternatives rejected", "Alternatives rejected", "the two strongest options considered");
  const ol3 = h("ol", { class: "nd-list" });
  rejected.forEach((r, i) => {
    const meta = h("div", { class: "nd-meta" }, h("span", { text: `Option ${i + 1}` }), moveType(r.type) ? h("span", { text: moveType(r.type) }) : null, str(r.skeptic_lens) ? h("span", { class: "nd-tag", text: `Pressed by the ${scrub(r.skeptic_lens)} skeptic` }) : null);
    const body = h("div", { class: "nd-body" }, meta);
    if (str(r.move)) body.append(h("p", { class: "nd-finding", text: scrub(r.move) }));
    body.append(block(r.why_passed, notes, { lead: "Why we passed: ", empty: "reason not exported" }));
    ol3.append(h("li", { class: "nd-item" }, h("div", { class: "nd-num", "aria-hidden": "true", text: String(i + 1) }), body));
  });
  s3.body.append(rejected.length ? ol3 : h("p", { class: "p2-p p2-muted", text: "No rejected alternatives exported." }));
  if (rejected.length !== 2) s3.body.append(h("p", { class: "p2-p p2-muted", style: "font-size:12px", text: `The case asks for two rejected options; ${rejected.length} exported.` }));
  root.append(s3.sec);

  // 4. Kill signals.
  const kills = arr<Rec>(co.kill_signals);
  const s4 = section("What would prove it wrong", "What would prove it wrong", "early signals, months 6 to 12");
  const ol4 = h("ol", { class: "nd-list" });
  kills.forEach((k, i) => {
    const bad = failed(k.numeric_check);
    const body = h("div", { class: "nd-body" }, h("div", { class: "nd-meta" }, h("span", { text: scrub(k.month_window) || "months 6 to 12" })));
    if (bad) body.append(h("p", { class: "nd-finding p2-muted", text: "Withheld: this signal did not pass the numeric gate" }));
    else {
      body.append(h("p", { class: "nd-finding", text: scrub(k.signal) || "Signal not exported" }));
      body.append(facts([["Threshold", block(field(k, "threshold"), notes, { empty: "not exported" })], ["Reading", block(k, notes, { empty: "" })]]));
    }
    ol4.append(h("li", { class: "nd-item" }, h("div", { class: "nd-num", "aria-hidden": "true", text: String(i + 1) }), body));
  });
  s4.body.append(kills.length ? ol4 : h("p", { class: "p2-p p2-muted", text: "No kill signals exported." }));
  root.append(s4.sec);

  // 5. Why it will work, and what the evidence cannot tell us.
  const ev = (co.evidence ?? null) as Rec | null;
  const s5 = section("Why it will work", "Why it will work", str(ev?.decider) ? `the people who decide: ${scrub(ev?.decider)}` : undefined);
  s5.body.append(block(ev?.lands_because, notes, { empty: "Evidence not exported" }));
  const dl5 = h("dl", { class: "nd-verdict" },
    h("div", null, h("dt", { text: "What it can tell us" }), h("dd", null, block(ev?.can_tell, notes))),
    h("div", null, h("dt", { text: "What it cannot tell us" }), h("dd", null, block(ev?.cannot_tell, notes))));
  s5.body.append(dl5);
  const unresolved = arr<Rec>(co.unresolved);
  if (unresolved.length) {
    const d = h("details", { class: "nd-more" }, h("summary", { text: "Where the two skeptics still disagree" }));
    for (const u of unresolved) {
      const box = h("div", { style: "display:grid;gap:4px;margin-top:8px;font-size:13.5px;line-height:1.55" });
      if (str(u.topic)) box.append(h("div", { style: "font-weight:600", text: scrub(u.topic) }));
      if (str(u.cfo_position)) box.append(h("div", null, h("span", { class: "p2-muted", text: "CFO lens: " }), scrub(u.cfo_position)));
      if (str(u.decider_position)) box.append(h("div", null, h("span", { class: "p2-muted", text: "Decider lens: " }), scrub(u.decider_position)));
      if (str(u.record_note)) box.append(h("div", { class: "p2-muted" }, h("span", { text: "On the record: " }), scrub(u.record_note)));
      d.append(box);
    }
    s5.body.append(d);
  }
  root.append(s5.sec);

  // 6. Anything a doctor or patient would see.
  const promo = (co.promo ?? null) as Rec | null;
  const rc = (promo?.rules_check ?? {}) as Rec;
  const hasMaterial = promo?.has_material === true;
  const s6 = section("Anything a doctor or patient would see", "Anything a doctor or patient would see");
  if (hasMaterial) {
    s6.body.append(h("div", { role: "note", class: "p2-banner", text: BANNER }));
    if (rc.risks_prominent !== true || rc.labelled !== true) {
      s6.body.append(h("p", { class: "p2-p p2-muted", text: `Concept withheld: the compliance check did not confirm ${rc.risks_prominent !== true ? "that risks are shown as prominently as benefits" : "the student-concept label"}.` }));
    } else {
      const pieces = arr<Rec>(promo?.pieces);
      if (!pieces.length) s6.body.append(h("p", { class: "p2-p p2-muted", text: "No piece exported." }));
      for (const p of pieces) {
        const art = h("article", { class: "p2-piece" });
        if (str(p.title)) art.append(h("h4", { text: scrub(p.title) }));
        const body = field(p, "body");
        if (body) body.numeric_check = p.numeric_check;
        art.append(block(body, notes, { empty: "body not exported" }));
        if (!blockText(body).includes(BANNER)) art.append(h("div", { class: "p2-tag", text: BANNER }));
        s6.body.append(art);
      }
    }
    const rules: Array<[string, string]> = [["approved_uses_only", "claims only for approved uses"], ["risks_prominent", "risks as prominent as benefits"], ["h2h_only", "comparisons only with head-to-head evidence"], ["no_testimonials", "no invented testimonials or likenesses"], ["labelled", "labelled as a student concept"], ["claims_map_present", "claims map present"]];
    const ul = h("ul", { class: "p2-rules", "aria-label": "Promotion rules check" });
    for (const [k, label] of rules) { const ok = rc[k] === true; ul.append(h("li", { class: ok ? "is-ok" : "is-no", text: `${ok ? "✓" : "✗"} ${label}${rc[k] == null ? " (not checked)" : ""}` })); }
    s6.body.append(ul);
  } else s6.body.append(h("p", { class: "p2-p p2-muted", text: "This move includes no campaign, messaging or other material a doctor or patient would see." }));
  root.append(s6.sec);

  // 7. Claims map.
  const claims = arr<Rec>(promo?.claims_map);
  const s7 = section("Claims map", "Claims map");
  if (claims.length) {
    const tb = h("tbody");
    for (const r of claims) {
      const e = (arr<Ev>(r.cites)[0] ?? (r.cite && typeof r.cite === "object" ? r.cite : null)) as Ev | null;
      const ev2 = e ? (e.cite_id && notes.ix.get(e.cite_id)) || e : null;
      const href = ev2 ? citeHref(ev2) : null;
      const src = ev2 ? (href ? h("a", { class: "nd-src", href, target: "_blank", rel: "noopener noreferrer", text: citeLabel(ev2) }) : h("span", { text: citeLabel(ev2) })) : h("span", { class: "p2-muted", text: "none" });
      tb.append(h("tr", null, h("td", { text: scrub(r.claim) || "not exported" }), h("td", { text: scrub(r.support_section) || "not exported" }), h("td", null, src)));
    }
    const table = h("table", { class: "p2-table" }, h("colgroup", null, h("col", { style: "width:44%" }), h("col", { style: "width:30%" }), h("col", { style: "width:26%" })),
      h("thead", null, h("tr", null, h("th", { text: "Claim" }), h("th", { text: "Label section or study" }), h("th", { text: "Source" }))), tb);
    s7.body.append(h("div", { class: "p2-scroll" }, table));
  } else s7.body.append(h("p", { class: "p2-p p2-muted", text: hasMaterial ? "No claims map exported." : "No doctor- or patient-facing material, so no claims map." }));
  root.append(s7.sec);

  // 8. Numbers.
  const s8 = section("Numbers", "Numbers");
  const row = h("div", { class: "p2-numbers" }, numericPill(co.numeric_summary));
  const fw = num(co.figures_withheld);
  if (fw && fw > 0) row.append(h("span", { text: `${fw} figure${fw === 1 ? "" : "s"} withheld because the gate never checked ${fw === 1 ? "it" : "them"}.` }));
  if (str(co.numeric_summary?.note)) row.append(h("span", { text: scrub(co.numeric_summary.note) }));
  s8.body.append(row);
  root.append(s8.sec);

  const tr = traceSection(trace, co);
  if (tr) root.append(tr);

  // Ask next: the other picks' moves, and the way back to the Part 1 findings.
  const next = h("div", { class: "no-print flex flex-wrap gap-2", "aria-label": "Ask next" });
  for (const o of ctx.ready) if (o !== t) next.append(h("button", { type: "button", class: CHIP_CLS, text: `The CEO Move for ${ctx.nameOf(o)} (${o})`, onclick: () => ctx.open(o) }));
  next.append(h("button", { type: "button", class: CHIP_CLS, text: `Part 1 findings for ${name}`, onclick: () => ctx.part1(t) }));
  root.append(next);
  return { root, notes };
}

/* ---------- the thinking state, built from the trace ---------- */
function thinkingSteps(co: Rec, trace: Rec | null, name: string): Array<[string, string]> {
  const steps: Array<[string, string]> = [];
  const cands = arr<Rec>(trace?.steps).filter((s) => s && Number(s.step) > 0);
  const n = num(co.candidates_considered) ?? cands.length;
  steps.push(["strategist.propose", `Proposing ${n || "the"} candidate moves for ${name} from the Part 1 findings, each with a budget or a commitment of people.`]);
  for (const s of cands) {
    const v = String(s.verdict ?? "").toLowerCase();
    const mv = scrub(s.move).replace(WITHHELD, "").replace(/\s+/g, " ").trim();
    steps.push([`skeptics ${str(s.candidate_id) ?? `step ${s.step}`}`, `${mv.length > 140 ? `${mv.slice(0, 137).trimEnd()}…` : mv}${v ? ` Verdict: ${v}.` : ""}`]);
  }
  const ns = co.numeric_summary as Rec | undefined;
  if (ns?.status) steps.push(["gate.numeric", ns.status === "passed" ? `Checking every figure in the answer against its cited page: ${num(ns.checked) ?? 0} of ${num(ns.total) ?? 0} checked.` : `Numeric gate: ${String(ns.status)}.`]);
  steps.push(["decide.write", "Writing the move, the case, the two rejected options, the kill signals and the claims map, each with its sources."]);
  return steps;
}

/* ---------- chat integration ---------- */
const state = { index: null as Rec | null, ready: [] as string[], picked: [] as string[], turns: new Map<string, HTMLElement>(), names: new Map<string, string>(), list: null as HTMLElement | null, running: new Set<string>() };

const parkerList = () => document.querySelector<HTMLElement>("main#main > ol:not(.p2-turns)");
function ownList(): HTMLElement | null {
  const his = parkerList();
  if (!his) return null;
  if (!state.list) state.list = h("ol", { class: "space-y-8 pt-4 p2-turns", "aria-label": "The CEO Move" });
  if (!state.list.isConnected) his.insertAdjacentElement("afterend", state.list);
  return state.list;
}
function nameOf(t: string): string { return state.names.get(t) ?? t; }
/** The ticker a Part 1 turn is showing, from its heading, and its company name. */
function turnTicker(li: Element): { t: string; name: string } | null {
  const h2 = li.querySelector("h2");
  const sp = h2?.querySelector("span.font-mono");
  const t = sp?.textContent?.trim();
  if (!h2 || !t) return null;
  const name = (h2.textContent ?? "").replace(t, "").trim();
  if (name) state.names.set(t, name);
  return { t, name };
}
function goPart1(t: string, n?: number) {
  const li = Array.from(document.querySelectorAll<HTMLElement>("main#main > ol:not(.p2-turns) > li[data-turn]")).find((x) => x.querySelector("h2 span.font-mono"));
  if (!li) return;
  const cur = turnTicker(li);
  if (cur && cur.t !== t) {
    const tab = Array.from(li.querySelectorAll<HTMLButtonElement>('[role="tablist"] button[role="tab"]')).find((b) => b.querySelector("span")?.textContent?.trim() === t || b.textContent?.trim().endsWith(t));
    tab?.click();
  }
  window.setTimeout(() => {
    const target = (n != null && li.querySelector(`#p1-finding-${n}`)) || li.querySelector("h2") || li;
    target.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "start" });
  }, cur && cur.t !== t ? 250 : 0);
}

async function openPart2(t: string) {
  const list = ownList();
  if (!list) return;
  const had = state.turns.get(t);
  if (had && had.isConnected) { had.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "start" }); return; }
  if (had) { list.append(had); had.scrollIntoView({ block: "start" }); return; }
  if (state.running.has(t)) return;
  state.running.add(t);
  const n = state.turns.size + 1;
  const li = h("li", { "data-turn": `p2-${n}`, "data-p2-turn": t, class: "space-y-4 p2-turn" },
    h("div", { class: "no-print flex justify-end" }, h("div", { class: "max-w-[85%] rounded-2xl rounded-br-sm bg-purple dark:bg-purple-deep px-4 py-2.5 text-[15px] text-white", text: `For ${nameOf(t)} (${t}), ${PROMPT}` })));
  const col = h("div", { class: "space-y-4" });
  li.append(col);
  state.turns.set(t, li);
  list.append(li);
  li.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "start" });

  const t0 = performance.now();
  const live = h("div", { class: "th-live", role: "status", "aria-live": "polite" });
  const head = h("div", { class: "th-head" }, h("span", { class: "th-spark", "aria-hidden": "true" }), h("span", { class: "th-label", text: "Thinking" }), h("span", { class: "th-time", text: "0s" }));
  const ol = h("ol", { class: "th-steps" });
  live.append(head, ol);
  col.append(live);
  const tick = window.setInterval(() => { head.lastElementChild!.textContent = `${Math.max(1, Math.round((performance.now() - t0) / 1000))}s`; }, 500);

  // The other picks load alongside so the follow-up chips can carry company names.
  const [{ co, trace }] = await Promise.all([loadCompany(t), ...state.ready.filter((o) => o !== t).map((o) => loadCompany(o).then((r) => { if (r.co && scrub(r.co.company)) state.names.set(o, scrub(r.co.company)); }))]);
  if (!co) {
    window.clearInterval(tick);
    live.replaceWith(h("p", { role: "alert", class: "p2-p", style: "color:rgb(var(--bad))", text: `Could not load data/part2/${t}.json.` }));
    state.running.delete(t);
    return;
  }
  const name = scrub(co.company) || nameOf(t);
  state.names.set(t, name);
  const steps = thinkingSteps(co, trace, name);
  const instant = reduceMotion();
  for (let i = 0; i < steps.length; i++) {
    ol.querySelector("li.is-now")?.classList.replace("is-now", "is-done");
    ol.append(h("li", { class: "is-now" }, h("span", { class: "th-tag", text: steps[i][0] }), h("span", { class: "th-txt", text: steps[i][1] })));
    if (!instant) await sleep(i === 0 ? 650 : 420);
  }
  ol.querySelector("li.is-now")?.classList.replace("is-now", "is-done");
  window.clearInterval(tick);
  const secs = Math.max(1, Math.round((performance.now() - t0) / 1000));
  const done = h("details", { class: "th-done" }, h("summary", { text: `Thought for ${secs}s` }), ol);
  live.replaceWith(done);

  const { root, notes } = renderAnswer(co, trace, t, { ready: state.ready, picked: state.picked, nameOf, open: openPart2, part1: goPart1 });
  root.dataset.p2Unresolved = String(notes.unresolved);
  root.dataset.p2Sups = String(notes.sups);
  col.append(root);
  state.running.delete(t);
}

/** Add or refresh the Part 2 chip on every finished Part 1 answer. */
function placeChips() {
  if (!state.ready.length) return;
  for (const li of document.querySelectorAll<HTMLElement>("main#main > ol:not(.p2-turns) > li[data-turn]")) {
    const next = li.querySelector<HTMLElement>('div[aria-label="Ask next"]');
    if (!next || li.querySelector(".th-live")) continue;
    const cur = turnTicker(li);
    if (!cur) continue;
    let chip = next.querySelector<HTMLButtonElement>("button[data-p2-chip]");
    if (!state.ready.includes(cur.t)) { chip?.remove(); continue; }
    if (!chip) {
      chip = h("button", { type: "button", class: CHIP_CLS, "data-p2-chip": "" }) as HTMLButtonElement;
      chip.addEventListener("click", () => { const t = chip!.dataset.p2Chip; if (t) void openPart2(t); });
      next.prepend(chip);
    }
    if (chip.dataset.p2Chip !== cur.t) {
      chip.dataset.p2Chip = cur.t;
      chip.replaceChildren(h("span", { class: "font-semibold", text: "The CEO Move" }), ` for ${cur.name || nameOf(cur.t)} (${cur.t})`);
      chip.title = PROMPT.charAt(0).toUpperCase() + PROMPT.slice(1);
    }
  }
  // Keep our turns on the page when his list is re-rendered (for example after a visit to the findings tab).
  if (state.turns.size && parkerList() && !(state.list?.isConnected)) {
    const list = ownList();
    if (list) for (const li of state.turns.values()) if (!li.isConnected) list.append(li);
  }
}

/** His chat box is a one-row textarea; when his bundle pre-fills the Part 2 prompt (or anyone types a long
 *  question) it must grow to fit, up to his max height, instead of clipping the second line. */
function fitChatInput() {
  let last: string | null = null;
  const fit = () => {
    const ta = document.getElementById("chat-input") as HTMLTextAreaElement | null;
    if (!ta) { last = null; return; }
    if (ta.value === last && ta.style.height) return;
    last = ta.value;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
    ta.style.overflowY = ta.scrollHeight > 160 ? "auto" : "hidden";
  };
  document.addEventListener("input", (e) => { if ((e.target as HTMLElement | null)?.id === "chat-input") fit(); });
  window.addEventListener("resize", () => { last = null; fit(); });
  window.setInterval(fit, 200);
  fit();
}

async function main() {
  if (document.getElementById("p2-style")) return;
  fitChatInput();
  document.head.append(h("style", { id: "p2-style", text: STYLE }));
  const index = await getJson("index.json");
  if (!index) return; // No Part 2 export on this page: no chip at all.
  const picked = arr<string>(index.picked).filter((x) => typeof x === "string");
  const avail = Array.isArray(index.available) ? arr<string>(index.available) : picked;
  const missing = new Set(arr<Rec>(index.missing).map((m) => m?.ticker));
  state.index = index;
  state.picked = picked;
  state.ready = picked.filter((t) => avail.includes(t) && !missing.has(t));
  if (!state.ready.length) return;
  let queued = false;
  const schedule = () => { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; placeChips(); }); };
  new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true, characterData: true });
  window.addEventListener("hashchange", schedule);
  schedule();
  (window as unknown as Rec).__needlePart2 = { state, open: openPart2 };
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => void main());
else void main();
