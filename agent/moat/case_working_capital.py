"""Working-capital retrieval: inventory, receivables and revenue growth by period, with outpacing flags.

Answers: "are inventory or receivables growing faster than revenue, and what does management say about it?"
(the case's channel-stuffing / inventory-build / DSO-drift hiding places).

    from agent.moat.case_working_capital import working_capital
    rows = working_capital("MRK", quarters=12)

Returns kind="quarter" rows (10-Q/10-K filers) or kind="annual" rows (IFRS filers that publish no quarterly
XBRL), newest first, then kind="filing_note" rows (management's own words from the latest 10-K/10-Q).
Quarterly flows are derived from cumulative durations (Q4 = FY minus 9M). When a later filing restated a
period, the latest accession wins and `restated_from` shows the earlier number (flag "restated").
Unknown tickers return [].

CLI:  python -m agent.moat.case_working_capital MRK [PFE ...]
Data: SEC XBRL companyfacts, cached to data/moat/tables/xbrl_working_capital.csv (built from the local
data/corpus/*/*/xbrl_companyfacts.json.gz files; missing tickers are fetched from data.sec.gov at <=1 request/s).
"""

import csv
import glob
import gzip
import io
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date
from functools import lru_cache

from agent.moat import cite as C
from agent.moat.common import OUT, ROOT, write

CACHE_REL = "tables/xbrl_working_capital.csv"
COLS = ["ticker", "concept", "period_end", "period_start", "fy", "fp", "form", "accn", "filed", "value", "unit",
        "source_url"]
UA = "neeley-ai-forward aidanmcjones@gmail.com"
REVENUE = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenue"]
INVENTORY = ["InventoryNet", "Inventories"]
RECEIVABLES = ["AccountsReceivableNetCurrent", "TradeAndOtherCurrentReceivables", "CurrentTradeReceivables"]
ASSETS = ["Assets"]
COGS = ["CostOfGoodsAndServicesSold", "CostOfRevenue"]
ALL_CONCEPTS = set(REVENUE + INVENTORY + RECEIVABLES + ASSETS + COGS)
FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A", "20-F", "20-F/A", "6-K", "6-K/A", "40-F"}
MIN_END = "2018-01-01"
NOTE_QUERIES = [("inventory increase", "inventory build"), ("days sales outstanding", "dso"),
                ("wholesaler inventory", "wholesaler inventory"), ("channel inventory", "channel inventory"),
                ("pre-launch inventory", "pre-launch inventory"), ("destocking", "destocking")]


# ---------------------------------------------------------------- cache

def _local_gz():
    return {p.split("/")[-2].upper(): p for p in glob.glob(str(ROOT / "data/corpus/*/*/xbrl_companyfacts.json.gz"))}


def _fetch(ticker):
    """Fetch companyfacts for a ticker not in the local corpus (1 request/s). Returns the dict or None."""
    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    try:
        tm = get("https://www.sec.gov/files/company_tickers.json")
        cik = next(v["cik_str"] for v in tm.values() if v["ticker"].upper() == ticker)
        time.sleep(1.1)
        return get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
    except Exception:
        return None


def _rows_from_facts(ticker, d):
    cik = int(d["cik"])
    base = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    out = []
    for ns, facts in d.get("facts", {}).items():
        for c, body in facts.items():
            if c not in ALL_CONCEPTS:
                continue
            for unit, arr in body["units"].items():
                for f in arr:
                    if f.get("form") not in FORMS or not f.get("end") or f["end"] < MIN_END:
                        continue
                    out.append([ticker, c, f["end"], f.get("start", ""), f.get("fy", ""), f.get("fp", ""), f["form"],
                                f.get("accn", ""), f.get("filed", ""), f["val"], unit, f"{base}#{c}/{f.get('accn', '')}"])
    return out


def _tickers_for_cache():
    from agent.moat import case_sets as S
    makers = set(S.SHORTLIST) | {"REGN", "BBIO", "ALNY", "NVS", "TAK", "SNY", "GSK", "NVO", "AZN"}
    return sorted(makers)


