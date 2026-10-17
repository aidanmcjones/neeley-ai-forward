"""Peek helper: python -m agent.moat.verify.m_peek file start n [grep] ++ file start n [grep] ..."""
import re
import sys

args = sys.argv[1:]
jobs, cur = [], []
for a in args:
    if a == "++":
        jobs.append(cur)
        cur = []
    else:
        cur.append(a)
jobs.append(cur)
for job in jobs:
    f, a, n = job[0], int(job[1]), int(job[2])
    print("=====", f)
    lines = open(f).read().split("\n")
    if len(job) > 3:
        rx = re.compile(job[3], re.I)
        k = 0
        for i, l in enumerate(lines):
            if i >= a and rx.search(l):
                print(i + 1, l[:220])
                k += 1
                if k >= n:
                    break
    else:
        for i in range(a, min(a + n, len(lines))):
            if lines[i].strip():
                print(i + 1, lines[i][:260])
