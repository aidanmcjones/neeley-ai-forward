import re, sys, glob
pat = re.compile(sys.argv[2], re.I)
maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 40
for f in sorted(glob.glob(sys.argv[1])):
    txt = open(f).read()
    parts = re.split(r"(\[\[page \d+ \| printed [^\]]+\]\])", txt)
    page = "?"
    n = 0
    print("=====", f)
    for part in parts:
        m = re.match(r"\[\[page (\d+) \| printed ([^\]]+)\]\]", part)
        if m:
            page = m.group(2) if m.group(2) != "?" else "p" + m.group(1)
            continue
        flat = " ".join(part.split())
        for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z“])", flat):
            if pat.search(s) and 40 < len(s) < 700:
                print(f"[{page}] {s}")
                n += 1
                if n >= maxn: break
        if n >= maxn: break
