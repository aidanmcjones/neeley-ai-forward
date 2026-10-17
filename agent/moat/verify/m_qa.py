"""Verified Q&A parser for earnings call transcripts (all layouts in data/corpus and data/moat).

Returns turns [(line_no, speaker, role, text)] with role in {"O" operator, "E" executive, "A" analyst}.
Role logic, in order:
  1. explicit label (LSEG "Name - Firm - Analyst", marketbeat "(Analyst at X)", benzinga "Name, Analyst at X");
  2. company roster: participants lists, pre-Q&A speakers, titled exec labels, cross-quarter roster;
  3. position: the first non-exec speaker after an operator/moderator introduction is the analyst.
For allmind (anonymized, unreliable diarization) roles are position-only: the turn right after an
introduction is the analyst question; everything until the next introduction is the answer.
Fool TAKEAWAYS/SUMMARY/RISKS (AI-written) are skipped by starting at "Full Conference Call Transcript".
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NOISE = re.compile(r"^\[\[page|LSEG STREETEVENTS|REFINITIV STREETEVENTS|^\s*\d+\s*$|Contact Us|THOMSON REUTERS|©|"
                   r"prior written consent|^[A-Z]+ \d+, 20\d\d / |^\s*Ad\s*$|^<!--|^\s{0,4}(ticker|retrieved|verbatim)", re.I)
INTRO = re.compile(r"(first|next|last|final|following) question|question (today )?(is |will be |comes |is coming |will come )?"
                   r"(from|comes from)|comes from the line|line of [A-Z]|your line is|line is (now )?(open|live)|over to you|"
                   r"go ahead|we('ll| will) (go|move|take) (next )?to [A-Z]\w+ \w*\s?(at|from|with|of) |question,? please", re.I)
EXEC_TITLE = re.compile(r"chief|officer|president|\bCEO\b|\bCFO\b|investor relations|\bIR\b|executive vice|\bEVP\b|\bSVP\b|"
                        r"head of|chair|treasurer|controller|general counsel|vice president|director, investor", re.I)
COMPANY = {"ABBV": r"abbvie", "AMGN": r"amgen", "AZN": r"astrazeneca|alexion", "BMY": r"bristol|BMS", "GILD": r"gilead|kite",
           "JNJ": r"johnson", "LLY": r"lilly", "MRK": r"merck", "NVO": r"novo", "PFE": r"pfizer"}
INTRO_NAME = re.compile(r"(?:from|is|to|of) (?:the line of )?([A-Z][A-Za-zÀ-ſ'’-]+(?: [A-Z][A-Za-zÀ-ſ'’.-]+){1,3}?)"
                        r"(?:,? (?:from|at|with|of) ([A-Z][A-Za-z&.'’ -]{1,40}?))?(?=[.,?]| Your| Please| over| Over|$)")
NAME_RX = re.compile(r"(?:from|is|of|to|with|by) ([A-Z][A-Za-zÀ-ſ'.-]+(?: [A-Z][A-Za-zÀ-ſ'.-]+){0,3})")


FIRM = re.compile(r"analyst|equity|research|capital|securities|partners|bank|sachs|morgan|cowen|leerink|evercore|"
                  r"bernstein|ubs|barclays|citi|jefferies|wolfe|guggenheim|piper|raymond|cantor|bmo|rbc|wells fargo|"
                  r"berenberg|redburn|danske|deutsche|hsbc|bnp|kepler|jyske|nordea|carnegie|exane|oddo|truist|mizuho", re.I)


def an_title(s, comp):
    return bool(re.search(r"analyst", s, re.I)) or (bool(s.strip()) and not comp.search(s) and (bool(FIRM.search(s)) or (" at " in s and not EXEC_TITLE.search(s))))


def ex_title(s, comp):
    if not s or not s.strip() or re.search(r"analyst", s, re.I):
        return False
    return bool(comp.search(s)) or (bool(EXEC_TITLE.search(s)) and not FIRM.search(s))


def norm(s):
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def last(s):
    n = norm(re.sub(r"\(.*?\)", "", s)).split()
    return n[-1] if n else ""


def layout(text):
    head = text[:400]
    if len(re.findall(r"^\*\*[^*]{2,90}:\*\*", text, re.M)) >= 5:
        return "md"
    if "fool.com" in head and len(re.findall(r"Analyst \([^)]+\)\. ", text)) >= 3:
        return "fool_inline"
    if "allmind" in head:
        return "allmind"
    if "roic.ai" in head:
        return "roic"
    if "benzinga" in head:
        return "benzinga"
    if "format: pdf" in head:
        return "lseg"
    if re.search(r"^\*\*[^*]{2,90}:\*\*", text, re.M):
        return "md"
    return "fool"


def raw_turns(text, lay):
    """[(line, label, title, text)] in document order."""
    lines = text.split("\n")
    out, cur = [], None

    def add(i, lab, title, body):
        nonlocal cur
        cur = [i + 1, lab.strip(), title.strip(), body.strip()]
        out.append(cur)

    start = 0
    if lay == "fool_inline":
        # "Operator. ... Analyst (Name). ... Exec Name. ..." run together; exec names from CALL PARTICIPANTS
        m = re.search(r"CALL PARTICIPANTS(.*?)TAKEAWAYS", text, re.S)
        names = [l.split(" - ")[-1].strip() for l in (m.group(1).split("\n") if m else []) if " - " in l]
        k = text.find("Full Conference Call Transcript")
        body = text[k:]
        alts = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
        rx = re.compile(r"(?:(?<=^)|(?<=[.?!] )|(?<=\n))(Operator|Analyst \(([^)]+)\)" + (("|" + alts) if alts else "") + r")\. ")
        pos = [(mm.start(), mm.end(), mm.group(1), mm.group(2)) for mm in rx.finditer(body)]
        base_line = text[:k].count("\n")
        for n, (a, b, lab, an) in enumerate(pos):
            end = pos[n + 1][0] if n + 1 < len(pos) else len(body)
            ln = base_line + body[:a].count("\n") + 1
            seg = re.sub(r"\[\[page[^\]]*\]\]", " ", body[b:end])
            out.append([ln, an if an else lab, "Analyst" if an else ("" if lab == "Operator" else "AbbVie"), re.sub(r"\s+", " ", seg).strip()])
        return out
    if lay == "fool":
        for i, l in enumerate(lines):
            if l.strip().startswith("Full Conference Call Transcript"):
                start = i + 1
                break
        else:
            for i, l in enumerate(lines):
                if l.strip() == "SUMMARY":
                    start = i + 14
    i = start
    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if not s or NOISE.search(l):
            i += 1
            continue
        if lay == "md":
            m = re.match(r"^\*\*([^*(]{1,80}?)(?: \(([^)]*)\))?:\*\*\s*(.*)$", s)
            if m:
                add(i, m.group(1), m.group(2) or "", m.group(3))
                i += 1
                continue
        elif lay == "fool":
            m = re.match(r"^([A-Z][A-Za-zÀ-ſ.'’ -]{1,50}?)(?: \(([^)]*)\))?:\s+(.*)$", s)
            if m and len(m.group(1).split()) <= 5:
                add(i, m.group(1), m.group(2) or "", m.group(3))
                i += 1
                continue
        elif lay == "lseg":
            if s == "Operator":
                add(i, "Operator", "", "")
                i += 1
                continue
            m = re.match(r"^([A-Z][A-Za-zÀ-ſ.'’ ]{2,40}?)\s?-\s?(.{2,80}?)\s?-\s?(.{2,120})$", s)
            if m and len(s) < 170 and (re.search(r"analyst", m.group(3), re.I) or EXEC_TITLE.search(m.group(3))):
                add(i, m.group(1), m.group(2) + " | " + m.group(3), "")
                i += 1
                continue
        elif lay == "roic":
            if re.fullmatch(r"[A-Z]{1,2}", s):
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    add(j, lines[j], "", "")
                    i = j + 1
                    continue
        elif lay == "benzinga":
            if l.startswith(" ") and len(s) < 140 and not re.search(r"[.?!]$", s) and (
                    s == "OPERATOR" or re.match(r"^[A-Z][A-Za-zÀ-ſ.'’ -]{2,40}(,.*)?$", s)) and len(s.split(",")[0].split()) <= 5:
                parts = s.split(",", 1)
                add(i, "Operator" if s == "OPERATOR" else parts[0], parts[1] if len(parts) > 1 else "", "")
                i += 1
                continue
        elif lay == "allmind":
            m = re.match(r"^\s*(Speaker #\d+|[A-Z][A-Za-zÀ-ſ.' -]{1,40}?)\s?:\s(.*)$", l)
            if m:
                add(i, m.group(1), "", m.group(2))
                i += 1
                continue
        if cur is not None:
            cur[3] += " " + s
        i += 1
    # merge consecutive same label; drop near-duplicate consecutive turns (allmind double tracks)
    merged = []
    for t in out:
        if merged and merged[-1][1] == t[1]:
            merged[-1][3] += " " + t[3]
        elif merged and lay == "allmind" and t[3][:60] and t[3][:60] in merged[-1][3]:
            continue
        else:
            merged.append(t)
    return merged


def participants(text, tk):
    """Names from participants lists: (execs, analysts)."""
    ex, an = set(), set()
    m = re.search(r"CORPORATE PARTICIPANTS(.*?)CONFERENCE CALL PARTICIPANTS(.*?)(PRESENTATION|Operator)", text, re.S)
    if m:
        for l in m.group(1).split("\n"):
            if l.strip():
                ex.add(last(re.split(COMPANY[tk], l, flags=re.I)[0]))
        for l in m.group(2).split("\n"):
            if l.strip():
                an.add(last(" ".join(l.split()[:3])) if False else norm(l).split()[1] if len(norm(l).split()) > 1 else "")
    m = re.search(r"CALL PARTICIPANTS(.*?)(RISKS|TAKEAWAYS|Need a quote)", text, re.S)
    if m:
        for l in m.group(1).split("\n"):
            if "—" in l:
                ex.add(last(l.split("—")[-1]))
    ex.discard("")
    an.discard("")
    return ex, an


QA_RX = re.compile(r"first\s?question|open\s?(up\s?)?the\s?(call|line|lines|floor)\s?(up\s?)?(for|to)\s?(questions|q&a)|"
                   r"ready\s?(for|to\s?take)\s?(the\s?)?(q&a|questions|first)|move\s?to\s?(the\s?)?q&a|begin\s?the\s?question|"
                   r"operator\s?instructions|question-and-answer session|take\s?your\s?questions", re.I)


def qa_start(turns, text=None, strict=False):
    if text and "QUESTIONS AND ANSWERS" in text:
        ln = text[:text.index("QUESTIONS AND ANSWERS")].count("\n") + 1
        for k, t in enumerate(turns):
            if t[0] >= ln:
                return k
    for k, t in enumerate(turns):
        if k > 2 and QA_RX.search(t[3]) and not re.search(r"after the speaker", t[3], re.I):
            # the analyst cannot be before this turn; start at the turn itself
            return k
    return None if strict else len(turns) // 2


def classify(text, tk, roster=None):
    lay = layout(text)
    turns = raw_turns(text, lay)
    k0 = qa_start(turns, text)
    roster = roster or {"E": set(), "A": set()}
    ex, an = participants(text, tk)
    ex |= roster["E"]
    an |= roster["A"]
    comp = re.compile(COMPANY[tk], re.I)
    for t in turns[:k0]:
        if t[1].lower() != "operator" and lay != "allmind" and last(t[1]) not in an:
            ex.add(last(t[1]))
    out = []
    pending_intro = False
    intro_names = set()
    intro_text = ""
    prev_role = None
    for k, (ln, lab, title, body) in enumerate(turns):
        if k < k0:
            continue
        L = last(lab)
        is_op = lab.lower() == "operator"
        if lay == "allmind":
            if INTRO.search(body) and (len(body) < 600 or k == k0):
                role = "O"
                pending_intro = True
                intro_text = body
            elif pending_intro and prev_role == "O" and lab == out[-1][1] if out else False:
                role = "O"
            elif pending_intro:
                role = "A"
                pending_intro = False
            elif prev_role == "A" and lab == out[-1][1]:
                role = "A"
            else:
                role = "E"
            spk = lab
            if role == "A":
                nm = [a + (", " + b if b else "") for a, b in INTRO_NAME.findall(intro_text)]
                spk = f"{lab} (introduced as {nm[-1]})" if nm else lab
            out.append((ln, spk, role, body))
            prev_role = role
            continue
        if is_op:
            role = "O"
        elif an_title(title + " " + lab, comp):
            role = "A"
        elif ex_title(title, comp):
            role = "E"
        elif L in an:
            role = "A"
        elif L in ex:
            role = "E"
        elif L and L in intro_names:
            role = "A"
        elif pending_intro:
            role = "A"
        else:
            role = "E"
        if (role == "E" and prev_role == "O" and pending_intro and len(body) > 80 and "?" in body[:700]
                and re.match(r"\W*(great|hi|hey|thank|thanks|good (morning|afternoon)|yes|yeah|i have|so|maybe|[A-Z][a-z]+ [A-Z][a-z]+ from)", body, re.I)
                and not re.search(r"question,? [A-Z][a-z]+[.,]", body[:120])):
            role = "A"
            nm = [a + (", " + b if b else "") for a, b in INTRO_NAME.findall(intro_text)]
            lab = f"{lab} [source mislabel; introduced as {nm[-1] if nm else '?'}]"
        if role == "O" or (role == "E" and INTRO.search(body) and len(body) < 500):
            if INTRO.search(body):
                pending_intro = True
                intro_text = body
                intro_names = {last(n) for n in NAME_RX.findall(body)}
                for n in NAME_RX.findall(body):
                    for w in norm(n).split():
                        intro_names.add(w)
        elif role == "A":
            pending_intro = False
            an.add(L)
        else:
            pending_intro = False
        if role == "A" and re.fullmatch(r"(unknown )?analyst", lab.strip(), re.I):
            nm = [a + (", " + b if b else "") for a, b in INTRO_NAME.findall(intro_text)]
            lab = f"{lab} (introduced as {nm[-1]})" if nm else lab
        out.append((ln, lab, role, body))
        prev_role = role
    return lay, k0, clean(out, lay)


ANSWER_START = re.compile(r"^\W*(yes,? of course|okay\.? so|so,? [A-Z][a-z]+,|[A-Z][a-z]+,? thank(s| you)( very much)? for (the|your|those)|"
                          r"thanks?,? [A-Z][a-z]+\.? (so|let me|i)|let me (take|start)|i'?ll (take|start)|we|and )", re.I)


def clean(out, lay):
    """Drop page-footer pseudo-turns, demote allmind answer-like 'analyst' turns, dedupe repeated questions."""
    res, seen, used, recent = [], set(), set(), []
    for ln, lab, role, body in out:
        if re.fullmatch(r"(subscribe|benzinga research|terms.*|ad)", lab.strip(), re.I):
            break
        if role == "A":
            key = re.sub(r"[^a-z0-9]", "", body.lower())[:60]
            if key in seen:
                continue
            seen.add(key)
            words = set(re.findall(r"[a-z]{4,}", body.lower()[:600]))
            if lay == "allmind" and any(len(words & w) / max(1, len(words | w)) > 0.45 for w in recent[-3:]):
                continue
            recent.append(words)
            if lay == "allmind" and (ANSWER_START.search(body) or not re.search(r"\?|question|thank(s| you) for taking", body[:500], re.I)):
                role = "E"
            if "(introduced as" in lab and re.fullmatch(r"(unknown )?analyst \(introduced as .*\)", lab, re.I):
                if lab in used:
                    lab = f"Analyst (unnamed in source, line {ln})"
                used.add(lab)
        res.append((ln, lab, role, body))
    return res


def roster_for(files, tk):
    """Cross-quarter roster: exec = titled exec labels or pre-Q&A speakers; analyst = labeled analysts."""
    E, A = set(), set()
    for f in files:
        text = Path(f).read_text()
        lay = layout(text)
        if lay == "allmind":
            continue
        turns = raw_turns(text, lay)
        k0 = qa_start(turns, text, strict=True)
        comp = re.compile(COMPANY[tk], re.I)
        ex, an = participants(text, tk)
        E |= ex
        A |= an
        for k, t in enumerate(turns):
            if t[1].lower() == "operator":
                for nm in INTRO_NAME.findall(t[3]):
                    A.add(last(nm[0]))
            if an_title(t[2] + " " + t[1], comp):
                A.add(last(t[1]))
            elif ex_title(t[2], comp):
                E.add(last(t[1]))
            elif k0 is not None and k < k0 and t[1].lower() != "operator":
                E.add(last(t[1]))
    # names labeled with exec titles or company stay exec even if an operator once said them
    titled = set()
    for f in files:
        text = Path(f).read_text()
        lay = layout(text)
        if lay == "allmind":
            continue
        comp = re.compile(COMPANY[tk], re.I)
        for t in raw_turns(text, lay):
            if ex_title(t[2], comp):
                titled.add(last(t[1]))
    A -= titled
    A.discard("analyst")
    A |= {"novod"}  # Michael Novod is a Nordea analyst (NVO calls), never an executive
    E.discard("novod")
    E -= A
    E.discard("")
    A.discard("")
    return {"E": E, "A": A}
