"""Human-judged tiers for every randomized separate-arm trial on an appendix pair, read from the CT.gov v2 record.

direct   = the trial randomizes drug A against drug B (same backbone, or the two branded regimens) as its comparison
regimen  = randomized, but A and B sit inside different regimens (A+chemo vs B+other agent): supports a regimen
           claim only, not a molecule-vs-molecule claim
none     = A and B are in different cohorts/backbones of a platform, dose-escalation, PK/DDI or class-strategy study;
           randomization is not between them
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTD = ROOT / "data/moat/verified/product"
NONE = {"NCT03520686", "NCT06618287", "NCT03952325", "NCT02054520", "NCT03565445", "NCT06890598", "NCT04379596",
        "NCT01042379", "NCT05116202", "NCT04061473", "NCT03083704", "NCT07312851", "NCT03310021", "NCT05723510",
        "NCT05491460", "NCT04862663", "NCT04802759", "NCT03616587", "NCT03424005", "NCT03284957", "NCT06648031",
        "NCT05080218", "NCT03766724", "NCT03565458", "NCT04189484", "NCT01764997", "NCT07532304", "NCT03916328",
        "NCT07510191", "NCT05689671", "NCT05305066", "NCT05379322", "NCT05928039"}
REGIMEN = {"NCT06364917", "NCT05926960", "NCT06561386", "NCT07740941", "NCT07572123", "NCT06999980", "NCT06364631",
           "NCT05629585", "NCT04380636", "NCT05298423", "NCT06103864", "NCT05687266", "NCT06008093", "NCT06112379",
           "NCT03273153", "NCT04619797", "NCT05224141", "NCT06646276", "NCT07374328", "NCT06757634", "NCT06221969",
           "NCT06131437", "NCT06534411", "NCT04487080", "NCT07682961"}
NOTE = {
    "NCT04487080": "MARIPOSA: amivantamab+lazertinib vs osimertinib; on the Rybrevant/Lazcluze label (PFS); OS also reported",
    "NCT03987919": "SURPASS-2: tirzepatide 5/10/15 mg vs semaglutide 1 mg, HbA1c; open-label",
    "NCT05822830": "SURMOUNT-5: tirzepatide vs semaglutide 2.4 mg, % body weight change at wk 72",
    "NCT06045221": "ACHIEVE-3: orforglipron vs oral semaglutide (Rybelsus), not injectable Ozempic/Wegovy",
    "NCT02648204": "SUSTAIN 7: semaglutide vs dulaglutide, HbA1c",
    "NCT03015220": "PIONEER 10 (Japan): oral semaglutide vs dulaglutide 0.75 mg (Japanese dose)",
    "NCT02684370": "UltIMMa-1: risankizumab vs ustekinumab vs placebo, psoriasis",
    "NCT02684357": "UltIMMa-2: risankizumab vs ustekinumab vs placebo, psoriasis",
    "NCT04524611": "SEQUENCE: risankizumab vs ustekinumab in anti-TNF-failed Crohn's; open-label, assessor-blinded",
    "NCT03478787": "IMMerge: risankizumab vs secukinumab, psoriasis",
    "NCT02694523": "IMMvent: risankizumab vs adalimumab, psoriasis",
    "NCT02629159": "SELECT-COMPARE: upadacitinib vs adalimumab vs placebo on MTX, RA (collector missed: rescue-switch arms)",
    "NCT03104400": "SELECT-PsA 1: upadacitinib vs adalimumab vs placebo, PsA",
    "NCT05814627": "SELECT-SWITCH: upadacitinib vs adalimumab after TNFi failure, RA",
    "NCT03266783": "COBRRA: apixaban vs rivaroxaban, clinically relevant bleeding in acute VTE",
    "NCT05207709": "HARMONIA: ribociclib vs palbociclib, HER2-enriched subtype",
    "NCT02607930": "GS-US-380-1489: B/F/TAF vs ABC/DTG/3TC (Triumeq), treatment-naive",
    "NCT02607956": "GS-US-380-1490: B/F/TAF vs DTG + F/TAF, treatment-naive",
    "NCT04884139": "PASO-DOBLE: switch to DTG/3TC (Dovato) vs BIC/FTC/TAF (Biktarvy)",
    "NCT04542070": "SOLAR: CAB+RPV LA (Cabenuva) vs continuing Biktarvy",
    "NCT04790513": "LIBerate-H2H: lerodalcibep vs evolocumab vs alirocumab",
    "NCT01177813": "EMPA-REG MONO: empagliflozin vs placebo with sitagliptin as active reference",
}
VERDICT = {
    "pembrolizumab vs nivolumab": "Not supported for molecule claims: no trial randomizes Keytruda against Opdivo as monotherapy (CT.gov has only regimen trials and a withdrawn study); JCOG2007 (PMID 39159638, jRCT-registered, not on CT.gov) randomized pembrolizumab+chemo vs nivolumab+ipilimumab+chemo, a regimen comparison.",
    "pembrolizumab vs durvalumab": "Not supported for molecule claims; only regimen trials (e.g., KEYLYNK-012 / KEYVIBE-006 pembrolizumab-based CRT vs CRT then durvalumab), none with posted results.",
    "pembrolizumab vs atezolizumab": "Not supported for molecule claims: IMspire170 and SKYSCRAPER-06 (results posted) randomized atezolizumab-based regimens against pembrolizumab regimens; regimen-level only.",
    "nivolumab vs atezolizumab": "Not supported: no completed randomized nivolumab-vs-atezolizumab trial.",
    "sitagliptin vs semaglutide": "Supported for semaglutide vs sitagliptin: SUSTAIN 2 and PIONEER 3/7/12 (results posted); sitagliptin comparisons appear on the Ozempic and Rybelsus labels.",
    "sitagliptin vs empagliflozin": "Weak: EMPA-REG MONO used sitagliptin only as an active reference arm; other trials are small investigator studies.",
    "apixaban vs rivaroxaban": "Not supported for efficacy: only small Phase 4 RCTs (COBRRA bleeding endpoint in VTE, RAMBLE, COVET, COBRRA pilot); the large-scale data are observational.",
    "palbociclib vs abemaciclib": "Not supported: no Phase 3 Ibrance-vs-Verzenio RCT; only small or platform studies.",
    "palbociclib vs ribociclib": "Not supported: HARMONIA (ribociclib vs palbociclib, HER2-enriched) is the only Phase 3 RCT and has no posted results.",
    "tafamidis vs acoramidis": "Not supported: no head-to-head trial (ATTRibute-CM and ATTR-ACT were placebo-controlled).",
    "tafamidis vs vutrisiran": "Not supported: no CT.gov record randomizes vutrisiran against tafamidis.",
    "tirzepatide vs semaglutide": "Supported for Mounjaro (SURPASS-2 vs semaglutide 1 mg is on the Mounjaro label); SURMOUNT-5 vs semaglutide 2.4 mg has posted results but is not on the current Zepbound label.",
    "dulaglutide vs semaglutide": "Evidence exists but is not on either current label: SUSTAIN 7 (Phase 3, results posted) randomized semaglutide vs dulaglutide; PIONEER 10 uses a Japan-only dulaglutide dose.",
    "orforglipron vs semaglutide": "Partly supported: ACHIEVE-3 compares orforglipron with oral semaglutide (Rybelsus), not the Wegovy pill dose or injectables.",
    "risankizumab vs guselkumab": "Not yet supported: CHARGE (UC/CD) is recruiting, no results.",
    "risankizumab vs ustekinumab": "Trial evidence exists (UltIMMa-1/2 psoriasis, results posted; SEQUENCE Crohn's, no posted results), but the current Skyrizi label does not present these comparisons, so a promotional comparison would rest on study data outside the label.",
    "risankizumab vs secukinumab": "Trial evidence in psoriasis (IMMerge, results posted); not presented on the current Skyrizi label.",
    "risankizumab vs vedolizumab": "Not yet supported: REVAMP is ongoing; PATHFINDER is a class-strategy trial.",
    "risankizumab vs adalimumab": "Trial evidence in psoriasis only (IMMvent, results posted); not presented on the current Skyrizi label; nothing in IBD.",
    "upadacitinib vs guselkumab": "Not supported: no head-to-head trial found.",
    "upadacitinib vs ustekinumab": "Not supported: one not-yet-recruiting trial.",
    "upadacitinib vs secukinumab": "Not supported: one not-yet-recruiting pragmatic trial; COVER is a vaccine-interruption study.",
    "upadacitinib vs vedolizumab": "Not supported: no head-to-head trial found.",
    "upadacitinib vs adalimumab": "Supported in RA within label (the Rinvoq label describes the adalimumab arm of SELECT-COMPARE); SELECT-PsA 1 results posted; SELECT-SWITCH completed, no posted results.",
    "daratumumab vs isatuximab": "Not supported: no head-to-head trial; both were tested against non-CD38 backbones.",
    "osimertinib vs amivantamab": "Supported for the combination only: MARIPOSA (Phase 3, results posted) randomized amivantamab+lazertinib vs osimertinib and is on the Rybrevant label.",
    "osimertinib vs lazertinib": "Same as above: lazertinib monotherapy was a minor MARIPOSA arm; the label claim is for the combination.",
    "dapagliflozin vs empagliflozin": "Not supported: only small investigator studies; no registrational Farxiga-vs-Jardiance RCT.",
    "evolocumab vs alirocumab": "Not supported for each other: the only randomized three-way trial (LIBerate-H2H) is a lerodalcibep study with no posted results.",
    "evolocumab vs inclisiran": "Not supported: no head-to-head trial found on CT.gov.",
    "evolocumab vs enlicitide": "Not supported: no CT.gov record pairs enlicitide (MK-0616) with evolocumab.",
    "etanercept vs risankizumab": "Not supported: no head-to-head trial found.",
    "etanercept vs upadacitinib": "Not supported: only class-level strategy studies.",
    "etanercept vs adalimumab": "Weak: two small Phase 4 RA studies; no registrational Enbrel-vs-Humira RCT.",
    "bictegravir vs dolutegravir": "Supported for a non-inferiority/tolerability framing only: GS-1489 and GS-1490 (Phase 3, results posted, described on the Biktarvy label) randomized B/F/TAF vs DTG regimens; no superiority claim.",
    "bictegravir vs cabotegravir": "Limited: SOLAR (Phase 3, results posted) randomized switching to CAB+RPV LA vs continuing Biktarvy; a switch-study framing only.",
    "lenacapavir vs cabotegravir": "Not supported for PrEP (Yeztugo vs Apretude): no head-to-head PrEP trial; the one trial is a treatment regimen study, recruiting.",
}


def main():
    pairs = json.loads((OUTD / "_h2h_pairs_raw.json").read_text())
    long, wide = [], []
    for p in pairs:
        direct, reg = [], []
        for t in p["trials"]:
            n = t["nct_id"]
            tier = "none" if n in NONE else ("regimen" if n in REGIMEN else "direct")
            long.append({"pair": p["pair"], "nct_id": n, "acronym": t["acronym"], "tier": tier, "phase": t["phase"],
                         "status": t["status"], "results_posted": t["results_posted"], "arm_a": t["arm_a"],
                         "arm_b": t["arm_b"], "primary_outcome": t["primary_outcome"], "title": t["title"],
                         "note": NOTE.get(n, ""), "source": f"https://clinicaltrials.gov/api/v2/studies/{n}",
                         "source_row": n})
            s = f"{n} ({t['acronym'] or t['title'][:40]}; {t['phase'] or 'NA'}; {t['status']}; results {t['results_posted']}): {t['primary_outcome'][:160]}"
            (direct if tier == "direct" else reg if tier == "regimen" else []).append(s)
        wide.append({"pair": p["pair"], "n_ctgov_rows_checked": p["n_ctgov_rows_checked"],
                     "n_direct_h2h": len(direct), "n_regimen_h2h": len(reg), "direct_h2h_trials": " || ".join(direct),
                     "regimen_h2h_trials": " || ".join(reg), "verdict": VERDICT.get(p["pair"], ""),
                     "source": "https://clinicaltrials.gov/api/v2/studies", "source_row": p["pair"]})
    for name, rows in (("h2h_by_pair.csv", wide), ("h2h_trials_appendix.csv", long)):
        with open(OUTD / name, "w", newline="") as f:
            w = csv.DictWriter(f, list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(len(wide), len(long), {t: sum(r["tier"] == t for r in long) for t in ("direct", "regimen", "none")})
    tiers = {(r["pair"], r["nct_id"]): r["tier"] for r in long}
    path = OUTD / "head_to_head.csv"
    rows = list(csv.DictReader(open(path)))
    cols = list(rows[0].keys()) + (["h2h_tier"] if "h2h_tier" not in rows[0] else [])
    for r in rows:
        a, b = r["drugs"].split(" vs ")
        t = tiers.get((f"{a} vs {b}", r["nct_id"])) or tiers.get((f"{b} vs {a}", r["nct_id"]))
        r["h2h_tier"] = t or ("" if r["true_head_to_head"] == "y" else "none")
        if t == "none" and r["true_head_to_head"] == "y":
            r["true_head_to_head"] = "n"
            r["verify_note"] += "; human read of record: drugs are in separate cohorts/backbones, not compared"
            if r["design"] == "head_to_head_separate_arms":
                r["verify_status"] = "fixed"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["verify_status"] for r in rows), Counter(r["true_head_to_head"] for r in rows))


main()
