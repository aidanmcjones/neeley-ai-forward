"""Cross-source check of earnings-call transcripts: align two independent copies and measure agreement on executive speech.

Writes data/moat/verified/calls/cross_source.csv and cross_source_diffs.csv.
"""
import csv
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pymupdf

from agent.moat.calls_mb import parse as mb_parse
from agent.moat.calls_tables import classify, read_lseg, read_turns, split_header
from agent.moat.common import ROOT

V = ROOT / "data" / "moat" / "verified" / "calls"
SRC = V / "src"
RAW = Path("/tmp/gd/raw")
CORP = ROOT / "data" / "corpus" / "companies"
MOAT = ROOT / "data" / "moat" / "companies"
FILL = {"uh", "um", "er", "ah", "erm", "uhm", "mm", "hmm"}
NEG = re.compile(r"(n't|^not$|^no$|^never$|^without$|^cannot$|^none$|^nor$)", re.I)
NUMW = re.compile(r"\d|^(million|billion|percent|percentage|basis|points|one|two|three|four|five|six|seven|eight|nine|ten|"
                  r"twenty|thirty|forty|fifty|hundred|thousand|half|double|first|second|third|fourth|q[1-4])$", re.I)


def pdf_lines(p):
    d = pymupdf.open(p)
    out = []
    for i, pg in enumerate(d):
        for l in pg.get_text().split("\n"):
            if l.strip():
                out.append((i + 1, l.strip()))
    return out


def load(kind, path):
    """Return list of turns with name, kind, text."""
    if kind == "lseg_pdf":
        turns = read_lseg(pdf_lines(path))
        for t in turns:
            t["kind"] = "operator" if t["name"] == "Operator" else ("analyst" if re.search(r"Analyst|Research", t["role"]) else "executive")
    elif kind == "mb_html":
        turns = mb_parse(Path(path).read_text(errors="replace"))
    else:
        head, body = split_header(Path(path).read_text(errors="replace"))
        turns, _ = read_turns(body, head)
        classify(turns)
    turns = [t for t in turns if t.get("text")]
    if len(turns) < 5 and kind == "file":
        head, body = split_header(Path(path).read_text(errors="replace"))
        body = re.sub(r"Speaker #\d+ :", " ", re.sub(r"\[\[page[^\]]*\]\]", " ", body))
        turns = [{"name": "?", "kind": "", "text": body}]
    return turns


JUNK = re.compile(r"(REFINITIV|LSEG) STREETEVENTS.*?affiliated companies\.|(REFINITIV|LSEG) STREETEVENTS[^.]*", re.S)
ROMAN = {"ii": "2", "iii": "3", "iv": "4", "iib": "2 b", "iiib": "3 b"}
WORDN = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
         "ten": "10"}


def clean_text(s):
    return JUNK.sub(" ", s)


def toks(turns):
    """Parallel lists: original tokens, normalized tokens, speaker kind, speaker name."""
    o, n, k, s = [], [], [], []
    for t in turns:
        for w in clean_text(t["text"]).split():
            base = w.lower().replace("’", "'").replace("'", "")
            base = re.sub(r"(?<=\d),(?=\d)", "", base)
            if re.match(r"^['’]\d\d\b", w):
                base = "20" + base
            base = base.replace("multibillion", "multi billion").replace("multimillion", "multi million")
            parts = re.split(r"[-/–]", base)
            for p in parts:
                p = re.sub(r"[^\w%.]", "", p).strip(".")
                p = re.sub(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)", " ", p)
                for nw in p.split():
                    if w.strip(".,;:")[:3].isupper() or w[:2] in ("II", "IV"):
                        nw = ROMAN.get(nw, nw)
                    if nw == "i" and n and n[-1] == "phase":
                        nw = "1"
                    nw = WORDN.get(nw, nw)
                    for x in nw.split():
                        if not x or x in FILL:
                            continue
                        o.append(w)
                        n.append(x)
                        k.append(t.get("kind", ""))
                        s.append(t["name"])
    return o, n, k, s


def sents(turns, kind="executive"):
    out = []
    for t in turns:
        if t.get("kind") != kind:
            continue
        for s in re.split(r"(?<=[.?!])\s+", t["text"]):
            if len(s.split()) >= 8:
                out.append((t["name"], s.strip()))
    return out


