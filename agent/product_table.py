"""Per-drug join table for the pharma case: one row per company x brand, with LOE, pricing and pipeline facts.

Answers, per brand: "when does exclusivity end" and "when does pricing change". Works for any list of tickers or
CIKs; the 14 candidate companies in agent.gap_data.COMPANIES have hand-tuned applicant regexes, any other company
falls back to a regex built from its SEC name.

Inputs (all in R2, see docs/research/pharma_data_map.md and docs/research/product_table.md):
  public/orange_book.zip, public/purple_book_2026_09.csv, public/paragraph_iv.xlsx, public/ira_selected_drugs_mfp.zip,
  public/partd_spending_dy24.csv, public/partd_quarterly_2025.csv.gz, public/partb_spending_dy24.csv,
  public/first_generics.csv, classes/*.jsonl.gz, xbrl_product/<cik>/<acc>.jsonl.gz, xbrl/<cik>.json,
  trials/<cik>.jsonl.gz, formulary/rxcui_summary.csv.gz, index/tenk_index.jsonl,
  derived/company_stated_loe.jsonl and derived/loe_curves.json (optional, from parallel workers).

Outputs: derived/product_table/<TICKERS>.csv, <TICKERS>_citations.jsonl, <TICKERS>_timeline.json

Run:  python -m agent.product_table --tickers BMY,PFE,JNJ
      python -m agent.product_table --ciks 14272,78003 --no-upload
Set PRODUCT_TABLE_CACHE=<dir> to cache R2 objects on disk between runs.
"""

import argparse
import gzip
import io
import json
import os
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd

from agent.gap_data import COMPANIES
from agent.tenk import Store

TODAY = date.today()
HORIZON = 2030
MIN_REVENUE = 250e6
LOE_WINDOW = (2024, 2032)

TICKERS = {"MCK": 927653, "COR": 1140859, "CAH": 721371, "ALC": 1167379, "BLCO": 1860742, "ABBV": 1551152,
           "MRK": 310158, "BMY": 14272, "PFE": 78003, "LLY": 59478, "JNJ": 200406, "REGN": 872589,
           "AMGN": 318154, "GILD": 882095}

# IRA selection announcement dates by initial price applicability year (CMS press releases)
IRA_SELECTED_ON = {2026: "2023-08-29", 2027: "2025-01-17", 2028: "2026-01-27"}

# Partnered products: the NDA/BLA holder is not the only company booking revenue (from 10-K collaboration notes)
PARTNERED = {
    "ELIQUIS": "BMS holds the NDA and books global net sales; Pfizer shares profits and losses and reports Eliquis "
               "alliance revenue (do not add the two companies' Eliquis revenue together).",
    "XARELTO": "Janssen (J&J) holds the US NDA and books US sales; Bayer markets and books sales outside the US.",
    "IMBRUVICA": "Pharmacyclics (AbbVie) holds the NDA and books US sales; Janssen (J&J) books sales outside the US; "
                 "profits are shared.",
    "LENVIMA": "Eisai holds the NDA; Merck reports alliance revenue.",
    "LYNPARZA": "AstraZeneca holds the NDA; Merck reports alliance revenue.",
    "XTANDI": "Astellas holds the NDA; Pfizer (via Medivation) shares US profits and books its share as revenue.",
    "JARDIANCE": "Boehringer Ingelheim holds the NDA; Lilly reports its alliance share.",
    "EYLEA": "Regeneron books US net sales; Bayer markets outside the US and shares profits.",
    "DUPIXENT": "Sanofi books global net sales; Regeneron reports its share of collaboration profits.",
    "PRALUENT": "Regeneron books US sales; Sanofi markets outside the US.",
    "ADCETRIS": "Pfizer (Seagen) books US and Canada sales; Takeda markets elsewhere.",
}

AREA_TERMS = [
    "atrial fibrillation", "thrombo", "embolism", "stroke", "heart failure", "hypertension", "hypercholesterol",
    "hyperlipid", "coronary", "myocardial infarction", "cardiomyopathy", "diabetes", "obesity", "overweight",
    "chronic kidney disease", "psoriasis", "psoriatic arthritis", "rheumatoid arthritis", "spondyl", "crohn",
    "ulcerative colitis", "atopic dermatitis", "asthma", "chronic obstructive", "hidradenitis", "uveitis", "lupus",
    "multiple sclerosis", "migraine", "alzheimer", "parkinson", "schizophrenia", "bipolar", "depressi", "hiv",
    "hepatitis b", "hepatitis c", "influenza", "covid", "respiratory syncytial", "pneumococcal", "papillomavirus",
    "melanoma", "lung cancer", "non-small cell", "small cell lung", "breast cancer", "prostate cancer",
    "renal cell", "urothelial", "bladder cancer", "colorectal", "gastric", "esophag", "head and neck",
    "hepatocellular", "cervical cancer", "endometrial", "ovarian", "lymphoma", "leukemia", "myeloma",
    "myelodysplastic", "mesothelioma", "merkel", "macular degeneration", "macular edema", "osteoporosis",
    "anemia", "hemophilia", "sickle cell", "pulmonary arterial hypertension", "cystic fibrosis", "amyloid",
    "thyroid eye", "gout", "alopecia", "neutropenia", "thrombocytopenia", "graft", "biliary",
]
# XBRL member names that do not match the current US brand name (member key prefix -> brand key)
MEMBER_ALIASES = {"VYNDAQEL": "VYNDAMAX", "PREVNARPREVENAR": "PREVNAR20", "ELYEAHD": "EYLEAHD",
                  "INVEGASUSTENNAXEPLIONTRINZATREVICTA": "INVEGASUSTENNA"}
ACTIVE_STATUSES ={"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}
GENERIC_MEMBER = re.compile(r"^(OTHER|TOTAL|PRODUCT|SERVICE|ALLIANCE|COLLABORATION|ROYALT|NETPRODUCT|SALESREVENUE|"
                            r"GROWTH|LEGACY|SHAREOF|REIMBURSE|EXCLUDING|ONCOLOGY|IMMUNOLOGY|NEUROSCIENCE|"
                            r"CARDIOMETABOLIC|INNOVATIVE|MEDTECH|PHARMACEUTICAL|VACCINE|ANIMAL|SALESBASED|"
                            r"REGENERONS|INTERNATIONAL|US$|UNITEDSTATES)")

store = Store()


# ---------------------------------------------------------------- small helpers

def _get(key):
    cache = os.environ.get("PRODUCT_TABLE_CACHE") if not key.startswith("derived/") else None
    if cache:
        p = Path(cache) / key
        if p.exists():
            return p.read_bytes()
    data = store.get(key)
    if data is not None and cache:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return data


def _gunzip(data):
    return gzip.decompress(data) if data and data[:2] == b"\x1f\x8b" else data


def _jsonl(key):
    data = _gunzip(_get(key))
    return [json.loads(l) for l in data.decode().splitlines() if l.strip()] if data else []


def bkey(s):
    """Normalized brand key: uppercase alphanumerics only."""
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def words(s):
    return re.findall(r"[A-Z0-9]+", re.sub(r"\(.*?\)", " ", str(s).upper()))


def iso(d):
    if d is None or (isinstance(d, float) and pd.isna(d)) or d is pd.NaT:
        return None
    if isinstance(d, str):
        return d
    return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)


def todate(x, fmt=None):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    t = pd.to_datetime(x, format=fmt, errors="coerce")
    return None if pd.isna(t) else t.date()


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, min(d.day, 28))


def num(x):
    try:
        v = float(x)
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- reference loaders (cached per process)

@lru_cache(None)
def orange_book():
    z = zipfile.ZipFile(io.BytesIO(_get("public/orange_book.zip")))
    rd = lambda n: pd.read_csv(z.open(n), sep="~", dtype=str, encoding="latin-1")
    prod, pat, exc = rd("products.txt"), rd("patent.txt"), rd("exclusivity.txt")
    pat = pat[pat.Appl_Type == "N"].copy()
    pat["date"] = pd.to_datetime(pat.Patent_Expire_Date_Text, format="%b %d, %Y", errors="coerce")
    exc = exc[exc.Appl_Type == "N"].copy()
    exc["date"] = pd.to_datetime(exc.Exclusivity_Date, format="%b %d, %Y", errors="coerce")
    prod["approval"] = pd.to_datetime(prod.Approval_Date, format="%b %d, %Y", errors="coerce")
    return prod, pat, exc


