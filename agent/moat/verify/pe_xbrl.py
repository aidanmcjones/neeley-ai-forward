"""Peers item 3: spot check peer_product_revenue_xbrl.csv against the XBRL instance documents on EDGAR.

Samples 72 rows weighted to product members and 10-K rows, downloads each cited instance (cached under
/tmp/pev/xbrl), and re-finds the fact by concept, period and the full dimension set. Also audits the whole
table for non-revenue concepts and the period convention (no Q4 derivation is present).
"""
import io
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from agent.moat.common import write
from agent.moat.verify.pe_lib import ROOT

CACHE = Path("/tmp/pev/xbrl")
UA = {"User-Agent": "Neeley AI Forward research aidan@justinianhq.com"}
XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"
PRODUCT_WORDS = re.compile(r"Amvuttra|ONPATTRO|GIVLAARI|OXLUMO|Eylea|ELYEA|LIBTAYO|Praluent|Evkeeza|Inmazeb|Ronapreve|"
                           r"Attruby|Kevzara|Dupixent|Veopoz|Lynozyfic|Leqvio|Qfitlia|Zolgensma|ProductMember", re.I)


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / url.split("/")[-2] / url.split("/")[-1]
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers=UA)
        f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        time.sleep(0.2)
    return f


def facts(path):
    root = ET.parse(path).getroot()
    ctx = {}
    for c in root.iter(XBRLI + "context"):
        p = c.find(XBRLI + "period")
        s, e = p.find(XBRLI + "startDate"), p.find(XBRLI + "endDate")
        dims = {m.get("dimension").split(":")[-1]: m.text.strip() for m in c.iter(XBRLDI + "explicitMember")}
        ctx[c.get("id")] = (s.text if s is not None else None, e.text if e is not None else None, dims)
    out = []
    for el in root:
        cr = el.get("contextRef")
        if cr is None or el.text is None:
            continue
        tag = el.tag
        ns, local = tag[1:].split("}")
        out.append((local, ctx[cr], el.text.strip()))
    return out


def dims_of(r):
    d = dict(x.split("=", 1) for x in r.source_row.split("|"))
    return d


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/peer_product_revenue_xbrl.csv")
    rev = d.concept.str.contains("RevenueFromContractWithCustomer|^us-gaap:Revenues$|RevenueFromCollaborative")
    d["concept_is_revenue"] = rev
    prod = d.product_member.fillna("").str.contains(PRODUCT_WORDS) & rev
    s1 = d[prod & (d.form == "10-K")].sample(30, random_state=3)
    s2 = d[prod & (d.form == "10-Q")].sample(24, random_state=3)
    s3 = d[~prod].sample(18, random_state=3)
    s = pd.concat([s1, s2, s3])
    rows = []
    cache = {}
    for i, r in s.iterrows():
        if r.source not in cache:
            try:
                cache[r.source] = facts(fetch(r.source))
            except Exception as e:  # noqa: BLE001
                cache[r.source] = e
        F = cache[r.source]
        if isinstance(F, Exception):
            rows.append(dict(row_index=i, status="fetch_failed", detail=str(F)[:120]))
            continue
        want = dims_of(r)
        local = r.concept.split(":")[-1]
        hits = [(c, v) for (n, c, v) in F if n == local and c[1] == r.period_end and c[0] == r.period_start
                and {k: v2.split(":")[-1] for k, v2 in c[2].items()} == {k: v2.split(":")[-1] for k, v2 in want.items()}]
        if not hits:
            st, val = "fact_not_found", None
        else:
            val = float(hits[0][1])
            st = "match" if abs(val - r.value_usd) < 0.5 else "value_mismatch"
        rows.append(dict(row_index=i, status=st, xbrl_value=val))
    c = pd.DataFrame(rows).set_index("row_index")
    out = s.join(c)
    out["days_inclusive"] = (pd.to_datetime(out.period_end) - pd.to_datetime(out.period_start)).dt.days + 1
    out["period_label"] = out.apply(lambda r: "FY" if r.days > 350 else ("9M YTD" if r.days > 260 else
                                    ("6M YTD" if r.days > 170 else ("quarter" if r.days > 80 else "other"))), axis=1)
    print(out.status.value_counts())
    print(out[out.status != "match"][["ticker", "accession", "concept", "product_member", "period_start",
                                       "period_end", "value_usd", "xbrl_value", "status"]].to_string())
    buf = io.StringIO()
    out.to_csv(buf, index=True, index_label="raw_row_index")
    write("verify_peers", "verified/peers/peer_product_revenue_xbrl_checks.csv", buf.getvalue(), group="tables",
          doc_type="table", quality="verified", source_url="EDGAR XBRL instance documents (per row `source`)")
    audit = dict(rows=len(d), non_revenue_concept_rows=int((~rev).sum()),
                 non_revenue_concepts=d[~rev].concept.value_counts().to_dict(),
                 q4_rows=int(((d.days > 80) & (d.days < 95) & d.period_end.str.endswith("12-31")).sum()),
                 days_convention="end minus start (exclusive); 2021-01-01..2021-12-31 = 364",
                 ytd_rows=int(((d.days > 170) & (d.days < 350)).sum()),
                 product_name_column=False,
                 sample=len(out), sample_match=int((out.status == "match").sum()))
    print(json.dumps(audit, indent=1))
    Path("/tmp/pev/xbrl_audit.json").write_text(json.dumps(audit))


if __name__ == "__main__":
    main()
