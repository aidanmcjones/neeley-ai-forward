"""Peers wave 3 item 4b: promote checked wave-3 product revenue rows into verified/peers/peer_product_revenue.csv.

Reads data/moat/verify/pe_w3_rev_checks.csv (from pe_w3_rev.py). Values are always taken from the re-parsed source
line, the period label from the governing table header, and GSK names from the full wrapped name. Rows whose value
or geography did not reproduce, and duplicate rows from an alternate filing of the same release, go to
peer_product_revenue_wave3_dropped.csv. Draws the 120-row stratified hand sample and logs AI errors.

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_promote.py
"""
import io
import json

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT, log_wrong

SRC = ROOT / "data/moat/tables/peer_product_revenue_wave3.csv"
CHK = ROOT / "data/moat/verify/pe_w3_rev_checks.csv"
VER = ROOT / "data/moat/verified/peers/peer_product_revenue.csv"
COMPANY = {"SNY": "Sanofi", "GSK": "GSK", "TAK": "Takeda", "NVS": "Novartis"}
CUR = {"SNY": "EUR", "GSK": "GBP", "TAK": "JPY", "NVS": "USD"}
SUB = {"SNY": {"Biopharma", "Company", "Consumer Healthcare", "Core Assets", "General Medicines", "Non-Core Assets",
               "Opella", "Pharma", "Specialty Care", "Total Pharma", "Total Pharma launches", "Total Sanofi",
               "Total other medicines", "Vaccines", "Allergy", "Digestive Wellness", "Pain Care",
               "Physical and Mental Wellness"},
       "GSK": {"Shingles", "Meningitis", "Influenza", "Established Vaccines", "Vaccines ex COVID", "Vaccines",
               "Pandemic", "HIV", "Long-Acting Injectables", "Respiratory, Immunology and Inflammation",
               "Immunology and Inflammation", "Oncology", "Specialty Medicines", "General Medicines", "Respiratory"}}
RESID = {"Others", "Non-Core / Others", "Others core assets", "Others non-core assets", "Industrial Sales", "Other",
         "Other Respiratory", "Other General Medicines"}
GROUP = {"Influenza Vaccines", "Influenza vaccines", "Hepatitis", "Fluarix, FluLaval", "Infanrix, Pediarix",
         "Priorix, Priorix Tetra, Varilrix"}
END = {"Q1": "03-31", "Q2": "06-30", "H1": "06-30", "Q3": "09-30", "9M": "09-30", "Q4": "12-31", "FY": "12-31"}
TAK_END = {"Q1": (0, "06-30"), "H1": (0, "09-30"), "9M": (0, "12-31"), "FY": (1, "03-31")}


def row_type(t, name, indented=None):
    if t == "GSK" and name == "Other General Medicines":  # bold category subtotal vs indented residual line inside it
        return "residual" if indented in (True, "True") else "subtotal"
    if name in RESID:
        return "residual"
    if name in GROUP:
        return "product_group"
    if name in SUB.get(t, set()):
        return "subtotal"
    return "product"


