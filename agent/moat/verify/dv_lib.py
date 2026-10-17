"""Shared helpers for the deals verification (dv_*): load deal_comps, fetch the source page text, mechanical checks."""
import gzip
import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from agent.moat.common import OUT
from agent.moat.deals_lib import amounts

WORK = OUT / "verify" / "deals_work"
WORK.mkdir(parents=True, exist_ok=True)
CACHE10K = WORK / "10k_cache"
CACHE10K.mkdir(exist_ok=True)


def load():
    return pd.read_csv(OUT / "tables" / "deal_comps.csv", dtype={"deal_id": str})


def norm(t):
    t = re.sub(r"\s+", " ", t or "").replace(" • ", ". ").replace(" ● ", ". ").replace("•", ". ")
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=4000)
def md_pages(fname):
    p = OUT / "deals" / fname
    if not p.exists():
        return {}
    t = p.read_text(errors="ignore")
    parts = re.split(r"\[\[page (\d+) \|[^\]]*\]\]", t)
    pages = {}
    for i in range(1, len(parts), 2):
        pages[int(parts[i])] = parts[i + 1]
    return pages


def r2_10k(key):
    f = CACHE10K / (key.replace("/", "_") + ".txt")
    if f.exists():
        return f.read_text()
    from agent.tenk import Store
    import boto3, os
    s = Store()
    c = boto3.client("s3", endpoint_url=s.s3.meta.endpoint_url, aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                     aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    raw = c.get_object(Bucket="catalyst-lab-archive", Key=key)["Body"].read()
    t = gzip.decompress(raw).decode("utf-8", "ignore")
    f.write_text(t)
    return t


def source_text(row):
    """Return (page_text, whole_doc_text, locator) for a row."""
    src, sr = str(row["source"]), str(row["source_row"])
    if src.startswith("r2://"):
        key = src.split("catalyst-lab-archive/")[1]
        t = r2_10k(key)
        m = re.search(r"offset (\d+)", sr)
        off = int(m.group(1)) if m else 0
        a = max(0, t.rfind("\n", 0, off))
        b = t.find("\n", off + 1)
        par = t[a:b if b > 0 else off + 3000]
        win = t[max(0, off - 3000): off + 3000]
        return par, win, f"{key}@{off}"
    fname = sr.split(" ")[0]
    m = re.search(r"\[\[page (\d+)", sr)
    pg = int(m.group(1)) if m else 1
    pages = md_pages(fname)
    return pages.get(pg, ""), "\n".join(pages.values()), f"{fname} p{pg}"


def amt_set(text):
    return [v for v, _, _ in amounts(re.sub(r"\s+", " ", text))]


def has_amt(vals, v, tol=0.011):
    return any(abs(x - v) <= max(tol, 0.0005 * v) for x in vals)


def isnum(v):
    return v is not None and not (isinstance(v, float) and v != v) and str(v) != ""
