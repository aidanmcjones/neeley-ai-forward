"""CMS Part B ASP payment limit files, 2020Q1..2026Q4, filtered to the HCPCS of the 52 drugs and their biosimilars."""
import csv, glob, io, re, zipfile
import pandas as pd
from agent.drug_pack import DRUGS
from agent.moat.common import write, note_gap

S = "pricing"
Z = "/Users/aidanjones/.claude/jobs/9174fb40/tmp/aspzips/"
MON = {"January": 1, "April": 2, "July": 3, "October": 4}

# HCPCS per drug from the per-drug packs (Part B spending file and IRA file)
hc = {}
for slug in DRUGS:
    for fn, col in (("medicare_partb_spending.csv", "HCPCS_Cd"), ("ira_negotiation.csv", "HCPCS Code")):
        try:
            d = pd.read_csv(f"data/corpus/drugs/{slug}/{fn}", dtype=str)
        except Exception:
            continue
        for c in d[col].dropna().unique():
            hc.setdefault(c.strip(), set()).add(slug)
stems = {}
for slug, (name, lab, ing, tk) in DRUGS.items():
    stems.setdefault(ing.lower()[:8], set()).add(slug)
print("hcpcs from packs:", len(hc), {k: sorted(v) for k, v in hc.items()})

rows = []
for f in sorted(glob.glob(Z + "*.zip")):
    z = zipfile.ZipFile(f)
    cands = [n for n in z.namelist() if n.endswith(".csv") and "Not Payable" not in n]
    txt = z.read(cands[0]).decode("latin1")
    m = re.search(r"Effective (\w+) \d+, (\d{4})", txt)
    q = f"{m.group(2)}Q{MON[m.group(1)]}"
    lines = txt.splitlines()
    hi = next(i for i, l in enumerate(lines) if l.startswith("HCPCS Code"))
    rd = csv.DictReader(io.StringIO("\n".join(lines[hi:])))
    for n, r in enumerate(rd, start=hi + 2):
        code = (r.get("HCPCS Code") or "").strip()
        sd = (r.get("Short Description") or "").strip()
        if not code:
            continue
        drugs = set(hc.get(code, ()))
        low = sd.lower()
        for st, sl in stems.items():
            if st in low:
                drugs |= sl
        if not drugs:
            continue
        rows.append(dict(hcpcs=code, short_desc=sd, quarter=q, payment_limit=r.get("Payment Limit"), dosage=r.get("HCPCS Code Dosage"),
                         coinsurance_pct=r.get("Co-insurance Percentage"), notes=r.get("Notes"), drugs=";".join(sorted(drugs)),
                         match_basis="hcpcs_in_pack" if code in hc else "ingredient_in_short_desc",
                         source=f"https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files ({f.split('/')[-1]}:{cands[0]})",
                         source_row=f"{q}|file_line={n}|HCPCS={code}"))
df = pd.DataFrame(rows)
df = df.sort_values(["hcpcs", "quarter"])
write(S, "tables/partb_asp_quarterly.csv", df.to_csv(index=False), group="pricing", doc_type="table", source_url="https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files")
print(len(df), df.quarter.min(), df.quarter.max(), df.hcpcs.nunique(), df.quarter.nunique())
have = set(";".join(df.drugs).split(";"))
miss = [s for s in DRUGS if s not in have]
print("drugs with no ASP row:", miss)
for s in miss:
    note_gap(S, DRUGS[s][3], s, "no Part B ASP HCPCS match (self-administered/oral, or no ingredient/HCPCS in payment limit file)")
