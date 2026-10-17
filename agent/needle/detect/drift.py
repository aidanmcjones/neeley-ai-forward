"""Language drift: FY2025 vs FY2024 annual report wording in risk factors and MD&A.

Deterministic, no network. Paragraphs are matched within a section by word-set Jaccard; unmatched or
changed paragraphs become added / removed / intensified / modified signals, scored and capped at 40 per ticker.
"""

import re

from agent.needle import pages
from agent.needle.detect import cli
from agent.needle.schema import Evidence, Signal

TOPICS = {
    "ira": r"Inflation Reduction Act|negotiat|maximum fair price",
    "mfn": r"most favored|\bMFN\b",
    "tariff": r"tariff",
    "gtn": r"gross-to-net|rebate|chargeback|discount",
    "340b": r"340B",
    "generic": r"generic|biosimilar|exclusivity|patent|loss of exclusivity",
    "litigation": r"litigation",
    "supply": r"supply|manufactur|shortage",
    "pricing": r"price|pricing",
    "china": r"china",
    "ai": r"\bAI\b|artificial intelligence",
}
TOPIC_RE = {k: re.compile(v, re.I if k not in ("340b", "ai", "mfn") else 0) for k, v in TOPICS.items()}
HEDGE = {"may", "could", "might", "potential", "potentially"}
CERTAIN = {"will", "is", "are", "has", "have"}
NUM_RE = re.compile(r"\$\s?\d[\d,.]*|\b\d[\d,.]*\s?%|\b\d[\d,]*(?:\.\d+)?\b")
WORD_RE = re.compile(r"[a-z0-9]+")
MAX_PER_TICKER = 40


def _section_of(block, cur, f20=False):
    """Return the new section if this short block is a heading, else cur."""
    b = block.strip().lstrip("#*| ").strip()
    if len(b.split()) > 14:
        return cur
    low = b.lower()
    m = re.match(r"item\s*(\d+[abc]?)\b", low)
    if m:
        it = m.group(1)
        if it == "1a":
            return "risk"
        if it == "7" and not f20:  # in a 20-F, Item 7 is major shareholders
            return "mdna"
        if it == "5" and f20:
            return "mdna"
        return "other"
    if re.match(r"d\.\s*risk factors", low):
        return "risk"
    if re.match(r"(risk factors|management.s discussion and analysis)", low):
        return "risk" if low.startswith("risk") else "mdna"
    return cur


GLOSSY_RISK = re.compile(r"^(principal )?risks?( management| factors| overview)?( \(continued\))?$|^risk management", re.I)
GLOSSY_MDNA = re.compile(r"^(financial review|operating review|financial performance|strategic report|business review)", re.I)
GLOSSY_END = re.compile(r"^(corporate governance|governance|financial statements|consolidated financial statements|"
                        r"notes to |section \d|note \d|consolidated |financial statements|sustainability statement|remuneration|directors.? report|shareholder information|sustainability statements?)", re.I)


GLOSSY_HEAD = re.compile(GLOSSY_RISK.pattern + "|" + GLOSSY_MDNA.pattern + "|" + GLOSSY_END.pattern, re.I)


def _glossy_section(block, cur):
    b = block.strip().lstrip("#*| ").strip()
    if len(b.split()) > 8:
        return cur
    if GLOSSY_RISK.match(b):
        return "risk"
    if GLOSSY_MDNA.match(b):
        return "mdna"
    if GLOSSY_END.match(b):
        return "other"
    return cur


def _annual(ticker):
    ds = pages.docs(ticker)
    gl = {}
    for did, d in ds.items():
        if d["row"].get("doc_type") == "annual_report_glossy":
            m = re.search(r"(2024|2025)", str(d["row"].get("period", "")) + did)
            if m:
                gl[m.group(1)] = did
    best = {}
    for did, d in ds.items():
        if d["row"].get("doc_type") != "annual_report":
            continue
        yr = str(d["row"].get("period", ""))[:4]
        if yr in ("2024", "2025") and (yr not in best or len(d["flat"]) > len(ds[best[yr]]["flat"])):
            best[yr] = did
    if "2025" in gl and "2024" in gl:
        return ds, gl["2025"], gl["2024"], best.get("2025"), best.get("2024")
    return ds, best.get("2025"), best.get("2024"), None, None


