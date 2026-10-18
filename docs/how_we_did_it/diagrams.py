"""Flow charts for the How We Did It report. Drawn at the printed width (6.7 in) so type is 1:1 on the page,
cropped to the drawn artists (not the axes), titles anchored to the top of each box and subtitles to the bottom."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.transforms import Bbox
import os

OUT = os.path.dirname(os.path.abspath(__file__))
DPI = 200
W = 6.7  # printed column width in inches; every figure is drawn at this width
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
TS, SS, NS = 8.0, 6.8, 6.8  # title, subtitle, note sizes in points (printed 1:1)

plt.rcParams["font.family"] = ["Arial", "Helvetica", "DejaVu Sans"]


def fig(h):
    f, ax = plt.subplots(figsize=(W, h), dpi=DPI)
    ax.set_position([0, 0, 1, 1])
    f.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, W)
    ax.set_ylim(0, h)
    ax.axis("off")
    return f, ax


def bh_for(sub):
    """Box height from the subtitle's line count."""
    n = 0 if not sub else sub.count("\n") + 1
    return {0: 0.42, 1: 0.58, 2: 0.72, 3: 0.86}[n]


def box(ax, x, y, w, h, title, sub=None, fill=SAND, edge=LINE, tsize=TS, ssize=SS, bold=True, radius=0.07):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                       linewidth=0.9, edgecolor=edge, facecolor=fill)
    ax.add_patch(p)
    if sub:
        ax.text(x + w / 2, y + h - 0.085, title, ha="center", va="top", fontsize=tsize,
                color=INK, weight="bold" if bold else "normal")
        ax.text(x + w / 2, y + (h - 0.30) / 2, sub, ha="center", va="center", fontsize=ssize, color=MUTED, linespacing=1.22)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=tsize,
                color=INK, weight="bold" if bold else "normal", linespacing=1.22)


def arrow(ax, x1, y1, x2, y2, color=MUTED, lw=1.0, style="-|>", rad=0.0, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=7, linewidth=lw,
                        color=color, connectionstyle=f"arc3,rad={rad}", linestyle=ls, shrinkA=0, shrinkB=0)
    ax.add_patch(a)


def label(ax, x, y, s, size=NS, color=MUTED, ha="center", va="center", weight="normal"):
    ax.text(x, y, s, ha=ha, va=va, fontsize=size, color=color, weight=weight, linespacing=1.25)


def row(ax, y, items, bw, gap, x0=None, arrows=True, **kw):
    """Lay out boxes left to right, centred on the canvas unless x0 is given. Returns the x positions and bh."""
    n = len(items)
    total = n * bw + (n - 1) * gap
    x = (W - total) / 2 if x0 is None else x0
    bh = max(bh_for(s) for _, s, _ in items)
    xs = []
    for t, s, fill in items:
        box(ax, x, y, bw, bh, t, s, fill=fill, **kw)
        xs.append(x)
        x += bw + gap
    if arrows:
        for i in range(n - 1):
            arrow(ax, xs[i] + bw, y + bh / 2, xs[i + 1], y + bh / 2)
    return xs, bh


def save(f, ax, name, pad=0.05):
    f.canvas.draw()
    r = f.canvas.get_renderer()
    arts = list(ax.texts) + list(ax.patches) + list(ax.lines)
    bb = Bbox.union([a.get_window_extent(r) for a in arts]).transformed(f.dpi_scale_trans.inverted())
    f.savefig(os.path.join(OUT, name), bbox_inches=bb.padded(pad), facecolor=PAPER, dpi=DPI)
    plt.close(f)


