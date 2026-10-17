"""Thin adapter over the shared citation index (data/moat/index/citations.sqlite, built by agent.moat.index).

This is NOT a second index. Document rows, page text, labels and location strings all come from
agent/moat/cite.py (copied from data-moat commit 704741d): db(), label(), where(), get_page().
The adapter adds only what the citation package needs on top:
  * alias resolution: a few documents are in the sqlite twice, once per id scheme (corpus
    `NVO:6k/2025-08-06_caq22025.md`, path under data/corpus; moat `NVO:companies/NVO/6k/...`, path under data/moat),
    with the same ticker, doc_type and source_url. They resolve to one DocRecord whose canonical_id is the corpus id.
  * id-scheme aliasing (review D13): the detectors cite corpus-style ids (`VRTX:10k_FY2024.md`) while some tickers
    are indexed only under moat-style ids (`VRTX:companies/VRTX/10k_FY2024.md`), and the reverse. When no record
    has the exact id, resolve() tries the other scheme (`T:<rel>` <-> `T:companies/T/<rel>`), then a unique suffix
    match among the ticker's records (`T:<rel>` -> the one `T:.../<rel>`). Ambiguous suffixes resolve to None.
  * doc_type normalisation to the citation vocabulary (10-K, 10-Q, 20-F, 8-K, call transcript, label, proxy,
    comment letter, press, other).
Page id convention (frozen by the scraper): doc_id#p<page_no>, page_no = first number of "[[page N | printed M]]".
The sqlite path: env CITATIONS_DB, else data/moat/index/citations.sqlite in this repo, else the gap-data worktree
(see agent.moat.cite.DB). load_index(db_path) switches it for the process.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from agent.moat import cite as moat

DOC_TYPES = ("10-K", "10-Q", "20-F", "8-K", "call transcript", "label", "proxy", "comment letter", "press", "other")
_TYPE = {"annual_report": "10-K", "quarterly_report": "10-Q", "transcript": "call transcript",
         "transcript_source": "call transcript", "fda_label": "label", "fda_label_version": "label",
         "proxy_statement": "proxy", "sec_comment_letter": "comment letter", "press_release": "press",
         "earnings_release": "8-K", "policy_8k": "8-K", "current_report_8k": "8-K", "material_agreement": "8-K"}


def norm_doc_type(doc_type, form=""):
    f = (form or "").upper().strip()
    if f in ("10-K", "10-Q", "20-F", "8-K"):
        return f
    if f.startswith("20-F"):
        return "20-F"
    return _TYPE.get(doc_type, "other")


@dataclass
class DocRecord:
    canonical_id: str
    ticker: str
    doc_type: str                  # citation vocabulary
    raw_doc_type: str
    form: str
    period: str
    filed: str
    source_url: str
    local_path: str                # repo-relative path from the sqlite
    page_count: int | None
    page_scheme: str               # marker | section | pdf_page | none
    license: str
    doc_title: str                 # moat.label(row)
    aliases: list = field(default_factory=list)
    row: object = None             # the sqlite Row, for moat.where()

    def exists(self):
        return self.page_count not in (None, 0) and self.page_scheme != "none"


def _rec(r):
    return DocRecord(canonical_id=r["doc_id"], ticker=(r["ticker"] or "").upper(), doc_type=norm_doc_type(r["doc_type"], r["form"]),
                     raw_doc_type=r["doc_type"], form=r["form"] or "", period=r["period"] or "", filed=r["filed"] or "",
                     source_url=r["source_url"] or "", local_path=r["path"] or "", page_count=r["n_pages"],
                     page_scheme=r["page_scheme"] or "none", license=r["license"] or "", doc_title=moat.label(r), row=r)


class DocIndex:
    def __init__(self):
        self.db_path = Path(moat.DB)
        self.records = {}
        self._alias = {}
        rows = moat.db().execute("SELECT * FROM docs").fetchall()
        recs = [_rec(r) for r in rows]
        by_key = {}
        for r in recs:
            if r.source_url.startswith("http") and r.local_path.startswith("data/corpus"):
                by_key.setdefault((r.ticker, r.raw_doc_type, r.source_url), []).append(r)
        for r in recs:
            twin = by_key.get((r.ticker, r.raw_doc_type, r.source_url), []) if r.local_path.startswith("data/moat") else []
            if len(twin) == 1:
                twin[0].aliases.append(r.canonical_id)
                self._alias[r.canonical_id] = twin[0].canonical_id
            else:
                self.records[r.canonical_id] = r
        for r in recs:
            if r.canonical_id not in self._alias:
                self.records[r.canonical_id] = r

    def _use(self):
        """agent.moat.cite holds one global DB path; re-point it at this index's sqlite before any query."""
        if Path(moat.DB) != self.db_path:
            moat.DB = self.db_path
            moat.db.cache_clear()

    def __len__(self):
        return len(self.records)

    def __contains__(self, doc_id):
        return self.resolve(doc_id) is not None

    def resolve(self, doc_id):
        self._use()
        r = self.records.get(self._alias.get(doc_id, doc_id))
        return r if r is not None else self._scheme_alias(doc_id)

    def _scheme_alias(self, doc_id):
        """Corpus-style <-> moat-style id, then a unique suffix within the ticker (review D13)."""
        if not doc_id or ":" not in str(doc_id):
            return None
        pre, rel = str(doc_id).split(":", 1)
        moat_pre = f"companies/{pre}/"
        other = f"{pre}:{rel[len(moat_pre):]}" if rel.startswith(moat_pre) else f"{pre}:{moat_pre}{rel}"
        r = self.records.get(self._alias.get(other, other))
        if r is not None:
            return r
        base = rel[len(moat_pre):] if rel.startswith(moat_pre) else rel
        hits = {id(x): x for k, x in self._suffix().get(pre, ()) if k == base or k.endswith("/" + base)}
        return next(iter(hits.values())) if len(hits) == 1 else None

    def _suffix(self):
        if getattr(self, "_sfx", None) is None:
            sfx = {}
            for cid, r in self.records.items():
                if ":" in cid:
                    pre, rel = cid.split(":", 1)
                    sfx.setdefault(pre, []).append((rel, r))
            for a, cid in self._alias.items():
                if ":" in a and cid in self.records:
                    pre, rel = a.split(":", 1)
                    sfx.setdefault(pre, []).append((rel, self.records[cid]))
            self._sfx = sfx
        return self._sfx

    def canonical(self, doc_id):
        r = self.resolve(doc_id)
        return r.canonical_id if r else None

    def get_page(self, doc_id, page):
        """(page_number, printed_folio, text) via agent.moat.cite.get_page, or None."""
        r = self.resolve(doc_id)
        try:
            n = int(page)
        except (TypeError, ValueError):
            return None
        p = moat.get_page(r.canonical_id, n) if r else None
        return (n, p["printed"], p["text"]) if p else None

    def pages(self, doc_id):
        r = self.resolve(doc_id)
        if not r:
            return {}
        cur = moat.db().execute("SELECT page_no, printed, text FROM pages WHERE doc_id=? ORDER BY page_no", (r.canonical_id,))
        return {p[0]: (p[1], p[2]) for p in cur}

    def location(self, doc_id, page):
        """Human page string from moat.where(): 'p. 58', 'Item 1A', 'section Warnings', 'PDF p. 3', 'file page N (...)'."""
        r, got = self.resolve(doc_id), self.get_page(doc_id, page)
        return moat.where(r.row, got[0], got[1]) if r and got else ""


@lru_cache(maxsize=4)
def _load(db_key):
    if db_key and Path(db_key) != Path(moat.DB):
        moat.DB = Path(db_key)
        moat.db.cache_clear()
    return DocIndex()


def load_index(db_path=None):
    """Cached DocIndex over the sqlite (default: whatever agent.moat.cite.DB resolves to)."""
    return _load(str(db_path) if db_path else None)


def get_page(canonical_id, page, db_path=None):
    return load_index(db_path).get_page(canonical_id, page)
