"""Formulary history per case-drug RXCUI from the SPUF basic-formulary files (same aggregation as gap_data.step_formulary)."""
import re
from pathlib import Path

import pandas as pd

from agent.moat.common import note_gap, write

TMP = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/rx")
URLS = {
    "2023Q4": "https://data.cms.gov/sites/default/files/2025-01/1fc9b722-db45-4925-96c0-1bde30a2ae0f/SPUF_2024_20250131_2023q4.zip",
    "2024Q4": "https://data.cms.gov/sites/default/files/2025-01/e78ce888-f571-4d86-baf0-7a1f9efffff4/SPUF_2025_20250109.zip",
    "2025Q4": "https://data.cms.gov/sites/default/files/2026-01/5942aa7e-a0c4-4e65-bd56-32608c33649f/SPUF_2026_20260107.zip",
    "2026Q3": "https://data.cms.gov/sites/default/files/2026-10/062e9434-ed9d-4e83-abbd-4d64eb375949/SPUF_2026_20261007.zip",
}
WANT = {"FORMULARY_ID", "RXCUI", "TIER_LEVEL_VALUE", "QUANTITY_LIMIT_YN", "PRIOR_AUTHORIZATION_YN", "STEP_THERAPY_YN"}


def summarize(path):
    parts = []
    for chunk in pd.read_csv(path, sep="|", dtype=str, encoding="latin-1", chunksize=2_000_000,
                             usecols=lambda c: c.upper() in WANT):
        chunk.columns = [c.upper() for c in chunk.columns]
        parts.append(chunk.drop_duplicates(["FORMULARY_ID", "RXCUI"]))
    f = pd.concat(parts).drop_duplicates(["FORMULARY_ID", "RXCUI"])
    n_form = f["FORMULARY_ID"].nunique()
    f["TIER"] = pd.to_numeric(f["TIER_LEVEL_VALUE"], errors="coerce")
    for c in ("QUANTITY_LIMIT_YN", "PRIOR_AUTHORIZATION_YN", "STEP_THERAPY_YN"):
        f[c] = f[c].eq("Y")
    g = f.groupby("RXCUI").agg(formularies=("FORMULARY_ID", "nunique"), tier_median=("TIER", "median"),
                               tier_mean=("TIER", "mean"), prior_auth_share=("PRIOR_AUTHORIZATION_YN", "mean"),
                               step_therapy_share=("STEP_THERAPY_YN", "mean"),
                               quantity_limit_share=("QUANTITY_LIMIT_YN", "mean")).reset_index()
    g["coverage_share"] = g["formularies"] / n_form
    g["total_formularies"] = n_form
    return g


def main():
    m = pd.read_csv(TMP / "rxcui_map.csv", dtype=str)
    out = []
    for q, url in URLS.items():
        p = TMP / "spuf" / f"{q}_basic_formulary.txt"
        if not p.exists():
            note_gap("rx", "ALL", f"formulary_{q}", "SPUF zip not downloaded in time")
            continue
        g = summarize(p).rename(columns={"RXCUI": "rxcui"})
        g.to_csv(TMP / f"formulary_all_{q}.csv", index=False)
        j = m.merge(g, on="rxcui", how="left")
        j["quarter"] = q
        j["covered_in_any_formulary"] = j["formularies"].notna()
        j["source"] = url
        j["source_row"] = [f"{q}:{r}" for r in j["rxcui"]]
        out.append(j)
        print(q, len(g), j["covered_in_any_formulary"].sum(), flush=True)
    df = pd.concat(out)
    df = df.rename(columns={"rx_name": "rxcui_name", "tty": "rxcui_tty", "link": "rxcui_link"})
    write("rx", "tables/formulary_history.csv", df.round(4).to_csv(index=False), group="rx", doc_type="table",
          source_url="https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers")
    print(len(df))


main()
