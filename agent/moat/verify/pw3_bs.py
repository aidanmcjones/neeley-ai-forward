"""Wave 3: print the balance-sheet region of cached filings. Usage: pw3_bs.py anchor_regex before after file [file ...]"""
import re, sys, pathlib
from agent.moat.verify.pw3_docs import text

anchor, before, after = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for f in sys.argv[4:]:
    t = re.sub(r"[\s|​]+", " ", text(pathlib.Path("data/moat/verify/pp_cache/w3/" + f).read_text()))
    hits = [m.start() for m in re.finditer(anchor, t, re.I)]
    print("=====", f, "hits", len(hits))
    if hits:
        i = hits[0]
        print(t[max(0, i - before): i + after])
    print()
