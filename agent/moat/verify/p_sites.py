"""Check manufacturing_sites_detail rows against drls_reg.txt lines; dump names; probe for misses."""
import csv
import re
import sys

from agent.moat.common import ROOT

FDA = "/Users/aidanjones/.claude/jobs/9174fb40/tmp/fda/x/drls_reg.txt"
raw = open(FDA, encoding="latin-1").read().splitlines()
hdr = [h.strip() for h in raw[0].split("\t")]
det = list(csv.DictReader(open(ROOT / "data/moat/tables/manufacturing_sites_detail.csv")))
mode = sys.argv[1]
if mode == "check":
    bad = 0
    for d in det:
        ln = int(d["source_row"].split("line ")[1])
        r = dict(zip(hdr, [p.strip() for p in raw[ln - 1].split("\t")]))
        ok = r.get("FEI_NUMBER") == d["fei_number"] and r.get("FIRM_NAME") == d["firm_name"] and r.get("OPERATIONS") == d["operations"]
        if not ok:
            bad += 1
            print("MISMATCH", d["ticker"], d["fei_number"], d["firm_name"], "|", r.get("FEI_NUMBER"), r.get("FIRM_NAME"))
    print("checked", len(det), "mismatch", bad)
    print("header", hdr)
elif mode == "names":
    for d in det:
        r = dict(zip(hdr, [p.strip() for p in raw[int(d["source_row"].split("line ")[1]) - 1].split("\t")]))
        print(d["ticker"], d["has_manufacture_op"], d["country_code"], "|", d["firm_name"], "|", d["registrant_name"], "|", d["matched_on"], "|", r.get("ADDRESS", "")[:70])
else:
    pat = re.compile(sys.argv[2], re.I)
    for ln, line in enumerate(raw[1:], 2):
        if pat.search(line):
            r = dict(zip(hdr, [p.strip() for p in line.split("\t")]))
            print(ln, "|", r.get("FIRM_NAME"), "|", r.get("REGISTRANT_NAME"), "|", r.get("OPERATIONS"), "|", r.get("ADDRESS", "")[-60:])
