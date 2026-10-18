"""Usage: python -m agent.moat.verify.f_grep <path> <regex> [width]  -> prints page|printed: snippet"""
import re, sys
from agent.moat.verify.f_lib import pages

path, pat = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 250
n = 0
for pg, printed, body in pages(path):
    body = re.sub(r"\s+", " ", body)
    for m in re.finditer(pat, body, re.I):
        print(f"[p{pg}|printed {printed}] ...{body[max(0, m.start() - w): m.end() + w]}...")
        n += 1
        if n > 12:
            sys.exit()