@lru_cache(None)
def ob_by_appl():
    """Per NDA: substance patent (with *PED), last listed patent, NCE/PED/ODE/NP exclusivity, latest exclusivity."""
    _, pat, exc = orange_book()
    out = defaultdict(dict)
    for appl, g in pat.groupby("Appl_No"):
        subs = set(g.loc[g.Drug_Substance_Flag == "Y", "Patent_No"].str.replace("*PED", "", regex=False))
        base = g.Patent_No.str.replace("*PED", "", regex=False)
        # compound patent = the oldest (lowest-numbered) drug-substance patent; later substance patents are usually
        # salts/crystal forms that generics design around
        subs = {min(subs, key=lambda p: int(re.sub(r"\D", "", p) or 0))} if subs else subs
        sg = g[base.isin(subs)].dropna(subset=["date"])
        if len(sg):
            r = sg.loc[sg.date.idxmax()]
            out[appl]["substance"] = (r.date.date(), f"patent.txt N~{appl}~{r.Product_No}~{r.Patent_No}")
        ag = g.dropna(subset=["date"])
        if len(ag):
            r = ag.loc[ag.date.idxmax()]
            out[appl]["last_patent"] = (r.date.date(), f"patent.txt N~{appl}~{r.Product_No}~{r.Patent_No}")
    for appl, g in exc.dropna(subset=["date"]).groupby("Appl_No"):
        r = g.loc[g.date.idxmax()]
        out[appl]["latest_excl"] = (r.Exclusivity_Code, r.date.date(),
                                    f"exclusivity.txt N~{appl}~{r.Product_No}~{r.Exclusivity_Code}")
        for label, rx in (("nce", r"^NCE"), ("ode", r"^ODE"), ("np", r"^NP$"), ("ped", r"^PED")):
            s = g[g.Exclusivity_Code.str.match(rx, na=False)]
            if len(s):
                rr = s.loc[s.date.idxmax()]
                out[appl][label] = (rr.date.date(), f"exclusivity.txt N~{appl}~{rr.Product_No}~{rr.Exclusivity_Code}")
    return out


@lru_cache(None)
def purple_book():
    text = _get("public/purple_book_2026_09.csv").decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    hdr = [i for i, l in enumerate(lines) if l.startswith("N/R/U") or l.startswith('"N/R/U')]
    pb = pd.read_csv(io.StringIO("\n".join(lines[hdr[-1]:])), dtype=str)
    pb["row_no"] = pb.index + hdr[-1] + 2
    for c in ("Approval Date", "Inter. Approval Date", "Ref. Product Exclusivity Exp. Date",
              "Orphan Exclusivity Exp. Date", "Date of First Licensure"):
        pb[c + "_d"] = pd.to_datetime(pb[c].str.strip(), format="%B %d, %Y", errors="coerce")
    pb["brand_u"] = pb["Proprietary Name"].str.upper().str.strip()
    pb["ref_u"] = pb["Ref. Product Proprietary Name"].str.upper().str.strip()
    return pb


@lru_cache(None)
def piv_list():
    x = pd.read_excel(io.BytesIO(_get("public/paragraph_iv.xlsx")), header=None, dtype=object)
    hdr = next(i for i in range(10) if str(x.iloc[i, 0]).strip().upper() == "DRUG NAME")
    x = x.iloc[hdr + 1:].reset_index(drop=True)
    x.columns = ["drug", "form", "strength", "rld", "submitted", "n_anda", "status180", "decision180",
                 "first_approval", "first_marketing", "last_patent"]
    x["row_no"] = x.index + hdr + 2
    parts = x.rld.astype(str).str.split("\n")
    x["rld_brand"] = parts.str[0].str.strip()
    x["nda"] = parts.str[-1].str.extract(r"(\d+)")[0].str.zfill(6)
    for c in ("submitted", "decision180", "first_approval", "first_marketing", "last_patent"):
        x[c] = pd.to_datetime(x[c].astype(str).str.strip(), errors="coerce", format="mixed")
    x["n_anda"] = pd.to_numeric(x.n_anda, errors="coerce")
    return x


@lru_cache(None)
def ira_file():
    z = zipfile.ZipFile(io.BytesIO(_get("public/ira_selected_drugs_mfp.zip")))
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    df = pd.read_csv(z.open(name), dtype=str, encoding="latin-1")
    df["row_no"] = df.index + 2
    df["eff"] = pd.to_datetime(df["MFP Effective Date"], format="%m/%d/%Y", errors="coerce")
    df["end"] = pd.to_datetime(df["MFP End Date"], format="%m/%d/%Y", errors="coerce")
    df["names"] = df["Selected Drug Name"].fillna("").str.upper().str.split(";").apply(lambda l: {bkey(s) for s in l})
    return df, name


@lru_cache(None)
def cms(key):
    raw = _gunzip(_get(key))
    df = pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False)
    df["row_no"] = df.index + 2
    df["w"] = df.Brnd_Name.fillna("").apply(words)
    return df


@lru_cache(None)
def brand_products():
    rows = _jsonl("classes/brand_products.jsonl.gz")
    for r in rows:
        r["brand"] = str(r["brand"]).upper().strip()
        r["key"] = bkey(r["brand"])
    return rows


@lru_cache(None)
def ingredient_classes():
    return {r["ingredient"]: r for r in _jsonl("classes/ingredient_classes.jsonl.gz")}


@lru_cache(None)
def labels():
    out = {}
    for r in _jsonl("classes/brand_indications.jsonl.gz"):
        k = bkey(r["brand"])
        if k not in out or (r.get("indications") and not out[k].get("indications")):
            out[k] = r
    return out


@lru_cache(None)
def formulary():
    raw = _get("formulary/rxcui_summary.csv.gz")
    if not raw:
        return None
    f = pd.read_csv(io.BytesIO(_gunzip(raw)), dtype={"RXCUI": str})
    return f.set_index("RXCUI")


@lru_cache(None)
def tenk_index():
    return _jsonl("index/tenk_index.jsonl")


@lru_cache(None)
def stated_loe():
    return _jsonl("derived/company_stated_loe.jsonl")


@lru_cache(None)
def loe_curves():
    raw = _get("derived/loe_curves.json")
    return json.loads(raw) if raw else None


@lru_cache(None)
def first_generics():
    raw = _get("public/first_generics.csv")
    if not raw:
        return None
    df = pd.read_csv(io.BytesIO(raw), dtype=str)
    df["row_no"] = df.index + 2
    df["w"] = df["Brand Name"].fillna("").apply(words)
    return df


# ---------------------------------------------------------------- companies

def resolve(tickers=(), ciks=()):
    out = []
    unknown = [t.upper() for t in tickers if t.upper() not in TICKERS]
    tmap = {}
    if unknown:
        from agent.tenk import ticker_map
        tmap = ticker_map()
    for t in tickers:
        t = t.upper()
        c = TICKERS.get(t) or tmap.get(t)
        if not c:
            raise SystemExit(f"unknown ticker {t}")
        out.append((t, c))
    rev = {v: k for k, v in TICKERS.items()}
    out += [(rev.get(int(c), str(c)), int(c)) for c in ciks]
    return list(dict.fromkeys(out))


def company_info(cik):
    if cik in COMPANIES:
        return COMPANIES[cik]
    name = next((f["company"] for f in tenk_index() if f["cik"] == cik), None)
    if not name:
        from agent.tenk import sec_get
        name = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)["name"]
    first = next((w for w in words(name) if len(w) >= 4 and w not in {"INC", "CORP", "THE"}), words(name)[0])
    return name, rf"\b{first}"


# ---------------------------------------------------------------- revenue (XBRL instance product facts)