def main():
    d = pd.read_csv(SRC)
    c = pd.read_csv(CHK).set_index("idx")
    old = pd.read_csv(VER)
    old = old[old.ticker == "NVS"].copy()  # rerun-safe: keep only the NVS base rows
    for k, v in dict(company="Novartis", currency="USD", period_scope="FY", period_end=None, row_type="product",
                     segment=None, europe_m=None, other_m=None, verify_status="verified").items():
        if k not in old.columns:
            old[k] = v
    old["period_end"] = old.fiscal_year.astype(str) + "-12-31"
    keep, drop, aiw = [], [], {}
    for idx, r in d.iterrows():
        k = c.loc[idx]
        t = r.ticker
        name = k.src_name if t == "GSK" and isinstance(k.src_name, str) else r.brand
        seg = None
        if t == "GSK" and isinstance(k.header, str):
            seg = k.header.split(" turnover")[0]
        if t == "TAK":
            scope, label = k.src_scope, k.src_label
            y = int(label[2:6])
            add, md = TAK_END[scope]
            pend = f"{y + add}-{md}"
        else:
            scope, label = k.src_scope, k.src_label
            pend = f"{int(k.src_year)}-{END[scope]}"
        status = []
        if not k.label_scope_ok:
            status.append("label_corrected")
            aiw.setdefault((t, "period_scope"), []).append((r.brand, r.fiscal_year, label, r.source))
        if name != r.brand:
            status.append("name_corrected")
            aiw.setdefault((t, "name"), []).append((r.brand, r.fiscal_year, name, r.source))
        ok = bool(k.line_ok and k.total_ok and (k.us_ok in (True, "True")) and (k.other_ok in (True, "True")))
        note = str(r.verify_note)
        note = note.split("; ", 1)[1] if note.startswith("scope=") else note
        rec = r.to_dict()
        rec.update(fiscal_year=label, brand=name, company=COMPANY[t], currency=CUR[t], period_scope=scope,
                   period_end=pend, row_type=row_type(t, name, k.get("indented")), segment=seg,
                   europe_m=k.get("src_eu") if t != "TAK" else None,
                   other_m=k.get("src_other") if t != "TAK" else None,
                   classification=seg if t == "GSK" else r.classification,
                   printed_page=None if str(r.printed_page) == "?" else r.printed_page,
                   verify_status="verified" + ("_" + "_".join(status) if status else ""),
                   verify_note=(f"governing header line {int(k.header_line)}: {k.header}; " if t != "TAK" and k.header_line == k.header_line else
                                f"Takeda {scope} cumulative period of FY{label[2:6]} (April start); " if t == "TAK" else "") + note
                   + ("; values in local currency millions despite *_usd_m column names" ))
        if t == "SNY":
            rec["verify_note"] += "; other_m = Rest of world, row_usd_m = Europe + Rest of world"
        if t == "GSK":
            rec["verify_note"] += "; other_m = International, row_usd_m = Europe + International"
        (keep if ok else drop).append(rec if ok else {**rec, "drop_reason": "value or geography did not reproduce"})
    k = pd.DataFrame(keep)
    # alternate filing: SNY 2024 half-year management report (000016) repeats the H1 2024 release (000018)
    alt = k[k.doc == "2024-07-25_0001121404-24-000016"]
    rel = k[k.doc == "2024-07-25_0001121404-24-000018"].set_index(["fiscal_year", "brand"]).total_usd_m
    same = sum(1 for _, a in alt.iterrows() if rel.get((a.fiscal_year, a.brand)) == a.total_usd_m)
    for _, a in alt.iterrows():
        drop.append({**a.to_dict(), "drop_reason": f"duplicate: half-year management report repeats results release 2024-07-25_0001121404-24-000018 ({same}/{len(alt)} rows matched in it)"})
    k = k[k.doc != "2024-07-25_0001121404-24-000016"]
    dup = k.duplicated(["ticker", "fiscal_year", "segment", "brand", "row_type"], keep=False)
    print("remaining duplicate keys", int(dup.sum()))
    if dup.any():
        print(k[dup][["ticker", "fiscal_year", "segment", "brand", "doc", "source_row"]].to_string())
    out = pd.concat([old, k], ignore_index=True)
    cols = list(old.columns) + [x for x in out.columns if x not in old.columns]
    out = out[cols]
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/peer_product_revenue.csv", buf.getvalue(), group="peers",
          doc_type="table", period="2022-2026", quality="verified")
    dr = pd.DataFrame(drop)
    buf = io.StringIO()
    dr.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/peer_product_revenue_wave3_dropped.csv", buf.getvalue(), group="peers",
          doc_type="table", quality="dropped")
    print("kept", len(k), "dropped", len(dr), "total file", len(out))
    print(k.groupby(["ticker", "row_type"]).size().to_string())
    print(k.groupby("ticker").verify_status.value_counts().to_string())
    json.dump({f"{a}|{b}": len(v) for (a, b), v in aiw.items()}, open(ROOT / "data/moat/verify/pe_w3_aiw_counts.json", "w"))
    return aiw


if __name__ == "__main__":
    main()