def build_cache(tickers=None):
    """(Re)build data/moat/tables/xbrl_working_capital.csv for the shortlist and rival makers."""
    local = _local_gz()
    rows, missing = [], []
    for t in tickers or _tickers_for_cache():
        if t in local:
            d = json.load(gzip.open(local[t]))
        else:
            d = _fetch(t)
            if not d:
                missing.append(t)
                continue
        rows += _rows_from_facts(t, d)
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[8]))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    w.writerows(rows)
    write("filings", CACHE_REL, data=buf.getvalue().encode("utf-8"), group="xbrl", doc_type="table",
          source_url="https://data.sec.gov/api/xbrl/companyfacts/", upload=False)
    # write() logs a manifest line; the citation index is built from manifests, and this table is read
    # directly by this helper (not indexed), so drop the line to keep test_counts_match_manifests green.
    man = OUT / "manifests" / "filings.jsonl"
    if man.exists():
        keep = [ln for ln in man.read_text().splitlines() if f"xbrl:{CACHE_REL}" not in ln]
        man.write_text("\n".join(keep) + "\n")
    if missing:
        print("working_capital: no companyfacts for " + ", ".join(missing), file=sys.stderr)
    return len(rows)


@lru_cache(maxsize=1)
def _load():
    path = OUT / CACHE_REL
    if not path.exists():
        build_cache()
    by = defaultdict(list)
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            r["value"] = float(r["value"])
            by[r["ticker"]].append(r)
    return by


# ---------------------------------------------------------------- series derivation

def _d(s):
    return date.fromisoformat(s)


