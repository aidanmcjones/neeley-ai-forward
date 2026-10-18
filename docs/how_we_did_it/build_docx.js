// Builds "How we did it" as a .docx in the quiet, declarative house style of an Anthropic announcement.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, ImageRun, LevelFormat, Footer, PageNumber, TabStopType,
  VerticalAlign,
} = require("docx");

const DIR = __dirname;
const OUT = path.join(DIR, "NEEDLE_How_We_Did_It.docx");

// Palette (warm, understated)
const INK = "141413";
const MUTED = "5E5D59";
const CLAY = "D97757";
const SAND = "F0EEE6";
const LINE = "D9D6CE";
const SLATE_SOFT = "E1ECF6";

const SERIF = "Georgia";
const SANS = "Arial";
const MONO = "Courier New";

const PAGE_W = 12240, PAGE_H = 15840, MARGIN = 1296; // US Letter, 0.9in margins
const TEXT_W = PAGE_W - 2 * MARGIN; // 9648 DXA = 6.7in

// ---------- helpers ----------
const run = (text, opts = {}) => new TextRun({ text, font: SANS, size: 21, color: INK, ...opts });
const p = (children, opts = {}) =>
  new Paragraph({ spacing: { after: 160, line: 300 }, ...opts, children: Array.isArray(children) ? children : [run(children)] });
const body = (text, opts = {}) => p([run(text)], opts);
const bodyRuns = (runs, opts = {}) => p(runs, opts);
const muted = (text, size = 18) => new TextRun({ text, font: SANS, size, color: MUTED });
const bold = (text) => run(text, { bold: true });

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 520, after: 200 },
    children: [new TextRun({ text, font: SERIF, size: 38, color: INK })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 320, after: 120 },
    keepNext: true,
    children: [new TextRun({ text, font: SERIF, size: 27, color: INK })],
  });
}
function kicker(text) {
  return new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: text.toUpperCase(), font: SANS, size: 16, color: CLAY, bold: true, characterSpacing: 40 })],
  });
}
function rule(color = LINE, after = 240, before = 120) {
  return new Paragraph({
    spacing: { before, after },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color, space: 1 } },
    children: [],
  });
}
function callout(text, attribution) {
  const children = [
    new Paragraph({
      spacing: { before: 60, after: attribution ? 60 : 120, line: 320 },
      indent: { left: 360, right: 720 },
      border: { left: { style: BorderStyle.SINGLE, size: 18, color: CLAY, space: 12 } },
      children: [new TextRun({ text, font: SERIF, size: 25, color: INK, italics: true })],
    }),
  ];
  if (attribution) {
    children.push(
      new Paragraph({
        spacing: { after: 200 },
        indent: { left: 360 },
        border: { left: { style: BorderStyle.SINGLE, size: 18, color: CLAY, space: 12 } },
        children: [muted(attribution, 17)],
      })
    );
  }
  return children;
}
function bullets(items, ref = "bullets") {
  return items.map((it) => {
    const runs = typeof it === "string" ? [run(it)] : it;
    return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 90, line: 290 }, children: runs });
  });
}
function numbered(items) {
  return items.map((it) => {
    const runs = typeof it === "string" ? [run(it)] : it;
    return new Paragraph({ numbering: { reference: "numbers", level: 0 }, spacing: { after: 90, line: 290 }, children: runs });
  });
}
function figure(file, caption, widthIn = 6.7) {
  const buf = fs.readFileSync(path.join(DIR, file));
  // read PNG dimensions
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const wpx = Math.round(widthIn * 96), hpx = Math.round((h / w) * widthIn * 96);
  return [
    new Paragraph({
      spacing: { before: 160, after: 60 },
      alignment: AlignmentType.CENTER,
      keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: hpx } })],
    }),
    new Paragraph({ spacing: { after: 240 }, alignment: AlignmentType.LEFT, children: [muted(caption, 17)] }),
  ];
}
function codeBlock(text, title) {
  const out = [];
  if (title) {
    out.push(
      new Paragraph({
        spacing: { before: 160, after: 40 },
        keepNext: true,
        children: [new TextRun({ text: title, font: SANS, size: 18, color: CLAY, bold: true })],
      })
    );
  }
  const lines = text.replace(/\t/g, "    ").split("\n");
  lines.forEach((ln, i) => {
    out.push(
      new Paragraph({
        shading: { type: ShadingType.CLEAR, fill: SAND, color: "auto" },
        spacing: { before: i === 0 ? 0 : 0, after: i === lines.length - 1 ? 200 : 0, line: 250 },
        indent: { left: 200, right: 200 },
        keepNext: i < lines.length - 1,
        keepLines: true,
        children: [new TextRun({ text: ln.length ? ln : " ", font: MONO, size: 15, color: INK })],
      })
    );
  });
  return out;
}
const cellBorders = {
  top: { style: BorderStyle.SINGLE, size: 4, color: LINE },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
};
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = TEXT_W / total;
  const cw = widths.map((w) => Math.round(w * scale));
  const mk = (text, i, isHead) =>
    new TableCell({
      width: { size: cw[i], type: WidthType.DXA },
      borders: cellBorders,
      shading: isHead ? { type: ShadingType.CLEAR, fill: SAND, color: "auto" } : undefined,
      margins: { top: 70, bottom: 70, left: 90, right: 90 },
      verticalAlign: VerticalAlign.TOP,
      children: (Array.isArray(text) ? text : [text]).map(
        (t) =>
          new Paragraph({
            spacing: { after: 0, line: 250 },
            children: [new TextRun({ text: String(t), font: SANS, size: opts.size || 17, color: INK, bold: !!isHead })],
          })
      ),
    });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => mk(h, i, true)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => mk(c, i, false)) })),
    ],
  });
}
function statStrip(stats) {
  // one row of big numbers with small labels
  const n = stats.length;
  const cw = Array(n).fill(Math.floor(TEXT_W / n));
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({
        children: stats.map(
          ([num, lab], i) =>
            new TableCell({
              width: { size: cw[i], type: WidthType.DXA },
              borders: {
                top: { style: BorderStyle.SINGLE, size: 8, color: CLAY },
                bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE },
                left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
              },
              margins: { top: 120, bottom: 120, left: 80, right: 80 },
              children: [
                new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: num, font: SERIF, size: 34, color: INK })] }),
                new Paragraph({ spacing: { after: 0, line: 230 }, children: [muted(lab, 15)] }),
              ],
            })
        ),
      }),
    ],
  });
}
const spacer = (after = 120) => new Paragraph({ spacing: { after }, children: [] });

