"""Coverage check of the moat database against the case's "Source material" list, for the 10 shortlist companies.

    PYTHONPATH=. venv python -m agent.moat.case_sources [--no-fda]

Writes data/moat/CASE_SOURCES.md and prints it. Gap list also goes to GAPS_JSON.
build(fda=True) returns (markdown, gaps, rows). Columns: 1 annual reports, 2 last four calls, 3 latest 10-Q/interim,
4 rival filings and statements, 5 FDA labels and openFDA currency, 6 Orange/Purple Book + FDA calendar, 7 10-K patent table.
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

from agent.moat import case_sets as CS
from agent.moat.cite import db, search_pages

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "data" / "moat" / "verified"
OUT = ROOT / "data" / "moat" / "CASE_SOURCES.md"
GAPS_JSON = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/case_gaps.json")
GRADE = {"A": 1, "B": 2, "C": 3, "D": 4}
FDA_URL = "https://api.fda.gov/drug/label.json"


def _csv(rel):
    p = V / rel
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _yr(p):
    m = re.search(r"(20\d\d)", p or "")
    return int(m.group(1)) if m else 0


def _pkey(p):
    """Sortable key for periods like 2026Q3, 2026H1, 2025FY, 2025-12-31."""
    p = p or ""
    m = re.match(r"(20\d\d)[QH](\d)", p)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.match(r"(20\d\d)-(\d\d)", p)
    if m:
        return (int(m.group(1)), (int(m.group(2)) + 2) // 3)
    return (_yr(p), 9)


def docs(ticker, types):
    q = "SELECT * FROM docs WHERE ticker=? AND doc_type IN (%s)" % ",".join("?" * len(types))
    return [dict(r) for r in db().execute(q, [ticker, *types])]


def annual_reports(ticker):
    """Latest two annual reports (main doc per FY; no exhibits, duplicates, finance reports or glossy)."""
    rows = [d for d in docs(ticker, ["annual_report"]) if not re.search(r"_d2|ex15|finance_report", d["doc_id"])]
    by = {}
    for d in rows:
        by.setdefault(_yr(d["period"]), []).append(d)
    return [sorted(by[y], key=lambda x: (len(x["doc_id"]), x["doc_id"]))[0] for y in sorted(by, reverse=True)[:2]]


def grade_reasons():
    out = {}
    for f in ("calls/transcript_grades.csv", "calls/transcript_grades_wave3.csv"):
        for r in _csv(f):
            out[(r["ticker"], r["quarter"])] = r["reason"]
    return out


def last_calls(ticker, reasons, n=4):
    by = {}
    for d in docs(ticker, ["transcript"]):
        by.setdefault(d["period"], []).append(d)
    res = []
    for per in sorted(by, key=_pkey, reverse=True)[:n]:
        best = sorted(by[per], key=lambda d: (GRADE.get(d["quote_grade"], 9), d["superseded_by"] != "", d["doc_id"]))[0]
        res.append((per, best, reasons.get((ticker, per), "")))
    return res


def latest_quarter_doc(ticker):
    ds = docs(ticker, ["interim_report"] if ticker in CS.FOREIGN_FILERS else ["quarterly_report"])
    ds.sort(key=lambda d: _pkey(d["period"]), reverse=True)
    return ds[0] if ds else None


def latest_label(drug):
    ds = [dict(d) for d in db().execute(
        "SELECT * FROM docs WHERE drug=? AND doc_type IN ('fda_label_version','fda_label')", (drug,))]
    v = [d for d in ds if d["doc_type"] == "fda_label_version" and d["period"]]
    if v:
        return max(v, key=lambda d: d["period"])
    return ds[0] if ds else None


def openfda_latest(brand):
    url = FDA_URL + "?" + urllib.parse.urlencode({"search": f'openfda.brand_name:"{brand}"', "limit": 5}, safe=':"')
    req = urllib.request.Request(url, headers={"User-Agent": "neeley-ai-forward aidanmcjones@gmail.com"})
    with urllib.request.urlopen(req, timeout=20) as r:
        js = json.load(r)
    best = ""
    for x in js.get("results", []):
        names = [n.lower() for n in x.get("openfda", {}).get("brand_name", [])]
        if brand.lower() in names:
            best = max(best, x.get("effective_time", ""))
    return f"{best[:4]}-{best[4:6]}-{best[6:8]}" if best else ""


def _d(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def build(fda=True):
    reasons = grade_reasons()
    stm = _csv("peers/rival_product_statements.csv")
    loe = _csv("pipeline/loe_calendar.csv")
    cal = _csv("pipeline/fda_calendar.csv") + _csv("pipeline/fda_calendar_wave2.csv")
    gaps = []
    label_status = {}

    def gap(company, column, item, fix, free=True):
        gaps.append({"company": company, "column": column, "item": item, "fix": fix, "free": free})

    def label_cell(co, drug):
        if drug in label_status:
            return label_status[drug]
        lab = latest_label(drug)
        if not lab:
            label_status[drug] = f"{drug}: GAP no label"
            gap(co, "5 FDA label", drug, f"DailyMed SPL for {drug} (https://dailymed.nlm.nih.gov)", True)
            return label_status[drug]
        per = lab["period"] or "no date"
        status = "unchecked"
        if fda:
            try:
                time.sleep(1.0)
                ofd = openfda_latest(drug.replace("-", " ").upper())
                mine, theirs = _d(per), _d(ofd)
                if not ofd:
                    status = "unchecked (openFDA no match)"
                elif mine and theirs and (theirs - mine).days > 60:
                    status = f"STALE (openFDA {ofd})"
                    gap(co, "5 FDA label", drug, f"ours {per}, openFDA {ofd}: refetch SPL via {FDA_URL} or DailyMed", True)
                else:
                    status = f"current (openFDA {ofd})"
            except Exception:
                status = "unchecked (API fail)"
        label_status[drug] = f"{drug}: {lab['doc_id']} ({per}) {status}"
        return label_status[drug]

    def loe_cell(co, drug):
        l = [r for r in loe if r["brand"].lower().replace(" ", "-") == drug.lower()]
        c = [r for r in cal if r["drug"].lower().replace(" ", "-") == drug.lower()]
        if not l and not c:
            gap(co, "6 Orange/Purple Book", drug,
                "FDA Orange Book data files (https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files) "
                "or Purple Book (https://purplebooksearch.fda.gov)", True)
            return f"{drug}: GAP"
        bits = []
        if l:
            r = l[0]
            ob = r["orange_book_last_patent"] or r["purple_book_ref_exclusivity"] or r["exclusivity_latest_date"] or "no date"
            bits.append(f"loe {len(l)} row(s), first {ob}")
        if c:
            bits.append(f"fda_calendar {len(c)} row(s), latest {max(x['date'] for x in c)}")
        return f"{drug}: " + "; ".join(bits)

    rows = []
    for t in CS.SHORTLIST:
        co = t
        cell = {"co": f"{t} ({CS.COMPANY_NAMES[t]})"}
        ars = annual_reports(t)
        parts = []
        for w in ("FY2025", "FY2024"):
            d = next((x for x in ars if str(_yr(x["period"])) == w[2:]), None)
            if d:
                parts.append(f"{w}: {d['doc_id']} (filed {d['filed']})")
            else:
                parts.append(f"{w}: GAP")
                gap(co, "1 annual reports", w, f"{t} {w} annual report from SEC EDGAR / company IR", True)
        cell["ar"] = "<br>".join(parts)

        calls = last_calls(t, reasons)
        parts = []
        for per, d, rs in calls:
            g = d["quote_grade"] or "ungraded"
            q = "quotable" if g in ("A", "B") else "NOT quotable"
            bb = " bloomberg_licensed" if d["license"] == "bloomberg_licensed" else ""
            parts.append(f"{per}: {d['doc_id']} grade {g}{bb}, {q}" + (f" [{rs}]" if rs else ""))
            if g not in ("A", "B"):
                gap(co, "2 calls", f"{per} call best grade {g}",
                    "official IR transcript (free where posted) or Bloomberg transcript (paywalled)", False)
        if len(calls) < 4:
            parts.append("GAP: fewer than four quarters")
            gap(co, "2 calls", "fewer than 4 quarters", "company IR transcripts", True)
        cell["calls"] = "<br>".join(parts)

        q = latest_quarter_doc(t)
        if q and _pkey(q["period"]) >= _pkey("2026Q2"):
            cell["q"] = f"{q['doc_id']} ({q['period']})"
        else:
            cell["q"] = f"GAP (latest {q['doc_id'] if q else 'none'})"
            gap(co, "3 latest 10-Q", "2026Q2", f"{t} 2026Q2 10-Q/interim from EDGAR or IR", True)

        seen = {}
        for r, m, note in CS.rivals(t):
            seen[(r, m)] = note
        parts, makers = [], {}
        for (r, m) in seen:
            if m == "GENERIC":
                parts.append(f"{r}: generic, no maker filing")
                continue
            if m not in makers:
                ar = annual_reports(m)
                ar = ar[0] if ar else None
                tr = last_calls(m, reasons, 1)
                tr = tr[0] if tr else None
                a_s = f"AR {ar['doc_id']} ({ar['period']})" if ar else "AR GAP"
                if not ar:
                    gap(co, "4 rivals", f"{m} annual report", f"{m} annual report from IR site", True)
                if m == "BOEHRINGER":
                    c_s = "no calls (private)"
                elif tr:
                    c_s = f"call {tr[1]['doc_id']} ({tr[0]}, grade {tr[1]['quote_grade'] or 'ungraded'})"
                else:
                    c_s = "call GAP"
                    gap(co, "4 rivals", f"{m} transcript", f"{m} IR call transcript (free if posted, else Bloomberg, paywalled)", False)
                makers[m] = f"{a_s}; {c_s}"
            ss = [x for x in stm if x["product"].lower() == r.lower()]
            sp = f"stmts {len(ss)}, latest {max(x['period'] for x in ss)}" if ss else "stmts 0 GAP"
            if not ss:
                gap(co, "4 rivals", f"{r} ({m}) statements",
                    f"mine {m} latest annual report and call for {r} into rival_product_statements.csv", True)
            parts.append(f"{r} [{m}]: {makers[m]}; {sp}")
        cell["rivals"] = "<br>".join(parts)

        drugs = list(CS.products(t))
        for (r, m) in seen:
            if m != "GENERIC" and r not in drugs:
                drugs.append(r)
        gens = [r for (r, m) in seen if m == "GENERIC"]
        cell["labels"] = "<br>".join([label_cell(co, d) for d in drugs] + [f"{g}: generic" for g in gens])
        cell["loe"] = "<br>".join([loe_cell(co, d) for d in drugs] + [f"{g}: generic" for g in gens])

        own = [r for r in loe if r["ticker"] == t and r["company_stated_loe"] and r["tenk_page"]]
        items = sorted({f"{r['brand']} {r['territory']} {r['company_stated_loe']} p{r['tenk_page']}" for r in own})
        fy = next((x for x in ars if _yr(x["period"]) == 2025), None)
        pages = []
        if fy:
            for qq in ("patent expiration", "compound patent"):
                pages += [h["page_no"] for h in search_pages(qq, ticker=t, doc_type="annual_report", k=60)
                          if h["doc_id"] == fy["doc_id"]]
            pages = sorted(set(pages))[:8]
        if own:
            txt = f"{len(own)} loe rows with tenk_page: " + "; ".join(items[:6]) + (" ..." if len(items) > 6 else "")
        else:
            txt = "GAP: no loe rows with company_stated_loe and tenk_page"
            gap(co, "7 10-K patent table", "loe rows with tenk_page", "re-extract patent table from FY2025 annual report", True)
        txt += f"<br>FY2025 patent pages: {pages if pages else 'GAP none found'}"
        if not pages:
            gap(co, "7 10-K patent table", "patent/exclusivity page", "locate patent section in the FY2025 annual report", True)
        cell["tenk"] = txt
        rows.append(cell)

    hdr = ["Company", "1 Annual reports", "2 Last four calls", "3 Latest 10-Q / interim", "4 Rivals (AR, call, statements)",
           "5 FDA labels (+openFDA)", "6 Orange/Purple Book, FDA calendar", "7 10-K patent table"]
    md = ["# Case source coverage (shortlist)", "",
          f"Generated {date.today()} by `python -m agent.moat.case_sources`. openFDA check: {'on' if fda else 'skipped (--no-fda)'}.", "",
          "| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for c in rows:
        md.append("| " + " | ".join([c["co"], c["ar"], c["calls"], c["q"], c["rivals"], c["labels"], c["loe"], c["tenk"]]) + " |")
    md += ["", "## Gaps", ""]
    for i, g in enumerate(gaps, 1):
        md.append(f"{i}. {g['company']} / {g['column']} / {g['item']}: {g['fix']} ({'free' if g['free'] else 'paywalled'})")
    if not gaps:
        md.append("None.")
    return "\n".join(md) + "\n", gaps, rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    md, gaps, _ = build(fda="--no-fda" not in argv)
    OUT.write_text(md, encoding="utf-8")
    try:
        GAPS_JSON.parent.mkdir(parents=True, exist_ok=True)
        GAPS_JSON.write_text(json.dumps(gaps, indent=1), encoding="utf-8")
    except OSError:
        pass
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