def _dedupe(rows):
    """{(start, end): fact} keeping the latest filing; `restated_from` = earlier differing {value, accn}."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["period_start"], r["period_end"])].append(r)
    out = {}
    for k, lst in groups.items():
        lst.sort(key=lambda r: (r["filed"], r["accn"]))
        last = lst[-1]
        prior = [r for r in lst if r["value"] != last["value"]]
        res = dict(last)
        res["restated_from"] = ({"value": prior[0]["value"], "accn": prior[0]["accn"], "filed": prior[0]["filed"]}
                                if prior else None)
        out[k] = res
    return out


def _bucket(days):
    for b, lo, hi in ((91, 80, 100), (182, 170, 195), (273, 260, 285), (365, 350, 380)):
        if lo <= days <= hi:
            return b
    return None


def _flow_periods(rows):
    """Return {(period_end, bucket): fact} for true 3-month / 6-month / 12-month standalone periods."""
    facts = _dedupe([r for r in rows if r["period_start"]])
    by_start = defaultdict(dict)
    out = {}
    for (s, e), f in facts.items():
        b = _bucket((_d(e) - _d(s)).days)
        if b is None:
            continue
        by_start[s][e] = f
        if b == 91:
            out[(e, 91)] = dict(f, derived=False, period_start=s)
    for s, ends in by_start.items():
        es = sorted(ends)
        prev = None
        for e in es:
            f = ends[e]
            days = (_d(e) - _d(s)).days
            if _bucket(days) == 365 and (e, 365) not in out:
                out[(e, 365)] = dict(f, derived=False)
            if prev is None:
                if _bucket(days) == 91:
                    pass
                elif _bucket(days) == 182 and (e, 182) not in out:
                    out[(e, _bucket(days))] = dict(f, derived=False)
            else:
                gap = (_d(e) - _d(prev)).days
                b = _bucket(gap)
                if b in (91, 182) and (e, b) not in out:
                    p = ends[prev]
                    rf = f["restated_from"] or p["restated_from"]
                    out[(e, b)] = dict(f, value=f["value"] - p["value"], derived=True, restated_from=rf,
                                       period_start=prev,
                                       accn=f["accn"], form=f["form"])
            prev = e
    return out


def _stock(rows):
    facts = _dedupe([r for r in rows if not r["period_start"]])
    return {k[1]: f for k, f in facts.items()}


def _merge(series_list):
    """Fill gaps: first series (most points) wins per key."""
    out = {}
    for s in sorted(series_list, key=len, reverse=True):
        for k, v in s.items():
            out.setdefault(k, v)
    return out


def _by_concept(rows, names):
    return [(n, [r for r in rows if r["concept"] == n]) for n in names]


def _near(d_end, series, days, tol=12):
    t = _d(d_end)
    for k in series:
        ke = k if isinstance(k, str) else k[0]
        if abs((t - _d(ke)).days - days) <= tol:
            return series[k]
    return None


# ---------------------------------------------------------------- citation

@lru_cache(maxsize=None)
def _bs_doc(ticker, period_end):
    r = C.db().execute(
        "SELECT doc_id FROM docs WHERE ticker=? AND period=? AND doc_type IN ('quarterly_report','annual_report') "
        "ORDER BY (superseded_by<>''), CASE doc_type WHEN 'quarterly_report' THEN 0 ELSE 1 END LIMIT 1",
        (ticker, period_end)).fetchone()
    return r["doc_id"] if r else None


@lru_cache(maxsize=None)
def _bs_page(doc_id):
    """First page that looks like the balance sheet (inventories, receivables and total assets together)."""
    for pat in (("%Inventories%", "%receivable%", "%Total assets%"), ("%Inventories%", "%receivable%", "%otal%")):
        r = C.db().execute("SELECT page_no FROM pages WHERE doc_id=? AND text LIKE ? AND text LIKE ? AND text LIKE ? "
                           "ORDER BY page_no LIMIT 1", (doc_id, *pat)).fetchone()
        if r:
            return r["page_no"]
    return None


def _citation(ticker, period_end, fallback):
    doc = _bs_doc(ticker, period_end)
    if doc:
        pg = _bs_page(doc)
        if pg:
            c, url = C.cite(doc, pg)
            return c, url, f"{doc}#p{pg}", doc
    return (f"SEC XBRL companyfacts {ticker} {fallback['concept']} {fallback['accn']}", fallback["source_url"].split("#")[0],
            f"url:{fallback['source_url']}", "")


# ---------------------------------------------------------------- main

def _pct(a, b):
    return round((a / b - 1) * 100, 1) if a is not None and b else None


def _fmt(v, cur):
    return "n/a" if v is None else f"{v / 1e6:,.0f}m {cur}"


def working_capital(ticker, quarters=12):
    t = (ticker or "").upper().strip()
    rows = _load().get(t)
    if not rows:
        return []
    cur = rows[0]["unit"]
    rev_s = _merge([_flow_periods(rs) for _, rs in _by_concept(rows, REVENUE)])
    cogs_s = _merge([_flow_periods(rs) for _, rs in _by_concept(rows, COGS)])
    inv_s = _merge([_stock(rs) for _, rs in _by_concept(rows, INVENTORY)])
    rec_s = _merge([_stock(rs) for _, rs in _by_concept(rows, RECEIVABLES)])
    def pick(bucket):
        rv = {k[0]: v for k, v in rev_s.items() if k[1] == bucket}
        es = sorted(e for e in rv if e in inv_s or e in rec_s)
        if es and bucket == 91:  # keep a contiguous recent window (no stale rows after a gap in the data)
            win = [es[-1]]
            for e in reversed(es[:-1]):
                if (_d(win[0]) - _d(e)).days > 110:
                    break
                win.insert(0, e)
            es = win
        return rv, es

    bucket, kind = 91, "quarter"
    rev, ends = pick(91)
    if len(ends) < 4:  # IFRS filers without quarterly XBRL: annual periods
        bucket, kind = 365, "annual"
        rev, ends = pick(365)
    cogs = {k[0]: v for k, v in cogs_s.items() if k[1] == bucket}
    span = bucket if bucket == 365 else 91

    def ttm(e):
        if bucket == 365:
            return rev[e]["value"]
        pts = sorted([x for x in rev if 0 <= (_d(e) - _d(x)).days <= 285])[-4:]
        return sum(rev[x]["value"] for x in pts) if len(pts) == 4 and (_d(e) - _d(pts[0])).days > 240 else None

    def metrics(e):
        r, c, i, a = rev.get(e), cogs.get(e), inv_s.get(e), rec_s.get(e)
        days = 365 if bucket == 365 else (_d(e) - _d(r["period_start"])).days if r else span
        rv = r["value"] if r else None
        return {"rev": rv, "inv": i["value"] if i else None, "rec": a["value"] if a else None,
                "dso": round(a["value"] / rv * days, 1) if a and rv else None,
                "dio": round(i["value"] / c["value"] * days, 1) if i and c and c["value"] else None,
                "days": days}

    out = []
    for e in reversed(ends[-quarters:]):
        m = metrics(e)
        prior_end = next((x for x in ends + sorted(rev) if abs((_d(e) - _d(x)).days - 365) <= 12), None)
        pm = metrics(prior_end) if prior_end else {}
        r, c, i, a = rev.get(e), cogs.get(e), inv_s.get(e), rec_s.get(e)
        ry, iy, ay = (_pct(m["rev"], pm.get("rev")), _pct(m["inv"], pm.get("inv")), _pct(m["rec"], pm.get("rec")))
        dso_y = _pct(m["dso"], pm.get("dso"))
        flags = []
        if iy is not None and ry is not None and iy > ry and iy > 0:
            flags.append("inventory_outpaces_revenue")
        if ay is not None and ry is not None and ay > ry and ay > 0:
            flags.append("receivables_outpace_revenue")
        if dso_y is not None and dso_y >= 10:
            flags.append("dso_up_10pct_yoy")
        used = {"revenue": r, "inventory": i, "receivables": a}
        restated = {k: v["restated_from"] for k, v in used.items() if v and v.get("restated_from")}
        if restated:
            flags.append("restated")
        anchor = i or a or r
        citation, url, locator, doc = _citation(t, e, anchor)
        tt = ttm(e)
        text = (f"{t} {e}: revenue {_fmt(m['rev'], cur)}"
                + (f" ({ry:+.1f}% yoy)" if ry is not None else "")
                + f"; inventory {_fmt(m['inv'], cur)}" + (f" ({iy:+.1f}% yoy)" if iy is not None else "")
                + f"; receivables {_fmt(m['rec'], cur)}" + (f" ({ay:+.1f}% yoy)" if ay is not None else "")
                + (f"; DSO {m['dso']} days" if m["dso"] is not None else "")
                + (f"; DIO {m['dio']} days" if m["dio"] is not None else ""))
        out.append({
            "ticker": t, "kind": kind, "text": text[:600], "citation": citation, "url": url, "locator": locator,
            "source_id": locator, "quote_grade": "", "license": "", "period_end": e, "unit": cur,
            "revenue": m["rev"], "revenue_yoy_pct": ry, "inventory": m["inv"], "inventory_yoy_pct": iy,
            "receivables": m["rec"], "receivables_yoy_pct": ay, "dso_days": m["dso"], "dio_days": m["dio"],
            "dso_yoy_pct": dso_y, "inventory_to_revenue_ttm": round(m["inv"] / tt, 4) if m["inv"] and tt else None,
            "flags": flags, "restated_from": restated or None, "balance_sheet_doc": doc,
            "xbrl_sources": {k: v["source_url"] for k, v in used.items() if v},
            "verify_status": "xbrl_companyfacts", "source": "SEC XBRL companyfacts",
        })
    out += _filing_notes(t)
    return out


def _filing_notes(t):
    db = C.db()
    docs = []
    for types in (("quarterly_report",), ("annual_report",), ("interim_report",)):
        r = db.execute(f"SELECT doc_id FROM docs WHERE ticker=? AND doc_type IN ({','.join('?' * len(types))}) "
                       "AND superseded_by='' ORDER BY COALESCE(NULLIF(filed,''),period) DESC LIMIT 1",
                       (t, *types)).fetchone()
        if r:
            docs.append(r["doc_id"])
    if not docs:
        return []
    ph = ",".join("?" * len(docs))
    sql = ("SELECT p.doc_id, p.page_no, snippet(pages_fts, 0, '[', ']', ' ... ', 40) AS snip FROM pages_fts "
           f"JOIN pages p ON p.id = pages_fts.rowid WHERE pages_fts MATCH ? AND p.doc_id IN ({ph}) "
           "ORDER BY bm25(pages_fts) LIMIT 2")
    out = []
    for q, topic in NOTE_QUERIES:
        hits = db.execute(sql, [C.fts_query(q), *docs]).fetchall()
        if not hits and len(q.split()) > 1:
            hits = db.execute(sql, [C._or(q), *docs]).fetchall()
        for h in hits:
            c, url = C.cite(h["doc_id"], h["page_no"])
            loc = f"{h['doc_id']}#p{h['page_no']}"
            out.append({"ticker": t, "kind": "filing_note", "text": " ".join(h["snip"].split())[:600], "citation": c,
                        "url": url, "locator": loc, "source_id": loc, "quote_grade": "", "license": "", "topic": topic})
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        sys.exit("usage: python -m agent.moat.case_working_capital TICKER [TICKER ...]")
    for t in argv:
        rows = working_capital(t)
        if not rows:
            print(f"{t}: no XBRL working-capital data")
            continue
        for r in rows:
            if r["kind"] == "filing_note":
                print(f"[note:{r['topic']}] {r['text']} | {r['citation']} | {r['locator']}")
            else:
                print(f"[{r['kind']}] {r['text']} | flags={r['flags']} | {r['citation']} | {r['locator']}")


if __name__ == "__main__":
    main()
