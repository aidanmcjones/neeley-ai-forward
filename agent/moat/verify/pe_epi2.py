"""Epi items 1, 3, 4, 5: indication_map vs label section 1; Part D recompute from the raw CMS file; Medicare floor %
recompute and subset caveat; dedupe gaps/epi.jsonl."""
import gzip
import io
import json
import re

import pandas as pd

from agent.moat.common import store, write
from agent.moat.verify.pe_lib import ROOT, norm

PARTB_IV = {"keytruda", "opdivo", "darzalex", "imfinzi", "tecentriq", "keytruda-qlex", "opdivo-qvantig",
            "darzalex-faspro", "sarclisa", "rybrevant", "entyvio", "cabenuva", "apretude", "amvuttra", "leqvio",
            "stelara", "skyrizi", "tremfya"}  # physician-administered (all or some forms) -> Part B, not Part D
CANCER_SUBSET = {"NSCLC": "lung and bronchus (all histologies)", "SCLC": "lung and bronchus (all histologies)",
                 "HR+/HER2- breast cancer": "female breast (all subtypes)", "HER2+ breast cancer": "female breast (all subtypes)",
                 "triple-negative breast cancer": "female breast (all subtypes)",
                 "colorectal cancer (MSI-H/dMMR) and tumor-agnostic MSI-H/TMB-H": "colorectal (all; MSI-H minority)",
                 "HNSCC": "oral cavity and pharynx (proxy)", "hepatocellular carcinoma": "liver and intrahepatic bile duct (proxy)",
                 "biliary tract cancer": "liver and intrahepatic bile duct (proxy)", "lymphoma (cHL / PMBCL)": "Hodgkin only",
                 "renal cell carcinoma": "kidney and renal pelvis", "gastric / GEJ cancer": "stomach only",
                 "urothelial / bladder cancer": "urinary bladder"}


def label_check():
    d = pd.read_csv(ROOT / "data/moat/tables/indication_map.csv", dtype={"label_section": str})
    s = d.sample(60, random_state=11).copy()
    out = []
    for _, r in s.iterrows():
        p = ROOT / "data/corpus/drugs" / r.drug / "label_sections.md"
        if not p.exists():
            out.append(dict(status="no_label_copy"))
            continue
        t = p.read_text(errors="replace")
        m1 = re.search(r"^## 1\s+INDICATIONS.*?(?=^## 2\s|\Z)", t, re.M | re.S)
        sec1 = m1.group(0) if m1 else ""
        hdr = re.search(r"^###\s*" + re.escape(str(r.label_section)) + r"[\s\t]+(.+)$", sec1, re.M)
        sid = re.search(r"setid=([\w-]+)", t[:400])
        url_ok = sid is not None and sid.group(1) in r.source
        if hdr is None:
            # single-section labels (no 1.x headings): look for the sub_indication text in section 1
            ok = norm(r.sub_indication, True) in norm(sec1, True)
            st = ("in_section1_no_subheading" if ok else ("section1_whole_paraphrased" if sec1 and str(r.label_section) in ("1", "1.0") else "not_in_section1"))
            heading = None
        else:
            heading = hdr.group(1).strip()
            st = "ok" if norm(heading, True) == norm(r.label_section_heading, True) else "heading_mismatch"
        block = sec1
        if hdr:
            rest = sec1[hdr.end():]
            nxt = re.search(r"^###\s", rest, re.M)
            block = rest[:nxt.start()] if nxt else rest
        aa = "accelerated approval" in block.lower()
        out.append(dict(status=st, label_heading=heading, setid_matches_url=url_ok, accelerated_approval_in_section=aa,
                        label_version=(re.search(r"spl_version: (\d+)\s+published: ([^\n]+?) retrieved", t[:600]) or [None])[0]))
    s = pd.concat([s.reset_index(drop=True), pd.DataFrame(out)], axis=1)
    # whole-table scan for accelerated approval flags
    print("indication_map sample:", s.status.value_counts().to_dict(), "AA:", int(s.accelerated_approval_in_section.sum()))
    buf = io.StringIO()
    s.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/indication_map.csv", buf.getvalue(), group="tables", doc_type="table",
          quality="verified_sample", source_url="data/corpus/drugs/<drug>/label_sections.md (DailyMed SPL)")
    return s


def partd_raw():
    raw = store().get("public/partd_spending_dy24.csv")
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return pd.read_csv(io.BytesIO(raw), low_memory=False)


