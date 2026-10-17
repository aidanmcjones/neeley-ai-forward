"""Build tables/pipeline_landscape.csv and tables/pipeline_assets.csv from the CT.gov harvest."""
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from agent.moat.common import write, note_gap
from agent.tenk import sec_get

SC = Path("data/moat/scratch/pipeline")

# indication classifier (conditions + title). First label that matches is primary; all matches listed.
IND = [
    ("type 2 diabetes", r"type 2 diab|t2d|diabetes mellitus, type 2|type 2 diabetes"),
    ("obesity", r"obes|overweight|weight (management|loss|reduction)"),
    ("afib anticoagulation", r"atrial fibrillation|venous thrombo|thromboembol|stroke prevention|factor xi"),
    ("NSCLC", r"non-?small[- ]cell lung|nsclc"),
    ("melanoma", r"melanoma"),
    ("RCC", r"renal cell|kidney cancer"),
    ("HCC", r"hepatocellular|liver cancer"),
    ("bladder/urothelial", r"urothelial|bladder cancer"),
    ("gastric", r"gastric|stomach|gastroesophageal junction"),
    ("esophageal", r"esophag|oesophag"),
    ("HNSCC", r"head and neck"),
    ("TNBC", r"triple[- ]negative"),
    ("HR+ breast", r"hormone receptor|hr\+|hr-positive|er\+|er-positive|breast"),
    ("plaque psoriasis", r"psoria(sis|tic)(?! arthritis)|plaque psoriasis"),
    ("psoriatic arthritis", r"psoriatic arthritis"),
    ("Crohn's", r"crohn"),
    ("ulcerative colitis", r"ulcerative colitis"),
    ("rheumatoid arthritis", r"rheumatoid"),
    ("atopic dermatitis", r"atopic dermatitis|eczema"),
    ("multiple myeloma", r"myeloma"),
    ("HIV", r"\bhiv\b|human immunodeficiency"),
    ("ATTR-CM", r"transthyretin|attr|amyloid.{0,30}cardiomyopathy|cardiac amyloid"),
    ("hypercholesterolemia/ASCVD", r"cholesterol|lipoprotein|ldl|atherosclero|cardiovascular|lipidemia"),
    ("MASH", r"nash|mash|steatohepatitis|steatotic"),
]
GROUP = {  # indication -> reporting group
    "type 2 diabetes": "diabetes/obesity", "obesity": "diabetes/obesity",
    "plaque psoriasis": "psoriasis/IBD/immunology", "psoriatic arthritis": "psoriasis/IBD/immunology",
    "Crohn's": "psoriasis/IBD/immunology", "ulcerative colitis": "psoriasis/IBD/immunology",
    "rheumatoid arthritis": "psoriasis/IBD/immunology", "atopic dermatitis": "psoriasis/IBD/immunology",
}
PLACEBO = re.compile(r"placebo|saline|vehicle|sham|matching|standard of care|best supportive|\bsoc\b|dextrose|"
                     r"no treatment|usual care|control|diluent|water for|^observation|^surgery|radiotherapy|"
                     r"radiation|^blood|^biopsy|questionnaire|diet|exercise|lifestyle|pharmacokinetic sampling", re.I)
