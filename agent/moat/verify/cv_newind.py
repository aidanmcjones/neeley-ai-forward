"""Costs verifier item 6: new_indication_benchmarks.csv. 60-row sample judged by hand (supplement approval date
re-checked against a fresh Drugs@FDA download; trial judged against what that supplement actually approved),
rules for the rest (maker-sponsor check, semaglutide/tirzepatide brand check). Writes the verified table and
new_indication_benchmarks_dropped.csv."""
import io
import re

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, log_wrong

MAKER = {
    "amjevita": "Amgen", "amvuttra": "Alnylam", "apretude": "ViiV|GlaxoSmithKline", "biktarvy": "Gilead",
    "cosentyx": "Novartis", "darzalex": "Janssen|Genmab", "darzalex-faspro": "Janssen|Genmab",
    "dovato": "ViiV|GlaxoSmithKline", "eliquis": "Bristol|Pfizer", "enbrel": "Amgen|Immunex|Wyeth|Pfizer",
    "entyvio": "Millennium|Takeda", "farxiga": "AstraZeneca|Bristol", "humira": "Abbott|AbbVie", "ibrance": "Pfizer",
    "imfinzi": "AstraZeneca|MedImmune", "janumet": "Merck", "januvia": "Merck", "jardiance": "Boehringer|Lilly",
    "keytruda": "Merck", "keytruda-qlex": "Merck", "kisqali": "Novartis", "lazcluze": "Janssen|Yuhan",
    "leqvio": "Novartis|Medicines Company", "mounjaro": "Lilly", "zepbound": "Lilly", "opdivo": "Bristol|Ono",
    "opdivo-qvantig": "Bristol|Ono", "ozempic": "Novo Nordisk", "rybelsus": "Novo Nordisk", "wegovy": "Novo Nordisk",
    "praluent": "Sanofi|Regeneron", "repatha": "Amgen", "rinvoq": "AbbVie", "skyrizi": "AbbVie", "rybrevant": "Janssen",
    "sarclisa": "Sanofi", "stelara": "Janssen|Centocor", "tagrisso": "AstraZeneca", "tecentriq": "Roche|Genentech",
    "tremfya": "Janssen", "trulicity": "Lilly", "verzenio": "Lilly", "wezlana": "Amgen", "xarelto": "Janssen|Johnson|Bayer",
}

