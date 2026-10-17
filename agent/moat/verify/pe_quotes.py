"""Peers item 1: re-check every rival_product_statements quote against its cited doc and page.

Checks: verbatim on the cited page (whitespace-normalized), printed folio, product named in the quote, whether
another product is the real subject, publisher-written text inside third-party transcript pages (MarketBeat
'Key Takeaways', Fool/Webull TAKEAWAYS/SUMMARY, 'About <company>' boilerplate), speaker re-derivation, and the
topic regex bug. Writes data/moat/verified/peers/rival_product_statements.csv.
"""
import io
import re
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, norm, pages

ALIASES = {"Amvuttra": ["amvuttra", "vutrisiran"], "Attruby": ["attruby", "acoramidis", "beyonttra"],
           "Leqvio": ["leqvio", "inclisiran"], "Praluent": ["praluent", "alirocumab"],
           "Kisqali": ["kisqali", "ribociclib"], "Cosentyx": ["cosentyx", "secukinumab"],
           "Entyvio": ["entyvio", "vedolizumab"], "Sarclisa": ["sarclisa", "isatuximab"],
           "Tecentriq": ["tecentriq", "atezolizumab"], "Imfinzi": ["imfinzi", "durvalumab"],
           "Jardiance": ["jardiance", "empagliflozin"], "Apretude": ["apretude", "cabotegravir"],
           "Cabenuva": ["cabenuva", "cabotegravir", "vocabria", "rekambys"], "Dovato": ["dovato", "dolutegravir"],
           "Wezlana": ["wezlana", "ustekinumab"], "Amjevita": ["amjevita", "adalimumab"],
           "Lipfendra": ["lipfendra", "enlicitide"]}
OTHER = ['onpattro', 'patisiran', 'vyndaqel', 'vyndamax', 'tafamidis', 'eplontersen', 'wainua', 'repatha', 'evolocumab',
         'keytruda', 'opdivo', 'darzalex', 'verzenio', 'ibrance', 'stelara', 'humira', 'skyrizi', 'rinvoq', 'tremfya',
         'biktarvy', 'descovy', 'yeztugo', 'lenacapavir', 'taltz', 'dupixent', 'kevzara', 'farxiga', 'zilebesiran',
         'ocrevus', 'gazyva', 'vabysmo', 'juluca', 'triumeq', 'enbrel', 'otezla', 'aimovig', 'mounjaro', 'zepbound',
         'kesimpta', 'pluvicto', 'scemblix', 'entresto', 'imjudo', 'tagrisso', 'eylea', 'givlaari', 'oxlumo']
for v in ALIASES.values():
    OTHER += v
OTHER = sorted(set(OTHER))
# maker of each product, and whether the cited doc is the maker's own disclosure
TRUE_MAKER = {"Jardiance": "Boehringer Ingelheim (Lilly co-commercializes and books alliance revenue)",
              "Praluent": "Regeneron (US) / Sanofi (ex-US)", "Cabenuva": "ViiV Healthcare (GSK majority)",
              "Apretude": "ViiV Healthcare (GSK majority)", "Dovato": "ViiV Healthcare (GSK majority)"}
FOCAL = {"AZN", "LLY", "MRK", "AMGN"}
JUNK_SPK = {'Quarterly Report', 'Watch the full earnings call below', 'Drug Manufacturers', 'Annual Report',
            'Do NOT Buy SpaceX', 'BridgeBio', 'BridgeBio Pharma', 'Alnylam Pharma', 'Regeneron Pharmaceuticals',
            'Amgen', 'Cabenuva', 'Chief Financial Officer'}