def latest_annual(cik):
    fs = [f for f in tenk_index() if f["cik"] == cik and f["form"] in ("10-K", "20-F")]
    for f in sorted(fs, key=lambda f: f["filed_date"], reverse=True):
        rows = _jsonl(f"xbrl_product/{cik}/{f['accession']}.jsonl.gz")
        if rows:
            return f, rows
    return (fs[-1] if fs else None), []


def product_revenue(cik):
    """{member: {year: {"total": (value, row_key), "us": (value, row_key), "us_only": bool}}}, filing row."""
    f, rows = latest_annual(cik)
    by = defaultdict(lambda: defaultdict(lambda: {"tot": [], "us": [], "nonus": []}))
    for r in rows:
        unit = str(r.get("unit") or "").lower()
        concept = r["concept"].split(":")[-1]
        if r["days"] < 350 or "usd" not in unit or "percent" in concept.lower() or not r["value"]:
            continue
        m = r["dims"].get("srt:ProductOrServiceAxis")
        if not m:
            continue
        geo = r["dims"].get("srt:StatementGeographicalAxis")
        slot = "tot" if geo is None else "us" if geo == "country:US" else "nonus" if geo.endswith("NonUsMember") else None
        if slot:
            rk = f"{r['concept']}|{m}|{r['start']}..{r['end']}|{geo or 'total'}"
            by[m][int(r["end"][:4])][slot].append((r["value"], rk))
    out = {}
    for m, years in by.items():
        out[m] = {}
        for y, s in years.items():
            tot = max(s["tot"]) if s["tot"] else None
            us = max(s["us"]) if s["us"] else None
            non = max(s["nonus"]) if s["nonus"] else None
            us_only = False
            if tot is None and us and non:
                tot = (us[0] + non[0], f"{us[1]} + {non[1]}")
            elif tot is None and us:
                tot, us_only = us, True
            out[m][y] = {"total": tot, "us": us, "us_only": us_only}
    return out, f


def company_revenue(cik, accession, fy):
    raw = _get(f"xbrl/{cik}.json")
    if not raw:
        return None
    facts = json.loads(raw).get("facts", {}).get("us-gaap", {})
    best = None
    for c in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"):
        for v in facts.get(c, {}).get("units", {}).get("USD", []):
            if v.get("accn") == accession and v.get("start") and v["end"][:4] == str(fy):
                days = (datetime.fromisoformat(v["end"]) - datetime.fromisoformat(v["start"])).days
                if days > 350 and (best is None or v["val"] > best[0]):
                    best = (v["val"], f"{c}|{v['start']}..{v['end']}|accn {accession}")
    return best


def member_key(m):
    s = m.split(":")[-1]
    s = re.sub(r"Member$", "", s)
    s = re.sub(r"^AllianceRevenue", "", s, flags=re.I)
    s = re.sub(r"(NetProductSales|ProductSales|Family|Franchise)$", "", s, flags=re.I)
    return bkey(s)


def match_member(m, own, allb):
    """Return (brand_key, method) for a revenue member, preferring the company's own brands."""
    k = member_key(m)
    if len(k) < 4 or GENERIC_MEMBER.match(k):
        return None, None
    for pre, target in MEMBER_ALIASES.items():
        if k == pre and target in allb:
            return target, ("own" if target in own else "partner") + ":alias"
    for pool, tag in ((own, "own"), (allb, "partner")):
        if k in pool:
            return k, f"{tag}:exact"
        pre = [b for b in pool if len(b) >= 4 and k.startswith(b)]
        if pre:
            return max(pre, key=len), f"{tag}:prefix"
        if tag == "own":
            pre = [b for b in pool if len(k) >= 5 and b.startswith(k)]
            if pre:
                return min(pre, key=len), f"{tag}:member_prefix"
        fw = [b for b, first in pool.items() if first and len(first) >= 5 and k.startswith(first)]
        if fw:
            return min(fw, key=len), f"{tag}:first_word"
    return None, None


# ---------------------------------------------------------------- brand universe

@lru_cache(None)
def brand_universe():
    """brand_key -> {brand, ingredient, modality, holder, cik_holder, appls, dfroutes}"""
    prod, _, _ = orange_book()
    pb = purple_book()
    u = {}
    for r in brand_products():
        k = r["key"]
        if k not in u:
            u[k] = {"brand": r["brand"], "ingredient": str(r["ingredient"]).strip(), "modality": r["modality"],
                    "holder": r["applicant"], "holder_cik": r["cik"], "appls": set(), "dfroutes": set()}
    from agent.gap_data import company_for
    n = prod[(prod.Appl_Type == "N") & (prod.Type == "RX")]
    for r in n.itertuples():
        k = bkey(r.Trade_Name)
        if k not in u:  # brand_products keeps one row per brand+ingredient; add any RX NDA brand it missed
            u[k] = {"brand": r.Trade_Name.upper().strip(), "ingredient": r.Ingredient, "modality": "small molecule",
                    "holder": r.Applicant_Full_Name, "holder_cik": company_for(r.Applicant_Full_Name),
                    "appls": set(), "dfroutes": set()}
        if k in u:
            u[k]["appls"].add(r.Appl_No)
            u[k]["dfroutes"].add((r.Ingredient, r._2))
    for r in pb[pb["License Type"].str.startswith("351(a)", na=False)].itertuples():
        k = bkey(r.brand_u)
        if k in u:
            u[k]["appls"].add(str(r._3))
    return u


def first_word_map(keys, uni):
    return {k: bkey(words(uni[k]["brand"])[0]) if words(uni[k]["brand"]) else None for k in keys}


def own_brands(cik, rx):
    uni = brand_universe()
    keys = {k for k, v in uni.items() if v["holder_cik"] == cik or (cik not in COMPANIES and v["holder"]
                                                                   and re.search(rx, v["holder"], re.I))}
    # fold line extensions with the same ingredient into the base brand (ELIQUIS SPRINKLE -> ELIQUIS)
    groups = {}
    for k in sorted(keys, key=len):
        base = next((b for b in groups if k.startswith(b) and k != b and uni[b]["ingredient"].lower() ==
                     uni[k]["ingredient"].lower() and words(uni[k]["brand"])[0] == words(uni[b]["brand"])[0]), None)
        groups.setdefault(base or k, []).append(k)
    return groups


# ---------------------------------------------------------------- per-brand facts

class Row(dict):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cites = {}

    def put(self, field, value, source, key, row_key=None, accession=None):
        if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
            return
        self[field] = value
        self.cites[field] = (source, key, row_key, accession)


