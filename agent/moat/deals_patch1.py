import re
p='agent/moat/deals_extract.py'; s=open(p).read()
s=s.replace('''    start = pm.end() if pm else 0
    head = bt[start:start + 900]''','''    if pm:
        start = pm.end()
    else:
        im0 = re.search(r"Item\\s+(?:1\\.01|8\\.01|2\\.01|7\\.01)", bt)
        start = im0.start() if im0 else 0
    head = bt[start:start + 900]''')
s=s.replace("if not DEAL_KW.search(head):","if not DEAL_KW.search(bt[start:start + 3000]):")
s=s.replace('''    q = (quote or "")[:300]''','''    q = window(quote or "")''')
s=s.replace('''def clean_name(n):''','''def window(q):
    q = q.strip()
    if len(q) <= 300:
        return q
    a = amounts(q)
    i = a[0][1] if a else 0
    lo = max(0, i - 150)
    return q[lo:lo + 300].strip()


def clean_name(n):''')
s=s.replace('cand.split()[0] not in ("The"','cand.split()[0] not in ("Exhibits", "Exhibit", "San", "New", "The"')
open(p,'w').write(s)
p='agent/moat/deals_lib.py'; s=open(p).read()
s=s.replace('''    t = re.sub(r"\\s+", " ", text)
    return''','''    t = re.sub(r"\\s+", " ", text).replace(" • ", ". ").replace(" ● ", ". ").replace("•", ". ")
    return''')
open(p,'w').write(s)