// ---------- content ----------
const content = [];
const add = (...xs) => xs.flat().forEach((x) => content.push(x));

// Masthead
add(
  kicker("Neeley AI Forward 2026  ·  The Fine Print  ·  Advanced track"),
  new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: "How we did it", font: SERIF, size: 64, color: INK })],
  }),
  new Paragraph({
    spacing: { after: 200, line: 300 },
    children: [new TextRun({ text: "NEEDLE reads ten drugmakers' fine print, argues with itself, and shows judges the page behind every number.", font: SERIF, size: 27, color: MUTED })],
  }),
  new Paragraph({
    spacing: { after: 60 },
    children: [muted("Team NEEDLE: Aidan Jones and Parker Kingsbury  ·  TCU Neeley School of Business  ·  October 18, 2026", 18)],
  }),
  rule(CLAY, 280, 160)
);

// Lede
add(
  bodyRuns([
    run("Over thirty hours we built NEEDLE, a system that finds material, non-obvious facts in pharmaceutical filings and turns them into one defensible CEO decision. It reads ten companies blind, argues every candidate finding between two skeptics who assume it is wrong, seals its company pick with a hash before anyone can influence it, and refuses to display any number it cannot trace to a page a judge can open."),
  ]),
  body("The deliverable is a chat page with two prompts, both taken verbatim from the case. The first returns a five-finding table, a Sharpest Needle and a product fine-print comparison for Amgen, Merck or Pfizer. The second returns one strategic move for the next 24 months with a budget, the math, two rejected alternatives and the signals that would prove it wrong. Every figure on the page carries a footnote that opens the source document at the cited page."),
  body("This report covers the tools we used and what each was for, how documents reached the AI and how the work was split between people and tools, the prompts that mattered most, the cases where the AI was confidently wrong, and what we would do differently. We logged 542 of those wrong cases. The ones that taught us the most were caught by a person reading a page, not by code.")
);

add(
  spacer(60),
  statStrip([
    ["78,392", "pages in the citation index, from 7,003 documents and 117,904 fact rows"],
    ["95", "candidate findings from ten blind readers; 70 killed, 25 narrowed, 0 survived as first stated"],
    ["503", "numbers and 261 citations re-verified by an independent agent; 7 defects, all scoping, all fixed"],
    ["542", "logged cases of a confidently wrong AI, each with the source, the catch and the fix"],
  ]),
  spacer(200)
);

add(figure("fig7_timeline.png", "Figure 1. The weekend, Central Time. The case was released Saturday morning; the blind Part 1 pass ran Saturday night and Part 2 after midnight.", 6.7));

// 1. What the case asked
add(
  h1("1. What the case asked, and the two traps in it"),
  body("The Fine Print asks for two things. Part 1: pick one of ten drugmakers and find at least five findings that would change an investor's view and are not obvious, each with impact math, a peer comparison and a confidence call, plus the single sharpest one and a side-by-side of one product against the rivals the case names. Part 2: take the CEO's seat and recommend one move for the next 24 months with a budget or a commitment of people, the math, the two strongest rejected alternatives, and measurable kill signals in months six to twelve."),
  body("The case also names the two ways AI fails at this. On Part 1, a model will surface things management already said plainly: the patent cliff, the press-release headline, the starter thread. On Part 2, as the case puts it, AI will argue convincingly for almost any strategy. We treated both as design constraints rather than warnings."),
  ...callout("Every number you see was computed by deterministic code from a cited page. AI writes the words, argues the case and reads the calls, and nothing it says reaches the screen until a verifier has found it on the page it cites. When the AI was wrong, and it was, that is how we caught it.", "The line we built the system around"),
  body("Three principles followed. Code fetches and verifies: every source is collected by scripts into a page-marked index, never pasted into a chat, and every quote is checked by exact match on its page. Agents reason, blind and adversarially: the readers who look for findings cannot see any prior run, and every candidate must survive two skeptics who read each other's arguments. Humans decide: a person opened the cited page behind every needle before it reached a slide, and the company pick rests on that read."),
  figure("fig1_system.png", "Figure 2. The system at a glance. Sources flow left to right; people and a watcher session sit alongside the two stages where judgment happens.")
);