OFFICIAL = ("sanofi.com", "gsk.com", "merck.com")
TS = re.compile(r'^\s*\d{2}:\d{2}:\d{2}\s*$')
INLINE = re.compile(r"^\s*([A-Z][A-Za-z.'’\- ]{1,40}?|Speaker #\d+)\s?:\s")
# collector's topic regexes with the bug fixed (word boundaries, IRA case-sensitive, no bare %)
TOPICS_FIXED = [("exclusivity", r"\bpatent|\bexclusivity\b|loss of exclusivity|\bgenerics?\b|\bbiosimilar|\bLOE\b|\bexpir|market protection|\bANDA\b"),
                ("pricing", r"\bpric|\brebate|(?-i:\bIRA\b)|\bnegotiat|\bMFN\b|\breimburs|gross-to-net|net price|\bMedicare\b|\bMedicaid\b|\bpayers?\b|\bpayors?\b|\bformular"),
                ("competition", r"\bcompet|\bversus\b|\bvs\.|\brival|market share|\bswitch|market leader|head-to-head|\bKeytruda\b|\bOpdivo\b"),
                ("growth", r"\bgrew\b|\bgrowth\b|\bsales (increase|decrease)|\bdecline|\blaunch|\buptake|\bguidance\b"),
                ("revenue", r"\brevenues?\b|\bsales\b|\bnet product\b|(USD|EUR|CHF|JPY|\$|£) ?[\d.,]+ ?(million|billion|bn|m)\b")]


def topic_fixed(s):
    return "|".join(n for n, r in TOPICS_FIXED if re.search(r, s, re.I)) or "mention"


def transcript_bounds(p):
    t = (ROOT / p).read_text(errors='replace')
    L = t.split('\n')
    if any(o in L[0] for o in OFFICIAL):
        return L, 0, len(L)
    low = [l.strip().lower() for l in L]
    marks = [k for k, l in enumerate(low) if l in ('full conference call transcript', 'full transcript', 'presentation')
             or l.startswith('ai generated. may contain errors')]
    start = max(marks) if marks else next((k for k, l in enumerate(low) if re.match(r'^operator\b', l)), 0)
    if not marks and start == 0:
        start = 0
    ts = [k for k, l in enumerate(L) if TS.match(l)]
    end = ts[-1] + 12 if ts else len(L)
    about = next((k for k, l in enumerate(L) if k > start and re.match(r'^\s*About [A-Z]', l)), None)
    if about and about < end:
        end = about
    return L, start, end


