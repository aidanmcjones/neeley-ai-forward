"""Wave 3: run pw3_docs checks for a named batch and write snippets to data/moat/verify/pw3_docs_<batch>.txt."""
import re, sys
from agent.moat.verify.pw3_docs import get, main_doc, text

B = {
    "cover": [
        ("TEM", "1717115:0001193125-26-326090", [r"Class A common stock.{0,80}outstanding", r"outstanding as of"]),
        ("KNSA", "1730430:0001104659-26-087545", [r"outstanding as of", r"common shares.{0,60}outstanding"]),
        ("ALMS", "1847367:0001847367-26-000018", [r"outstanding as of", r"shares of .{0,60}outstanding"]),
        ("PROK", "1850270:0001193125-26-342373", [r"Class A common stock.{0,80}outstanding", r"outstanding as of"]),
    ],
    "debt": [
        ("IBRX", "https://www.sec.gov/Archives/edgar/data/1326110/000132611026000079/ibrx-20260630.htm",
         [r"related.party (convertible )?note", r"Total liabilities", r"revenue interest liabilit", r"term loan"]),
        ("KPTI", "https://www.sec.gov/Archives/edgar/data/1503802/000119312526347906/kpti-20260630.htm",
         [r"convertible senior notes", r"term loan", r"Total liabilities", r"deferred royalty"]),
        ("TIL", "https://www.sec.gov/Archives/edgar/data/1789769/000178976926000057/til-20260630.htm",
         [r"loan payable", r"Total liabilities"]),
        ("SKYE", "https://www.sec.gov/Archives/edgar/data/1516551/000162828026056968/skye-20260630.htm",
         [r"insurance premium loan", r"Total liabilities"]),
        ("ORMP", "https://www.sec.gov/Archives/edgar/data/1176309/000121390026087361/ea0300383-10q_oramed.htm",
         [r"convertible note", r"Total liabilities"]),
        ("KNSA_BS", "https://www.sec.gov/Archives/edgar/data/1730430/000110465926087545/knsa-20260630x10q.htm",
         [r"Cash and cash equivalents \|", r"Short-term investments", r"Total liabilities"]),
    ],
}
batch = sys.argv[1]
items = B[batch] if batch in B else []
out = open(f"data/moat/verify/pw3_docs_{batch}.txt", "w")
for tk, src, pats in items:
    url = src if src.startswith("http") else main_doc(*src.split(":"))
    t = text(get(url))
    out.write(f"===== {tk} {url} chars={len(t)}\n")
    for pat in pats:
        for m in list(re.finditer(pat, t, re.I))[:3]:
            s = t[max(0, m.start() - 250): m.end() + 450].replace("\n", " / ")
            out.write(f"--- [{pat}] @{m.start()}: {re.sub(' +', ' ', s)}\n")
    out.flush()
print("wrote", out.name)