# 1. System overview --------------------------------------------------------
def system_overview():
    f, ax = fig(2.3)
    items = [
        ("Public sources", "SEC, FDA, CMS,\ncalls, labels", SAND),
        ("Citation index", "7,003 docs\n78,392 pages", SLATE_SOFT),
        ("Agent pipelines", "Part 1 and Part 2\nblind, adversarial", CLAY_SOFT),
        ("Citation gate", "cited, derived,\nassumed, or\nwithheld", MOSS_SOFT),
        ("Static chat UI", "cached answers,\nno API key", SAND),
        ("Judges", "every number\nopens its\nsource page", SAND),
    ]
    y = 1.3
    bw = 0.96
    xs, bh = row(ax, y, items, bw=bw, gap=0.188)
    hb_y, hb_h = 0.2, 0.74
    left = xs[0]
    right = xs[-1] + bw
    half = (right - left - 0.2) / 2
    box(ax, left, hb_y, half, hb_h, "Humans", "read every needle on its cited page\nand make the company pick", fill=PAPER, edge=CLAY)
    box(ax, left + half + 0.2, hb_y, half, hb_h, "Watcher session", "checks each agent against its goal,\nthe rubric and the one deadline", fill=PAPER, edge=CLAY)
    for i in (2, 3):
        cx = xs[i] + bw / 2
        arrow(ax, cx, y, cx, hb_y + hb_h, color=CLAY, style="<|-|>", lw=0.8, ls=(0, (3, 2)))
    save(f, ax, "fig1_system.png")


# 2. A document's path ------------------------------------------------------
def document_path():
    f, ax = fig(2.0)
    items = [
        ("Fetch by code", "EDGAR, DailyMed, CMS,\ntranscripts; never pasted", SAND),
        ("Page-mark", "[[page N | printed P]]\non every page", SAND),
        ("Index", "SQLite with FTS5:\npages, turns, facts", SLATE_SOFT),
        ("Grade and flag", "transcripts A to D,\nlicensed, superseded", SAND),
        ("Verify on demand", "verify_quote(text,\ndoc, page) is exact", SAND),
    ]
    y = 1.05
    bw = 1.22
    xs, bh = row(ax, y, items, bw=bw, gap=0.15)
    notes = [
        (xs[0], "left", xs[0] + bw / 2, "Collectors log their own errors:\n516 cases in ai_wrong.jsonl"),
        (xs[2] + bw / 2, "center", xs[2] + bw / 2, "117,904 fact rows from\n302 verified tables"),
        (xs[4] + bw, "right", xs[4] + bw / 2, "Rows that fail are dropped\nbefore any agent sees them"),
    ]
    for tx, ha, lx, s in notes:
        label(ax, tx, 0.62, s, ha=ha, va="top")
        ax.plot([lx, lx], [y, 0.68], color=LINE, lw=0.7, linestyle=(0, (2, 2)))
    save(f, ax, "fig2_document.png")


# 3. Team and agents --------------------------------------------------------
def team_split():
    f, ax = fig(2.7)
    bw, gap = 1.52, 0.207
    items = [
        ("Scraper session", "data-moat, PR #16\nindex, verified tables,\nretrieval helpers", SLATE_SOFT),
        ("Model session", "quant-model, PR #21\nPart 1 and Part 2\nagent waves, the gate", CLAY_SOFT),
        ("UI session", "ui, PR #22\nexporters, chat page,\nartifact publishes", MOSS_SOFT),
        ("Watcher session", "status checks, rubric\nand scope drift, rulings\non refresh discrepancies", SAND),
    ]
    y = 0.95
    xs, bh = row(ax, y, items, bw=bw, gap=gap, arrows=False)
    left, right = xs[0], xs[-1] + bw
    hw = (right - left - 0.3) / 2
    hy, hh = 2.05, 0.56
    box(ax, left, hy, hw, hh, "Parker", "company read, findings judgment, Part 2 content, deck", fill=PAPER, edge=CLAY)
    box(ax, left + hw + 0.3, hy, hw, hh, "Aidan", "API key, worktrees and PR chain, UI, demo, report, Devpost", fill=PAPER, edge=CLAY)
    for cx in (xs[0] + bw / 2, xs[1] + bw / 2):
        arrow(ax, left + hw / 2, hy, cx, y + bh, color=CLAY, lw=0.8)
    for cx in (xs[2] + bw / 2, xs[3] + bw / 2):
        arrow(ax, left + hw + 0.3 + hw / 2, hy, cx, y + bh, color=CLAY, lw=0.8)
    arrow(ax, xs[3] + bw / 2, y, xs[0] + bw / 2, y, color=MUTED, lw=0.7, style="<|-|>", rad=-0.16)
    label(ax, W / 2, 0.46, "cross-session messages: status, SHAs, data inventories, rulings")
    label(ax, W / 2, 0.2, "PR chain: main < scaffold #1 < gap-data #2 < corpus #5 < needle (Parker) < data-moat #16  |  quant-model #21 < ui #22", color=INK)
    save(f, ax, "fig3_team.png")


