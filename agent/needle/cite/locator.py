"""Citation contract: what every number and quote the model emits must carry.

Citation  one verifiable pointer: document, page, span, verbatim quote, links, verification result.
Claim     a sentence (or number) the model asserts, paired with one or more Citations.

Identity: cite_id is a stable hash of (canonical_id, page, quote), so the same evidence emitted twice
gets one footnote. char_start/char_end are offsets into the page text as returned by
DocIndex.get_page (None until verification locates the span).
"""

import hashlib
from dataclasses import asdict, dataclass, field

STATUSES = ("exact", "substring", "fuzzy", "number_match", "unverified")
CLAIM_TYPES = ("quote", "number", "paraphrase")


@dataclass
class Verification:
    status: str = "unverified"        # exact | substring | fuzzy | number_match | unverified
    score: float = 0.0                # 0..1
    checked_at: str = ""              # ISO-8601 UTC, empty until verified
    detail: str = ""

    @property
    def ok(self):
        return self.status in ("exact", "substring", "fuzzy", "number_match")


@dataclass
class Citation:
    canonical_id: str
    page: int | None = None           # file page (the [[page N]] marker)
    quote: str = ""                   # verbatim text from that page
    claim_type: str = "quote"         # quote | number | paraphrase
    value: str | None = None          # the number as the model emitted it, e.g. "15,144" or "(183)"
    unit: str = ""                    # "USD millions", "percent", "" ...
    ticker: str = ""
    doc_type: str = ""
    doc_title: str = ""
    period: str = ""
    folio: str = ""                   # printed page, "?" when unknown
    char_start: int | None = None
    char_end: int | None = None
    source_url: str = ""
    deep_link: str = ""
    viewer_link: str = ""
    speaker: str = ""                 # call transcripts
    location: str = ""                # moat.where(): "p. 58", "Item 1A", "section Warnings", "PDF p. 3"
    raw_doc_type: str = ""            # sqlite docs.doc_type; drives deep-link rules
    page_scheme: str = ""             # marker | section | pdf_page | none
    license: str = ""                 # "bloomberg_licensed" = team only, never public
    verification: Verification = field(default_factory=Verification)
    confidence_note: str = ""
    cite_id: str = ""

    def __post_init__(self):
        if not self.cite_id:
            self.cite_id = make_cite_id(self.canonical_id, self.page, self.quote)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        v = d.pop("verification", None) or {}
        return cls(**d, verification=Verification(**v))


@dataclass
class Claim:
    text: str                                          # the model's sentence
    citations: list = field(default_factory=list)      # list[Citation]

    def to_dict(self):
        return {"text": self.text, "citations": [c.to_dict() for c in self.citations]}


def make_cite_id(canonical_id, page, quote):
    key = f"{canonical_id}|{page}|{' '.join((quote or '').split()).lower()}"
    return "c_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