# marketed comparators and backbone drugs: never credited as the sponsor's asset
COMP = set("""pembrolizumab keytruda nivolumab opdivo ipilimumab atezolizumab durvalumab cemiplimab carboplatin cisplatin
paclitaxel nab-paclitaxel docetaxel pemetrexed gemcitabine etoposide oxaliplatin capecitabine fluorouracil 5-fu
leucovorin irinotecan bevacizumab trastuzumab cetuximab ramucirumab osimertinib tagrisso sotorasib fulvestrant
letrozole anastrozole exemestane tamoxifen palbociclib ribociclib abemaciclib dexamethasone lenalidomide
pomalidomide bortezomib daratumumab carfilzomib cyclophosphamide semaglutide ozempic wegovy rybelsus tirzepatide
mounjaro zepbound dulaglutide liraglutide metformin sitagliptin empagliflozin dapagliflozin glargine insulin
degludec apixaban rivaroxaban warfarin enoxaparin heparin aspirin atorvastatin rosuvastatin ezetimibe evolocumab
alirocumab inclisiran ustekinumab adalimumab secukinumab risankizumab guselkumab ixekizumab upadacitinib
vedolizumab infliximab methotrexate dupilumab tofacitinib baricitinib etanercept tenofovir emtricitabine
dolutegravir bictegravir biktarvy descovy truvada tafamidis vutrisiran acoramidis resmetirom pioglitazone
glimepiride lantus tresiba fiasp novolog humalog sunitinib sorafenib lenvatinib axitinib cabozantinib enfortumab
vedotin gemcitabine-cisplatin tislelizumab toripalimab sintilimab camrelizumab trifluridine regorafenib
fruquintinib nab paclitaxel ado-trastuzumab deruxtecan sacituzumab govitecan eribulin vinorelbine capivasertib
alpelisib everolimus elacestrant imlunestrant olaparib enzalutamide abiraterone""".split())
OWN10 = [("ABBV", r"abbvie|allergan|pharmacyclics"), ("MRK", r"merck sharp|\bmsd\b|merck & co|merck research"),
         ("BMY", r"bristol|celgene|juno thera|myokardia|karuna"), ("PFE", r"pfizer|seagen|wyeth|arena pharma"),
         ("LLY", r"eli lilly|\blilly\b|loxo|dice thera|morphic"), ("JNJ", r"janssen|johnson & johnson|actelion"),
         ("AMGN", r"^amgen|horizon thera"), ("GILD", r"gilead|kite pharma"), ("AZN", r"astrazeneca|medimmune|alexion"),
         ("NVO", r"novo nordisk")]
PEERS = [("GSK", r"glaxosmithkline|\bgsk\b|viiv"), ("SNY", r"sanofi|genzyme"), ("TAK", r"takeda"),
         ("NVS", r"novartis"), ("ROG", r"hoffmann|genentech|\broche\b|chugai"), ("REGN", r"regeneron"),
         ("BAYRY", r"bayer"), ("BI", r"boehringer"), ("DSNKY", r"daiichi"), ("ALPMY", r"astellas"),
         ("VRTX", r"vertex"), ("BIIB", r"biogen"), ("ALNY", r"alnylam"), ("MRNA", r"moderna"),
         ("ONC", r"beigene|beone"), ("EISAY", r"eisai"), ("OTSKY", r"otsuka"), ("UCB", r"\bucb\b"),
         ("INCY", r"incyte"), ("MRKDY", r"merck kgaa|emd serono"), ("ARGX", r"argenx"), ("BNTX", r"biontech")]


def own_of(name):
    n = name.lower()
    for t, rx in OWN10:
        if re.search(rx, n):
            return "own10", t
    for t, rx in PEERS:
        if re.search(rx, n):
            return "peer", t
    return "other", None


def norm_co(s):
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    s = re.sub(r"\b(inc|incorporated|corp|corporation|ltd|limited|llc|plc|co|company|sa|ag|nv|se|gmbh|lp|holdings|"
               r"pharmaceuticals?|pharma|therapeutics|biopharma|biosciences?|bio|biotech|biotechnology|medicines?|"
               r"sciences|oncology|group|international|usa|us|the|and|ab|as|spa|kk|bv)\b", " ", s)
    return " ".join(s.split())


def asset_norm(s):
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.split(r" \+ | and |/| plus |,|;", s)[0]
    s = re.sub(r"\b(qd|bid|qw|tid|q\d+w|prefilled|syringe|pen|biosimilar|treatment|therapy|blank|analog|placebo)\b", " ", s)
    s = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|ug|g|ml|iu|units?|mg/kg|%|q\d+w)\b", " ", s)
    s = re.sub(r"\b(tablets?|capsules?|injection|subcutaneous|oral|intravenous|iv|sc|infusion|solution|low|high|"
               r"dose|doses|weekly|daily|once|arm|group|cohort|part|fixed|combination|mono(therapy)?|versus|vs)\b", " ", s)
    s = re.sub(r"[^a-z0-9\-]", " ", s)
    return " ".join(s.split())


def has_codeid(s):
    return bool(re.search(r"[A-Za-z]{2,6}[- ]?\d{3,}|\b[A-Z]{2,5}-?\d+[A-Za-z]?\b", s))


