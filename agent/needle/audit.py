"""Tamper-evident audit trail: every signal, verifier verdict, finding and prediction NEEDLE produces is appended
to out/ledger.jsonl as a hash chain. Each record stores sha256(prev_hash + canonical JSON of its body), so editing,
deleting or reordering any past record breaks verify_chain(). seal() gives the content hash used to commit a
prediction before its outcome is known.

  append(kind, payload) -> record     kind: signal | verdict | finding | prediction | run
  verify_chain() -> (ok, n_records, first_bad_seq)
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER = ROOT / "out" / "ledger.jsonl"
GENESIS = "0" * 64


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def seal(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def _last(path):
    if not path.exists():
        return 0, GENESIS
    last = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    if not last:
        return 0, GENESIS
    rec = json.loads(last)
    return rec["seq"], rec["hash"]


def append(kind, payload, path=LEDGER):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seq, prev = _last(path)
    body = {"seq": seq + 1, "ts": datetime.now(timezone.utc).isoformat(), "kind": kind, "payload": payload, "prev": prev}
    rec = {**body, "hash": hashlib.sha256((prev + canonical(body)).encode("utf-8")).hexdigest()}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(canonical(rec) + "\n")
    return rec


def verify_chain(path=LEDGER):
    path = Path(path)
    if not path.exists():
        return True, 0, None
    prev, n = GENESIS, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        n += 1
        body = {k: rec[k] for k in ("seq", "ts", "kind", "payload", "prev")}
        if rec["prev"] != prev or rec["hash"] != hashlib.sha256((prev + canonical(body)).encode("utf-8")).hexdigest():
            return False, n, rec.get("seq")
        prev = rec["hash"]
    return True, n, None
