"""Substantive-difference test and span rendering for c_cross."""
import re

NEGS = {"not", "no", "never", "without", "cannot", "none", "nor", "dont", "doesnt", "didnt", "isnt", "arent", "wasnt",
        "werent", "wont", "cant", "couldnt", "wouldnt", "shouldnt", "havent", "hasnt", "hadnt", "neither", "nothing"}
NUMW = {"million", "billion", "thousand", "hundred", "percent", "half", "double", "%"}


def uniq(ws):
    out = []
    for w in ws:
        if not out or out[-1] is not w:
            out.append(w)
    return out


def caps(orig, prev):
    s = set()
    for i, w in enumerate(orig):
        p = prev if i == 0 else orig[i - 1]
        if w[:1].isupper() and not (p or ".").endswith((".", "?", "!")) and len(w.strip(".,;:?!\"'")) > 3:
            s.add(re.sub(r"[^a-z0-9]", "", w.lower()))
    return s


def substantive(an, bn, ao, bo, aprev="", bprev=""):
    why = []
    na = [x for x in an if re.search(r"\d", x) or x in NUMW]
    nb = [x for x in bn if re.search(r"\d", x) or x in NUMW]
    if na != nb:
        why.append("number")
    if bool(set(an) & NEGS) != bool(set(bn) & NEGS):
        why.append("negation")
    ca, cb = caps(ao, aprev), caps(bo, bprev)
    if ca and cb and ca != cb:
        why.append("name")
    return why
