p = 'agent/moat/deals_lib.py'
s = open(p).read()
a = s.index("def stage_of(text):")
b = s.index("def classify(")
new = '''def stage_of(text):
    t = text[:2500]
    if re.search(r"(?:NDA|BLA|MAA)\\s+(?:submission|was submitted|has been submitted|accepted|under review)|(?:submitted|filed) (?:an? )?(?:NDA|BLA|MAA)|PDUFA", t):
        return "filed"
    if re.search(r"commercial rights to|marketed product|approved product|currently marketed|FDA-approved (?:drug|product|therap)|net sales of|commercially available|approved (?:in|by) the", t, re.I):
        return "marketed"
    for k, rx in (("Ph3", r"phase\\s*(?:3|III)\\b|pivotal|registrational"), ("Ph2", r"phase\\s*(?:2|II)\\b"),
                  ("Ph1", r"phase\\s*(?:1|I)\\b|first-in-human|first in human"), ("preclinical", r"pre-?clinical|discovery|IND-enabling|research collaboration|lead optimization")):
        if re.search(rx, t, re.I):
            return k
    return ""


'''
s = s[:a] + new + s[b:]
s = s.replace("            tot = max(x[0] for x in a)\n            quote = quote or s\n    return up, eq, ms, tot, quote",
              "            tot = max(x[0] for x in a)\n            quote = quote or s\n    if tot is not None and up is not None and ms is not None and abs(tot - up) < 1e-9:\n        tot = up + ms\n    return up, eq, ms, tot, quote")
open(p, 'w').write(s)
p = 'agent/moat/deals_extract.py'
s = open(p).read()
s = s.replace('if am and am.group(1) not in ("COVID-19"', 'if am and not am.group(1).startswith(("EX", "FY", "Q", "ASCO", "ESMO", "SEC", "ISO")) and am.group(1) not in ("COVID-19"')
open(p, 'w').write(s)
p = 'agent/moat/deals_build.py'
s = open(p).read()
s = s.replace('|asset|definitive|merger"', '|asset|definitive|merger|progress|announce|strategic|enter|global|plan|update|expand|results|\\\\bpr\\\\b"')
open(p, 'w').write(s)
