import re
from pathlib import Path
from agent.moat.deals_extract import *
import collections
c = collections.Counter(); ex = collections.defaultdict(list)
for p in sorted(OUTD.glob("*.md"))[:279]:
    raw = p.read_text(); bt = re.sub(r"\s+"," ",raw)
    pm = re.search(r"PRESS RELEASE|News Release|FOR IMMEDIATE RELEASE|Exhibit 99\.?\s?1", bt)
    start = pm.end() if pm else 0
    if SKIP_TITLE.search(bt[start:start+350]): k="skiptitle"
    elif not DEAL_KW.search(bt[start:start+900]): k="nodealkw"
    else:
        sents = sentences(bt); up,eq,ms,tot,q = econ(sents,"x")
        k = "noecon" if (up is None and tot is None and ms is None) else "ok"
    c[k]+=1; ex[k].append(p.name)
print(c)
for k in ("noecon","nodealkw"):
    for n in ex[k][:4]:
        t=re.sub(r"\s+"," ",(OUTD/n).read_text())
        i=t.find("[[page"); print(k,n,t[i+30:i+500]); print()