def medicare_check():
    m = pd.read_csv(ROOT / "data/moat/tables/medicare_market.csv")
    pby = pd.read_csv(ROOT / "data/moat/tables/partd_by_year.csv")
    raw = partd_raw()
    cols = [c for c in raw.columns if c.endswith("_2024")]
    m24 = m[m.period.astype(str) == "2024"]
    drugs = [x for x in m24[m24.part_d_claims > 0].drug.unique()][:15]
    if len(drugs) < 15:
        drugs = list(m24.drug.unique())[:15]
    rows = []
    for dr in drugs:
        r = m24[m24.drug == dr].iloc[0]
        brands = pby[(pby.drug == dr)].brand.dropna().unique()
        sub = raw[raw.Brnd_Name.isin(brands) & (raw.Mftr_Name == "Overall")]
        claims = pd.to_numeric(sub.get("Tot_Clms_2024"), errors="coerce").sum()
        spend = pd.to_numeric(sub.get("Tot_Spndng_2024"), errors="coerce").sum()
        benes = pd.to_numeric(sub.get("Tot_Benes_2024"), errors="coerce")
        rows.append(dict(drug=dr, cls=r["class"], brands="; ".join(brands), table_claims=r.part_d_claims, raw_claims=claims,
                         table_spend=r.part_d_spend, raw_spend=spend, table_benes_floor=r.part_d_benes_floor,
                         raw_benes_floor=benes.max() if len(benes) else None, raw_benes_sum=benes.sum() if len(benes) else None,
                         part_b_administered=dr in PARTB_IV))
    c = pd.DataFrame(rows)
    c["claims_ok"] = (c.table_claims - c.raw_claims).abs() < 1
    c["spend_ok"] = (c.table_spend - c.raw_spend).abs() < 1
    c["benes_ok"] = (c.table_benes_floor.fillna(-1) - c.raw_benes_floor.fillna(-1)).abs() < 1
    # class share arithmetic for every 2024 row
    g = m24.groupby("class")
    m24 = m24.assign(cls_claims_re=g.part_d_claims.transform("sum"))
    m24 = m24.assign(share_re=m24.part_d_claims / m24.cls_claims_re)
    sh = m24[["class", "drug", "part_d_claims", "class_claims_2024", "cls_claims_re", "drug_share_of_class_claims_2024", "share_re"]]
    sh = sh.assign(class_total_ok=(sh.class_claims_2024 - sh.cls_claims_re).abs() < 1,
                   share_ok=(sh.drug_share_of_class_claims_2024.fillna(0) - sh.share_re.fillna(0)).abs() < 0.0015)
    note_iv = m.note.str.contains("Part D", na=False).mean()
    print(c[["drug", "claims_ok", "spend_ok", "benes_ok", "part_b_administered"]].to_string())
    print("class totals ok", int(sh.class_total_ok.sum()), "/", len(sh), "share ok", int(sh.share_ok.sum()), "/", len(sh))
    print(sh[~sh.share_ok | ~sh.class_total_ok].head(10).to_string())
    c["part_d_only_labelled_in_row"] = False
    for i, r in c.iterrows():
        n = str(m[m.drug == r.drug].note.iloc[0])
        c.loc[i, "part_d_only_labelled_in_row"] = bool(re.search(r"Part B|Part-D-only|Part D only", n))
    out = pd.concat([c.assign(check="drug_2024_recompute"), sh.assign(check="class_share_2024")], ignore_index=True)
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/medicare_market_checks.csv", buf.getvalue(), group="tables", doc_type="table",
          quality="verified", source_url="R2 public/partd_spending_dy24.csv (CMS Part D spending by drug, DY2024)")
    return c, sh, note_iv


def sizing():
    s = pd.read_csv(ROOT / "data/moat/tables/market_sizing_inputs.csv")
    ep = pd.read_csv(ROOT / "data/moat/verified/epi/indication_epidemiology.csv")
    has = s.medicare_floor_pct_of_denominator.notna()
    den = s.apply(lambda r: r.us_prevalence_n if r.denominator_basis == "prevalent" else
                  (r.diagnosed_n if r.denominator_basis == "diagnosed" else r.annual_incidence_n), axis=1)
    s["denominator_n"] = den
    s["floor_pct_recomputed"] = (s.medicare_partd_benes_on_drug_2024_floor / den * 100).round(3)
    s["floor_pct_ok"] = (s.floor_pct_recomputed - s.medicare_floor_pct_of_denominator).abs() <= 0.0015 + 0.001 * s.medicare_floor_pct_of_denominator.abs()
    s["floor_pct_ok"] = s.floor_pct_ok.astype(object).where(has, None)
    epi = ep.set_index("indication")
    s["denominator_matches_verified_epi"] = s.apply(lambda r: (r.indication in epi.index and
                                                    float(epi.loc[r.indication, "us_prevalence_n"]) == float(r.us_prevalence_n))
                                                    if pd.notna(r.us_prevalence_n) else pd.NA, axis=1)
    s["subset_caveat"] = s.indication.map(lambda i: f"denominator is {CANCER_SUBSET[i]}, not the labelled subset" if i in CANCER_SUBSET else "")
    s["epi_confidence"] = s.indication.map(lambda i: epi.loc[i, "confidence"] if i in epi.index else "no epi row")
    s["part_b_drug_floor_understated"] = s.drug.isin(PARTB_IV)
    print("funnel rows", int(has.sum()), "floor ok", int(s.floor_pct_ok.fillna(False).sum()),
          "denominator basis", s[has].denominator_basis.value_counts().to_dict(),
          "subset caveat", int((s.subset_caveat != "").sum()), "partB", int(s[has].part_b_drug_floor_understated.sum()))
    print(s[has & (s.floor_pct_ok == False)][["drug", "indication", "medicare_floor_pct_of_denominator", "floor_pct_recomputed", "denominator_basis"]].head(10).to_string())  # noqa: E712
    buf = io.StringIO()
    s.to_csv(buf, index=False)
    write("verify_epi", "verified/epi/market_sizing_inputs.csv", buf.getvalue(), group="tables", doc_type="table",
          quality="verified", source_url="data/moat/tables/market_sizing_inputs.csv")
    return s


def dedupe_gaps():
    p = ROOT / "data/moat/gaps/epi.jsonl"
    lines = p.read_text().splitlines()
    seen, keep = set(), []
    for l in lines:
        if l.strip() and l not in seen:
            seen.add(l)
            keep.append(l)
    # also drop same ticker/item/reason written at different times
    seen2, keep2 = set(), []
    for l in keep:
        j = json.loads(l)
        k = (j.get("ticker"), j.get("item"), j.get("reason"))
        if k not in seen2:
            seen2.add(k)
            keep2.append(l)
    p.write_text("\n".join(keep2) + "\n")
    print(f"gaps/epi.jsonl {len(lines)} -> exact dedupe {len(keep)} -> same item/reason dedupe {len(keep2)}")
    return len(lines), len(keep), len(keep2)


if __name__ == "__main__":
    label_check()
    medicare_check()
    sizing()
    dedupe_gaps()