// 2. Tools
add(
  h1("2. The tools and what each was for"),
  body("We used one model family for every reasoning step and ordinary engineering for everything else. No model wrote a number into the deliverable; models proposed, argued and verified, and code decided what could be shown."),
  table(
    ["Tool", "What it was for"],
    [
      ["Claude Code with Claude Opus 5.5", "Four long-running sessions (scraper, model, UI, watcher) and 59 worker agents launched by the model session. Every reader, skeptic, synthesizer, ranker, writer, strategist and verifier was an Opus agent with a written brief. Later sessions ran on Claude Fable 5.1."],
      ["Git worktrees and a PR chain", "Each session owned one branch and one open pull request; no two agents edited the same file. Chain: scaffold #1, gap-data #2, corpus #5, Parker's needle branch, data-moat #16, quant-model #21, ui #22."],
      ["Python collectors", "Fetched SEC EDGAR filings and XBRL companyfacts, DailyMed labels, Orange and Purple Book dates, CMS Part B and Part D files, NADAC, FAERS, ClinicalTrials.gov, ICER reports and GDELT news volumes into page-marked text and verified CSV tables."],
      ["The citation index (SQLite, FTS5)", "7,003 documents, 78,392 pages, 15,463 speaker turns and 117,904 fact rows. A five-call API: search_pages, search_facts, get_page, cite, verify_quote. Transcripts graded A to D for quotability; Bloomberg pages flagged as licensed."],
      ["Eight case retrieval helpers", "One per item on the case's own 'where findings hide' list: language drift, gross-to-net, working capital, segment changes, footnotes, call Q&A, label fine print, peer forces. Each returns cited rows and never ranks them."],
      ["The per-number citation gate", "Python that checks every figure in every block one at a time against the quoted span, a recomputed derivation or a printed assumption label, and withholds anything else."],
      ["Adversarial review pattern", "Two skeptic agents with different lenses, two rounds in which each reads the other, a synthesizer who never averages, then a fresh verifier. Used on the quant spec, the gate itself, the backtest, every Part 1 finding and every Part 2 move."],
      ["Bloomberg transcripts and WRDS I/B/E/S", "Official transcripts to upgrade quote grades; analyst consensus for the 'was it priced in' test. Both licensed, so used locally and cited by label only."],
      ["pytest", "259 tests across the data, citation and model code; every behavior change carried a test."],
      ["Vite and React, published as a claude.ai Artifact", "A static one-page chat with cached answers and no API key, republished on every commit so Parker and the judges always saw the committed state."],
      ["agent-chat (GitHub issues)", "A message bus so Aidan's and Parker's agents could ask each other for data without a human relaying."],
      ["Cloudflare R2", "Bulk storage for the corpus and the gzipped index, so either machine could rebuild from the same bytes."],
    ],
    [2.1, 4.6]
  )
);

