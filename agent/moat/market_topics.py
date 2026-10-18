"""Shared topic regexes and transcript Q&A parser for the market stream."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CORP = ROOT / "data" / "corpus" / "companies"

TOPICS = {
    "IRA_negotiation": r"\bIRA\b|inflation reduction act|medicare (drug )?(price )?negotiat|negotiated price|maximum fair price|\bMFP\b|part d redesign|part d",
    "MFN": r"\bMFN\b|most[- ]favou?red[- ]nation|international reference pric|trumprx|direct[- ]to[- ]consumer pric",
    "tariff": r"tariff|section 232|onshor|reshor|manufacturing investment",
    "gross_to_net_price": r"gross[- ]to[- ]net|\bGTN\b|net price|net pricing|pricing pressure|rebate|price erosion|price cut|list price|price decline|340b|\bPBM",
    "inventory_channel": r"inventory|destock|channel|wholesaler|stocking|buy[- ]in|distributor",
    "biosimilar_generic": r"biosimilar|generic|loss of exclusivity|\bLOE\b|patent cliff|exclusivity|patent expir",
    "guidance": r"guidance|outlook|full[- ]year|raise[ds]? (our )?(the )?(guid|outlook)|midpoint",
    "pipeline": r"pipeline|phase [123i]+\b|phase ?[123]|\b(MK|BMS|PF|LY|ABBV|AMG|GS|AZD|JNJ|CagriSema|NNC)-?\d{3,7}\b|maritide|retatrutide|orforglipron|cagrisema|amycretin|foundayo|lipfendra|read-?out",
    "top_products": r"keytruda|januvia|janumet|opdivo|eliquis|ibrance|vyndaqel|vyndamax|mounjaro|zepbound|trulicity|ozempic|wegovy|skyrizi|rinvoq|humira|stelara|tremfya|darzalex|tagrisso|farxiga|imfinzi|enbrel|repatha|biktarvy|yeztugo|lenacapavir|xarelto|verzenio|kisqali|jardiance",
}
TOPIC_RE = {k: re.compile(v, re.I) for k, v in TOPICS.items()}

QA_START = re.compile(r"questions and answers|Q&A|first question|open (up )?the (call|lines?) (up )?for|for questions|take your questions|begin the question", re.I)
HTML_LABEL = re.compile(r"^\s*([A-Z][A-Za-z.'À-ſ -]{1,45}):\s+(.*)$")
PDF_LABEL = re.compile(r"^([A-Z][^-\n]{1,50}) - (.{2,120}) - (.{2,120})$")
NOISE = re.compile(r"^\[\[page|LSEG STREETEVENTS|^\d+$|Contact Us|THOMSON REUTERS|©", re.I)


def parse_qa(text):
    """Return (qa_start_line, turns) where turns = [(line_no, speaker, is_analyst, text)]. Fool TAKEAWAYS/SUMMARY skipped."""
    lines = text.split("\n")
    # skip AI sections
    floor = 0
    for i, l in enumerate(lines):
        if l.strip() == "SUMMARY":
            floor = i
            # summary ends at first label line afterwards or after 14 paragraphs
            for j in range(i + 1, min(i + 40, len(lines))):
                if HTML_LABEL.match(lines[j]) and lines[j].strip().split(":")[0] in ("Operator",):
                    floor = j
                    break
            else:
                floor = i + 14
            break
    is_pdf = "format: pdf" in text[:600]
    start = None
    cands = [i for i in range(floor, len(lines)) if QA_START.search(lines[i]) and not lines[i].strip().startswith("<!--")]
    for i in cands:
        if any(re.match(r"^\s*Operator", lines[j]) for j in range(i, min(i + 4, len(lines)))) and i > len(lines) * 0.05:
            start = i
            break
    if start is None:
        start = int(len(lines) * 0.5)
    turns = []
    cur = None
    prev_op = False
    names_analyst = set()
    for i in range(start, len(lines)):
        l = lines[i]
        if NOISE.search(l) or not l.strip():
            continue
        spk = None
        body = l
        analyst = False
        if is_pdf:
            if l.strip() == "Operator":
                spk, body = "Operator", ""
            else:
                m = PDF_LABEL.match(l)
                if m:
                    spk, body = m.group(1).strip(), ""
                    analyst = m.group(3).strip().lower().startswith("analyst") or "equity analyst" in m.group(3).lower() or m.group(3).strip().endswith("Analyst")
        else:
            m = HTML_LABEL.match(l)
            if m and len(m.group(1).split()) <= 5:
                spk, body = m.group(1).strip(), m.group(2)
        if spk is not None:
            if spk == "Operator":
                prev_op = True
                analyst = False
            else:
                if not is_pdf:
                    if prev_op and spk != "Operator":
                        names_analyst.add(spk)
                    analyst = spk in names_analyst
                prev_op = False
            cur = [i + 1, spk, analyst, body]
            turns.append(cur)
        elif cur is not None:
            cur[3] += " " + l.strip()
    return start + 1, [tuple(t) for t in turns]
