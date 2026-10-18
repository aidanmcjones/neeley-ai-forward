"""Product fine print: a deterministic, fully cited side-by-side of one product against its listed rivals.

    from agent.needle.quant.product import compare, tie_to_financials, growth_limiter
    cmp = compare("LLY", "zepbound")
    claims = tie_to_financials(cmp, findings=None)       # list[ProductClaim] (Claim subclass), gate()-ready
    sentence, priced_in, reasons, cites = growth_limiter(cmp, claims)

The comparison has exactly the five rows the case asks for (ROWS). Every cell is a Cell: a display value, a detail dict,
Citations (label section pages, 10-K pages, CMS / White House pages; all verified through agent.needle.cite.verify), and
table refs (file + key) for numbers that live only in a table with no page (Orange Book, NADAC, Part D). A cell that
cannot be filled is empty with a stated reason; nothing is invented. No API is called.

Label facts come from agent.needle.detect.labels.profile (the existing detector). Label quotes are located on their
section page in the shared citation index (doc_type fda_label, page = label section) so verify() and gate() accept them.
"""

import json
import math
import os
import re
import statistics
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import pandas as pd

from agent.findings import _norm
from agent.needle.cite.index import load_index
from agent.needle.cite.locator import Citation, Claim
from agent.needle.cite.verify import verify

from . import impact as IM
from . import weights as W

REPO = Path(__file__).resolve().parents[3]
_GAP = Path("/Users/aidanjones/dev/neeley-ai-forward/.claude/worktrees/gap-data")
AS_OF = "2026-10-17"
HORIZON_MONTHS = 24

ROWS = [("approved_uses", "Approved uses"),
        ("safety", "Boxed warnings and safety fine print"),
        ("dosing", "Dosing and convenience"),
        ("timeline", "Patent and exclusivity timeline"),
        ("pricing", "Pricing and gross-to-net exposure")]

# ------------------------------------------------------------------ appendix (case pages 4-5) as data
# Entity keys: name (display), slug (drug pack under data/corpus/drugs; None = no label), maker, variant (same pack,
# different presentation), ingredient (used only for the 10-K text search fallback).


def E(name, slug, maker, ingredient="", variant="", note=""):
    return {"name": name, "slug": slug, "maker": maker, "ingredient": ingredient, "variant": variant, "note": note}


APPENDIX = {
    "MRK": {"company": "Merck",
            "starter": "Keytruda's 2028 patent expiry; Januvia and Janumet lost U.S. exclusivity in 2026 and now face generics and a Medicare negotiated price.",
            "products": {
                "keytruda": {"self": E("Keytruda", "keytruda", "Merck", "pembrolizumab"),
                             "rivals": [E("Opdivo", "opdivo", "Bristol Myers Squibb", "nivolumab"),
                                        E("Imfinzi", "imfinzi", "AstraZeneca", "durvalumab"),
                                        E("Tecentriq", "tecentriq", "Roche", "atezolizumab")]},
                "januvia": {"self": E("Januvia", "januvia", "Merck", "sitagliptin"),
                            "rivals": [E("Generic sitagliptin", None, "generic makers", "sitagliptin", note="no brand label in the packs"),
                                       E("Ozempic", "ozempic", "Novo Nordisk", "semaglutide"),
                                       E("Jardiance", "jardiance", "Boehringer Ingelheim/Lilly", "empagliflozin")]}}},
    "BMY": {"company": "Bristol Myers Squibb",
            "starter": "Eliquis and Opdivo both lose U.S. exclusivity in 2028, putting a large share of revenue at risk.",
            "products": {
                "eliquis": {"self": E("Eliquis", "eliquis", "Bristol Myers Squibb", "apixaban"),
                            "rivals": [E("Xarelto", "xarelto", "Johnson & Johnson", "rivaroxaban")]},
                "opdivo": {"self": E("Opdivo", "opdivo", "Bristol Myers Squibb", "nivolumab"),
                           "rivals": [E("Keytruda", "keytruda", "Merck", "pembrolizumab"),
                                      E("Tecentriq", "tecentriq", "Roche", "atezolizumab")]}}},
    "PFE": {"company": "Pfizer",
            "starter": "Ibrance faces generic pressure from 2027 while the company rebuilds its growth story.",
            "products": {
                "ibrance": {"self": E("Ibrance", "ibrance", "Pfizer", "palbociclib"),
                            "rivals": [E("Verzenio", "verzenio", "Eli Lilly", "abemaciclib"),
                                       E("Kisqali", "kisqali", "Novartis", "ribociclib")]},
                "vyndamax": {"self": E("Vyndamax (Vyndaqel family)", "vyndamax", "Pfizer", "tafamidis"),
                             "rivals": [E("Attruby", "attruby", "BridgeBio", "acoramidis"),
                                        E("Amvuttra", "amvuttra", "Alnylam", "vutrisiran")]}}},
    "LLY": {"company": "Eli Lilly",
            "starter": "Mounjaro and Zepbound lead the obesity market, but price cuts and the race for a pill are reshaping it; Trulicity loses exclusivity in 2027.",
            "products": {
                "zepbound": {"self": E("Zepbound", "zepbound", "Eli Lilly", "tirzepatide"),
                             "rivals": [E("Ozempic", "ozempic", "Novo Nordisk", "semaglutide"),
                                        E("Wegovy injection", "wegovy", "Novo Nordisk", "semaglutide", variant="injection"),
                                        E("Wegovy pill", "wegovy", "Novo Nordisk", "semaglutide", variant="tablet",
                                          note="oral Wegovy tablets share the Wegovy label and Orange Book pack")]},
                "mounjaro": {"self": E("Mounjaro", "mounjaro", "Eli Lilly", "tirzepatide"),
                             "rivals": [E("Ozempic", "ozempic", "Novo Nordisk", "semaglutide"),
                                        E("Wegovy injection", "wegovy", "Novo Nordisk", "semaglutide", variant="injection"),
                                        E("Wegovy pill", "wegovy", "Novo Nordisk", "semaglutide", variant="tablet")]},
                "trulicity": {"self": E("Trulicity", "trulicity", "Eli Lilly", "dulaglutide"),
                              "rivals": [E("Ozempic", "ozempic", "Novo Nordisk", "semaglutide"),
                                         E("Wegovy injection", "wegovy", "Novo Nordisk", "semaglutide", variant="injection"),
                                         E("Wegovy pill", "wegovy", "Novo Nordisk", "semaglutide", variant="tablet")]}}},
    "NVO": {"company": "Novo Nordisk",
            "starter": "Medicare's negotiated price for semaglutide (the active ingredient in Ozempic and Wegovy) takes effect January 2027, about 71% below the 2025 list price.",
            "products": {
                "ozempic": {"self": E("Ozempic", "ozempic", "Novo Nordisk", "semaglutide"),
                            "rivals": [E("Mounjaro", "mounjaro", "Eli Lilly", "tirzepatide"),
                                       E("Zepbound", "zepbound", "Eli Lilly", "tirzepatide"),
                                       E("Foundayo", "foundayo", "Eli Lilly", "orforglipron")]},
                "wegovy": {"self": E("Wegovy", "wegovy", "Novo Nordisk", "semaglutide"),
                           "rivals": [E("Mounjaro", "mounjaro", "Eli Lilly", "tirzepatide"),
                                      E("Zepbound", "zepbound", "Eli Lilly", "tirzepatide"),
                                      E("Foundayo", "foundayo", "Eli Lilly", "orforglipron")]}}},
    "ABBV": {"company": "AbbVie",
             "starter": "Life after Humira: how fast Skyrizi and Rinvoq are filling the revenue gap.",
             "products": {
                 "skyrizi": {"self": E("Skyrizi", "skyrizi", "AbbVie", "risankizumab"),
                             "rivals": [E("Tremfya", "tremfya", "Johnson & Johnson", "guselkumab"),
                                        E("Stelara", "stelara", "Johnson & Johnson", "ustekinumab"),
                                        E("Cosentyx", "cosentyx", "Novartis", "secukinumab"),
                                        E("Entyvio", "entyvio", "Takeda", "vedolizumab"),
                                        E("Amjevita (Humira biosimilar)", "amjevita", "Amgen", "adalimumab")]},
                 "rinvoq": {"self": E("Rinvoq", "rinvoq", "AbbVie", "upadacitinib"),
                            "rivals": [E("Tremfya", "tremfya", "Johnson & Johnson", "guselkumab"),
                                       E("Cosentyx", "cosentyx", "Novartis", "secukinumab"),
                                       E("Entyvio", "entyvio", "Takeda", "vedolizumab"),
                                       E("Amjevita (Humira biosimilar)", "amjevita", "Amgen", "adalimumab")]}}},
    "JNJ": {"company": "Johnson & Johnson",
            "starter": "Stelara biosimilar erosion, Medicare drug-price negotiation, and the shift toward newer immunology and cancer drugs.",
            "products": {
                "stelara": {"self": E("Stelara", "stelara", "Johnson & Johnson", "ustekinumab"),
                            "rivals": [E("Skyrizi", "skyrizi", "AbbVie", "risankizumab"),
                                       E("Rinvoq", "rinvoq", "AbbVie", "upadacitinib"),
                                       E("Wezlana (Stelara biosimilar)", "wezlana", "Amgen", "ustekinumab")]},
                "tremfya": {"self": E("Tremfya", "tremfya", "Johnson & Johnson", "guselkumab"),
                            "rivals": [E("Skyrizi", "skyrizi", "AbbVie", "risankizumab"),
                                       E("Rinvoq", "rinvoq", "AbbVie", "upadacitinib"),
                                       E("Wezlana (Stelara biosimilar)", "wezlana", "Amgen", "ustekinumab")]},
                "darzalex": {"self": E("Darzalex", "darzalex", "Johnson & Johnson", "daratumumab"),
                             "rivals": [E("Sarclisa", "sarclisa", "Sanofi", "isatuximab")]}}},
    "AZN": {"company": "AstraZeneca",
            "starter": "Cancer-drug growth, near-term exclusivity losses (generic Farxiga was approved in 2026), and exposure to U.S. pricing politics as a UK-based company.",
            "products": {
                "tagrisso": {"self": E("Tagrisso", "tagrisso", "AstraZeneca", "osimertinib"),
                             "rivals": [E("Rybrevant (with Lazcluze)", "rybrevant", "Johnson & Johnson", "amivantamab"),
                                        E("Lazcluze (with Rybrevant)", "lazcluze", "Johnson & Johnson", "lazertinib")]},
                "farxiga": {"self": E("Farxiga", "farxiga", "AstraZeneca", "dapagliflozin"),
                            "rivals": [E("Generic dapagliflozin", None, "generic makers", "dapagliflozin", note="no brand label in the packs"),
                                       E("Jardiance", "jardiance", "Boehringer Ingelheim/Lilly", "empagliflozin")]},
                "imfinzi": {"self": E("Imfinzi", "imfinzi", "AstraZeneca", "durvalumab"),
                            "rivals": [E("Keytruda", "keytruda", "Merck", "pembrolizumab")]}}},
    "AMGN": {"company": "Amgen",
             "starter": "Enbrel and Repatha lose U.S. exclusivity around 2029 while Amgen bets on obesity drugs.",
             "products": {
                 "repatha": {"self": E("Repatha", "repatha", "Amgen", "evolocumab"),
                             "rivals": [E("Praluent", "praluent", "Regeneron", "alirocumab"),
                                        E("Leqvio", "leqvio", "Novartis", "inclisiran"),
                                        E("Lipfendra", "lipfendra", "Merck", "enlicitide")]},
                 "enbrel": {"self": E("Enbrel", "enbrel", "Amgen", "etanercept"),
                            "rivals": [E("Skyrizi", "skyrizi", "AbbVie", "risankizumab"),
                                       E("Rinvoq", "rinvoq", "AbbVie", "upadacitinib"),
                                       E("Humira", "humira", "AbbVie", "adalimumab")]}}},
    "GILD": {"company": "Gilead",
             "starter": "A dominant HIV franchise, and how long that dominance can hold.",
             "products": {
                 "biktarvy": {"self": E("Biktarvy", "biktarvy", "Gilead", "bictegravir"),
                              "rivals": [E("Dovato", "dovato", "ViiV Healthcare (GSK/Shionogi)", "dolutegravir"),
                                         E("Cabenuva", "cabenuva", "ViiV Healthcare (GSK/Shionogi)", "cabotegravir")]},
                 "yeztugo": {"self": E("Yeztugo", "yeztugo", "Gilead", "lenacapavir"),
                             "rivals": [E("Apretude", "apretude", "ViiV Healthcare (GSK/Shionogi)", "cabotegravir")]}}},
}
# the Appendix names these as the headline pair for each company; used as defaults by the CLI
DEFAULT_PRODUCT = {"LLY": "zepbound", "AZN": "tagrisso", "MRK": "keytruda", "BMY": "opdivo", "PFE": "ibrance",
                   "NVO": "wegovy", "ABBV": "skyrizi", "JNJ": "stelara", "AMGN": "repatha", "GILD": "biktarvy"}


