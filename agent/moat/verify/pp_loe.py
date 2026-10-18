"""Pipeline verifier item 5: loe_calendar.csv.

1. Every row with a company-stated date: find the quote in the company's page-marked 10-K (data/corpus), record the
   page, confirm the stated date is in the quote and the brand is named; reconcile with agent/cache/company_stated_loe.jsonl.
2. Orange Book rule dates: flag rule dates that come from one strength's (or another formulation's) first generic.
3. Biologics: fill rule_output_loe with BLA approval + 12 years from the Purple Book, method labelled.
Usage: python -m agent.moat.verify.pp_loe [--write]
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import log_wrong, norm, pages

C = Path("data/moat/verify/pp_cache")
l = pd.read_csv("data/moat/tables/loe_calendar.csv")
TENK = {t: f"data/corpus/companies/{t}/10k_FY2025.md" for t in
        ["ABBV", "AMGN", "BMY", "GILD", "JNJ", "LLY", "MRK", "PFE", "AZN", "NVO"]}
TENK["REGN"] = "data/corpus/peers/REGN/10k_FY2025.md"
CIK2T = {14272: "BMY", 78003: "PFE", 200406: "JNJ", 59478: "LLY", 318154: "AMGN", 872589: "REGN", 310158: "MRK",
         1551152: "ABBV", 882095: "GILD", 1860742: "BLCO"}


def loose(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", norm(s).lower()).split())


def find_page(path, quote):
    if not path or not Path(path).exists() or not isinstance(quote, str):
        return None, "no 10-K text"
    q = loose(quote)
    pg = pages(path)
    lp = {n: loose(t) for n, (_, t) in pg.items()}
    for n, t in lp.items():
        if q in t:
            return n, "verbatim"
    # quote may straddle a page break
    keys = sorted(lp)
    for a, b in zip(keys, keys[1:]):
        if q in lp[a] + " " + lp[b]:
            return a, "verbatim (spans page break)"
    head, tail = q[:90], q[-90:]
    for n, t in lp.items():
        if head in t:
            return n, "head only (quote truncated or edited)"
    for n, t in lp.items():
        if tail in t:
            return n, "tail only"
    return None, "not found"


def date_tokens(s):
    s = str(s)
    toks = re.findall(r"\b(?:19|20)\d{2}\b", s)
    toks += re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)", s)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        toks = [m.group(3)]
    return toks


stated = pd.DataFrame([json.loads(x) for x in open("agent/cache/company_stated_loe.jsonl")])
stated["k"] = stated["product"].map(lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", str(s)).lower()))

# ---- 1. stated dates
res = []
for i, r in l.iterrows():
    if pd.isna(r.company_stated_loe):
        continue
    tk = r.ticker if isinstance(r.ticker, str) else CIK2T.get(int(r.cik))
    path = TENK.get(tk)
    page, how = find_page(path, r.quote)
    q = norm(str(r.quote)).lower()
    dt = date_tokens(r.company_stated_loe)
    date_in = all(t.lower() in q for t in dt) if dt else False
    brand = re.sub(r"\(.*?\)", "", str(r.brand)).strip().lower()
    first = brand.split()[0] if brand else ""
    brand_in = first in q or str(r.ingredient).lower().split()[0] in q
    k = re.sub(r"[^a-z0-9]", "", brand)
    s = stated[(stated.cik == int(r.cik)) & (stated.k == k)]
    col = {"US": "us_loe", "EU": "eu_loe", "Japan": "japan_loe"}[r.territory]
    sv = s[col].dropna().tolist() if len(s) else []
    agree = None if not len(s) else (str(r.company_stated_loe) in [str(x) for x in sv] or
                                     any(str(x) in str(r.company_stated_loe) or str(r.company_stated_loe) in str(x) for x in sv))
    res.append(dict(idx=i, ticker=tk, brand=r.brand, territory=r.territory, stated=r.company_stated_loe,
                    tenk_page=page, quote_match=how, date_in_quote=date_in, brand_in_quote=brand_in,
                    jsonl_rows=len(s), jsonl_value="; ".join(map(str, sv)), jsonl_agrees=agree))
R = pd.DataFrame(res)
R.to_csv(C / "loe_stated_checks.csv", index=False)
print("stated rows", len(R), "US", (R.territory == "US").sum())
print(R.quote_match.value_counts().to_dict())
us = R[R.territory == "US"]
print("US: date in quote", us.date_in_quote.sum(), "brand in quote", us.brand_in_quote.sum(), "page found",
      us.tenk_page.notna().sum(), "jsonl agree", us.jsonl_agrees.value_counts(dropna=False).to_dict())

# ---- 2. Orange Book strength / formulation check
zf = zipfile.ZipFile(C / "orange_book.zip")
prod = pd.read_csv(zf.open("products.txt"), sep="~", dtype=str)
prod["appr"] = pd.to_datetime(prod.Approval_Date, format="%b %d, %Y", errors="coerce")
ob = []
for i, r in l[(l.territory == "US") & (l.modality == "small molecule") & l.rule_output_loe.notna()].iterrows():
    br = prod[(prod.Appl_Type == "N") & (prod.Trade_Name.str.upper() == str(r.brand).upper().split(" (")[0])]
    if br.empty:
        continue
    rule = pd.Timestamp(r.rule_output_loe)
    brand_appr = br.appr.min()
    ing, dfr = set(br.Ingredient), set(br["DF;Route"])
    an = prod[(prod.Appl_Type == "A") & prod.Ingredient.isin(ing) & prod["DF;Route"].isin(dfr)]
    flag = []
    if pd.notna(brand_appr) and rule < brand_appr:
        flag.append(f"rule date {rule.date()} predates the brand's own NDA approval {brand_appr.date()}: generic of "
                    "an older product with the same ingredient and form")
    bstr = set(br.Strength.str.upper())
    if len(an):
        firsts = an.groupby(an.Strength.str.upper()).appr.min()
        at_rule = an[an.appr <= rule + pd.Timedelta(days=1)]
        covered = set(at_rule.Strength.str.upper()) & bstr
        from_anda = (an.appr - rule).abs().min() <= pd.Timedelta(days=1)
        if from_anda:
            missing = bstr - covered
            if covered and missing:
                late = {s: (firsts.get(s).date().isoformat() if s in firsts and pd.notna(firsts.get(s)) else "none")
                        for s in sorted(missing)}
                flag.append(f"rule date = first ANDA for strength(s) {sorted(covered)} only; other brand strengths "
                            f"first ANDA: {late}")
    ob.append(dict(idx=i, ticker=r.ticker, brand=r.brand, rule=r.rule_output_loe, brand_nda_approval=brand_appr,
                   n_anda=len(an), flag="; ".join(flag)))
OB = pd.DataFrame(ob)
OB.to_csv(C / "loe_ob_checks.csv", index=False)
print("OB checked", len(OB), "flagged", (OB.flag != "").sum())
print(OB[OB.flag != ""][["ticker", "brand", "rule", "flag"]].to_string()[:3000])

# ---- 3. biologics: BLA approval + 12y
raw = (C / "purple_book.csv").read_text(errors="ignore").splitlines()
hdr = [i for i, x in enumerate(raw) if x.startswith("N/R/U,Applicant,BLA Number")]
frames = []
for j, h in enumerate(hdr):
    end = hdr[j + 1] - 3 if j + 1 < len(hdr) else len(raw)
    frames.append(pd.read_csv(io.StringIO("\n".join(raw[h:end])), dtype=str, on_bad_lines="skip"))
pb = pd.concat(frames).drop_duplicates(["BLA Number", "Proprietary Name", "Approval Date"])
pb["appr"] = pd.to_datetime(pb["Approval Date"], errors="coerce")
pb["first_lic"] = pd.to_datetime(pb["Date of First Licensure"], errors="coerce")
pb["name_u"] = pb["Proprietary Name"].str.upper().str.strip()
a351 = pb[pb["License Type"].str.startswith("351(a)", na=False)]
print("purple book rows", len(pb), "351(a)", len(a351))
bio = []
for i, r in l[(l.territory == "US") & (l.modality == "biologic")].iterrows():
    nm = str(r.brand).upper().split(" (")[0].strip()
    hit = a351[a351.name_u == nm]
    if hit.empty:
        bio.append(dict(idx=i, brand=r.brand, bla=None, approval=None, rule12=None, method="no 351(a) row in Purple Book export"))
        continue
    d0 = hit.first_lic.min() if hit.first_lic.notna().any() else hit.appr.min()
    if pd.isna(d0):
        bio.append(dict(idx=i, brand=r.brand, bla=hit["BLA Number"].iloc[0], approval=None, rule12=None,
                        method="Purple Book row has no approval date"))
        continue
    r12 = (d0 + pd.DateOffset(years=12)).date().isoformat()
    pbx = r.purple_book_ref_exclusivity
    bio.append(dict(idx=i, brand=r.brand, bla=hit["BLA Number"].iloc[0], approval=d0.date().isoformat(), rule12=r12,
                    pb_excl=pbx, agrees_pb=(None if pd.isna(pbx) else r12 == str(pbx)),
                    method="BLA first licensure (Purple Book) + 12 years, 42 USC 262(k)(7); upper bound if settlements allow earlier entry"))
B = pd.DataFrame(bio)
B.to_csv(C / "loe_bio_checks.csv", index=False)
print("biologic US rows", len(B), "filled", B.rule12.notna().sum(), "pb agree", B.get("agrees_pb", pd.Series()).value_counts(dropna=False).to_dict())

if "--write" in sys.argv:
    out = l.copy()
    out["rule_method"] = None
    out.loc[out.rule_output_loe.notna(), "rule_method"] = "product_table Orange/Purple Book rule (collector)"
    out["tenk_page"] = None
    out["verify_status"] = None
    out["verify_note"] = ""
    for r in R.itertuples():
        st = "pass" if (r.tenk_page is not None and not pd.isna(r.tenk_page) and r.date_in_quote and r.brand_in_quote
                        and r.quote_match.startswith("verbatim")) else "check"
        note = [f"quote {r.quote_match}"]
        if not r.date_in_quote:
            note.append("stated date not in quote")
        if not r.brand_in_quote:
            note.append("brand not named in quote")
        if r.jsonl_agrees is False:
            note.append(f"company_stated_loe.jsonl says {r.jsonl_value}")
        out.at[r.idx, "tenk_page"] = r.tenk_page
        out.at[r.idx, "verify_status"] = st
        out.at[r.idx, "verify_note"] = "; ".join(note)
    for r in OB[OB.flag != ""].itertuples():
        out.at[r.idx, "verify_note"] = (out.at[r.idx, "verify_note"] + "; rule date flag: " + r.flag).strip("; ")
        out.at[r.idx, "rule_method"] = "product_table rule (FLAGGED: see verify_note)"
    for r in B[B.rule12.notna()].itertuples():
        old = out.at[r.idx, "rule_output_loe"]
        if pd.notna(old) and str(old) != r.rule12:
            out.at[r.idx, "verify_note"] = (out.at[r.idx, "verify_note"] +
                                            f"; collector rule {old} replaced (first biosimilar approval is not LOE)").strip("; ")
        out.at[r.idx, "rule_output_loe"] = r.rule12
        out.at[r.idx, "rule_method"] = r.method + f" (BLA {r.bla}, licensed {r.approval})"
    out.loc[out.verify_status.isna(), "verify_status"] = "not_stated"
    write("verify_pipeline", "verified/pipeline/loe_calendar.csv", out.to_csv(index=False), group="pipeline",
          doc_type="table", quality="verified", source_url="data/corpus 10-K FY2025; FDA Orange Book; FDA Purple Book")
    print(out.verify_status.value_counts().to_dict())