# sample judgements: row index -> (match_confidence, note)
W = "wrong"
P = "plausible"
C = "pivotal_confirmed"
J = {
    3: (W, "JHSPH ADVISE uveitis trial of Humira; not an Amgen trial and not the basis of an Amjevita supplement"),
    6: (C, "HELIOS-B is the pivotal trial for the ATTR-CM indication approved 2025-03-20"),
    7: (W, "LATITUDE tests Cabenuva for HIV treatment; Apretude is PrEP"),
    10: (W, "investigator-initiated neuro-monitoring switch study (n=100), not pivotal"),
    28: (P, "secukinumab GCA phase 3 by Novartis; the same NCT is also matched to s91, so at most one is right"),
    42: (W, "Biocad biosimilar BCD-264 trial with Darzalex as comparator"),
    46: (W, "COLUMBA supported the 2020 original SC approval; the 2021-07-09 supplement was D-Pd (APOLLO)"),
    54: (W, "STAT is a single-arm pilot (n=131), not a pivotal trial"),
    62: (W, "Zurich MOSES stroke-biomarker trial; the 2025 Eliquis supplements were pediatric VTE"),
    77: (W, "WGET (NIAMS) found etanercept ineffective in Wegener's; no such indication"),
    84: (W, "vedolizumab aGVHD prophylaxis trial; Entyvio has no GVHD indication"),
    88: (P, "DECLARE-TIMI 58 is Farxiga's CV outcomes trial, but the HF-hospitalization indication was approved Oct 2019, not 2019-02-22"),
    95: (W, "Japanese RA study; the 2005-10-03 Humira supplement approved psoriatic arthritis (ADEPT)"),
    126: (W, "SONIA (Dutch BOOG strategy trial) was not the basis of an Ibrance supplement"),
    141: (W, "AEGEAN was approved Aug 2024; the 2022-11-10 approval was POSEIDON (Imjudo + Imfinzi, NSCLC)"),
    151: (P, "Merck sitagliptin/MK0431A comparison trial; label-data supplement, not a new indication"),
    158: (P, "same Merck trial as the Janumet row; label-data supplement"),
    166: (W, "EMPA-REG OUTCOME supported the CV indication approved 2016-12-02, not this 2015 supplement"),
    224: (W, "KEYNOTE-407 China extension (n=125); the Oct 2020 Keytruda approval was cHL (KEYNOTE-204)"),
    283: (P, "Merck RCC triplet trial; Keytruda Qlex supplement content not confirmed"),
    292: (W, "BioItaLEE molecular-features study; no indication; NATALEE approved Sept 2024"),
    295: (P, "PALOMA-3 (SC vs IV amivantamab with lazertinib) could support a Lazcluze label update; not confirmed"),
    298: (W, "LIB Therapeutics lerodalcibep trial with inclisiran comparator"),
    301: (W, "investigator trial in Bangladesh; also a weight-management (Zepbound) trial matched to Mounjaro"),
    329: (W, "Italian NIBIT-M2 melanoma brain-metastasis trial; the 2018-03-05 letter is a dosing-schedule supplement"),
    369: (W, "Ono Japan/Asia gastric trial; Qvantig supplements carried indications over from Opdivo IV"),
    370: (W, "SUSTAIN China; the 2020-01-16 Ozempic supplement was CV risk reduction (SUSTAIN-6)"),
    377: (W, "ODYSSEY EAST (Asia); not the basis of a US indication"),
    386: (W, "ORIG-2 application, not a supplement; HUYGENS imaging study"),
    397: (P, "LEVEL UP (upadacitinib vs dupilumab, AbbVie) could support a label-data update; not a new indication"),
    400: (W, "Qilu semaglutide injection biosimilar trial matched to oral Rybelsus"),
    405: (W, "the 2024-09-19 Rybrevant approval was MARIPOSA-2; PALOMA-3 is the SC formulation trial"),
    407: (W, "ICARIA-MM supported the 2020 original approval; the 2021-03-31 supplement was IKEMA (Sarclisa + Kd)"),
    419: (P, "AbbVie pediatric psoriasis trial; a pediatric supplement is plausible, not confirmed"),
    432: (W, "ICONIC-ADVANCE tests icotrokinra with ustekinumab as comparator"),
    436: (W, "Shandong investigator trial; Tagrisso adjuvant (ADAURA) was Dec 2020"),
    445: (W, "IMpower133 was approved 2019-03-18, not 2018-06-14"),
    476: (C, "DISCOVER-2 is pivotal for the psoriatic arthritis indication approved 2020-07-13"),
    485: (W, "Sanofi LixiLan-G trial of iGlarLixi vs GLP-1 RA; not a Trulicity trial"),
    492: (C, "monarchE is pivotal for adjuvant early breast cancer, approved 2021-10-12"),
    501: (W, "FLOW is the Ozempic CKD trial (approved Jan 2025); the 2024-03-08 Wegovy approval was SELECT"),
    506: (W, "Lilly mirikizumab extension study matched to an Amgen ustekinumab biosimilar"),
    515: (W, "AP-HP portal-vein thrombosis investigator trial"),
    519: (W, "investigator trial in Bangladesh, n=440"),
    454: (W, "the 2020-05-18 Tecentriq approval was IMpower110 (1L NSCLC); IMpassion130 is breast"),
    347: (W, "CheckMate 9X8 (phase 2/3 CRC); the 2021-04-16 Opdivo approval was CheckMate 649 (gastric)"),
    120: (W, "PALOMA-2 supported the 2017 full approval, not this 2018 supplement"),
    129: (W, "PATHWAY (National Cancer Center Japan) investigator trial"),
    510: (W, "ATLAS ACS 2 TIMI 51: the US ACS indication was never approved (CRLs)"),
    252: (W, "KEYNOTE-775 was approved July 2021, not 2023-10-12"),
    219: (W, "Henan investigator anlotinib trial; the 2020-06-16 approval was TMB-H (KEYNOTE-158)"),
    73: (W, "WGET; no Wegener's indication"),
    340: (W, "CheckMate 577 was approved 2021-05-20; the 2020-05-15 approval was CheckMate 227 (Opdivo + Yervoy NSCLC)"),
    115: (W, "VARSITY is a Takeda vedolizumab trial with Humira as comparator"),
    412: (W, "MOTIVATE supported Crohn's approval in June 2022, not 2021-04-26"),
    513: (W, "CASSINI was not the basis of the 2018-10-11 supplement (COMPASS, CAD/PAD)"),
    270: (W, "KEYNOTE-937 adjuvant HCC has no US approval"),
    456: (W, "the 2020-07-30 Tecentriq approval was IMspire150 (melanoma); IMpassion130 is breast"),
    71: (W, "WGET; no Wegener's indication"),
    195: (W, "KEYNOTE-181 China extension; the 2019-02-15 approval was adjuvant melanoma (KEYNOTE-054)"),
}


