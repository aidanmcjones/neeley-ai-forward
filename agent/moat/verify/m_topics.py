"""Verified analyst_topics: rebuild from transcripts with m_qa roles and tighter topic matching.

Matching runs three ways so spaceless LSEG text (JNJ) still matches: squashed lowercase literals on
alnum-only text, case-sensitive acronyms on original text, and boundary regexes on original text.
Writes data/moat/verified/market/{analyst_topics.csv, never_asked.csv, analyst_turns_sample.csv}.
"""
import csv
import io
import re
from collections import defaultdict
from agent.moat.common import write
from agent.moat.verify.m_qa import ROOT, classify, roster_for, layout

SQ = {
    "IRA_negotiation": r"inflationreductionact|medicare(drug)?(price)?negotiat|pricenegotiat|negotiatedprice|maximumfairprice|"
                       r"partdredesign|pillpenalty|smallmoleculepenalty|epicact|selecteddrug|cmsnegotiat|negotiationwithcms|governmentpricesetting",
    "MFN": r"mostfavou?rednation|internationalreferencepric|trumprx|directtoconsumerpric|dtcpric|"
           r"(agreement|deal)with(the)?(administration|whitehouse|government)|administrationdeal|whitehousedeal",
    "tariff": r"tariff|section232|manufacturinginvestment|domesticmanufacturing",
    "gross_to_net_price": r"grosstonet|netprice|netpricing|pricingpressure|rebate|priceerosion|pricecut|listprice|pricedecline|340b|pricingenvironment",
    "inventory_channel": r"inventor(y|ies)|destock|stocking|wholesaler|distributor|channelinventor|channeldynamic|channelfill|tradeinventor",
    "biosimilar_generic": r"biosimilar|generic|lossofexclusivity|patentcliff|exclusivity|patentexpir",
    "guidance": r"guidance|outlook|fullyear|midpoint",
    "pipeline": r"pipeline|phase(1|2|3|ii|iii|one|two|three)|readout|toplinedata|pivotal",
}
ACR = {
    "IRA_negotiation": r"(?<![A-Z])(IRA|MFP)(?![A-Z])",
    "MFN": r"(?<![A-Z])MFN(?![A-Z])",
    "gross_to_net_price": r"(?<![A-Z])(GTN|PBMs?)(?![A-Z])",
    "biosimilar_generic": r"(?<![A-Z])LOE(?![A-Z])",
    "pipeline": r"\b(MK|BMS|PF|LY|ABBV|AMG|GS|AZD|JNJ|NNC)-?\d{3,7}\b",
}
ORIG = {
    "IRA_negotiation": r"\bpart\s?d\b",
    "inventory_channel": r"\bbuy[- ]in\b",
    "tariff": r"\b(on|re)-?shor|\bU\.?S\.? manufacturing|\bAmerican manufacturing",
}
PRODUCTS = {
    "ABBV": "skyrizi|rinvoq|humira|vraylar|botox|imbruvica|venclexta|ubrelvy|qulipta|elahere|vyalev|emraclidine",
    "AMGN": "repatha|prolia|xgeva|evenity|enbrel|otezla|tezspire|blincyto|tepezza|krystexxa|uplizna|imdelltra|amjevita|maritide",
    "AZN": "farxiga|tagrisso|imfinzi|enhertu|calquence|lynparza|ultomiris|soliris|breztri|fasenra|saphnelo|airsupra|datroway|wainua|baxdrostat|camizestrant",
    "BMY": "opdivo|eliquis|revlimid|pomalyst|yervoy|reblozyl|breyanzi|camzyos|cobenfy|sotyktu|abecma|krazati|opdualag|zeposia|orencia|qvantig",
    "GILD": "biktarvy|descovy|yeztugo|lenacapavir|trodelvy|veklury|yescarta|tecartus|livdelzi|sunlenca|genvoya|epclusa",
    "JNJ": "darzalex|stelara|tremfya|erleada|carvykti|rybrevant|lazcluze|spravato|simponi|invega|xarelto|icotyde|icotrokinra|inlexzo|tecvayli|talvey|imaavy|caplyta",
    "LLY": "mounjaro|zepbound|trulicity|verzenio|jardiance|taltz|ebglyss|omvoh|kisunla|jaypirca|orforglipron|foundayo|retatrutide",
    "MRK": "keytruda|gardasil|januvia|janumet|winrevair|welireg|capvaxive|bridion|lynparza|lenvima|enflonsia|ohtuvayre|verquvo|qlex",
    "NVO": "ozempic|wegovy|rybelsus|saxenda|victoza|tresiba|alhemo|awiqli|cagrisema|amycretin",
    "PFE": "eliquis|vyndaqel|vyndamax|tafamidis|prevnar|paxlovid|comirnaty|ibrance|xtandi|padcev|abrysvo|nurtec|xeljanz|lorbrena|elrexfio|hympavzi",
}
TOPICS = ["IRA_negotiation", "MFN", "tariff", "gross_to_net_price", "inventory_channel", "biosimilar_generic", "pipeline",
          "guidance", "top_products"]
RANK = {"lseg": 0, "md": 1, "fool": 2, "fool_inline": 2, "roic": 2, "benzinga": 3, "allmind": 4}
OUTDIR = "verified/market"


def squash(text):
    keep = [(i, c.lower()) for i, c in enumerate(text) if c.isalnum()]
    return "".join(c for _, c in keep), [i for i, _ in keep]


