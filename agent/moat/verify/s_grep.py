"""Grep a page-marked markdown file and print hits with their [[page N | printed M]] marker.

usage: python -m agent.moat.verify.s_grep <file> <regex> [context_chars] [max_hits]
"""
import re
import sys

PAGE = re.compile(r"\[\[page (\d+) \| printed ([^\]]*)\]\]")


def pages(text):
    marks = [(m.start(), m.group(1), m.group(2).strip()) for m in PAGE.finditer(text)]
    return marks


def where(marks, pos):
    cur = ("?", "?")
    for start, p, pr in marks:
        if start <= pos:
            cur = (p, pr)
        else:
            break
    return cur


def main():
    path, pat = sys.argv[1], sys.argv[2]
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    text = open(path, encoding="utf-8", errors="ignore").read()
    marks = pages(text)
    n = 0
    for m in re.finditer(pat, text, re.I):
        p, pr = where(marks, m.start())
        snip = text[max(0, m.start() - ctx): m.end() + ctx].replace("\n", " ")
        print(f"--- pdf {p} printed {pr} @ {m.start()}\n{snip}\n")
        n += 1
        if n >= mx:
            break
    print(f"hits shown: {n}")


if __name__ == "__main__":
    main()
