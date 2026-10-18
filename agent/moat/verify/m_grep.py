"""grep with page numbers: m_grep <regex> <file> [<file> ...] (max 8 hits per file)."""
import re
import sys

rx = re.compile(sys.argv[1], re.I)
for f in sys.argv[2:]:
    page, n = "?", 0
    for i, l in enumerate(open(f).read().split("\n")):
        m = re.match(r"\[\[page (\d+) \| printed ([^\]]*)\]\]", l)
        if m:
            page = f"{m.group(1)}/printed {m.group(2).strip()}"
            continue
        if rx.search(l) and n < 8:
            print(f"{f.split('/')[-1]} p{page} L{i + 1}: {l.strip()[:320]}")
            n += 1
