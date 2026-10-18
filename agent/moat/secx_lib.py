import csv, io, re, json
import agent.tenk as tenk
tenk.MIN_INTERVAL = 0.5
from agent.tenk import sec_get, ticker_map
from agent.corpus import filings, paged_text, render, folder_docs
from agent.moat.common import write, note_gap, OUT, ROOT

TICKERS = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]
_cik = None


def ciks():
    global _cik
    if _cik is None:
        m = ticker_map()
        _cik = {t: m[t] for t in TICKERS}
    return _cik


def url_of(cik, acc, name):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{name}"


def corpus_urls():
    urls = set()
    with open(ROOT / "data/corpus/manifest.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            urls.add(r["source_url"])
    mdir = OUT / "manifests"
    for p in mdir.glob("*.jsonl"):
        if p.stem == "secx":
            continue
        for ln in p.read_text().splitlines():
            if ln.strip():
                try:
                    urls.add(json.loads(ln)["source_url"])
                except Exception:
                    pass
    return urls


def save_doc(rel, url, raw, ticker, doc_type, f, group="companies"):
    pages = paged_text(raw)
    hdr = f"<!-- source: {url} | ticker: {ticker} type: {doc_type} form: {f.get('form')} filed: {f.get('filed')} -->\n"
    body = render(pages, hdr)
    return write("secx", rel, body, ticker=ticker, group=group, doc_type=doc_type, form=f.get("form"),
                 period=f.get("period"), filed=f.get("filed"), source_url=url, pages=len(pages),
                 pages_with_folio=sum(1 for p, _ in pages if p))


def write_csv(rel, cols, rows, doc_type="table"):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    write("secx", rel, buf.getvalue(), group="tables", doc_type=doc_type, source_url="SEC EDGAR")
    print("wrote", rel, len(rows), flush=True)
