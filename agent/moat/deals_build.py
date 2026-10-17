"""Merge extracted rows, dedupe, write tables/deal_comps.csv and tables/deal_benchmarks.csv via the shared writer."""
import csv, io, json, re, statistics
from datetime import date
from pathlib import Path
from agent.moat.common import write, note_gap, OUT
from agent.moat.deals_lib import amounts, sentences, stage_of

COLS = ["deal_id", "date", "deal_type", "acquirer_or_licensee", "target_or_licensor", "asset", "modality", "therapeutic_area",
        "indication", "stage_at_deal", "upfront_usd_m", "equity_usd_m", "milestones_usd_m", "total_potential_usd_m",
        "royalty_terms", "territory", "deal_value_to_peak_sales_note", "source", "source_row", "quote", "confidence", "origin"]
BAD_PARTY = re.compile(r"agreement|collaboration|license|licence|exhibit|the company|company$|we |our |purchase|amendment|option|^\d|asset|definitive|merger|clinical progress|announce|^strategic|^enter|global collab|^update", re.I)


def load(f, origin):
    p = Path(f)
    if not p.exists():
        return []
    rows = [json.loads(l) for l in p.open()]
    for r in rows:
        r["origin"] = origin
        r.pop("_acc", None)
    return rows


rows = load("data/moat/scratch/deals_8k_rows.jsonl", "edgar_8k") + load("data/moat/scratch/deals_own8k_rows.jsonl", "own_8k") + \
    load("data/moat/scratch/deals_10k_rows.jsonl", "10k_note")
pri = {"edgar_8k": 0, "own_8k": 1, "10k_note": 2}
rows.sort(key=lambda r: (pri[r["origin"]], r["date"]))


def d2(s):
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


kept = []
for r in rows:
    if r["date"] < "2020-01-01" or r["date"] > "2026-10-17":
        continue
    if r["origin"] == "10k_note":
        r["stage_at_deal"] = stage_of(r.get("quote") or "")
    for k in ("acquirer_or_licensee", "target_or_licensor"):
        v = (r.get(k) or "").strip(" ,.;")
        if BAD_PARTY.search(v) or len(v) < 3:
            v = ""
        r[k] = v
    up, tot = r.get("upfront_usd_m"), r.get("total_potential_usd_m")
    if up is None and tot is None:
        continue
    if (up and up > 150000) or (tot and tot > 400000):
        continue
    if up is not None and up < 0.05 and tot is None:
        continue
    q = (r.get("quote") or "").strip()
    if not re.search(r"\$", q):
        continue
    key = (round(up or 0, 1), round(r.get("milestones_usd_m") or 0), round(tot or 0))
    dup = False
    for k2 in kept:
        if k2["_key"] == key and key != (0, 0, 0):
            span = 400 if "10k_note" in (r["origin"], k2["origin"]) else 14
            if abs((d2(r["date"]) - d2(k2["date"])).days) <= span:
                dup = True
                for c in COLS:  # fill blanks from the duplicate
                    if c not in ("source", "source_row", "quote", "origin", "confidence", "date") and not k2.get(c) and r.get(c):
                        k2[c] = r[c]
                k2["origin"] += "+" + r["origin"] if r["origin"] not in k2["origin"] else ""
                break
    if dup:
        continue
    r["_key"] = key
    kept.append(r)
kept.sort(key=lambda r: (r["date"], r["source_row"]))
for i, r in enumerate(kept, 1):
    r["deal_id"] = f"D{i:04d}"
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=COLS, extrasaction="ignore")
w.writeheader()
for r in kept:
    w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in COLS})
write("deals", "tables/deal_comps.csv", buf.getvalue(), group="deals", doc_type="table", period="2020-2026",
      source_url="EDGAR full-text search + R2 8-K/10-K", quality="derived")
print("deal_comps rows", len(kept))

# ---------------------------------------------------------------- benchmarks


def royalty_pct(t):
    if not t:
        return None
    nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s?%|(\d+(?:\.\d+)?) percent", t) for x in x if x] if False else None
    ns = []
    for a, b in re.findall(r"(\d+(?:\.\d+)?)\s?%|(\d+(?:\.\d+)?) percent", t):
        ns.append(float(a or b))
    ns = [x for x in ns if 0 < x <= 50]
    if ns:
        return (min(ns) + max(ns)) / 2
    tl = t.lower()
    for k, v in (("low double-digit", 12), ("mid double-digit", 15), ("high double-digit", 20), ("double-digit", 15), ("low single-digit", 3),
                 ("mid single-digit", 5), ("high single-digit", 8), ("single-digit", 5), ("teens", 15)):
        if k in tl:
            return v
    return None


