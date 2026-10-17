"""Scratch: grep a regex across page-marked docs, print page hits. usage: cv_peek REGEX FILE [FILE...]"""
import re
import sys
from agent.moat.verify.pe_lib import pages
rx = re.compile(sys.argv[1], re.I)
lim = 6
for f in sys.argv[2:]:
    n = 0
    for k, (pr, t) in pages(f).items():
        for m in rx.finditer(t):
            if n < lim:
                s = t[max(0, m.start() - 60):m.end() + 120].replace("\n", " ")
                print(f.split("/")[-1], k, pr, "|", s)
                n += 1
