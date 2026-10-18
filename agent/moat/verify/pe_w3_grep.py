"""Wave 3 epi verifier helper: grep a downloaded primary-source text file with context (whitespace collapsed).
Usage: python agent/moat/verify/pe_w3_grep.py <file> <regex> [max_hits] [context_chars]"""
import re
import sys

f = open(sys.argv[1], encoding="utf-8", errors="replace").read()
f = re.sub(r"\s+", " ", f)
n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
c = int(sys.argv[4]) if len(sys.argv) > 4 else 220
for i, m in enumerate(re.finditer(sys.argv[2], f)):
    if i >= n:
        break
    print(">>", f[max(0, m.start() - c):m.end() + c])
    print()
print("-----")
