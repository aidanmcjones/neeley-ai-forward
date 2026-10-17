import re, sys
import xml.etree.ElementTree as ET
from agent.moat.secx_lib import *

COLS = ["ticker", "person", "role", "date", "code", "shares", "price", "value", "acq_disp", "security", "derivative",
        "owned_after", "accession", "url"]


def txt(e, path):
    x = e.find(path)
    return (x.text or "").strip() if x is not None and x.text else ""


def parse(xml, t, url, acc):
    root = ET.fromstring(xml)
    rel = root.find("reportingOwner/reportingOwnerRelationship")
    if rel is None:
        return []
    isdir, isoff = txt(rel, "isDirector") in ("1", "true"), txt(rel, "isOfficer") in ("1", "true")
    if not (isdir or isoff):
        return []
    role = txt(rel, "officerTitle") if isoff else ""
    role = ("Director; " if isdir else "") + role
    person = txt(root, "reportingOwner/reportingOwnerId/rptOwnerName")
    rows = []
    for kind, tag in (("N", "nonDerivativeTable/nonDerivativeTransaction"), ("D", "derivativeTable/derivativeTransaction")):
        for tr in root.findall(tag):
            sh = txt(tr, "transactionAmounts/transactionShares/value")
            pr = txt(tr, "transactionAmounts/transactionPricePerShare/value")
            try:
                val = round(float(sh) * float(pr), 2) if sh and pr else ""
            except ValueError:
                val = ""
            rows.append({"ticker": t, "person": person, "role": role.strip("; "),
                         "date": txt(tr, "transactionDate/value"), "code": txt(tr, "transactionCoding/transactionCode"),
                         "shares": sh, "price": pr, "value": val,
                         "acq_disp": txt(tr, "transactionAmounts/transactionAcquiredDisposedCode/value"),
                         "security": txt(tr, "securityTitle/value"), "derivative": "Y" if kind == "D" else "",
                         "owned_after": txt(tr, "postTransactionAmounts/sharesOwnedFollowingTransaction/value"),
                         "accession": acc, "url": url})
    return rows


def main():
    allrows = []
    only = sys.argv[1:]
    for t, cik in ciks().items():
        if t in ("AZN", "NVO") or (only and t not in only):
            continue
        _, fs = filings(cik, "2024-01-01")
        fs = [f for f in fs if f["form"] in ("4", "4/A")]
        print(t, len(fs), "form 4s", flush=True)
        for i, f in enumerate(fs):
            name = f["primary_doc"].split("/")[-1]
            url = url_of(cik, f["accession"], name)
            try:
                allrows += parse(sec_get(url), t, url, f["accession"])
            except Exception as e:
                note_gap("secx", t, f"form4 {f['accession']}", repr(e)[:150])
            if i % 100 == 99:
                write_csv("tables/insider_trades.csv", COLS, allrows)
        write_csv("tables/insider_trades.csv", COLS, allrows)


if __name__ == "__main__":
    main()