# 4. Part 1 pipeline --------------------------------------------------------
def part1_pipeline():
    f, ax = fig(3.5)
    bw, gap = 1.22, 0.15
    a_items = [
        ("10 blind readers", "one per company;\ncase, rubric, index;\n8 hiding places", SAND),
        ("20 skeptics", "round 1; materiality\nand math; obviousness;\ndefault to refuted", CLAY_SOFT),
        ("Round 2", "same agents resumed;\neach reads the other\nlens; concede or hold", CLAY_SOFT),
        ("10 synthesizers", "survived, narrowed\nor killed; no voting,\nno averaging", SAND),
        ("1 ranker", "picks 3 on the case's\ntest; seals selection\nwith sha256", MOSS_SOFT),
    ]
    b_items = [
        ("3 writers", "AMGN, MRK, PFE: five\nfindings, needle, product\ntable; every cell gated", SAND),
        ("Per-number gate", "261 cites and 503\nnumbers; fails closed", MOSS_SOFT),
        ("Verifier", "fresh context; assume\nevery number wrong;\n7 scoping defects", CLAY_SOFT),
        ("Priced-in, fixes", "evidence-graded call;\nseven fixes re-gated", SAND),
        ("UI exporter", "0 errors, 0 figures\nwithheld; cached", MOSS_SOFT),
    ]
    ya = 2.02
    xs, bha = row(ax, ya, a_items, bw=bw, gap=gap)
    x0 = xs[0]
    label(ax, x0, ya + bha + 0.1, "Phase A, 45 minutes wall clock", ha="left", va="bottom", color=CLAY, weight="bold")
    yb = 0.48
    xb, bhb = row(ax, yb, b_items, bw=bw, gap=gap)
    label(ax, x0, yb + bhb + 0.1, "Phase B, after the seal", ha="left", va="bottom", color=CLAY, weight="bold")
    ex = xs[4] + bw / 2
    ey = ya - 0.14
    ax.plot([ex, ex, x0 - 0.1, x0 - 0.1], [ya, ey, ey, yb + bhb / 2], color=MUTED, lw=0.9)
    arrow(ax, x0 - 0.1, yb + bhb / 2, x0, yb + bhb / 2, color=MUTED, lw=0.9)
    label(ax, x0 + 0.1, ey - 0.07, "95 candidates in; 70 killed, 25 narrowed, 0 survived as stated. The usual kill: management already said it.", ha="left", va="top", color=INK)
    label(ax, W / 2, 0.26, "Phase A agents may not open any prior run, league table, nugget file or other worktree.\nThe seal is checked by recomputing the hash.", va="top")
    save(f, ax, "fig4_part1.png")