def _paras(doc, glossy=False):
    """[(page, paragraph, section)] for risk and mdna paragraphs only."""
    out, cur, last_head = [], "other", -99
    f20 = "20f_" in doc.get("id", "")
    sec_fn = (lambda b, c: _glossy_section(b, c)) if glossy else (lambda b, c: _section_of(b, c, f20))
    for pg in sorted(doc["pages"]):
        text = doc["pages"][pg][1]
        if glossy:   # PDF text: headings sit on their own line inside the block
            buf = []
            if cur != "other" and pg - last_head > 8:   # section headings are not repeated: stop after 8 pages
                cur = "other"

            def flush():
                if buf:
                    for p in pages.paragraphs("\n".join(buf), 15):
                        if cur in ("risk", "mdna"):
                            out.append((pg, p, cur))
                    buf.clear()

            for line in text.split("\n"):
                new = _glossy_section(line, cur)
                if new in ("risk", "mdna") and GLOSSY_HEAD.match(line.strip().lstrip("#*| ")):
                    last_head = pg
                if new != cur or not line.strip():
                    flush()
                    cur = new
                if line.strip() and not (len(line.split()) <= 8 and GLOSSY_HEAD.match(line.strip())):
                    buf.append(line)
            flush()
            continue
        for block in re.split(r"\n\s*\n", text):
            cur = sec_fn(block, cur)
            for p in pages.paragraphs(block, 15):
                if cur in ("risk", "mdna"):
                    out.append((pg, p, cur))
    return out


def _words(p):
    return frozenset(WORD_RE.findall(p.lower()))


