"""Build tables/transcripts_index.csv and tables/qa_turns.csv over corpus + moat transcripts."""
import csv
import re
from collections import Counter
from pathlib import Path

from agent.moat.calls_gen import FIRM_HINT, OWN_HINT, parse_lines
from agent.moat.common import ROOT, write

CORPUS = ROOT / "data" / "corpus" / "companies"
MOAT = ROOT / "data" / "moat" / "companies"
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
PAGE = re.compile(r"^\[\[page (\d+) \| printed ([^\]]+)\]\]")
SPEAK_MD = re.compile(r"^\*\*(.+?)(?: \((.*)\))?:\*\* (.*)$")
FOOL = re.compile(r"^([A-Z][A-Za-z.'’\- ]{1,40}|Unknown Analyst): (.*)$")
QINTRO = re.compile(r"(?:from|of|line of)\s+(?:the line of\s+)?([A-Z][\w.'’\-]+(?: [A-Z][\w.'’\-]+){0,3}),?\s+(?:from|with|of|at|over at)\s+([A-Z][\w&.,'’\- ]{2,50}?)(?:[.,]| Please| Your|$)")


def split_header(raw):
    m = re.match(r"\s*<!--(.*?)-->", raw, re.S)
    head = m.group(1) if m else ""
    return head, raw[m.end():] if m else raw


def hmeta(head):
    src = re.search(r"source:\s*(\S+)", head)
    q = re.search(r"quality:\s*(\w+)", head)
    cd = re.search(r"call_date=(\d{4}-\d\d-\d\d)", head)
    return (src.group(1) if src else ""), (q.group(1) if q else ""), (cd.group(1) if cd else "")


def guess_date(url, body):
    m = re.search(r"EVENT DATE/TIME:\s*([A-Z]+) (\d+), (\d{4})", body[:3000])
    if m and m.group(1)[:3].lower() in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"_(\d{4}-\d\d-\d\d)\.pdf", url)
    if m:
        return m.group(1)
    m = re.search(r"/(\d{4})/(\d\d)/(\d\d)/", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2}), (20\d\d)", body[:6000])
    if m:
        return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return ""


def pages_text(body):
    """Yield (page, line) for non-empty lines."""
    page = 1
    for l in body.split("\n"):
        m = PAGE.match(l.strip())
        if m:
            page = int(m.group(1))
            continue
        if l.strip():
            yield page, l.strip()


def read_turns(body, url):
    """Return (turns, fmt). turn = dict(name, role, text, page)."""
    lines = list(pages_text(body))
    md = [x for x in lines if SPEAK_MD.match(x[1])]
    if len(md) > 20:
        turns = []
        for pg, l in lines:
            m = SPEAK_MD.match(l)
            if m:
                turns.append({"name": m.group(1), "role": m.group(2) or "", "text": m.group(3), "page": pg})
        return turns, "md"
    head = body[:1500]
    if "LSEG" in head or "EDITED TRANSCRIPT" in head or "_Transcript_" in url:
        return read_lseg(lines), "lseg"
    fool = [x for x in lines if FOOL.match(x[1])]
    if len(fool) > 25:
        return read_fool(lines), "fool"
    return read_labels(lines), "labels"


LSEG_JUNK = re.compile(r"(LSEG STREETEVENTS|©20\d\d LSEG|consent of LSEG|registered trademarks of LSEG|, [A-Z.]+ - Q\d 20\d\d .*Call$|^\d{1,3}$|^Contact Us$)")


def read_lseg(lines):
    start = next((i for i, (_, l) in enumerate(lines) if l in ("PRESENTATION",)), 0)
    turns, cur = [], None
    for pg, l in lines[start + 1:]:
        if LSEG_JUNK.search(l) or l in ("QUESTIONS AND ANSWERS", "DISCLAIMER"):
            continue
        parts = [p.strip() for p in l.split(" - ")]
        if len(parts) < 3 and re.search(r"-(Analyst|[^-]*(Officer|President|Chairman|Director|Relations|Executive|Head|Chief))$", l):
            alt = [p.strip() for p in re.split(r"(?<=[a-z.])-(?=[A-Z])", l)]
            if len(alt) >= 3:
                parts = alt
        is_sp = False
        if l == "Operator":
            is_sp, name, role = True, "Operator", ""
        elif 3 <= len(parts) <= 5 and len(parts[0].split()) <= 5 and parts[0][0].isupper() and not re.search(r"[.?!,]$", parts[0]) \
                and len(parts[-1].split()) <= 14 and len(l) < 160:
            is_sp, name, role = True, parts[0], " - ".join(parts[1:])
        if is_sp:
            cur = {"name": name, "role": role, "text": "", "page": pg}
            turns.append(cur)
        elif cur is not None:
            cur["text"] += (" " if cur["text"] else "") + l
    return turns


