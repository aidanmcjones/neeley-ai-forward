"""Regex extraction of deal economics from press-release style text and 10-K agreement paragraphs."""
import re

MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(billion|million|bn|mm|thousand)?\b", re.I)
SENT_SPLIT = re.compile(r"(?<=[\.\!\?])\s+(?=[A-Z“\"(])")
SUFFIX = r"(?:,? (?:Inc|Ltd|Limited|Corp|Corporation|plc|PLC|AG|N\.V|NV|S\.A|SA|SE|LLC|Co|GmbH|A/S|AB|KGaA|S\.p\.A|Pty|K\.K|Holdings|Company)\.?)"
ORG = r"[A-Z][A-Za-z0-9&\.\-’' ]{1,45}?" + SUFFIX + r"?"

STAGES = [("filed", r"\bNDA\b|\bBLA\b|\bMAA\b|under review|filed with|submitted"), ("marketed", r"\bapproved\b|marketed|commercial(?:ized)? product|currently sold|net sales|FDA-approved"),
          ("Ph3", r"phase\s*(?:3|III)\b|pivotal|registrational"), ("Ph2", r"phase\s*(?:2|II)\b"),
          ("Ph1", r"phase\s*(?:1|I)\b|first-in-human|first in human"), ("preclinical", r"pre-?clinical|discovery|IND-enabling|research collaboration|lead optimization")]
MODS = [("ADC", r"antibody[- ]drug conjugate|\bADCs?\b"), ("bispecific", r"bispecific|trispecific"), ("antibody", r"antibod|monoclonal|\bmAb"),
        ("siRNA/oligonucleotide", r"siRNA|RNAi|antisense|oligonucleotide"), ("mRNA", r"\bmRNA\b"), ("gene editing", r"CRISPR|gene edit|base edit"),
        ("gene therapy", r"gene therapy|\bAAV\b|lentivir"), ("cell therapy", r"CAR-?T|cell therapy|\bTCR\b|\bNK cell|TIL\b"),
        ("radiopharmaceutical", r"radiopharm|radioligand|radiotherap"), ("degrader", r"degrader|PROTAC|molecular glue"),
        ("peptide", r"peptide|GLP-1"), ("vaccine", r"vaccine"), ("biosimilar", r"biosimilar"), ("small molecule", r"small[- ]molecule|inhibitor|oral(?:ly)?\b|agonist|antagonist|tablet"),
        ("platform", r"platform")]
TAS = [("oncology", r"oncolog|cancer|tumou?r|carcinoma|leukemia|lymphoma|myeloma|melanoma"), ("neurology", r"neurolog|alzheimer|parkinson|CNS\b|epilep|ALS\b|huntington|migraine|neurodegen|multiple sclerosis"),
       ("psychiatry", r"psychiatr|depress|schizophren|bipolar|anxiety"), ("immunology", r"immunolog|inflammat|autoimmun|psoria|lupus|atopic|rheumat|colitis|crohn|asthma|COPD"),
       ("metabolic", r"obesity|diabet|metabolic|cardiometabolic|NASH|MASH|lipid|cholesterol"), ("cardiovascular", r"cardio|heart|hypertens|thrombo"),
       ("infectious disease", r"infect|antiviral|antibacterial|antibiotic|HIV|hepatitis|COVID|influenza|RSV|antifungal"), ("ophthalmology", r"ophthalm|retina|macular|glaucoma|dry eye"),
       ("hematology", r"hematolog|sickle|hemophilia|anemia|thalass"), ("rare disease", r"rare disease|orphan|lysosomal|duchenne|cystic fibrosis"),
       ("dermatology", r"dermatolog|acne|alopecia|vitiligo"), ("respiratory", r"respirat|pulmonary|lung disease|IPF\b"), ("pain", r"\bpain\b|analges|opioid"),
       ("renal/GI/hepatic", r"kidney|renal|gastro|liver|hepat")]


def money_m(m):
    v = float(m.group(1).replace(",", ""))
    u = (m.group(2) or "").lower()
    if u in ("billion", "bn"):
        return v * 1000
    if u in ("million", "mm"):
        return v
    if u == "thousand":
        return v / 1000
    if v >= 100000:
        return v / 1e6
    return None


def sentences(text):
    t = re.sub(r"\s+", " ", text).replace(" • ", ". ").replace(" ● ", ". ").replace("•", ". ")
    return [s.strip() for s in SENT_SPLIT.split(t) if s.strip()]


def amounts(s):
    out = []
    for m in MONEY.finditer(s):
        v = money_m(m)
        if v is not None:
            out.append((v, m.start(), m.end()))
    return out


def fmt(v):
    return "" if v is None else (f"{v:.1f}".rstrip("0").rstrip(".") if v < 1000 else f"{v:.0f}")


def first(rx_list, text, default=""):
    best = None
    for name, rx in rx_list:
        m = re.search(rx, text, re.I)
        if m and (best is None or False):
            return name
    return default


def stage_of(text):
    t = text[:2500]
    if re.search(r"(?:NDA|BLA|MAA)\s+(?:submission|was submitted|has been submitted|accepted|under review)|(?:submitted|filed) (?:an? )?(?:NDA|BLA|MAA)|PDUFA", t):
        return "filed"
    if re.search(r"commercial rights to|marketed product|approved product|currently marketed|FDA-approved (?:drug|product|therap)|net sales of|commercially available|approved (?:in|by) the", t, re.I):
        return "marketed"
    for k, rx in (("Ph3", r"phase\s*(?:3|III)\b|pivotal|registrational"), ("Ph2", r"phase\s*(?:2|II)\b"),
                  ("Ph1", r"phase\s*(?:1|I)\b|first-in-human|first in human"), ("preclinical", r"pre-?clinical|discovery|IND-enabling|research collaboration|lead optimization")):
        if re.search(rx, t, re.I):
            return k
    return ""


