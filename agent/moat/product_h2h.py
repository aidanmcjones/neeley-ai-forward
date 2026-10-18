"""Head-to-head evidence: ClinicalTrials.gov v2 + PubMed per competitive pair."""
import csv
import io
import itertools
import time

import requests

from agent.moat.common import write, note_gap

SETS = {
    "ici": ["pembrolizumab", "nivolumab", "durvalumab", "atezolizumab"],
    "t2d": ["sitagliptin", "semaglutide", "empagliflozin", "dapagliflozin", "tirzepatide", "dulaglutide", "orforglipron"],
    "anticoag": ["apixaban", "rivaroxaban"],
    "cdk": ["palbociclib", "abemaciclib", "ribociclib"],
    "attr": ["tafamidis", "acoramidis", "vutrisiran"],
    "immuno": ["risankizumab", "upadacitinib", "guselkumab", "ustekinumab", "secukinumab", "vedolizumab",
               "adalimumab", "etanercept"],
    "myeloma": ["daratumumab", "isatuximab"],
    "egfr": ["osimertinib", "amivantamab", "lazertinib"],
    "lipid": ["evolocumab", "alirocumab", "inclisiran", "enlicitide"],
    "hiv": ["bictegravir", "dolutegravir", "cabotegravir", "lenacapavir"],
}
PAIRS = [(a, b) for v in SETS.values() for a, b in itertools.combinations(v, 2)]
H = {"User-Agent": "Neeley AI Forward hackathon"}
FIELDS = "NCTId,BriefTitle,Phase,OverallStatus,HasResults,ArmGroupInterventionName,PrimaryOutcomeMeasure,StartDate,LeadSponsorName"


def ct(a, b):
    out, tok = [], None
    while True:
        p = {"query.intr": f"{a} AND {b}", "pageSize": 100, "fields": FIELDS}
        if tok:
            p["pageToken"] = tok
        r = requests.get("https://clinicaltrials.gov/api/v2/studies", params=p, headers=H, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j.get("studies", [])
        tok = j.get("nextPageToken")
        if not tok:
            return out
        time.sleep(0.3)


def design(s, a, b):
    arms = s["protocolSection"].get("armsInterventionsModule", {}).get("armGroups", [])
    ina = [any(a in n.lower() for n in x.get("interventionNames", [])) for x in arms]
    inb = [any(b in n.lower() for n in x.get("interventionNames", [])) for x in arms]
    sep = any(x and not y for x, y in zip(ina, inb)) and any(y and not x for x, y in zip(ina, inb))
    both = any(x and y for x, y in zip(ina, inb))
    return "head_to_head_separate_arms" if sep else ("combination_same_arm" if both else "mentioned_not_compared")


def pubmed(a, b):
    q = (f'({a}[Title/Abstract]) AND ({b}[Title/Abstract]) AND (randomized controlled trial[pt] OR '
         f'network meta-analysis[tiab] OR "head-to-head"[tiab] OR "indirect comparison"[tiab] OR meta-analysis[pt])')
    r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                     params={"db": "pubmed", "term": q, "retmax": 25, "retmode": "json", "sort": "relevance"},
                     headers=H, timeout=60)
    ids = r.json()["esearchresult"]["idlist"]
    if not ids:
        return []
    time.sleep(0.4)
    r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                     params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"}, headers=H,
                     timeout=60).json()["result"]
    return [(i, r[i]["title"], r[i].get("pubdate", "")[:4], r[i].get("pubtype", [])) for i in ids if i in r]


def tocsv(rows, cols):
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(cols)
    w.writerows(rows)
    return f.getvalue()


def main():
    rows, prow = [], []
    for a, b in PAIRS:
        try:
            for s in ct(a, b):
                p = s["protocolSection"]
                nct = p["identificationModule"]["nctId"]
                po = [o.get("measure") for o in p.get("outcomesModule", {}).get("primaryOutcomes", [])]
                rows.append([nct, f"{a} vs {b}", design(s, a, b), "/".join(p.get("designModule", {}).get("phases", [])),
                             p["statusModule"].get("overallStatus"), "y" if s.get("hasResults") else "n",
                             p["identificationModule"].get("briefTitle"), " | ".join(x for x in po if x)[:400],
                             p["statusModule"].get("startDateStruct", {}).get("date", ""),
                             p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
                             f"https://clinicaltrials.gov/study/{nct}",
                             f"https://clinicaltrials.gov/api/v2/studies/{nct}", nct])
        except Exception as e:
            note_gap("product", f"{a}-{b}", "ctgov head-to-head", str(e))
        try:
            for pid, t, y, pt in pubmed(a, b):
                prow.append([pid, f"{a} vs {b}", t, y, "; ".join(pt), f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                             "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", pid])
        except Exception as e:
            note_gap("product", f"{a}-{b}", "pubmed head-to-head", str(e))
        print(a, b, len(rows), len(prow), flush=True)
        time.sleep(0.3)
    cols = ["nct_id", "drugs", "design", "phase", "status", "results_posted", "title", "primary_outcome",
            "start_date", "sponsor", "url", "source", "source_row"]
    write("product", "tables/head_to_head.csv", tocsv(rows, cols), group="product", doc_type="table",
          source_url="https://clinicaltrials.gov/api/v2/studies")
    write("product", "tables/head_to_head_pubmed.csv",
          tocsv(prow, ["pmid", "drugs", "title", "year", "pubtypes", "url", "source", "source_row"]),
          group="product", doc_type="table", source_url="https://pubmed.ncbi.nlm.nih.gov/")
    print(len(rows), len(prow))


if __name__ == "__main__":
    main()