def read_fool(lines):
    st = 0
    for i, (_, l) in enumerate(lines):
        if re.search(r"full conference call transcript", l, re.I):
            st = i + 1
            break
    turns, cur = [], None
    for pg, l in lines[st:]:
        if re.match(r"^(Image source|Related|More |Our |\* ?)", l) and cur is None:
            continue
        m = FOOL.match(l)
        if m and len(m.group(1).split()) <= 4:
            cur = {"name": m.group(1), "role": "", "text": m.group(2), "page": pg}
            turns.append(cur)
        elif cur is not None:
            if re.match(r"^(This article is a transcript|Where to invest|Before you buy|Stock Advisor)", l):
                break
            cur["text"] += " " + l
    return turns


INLINE = re.compile(r"Analyst \(([^)]+)\)\. |(?:^|\n)([A-Z][a-z]+(?: [A-Z][a-z]?\.?)? [A-Z][a-zA-Z']+)\. (?=[A-Z])")


def read_inline(lines):
    """ABBV 2026Q2 style: 'Analyst (Name). question' and 'First Last. answer' at line start."""
    st = next((i for i, (_, l) in enumerate(lines) if "star 1 if you have a question" in l), None)
    if st is None:
        return []
    text = "\n".join(l for _, l in lines[st:])
    turns, last, cur = [], 0, None
    for m in INLINE.finditer(text):
        if cur is not None:
            cur["text"] = text[last:m.start()].replace("\n", " ").strip()
        name = m.group(1) or m.group(2)
        cur = {"name": name, "role": "Analyst" if m.group(1) else "", "text": "", "page": 1}
        turns.append(cur)
        last = m.end()
    if cur is not None:
        cur["text"] = text[last:].replace("\n", " ").strip()
    pre = {"name": "Operator", "role": "", "text": "question star 1 first question", "page": 1}
    return [pre] + turns


def read_labels(lines):
    if any("Analyst (" in l and re.search(r"Analyst \([A-Z]", l) for _, l in lines[:2000]):
        t = read_inline(lines)
        if t:
            return t
    try:
        turns = parse_lines([l for _, l in lines])
    except Exception:
        return []
    for t in turns:
        t["page"] = 1
    return turns


OPLIKE = re.compile(r"press (star|\*)|question (comes|is coming|will come) from|your line is open|(first|next) question|Operator Instructions|go ahead", re.I)


def classify(turns):
    qa = None
    for i, t in enumerate(turns):
        if t["name"] == "Operator" or (len(t["text"]) < 400 and OPLIKE.search(t["text"])):
            t["kind"] = "operator"
            if qa is None and i > 0 and re.search(r"question|Instructions", t["text"], re.I):
                qa = i
    if qa is None:
        qa = next((i for i, t in enumerate(turns) if re.search(r"\bAnalyst\b", t["role"]) or t["name"].startswith("Unknown Analyst")), None)
    pre = {t["name"] for t in turns[: qa if qa is not None else 0]}
    firms = Counter()
    for t in turns:
        if " at " in t["role"] and t["name"] != "Operator":
            firms[t["role"].rsplit(" at ", 1)[1].strip()] += 1
        elif t["role"].count(" - ") >= 1 and t["name"] != "Operator":
            firms[t["role"].split(" - ")[0].strip()] += 1
    own = firms.most_common(1)[0][0] if firms else ""
    for t in turns:
        r = t["role"]
        if t.get("kind"):
            continue
        firm = ""
        if " - " in r:
            firm = r.split(" - ")[0].strip()
        elif " at " in r:
            firm = r.rsplit(" at ", 1)[1].strip()
        if t["name"] == "Operator" or t.get("kind") == "operator":
            k = "operator"
        elif re.search(r"\bAnalyst\b", r) or t["name"].startswith("Unknown Analyst"):
            k = "analyst"
        elif t["name"] in pre:
            k = "executive"
        elif firm and firm == own:
            k = "executive"
        elif firm:
            k = "analyst"
        elif r and OWN_HINT.search(r) and not FIRM_HINT.search(r):
            k = "executive"
        else:
            k = "analyst"
        t["kind"] = k
    return qa