def derive_speaker(L, li):
    """Walk back from the quote line to the speaker label for the transcript formats in this corpus."""
    m = INLINE.match(L[li])
    if m:
        return m.group(1).strip()
    for k in range(li - 1, max(0, li - 400), -1):
        s = L[k].strip()
        if TS.match(L[k]):  # MarketBeat: name, title, timestamp
            prev = [L[j].strip() for j in range(k - 1, max(0, k - 8), -1) if L[j].strip()]
            if prev and prev[0] == 'Operator':
                return 'Operator'
            return prev[1] if len(prev) > 1 else None
        m = INLINE.match(L[k])
        if m:
            return m.group(1).strip()
    return None


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/rival_product_statements.csv")
    bounds = {p: transcript_bounds(p) for p in d[d.doc_type == 'earnings_call'].path.unique()}
    out = []
    for i, r in d.iterrows():
        pg = pages(r.path)
        p = int(r.page)
        q, ql = norm(r.quote), norm(r.quote, loose=True)
        if p in pg and q in norm(pg[p][1]):
            vs = "verbatim"
        elif p in pg and ql in norm(pg[p][1], loose=True):
            vs = "verbatim_loose"
        else:
            vs = "not_on_page"
        printed_ok = p in pg and str(pg[p][0]) == str(r.printed_page)
        own = ALIASES[r['product']]
        low = q.lower()
        oth = [o for o in OTHER if o not in own and re.search(r'\b' + o + r'\b', low)]
        if not any(o in low for o in own):
            subj = "product_absent"
        elif not oth:
            subj = "sole"
        else:
            n_own = sum(len(re.findall(r'\b' + o + r'\b', low)) for o in own)
            n_oth = sum(len(re.findall(r'\b' + o + r'\b', low)) for o in oth)
            first_oth = min(low.find(o) for o in oth)
            first_own = min(low.find(o) for o in own if o in low)
            subj = "secondary" if (n_oth > n_own and first_oth < first_own) else "shared"
        region, spk, spk_status = "filing", "", "n/a (filing)"
        if r.doc_type == 'earnings_call':
            L, s0, e0 = bounds[r.path]
            li = next((k for k, l in enumerate(L) if q[:50] in norm(l)), None)
            if li is None:
                region = "unlocated"
            elif li < s0:
                region = "publisher_text_before_call"
            elif li > e0:
                region = "publisher_text_after_call"
            else:
                region = "call"
            ds = derive_speaker(L, li) if (li is not None and region == "call") else None
            if ds and not (ds.startswith('Speaker #') or ds == 'Operator' or
                           re.fullmatch(r"[A-Z][A-Za-z.'’\-]+( [A-Z][A-Za-z.'’\-]+){1,3}", ds)):
                ds = None  # not a person's name (e.g. a slide title)
            old = "" if pd.isna(r.speaker) else str(r.speaker)
            if ds and not ds.startswith('Speaker #'):
                spk, spk_status = ds, ("confirmed" if ds.split()[-1] in old else ("replaced" if old else "filled"))
            elif ds:
                spk, spk_status = ds, "unidentified_label"
            elif old and old not in JUNK_SPK:
                spk, spk_status = old, "collector_unverified"
            else:
                spk, spk_status = "", ("junk_removed" if old else "unknown")
        if region.startswith("publisher"):
            status = "drop_publisher_text"
        elif vs == "not_on_page":
            status = "drop_not_on_page"
        elif subj == "product_absent":
            status = "drop_product_absent"
        else:
            status = "verified" + ("_secondary_subject" if subj == "secondary" else "")
        maker = r.maker
        if r['product'] == 'Jardiance':
            mis = "partner (BI is the maker; Lilly co-commercializes)"
        else:
            mis = "yes"
        role = "focal_company_doc (not a peer)" if maker in FOCAL else "peer_doc"
        frag = (not re.search(r'[.!?;:"”)]\s*$', r.quote.strip())) or (' | ' in r.quote)
        out.append(dict(verify_status=status, quote_check=vs, printed_ok=printed_ok, subject=subj,
                        other_products="; ".join(oth), region=region, speaker_verified=spk,
                        speaker_status=spk_status, fragment=frag, topic_fixed=topic_fixed(r.quote),
                        maker_is_source=mis, source_role=role, true_maker=TRUE_MAKER.get(r['product'], maker),
                        page_granularity=("whole_doc_one_page" if len(pg) == 1 and r.doc_type == 'annual_report'
                                          else ("web_page_single" if len(pg) == 1 else "page"))))
    v = pd.concat([d, pd.DataFrame(out)], axis=1)
    v['period'] = v.doc.str.extract(r'(FY\d{4}|\d{4}Q\d|\d{4}H\d|\d{4})$')[0].where(v.period.isna(), v.period)
    v.to_pickle('/tmp/pe_quotes_full.pkl')
    keep = v[v.verify_status.str.startswith('verified')].copy()
    keep['speaker'] = keep['speaker_verified']
    keep = keep.drop(columns=['speaker_verified'])
    buf = io.StringIO()
    keep.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/rival_product_statements.csv", buf.getvalue(), group="tables",
          doc_type="table", quality="verified", source_url="data/moat/tables/rival_product_statements.csv")
    buf = io.StringIO()
    v[~v.verify_status.str.startswith('verified')].to_csv(buf, index=False)
    write("verify_peers", "verified/peers/rival_product_statements_dropped.csv", buf.getvalue(), group="tables",
          doc_type="table", quality="verified", source_url="data/moat/tables/rival_product_statements.csv")
    print(v.verify_status.value_counts())
    print(v.groupby(['doc_type', 'speaker_status']).size())
    pr = v.groupby('product').verify_status.apply(lambda s: s.str.startswith('verified').mean()).round(3)
    print(pr)
    print("topic changed by fix:", (v.topic != v.topic_fixed).sum())
    print("pricing old/new:", v.topic.str.contains('pricing').sum(), v.topic_fixed.str.contains('pricing').sum())
    print("fragments:", v.fragment.sum(), "period filled:", v.period.notna().sum())


if __name__ == "__main__":
    main()
