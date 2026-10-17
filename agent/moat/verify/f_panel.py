"""Re-check a stratified sample of product_revenue_quarterly.csv against re-fetched XBRL instances and the page-marked text."""
import csv, os, random, re, collections
os.environ.setdefault("SEC_USER_AGENT", "Neeley AI Forward hackathon aidan@justinianhq.com")
import agent.tenk
agent.tenk.MIN_INTERVAL = 0.5
from agent.tenk import sec_get
from lxml import etree
from agent.moat.verify.f_lib import PANEL, acc_doc, find_value

random.seed(7)
REVQ = re.compile(r"^us-gaap:Revenue")
strata = collections.defaultdict(list)
for r in PANEL:
    if not REVQ.match(r["concept"]) or not r["product_member"]:
        continue
    geo = "US" if r["geography"] == "country:US" else "total" if r["geography"] == "" else None
    if geo:
        strata[(r["ticker"], r["form"], geo)].append(r)
sample = []
for k, rows in sorted(strata.items()):
    accs = sorted({r["accession"] for r in rows})
    pick = random.sample(accs, min(2, len(accs)))
    pool = [r for r in rows if r["accession"] in pick]
    sample += random.sample(pool, min(16, len(pool)))
print("sample", len(sample), "instances", len({r["source"] for r in sample}))

ns_x, ns_d = "http://www.xbrl.org/2003/instance", "http://xbrl.org/2006/xbrldi"
cache = {}


def facts(url):
    if url in cache:
        return cache[url]
    root = etree.fromstring(sec_get(url).encode(), parser=etree.XMLParser(huge_tree=True, recover=True))
    nsmap = {}
    ctx = {}
    for c in root.iter(f"{{{ns_x}}}context"):
        dims = tuple(sorted((m.get("dimension").split(":")[-1], (m.text or "").strip()) for m in c.iter(f"{{{ns_d}}}explicitMember")))
        ctx[c.get("id")] = (c.findtext(f".//{{{ns_x}}}startDate"), c.findtext(f".//{{{ns_x}}}endDate"), dims)
    out = collections.defaultdict(set)
    for el in root.iter():
        if not isinstance(el.tag, str) or el.get("contextRef") not in ctx:
            continue
        q = etree.QName(el)
        pre = "us-gaap" if "fasb.org" in (q.namespace or "") else "company"
        s, e, d = ctx[el.get("contextRef")]
        try:
            out[(f"{pre}:{q.localname}", s, e, d)].add(float(el.text))
        except (TypeError, ValueError):
            pass
    cache[url] = out
    return out


res = []
text_done = 0
for r in sample:
    d = tuple(sorted(tuple(x.split("=", 1)) for x in r["source_row"].split("|")))
    try:
        f = facts(r["source"])
        vals = f.get((r["concept"], r["period_start"], r["period_end"], d), set())
        st = "verified" if float(r["value_usd"]) in vals else ("mismatch" if vals else "not_found")
        xv = ";".join(str(v) for v in sorted(vals))
    except Exception as ex:
        st, xv = "fetch_error", repr(ex)[:80]
    page, tstat = "", ""
    doc = acc_doc(r["accession"])
    if doc and text_done < 80 and abs(float(r["value_usd"])) >= 1e6:
        w = re.sub(r"(?i)member$", "", r["product_member"].split(":")[-1])
        w = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", w).split()[0]
        hits = find_value(doc, float(r["value_usd"]), near=re.escape(w[:10]))
        tstat = "found_in_text" if hits else "not_found_in_text"
        page = ";".join(f"p{p}/printed {pr}" for p, pr in hits[:2])
        text_done += 1
    res.append({"ticker": r["ticker"], "accession": r["accession"], "form": r["form"], "concept": r["concept"],
                "product_member": r["product_member"], "geography": r["geography"] or "total", "period_start": r["period_start"],
                "period_end": r["period_end"], "value_usd": r["value_usd"], "xbrl_status": st, "xbrl_values": xv,
                "text_doc": doc or "", "text_status": tstat, "printed_page": page, "source": r["source"]})
with open("data/moat/scratch/product_revenue_checks.csv", "w") as fh:
    w = csv.DictWriter(fh, list(res[0].keys()))
    w.writeheader()
    w.writerows(res)
print(collections.Counter(x["xbrl_status"] for x in res), collections.Counter(x["text_status"] for x in res))