def fda_loe(row, keys, uni):
    """Orange Book / Purple Book LOE facts for the brand group; fills row and returns (date, basis)."""
    appls = set().union(*(uni[k]["appls"] for k in keys))
    obd = ob_by_appl()
    modality = uni[keys[0]]["modality"]
    sub = max((obd[a]["substance"] for a in appls if "substance" in obd.get(a, {})), default=None)
    last = max((obd[a]["last_patent"] for a in appls if "last_patent" in obd.get(a, {})), default=None)
    lex = max((obd[a]["latest_excl"] for a in appls if "latest_excl" in obd.get(a, {})), key=lambda t: t[1],
              default=None)
    ob_key = "public/orange_book.zip"
    if sub:
        row.put("loe_orange_book_substance", iso(sub[0]), "FDA Orange Book patent.txt", ob_key, sub[1])
    if last:
        row.put("loe_last_listed_patent", iso(last[0]), "FDA Orange Book patent.txt", ob_key, last[1])
    if lex:
        row.put("exclusivity_latest_code", lex[0], "FDA Orange Book exclusivity.txt", ob_key, lex[2])
        row.put("exclusivity_latest_date", iso(lex[1]), "FDA Orange Book exclusivity.txt", ob_key, lex[2])

    # Paragraph IV
    piv = piv_list()
    p = piv[piv.nda.isin(appls)]
    has_piv = len(p) > 0
    if has_piv:
        first = p.loc[p.submitted.idxmin()] if p.submitted.notna().any() else p.iloc[0]
        rk = f"paragraph_iv.xlsx row {int(first.row_no)} (RLD/NDA {first.rld_brand} {first.nda})"
        row.put("piv_first_submission", iso(todate(first.submitted)), "FDA Paragraph IV list", "public/paragraph_iv.xlsx", rk)
        if p.n_anda.notna().any():
            row.put("piv_anda_count", int(p.n_anda.max()), "FDA Paragraph IV list", "public/paragraph_iv.xlsx",
                    f"paragraph_iv.xlsx rows {','.join(str(int(i)) for i in p.row_no)} (max NUMBER OF ANDAs)")
        if isinstance(first.status180, str):
            row.put("piv_180day_status", first.status180.strip(), "FDA Paragraph IV list", "public/paragraph_iv.xlsx", rk)
        if p.first_marketing.notna().any():
            fm = p.loc[p.first_marketing.idxmin()]
            row.put("piv_first_generic_marketing", iso(todate(fm.first_marketing)), "FDA Paragraph IV list",
                    "public/paragraph_iv.xlsx", f"paragraph_iv.xlsx row {int(fm.row_no)} (FIRST COMMERCIAL MARKETING BY FTF)")
        if p.last_patent.notna().any():
            lp = p.loc[p.last_patent.idxmax()]
            row.put("piv_last_qualifying_patent", iso(todate(lp.last_patent)), "FDA Paragraph IV list",
                    "public/paragraph_iv.xlsx", f"paragraph_iv.xlsx row {int(lp.row_no)}")

    # ANDA holders: same ingredient and dosage form/route as the brand's NDAs
    prod, _, _ = orange_book()
    dfr = set().union(*(uni[k]["dfroutes"] for k in keys))
    if dfr:
        a = prod[(prod.Appl_Type == "A") & prod.Type.isin(["RX", "DISCN"])]
        a = a[[(i, d) in dfr for i, d in zip(a.Ingredient, a["DF;Route"])]]
        if len(a):
            rk = f"products.txt Appl_Type=A, Ingredient+DF;Route of NDA {','.join(sorted(appls))}"
            row.put("generic_anda_holders_count", int(a.Applicant_Full_Name.nunique()), "FDA Orange Book products.txt",
                    ob_key, rk + ", Type RX or DISCN (approved, maybe not launched)")
            row.put("generic_anda_holders_marketed", int(a[a.Type == "RX"].Applicant_Full_Name.nunique()),
                    "FDA Orange Book products.txt", ob_key, rk + ", Type RX")
            if a.approval.notna().any():
                fa = a.loc[a.approval.idxmin()]
                row.put("generic_first_anda_approval", iso(fa.approval.date()), "FDA Orange Book products.txt", ob_key,
                        f"products.txt A~{fa.Appl_No}~{fa.Product_No}")
        else:
            row["generic_anda_holders_count"] = 0
            row.cites["generic_anda_holders_count"] = ("FDA Orange Book products.txt", ob_key,
                                                       f"no Appl_Type=A rows for NDA {','.join(sorted(appls))}", None)

    # Purple Book
    pb = purple_book()
    brands_u = [uni[k]["brand"] for k in keys]
    ref = pb[pb.brand_u.isin(brands_u) & pb["License Type"].str.startswith("351(a)", na=False)]
    if ref["Ref. Product Exclusivity Exp. Date_d"].notna().any():
        r = ref.loc[ref["Ref. Product Exclusivity Exp. Date_d"].idxmax()]
        row.put("pb_ref_exclusivity", iso(r["Ref. Product Exclusivity Exp. Date_d"].date()), "FDA Purple Book",
                "public/purple_book_2026_09.csv", f"row {r.row_no} BLA {r['BLA Number']}")
    if ref["Orphan Exclusivity Exp. Date_d"].notna().any():
        r = ref.loc[ref["Orphan Exclusivity Exp. Date_d"].idxmax()]
        row.put("pb_orphan_exclusivity", iso(r["Orphan Exclusivity Exp. Date_d"].date()), "FDA Purple Book",
                "public/purple_book_2026_09.csv", f"row {r.row_no} BLA {r['BLA Number']}")
    bios = pb[pb.ref_u.isin(brands_u) & pb["License Type"].str.startswith("351(k)", na=False)]
    if modality == "biologic" or len(bios):
        rk = f"351(k) rows with Ref. Product Proprietary Name in {brands_u}"
        row.put("biosimilar_count", int(bios.brand_u.nunique()), "FDA Purple Book", "public/purple_book_2026_09.csv", rk)
        if len(bios):
            row.put("interchangeable_flag", bool(bios["License Type"].str.contains("Interchangeable").any()),
                    "FDA Purple Book", "public/purple_book_2026_09.csv", rk)
            b0 = bios.loc[bios["Approval Date_d"].idxmin()]
            row.put("biosimilar_first_approval", iso(b0["Approval Date_d"].date()), "FDA Purple Book",
                    "public/purple_book_2026_09.csv", f"row {b0.row_no} {b0['Proprietary Name']} BLA {b0['BLA Number']}")
            row["_biosimilars"] = [(iso(g["Approval Date_d"].min().date()), n, int(g.row_no.min()))
                                   for n, g in bios.groupby("Proprietary Name")]

    # FDA-only estimate (section 1 rule)
    cands, basis = [], []
    if modality == "biologic":
        if row.get("pb_ref_exclusivity"):
            cands.append(todate(row["pb_ref_exclusivity"]))
            basis.append(f"Purple Book 12-year reference exclusivity {row['pb_ref_exclusivity']}")
        if row.get("biosimilar_count"):
            basis.append(f"{row['biosimilar_count']} biosimilar(s) approved, first {row.get('biosimilar_first_approval')}"
                         f"{', interchangeable' if row.get('interchangeable_flag') else ''}; launch timing set by settlements")
            if not cands or cands[0] < TODAY:
                cands = [todate(row["biosimilar_first_approval"])]
                basis[0:0] = ["lower bound = first biosimilar approval"]
        if not cands:
            basis.append("no Purple Book exclusivity date; use 10-K stated LOE")
    else:
        nce = max((obd[a]["nce"] for a in appls if "nce" in obd.get(a, {})), default=None)
        if nce:
            ped = max((obd[a]["ped"] for a in appls if "ped" in obd.get(a, {})), default=None)
            d = nce[0]
            if ped and 0 < (ped[0] - nce[0]).days <= 200:
                d = ped[0]
            if has_piv:
                d = add_months(d, 30)
            cands.append(d)
            basis.append(f"NCE exclusivity {iso(nce[0])}{' + PED' if d != nce[0] and not has_piv else ''}"
                         f"{' + 30-month stay (PIV filed)' if has_piv else ''}")
        if sub:
            cands.append(sub[0])
            basis.append(f"drug-substance patent {iso(sub[0])} ({sub[1].split('~')[-1]})")
        for lab in ("ode", "np"):
            o = max((obd[a][lab] for a in appls if lab in obd.get(a, {})), default=None)
            if o:
                cands.append(o[0])
                basis.append(f"{lab.upper()} exclusivity {iso(o[0])}")
        if row.get("piv_first_generic_marketing"):
            basis.append(f"first-filer generic marketed {row['piv_first_generic_marketing']}")
            if not cands or max(cands) < todate(row["piv_first_generic_marketing"]):
                cands = [todate(row["piv_first_generic_marketing"])]
        if not cands and row.get("generic_anda_holders_count"):
            basis.append(f"no unexpired substance patent or exclusivity; {row['generic_anda_holders_count']} ANDA "
                         f"holder(s) approved (first {row.get('generic_first_anda_approval')})")
            if row.get("generic_first_anda_approval"):
                cands = [todate(row["generic_first_anda_approval"])]
        if last and not sub:
            basis.append(f"last listed patent {iso(last[0])} (formulation/use, upper bound)")
    est = max(cands) if cands else None
    return est, "; ".join(basis)