# ------------------------------------------------------------------ data roots
def moat_root(data_root=None):
    for c in (data_root, os.environ.get("MOAT_ROOT"), REPO / "data" / "moat", _GAP / "data" / "moat"):
        if c and (Path(c) / "tables").exists():
            return Path(c)
    return None


def cache_root():
    for c in (REPO / "agent" / "cache", _GAP / "agent" / "cache"):
        if (c / "company_stated_loe.jsonl").exists():
            return c
    return None


def default_db():
    """The shared citations.sqlite: env CITATIONS_DB, else the repo copy, else the gap-data copy (explicit, so a test that
    re-points agent.moat.cite.DB cannot change which index the comparison reads)."""
    if os.environ.get("CITATIONS_DB"):
        return Path(os.environ["CITATIONS_DB"])
    local = REPO / "data" / "moat" / "index" / "citations.sqlite"
    return local if local.exists() else _GAP / "data" / "moat" / "index" / "citations.sqlite"


class Data:
    """Lazy CSV access under the moat; every accessor returns an empty frame when the file is absent."""

    def __init__(self, root=None):
        self.root = moat_root(root)
        self._c = {}

    def csv(self, rel):
        if rel not in self._c:
            p = self.root / rel if self.root else None
            self._c[rel] = pd.read_csv(p, low_memory=False) if p and p.exists() else pd.DataFrame()
        return self._c[rel]


# ------------------------------------------------------------------ cell types
@dataclass
class Cell:
    value: str | None = None
    detail: dict = field(default_factory=dict)
    citations: list = field(default_factory=list)        # list[Citation], verified
    refs: list = field(default_factory=list)             # table refs: {"file", "key", "note"} for numbers with no page
    empty_reason: str = ""

    @property
    def empty(self):
        return self.value in (None, "")

    def to_dict(self):
        return {"value": self.value, "detail": self.detail, "citations": [c.to_dict() for c in self.citations],
                "refs": self.refs, "empty_reason": self.empty_reason}


@dataclass
class ProductComparison:
    ticker: str
    product: str
    as_of: str
    entities: list                       # [self entity, rival entities...] (dicts)
    rows: dict                           # row_key -> {entity name -> Cell}
    notes: list = field(default_factory=list)
    context: dict = field(default_factory=dict)   # revenue, scorecard, starter, filled by compare()

    def cell(self, row, name):
        return self.rows[row][name]

    def withheld(self):
        """Non-empty cells whose numbers the numeric gate does not pass (review C5, D9): every number (and, in a
        timeline or pricing cell, every date) must be verified by one of its citations, derived, or a labelled
        assumption. These cells are not printed."""
        return [(r, n) for r, d in self.rows.items() for n, c in d.items()
                if not c.empty and not cell_gate(self, r, n).passed]

    def uncited(self):
        """Non-empty cells with no passing citation at all, plus the withheld cells (review verify2 3: a cell whose
        numbers are all labelled table values or that has no numbers is still uncited when nothing cites it)."""
        out = []
        for r, d in self.rows.items():
            for n, c in d.items():
                if c.empty:
                    continue
                g = cell_gate(self, r, n)
                if not g.passed or not g.citations:
                    out.append((r, n))
        return out

    def table_only(self):
        """Non-empty cells that pass the gate but carry numbers taken from table rows with no verified facts row
        (labelled 'unverified table value' assumptions): listed so the reader knows which numbers are not page-cited."""
        out = []
        for r, d in self.rows.items():
            for n, c in d.items():
                if c.empty:
                    continue
                res = cell_gate(self, r, n)
                if res.passed and any(x["kind"] == "assumed" and str(x.get("label", "")).startswith("unverified table")
                                      for x in res.numbers):
                    out.append((r, n))
        return out

    def empties(self):
        return [(r, n, c.empty_reason) for r, d in self.rows.items() for n, c in d.items() if c.empty]

    def to_dict(self):
        return {"ticker": self.ticker, "product": self.product, "as_of": self.as_of,
                "entities": self.entities, "rows": {r: {n: c.to_dict() for n, c in d.items()} for r, d in self.rows.items()},
                "row_titles": dict(ROWS), "notes": self.notes,
                "context": {k: v for k, v in self.context.items() if not k.startswith("_")}}


# ------------------------------------------------------------------ citation helpers
_PAGE_CACHE = {}


def _pages(idx, doc):
    key = (str(idx.db_path), doc)
    if key not in _PAGE_CACHE:
        _PAGE_CACHE[key] = {n: _norm(t) for n, (_, t) in idx.pages(doc).items()}
    return _PAGE_CACHE[key]


def find_page(idx, doc, quote):
    """File page of `doc` whose normalized text contains the normalized quote (first match), else None."""
    nq = _norm(quote)
    if len(nq) < 12:
        return None
    for n, t in _pages(idx, doc).items():
        if nq in t:
            return n
    head = nq[:60]
    for n, t in _pages(idx, doc).items():
        if head in t:
            return n
    return None


def _clip_chars(q, n=300):
    q = " ".join((q or "").split())
    if len(q) <= n:
        return q
    cut = q[:n].rsplit(" ", 1)[0]
    return cut


def _warning_cite(idx, doc, sec5, title):
    """Citation for one 5.x warning: its heading, else (a heading the index stored as an unclassified section) the
    first sentence of the text under that heading in section 5."""
    c = cite_quote(idx, doc, title.strip())
    if _ok(c):
        return c
    m = re.search(r"^###\s*" + re.escape(title.strip()) + r"\s*\n+(.+)", sec5, re.M)
    if m:
        para = re.sub(r"\s+", " ", m.group(1)).strip()
        sent = re.split(r"(?<=[.;])\s", para)[0]
        return cite_quote(idx, doc, sent[:200])
    return c


def cite_quote(idx, doc, quote, claim_type="quote", value=None, unit="", page=None, hint=None):
    """Locate `quote` in `doc`, build a Citation and verify it. Returns the Citation or None when the doc or text is absent."""
    if doc not in idx:
        return None
    q = _clip_chars(quote)
    pg = find_page(idx, doc, q)
    if pg is None and page is not None and idx.get_page(doc, page):
        pg = int(page)
    if pg is None and hint is not None and idx.get_page(doc, hint):
        pg = int(hint)
    if pg is None:
        return None
    c = Citation(canonical_id=doc, page=pg, quote=q, claim_type=claim_type, value=value, unit=unit)
    return verify(c, idx)