def squash(s):
    s = re.sub(r"\b(uh|um|er|ah)\b", "", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def substantive(a, b):
    """Why a differing span matters for a quote: number, negation or name."""
    why = []
    seg = a + b
    if any(NUMW.search(w) for w in seg) and [w for w in a if NUMW.search(w)] != [w for w in b if NUMW.search(w)]:
        why.append("number")
    if any(NEG.search(w) for w in a) != any(NEG.search(w) for w in b):
        why.append("negation")
    ca = {w.strip(".,;:?!\"'") for w in a if w[:1].isupper()}
    cb = {w.strip(".,;:?!\"'") for w in b if w[:1].isupper()}
    if (ca - cb or cb - ca) and len(" ".join(a + b)) > 3 and any(len(x) > 3 for x in (ca ^ cb)):
        why.append("name")
    return why


def compare(ref, oth, spaceless=False):
    rs = sents(ref)
    big = squash(" ".join(t["text"] for t in oth))
    hit = sum(1 for _, s in rs if squash(s) in big)
    res = {"ref_exec_sentences": len(rs), "exact_sentence_match_pct": round(100 * hit / max(1, len(rs)), 1)}
    diffs = []
    if spaceless:
        # reference is the clean copy; check each sentence of it inside the spaceless official
        res["exec_word_agreement_pct"] = ""
        for name, s in rs:
            if squash(s) not in big:
                diffs.append({"speaker": name, "why": "not found verbatim", "ref": s, "other": ""})
        return res, diffs
    ro, rn, rk, rsn = toks(ref)
    oo, on, _, _ = toks(oth)
    sm = SequenceMatcher(None, rn, on, autojunk=False)
    ex_tot = sum(1 for x in rk if x == "executive")
    ex_match = 0
    for a, b, size in sm.get_matching_blocks():
        ex_match += sum(1 for x in rk[a:a + size] if x == "executive")
    res["exec_word_agreement_pct"] = round(100 * ex_match / max(1, ex_tot), 1)
    res["all_word_agreement_pct"] = round(100 * sum(b.size for b in sm.get_matching_blocks()) / max(1, len(rn)), 1)
    big_blocks = [b for b in sm.get_matching_blocks() if b.size >= 20]
    if big_blocks:
        lo, hi = big_blocks[0].a, big_blocks[-1].a + big_blocks[-1].size
        tot = sum(1 for x in rk[lo:hi] if x == "executive")
        mt = sum(sum(1 for x in rk[b.a:b.a + b.size] if x == "executive") for b in sm.get_matching_blocks() if lo <= b.a < hi)
        res["overlap_exec_agreement_pct"] = round(100 * mt / max(1, tot), 1)
        res["coverage_of_a_pct"] = round(100 * (hi - lo) / max(1, len(rn)), 1)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (i2 - i1) > 60 or (j2 - j1) > 60:
            continue
        if not any(x == "executive" for x in rk[i1:max(i2, i1 + 1)]):
            continue
        from agent.moat.verify.c_sub import substantive as sub2, uniq
        ao, bo = uniq(ro[i1:i2]), uniq(oo[j1:j2])
        why = sub2(rn[i1:i2], on[j1:j2], ao, bo, ro[i1 - 1] if i1 else "", oo[j1 - 1] if j1 else "")
        if not why:
            continue
        ctx_a = " ".join(uniq(ro[max(0, i1 - 12):i2 + 12]))
        ctx_b = " ".join(uniq(oo[max(0, j1 - 12):j2 + 12]))
        diffs.append({"speaker": rsn[i1] if i1 < len(rsn) else "", "why": "+".join(why),
                      "ref": ctx_a, "other": ctx_b, "ref_span": " ".join(ao), "other_span": " ".join(bo)})
    return res, diffs


def c(t, q):
    return CORP / t / "transcripts" / f"{q}_transcript.md"


def m(t, q):
    return MOAT / t / "transcripts" / f"{q}_transcript.md"


PAIRS = []
for t in ("MRK", "PFE", "JNJ"):  # official LSEG (corpus) vs MarketBeat/Quartr
    PAIRS.append((t, "2025Q3", ("official LSEG (corpus)", "file", c(t, "2025Q3")), ("MarketBeat/Quartr", "mb_html", RAW / f"{t}_2025Q3.html")))
PAIRS.append(("MRK", "2025Q2", ("official LSEG PDF (merck.com)", "lseg_pdf", SRC / "MRK_2025Q2_official.pdf"), ("moat MarketBeat/Quartr", "file", m("MRK", "2025Q2"))))
for q in ("2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"):
    PAIRS.append(("PFE", q, ("official LSEG PDF (pfizer q4cdn)", "lseg_pdf", SRC / f"PFE_{q}_official.pdf"), ("moat third-party", "file", m("PFE", q))))
for q in ("2024Q3", "2025Q2"):
    PAIRS.append(("JNJ", q, ("official LSEG PDF (jnj q4cdn)", "lseg_pdf", SRC / f"JNJ_{q}_official.pdf"), ("moat MarketBeat/Quartr", "file", m("JNJ", q))))
for t in ("ABBV", "AMGN", "BMY", "LLY", "NVO"):
    PAIRS.append((t, "2025Q3", ("corpus third-party", "file", c(t, "2025Q3")), ("MarketBeat/Quartr", "mb_html", RAW / f"{t}_2025Q3.html")))
for t, q in (("AZN", "2025Q3"), ("AZN", "2026Q1"), ("GILD", "2025Q3")):
    PAIRS.append((t, q, ("moat MarketBeat/Quartr", "file", m(t, q)), ("corpus third-party (superseded)", "file", c(t, q))))


def src_url(path):
    p = Path(path)
    if p.suffix == ".md":
        m_ = re.search(r"source:\s*(\S+)", p.read_text(errors="replace")[:600])
        return m_.group(1) if m_ else ""
    return p.name


def main():
    only = sys.argv[1:]
    V.mkdir(parents=True, exist_ok=True)
    rows, drows = [], []
    for t, q, (an, ak, ap), (bn, bk, bp) in PAIRS:
        if only and t not in only:
            continue
        if not Path(ap).exists() or not Path(bp).exists():
            print("missing", t, q, ap, bp)
            continue
        A, B = load(ak, ap), load(bk, bp)
        res, diffs = compare(A, B)
        notable = diffs[:4]
        row = {"ticker": t, "quarter": q, "source_a": f"{an}: {src_url(ap)}", "source_b": f"{bn}: {src_url(bp)}",
               "turns_a": len(A), "turns_b": len(B), **res, "n_substantive_diffs": len(diffs),
               "notable_differences": " || ".join(f"[{d['why']}] {d['speaker']}: A='{d['ref_span']}' B='{d['other_span']}'" for d in notable)}
        rows.append(row)
        for d in diffs:
            drows.append({"ticker": t, "quarter": q, "source_a": an, "source_b": bn, **d})
        print(t, q, res, len(diffs), flush=True)
    # JNJ 2026Q2: clean MarketBeat copy vs spaceless official LSEG text
    if not only or "JNJ" in only:
        A = load("mb_html", SRC / "JNJ_2026Q2_mb.html")
        B = load("lseg_pdf", SRC / "JNJ_2026Q2_official.pdf")
        res, diffs = compare(A, B, spaceless=True)
        rows.append({"ticker": "JNJ", "quarter": "2026Q2", "source_a": "MarketBeat/Quartr: JNJ_2026Q2_mb.html",
                     "source_b": "official LSEG PDF (spaces lost; compared with spaces stripped)", "turns_a": len(A),
                     "turns_b": len(B), **res, "n_substantive_diffs": len(diffs),
                     "notable_differences": " || ".join(f"{d['speaker']}: '{d['ref'][:160]}'" for d in diffs[:3])})
        for d in diffs:
            drows.append({"ticker": "JNJ", "quarter": "2026Q2", "source_a": "MarketBeat", "source_b": "official LSEG", **d})
        print("JNJ 2026Q2", res, len(diffs))
    cols = ["ticker", "quarter", "source_a", "source_b", "turns_a", "turns_b", "ref_exec_sentences", "exec_word_agreement_pct",
            "all_word_agreement_pct", "overlap_exec_agreement_pct", "coverage_of_a_pct", "exact_sentence_match_pct", "n_substantive_diffs", "notable_differences"]
    with (V / "cross_source.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    dc = ["ticker", "quarter", "source_a", "source_b", "speaker", "why", "ref_span", "other_span", "ref", "other"]
    with (V / "cross_source_diffs.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, dc, extrasaction="ignore")
        w.writeheader()
        w.writerows(drows)


if __name__ == "__main__":
    main()
