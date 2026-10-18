"""Shared output helper for the verify_secx stream: CSV text -> common.write (local + R2) and the AI-was-wrong log."""
import csv
import io
import json
from pathlib import Path

from agent.moat.common import write

AI_WRONG = Path("data/moat/verify/ai_wrong.jsonl")


def out(name, cols, rows, source_url):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    row = write("verify_secx", f"verified/secx/{name}", buf.getvalue(), group="tables", doc_type="table",
                source_url=source_url)
    print(row["path"], row["chars"], len(rows), "rows")
    return row


def ai_wrong(entries):
    AI_WRONG.parent.mkdir(parents=True, exist_ok=True)
    with AI_WRONG.open("a") as f:
        for e in entries:
            e = {"stream": "secx", **e}
            f.write(json.dumps(e) + "\n")
    print("ai_wrong +", len(entries))