def hits(text, tk, topic):
    """Return list of original-text start offsets for matches of topic in text."""
    sq, idx = squash(text)
    pos = []
    pat = SQ.get(topic) if topic != "top_products" else PRODUCTS[tk]
    if pat:
        pos += [idx[m.start()] for m in re.finditer(pat, sq)]
    if topic in ACR:
        pos += [m.start() for m in re.finditer(ACR[topic], text)]
    if topic in ORIG:
        pos += [m.start() for m in re.finditer(ORIG[topic], text, re.I)]
    return sorted(set(pos))


def snippet(text, p):
    a = text.rfind(". ", 0, max(0, p - 200))
    a = 0 if a < 0 else a + 2
    b = text.find(". ", p + 40)
    b = len(text) if b < 0 or b - p > 300 else b + 1
    return re.sub(r"\s+", " ", text[a:b]).strip()[:500]


def terms(hit):
    out = set()
    for t, ps in hit:
        for p in ps:
            out.add(re.sub(r"\s+", " ", t[3][p:p + 22]).strip())
    return "; ".join(sorted(out))[:300]


def pick_files():
    by = defaultdict(list)
    for base in ("data/corpus/companies", "data/moat/companies"):
        for f in sorted((ROOT / base).glob("*/transcripts/*_transcript.md")):
            by[f.parts[-3]].append(f)
    return by


def main():
    by = pick_files()
    rosters = {tk: roster_for(fs, tk) for tk, fs in by.items()}
    globalA = set().union(*[r["A"] for r in rosters.values()])
    for r in rosters.values():
        r["E"] -= globalA
    old = defaultdict(dict)
    with open(ROOT / "data/moat/tables/analyst_topics.csv") as f:
        for r in csv.DictReader(f):
            old[(r["ticker"], r["quarter"])][r["topic"]] = (int(r["analyst_turns"]), int(r["turns_with_topic"]))
    rows, sample, choice = [], [], []
    for tk, fs in sorted(by.items()):
        cands = defaultdict(list)
        for f in fs:
            text = f.read_text()
            lay, k0, turns = classify(text, tk, rosters[tk])
            an = [t for t in turns if t[2] == "A"]
            cands[f.name.split("_")[0]].append((RANK[lay], -len(an), str(f.relative_to(ROOT)), lay, turns, text))
        for q in sorted(cands):
            cs = sorted(cands[q], key=lambda c: (c[0] if -c[1] >= 4 else 9, c[1]))
            rank, nneg, rel, lay, turns, text = cs[0]
            choice.append([tk, q, rel, lay, -nneg, "; ".join(f"{c[2]}({c[3]},{-c[1]})" for c in cs[1:])])
            an = [t for t in turns if t[2] == "A"]
            for t in an:
                sample.append([tk, q, rel, t[0], t[1], re.sub(r"\s+", " ", t[3])[:300]])
            for topic in TOPICS:
                hit = [(t, hits(t[3], tk, topic)) for t in an]
                hit = [(t, p) for t, p in hit if p]
                ex = max(hit, key=lambda h: len(h[1]), default=None)
                o = old.get((tk, q), {}).get(topic)
                rows.append([tk, q, topic, len(an), len(hit), len({t[1] for t, _ in hit}), sum(len(p) for _, p in hit),
                             snippet(ex[0][3], ex[1][0]) if ex else "", ex[0][1] if ex else "", rel if ex else "",
                             ex[0][0] if ex else "", terms(hit), lay, o[0] if o else "", o[1] if o else "",
                             (len(hit) - o[1]) if o else "", rel, ex[0][0] if ex else ""])
    cols = ["ticker", "quarter", "topic", "analyst_turns", "turns_with_topic", "analysts_asking", "mentions", "example_quote",
            "example_speaker", "example_file", "example_line", "matched_terms", "layout", "collector_analyst_turns",
            "collector_turns_with_topic", "delta_vs_collector", "source", "source_row"]
    emit("analyst_topics.csv", cols, rows)
    emit("analyst_turns_all.csv", ["ticker", "quarter", "file", "line", "speaker", "question_text_first300"], sample)
    emit("transcript_choice.csv", ["ticker", "quarter", "file_used", "layout", "analyst_turns", "alternates(layout,analyst_turns)"], choice)
    # never asked
    agg = defaultdict(lambda: {"q": [], "asked": [], "turns": 0})
    for r in rows:
        a = agg[(r[0], r[2])]
        a["q"].append(r[1])
        a["turns"] += r[4]
        if r[4]:
            a["asked"].append(r[1])
    na = []
    for (tk, topic), a in sorted(agg.items()):
        qs = sorted(a["q"])
        streak = 0
        for q in reversed(qs):
            if q in a["asked"]:
                break
            streak += 1
        na.append([tk, topic, len(qs), f"{qs[0]}..{qs[-1]}", len(a["asked"]), a["turns"], max(a["asked"]) if a["asked"] else "",
                   streak, "never asked" if not a["asked"] else (f"not asked in last {streak} quarters" if streak else "")])
    emit("never_asked.csv", ["ticker", "topic", "quarters_covered", "quarter_range", "quarters_asked", "turns_total",
                             "last_asked", "recent_unasked_streak", "flag"], na)
    print(len(rows), "rows;", len(sample), "analyst turns")


def emit(name, cols, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    write("verify_market", f"{OUTDIR}/{name}", buf.getvalue(), group="market", doc_type="table",
          source_url="data/corpus/companies/*/transcripts + data/moat/companies/*/transcripts", upload=False)


if __name__ == "__main__":
    main()