def is_code(s):
    return bool(re.search(r"[A-Za-z]{2,6}[- ]?\d{3,}|\b[a-z]+(mab|nib|tide|stat|gliptin|gliflozin|ciclib|degib|lutamide|"
                          r"parib|tinib|limab|zumab|ximab|rsen|siran|tug|mig|tecan|vedotin)\b", s, re.I))


# SEC filer names
tickers = sec_get("https://www.sec.gov/files/company_tickers_exchange.json", as_json=True)
sec = {}
for r in tickers["data"]:
    d = dict(zip(tickers["fields"], r))
    sec.setdefault(norm_co(d["name"]), (int(d["cik"]), d["ticker"], d["name"], d.get("exchange")))
(SC / "sec_names.json").write_text(json.dumps({k: v for k, v in sec.items()}))


def sec_match(sponsor):
    mm = re.search(r"subsidiary of (.+)$", sponsor, re.I)
    if mm:
        sponsor = mm.group(1)
    n = norm_co(sponsor)
    if sponsor in ("United BioPharma", "Polaris Group", "Asana BioSciences"):
        return None  # name collision with unrelated SEC filers
    if n in sec:
        return sec[n]
    return None


studies = {}
for f in sorted(SC.glob("*.json")):
    if f.name in ("sec_names.json",):
        continue
    for s in json.load(open(f)):
        studies.setdefault(s["protocolSection"]["identificationModule"]["nctId"], s)

rows = []
for nct, s in studies.items():
    p = s["protocolSection"]
    conds = p.get("conditionsModule", {}).get("conditions", [])
    title = p["identificationModule"].get("briefTitle", "")
    text = " | ".join(conds) + " | " + title
    inds = [n for n, rx in IND if re.search(rx, text, re.I)]
    # keep generic cancer labels honest: breast needs HR/ER wording else only TNBC / skip
    if "HR+ breast" in inds and "TNBC" not in inds and not re.search(r"hormone receptor|hr\+|hr-positive|er\+|er-positive", text, re.I):
        inds.remove("HR+ breast")
    if "hypercholesterolemia/ASCVD" in inds and len(inds) > 1 and not re.search(r"cholesterol|lipoprotein|ldl|lipidemia|atherosclero", text, re.I):
        inds.remove("hypercholesterolemia/ASCVD")
    if not inds:
        continue
    sp = p["sponsorCollaboratorsModule"]["leadSponsor"]["name"]
    colls = [c["name"] for c in p["sponsorCollaboratorsModule"].get("collaborators", [])]
    ints = p.get("armsInterventionsModule", {}).get("interventions", [])
    cands = []
    for i in ints:
        names = [i["name"]] + i.get("otherNames", [])
        if i["type"] not in ("DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT", "OTHER"):
            continue
        if PLACEBO.search(i["name"]):
            continue
        toks = {t for n in names for t in re.findall(r"[a-z0-9\-]+", n.lower())}
        if toks & COMP and not any(has_codeid(n) for n in names):
            continue
        cands.append(names)
    if not cands:
        continue
    sm = sec_match(sp)
    kind, tk = own_of(sp)
    if not any(x in ("PHASE2", "PHASE3") for x in p["designModule"]["phases"]) or "PHASE1" in p["designModule"]["phases"]:
        continue
    ph = "/".join(x.replace("PHASE", "Phase ") for x in p["designModule"]["phases"] if x != "NA")
    rows.append(dict(
        nct_id=nct, sponsor=sp, collaborators="; ".join(colls), drug="; ".join(c[0] for c in cands[:4]),
        _cands=cands[:4], mechanism="", phase=ph.replace("Phase 2/Phase 3", "Phase 2/3"),
        status=p["statusModule"].get("overallStatus"),
        enrollment=p["designModule"].get("enrollmentInfo", {}).get("count"),
        start=p["statusModule"].get("startDateStruct", {}).get("date"),
        primary_completion=p["statusModule"].get("primaryCompletionDateStruct", {}).get("date"),
        has_results=s.get("hasResults"), conditions="; ".join(conds[:6]), indications="; ".join(inds),
        primary_indication=inds[0], title=title,
        is_sponsor_public=bool(sm), sponsor_cik=sm[0] if sm else (None), sponsor_ticker=sm[1] if sm else tk,
        owner_class=kind, owner_ticker=tk,
        source=f"https://clinicaltrials.gov/api/v2/studies/{nct}", source_row=nct))