def pick_stated(cik, keys, uni):
    names = {bkey(re.sub(r"\(.*?\)", "", uni[k]["brand"])) for k in keys}

    def pnames(r):  # "Mounjaro/Zepbound (data protection)" -> {MOUNJARO, ZEPBOUND}
        base = re.sub(r"\(.*?\)", "", str(r.get("product", "")))
        return {bkey(p) for p in re.split(r"/|,|;", base)} | {bkey(base)}
    rows = [r for r in stated_loe() if pnames(r) & names]
    if not rows:
        return None
    def rank(r):
        prod = str(r.get("product", "")).lower()
        return (r.get("us_loe") is not None, "settlement" in prod or "settlement" in str(r.get("basis", "")).lower(),
                r.get("cik") == cik, "(" not in prod or "table row" in prod, "additional" not in prod)
    return max(rows, key=rank)


def parse_loe_text(s):
    if not s:
        return None, None
    s = str(s)
    d = todate(s) if re.search(r"[A-Za-z]{3,}\.? \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}", s) else None
    if d:
        return d.isoformat(), d.year
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", s)
    if m:
        d = todate(f"{m.group(1)} 1, {m.group(2)}")
        if d:
            return d.isoformat()[:7], d.year
    m = re.search(r"(19|20)\d{2}", s)
    return (m.group(0), int(m.group(0))) if m else (None, None)


def pricing(row, keys, uni):
    brands = [uni[k]["brand"] for k in keys]
    ing = uni[keys[0]]["ingredient"].lower()
    ing_w = re.findall(r"[a-z]+", ing)[:1]

    def match(df, gcol):
        bw = [words(b) for b in brands]
        ok = df.w.apply(lambda w: any(w[:len(b)] == b for b in bw if b))
        g = df[gcol].fillna("").str.lower()
        if ing_w:
            ok &= g.str.contains(ing_w[0][:6], regex=False)
        return df[ok]

    d = cms("public/partd_spending_dy24.csv")
    m = match(d[d.Mftr_Name == "Overall"], "Gnrc_Name")
    if len(m):
        sp = m.Tot_Spndng_2024.apply(num)
        top = m.loc[sp.fillna(-1).idxmax()]
        rk = f"Brnd_Name={'|'.join(sorted(set(m.Brnd_Name)))} Mftr_Name=Overall rows {','.join(map(str, m.row_no))}"
        src, key = "CMS Part D Spending by Drug DY2024", "public/partd_spending_dy24.csv"
        row.put("partd_spend_2024", round(sp.sum(skipna=True), 0) if sp.notna().any() else None, src, key, rk)
        row.put("partd_spend_per_unit_2024", num(top.Avg_Spnd_Per_Dsg_Unt_Wghtd_2024), src, key, f"row {top.row_no}")
        row.put("partd_per_unit_chg_23_24", num(top.Chg_Avg_Spnd_Per_Dsg_Unt_23_24), src, key, f"row {top.row_no}")
        row.put("partd_per_unit_cagr_20_24", num(top.CAGR_Avg_Spnd_Per_Dsg_Unt_20_24), src, key, f"row {top.row_no}")
    q = cms("public/partd_quarterly_2025.csv.gz")
    for period, field in (("2025 (Q1-Q4)", "partd_spend_2025"), ("2026 (Q1)", "partd_spend_2026q1")):
        m = match(q[(q.Mftr_Name == "Overall") & (q.Year == period)], "Gnrc_Name")
        if len(m):
            row.put(field, round(m.Tot_Spndng.apply(num).sum(), 0), "CMS Quarterly Part D Spending",
                    "public/partd_quarterly_2025.csv.gz", f"Year={period} Overall rows {','.join(map(str, m.row_no))}")
    b = cms("public/partb_spending_dy24.csv")
    m = match(b, "Gnrc_Name")
    if len(m):
        sp = m.Tot_Spndng_2024.apply(num)
        top = m.loc[sp.fillna(-1).idxmax()]
        src, key = "CMS Part B Spending by Drug DY2024", "public/partb_spending_dy24.csv"
        row.put("partb_spend_2024", round(sp.sum(skipna=True), 0) if sp.notna().any() else None, src, key,
                f"rows {','.join(map(str, m.row_no))}")
        row.put("partb_hcpcs", top.HCPCS_Cd, src, key, f"row {top.row_no}")
        row.put("partb_asp_2024", num(top.get("Avg_DY24_ASP_Price")), src, key, f"row {top.row_no} Avg_DY24_ASP_Price")
        row.put("partb_per_unit_chg_23_24", num(top.get("Chg_Avg_Spndng_Per_Dsg_Unt_23_24")), src, key, f"row {top.row_no}")

    # IRA negotiation
    ira, fname = ira_file()
    names = {bkey(x) for x in brands}
    m = ira[ira.names.apply(lambda s: bool(s & names))]
    if len(m):
        src, key = "CMS Negotiation Program selected drug list + MFP file", "public/ira_selected_drugs_mfp.zip"
        ipay = int(m.IPAY.astype(int).min())
        mi = m[m.IPAY.astype(int) == ipay]
        row.put("ira_ipay", ipay, src, key, f"{fname} rows {mi.row_no.min()}..{mi.row_no.max()} IPAY")
        row.put("ira_selected_date", IRA_SELECTED_ON.get(ipay), "CMS selected drug announcement (IPAY date table)",
                key, f"IPAY {ipay}")
        withp = mi[mi["Single MFP per 30 DES"].notna()]
        if len(withp):
            e0 = withp.loc[withp.eff.idxmin()]
            row.put("ira_mfp_30day", num(e0["Single MFP per 30 DES"]), src, key, f"{fname} row {e0.row_no}")
            row.put("ira_mfp_effective", iso(e0.eff.date()), src, key, f"{fname} row {e0.row_no}")
            e1 = withp.loc[withp.eff.idxmax()]
            if e1.eff > e0.eff:
                row.put("ira_mfp_30day_latest", num(e1["Single MFP per 30 DES"]), src, key,
                        f"{fname} row {e1.row_no} ({e1['Type of Update']})")
                row.put("ira_mfp_latest_effective", iso(e1.eff.date()), src, key, f"{fname} row {e1.row_no}")
        elif mi.eff.notna().any():
            row.put("ira_mfp_effective", iso(mi.eff.min().date()), src, key, f"{fname} IPAY {ipay} (MFP not yet published)")
        des = m[m["Type of Update"].str.strip().str.lower() == "deselect"]
        row["ira_deselected"] = bool(len(des))
        row.cites["ira_deselected"] = (src, key, f"{fname} Type of Update=Deselect rows "
                                       f"{','.join(map(str, des.row_no)) or 'none'}", None)
        if len(des):
            ndc_all, ndc_des = set(m["NDC-11"].dropna()), set(des["NDC-11"].dropna())
            row.put("ira_deselect_date", iso(des.end.max().date()) if des.end.notna().any() else None, src, key,
                    f"{fname} row {des.row_no.iloc[0]} MFP End Date")
            row.put("ira_deselect_scope", "all NDCs" if ndc_des >= ndc_all else f"{len(ndc_des)} of {len(ndc_all)} NDCs",
                    src, key, f"{fname} Deselect rows")
            row["_ira_deselect_remark"] = str(des.Remarks.dropna().iloc[0]) if des.Remarks.notna().any() else ""
        row["_ira_inflation"] = [(iso(r.eff.date()), num(r["Single MFP per 30 DES"]), int(r.row_no))
                                 for _, r in mi[mi["Type of Update"].str.strip() == "Inflation"]
                                 .drop_duplicates("eff").iterrows() if pd.notna(r.eff)]


def classes_for(ingredient):
    c = ingredient_classes().get(str(ingredient).strip().lower()) or {}
    return c, sorted({a[0] for a in c.get("atc") or [] if len(a[0]) == 5})


# ---------------------------------------------------------------- build

