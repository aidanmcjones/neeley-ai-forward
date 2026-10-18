"""Earnings-call Q&A with deflection and new-phrase flags, plus metrics a company stopped reporting.

Answers two questions from the case's "where findings hide" list:
  1. Which analyst questions did management dodge, which phrases are brand new this quarter, and which topics
     have analysts stopped asking about?  -> call_qa()
  2. Which product lines or key metrics appeared in earlier earnings releases but vanished from the latest two?
     -> dropped_metrics()

    from agent.moat.case_calls import call_qa, dropped_metrics
    call_qa("MRK", quarters=4)          # qa_pair, new_phrase and never_asked rows
    dropped_metrics("MRK", releases=6)  # dropped_metric rows

    call_qa(ticker, quarters=4, flags=("deflection", "new_phrase", "never_asked"), grade_min="C", k=80) -> [dict]
    dropped_metrics(ticker, releases=6) -> [dict]

CLI:  python -m agent.moat.case_calls MRK [--quarters 4] [--grade C] [-k 20] [--dropped] [--releases 6]

Data: citation index docs/pages/turns tables (transcripts, earnings_release, earnings_slides, quarterly_report),
data/moat/verified/calls/qa_turns.csv (analyst vs executive labels) and the indexed fact rows of
data/moat/verified/market/never_asked.csv. Every returned text passes cite.verify_quote on the cited page, or is
a verified table row cited by its facts.locator. Scores are heuristics, not findings.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from agent.findings import _norm
from agent.moat.cite import GRADE_ORDER, TRANSCRIPT_TYPES, cite, db, verify_quote

ROOT = Path(__file__).resolve().parents[2]
QA_CSV = ROOT / "data" / "moat" / "verified" / "calls" / "qa_turns.csv"
NEVER_TABLE = "market/never_asked.csv"
MAXTXT = 600

STOP = set("""a about above after again against all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her here
hers herself him himself his how i if in into is it its itself just let me more most my myself no nor not now of off on
once only or other our ours ourselves out over own same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up very was we were what when where which while
who whom why will with would you your yours yourself yourselves yeah okay ok thank thanks think going really kind sort
lot know get got see well good great question questions just maybe like want things thing way year years quarter
quarters able look looking make made said says say us one two three first second third next new also first-quarter
second-quarter third-quarter fourth-quarter please hi morning afternoon evening guys sure right""".split())
MONTHS = set("january february march april may june july august september october november december".split())
QUANT_WORDS = ["guidance", "how much", "what percent", "what percentage", "quantify", "timing", "when ", "how many",
               "magnitude", "size of", "how big", "range", "%", "basis points", "bps"]
DEFLECT = ["we don't break out", "we do not break out", "not going to comment", "won't comment", "not going to get into",
           "we're not providing", "we are not providing", "not providing guidance", "stay tuned", "as we've said",
           "as we have said", "as i said", "too early", "premature", "we'll update you", "we will update you",
           "update you", "i won't speculate", "won't speculate", "not going to speculate", "we don't guide",
           "we do not guide", "not in a position", "can't comment", "cannot comment", "don't want to get ahead",
           "not going to give", "we'll provide more", "more to come", "at the appropriate time", "in due course",
           "we haven't disclosed", "not disclosing"]
KEY_METRICS = ["gross-to-net", "gross to net", "new prescriptions", "nbrx", "trx", "market share", "patients on therapy",
               "patients treated", "ex-u.s.", "outside the u.s.", "international", "constant currency", "ex-fx",
               "operational growth", "volume growth", "price", "inventory", "wholesaler", "medicaid", "340b",
               "rebate", "royalty", "alliance revenue"]
NUM = re.compile(r"\d")


# ---------------------------------------------------------------- shared helpers

def _sentences(text):
    """Split prose into sentences, dropping markdown speaker headers."""
    text = re.sub(r"\*\*[^*\n]{1,160}?:\*\*", "\n", text or "")
    text = text.replace("**", " ")
    parts = re.split(r"(?<=[.!?])\s+(?=[\"'(A-Z0-9])|\n\s*\n", text)
    out = []
    for p in parts:
        p = " ".join(p.split())
        p = re.sub(r"^(?:[QA] - [^{}]{2,80}\{BIO \d+ <GO>\}\s*|Speaker #?\d+\s*:\s*)+", "", p)
        p = re.sub(r"\s*(?:[QA] - [^{}]{2,80}\{BIO \d+ <GO>\}|Speaker #?\d+\s*:).*$", "", p)
        if len(p.split()) >= 4:
            out.append(p)
    return out


def _words(s):
    return re.findall(r"[a-z][a-z\-']+", s.lower())


def _content(s):
    return {w for w in _words(s) if w not in STOP and len(w) > 3}


def _row_base(ticker, kind, doc, page_no, text):
    c, url = cite(doc["doc_id"], page_no)
    loc = f"{doc['doc_id']}#p{page_no}"
    g = doc["quote_grade"] if doc["doc_type"] in TRANSCRIPT_TYPES else ""
    return {"ticker": ticker, "kind": kind, "text": text[:MAXTXT], "citation": c, "url": url, "locator": loc,
            "source_id": loc, "doc_id": doc["doc_id"], "page_no": page_no, "quote_grade": g,
            "license": doc["license"] or "", "quotable": g in ("A", "B")}


@lru_cache(maxsize=1)
def _qa_rows():
    if not QA_CSV.exists():
        return {}
    by_path = defaultdict(list)
    with open(QA_CSV, newline="") as f:
        for r in csv.DictReader(f):
            by_path[r["path"]].append(r)
    return dict(by_path)


@lru_cache(maxsize=64)
def _pages(doc_id):
    return {r["page_no"]: r["text"] or "" for r in
            db().execute("SELECT page_no, text FROM pages WHERE doc_id=? ORDER BY page_no", (doc_id,))}


def _people(ticker):
    """Speaker names labelled in qa_turns.csv for this ticker: {norm name: role}."""
    out = {}
    for rows in _qa_rows().values():
        for r in rows:
            if r["ticker"] == ticker:
                out[_name(r["speaker_verified"] or r["speaker"])] = r["role_verified"] or r["role"]
    return out


def _name(s):
    return " ".join((s or "").split("(")[0].split()).lower()


# ---------------------------------------------------------------- transcript choice

def _transcripts(ticker, grade_min=None):
    """One best doc per quarter: grade A, then B, then C (D only if grade_min allows); no superseded docs.
    Ties prefer a doc with qa_turns labels, then one with indexed turns."""
    lim = GRADE_ORDER.get((grade_min or "D").upper(), 4)
    rows = db().execute(
        "SELECT d.*, (SELECT COUNT(*) FROM turns t WHERE t.doc_id=d.doc_id) AS nturns FROM docs d "
        "WHERE d.ticker=? AND d.doc_type IN ('transcript','transcript_source') AND d.superseded_by=''",
        (ticker,)).fetchall()
    qa = _qa_rows()
    best = {}
    for d in rows:
        g = GRADE_ORDER.get(d["quote_grade"] or "", 9)
        if g > lim or not re.match(r"^\d{4}Q[1-4]$", d["period"] or ""):
            continue
        key = (g, 0 if d["path"] in qa else 1, 0 if d["nturns"] else 1, d["doc_type"] != "transcript")
        if d["period"] not in best or key < best[d["period"]][0]:
            best[d["period"]] = (key, dict(d))
    return [best[p][1] for p in sorted(best)]


def _turns(doc, ticker):
    """[(role, speaker, firm, text, page_no)] in call order, from qa_turns.csv when it covers the doc, else from the
    index turns table with heuristic roles."""
    qa = _qa_rows().get(doc["path"])
    if qa:
        return [((r["role_verified"] or r["role"]), r["speaker_verified"] or r["speaker"],
                 r["firm_verified"] or r["firm"], r["text"], int(r["page"] or 1), "qa_turns.csv") for r in qa]
    trs = db().execute("SELECT page_no, turn_no, speaker, char_start FROM turns WHERE doc_id=? ORDER BY turn_no",
                       (doc["doc_id"],)).fetchall()
    if not trs:
        return []
    pages, people, out = _pages(doc["doc_id"]), _people(ticker), []
    for i, t in enumerate(trs):
        nxt = trs[i + 1] if i + 1 < len(trs) else None
        chunks, p = [], t["page_no"]
        while p in pages:
            start = t["char_start"] if p == t["page_no"] else 0
            if nxt and p == nxt["page_no"]:
                chunks.append(pages[p][start:nxt["char_start"]])
                break
            chunks.append(pages[p][start:])
            if not nxt:
                break
            p += 1
        text = re.sub(r"^\s*\*\*[^*]{1,160}?:\*\*", "", " ".join(chunks)).strip()
        spk = t["speaker"] or ""
        if _name(spk) == "operator":
            role = "operator"
        else:
            role = people.get(_name(spk))
            if not role:
                role = "analyst" if re.search(r"analyst|securities|research|capital|bank|partners", spk, re.I) or \
                    text.rstrip().endswith("?") else "executive"
        firm = spk.split("(", 1)[1].rstrip(")") if "(" in spk else ""
        out.append((role, _name(spk).title() if spk else "", firm, text, t["page_no"], "turns (heuristic role)"))
    return out


def _verified_span(text, doc_id, page_no, pages, anchors=(), want_q=False):
    """A run of sentences from `text` that verify on one page (start page, the next two, or the one before).
    Starts at the first sentence holding an anchor phrase (or a '?' when want_q), else at the first that verifies.
    -> (span, page)."""
    sents = _sentences(text)
    tries = (page_no, page_no + 1, page_no + 2, page_no - 1)

    def where(s):
        return next((p for p in tries if p in pages and verify_quote(s, doc_id, p)), None)

    order = list(range(len(sents)))
    pick = [i for i in order if (anchors and any(a in sents[i].lower() for a in anchors)) or
            (want_q and "?" in sents[i])]
    for start in pick + order:
        at = where(sents[start])
        if at is None:
            continue
        span = [sents[start]]
        for s in sents[start + 1:]:
            if len(" ".join(span + [s])) > MAXTXT or not verify_quote(" ".join(span + [s]), doc_id, at):
                break
            span.append(s)
        return " ".join(span), at
    return "", None


def _deflection(q, a):
    reasons, score = [], 0.0
    ql, al = q.lower(), a.lower()
    quant = NUM.search(q) or any(w in ql for w in QUANT_WORDS)
    if quant and not NUM.search(a):
        score += 0.35
        reasons.append("quantitative question, no number in answer")
    hits = [p for p in DEFLECT if p in al]
    if hits:
        score += min(0.4, 0.2 * len(hits))
        reasons.append("deflection phrase: " + "; ".join(sorted(set(hits))[:4]))
    qw, aw = len(q.split()), len(a.split())
    if qw >= 25 and aw < 0.6 * qw:
        score += 0.15
        reasons.append(f"answer shorter than question ({aw} vs {qw} words)")
    qn = _content(q)
    if len(qn) >= 5:
        ov = len(qn & _content(a)) / len(qn)
        if ov < 0.15:
            score += 0.2
            reasons.append(f"low topic overlap with question ({ov:.0%} of question terms)")
    return round(min(score, 1.0), 2), reasons


def _pairs(ticker, doc):
    turns = _turns(doc, ticker)
    pairs, i = [], 0
    while i < len(turns):
        if turns[i][0] != "analyst":
            i += 1
            continue
        qs, j = [], i
        while j < len(turns) and turns[j][0] == "analyst" and turns[j][1] == turns[i][1]:
            qs.append(turns[j])
            j += 1
        ans = []
        while j < len(turns) and turns[j][0] not in ("analyst",):
            if turns[j][0] == "executive":
                ans.append(turns[j])
            j += 1
        if ans:
            pairs.append((qs, ans))
        i = j
    return pairs


def _qa_pair_rows(ticker, doc):
    out, pages = [], _pages(doc["doc_id"])
    for qs, ans in _pairs(ticker, doc):
        q = " ".join(t[3] for t in qs)
        a = " ".join(t[3] for t in ans)
        score, reasons = _deflection(q, a)
        hits = [p for p in DEFLECT if p in a.lower()]
        span, at, who = "", None, ans[0]
        # the turn with the deflection phrase, else the longest executive turn, else any that verifies
        ranked = sorted(ans, key=lambda t: (not any(h in t[3].lower() for h in hits), -len(t[3].split())))
        for t in ranked:
            span, at = _verified_span(t[3], doc["doc_id"], t[4], pages, anchors=hits)
            if span:
                who = t
                break
        if not span:
            continue
        qspan, qat = "", None
        for t in qs:
            qspan, qat = _verified_span(t[3], doc["doc_id"], t[4], pages, want_q=True)
            if qspan:
                break
        row = _row_base(ticker, "qa_pair", doc, at, span)
        row.update({"quarter": doc["period"], "speaker": who[1], "firm": who[2], "analyst": qs[0][1],
                    "analyst_firm": qs[0][2], "question": (qspan or " ".join(_sentences(q)))[:MAXTXT], "question_verified": bool(qspan),
                    "question_locator": f"{doc['doc_id']}#p{qat}" if qat else "", "answer": span,
                    "answer_words": len(a.split()), "question_words": len(q.split()),
                    "deflection_score": score, "deflection_reasons": reasons, "role_source": who[5]})
        out.append(row)
    return out


# ---------------------------------------------------------------- new phrases

BOILER = re.compile(r"CORPORATE PARTICIPANTS|CONFERENCE CALL PARTICIPANTS|DISCLAIMER|Forward-Looking Statements? "
                    r"(?:Disclaimer|Safe Harbor)", re.I)
VENDOR = re.compile(r"Benzinga|EquityMultiple|17b disclosure|Refinitiv|StreetEvents|Seeking Alpha|Motley Fool|"
                    r"All rights reserved|Thomson Reuters|FactSet|Bloomberg Transcript|\btranscripts?\b", re.I)
# "Dean Li - Merck & Co Inc - Executive Vice President, ... " speaker header lines in flattened transcripts
HDR = re.compile(r"^(?:Operator\s+)?(?:[A-Z][\w.'\-]+\s+){1,4}-\s+[^.?!]{2,80}?\s+-\s+[^.?!]*?(?:Officer|President|"
                 r"Relations|Laboratories|Analyst|Director|Head|Chair|Officer of [A-Z]\w+)\s+(?=[A-Z])")


def _cands(text, names):
    """Capitalised phrases and content bigrams/trigrams with counts."""
    caps, grams = Counter(), Counter()
    lower_words = set(re.findall(r"(?<![\w-])[a-z][a-z\-]+(?![\w-])", text))
    for m in re.finditer(r"\b([A-Z][\w\-]*[A-Za-z](?:\s+(?:of\s+|and\s+|&\s+)?[A-Z][\w\-]*[A-Za-z]){0,3})\b", text):
        ph = m.group(1)
        while ph.split() and ph.split()[0].lower() in STOP | {"sales", "us", "u.s."} and len(ph.split()) > 1:
            ph = ph.split(None, 1)[1]
        toks = ph.lower().split()
        if all(t in STOP or t in MONTHS or t in names for t in toks):
            continue
        if any(t in names for t in toks):
            continue
        if len(toks) == 1:
            t = toks[0]
            special = ph.isupper() or re.search(r"[A-Z]|-", ph[1:])
            if len(t) < 4 or t in STOP or t in MONTHS or (not special and t in lower_words):
                continue
        caps[ph] += 1
    for sent in _sentences(text):
        toks = [w for w in re.findall(r"[a-z][a-z\-]+", sent.lower())]
        for n in (2, 3):
            for i in range(len(toks) - n + 1):
                g = toks[i:i + n]
                if g[0] in STOP or g[-1] in STOP or any(t in names or t in MONTHS for t in g) or \
                        sum(t not in STOP for t in g) < 2 or any(len(t) < 3 for t in (g[0], g[-1])):
                    continue
                grams[" ".join(g)] += 1
    return caps, grams


def _flat(s):
    return " " + re.sub(r"[^a-z0-9]+", " ", s.lower()) + " "


def _new_phrase_rows(ticker, docs, analyst_texts, limit=25):
    latest, prior = docs[-1], docs[-4:-1]
    if not prior:
        return []
    pages = _pages(latest["doc_id"])
    if len(pages) > 2:  # drop participant lists and disclaimers when they sit on their own pages
        pages = {p: t for p, t in pages.items() if not BOILER.search(t)}
    text = "\n\n".join(pages[p] for p in sorted(pages))
    names = set()
    for r in db().execute("SELECT DISTINCT speaker FROM turns WHERE doc_id IN (%s)" % ",".join("?" * len(docs)),
                          [d["doc_id"] for d in docs]):
        names |= set(_name(r[0]).split())
    for rows in _qa_rows().values():
        for r in rows:
            if r["ticker"] == ticker:
                names |= set(_name(r["speaker_verified"] or r["speaker"]).split())
                names |= set(_name(r["firm_verified"] or r["firm"]).split()) - STOP
    for t in re.findall(r"\bOperator\s+((?:[A-Z][\w'\-]+\s+){1,3}[A-Z][\w'\-]+)\s*,", text):
        names |= set(t.lower().split())
    for t in re.findall(r"\*\*([^*:(]{2,60})", text):
        names |= set(t.lower().split())
    names -= STOP
    body = text
    for q in analyst_texts:
        body = body.replace(q, " ")
    caps, grams = _cands(body, names)
    prior_flat = "".join(_flat("\n".join(_pages(d["doc_id"]).values())) for d in prior)
    picked = []
    for ph, n, kind in sorted([(p, n, "capitalised") for p, n in caps.items()] +
                              [(g, n, "ngram") for g, n in grams.items() if n >= 2],
                              key=lambda x: (x[2] != "capitalised", -x[1], -len(x[0]))):
        f = _flat(ph)
        if len(f.strip()) < 4 or f in prior_flat or re.fullmatch(r"[\s0-9]+", f):
            continue
        if any(f.strip() in _flat(p[0]) for p in picked):
            continue
        picked.append((ph, n, kind))
        if len(picked) >= limit * 3:
            break
    qn = [_norm(q) for q in analyst_texts]
    out = []
    for ph, n, kind in picked:
        pat = re.compile(rf"(?<![\w-]){re.escape(ph)}(?![\w-])", re.I)
        hit = None
        for p in sorted(pages):
            for s in _sentences(pages[p]):
                s = HDR.sub("", s)
                if len(s) <= MAXTXT and pat.search(s) and not VENDOR.search(s) and not any(_norm(s) in q for q in qn) and verify_quote(s, latest["doc_id"], p):
                    hit = (s, p)
                    break
            if hit:
                break
        if not hit:
            continue
        row = _row_base(ticker, "new_phrase", latest, hit[1], hit[0])
        row.update({"quarter": latest["period"], "phrase": ph, "phrase_kind": kind, "mentions": n,
                    "compared_against": [d["doc_id"] for d in prior], "speaker": "", "firm": "",
                    "question": "", "answer": hit[0], "deflection_score": None, "deflection_reasons": []})
        out.append(row)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- never asked

def _never_asked_rows(ticker):
    rows = db().execute('SELECT f.*, d.source_url FROM facts f LEFT JOIN docs d USING(doc_id) '
                        'WHERE f."table"=? AND f.ticker=? ORDER BY f.id', (NEVER_TABLE, ticker)).fetchall()
    out = []
    for r in rows:
        vals = json.loads(r["row_json"]) if r["row_json"] else {}
        out.append({"ticker": ticker, "kind": "never_asked", "text": (r["text"] or "")[:MAXTXT],
                    "citation": f"table {NEVER_TABLE}, row {r['row_key'].split('#')[-1]}",
                    "url": r["source_url"] or "", "locator": r["locator"], "source_id": r["locator"],
                    "quote_grade": "", "license": "", "quotable": False, "quarter": vals.get("last_asked", ""),
                    "topic": vals.get("topic", ""), "quarters_asked": vals.get("quarters_asked", ""),
                    "quarters_covered": vals.get("quarters_covered", ""),
                    "recent_unasked_streak": vals.get("recent_unasked_streak", ""), "flag": vals.get("flag", ""),
                    "speaker": "", "firm": "", "question": "", "answer": "", "deflection_score": None,
                    "deflection_reasons": [], "verify_status": r["verify_status"], "source": r["source"]})
    return out


def call_qa(ticker, quarters=4, flags=("deflection", "new_phrase", "never_asked"), grade_min="C", k=80):
    """Q&A pairs scored for deflection (highest first, at most k), new phrases in the latest call, and topics
    analysts stopped asking about. Returns [] for a ticker with no graded transcripts and no never_asked rows."""
    ticker = (ticker or "").upper()
    flags = set(flags or ())
    docs = _transcripts(ticker, grade_min)[-max(1, quarters):]
    out = []
    if docs and "deflection" in flags:
        pairs = [r for d in docs for r in _qa_pair_rows(ticker, d)]
        pairs.sort(key=lambda r: (-r["deflection_score"], r["quarter"]), reverse=False)
        out += pairs[:k]
    if docs and "new_phrase" in flags:
        latest = docs[-1]
        history = [d for d in _transcripts(ticker, "D") if d["period"] < latest["period"]][-3:]
        aq = [t[3] for t in _turns(latest, ticker) if t[0] == "analyst"]
        out += _new_phrase_rows(ticker, history + [latest], aq)
    if "never_asked" in flags:
        out += _never_asked_rows(ticker)
    return out


# ---------------------------------------------------------------- dropped metrics

NUMLINE = re.compile(r"^\(?\s*\$?\s*\(?-?[\d,]+(\.\d+)?\s*\)?\s*(%|bn|m|billion|million)?\s*\)?$", re.I)
BAD_LABEL = re.compile(r"^(table \w+|total|change|% change|ytd|full year|q[1-4]|[1-4]q|\d{4}|june|march|september|"
                       r"december|three months|six months|nine months|ex-?fx|as reported|operational|currency|worldwide|u s|us|"
                       r"united states|international|ex-u s|rest of world|other|all other|europe|japan|china|"
                       r"emerging markets)$|\b(past|months|except|amounts|previously|includes|approximately)\b", re.I)


PERIODISH = re.compile(r"\b(?:19|20)\d\d\b|\b[1-4]q\d{0,2}\b|\bq[1-4]\b|\bfy\d*\b|\bh[12]\b|\bbillion\b|\bmillion\b")


def _norm_label(s):
    s = re.sub(r"(?<=[A-Za-z])\d(?:,\d)*\b|\(\s*[a-z0-9]\s*\)|[*†‡]", " ", s)
    s = re.sub(r"[^A-Za-z0-9&/\-+ ]+", " ", s)
    return " ".join(s.split()).lower()


def _labels(text):
    """{normalized label: raw label} for lines that carry a number: '<Name> ... $<number>' or a table row."""
    out = {}

    def add(raw):
        raw = " ".join(raw.split()).strip(" :-|")
        n = _norm_label(raw)
        if 3 <= len(n) <= 60 and raw[:1].isalpha() and "," not in raw and re.match(r"[a-z]", n) and re.search(r"[a-z]{3}", n) and len(n.split()) <= 7 \
                and not BAD_LABEL.search(n) and ":" not in raw and not PERIODISH.search(n) \
                and n.split()[-1] not in STOP:
            out.setdefault(n, raw)

    buf = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and any(NUM.search(c) for c in cells[1:]) and not NUM.search(cells[0][:1]):
                add(cells[0])
            buf = []
            continue
        if NUMLINE.match(s) or s in ("*", "\u2014", "-", "N/M", "n/m", "NM"):
            if buf:
                lab, i = buf[-1], len(buf) - 1
                while i > 0 and (lab[:1].islower() or buf[i - 1].split()[-1].lower() in STOP):
                    i -= 1
                    lab = buf[i] + " " + lab
                add(lab)
            buf = []
            continue
        m = re.match(r"^(.{3,60}?)\s*(?:\.{2,}|\s{2,}|:)?\s*\$\s?[\d,.]+", s)
        if m and not NUM.search(m.group(1)[:1]):
            add(m.group(1))
            buf = []
            continue
        for m in re.finditer(r"\b([A-Z][A-Za-z0-9/\-]+(?:\s+[A-Z][A-Za-z0-9/\-]+){0,3})\s+(?:Sales|Revenue)s?\s+"
                             r"(?:Were|Was|of|Grew|Increased|Decreased)\s+\$", s):
            add(m.group(1) + " sales")
        buf.append(s)
        buf = buf[-3:]
    return out


def _metrics(text):
    t = " " + text.lower() + " "
    return {m for m in KEY_METRICS if re.search(rf"(?<![a-z]){re.escape(m)}(?![a-z])", t)}


def _series(ticker, releases):
    """{series name: [(period, [docs])]} oldest first, last `releases` entries each."""
    con, out = db(), {}
    rel = defaultdict(list)
    for d in con.execute("SELECT * FROM docs WHERE ticker=? AND doc_type='earnings_release' AND superseded_by=''",
                         (ticker,)):
        rel[d["filed"] or d["period"]].append(dict(d))
    if rel:
        out["earnings_release"] = sorted(rel.items())[-releases:]
    sl = defaultdict(list)
    for d in con.execute("SELECT * FROM docs WHERE ticker=? AND doc_type='earnings_slides' AND superseded_by=''",
                         (ticker,)):
        sl[d["period"]].append(dict(d))
    if sl:
        out["earnings_slides"] = sorted(sl.items())[-releases:]
    tq = defaultdict(list)
    for d in con.execute("SELECT * FROM docs WHERE ticker=? AND doc_type='quarterly_report' AND superseded_by=''",
                         (ticker,)):
        tq[d["period"]].append(dict(d))
    if tq:
        out["10-Q product sales"] = sorted(tq.items())[-releases:]
    return out


def _sales_pages(doc):
    """10-Q pages that hold a product sales table (several numeric label lines and the word sales)."""
    for p, text in _pages(doc["doc_id"]).items():
        lo = text.lower()
        if re.search(r"(product|pharmaceutical|worldwide|net) (sales|revenue)|sales by|revenue by", lo) and \
                len(_labels(text)) >= 8:
            yield p, text


def dropped_metrics(ticker, releases=6):
    """Labels (products, line items, key-metric words) seen in at least two earlier releases of a series and
    missing from its latest two. Series: earnings releases (by filing date), earnings slides and 10-Q product sales
    pages (by period), each compared only with itself."""
    ticker = (ticker or "").upper()
    out = []
    for series, items in _series(ticker, releases).items():
        if len(items) < 4:
            continue
        seen = []  # per release: {label: (raw, doc, page)}, plus metric words
        for period, docs in items:
            labs, mets = {}, {}
            for d in docs:
                pages = _sales_pages(d) if series.startswith("10-Q") else _pages(d["doc_id"]).items()
                for p, text in pages:
                    for n, raw in _labels(text).items():
                        labs.setdefault(n, (raw, d, p))
                    for m in _metrics(text):
                        mets.setdefault(m, (m, d, p))
            seen.append((period, docs, labs, mets))
        earlier, latest = seen[:-2], seen[-2:]
        sizes = sorted(len(x[2]) for x in earlier)
        if min(len(x[2]) for x in latest) < 0.5 * sizes[len(sizes) // 2]:
            continue  # latest releases parsed much thinner than earlier ones: a format change, not dropped metrics
        check = latest[-1][1][0]["doc_id"] if latest[-1][1] else ""
        later_flat = "".join(_flat("\n".join(_pages(x["doc_id"]).values())) for s_ in latest for x in s_[1])
        for kind, idx in (("label", 2), ("key_metric", 3)):
            later = set().union(*(s[idx].keys() for s in latest))
            counts = Counter(n for s in earlier for n in s[idx])
            for n, c in counts.items():
                if c < 2 or n in later:
                    continue
                if kind == "label" and any(n in L or L in n for L in later if len(L) > 4 and len(n) > 4):
                    continue  # renamed or reworded, not dropped
                core = re.sub(r"\s+(united states|u s|us|international|worldwide|ex-u s|total)$", "", n)
                if _flat(core) in later_flat:
                    continue  # still printed somewhere in the latest releases, just not as a parsed line
                last = [s for s in earlier if n in s[idx]][-1]
                raw, d, p = last[idx][n]
                sent = _evidence(raw, d["doc_id"], p)
                if not sent:
                    continue
                c_str, url = cite(d["doc_id"], p)
                loc = f"{d['doc_id']}#p{p}"
                out.append({"ticker": ticker, "kind": "dropped_metric", "metric_kind": kind, "series": series,
                            "label": raw, "text": sent, "citation": c_str, "url": url, "locator": loc,
                            "source_id": loc, "quote_grade": "", "license": d["license"] or "",
                            "last_seen": last[0], "times_seen": c, "releases_compared": [s[0] for s in seen],
                            "missing_from": [s[0] for s in latest], "checked_against": check,
                            "checked_against_all": [x["doc_id"] for s in latest for x in s[1]]})
    out.sort(key=lambda r: (r["series"], r["metric_kind"] != "key_metric", -r["times_seen"], r["label"]))
    return out


def _evidence(raw, doc_id, page_no):
    """A verified snippet from the page that contains the label: its sentence, or the label with the next figure."""
    text = _pages(doc_id).get(page_no, "")
    flat = " ".join(text.split())
    i = _norm(flat).find(_norm(raw))
    if i < 0:
        return ""
    for s in _sentences(text):
        if _norm(raw) in _norm(s) and len(s) <= MAXTXT and verify_quote(s, doc_id, page_no):
            return s
    m = re.search(re.escape(" ".join(raw.split())) + r"[^$\d]{0,40}\$?\s?[\d,.]+(\s?%)?", flat, re.I)
    snip = m.group(0) if m else flat[i:i + len(raw)]
    return snip if verify_quote(snip, doc_id, page_no) else ""


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Earnings-call Q&A flags and dropped metrics")
    ap.add_argument("ticker")
    ap.add_argument("--quarters", type=int, default=4)
    ap.add_argument("--grade", default="C")
    ap.add_argument("-k", type=int, default=20)
    ap.add_argument("--flags", default="deflection,new_phrase,never_asked")
    ap.add_argument("--dropped", action="store_true", help="run dropped_metrics instead of call_qa")
    ap.add_argument("--releases", type=int, default=6)
    a = ap.parse_args(argv)
    if a.dropped:
        rows = dropped_metrics(a.ticker, releases=a.releases)
        if not rows:
            print(f"no dropped metrics for {a.ticker}: fewer than 4 releases in a series, or nothing dropped")
        for r in rows:
            print(f"[{r['series']}/{r['metric_kind']}] {r['label']!r} last seen {r['last_seen']} "
                  f"(x{r['times_seen']}), missing from {r['missing_from']}  <{r['locator']}>")
            print(f"    {r['citation']}: {r['text'][:200]}")
        return
    rows = call_qa(a.ticker, quarters=a.quarters, flags=tuple(a.flags.split(",")), grade_min=a.grade, k=a.k)
    if not rows:
        print(f"no rows for {a.ticker}: no transcripts at grade {a.grade} or better and no never_asked rows")
    for r in rows:
        head = f"[{r['kind']}] {r.get('quarter', '')} grade={r['quote_grade'] or '-'}{' LICENSED' if r['license'] else ''}"
        if r["kind"] == "qa_pair":
            print(f"{head} score={r['deflection_score']} {r['analyst']} -> {r['speaker']}  <{r['locator']}>")
            print(f"    Q: {r['question'][:160]}")
            print(f"    A: {r['answer'][:200]}")
            print(f"    why: {'; '.join(r['deflection_reasons'])}  ({r['citation']})")
        elif r["kind"] == "new_phrase":
            print(f"{head} phrase={r['phrase']!r} x{r['mentions']}  <{r['locator']}>")
            print(f"    {r['citation']}: {r['text'][:200]}")
        else:
            print(f"{head} topic={r['topic']} streak={r['recent_unasked_streak']}  <{r['locator']}>")
            print(f"    {r['text'][:200]}")


if __name__ == "__main__":
    main(sys.argv[1:])
