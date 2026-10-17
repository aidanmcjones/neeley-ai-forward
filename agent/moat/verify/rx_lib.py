"""Shared helpers for the rx stream verifier (Opus): cached CMS API calls, raw Part D loader, brand classifier."""
import hashlib
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

from agent.drug_pack import DRUGS
from agent.moat.common import store

ROOT = Path(__file__).resolve().parents[3]
C = Path("/tmp/rxv/cache")
C.mkdir(parents=True, exist_ok=True)
AIW = ROOT / "data/moat/verify/ai_wrong.jsonl"
PD_PROV = {2019: "2a6705e6-7a1e-460c-ba22-35249a531918", 2020: "7795fe20-e80e-435a-a9ed-d2d65e05feeb",
           2021: "f68114ed-f854-4ffc-9c6e-ed78b5e2f8d0", 2022: "b101b457-ffa4-49bb-8fd9-27c1266086e2",
           2023: "e54db557-cd82-4e91-a0fe-61aad5865d69", 2024: "9552739e-3d05-4c1b-8eff-ecabf391e2e5"}
PD_GEO = {2019: "73a6335e-f16f-4c81-a84b-6b5a986e2bf8", 2020: "83891e77-99cf-4865-b60a-97703b916e09",
          2021: "7dda2a9d-034a-446a-b4b3-e1254e0127b2", 2022: "1fc57194-a51d-4864-aee6-de0889488151",
          2023: "3463648b-1971-478d-84ca-80cadc758153", 2024: "c8ea3f8e-3a09-4fea-86f2-8902fb4b0920"}
API = "https://data.cms.gov/data-api/v1/dataset/{}/data"
TARGETS = ["eliquis", "xarelto", "ozempic", "jardiance", "mounjaro", "repatha", "skyrizi", "rinvoq", "biktarvy",
           "keytruda", "trulicity", "rybelsus"]
S = requests.Session()


def cms(ds, params, size=5000):
    """All rows of a data.cms.gov dataset matching params (cached)."""
    key = hashlib.md5((ds + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    f = C / f"{key}.json"
    if f.exists():
        return json.load(open(f))
    rows, off = [], 0
    while True:
        for i in range(6):
            try:
                r = S.get(API.format(ds), params={**params, "size": size, "offset": off}, timeout=180)
                if r.ok:
                    page = r.json()
                    break
            except requests.RequestException:
                pass
            time.sleep(3 * (i + 1))
        else:
            raise RuntimeError(f"{ds} {params}")
        rows += page
        if len(page) < size:
            break
        off += size
    json.dump(rows, open(f, "w"))
    return rows


def raw_partd(year):
    f = Path(f"/tmp/rxv/partd_{year}.csv.gz")
    if not f.exists():
        f.write_bytes(store().get(f"rx/raw/partd_prescribers_{year}.csv.gz"))
    d = pd.read_csv(f, dtype={"Prscrbr_NPI": str})
    for c in ("Tot_Clms", "Tot_30day_Fills", "Tot_Drug_Cst", "Tot_Benes"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["year"] = year
    return d


BRANDS = sorted(((v[0].lower(), slug) for slug, v in DRUGS.items()), key=lambda t: -len(t[0]))


def norm_brand(b):
    """CMS brand strings carry pack suffixes: 'Humira(Cf) Pen', 'Repatha Sureclick', 'Skyrizi Pen'."""
    b = re.sub(r"\(.*?\)", " ", str(b or "").lower())
    return re.sub(r"[^a-z0-9 ]", " ", b).split()


def classify(brnd):
    w = norm_brand(brnd)
    s = " ".join(w)
    for name, slug in BRANDS:
        if s == name or s.startswith(name + " "):
            return slug
    return None


def log_wrong(entries):
    with AIW.open("a") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def out(name, df_or_text, source_url):
    """Write verified/rx/<name> via common.write; with RXV_DRY=1 only to /tmp/rxv/out (no manifest, no R2)."""
    import io
    import os

    from agent.moat.common import write
    if isinstance(df_or_text, pd.DataFrame):
        b = io.StringIO()
        df_or_text.to_csv(b, index=False)
        text = b.getvalue()
    else:
        text = df_or_text
    if os.environ.get("RXV_DRY"):
        p = Path("/tmp/rxv/out") / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return
    write("verify_rx", f"verified/rx/{name}", text, group="rx", doc_type="table", source_url=source_url, quality="verified")