def build(ciks=None, tickers=None):
    pairs = resolve(tickers or [], ciks or [])
    uni = brand_universe()
    first_all = first_word_map(uni.keys(), uni)
    rows, unmatched = [], {}
    for ticker, cik in pairs:
        name, rx = company_info(cik)
        groups = own_brands(cik, rx)
        own_first = first_word_map(groups.keys(), uni)
        rev, filing = product_revenue(cik)
        fy = int(filing["period"][:4]) if filing else None
        acc = filing["accession"] if filing else None
        xkey = f"xbrl_product/{cik}/{acc}.jsonl.gz" if acc else None
        comp_rev = company_revenue(cik, acc, fy) if acc else None

        # map revenue members to brand groups
        member_for, partner_groups, unm = {}, {}, []
        for m, years in rev.items():
            k, how = match_member(m, own_first, first_all)
            if not k:
                if years.get(fy, {}).get("total"):
                    unm.append((m, years[fy]["total"][0]))
                continue
            if how.startswith("own"):
                base = next(b for b, ks in groups.items() if k in ks)
            else:
                base = k
                ing = uni[k]["ingredient"].lower()
                partner_groups[k] = [k] + [k2 for k2, v in uni.items() if k2 != k and k2.startswith(k)
                                           and v["ingredient"].lower() == ing]
            val = (years.get(fy, {}).get("total") or (0,))[0]
            score = (how.endswith("exact"), val)
            if base not in member_for or score > member_for[base][2]:
                if base in member_for:
                    unm.append((member_for[base][0], None))
                member_for[base] = (m, how, score)
            else:
                unm.append((m, val))
        unmatched[f"{ticker} ({cik})"] = [{"member": m, f"revenue_{fy}": v} for m, v in sorted(unm, key=lambda t: -(t[1] or 0))]

        for base, keys in list(groups.items()) + list(partner_groups.items()):
            if base in partner_groups and base in groups:
                continue
            info = uni[base]
            row = Row(company=name, ticker=ticker, cik=cik, brand=info["brand"], ingredient=info["ingredient"],
                      modality=info["modality"])
            ob_key = "classes/brand_products.jsonl.gz"
            row.put("brand_group", "; ".join(uni[k]["brand"] for k in keys), "brand_products", ob_key, "brand keys")
            row.put("appl_nos", ", ".join(sorted(set().union(*(uni[k]["appls"] for k in keys)))),
                    "FDA Orange Book products.txt / Purple Book", "public/orange_book.zip",
                    f"Trade_Name/Proprietary Name in {[uni[k]['brand'] for k in keys]}")
            row.put("nda_holder", info["holder"], "FDA Orange Book / Purple Book applicant", ob_key, f"brand={info['brand']}")
            row["revenue_booker"] = name
            if base in PARTNERED:
                row.put("partner_note", PARTNERED[base], "10-K collaboration note (hand-entered)",
                        filing["storage_key"] if filing else None, "PARTNERED table in agent/product_table.py", acc)

            # revenue
            if base in member_for:
                m, how, _ = member_for[base]
                row.put("revenue_member", m, "SEC 10-K XBRL instance", xkey, how, acc)
                yrs = rev[m]
                cur, prev = yrs.get(fy, {}), yrs.get(fy - 1, {})
                if cur.get("total"):
                    row.put("revenue_fy", fy, "SEC 10-K XBRL instance", xkey, cur["total"][1], acc)
                    row.put("revenue_latest_fy", cur["total"][0], "SEC 10-K XBRL instance", xkey, cur["total"][1], acc)
                    if cur.get("us_only"):
                        row.put("revenue_scope", "US only (company tags only US sales)", "SEC 10-K XBRL instance", xkey,
                                cur["total"][1], acc)
                if prev.get("total"):
                    row.put("revenue_prior_fy", prev["total"][0], "SEC 10-K XBRL instance", xkey, prev["total"][1], acc)
                if cur.get("total") and prev.get("total") and prev["total"][0]:
                    row.put("revenue_yoy", round(cur["total"][0] / prev["total"][0] - 1, 4), "derived from XBRL",
                            xkey, f"{cur['total'][1]} / {prev['total'][1]}", acc)
                if cur.get("us") and cur.get("total") and not cur.get("us_only"):
                    row.put("revenue_us", cur["us"][0], "SEC 10-K XBRL instance", xkey, cur["us"][1], acc)
                    row.put("revenue_us_share", round(cur["us"][0] / cur["total"][0], 4), "derived from XBRL", xkey,
                            f"{cur['us'][1]} / {cur['total'][1]}", acc)
                if cur.get("total") and comp_rev:
                    row.put("pct_of_company_revenue", round(cur["total"][0] / comp_rev[0], 4), "derived from XBRL",
                            f"xbrl/{cik}.json", f"{cur['total'][1]} / {comp_rev[1]}", acc)
            if comp_rev:
                row.put("company_revenue_fy", comp_rev[0], "SEC companyfacts", f"xbrl/{cik}.json", comp_rev[1], acc)

            # LOE
            est, basis = fda_loe(row, keys, uni)
            row.put("loe_fda_estimate", iso(est), "derived (Orange/Purple Book rule, section 1)", "public/orange_book.zip",
                    basis or None)
            st = pick_stated(cik, keys, uni)
            if st:
                skey = "derived/company_stated_loe.jsonl"
                srk = f"product={st.get('product')} cik={st.get('cik')} section={st.get('section')}"
                row.put("loe_company_stated", st.get("us_loe"), "10-K text (company stated LOE)", skey, srk, st.get("accession"))
                row.put("loe_company_basis", st.get("basis"), "10-K text (company stated LOE)", skey, srk, st.get("accession"))
                row.put("loe_company_quote", (st.get("quote") or "")[:400], "10-K text (company stated LOE)", skey, srk,
                        st.get("accession"))
                row.put("loe_eu_stated", st.get("eu_loe"), "10-K text (company stated LOE)", skey, srk, st.get("accession"))
            stated_text, stated_year = parse_loe_text(st.get("us_loe")) if st else (None, None)
            cd = curve_drug(keys, uni)
            if not stated_text and cd:
                # verified US LOE year with a 10-K quote from the LOE-curve benchmark set
                ckey, crk = "derived/loe_curves.json", f"drugs[brand={cd['brand']}] loe_quote"
                row.put("loe_company_stated", str(cd["loe_year"]), "10-K text (LOE curve benchmark set)", ckey, crk,
                        cd.get("loe_accession"))
                row.put("loe_company_basis", f"10-K: loss of exclusivity in {cd['loe_year']}",
                        "10-K text (LOE curve benchmark set)", ckey, crk, cd.get("loe_accession"))
                row.put("loe_company_quote", cd.get("loe_quote", "")[:400], "10-K text (LOE curve benchmark set)", ckey,
                        crk, cd.get("loe_accession"))
                stated_text, stated_year = str(cd["loe_year"]), int(cd["loe_year"])
                st = {"basis": f"10-K: loss of exclusivity in {cd['loe_year']}", "product": cd["brand"],
                      "accession": cd.get("loe_accession")}
                srcname, srckey = "10-K text (LOE curve benchmark set)", "derived/loe_curves.json"
            else:
                srcname, srckey = "10-K text (company stated LOE)", "derived/company_stated_loe.jsonl"
            if stated_text:
                row.put("loe_best_estimate", stated_text, srcname, srckey, f"product={st.get('product')}",
                        st.get("accession"))
                row["loe_best_year"] = stated_year
                row.cites["loe_best_year"] = row.cites["loe_best_estimate"]
                row.put("loe_basis", f"company-stated ({st.get('basis')}); FDA rule says {iso(est) or 'n/a'}",
                        "10-K text + FDA rule", srckey, f"product={st.get('product')}", st.get("accession"))
            elif est:
                pre = f"company says: {st.get('basis')}; " if st and st.get("basis") else ""
                row.put("loe_best_estimate", iso(est), "derived (Orange/Purple Book rule, section 1)",
                        "public/orange_book.zip", basis)
                row["loe_best_year"] = est.year
                row.cites["loe_best_year"] = row.cites["loe_best_estimate"]
                row.put("loe_basis", pre + "FDA rule: " + basis, "derived (Orange/Purple Book rule, section 1)",
                        "public/orange_book.zip", basis)
            elif basis:
                row.put("loe_basis", basis, "derived (Orange/Purple Book rule, section 1)", "public/orange_book.zip", basis)

            pricing(row, keys, uni)
            enrich(row, keys, uni, cik)
            rows.append(row)

    for r in rows:
        risk(r)
    keep = [r for r in rows if (r.get("revenue_latest_fy") or 0) >= MIN_REVENUE or r.get("ira_ipay")
            or (r.get("loe_best_year") and LOE_WINDOW[0] <= r["loe_best_year"] <= LOE_WINDOW[1]
                and (r.get("revenue_latest_fy") or r.get("partd_spend_2024") or r.get("partb_spend_2024")))]
    keep.sort(key=lambda r: (-(r.get("revenue_latest_fy") or 0), -(r.get("partd_spend_2024") or 0)))
    for r in keep:
        competitors(r, uni)
    cols = COLUMNS + sorted({k for r in keep for k in r if not k.startswith("_")} - set(COLUMNS))
    df = pd.DataFrame([{c: r.get(c) for c in cols} for r in keep], columns=cols)
    cites = citations(keep)
    timeline = {f"{r['ticker']} | {r['brand']}": events(r) for r in keep}
    return df, cites, {"brands": timeline, "unmatched_revenue_members": unmatched,
                       "inputs_present": {"company_stated_loe": bool(stated_loe()), "loe_curves": bool(loe_curves())}}


