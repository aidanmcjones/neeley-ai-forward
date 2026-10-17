"""Scan the 10 companies' own 8-Ks in R2 (neeley-ai-forward) for deal announcements -> page-marked md + rows."""
import gzip, json, re
from agent.tenk import Store
from agent.moat.common import write
from agent.moat.deals_lib import *

s = Store()
keys = [o["Key"] for o in s.s3.get_paginator("list_objects_v2").paginate(Bucket=s.bucket, Prefix="index/8k_")
        .build_full_result().get("Contents", [])]
out = open("data/moat/scratch/deals_own8k_rows.jsonl", "w")
n = 0
for k in keys:
    rows = [json.loads(l) for l in s.s3.get_object(Bucket=s.bucket, Key=k)["Body"].read().decode().splitlines() if l.strip()]
    for r in rows:
        if r["filingDate"] < "2020-01-01" or not re.search(r"1\.01|2\.01|7\.01|8\.01|1\.02", r.get("items", "")):
            continue
        raw = s.get(r["storage_key"])
        if not raw:
            continue
        txt = gzip.decompress(raw).decode("utf-8", "ignore")
        bt = re.sub(r"\s+", " ", txt)
        if not re.search(r"license|collaborat|acquire|merger|asset purchase|royalt", bt[:6000], re.I):
            continue
        if re.search(r"Item 2\.02", bt[:3000]) and not re.search(r"Item (?:1\.01|2\.01)", bt[:3000]):
            continue
        sents = sentences(bt)
        dt = deal_type(bt[:6000])
        if dt == "acquisition":
            tot, q = acq_econ(sents)
            a, tg = parties_acq(bt[:2500])
            if not tot:
                continue
            up, eq, ms = tot, None, None
        else:
            up, eq, ms, tot, q = econ(sents, dt)
            if up is None and tot is None:
                continue
            a = tg = ""
        n += 1
        rel = f"deals/{r['filingDate']}_{r['accessionNumber']}_own.md"
        pages = [(None, txt[:60000])]
        md = f"<!-- source: {r['source']} | acc={r['accessionNumber']} filer={r['company']} filed={r['filingDate']} -->\n\n[[page 1 | printed ?]]\n\n{txt[:60000]}\n"
        write("deals", rel, md, group="deals", doc_type="8-K own", form="8-K", filed=r["filingDate"], source_url=r["source"], pages=1, upload=False)
        q = (q or "")
        if len(q) > 300:
            am = amounts(q)
            lo = max(0, (am[0][1] if am else 0) - 150)
            q = q[lo:lo + 300]
        row = dict(date=r["filingDate"], deal_type=dt, acquirer_or_licensee=a, target_or_licensor=tg, asset="",
                   modality=classify(bt[:6000], MODS), therapeutic_area=classify(bt[:6000], TAS), indication="",
                   stage_at_deal=stage_of(bt[:6000]), upfront_usd_m=up, equity_usd_m=eq, milestones_usd_m=ms,
                   total_potential_usd_m=tot, royalty_terms=royalty_text(sents), territory=terr(bt[:6000]),
                   deal_value_to_peak_sales_note=peak_note(sents), source=r["source"], source_row=f"{rel.split('/')[1]} [[page 1 | printed ?]]",
                   quote=q, confidence="medium:role", _src="own8k", _filer=r["company"])
        out.write(json.dumps(row) + "\n")
print("own 8-K deal rows", n)
