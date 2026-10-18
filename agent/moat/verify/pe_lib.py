"""Helpers for the peers/epi verifiers: page splitting, text normalization, ai_wrong logging."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AIW = ROOT / "data" / "moat" / "verify" / "ai_wrong.jsonl"
PAGE_RE = re.compile(r"\[\[page (\d+) \| printed ([^\]]*)\]\]")


@lru_cache(maxsize=64)
def pages(path):
    """Return {page_no: (printed, text)} for a page-marked markdown doc."""
    txt = (ROOT / path).read_text(errors="replace")
    out = {}
    ms = list(PAGE_RE.finditer(txt))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(txt)
        out[int(m.group(1))] = (m.group(2).strip(), txt[m.end():end])
    return out


def norm(s, loose=False):
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("\xa0", " ")
    s = s.replace("|", " ")
    if loose:
        s = re.sub(r"[^A-Za-z0-9%.,$]+", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def log_wrong(entries):
    with AIW.open("a") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
