"""Probe data.medicaid.gov NADAC 2026 and SDUD 2025/2026 for the 2026 launches (Lipfendra, Foundayo)."""
import json

from agent.moat.pricing_medicaid import NADAC, SDUD, query

TERMS = ["FOUNDAYO", "LIPFENDRA", "ENLICITIDE", "ORFORGLIPRON"]

if __name__ == "__main__":
    for t in TERMS:
        r = query(NADAC[2026], [("ndc_description", t + "%", "like")])
        asof = sorted({x["as_of_date"] for x in r})
        print("NADAC2026", t, len(r), asof[-3:] if asof else None)
    # latest as_of in the 2026 NADAC file overall
    r = query(NADAC[2026], [("ndc_description", "JANUVIA%", "like")])
    print("NADAC2026 latest as_of (Januvia probe)", sorted({x["as_of_date"] for x in r})[-2:])
    for y in (2025, 2026):
        for t in TERMS[:2]:
            r = query(SDUD[y], [("state", "XX", "="), ("product_name", t[:9] + "%", "like")])
            print("SDUD", y, t, len(r), sorted({(x["year"], x["quarter"]) for x in r}))
        r = query(SDUD[y], [("state", "XX", "="), ("product_name", "JANUVIA%", "like")])
        print("SDUD", y, "quarters posted (Januvia probe)", sorted({(x["year"], x["quarter"]) for x in r}))
