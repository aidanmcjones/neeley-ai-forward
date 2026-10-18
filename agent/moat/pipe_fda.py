"""tables/fda_calendar.csv: Drugs@FDA actions 2025-26, PDUFA statements in filings and calls, Purple Book biosimilars."""
import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from agent.moat.common import write, note_gap
from agent.tenk import Store

S = Store()
SC = Path("data/moat/scratch/pipeline")
rows = []

# ---------------------------------------------------------------- case ingredients
frames = [pd.read_csv(io.BytesIO(S.get(f"derived/product_table/{n}.csv")))
          for n in ["BMY_PFE_JNJ", "LLY_AMGN_REGN", "MRK_BMY_ABBV"]]
pt = pd.concat(frames).drop_duplicates(["cik", "brand"])
ings = {}
for r in pt.itertuples():
    for w in re.split(r"[,;/ ]+and |[,;/]", str(r.ingredient).lower()):
        w = w.strip()
        if len(w) > 4 and w != "nan":
            ings[w] = (r.ticker, r.brand)
extra = ["semaglutide", "tirzepatide", "orforglipron", "retatrutide", "survodutide", "cagrilintide", "tafamidis",
         "acoramidis", "vutrisiran", "lenacapavir", "cabotegravir", "enlicitide", "olezarsen", "obicetrapib",
         "milvexian", "asundexian", "abelacimab", "ivonescimab", "datopotamab", "sacituzumab", "zongertinib"]
for e in extra:
    ings.setdefault(e, (None, None))

# ---------------------------------------------------------------- A. Drugs@FDA
z = zipfile.ZipFile(io.BytesIO(S.get("public/drugsatfda.zip")))
sub = pd.read_csv(z.open("Submissions.txt"), sep="\t", encoding="latin1", dtype=str, on_bad_lines="skip")
prod = pd.read_csv(z.open("Products.txt"), sep="\t", encoding="latin1", dtype=str, on_bad_lines="skip")
app = pd.read_csv(z.open("Applications.txt"), sep="\t", encoding="latin1", dtype=str, on_bad_lines="skip")
cls = pd.read_csv(z.open("SubmissionClass_Lookup.txt"), sep="\t", encoding="latin1", dtype=str, on_bad_lines="skip")
print(cls.columns.tolist())
sub["date"] = pd.to_datetime(sub.SubmissionStatusDate, errors="coerce")
sub = sub[sub.date >= "2025-01-01"]
pg = prod.groupby("ApplNo").agg(drug=("DrugName", "first"), ingredient=("ActiveIngredient", "first")).reset_index()
m = sub.merge(pg, on="ApplNo").merge(app, on="ApplNo", how="left").merge(
    cls, left_on="SubmissionClassCodeID", right_on=cls.columns[0], how="left")
m["ing"] = m.ingredient.str.lower().fillna("")
hit = m[m.ing.apply(lambda x: any(k in x for k in ings))]
for r in hit.itertuples():
    k = next(k for k in ings if k in r.ing)
    desc = getattr(r, cls.columns[1], None) if len(cls.columns) > 1 else None
    if desc in ("LABELING", "REMS", "MANUF (CMC)", "BIOEQUIV"):
        continue
    rows.append(dict(source_type="Drugs@FDA submission", ticker=ings[k][0], sponsor=r.SponsorName, drug=r.drug,
                     ingredient=r.ingredient, action=f"{r.SubmissionType} {r.SubmissionNo} ({desc})",
                     status={"AP": "approved", "TA": "tentative approval"}.get(r.SubmissionStatus, r.SubmissionStatus),
                     date=r.date.date().isoformat(), review_priority=r.ReviewPriority, quote=r.SubmissionsPublicNotes,
                     doc=None, page=None, source="R2 public/drugsatfda.zip Submissions.txt",
                     source_row=f"{r.ApplNo}:{r.SubmissionType}:{r.SubmissionNo}"))
print("daf rows", len(rows))
note_gap("pipeline", None, "fda_calendar.pending_submissions",
         "Drugs@FDA lists only acted-on submissions (AP/TA); pending applications are not public, PDUFA dates come from company text")

