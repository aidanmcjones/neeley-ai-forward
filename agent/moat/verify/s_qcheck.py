"""Check that quote columns in a verified/secx CSV appear verbatim (whitespace and quote-style normalized) in the cited file.

usage: python -m agent.moat.verify.s_qcheck <csv> <quote_col>:<cite_col> [...]
"""
import csv
import re
import sys


def norm(s):
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    s = s.replace("​", " ").replace(" ", " ").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    path = sys.argv[1]
    pairs = [a.split(":") for a in sys.argv[2:]]
    cache = {}
    bad = 0
    n = 0
    for r in csv.DictReader(open(path)):
        for qc, cc in pairs:
            q, c = r.get(qc, ""), r.get(cc, "")
            if not q or not c:
                continue
            f = c.split(" ")[0]
            if f not in cache:
                try:
                    cache[f] = norm(open(f, errors="ignore").read())
                except FileNotFoundError:
                    cache[f] = None
            n += 1
            t = cache[f]
            if t is None or norm(q) not in t:
                bad += 1
                print("MISS", r.get("ticker"), qc, f, "|", q[:90])
    print(f"checked {n}, missing {bad}")


if __name__ == "__main__":
    main()
