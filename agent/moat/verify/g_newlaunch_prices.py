"""NADAC and SDUD rows for the 2026 launches, pulled live from data.medicaid.gov (verified at source).

Writes data/moat/verified/pricing/new_launch_prices.csv in the nadac_history.csv layout + verify_status/verify_note,
and records gaps (common.note_gap) for any drug with no NADAC or SDUD row.
"""
import csv
from pathlib import Path

from agent.moat.common import note_gap
from agent.moat.pricing_medicaid import NADAC, SDUD, query

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/moat/verified/pricing/new_launch_prices.csv"
COLS = ["drug", "match_kind", "match_term", "year_dataset", "ndc_description", "ndc", "nadac_per_unit",
        "effective_date", "pricing_unit", "pharmacy_type_indicator", "explanation_code",
        "classification_for_rate_setting", "corresponding_generic_drug_nadac_per_unit", "as_of_date", "source",
        "source_row", "verify_status", "verify_note"]
LAUNCHES = {"lipfendra": ("MRK", "LIPFENDRA", "ENLICITIDE"), "foundayo": ("LLY", "FOUNDAYO", "ORFORGLIPRON")}
AS_OF = "2026-10-17"


def main():
    rows = []
    for slug, (tic, brand, ing) in LAUNCHES.items():
        ds = NADAC[2026]
        got = []
        for kind, term in (("brand", brand), ("generic_ingredient", ing)):
            for r in query(ds, [("ndc_description", term + "%", "like")]):
                got.append(dict(drug=slug, match_kind=kind, match_term=term, year_dataset=2026,
                                **{k: r[k] for k in COLS[4:14]}, source=f"https://data.medicaid.gov/dataset/{ds}",
                                source_row=f"ndc={r['ndc']}|effective_date={r['effective_date']}|as_of={r['as_of_date']}|ds=2026",
                                verify_status="verified_at_source",
                                verify_note=f"row returned by data.medicaid.gov datastore query on {AS_OF} "
                                            f"(ndc_description LIKE '{term}%')"))
        sd = []
        for y in (2025, 2026):
            sd += query(SDUD[y], [("state", "XX", "="), ("product_name", brand[:9] + "%", "like")])
        qs = sorted({(x["year"], x["quarter"]) for x in query(SDUD[2026], [("state", "XX", "="),
                                                                            ("product_name", "JANUVIA%", "like")])})
        posted = ", ".join(f"{y}Q{q}" for y, q in qs)
        if not got:
            note_gap("pricing", tic, slug, f"no NADAC or SDUD row as of {AS_OF} (NADAC 2026 file through latest "
                                           f"as_of; SDUD 2026 quarters posted: {posted})")
        if not sd:
            note_gap("pricing", tic, slug, f"no SDUD national (XX) row as of {AS_OF}; SDUD 2026 quarters posted: "
                                           f"{posted} (first quarter after launch not yet released)")
        rows += got
        print(slug, "nadac", len(got), "sdud", len(sd), "sdud posted", posted)
    seen, uniq = set(), []
    for r in rows:
        k = (r["drug"], r["ndc"], r["effective_date"], r["as_of_date"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    uniq.sort(key=lambda r: (r["drug"], r["as_of_date"], r["ndc"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(uniq)
    print(OUT, len(uniq))


if __name__ == "__main__":
    main()