def _ok(c):
    return c is not None and c.verification.ok


def cell_gate(cmp_, row, name):
    """GateResult for one table cell: its passing citations plus the facts-row citations and labels of product_gate."""
    from agent.needle.cite.gate import date_check, merge_date_check, numeric_gate
    from .product_gate import cell_maps
    key = f"_gate|{row}|{name}"
    if key in cmp_.context:
        return cmp_.context[key]
    cell = cmp_.rows[row][name]
    ent = next(e for e in cmp_.entities if e["name"] == name)
    xc, dm, am = cell_maps(cmp_, row, ent, cell)
    cites = [c for c in list(cell.citations) + xc if c.verification.ok]
    res = numeric_gate([(f"{row}/{name}", cell.value or "")], cites, dm, am)
    # review verify2 3: dates, years and "12y" in a cell are the fact; numbers.tokenize excludes them, so they are
    # checked here against the cell's passing citations or a labelled table value (gate.date_check)
    dc = date_check(f"{row}/{name}", cell.value or "", cites, am, years=row == "timeline")
    if dc["total"]:
        res.numeric_check = merge_date_check(res.numeric_check, dc)
    res.citations, res.derived, res.assumptions = cites, dm, am
    cmp_.context[key] = res
    return res


def label_doc(slug):
    return f"drug:{slug}:label_sections.md"


# ------------------------------------------------------------------ label facts
def _labels():
    from agent.needle.detect import labels
    return labels


def _variant_dosing(idx, ent):
    """Wegovy pill: take the dosing sentence from the tablet section (the pack-level detector reads the injection)."""
    doc = label_doc(ent["slug"])
    for n, (printed, text) in idx.pages(doc).items():
        if re.search(r"Recommended Dosage of .* Tablets", printed or "") and "once daily" in text:
            m = re.search(r"The recommended starting dosage of [^\n]*?once daily\.", text)
            if m:
                return m.group(0), n
    return None, None


def _titration(slug, secs):
    s2 = secs.get(2, "")
    for ln in re.split(r"(?<=[.])\s+|\n", s2):
        if re.search(r"\b(escalat|titrat|increase the dos)", ln, re.I) and len(ln.split()) >= 8:
            return " ".join(ln.split()).lstrip("-• ")
    return None


def _label_cells(idx, data, ent):
    """-> {row: Cell} for approved_uses, safety, dosing (label-derived rows) for one entity."""
    L = _labels()
    slug, out = ent["slug"], {}
    if not slug:
        r = ent.get("note") or "no brand label in the drug packs"
        return {k: Cell(empty_reason=r) for k in ("approved_uses", "safety", "dosing")}
    if not L._label_path(slug).exists():
        r = f"drug pack {slug} has no label_sections.md"
        return {k: Cell(empty_reason=r) for k in ("approved_uses", "safety", "dosing")}
    P, lab = L.profile(slug), L._parse(slug)
    secs = lab["sections"]
    doc = label_doc(slug)
    ev = P["_evidence"]

    # approved uses
    im = data.csv("tables/indication_map.csv")
    names = []
    if len(im) and (im["drug"] == slug).any():
        names = [str(x) for x in im[im["drug"] == slug]["sub_indication"].dropna()]
        seen, uniq = set(), []
        for n_ in names:
            k_ = re.sub(r"\W+", " ", n_.lower()).strip()
            if k_ not in seen:
                seen.add(k_)
                uniq.append(n_)
        names = uniq
    if not names:
        names = list(P["indications"]["value"])
    q = ev.get("indications")
    cites = [c for c in [cite_quote(idx, doc, q.quote) if q else None] if _ok(c)]
    if names:
        out["approved_uses"] = Cell(f"{len(names)}: " + "; ".join(names), {"count": len(names), "names": names,
                                    "source": "indication_map.csv" if len(im) and (im["drug"] == slug).any() else "label section 1"},
                                    cites, [{"file": "tables/indication_map.csv", "key": slug}] if len(im) else [],
                                    "" if cites else "no indication quote located on a label page")
    else:
        out["approved_uses"] = Cell(empty_reason="label section 1 not parsed")
    if ent.get("variant") == "tablet":
        out["approved_uses"].detail["note"] = "uses listed are for the whole Wegovy label (injection and tablets)"

    # safety
    bw, ci, rems = P["boxed_warning"], P["contraindications"], P["rems"]
    parts, cites, det = [], [], {}
    if bw["value"] is True:
        parts.append(f"Boxed warning: {bw['heading'].replace('WARNING: ', '').title()}")
        det["boxed_warning"] = {"heading": bw["heading"], "text": bw.get("text")}
        c = cite_quote(idx, doc, ev["boxed_warning"].quote) if ev.get("boxed_warning") else None
        if _ok(c):
            cites.append(c)
    elif bw["value"] is False:
        parts.append("No boxed warning (label has no WARNING heading)")
        det["boxed_warning"] = False
        w5 = L._paras(secs.get(5, ""))
        c = cite_quote(idx, doc, L._clip(L._norm(w5[0]), 40)) if w5 else None
        if _ok(c):
            cites.append(c)
            det["note"] = "citation is the Warnings and Precautions section; absence of a boxed warning is the absence of a heading"
    if ci["value"] is not None:
        parts.append(f"{ci['value']} contraindication(s)")
        det["contraindications"] = ci["value"]
        c = cite_quote(idx, doc, ev["contraindications"].quote) if ev.get("contraindications") else None
        if not _ok(c) and ci["value"] == 0:
            c = cite_quote(idx, doc, "4 CONTRAINDICATIONS None.")       # section 4 reads "None."
        if _ok(c):
            cites.append(c)
            det["contra_cite_id"] = c.cite_id
    if rems["value"] is not None:
        parts.append("REMS: yes" if rems["value"] else "REMS: none found in label sections one to five")
        det["rems"] = rems["value"]
        if rems["value"] and ev.get("rems"):
            c = cite_quote(idx, doc, ev["rems"].quote)
            if _ok(c):
                cites.append(c)
    for n, key in ((5, "warnings_and_precautions"),):
        titles = re.findall(r"^###\s*(5\.\d+\s+[^\n]+)", secs.get(5, ""), re.M)
        if titles:
            det[key] = titles
            parts.append(f"{len(titles)} warnings and precautions")
            # each heading cited on its label page: the count derives from these cited items (review verify2 3)
            wc = [_warning_cite(idx, doc, secs.get(5, ""), t) for t in titles]
            if all(_ok(c) for c in wc):
                cites += [c for c in wc if c.cite_id not in {x.cite_id for x in cites}]
                det["warning_cite_ids"] = [c.cite_id for c in wc]
    out["safety"] = Cell("; ".join(parts) or None, det, cites, [], "" if parts else "label sections 4-5 not parsed")

    # dosing
    route, fq = P["route"], P["dosing_frequency"]
    dq = ev.get("dosing_frequency")
    dq_text, cites, det = (dq.quote if dq else None), [], {}
    if ent.get("variant") == "tablet":
        t, _pg = _variant_dosing(idx, ent)
        if t:
            dq_text, det = t, {"route": "oral", "frequency": "once daily", "doses_per_year": 365, "variant": "tablet"}
            route = {"value": "oral"}
            fq = {"value": "once daily", "doses_per_year": 365}
    elif ent.get("variant") == "injection":
        det["variant"] = "injection"
    c = cite_quote(idx, doc, dq_text) if dq_text else None
    if _ok(c):
        cites.append(c)
    tit = _titration(slug, secs)
    if tit:
        c2 = cite_quote(idx, doc, tit)
        if _ok(c2):
            cites.append(c2)
        det["titration"] = tit[:200]
    if route["value"] or fq["value"]:
        det.update({"route": route["value"], "frequency": fq["value"], "doses_per_year": fq.get("doses_per_year")})
        out["dosing"] = Cell(f"{route['value'] or 'route n/a'}, {fq['value'] or 'frequency n/a'}"
                             + ("; titration in label" if tit else ""), det, cites, [],
                             "" if cites else "no dosing quote located on a label page")
    else:
        out["dosing"] = Cell(empty_reason="label section 2 has no recognised dosing frequency")
    return out


# ------------------------------------------------------------------ timeline
def _tenk_docs(idx, ticker, accession=None):
    recs = [r for r in idx.records.values() if r.ticker == ticker and r.raw_doc_type == "annual_report"]
    if accession:
        a = accession.replace("-", "")
        hit = [r for r in recs if a in (r.source_url or "")]
        if hit:
            return hit
    return sorted(recs, key=lambda r: r.period, reverse=True)


