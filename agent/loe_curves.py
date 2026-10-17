"""Loss-of-exclusivity (LOE) sales-decline benchmark curves from real product revenue.

Source revenue: R2 xbrl_product/<cik>/<accession>.jsonl.gz (XBRL product-axis facts, fiscal 2017-2025).
LOE year: fiscal year in which US generics/biosimilars entered, each backed by a quote from a 10-K
(R2 tenk/ text, or sec.gov for two FY2018 filings that predate our 10-K text window).

Method: year 0 = LOE year. pct_of_peak(t) = sales(LOE+t) / max(sales in the 3 fiscal years before LOE that are
in our data). US sales when the filing reports a country:US row, else total (flagged in `geography`).
Curve = median (and min/max) across drugs of each modality, t = 0..4, with n per t.

Usage:  python -m agent.loe_curves            (rebuild, write local cache + R2 derived/)
        from agent.loe_curves import revenue_at_risk
"""

import collections
import csv
import gzip
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path

from agent.tenk import Store

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "agent" / "cache" / "loe_curves.json"
CSV_CACHE = ROOT / "agent" / "cache" / "loe_curves.csv"
R2_JSON, R2_CSV = "derived/loe_curves.json", "derived/loe_curves.csv"

# brand, company, cik, product-member key (lowercase substring of the XBRL member), modality, LOE year,
# accession of the 10-K holding the quote, quote, source ("r2" = in our R2 10-K text, "sec" = fetched from sec.gov), note
D = [
 ("Humira", "AbbVie", 1551152, "humira", "biologic", 2023, "0001551152-24-000011",
  "Humira is facing competition from biosimilar products in the United States following the loss of exclusivity in 2023", "r2",
  "US biosimilars from Jan 2023 under settlements. 2023 held up better than a pure biosimilar cliff because AbbVie used rebate walls with PBMs; the steep leg came in 2024-2025 when formularies flipped."),
 ("Stelara", "Johnson & Johnson", 200406, "stelara", "biologic", 2025, "0000200406-24-000013",
  "the Company does not anticipate the launch of a biosimilar version of STELARA before January 1, 2025 in the United States.", "r2",
  "Only one post-LOE year (FY2025) in the data; US sales in the 2025 year-0 row."),
 ("Neulasta", "Amgen", 318154, "neulasta", "biologic", 2018, "0000318154-19-000008",
  "A biosimilar version of Neulasta was approved in the second quarter of 2018 and launched in July 2018, and another biosimilar version was approved in the fourth quarter of 2018 and launched in January 2019.", "sec",
  "First biosimilar (Mylan Fulphila) July 2018, more in 2019-2021. Only FY2017 precedes LOE in our data, so peak is a single year. Data stops at FY2022 (Amgen dropped the line item)."),
 ("Epogen", "Amgen", 318154, "epogen", "biologic", 2018, "0000318154-19-000008",
  "On May 15, 2018, the FDA approved Hospira's RETACRIT, a biosimilar to EPOGEN, which was subsequently launched on November 14, 2018.", "sec",
  "Retacrit launched Nov 2018 so year 0 is only ~6 weeks exposed. Peak is FY2017 only; series ends FY2019 (Amgen stopped reporting it as a line item)."),
 ("Revlimid", "Bristol-Myers Squibb", 14272, "revlimid", "small_molecule", 2022, "0000014272-22-000051",
  "Natco was granted a volume-limited license to sell generic lenalidomide in the U.S. commencing in March 2022.", "r2",
  "SPECIAL SHAPE: volume-limited generic entry (settlement caps generic volume until Jan 31 2026), so decay is slower than an open generic cliff. Total (global) sales only; includes ex-US where generics entered Jan-Feb 2022. FY2019 is a partial Celgene year."),
 ("Lyrica", "Pfizer", 78003, "lyrica", "small_molecule", 2019, "0000078003-20-000014",
  "Lyrica lost patent protection in the U.S. in June 2019 and multi-source generic competition began in July 2019.", "r2",
  "Global sales (Upjohn segment disclosure), so ex-US dilutes the US erosion. Series ends FY2019 (Upjohn merged into Viatris)."),
 ("Truvada", "Gilead", 882095, "truvada", "small_molecule", 2020, "0000882095-22-000007",
  "the decrease in Truvada and Atripla sales in the United States, as expected, primarily due to the continued generic competition following the October 2020 loss of exclusivity in the United States.", "r2",
  "Generic entry Sept 30 / Oct 2020. Part of the decline is also a planned switch to Descovy (Gilead's own successor), so erosion is partly self-cannibalization."),
 ("Atripla", "Gilead", 882095, "atripla", "small_molecule", 2020, "0000882095-22-000007",
  "the decrease in Truvada and Atripla sales in the United States, as expected, primarily due to the continued generic competition following the October 2020 loss of exclusivity in the United States.", "r2",
  "Same October 2020 event as Truvada; series ends FY2021."),
 ("Ranexa", "Gilead", 882095, "ranexa", "small_molecule", 2019, "0000882095-20-000006",
  "the expected decline in sales of Ranexa and Letairis after the entry of generic versions in the United States in early 2019.", "r2",
  "Generic entry early 2019; Gilead reports it in an 'other products' group but the product row is in XBRL."),
 ("Letairis", "Gilead", 882095, "letairis", "small_molecule", 2019, "0000882095-20-000006",
  "the expected decline in sales of Ranexa and Letairis after the entry of generic versions in the United States in early 2019.", "r2",
  "Gilead reports Letairis as US-only in XBRL (no geography split); treated as US."),
 ("Sensipar", "Amgen", 318154, "sensipar", "small_molecule", 2019, "0000318154-20-000017",
  "Our current litigation also includes disputes with a number of other manufacturers that began selling their approved generic cinacalcet products in the United States in early 2019.", "r2",
  "One generic sold from late 2018 (settled Jan 2019); broad entry early 2019. Series ends FY2019 in our data, so only year 0."),
 ("Cialis", "Eli Lilly", 59478, "cialis", "small_molecule", 2018, "0000059478-20-000057",
  "U.S. exclusivity ended in late September 2018.", "r2",
  "Late-September entry so FY2018 holds only one quarter of erosion (year-0 pct is high; the collapse is in year 1). Peak is FY2017 only."),
 ("Alimta", "Eli Lilly", 59478, "alimta", "small_molecule", 2022, "0000059478-20-000057",
  "allowing Eagle a limited initial entry into the market with its product starting February 2022 (up to an approximate three-week supply) and subsequent unlimited entry starting April 2022.", "r2",
  "Settlement-dated entry (unlimited from April 2022). Series ends FY2023."),
 ("Zytiga", "Johnson & Johnson", 200406, "zytiga", "small_molecule", 2018, "0000200406-20-000010",
  "In November 2018, the United States Court of Appeals for the Federal Circuit denied Janssen's request for an injunction pending appeal. As a result, several generic versions of ZYTIGA have entered the market.", "r2",
  "Entry in Nov 2018, so FY2018 US sales still rose (pct above 100); the cliff is FY2019 onward. Peak is FY2017 only."),
 ("NuvaRing", "Merck", 310158, "nuvaring", "small_molecule", 2019, "0000310158-20-000005",
  "the patent that provided U.S. market exclusivity for NuvaRing expired in April 2018 and generic competition began in December 2019.", "r2",
  "Entry in December 2019, so year 0 is ~100% and the cliff lands in year 1 (FY2020)."),
 ("Noxafil", "Merck", 310158, "noxafil", "small_molecule", 2019, "0000310158-20-000005",
  "the patents that provided U.S. and EU market exclusivity for certain forms of Noxafil expired in July 2019 and December 2019, respectively, and the Company anticipates a significant decline in U.S. and EU Noxafil sales.", "r2",
  "US exclusivity expired July 2019."),
 ("Sutent", "Pfizer", 78003, "sutent", "small_molecule", 2021, "0000078003-22-000027",
  "The decrease for Sutent primarily reflects lower volume demand in the U.S. resulting from its loss of exclusivity in August 2021", "r2",
  "Global sales only. Already declining before LOE (competition from newer TKIs), so pct of peak overstates the LOE-only effect."),
 ("Sprycel", "Bristol-Myers Squibb", 14272, "sprycel", "small_molecule", 2024, "0000014272-25-000039",
  "For Sprycel, in the U.S., EU and Japan, generics have entered the market.", "r2",
  "Settlement allowed US generics from September 2024 (FY2021 10-K 0000014272-22-000051); FY2024 10-K confirms entry. Global sales only; EU/Japan generics also in the base."),
]