def quart(v):
    v = sorted(v)
    if len(v) < 2:
        return v[0], v[0], v[0]
    q = statistics.quantiles(v, n=4, method="inclusive")
    return q[0], statistics.median(v), q[2]


out = []
lic = [dict(r, therapeutic_area=r["therapeutic_area"] or "unclassified") for r in kept
       if r["deal_type"] != "acquisition" and r["deal_type"] != "royalty monetization"]
metrics = {"upfront_usd_m": lambda r: r.get("upfront_usd_m"), "total_potential_usd_m": lambda r: r.get("total_potential_usd_m"),
           "royalty_pct_mid": lambda r: royalty_pct(r.get("royalty_terms"))}
for stage in ["preclinical", "Ph1", "Ph2", "Ph3", "filed", "marketed", ""]:
    for ta in sorted(set(r["therapeutic_area"] for r in lic if r["stage_at_deal"] == stage or stage == "")) + ["ALL"]:
        grp = [r for r in lic if (r["stage_at_deal"] == stage or stage == "") and (ta == "ALL" or r["therapeutic_area"] == ta)]
        for mname, fn in metrics.items():
            vals = [(fn(r), r["deal_id"]) for r in grp if fn(r) is not None]
            if len(vals) < 3:
                continue
            q1, med, q3 = quart([v for v, _ in vals])
            out.append(dict(segment="licensing/option/co-dev", stage_at_deal=stage or "ALL", therapeutic_area=ta, metric=mname, n=len(vals),
                            q1=round(q1, 2), median=round(med, 2), q3=round(q3, 2), row_ids=" ".join(i for _, i in vals)))
# acquisitions: price vs trailing revenue where the source text gives revenue
mult = []
for r in kept:
    if r["deal_type"] != "acquisition" or not r.get("total_potential_usd_m"):
        continue
    f = OUT / "deals" / r["source_row"].split(" ")[0]
    if not f.exists():
        continue
    t = re.sub(r"\s+", " ", f.read_text())
    revs = []
    for s in sentences(t):
        if re.search(r"(?:net )?(?:revenue|sales)", s, re.I) and re.search(r"20(?:19|2\d)|trailing|last twelve|annual", s, re.I) and not re.search(r"peak|expected|project|forecast|potential|anticipate", s, re.I):
            for v, _, _ in amounts(s):
                if v >= 1:
                    revs.append((v, s))
    if revs:
        v, s = revs[0]
        m = r["total_potential_usd_m"] / v
        if 0.3 <= m <= 60 and abs(m - 1) > 0.03 and abs(v - r["total_potential_usd_m"]) > 0.5:
            mult.append((r, v, m, s))
if mult:
    ms_ = [m for _, _, m, _ in mult]
    q1, med, q3 = quart(ms_)
    out.append(dict(segment="acquisition", stage_at_deal="marketed", therapeutic_area="ALL", metric="price_to_trailing_revenue_x", n=len(ms_),
                    q1=round(q1, 2), median=round(med, 2), q3=round(q3, 2), row_ids=" ".join(r["deal_id"] for r, _, _, _ in mult)))
# acquisition equity value by stage
acq = [r for r in kept if r["deal_type"] == "acquisition" and r.get("total_potential_usd_m") and r["origin"].split("+")[0] != "10k_note"]
for stage in ["preclinical", "Ph1", "Ph2", "Ph3", "filed", "marketed", ""]:
    g = [r for r in acq if r["stage_at_deal"] == stage or stage == ""]
    if len(g) >= 3:
        q1, med, q3 = quart([r["total_potential_usd_m"] for r in g])
        out.append(dict(segment="acquisition", stage_at_deal=stage or "ALL", therapeutic_area="ALL", metric="deal_value_usd_m", n=len(g),
                        q1=round(q1, 1), median=round(med, 1), q3=round(q3, 1), row_ids=" ".join(r["deal_id"] for r in g)))
buf = io.StringIO()
bc = ["segment", "stage_at_deal", "therapeutic_area", "metric", "n", "q1", "median", "q3", "row_ids"]
w = csv.DictWriter(buf, fieldnames=bc)
w.writeheader()
w.writerows(out)
write("deals", "tables/deal_benchmarks.csv", buf.getvalue(), group="deals", doc_type="table", period="2020-2026", quality="derived")
print("benchmark rows", len(out), "acq multiples", len(mult))