def enrich(row, keys, uni, cik):
    info = uni[keys[0]]
    c, atc4 = classes_for(info["ingredient"])
    if atc4:
        row.put("atc4", ", ".join(atc4), "RxClass ATC", "classes/ingredient_classes.jsonl.gz",
                f"ingredient={info['ingredient'].lower()}")
        names = sorted({a[1] for a in c.get("atc") or [] if a[0] in atc4})
        row.put("atc4_name", "; ".join(names), "RxClass ATC", "classes/ingredient_classes.jsonl.gz",
                f"ingredient={info['ingredient'].lower()}")
    epc = [e[1] for e in c.get("fdaspl") or []]
    if epc:
        row.put("epc_class", "; ".join(epc[:3]), "RxClass FDA SPL EPC", "classes/ingredient_classes.jsonl.gz",
                f"ingredient={info['ingredient'].lower()}")
    lab = next((labels()[k] for k in keys if k in labels()), None)
    ind = (lab or {}).get("indications") or ""
    if ind:
        row.put("indication", re.sub(r"^\s*1 INDICATIONS AND USAGE\s*", "", ind)[:300], "openFDA drug label",
                "classes/brand_indications.jsonl.gz", f"brand={lab['brand']} set_id={lab.get('set_id')}")
    # formulary (Part D SPUF) via label RXCUIs
    f = formulary()
    rxcuis = [str(x) for x in (lab or {}).get("rxcui") or []]
    if f is not None and rxcuis:
        hit = f.loc[f.index.intersection(rxcuis)]
        if len(hit):
            best = hit.loc[hit.formularies.idxmax()]
            rk = f"RXCUI={best.name} (max formularies of {len(hit)} label RXCUIs)"
            src, key = "CMS Part D formulary (SPUF) summary", "formulary/rxcui_summary.csv.gz"
            row.put("formulary_coverage_share", num(best.coverage_share), src, key, rk)
            row.put("formulary_tier_median", num(best.tier_median), src, key, rk)
            row.put("formulary_prior_auth_share", num(best.prior_auth_share), src, key, rk)
            row.put("formulary_step_therapy_share", num(best.step_therapy_share), src, key, rk)
    # pipeline
    trials = trials_for(cik)
    if trials is not None:
        ing = re.findall(r"[a-z]+", info["ingredient"].lower())
        mol = [w for w in ing[:1] if len(w) >= 5] + [info["brand"].lower()]
        terms = [t for t in AREA_TERMS if t in ind.lower()]
        same_mol = {t["nct"] for t in trials if any(x in t["interventions"] for x in mol)}
        same_area = {t["nct"] for t in trials if terms and any(x in t["conditions"] for x in terms)}
        key = f"trials/{cik}.jsonl.gz"
        row.put("phase3_active_same_molecule", len(same_mol), "ClinicalTrials.gov v2", key,
                f"active Phase 3, intervention mentions {mol}")
        if terms:
            row.put("phase3_active_same_area", len(same_area), "ClinicalTrials.gov v2", key,
                    f"active Phase 3, condition mentions {terms[:8]}")
            row.put("phase3_area_terms", ", ".join(terms[:8]), "label indication keyword match",
                    "classes/brand_indications.jsonl.gz", f"brand={lab['brand']}")


@lru_cache(None)
def _trials(cik):
    rows = _jsonl(f"trials/{cik}.jsonl.gz")
    if not rows:
        return None
    out = []
    for s in rows:
        p = s.get("protocolSection", {})
        phases = p.get("designModule", {}).get("phases") or []
        status = p.get("statusModule", {}).get("overallStatus")
        if "PHASE3" not in phases or status not in ACTIVE_STATUSES:
            continue
        cond = " ".join((p.get("conditionsModule", {}).get("conditions") or []) +
                        (p.get("conditionsModule", {}).get("keywords") or [])).lower()
        iv = " ".join(i.get("name", "") for i in p.get("armsInterventionsModule", {}).get("interventions") or []).lower()
        out.append({"nct": p.get("identificationModule", {}).get("nctId"), "conditions": cond,
                    "interventions": iv + " " + p.get("identificationModule", {}).get("briefTitle", "").lower()})
    return tuple(out)


def trials_for(cik):
    return _trials(cik)


def curve_drug(keys, uni):
    c = loe_curves()
    names = {bkey(uni[k]["brand"]) for k in keys}
    return next((d for d in (c or {}).get("drugs") or [] if bkey(d["brand"]) in names and d.get("loe_year")), None)


def curve_pct(modality):
    """Median pct-of-peak by year since LOE, same shaping as agent.loe_curves.revenue_at_risk: running minimum,
    stop at the first missing year, held flat beyond the last point. Fractions (1.0 = peak)."""
    c = ((loe_curves() or {}).get("curves") or {}).get(modality)
    pct, floor = [], 100.0
    for v in (c or {}).get("pct_of_peak") or []:
        if v is None:
            break
        floor = min(floor, float(v))
        pct.append(floor / 100)
    return pct


def risk(row):
    """Revenue lost FY+1..2030 vs holding latest-FY revenue flat. LOE in the future: base = latest FY revenue (taken as
    the pre-LOE run-rate) eroding along the curve. LOE already passed: latest FY revenue is already eroded, so only
    the further decline from the curve position at FY is counted."""
    y, rev = row.get("loe_best_year"), row.get("revenue_latest_fy")
    modality = "biologic" if row.get("modality") == "biologic" else "small_molecule"
    pct = curve_pct(modality)
    if not (pct and y and rev):
        return
    fy = row.get("revenue_fy") or TODAY.year - 1
    p = lambda yr: 1.0 if yr < y else pct[min(yr - y, len(pct) - 1)]
    base = p(fy)
    lost = sum(rev * max(0.0, 1 - p(yr) / base) for yr in range(fy + 1, HORIZON + 1))
    row.put("revenue_at_risk_through_2030", round(lost, 0), "derived: revenue x (1 - LOE curve)",
            "derived/loe_curves.json", f"{modality} median curve, LOE year {y}, base FY{fy} revenue, years {fy + 1}-{HORIZON}")