// 3. Workflow
add(
  h1("3. The workflow"),
  h2("3.1 How documents got into the AI"),
  body("No document was ever pasted into a prompt. Collectors fetched each filing, transcript, label and dataset by code and wrote page-marked text, with a marker of the form [[page N | printed P]] on every page so that a file page and a printed page could both be cited. The index stores pages, speaker turns and fact rows with full-text search, and every row carries a locator of the form doc_id#p<page> that opens the source."),
  body("Two rules made the index trustworthy enough to reason over. First, verify_quote: a sentence passes only if it is an exact substring of the one page it cites after normalising quotes, dashes, whitespace and case. The retrieval helpers drop any row that fails before an agent sees it. Second, grades and flags: transcripts are graded A to D and only A and B may be quoted; Bloomberg pages are cited by label and never copied; a mislabeled transcript and a set of fool.com files that open with model-written summaries are marked superseded or unquotable."),
  figure("fig2_document.png", "Figure 3. A document's path into the index. The collectors also keep a log of their own confident mistakes, which became the largest part of our AI-was-wrong record."),
  body("The scraper session ran five waves on Saturday: the ten shortlist companies at filing depth with ten quarters of graded calls; the Part 2 backend for all ten companies and 52 drugs (epidemiology, peers, deals, pipeline, costs, prescribers); every gap a free source could still fill; the eight case helpers; and a Part 2 evidence wave of labels, head-to-head trials, payer tables, deal comps and 325 page-anchored filing numbers for the three picked companies. Explicit negatives are rows too, so 'no public source' is itself citable."),

  h2("3.2 How the work was split between people and tools"),
  body("Two people ran four long-lived Claude Code sessions, each in its own git worktree with its own branch and pull request. Parker owned the company read, the human judgment on findings, the Part 2 content and the deck. Aidan owned the API key, the repository and PR chain, the UI, the demo, this report and the submission. A fourth session, the watcher, did no building: it checked the other three against their goals, the rubric and the one deadline, and ruled on discrepancies when a refresh moved a published number."),
  figure("fig3_team.png", "Figure 4. People, sessions and branches. Sessions messaged each other directly with status, commit SHAs, data inventories and rulings."),
  body("Parker's branch also carried a nugget miner and a red-team agent that read footnotes, risk language and call Q&A for each company and scored our work against the rubric. An earlier quantitative league table that ranked companies by a scoring equation was demoted on Saturday evening to internal triage after it was led by a scorer bug (Section 5); nothing from it appears in the pitch."),
  body("Scope control mattered more than clever prompting. Every worker agent opened with the same frame: you are a worker, not an orchestrator; work only in your own worktree; own only the files named; do not spawn agents; report file paths and counts. Two agents never edited the same file all weekend."),

  h2("3.3 Part 1: Find the Story"),
  body("The Part 1 pipeline is blind, adversarial and sealed. Ten reader agents, one per company, were launched together Saturday at 10:27 pm with the case PDF, the rubric and the citation index, and a written list of files they were forbidden to open: any prior run, the league table, the nugget files, the red-team notes, every other worktree. Each walked the case's eight hiding places and wrote candidates with page-verified evidence as it found them."),
  body("Each company's candidates then went to two skeptics with different lenses, materiality and math versus obviousness, both instructed to assume every candidate is wrong until the cited page proves otherwise and to open each page themselves. In round two the same agents were resumed, read the other lens's file against the sources, and conceded, held or narrowed. A synthesizer per company ruled each candidate survived, narrowed or killed without voting or averaging. A single ranker picked three companies on the case's test, wrote selection.md, appended its sha256, and only then was allowed to read the league table and the red team to write a separate appendix."),
  figure("fig4_part1.png", "Figure 5. Part 1 in two phases. Phase A ran in 45 minutes of wall clock; Phase B wrote the deliverables through the gate and an independent verifier."),
  body("The skeptics killed about 80 percent of what the readers found, nearly always for the same reason: management already said it. The honest result of the trace is '0 survived as first stated, 25 narrowed', and the chat shows that. The sealed pick was Amgen, Merck and Pfizer. The blind result agreed with Parker's red-team read on Merck and Pfizer and with the retired league table on Amgen; Johnson & Johnson, which the league had favoured, dropped out."),
  body("Phase B then wrote each company's deliverable from the sealed rulings: five findings (killed-as-obvious rows used to fill the table are tagged on the record), the Sharpest Needle by one plain rule, the biggest impact that analysts asked about least, and the five-row product comparison with a financial tie, a growth limiter and an evidence-graded priced-in call. Every cell ran through the gate. A fresh verifier agent then re-opened all 261 citations and re-checked all 503 numbers with the instruction to assume each was wrong; it found seven defects, all of them attribution or scope rather than arithmetic, and all were fixed and re-gated."),
  table(
    ["Company", "Sharpest Needle", "Product fine print", "Priced in?"],
    [
      ["Amgen", "A $2.4B TAVNEOS intangible carried at about 5.2 times FY2025 sales against a drug the FDA has formally proposed to withdraw; not raised on any call.", "Repatha vs Praluent, Leqvio and Lipfendra", "Not priced in"],
      ["Merck", "IRS notices seeking about $1.3B of extra transition tax plus $260M of penalties, outside the non-GAAP EPS line the Street models and absent from every call and release.", "Keytruda and Keytruda Qlex vs Opdivo, Imfinzi and Tecentriq", "Not priced in"],
      ["Pfizer", "U.S. Vyndaqel revenue flat while the U.S. ATTR-CM class grew 47 percent in H1 2026; credited as a quantification, since rivals and management have described the share loss.", "Vyndaqel family vs Attruby and Amvuttra", "Priced in"],
    ],
    [1.0, 3.3, 1.6, 0.9]
  ),
  spacer(160),

  h2("3.4 Part 2: Make the Call"),
  body("Part 2 ran only for the three sealed companies and reused the structure. A strategist agent per company, with fresh context and the same forbidden list, proposed at least four costed moves of at least two types from the sealed Part 1 findings, and recorded every data gap as a request rather than a guess. Two skeptics, a CFO-and-math lens and a Decider-and-compliance lens, defaulted to kill, each received the specific operands, comparables and deciders to test, and were resumed for a second round against each other's files. A synthesizer picked one move ruled survived or narrowed, never one the CFO skeptic had refuted on the math, with exactly two rejected alternatives, kill signals with thresholds and month windows, decider evidence that states what it cannot tell, and the six promotional rules with a claims map wherever a doctor or patient would see material."),
  figure("fig5_part2.png", "Figure 6. Part 2. The scraper's evidence wave landed mid-run; files announced but not yet on disk stayed labelled as assumptions."),
  table(
    ["Company", "The move", "Budget", "Kill signals"],
    [
      ["Merck", "A 15-person team splits the $5.9B long-dated inventory pool by product by month six, discloses the split, and releases only the sellable surplus, up to $1.0B, to retire the 4.30 percent notes due 2028 rather than refinance them. The IRS needle is recorded as a non-driver, with a gated sentence saying why.", "$7.5M, 15 people", "Four, including the month-six surplus review below $0.34B and the long-dated line at or above $5.9B in the 10-Q note."],
      ["Amgen", "Owned by the head of R&D, file into the TAVNEOS withdrawal hearing record an offer to fully fund and independently adjudicate the FDA-required five-year trial plus a U.S. liver-safety registry, releasing the trial budget only if the FDA signals it will accept postmarketing commitments. The indexed precedents cut against it and the deliverable says so.", "$12.5M, 12 people", "Five, including any written denial of the hearing request and no FDA signal by month twelve."],
      ["Pfizer", "Scale the existing U.S. ATTR-CM detection program with scintigraphy referral support at high heart-failure, low-testing cardiology sites, paid in two $25M tranches against matched control sites, the second released at month twelve only on a 380-start gate. Two promotional pieces with a 17-row claims map.", "$50M over 24 months", "Three, including fewer than 380 attributable starts by month twelve and U.S. Vyndaqel share of the class below 45 percent."],
    ],
    [0.9, 3.6, 1.0, 1.9]
  ),
  spacer(120),
  body("Of 13 candidate moves, nine were killed and four narrowed. Every chosen move is a narrowed candidate labelled unrefuted rather than confirmed, and the points the two skeptics could not settle are printed as two positions, never averaged."),

  h2("3.5 How outputs were checked"),
  body("Five checks sit between an agent's sentence and the screen, and they catch different things."),
  figure("fig6_gate.png", "Figure 7. The gate decides what a number may be. It fails closed: a sentence with an unsupported figure is withheld and logged, never shown with a guess."),
  numbered([
    [bold("The per-number gate. "), run("Every figure in every finding, product cell, move, budget, math step, kill signal and promotional claim is tokenised and checked against the quoted span of its citation, a formula whose operands are each cited and which recomputes the printed value, or a printed assumption label. A text with no numbers reports 'no numbers', not a pass. The rule is strict on purpose: a numeral elsewhere on the same page does not count, because our first gate accepted exactly that and approved wrong numbers (Section 5).")],
    [bold("An independent verifier. "), run("A fresh agent that never saw the writers' reasoning re-opened every citation and re-ran every derivation. The gate checks numbers; the verifier checks attribution and scope, which is where all seven Part 1 defects were.")],
    [bold("The UI exporter. "), run("Before an answer is cached for the chat, the exporter re-runs the structural contract: every block passed or had no numbers, exactly two rejected alternatives, drivers that name real Part 1 findings, no figure in prose that no passed block governs. A company that fails is not written; its tab shows as 'writing'. Both Part 1 and Part 2 exported with zero errors and zero figures withheld.")],
    [bold("Tests and greps. "), run("259 tests, plus two mechanical checks after every write: a pattern that catches a dropped leading digit (one shell heredoc turned '$2.4B' into '.4B' before we banned heredocs for output) and a count of em dashes, which must be zero.")],
    [bold("A human read. "), run("A person opened the cited page behind every needle. Several of our worst errors passed every code check and were caught only there.")],
  ]),
  body("Across sessions, the watcher ran status checks, enforced the single deadline, and ruled on refresh discrepancies: a cited benchmark replaces an unsourced assumption even when it moves a number; a timing assumption stays when no page dates it; a published number that fails against a new source is logged and reported before anyone edits it.")
);