def firm_map(turns):
    m = {}
    for t in turns:
        if t["name"] == "Operator":
            for mm in QINTRO.finditer(t["text"]):
                m.setdefault(mm.group(1).strip().lower(), mm.group(2).strip())
    return m


def process(path, base):
    raw = path.read_text(errors="replace")
    head, body = split_header(raw)
    url, qual, cdate = hmeta(head)
    if not qual:
        qual = "official" if re.search(r"merck\.com|q4cdn|\.pdf", url) else "third_party"
    cdate = cdate or guess_date(url, body)
    if (path.parent.parent.name, path.name.split("_")[0]) == ("LLY", "2026Q2"):
        cdate = "2026-08-05"
    turns, fmt = read_turns(body, url)
    qa = classify(turns)
    turns = [t for t in turns if t["text"].strip() or t["name"] == "Operator"]
    qa = classify(turns) if qa is None or True else qa
    fm = firm_map(turns)
    named = [t for t in turns if t["name"] != "Operator" and not t["name"].startswith("Unknown") and not re.match(r"^Speaker \d", t["name"])]
    has_names = len(named) >= 10
    rel = path.relative_to(ROOT)
    tk, q = path.parent.parent.name, path.name.split("_")[0]
    rows = []
    if qa is not None:
        for t in turns[qa:]:
            if t["kind"] not in ("analyst", "executive"):
                continue
            firm = ""
            r = t["role"]
            if t["kind"] == "analyst":
                if " - " in r:
                    firm = r.split(" - ")[1] if r.count(" - ") >= 1 and len(r.split(" - ")) > 1 else ""
                elif " at " in r:
                    firm = r.rsplit(" at ", 1)[1].strip()
                elif r and FIRM_HINT.search(r):
                    firm = r
                if not firm:
                    firm = fm.get(t["name"].lower(), "")
            elif " at " in r:
                firm = r.rsplit(" at ", 1)[1].strip()
            elif " - " in r:
                firm = r.split(" - ")[0].strip()
            rows.append({"ticker": tk, "quarter": q, "speaker": t["name"], "role": t["kind"], "firm": firm,
                         "text": t["text"].strip(), "path": str(rel), "page": t["page"]})
    idx = {"ticker": tk, "quarter": q, "call_date": cdate, "source_quality": qual, "source_url": url,
           "has_speaker_names": str(has_names).lower(), "has_qa": str(bool(rows)).lower(), "chars": len(raw),
           "path": str(rel), "format": fmt, "n_qa_turns": len(rows)}
    return idx, rows


def main():
    idx, qrows = {}, []
    for base in (CORPUS, MOAT):
        for p in sorted(base.glob("*/transcripts/*_transcript.md")):
            tk, q = p.parent.parent.name, p.name.split("_")[0]
            row, rows = process(p, base)
            key = (tk, q)
            if key in idx and base is MOAT:
                row["supersedes"] = idx[key]["path"]
                qrows = [r for r in qrows if not (r["ticker"] == tk and r["quarter"] == q)]
            idx[key] = row
            qrows.extend(rows)
    cols = ["ticker", "quarter", "call_date", "source_quality", "source_url", "has_speaker_names", "has_qa", "chars", "path",
            "format", "n_qa_turns", "supersedes"]
    out = sorted(idx.values(), key=lambda r: (r["ticker"], r["quarter"]))
    tdir = ROOT / "tables"
    tdir.mkdir(exist_ok=True)
    with (tdir / "transcripts_index.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    qcols = ["ticker", "quarter", "speaker", "role", "firm", "text", "path", "page"]
    qrows.sort(key=lambda r: (r["ticker"], r["quarter"]))
    with (tdir / "qa_turns.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, qcols)
        w.writeheader()
        w.writerows(qrows)
    print("index", len(out), "qa", len(qrows))
    for r in out:
        print(r["ticker"], r["quarter"], r["call_date"], r["source_quality"], r["format"], r["has_speaker_names"], r["has_qa"], r["n_qa_turns"])


if __name__ == "__main__":
    main()
