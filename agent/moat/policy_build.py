"""Build tables/policy_exposure.csv, tables/manufacturing_sites.csv, tables/force_summary.csv."""
import csv
import io
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from agent.moat import policy_sites as PS
from agent.moat.common import ROOT, note_gap, write
from agent.moat.policy_spec import ROWS, C, K, R

ROWS.append(("NVO", "exposure_base", "FY2025 group net sales", 309064, "DKK m", "2025-12-31", C("NVO", "20f_FY2025_d2.md"),
             ["Net sales 309,064 290,403 232,261"], "group total, used as denominator for IRA revenue share"))

_cache = {}


def norm(s):
    s = s.replace("​", " ").replace("\xa0", " ")
    return " ".join(s.split())


def load(doc):
    if doc not in _cache:
        txt = (ROOT / doc).read_text()
        src = re.search(r"source: (\S+)", txt)
        parts = re.split(r"\[\[page (\d+) \| printed ([^\]]+)\]\]", txt)
        pages = []
        if len(parts) == 1:
            pages.append(("1", norm(txt)))
        else:
            for i in range(1, len(parts), 3):
                label = parts[i + 1].strip()
                label = label if label != "?" else f"p{parts[i]}"
                pages.append((label, norm(parts[i + 2])))
        _cache[doc] = (src.group(1) if src else "", pages)
    return _cache[doc]


def locate(doc, quotes):
    url, pages = load(doc)
    for q in quotes:
        nq = norm(q)
        for label, body in pages:
            if nq in body:
                return url, label, nq
    return url, None, None