// 4. Prompts
add(
  h1("4. The most important prompts"),
  body("Most of the prompting lives in written briefs, one per role, that every worker was told to read in full before starting: the forbidden lists, the output contracts, the gate rules, the eight category strings verbatim from the case. The launch prompts below pointed each agent at its brief and added the company-specific facts to test. They are reproduced exactly as sent, with one example per role; the other companies' prompts differ only in ticker and the specific checks lifted from that company's files."),
  ...codeBlock(
`CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Bash, Write, etc.)
- Write results to disk incrementally as you find them
- Do NOT spawn sub-agents
- Do NOT call TaskCreate/TaskUpdate or progress.sh
- Report results with absolute file paths and counts`,
    "The worker preamble, on every launch"
  ),
  body("Scope control did more than any clever wording. The preamble, plus one brief per role, is why 59 agents could run against one repository without a merge conflict."),
  ...codeBlock(
`TASK: You are the blind reader for ticker AMGN (Amgen). First read, in full, docs/part1/BLIND_READER_BRIEF.md and follow every rule in it, especially the DO NOT READ list (no prior-run files, no league/findings/nuggets/needle/handoff docs, no other worktrees). Then read the case PDF and rubric it names. Then walk all eight hiding places for AMGN using the citation index and verified tables, and write out/part1/_blind/AMGN/candidates.jsonl and reader_summary.md exactly in the brief's output contract. Verify every quote with verify_quote before writing it. Report the file paths, the number of candidates and no-finding records, and any data gaps.`,
    "Part 1 blind reader (paths shortened for the page)"
  ),
  ...codeBlock(
`TASK: Round 1 skeptic, lens MATERIALITY AND MATH, ticker AMGN. Read docs/part1/SKEPTIC_BRIEF.md in full and follow it. Input: out/part1/_blind/AMGN/candidates.jsonl (and reader_summary.md). Assume every candidate is wrong until the cited page proves otherwise; open each cited page with get_page yourself. Check especially: the TAVNEOS intangible figure and the "5.6 times sales" and EPS math (is it a gross or net-of-tax number, what share count), the IRS Puerto Rico exposure vs accrual numbers and periods, whether the receivables conclusion (no finding) is right, whether net-price percentages come from a cited page or a raw table, and whether "52% of growth in Other products" is arithmetic on cited lines. Write out/part1/_blind/AMGN/skeptic_materiality_r1.json in the brief's shape. Report the count of refuted vs held and the single biggest math problem you found.`,
    "Part 1 skeptic, round 1. Generic 'check the math' produced generic verdicts; naming the operands did not."
  ),
  ...codeBlock(
`Round 2, same lens (MATERIALITY AND MATH), ticker AMGN. The other skeptic, on the OBVIOUSNESS lens, has written out/part1/_blind/AMGN/skeptic_obviousness_r1.json. Read their argument AGAINST THE SOURCES (open the pages they cite with get_page). Concede what they got right, hold what you still believe with a reason, and narrow your claim if it was too broad. Do not restate round 1. In particular: they held c03 (TEPEZZA: the Q1 2026 10-Q says 22 of 29 growth points were channel inventory while the call credited demand) as least obvious, which you refuted as too small and contradicted by Q2; settle whether a channel-inventory-vs-demand discrepancy on a roughly $2B product is material. They held c06 narrowed (TAVNEOS carrying value about 5x sales, GAAP-only, FDA withdrawal request reported on the 2026Q2 call but not in the 10-Q note), c02 narrowed to the filings-only 54% deduction rate and 30% accrual build with new "timing of payments" wording, and c08 narrowed to the unflagged $130M Q2 2026 true-ups; they killed c05 (the accrual gap was answered in 2024Q2 and 2026Q1 Q&A) and c10 (the $2.5B U.S. capex undercuts "no pledge"). Size the narrowed c02, c06 and c08 versions on your math. Write out/part1/_blind/AMGN/skeptic_materiality_r2.json in the SKEPTIC_BRIEF round-2 shape (each verdict carries round2: {conceded, held, narrowed}). Report what changed between your rounds.`,
    "Part 1 skeptic, round 2. The same agent is resumed so it keeps its notes; it reads the other lens against the pages, not against the summary."
  ),
  ...codeBlock(
`TASK: Independent verifier for the three Part 1 deliverables. Assume every number is WRONG until the cited page proves it. Do not read the writers' reports or scripts; read only the output files and the sources. Files: out/part1/{AMGN,MRK,PFE}/part1.json. Sources: the citation index via agent/moat/cite.py (get_page(doc_id, page) and verify_quote). For each company: (1) for every finding row, open every cite in cites and confirm the quote is on the page (verify_quote) and that each number in finding, impact.text and impact.math is either inside a quoted span, equal to a cite's own value, labelled [derived] with operands that are themselves cited and whose arithmetic you reproduce, or labelled [assumption]; (2) for the Sharpest Needle "why" and the product_table financial_tie, growth_limiter and priced_in texts, do the same; (3) sample 6 product cells per company (at least one per row key) and check the quoted label or table text is on the page; (4) check that no sentence states as fact a number the blind skeptics refuted (read out/part1/_blind/<T>/synthesis.json rulings for the ids used); (5) check currency labels and that no Bloomberg-licensed page is quoted. Write out/part1/verify_report.md with a table per company (row or cell, what you checked, pass or fail, the exact defect) and a summary line with counts. Do not edit the part1 files. Report the fail count per company and the single worst defect.`,
    "Part 1 independent verifier"
  ),
  ...codeBlock(
`TASK: You are the Part 2 STRATEGIST for ticker AMGN (Amgen). First read, in full, docs/part2/STRATEGIST_BRIEF.md and follow every rule in it: the READ ONLY list, the DO NOT READ list, the index interpreter and usage, the citation rules, the Python-only writing rule and the grep check. Then read the case PDF's Part 2 section and the rubric, then out/part1/AMGN/part1.json and part1.md. Propose at least four candidate moves of at least two types, each costed with cited math, written to out/part2/_work/AMGN/candidates.jsonl in the brief's exact contract, plus strategist_summary.md and data_requests.md. The skeptics default to kill, so every number must trace to a cited page or carry [assumption]; a move management has already announced is obvious and must be marked so in already_announced_check. Work to disk as you go. Finish within about 40 minutes of work; depth on four well-evidenced moves beats six thin ones. Report the candidate ids, types, cost and return amounts, and the data gaps.`,
    "Part 2 strategist"
  ),
  ...codeBlock(
`What the skeptics concluded (verify against their files, do not trust this summary): all four AMGN candidates refuted as written; after round 2 both lenses name the same narrowed survivor: m01 in gated form, a $10M to $15M [assumption] hearing-record offer to the FDA ... Unresolved: whether the FDA's postmarketing-requirement path has real probability given the untrue-statements ground; whether m02's lift is unsourced or uncreditable; gross vs net rebate basis; UCB's walk-away price. Record them in unresolved[] as the two positions, never averaged.`,
    "From the Part 2 synthesizer prompt. The orchestrator's summary is a pointer, not evidence."
  ),
  ...codeBlock(
`Every number and every quotation in your answer must carry a citation to one of the provided source blocks. Quote figures exactly as they appear in the source (same digits, same units). Write one claim per sentence and cite each sentence that contains a number or a factual assertion. If the sources do not contain the fact, write "not found in the provided sources" instead of guessing. Never compute or round a figure that is not printed on a source page unless you show the calculation with each operand cited. Never invent, infer, or state page numbers or document names yourself; page references come only from the citations. Any sentence containing a number or quote that has no citation will be deleted before the reader sees it.`,
    "The citation system rule, appended to every cited model call. The last sentence is true: the gate deletes it."
  ),
  body("One more sentence did a great deal of work earlier in the weekend, when two reviewer agents were set on our own model code: 'Assume the claim is WRONG until the code proves otherwise.' Applied to the first backtest, it killed a result we had been pleased with (Section 5, case 1)."),
  body("Both pipelines are now packaged as Claude Code skills, fine-print-part1 and fine-print-part2, with every brief copied byte for byte and the launch and resume messages recorded per role, so the run can be repeated on any company in the index.")
);

