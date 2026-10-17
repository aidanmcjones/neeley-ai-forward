"""Page-anchored SEC corpus for the Fine Print case (Part 1: find).

For each company: the two latest annual reports (10-K or 20-F), every 10-Q since Jan 2026, earnings 8-Ks
(Item 2.02, primary doc + every EX-99) since Jul 2025, policy 8-Ks (Items 7.01 / 8.01) since Jan 2025 that mention
MFN, tariffs, the IRA or US manufacturing, foreign filers' 6-Ks since Jul 2025 that carry results or policy news,
and the XBRL companyfacts file (revenue, inventory, receivables by period).

Unlike agent/tenk.py, page boundaries are kept: EDGAR documents mark each printed page with a page-break style, and
the printed folio sits just above it. Each page is written as
    [[page 47 | printed 39]]
so every finding can cite "10-K FY2025, p. 39". Writes data/corpus/<group>/<TICKER>/... plus manifest.jsonl.

Usage:
  python -m agent.corpus                       # every company in COMPANIES
  python -m agent.corpus --tickers BMY,JNJ
"""

import argparse
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from agent.tenk import find_sections, html_to_text, sec_get, ticker_map

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "corpus"

# ticker: group. "companies" = the case shortlist (full pack); "peers" = makers of the rival products.
COMPANIES = {
    "MRK": "companies", "BMY": "companies", "PFE": "companies", "LLY": "companies", "NVO": "companies",
    "ABBV": "companies", "JNJ": "companies", "AZN": "companies", "AMGN": "companies", "GILD": "companies",
    "NVS": "peers", "GSK": "peers", "SNY": "peers", "TAK": "peers", "REGN": "peers", "ALNY": "peers",
    "BBIO": "peers",
    # the Big 3 US drug distributors: their 10-Ks describe brand stocking and buy-ins, a check on makers' sell-in
    "MCK": "distributors", "COR": "distributors", "CAH": "distributors",
}
ANNUAL = {"10-K", "20-F"}
QUARTERLY_SINCE = "2026-01-01"
EARNINGS_SINCE = "2025-07-01"
POLICY_SINCE = "2025-01-01"
POLICY_RE = re.compile(r"most[- ]favou?red[- ]nation|\bMFN\b|tariff|Section 232|Inflation Reduction Act|"
                       r"maximum fair price|drug price negotiation|U\.S\. manufacturing|TrumpRx", re.I)
RESULTS_RE = re.compile(r"(first|second|third|fourth|full)[- ](quarter|half|year)|interim report|"
                        r"financial (report|results|statement)|Q[1-4] 20\d\d|9M 20\d\d|H1 20\d\d", re.I)
PAGE_BREAK = re.compile(r"(?is)<hr\b[^>]*page-break[^>]*>|<(?:div|p)\b[^>]*page-break-(?:before|after)\s*:\s*always[^>]*>")
FOLIO = re.compile(r"^(?:Page\s+)?((?:[A-Z]{1,2}-)?\d{1,3}|[ivxlc]{1,6})$", re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- text with pages

def paged_text(raw):
    """[(printed_folio or None, text)] for one HTML document, split on its page breaks."""
    pages = []
    for chunk in PAGE_BREAK.split(raw):
        text = html_to_text(chunk)
        if not text.strip():
            continue
        folio = None
        # strip "- 10 -" style dashes around folios (Merck)
        tail = [ln.strip().strip("-–— ") for ln in text.splitlines() if ln.strip()][-3:]
        for ln in reversed(tail):
            last = ln.split()[-1] if ln.split() else ""
            if FOLIO.match(ln) or (FOLIO.match(last) and len(ln) < 60 and "|" not in ln):
                folio = FOLIO.match(ln).group(1) if FOLIO.match(ln) else FOLIO.match(last).group(1)
                break
        pages.append((folio, text))
    # a numeric folio that breaks the sequence on both sides is a table-of-contents or table number, not a folio
    nums = [int(f) if f and f.isdigit() else None for f, _ in pages]
    for i, n in enumerate(nums):
        if n is None:
            continue
        prev = nums[i - 1] if i > 0 else None
        nxt = nums[i + 1] if i + 1 < len(nums) else None
        fits = (prev is not None and n == prev + 1) or (nxt is not None and n == nxt - 1)
        if not fits and (prev is not None or nxt is not None):
            pages[i] = (None, pages[i][1])
    return pages


def render(pages, header):
    parts = [header]
    for i, (folio, text) in enumerate(pages, 1):
        parts.append(f"\n\n[[page {i} | printed {folio or '?'}]]\n\n{text}")
    return "".join(parts) + "\n"


# ---------------------------------------------------------------- EDGAR

def filings(cik, since):
    sub = sec_get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", as_json=True)
    blocks = [sub["filings"]["recent"]]
    for page in sub["filings"].get("files", []):
        if page.get("filingTo", "9999") >= since:
            blocks.append(sec_get(f"https://data.sec.gov/submissions/{page['name']}", as_json=True))
    out = {}
    for b in blocks:
        for i, form in enumerate(b["form"]):
            if b["filingDate"][i] < since:
                continue
            acc = b["accessionNumber"][i]
            out[acc] = {"form": form, "accession": acc, "filed": b["filingDate"][i],
                        "period": b["reportDate"][i] or None, "items": b.get("items", [""] * len(b["form"]))[i] or "",
                        "primary_doc": b["primaryDocument"][i], "desc": b.get("primaryDocDescription", [""] * len(b["form"]))[i]}
    return sub, sorted(out.values(), key=lambda f: f["filed"])


def folder_docs(cik, acc):
    acc_path = acc.replace("-", "")
    idx = sec_get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_path}/index.json", as_json=True)
    return [(d["name"], f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_path}/{d['name']}")
            for d in idx["directory"]["item"]]