# 5. Part 2 pipeline --------------------------------------------------------
def part2_pipeline():
    f, ax = fig(2.5)
    bw, gap = 1.22, 0.15
    items = [
        ("3 strategists", "4 or more costed moves\nof 2 or more types from\nthe sealed Part 1 rows", SAND),
        ("6 skeptics", "round 1; CFO and math;\nDecider and compliance;\ndefault to kill", CLAY_SOFT),
        ("Round 2", "resumed; read the other\nlens against the cited\npages; concede or hold", CLAY_SOFT),
        ("3 synthesizers", "ONE move, two rejected,\nkill signals, decider\nevidence, promo rules", SAND),
        ("Gate and exporter", "every block passed or\nno numbers; drivers tie\nto Part 1 findings", MOSS_SOFT),
    ]
    y = 1.35
    xs, bh = row(ax, y, items, bw=bw, gap=gap)
    sw, sh = 4.4, 0.76
    sx = xs[0] + ((xs[3] + bw) - xs[0] - sw) / 2
    box(ax, sx, 0.2, sw, sh, "Scraper data wave, mid-run", "labels, head-to-head, CMS, IRA, deal comps, 325 filing-number anchors;\nfiles not yet on disk stay [assumption]", fill=SLATE_SOFT)
    arrow(ax, sx + sw * 0.25, 0.2 + sh, xs[0] + bw / 2, y, color=MUTED, lw=0.8)
    arrow(ax, sx + sw * 0.75, 0.2 + sh, xs[3] + bw / 2, y, color=MUTED, lw=0.8)
    label(ax, xs[4] + bw / 2, 0.2 + sh / 2, "13 candidates\n9 killed, 4 narrowed\n0 survived as stated", color=INK)
    save(f, ax, "fig5_part2.png")


# 6. The gate ---------------------------------------------------------------
def gate_flow():
    f, ax = fig(2.5)
    bw, gap, bh = 1.56, 0.153, 0.6
    q = [
        ("Is it inside the quoted\nspan, or the citation's\nown value?", "verified"),
        ("Does a formula over\ncited operands\nrecompute it?", "derived"),
        ("Does it carry a printed\n[assumption] label?", "assumed"),
    ]
    y = 1.5
    x = 0
    for i, (t, res) in enumerate(q):
        box(ax, x, y, bw, bh, t, fill=SAND, bold=False, tsize=7.2)
        box(ax, x + 0.18, y - 0.66, bw - 0.36, 0.36, res, fill=MOSS_SOFT, tsize=7.6)
        arrow(ax, x + bw / 2, y, x + bw / 2, y - 0.3, color=MOSS, lw=0.9)
        label(ax, x + bw / 2 + 0.1, y - 0.15, "yes", color=MOSS, ha="left")
        arrow(ax, x + bw, y + bh / 2, x + bw + gap, y + bh / 2)
        label(ax, x + bw + gap / 2, y + bh / 2 + 0.1, "no", va="bottom")
        x += bw + gap
    box(ax, x, y, bw, bh, "Unsupported", "withheld and logged,\nnever shown with a guess", fill=CLAY_SOFT, edge=CLAY)
    box(ax, 0, 0.1, W, 0.6, "Then a person reads the page", "The gate proves a number is on the cited page. It cannot tell whether the page means what the sentence says.\nAn independent verifier and a human read do that.", fill=PAPER, edge=CLAY)
    save(f, ax, "fig6_gate.png")


# 7. Timeline ---------------------------------------------------------------
def timeline():
    f, ax = fig(1.5)
    y = 0.85
    pts = [
        ("Fri Oct 16", "scaffold, collectors,\nParker handoff"),
        ("Sat 9:00 am", "case released;\nshortlist of ten"),
        ("Sat afternoon", "data moat waves;\nnugget miner, red team"),
        ("Sat 10:27 pm", "blind Part 1 pass;\nseal at 11:12 pm"),
        ("Sun 12:05 am", "Part 2 waves; UI\nexports and publishes"),
        ("Sun 2:00 pm", "Devpost\nsubmission"),
    ]
    step = 1.14
    x0 = 0.75
    ax.plot([x0 - 0.3, x0 + 5 * step + 0.3], [y, y], color=LINE, lw=1.2)
    for i, (t, s) in enumerate(pts):
        x = x0 + i * step
        ax.plot([x], [y], marker="o", markersize=5.5, color=CLAY if i >= 3 else SLATE, markeredgecolor=PAPER, zorder=3)
        label(ax, x, y + 0.2, t, size=7.4, color=INK, weight="bold", va="baseline")
        label(ax, x, y - 0.2, s, va="top")
    save(f, ax, "fig7_timeline.png")


if __name__ == "__main__":
    system_overview()
    document_path()
    team_split()
    part1_pipeline()
    part2_pipeline()
    gate_flow()
    timeline()
    print("ok")
