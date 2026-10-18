"""Extra transcript layouts (roic block, allmind Speaker #N, spaceless JNJ, ABBV inline Analyst, moderator-style fool)."""
import re
from agent.moat.market_topics import NOISE, parse_qa

ANALYST_NAME_RES = [
    re.compile(r"(?:question|go to|go next to|go first to|next up|first up)[^.\n]{0,60}?\bfrom ([A-Z][\w.'-]+(?: [A-Z][\w.'-]+){0,3})"),
    re.compile(r"(?:go|goes|move) (?:first |next )?(?:to|with) ([A-Z][\w.'-]+(?: [A-Z][\w.'-]+){0,3}) (?:with|from|at|of)\b"),
]


def _norm(s):
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def parse_qa2(text):
    head = text[:300]
    lines = text.split("\n")
    if "roic" in head:
        start = None
        for i, l in enumerate(lines):
            if l.strip() == "Operator" and any("first question" in x.lower() for x in lines[i:i + 4]):
                start = i
                break
        if start is None:
            return 1, []
        turns, cur, prev_op, names = [], None, False, set()
        i = start
        while i < len(lines):
            l = lines[i].strip()
            if l == "Operator":
                cur = [i + 1, "Operator", False, ""]
                prev_op = True
                turns.append(cur)
            elif re.fullmatch(r"[A-Z]{1,2}", l):
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                name = lines[j].strip()
                if name == "Operator":
                    cur = [i + 1, "Operator", False, ""]
                    turns.append(cur)
                    prev_op = True
                    i = j + 1
                    continue
                if prev_op:
                    names.add(name)
                cur = [i + 1, name, name in names, ""]
                turns.append(cur)
                prev_op = False
                i = j
            elif l and cur is not None and not NOISE.search(l):
                cur[3] += " " + l
            i += 1
        return start + 1, [tuple(t) for t in turns]
    if "allmind" in head:
        pat = re.compile(r"^\s*Speaker #(\d+) : (.*)$")
        first_q = None
        for i, l in enumerate(lines):
            if re.search(r"first question", l, re.I) and pat.match(l) and i > len(lines) * 0.3:
                first_q = i
                break
        if first_q is None:
            return parse_qa(text)
        pre = {pat.match(l).group(1) for l in lines[:first_q] if pat.match(l)}
        turns = []
        for i in range(first_q, len(lines)):
            m = pat.match(lines[i])
            if m:
                body = m.group(2)
                oper = bool(re.search(r"raise hand|next question|your line|first question", body, re.I)) and len(body) < 400
                turns.append((i + 1, f"Speaker #{m.group(1)}", m.group(1) not in pre and not oper, body))
        return first_q + 1, turns
    if "fool.com" in head and len(re.findall(r"Analyst \(", text)) > 3:
        turns = []
        first = None
        for i, l in enumerate(lines):
            m = re.search(r"Analyst \(([^)]+)\)\.?\s*(.*)", l)
            if m:
                first = first or i
                turns.append((i + 1, m.group(1), True, m.group(2)))
        return (first or 0) + 1, turns
    start, turns = parse_qa(text)
    if re.search(r"-Analyst\s*$", text, re.M) and not any(t[2] for t in turns):
        turns, cur = [], None
        for i in range(start - 1, len(lines)):
            l = lines[i]
            if NOISE.search(l) or not l.strip():
                continue
            m = re.match(r"^(.+?)-(.+?)-([^-]+)$", l.strip())
            if l.strip() == "Operator":
                cur = [i + 1, "Operator", False, ""]
                turns.append(cur)
            elif m and len(l) < 120 and m.group(3).strip() == "Analyst" or (m and len(l) < 160 and re.search(r"Officer|President|Chair", m.group(3))):
                cur = [i + 1, m.group(1), m.group(3).strip() == "Analyst", ""]
                turns.append(cur)
            elif cur is not None:
                cur[3] += " " + l.strip()
        return start, [tuple(t) for t in turns]
    if turns and not any(t[2] for t in turns):
        blob = " ".join(t[3] for t in turns)
        last = set()
        for rx in ANALYST_NAME_RES:
            for m in rx.finditer(blob):
                n = _norm(m.group(1)).split()
                if n:
                    last.add(n[-1])
        ops = {t[1] for t in turns if re.search(r"line is open|next question", t[3], re.I) and len(t[3]) < 400}
        turns = [(a, b, bool(_norm(b).split()) and _norm(b).split()[-1] in last and b not in ops, d) for a, b, c, d in turns]
    return start, turns
