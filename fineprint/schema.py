"""Shared records for every NEEDLE stage, plus JSONL read/write.

Signal     a detector hit (code or LLM-classified), with the evidence that produced it
Evidence   one citable place: corpus doc_id + file page + the exact quote (the verifier checks it)
Finding    a Signal turned into a case-ready row: sentence, impact math, peer, confidence, verdict
Prediction a falsifiable claim about a future period, sealed by hash before the outcome is known

Evidence.source() is the "<doc_id>#p<page>" form agent.findings.verify expects.
"""

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class Evidence:
    doc_id: str
    page: int | None = None          # file page from the [[page N | printed P]] marker
    quote: str = ""
    speaker: str = ""
    figures: list = field(default_factory=list)
    printed: str = ""                # filled by the verifier from the page marker
    citation: str = ""               # "BMY 10-K FY2025, p. 39", filled by the verifier

    def source(self):
        return f"{self.doc_id}#p{self.page}"


@dataclass
class Signal:
    ticker: str
    detector: str                    # drift | forensics | calls | labels | supply | ...
    kind: str                        # e.g. inventory_outpaces_revenue, risk_added, qa_deflection
    period: str = ""
    value: float | None = None       # the metric the detector measured
    peer_median: float | None = None
    peer_z: float | None = None
    detail: str = ""                 # one line a human can read
    evidence: list = field(default_factory=list)   # list[Evidence]
    meta: dict = field(default_factory=dict)


@dataclass
class Finding:
    id: str
    ticker: str
    finding: str
    signal_kind: str
    evidence: list = field(default_factory=list)   # list[Evidence]
    impact: dict = field(default_factory=dict)     # {"formula", "base", "bear", "bull", "line", "eps"}
    peer: dict = field(default_factory=dict)       # {"metric_value", "peer_median", "z", "note"}
    vector: dict = field(default_factory=dict)     # materiality spec: I_norm P T Z D O E
    score: float = 0.0
    confidence: str = "low"
    verdict: str = "unverified"                    # verified | needs_human | rejected | unverified
    reason: str = ""
    outside: dict = field(default_factory=dict)    # outside-data corroboration
    hit_rate: dict = field(default_factory=dict)   # backtest stats for this signal kind


@dataclass
class Prediction:
    id: str
    ticker: str
    target_period: str               # e.g. 2026Q3
    metric: str                      # e.g. revenue_yoy, inventory_yoy, gross_margin
    direction: str                   # up | down | above | below
    threshold: float | None = None
    probability: float = 0.5
    basis: list = field(default_factory=list)      # signal kinds and hit rates it rests on
    made_at: str = ""
    outcome: str = "open"            # open | hit | miss
    actual: float | None = None


def _to_dict(obj):
    return asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj


def _from_dict(cls, d):
    names = {f.name for f in fields(cls)}
    kw = {k: v for k, v in d.items() if k in names}
    if "evidence" in kw:
        kw["evidence"] = [Evidence(**{k: v for k, v in e.items() if k in {f.name for f in fields(Evidence)}})
                          if isinstance(e, dict) else e for e in kw["evidence"]]
    return cls(**kw)


def write_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(_to_dict(r), ensure_ascii=False, default=_plain) + "\n")


def _plain(o):
    """numpy / pandas scalars -> plain Python numbers for JSON."""
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def read_jsonl(path, cls=None):
    path = Path(path)
    if not path.exists():
        return []
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [_from_dict(cls, r) for r in rows] if cls else rows
