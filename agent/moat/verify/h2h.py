"""Re-derive the head-to-head design of every ClinicalTrials.gov row from the full v2 record.

Fixes in the collector's rule: (1) placebo / matching-placebo interventions ("Placebo to match adalimumab") were
counted as the drug, so double-dummy RCTs were labeled combination_same_arm; (2) only generic names were matched,
so arms naming a brand or code (Skyrizi, LY3298176, BI 655066) were missed; (3) separate arms were called
head-to-head even when allocation was non-randomized, the study was observational, or arms were sequential.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/ct_cache")
OUTD = ROOT / "data/moat/verified/product"
SYN = {
    "pembrolizumab": ["keytruda", "mk-3475", "mk3475", "lambrolizumab"],
    "nivolumab": ["opdivo", "bms-936558", "mdx-1106", "ono-4538"],
    "durvalumab": ["imfinzi", "medi4736", "medi 4736"],
    "atezolizumab": ["tecentriq", "mpdl3280a", "rg7446"],
    "sitagliptin": ["januvia", "janumet", "mk-0431"],
    "semaglutide": ["ozempic", "wegovy", "rybelsus", "nn9535", "nn9924", "nn9536"],
    "empagliflozin": ["jardiance", "bi 10773", "bi10773", "synjardy"],
    "dapagliflozin": ["farxiga", "forxiga", "bms-512148"],
    "tirzepatide": ["mounjaro", "zepbound", "ly3298176"],
    "dulaglutide": ["trulicity", "ly2189265"],
    "orforglipron": ["ly3502970", "foundayo"],
    "apixaban": ["eliquis", "bms-562247"],
    "rivaroxaban": ["xarelto", "bay 59-7939", "bay59-7939"],
    "palbociclib": ["ibrance", "pd-0332991", "pd 0332991"],
    "abemaciclib": ["verzenio", "ly2835219"],
    "ribociclib": ["kisqali", "lee011"],
    "tafamidis": ["vyndaqel", "vyndamax", "fx-1006"],
    "acoramidis": ["attruby", "ag10"],
    "vutrisiran": ["amvuttra", "aln-ttrsc02"],
    "risankizumab": ["skyrizi", "bi 655066", "bi655066", "abbv-066"],
    "upadacitinib": ["rinvoq", "abt-494"],
    "guselkumab": ["tremfya", "cnto1959", "cnto 1959"],
    "ustekinumab": ["stelara", "cnto1275", "cnto 1275", "wezlana"],
    "secukinumab": ["cosentyx", "ain457"],
    "vedolizumab": ["entyvio", "mln0002"],
    "adalimumab": ["humira", "amjevita", "d2e7"],
    "etanercept": ["enbrel"],
    "daratumumab": ["darzalex"],
    "isatuximab": ["sarclisa", "sar650984"],
    "osimertinib": ["tagrisso", "azd9291"],
    "amivantamab": ["rybrevant", "jnj-61186372"],
    "lazertinib": ["lazcluze", "yh25448", "jnj-73841937"],
    "evolocumab": ["repatha", "amg 145", "amg145"],
    "alirocumab": ["praluent", "sar236553", "regn727"],
    "inclisiran": ["leqvio", "aln-pcssc"],
    "enlicitide": ["mk-0616", "lipfendra"],
    "bictegravir": ["biktarvy", "gs-9883", "b/f/taf", "bic/ftc/taf"],
    "dolutegravir": ["dovato", "tivicay", "triumeq", "gsk1349572", "dtg"],
    "cabotegravir": ["cabenuva", "apretude", "vocabria", "gsk1265744"],
    "lenacapavir": ["yeztugo", "sunlenca", "gs-6207"],
}
# appendix pairs: (company product, listed rival)
APPENDIX = [
    ("pembrolizumab", "nivolumab"), ("pembrolizumab", "durvalumab"), ("pembrolizumab", "atezolizumab"),
    ("nivolumab", "atezolizumab"), ("sitagliptin", "semaglutide"), ("sitagliptin", "empagliflozin"),
    ("apixaban", "rivaroxaban"), ("palbociclib", "abemaciclib"), ("palbociclib", "ribociclib"),
    ("tafamidis", "acoramidis"), ("tafamidis", "vutrisiran"), ("tirzepatide", "semaglutide"),
    ("dulaglutide", "semaglutide"), ("orforglipron", "semaglutide"),
    ("risankizumab", "guselkumab"), ("risankizumab", "ustekinumab"), ("risankizumab", "secukinumab"),
    ("risankizumab", "vedolizumab"), ("risankizumab", "adalimumab"), ("upadacitinib", "guselkumab"),
    ("upadacitinib", "ustekinumab"), ("upadacitinib", "secukinumab"), ("upadacitinib", "vedolizumab"),
    ("upadacitinib", "adalimumab"), ("daratumumab", "isatuximab"), ("osimertinib", "amivantamab"),
    ("osimertinib", "lazertinib"), ("dapagliflozin", "empagliflozin"), ("evolocumab", "alirocumab"),
    ("evolocumab", "inclisiran"), ("evolocumab", "enlicitide"), ("etanercept", "risankizumab"),
    ("etanercept", "upadacitinib"), ("etanercept", "adalimumab"), ("bictegravir", "dolutegravir"),
    ("bictegravir", "cabotegravir"), ("lenacapavir", "cabotegravir"),
]


def has(text, drug):
    t = text.lower()
    return drug in t or any(s in t for s in SYN.get(drug, []))


def classify(s, a, b):
    p = s["protocolSection"]
    dm = p.get("designModule", {})
    aim = p.get("armsInterventionsModule", {})
    ivs = {f"{i.get('type', '').title()}: {i.get('name', '')}".lower(): i for i in aim.get("interventions", [])}
    byname = {i.get("name", "").lower(): i for i in aim.get("interventions", [])}

    def drugs_in(ref):
        iv = ivs.get(ref.lower()) or byname.get(ref.split(": ", 1)[-1].lower())
        names = [ref] + ((iv.get("otherNames", []) + [iv.get("name", "")]) if iv else [])
        txt = " ".join(names)
        if "placebo" in (ref + " " + (iv.get("name", "") if iv else "")).lower():
            return set()
        return {d for d in (a, b) if has(txt, d)}

    arms = []
    for g in aim.get("armGroups", []):
        ds = set()
        for ref in g.get("interventionNames", []):
            ds |= drugs_in(ref)
        if not g.get("interventionNames"):
            ds = {d for d in (a, b) if has(g.get("label", "") + " " + g.get("description", ""), d)}
        lab = g.get("label", "")
        if len(ds) == 2 and "placebo" not in lab.lower() and not any(w in lab.lower() for w in (" followed by ", "switch", " then ", " to ", "→")):
            lab_ds = {d for d in (a, b) if has(lab, d)}
            if len(lab_ds) == 1:  # the other drug is listed only as rescue / switch therapy in this arm
                ds = lab_ds
        arms.append((g.get("label", ""), g.get("type", ""), ds))
    only_a = [x for x in arms if a in x[2] and b not in x[2]]
    only_b = [x for x in arms if b in x[2] and a not in x[2]]
    both = [x for x in arms if a in x[2] and b in x[2]]
    st = p.get("designModule", {}).get("studyType", "")
    alloc = dm.get("designInfo", {}).get("allocation", "")
    model = dm.get("designInfo", {}).get("interventionModel", "")
    if only_a and only_b:
        if st != "INTERVENTIONAL":
            d = "observational_cohorts"
        elif alloc == "RANDOMIZED" and model == "CROSSOVER":
            d = "h2h_randomized_crossover"
        elif alloc == "RANDOMIZED":
            d = "h2h_randomized"
        elif model == "SEQUENTIAL":
            d = "separate_arms_sequential_nonrandomized"
        else:
            d = "separate_arms_nonrandomized"
    elif both:
        d = "combination_or_choice_same_arm"
    else:
        d = "mentioned_not_compared"
    return d, {"study_type": st, "allocation": alloc, "model": model,
               "arm_a": " / ".join(x[0] for x in only_a)[:200], "arm_b": " / ".join(x[0] for x in only_b)[:200]}


def load(nct):
    f = CACHE / f"{nct}.json"
    return json.loads(f.read_text()) if f.exists() else None


def info(s):
    p = s["protocolSection"]
    po = [o.get("measure", "") for o in p.get("outcomesModule", {}).get("primaryOutcomes", [])]
    return {"phase": "/".join(p.get("designModule", {}).get("phases", [])), "status": p["statusModule"].get("overallStatus"),
            "results_posted": "y" if s.get("hasResults") else "n", "title": p["identificationModule"].get("briefTitle", ""),
            "acronym": p["identificationModule"].get("acronym", ""), "primary_outcome": " | ".join(po)[:400],
            "conditions": "; ".join(p.get("conditionsModule", {}).get("conditions", []))[:150],
            "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "")}


def main():
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/head_to_head.csv")))
    stats, out = {}, []
    for r in rows:
        a, b = r["drugs"].split(" vs ")
        s = load(r["nct_id"])
        if s is None:
            r.update(verify_status="dropped", design_verified="", verify_note="record not returned by CT.gov v2")
            out.append(r)
            continue
        d, x = classify(s, a, b)
        r["design_verified"] = d
        r.update(x)
        old = r["design"]
        true_h2h = d.startswith("h2h_randomized")
        if (old == "head_to_head_separate_arms") == true_h2h:
            r["verify_status"] = "verified"
            r["verify_note"] = f"CT.gov v2 record: {d}, allocation={x['allocation'] or 'NA'}, model={x['model'] or 'NA'}"
        else:
            r["verify_status"] = "fixed"
            r["verify_note"] = (f"collector flag {old} wrong: CT.gov v2 record shows {d} "
                                f"(studyType={x['study_type']}, allocation={x['allocation'] or 'NA'}, model={x['model'] or 'NA'})")
        r["true_head_to_head"] = "y" if true_h2h else "n"
        k = (old, d)
        stats[k] = stats.get(k, 0) + 1
        out.append(r)
    # extra searches (code names) for pairs the collector could not query
    have = {(r["nct_id"], r["drugs"]) for r in rows}
    extra_path = CACHE / "_extra.json"
    for e in (json.loads(extra_path.read_text()) if extra_path.exists() else []):
        if (e["nct_id"], e["drugs"]) in have:
            continue
        s = load(e["nct_id"])
        a, b = e["drugs"].split(" vs ")
        d, x = classify(s, a, b)
        i = info(s)
        r = {"nct_id": e["nct_id"], "drugs": e["drugs"], "design": "", "phase": i["phase"], "status": s["protocolSection"]["statusModule"].get("overallStatus"), "verify_status": "added",
             "results_posted": i["results_posted"], "title": i["title"], "primary_outcome": i["primary_outcome"],
             "sponsor": i["sponsor"], "url": f"https://clinicaltrials.gov/study/{e['nct_id']}",
             "source": f"https://clinicaltrials.gov/api/v2/studies/{e['nct_id']}", "source_row": e["nct_id"],
             "design_verified": d, "true_head_to_head": "y" if d.startswith("h2h_randomized") else "n",
             "verify_note": f"added by verifier: missed by collector (query.intr {e['query']}); {d}", **x}
        out.append(r)
        have.add((e["nct_id"], e["drugs"]))
    cols = list(rows[0].keys())
    for c in ["design_verified", "true_head_to_head", "study_type", "allocation", "model", "arm_a", "arm_b", "verify_status",
              "verify_note"]:
        if c not in cols:
            cols.append(c)
    # rename collector's trial status column to keep it apart from the verify status
    with open(OUTD / "head_to_head.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(out)
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(k, v)
    # per appendix pair
    by = {}
    for r in out:
        a, b = r["drugs"].split(" vs ")
        by.setdefault(frozenset((a, b)), []).append(r)
    pr = []
    for a, b in APPENDIX:
        rs = [r for r in by.get(frozenset((a, b)), []) if r.get("true_head_to_head") == "y"]
        seen = set()
        trials = []
        for r in rs:
            if r["nct_id"] in seen:
                continue
            seen.add(r["nct_id"])
            i = info(load(r["nct_id"]))
            trials.append({**i, "nct_id": r["nct_id"], "design_verified": r["design_verified"], "arm_a": r["arm_a"],
                           "arm_b": r["arm_b"], "n_rows_checked": len(by.get(frozenset((a, b)), []))})
        pr.append({"pair": f"{a} vs {b}", "n_ctgov_rows_checked": len(by.get(frozenset((a, b)), [])),
                   "n_true_h2h": len(trials), "trials": trials})
    (OUTD / "_h2h_pairs_raw.json").write_text(json.dumps(pr, indent=1))
    for p in pr:
        print(p["pair"], p["n_ctgov_rows_checked"], p["n_true_h2h"])


if __name__ == "__main__":
    main()
