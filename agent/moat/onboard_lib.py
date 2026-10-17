"""Shared pieces for agent.moat.onboard_company and agent.moat.onboard_drug.

Everything an onboarding run writes goes through agent.moat.common.write with stream "onboard_<KEY>", so the rows
land in data/moat/manifests/onboard_<KEY>.jsonl with the standard manifest columns and the citation index picks
them up (python -m agent.moat.index --add). Per-entity tables go to data/moat/onboard/<KEY>/<name>.csv and always
carry `source` and `source_row` columns. Step progress goes to data/moat/onboard/<KEY>/steps.jsonl and gaps to
data/moat/gaps/onboard.jsonl (note_gap), so a failed step never stops the run.
"""

import csv
import io
import json
import re
import time
from pathlib import Path

import requests

from agent.moat.common import OUT, ROOT, MANIFEST_COLS, note_gap, now, write

EXT = ROOT / "data" / "external"
POLICY_GOV = OUT / "policy_gov"
CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/onboard_cache")
UA_BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/141.0 Safari/537.36"
H = {"User-Agent": "Neeley AI Forward hackathon"}
STOP = {"inc", "corp", "corporation", "co", "plc", "ltd", "llc", "company", "the", "holdings", "group", "sa", "ag",
        "nv", "a/s", "as", "pharmaceuticals", "pharmaceutical", "therapeutics", "biosciences", "sciences", "of", "and",
        "limited", "gmbh", "bv", "b.v.", "s.a.", "srl", "pty", "kk", "k.k.", "international", "global", "usa", "us",
        "pharma", "holding", "laboratories", "labs", "biotech", "biologics", "manufacturing", "research",
        "services", "trust", "investments", "finance", "capital", "ireland", "uk", "de", "la", "le", "spa",
        "s.p.a.", "s.l.", "ab", "oy", "nl", "sas", "sarl", "japan", "china", "canada", "france", "germany", "india",
        "brasil", "brazil", "mexico", "italia", "espana", "spain", "australia", "korea", "taiwan", "ltda", "inc.",
        "corp.", "ltd.", "llc.", "healthcare", "health", "medical", "products", "development", "technologies",
        "technology", "bio", "life", "new", "north", "south", "america", "american", "europe", "european", "asia"}
ONBOARD_STREAM = "onboard_{key}"
CORP_SUFFIX = re.compile(r"(?i)\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|gmbh|ag|sa|s\.a|"
                         r"sas|sarl|s\.r\.l|srl|spa|s\.p\.a|bv|b\.v|nv|n\.v|plc|pty|ulc|lp|l\.p|llp|a/s|ab|oy|kk|k\.k|"
                         r"dac|ug|kg|sl|s\.l|ltda|bvba|sprl|aps|as)\b\.?")


# ---------------------------------------------------------------- names and aliases

def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def company_key(name):
    """Distinctive first word of a registrant name: 'REGENERON PHARMACEUTICALS, INC.' -> 'regeneron'."""
    words = [w for w in re.split(r"[\s,.&()/]+", str(name).lower()) if w and w not in STOP]
    return words[0] if words else str(name).lower().split()[0]


def aliases(name, former=(), subsidiaries=(), max_subs=25):
    """Lowercase name keys used to find the company in FDA, CMS and government documents.

    The registrant key comes first, then former names, then distinctive first words of Exhibit 21 subsidiaries
    that do not already contain the registrant key (acquired companies such as 'kite' or 'celgene'). Short or
    generic words are dropped so the alias list stays precise."""
    out = []

    def add(k):
        k = k.strip().lower()
        if len(k) >= 4 and k not in STOP and k not in out and not k.isdigit():
            out.append(k)

    add(company_key(name))
    for f in former:
        add(company_key(f))
    n = 0
    for s in subsidiaries:
        if not CORP_SUFFIX.search(str(s)):  # header or note rows ('Document and Entity Information') are not entities
            continue
        k = company_key(s)
        if k in out or len(k) < 5 or not re.fullmatch(r"[a-z][a-z\-']+", k):
            continue
        add(k)
        n += 1
        if n >= max_subs:
            break
    return out


def alias_regex(al):
    return re.compile(r"\b(" + "|".join(re.escape(a) for a in al) + r")\b", re.I) if al else re.compile(r"$^")