def quarter_label(period):
    if not period:
        return "unknown"
    y, m = period[:4], int(period[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


# ---------------------------------------------------------------- collector

class Collector:
    def __init__(self, ticker, group, cik, manifest):
        self.t, self.group, self.cik, self.manifest = ticker, group, cik, manifest
        self.dir = OUT / group / ticker
        self.done = {r["source_url"] for r in manifest.rows if r["ticker"] == ticker}

    def save(self, rel, url, raw, doc_type, meta):
        if url in self.done:
            return False
        pages = paged_text(raw)
        full = "\n\n".join(t for _, t in pages)
        header = (f"<!-- source: {url}\n     ticker: {self.t}  type: {doc_type}  form: {meta.get('form')}  "
                  f"filed: {meta.get('filed')}  period: {meta.get('period')}\n     retrieved: {now()} -->\n")
        body = render(pages, header)
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.manifest.add({
            "doc_id": f"{self.t}:{rel}", "ticker": self.t, "group": self.group, "doc_type": doc_type,
            "form": meta.get("form"), "filed": meta.get("filed"), "period": meta.get("period"),
            "accession": meta.get("accession"), "source_url": url, "retrieved_at": now(),
            "path": str(path.relative_to(ROOT)).replace("\\", "/"), "pages": len(pages),
            "pages_with_folio": sum(1 for f, _ in pages if f), "chars": len(full),
            "sha256": hashlib.sha256(body.encode()).hexdigest(), "source_quality": "official",
            "sections": find_sections(full) if doc_type == "annual_report" else None,
        })
        self.done.add(url)
        print(f"  {self.t} {rel} ({len(pages)} pages)")
        return True

    def run(self):
        sub, fs = filings(self.cik, POLICY_SINCE)  # FY2024 annual reports were filed in early 2025
        facts = sec_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{self.cik:010d}.json")
        p = self.dir / "xbrl_companyfacts.json.gz"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(gzip.compress(facts.encode()))

        annual = [f for f in fs if f["form"] in ANNUAL]
        n_annual = 2 if self.group == "companies" else 1
        for f in annual[-n_annual:]:
            fy = (f["period"] or f["filed"])[:4]
            stem = f"{f['form'].lower().replace('-', '')}_FY{fy}"
            self.fetch_primary(f, f"{stem}.md", "annual_report")
            # some 20-Fs (Novo Nordisk) keep the annual report itself in a companion document, e.g. nvo-20251231_d2.htm
            base = re.sub(r"\.htm$", "", f["primary_doc"])
            for name, url in folder_docs(self.cik, f["accession"]):
                m = re.fullmatch(rf"{re.escape(base)}_(d\d+)\.htm", name)
                if m and url not in self.done:
                    self.save(f"{stem}_{m.group(1)}.md", url, sec_get(url), "annual_report", f)

        tenqs = [f for f in fs if f["form"] == "10-Q" and f["filed"] >= QUARTERLY_SINCE]
        for f in tenqs if self.group == "companies" else tenqs[-1:]:
            self.fetch_primary(f, f"10q_{quarter_label(f['period'])}.md", "quarterly_report")
        for f in fs:
            if f["form"] == "10-Q":
                continue
            elif f["form"] == "8-K" and "2.02" in f["items"] and f["filed"] >= EARNINGS_SINCE:
                self.fetch_exhibits(f, "earnings", "earnings_release")
            elif f["form"] == "8-K" and re.search(r"7\.01|8\.01", f["items"]) and f["filed"] >= POLICY_SINCE:
                self.fetch_exhibits(f, "policy", "policy_8k", POLICY_RE)
            elif f["form"] == "6-K" and f["filed"] >= EARNINGS_SINCE:
                self.fetch_exhibits(f, "6k", "foreign_current_report", re.compile(
                    POLICY_RE.pattern + "|" + RESULTS_RE.pattern, re.I))

    def fetch_primary(self, f, rel, doc_type):
        acc_path = f["accession"].replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{acc_path}/{f['primary_doc']}"
        if url not in self.done:
            self.save(rel, url, sec_get(url), doc_type, f)

    def fetch_exhibits(self, f, sub, doc_type, must_match=None):
        try:
            docs = folder_docs(self.cik, f["accession"])
        except Exception as e:
            print(f"  skip {f['accession']}: {e}")
            return
        keep = [(n, u) for n, u in docs if n.lower().endswith((".htm", ".html", ".txt"))
                and (n == f["primary_doc"] or re.search(r"ex-?99|ex99|exhibit99|ex-99", n, re.I))
                and not n.endswith("-index.htm") and not n.endswith("-index-headers.html")]
        for name, url in keep:
            if url in self.done:
                continue
            raw = sec_get(url)
            if must_match and not must_match.search(html_to_text(raw)[:200000]):
                continue
            stem = re.sub(r"\.[a-z]+$", "", name)
            self.save(f"{sub}/{f['filed']}_{stem}.md", url, raw, doc_type, f)


class Manifest:
    def __init__(self, path):
        self.path = path
        self.rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] \
            if path.exists() else []

    def add(self, row):
        self.rows.append(row)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tickers")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(OUT / "manifest.jsonl")
    tmap = ticker_map()
    tickers = a.tickers.upper().split(",") if a.tickers else list(COMPANIES)
    for t in tickers:
        print(f"{t}...")
        try:
            Collector(t, COMPANIES.get(t, "peers"), tmap[t], manifest).run()
        except Exception as e:
            print(f"  FAILED {t}: {e}")
    print(f"manifest rows: {len(manifest.rows)}")


if __name__ == "__main__":
    main()
