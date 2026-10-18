"""MarketBeat (Quartr-provided) call transcripts -> page-marked, speaker-turn markdown under data/moat.

Usage: python -m agent.moat.calls_mb discover   # brute-force URLs for the wanted calls, writes /tmp/gd/found.json
       python -m agent.moat.calls_mb build      # fetch + parse + write via common.write
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import requests

from agent.corpus import html_to_text
from agent.moat.common import header, note_gap, write

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
SLUG = {"MRK": "merck-co-inc", "BMY": "bristol-myers-squibb", "PFE": "pfizer-inc", "LLY": "eli-lilly-and-company",
        "NVO": "novo-nordisk-as", "ABBV": "abbvie-inc", "JNJ": "johnson-johnson", "AZN": "astrazeneca-plc-stock-1",
        "AMGN": "amgen-inc", "GILD": "gilead-sciences-inc"}
# known call dates (from the MarketBeat listing) for 2024Q3..2026Q2; None = brute force
KNOWN = {
    "MRK": {"2024Q3": "2024-10-31", "2024Q4": "2025-2-4", "2025Q1": "2025-4-24", "2025Q2": "2025-7-29", "2025Q3": "2025-10-30"},
    "BMY": {"2024Q3": "2024-10-31", "2024Q4": "2025-2-6", "2025Q1": "2025-4-24", "2025Q2": "2025-7-31", "2025Q3": "2025-10-30"},
    "PFE": {"2024Q3": "2024-10-29", "2024Q4": "2025-2-4", "2025Q1": "2025-4-29", "2025Q2": "2025-8-5", "2025Q3": "2025-11-4"},
    "LLY": {"2024Q3": "2024-10-30", "2024Q4": "2025-2-6", "2025Q1": "2025-5-1", "2025Q2": "2025-8-7", "2025Q3": "2025-10-30"},
    "NVO": {"2024Q4": "2025-2-5", "2025Q1": "2025-5-7", "2025Q2": "2025-8-6", "2025Q3": "2025-11-5", "2026Q1": "2026-5-6"},
    "ABBV": {"2024Q3": "2024-10-30", "2024Q4": "2025-1-31", "2025Q1": "2025-4-25", "2025Q2": "2025-7-31", "2025Q3": "2025-10-31"},
    "JNJ": {"2024Q4": "2025-1-22", "2025Q1": "2025-4-15", "2025Q2": "2025-7-16", "2025Q3": "2025-10-14"},
    "AZN": {"2024Q3": "2024-11-12", "2024Q4": "2025-2-6", "2025Q1": "2025-4-29", "2025Q2": "2025-7-29", "2025Q3": "2025-11-6", "2026Q1": "2026-4-29"},
    "AMGN": {"2024Q3": "2024-10-30", "2024Q4": "2025-2-4", "2025Q1": "2025-5-1", "2025Q2": "2025-8-5", "2025Q3": "2025-11-4"},
    "GILD": {"2024Q3": "2024-11-6", "2024Q4": "2025-2-11", "2025Q1": "2025-4-24", "2025Q2": "2025-8-7", "2025Q3": "2025-10-30"},
}
WINDOWS = {"2024Q1": (date(2024, 4, 9), date(2024, 5, 10)), "2024Q2": (date(2024, 7, 9), date(2024, 8, 12)),
           "2024Q3": (date(2024, 10, 9), date(2024, 11, 14))}
RAW = Path("/tmp/gd/raw")
FOUND = Path("/tmp/gd/found.json")


def url_for(t, d):
    s = SLUG[t]
    s = s if s.endswith("-1") else s + "-stock"
    return f"https://www.marketbeat.com/earnings/reports/{d.year}-{d.month}-{d.day}-{s}/"


def get(u):
    try:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=60)
        r.encoding = "utf-8"
        return r.status_code, r.text
    except Exception:
        return 0, ""


def has_call(html):
    return "Transcript Sections" in html and "Skip to Participants" in html


def discover():
    found = json.loads(FOUND.read_text()) if FOUND.exists() else {}
    jobs = []
    for t in SLUG:
        for q, (a, b) in WINDOWS.items():
            if q in KNOWN[t] or f"{t}:{q}" in found:
                continue
            d = a
            while d <= b:
                if d.weekday() < 5:
                    jobs.append((t, q, d))
                d += timedelta(days=1)

    def probe(j):
        t, q, d = j
        code, html = get(url_for(t, d))
        return j, code, html

    with ThreadPoolExecutor(6) as ex:
        for (t, q, d), code, html in ex.map(probe, jobs):
            if code == 200 and has_call(html):
                found[f"{t}:{q}"] = url_for(t, d)
                print("FOUND", t, q, d, flush=True)
    FOUND.write_text(json.dumps(found, indent=1))


def quarter_of(d):
    q = {1: 4, 2: 4, 3: 4, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3}[d.month]
    return f"{d.year - 1 if q == 4 else d.year}Q{q}"


TS = re.compile(r"^\s*(\d\d):(\d\d):(\d\d)\s*$")


def parse(html):
    text = html_to_text(html)
    try:
        text = text.encode("cp1252").decode("utf-8")
    except Exception:
        try:
            text = text.encode("latin-1").decode("utf-8")
        except Exception:
            pass
    lines = text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "Skip to Participants")
    except StopIteration:
        return None
    end = len(lines)
    for i in range(start, len(lines) - 2):
        if lines[i].strip() == "Read more":
            end = i
            break
    part_i = next((i for i in range(end, len(lines)) if lines[i].strip() == "Participants"), None)
    execs, analysts = {}, {}
    if part_i:
        cur = None
        buf = [l.strip() for l in lines[part_i + 1:part_i + 200] if l.strip()]
        i = 0
        while i < len(buf):
            if buf[i] == "Executives":
                cur = execs
            elif buf[i] == "Analysts":
                cur = analysts
            elif cur is not None and i + 1 < len(buf):
                if buf[i] in ("Read more",) or buf[i].startswith("Frequently"):
                    break
                cur[buf[i]] = buf[i + 1]
                i += 1
            i += 1
    names = set(execs) | set(analysts) | {"Operator"}
    _fix = lambda a, b: (a, b)
    body = lines[start + 1:end]
    ts_idx = [i for i, l in enumerate(body) if TS.match(l)]
    heads = []
    for ti in ts_idx:
        prev = [j for j in range(ti - 1, max(ti - 12, -1), -1) if body[j].strip()][:3]
        prev.reverse()
        name_j = next((j for j in prev if body[j].strip() in names), None)
        if name_j is None:
            name_j = prev[0] if prev else ti
        heads.append(name_j)
    turns = []
    for k, ti in enumerate(ts_idx):
        nj = heads[k]
        hdr = [body[j].strip() for j in range(nj, ti) if body[j].strip()]
        name = hdr[0] if hdr else "Unknown"
        role = hdr[-1] if len(hdr) > 1 and hdr[-1] != name else ""
        stop = heads[k + 1] if k + 1 < len(ts_idx) else len(body)
        txt = " ".join(l.strip() for l in body[ti + 1:stop] if l.strip())
        m = TS.match(body[ti])
        turns.append({"name": name, "role": role, "text": txt, "t": f"{m.group(1)}:{m.group(2)}:{m.group(3)}"})
    for t in turns:
        mm = re.match(r"^Analyst \((.+)\)$", t["name"])
        if mm:
            t["name"], t["role"] = mm.group(1), "Analyst"
        elif (" at " in t["name"] or re.search(r"Director|Analyst|Research|Officer|President|Partner|Head of", t["name"])) \
                and t["role"] and " at " not in t["role"] and len(t["role"].split()) <= 5:
            t["name"], t["role"] = t["role"], t["name"]

    QI = re.compile(r"question (?:comes |is coming |will come )?from (?:the line of )?([A-Z][\w.'\-]+(?: [A-Z][\w.'\-]+){0,3}),? (?:with|from|of|at|over at) ([A-Z][\w&.,'\- ]{1,40}?)(?:\.| Your| Please|,|$)")
    last_op = None
    for t in turns:
        if t["name"] == "Operator":
            last_op = QI.search(t["text"]) or last_op
        elif t["name"] == "Analyst" and last_op:
            t["name"], t["role"] = last_op.group(1), f"Analyst at {last_op.group(2).strip()}"
        elif " at " in t["name"]:
            title = t["name"]
            if last_op:
                t["name"], t["role"] = last_op.group(1), title
            else:
                t["name"], t["role"] = "Unidentified analyst", title

    def firm_of(role):
        return role.rsplit(" at ", 1)[1].strip() if " at " in role else ""

    own = ""
    for t in turns:
        if t["name"] != "Operator":
            f = firm_of(t["role"] or execs.get(t["name"], "") or analysts.get(t["name"], ""))
            if f and not t["role"].lower().startswith("analyst"):
                own = f
                break
    for t in turns:
        n = t["name"]
        role = t["role"] or execs.get(n, "") or analysts.get(n, "")
        f = firm_of(role)
        t["role"] = role
        if n == "Operator":
            t["kind"] = "operator"
        elif role.lower().startswith("analyst"):
            t["kind"] = "analyst"
        elif f and f == own:
            t["kind"] = "executive"
        elif not f:
            t["kind"] = "executive" if n in execs else "analyst"
        else:
            t["kind"] = "analyst"
    return turns


def render(turns, source, quality, call_date, ticker, quarter):
    out = [header(source, ticker=ticker, type="transcript", period=quarter, quality=quality, call_date=call_date,
                  format="html_quartr"), ""]
    page, acc = 1, 0
    out.append(f"[[page {page} | printed {page}]]\n")
    for t in turns:
        if t["text"] == "":
            continue
        if acc >= 3000:
            page += 1
            acc = 0
            out.append(f"[[page {page} | printed {page}]]\n")
        label = t["name"] + (f" ({t['role']})" if t["role"] else "")
        line = f"**{label}:** {t['text']}"
        out.append(line + "\n")
        acc += len(line)
    return "\n".join(out), page


def build(only=None):
    found = json.loads(FOUND.read_text()) if FOUND.exists() else {}
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = []
    for t in SLUG:
        for q, d in KNOWN[t].items():
            yy, mm, dd = map(int, d.split("-"))
            jobs.append((t, q, url_for(t, date(yy, mm, dd)), d))
    for k, u in found.items():
        t, q = k.split(":")
        mt = re.search(r"/(\d{4})-(\d+)-(\d+)-", u)
        jobs.append((t, q, u, f"{mt.group(1)}-{mt.group(2)}-{mt.group(3)}"))

    def fetch(j):
        t, q, u, d = j
        p = RAW / f"{t}_{q}.html"
        if p.exists():
            return j, 200, p.read_text()
        code, html = get(u)
        if code == 200:
            p.write_text(html)
        return j, code, html

    with ThreadPoolExecutor(5) as ex:
        res = list(ex.map(fetch, jobs))
    for (t, q, u, d), code, html in res:
        if only and f"{t}:{q}" not in only:
            continue
        if code != 200 or not has_call(html):
            note_gap("calls", t, f"{q} transcript", f"MarketBeat {u} -> HTTP {code} or no transcript")
            print("MISS", t, q, code)
            continue
        mdt = re.search(r"Provided by Quartr\s+([A-Z][a-z]+) (\d+), (\d{4})", html_to_text(html))
        if mdt:
            mon = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                   "November", "December"].index(mdt.group(1)) + 1
            d = f"{mdt.group(3)}-{mon}-{mdt.group(2)}"
            u = url_for(t, date(int(mdt.group(3)), mon, int(mdt.group(2))))
        turns = parse(html)
        if not turns or len(turns) < 5:
            note_gap("calls", t, f"{q} transcript", f"MarketBeat {u} parsed to {len(turns or [])} turns")
            print("BADPARSE", t, q)
            continue
        iso = "-".join(x.zfill(2) for x in d.split("-"))
        md, pages = render(turns, u, "third_party", iso, t, q)
        write("calls", f"companies/{t}/transcripts/{q}_transcript.md", md, ticker=t, group="companies",
              doc_type="transcript", period=q, filed=iso, source_url=u, quality="third_party", pages=pages)
        print("OK", t, q, iso, len(turns), len(md), sum(1 for x in turns if x["kind"] == "analyst"))


if __name__ == "__main__":
    if sys.argv[1] == "discover":
        discover()
    else:
        build(set(sys.argv[2:]) or None)
