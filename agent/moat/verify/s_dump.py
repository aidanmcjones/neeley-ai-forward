"""Dump a company's SEC comment letters compactly (whitespace collapsed, staff boilerplate trimmed).

usage: python -m agent.moat.verify.s_dump <TICKER> [substring_filter] [max_chars_per_letter]
"""
import re
import sys
from pathlib import Path

ROOT = Path("data/moat/companies")
BOILER = [
    r"Please respond to this letter within ten business days.*?additional comments\.",
    r"We remind you that the company and its management are responsible.*?by the staff\.",
    r"Please contact [A-Z].*?questions\.",
]


def main():
    t = sys.argv[1]
    flt = sys.argv[2] if len(sys.argv) > 2 else ""
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    for p in sorted((ROOT / t / "sec_letters").glob("*.md")):
        if flt and flt not in p.name:
            continue
        s = p.read_text(errors="ignore")
        s = re.sub(r"\s+", " ", s)
        for b in BOILER:
            s = re.sub(b, "", s, flags=re.S)
        print(f"\n=== {p.name} ({len(s)} chars)\n{s[:mx]}")


if __name__ == "__main__":
    main()