// 5. AI wrong
add(
  h1("5. Where the AI was confidently wrong, and how we caught it"),
  body("We kept a log. The collectors recorded 516 cases where a model wrote something the source did not say, each with what it wrote, what the page says and how it was caught. The model and findings work added 26 more. The table picks the cases that changed how we built, grouped by what caught them."),
  table(
    ["What the AI claimed", "What was true", "Caught by", "What changed"],
    [
      ["Lilly led the company ranking; its gross margin implied about $68B of impact, 80 percent of its score.", "An 85.8 percent margin level had been scored as if it were a margin change. A high margin is a strength.", "A person tracing the score row by row because it looked too good.", "A favourable margin level scores zero. Lilly fell from first to eighth. The league was demoted to triage and never shown."],
      ["Our first citation gate marked four z-scores and four product counts on the top findings as 'verified'.", "The gate accepted any numeral on the cited page: an EPS of 1.18, an I/B/E/S value of -0.13, a page footer reading '- 3 -'.", "An independent re-check of the gate's own output.", "Verified now means inside the quoted span or equal to the citation's own value. The check was re-run from scratch."],
      ["Amgen needle from the ratio code: receivables growing faster than revenue, a collections flag.", "Receivables track gross invoices to three wholesalers with a separate rebate liability. The real signal was deductions rising from 51 to 54 percent of gross sales.", "Parker reading the receivables footnote.", "A ratio is a flag for a human read, never a finding by itself. The AstraZeneca version of the same flag was factored receivables; impact zero."],
      ["Label-table exclusivity dates: Trulicity 2026, Zepbound 2039, Ibrance 2037, Vyndamax 2035, Tremfya 2029.", "Later-listed use or formulation patents, or Purple Book reference exclusivity, not the compound date.", "A human read against each 10-K's patent table.", "Exclusivity rows read the company-stated date on the cited 10-K page and derive the gap from two dated operands."],
      ["The speaker check passed a named Truist analyst as the asker of a question.", "The surname sat in the operator's introduction; the question was asked by a colleague 'on for' him.", "A person reading the verifier's output.", "The name must be on the speaker label, not within a text window."],
      ["Quotes from fool.com transcripts.", "Those files open with model-written 'takeaways' that read like call text.", "The verifier, then a human read.", "The summaries are flagged in the corpus and the verifier rejects quotes from them."],
      ["Finding ids were stable across runs.", "Ids used Python's hash(), which is salted per process; joins across the league, the app and DECIDE broke silently.", "A test that ran two processes.", "sha256 ids."],
      ["616 rows of restated product revenue across filings.", "Zero true restatements. 447 were recasts where a company moved products between lines, mostly footnoted.", "Member-set reconciliation of old and new filings plus reading the footnotes.", "Recasts are a separate category and never a finding."],
      ["The Amgen Sharpest Needle rationale: 'the only surviving ruling both skeptics held through both rounds'.", "A second candidate had the same profile. The sentence overclaimed and the block had no marker map to trace its numbers.", "The independent verifier, as its single worst defect.", "The rationale was rewritten truthfully and given a marker map; the gate now checks for marker maps."],
      ["The Amgen blind reader: TAVNEOS sales appear in no filing table.", "The 10-K itemises them on page 75.", "The synthesizer settling the fact from the page.", "Readers' data-gap notes are treated as claims to verify, not facts."],
      ["A Part 2 move named a real executive as its owner, and a trial cost of $150,000 per patient stood as a bare assumption.", "The name was on no cited page. A published benchmark (Sertkaya 2024) was in the index.", "The orchestrator's post-synthesis read and the scraper's fills.", "Name the role unless the name is on a cited page. A cited benchmark replaces an assumption even when it moves a number."],
      ["A $100 billion market forecast recorded as an upfront deal payment; a takeover target's market cap 50 times too high from pricing ordinary shares at the ADS rate.", "Collector misreads of a press release and a share count.", "Hand checks on 554 deal rows and every target's balance sheet date.", "Deal benchmarks rebuilt from verified rows only; every target priced from one balance-sheet date."],
    ],
    [1.8, 1.8, 1.3, 1.8],
    { size: 16 }
  ),
  spacer(160),
  ...callout("The gate proves a number is on the cited page. It cannot tell whether the page means what the sentence says. Every one of the seven defects the verifier found in our final Part 1 tables was attribution or scope, not arithmetic.", "What the log taught us"),
  body("Two patterns run through the list. The AI was most confidently wrong where a number was plausible and the story around it was real: Lilly's margins are high and its obesity franchise is strong, so a $68B impact did not look absurd. And the checks that caught the worst cases were not the clever ones. A person reading a footnote, a colleague reading the other skeptic's file, a fresh agent told to assume everything is wrong: these found what the gate, the tests and the ratios could not.")
);

