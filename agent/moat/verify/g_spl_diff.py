"""Which top-level SPL sections differ between two cached versions (python -m ... <setid> <v_old> <v_new>)."""
import re
import sys

from agent.drug_pack import NS
from agent.moat.verify.g_newlaunch_labels import xml


def tops(root):
    out = {}
    for s in root.xpath("//v3:structuredBody/v3:component/v3:section", namespaces=NS):
        code = (s.xpath("./v3:code/@code", namespaces=NS) or ["?"])[0]
        title = " ".join(s.xpath("./v3:title//text()", namespaces=NS)).strip()[:60]
        out[f"{code} {title}"] = re.sub(r"\s+", " ", " ".join(s.itertext())).strip()
    return out


setid, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
A, B = tops(xml(setid, a)), tops(xml(setid, b))
for k in sorted(set(A) | set(B)):
    if A.get(k) != B.get(k):
        print("DIFF", k, len(A.get(k, "")), len(B.get(k, "")))
bw = [k for k in A if k.startswith("34066-1")]
print("boxed v%d:" % a, bw, (A[bw[0]][:300] if bw else ""))
