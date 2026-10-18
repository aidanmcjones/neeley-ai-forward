"""Find FY2026 revenue guidance lines in each company's latest earnings release(s); prints file, page, line."""
import re
import sys
from agent.moat.verify.m_qa import ROOT

RX = re.compile(r"(total revenues?|revenues?|sales|worldwide revenue)[^.\n]{0,160}(\$|DKK|billion|%)[^.\n]{0,160}|"
                r"(guidance|outlook|expects?)[^.\n]{0,120}(revenue|sales)[^.\n]{0,160}", re.I)
want = sys.argv[1:] or ["ABBV", "AMGN", "AZN", "BMY", "GILD", "JNJ", "LLY", "MRK", "NVO", "PFE"]
for tk in want:
    d = ROOT / "data/corpus/companies" / tk / "earnings"
    fs = sorted(d.glob("*.md")) if d.exists() else []
    fs += sorted((ROOT / "data/corpus/companies" / tk).glob("10q_2026Q2.md"))
    latest = [f for f in fs if f.name[:7] >= "2026-07"] or fs[-3:]
    print("####", tk, [f.name for f in latest])
    for f in latest:
        page = "?"
        n = 0
        for i, l in enumerate(f.read_text().split("\n")):
            m = re.match(r"\[\[page (\d+) \| printed ([^\]]*)\]\]", l)
            if m:
                page = f"{m.group(1)} (printed {m.group(2).strip()})"
                continue
            if re.search(r"2026", l) and re.search(r"guidance|outlook|expect|full[- ]year", l, re.I) and re.search(r"revenue|sales", l, re.I) and n < 6:
                print(f"  {f.name} p{page} L{i + 1}: {l.strip()[:330]}")
                n += 1