tr = pd.DataFrame(rows)
print("trials", len(tr))

# --- asset clustering: union-find over names within one sponsor
assets = defaultdict(lambda: dict(trials=[]))
parent = {}


def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    parent[find(a)] = find(b)


spkey = {r.sponsor: (own_of(r.sponsor)[1] or norm_co(r.sponsor)) for r in tr.itertuples()}
for r in tr.itertuples():
    for names in r._cands if False else getattr(r, "_cands", []):
        pass
tr = tr.rename(columns={"_cands": "cands"})
for r in tr.itertuples():
    sk = spkey[r.sponsor]
    for names in r.cands:
        ns = [asset_norm(n) for n in names if asset_norm(n)]
        for a in ns[1:]:
            union((sk, ns[0]), (sk, a))
        if ns:
            find((sk, ns[0]))
rank = {"Phase 3": 3, "Phase 2/3": 2.5, "Phase 2": 2}
recs = []
for r in tr.itertuples():
    sk = spkey[r.sponsor]
    seen = set()
    for names in r.cands:
        ns = [asset_norm(n) for n in names if asset_norm(n)]
        if not ns:
            continue
        root = find((sk, ns[0]))
        if root in seen:
            continue
        seen.add(root)
        disp = next((n for n in names if is_code(n) and len(n) < 25), names[0])
        recs.append(dict(key=root, sk=sk, disp=disp, alias=set(names), r=r))
ag = defaultdict(list)
for x in recs:
    ag[x["key"]].append(x)
arows = []
for key, xs in ag.items():
    trs = [x["r"] for x in xs]
    sponsors = pd.Series([t.sponsor for t in trs]).mode()[0]
    kind, tk = own_of(sponsors)
    sm = sec_match(sponsors)
    best = max(trs, key=lambda t: (rank.get(t.phase, 0), str(t.primary_completion)))
    inds = sorted({i for t in trs for i in t.indications.split("; ")})
    pcs = sorted(str(t.primary_completion) for t in trs if t.primary_completion and t.status in
                 ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"))
    pcs_all = sorted(str(t.primary_completion) for t in trs if t.primary_completion)
    aliases = sorted({a for x in xs for a in x["alias"]})[:6]
    flag = {"own10": "owned by one of the 10", "peer": "owned by a listed peer"}.get(
        kind, "potential licensing or acquisition target")
    arows.append(dict(
        sponsor=sponsors, asset=xs[0]["disp"], aliases="; ".join(aliases),
        most_advanced_phase=max((t.phase for t in trs), key=lambda p: rank.get(p, 0)),
        indications="; ".join(inds), n_trials=len(trs), n_active=sum(t.status in (
            "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION") for t in trs),
        nearest_primary_completion=(pcs or pcs_all or [None])[0],
        latest_primary_completion=(pcs_all or [None])[-1], flag=flag, owner_ticker=tk,
        is_sponsor_public=bool(sm), sponsor_cik=sm[0] if sm else None, sponsor_ticker=sm[1] if sm else tk,
        sample_nct=best.nct_id,
        source="https://clinicaltrials.gov/api/v2/studies/" + best.nct_id,
        source_row="; ".join(sorted({t.nct_id for t in trs})[:25])))
ad = pd.DataFrame(arows).sort_values(["flag", "most_advanced_phase", "n_trials"], ascending=[True, False, False])
tr["asset_key"] = tr.cands.apply(lambda c: c[0][0])
out = tr.drop(columns=["cands"])
write("pipeline", "tables/pipeline_landscape.csv", out.to_csv(index=False), group="pipeline", doc_type="table",
      source_url="https://clinicaltrials.gov/api/v2/studies")
write("pipeline", "tables/pipeline_assets.csv", ad.to_csv(index=False), group="pipeline", doc_type="table",
      source_url="https://clinicaltrials.gov/api/v2/studies")
print(len(out), len(ad), ad.flag.value_counts().to_dict())
note_gap("pipeline", None, "pipeline_landscape.mechanism", "CT.gov v2 has no mechanism field; column left blank")
note_gap("pipeline", None, "pipeline_landscape.indication_map", "epi stream indication_map.csv absent; own regex classifier in agent/moat/pipe_build.py")