EXCLUDED = [
 ("Remicade (J&J, Merck ex-US)", "US biosimilar entry was 2016, before our fiscal 2017-2025 data, so no pre-LOE peak can be indexed."),
 ("Zetia, Vytorin, Cubicin (Merck)", "US LOE 2016-2017, before our data window; peak not observable."),
 ("Januvia / Janumet (Merck)", "No US generic launched. FY2022 10-K (0001628280-23-005061) says US exclusivity runs to May 2026 under settlements; the 2023-2025 decline is price/Medicaid/IRA pressure, not LOE."),
 ("Humalog (Lilly)", "Authorized generic and price cuts from 2019, not a loss of exclusivity; excluded to keep LOE curve clean."),
 ("Forteo (Lilly)", "Patents expired 2018-2019 but 10-K gives no dated US generic or biosimilar entry; decline gradual. LOE year unverified."),
 ("Restasis (AbbVie)", "Sales fall in 2022 but no 10-K quote dates US generic entry. LOE year unverified."),
 ("Viread, Emend, Invanz (Gilead, Merck)", "Generic entry known from memory only; no dated US quote found in 10-K text. Unverified."),
 ("Chantix (Pfizer)", "Patent expired Nov 2020 but no dated generic entry in the text, and the 2021 collapse is confounded by the nitrosamine recall. Unverified and confounded."),
 ("Abraxane (BMS)", "Generics permitted in 2022 by settlement but total-only series rebounds in 2023 (non-monotonic) and mixes ex-US generics already on market; not a clean LOE series."),
 ("Aranesp, Enbrel, Eylea, Xarelto", "No US generic/biosimilar entry in the period (Enbrel biosimilars approved not launched; Eylea and Xarelto still protected or in litigation)."),
 ("Velcade (J&J)", "US sales are Takeda's, J&J reports ex-US only; no US series."),
]

