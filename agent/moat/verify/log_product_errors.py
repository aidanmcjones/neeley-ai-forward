"""Append product-stream AI errors found by the verifier to data/moat/verify/ai_wrong.jsonl."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E = [
    ("head_to_head.csv",
     "388 ClinicalTrials.gov rows flagged head_to_head_separate_arms (the two drugs randomized against each other)",
     "Only 166 are randomized trials that compare the two drugs in separate arms; 87 are observational cohorts, 86 non-randomized, 12 sequential non-randomized, and 37 are randomized studies where a human read showed the drugs sit in different cohorts/backbones of platform, dose-escalation or PK studies and are never compared",
     "Re-read every full CT.gov v2 record: studyType, designInfo.allocation, interventionModel, and per-arm intervention lists; hand-read every appendix-pair trial", 222,
     "NCT03952325 (CONTESSA TRIO: tesetaxel + nivolumab / pembrolizumab / atezolizumab in parallel non-comparative cohorts)"),
    ("head_to_head.csv",
     "Landmark active-comparator RCTs labeled combination_same_arm or mentioned_not_compared (e.g., SELECT-COMPARE upadacitinib vs adalimumab, PIONEER 12 oral semaglutide vs sitagliptin, UltIMMa-1 risankizumab vs ustekinumab)",
     "These randomize the two drugs against each other; the collector counted 'Placebo for adalimumab' double-dummy interventions and rescue-switch drugs as the drug, and matched only generic names (missed brand/code names such as BI 655066, LY3298176)",
     "Excluded placebo interventions, matched brand/code synonyms, used arm labels when the other drug appears only as rescue; compared against known registrational trials", 63,
     "https://clinicaltrials.gov/api/v2/studies/NCT02629159"),
    ("label_changes.csv",
     "effective_date for each label version",
     "The column holds the DailyMed published date; the SPL document's own effectiveTime is 1 to 750 days earlier (median 8 days)",
     "Compared each cited SPL XML <effectiveTime> with the row date", 1587,
     "keytruda v15: table says 2016-08-08, SPL effectiveTime 20160805"),
    ("label_changes.csv",
     "Label section 'modified' in a new version (e.g., boxed warning changes for Amjevita 2023-07, Xarelto 2026-04)",
     "Section text is identical to the prior version once whitespace, punctuation and renderer markup are removed (201 rows), or the excerpts contain only headings such as 'SPL UNCLASSIFIED SECTION', a code display name that is not label text (6 rows)",
     "Rebuilt section text from raw SPL XML for both versions and compared; checked every excerpt verbatim against the cited version", 207,
     "xarelto v64 BOXED WARNING: old_excerpt '### SPL UNCLASSIFIED SECTION ### SPL UNCLASSIFIED SECTION', new_excerpt empty"),
    ("label_changes.csv (since 2023, appendix drugs, boxed warnings)",
     "Boxed warning changes since 2023 implied as safety news",
     "8 of 11 surviving boxed warning changes are editorial (cross-reference renumbering, 'and' to ',', passive to imperative voice); only Rinvoq LQ added to the box (2024-04), 'Ozempic tablets' added to the Rybelsus box (2026-01) and 'mitochondrial diseases' added to Janumet's lactic acidosis risk factors (2026-08) change content",
     "Read the sentence diff of both SPL versions for every boxed warning row", 8,
     "eliquis v30 (2025-04): only '(2.4' -> '(2.5' in the cross-reference"),
    ("indication_timeline.csv",
     "n_indications per label version",
     "The number is a count of 1.x subsections (one subsection can hold several tumor types or lines of therapy), and for 545 versions with no titled subsections it is a paragraph-count heuristic; it is not a count of FDA-approved indications",
     "Recounted titled 1.x subsections in each SPL XML and checked how the collector derived the number", 545,
     "data/moat/verified/product/indication_timeline.csv n_indications_note"),
    ("recalls.csv",
     "Recall attributed to the brand (e.g., drug=januvia, opdivo, farxiga, jardiance, ozempic, stelara, dovato)",
     "The recalled product is a different product sharing the ingredient: Janumet, Opdualag, Xigduo XR, Synjardy XR, Glyxambi, Rybelsus, Triumeq, and IMULDOSA (a ustekinumab biosimilar from another firm, not Stelara)",
     "Re-fetched each recall_number from openFDA enforcement and read product_description", 10,
     "D-0653-2026 (IMULDOSA, listed under stelara)"),
    ("head_to_head.csv (coverage)",
     "Head-to-head evidence for appendix pairs taken from ClinicalTrials.gov only",
     "JCOG2007 (PMID 39159638), a randomized phase 3 of pembrolizumab+chemo vs nivolumab+ipilimumab+chemo, is registered in jRCT and absent from CT.gov; the enlicitide (Lipfendra) pairs returned zero CT.gov rows under the generic name",
     "Cross-checked PubMed RCT titles against the CT.gov list; re-queried CT.gov with code names (MK-0616, LY3502970, AG10, ALN-TTRSC02)", 2,
     "https://pubmed.ncbi.nlm.nih.gov/39159638/"),
    ("h2h verifier (self-check)",
     "Verifier's own first guess: PMID 39159638 is an observational comparison",
     "PubMed publication types say Randomized Controlled Trial, Phase III (JCOG2007)",
     "Checked pubtypes before writing the override", 1,
     "https://pubmed.ncbi.nlm.nih.gov/39159638/"),
]


def main():
    p = ROOT / "data/moat/verify/ai_wrong.jsonl"
    with p.open("a") as f:
        for t, said, src, how, n, ex in E:
            f.write(json.dumps({"stream": "product", "table": t, "what_the_ai_said": said, "what_the_source_says": src,
                                "how_caught": how, "count": n, "example_source": ex}) + "\n")
    print("appended", len(E))


main()
