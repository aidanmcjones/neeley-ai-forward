"""Costs verifier item 6: draw the 60-row sample (stratified by drug) of new_indication_benchmarks.csv, confirm each
supplement approval date against a fresh Drugs@FDA download (/tmp/cv/dafda/x), and print the rows for judgement.
Writes /tmp/cv/newind_sample.csv."""
import pandas as pd

from agent.moat.verify.pe_lib import ROOT

X = "/tmp/cv/dafda/x/"


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/new_indication_benchmarks.csv")
    sub = pd.read_csv(X + "Submissions.txt", sep="\t", encoding="latin-1", dtype=str)
    sub["k"] = sub.ApplNo.astype(int).astype(str) + ":" + sub.SubmissionNo.astype(int).astype(str)
    sub = sub[(sub.SubmissionStatus == "AP") & (sub.SubmissionType.str.strip() == "SUPPL")].drop_duplicates("k").set_index("k")
    docs = pd.read_csv(X + "ApplicationDocs.txt", sep="\t", encoding="latin-1", dtype=str, on_bad_lines="skip", quoting=3)
    docs = docs[docs.SubmissionType.str.strip() == "SUPPL"]
    docs["k"] = docs.ApplNo.astype(int).astype(str) + ":" + docs.SubmissionNo.astype(int).astype(str)
    letters = docs[docs.ApplicationDocsTypeID == "1"].groupby("k").ApplicationDocsURL.first()
    labels = docs[docs.ApplicationDocsTypeID == "2"].groupby("k").ApplicationDocsURL.first()
    k = d.appl_no.astype(str) + ":" + d.submission_no.astype(str)
    d["fda_date"] = k.map(sub.SubmissionStatusDate).str[:10]
    d["fda_class"] = k.map(sub.SubmissionClassCodeID)
    d["letter_url"] = k.map(letters)
    d["label_url"] = k.map(labels)
    d["date_ok"] = d.fda_date == d.approval_date
    d.loc[d.fda_date.isna(), "fda_date"] = "ORIG (not a supplement)"
    print("all rows date_ok", d.date_ok.value_counts(dropna=False).to_dict())
    print(d[~d.date_ok][["drug", "appl_no", "submission_no", "approval_date", "fda_date"]].to_string())
    m = d[d.nct_id.notna()]
    one = m.groupby("drug", group_keys=False).apply(lambda g: g.sample(1, random_state=7))
    rest = m.drop(one.index)
    big = rest[rest.drug.isin(m.drug.value_counts()[lambda v: v >= 10].index)]
    s = pd.concat([one, big.sample(60 - len(one), random_state=7)])
    s.to_csv("/tmp/cv/newind_sample.csv")
    d.to_csv("/tmp/cv/newind_all.csv")
    print(len(s))
    for i, r in s.iterrows():
        print(i, r.drug, r.appl_no, r.submission_no, r.approval_date, r.fda_date, r.review_priority, "|", r.nct_id,
              r.enrollment, r.sponsor, "|", r.conditions, "|", str(r.trial_title)[:150], "|", r.letter_url)


if __name__ == "__main__":
    main()
