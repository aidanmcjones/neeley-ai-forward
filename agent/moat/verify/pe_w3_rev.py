"""Peers wave 3 item 4: verify peer_product_revenue_wave3.csv (SNY EUR, GSK GBP, TAK JPY) row by row.

For every row: re-read the cited line from the 6-K, re-parse the numbers (SNY one line of Total / US / Europe / RoW,
GSK twelve value lines after the name, TAK the 'Sales of X were JPY n billion' sentence), and re-derive the period
scope from the governing table header (GSK '... turnover - three/six/nine months ended', SNY 'Appendix 1: Q2 2025
net sales', TAK 'Summary of Financial Statements for the Nine-month Period'). Writes a per-row check table that
pe_w3_promote.py turns into the verified file.

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_rev.py
"""
import re

import pandas as pd

from agent.moat.verify.pe_lib import ROOT

SRC = ROOT / "data/moat/tables/peer_product_revenue_wave3.csv"
OUT = ROOT / "data/moat/verify/pe_w3_rev_checks.csv"
_cache = {}


def lines(p):
    if p not in _cache:
        _cache[p] = (ROOT / p).read_text(errors="replace").split("\n")
    return _cache[p]


def tonum(t):
    t = t.strip().replace(",", "")
    if t in ("-", "—", "–", "", "n/a"):
        return 0.0
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def scope_from(text, filed):
    t = text.lower()
    yr = re.search(r"(20\d\d)", text)
    yr = int(yr.group(1)) if yr else None
    if re.search(r"fourth[- ]quarter|\bq4\b", t):
        s = "Q4"
    elif re.search(r"third[- ]quarter|\bq3\b", t):
        s = "Q3"
    elif re.search(r"second[- ]quarter|\bq2\b", t):
        s = "Q2"
    elif re.search(r"first[- ]quarter|\bq1\b", t):
        s = "Q1"
    elif re.search(r"\bh1\b|first[- ]half|half[- ]year|six months|six-month", t):
        s = "H1"
    elif re.search(r"\bytd\b|\b9m\b|nine months|nine-month", t):
        s = "9M"
    elif re.search(r"three months|three-month", t):
        m = re.search(r"(march|june|september|december)", t)
        s = {"march": "Q1", "june": "Q2", "september": "Q3", "december": "Q4"}.get(m.group(1) if m else "", "Q?")
    elif re.search(r"full[- ]year|year ended|\bfy\b", t):
        s = "FY"
    else:
        s = None
    return s, yr


SNY_H = re.compile(r"(Appendix 1:.*net sales|^\s*20\d\d net sales by|Full year 20\d\d|^\s*(Q[1-4]|H1|YTD|9M) 20\d\d \(€ million\)|D\.3\.2\.)")
GSK_H = re.compile(r"turnover\s*[–-]\s*(year|three|six|nine)", re.I)


def header(L, ln, rx):
    for i in range(ln - 1, -1, -1):
        if rx.search(L[i]):
            h = L[i].strip()
            if h.endswith(("ended 30", "ended 31")) and i + 1 < len(L):
                h += " " + L[i + 1].strip()
            return i + 1, h
    return None, None


PCT = re.compile(r"[+-]?\(?>?\d+(?:\.\d+)?\)?\s*%")
NUMTOK = re.compile(r"(?<![\w.])(\(?-?\d{1,3}(?:,\d{3})+\)?|\(?-?\d+\)?|—|–)(?![\w.%])")


def check_sny(r, L, ln):
    name = r.brand
    txt = L[ln - 1].strip()
    if not txt.startswith(name):
        return dict(name_ok=False, note=f"line does not start with brand: {txt[:60]}")
    rest = txt[len(name):]
    if not re.search(r"\d", rest):  # values on the next nonblank line
        j = ln
        while j < len(L) and not L[j].strip():
            j += 1
        rest = L[j]
    rest = PCT.sub(" ", rest)
    vals = [tonum(x) for x in NUMTOK.findall(rest)]
    if len(vals) < 4:
        return dict(name_ok=True, note=f"cannot parse values: {rest[:80]}")
    tot, us, eu, rw = vals[:4]
    return dict(name_ok=True, src_total=tot, src_us=us, src_eu=eu, src_other=rw,
                sum_ok=abs(us + eu + rw - tot) <= 2)


def check_gsk(r, L, ln):
    txt = L[ln - 1].strip()
    name_ok = txt == r.brand
    prev = next((L[i].strip() for i in range(ln - 2, -1, -1) if L[i].strip()), "")
    # names that wrap: 'Long' / 'Acting Injectables', 'Other' / 'Respiratory', 'Priorix, Priorix Tetra,' / 'Varilrix'
    frags, i = [], ln - 2
    while i >= 0 and len(frags) < 3:
        s = L[i].strip()
        if not s:
            i -= 1
            continue
        if re.match(r"^[\(\)\d,.>%–—-]+$", s) or s in ("CER%", "£m", "£%", "Growth", "International") or GSK_H.search(s):
            break
        frags.insert(0, s)
        i -= 1
    full = txt
    for f in reversed(frags):
        full = (f + "-" + full) if f == "Long" else (f + " " + full)
    toks, j = [], ln
    raw = []
    while j < len(L) and len(toks) < 12:
        if L[j].strip():
            toks.append(L[j].strip())
            raw.append(L[j])
        j += 1
    vals = [tonum(t.replace(">", "")) for t in toks]
    if len(vals) < 12 or any(vals[k] is None for k in (0, 3, 6, 9)):
        return dict(name_ok=name_ok, note=f"cannot parse values: {toks}", prev=prev)
    tot, us, eu, intl = vals[0], vals[3], vals[6], vals[9]
    # GSK prints bold therapeutic-area rows with no leading space and indented product rows with one
    indented = raw[0].startswith(" ")
    return dict(name_ok=name_ok, src_total=tot, src_us=us, src_eu=eu, src_other=intl,
                sum_ok=abs(us + eu + intl - tot) <= 2, indented=indented, prev=prev, src_name=full)


