"""grep helper: p_grep <file> <regex> [width] [max]; whitespace-normalized, case-insensitive."""
import re
import sys

from agent.moat.common import ROOT

txt = " ".join((ROOT / sys.argv[1]).read_text(errors="replace").replace("\x00", "").split())
w = int(sys.argv[3]) if len(sys.argv) > 3 else 200
mx = int(sys.argv[4]) if len(sys.argv) > 4 else 10
for n, m in enumerate(re.finditer(sys.argv[2], txt, re.I)):
    if n >= mx:
        break
    print(f"[{m.start()}] ...{txt[max(0, m.start() - w): m.end() + w]}...\n")