W = 350  # minimum days for a fiscal-year fact


def _fy(end):
    y, m = int(end[:4]), int(end[5:7])
    return y if m > 3 else y - 1


def _series(store):
    """{(cik, member_lower, fy): {'tot': max no-geo value, 'us': max country:US value}} from R2."""
    idx = [json.loads(l) for l in store.get("index/tenk_index.jsonl").decode().splitlines()]
    out = collections.defaultdict(lambda: {"tot": 0.0, "us": 0.0})
    for cik in sorted({d[2] for d in D}):
        for a in sorted({i["accession"] for i in idx if int(i["cik"]) == cik}):
            raw = store.get(f"xbrl_product/{cik}/{a}.jsonl.gz")
            if not raw:
                continue
            for line in gzip.decompress(raw).decode().splitlines():
                r = json.loads(line)
                d = r.get("dims") or {}
                p = d.get("srt:ProductOrServiceAxis")
                if not p or not r.get("value") or (r.get("days") or 0) <= W:
                    continue
                g = d.get("srt:StatementGeographicalAxis")
                k = (cik, p.lower(), _fy(r["end"]))
                if g is None:
                    out[k]["tot"] = max(out[k]["tot"], r["value"])
                elif g == "country:US":
                    out[k]["us"] = max(out[k]["us"], r["value"])
    return out, idx


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _verify_quote(store, idx, cik, acc, quote):
    rec = next((i for i in idx if i["accession"] == acc and int(i["cik"]) == cik), None)
    if not rec:
        return False
    raw = store.get(rec["storage_key"])
    return bool(raw) and _norm(quote) in _norm(gzip.decompress(raw).decode("utf8", "ignore"))


