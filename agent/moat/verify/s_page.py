"""Print pdf pages N..M of a page-marked markdown file, whitespace collapsed.

usage: python -m agent.moat.verify.s_page <file> <first> [last] [max_chars_per_page]
"""
import re
import sys


def main():
    path, a = sys.argv[1], int(sys.argv[2])
    b = int(sys.argv[3]) if len(sys.argv) > 3 else a
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 8000
    text = open(path, errors="ignore").read()
    parts = re.split(r"(\[\[page \d+ \| printed [^\]]*\]\])", text)
    for i in range(1, len(parts), 2):
        n = int(re.search(r"page (\d+)", parts[i]).group(1))
        if a <= n <= b:
            body = re.sub(r"\s+", " ", parts[i + 1])
            print(f"\n{parts[i]}\n{body[:mx]}")


if __name__ == "__main__":
    main()
