"""Bullfincher / roic.ai style transcripts (speaker label lines, paragraphs) -> page-marked speaker-turn markdown."""
import re
import sys
import requests

from agent.corpus import html_to_text
from agent.moat.calls_mb import UA, render
from agent.moat.common import note_gap, write

JOBS = [
    ("PFE", "2025Q2", "2025-08-05", "https://bullfincher.io/companies/pfizer/earnings-call/fy2025-q2", "bull"),
    ("LLY", "2025Q2", "2025-08-07", "https://bullfincher.io/companies/eli-lilly-and-company/earnings-call/fy2025-q2", "bull"),
    ("AMGN", "2025Q2", "2025-08-05", "https://bullfincher.io/companies/amgen/earnings-call/fy2025-q2", "bull"),
    ("GILD", "2025Q2", "2025-08-07", "https://bullfincher.io/companies/gilead-sciences/earnings-call/fy2025-q2", "bull"),
    ("NVO", "2025Q2", "2025-08-06", "https://www.roic.ai/quote/NOVO-B.CO/transcripts/2025/2", "roic"),
]
SMALL = {"of", "and", "the", "de", "van", "von", "&", "for", "at", "to", "in", "a", "da", "la", "der"}
END = re.compile(r"^(Sign in|Changelog|Resources|Related|Disclaimer|Previous|Next quarter|Back to|Unlock|Summary Financials|"
                 r"Earnings Call Transcripts?|ROIC AI|Read more|Share|Footer|About)\b", re.I)
OWN_HINT = re.compile(r"\b(CEO|CFO|COO|Chief|Officer|President|Chairman|Executive|Vice|Head|Treasurer|VP|EVP|SVP|Investor Relations|"
                      r"Director of Investor|Secretary|Founder)\b", re.I)
FIRM_HINT = re.compile(r"\b(Inc|Group|Bank|Securities|Capital|Research|LLC|LP|Partners|Co\.?|Investment|Markets|Equity|"
                       r"Management|Sachs|Morgan|Stanley|Cowen|Barclays|Citi|Jefferies|Evercore|Wolfe|Bernstein|UBS|BMO|"
                       r"Leerink|Oppenheimer|Truist|Piper|Cantor|Mizuho|HSBC|Deutsche|RBC|Wells|Fargo|JPMorgan|Redburn)\b")


def is_label(l):
    l = l.strip()
    if not l or len(l) > 70 or l[-1] in ".?!,;:\"" or l.startswith("["):
        return False
    words = l.replace("/", " ").split()
    if len(words) > 9:
        return False
    return all(w[0].isupper() or w.lower() in SMALL or w[0] in "&(" for w in words)


def parse(html, kind):
    return parse_lines([l.strip() for l in html_to_text(html).split("\n")])


def parse_lines(lines):
    start = next(i for i, l in enumerate(lines) if l.lower() == "operator" and i + 1 < len(lines))
    start = next(i for i, l in enumerate(lines) if l.lower() == "operator" and any(lines[j] for j in range(i + 1, i + 4)) and
                 len(next(x for x in lines[i + 1:i + 5] if x)) > 40)
    end = len(lines)
    for i in range(start + 50, len(lines)):
        if END.match(lines[i]) and len(lines[i]) < 60:
            end = i
            break
    paras = [l for l in lines[start:end] if l and not (len(l) <= 2 and l.isupper())]
    turns, cur = [], None
    i = 0
    while i < len(paras):
        p = paras[i]
        if is_label(p) and i + 1 < len(paras):
            labels = [p]
            j = i + 1
            while j < len(paras) and len(labels) < 3 and is_label(paras[j]) and j + 1 < len(paras):
                labels.append(paras[j])
                j += 1
            cur = {"name": labels[0], "role": " ".join(labels[1:]), "parts": []}
            turns.append(cur)
            i = j
            continue
        if cur is not None:
            cur["parts"].append(p)
        i += 1
    out = []
    seen_exec = set()
    qa = False
    for t in turns:
        t["text"] = " ".join(t.pop("parts"))
        if t["name"].lower() == "operator":
            t["name"] = "Operator"
        if not t["text"]:
            continue
        out.append(t)
    # classify
    for t in out:
        if t["name"] == "Operator":
            t["kind"] = "operator"
            if re.search(r"first question|next question|question comes from|line of", t["text"], re.I):
                qa = True
        elif not qa:
            t["kind"] = "executive"
            seen_exec.add(t["name"])
        else:
            if t["name"] in seen_exec or (t["role"] and OWN_HINT.search(t["role"]) and not FIRM_HINT.search(t["role"])):
                t["kind"] = "executive"
                seen_exec.add(t["name"])
            else:
                t["kind"] = "analyst"
    return out


def main():
    for t, q, d, u, kind in JOBS:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=60)
        r.encoding = "utf-8"
        if r.status_code != 200:
            note_gap("calls", t, f"{q} transcript", f"{u} HTTP {r.status_code}")
            print("MISS", t, q)
            continue
        turns = parse(r.text, kind)
        names = {}
        for x in turns:
            names[x["name"]] = names.get(x["name"], 0) + 1
        print(t, q, len(turns), sum(1 for x in turns if x["kind"] == "analyst"), sorted(names.items(), key=lambda z: -z[1])[:12])
        quality = "third_party"
        md, pages = render(turns, u, quality, d, t, q)
        write("calls", f"companies/{t}/transcripts/{q}_transcript.md", md, ticker=t, group="companies",
              doc_type="transcript", period=q, filed=d, source_url=u, quality=quality, pages=pages)


if __name__ == "__main__":
    main()
