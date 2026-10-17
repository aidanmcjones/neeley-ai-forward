"""Helpers for the filings verifier."""
import csv, json, re
from pathlib import Path

ROOT = Path(".")
MAN = [json.loads(l) for l in open("data/moat/manifests/filings.jsonl")]
PANEL = list(csv.DictReader(open("data/moat/tables/product_revenue_quarterly.csv")))
RESTATE = list(csv.DictReader(open("data/moat/tables/restatements.csv")))

ACC_FORM = {}
for r in PANEL:
    ACC_FORM[r["accession"]] = r["form"]
ACC_PERIOD = {}
for r in PANEL:
    a = r["accession"]
    if r["period_end"] > ACC_PERIOD.get(a, ""):
        ACC_PERIOD[a] = r["period_end"]


CORPUS = list(csv.DictReader(open("data/corpus/manifest.csv")))


def acc_doc(acc):
    """Local page-marked doc for an accession (moat filings stream, else data/corpus), or None."""
    nd = acc.replace("-", "")
    for m in MAN + CORPUS:
        if m.get("source_url") and f"/{nd}/" in m["source_url"] and m["path"].endswith(".md"):
            return m["path"]
    return None


PAGE_RE = re.compile(r"\[\[page (\d+) \| printed ([^\]]*)\]\]")


def pages(path):
    txt = open(path).read()
    parts = PAGE_RE.split(txt)
    out = []
    for i in range(1, len(parts), 3):
        out.append((int(parts[i]), parts[i + 1].strip(), parts[i + 2]))
    return out


def fmt_variants(v_usd, scale=1e6):
    """Printed forms of a USD value in millions (e.g. 1,234 or 1,234.5)."""
    m = v_usd / scale
    vs = set()
    if abs(m - round(m)) < 1e-6:
        vs.add(f"{abs(round(m)):,}")
    vs.add(f"{abs(m):,.1f}")
    return vs


def find_value(path, v_usd, near=None):
    """Return list of (page, printed) where the value prints (optionally near a keyword)."""
    hits = []
    for pg, printed, body in pages(path):
        for f in fmt_variants(v_usd):
            pat = r"(?<![\d,.])\$?\s?\(?" + re.escape(f) + r"(?![\d,]|\.\d)"
            for mm in re.finditer(pat, body):
                if near:
                    win = body[max(0, mm.start() - 3000): mm.end() + 300]
                    if not re.search(near, win, re.I):
                        continue
                hits.append((pg, printed))
                break
    return sorted(set(hits))
