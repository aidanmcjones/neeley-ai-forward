"""Build label_changes_key.csv: boxed warning + indication changes since 2023 for appendix drugs, read from the two
SPL versions, with a materiality call and a plain-English description."""
import csv
import difflib
import json
import re
from pathlib import Path

from agent.moat.verify.labels import NS, load, raw_text, sections

ROOT = Path(__file__).resolve().parents[3]
OUTD = ROOT / "data/moat/verified/product"
# hand-written after reading both SPL versions (sentences_added / sentences_removed)
BOXED = {
    ("eliquis", 30): ("editorial", "Boxed warning cross-reference renumbered (Dosage 2.4 -> 2.5); no change to the premature-discontinuation or spinal/epidural hematoma warnings."),
    ("ozempic", 16): ("editorial", "Thyroid C-cell tumor boxed warning: citation punctuation only ('and' -> ','); risk text unchanged."),
    ("wegovy", 9): ("editorial", "Thyroid C-cell tumor boxed warning: citation punctuation only; risk text unchanged."),
    ("rybelsus", 10): ("editorial", "Thyroid C-cell tumor boxed warning: citation punctuation only; risk text unchanged."),
    ("rybelsus", 12): ("substantive", "Boxed warning now names 'RYBELSUS and OZEMPIC tablets': the thyroid C-cell tumor warning and MTC/MEN 2 contraindication extend to a new oral Ozempic tablet presentation under this label."),
    ("rinvoq", 85): ("substantive", "Boxed warning extended to RINVOQ LQ (oral solution): every serious infection, mortality, malignancy, MACE and thrombosis statement now reads 'RINVOQ/RINVOQ LQ'."),
    ("rinvoq", 92): ("editorial", "Thrombosis paragraph reworded to say thromboses occurred in patients treated for inflammatory conditions with JAK inhibitors 'including RINVOQ'; same risk, now explicitly naming the product."),
    ("enbrel", 205): ("editorial", "Serious infection boxed warning rewritten from passive to imperative voice ('Test patients...', 'Initiate treatment...'); same TB, fungal and monitoring instructions."),
    ("biktarvy", 22): ("editorial", "Hepatitis B exacerbation boxed warning: 'coinfected with HIV-1 and HBV' reworded to 'with HIV-1 and HBV'; same monitoring instruction."),
    ("apretude", 7): ("editorial", "PrEP boxed warning: 'become infected with HIV-1' reworded to 'acquire HIV-1'; same instruction to switch to a full treatment regimen."),
    ("janumet", 61): ("substantive", "Lactic acidosis boxed warning adds 'mitochondrial diseases' to the listed risk factors for metformin-associated lactic acidosis."),
}


HAND = {  # within-sentence edits read by hand: (materiality, plain-English description)
    ("keytruda", "2023-11-07"): ("narrowing", "HER2+ gastric/GEJ first-line indication (with trastuzumab + chemo) restricted to tumors expressing PD-L1 CPS >=1."),
    ("keytruda", "2025-01-28"): ("editorial", "Moves the 'or not MSI-H' phrase within a colorectal/solid-tumor biomarker sentence; same population."),
    ("keytruda", "2026-04-06"): ("editorial", "Adds 'as determined by an FDA-authorized test' to PD-L1 biomarker statements; population unchanged."),
    ("keytruda", "2026-07-10"): ("expansion", "Muscle-invasive bladder cancer use with enfortumab vedotin-ejfv no longer limited to cisplatin-ineligible patients."),
    ("keytruda-qlex", "2026-04-06"): ("editorial", "Adds 'as determined by an FDA-authorized test' to PD-L1 biomarker statements."),
    ("keytruda-qlex", "2026-07-10"): ("expansion", "Same MIBC expansion as Keytruda: enfortumab vedotin-ejfv combination no longer limited to cisplatin-ineligible patients."),
    ("opdivo", "2025-05-23"): ("narrowing", "Gastric/GEJ/esophageal adenocarcinoma and ESCC first-line uses restricted to tumors expressing PD-L1 >=1."),
    ("opdivo-qvantig", "2024-12-27"): ("narrowing", "ESCC and gastric uses restricted to tumors expressing PD-L1 >=1 (mirrors Opdivo IV)."),
    ("imfinzi", "2025-02-28"): ("editorial", "dMMR endometrial indication now says 'as determined by an FDA-approved test'."),
    ("imfinzi", "2026-08-31"): ("editorial", "'FDA-approved' test wording changed to 'FDA-authorized'."),
    ("verzenio", "2023-03-03"): ("expansion", "Adjuvant early breast cancer use drops the Ki-67 >=20% test requirement and changes 'postmenopausal women, and men' to 'adult patients'."),
    ("mounjaro", "2025-12-19"): ("expansion", "Type 2 diabetes indication extended to pediatric patients 10 years and older."),
    ("cosentyx", "2023-10-06"): ("expansion", "Adds 'pediatric' to an existing indication (pediatric expansion within an existing use)."),
    ("entyvio", "2023-09-21"): ("editorial", "Adds abbreviations (UC), (CD)."),
    ("farxiga", "2026-06-03"): ("editorial", "Abbreviates 'cardiovascular' to 'CV'."),
    ("dovato", "2024-04-05"): ("expansion", "HIV-1 treatment indication extended to adolescents 12 years and older weighing at least 25 kg."),
}
STOP = {"and", "or", "the", "a", "an", "of", "for", "with", "in", "to", "see", "is", "are", "as", "who", "that"}


