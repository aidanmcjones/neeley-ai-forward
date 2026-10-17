"""Earnings-call and earnings-release detector.

Signals (deterministic, no network, no LLM):
  qa_deflection           management dodged an analyst question (one quarter)
  qa_repeated_deflection  same topic dodged in >= 2 different quarters (strong)
  call_topic_surge        a topic's mentions in the latest call >= 3x the earlier average (and >= 4)
  metric_dropped          a table row label seen in >= 2 earlier earnings releases is gone from the latest

Every quote is 20 to 45 consecutive words copied from the page and checked with pages.check().
"""

import re
from bisect import bisect_right
from collections import defaultdict

from agent import findings
from agent.needle import pages
from agent.needle.detect import SKIP_DOCS, cli
from agent.needle.schema import Evidence, Signal

FOOL_START = findings.FOOL_START

DEFLECT = [
    "we don't break out", "we do not break out", "we don't provide", "we do not provide", "not going to comment",
    "too early to", "we'll update you", "we will update you", "won't speculate", "will not speculate",
    "not going to speculate", "not in a position to", "we don't guide", "we do not guide", "i'd rather not",
    "i would rather not", "stay tuned", "more to come", "not going to get into", "we don't disclose",
    "we do not disclose", "we're not going to get into", "not going to provide", "not going to give",
    "unable to comment", "can't comment", "cannot comment", "we don't give", "we don't report",
]

WEAK = {"more to come", "stay tuned", "too early to"}   # often benign pipeline talk when no policy topic is shared

# topic -> (squashed keywords, case-sensitive regex for short tokens)
TOPICS = {
    "ira": (["inflationreductionact", "maximumfairprice", "medicarenegotiation", "medicaredrugpricenegotiation"],
            r"\bIRA\b"),
    "mfn": (["mostfavorednation", "mostfavourednation", "trumprx"], r"\bMFN\b"),
    "tariff": (["tariff"], None),
    "gtn": (["grosstonet", "rebate", "netprice", "pricing"], None),
    "340b": (["340b"], None),
    "generic": (["generic", "biosimilar"], None),
    "guidance": (["guidance"], None),
    "inventory": (["inventor", "destock", "stocking"], None),
    "launch": (["launch"], None),
    "pipeline": (["pipeline"], None),
}
TOPIC_RE = {t: re.compile(r) for t, (_, r) in TOPICS.items() if r}

QA_HEAD = re.compile(r"^\W*QUESTIONS?\s+AND\s+ANSWERS?\W*$")
QA_LINE = re.compile(r"first question|question-and-answer|question and answer session|open (?:up )?the (?:line|call)|"
                     r"ready (?:to begin|for) (?:the )?q&a|begin the q&a|open (?:it|the floor) up for questions", re.I)
BOILER = re.compile(r"LSEG|©|Republication or redistribution|prior written consent|^\W*\d{1,3}\W*$|"
                    r"Earnings Call\s*$|Contact Us", re.I)
NAME = r"(?:[A-Z][A-Za-z'’\-]+|[A-Z]\.)"
L_DASH = re.compile(rf"^\s*({NAME}(?: {NAME}){{1,3}}) ?(?:-|--|–) ?([^-].*?-.*)$")      # Name - Company - Title
L_COLON = re.compile(rf"^\s*({NAME}(?: {NAME}){{1,4}}|Operator|Speaker #\d+) ?:\s*(.*)$")
L_COMMA = re.compile(rf"^\s*({NAME}(?: {NAME}){{1,3}}), ([^.]{{3,110}})$")                # Name, Title at Company
L_ALONE = re.compile(rf"^\s*({NAME}(?: {NAME}){{1,3}})\s*$")
L_OP = re.compile(r"^\s*Operator\s*$")
MONTHS = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|quarter|months|ended|year", re.I)


# ------------------------------------------------------------------ text helpers

def squash(s):
    """Lowercase alphanumerics only, with the index of each kept char in s. Survives text with spaces removed."""
    chars, idx = [], []
    for i, c in enumerate(s):
        if c.isalnum():
            chars.append(c.lower())
            idx.append(i)
    return "".join(chars), idx


