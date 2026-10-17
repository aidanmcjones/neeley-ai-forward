"""Completeness check for data/corpus: merge every source log into one manifest and list what is missing.

Reads data/corpus/manifest.jsonl (SEC filings, drug packs) plus every <group>/<TICKER>/sources.jsonl (IR documents
saved by agent.ir_fetch), drops rows whose file no longer exists, and writes:
  data/corpus/manifest.csv   one row per document, the index Aidan and the tools read
  data/corpus/GAPS.md        expected documents we do not have, per company and per drug, plus worker notes

Usage:  python -m agent.corpus_check
"""

import json
from pathlib import Path

import pandas as pd

from agent.corpus import COMPANIES
from agent.drug_pack import DRUGS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "corpus"
QUARTERS = ["2025Q3", "2025Q4", "2026Q1", "2026Q2"]


def load_rows():
    rows = []
    for p in [OUT / "manifest.jsonl", *OUT.glob("*/*/sources.jsonl")]:
        rows += [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    df = pd.DataFrame(rows)
    df = df[df["path"].map(lambda p: (ROOT / p).exists())]
    return df.drop_duplicates("path", keep="last").sort_values(["group", "ticker", "doc_type", "path"])


def gaps(df):
    lines = ["# Corpus gaps", "", "Expected documents that are not in data/corpus. Regenerate with "
             "`python -m agent.corpus_check`.", ""]
    for t, group in COMPANIES.items():
        d = df[df["ticker"] == t]
        types = d["doc_type"].value_counts().to_dict()
        miss = []
        need_annual = 2 if group == "companies" else 1
        if types.get("annual_report", 0) < need_annual:
            miss.append(f"annual reports: {types.get('annual_report', 0)} of {need_annual}")
        if group == "companies":
            tq = set(d.loc[d["doc_type"] == "transcript", "period"].dropna())
            miss += [f"transcript {q}" for q in QUARTERS if not any(q in str(x) for x in tq)]
            if not types.get("earnings_slides"):
                miss.append("earnings slides: none")
            if not (types.get("quarterly_report") or types.get("foreign_current_report") or types.get("interim_report")):
                miss.append("quarterly report (10-Q / 6-K / interim): none")
        elif not types.get("transcript"):
            miss.append("latest earnings transcript")
        lines.append(f"## {t} ({group})")
        lines += [f"- {m}" for m in miss] or ["- complete against the checklist"]
        note = OUT / group / t / "GAPS.txt"
        if note.exists():
            lines += ["- worker notes:"] + [f"  - {x}" for x in note.read_text(encoding="utf-8").splitlines() if x.strip()]
        lines.append("")
    for extra in sorted({p.parent.name for p in OUT.glob("peers/*/sources.jsonl")} - set(COMPANIES)):
        lines += [f"## {extra} (peers, non-SEC)", f"- {len(df[df['ticker'] == extra])} documents", ""]
    lines.append("## Drugs")
    for slug in DRUGS:
        if not (OUT / "drugs" / slug / "label_sections.md").exists():
            lines.append(f"- {slug}: no FDA label")
    lines += ["- label PDFs: DailyMed redirects scripted PDF downloads; labels are cited by section number from "
              "label_sections.md, which links the DailyMed setid.", ""]
    return "\n".join(lines) + "\n"


def main():
    df = load_rows()
    cols = ["doc_id", "ticker", "group", "doc_type", "form", "period", "filed", "source_quality", "pages",
            "pages_with_folio", "chars", "path", "source_url", "retrieved_at", "sha256"]
    df[cols].to_csv(OUT / "manifest.csv", index=False)
    (OUT / "GAPS.md").write_text(gaps(df), encoding="utf-8")
    print(df.groupby(["group", "doc_type"]).size().to_string())
    print(f"\n{len(df)} documents; manifest.csv and GAPS.md written")


if __name__ == "__main__":
    main()