def resolve_cik(ticker, rows):
    """rows: company_tickers_exchange.json 'data' as dicts with cik, name, ticker, exchange. Exact ticker first,
    then the share-class-stripped form (BRK.B -> BRK-B)."""
    t = ticker.upper().strip()
    by = {str(r["ticker"]).upper(): r for r in rows if r.get("ticker")}
    for cand in (t, t.replace(".", "-"), t.replace("-", ".")):
        if cand in by:
            r = by[cand]
            return {"ticker": t, "cik": int(r["cik"]), "name": r["name"], "exchange": r.get("exchange") or ""}
    return None


def tickers_exchange():
    from agent.tenk import sec_get
    p = CACHE / "company_tickers_exchange.json"
    if p.exists() and time.time() - p.stat().st_mtime < 86400:
        data = json.loads(p.read_text())
    else:
        data = sec_get("https://www.sec.gov/files/company_tickers_exchange.json", as_json=True)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
    return [dict(zip(data["fields"], r)) for r in data["data"]]


# ---------------------------------------------------------------- run log and writes

class Run:
    """One onboarding run: stream name, step log, time budget, counts."""

    def __init__(self, key, budget_min=60, kind="company"):
        self.key, self.kind = key, kind
        self.stream = ONBOARD_STREAM.format(key=key)
        self.dir = OUT / "onboard" / key
        self.dir.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()
        self.budget = budget_min * 60
        self.steps = []
        self.counts = {"docs": 0, "pages": 0, "tables": 0, "rows": 0}

    def left(self):
        return self.budget - (time.time() - self.t0)

    def log(self, step, status, **kw):
        row = {"step": step, "status": status, "t": round(time.time() - self.t0, 1), "at": now(), **kw}
        self.steps.append(row)
        with (self.dir / "steps.jsonl").open("a") as f:
            f.write(json.dumps(row, default=str) + "\n")
        print(f"[{row['t']:7.1f}s] {self.key} {step}: {status} {json.dumps(kw, default=str)[:300]}", flush=True)

    def gap(self, item, reason):
        note_gap("onboard", self.key, item, str(reason)[:500])

    def step(self, name, fn, *a, min_left=30, **kw):
        if self.left() < min_left:
            self.log(name, "skipped", reason=f"time budget: {round(self.left())}s left")
            self.gap(name, "skipped: time budget exhausted")
            return None
        t = time.time()
        self.log(name, "start")
        try:
            res = fn(*a, **kw)
            self.log(name, "done", seconds=round(time.time() - t, 1), result=res)
            return res
        except Exception as e:
            self.log(name, "failed", seconds=round(time.time() - t, 1), error=repr(e)[:400])
            self.gap(name, f"step failed: {e!r}")
            return None

    def doc(self, rel, text, **meta):
        row = write(self.stream, rel, text, **meta)
        self.counts["docs"] += 1
        self.counts["pages"] += meta.get("pages") or 0
        return row

    def table(self, name, rows, cols=None, source_url=None, ticker=None):
        """Write data/moat/onboard/<KEY>/<name>.csv. Every row must carry source and source_row."""
        if not rows:
            return 0
        cols = cols or list(dict.fromkeys(k for r in rows for k in r))
        for c in ("source", "source_row"):
            if c not in cols:
                cols.append(c)
        buf = io.StringIO()
        w = csv.DictWriter(buf, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        write(self.stream, f"onboard/{self.key}/{name}.csv", buf.getvalue(), ticker=ticker, group="onboard",
              doc_type="table", source_url=source_url)
        self.counts["tables"] += 1
        self.counts["rows"] += len(rows)
        return len(rows)

    def finish(self, extra=None):
        summ = {"key": self.key, "kind": self.kind, "seconds": round(time.time() - self.t0, 1), **self.counts,
                "steps": {s["step"]: s["status"] for s in self.steps if s["status"] != "start"}, **(extra or {})}
        (self.dir / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
        return summ


def manifest_rows(key):
    p = OUT / "manifests" / f"{ONBOARD_STREAM.format(key=key)}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def check_manifest_row(row):
    """Schema check used by tests: every manifest column present, doc_id = '<ticker or group>:<rel>'."""
    missing = [c for c in MANIFEST_COLS if c not in row]
    if missing:
        return f"missing {missing}"
    if not row["path"].startswith("data/moat/"):
        return "path outside data/moat"
    rel = row["path"][len("data/moat/"):]
    if row["doc_id"] != f"{row['ticker'] or row['group']}:{rel}":
        return "doc_id does not match ticker/group and path"
    if not row["stream"].startswith("onboard_"):
        return "stream is not onboard_*"
    return ""


# ---------------------------------------------------------------- HTTP helpers

def http_get(url, params=None, headers=None, timeout=90, tries=3):
    last = None
    for a in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers or H, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
            if r.status_code in (404, 403):
                break
        except Exception as e:
            last = repr(e)
        time.sleep(2 * (a + 1))
    raise RuntimeError(f"{url}: {last}")


MEDICAID = "https://data.medicaid.gov/api/1/datastore/query/{ds}/0"


def medicaid_query(ds, conds, limit=5000, cap=40000):
    out, off = [], 0
    while off < cap:
        p = {"limit": limit, "offset": off}
        for i, (k, v, op) in enumerate(conds):
            p[f"conditions[{i}][property]"] = k
            p[f"conditions[{i}][value]"] = v
            p[f"conditions[{i}][operator]"] = op
        res = http_get(MEDICAID.format(ds=ds), params=p, timeout=120).json()["results"]
        out += res
        if len(res) < limit:
            break
        off += limit
        time.sleep(0.3)
    return out


def nadac_rows(brand, years=(2025, 2026), tag=None):
    from agent.moat.pricing_medicaid import NADAC
    rows = []
    for y in years:
        ds = NADAC[y]
        for r in medicaid_query(ds, [("ndc_description", brand.upper() + "%", "like")]):
            rows.append(dict(drug=tag or slug(brand), match_term=brand.upper(), year_dataset=y,
                             **{k: r.get(k) for k in ["ndc_description", "ndc", "nadac_per_unit", "effective_date",
                                                     "pricing_unit", "pharmacy_type_indicator", "as_of_date"]},
                             source=f"https://data.medicaid.gov/dataset/{ds}",
                             source_row=f"ndc={r.get('ndc')}|effective_date={r.get('effective_date')}|as_of={r.get('as_of_date')}|ds={y}"))
    return rows


def sdud_rows(brand, years=(2023, 2024, 2025), tag=None):
    from agent.moat.pricing_medicaid import SDUD
    rows = []
    for y in years:
        ds = SDUD[y]
        for r in medicaid_query(ds, [("state", "XX", "="), ("product_name", brand.upper()[:10] + "%", "like")]):
            rows.append(dict(drug=tag or slug(brand), ndc=r["ndc"], product_name=r["product_name"].strip(),
                             utilization_type=r["utilization_type"], year=r["year"], quarter=r["quarter"],
                             units_reimbursed=r["units_reimbursed"], prescriptions=r["number_of_prescriptions"],
                             total_amount_reimbursed=r["total_amount_reimbursed"],
                             medicaid_amount_reimbursed=r["medicaid_amount_reimbursed"],
                             suppression_used=r["suppression_used"], source=f"https://data.medicaid.gov/dataset/{ds}",
                             source_row=f"state=XX|ndc={r['ndc']}|{r['utilization_type']}|{r['year']}Q{r['quarter']}"))
    return rows


# ---------------------------------------------------------------- CMS spend files (data/external)

_spend = {}


def spend_frames():
    import pandas as pd
    if not _spend:
        d = pd.read_csv(EXT / "partd_spending_dy24.csv", dtype=str)
        d["spend_2024"] = pd.to_numeric(d["Tot_Spndng_2024"], errors="coerce").fillna(0)
        b = pd.read_csv(EXT / "partb_spending_dy24.csv", dtype=str)
        b["spend_2024"] = pd.to_numeric(b["Tot_Spndng_2024"], errors="coerce").fillna(0)
        _spend["d"], _spend["b"] = d, b
    return _spend["d"], _spend["b"]


PARTD_URL = ("https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/"
             "medicare-part-d-spending-by-drug (data/external/partd_spending_dy24.csv)")
PARTB_URL = ("https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/"
             "medicare-part-b-spending-by-drug (data/external/partb_spending_dy24.csv)")


def spend_rows(brand, part="D", tag=None):
    d, b = spend_frames()
    df = d if part == "D" else b
    pat = rf"^{re.escape(brand.split()[0])}\b"
    hit = df[df["Brnd_Name"].fillna("").str.contains(pat, case=False, regex=True)]
    rows = []
    for i, r in hit.iterrows():
        row = {k: v for k, v in r.items() if k != "spend_2024"}
        row.update(drug=tag or slug(brand), source=PARTD_URL if part == "D" else PARTB_URL,
                   source_row=f"line={i + 2}|Brnd_Name={r['Brnd_Name']}|Mftr_Name={r.get('Mftr_Name', '')}"
                              + (f"|HCPCS={r['HCPCS_Cd']}" if "HCPCS_Cd" in r else ""))
        rows.append(row)
    return rows


# ---------------------------------------------------------------- government documents already saved

FORCE_BY_DIR = {"cms": "IRA", "wh": "MFN", "tariff": "tariff"}
PAGE_RE = re.compile(r"\[\[page (\d+) \| printed ([^\]]+)\]\]")


def gov_mentions(pattern, tag, max_per_doc=6):
    """Every page of data/moat/policy_gov/** that names the company or drug: one row per (doc, page) with the
    sentence around the first hit. Page ids follow the index convention (doc_id#p<page_no>)."""
    from agent.moat.index import moat_rows
    by_path = {r["path"]: d for d, r in moat_rows().items()}
    rows = []
    for p in sorted(POLICY_GOV.rglob("*.md")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        src = re.search(r"source: (\S+)", text)
        parts = PAGE_RE.split(text)
        pages = [("1", "1", text)] if len(parts) == 1 else [(parts[i], parts[i + 1], parts[i + 2])
                                                            for i in range(1, len(parts), 3)]
        rel = p.relative_to(ROOT).as_posix()
        n = 0
        for pno, printed, body in pages:
            m = pattern.search(body)
            if not m:
                continue
            flat = " ".join(body.split())
            m2 = pattern.search(flat)
            a = max(0, flat.rfind(". ", 0, m2.start()) + 2) if m2 else 0
            b = flat.find(". ", m2.end()) if m2 else -1
            quote = flat[a:(b + 1 if b > 0 else a + 400)][:600]
            doc_id = by_path.get(rel, "")
            rows.append({"key": tag, "force": FORCE_BY_DIR.get(p.parent.name, p.parent.name), "doc": rel,
                         "doc_id": doc_id, "page_no": pno, "printed_page": printed.strip(), "matched": m.group(0),
                         "quote": quote, "source": src.group(1) if src else rel,
                         "source_row": f"{doc_id or rel}#p{pno}"})
            n += 1
            if n >= max_per_doc:
                break
    return rows


# ---------------------------------------------------------------- Orange / Purple Book applicants

_brands = None


def brand_products():
    """(brand, ingredient, appl_no, applicant, modality) for every Rx NDA and 351(a) BLA (agent.gap_data logic)."""
    global _brands
    if _brands is None:
        from agent.gap_data import brand_products as bp
        _brands = bp(EXT)
    return _brands


def applicant_products(al_re):
    """Products whose Orange/Purple Book applicant matches the company aliases (gap_data.company_for logic,
    with the alias regex in place of the hard-coded COMPANIES table)."""
    out = {}
    for brand, ing, appl, applicant, modality in brand_products():
        if isinstance(applicant, str) and al_re.search(applicant) and not re.search(r"KGAA|EMD SERONO", applicant, re.I):
            out.setdefault(str(brand).upper(), {"brand": str(brand).upper(), "ingredient": str(ing), "appl_no": appl,
                                                "applicant": applicant, "modality": modality})
    return out


def product_for_brand(brand):
    """Orange/Purple Book row for one brand (exact first word match), or None."""
    b = brand.upper().split()[0]
    for row in brand_products():
        if isinstance(row[0], str) and row[0].upper().split()[0] == b:
            return {"brand": row[0], "ingredient": str(row[1]), "appl_no": row[2], "applicant": row[3],
                    "modality": row[4]}
    return None


# ---------------------------------------------------------------- RxClass

RXCLASS = "https://rxnav.nlm.nih.gov/REST/rxclass"


def rx_classes(ingredient, source="ATC"):
    rela = {"ATC": None, "FDASPL": "has_EPC"}[source]
    p = {"drugName": ingredient.split()[0].lower(), "relaSource": source}
    if rela:
        p["relas"] = rela
    info = http_get(f"{RXCLASS}/class/byDrugName.json", params=p, timeout=30).json() \
        .get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
    return list({c["rxclassMinConceptItem"]["classId"]: c["rxclassMinConceptItem"]["className"] for c in info}.items())


def rx_members(class_id, source="ATC"):
    p = {"classId": class_id, "relaSource": source}
    if source == "FDASPL":
        p["rela"] = "has_EPC"
    ms = http_get(f"{RXCLASS}/classMembers.json", params=p, timeout=30).json() \
        .get("drugMemberGroup", {}).get("drugMember", [])
    return sorted({m["minConcept"]["name"].lower() for m in ms})
