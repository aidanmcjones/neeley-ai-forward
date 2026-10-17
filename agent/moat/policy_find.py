import re, sys
f, pat = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
w = int(sys.argv[4]) if len(sys.argv) > 4 else 160
txt = open(f).read()
page = "?"
pos = 0
parts = re.split(r"(\[\[page \d+ \| printed [^\]]+\]\])", txt)
k = 0
for part in parts:
    m = re.match(r"\[\[page (\d+) \| printed ([^\]]+)\]\]", part)
    if m:
        page = m.group(2)
        continue
    flat = " ".join(part.split())
    for m in re.finditer(pat, flat):
        print(f"[{page}] ...{flat[max(0, m.start()-20):m.end()+w]}")
        k += 1
        if k >= n: sys.exit()