def competitors(row, uni):
    atc = set((row.get("atc4") or "").split(", ")) - {""}
    if not atc:
        return
    own_ing = row["ingredient"].lower()
    d = cms("public/partd_spending_dy24.csv")
    spend = d[d.Mftr_Name == "Overall"].groupby(d.Brnd_Name.fillna("").apply(bkey)).Tot_Spndng_2024.apply(
        lambda s: s.apply(num).sum())
    b = cms("public/partb_spending_dy24.csv")
    spend_b = b.groupby(b.Brnd_Name.fillna("").apply(bkey)).Tot_Spndng_2024.apply(lambda s: s.apply(num).sum())
    out = []
    for k, v in uni.items():
        ing = v["ingredient"].lower()
        if ing == own_ing or ing.split(";")[0].split("-")[0].strip() == own_ing.split(";")[0].strip():
            continue
        _, a4 = classes_for(v["ingredient"])
        if not (set(a4) & atc):
            continue
        sp = float(spend.get(k, 0) or 0) + float(spend_b.get(k, 0) or 0)
        out.append((sp, k, v))
    out.sort(key=lambda t: -t[0])
    comp = []
    for sp, k, v in out[:6]:
        tmp = Row()
        est, _ = fda_loe(tmp, [k], uni)
        st = pick_stated(v["holder_cik"], [k], uni)
        stated = parse_loe_text(st.get("us_loe"))[0] if st else None
        comp.append({"brand": v["brand"], "ingredient": v["ingredient"], "holder": v["holder"],
                     "medicare_spend_2024": round(sp) if sp else None, "loe": stated or iso(est),
                     "loe_source": "10-K stated" if stated else "FDA rule" if est else None})
    row.put("competitors", json.dumps(comp), "derived: same ATC level-4 class, ranked by Medicare spend",
            "classes/ingredient_classes.jsonl.gz", f"ATC4 {sorted(atc)}; LOE per competitor from Orange/Purple Book or 10-K")


COLUMNS = ["company", "ticker", "cik", "brand", "brand_group", "ingredient", "modality", "appl_nos", "nda_holder",
           "revenue_booker", "partner_note", "revenue_member", "revenue_fy", "revenue_latest_fy", "revenue_prior_fy",
           "revenue_yoy", "revenue_us", "revenue_us_share", "revenue_scope", "company_revenue_fy",
           "pct_of_company_revenue", "loe_best_estimate", "loe_best_year", "loe_basis", "loe_company_stated",
           "loe_company_basis", "loe_eu_stated", "loe_fda_estimate", "loe_orange_book_substance",
           "loe_last_listed_patent", "exclusivity_latest_code", "exclusivity_latest_date", "pb_ref_exclusivity",
           "pb_orphan_exclusivity", "piv_first_submission", "piv_anda_count", "piv_180day_status",
           "piv_first_generic_marketing", "piv_last_qualifying_patent", "generic_anda_holders_count",
           "generic_first_anda_approval", "biosimilar_count", "interchangeable_flag", "biosimilar_first_approval",
           "partd_spend_2024", "partd_spend_per_unit_2024", "partd_per_unit_chg_23_24", "partd_per_unit_cagr_20_24",
           "partd_spend_2025", "partd_spend_2026q1", "partb_spend_2024", "partb_hcpcs", "partb_asp_2024",
           "partb_per_unit_chg_23_24", "ira_ipay", "ira_selected_date", "ira_mfp_30day", "ira_mfp_effective",
           "ira_mfp_30day_latest", "ira_mfp_latest_effective", "ira_deselected", "ira_deselect_date",
           "ira_deselect_scope", "revenue_at_risk_through_2030", "atc4", "atc4_name", "epc_class", "competitors",
           "formulary_coverage_share", "formulary_tier_median", "formulary_prior_auth_share",
           "formulary_step_therapy_share", "phase3_active_same_molecule", "phase3_active_same_area",
           "phase3_area_terms", "indication", "loe_company_quote"]


def citations(rows):
    out = []
    for r in rows:
        for field, (src, key, rk, acc) in r.cites.items():
            v = r.get(field)
            if v is None:
                continue
            out.append({"fact_id": f"{r['cik']}:{bkey(r['brand'])}:{field}", "company": r["company"], "brand": r["brand"],
                        "field": field, "value": v, "source_name": src, "url_or_key": key, "row_key": rk,
                        "accession": acc})
    return out


def events(r):
    ev = []
    add = lambda d, e, s: ev.append({"date": d, "event": e, "source": s}) if d else None
    add(r.get("piv_first_submission"), f"First Paragraph IV ANDA submitted ({r.get('piv_anda_count')} ANDAs to date)",
        "public/paragraph_iv.xlsx")
    add(r.get("piv_first_generic_marketing"), "First-filer generic commercial marketing", "public/paragraph_iv.xlsx")
    add(r.get("generic_first_anda_approval"), "First ANDA (generic) approval listed in Orange Book", "public/orange_book.zip")
    add(r.get("ira_selected_date"), f"Selected for Medicare negotiation (IPAY {r.get('ira_ipay')})",
        "public/ira_selected_drugs_mfp.zip")
    if r.get("ira_mfp_effective"):
        mfp = f" at ${r['ira_mfp_30day']:,.2f} per 30 days" if r.get("ira_mfp_30day") else " (price not yet published)"
        add(r["ira_mfp_effective"], "Medicare maximum fair price takes effect" + mfp, "public/ira_selected_drugs_mfp.zip")
    for d, p, rn in r.get("_ira_inflation") or []:
        if d != r.get("ira_mfp_effective"):
            add(d, f"MFP inflation update to ${p:,.2f} per 30 days", f"public/ira_selected_drugs_mfp.zip row {rn}")
    if r.get("ira_deselected"):
        add(r.get("ira_deselect_date"), f"Deselected from negotiation, MFP ends ({r.get('ira_deselect_scope')}; "
            f"{r.get('_ira_deselect_remark', '')[:120]})", "public/ira_selected_drugs_mfp.zip")
    add(r.get("loe_fda_estimate"), "Estimated LOE from FDA patent/exclusivity rule", "public/orange_book.zip")
    if r.get("loe_company_stated"):
        d, _ = parse_loe_text(r["loe_company_stated"])
        add(d, f"Company-stated US LOE ({r.get('loe_company_basis', '')[:100]})", "derived/company_stated_loe.jsonl")
    add(r.get("loe_orange_book_substance"), "Drug-substance patent expires (Orange Book)", "public/orange_book.zip")
    add(r.get("pb_ref_exclusivity"), "Biologic 12-year reference exclusivity ends (Purple Book)",
        "public/purple_book_2026_09.csv")
    for d, n, rn in r.get("_biosimilars") or []:
        add(d, f"Biosimilar {n} approved", f"public/purple_book_2026_09.csv row {rn}")
    return sorted(ev, key=lambda e: str(e["date"]))


# ---------------------------------------------------------------- CLI

def summarize(df):
    show = ["ticker", "brand", "revenue_latest_fy", "revenue_yoy", "loe_best_estimate", "ira_ipay", "ira_mfp_30day",
            "ira_deselected", "partd_spend_2024", "biosimilar_count", "generic_anda_holders_count"]
    s = df[show].copy()
    s["revenue_latest_fy"] = (s.revenue_latest_fy / 1e9).round(2)
    s["partd_spend_2024"] = (s.partd_spend_2024 / 1e9).round(2)
    return s.rename(columns={"revenue_latest_fy": "rev_$B", "partd_spend_2024": "partD24_$B"}).to_string(index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tickers", default="")
    ap.add_argument("--ciks", default="")
    ap.add_argument("--no-upload", action="store_true", help="write to data/product_table/ instead of R2")
    a = ap.parse_args()
    tickers = [t.strip() for t in a.tickers.split(",") if t.strip()]
    ciks = [int(c) for c in a.ciks.split(",") if c.strip()]
    df, cites, tl = build(ciks=ciks, tickers=tickers)
    tag = "_".join(tickers + [str(c) for c in ciks])
    files = {f"derived/product_table/{tag}.csv": df.to_csv(index=False).encode(),
             f"derived/product_table/{tag}_citations.jsonl": "\n".join(json.dumps(c, default=str) for c in cites).encode(),
             f"derived/product_table/{tag}_timeline.json": json.dumps(tl, indent=1, default=str).encode()}
    for k, v in files.items():
        if a.no_upload or store.kind != "r2":
            p = Path(__file__).resolve().parent.parent / "data" / k
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(v)
        else:
            store.put(k, v, "text/csv" if k.endswith(".csv") else "application/json")
        print(f"wrote {k} ({len(v):,} bytes)")
    print(f"{len(df)} rows, {len(cites)} citations; inputs present: {tl['inputs_present']}")
    print(summarize(df))
    for c, u in tl["unmatched_revenue_members"].items():
        print(f"unmatched revenue members {c}: {len(u)} (top: {[x['member'] for x in u[:6]]})")


if __name__ == "__main__":
    main()
