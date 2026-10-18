"""Wave 3: apply Purple Book reference corrections, licensure dates, PDUFA relocations and fragment lists to
verified/pipeline/fda_calendar.csv."""
import re, shutil
import pandas as pd
from agent.moat.common import write, OUT
from agent.moat.verify.pe_lib import ROOT, norm, pages

V = OUT / "verified/pipeline"
if not (V / "fda_calendar_wave2.csv").exists():
    shutil.copy(V / "fda_calendar.csv", V / "fda_calendar_wave2.csv")
f = pd.read_csv(V / "fda_calendar_wave2.csv")
r = pd.read_csv(OUT / "tables/fda_calendar_rechecks.csv")
PB = "https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/2026/purplebook-search-September-data-download.csv"


def loose(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", norm(s).lower()).split())


def page_text(doc, page):
    pg = pages(doc)
    return loose(pg.get(page, ("", ""))[1]) + " " + loose(pg.get(page + 1, ("", ""))[1])


def fragments(quote, txt, minw=6):
    """Greedy maximal verbatim word runs of the quote found in txt (at least minw words)."""
    w = loose(re.sub(r"\[\[page[^\]]*\]\]", " ", str(quote))).split()
    out, i, covered = [], 0, 0
    while i < len(w):
        j = i + minw
        if j > len(w) or " ".join(w[i:j]) not in txt:
            i += 1; continue
        while j < len(w) and " ".join(w[i:j + 1]) in txt:
            j += 1
        out.append(" ".join(w[i:j])); covered += j - i; i = j
    return out, covered / max(len(w), 1)


f["licensure_date"] = pd.NA
f["reference_product_purple_book"] = pd.NA
pbr = r[r.check.str.startswith("purplebook")].drop_duplicates("row_key")
ex = pbr.note.str.extract(r"Purple Book: [^/]+/ ref ([^/]+?) / .*approval ([A-Z][a-z]+ \d{1,2}, \d{4})")
pbr = pbr.assign(pb_ref=ex[0], pb_date=pd.to_datetime(ex[1], format="%B %d, %Y", errors="coerce"))
fixes = 0
for _, x in pbr.iterrows():
    key = x.row_key.split(":", 1)[1]
    m = (f.source_row == key) & f.source_type.str.startswith("Purple Book biosimilar (351")
    f.loc[m, "licensure_date"] = None if pd.isna(x.pb_date) else x.pb_date.strftime("%Y-%m-%d")
    f.loc[m, "reference_product_purple_book"] = x.pb_ref
    if x.result == "fail":
        ref_brand = x.pb_ref.split(" (")[0].upper()
        old = f.loc[m, "action"].iloc[0]
        f.loc[m, "action"] = f.loc[m, "action"].str.replace(r"biosimilar of [A-Z]+", f"biosimilar of {ref_brand}", regex=True)
        f.loc[m, "verify_status"] = "corrected"
        f.loc[m, "verify_note"] = f"reference product corrected from '{old.split(';')[0]}' to Purple Book '{x.pb_ref}' ({PB})"
        fixes += int(m.sum())
    else:
        f.loc[m, "verify_status"] = "pass"
        f.loc[m, "verify_note"] = f"Purple Book Sept 2026: reference, name, BLA match; licensure {f.loc[m, 'licensure_date'].iloc[0]}"
# openFDA re-check of 60 Drugs@FDA actions (kept in its own column so exposure_not_sponsor stays visible)
f["openfda_check"] = pd.NA
for _, x in r[r.check.str.startswith("drugsfda")].iterrows():
    m = (f.source_row == x.row_key.split(":", 1)[1]) & (f.source_type == "Drugs@FDA submission")
    f.loc[m, "openfda_check"] = f"{x.result}: {x.note} ({x.source_url})"
    f.loc[m & (f.verify_status == "unverified"), "verify_status"] = x.result
# PDUFA: fragments and relocations
pd_r = r[r.check == "pdufa_quote_search_other_docs"]
conf = {"fragments": 0, "relocated": 0, "reloc_failed": 0}
f["quote_fragments"] = pd.NA
for _, x in pd_r.iterrows():
    i = int(re.search(r"csvrow(\d+)", x.row_key).group(1))
    row = f.loc[i]
    if x.result == "relocated_partial":
        newdoc = x.source_url
        newpage = int(re.search(r"page (\d+) \(cited", x.note).group(1))
        frs, cov = fragments(row.quote, page_text(newdoc, newpage))
        if cov >= 0.6:
            f.loc[i, "verify_note"] = (f"re-pointed from {row.doc} p{int(row.page)} to {newdoc} p{newpage}; "
                                       f"{cov:.0%} of quote words in verbatim runs there")
            f.loc[i, "doc"], f.loc[i, "page"], f.loc[i, "source"] = newdoc, newpage, newdoc
            f.loc[i, "verify_status"] = "verbatim_fragments"
            f.loc[i, "quote_fragments"] = " ... ".join(frs)
            conf["relocated"] += 1
        else:
            conf["reloc_failed"] += 1
            f.loc[i, "verify_note"] = f"relocation to {newdoc} p{newpage} NOT confirmed ({cov:.0%}); left as fail"
    else:
        frs, cov = fragments(row.quote, page_text(row.doc, int(row.page)))
        if cov >= 0.6:
            f.loc[i, "verify_status"] = "verbatim_fragments"
            f.loc[i, "quote_fragments"] = " ... ".join(frs)
            f.loc[i, "verify_note"] = f"quote is stitched from verbatim runs on cited page {int(row.page)} (+1): {cov:.0%} of words covered"
            conf["fragments"] += 1
        else:
            f.loc[i, "verify_note"] = f"fragments NOT confirmed on cited page ({cov:.0%}); left as fail"
print("ref fixes rows", fixes, conf, f.verify_status.value_counts().to_dict(), "licensure filled", int(f.licensure_date.notna().sum()))
write("verify_pipeline", "verified/pipeline/fda_calendar.csv", f.to_csv(index=False), group="pipeline", doc_type="verified_table",
      source_url=PB + "; openFDA drugsfda; company filings")
write("verify_pipeline", "verified/pipeline/fda_calendar_wave2.csv", (V / "fda_calendar_wave2.csv").read_text(), group="pipeline",
      doc_type="verified_table_prior")
