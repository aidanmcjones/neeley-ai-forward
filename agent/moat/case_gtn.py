"""Gross-to-net series for a company and its drugs, every row cited.

Answers: how far do list prices (WAC, Part D gross, NADAC) and net-like prices (ASP, company-reported net)
diverge, and what do the filings say about sales deductions, rebates and gross-to-net.

Signature:  gtn_series(ticker=None, drug=None, k=200) -> list[dict]   (at least one of ticker / drug)

Row kinds: company_list_vs_net, drug_gtn_exposure, drug_gtn_proxy, wac_event, nadac, partd_support, partb_asp,
filing_sales_deduction_table, filing_statement.  Rows are sorted by drug then period (company-level rows
have drug == "").  Table rows carry period, value, unit, verify_status, source, source_row and the
facts.locator; filing rows carry the page locator and a quote that passes cite.verify_quote.

Example:  python -m agent.moat.case_gtn MRK
          python -m agent.moat.case_gtn --drug keytruda
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from agent.moat import cite, case_sets

ROOT = Path(__file__).resolve().parents[2] / "data" / "moat"
VER = ROOT / "verified" / "pricing"
TAB = ROOT / "tables"

FILING_TYPES = ["annual_report", "quarterly_report", "interim_report"]
FILING_QUERIES = ['"gross-to-net"', '"gross to net"', '"gross-to-net adjustments"', '"sales deductions"',
                  '"rebates and discounts"', '"Medicaid rebate"', '"net price"',
                  '"sales discounts, returns and allowances"', '"accrued rebates"']
# phrase regex used to place the excerpt window on the hit page
PHRASES = re.compile(r"(gross[- ]to[- ]net|GTN adjustments|sales deductions|rebates and discounts|"
                     r"Sales Discounts, Returns and Allowances|Accrued rebates|Medicaid rebate|net price)", re.I)
TABLE_HINT = re.compile(r"(reconciliation of gross|sales discounts, returns|accrued rebates|gross sales|"
                        r"chargebacks?|gross-to-net|sales deductions)", re.I)


# ------------------------------------------------------------------ helpers

def _read(path):
    """[(row_key_line_no, dict)] with line_no = record index + 2 (header is line 1), matching facts.row_key '#N'."""
    with open(path, newline="", encoding="utf-8") as f:
        return [(i + 2, r) for i, r in enumerate(csv.DictReader(f))]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _first_url(s):
    m = re.search(r"https?://[^\s;|,)\"]+", s or "")
    return m.group(0) if m else ""


def _facts_lookup(table, line_nos):
    """{line_no: (locator, verify_status)} from the facts table for one csv; empty when not indexed."""
    out = {}
    nos = sorted(set(line_nos))
    con = cite.db()
    for i in range(0, len(nos), 500):
        chunk = nos[i:i + 500]
        keys = [f"{table}#{n}" for n in chunk]
        q = ('SELECT row_key, locator, verify_status FROM facts WHERE "table"=? AND row_key IN (%s)'
             % ",".join("?" * len(keys)))
        for r in con.execute(q, [table, *keys]):
            n = int(r["row_key"].rsplit("#", 1)[1])
            out.setdefault(n, (r["locator"] or "", r["verify_status"] or ""))
    return out


def _tokens(drug):
    return [t.strip().lower() for t in re.split(r"[/;]", drug or "") if t.strip()]


def _drug_match(query_tokens, cell):
    """Case-insensitive; the cell may be 'a/b' or 'a;b'; 'keytruda' also matches 'keytruda-qlex'."""
    for c in _tokens(cell):
        for q in query_tokens:
            if c == q or c.startswith(q + "-") or q.startswith(c + "-"):
                return True
    return False


def _row(ticker, kind, drug, period, text, value, unit, table, line, src, srow, status, loc, citation, url, **extra):
    d = {"ticker": ticker, "kind": kind, "drug": drug, "period": str(period), "year": str(period)[:4],
         "text": text[:599], "value": value, "unit": unit, "verify_status": status, "source": src,
         "source_row": srow, "citation": citation, "url": url, "locator": loc, "source_id": loc,
         "quote_grade": "", "license": "", "table": table}
    d.update(extra)
    return d


def _table_cite(table, key, src):
    kind = "Verified table" if table.startswith("pricing/") else "Raw table"
    return f"{kind} {table}, row {key}" + (f" ({src[:90]})" if src else "")


def _loc_status(table, line, facts, default_status):
    loc, st = facts.get(line, ("", ""))
    return (loc or f"fact:{table}#{line}"), (st or default_status)


def _fmt(v, nd=2):
    f = _num(v)
    return "n/a" if f is None else f"{f:,.{nd}f}"


# ------------------------------------------------------------------ table sources

def _company_rows(ticker):
    t = "pricing/company_list_vs_net.csv"
    rows = [(n, r) for n, r in _read(VER / "company_list_vs_net.csv") if r["ticker"].upper() == ticker]
    facts = _facts_lookup(t, [n for n, _ in rows])
    out = []
    for n, r in rows:
        loc, st = _loc_status(t, n, facts, r.get("verified") or "unverified")
        st = r.get("verified") or st
        c, url = _table_cite(t, n, r["source"]), r["source"]
        m = re.match(r"([^#]+:.+?)#p(\d+)$", loc)
        if m:
            try:
                c, url = cite.cite(m.group(1), int(m.group(2)))
            except KeyError:
                pass
        text = (f"{ticker} {r['year']}: average list price change {_fmt(r['avg_list_price_change_pct'], 1)}%, "
                f"average net price change {_fmt(r['avg_net_price_change_pct'], 1)}%"
                + (f", average discount {_fmt(r['avg_discount_pct'], 1)}%" if r["avg_discount_pct"] else "")
                + f" ({r['scope']}). {r['note']}")
        out.append(_row(ticker, "company_list_vs_net", "", r["year"], text, _num(r["avg_net_price_change_pct"]), "%",
                        t, n, r["source"], r["source_row"], st, loc, c, url,
                        list_change_pct=_num(r["avg_list_price_change_pct"]),
                        net_change_pct=_num(r["avg_net_price_change_pct"]),
                        discount_pct=_num(r["avg_discount_pct"]), scope=r["scope"], verify_note=r["verify_note"]))
    return out


def _sel(r, ticker, toks):
    comp = (r.get("company") or "").upper()
    return (ticker and comp == ticker) or (toks and _drug_match(toks, r["drug"]))


def _exposure_rows(ticker, toks):
    t = "pricing/gtn_exposure.csv"
    rows = [(n, r) for n, r in _read(VER / "gtn_exposure.csv") if _sel(r, ticker, toks)]
    facts = _facts_lookup(t, [n for n, _ in rows])
    out = []
    for n, r in rows:
        loc, st = _loc_status(t, n, facts, "verified")
        if not r["list_like_series"] and not r["net_like_series"]:
            text = f"{r['drug']}: {r['exposure_call']} (confidence {r['confidence']})."
        else:
            text = (f"{r['drug']}: list-like ({r['list_like_series']}, {r['list_like_from'][:4]} to {r['list_like_to'][:4]}) "
                    f"{_fmt(r['list_like_pct'], 1)}% vs net-like ({r['net_like_series']}, {r['net_like_from'][:4]} to "
                    f"{r['net_like_to'][:4]}) {_fmt(r['net_like_pct'], 1)}%. {r['exposure_call']} "
                    f"(confidence {r['confidence']}). WAC increase events since 2019: {r['wac_increase_events_since_2019']}.")
        period = f"{r['list_like_from'][:4]}-{(r['net_like_to'] or r['list_like_to'])[:4]}" if r["list_like_from"] else ""
        out.append(_row(r["company"], "drug_gtn_exposure", r["drug"], period, text, _num(r["net_like_pct"]), "% change",
                        t, n, r["sources"] or "data/moat/verified/pricing/gtn_exposure.csv", f"{t}#{n}", st, loc, _table_cite(t, f"{r['drug']}", r["sources"]),
                        _first_url(r["sources"]) or "", list_like_pct=_num(r["list_like_pct"]),
                        net_like_pct=_num(r["net_like_pct"]), exposure_call=r["exposure_call"],
                        confidence=r["confidence"], ira_ipay=r["ira_ipay"], ira_mfp_effective=r["ira_mfp_effective"],
                        ira_mfp_per_30day=_num(r["ira_mfp_per_30day"]),
                        nadac_vs_mfp=_num(r["nadac_vs_mfp_ndc_matched"]), wac_events=_num(r["wac_increase_events_since_2019"]),
                        wac_cum_pct_since_2019=_num(r["wac_cum_pct_since_2019"]), ira_status_note=r["ira_status_note"]))
    return out


def _proxy_rows(ticker, toks):
    t = "pricing/gtn_proxy.csv"
    rows = [(n, r) for n, r in _read(VER / "gtn_proxy.csv") if _sel(r, ticker, toks)]
    facts = _facts_lookup(t, [n for n, _ in rows])
    out = []
    for n, r in rows:
        loc, st = _loc_status(t, n, facts, "verified")
        bits = [f"{r['drug']} {r['year']}"]
        if r["partd_spend_per_unit"]:
            bits.append(f"Part D gross spend per unit {_fmt(r['partd_spend_per_unit'])}")
        if r["asp_payment_limit_per_hcpcs_unit"]:
            bits.append(f"ASP payment limit per {r['asp_hcpcs_unit']} ({r['asp_hcpcs']}) {_fmt(r['asp_payment_limit_per_hcpcs_unit'], 3)}")
        if r["nadac_weighted_per_unit"] or r["nadac_simple_mean_per_unit"]:
            bits.append(f"NADAC per {r['nadac_unit'] or 'unit'} {_fmt(r['nadac_weighted_per_unit'] or r['nadac_simple_mean_per_unit'], 3)}")
        if r["partd_vs_nadac_ratio"]:
            bits.append(f"Part D/NADAC ratio {_fmt(r['partd_vs_nadac_ratio'])}")
        if r["asp_vs_nadac_per_mg"]:
            bits.append(f"ASP/NADAC per mg {_fmt(r['asp_vs_nadac_per_mg'])}")
        if r["ira_mfp_per_30day"]:
            bits.append(f"IRA MFP per 30 days {_fmt(r['ira_mfp_per_30day'])} (effective {r['ira_mfp_effective']})")
        val = _num(r["partd_spend_per_unit"])
        out.append(_row(r["company"], "drug_gtn_proxy", r["drug"], r["year"], "; ".join(bits) + ".", val,
                        "USD per Part D unit" if val is not None else "USD",
                        t, n, r["source"], r["source_row"], st, loc, _table_cite(t, r["source_row"], r["source"]),
                        _first_url(r["source"]) or "", partd_spend_per_unit=val,
                        asp_payment_limit_per_hcpcs_unit=_num(r["asp_payment_limit_per_hcpcs_unit"]),
                        asp_hcpcs=r["asp_hcpcs"], nadac_per_unit=_num(r["nadac_weighted_per_unit"] or r["nadac_simple_mean_per_unit"]),
                        partd_vs_nadac_ratio=_num(r["partd_vs_nadac_ratio"]), asp_vs_nadac_per_mg=_num(r["asp_vs_nadac_per_mg"]),
                        ira_mfp_per_30day=_num(r["ira_mfp_per_30day"]), basis_note=r["basis_note"]))
    return out


def _drug_set(ticker):
    """Drug keys for a ticker: gtn tables by company plus case_sets products."""
    ds = set()
    for f in ("gtn_proxy.csv", "gtn_exposure.csv"):
        for _, r in _read(VER / f):
            if (r.get("company") or "").upper() == ticker:
                ds.add(r["drug"].lower())
    ds.update(case_sets.products(ticker))
    return sorted(ds)


def _wac_rows(toks, maker):
    t = "tables/wac_increases.csv"
    rows = [(n, r) for n, r in _read(TAB / "wac_increases.csv") if _drug_match(toks, r["drug"])]
    groups = defaultdict(list)
    for n, r in rows:
        groups[(r["drug"].lower(), r["wac_effective_date"], r["wac_increase_amount"] if r["wac_increase_amount"] != r["wac_effective_date"][:4] else "", "" if r["wac_increase_amount"] == r["wac_effective_date"][:4] else r["wac_after_increase"])].append((n, r))
    facts = _facts_lookup(t, [g[0][0] for g in groups.values()])
    out = []
    for (drug, date, amt, after), g in groups.items():
        n, r = g[0]
        a, af = _num(amt), _num(after)
        loc, st = _loc_status(t, n, facts, "unverified_raw")
        if r["wac_increase_amount"].strip() == date[:4]:
            # the 2020 CHHS file is column-shifted in the raw table: the amount cell holds the year
            text = (f"{drug} WAC increase event effective {date} ({r['product_desc'][:100]}): the 2020 source file is "
                    "misaligned in this table, so the increase amount and new WAC are not usable.")
            out.append(_row(maker.get(drug, ""), "wac_event", drug, date, text, None, "", t, n, r["source"],
                            r["source_row"], "unreliable_raw", loc, _table_cite(t, r["source_row"], r["manufacturer"]),
                            r["source"], n_ndc=len(g), manufacturer=r["manufacturer"]))
            continue
        pct = round(100 * a / (af - a), 1) if a is not None and af and af > a else None
        text = (f"{drug} WAC increase effective {date}: +{_fmt(amt)} to {_fmt(after)} per unit"
                + (f" (+{pct}%)" if pct is not None else "") + f"; {r['product_desc'][:120]}"
                + (f"; reported factors: {r['cost_increase_factors'][:150]}" if r["cost_increase_factors"] else "") + ".")
        out.append(_row(maker.get(drug, ""), "wac_event", drug, date, text, a, "USD per unit (WAC increase)",
                        t, n, r["source"], r["source_row"], st, loc, _table_cite(t, r["source_row"], r["manufacturer"]),
                        r["source"], wac_after=af, wac_increase_pct=pct, n_ndc=len(g), manufacturer=r["manufacturer"]))
    return out


def _nadac_rows(toks, ticker_label, quarterly):
    t = "tables/nadac_history.csv"
    rows = [(n, r) for n, r in _read(TAB / "nadac_history.csv") if _drug_match(toks, r["drug"])]
    # latest as_of date inside each year (or quarter); average over the NDCs observed on that date
    best = {}
    for n, r in rows:
        d = r["as_of_date"]
        if not d or _num(r["nadac_per_unit"]) is None:
            continue
        per = f"{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}" if quarterly else d[:4]
        key = (r["drug"].lower(), r["match_kind"], per)
        if key not in best or d > best[key][0]:
            best[key] = (d, [])
        if d == best[key][0]:
            best[key][1].append((n, r))
    facts = _facts_lookup(t, [v[1][0][0] for v in best.values()])
    out = []
    for (drug, kind, per), (d, g) in best.items():
        vals = [float(r["nadac_per_unit"]) for _, r in g]
        n, r = g[0]
        mean = sum(vals) / len(vals)
        loc, st = _loc_status(t, n, facts, "unverified_raw")
        text = (f"{drug} ({kind.replace('_', ' ')}) NADAC {per}, as of {d}: mean {mean:,.3f} per {r['pricing_unit']} over "
                f"{len(vals)} NDC(s), range {min(vals):,.3f} to {max(vals):,.3f}. Simple mean, strengths may differ.")
        out.append(_row(ticker_label.get(drug, ""), "nadac", drug, per, text, round(mean, 4), f"USD per {r['pricing_unit']}",
                        t, n, r["source"], r["source_row"], st, loc, _table_cite(t, r["source_row"], "CMS NADAC"),
                        r["source"], as_of=d, n_ndc=len(vals), min_value=min(vals), max_value=max(vals), match_kind=kind))
    return out


def _partd_rows(toks, ticker_label):
    t = "tables/partd_by_year.csv"
    rows = [(n, r) for n, r in _read(TAB / "partd_by_year.csv")
            if _drug_match(toks, r["drug"]) and r["mftr"] == "Overall" and r["grain"] == "year" and _num(r["spend_per_unit"]) is not None]
    facts = _facts_lookup(t, [n for n, _ in rows])
    out = []
    for n, r in rows:
        loc, st = _loc_status(t, n, facts, "unverified_raw")
        text = (f"{r['drug']} {r['period']} Medicare Part D ({r['brand']}): gross spend per dosage unit {_fmt(r['spend_per_unit'])}, "
                f"per claim {_fmt(r['spend_per_claim'])}, total spend {_fmt(r['total_spend'], 0)}, claims {_fmt(r['claims'], 0)} "
                "(before manufacturer rebates).")
        out.append(_row(ticker_label.get(r["drug"].lower(), ""), "partd_support", r["drug"].lower(), r["period"], text,
                        _num(r["spend_per_unit"]), "USD per dosage unit", t, n, r["source"], r["source_row"], st, loc,
                        _table_cite(t, r["source_row"], "CMS Part D Spending by Drug"), _first_url(r["source"]),
                        spend_per_claim=_num(r["spend_per_claim"]), total_spend=_num(r["total_spend"])))
    return out


def _partb_rows(toks, ticker_label):
    t = "tables/partb_asp_quarterly.csv"
    rows = [(n, r) for n, r in _read(TAB / "partb_asp_quarterly.csv")
            if _drug_match(toks, r["drugs"]) and _num(r["payment_limit"]) is not None]
    latest = {}
    for n, r in rows:  # Q4 of each year plus the newest quarter per HCPCS
        latest[(r["hcpcs"], r["quarter"])] = (n, r)
    keep = {}
    for (h, q), v in latest.items():
        mx = max(qq for (hh, qq) in latest if hh == h)
        if q.endswith("Q4") or q == mx:
            keep[(h, q)] = v
    facts = _facts_lookup(t, [v[0] for v in keep.values()])
    out = []
    for (h, q), (n, r) in keep.items():
        loc, st = _loc_status(t, n, facts, "unverified_raw")
        drug = next((d for d in _tokens(r["drugs"]) if any(d == x or d.startswith(x + "-") for x in toks)),
                    _tokens(r["drugs"])[0])
        text = (f"{drug} Part B ASP payment limit {q}: {_fmt(r['payment_limit'], 3)} per {r['dosage']} "
                f"({r['hcpcs']}, {r['short_desc']}). ASP is net of most rebates; payment limit is ASP plus 6%.")
        out.append(_row(ticker_label.get(drug, ""), "partb_asp", drug, q, text, _num(r["payment_limit"]),
                        f"USD per {r['dosage']}", t, n, r["source"], r["source_row"], st, loc,
                        _table_cite(t, r["source_row"], "CMS ASP pricing file"), _first_url(r["source"]) or r["source"],
                        hcpcs=r["hcpcs"]))
    return out


# ------------------------------------------------------------------ filings

def _excerpt(text, m, width=560):
    """Window of page text starting at a line start shortly before the phrase match."""
    start = max(0, m.start() - 200)
    nl = text.rfind("\n", max(0, start - 80), m.start())
    if nl != -1:
        start = nl + 1
    else:
        sp = text.find(" ", start)
        start = sp + 1 if 0 <= sp < m.start() else start
    ex = text[start:start + width]
    return ex.strip()


def _filing_rows(ticker, limit):
    seen, hits = set(), []
    for q in FILING_QUERIES:
        for dts, grade in ((FILING_TYPES, None), (["transcript"], "B")):
            for h in cite.search_pages(q, ticker=ticker, doc_type=dts, grade_min=grade, k=8):
                if h["source_id"] in seen:
                    continue
                seen.add(h["source_id"])
                hits.append((q, h))
    out, dup = [], set()
    for q, h in hits:
        p = cite.get_page(h["doc_id"], h["page_no"])
        if not p:
            continue
        m = PHRASES.search(p["text"])
        if not m:
            continue
        ex = _excerpt(p["text"], m)[:560]
        if len(ex) < 160:
            continue
        nums = len(re.findall(r"\d[\d,\.]*", ex))
        table = nums >= 8 and bool(TABLE_HINT.search(ex))
        sig = re.sub(r"\W+", " ", ex[:90]).lower()
        if not table and sig in dup:
            continue
        dup.add(sig)
        if not cite.verify_quote(ex, h["doc_id"], h["page_no"]):
            continue
        d = cite.db().execute("SELECT period, doc_type FROM docs WHERE doc_id=?", (h["doc_id"],)).fetchone()
        out.append((table, nums, _row(ticker, "filing_sales_deduction_table" if table else "filing_statement", "",
                                        d["period"] or "", ex, None, "", "", 0, "", "",
                                        "quote_verified", h["source_id"], h["citation"], h["url"], doc_type=d["doc_type"],
                                        query=q.strip('"'), quote=ex)))
        out[-1][2]["quote_grade"] = h["quote_grade"] if d["doc_type"].startswith("transcript") else ""
        out[-1][2]["license"] = h["license"] or ""
        out[-1][2]["table"] = ""
    out.sort(key=lambda x: x[2]['period'], reverse=True)  # newest first
    out.sort(key=lambda x: not x[0])  # tables first (stable)
    return [r for _, _, r in out[:limit]]


# ------------------------------------------------------------------ public

def gtn_series(ticker=None, drug=None, k=200):
    """Gross-to-net rows for a ticker and/or a drug (lower-case key, 'a/b' pairs allowed)."""
    if not ticker and not drug:
        raise ValueError("give ticker and/or drug")
    ticker = ticker.upper() if ticker else None
    toks = _tokens(drug) if drug else []
    maker_of = {}
    for f in ("gtn_proxy.csv", "gtn_exposure.csv"):
        for _, r in _read(VER / f):
            maker_of.setdefault(r["drug"].lower(), r["company"])
    if ticker:
        toks = sorted(set(toks) | set(_drug_set(ticker)))
    tickers = [ticker] if ticker else sorted({maker_of[d] for d in maker_of if _drug_match(toks, d)})

    groups = []
    for tk in tickers:
        groups.append(_company_rows(tk.upper()))
    groups.append(_exposure_rows(ticker, toks if not ticker else []))
    groups.append(_proxy_rows(ticker, toks if not ticker else []))
    if toks:
        groups.append(_wac_rows(toks, maker_of))
        groups.append(_nadac_rows(toks, maker_of, quarterly=not ticker))
        groups.append(_partb_rows(toks, maker_of))
        groups.append(_partd_rows(toks, maker_of))
    data_rows = [r for g in groups for r in g]
    if not data_rows:
        return []
    filing = []
    for tk in tickers:
        filing += _filing_rows(tk, 12 if ticker else 6)
    rows = []
    # priority under the k cap: filings and company-level first, then exposure/proxy, then events and supports
    prio = {"company_list_vs_net": 0, "filing_sales_deduction_table": 0, "filing_statement": 1, "drug_gtn_exposure": 0,
            "drug_gtn_proxy": 1, "wac_event": 2, "partb_asp": 2, "nadac": 3, "partd_support": 3}
    pool = sorted(data_rows + filing, key=lambda r: prio[r["kind"]])
    rows = pool[:k]
    rows.sort(key=lambda r: (r["drug"], r["period"], r["kind"]))
    return rows


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    drug = None
    if "--drug" in a:
        i = a.index("--drug")
        drug = a[i + 1]
        del a[i:i + 2]
    ticker = a[0] if a else None
    if not ticker and not drug:
        print("usage: python -m agent.moat.case_gtn TICKER [--drug NAME]")
        return 2
    rows = gtn_series(ticker, drug)
    if not rows:
        print(f"no gross-to-net data for ticker={ticker} drug={drug}")
        return 1
    for r in rows:
        print(f"{r['drug'] or '-':14} {r['period']:>11} {r['kind']:28} {r['text'][:110]} | {r['citation'][:60]} | {r['locator'][:50]}")
    print(f"{len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