def build(write=True):
    store = Store()
    S, idx = _series(store)
    drugs = []
    for brand, company, cik, key, modality, loe, acc, quote, src, note in D:
        years = collections.defaultdict(dict)
        for (c, m, y), v in S.items():
            if c == cik and key in m:
                years[y] = v
        geo = "US" if any(years[y]["us"] for y in years) else "total"
        val = {y: (years[y]["us"] if geo == "US" else years[y]["tot"]) for y in years}
        val = {y: v for y, v in val.items() if v}
        pre = [val[y] for y in range(loe - 3, loe) if y in val]
        peak = max(pre) if pre else None
        series = {str(y): round(v) for y, v in sorted(val.items())}
        pct = {}
        if peak:
            for t in range(0, 5):
                if loe + t in val:
                    pct[str(t)] = round(100 * val[loe + t] / peak, 1)
        quote_ok = _verify_quote(store, idx, cik, acc, quote) if src == "r2" else None
        included = bool(peak) and "0" in pct and (quote_ok is True or src == "sec")
        if src == "r2" and not quote_ok:
            note += " WARNING: quote not found verbatim in R2 text."
        drugs.append({
            "brand": brand, "company": company, "cik": cik, "modality": modality, "geography": geo,
            "loe_year": loe, "loe_quote": quote, "loe_accession": acc,
            "loe_quote_source": "R2 tenk text (verbatim match checked)" if src == "r2" else "sec.gov FY2018 10-K (outside R2 text window)",
            "peak_pre_loe_usd": round(peak) if peak else None,
            "peak_years_used": [y for y in range(loe - 3, loe) if y in val],
            "series": series, "pct_of_peak_by_t": pct, "included": included, "note": note,
        })
    curves = {}
    for mod in ("biologic", "small_molecule"):
        yrs, med, lo, hi, n = [], [], [], [], []
        for t in range(0, 5):
            v = [d["pct_of_peak_by_t"][str(t)] for d in drugs if d["included"] and d["modality"] == mod and str(t) in d["pct_of_peak_by_t"]]
            yrs.append(t)
            n.append(len(v))
            med.append(round(statistics.median(v), 1) if v else None)
            lo.append(min(v) if v else None)
            hi.append(max(v) if v else None)
        curves[mod] = {"year": yrs, "pct_of_peak": med, "low": lo, "high": hi, "n": n}
    out = {
        "as_of": date.today().isoformat(),
        "method": __doc__.split("Usage:")[0].strip(),
        "caveats": [
            "n is small, especially for biologics (4 drugs, n falls to 1-2 by year 2); treat the biologic curve beyond year 1 as indicative.",
            "Year 0 is the fiscal year of entry; entries late in the year (Cialis Sep, Zytiga Nov, Epogen Nov, NuvaRing Dec) show ~90-145% at t=0 and carry the cliff in t=1.",
            "Peak is the max of up to 3 pre-LOE years in our data (FY2017+); drugs with a 2018 LOE have a single pre-LOE year.",
            "Several series are global (flagged geography=total) and understate US erosion; Revlimid is volume-limited and decays slower.",
            "Humira year 0 held up because of PBM rebate walls; Humira is the largest biologic and sets the biologic tail.",
            "Selection: only LOEs with a verified 10-K quote and at least a year-0 data point; unverified or confounded cases are in `excluded`.",
        ],
        "curves": curves, "drugs": drugs,
        "excluded": [{"drug": a, "reason": b} for a, b in EXCLUDED],
    }
    if write:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        blob = json.dumps(out, indent=1).encode()
        CACHE.write_bytes(blob)
        rows = [["brand", "company", "modality", "geography", "loe_year", "included", "t", "fiscal_year", "sales_usd", "pct_of_peak"]]
        for d in drugs:
            for t in range(0, 5):
                y = d["loe_year"] + t
                if str(y) in d["series"]:
                    rows.append([d["brand"], d["company"], d["modality"], d["geography"], d["loe_year"], d["included"], t, y,
                                 d["series"][str(y)], d["pct_of_peak_by_t"].get(str(t), "")])
        with open(CSV_CACHE, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        store.put(R2_JSON, blob, "application/json")
        store.put(R2_CSV, CSV_CACHE.read_bytes(), "text/csv")
    return out


def _load():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return build()


def revenue_at_risk(sales, loe_year, modality, through=2030):
    """Lost sales per year from loe_year to `through`: sales * (1 - median pct of peak(t)) / 100 scale.

    `sales` is the pre-LOE annual run-rate (the 'peak'). Median curve is forced non-increasing (running min)
    and held flat at its year-4 value beyond t=4. Returns [(year, lost_sales), ...]."""
    c = _load()["curves"][modality]
    pct, floor = [], 100.0
    for v in c["pct_of_peak"]:
        if v is None:
            break
        floor = min(floor, v)
        pct.append(floor)
    out = []
    for y in range(loe_year, through + 1):
        t = y - loe_year
        p = pct[min(t, len(pct) - 1)]
        out.append((y, round(sales * max(0.0, 1 - p / 100), 2)))
    return out


if __name__ == "__main__":
    o = build()
    for m, c in o["curves"].items():
        print(m)
        for i, t in enumerate(c["year"]):
            print(f"  t={t} median={c['pct_of_peak'][i]} low={c['low'][i]} high={c['high'][i]} n={c['n'][i]}")
    print("included:", [d["brand"] for d in o["drugs"] if d["included"]])
    print("wrote", CACHE, CSV_CACHE, "and R2", R2_JSON, R2_CSV, file=sys.stderr)