def strip_refs(t):
    t = re.sub(r"\[see [^\]]*\]", " ", t)
    t = re.sub(r"\(\s*[\d.,\s]+\)", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def titles(root):
    s = sections(root).get("1 INDICATIONS")
    if s is None:
        return []
    out = []
    for c in s.xpath(".//v3:component/v3:section", namespaces=NS):
        t = " ".join(" ".join(c.xpath("./v3:title//text()", namespaces=NS)).split())
        if t:
            out.append(t)
    return out


def best(x, pool):
    return max((difflib.SequenceMatcher(None, x, y).ratio() for y in pool), default=0.0)


def main():
    raw = json.loads((OUTD / "_label_key_raw.json").read_text())
    out = []
    for r in raw:
        cur, prev = load(r["setid"], r["version"]), load(r["setid"], r["prev_version"])
        add = [strip_refs(x) for x in r["sentences_added"].split(" || ") if x]
        rem = [strip_refs(x) for x in r["sentences_removed"].split(" || ") if x]
        if r["section"] == "BOXED WARNING":
            mat, desc = BOXED.get((r["drug"], r["version"]), ("unreviewed", "boxed warning text changed; read both versions"))
        else:
            ta, tp = titles(cur), titles(prev)
            norm = lambda t: re.sub(r"^[\d.\s]+", "", t).lower()
            new_t = [t for t in ta if norm(t) not in {norm(x) for x in tp}]
            gone_t = [t for t in tp if norm(t) not in {norm(x) for x in ta}]
            new_s = [x for x in add if best(x, rem) < 0.85 and len(x) > 25]
            gone_s = [x for x in rem if best(x, add) < 0.85 and len(x) > 25]
            parts = []
            if new_t:
                parts.append("New indication heading(s): " + "; ".join(new_t))
            if gone_t:
                parts.append("Heading(s) removed: " + "; ".join(gone_t))
            if new_s:
                parts.append("Added text: " + " | ".join(s[:260] for s in new_s[:3]))
            if gone_s:
                parts.append("Removed text: " + " | ".join(s[:200] for s in gone_s[:2]))
            # within-sentence edits: word-level diff of near-identical sentence pairs
            edits = []
            for a in add:
                if best(a, rem) < 0.85:
                    continue
                b = max(rem, key=lambda y: difflib.SequenceMatcher(None, a, y).ratio())
                wa, wb = b.split(), a.split()
                for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb).get_opcodes():
                    if tag == "equal":
                        continue
                    old_w, new_w = " ".join(wa[i1:i2]), " ".join(wb[j1:j2])
                    toks = [t for t in re.findall(r"[a-z0-9≥≤%]+", (old_w + " " + new_w).lower()) if t not in STOP]
                    if toks:
                        edits.append(f"'{old_w[:80]}' -> '{new_w[:80]}'")
            if edits:
                parts.append("Edited wording: " + "; ".join(list(dict.fromkeys(edits))[:4]))
            if new_t or gone_t or new_s or gone_s:
                mat = "substantive"
                desc = " / ".join(parts)
            elif edits:
                mat = "wording_change_check"
                desc = " / ".join(parts)
            else:
                mat = "editorial"
                desc = "Punctuation, formatting or cross-reference edit only"
        how = "hand" if r["section"] == "BOXED WARNING" else "auto sentence diff"
        if (r["drug"], r["effective_date"]) in HAND and r["section"] == "1 INDICATIONS":
            mat, desc = HAND[(r["drug"], r["effective_date"])]
            how = "hand"
        out.append({"drug": r["drug"], "section": r["section"], "effective_date": r["effective_date"],
                    "description_method": how,
                    "version": r["version"], "prev_version": r["prev_version"], "materiality": mat,
                    "description": desc, "sentences_added": r["sentences_added"][:1500],
                    "sentences_removed": r["sentences_removed"][:1500], "source": r["source"],
                    "prev_source": r["prev_source"], "source_row": f"{r['setid']}:v{r['version']}:{r['section']}",
                    "verify_status": "verified",
                    "verify_note": f"read SPL v{r['prev_version']} and v{r['version']} from DailyMed; diff of section text"})
    with open(OUTD / "label_changes_key.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(len(out), Counter((r["section"], r["materiality"]) for r in out))


main()
