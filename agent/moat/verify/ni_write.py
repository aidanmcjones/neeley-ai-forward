"""New-indication rebuild, step 4: write new_indication_benchmarks.csv (rebuilt), keep the collector file as
new_indication_benchmarks_collector.csv, write new_indication_timing_summary.csv, and log the collector's measured
matching failure rate to data/moat/verify/ai_wrong.jsonl."""
import io
import re
from datetime import date
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.ni_build import ct_fields, ct_get, months, pdate
from agent.moat.verify.pe_lib import log_wrong

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "data/moat/verified/costs"
TA = {
    "oncology": "keytruda keytruda-qlex opdivo opdivo-qvantig tecentriq imfinzi ibrance darzalex darzalex-faspro tagrisso "
                "verzenio kisqali rybrevant lazcluze sarclisa",
    "immunology": "humira amjevita wezlana enbrel cosentyx skyrizi rinvoq stelara tremfya entyvio",
    "cardiometabolic": "xarelto eliquis jardiance farxiga januvia janumet praluent repatha leqvio trulicity wegovy ozempic "
                       "rybelsus zepbound mounjaro",
    "infectious_disease": "biktarvy dovato apretude cabenuva",
    "rare_disease": "amvuttra",
}
TA = {d: a for a, ds in TA.items() for d in ds.split()}
ORIG = {("entyvio", 761359, 1, "2024-04-18"), ("repatha", 125522, 2, "2021-02-26"), ("keytruda-qlex", 761467, 2, "2025-09-19")}
COLS = ["drug", "ticker", "therapeutic_area", "appl_no", "supplement_number", "approval_date", "indication_added",
        "label_section", "pivotal_nct", "pivotal_trial_name", "enrollment", "start_date", "primary_completion_date",
        "months_start_to_completion", "months_completion_to_approval", "match_method", "match_confidence",
        "supplement_type", "source", "source_row", "verify_status", "verify_note", "approval_letter_url",
        "letter_provides_for", "ctgov_url", "label_version", "prior_label_version", "collector_nct"]


NON_HAND = "hand check: pediatric extension or dosing/route change of an existing indication; no new indication"
OVR = {  # (drug, supplement) -> hand corrections after reading the letter and the label diff
    ("opdivo", 63): {"pivotal_nct": "NCT02060188", "pivotal_trial_name": "CHECKMATE-142", "match_confidence": "plausible",
                     "hand": "hand check: nivolumab+ipilimumab MSI-H CRC approval rested on CheckMate-142; diff picked CheckMate-032"},
    ("xarelto", 25): {"pivotal_nct": "NCT01776424", "pivotal_trial_name": "COMPASS",
                      "hand": "label prints NCT10776424 (typo); COMPASS is NCT01776424"},
    ("cosentyx", 43): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("trulicity", 36): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("trulicity", 51): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("leqvio", 17): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("leqvio", 18): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("stelara", 21): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("tremfya", 26): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("jardiance", 42): {"supplement_type": "non_indication", "hand": NON_HAND},
    ("repatha", 2): {"match_confidence": "plausible", "hand": "hand check: trial identity not confirmed against the letter"},
    ("zepbound", 6): {"match_confidence": "plausible", "hand": "hand check: trial identity not confirmed against the letter"},
}


def s(x):
    return "" if pd.isna(x) else str(x)


