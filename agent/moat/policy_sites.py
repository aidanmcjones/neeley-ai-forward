"""FDA Drug Establishments Current Registration Site -> manufacturing_sites.csv (per company x country counts)."""
import csv
import re
import sys
import zipfile
import io
from collections import Counter, defaultdict

from agent.moat.common import OUT, note_gap, now, write
from agent.moat.policy_gov import get

URL = "https://www.accessdata.fda.gov/cder/drls_reg.zip"
PAGE = "https://www.fda.gov/drugs/drug-approvals-and-databases/drug-establishments-current-registration-site"

ALIASES = {
    "MRK": r"merck sharp|\bmsd\b|merck & co|schering.plough|msd international|organon llc$",
    "BMY": r"bristol.myers|bristol myers|celgene|squibb|medarex|\bbms\b|mirati|2seventy|juno therap|rayze|karuna",
    "PFE": r"pfizer|wyeth|hospira|pharmacia|upjohn|seagen|seattle genetics|meridian medical|arena pharm|anacor|medivation|array biopharma|biohaven|king pharm",
    "LLY": r"\blilly\b|eli lilly|loxo|imclone|dermira|verve",
    "NVO": r"novo nordisk|nnpharmaplan|novo-nordisk",
    "ABBV": r"abbvie|allergan|pharmacyclics|stemcentrx|cerevel|immunogen|abbott laboratories? (?:ireland|singapore)",
    "JNJ": r"janssen|johnson & johnson|johnson and johnson|actelion|cilag|\balza\b|momenta|intra.cellular|mcneil",
    "AZN": r"astrazeneca|astra zeneca|medimmune|alexion|zeneca|amylin|acerta",
    "AMGN": r"\bamgen\b|immunex|horizon therapeutics|horizon medicines|onyx pharm|abgenix",
    "GILD": r"gilead|kite pharma|\bkite\b|immunomedics|forty seven|cymabay|pharmasset",
}
EXCLUDE = r"elanco|merck kgaa|emd serono|merck life science|merck chemicals|sigma|merck biodevelopment|gilead alberta"


def country(addr):
    m = re.search(r"\(([A-Z]{3})\)\s*$", addr.strip())
    return m.group(1) if m else "UNK"


if __name__ == "__main__":
    raw = open(sys.argv[1], encoding="latin-1").read().splitlines()
    hdr = [h.strip() for h in raw[0].split("\t")]
    rows = []
    for ln, line in enumerate(raw[1:], 2):
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < len(hdr) - 4:
            continue
        rec = dict(zip(hdr, parts))
        rec["_line"] = ln
        rows.append(rec)
    print(len(rows), "rows")
    sites = defaultdict(dict)  # ticker -> fei -> rec
    detail = []
    for r in rows:
        name = r["FIRM_NAME"].lower()
        reg = r.get("REGISTRANT_NAME", "").lower()
        for t, pat in ALIASES.items():
            hit = None
            if re.search(pat, name) and not re.search(EXCLUDE, name):
                hit = "firm_name"
            elif re.search(pat, reg) and not re.search(EXCLUDE, reg):
                hit = "registrant_name"
            if hit:
                ops = r["OPERATIONS"]
                mfg = bool(re.search(r"MANUFACTURE", ops))
                key = (r["FEI_NUMBER"], r["ADDRESS"])
                sites[t][key] = (r, hit, mfg)
                break
    out = []
    summary = []
    for t in ALIASES:
        cnt_all = Counter()
        cnt_mfg = Counter()
        for key, (r, hit, mfg) in sites[t].items():
            c = country(r["ADDRESS"])
            cnt_all[c] += 1
            if mfg:
                cnt_mfg[c] += 1
            detail.append([t, r["FEI_NUMBER"], r["FIRM_NAME"], r["REGISTRANT_NAME"], hit, c, r["OPERATIONS"], "Y" if mfg else "N",
                           r["EXPIRATION_DATE"], f"drls_reg.txt line {r['_line']}"])
        for c in sorted(cnt_all):
            out.append([t, c, cnt_all[c], cnt_mfg[c]])
        us = cnt_all["USA"] + cnt_all["PRI"]
        tot = sum(cnt_all.values())
        usm = cnt_mfg["USA"] + cnt_mfg["PRI"]
        totm = sum(cnt_mfg.values())
        summary.append((t, tot, us, totm, usm))
        print(t, "all", tot, "US+PR", us, "| mfg", totm, "US+PR", usm)
    # write detail csv and country counts
    src = URL
    with open(OUT / "tables_tmp_sites_detail.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "fei_number", "firm_name", "registrant_name", "matched_on", "country", "operations", "has_manufacture_op", "expiration_date", "source_row"])
        w.writerows(detail)