def classify(text, key):
    best = ""
    bpos = 10 ** 9
    for name, rx in key:
        m = re.search(rx, text, re.I)
        if m and m.start() < bpos:
            best, bpos = name, m.start()
    return best


def deal_type(text):
    t = text[:2500].lower()
    if re.search(r"royalty purchase|royalty monetization|sale of (?:its )?royalt|royalty financing|synthetic royalty", t):
        return "royalty monetization"
    if re.search(r"asset purchase agreement|acquire (?:certain )?assets|purchase of (?:certain )?assets", t):
        return "asset purchase"
    if re.search(r"merger agreement|tender offer|per share in cash|to acquire .{0,80}(?:inc|corp|ltd|plc)|definitive agreement to acquire|to be acquired", t):
        return "acquisition"
    if re.search(r"\boption (?:and|to)\b|option agreement|exclusive option|option to (?:license|acquire)", t):
        return "option"
    if re.search(r"co-?develop|co-?commerciali|co-?promot|profit[- ]shar", t):
        return "co-development"
    return "license"


def terr(text):
    m = re.search(r"(?:outside (?:of )?(?:the )?(?:United States|U\.S\.|US|Greater China|China|Japan|North America)(?: and [A-Z][a-z]+)?|Greater China|ex-U\.?S\.?|worldwide|global(?:ly)?|United States|North America|Europe|Japan|China|Asia(?:-Pacific)?|Latin America|Middle East)", text, re.I)
    return m.group(0) if m else ""


def royalty_text(sents):
    for s in sents:
        if re.search(r"royalt", s, re.I) and re.search(r"%|percent|tiered|double-digit|single-digit|teens|net sales", s, re.I):
            return s[:250]
    return ""


def peak_note(sents):
    for s in sents:
        if re.search(r"peak (?:annual |global |worldwide |net )?sales|peak revenue", s, re.I):
            return s[:250]
    return ""


def econ(sents, kind):
    """Return upfront, equity, milestones, total (USD m) and the quote sentence."""
    up = eq = ms = tot = None
    quote = None
    for s in sents:
        a = amounts(s)
        if not a:
            continue
        low = s.lower()
        if up is None and re.search(r"up-?front|initial payment|signing payment|payment at signing|cash payment of", low):
            # amount nearest 'upfront'
            pos = [m.start() for m in re.finditer(r"up-?front|initial payment|signing payment|cash payment of", low)][0]
            cand = [x for x in a if not re.match(r"\s*(?:in )?(?:development|regulatory|sales|commercial|milestone)", s[x[2]:x[2] + 30].lower())]
            cand = cand or a
            v = min(cand, key=lambda x: abs(x[1] - pos))[0]
            up = v
            quote = quote or s
        if eq is None and re.search(r"equity investment|purchase of .{0,40}(?:shares|common stock)|invest(?:ment)? .{0,40}equity|equity of|private placement|will purchase .{0,50}shares", low):
            eq = a[0][0]
        if re.search(r"milestone", low):
            m_ = [x[0] for x in a if x[0] != up]
            if m_ and (ms is None or max(m_) > ms):
                ms = max(m_)
                quote = quote or s
        if tot is None and re.search(r"total (?:potential |deal |transaction )?(?:value|consideration|payments?)|aggregate (?:transaction |deal )?(?:value|consideration|payments?|amount)|worth up to|potential (?:deal |transaction )?value|transaction value|equity value|valued at|up to \$[\d,\.]+ (?:billion|million) (?:in total|in aggregate|total)|deal valued|total of up to|for a total", low):
            tot = max(x[0] for x in a)
            quote = quote or s
    if tot is not None and up is not None and ms is not None and abs(tot - up) < 1e-9:
        tot = up + ms
    return up, eq, ms, tot, quote


def acq_econ(sents):
    price = tot = None
    q = None
    for s in sents:
        low = s.lower()
        if "per share" in low and ("cash" in low) and q is None:
            q = s
        a = amounts(s)
        if a and tot is None and re.search(r"aggregate|equity value|transaction value|valued at|total (?:equity|consideration|value)|approximately \$[\d\.,]+ (?:billion|million)", low) and re.search(r"acqui|merger|transaction|equity|offer|cash", low):
            tot = max(x[0] for x in a)
            q = q if q and tot else s
            q = s
    return tot, q


def parties_acq(head):
    h = re.sub(r"\s+", " ", head)
    m = re.search(r"(" + ORG + r")\s+(?:to acquire|will acquire|has agreed to acquire|agrees to acquire|announces? (?:a )?(?:definitive )?(?:merger )?agreement to acquire|to buy|acquires|to purchase)\s+(" + ORG + r")(?= for | in | to |,|;|\.| \(| and |$)", h)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.search(r"(" + ORG + r")\s+(?:to be acquired by|enters into (?:a )?(?:definitive )?(?:merger )?agreement to be acquired by|agrees to be acquired by)\s+(" + ORG + r")(?= for | in | to |,|;|\.| \(| and |$)", h)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    m = re.search(r"(" + ORG + r") (?:and|,) (" + ORG + r") (?:announce|enter|sign|have)", h)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", ""
