"""Flow charts for the How We Did It report. Warm, quiet palette; one visual system."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT = os.path.dirname(os.path.abspath(__file__))
INK = "#141413"
MUTED = "#5E5D59"
LINE = "#B8B5AD"
PAPER = "#FFFFFF"
CLAY = "#D97757"
CLAY_SOFT = "#F6E3DA"
SAND = "#F0EEE6"
SLATE = "#6A9BCC"
SLATE_SOFT = "#E1ECF6"
MOSS = "#7A9E7E"
MOSS_SOFT = "#E4EEE5"
FONT = "Helvetica Neue"

plt.rcParams["font.family"] = [FONT, "Helvetica", "Arial", "DejaVu Sans"]


def fig(w, h):
    f, ax = plt.subplots(figsize=(w, h), dpi=220)
    f.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return f, ax


def box(ax, x, y, w, h, title, sub=None, fill=SAND, edge=LINE, tsize=7.4, ssize=6.2, bold=True, radius=0.08):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                       linewidth=0.9, edgecolor=edge, facecolor=fill)
    ax.add_patch(p)
    if sub:
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", fontsize=tsize,
                color=INK, weight="bold" if bold else "normal")
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=ssize, color=MUTED, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=tsize,
                color=INK, weight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color=MUTED, lw=1.0, style="-|>", rad=0.0, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=9, linewidth=lw,
                        color=color, connectionstyle=f"arc3,rad={rad}", linestyle=ls, shrinkA=2, shrinkB=2)
    ax.add_patch(a)


def label(ax, x, y, s, size=7.0, color=MUTED, ha="center", weight="normal", style="normal"):
    ax.text(x, y, s, ha=ha, va="center", fontsize=size, color=color, weight=weight, style=style, linespacing=1.25)


def save(f, name):
    f.savefig(os.path.join(OUT, name), bbox_inches="tight", pad_inches=0.08, facecolor=PAPER)
    plt.close(f)


# 1. System overview --------------------------------------------------------
def system_overview():
    f, ax = fig(7.2, 3.0)
    y = 1.65
    bw, bh, gap = 1.1, 0.8, 0.1
    xs = [0.1]
    for _ in range(5):
        xs.append(xs[-1] + bw + gap)
    boxes = [
        ("Public sources", "SEC, FDA, CMS,\ncalls, labels", SAND),
        ("Citation index", "7,003 docs\n78,392 pages", SLATE_SOFT),
        ("Agent pipelines", "Part 1 and Part 2\nblind, adversarial", CLAY_SOFT),
        ("Per-number gate", "cited, derived,\nassumed, or withheld", MOSS_SOFT),
        ("Static chat UI", "cached answers,\nno API key", SAND),
        ("Judges", "every number opens\nits source page", SAND),
    ]
    for (t, s, fill), x in zip(boxes, xs):
        box(ax, x, y, bw, bh, t, s, fill=fill)
    for i in range(5):
        arrow(ax, xs[i] + bw, y + bh / 2, xs[i + 1], y + bh / 2)
    # human and watcher band
    hb_y = 0.35
    box(ax, 0.1, hb_y, 3.45, 0.7, "Humans", "read every needle on its cited page\nand make the company pick", fill=PAPER, edge=CLAY, tsize=7.6, ssize=6.2)
    box(ax, 3.65, hb_y, 3.45, 0.7, "Watcher session", "checks each agent against its goal,\nthe rubric and the one deadline", fill=PAPER, edge=CLAY, tsize=7.6, ssize=6.2)
    for x in [xs[2] + bw / 2, xs[3] + bw / 2]:
        arrow(ax, x, y, x, hb_y + 0.7, color=CLAY, style="<|-|>", lw=0.8, ls=(0, (3, 2)))
    label(ax, 3.6, 2.72, "Code fetches and verifies. Agents reason. Humans decide.", size=8.2, color=INK, weight="bold")
    save(f, "fig1_system.png")


# 2. A document's path ------------------------------------------------------
def document_path():
    f, ax = fig(7.2, 2.35)
    y = 1.2
    bw, bh, gap = 1.28, 0.72, 0.16
    x = 0.15
    steps = [
        ("Fetch by code", "EDGAR, DailyMed, CMS,\ntranscripts; never pasted"),
        ("Page-mark", "[[page N | printed P]]\non every page"),
        ("Index", "SQLite with FTS5:\npages, turns, facts"),
        ("Grade and flag", "transcripts A to D,\nlicensed, superseded"),
        ("Verify on demand", "verify_quote(text,\ndoc, page) is exact"),
    ]
    xs = []
    for t, s in steps:
        box(ax, x, y, bw, bh, t, s, fill=SLATE_SOFT if "Index" in t else SAND, tsize=7.4, ssize=6.2)
        xs.append(x)
        x += bw + gap
    for i in range(len(xs) - 1):
        arrow(ax, xs[i] + bw, y + bh / 2, xs[i + 1], y + bh / 2)
    label(ax, 3.6, 2.12, "Every sentence an agent may quote carries doc_id#p<page>, and the page can be opened.", size=8.0, color=INK, weight="bold")
    # bottom notes
    notes = [
        (xs[0] + bw / 2, "Collectors log their own\nerrors: 516 cases in ai_wrong.jsonl"),
        (xs[2] + bw / 2, "117,904 fact rows from\n302 verified tables"),
        (xs[4] + bw / 2, "Rows that fail are dropped\nbefore any agent sees them"),
    ]
    for cx, s in notes:
        label(ax, cx, 0.55, s, size=6.6)
        arrow(ax, cx, y, cx, 0.85, color=LINE, style="-", lw=0.7, ls=(0, (2, 2)))
    save(f, "fig2_document.png")


# 3. Team and agents --------------------------------------------------------
def team_split():
    f, ax = fig(7.2, 3.4)
    # humans
    box(ax, 0.2, 2.55, 3.3, 0.66, "Parker", "company read, findings judgment,\nPart 2 content, deck", fill=PAPER, edge=CLAY)
    box(ax, 3.7, 2.55, 3.3, 0.66, "Aidan", "API key, worktrees and PR chain, UI, demo,\nhow-we-did-it, Devpost", fill=PAPER, edge=CLAY)
    # four sessions
    y = 1.2
    bw, bh, gap = 1.58, 0.92, 0.14
    x = 0.2
    sessions = [
        ("Scraper session", "data-moat, PR #16\nindex, verified tables,\nretrieval helpers", SLATE_SOFT),
        ("Model session", "quant-model, PR #21\nPart 1 and Part 2\nagent waves, the gate", CLAY_SOFT),
        ("UI session", "ui, PR #22\nexporters, chat page,\nartifact publishes", MOSS_SOFT),
        ("Watcher session", "status checks, rubric\nand scope drift, rulings\non refresh discrepancies", SAND),
    ]
    xs = []
    for t, s, fill in sessions:
        box(ax, x, y, bw, bh, t, s, fill=fill, tsize=7.6, ssize=6.3)
        xs.append(x)
        x += bw + gap
    for cx in [xs[0] + bw / 2, xs[1] + bw / 2]:
        arrow(ax, 1.85, 2.55, cx, y + bh, color=CLAY, lw=0.8)
    for cx in [xs[2] + bw / 2, xs[3] + bw / 2]:
        arrow(ax, 5.35, 2.55, cx, y + bh, color=CLAY, lw=0.8)
    # messages between sessions
    arrow(ax, xs[3] + bw / 2, y, xs[0] + bw / 2, y, color=MUTED, lw=0.7, style="<|-|>", rad=-0.18)
    label(ax, 3.6, 0.62, "cross-session messages: status, SHAs, data inventories, rulings", size=6.6)
    # PR chain
    label(ax, 3.6, 0.32, "PR chain: main  <  scaffold #1  <  gap-data #2  <  corpus #5  <  needle (Parker)  <  data-moat #16  |  quant-model #21  <  ui #22", size=6.6, color=INK)
    label(ax, 3.6, 3.32, "Two people, four long-running Claude Code sessions, each in its own git worktree and branch.", size=8.0, color=INK, weight="bold")
    save(f, "fig3_team.png")


# 4. Part 1 pipeline --------------------------------------------------------
def part1_pipeline():
    f, ax = fig(7.2, 3.9)
    label(ax, 3.6, 3.75, "Part 1: Find the Story. Blind, adversarial, sealed, then written through the gate.", size=8.0, color=INK, weight="bold")
    # Phase A
    ya = 2.45
    bw, bh, gap = 1.22, 0.86, 0.12
    x = 0.15
    stages = [
        ("10 blind readers", "one per company; case,\nrubric, index only;\n8 hiding places", SAND),
        ("20 skeptics", "round 1; materiality and\nmath; obviousness;\ndefault to refuted", CLAY_SOFT),
        ("Round 2", "same agents resumed;\neach reads the other\nlens, concedes or holds", CLAY_SOFT),
        ("10 synthesizers", "survived, narrowed\nor killed; no voting,\nno averaging", SAND),
        ("1 ranker", "picks 3 on the case's\ntest; seals selection.md\nwith sha256", MOSS_SOFT),
    ]
    xs = []
    for t, s, fill in stages:
        box(ax, x, ya, bw, bh, t, s, fill=fill, tsize=7.2, ssize=6.2)
        xs.append(x)
        x += bw + gap
    for i in range(len(xs) - 1):
        arrow(ax, xs[i] + bw, ya + bh / 2, xs[i + 1], ya + bh / 2)
    label(ax, 0.15, ya + bh + 0.14, "Phase A, 45 minutes wall clock", size=7.0, ha="left", color=CLAY, weight="bold")
    label(ax, 3.9, 2.12, "95 candidates in; 70 killed, 25 narrowed, 0 survived as stated. The usual kill: management already said it.", size=6.8)
    # Phase B
    yb = 0.85
    stages_b = [
        ("3 writers", "AMGN, MRK, PFE: five\nfindings, needle, product\ntable; every cell gated", SAND),
        ("Per-number gate", "261 cites and 503\nnumbers; fail closed", MOSS_SOFT),
        ("Verifier", "fresh context; assume\nevery number wrong;\n7 scoping defects", CLAY_SOFT),
        ("Priced-in and fixes", "evidence-graded call;\nseven fixes re-gated", SAND),
        ("UI exporter", "0 errors, 0 figures\nwithheld; cached answer", MOSS_SOFT),
    ]
    xb = []
    x = 0.15
    for t, s, fill in stages_b:
        box(ax, x, yb, bw, bh, t, s, fill=fill, tsize=7.2, ssize=6.2)
        xb.append(x)
        x += bw + gap
    for i in range(len(xb) - 1):
        arrow(ax, xb[i] + bw, yb + bh / 2, xb[i + 1], yb + bh / 2)
    label(ax, 1.5, yb + bh + 0.14, "Phase B, after the seal", size=7.0, ha="left", color=CLAY, weight="bold")
    ex, ey = xs[4] + bw / 2, ya - 0.1
    ax.plot([ex, ex, xb[0] + bw / 2, xb[0] + bw / 2], [ya, ey, ey, yb + bh + 0.3], color=MUTED, lw=0.9)
    arrow(ax, xb[0] + bw / 2, yb + bh + 0.3, xb[0] + bw / 2, yb + bh, color=MUTED, lw=0.9)
    label(ax, 3.6, 0.45, "Phase A agents may not open any prior run, league table, nugget file or other worktree. The seal is checked by recomputing the hash.", size=6.8)
    save(f, "fig4_part1.png")


# 5. Part 2 pipeline --------------------------------------------------------
def part2_pipeline():
    f, ax = fig(7.2, 2.9)
    label(ax, 3.6, 2.75, "Part 2: Make the Call. One move per company, argued by options and two skeptics who default to kill.", size=8.0, color=INK, weight="bold")
    y = 1.45
    bw, bh, gap = 1.22, 0.9, 0.12
    x = 0.15
    stages = [
        ("3 strategists", "4 or more costed moves\nof 2 or more types from\nthe sealed Part 1 findings", SAND),
        ("6 skeptics", "round 1; CFO and math;\nDecider and compliance;\ndefault to kill", CLAY_SOFT),
        ("Round 2", "resumed; read the other\nlens against the cited\npages; concede or hold", CLAY_SOFT),
        ("3 synthesizers", "ONE move, two rejected,\nkill signals, decider\nevidence, promo rules", SAND),
        ("Gate and exporter", "every block passed or\nno numbers; drivers tie\nto Part 1 findings", MOSS_SOFT),
    ]
    xs = []
    for t, s, fill in stages:
        box(ax, x, y, bw, bh, t, s, fill=fill, tsize=7.2, ssize=6.2)
        xs.append(x)
        x += bw + gap
    for i in range(len(xs) - 1):
        arrow(ax, xs[i] + bw, y + bh / 2, xs[i + 1], y + bh / 2)
    # scraper feed
    box(ax, 1.4, 0.22, 4.4, 0.72, "Scraper data wave, mid-run", "labels, head-to-head, CMS, IRA, deal comps, 325 filing-number\nanchors; files not yet on disk stay [assumption]", fill=SLATE_SOFT, tsize=7.2, ssize=6.0)
    arrow(ax, 3.6, 0.94, xs[3] + bw / 2, y, color=MUTED, lw=0.8)
    arrow(ax, 2.2, 0.94, xs[0] + bw / 2, y, color=MUTED, lw=0.8)
    label(ax, 6.55, 0.6, "13 candidates\n9 killed, 4 narrowed\n0 survived as stated", size=6.8, color=INK)
    save(f, "fig5_part2.png")


# 6. The gate ---------------------------------------------------------------
def gate_flow():
    f, ax = fig(7.2, 3.1)
    label(ax, 3.6, 2.95, "The per-number gate, run on every figure in every block before anything is shown.", size=8.0, color=INK, weight="bold")
    bw, bh = 1.5, 0.62
    # decision chain
    y = 1.95
    q = [
        ("Is it inside the quoted span,\nor the citation's own value?", "verified"),
        ("Does a formula over cited\noperands recompute it?", "derived"),
        ("Does it carry a printed\n[assumption] label?", "assumed"),
    ]
    x = 0.15
    xs = []
    for i, (t, res) in enumerate(q):
        box(ax, x, y, bw, bh, t, fill=SAND, bold=False, tsize=7.0)
        xs.append(x)
        box(ax, x + 0.1, y - 0.72, bw - 0.2, 0.4, res, fill=MOSS_SOFT, tsize=7.6)
        arrow(ax, x + bw / 2, y, x + bw / 2, y - 0.32, color=MOSS, lw=0.9)
        label(ax, x + bw / 2 + 0.3, y - 0.17, "yes", size=6.4, color=MOSS)
        if i < 2:
            arrow(ax, x + bw, y + bh / 2, x + bw + 0.3, y + bh / 2)
            label(ax, x + bw + 0.15, y + bh / 2 + 0.13, "no", size=6.4)
        x += bw + 0.3
    box(ax, x, y, bw, bh, "Unsupported", "withheld and logged,\nnever shown with a guess", fill=CLAY_SOFT, edge=CLAY, tsize=7.4, ssize=6.0)
    arrow(ax, xs[2] + bw, y + bh / 2, x, y + bh / 2)
    label(ax, xs[2] + bw + 0.15, y + bh / 2 + 0.13, "no", size=6.4)
    box(ax, 0.15, 0.2, 6.9, 0.78, "Then a person reads the page", "The gate proves a number is on the cited page. It cannot tell whether the page means what the sentence says.\nAn independent verifier and a human read do that.", fill=PAPER, edge=CLAY, tsize=7.4, ssize=6.2)
    save(f, "fig6_gate.png")


# 7. Timeline ---------------------------------------------------------------
def timeline():
    f, ax = fig(7.2, 1.9)
    y = 1.0
    ax.plot([0.3, 6.9], [y, y], color=LINE, lw=1.2)
    pts = [
        (0.3, "Fri Oct 16", "scaffold, collectors,\nParker handoff"),
        (1.5, "Sat 9:00 am", "case released;\nshortlist of ten"),
        (2.7, "Sat afternoon", "data moat waves 1 to 4;\nnugget miner and red team"),
        (4.0, "Sat 10:27 pm", "blind Part 1 pass;\nseal at 11:12 pm"),
        (5.2, "Sun 12:05 am", "Part 2 waves;\nUI exports and publishes"),
        (6.6, "Sun 2:00 pm", "Devpost\nsubmission"),
    ]
    for i, (x, t, s) in enumerate(pts):
        ax.plot([x], [y], marker="o", markersize=5.5, color=CLAY if i in (3, 4, 5) else SLATE, markeredgecolor=PAPER, zorder=3)
        label(ax, x, y + 0.32, t, size=7.2, color=INK, weight="bold")
        label(ax, x, y - 0.42, s, size=6.5)
    label(ax, 3.6, 1.72, "Thirty hours, Central Time.", size=8.0, color=INK, weight="bold")
    save(f, "fig7_timeline.png")


if __name__ == "__main__":
    system_overview()
    document_path()
    team_split()
    part1_pipeline()
    part2_pipeline()
    gate_flow()
    timeline()
    print("ok")
