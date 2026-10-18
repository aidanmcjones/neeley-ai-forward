"""Scan R2 catalyst-lab-archive 10k/ texts (2024-2026) for agreement paragraphs with upfront economics."""
import gzip, json, os, re, sys
import boto3
from agent.tenk import Store
from agent.moat.deals_lib import *

s = Store()
c = boto3.client("s3", endpoint_url=s.s3.meta.endpoint_url, aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                 aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
keys = []
for yr in ("2024", "2025", "2026"):
    pg = c.get_paginator("list_objects_v2")
    for page in pg.paginate(Bucket="catalyst-lab-archive", Prefix=f"10k/date={yr}-"):
        keys += [o["Key"] for o in page.get("Contents", [])]
print(len(keys), "10-K keys", flush=True)
MON = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_RX = re.compile(r"\b(?:On |In |During |Effective )?" + MON + r"(?: \d{1,2},)? (20\d\d)")
MONTHS = {m: i + 1 for i, m in enumerate("January February March April May June July August September October November December".split())}
out = open("data/moat/scratch/deals_10k_rows.jsonl", "w")
nrows = 0
for i, k in enumerate(keys):
    try:
        raw = c.get_object(Bucket="catalyst-lab-archive", Key=k)["Body"].read()
        text = gzip.decompress(raw).decode("utf-8", "ignore")
    except Exception as e:
        print("ERR", k, e)
        continue
    if not re.search(r"upfront|up-front", text, re.I):
        continue
    # company name: first line pattern
    nm = re.search(r"\n\s*([A-Z][A-Za-z0-9&\.,\- ]{2,60}(?:Inc\.?|Corp\.?|Corporation|Ltd\.?|Limited|plc|N\.V\.|Holdings|Therapeutics|Pharmaceuticals))\s*\n\s*\(Exact name", text)
    comp = nm.group(1).strip() if nm else ""
    date_filed = k.split("date=")[1][:10]
    seen_par = set()
    for m in re.finditer(r"up-?front (?:payment|fee|cash payment)[^.]{0,60}\$\s?\d", text, re.I):
        a = max(0, text.rfind("\n", 0, m.start()))
        b = text.find("\n", m.end())
        par = re.sub(r"\s+", " ", text[a:b if b > 0 else m.end() + 1500]).strip()
        if len(par) < 120 or par[:80] in seen_par:
            continue
        seen_par.add(par[:80])
        dm = DATE_RX.search(par)
        if not dm:
            continue
        yr = int(dm.group(2))
        if yr < 2020:
            continue
        mon = MONTHS[dm.group(1)]
        d = f"{yr}-{mon:02d}-" + (re.search(r"(\d{1,2}),", dm.group(0)).group(1).zfill(2) if re.search(r"(\d{1,2}),", dm.group(0)) else "01")
        sents = sentences(par)
        if not re.search(r"agreement|licens", par, re.I):
            continue
        up, eq, ms, tot, quote = econ(sents, "x")
        if up is None:
            continue
        cpm = re.search(r"(?:with|and|from|to)\s+(" + ORG + r")(?=\s*\(|,|\.|\s+(?:for|to|under|pursuant|regarding|which|whereby))", par)
        cp = cpm.group(1).strip() if cpm else ""
        dt = deal_type(par)
        low = par.lower()
        recv = bool(re.search(r"\b(received|receive|eligible to receive|entitled to receive|recognized)\b[^.]{0,100}(?:up-?front|milestone)|(?:up-?front|milestone)[^.]{0,80}(?:received|payable to us|paid to us)", low))
        pay = bool(re.search(r"\b(?:we|company) (?:paid|made|agreed to pay|will pay|is obligated to pay)\b", low))
        if recv and not pay:
            lic, lor, conf = cp, comp, "medium"
        elif pay and not recv:
            lic, lor, conf = comp, cp, "medium"
        else:
            lic, lor, conf = cp, comp, "low:role"
        row = dict(date=d, deal_type=dt, acquirer_or_licensee=lic, target_or_licensor=lor, asset=(re.search(r"\b([A-Z]{1,5}[-‑]?\d{2,6}[A-Za-z]?)\b", par) or [None, ""])[1] if re.search(r"\b([A-Z]{1,5}[-‑]?\d{2,6}[A-Za-z]?)\b", par) else "",
                   modality=classify(par, MODS), therapeutic_area=classify(par, TAS), indication="", stage_at_deal=stage_of(par),
                   upfront_usd_m=up, equity_usd_m=eq, milestones_usd_m=ms, total_potential_usd_m=tot if tot else (up + ms if ms else None),
                   royalty_terms=royalty_text(sents), territory=terr(par), deal_value_to_peak_sales_note="",
                   source=f"r2://catalyst-lab-archive/{k}", source_row=f"10-K filed {date_filed} (agreement note paragraph, offset {m.start()})",
                   quote=window_q if (window_q := (quote or par)[:300]) else "", confidence=conf, _src="10k", _filer=comp)
        out.write(json.dumps(row) + "\n")
        nrows += 1
    if i % 200 == 0:
        print(i, nrows, flush=True)
        out.flush()
print("done", nrows)
