"""Gap closer fetch helper: SEC through agent.tenk.sec_get (0.5 s interval), other hosts via requests.

python -m agent.moat.verify.g_fetch <url> [out_path]
"""
import json
import os
import sys
from pathlib import Path

import requests

import agent.tenk as T

T.MIN_INTERVAL = 0.5
os.environ.setdefault("SEC_USER_AGENT", "Neeley AI Forward hackathon aidan@justinianhq.com")


def get(url, as_json=False):
    if "sec.gov" in url:
        return T.sec_get(url, as_json=as_json)
    r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0 (Neeley AI Forward research)"})
    r.raise_for_status()
    return r.json() if as_json else r.text


if __name__ == "__main__":
    url = sys.argv[1]
    out = get(url, as_json=url.endswith(".json"))
    s = out if isinstance(out, str) else json.dumps(out)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
        Path(sys.argv[2]).write_text(s)
        print("wrote", len(s))
    else:
        print(s[:20000])
