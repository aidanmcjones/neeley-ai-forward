"""Upload verified pricing outputs and append AI-was-wrong rows."""
import json
from pathlib import Path

from agent.moat.common import write

V = Path("data/moat/verified/pricing")
for f in ["gtn_proxy.csv", "gtn_exposure.csv", "sample_checks.csv", "company_list_vs_net.csv", "movements.md"]:
    p = V / f
    if p.exists():
        write("verify_pricing", f"verified/pricing/{f}", p.read_text(), group="pricing", doc_type="table" if f.endswith(".csv") else "memo",
              source_url="derived (verification of data/moat/tables pricing stream)")
        print("uploaded", f)

S = "pricing"
rows = [
    dict(table="gtn_proxy.csv", what_the_ai_said="Stelara NADAC is 4.27x the MFP (mean NADAC per mL / mean MFP per unit)",
         what_the_source_says="MFP per unit is $8,979.65 per mL for SC NDC-9s but $25.11 per mL for IV vial NDC-9s 57894-0054/0444; averaging them is meaningless. Same-NDC-9 NADAC/MFP = 3.32 (both NDCs 3.31-3.32). Ozempic/Wegovy/Rybelsus share one CMS selection whose per-unit MFP spans $9.23/tablet to $192.82/mL; the collector's $83.79 mean mixed all three brands",
         how_caught="NDC-9 join of CMS MFP file to NADAC NDCs, checking NCPDP unit per NDC", count=4, example_source="data/corpus/drugs/stelara/ira_negotiation.csv"),
    dict(table="gtn_proxy.csv", what_the_ai_said="nadac_brand_mean_per_unit = simple mean over brand NDCs, unit = mode",
         what_the_source_says="2025-2026 NADAC mixes EA tablets with ML pens/suspension for Ozempic, Wegovy and Xarelto (Ozempic 2026 mean $294.75 blends $33/tablet with $332/mL); per-mL means also shift with pen mix (Ozempic per mL 'fell 10%' 2020-2026 while every same NDC rose; true same-NDC +21%)",
         how_caught="per-NDC pricing_unit audit and fixed-basket same-NDC trend", count=6, example_source="https://data.medicaid.gov/dataset/fbb83258-11c7-47f5-8b18-5f8e79f7e704"),
    dict(table="gtn_proxy.csv", what_the_ai_said="Entyvio Part D spend per unit +100% 2020-2024",
         what_the_source_says="spend summed over 'Entyvio' (per vial) and 'Entyvio Pen' (per mL) rows; vial row units/claim fell 2.04 to 1.04 (CMS Outlier_Flag=1 for 2020-2022). Per claim +21.8%; WAC per vial +42%",
         how_caught="units per claim check vs Medicaid SDUD units per Rx (steady ~1.0) and CMS outlier flags", count=1,
         example_source="https://data.cms.gov/data-api/v1/dataset/7e0b4365-fd63-4a29-8f5e-e0ac9f66a81b/data?filter[Brnd_Name]=Entyvio"),
    dict(table="gtn_proxy.csv", what_the_ai_said="partb_hcpcs = first code (alphabetical) among HCPCS listed for the pack",
         what_the_source_says="Darzalex IV was given Faspro J9144; Keytruda Qlex and Opdivo Qvantig got the IV codes J9271/J9299 (years before they existed); Stelara 2026 switched to IV J3358 ($11.43/mg vs SC $155.88) looking like a 93% ASP fall; Yeztugo 2023-2024 got Sunlenca J1961; Wezlana got Stelara's own code",
         how_caught="explicit product-to-HCPCS map from CMS short descriptors", count=31, example_source="https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files"),
    dict(table="wac_increases.csv", what_the_ai_said="2020 rows: wac_increase_amount = 2020, wac_after_increase = e.g. 8.10",
         what_the_source_says="HCAI 2020 file data rows carry an extra column versus the header (year, then two numbers), so increase amount and WAC after are shifted; e.g. Entyvio 01/03/2020 row reads 2020 | 8.10 | 143.17",
         how_caught="re-read of raw q1-q4-2020 xlsx", count=78,
         example_source="https://data.chhs.ca.gov/dataset/0c693b50-6d23-46a0-a1ae-7c320fe23dff/resource/f3e4ba62-3df4-40dd-9876-f7aea7384c1b/download/q1-q4-2020-prescription-drug-wac-increases.xlsx"),
    dict(table="company_list_vs_net.csv", what_the_ai_said="BMS 2025 average discount 47% ('53 cents retained' read as discount 47)",
         what_the_source_says="'approximately 53 cents of each dollar of our company's U.S. gross sales were retained by the healthcare system'; 'Over 53% of list prices were retained' = 53% gross-to-net",
         how_caught="page re-read", count=1, example_source="data/moat/companies/BMY/pricing_report_2025.md#page 37"),
    dict(table="company_list_vs_net.csv", what_the_ai_said="Merck 2018 net 'printed 2.99 with footnote 9, read as 2.9'",
         what_the_source_says="page 1 has footnotes 1-6 only; no footnote 9 exists. Value printed 2.99; kept as printed with note",
         how_caught="page re-read", count=1, example_source="data/moat/companies/MRK/pricing_report_2023.md#page 1"),
    dict(table="company_list_vs_net.csv", what_the_ai_said="Pfizer: net -2 for 2025 only; ex-COVID 2023-2025",
         what_the_source_says="same table also states all-portfolio net 2023 +5% and 2024 (2)%; two PFE 2025 rows had no scope column to tell them apart",
         how_caught="page re-read", count=2, example_source="data/moat/companies/PFE/pricing_report_2025.md#page 54"),
]
with open("data/moat/verify/ai_wrong.jsonl", "a") as fh:
    for r in rows:
        fh.write(json.dumps({"stream": S, **r}) + "\n")
print("ai_wrong rows", len(rows))