// 6. Differently
add(
  h1("6. What we would do differently"),
  bullets([
    [bold("Build the gate before the scorer. "), run("The scoring model ran for a day on numbers nothing had verified, and the first gate was wrong too. Verification is the product; everything else is a view over it.")],
    [bold("Pick the company on human-read findings first, "), run("with code ratios as corroboration and not the other way round. The blind pass we ran Saturday night is the process we should have started with Saturday morning.")],
    [bold("Start from the case's deliverables. "), run("We built a larger model than the case needed and spent part of the weekend defending it. The findings table, the needle, the product comparison, one move and this report are the whole job.")],
    [bold("Write the handoff before each phase. "), run("Two long sessions became unusable overnight when their requests began failing; the work continued only because the briefs, the launch prompts and the state lived in the repository, not in a context window.")],
    [bold("Put the rubric checks in the first prompt. "), run("'One committed number with an owner and a decision month' and 'tie the move to the sealed needle' were added mid-wave to the Part 2 synthesizers. They belong in the brief.")],
    [bold("Give every skeptic the operands to test. "), run("Generic instructions produced generic verdicts. Lifting the specific figures, comparables and deciders from the candidates file into each prompt is what made round two sharp.")],
    [bold("Fix identifiers on day one. "), run("Unstable ids broke joins quietly for hours.")],
    [bold("Arm the API key earlier. "), run("The planned one-pass model track, with citations on every block and the courtroom trial, stayed a plan; every sentence in the demo is deterministic. That is honest, but a checked model track would have been better.")],
    [bold("Write partial output early and keep per-worker scratch space. "), run("The host machine slept mid-run once and parallel workers collided on a shared folder once; both are avoidable.")],
  ])
);