def check_tak(r, L, ln):
    txt = L[ln - 1]
    m = re.search(r"Sales of (.+?) (?:\(.*?\) )?were JPY ([\d,.]+) billion", txt)
    if not m:
        return dict(name_ok=False, note="no 'Sales of X were JPY n billion' sentence")
    name_ok = r.brand in m.group(1) or m.group(1).startswith(r.brand)
    tot = round(float(m.group(2).replace(",", "")) * 1000, 1)
    return dict(name_ok=name_ok, src_total=tot, sum_ok=True)


def tak_scope(L):
    head = " ".join(L[:400])
    m = re.search(r"(Three|Six|Nine)-month Period Ended|Fiscal Year Ended|for the (three|six|nine)-month period|for the fiscal year", head, re.I)
    if not m:
        return None
    w = m.group(0).lower()
    return "Q1" if "three" in w else "H1" if "six" in w else "9M" if "nine" in w else "FY"


def main():
    d = pd.read_csv(SRC)
    out = []
    for idx, r in d.iterrows():
        L = lines(r.source_path)
        ln = int(re.match(r"line (\d+)", r.source_row).group(1))
        c = dict(idx=idx, ticker=r.ticker, fiscal_year=r.fiscal_year, brand=r.brand, doc=r.doc, line=ln)
        cited = r.source_row.split(": ", 1)[1].split()[0] if ": " in r.source_row else ""
        c["line_ok"] = cited in L[ln - 1]
        if r.ticker == "SNY":
            c.update(check_sny(r, L, ln))
            hl, h = header(L, ln, SNY_H)
            if h and "D.3.2" in h:
                h = "half-year report " + h
            c["header_line"], c["header"] = hl, h
            s, y = scope_from(h or "", r.doc)
        elif r.ticker == "GSK":
            c.update(check_gsk(r, L, ln))
            hl, h = header(L, ln, GSK_H)
            c["header_line"], c["header"] = hl, h
            s, y = scope_from(h or "", r.doc)
            if y is None and s:
                fy = int(r.doc[:4])
                y = fy - 1 if (s in ("Q4", "FY") and r.doc[5:7] in ("01", "02")) else fy
        else:
            c.update(check_tak(r, L, ln))
            s = tak_scope(L)
            c["header"] = s
            y = None
        if r.ticker == "SNY" and y is None and s:
            fy = int(r.doc[:4])
            y = fy - 1 if (s in ("Q4", "FY") and r.doc[5:7] in ("01", "02")) else fy
        c["src_scope"], c["src_year"] = s, y
        if r.ticker == "TAK":
            fyl = re.match(r"FY(\d{4})Q(\d)", r.fiscal_year)
            c["src_label"] = f"FY{fyl.group(1)}{ {'Q1': 'Q1', 'H1': 'H1', '9M': '9M', 'FY': 'FY'}.get(s, '?') }"
            c["label_scope_ok"] = {"1": "Q1", "2": "H1", "3": "9M", "4": "FY"}[fyl.group(2)] == s and fyl.group(2) == "1"
            yy, mm = int(r.doc[:4]), int(r.doc[5:7])
            exp_fy, exp_q = (yy, "1") if mm in (7, 8) else (yy, "2") if mm in (10, 11) else (yy - 1, "3") if mm in (1, 2) else (yy - 1, "4")
            c["fy_label_ok"] = int(fyl.group(1)) == exp_fy and fyl.group(2) == exp_q
        else:
            c["src_label"] = f"{y}{s}" if s else None
            c["label_scope_ok"] = c["src_label"] == str(r.fiscal_year)
        c["total_ok"] = c.get("src_total") is not None and abs(c["src_total"] - r.total_usd_m) < 0.6
        if r.ticker in ("SNY", "GSK") and c.get("src_us") is not None:
            c["us_ok"] = abs(c["src_us"] - r.us_usd_m) < 0.6
            c["other_ok"] = abs(c["src_eu"] + c["src_other"] - r.row_usd_m) < 0.6
        else:
            c["us_ok"] = c["other_ok"] = (r.ticker == "TAK") or None
        out.append(c)
    o = pd.DataFrame(out)
    o.to_csv(OUT, index=False)
    for col in ["line_ok", "name_ok", "total_ok", "us_ok", "other_ok", "sum_ok", "label_scope_ok"]:
        print(col, o.groupby("ticker")[col].apply(lambda s: f"{(s == True).sum()}/{len(s)}").to_dict())
    print(o.groupby(["ticker", "src_scope"]).size())


if __name__ == "__main__":
    main()