def main():
    a = pd.read_csv("/tmp/ni/assembled.csv")
    out = []
    for r in a.to_dict("records"):
        key = (r["drug"], int(r["appl_no"]), int(r["supplement_number"]))
        o = OVR.get((r["drug"], key[2]), {})
        if o:
            r.update({k: v for k, v in o.items() if k != "hand"})
            r["trial_note"] = "; ".join(x for x in [s(r.get("trial_note")), o["hand"]] if x)
            if "pivotal_nct" in o:
                d = ct_get(o["pivotal_nct"])
                f = ct_fields(d) if d else {}
                st, pc = pdate(f.get("start_date")), pdate(f.get("primary_completion_date"))
                A = date.fromisoformat(r["approval_date"])
                r.update(enrollment=f.get("enrollment"), start_date=f.get("start_date"),
                         primary_completion_date=f.get("primary_completion_date"),
                         months_start_to_completion=months(st, pc) if st and pc and pc <= A else None,
                         months_completion_to_approval=months(pc, A) if pc and pc <= A else None)
        if re.fullmatch(r"(Study|Trial) \d+", s(r.get("pivotal_trial_name"))) and s(r.get("pivotal_nct")):
            d = ct_get(r["pivotal_nct"])
            acr = (ct_fields(d).get("acronym") if d else "") or ""
            if acr:
                r["pivotal_trial_name"] = f"{acr} (label: {r['pivotal_trial_name']})"
        v = "" if pd.isna(r.get("version")) else int(r["version"])
        if not pd.isna(r.get("s14_version")) and s(r.get("s14_section")):
            v = int(r["s14_version"])
        pv = "" if pd.isna(r.get("prev_version")) else int(r["prev_version"])
        sec = s(r.get("s14_section"))
        src = (f"https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid={r['setid']}&type=zip&version={v}" if v != ""
               else s(r["letter"]))
        srow = f"{r['setid']}:v{v}:{sec} {s(r.get('s14_heading'))}".strip() if sec else (
            f"{r['setid']}:v{v}:1 INDICATIONS {s(r['label_section'])}".strip() if v != "" else f"{key[1]}:{key[2]}")
        typ, conf = r["supplement_type"], r["match_confidence"]
        notes = [s(r["type_reason"])]
        if s(r.get("trial_note")):
            notes.append(s(r["trial_note"]))
        if s(r.get("months_note")):
            notes.append(s(r["months_note"]))
        if key + (r["approval_date"],) in ORIG:
            status = "dropped"
            notes.insert(0, "ORIG submission, not an efficacy supplement")
        elif typ == "non_indication":
            status = "verified" if s(r["provides"]) else "unchecked"
        elif conf == "pivotal_confirmed":
            status = "verified"
            notes.append(f"trial first named in section 14 at label v{v}; approval letter text matches its section 14 "
                         "context; CT.gov sponsor matches maker")
        else:
            status = "unchecked"
        if typ == "non_indication":
            months_ok = False
        else:
            months_ok = True
        out.append({
            "drug": r["drug"], "ticker": s(r["ticker"]), "therapeutic_area": TA.get(r["drug"], ""),
            "appl_no": key[1], "supplement_number": key[2], "approval_date": r["approval_date"],
            "indication_added": s(r["indication_added"]) if typ != "non_indication" else "",
            "label_section": s(r["label_section"]) if typ != "non_indication" else "",
            "pivotal_nct": s(r.get("pivotal_nct")), "pivotal_trial_name": s(r.get("pivotal_trial_name")),
            "enrollment": "" if pd.isna(r.get("enrollment")) else int(r["enrollment"]),
            "start_date": s(r.get("start_date")), "primary_completion_date": s(r.get("primary_completion_date")),
            "months_start_to_completion": r.get("months_start_to_completion") if months_ok else None,
            "months_completion_to_approval": r.get("months_completion_to_approval") if months_ok else None,
            "match_method": r["match_method"], "match_confidence": conf, "supplement_type": typ,
            "source": src, "source_row": srow, "verify_status": status, "verify_note": "; ".join(n for n in notes if n),
            "approval_letter_url": s(r["letter"]), "letter_provides_for": s(r["provides"])[:400],
            "ctgov_url": f"https://clinicaltrials.gov/study/{r['pivotal_nct']}" if s(r.get("pivotal_nct")) else "",
            "label_version": v, "prior_label_version": pv, "collector_nct": s(r["old_nct"]),
        })
    df = pd.DataFrame(out, columns=COLS).sort_values(["drug", "approval_date", "supplement_number"])
    # keep collector file
    old = (C / "new_indication_benchmarks.csv").read_bytes()
    if not (C / "new_indication_benchmarks_collector.csv").exists():
        write(stream="verify_costs", rel="verified/costs/new_indication_benchmarks_collector.csv", data=old,
              group="costs", doc_type="benchmark_table", source_url="collector heuristic (superseded)")
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    write(stream="verify_costs", rel="verified/costs/new_indication_benchmarks.csv", data=buf.getvalue(),
          group="costs", doc_type="benchmark_table",
          source_url="DailyMed SPL version history + FDA approval letters + ClinicalTrials.gov v2")
    # summary
    ok = df[(df.match_confidence == "pivotal_confirmed") & (df.supplement_type != "non_indication") &
            (df.verify_status == "verified")]
    # one trial-approval event counts once (two supplements in one letter; Keytruda and Keytruda Qlex share trials)
    ok = ok.drop_duplicates(["pivotal_nct", "approval_date"])
    rows = []
    for grp, sub in [("overall", ok)] + [(f"ta:{k}", g) for k, g in ok.groupby("therapeutic_area")] + \
            [(f"type:{k}", g) for k, g in ok.groupby("supplement_type")]:
        for m in ["months_start_to_completion", "months_completion_to_approval"]:
            x = pd.to_numeric(sub[m], errors="coerce").dropna()
            rows.append({"group": grp, "metric": m, "n": len(x),
                         "median": round(x.median(), 1) if len(x) else None,
                         "p25": round(x.quantile(.25), 1) if len(x) else None,
                         "p75": round(x.quantile(.75), 1) if len(x) else None,
                         "n_drugs": sub.drug.nunique(),
                         "source": "data/moat/verified/costs/new_indication_benchmarks.csv",
                         "source_row": "match_confidence=pivotal_confirmed, supplement_type!=non_indication, "
                                       "deduped on (pivotal_nct, approval_date); interim-analysis rows have no months"})
    sm = pd.DataFrame(rows)
    buf = io.StringIO()
    sm.to_csv(buf, index=False)
    write(stream="verify_costs", rel="verified/costs/new_indication_timing_summary.csv", data=buf.getvalue(),
          group="costs", doc_type="benchmark_summary", source_url="derived from new_indication_benchmarks.csv")
    # collector failure rate over all rows
    old = pd.read_csv(C / "new_indication_benchmarks_collector.csv")
    olddrop = pd.read_csv(C / "new_indication_benchmarks_dropped.csv")
    n_all = len(df)
    non = df[df.supplement_type == "non_indication"]
    non_wrong = int((non.collector_nct != "").sum())
    conf = df[(df.match_confidence == "pivotal_confirmed") & (df.supplement_type != "non_indication")]
    conf_right = int((conf.collector_nct == conf.pivotal_nct).sum())
    pl = df[df.match_confidence == "plausible"]
    pl_right = int((pl.collector_nct == pl.pivotal_nct).sum())
    judged = len(non) + len(conf)
    wrong = non_wrong + (len(conf) - conf_right)
    entry = {"stream": "costs", "table": "new_indication_benchmarks.csv", "row_key": "all supplement rows",
             "what_the_ai_wrote": "pivotal trial = nearest maker-agnostic Phase 3 (n>=100) completing 0-900 days "
                                  "before each efficacy-supplement approval",
             "what_the_source_says": (f"label section 14 version diff + approval letters: {len(non)} of {n_all} rows are "
                                      f"non-indication supplements (dosing, formulation, safety, pediatric extension, "
                                      f"conversion) that have no pivotal trial, yet the collector gave {non_wrong} of them "
                                      f"a trial; of {len(conf)} rows with a label-confirmed pivotal trial the collector "
                                      f"matched {conf_right}; of {len(pl)} plausible rows it agreed on {pl_right}. "
                                      f"Measured failure on judged rows {wrong}/{judged} = {wrong / judged:.0%}"),
             "error_type": "wrong_entity_match", "severity": "high",
             "how_caught": "DailyMed SPL version diff of section 14 (new NCTs at the label version implementing each "
                           "supplement) cross-checked with FDA approval-letter 'provides for' text and CT.gov sponsor",
             "count": wrong, "example_cite": "keytruda s40 2019-02-15: collector NCT03933449, label KEYNOTE-054 NCT02362594"}
    aiw = ROOT / "data/moat/verify/ai_wrong.jsonl"
    if "DailyMed SPL version diff of section 14" in aiw.read_text():
        lines = [x for x in aiw.read_text().splitlines() if "DailyMed SPL version diff of section 14" not in x]
        aiw.write_text("\n".join(lines) + "\n")
    log_wrong([entry])
    print(df.supplement_type.value_counts(), df.match_confidence.value_counts(),
          pd.crosstab(df.supplement_type, df.match_confidence), sep="\n")
    print(sm.to_string())
    print(entry["what_the_source_says"])
    print(len(old), len(olddrop))


if __name__ == "__main__":
    main()