# ---------------------------------------------------------------- B. Purple Book 351(k)
pb = pd.read_csv(SC / "pb_raw.csv", header=None, dtype=str, skiprows=4)
pb = pb.iloc[:, :14]
pb.columns = ["flag", "applicant", "bla", "brand", "proper", "license", "strength", "form", "route", "pres", "mkt", "lic", "x", "y"]
bs = pb[pb.license.fillna("").str.contains("351\\(k\\)")]
case_bio = {}
for r in pt[pt.modality.astype(str).str.contains("bio", case=False)].itertuples():
    case_bio[str(r.ingredient).lower().split(",")[0].strip()] = (r.ticker, r.brand)
for r in bs.itertuples():
    base = str(r.proper).lower().split("-")[0]
    ref = case_bio.get(base) or next((v for k, v in case_bio.items() if base[:8] and base[:8] in k), None)
    if ref:
        rows.append(dict(source_type="Purple Book biosimilar (351(k))", ticker=ref[0], sponsor=r.applicant, drug=r.brand,
                         ingredient=r.proper, action=f"biosimilar of {ref[1]}; {r.license}",
                         status=f"{r.mkt}; monthly report flag {r.flag}", date=r.lic, quote=None, doc=None, page=None,
                         source="R2 public/purple_book_2026_09.csv", source_row=f"BLA{r.bla}:{r.brand}"))
# first biosimilar approval per case biologic from the product table
for r in pt.itertuples():
    if pd.notna(r.biosimilar_first_approval):
        rows.append(dict(source_type="Purple Book biosimilar summary", ticker=r.ticker, sponsor=None, drug=r.brand,
                         ingredient=r.ingredient, action=f"{r.biosimilar_count} biosimilar(s) licensed; interchangeable={r.interchangeable_flag}",
                         status="licensed", date=r.biosimilar_first_approval, quote=None,
                         source="R2 derived/product_table (Purple Book rule output)", source_row=f"{r.cik}:{r.brand}"))
print("with purple", len(rows))

# ---------------------------------------------------------------- C. PDUFA statements in filings and calls
PAT = re.compile(r"PDUFA|target action date|regulatory decision|FDA decision|action date|goal date", re.I)
YR = re.compile(r"\b(2025|2026|2027)\b")
PG = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")


def recent(path):
    n = path.name
    m_ = re.match(r"(\d{4})-(\d\d)", n)
    if m_:
        return m_.group(1) >= "2025"
    if re.search(r"10q_2025Q[23]|10k_FY202[45]|20f_FY202[45]|10q_2026", n):
        return True
    return False


files = [p for base in ("data/moat/companies", "data/corpus/companies", "data/corpus/peers")
         for p in Path(base).rglob("*.md") if recent(p) and "proxy" not in p.name]
print("files", len(files))
seen = set()
for p in files:
    tk = p.relative_to(p.parents[len(p.parts) - 1]).parts if False else None
    parts = p.parts
    tk = parts[parts.index("companies") + 1] if "companies" in parts else parts[parts.index("peers") + 1]
    txt = p.read_text(errors="ignore")
    marks = [(m_.start(), m_.group(1)) for m_ in PG.finditer(txt)]
    for m_ in PAT.finditer(txt):
        a, b = max(0, m_.start() - 250), min(len(txt), m_.end() + 250)
        q = " ".join(txt[a:b].split())
        if not YR.search(q):
            continue
        if re.search(r"drug user fee|reauthoriz", q, re.I):
            continue
        sig = (tk, q[100:160])
        if sig in seen:
            continue
        seen.add(sig)
        pgno = None
        for pos, n in marks:
            if pos <= m_.start():
                pgno = n
        dts = re.findall(r"(?:Q[1-4]|first half|second half|H[12]|(?:January|February|March|April|May|June|July|August|September|October|November|December)(?: \d{1,2},)?) ?(?:of )?(?:2025|2026|2027)", q)
        rows.append(dict(source_type="PDUFA / decision statement in company text", ticker=tk, sponsor=tk, drug=None,
                         ingredient=None, action=m_.group(0), status="stated", date="; ".join(dict.fromkeys(dts)) or None,
                         quote=q, doc=str(p), page=pgno, source=str(p), source_row=f"{p.name}#p{pgno}"))
df = pd.DataFrame(rows)
print(df.source_type.value_counts().to_dict())
write("pipeline", "tables/fda_calendar.csv", df.to_csv(index=False), group="pipeline", doc_type="table",
      source_url="R2 public/drugsatfda.zip; public/purple_book_2026_09.csv; data/moat/companies")
