"""Find precedent pricing-move statements (with page) in the page-marked filings, calls and policy documents."""
import glob
import json
import re

PAGE = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")
PATS = {
    "insulin_cut": r"(?:reduc|lower|cut)\w* (?:the )?(?:list )?price[s]?[^.]{0,120}insulin|insulin[^.]{0,200}(?:70%|75%|price (?:cut|reduction)|list price)",
    "januvia_cut": r"(?:Januvia|Janumet)[^.]{0,200}(?:list price|price (?:reduction|cut)|42%)|(?:list price|price (?:reduction|cut)|42%)[^.]{0,200}(?:Januvia|Janumet)",
    "direct_to_patient": r"LillyDirect|NovoCare|PfizerForAll|BMS Patient Assistance|direct[- ]to[- ](?:patient|consumer) (?:pricing|price|program|platform|offer)|TrumpRx",
    "cost_plus": r"Cost Plus Drugs?[^.]{0,200}|Eliquis[^.]{0,200}(?:Cost Plus|direct)",
    "mfn_medicaid": r"Medicaid[^.]{0,120}(?:most[- ]favored|MFN)|(?:most[- ]favored|MFN)[^.]{0,200}Medicaid",
    "authorized_generic": r"authorized generic[^.]{0,250}",
    "volume_after_price": r"(?:volume|prescriptions|demand|TRx|NBRx)[^.]{0,120}(?:following|after|since|due to)[^.]{0,80}(?:price (?:reduction|cut|decrease)|lower(?:ed)? (?:list )?price|list price)",
}
RX = {k: re.compile(v, re.I) for k, v in PATS.items()}
files = (glob.glob("data/corpus/companies/*/*.md") + glob.glob("data/corpus/companies/*/*/*.md") + glob.glob("data/corpus/peers/*/*.md") + glob.glob("data/corpus/peers/*/*/*.md")
         + glob.glob("data/moat/companies/*/*.md") + glob.glob("data/moat/companies/*/*/*.md"))
out = []
for f in files:
    try:
        txt = open(f, errors="ignore").read()
    except OSError:
        continue
    parts = PAGE.split(txt)
    pages = [(parts[i], parts[i + 1], parts[i + 2]) for i in range(1, len(parts) - 2, 3)] or [("1", "", txt)]
    seen = {}
    for pg, pr, body in pages:
        for k, rx in RX.items():
            if seen.get(k, 0) >= 3:
                continue
            for m in rx.finditer(body):
                s = body[max(0, m.start() - 160):m.end() + 200]
                s = " ".join(s.split())
                out.append({"kind": k, "file": f, "page": pg, "text": s[:520]})
                seen[k] = seen.get(k, 0) + 1
                if seen[k] >= 3:
                    break
json.dump(out, open("data/moat/scratch/costs_price.json", "w"))
from collections import Counter
print(len(out), Counter(o["kind"] for o in out))
