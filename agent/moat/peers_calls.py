"""Peer transcripts 2024Q1-2025Q2 from MarketBeat (Quartr), via calls_mb parse/render. Third-party => quality C.
Discovery follows MarketBeat's redirect-to-nearest-report behaviour and keys on the final URL's date."""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from agent.corpus import html_to_text
from agent.moat import calls_mb as mb
from agent.moat.common import write, note_gap, OUT

SLUG = {"NVS": "novartis-ag", "GSK": "glaxosmithkline-plc", "SNY": "sanofi", "TAK": "takeda-pharmaceutical-company-limited",
        "REGN": "regeneron-pharmaceuticals-inc", "ALNY": "alnylam-pharmaceuticals-inc", "BBIO": "bridgebio-pharma-inc",
        "ROCHE": "roche-holding-ag"}
WIN = {"2024Q1": (date(2024, 4, 1), date(2024, 5, 20)), "2024Q2": (date(2024, 7, 1), date(2024, 8, 20)),
       "2024Q3": (date(2024, 10, 1), date(2024, 11, 20)), "2024Q4": (date(2025, 1, 15), date(2025, 3, 10)),
       "2025Q1": (date(2025, 4, 1), date(2025, 5, 20)), "2025Q2": (date(2025, 7, 1), date(2025, 8, 20))}
if len(sys.argv) > 1:
    SLUG = {k: v for k, v in SLUG.items() if k in sys.argv[1].split(",")}
DATE_RE = re.compile(r"/reports/(\d{4})-(\d+)-(\d+)-")


def label(t, d):
    if t == "TAK":  # fiscal naming like the corpus (FY ends March)
        m = d.month
        if m in (7, 8): return f"{d.year}Q1"
        if m in (10, 11): return f"{d.year}Q2"
        if m in (1, 2): return f"{d.year - 1}Q3"
        return f"{d.year - 1}Q4"
    return mb.quarter_of(d)


def probe(j):
    t, d = j
    u = f"https://www.marketbeat.com/earnings/reports/{d.year}-{d.month}-{d.day}-{SLUG[t]}-stock/"
    try:
        r = mb.requests.get(u, headers={"User-Agent": mb.UA}, timeout=60)
        r.encoding = "utf-8"
        return t, r.url, r.text
    except Exception:
        return t, "", ""


def main():
    jobs = []
    for t in SLUG:
        for q, (a, b) in WIN.items():
            d = a
            while d <= b:
                if d.weekday() < 5:
                    jobs.append((t, d))
                d += timedelta(days=1 if len(sys.argv) > 2 else 3)
    found = {}
    with ThreadPoolExecutor(6) as ex:
        for t, url, html in ex.map(probe, jobs):
            m = DATE_RE.search(url)
            if m and mb.has_call(html) and SLUG[t] in url:
                found.setdefault((t, url), html)
    print("candidate reports", len(found), flush=True)
    got = {}
    for (t, url), html in sorted(found.items()):
        m = DATE_RE.search(url)
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        mdt = re.search(r"Provided by Quartr\s+([A-Z][a-z]+) (\d+), (\d{4})", html_to_text(html))
        q = label(t, d)
        if not any(a <= d <= b for a, b in WIN.values()):
            continue
        turns = mb.parse(html)
        if not turns or len(turns) < 5:
            note_gap("peers", t, f"{q} transcript", f"MarketBeat {url} parsed to {len(turns or [])} turns")
            continue
        md, pages = mb.render(turns, url, "third_party", d.isoformat(), t, q)
        rel = f"companies/{t}/transcripts/{q}_transcript.md"
        if (OUT / rel).exists():
            continue
        write("peers", rel, md, ticker=t, group="companies", doc_type="transcript", period=q, filed=d.isoformat(),
              source_url=url, quality="C", pages=pages)
        got.setdefault(t, []).append(q)
        print("OK", t, q, d, len(turns), flush=True)
    for t in SLUG:
        for q in WIN:
            if q not in got.get(t, []) and not (OUT / f"companies/{t}/transcripts/{q}_transcript.md").exists():
                note_gap("peers", t, f"{q} transcript", "no MarketBeat/Quartr transcript found; no other free source tried")
                print("MISS", t, q)


main()