def main():
    out = []
    fails = []
    for t, force, item, value, unit, date, doc, quotes, note in ROWS:
        tickers = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"] if t == "ALL" else [t]
        url, page, q = locate(doc, quotes)
        if page is None:
            fails.append((t, item, doc, quotes[0][:80]))
            continue
        for tk in tickers:
            out.append([tk, force, item, value, unit, date, doc, page, q[:300], url, f"{doc}#page={page}", note])
    # sites
    site_rows, trace_sites = build_sites()
    out.extend(site_rows)
    for i, r in enumerate(out, 1):
        r.insert(0, f"R{i:03d}")
    cols = ["row_id", "ticker", "force", "item", "value", "unit", "effective_date", "doc", "printed_page_or_section", "quote", "source", "source_row", "note"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(out)
    write("policy", "tables/policy_exposure.csv", buf.getvalue(), group="policy", doc_type="table", period="2026", source_url="see source column")
    print("policy_exposure rows", len(out), "failures", len(fails))
    for f in fails:
        print("FAIL", f)
        note_gap("policy", f[0], f[1], f"quote not found in {f[2]}")
    summary(out)


def build_sites():
    raw = open(sys.argv[1], encoding="latin-1").read().splitlines()
    hdr = [h.strip() for h in raw[0].split("\t")]
    sites = defaultdict(dict)
    for ln, line in enumerate(raw[1:], 2):
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < len(hdr) - 4:
            continue
        r = dict(zip(hdr, parts))
        name, reg = r["FIRM_NAME"].lower(), r.get("REGISTRANT_NAME", "").lower()
        for t, pat in PS.ALIASES.items():
            hit = None
            if re.search(pat, name) and not re.search(PS.EXCLUDE, name):
                hit = "firm_name"
            elif re.search(pat, reg) and not re.search(PS.EXCLUDE, reg):
                hit = "registrant_name"
            if hit:
                sites[t][(r["FEI_NUMBER"], r["ADDRESS"])] = (r, hit, ln)
                break
    cols = ["ticker", "country_code", "us_or_non_us", "n_sites", "n_sites_with_manufacture_op", "example_firm_names", "source_rows", "source"]
    rows = []
    det = [["ticker", "fei_number", "firm_name", "registrant_name", "matched_on", "country_code", "operations", "has_manufacture_op", "registration_expiration", "source_row"]]
    agg = {}
    for t in PS.ALIASES:
        by = defaultdict(list)
        for key, (r, hit, ln) in sites[t].items():
            c = PS.country(r["ADDRESS"])
            mfg = "MANUFACTURE" in r["OPERATIONS"]
            by[c].append((r, mfg, ln, hit))
            det.append([t, r["FEI_NUMBER"], r["FIRM_NAME"], r["REGISTRANT_NAME"], hit, c, r["OPERATIONS"], "Y" if mfg else "N", r["EXPIRATION_DATE"], f"drls_reg.txt:line {ln}"])
        tot = totm = us = usm = 0
        for c in sorted(by):
            lst = by[c]
            isus = c in ("USA", "PRI", "VIR", "GUM")
            n, nm = len(lst), sum(1 for x in lst if x[1])
            tot += n
            totm += nm
            if isus:
                us += n
                usm += nm
            rows.append([t, c, "US (incl. territories)" if isus else "non-US", n, nm, "; ".join(sorted({x[0]["FIRM_NAME"] for x in lst})[:3]),
                         ",".join(str(x[2]) for x in lst[:30]), PS.URL])
        agg[t] = (tot, us, totm, usm)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    write("policy", "tables/manufacturing_sites.csv", buf.getvalue(), group="policy", doc_type="table", source_url=PS.URL)
    buf = io.StringIO()
    csv.writer(buf).writerows(det)
    write("policy", "tables/manufacturing_sites_detail.csv", buf.getvalue(), group="policy", doc_type="table", source_url=PS.URL)
    print("manufacturing_sites rows", len(rows), "detail", len(det) - 1)
    exp = []
    for t, (tot, us, totm, usm) in agg.items():
        for item, v in [("FDA-registered establishments, all operations: total", tot), ("FDA-registered establishments, all operations: US incl. PR", us),
                        ("FDA-registered establishments with a MANUFACTURE operation: total", totm), ("FDA-registered establishments with a MANUFACTURE operation: US incl. PR", usm)]:
            exp.append([t, "manufacturing", item, v, "sites", "2026-10-16", "data/moat/tables/manufacturing_sites.csv", "n/a", "n/a (computed from FDA drls_reg.txt, see manufacturing_sites_detail.csv)", PS.URL, "tables/manufacturing_sites_detail.csv", "name-alias match; CDER-registered only"])
    return exp, agg


def summary(out):
    by = defaultdict(list)
    for r in out:
        by[r[1]].append(r)

    def find(t, prefix):
        return [r for r in by[t] if r[3].startswith(prefix)]

    def val(t, prefix):
        rs = find(t, prefix)
        return (rs[0][4], rs[0][0]) if rs else (None, None)

    cols = ["ticker", "ira_drug_count_ipay2026_2028", "ira_drugs", "ira_drug_fy2025_revenue", "ira_revenue_unit", "ira_share_of_total_revenue_pct", "mfn_date",
            "us_investment_pledge_usd_bn", "pledge_scope", "tariff_exempt_until", "mfg_sites_total", "mfg_sites_non_us", "pct_mfg_sites_outside_us", "us_revenue_share_pct", "traceable_row_ids"]
    rows = []
    for t in ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]:
        ira_rows = [r for r in by[t] if r[2] == "IRA" and "MFP per 30-day" in r[3] or (r[2] == "IRA" and "IPAY 2028" in r[3])]
        drugs = []
        for r in ira_rows:
            m = re.match(r"IRA (.+?) \(IPAY (\d+)\)", r[3])
            drugs.append(f"{m.group(1)} ({m.group(2)})")
        rev_rows = [r for r in by[t] if r[2] == "IRA" and r[3].startswith("FY2025 revenue")]
        rev = sum(float(r[4]) for r in rev_rows)
        unit = rev_rows[0][5]
        tot = float(val(t, "FY2025 group net sales")[0] or val(t, "FY2025 Total revenue")[0])
        totid = val(t, "FY2025 group net sales")[1] or val(t, "FY2025 Total revenue")[1]
        usr, usid = val(t, "FY2025 US revenue")
        tot_us_den = float(val(t, "FY2025 Total revenue")[0])
        mfn = find(t, "MFN agreement announced")
        pl = [r for r in by[t] if r[2] == "manufacturing" and ("pledged" in r[3] or "pledge" in r[3] or "announced 2025" in r[3])]
        pr = pl[0]
        tx = find(t, "Statutory tariff-exemption end")
        mt = val(t, "FDA-registered establishments with a MANUFACTURE operation: total")
        mu = val(t, "FDA-registered establishments with a MANUFACTURE operation: US")
        outside = float(mt[0]) - float(mu[0])
        trace = ",".join([r[0] for r in ira_rows] + [r[0] for r in rev_rows] + [totid, usid, mfn[0][0], pr[0], tx[0][0], mt[1], mu[1]])
        rows.append([t, len(drugs), "; ".join(drugs), round(rev), unit, round(100 * rev / tot, 1), mfn[0][4], pr[4], pr[3], tx[0][4], int(float(mt[0])), int(outside),
                     round(100 * outside / float(mt[0]), 1), round(100 * float(usr) / tot_us_den, 1), trace])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    write("policy", "tables/force_summary.csv", buf.getvalue(), group="policy", doc_type="table")
    print(buf.getvalue())


if __name__ == "__main__":
    main()