// 7. Limits and reproducing
add(
  h1("7. Limits we state, and how to reproduce the run"),
  body("Some things the system cannot see, and we say so rather than estimate. No product-level net price is public, so we never claim one; our policy and patent math covers the U.S. only, because filings give ex-U.S. revenue but not units or price; formulary and rebate contracts are private; analyst consensus is licensed and feeds the math but is never displayed; CMS Part D claims are annual to data year 2024; most Q3 2026 results land after judging, so the numbers run through Q2 2026. Every footnote opens the source document, but the page-highlight viewer runs only on our machines; public footnotes give the file page, the printed page and the document link."),
  body("Everything is in one repository. The data branch holds the collectors, the index builder and the verified tables; the model branch holds the gate, the two pipelines and their outputs; the UI branch holds the exporters and the chat. The two skills, fine-print-part1 and fine-print-part2, carry each brief byte for byte and the launch and resume messages per role. A new company enters with one command that builds its filings, labels, calls and tables into the same index with stable ids; we proved it on three companies that were not in the case."),
  rule(LINE, 120, 200),
  new Paragraph({
    spacing: { after: 0 },
    children: [muted("Repository: aidanmcjones/neeley-ai-forward. Final commits: data-moat ce3c0f2, quant-model 2460a00, ui 2401772. Sealed selection sha256 903fc656fa7a1d1b2bdf303d8d8f9321d5f1f7b741f6b751c4cdf4f9c40c8fa7.", 16)],
  })
);

// ---------- document ----------
const doc = new Document({
  creator: "Team NEEDLE",
  title: "How we did it",
  description: "Neeley AI Forward 2026, The Fine Print: tools, workflow, prompts, where the AI was wrong, what we would change.",
  styles: {
    default: { document: { run: { font: SANS, size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: SERIF, size: 38, color: INK }, paragraph: { spacing: { before: 520, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: SERIF, size: 27, color: INK }, paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 260 } }, run: { color: CLAY } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 300 } }, run: { color: CLAY, bold: true } } }] },
    ],
  },
  sections: [
    {
      properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: 1296, bottom: 1200, left: MARGIN, right: MARGIN } } },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
              children: [
                muted("NEEDLE  ·  How we did it  ·  Neeley AI Forward 2026", 15),
                new TextRun({ text: "\t", font: SANS, size: 15 }),
                new TextRun({ children: [PageNumber.CURRENT], font: SANS, size: 15, color: MUTED }),
              ],
            }),
          ],
        }),
      },
      children: content,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("wrote", OUT, buf.length, "bytes");
});