@lru_cache(maxsize=1)
def _loe_rows():
    c = cache_root()
    if not c:
        return []
    return [json.loads(l) for l in (c / "company_stated_loe.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def _company_stated(idx, ticker, ent):
    """-> (value, detail, citations, note). Looks in the cached 10-K LOE table first, then searches the latest annual
    report text for a sentence about the brand and a patent or exclusivity year."""
    brand = ent["name"].split(" (")[0].split()[0].lower()
    # thread #19 (d): the LOE comes from pipeline/loe_calendar.csv (company_stated_loe with its 10-K page, a dated
    # settlement entry first) or the company's own filing; never from labels_table.json (Orange/Purple Book max,
    # which mixes orphan exclusivity into protection)
    try:
        from . import verified_tables as VT
        got = VT.loe(ticker, brand)
    except Exception:
        got = None
    if got:
        d, tv, row = got
        cites = [c for c in tv.citations if _ok(c)]
        if cites:
            day = d.isoformat() if (d.month, d.day) != (1, 1) else str(d.year)
            basis = (row.get("best_basis") or row.get("rule_method") or "company-stated") if isinstance(row, dict) else ""
            basis = str(basis).split("; FDA rule")[0]
            return day, {"us_loe": day, "basis": str(basis)[:160], "source": tv.label}, cites, \
                f"{day} (US), basis: {str(basis)[:120] or 'company filing'}"
    rows = [r for r in _loe_rows() if r["product"].lower().split()[0] == brand and r.get("us_loe")]
    cites = []
    for r in rows[:2]:
        for rec in _tenk_docs(idx, ticker, r.get("accession")):
            c = cite_quote(idx, rec.canonical_id, r["quote"], claim_type="number", value=str(r["us_loe"]), unit="year")
            if _ok(c):
                cites.append(c)
                break
    if rows:
        r = rows[0]
        v = f"{r['us_loe']} (US), basis: {r['basis']}"
        return r["us_loe"], {"us_loe": r["us_loe"], "eu_loe": r.get("eu_loe"), "japan_loe": r.get("japan_loe"), "basis": r["basis"],
                              "section": r["section"], "source": "company_stated_loe.jsonl"}, cites, v
    row = ip_table_row(idx, ticker, brand)
    if row and row["us_loe"]:
        c = cite_quote(idx, row["doc"], row["quote"], claim_type="number", value=row["us_loe"], unit="year", hint=row["page"])
        if _ok(c):
            return row["us_loe"], {"us_loe": row["us_loe"], "us_loe_group": row["us_loe_group"],
                                   "source": "annual report Patent Expiries of Key Marketed Products row",
                                   "basis": "key patent expiry years, US column"}, [c], f"{row['us_loe_group']} (annual report IP table)"
    # text-search fallback: (a) a table row "<brand> ... compound patent U.S. <year>", (b) a sentence with the brand and an expiry year
    names = [n for n in (brand, ent.get("ingredient", "").lower()) if n]
    for rec in _tenk_docs(idx, ticker)[:1]:
        for n, (printed, text) in idx.pages(rec.canonical_id).items():
            flat = " ".join(text.split())
            for x in names:
                m = re.search(r"\b" + re.escape(x) + r"\b[A-Za-z/ ]{0,25}?compound patent U\.S\. (20\d\d)", flat, re.I)
                if m:
                    c = cite_quote(idx, rec.canonical_id, m.group(0), claim_type="number", value=m.group(1), unit="year", hint=n)
                    if _ok(c):
                        return m.group(1), {"us_loe": m.group(1), "source": "10-K intellectual property table (row matched by text)",
                                            "basis": "compound patent, estimated expiry"}, [c], f"{m.group(1)} (10-K compound patent row)"
        best = None
        for n, (printed, text) in idx.pages(rec.canonical_id).items():
            for s_ in re.split(r"(?<=[.;])\s+|\n", text):
                sl = s_.lower()
                if any(re.search(r"\b" + re.escape(x) + r"\b", sl) for x in names) and re.search(r"expir|loss of (market )?exclusivity", sl):
                    ys = [y for y in re.findall(r"\b(20[2-5]\d)\b", s_) if int(y) >= 2026]
                    if ys and 40 < len(s_) < 600:
                        best = (n, " ".join(s_.split()), min(ys))
                        break
            if best:
                break
        if best:
            c = cite_quote(idx, rec.canonical_id, best[1], claim_type="quote", hint=best[0])
            if _ok(c):
                return best[2], {"us_loe": best[2], "source": "10-K text search (sentence naming the product and an expiry year)",
                                 "caveat": "year taken from a sentence, not from the LOE table; check the quote"}, [c], f"{best[2]} (text search)"
    return None, {}, [], ""


def _timeline_cell(idx, data, ticker, ent):
    slug = ent["slug"]
    if not slug:
        return Cell(empty_reason=ent.get("note") or "no drug pack")
    L = _labels()
    if not L._label_path(slug).exists():
        return Cell(empty_reason=f"drug pack {slug} missing")
    P = L.profile(slug)
    det, refs, parts = {}, [], []
    ob_end = P["protection_end"]["value"]
    pat, exl = P["latest_patent_expiry"], P["exclusivity"]
    if pat["value"]:
        det["orange_book_latest_patent"] = pat["value"]
        parts.append(f"Orange Book latest patent {pat['value']} ({P['patent_count']['value']} patents)")
        refs.append({"file": f"data/corpus/drugs/{slug}/orange_book_patents.csv", "key": f"Patent_No={pat.get('patent_no')}"})
    exl_prod = [e for e in (exl["value"] or []) if not str(e.get("code", "")).upper().startswith("ODE")]
    if exl["value"]:
        det["orange_book_exclusivity"] = exl["value"]
        det["orphan_exclusivity_not_protection"] = [e for e in exl["value"] if e not in exl_prod]
    if exl_prod:
        parts.append("exclusivity " + ", ".join(f"{e['code']} {e['date']}" for e in exl_prod[-3:]))
        refs.append({"file": f"data/corpus/drugs/{slug}/orange_book_exclusivity.csv", "key": slug})
    pb = P["purple_exclusivity"]
    if pb.get("derived_12y_reference_exclusivity") or pb["value"]:
        det["purple_book"] = {"exclusivity": pb["value"], "derived_12y": pb.get("derived_12y_reference_exclusivity"),
                              "biosimilars_referencing": P["biosimilars_referencing"]["value"]}
        parts.append(f"Purple Book 12y reference exclusivity {pb.get('derived_12y_reference_exclusivity')}")
        refs.append({"file": f"data/corpus/drugs/{slug}/purple_book.csv", "key": slug})
    if P["paragraph_iv"]["value"]:
        det["paragraph_iv_filings"] = P["paragraph_iv"]["value"]
    # orphan drug exclusivity is indication-limited: it is not product protection (Parker, red team v3 (d)), so the
    # labels profile's protection_end (max over every date incl. orphan) is kept for reference but never printed
    det["protection_end_labels_profile_not_used"] = ob_end
    ob_end = None
    cs_val, cs_det, cites, cs_txt = _company_stated(idx, ticker, ent) if ent["maker"] and _maker_ticker(ent) == ticker else (None, {}, [], "")
    if cs_val is None and _maker_ticker(ent) and _maker_ticker(ent) != ticker:
        t2 = _maker_ticker(ent)
        cs_val, cs_det, cites, cs_txt = _company_stated(idx, t2, ent)
    disc = None
    if cs_val:
        det["company_stated"] = cs_det
        parts.insert(0, f"Company-stated US LOE {cs_txt}")
        if ob_end:
            # review D10: company-stated dates come as "8/27/2029" too; read the 4-digit year, never the first 4 chars
            cs_year = re.search(r"\d{4}", str(cs_val))
            gap = int(str(ob_end)[:4]) - int(cs_year.group()) if cs_year else 0
            if abs(gap) >= 1:
                disc = (f"Orange/Purple Book protection ends {ob_end[:4]} vs company-stated {cs_val}: "
                        f"{abs(gap)} year(s) {'later' if gap > 0 else 'earlier'} in the regulatory data "
                        "(the 10-K date is usually the compound patent; Orange Book lists the latest patent of any kind)")
                det["discrepancy"] = disc
                parts.append(disc)
    else:
        det["company_stated"] = None
    if ent.get("variant"):
        det["note"] = "Orange Book pack is shared by the injection and tablet presentations"
    if not parts:
        return Cell(empty_reason="no Orange Book, Purple Book or company-stated rows for this drug")
    empty_note = "" if cites else "no company-stated date located in the 10-K index (regulatory dates are table refs only)"
    return Cell("; ".join(parts), det, cites, refs, empty_note)


_MAKER = {"Merck": "MRK", "Bristol Myers Squibb": "BMY", "Pfizer": "PFE", "Eli Lilly": "LLY", "Novo Nordisk": "NVO",
          "AbbVie": "ABBV", "Johnson & Johnson": "JNJ", "AstraZeneca": "AZN", "Amgen": "AMGN", "Gilead": "GILD"}


def _maker_ticker(ent):
    return _MAKER.get(ent["maker"])


# ------------------------------------------------------------------ pricing
def _policy_rows(data, ticker, ent):
    pe = data.csv("verified/policy/policy_exposure.csv")
    if not len(pe):
        return pe
    t = _maker_ticker(ent)
    if not t:
        return pe.iloc[0:0]
    brand = ent["name"].split(" (")[0].split()[0].lower()
    s = pe[(pe["ticker"] == t) & pe["force"].isin(["IRA", "MFN"])]
    m = s["item"].fillna("").str.lower().str.contains(brand) | s["value"].fillna("").astype(str).str.lower().str.contains(brand)
    return s[m | ((s["item"].fillna("").str.contains("TrumpRx")) & s["value"].fillna("").astype(str).str.lower().str.contains(brand))]


def _policy_doc(idx, r):
    d = str(r["doc"])
    ticker = r["ticker"]
    cands = []
    if d.startswith("data/moat/"):
        cands.append("policy_gov:" + d[len("data/moat/"):])
    base = d.split("/")[-1]
    cands += [f"{ticker}:{base}", f"{ticker}:companies/{ticker}/{base}"]
    for c in cands:
        if c in idx:
            return c
    return None


def _policy_cite(idx, r):
    doc = _policy_doc(idx, r)
    if not doc:
        return None
    pg = None
    s = str(r.get("printed_page_or_section", ""))
    if re.fullmatch(r"\d+", s):
        pg = int(s)
    return cite_quote(idx, doc, str(r["quote"]), page=pg)


def _pricing_cell(idx, data, ticker, ent):
    slug = ent["slug"]
    det, cites, refs, parts = {}, [], [], []
    if not slug:
        return Cell(empty_reason=ent.get("note") or "generic or unlisted product, no price series")
    ge = data.csv("verified/pricing/gtn_exposure.csv")
    gx = ge[ge["drug"] == slug] if len(ge) else ge
    if len(gx):
        r = gx.iloc[0]
        det["gtn_exposure"] = {"list_like_series": r.get("list_like_series"), "list_like_pct": r.get("list_like_pct"),
                               "list_like_years": [r.get("list_like_from"), r.get("list_like_to")],
                               "net_like_series": r.get("net_like_series"), "net_like_pct": r.get("net_like_pct"),
                               "net_like_years": [r.get("net_like_from"), r.get("net_like_to")],
                               "exposure_call": r.get("exposure_call"), "confidence": r.get("confidence")}
        if isinstance(r.get("exposure_call"), str):
            parts.append("list vs net proxy: " + r["exposure_call"])
        refs.append({"file": "verified/pricing/gtn_exposure.csv", "key": slug})
    gp = data.csv("verified/pricing/gtn_proxy.csv")
    gp = gp[gp["drug"] == slug] if len(gp) else gp
    if len(gp):
        r = gp.sort_values("year").iloc[-1]
        d = {"year": int(r["year"])}
        for k in ("partd_spend_per_unit", "partd_spend_per_claim", "asp_payment_limit_per_hcpcs_unit", "asp_hcpcs",
                  "nadac_weighted_per_unit", "nadac_per_30day_median", "ira_mfp_per_30day", "partd_vs_nadac_ratio"):
            if k in r and pd.notna(r[k]):
                d[k] = float(r[k]) if k != "asp_hcpcs" else r[k]
        det["price_proxies"] = d
        bits = []
        if "partd_spend_per_claim" in d:
            bits.append(f"Part D gross ${d['partd_spend_per_claim']:,.0f}/claim")
        if "asp_payment_limit_per_hcpcs_unit" in d:
            bits.append(f"Part B ASP limit ${d['asp_payment_limit_per_hcpcs_unit']:,.2f}/{d.get('asp_hcpcs')} unit")
        if "nadac_weighted_per_unit" in d:
            bits.append(f"NADAC ${d['nadac_weighted_per_unit']:,.2f}/unit")
        if bits:
            parts.append(f"{d['year']}: " + ", ".join(bits))
        refs.append({"file": "verified/pricing/gtn_proxy.csv", "key": f"{slug}|{d['year']}"})
    for _, r in _policy_rows(data, ticker, ent).iterrows():
        c = _policy_cite(idx, r)
        item, val = str(r["item"]), str(r["value"])
        if "revenue" in item.lower():
            continue
        if "IRA" == r["force"] and ("MFP" in item or "selected" in item.lower() or "selection" in item.lower() or "list price" in item):
            det.setdefault("ira", []).append({"row_id": r["row_id"], "item": item, "value": val, "unit": r["unit"]})
            parts.append(f"{item}: {val} {r['unit'] if str(r['unit']) not in ('nan', 'flag', 'date') else ''}".strip())
            if _ok(c):
                cites.append(c)
        elif r["force"] == "MFN" and "TrumpRx" in item:
            det.setdefault("mfn_cash", []).append({"row_id": r["row_id"], "value": val, "date": r["effective_date"]})
            parts.append(f"MFN/TrumpRx cash: {val}")
            if _ok(c):
                cites.append(c)
    try:
        L = _labels()
        ira = L.profile(slug)["ira"]["value"]
        det["ira_status"] = ira
        exp_ = any("expected" in str(x["item"]).lower() for x in det.get("ira", []))
        parts.append("IRA: selected IPAY %s, MFP $%s/30d" % (ira["ipay"], round(ira["mfp_per_30_days"], 2)) if ira["selected"]
                     else ("IRA: not yet selected (company expects selection)" if exp_ else "IRA: not selected"))
        med = L.profile(slug)["medicare"]["value"]
        if med:
            det["medicare"] = {k: med[k] for k in ("part", "year", "spend", "claims", "beneficiaries", "avg_per_claim")}
            refs.append({"file": f"data/corpus/drugs/{slug}/medicare_part{med['part'].lower()}_spending.csv", "key": f"{med['year']}"})
    except Exception:
        pass
    # company-level realised list-vs-net anchor
    lv = data.csv("verified/pricing/company_list_vs_net.csv")
    t = _maker_ticker(ent)
    if len(lv) and t and (lv["ticker"] == t).any():
        r = lv[lv["ticker"] == t].sort_values("year").iloc[-1]
        det["company_gtn_anchor"] = {"year": int(r["year"]), "avg_list_change_pct": r["avg_list_price_change_pct"],
                                     "avg_net_change_pct": r["avg_net_price_change_pct"], "avg_discount_pct": r["avg_discount_pct"]}
        refs.append({"file": "verified/pricing/company_list_vs_net.csv", "key": f"{t}|{int(r['year'])}"})
    if not parts:
        return Cell(empty_reason="no price series, IRA row or MFN row for this drug")
    miss = "" if cites else "no CMS or White House page located for this drug; values are table refs only"
    return Cell("; ".join(parts), det, cites, refs, miss)


# ------------------------------------------------------------------ revenue and context
def product_revenue(data, ticker, slug):
    """-> {"usd": total, "us": US or None, "basis", "ref"} from product_revenue_quarterly (latest 12 months), else None."""
    d = data.csv("tables/product_revenue_quarterly.csv")
    if not len(d):
        return None
    base = d[(d["ticker"] == ticker) & d["product_member"].fillna("").str.lower().str.contains(slug.split("-")[0], regex=False)
             & d["concept"].fillna("").str.contains("Revenues") & ~d["product_member"].fillna("").str.lower().str.contains("qlex|membermember")]
    if not len(base):
        return None

    def latest(frame):
        if not len(frame):
            return None
        yr = frame[frame["days"] >= 350].sort_values("period_end")
        if len(yr):
            r = yr.iloc[-1]
            return float(r["value_usd"]), f"FY ending {r['period_end']}", r
        r = frame.sort_values("period_end").iloc[-1]
        return float(r["value_usd"]) * 365 / float(r["days"]), f"annualised {int(r['days'])}-day period ending {r['period_end']}", r

    tot = latest(base[base["geography"].isna() & base["other_dims"].isna()]) or latest(base[base["geography"].isna()])
    if not tot:
        return None
    us = latest(base[(base["geography"] == "country:US") & (base["period_end"] == tot[2]["period_end"]) & (base["days"] == tot[2]["days"])])
    r = tot[2]
    return {"usd": tot[0], "us": us[0] * (365 / float(us[2]["days"]) if tot[1].startswith("annual") else 1) if us else None,
            "basis": tot[1], "ref": f"product_revenue_quarterly.csv {ticker}|{r['product_member']}|{r['period_end']}|{int(r['days'])}d"}


_N = r"\d{1,3},\d{3}"            # thousands form (sales in USD millions); years never match
_S = r"(?:\d{1,3},\d{3}|\d{1,3}|\u2014)"
_SIX = re.compile(r"(?<![\d,])(" + _N + r"\s+" + _S + r"\s+" + _S + r"\s+" + _N + r"\s+" + _S + r"\s+" + _S + r")(?![\d,])")


def ip_table_row(idx, ticker, brand):
    """Annual-report 'Patent Expiries of Key Marketed Products' row (AstraZeneca 20-F layout): brand, description, US expiry
    group, other territories, then US sales for 3 years and rest-of-world sales for 3 years (USD millions, newest first).
    -> dict(us_loe_group, us_loe, us_sales, row_sales, quote, page, doc) or None."""
    for rec in _tenk_docs(idx, ticker)[:1]:
        for n, (_, text) in idx.pages(rec.canonical_id).items():
            if "Patent Expiries of Key Marketed Products" not in text and "Patent expiries of key marketed products" not in text:
                continue
            flat = " ".join(text.replace("\u200b", " ").split())
            m = re.search(r"\b" + re.escape(brand) + r"\b(?:/ ?\w+)?(?: \d)? \([a-z ]+\)", flat, re.I)
            if not m:
                continue
            tail = flat[m.end():]
            six = _SIX.search(tail)
            if not six:
                continue
            seg = tail[:six.start()]
            tl = seg[seg.rfind(". ") + 2:] if ". " in seg else seg
            g = re.match(r"\s*((?:20\d\d(?:-20\d\d)?)(?:\s*,\s*20\d\d(?:-20\d\d)?)*)", tl)
            nums = [float(x.replace(",", "")) if x != "\u2014" else 0.0 for x in six.group(1).split()]
            quote = (tl.strip() + " " + six.group(1)).strip()
            return {"us_loe_group": g.group(1) if g else None, "us_loe": re.match(r"20\d\d", g.group(1)).group(0) if g else None,
                    "us_sales": nums[:3], "row_sales": nums[3:], "quote": quote[-300:], "sales_quote": six.group(1), "page": n, "doc": rec.canonical_id, "first_sales": six.group(1).split()[0]}
    return None


@lru_cache(maxsize=8)
def _scorecard(root_key):
    p = Path(root_key) / "verified" / "market" / "priced_in_scorecard.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


# ------------------------------------------------------------------ compare
def compare(ticker, product, rivals=None, data_root=None, index=None):
    """Side-by-side of `product` (a drug-pack slug or display name) against its appendix rivals. `rivals` may be a list of
    display names or slugs to restrict to; default is the appendix set."""
    ticker = ticker.upper()
    prod = product.lower()
    app = APPENDIX.get(ticker)
    if not app or prod not in app["products"]:
        raise KeyError(f"{ticker}/{product} is not in the case appendix (known: {sorted(app['products']) if app else 'none'})")
    spec = app["products"][prod]
    ents = [spec["self"]] + list(spec["rivals"])
    if rivals:
        want = {r.lower() for r in rivals}
        ents = [ents[0]] + [e for e in ents[1:] if e["name"].lower() in want or (e["slug"] or "") in want]
    data, idx = Data(data_root), (index or load_index(default_db()))
    rows = {k: {} for k, _ in ROWS}
    for e in ents:
        cells = _label_cells(idx, data, e)
        for k in ("approved_uses", "safety", "dosing"):
            rows[k][e["name"]] = cells[k]
        rows["timeline"][e["name"]] = _timeline_cell(idx, data, ticker, e)
        rows["pricing"][e["name"]] = _pricing_cell(idx, data, ticker, e)
    notes = []
    ctx = {"starter": app["starter"], "company": app["company"]}
    rev = product_revenue(data, ticker, spec["self"]["slug"]) if spec["self"]["slug"] else None
    if rev is None and spec["self"]["slug"]:
        row = ip_table_row(idx, ticker, spec["self"]["name"].split()[0])
        if row:
            c = cite_quote(idx, row["doc"], row["sales_quote"], claim_type="number", value=row["first_sales"], unit="USD millions", hint=row["page"])
            if _ok(c):
                ctx["revenue_citation"] = c.to_dict()
                rev = {"usd": (row["us_sales"][0] + row["row_sales"][0]) * 1e6, "us": row["us_sales"][0] * 1e6,
                       "basis": "annual report table row, latest fiscal year (US + rest of world, derived sum of two cited numbers)",
                       "ref": f"{row['doc']} p{row['page']}", "_cite": c}
    ctx["revenue"] = {k: v for k, v in rev.items() if not k.startswith("_")} if rev else None
    if rev and "_cite" in rev:
        ctx["_revenue_cite"] = rev["_cite"]
    if not rev:
        notes.append("product revenue not found in product_revenue_quarterly.csv or the annual report IP table; revenue-based channels are not quantified")
    sc = _scorecard(str(data.root)) if data.root else pd.DataFrame()
    ctx["scorecard"] = sc[sc["ticker"] == ticker].set_index("topic")[["share_of_quarters_asked", "analyst_turns_on_topic", "share_of_all_analyst_turns",
                                                                      "analyst_attention_tier", "last_quarter_asked"]].to_dict("index") if len(sc) else {}
    ctx["data_root"] = str(data.root)
    ctx["_data"] = data
    return ProductComparison(ticker, prod, AS_OF, ents, rows, notes, ctx)


# ------------------------------------------------------------------ tie to financials
@dataclass
class ProductClaim(Claim):
    """A Claim in the FIND row shape (docs/quant_model.md 4.10), signal_family 'product'."""
    id: str = ""
    ticker: str = ""
    signal_family: str = "product"
    channel: str = ""
    direction: str = "negative"
    impact: dict = field(default_factory=dict)
    peer: dict = field(default_factory=dict)
    confidence: str = "low"
    confidence_reasons: list = field(default_factory=list)
    obscurity_note: str = ""
    flags: list = field(default_factory=list)

    numeric_check: dict = field(default_factory=dict)

    def record(self):
        from agent.needle.cite.locator import _jsonable
        d = {k: getattr(self, k) for k in ("id", "ticker", "signal_family", "channel", "direction", "impact", "peer", "confidence",
                                          "confidence_reasons", "obscurity_note", "flags", "numeric_check")}
        d["sentence"] = self.text
        d["citations"] = [c.to_dict() for c in self.citations]
        d["derived"] = _jsonable(self.derived or {})
        d["assumptions"] = _jsonable(self.assumptions or {})
        return d


OBSCURITY_NOTE = ("Label and exclusivity facts are old (often years), so a FIND obscurity term computed on the label date decays "
                  "to about zero. Compute O on the financial consequence instead: its age is the date the revenue effect first "
                  "becomes visible (MFP effective date, LOE year, first quarter the Medicare gap could show), and the "
                  "analyst-attention term is the scorecard share for the consequence's topic, not the label's.")

# loss-rate band for first full year after generic/biosimilar entry, from loe_curves.csv (US rows): q25/median/q75 pct of peak
CM_DEFAULT = 0.70           # spec 4.3: contribution margin on an incremental net revenue dollar


def _fmt_m(x):
    return f"${abs(x) / 1e6:,.0f}M" if abs(x) < 1e9 else f"${abs(x) / 1e9:,.2f}B"


def _loe_band(modality):
    c = cache_root()
    if not c:
        return None
    d = pd.read_csv(c / "loe_curves.csv")
    d = d[(d["geography"] == "US") & (d["modality"] == modality) & (d["included"] == True)]  # noqa: E712
    t1 = d[d["t"] == 1]["pct_of_peak"].dropna()
    if len(t1) < 3:
        return None
    q = statistics.quantiles(list(t1), n=4)
    return {"n": int(len(t1)), "q25": q[0], "median": statistics.median(t1), "q75": q[2]}


def _is_biologic(cmp_, ent):
    L = _labels()
    P = L.profile(ent["slug"])
    return bool(P["purple_exclusivity"]["value"] or P["biosimilars_referencing"]["value"]) or P["route"]["value"] in ("intravenous", "subcutaneous") \
        and (P["biosimilars_referencing"]["value"] is not None)


def _indication_text(P):
    """Indication names as one string, for the IRA class rule's oncology / HIV test."""
    try:
        return " ".join(str(x) for x in (P["indications"]["value"] or []))
    except Exception:
        return ""


def _channels(cmp_):
    """All feasible label-to-numbers channels for the product, each with math. Returned unranked."""
    me = cmp_.entities[0]
    out, uq = [], []
    rev = (cmp_.context.get("revenue") or {}).get("usd")
    rev_us = (cmp_.context.get("revenue") or {}).get("us")
    L = _labels()
    P = L.profile(me["slug"])
    pricing = cmp_.rows["pricing"][me["name"]]
    timeline = cmp_.rows["timeline"][me["name"]]
    # (1) IRA MFP
    ira = P["ira"]["value"]
    pol = pricing.detail.get("ira", [])
    mfp = next((float(x["value"]) for x in pol if "MFP per 30-day" in x["item"]), None)
    listp = next((float(x["value"]) for x in pol if "list price per 30-day" in x["item"]), None)
    med = P["medicare"]["value"]
    if ira["selected"] and med and med["part"] == "D" and med["claims"]:
        mfp = mfp or ira["mfp_per_30_days"]
        listp = listp or (med["avg_per_claim"])
        if mfp and listp:
            # the one IRA formula (impact.ira_class_rule, review S3): G x max(0, k x d - m_avoided)
            G = med["claims"] * listp
            d = max(0.0, 1 - mfp / listp)
            revs, k, low, part_d = IM.ira_class_dollars(G, d, me["name"], _indication_text(P), part_d=True)
            res = {case: -v for case, v in zip(("bull", "base", "bear"), revs)}
            out.append({"channel": "ira_mfp", "topic": "IRA_negotiation", "dRev": res,
                        "formula": (f"dRev = -G x max(0, k x d - m_avoided): G = Part D claims {med['year']}: {med['claims']:,.0f} x list30 ${listp:,.0f}; "
                                    f"d = 1 - MFP30 ${mfp:,.0f} / list30 = {d:.0%}; k = {k} ({'low-rebate class' if low else 'rebated class'}); "
                                    f"m_avoided = {W.M_MDP_AVOIDED} (FIND impact.ira_class_rule, the one IRA formula)"),
                        "inputs": {"claims": med["claims"], "list30": listp, "mfp30": mfp, "d": d, "k": k, "m_avoided": W.M_MDP_AVOIDED, "mfp_effective": ira["mfp_effective"]},
                        "years_to_event": max(0.0, (pd.Timestamp(ira["mfp_effective"]) - pd.Timestamp(AS_OF)).days / 365.25) if ira["mfp_effective"] else None,
                        "cm": W.CM_PRICE, "assumed": False, "citations": [c for c in pricing.citations]})
    elif not ira["selected"]:
        exp = [x for x in pol if "expected" in x["item"].lower() and "selection" in x["item"].lower()]
        cuts = _ira_cuts(cmp_.context.get("_data"))
        if exp and med and cuts:
            eff = next((x["value"] for x in exp if re.match(r"20\d\d-\d\d-\d\d", str(x["value"]))), None)
            q = statistics.quantiles(cuts, n=4)
            d = (q[0] / 100, statistics.median(cuts) / 100, q[2] / 100)
            revs, k, low, part_d = IM.ira_class_dollars(med["spend"], d, me["name"], _indication_text(P),
                                                        part_d=med["part"] == "D")
            res = {case: -v for case, v in zip(("bull", "base", "bear"), revs)}
            out.append({"channel": "ira_expected", "topic": "IRA_negotiation", "dRev": res,
                        "formula": (f"dRev = -G x max(0, k x d - m_avoided): G = Medicare Part {med['part']} gross spend {med['year']} ({_fmt_m(med['spend'])}); "
                                    f"d = observed CMS cuts in the verified IRA rows (n={len(cuts)}): q25 {q[0]:.0f} / median {statistics.median(cuts):.0f} / q75 {q[2]:.0f} percent (bull/base/bear); "
                                    f"k = {k}; m_avoided = {W.M_MDP_AVOIDED if part_d else (0.0, 0.0, 0.0)} (FIND impact.ira_class_rule)"),
                        "inputs": {"medicare_spend": med["spend"], "year": med["year"], "cuts_pct": cuts, "mfp_effective": eff},
                        "years_to_event": max(0.0, (pd.Timestamp(eff) - pd.Timestamp(AS_OF)).days / 365.25) if eff else None,
                        "cm": W.CM_PRICE, "assumed": False, "citations": [c for c in pricing.citations]})
        else:
            uq.append("IRA: product is not a selected drug in the pack and no expected-selection row exists")
    # (2) LOE erosion
    cs = timeline.detail.get("company_stated") or {}
    year = None
    for v in (cs.get("us_loe"), (timeline.detail.get("protection_end_regulatory") or "")[:4] or None):
        if v and str(v)[:4].isdigit():
            year = int(str(v)[:4])
            break
    if year and rev:
        base_rev = rev_us or rev
        yrs = year - 2026.8
        if yrs <= 6:
            modality = "biologic" if _is_biologic(cmp_, me) else "small_molecule"
            band = _loe_band(modality)
            if band:
                res = {"bull": -base_rev * (1 - band["q75"] / 100), "base": -base_rev * (1 - band["median"] / 100), "bear": -base_rev * (1 - band["q25"] / 100)}
                out.append({"channel": "loe_erosion", "topic": "biosimilar_generic", "dRev": res,
                            "formula": f"dRev = -annual {'US ' if rev_us else 'worldwide '}revenue {_fmt_m(base_rev)} x (1 - pct_of_peak at t=1 / 100); {modality} US curves n={band['n']}: q75 {band['q75']:.0f} / median {band['median']:.0f} / q25 {band['q25']:.0f} percent of peak",
                            "inputs": {"revenue": base_rev, "revenue_is_us": bool(rev_us), "loe_year": year, "modality": modality, "band": band},
                            "years_to_event": max(0.0, yrs), "cm": 1.0 if modality == "biologic" else CM_DEFAULT, "assumed": False,
                            "citations": list(timeline.citations) + ([cmp_.context["_revenue_cite"]] if "_revenue_cite" in cmp_.context else [])})
        else:
            uq.append(f"LOE {year} is beyond a 6 year horizon; no erosion channel")
    elif year is None:
        uq.append("no LOE year for the product")
    # (3) label breadth to Medicare Part D access (rival Part D claims where the product has none)
    mine = P["indication_count"]["value"]
    own_tokens = _use_tokens(cmp_.rows["approved_uses"][me["name"]].detail.get("names", []))
    ranked = sorted((r for r in cmp_.entities[1:] if r["slug"]),
                    key=lambda r: -len(own_tokens & _use_tokens(cmp_.rows["approved_uses"][r["name"]].detail.get("names", []))))
    for r in ranked:
        if not (own_tokens & _use_tokens(cmp_.rows["approved_uses"][r["name"]].detail.get("names", []))):
            continue            # no shared use: the rival is not competing for the same patients, so no breadth gap is claimed
        PR = L.profile(r["slug"])
        rm, mm = PR["medicare"]["value"], med
        if rm and mm and rm["part"] == "D" and mm["part"] == "D" and PR["indication_count"]["value"] and mine is not None \
                and PR["indication_count"]["value"] > mine and rm["claims"] > 5 * max(mm["claims"], 1) and mm["avg_per_claim"]:
            gap = rm["claims"] - mm["claims"]
            res = {}
            for case, cap, g in (("bear", 0.50, 0.50), ("base", 0.35, 0.60), ("bull", 0.20, 0.70)):
                res[case] = -gap * cap * mm["avg_per_claim"] * (1 - g)
            rin = [i for i in cmp_.rows["approved_uses"][r["name"]].detail.get("names", [])]
            out.append({"channel": "label_breadth_medicare", "topic": "top_products", "dRev": res,
                        "formula": (f"dRev = -(rival Part D claims {rm['claims']:,.0f} - own {mm['claims']:,.0f}) x capture x own gross per claim "
                                    f"${mm['avg_per_claim']:,.0f} x (1 - GTN); capture 50/35/20 percent (bear/base/bull, ASSUMED, no published elasticity); GTN 50/60/70 percent"),
                        "inputs": {"rival": r["name"], "rival_claims": rm["claims"], "own_claims": mm["claims"], "year": mm["year"],
                                   "own_indications": len(cmp_.rows["approved_uses"][me["name"]].detail.get("names", [])) or mine,
                                   "rival_indications": len(rin) or PR["indication_count"]["value"], "rival_uses": rin,
                                   "label_change": _last_label_change(cmp_.context.get("_data"), me["slug"])},
                        "years_to_event": 0.0, "cm": CM_DEFAULT, "rival": r["name"], "assumed": True,
                        "citations": [c for n in (me["name"], r["name"]) for c in cmp_.rows["approved_uses"][n].citations]})
            break
    # (4) cash price / MFN scenario
    mfn = pricing.detail.get("mfn_cash")
    if mfn and rev:
        nums = [float(x.replace(",", "")) for x in re.findall(r"\$([\d,]+)", mfn[0]["value"])]
        listm = _first_list_month(pricing)
        if nums and listm:
            cash = nums[0]
            cut = 1 - cash / listm
            res = {"bear": -rev * 0.40 * cut, "base": -rev * 0.25 * cut, "bull": -rev * 0.10 * cut}
            out.append({"channel": "mfn_cash_price", "topic": ["MFN", "gross_to_net_price"], "assumed": True, "dRev": res,
                        "formula": f"dRev = -annual revenue {_fmt_m(rev)} x share of volume moved to the cash price x (1 - cash ${cash:,.0f} / list ${listm:,.0f}); share 40/25/10 percent (bear/base/bull) is an ASSUMED SCENARIO, not data",
                        "inputs": {"cash": cash, "list_month": listm, "cut": cut, "revenue": rev},
                        "years_to_event": 0.0, "cm": 1.0, "citations": [c for c in pricing.citations if "TrumpRx" in c.quote or "per month" in c.quote]})
    # (5) boxed warning difference (not class-wide) and convenience
    bw = P["boxed_warning"]["value"]
    if bw and rev:
        rv = [(r, _labels().profile(r["slug"])["boxed_warning"]["value"]) for r in cmp_.entities[1:] if r["slug"]]
        if rv and all(v is False for _, v in rv):
            res = {"bear": -rev * 0.25, "base": -rev * 0.10, "bull": 0.0}
            out.append({"channel": "boxed_warning_share", "topic": "top_products", "dRev": res, "assumed": True,
                        "formula": f"dRev = -annual revenue {_fmt_m(rev)} x 10 to 25 percent of US volume over 12-18 months (boxed warning added; pharma_impact_math KQ6); applied to a static difference as a ceiling only",
                        "inputs": {"revenue": rev}, "years_to_event": 1.0, "cm": CM_DEFAULT, "assumed": True, "citations": list(cmp_.rows["safety"][me["name"]].citations)})
        elif rv:
            uq.append("boxed warning is class-wide (a rival also carries one): elasticity near zero, no channel")
    if not out:
        uq.append("no channel had its inputs")
    return out, uq


_STOP = {"of", "the", "in", "and", "with", "for", "to", "or", "risk", "adults", "patients", "treatment", "reduction", "disease"}


def _ira_cuts(data):
    if data is None:
        return []
    pe = data.csv("verified/policy/policy_exposure.csv")
    if not len(pe):
        return []
    s = pe[(pe["force"] == "IRA") & pe["item"].fillna("").str.contains("% cut of MFP vs list") & pe["status"].isin(["verified", "fixed", "added"])]
    return [float(v) for v in pd.to_numeric(s["value"], errors="coerce").dropna()]


def _use_tokens(names):
    return {w for n in names for w in re.findall(r"[a-z]{4,}", n.lower()) if w not in _STOP}


def _last_label_change(data, slug):
    """(date, n_indications) of the most recent label version whose indication count differs from the previous one."""
    if data is None:
        return None
    d = data.csv("tables/indication_timeline.csv")
    d = d[d["drug"] == slug].sort_values("effective_date") if len(d) else d
    if not len(d):
        return None
    prev, hit = None, None
    for _, r in d.iterrows():
        if prev is not None and r["n_indications"] != prev:
            hit = (r["effective_date"], int(r["n_indications"]))
        prev = r["n_indications"]
    return hit


def _first_list_month(pricing):
    for x in pricing.detail.get("mfn_cash", []):
        pass
    for c in pricing.citations:
        m = re.search(r"from \$([\d,]+) per month", c.quote)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def tie_to_financials(comparison, findings=None):
    """Return product findings (ProductClaim, a Claim) that show where a label or protection difference appears, or should
    appear, in the numbers. Ranked by base |dRev| over the next 24 months of horizon plus the first post-event year.
    `findings` (existing engine findings for the ticker, optional) are used only to attach a peer comparison sentence."""
    import hashlib
    cmp_ = comparison
    chans, uq = _channels(cmp_)
    me = cmp_.entities[0]
    claims = []
    from agent.needle.cite.gate import numeric_gate
    from .product_gate import channel_maps
    for ch in sorted(chans, key=lambda c: (bool(c.get("assumed")), -abs(c["dRev"]["base"]))):
        d = ch["dRev"]
        cm = ch["cm"]
        # review C5: the per-number gate replaces "keep the claim when any one citation verifies"
        try:
            xc, dmap, amap = channel_maps(cmp_, ch)
        except Exception as e:                                   # fail closed
            xc, dmap, amap = [], {}, {}
            cmp_.notes.append(f"{ch['channel']}: gate maps failed ({e})")
        seen_ids, cites = set(), []
        for c in list(ch["citations"]) + xc:
            if c is not None and c.verification.ok and c.cite_id not in seen_ids:
                seen_ids.add(c.cite_id)
                cites.append(c)
        rival = ch.get("rival") or (cmp_.entities[1]["name"] if len(cmp_.entities) > 1 else "its rivals")
        sent = _sentence(cmp_, ch)
        math = math_lines(ch)
        res = numeric_gate([("sentence", sent)] + [(f"impact.math[{j}]", m) for j, m in enumerate(math)], cites, dmap,
                           amap)
        if not res.passed:
            cmp_.notes.append(f"{ch['channel']}: withheld by numeric gate: "
                              + "; ".join(f"{u['value']} ({u['reason']})" for u in res.numeric_check["unsupported"][:6]))
            continue
        peer = _peer(cmp_, ch)
        rec_conf = "medium" if ch["channel"] in ("ira_mfp", "loe_erosion") and len(cites) >= 1 else "low"
        reasons = [f"{len(cites)} verified citation(s)"]
        if ch["channel"] in ("mfn_cash_price", "label_breadth_medicare", "boxed_warning_share"):
            reasons.append("bull/base/bear uses an assumed share or elasticity (see formula), so confidence is capped at low")
            rec_conf = "low"
        impact = {"channel": ch["channel"], "formula": ch["formula"], "inputs": ch["inputs"],
                  "dRev": {k: round(v) for k, v in d.items()}, "CM": cm,
                  "dOI": {k: round(v * cm) for k, v in d.items()},
                  "bull_bear": {"bull": round(d["bull"]), "bear": round(d["bear"])},
                  "dEPS": None, "dEPS_note": "dEPS = dRev x CM x (1 - t) / D; t and D are company constants held by the FIND scorer (spec 10.1)",
                  "t_years": ch.get("years_to_event"), "horizon_months": HORIZON_MONTHS, "as_of": cmp_.as_of,
                  "math_lines": math}
        cid = hashlib.sha256(f"{cmp_.ticker}|product|{ch['channel']}|{cites[0].cite_id}".encode()).hexdigest()[:12]
        claims.append(ProductClaim(text=sent, citations=cites, derived=dmap, assumptions=amap,
                                   numeric_check=res.numeric_check, id=cid, ticker=cmp_.ticker, channel=ch["channel"],
                                   direction="negative", impact=impact, peer=peer, confidence=rec_conf, confidence_reasons=reasons,
                                   obscurity_note=OBSCURITY_NOTE, flags=["signal_family=product", "topic=" + "|".join(ch["topic"] if isinstance(ch["topic"], list) else [ch["topic"]]), f"assumed_parameters={bool(ch.get('assumed'))}"]
                                   + (["event_beyond_24_months"] if (ch.get("years_to_event") or 0) > 2 else [])))
    if not claims:
        cmp_.notes.append("tie_to_financials produced no finding: " + "; ".join(uq))
    cmp_.context["unquantified"] = uq
    return claims


def math_lines(ch):
    """The impact lines product.md prints for a channel (gated with the sentence)."""
    d, cm = ch["dRev"], ch["cm"]
    r = {k: round(v) for k, v in d.items()}
    o = {k: round(v * cm) for k, v in d.items()}
    return [f"math: {ch['formula']}",
            f"dRev bull/base/bear: ${r['bull']:,} / ${r['base']:,} / ${r['bear']:,}; dOI at CM {cm}: base ${o['base']:,}"]


def _sentence(cmp_, ch):
    me = cmp_.entities[0]["name"]
    d = ch["dRev"]
    rng = f"{_fmt_m(d['base'])} base ({_fmt_m(d['bull'])} bull to {_fmt_m(d['bear'])} bear)"
    i = ch["inputs"]
    if ch["channel"] == "ira_mfp":
        return (f"{me} is an IRA-selected drug whose Medicare negotiated price takes effect {i['mfp_effective']}, about "
                f"${i['list30'] - i['mfp30']:,.0f} below the 30-day list price, which puts roughly {rng} of annual revenue at risk.")
    if ch["channel"] == "ira_expected":
        return (f"{me} is expected to be selected for IRA price negotiation with the negotiated price effective {i['mfp_effective']}, and "
                f"applying the cuts CMS has already set (median {statistics.median(i['cuts_pct']):.0f}% off list) to its {i['year']} Medicare spend "
                f"of {_fmt_m(i['medicare_spend'])} puts about {rng} of annual revenue at risk.")
    if ch["channel"] == "loe_erosion":
        return (f"{me} loses US exclusivity in {i['loe_year']}, and the first full year after entry has taken a median "
                f"{100 - i['band']['median']:.0f}% of peak sales from comparable {i['modality'].replace('_', ' ')} products, "
                f"about {rng} on {me}'s {_fmt_m(i['revenue'])} of annual revenue.")
    if ch["channel"] == "label_breadth_medicare":
        lc = i.get("label_change")
        tail = (f" ({me}'s label last changed its indication count on {lc[0]}, so the {i['year']} claims mostly predate that change)" if lc else "")
        return (f"{ch['rival']} is labeled for {i['rival_indications']} uses against {me}'s {i['own_indications']} and had "
                f"{i['rival_claims']:,.0f} Medicare Part D claims in {i['year']} against {i['own_claims']:,.0f} for {me}{tail}; closing that "
                f"label-driven coverage gap is worth about {rng} a year on an assumed capture rate.")
    if ch["channel"] == "mfn_cash_price":
        return (f"The US cash price of ${i['cash']:,.0f} a month sits {i['cut']:.0%} below {me}'s ${i['list_month']:,.0f} list price, so every "
                f"point of volume that moves to the cash channel gives up net revenue; on an assumed 10 to 40 percent of volume the range is {rng}.")
    if ch["channel"] == "boxed_warning_share":
        return f"{me} carries a boxed warning that none of its listed rivals carries, which the published elasticity would price at up to {rng}."
    return f"{me}: {ch['channel']} {rng}."


def _peer(cmp_, ch):
    me = cmp_.entities[0]["name"]
    if ch["channel"] == "label_breadth_medicare":
        i = ch["inputs"]
        return {"metric_value": i["own_claims"], "peer_median": i["rival_claims"], "named_peer_row": f"{i['rival']} Part D claims {i['year']} (medicare_partd_spending.csv)",
                "peer_z": None, "note": f"rival maker: {next((e['maker'] for e in cmp_.entities if e['name'] == i['rival']), '')}"}
    rv = cmp_.entities[1:]
    vals = []
    for r in rv:
        c = cmp_.rows["pricing"][r["name"]]
        ira = c.detail.get("ira_status")
        if ira:
            vals.append(f"{r['name']}: IRA {'selected IPAY %s' % ira['ipay'] if ira['selected'] else 'not selected'}")
    return {"metric_value": None, "peer_median": None, "peer_z": None, "named_peer_row": "; ".join(vals) or "no rival row",
            "note": "compared with the listed rivals' IRA status and exclusivity cells in the table"}


# ------------------------------------------------------------------ growth limiter and priced-in call
_STARTER_WORDS = {"IRA_negotiation": ("negotiat", "ira", "medicare"), "biosimilar_generic": ("exclusivity", "patent", "generic", "biosimilar", "expiry"),
                  "MFN": ("price cut", "pricing", "price"), "top_products": ("lead", "market", "obesity", "pill", "growth"),
                  "gross_to_net_price": ("price", "net")}


def growth_limiter(comparison, findings=None):
    """-> (sentence, priced_in, reasons, citations). `findings` are the ProductClaims from tie_to_financials (computed if None).

    The limiter is the channel with the largest base |dRev| among those with inputs. It is called priced in when the market
    has demonstrably asked about it: the scorecard share of quarters in which analysts asked about the channel's topic is at
    least 0.5, AND the consequence matches the case starter thread (the appendix already states it). Consensus is carried as a
    reason only: no revenue consensus is wired to a product, so it is never what flips the call."""
    claims = findings if findings is not None else tie_to_financials(comparison)
    me = comparison.entities[0]
    if not claims:
        return (f"The data do not support naming what limits {me['name']}'s growth: no label-to-numbers channel had its inputs.", False,
                ["no quantified channel; priced-in cannot be tested"] + comparison.context.get("unquantified", []), [])
    top = claims[0]
    topics = next((f.split("=", 1)[1] for f in top.flags if f.startswith("topic=")), "").split("|")
    rows_ = [(t, comparison.context.get("scorecard", {}).get(t)) for t in topics]
    rows_ = [(t, r) for t, r in rows_ if r]
    topic, sc = max(rows_, key=lambda x: x[1]["share_of_quarters_asked"]) if rows_ else (topics[0], None)
    starter = comparison.context.get("starter", "").lower()
    match = any(w in starter for t in topics for w in _STARTER_WORDS.get(t, ()))
    share = float(sc["share_of_quarters_asked"]) if sc else None
    reasons = []
    if sc:
        reasons.append(f"analysts asked about {topic} in {share:.0%} of covered quarters ({sc['analyst_turns_on_topic']} turns, "
                       f"{sc['share_of_all_analyst_turns']:.1%} of all analyst turns; tier: {sc['analyst_attention_tier']}; last asked {sc['last_quarter_asked']})")
    else:
        reasons.append(f"no analyst-question scorecard row for topic {'/'.join(topics)}")
    reasons.append("case starter thread " + ("already names this consequence" if match else "does not name this consequence"))
    reasons.append("consensus: not tested for a product-level number (I/B/E/S revenue consensus is company-level only)")
    priced = bool(sc is not None and share >= 0.5 and match) or bool(share is not None and share >= 0.8)
    d = top.impact["dRev"]
    what = {"ira_mfp": "the Medicare negotiated price", "loe_erosion": "loss of US exclusivity", "ira_expected": "the expected Medicare negotiated price", "label_breadth_medicare": "a narrower label that keeps it out of Medicare coverage",
            "mfn_cash_price": "the shift of volume to the lower cash price", "boxed_warning_share": "its boxed warning"}.get(top.channel, top.channel)
    s = (f"What limits {me['name']}'s growth is {what}, worth about {_fmt_m(d['base'])} a year in the base case, and "
         + ("the market has already priced it in." if priced else "the market has not clearly priced it in."))
    return s, priced, reasons, list(top.citations)
