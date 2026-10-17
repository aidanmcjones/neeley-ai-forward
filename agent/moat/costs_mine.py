"""Mine page-marked annual reports for headcount, advertising expense and sales-force statements. Writes candidates to scratch."""
import glob
import json
import re
import sys

PAGE = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")
PATS = {
    "headcount": re.compile(r"[^.\n]{0,160}\b(?:employ(?:ed|s)|had|workforce of|headcount)[^.\n]{0,80}?\b\d{1,3},\d{3}\b[^.\n]{0,160}|"
                            r"[^.\n]{0,100}\b\d{1,3},\d{3}\s+(?:employees|people|full-time|permanent)[^.\n]{0,120}", re.I),
    "advertising": re.compile(r"[^.\n]{0,200}\badvertising\b[^.\n]{0,200}?\$\s?[\d,.]+\s*(?:million|billion)?[^.\n]{0,120}", re.I),
    "salesforce": re.compile(r"[^.\n]{0,160}\b(?:sales force|field force|sales representatives|salesforce|field-based|medical representatives)\b[^.\n]{0,200}", re.I),
}
KEEP = {"headcount": 3, "advertising": 4, "salesforce": 4}


def main():
    files = sorted(glob.glob("data/corpus/companies/*/10k_*.md") + glob.glob("data/corpus/companies/*/20f_*.md")
                   + glob.glob("data/corpus/peers/*/10k_*.md") + glob.glob("data/corpus/peers/*/20f_*.md")
                   + glob.glob("data/moat/companies/*/10k_*.md") + glob.glob("data/moat/companies/*/20f_*.md")
                   + glob.glob("data/moat/companies/*/ar_*.md"))
    out = []
    for f in files:
        txt = open(f, errors="ignore").read()
        parts = PAGE.split(txt)
        # parts: [pre, page, printed, text, page, printed, text...]
        pages = [(parts[i], parts[i + 1], parts[i + 2]) for i in range(1, len(parts) - 2, 3)]
        for kind, rx in PATS.items():
            n = 0
            for pg, pr, body in pages:
                for m in rx.finditer(body):
                    s = " ".join(m.group(0).split())
                    if kind == "headcount" and not re.search(r"employ|workforce|headcount", s, re.I):
                        continue
                    out.append({"file": f, "kind": kind, "page": pg, "printed": pr, "text": s[:420]})
                    n += 1
                    if n >= KEEP[kind] * 3:
                        break
                if n >= KEEP[kind] * 3:
                    break
    json.dump(out, open("data/moat/scratch/costs_mine.json", "w"))
    print(len(files), len(out))


main()