def brand_wrong(r):
    t = f"{r.conditions} {r.trial_title}".lower()
    obes = re.search(r"obes|overweight|weight management|weight loss", t)
    t2d = re.search(r"type 2|diabet", t)
    if r.drug in ("wegovy", "zepbound") and t2d and not obes:
        return "T2D trial matched to the obesity brand"
    if r.drug in ("ozempic", "mounjaro") and obes and not t2d:
        return "obesity trial matched to the T2D brand"
    if r.drug == "ozempic" and "cagrisema" in t:
        return "CagriSema trial, not Ozempic"
    if r.drug == "rybelsus" and re.search(r"injection|ingection|once-weekly|subcutaneous", t):
        return "injectable semaglutide trial matched to oral Rybelsus"
    if r.drug == "wegovy" and "kidney" in t:
        return "FLOW (Ozempic CKD) matched to Wegovy"
    return None


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/new_indication_benchmarks.csv")
    a = pd.read_csv("/tmp/cv/newind_all.csv", index_col=0)
    d["drugsatfda_date"] = a.fda_date
    d["approval_date_ok"] = a.date_ok
    d["approval_letter_url"] = a.letter_url
    mc, st, nt, drop = [], [], [], []
    for i, r in d.iterrows():
        notes = []
        if not r.approval_date_ok:
            notes.append(f"Drugs@FDA SUPPL {r.submission_no} date is {r.drugsatfda_date}; the row's date belongs to an ORIG submission with the same number")
        if pd.isna(r.nct_id):
            m, n = "no_match", "no trial matched by the collector"
        elif i in J:
            m, n = J[i]
            n = "sampled, judged by hand: " + n
        else:
            spons = str(r.sponsor)
            if not re.search(MAKER[r.drug], spons, re.I):
                m, n = W, f"sponsor '{spons}' is not the maker or its partner; investigator, competitor or biosimilar trial"
            else:
                m, n = P, "maker-sponsored phase 3 in the window; not hand-checked (sampled precision of maker-sponsored matches was low, see NOTES.md)"
        bw = brand_wrong(r) if pd.notna(r.nct_id) else None
        if bw and r.drug in ("wegovy", "zepbound", "ozempic", "mounjaro", "rybelsus"):
            m, n = W, bw + ("; " + n if i in J else "")
            drop.append(i)
        notes.insert(0, n)
        mc.append(m)
        st.append("verified" if m == C else "corrected" if m == W else "unverified")
        nt.append("; ".join(notes))
    d["match_confidence"] = mc
    d["verify_status"] = st
    d["verify_note"] = nt
    s = d.loc[list(J)]
    rate = (s.match_confidence == W).mean()
    sp = s[[bool(re.search(MAKER[x.drug], str(x.sponsor), re.I)) for _, x in s.iterrows()]]
    print("sample", len(s), s.match_confidence.value_counts().to_dict(), "wrong rate", round(rate, 3))
    print("maker-sponsored in sample", len(sp), sp.match_confidence.value_counts().to_dict())
    print("all", d.match_confidence.value_counts().to_dict(), "dropped", len(drop))
    print("date ok", d.approval_date_ok.value_counts().to_dict())
    dropped = d.loc[drop]
    kept = d.drop(drop)
    for name, df in (("new_indication_benchmarks.csv", kept), ("new_indication_benchmarks_dropped.csv", dropped)):
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        write("verify_costs", f"verified/costs/{name}", buf.getvalue(), group="costs", doc_type="table",
              source_url="Drugs@FDA (fresh download 2026-10-17) + ClinicalTrials.gov", quality="verified")
    log_wrong([{"stream": "costs", "table": "new_indication_benchmarks.csv", "row_key": "heuristic NCT match (60-row sample)",
                "what_the_ai_said": "nearest Phase 3 (>=100 enrolled) completing 0-900 days before approval = the supplement's trial",
                "what_the_source_says": f"{(s.match_confidence == W).sum()} of 60 sampled matches are wrong (investigator, competitor or biosimilar trials, "
                                        "trials for a different indication approved in another year, or another brand's trial); 3 are the pivotal trial",
                "error_type": "heuristic_join", "severity": "high", "how_caught": "hand review vs Drugs@FDA approvals and known pivotal trials",
                "count": int((s.match_confidence == W).sum()), "example_source": "row amjevita 761024:19 -> NCT03828019 (JHSPH uveitis trial of Humira)"},
               {"stream": "costs", "table": "new_indication_benchmarks.csv", "row_key": "semaglutide/tirzepatide brand",
                "what_the_ai_said": "generic-name trial search per brand",
                "what_the_source_says": f"{len(drop)} rows matched another brand's trial (e.g. FLOW CKD trial on Wegovy, Qilu injection on Rybelsus)",
                "error_type": "brand_crossover", "severity": "medium", "how_caught": "conditions/title vs brand indication", "count": len(drop),
                "example_source": "wegovy 215256:11 -> NCT03819153"}])


if __name__ == "__main__":
    main()