def _jac(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def _topics(p):
    return [k for k, r in TOPIC_RE.items() if r.search(p)]


def _nums(p):
    return set(NUM_RE.findall(p))


def _quote(p):
    w = p.split()
    return " ".join(w[:40]) if len(w) > 40 else p


def _describe(kind, sec, topics, extra="", p=""):
    s = {"risk": "risk factors", "mdna": "MD&A"}[sec]
    verb = {"added": "new paragraph in", "removed": "paragraph dropped from", "intensified": "stronger wording in",
            "modified": "reworded paragraph in"}[kind]
    t = f" (topics: {', '.join(topics)})" if topics else ""
    w = p.split()
    gist = f": '{' '.join(w[:18])}{'...' if len(w) > 18 else ''}'" if w else ""  # say what the paragraph says
    return f"{verb.capitalize()} {s} vs FY2024{t}{extra}{gist}"


def _cand(kind, sec, pg, p, sim, old=None, oldpg=None, extra=""):
    return dict(kind=kind, sec=sec, pg=pg, p=p, topics=_topics(p), num=bool(_nums(p)), sim=sim,
                old=old, oldpg=oldpg, extra=extra)


def run(ticker):
    ticker = ticker.upper()
    ds, id25, id24, f25, f24 = _annual(ticker)
    sigs = []
    if f25 and f24:   # glossy PDFs preferred; SEC 20-F is the fallback
        sigs = _compare(ticker, ds, id25, id24, True)
        id25, id24 = f25, f24
    if len(sigs) < 5 and id25 and id24:
        sigs = _compare(ticker, ds, id25, id24, False) or sigs
    return sigs


RISK_VOCAB = re.compile(r"material adverse|significant|substantial|impairment|decline", re.I)


def _compare(ticker, ds, id25, id24, glossy):
    p25, p24 = _paras({**ds[id25], "id": id25}, glossy), _paras({**ds[id24], "id": id24}, glossy)
    w25 = [_words(p) for _, p, _ in p25]
    w24 = [_words(p) for _, p, _ in p24]
    cands = []
    used24 = set()          # FY24 paragraphs that are the best match (>= 0.45) of some FY25 paragraph
    for i, (pg, p, sec) in enumerate(p25):
        best, bj = -1.0, -1
        for j, (_, _, s2) in enumerate(p24):
            if s2 != sec:
                continue
            sc = _jac(w25[i], w24[j])
            if sc > best:
                best, bj = sc, j
        if best >= 0.45:
            used24.add(bj)
        if best >= 0.85:
            continue
        if best >= 0.45:
            old = p24[bj][1]
            nw, ow = set(WORD_RE.findall(p.lower())), set(WORD_RE.findall(old.lower()))
            hedge_rm = (HEDGE & ow) - nw
            cert_add = (CERTAIN & nw) - ow
            new_nums = _nums(p) - _nums(old)
            old_topics = _topics(old)
            new_topics = [t for t in _topics(p) if t not in old_topics]
            vocab_new = sorted({m.lower() for m in RISK_VOCAB.findall(p)} - {m.lower() for m in RISK_VOCAB.findall(old)})
            nn = lambda ws: {w for w in ws if not w.isdigit()}
            if len(nn(nw) ^ nn(ow)) < 4 and not hedge_rm and not vocab_new:
                continue  # routine update: only numbers, years or percentages changed
            intens = bool(hedge_rm) or bool(vocab_new)
            bits = []
            if hedge_rm:
                bits.append(f"hedges dropped: {', '.join(sorted(hedge_rm))}")
            if hedge_rm and cert_add:
                bits.append(f"certainty added: {', '.join(sorted(cert_add))}")
            if vocab_new:
                bits.append(f"new risk vocabulary: {', '.join(vocab_new)}")
            if new_nums:
                bits.append(f"new figures: {', '.join(sorted(new_nums)[:4])}")
            if new_topics:
                bits.append(f"new topics: {', '.join(new_topics)}")
            extra = "; " + "; ".join(bits) if bits else ""
            cands.append(_cand("intensified" if intens else "modified", sec, pg, p, best, old, p24[bj][0], extra))
        else:
            cands.append(_cand("added", sec, pg, p, best))
    for j, (pg, p, sec) in enumerate(p24):
        if j in used24:
            continue
        best = max((_jac(w24[j], w25[i]) for i in range(len(p25)) if p25[i][2] == sec), default=0.0)
        if best < 0.45:
            cands.append(_cand("removed", sec, pg, p, best))
    base = {"added": 3, "intensified": 3, "removed": 2, "modified": 1}
    for c in cands:
        c["score"] = base[c["kind"]] + len(c["topics"]) + (1 if c["num"] else 0)
    cands.sort(key=lambda c: (-c["score"], c["sec"], c["pg"]))

    sigs, dropped = [], 0
    for c in cands:
        if len(sigs) >= MAX_PER_TICKER:
            break
        if c["kind"] == "removed":
            evs = [Evidence(id24, c["pg"], _quote(c["p"]))]
        else:
            evs = [Evidence(id25, c["pg"], _quote(c["p"]))]
            if c["old"]:
                evs.append(Evidence(id24, c["oldpg"], _quote(c["old"])))
        for e in evs:
            if "�" in e.quote:
                orig = e.quote
                e.quote = " ".join(orig.replace("�", "").split())
                if pages.check(e, ds)[0] != "verified":
                    e.quote = orig
        if any(pages.check(e, ds)[0] != "verified" for e in evs):
            dropped += 1
            continue
        sigs.append(Signal(
            ticker, "drift", f"{c['sec']}_{c['kind']}", "FY2025", float(c["score"]),
            detail=_describe(c["kind"], c["sec"], c["topics"], c["extra"], c["p"]), evidence=evs,
            meta={"section": c["sec"], "topics": c["topics"], "fy24_quote": _quote(c["old"]) if c["old"] else "",
                  "similarity": round(c["sim"], 3)}))
    print(f"{ticker}: drift candidates={len(cands)} emitted={len(sigs)} dropped_unverified={dropped}")
    return sigs


if __name__ == "__main__":
    cli("drift", run)