def find_keys(text, keys):
    """[(start_char, end_char)] for each squashed key found in text."""
    sq, idx = squash(text)
    out = []
    for k in keys:
        k = "".join(c for c in k.lower() if c.isalnum())
        for m in re.finditer(re.escape(k), sq):
            out.append((idx[m.start()], idx[m.end() - 1] + 1))
    return sorted(out)


def window(text, start, end, target=36):
    """20 to 45 consecutive words of text covering [start, end) as exactly as possible, else None."""
    ws = list(re.finditer(r"\S+", text))
    n = len(ws)
    if n < 20:
        return None
    starts = [w.start() for w in ws]
    a = max(0, bisect_right(starts, start) - 1)
    b = max(a + 1, bisect_right(starts, max(start, end - 1)))
    span = min(b - a, 40)
    s = max(0, a - (target - span) // 2)
    e = s + max(target, span)
    if e > n:
        e = n
        s = max(0, n - max(target, span))
    if e - s > 45:
        e = s + 45
    if e - s < 20:
        return None
    return " ".join(w.group() for w in ws[s:e])


def topics_in(text):
    found = set()
    sq, _ = squash(text)
    for t, (keys, _) in TOPICS.items():
        if any("".join(c for c in k if c.isalnum()) in sq for k in keys) or (t in TOPIC_RE and TOPIC_RE[t].search(text)):
            found.add(t)
    return found


def count_topic(text):
    sq, _ = squash(text)
    out = {}
    for t, (keys, _) in TOPICS.items():
        n = sum(sq.count("".join(c for c in k if c.isalnum())) for k in keys)
        if t in TOPIC_RE:
            n += len(TOPIC_RE[t].findall(text))
        out[t] = n
    return out


# ------------------------------------------------------------------ transcript parsing

def parse_label(line, prev_blank, next_line):
    """(speaker, label, rest) when line opens a speaker turn, else None."""
    if L_OP.match(line):
        return "Operator", line.strip(), ""
    if len(line) < 220:
        m = L_DASH.match(line)
        if m and len(line) < 190 and not re.search(r"[.?!]\s+\w", m.group(1)):
            return m.group(1).strip(), line.strip(), ""
    m = L_COLON.match(line)
    if m:
        return m.group(1).strip(), line.strip(), m.group(2).strip()
    m = L_COMMA.match(line)
    if m and next_line is not None and len(m.group(2).split()) <= 14:
        return m.group(1).strip(), line.strip(), ""
    if prev_blank and L_ALONE.match(line) and len(line) < 40 and next_line is not None:
        return line.strip(), line.strip(), ""
    return None


def parse_turns(doc):
    """Speaker turns in call order: dict(speaker, label, qa, blocks=[(page, text)]). Skips fool.com takeaways."""
    full = "\n".join(t for _, (_, t) in sorted(doc["pages"].items()))
    started = FOOL_START not in full.lower()
    turns, cur, qa = [], None, False
    pending_name_only = False
    for pg, (_, text) in sorted(doc["pages"].items()):
        if not started:
            i = text.lower().find(FOOL_START)
            if i == -1:
                continue
            started, text = True, text[i + len(FOOL_START):]
        lines = text.split("\n")
        prev_blank = True
        run = []          # lines of the current contiguous block

        def flush():
            nonlocal run
            if cur is not None and run:
                cur["blocks"].append((pg, " ".join(run)))
            run = []

        for i, raw in enumerate(lines):
            line = raw.rstrip()
            if not line.strip():
                prev_blank = True
                continue
            if BOILER.search(line) and len(line) < 220:
                flush()
                prev_blank = False
                continue
            if QA_HEAD.match(line.strip()) or (not qa and QA_LINE.search(line)):
                qa = True
            nxt = next((x for x in lines[i + 1:i + 3] if x.strip()), None)
            lab = parse_label(line, prev_blank, nxt)
            prev_blank = False
            if lab:
                flush()
                cur = {"speaker": lab[0], "label": lab[1], "qa": qa, "blocks": []}
                turns.append(cur)
                if lab[2]:
                    run.append(lab[2])
                continue
            run.append(line.strip())
        flush()
    return [t for t in turns if t["blocks"] or t["speaker"] == "Operator"]


def classify(turns):
    """Mark each turn role: operator | analyst | mgmt."""
    prepared = {t["speaker"] for t in turns if not t["qa"]}
    has_op = any(t["speaker"] == "Operator" and t["qa"] for t in turns)
    analysts, prev = set(), None
    for t in turns:
        s = t["speaker"]
        text = " ".join(b[1] for b in t["blocks"])
        if s == "Operator":
            t["role"] = "operator"
        else:
            if t["qa"] and s not in prepared and s not in analysts:
                lab = t["label"].lower()
                if ("analyst" in lab or re.search(r"\bwith [A-Z]", t["label"]) or
                        (prev is not None and prev["speaker"] == "Operator") or
                        (not has_op and "?" in text[:1500])):
                    analysts.add(s)
            if re.search(r"analyst", t["label"], re.I) and not re.search(r"investor relations", t["label"], re.I):
                analysts.add(s)
            t["role"] = "analyst" if s in analysts else "mgmt"
        prev = t
    return turns


def words30(s):
    return " ".join(s.split()[:30])


def find_deflections(doc):
    """[dict(speaker, page, quote, question, topics, phrase)] for management answers in Q&A."""
    turns = classify(parse_turns(doc))
    out, q_parts, last_role = [], [], None
    for t in turns:
        text = " ".join(b[1] for b in t["blocks"])
        if t["role"] == "analyst" and t["qa"]:
            q_parts = q_parts + [text] if last_role == "analyst" else [text]
        elif t["role"] == "mgmt" and t["qa"] and q_parts:
            q = " ".join(q_parts)
            qt, at = topics_in(q), topics_in(text)
            shared = qt & at
            if not shared and 0 < len(qt) <= 2:
                shared = qt
            hit = None
            for pg, btxt in t["blocks"]:
                for phrase in DEFLECT:
                    for s, e in find_keys(btxt, [phrase]):
                        quote = window(btxt, s, e)
                        if not quote or (not shared and phrase in WEAK):
                            continue
                        tp = (topics_in(quote) & qt) or shared
                        hit = (pg, quote, phrase, tp)
                        break
                    if hit:
                        break
                if hit:
                    break
            if hit:
                out.append({"speaker": t["speaker"], "page": hit[0], "quote": hit[1], "phrase": hit[2],
                            "question": words30(max(q_parts, key=len)), "topics": sorted(hit[3])})
        if t["role"] in ("analyst", "mgmt"):
            last_role = t["role"]
    return out, turns


# ------------------------------------------------------------------ evidence + verification

class Checker:
    def __init__(self, ticker):
        self.docs = pages.docs(ticker, ("transcript", "earnings_release"))
        self.drops = defaultdict(int)

    def evidence(self, doc_id, page, quote, speaker=""):
        """Evidence if the quote verifies (needs_human kept for speaker-only issues), else None."""
        ev = Evidence(doc_id, page, quote, speaker)
        status, reason = pages.check(ev, self.docs)
        if status == "verified":
            self.drops["verified"] += 1
            return ev, "verified"
        if status == "needs_human" and "speaker" in reason and self.docs[doc_id]["row"]["doc_type"] == "transcript":
            self.drops["needs_human_speaker"] += 1
            return ev, "needs_human"
        self.drops[f"dropped_{status}"] += 1
        return None, status


# ------------------------------------------------------------------ release metrics

NUM = r"\(?\$?\s*\d[\d,]*(?:\.\d+)?\)?%?"
ROW = re.compile(rf"^\s*(?P<label>[A-Za-z][A-Za-z0-9 &/®™,\-\.'’]{{2,60}}?)[\s$]+(?P<nums>{NUM}(?:[\s$%]+{NUM}|\s+[—-]){{1,}})\s*$")
GENERIC = re.compile(r"^(total|net|other|u s|us|international|worldwide|income|earnings|gross|operating|diluted|basic|"
                     r"weighted|cash|per share|revenues?|sales|dollars|percent|and|of|the|in|as|to|for)$")


def norm_label(s):
    s = re.sub(r"[^a-z ]", " ", s.lower().replace("®", "").replace("™", ""))
    return " ".join(s.split())


def release_labels(doc):
    """{norm_label: [(page, raw_line)]} for table-like lines in one release doc."""
    out = defaultdict(list)
    for pg, (_, text) in doc["pages"].items():
        for line in text.split("\n"):
            m = ROW.match(line)
            if not m:
                continue
            lab = norm_label(m.group("label"))
            if len(lab) < 4 or len(lab.split()) > 7 or GENERIC.match(lab) or MONTHS.search(lab):
                continue
            out[lab].append((pg, line))
    return out


def metric_dropped(ticker, ck):
    rel = {i: d for i, d in pages.docs(ticker, ("earnings_release",)).items() if i not in SKIP_DOCS}
    groups = defaultdict(list)
    for i in rel:
        m = re.search(r"earnings/(\d{4}-\d{2}-\d{2})_", i)
        if m:
            groups[m.group(1)].append(i)
    dates = sorted(groups)
    if len(dates) < 3:
        return []
    labs = []
    for d in dates:
        merged = defaultdict(list)
        for i in groups[d]:
            for k, v in release_labels(rel[i]).items():
                merged[k] += [(i, pg, ln) for pg, ln in v]
        labs.append(merged)
    latest = dates[-1]
    latest_lines = [set(norm_label(ln).split()) for i in groups[latest]
                    for _, (_, t) in rel[i]["pages"].items() for ln in t.split(chr(10))]
    earlier_common = [k for k in labs[-2] if sum(k in labs[j] for j in range(len(labs) - 1)) >= 2]
    if not earlier_common:
        return []
    overlap = sum(k in labs[-1] for k in earlier_common) / len(earlier_common)
    if overlap < 0.5:      # release layout changed wholesale: label absence would be parsing noise
        return []
    sigs = []
    for k in sorted(labs[-2]):
        seen = [j for j in range(len(labs) - 1) if k in labs[j]]
        if len(seen) < 2 or k in labs[-1]:
            continue
        toks = set(k.split())
        if any(len(toks & ln) >= 0.8 * len(toks) for ln in latest_lines):   # reworded, not dropped
            continue
        j = seen[-1]
        doc_id, pg, line = labs[j][k][0]
        text = rel[doc_id]["pages"][pg][1]
        pos = text.find(line.strip())
        quote = window(text, pos, pos + len(line.strip())) if pos >= 0 else None
        if not quote:
            ck.drops["metric_no_window"] += 1
            continue
        ev, st = ck.evidence(doc_id, pg, quote)
        if not ev:
            continue
        sigs.append(Signal(
            ticker=ticker, detector="calls", kind="metric_dropped", value=float(len(seen)),
            detail=f"Row '{k}' appeared in {len(seen)} earlier earnings releases (last {dates[j]}) but not in "
                   f"the {latest} release.",
            evidence=[ev], meta={"label": k, "last_seen": dates[j], "latest_release": latest, "verifier": st}))
    return sigs


# ------------------------------------------------------------------ run

def run(ticker):
    ticker = ticker.upper()
    ck = Checker(ticker)
    tr = sorted(((i, d) for i, d in ck.docs.items()
                 if d["row"]["doc_type"] == "transcript" and i not in SKIP_DOCS),
                key=lambda x: x[1]["row"]["period"])
    sigs = []
    period = tr[-1][1]["row"]["period"] if tr else ""
    per_doc = {}
    for i, d in tr:
        defl, turns = find_deflections(d)
        per_doc[i] = (d["row"]["period"], defl, turns)

    # deflections
    by_topic = defaultdict(lambda: defaultdict(list))     # topic -> quarter -> [(doc_id, defl)]
    singles = {}                                          # (quarter, doc, page, quote) for topic-less hits
    for i, (q, defl, _) in per_doc.items():
        for f in defl:
            for t in f["topics"] or ["other"]:
                by_topic[t][q].append((i, f))
    emitted = set()
    for topic, qs in sorted(by_topic.items()):
        quarters = sorted(qs)
        evs, ok_q = [], []
        for q in quarters:
            for i, f in qs[q]:
                ev, st = ck.evidence(i, f["page"], f["quote"], f["speaker"])
                if ev:
                    evs.append((q, i, f, ev, st))
                    ok_q.append(q)
                    break
        if topic != "other" and len(set(ok_q)) >= 2:
            who = "; ".join(f"{q}: {f['speaker']}" for q, _, f, _, _ in evs)
            last = evs[-1][2]
            sigs.append(Signal(
                ticker=ticker, detector="calls", kind="qa_repeated_deflection", period=period,
                value=float(len(set(ok_q))),
                detail=f"Management deflected {topic} questions in {len(set(ok_q))} quarters ({who}); latest answer "
                       f"to: '{last['question']}'",
                evidence=[e for *_, e, _ in evs][-3:],
                meta={"topic": topic, "quarters": sorted(set(ok_q)), "phrases": [f['phrase'] for _, _, f, _, _ in evs],
                      "verifier": "needs_human" if any(s == "needs_human" for *_, s in evs) else "verified"}))
            emitted |= {id(f) for _, _, f, _, _ in evs}
    for topic, qs in sorted(by_topic.items()):
        for q in sorted(qs):
            for i, f in qs[q]:
                if id(f) in emitted:
                    continue
                ev, st = ck.evidence(i, f["page"], f["quote"], f["speaker"])
                if not ev:
                    continue
                emitted.add(id(f))
                sigs.append(Signal(
                    ticker=ticker, detector="calls", kind="qa_deflection", period=q, value=1.0,
                    detail=f"{f['speaker']} deflected a {topic} question in {q} ('{f['phrase']}'); asked: "
                           f"'{f['question']}'",
                    evidence=[ev], meta={"topic": topic, "phrase": f["phrase"], "question": f["question"],
                                         "verifier": st}))
                break

    # topic surge
    if len(tr) >= 2:
        counts = [count_topic(" ".join(t for _, (_, t) in sorted(d["pages"].items()))) for _, d in tr]
        for topic in TOPICS:
            latest, earlier = counts[-1][topic], [c[topic] for c in counts[:-1]]
            avg = sum(earlier) / len(earlier)
            if latest >= 4 and latest >= 3 * avg:
                ratio = latest / max(avg, 1.0)
                i, d = tr[-1]
                _, _, turns = per_doc[i]
                keys = TOPICS[topic][0]
                best = None
                for t in turns:
                    if t["role"] != "mgmt":
                        continue
                    for pg, btxt in t["blocks"]:
                        hits = find_keys(btxt, keys)
                        if hits and (best is None or len(hits) > best[0]):
                            q = window(btxt, *hits[0])
                            if q:
                                best = (len(hits), pg, q, t["speaker"])
                if not best:
                    ck.drops["surge_no_quote"] += 1
                    continue
                ev, st = ck.evidence(i, best[1], best[2], best[3])
                if ev:
                    sigs.append(Signal(
                        ticker=ticker, detector="calls", kind="call_topic_surge", period=period,
                        value=round(ratio, 2),
                        detail=f"'{topic}' came up {latest} times in the {period} call vs an average of {avg:.1f} in "
                               f"earlier calls ({ratio:.1f}x).",
                        evidence=[ev], meta={"topic": topic, "latest": latest, "earlier": earlier, "verifier": st}))

    sigs += [s for s in metric_dropped(ticker, ck)]
    for s in sigs:
        s.period = s.period or period
    print(f"{ticker}: evidence checks {dict(ck.drops)}")
    return sigs


if __name__ == "__main__":
    cli("calls", run)
