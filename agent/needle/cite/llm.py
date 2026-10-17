"""Request builder and response parser for cited generation (no API calls are made here).

Pattern (from the citation design notes): send each selected page as a `search_result` content block with
`citations: {"enabled": true}`; `source` is the viewer link (which encodes doc and page, so the response is
self-describing) and `title` is "<doc_title> p. <folio>". The model returns `text` blocks, each with a `citations`
array of `search_result_location` objects (cited_text, search_result_index, start/end_block_index, source, title).
parse_cited_response turns each text block into a Claim, each location into a Citation, and runs verify() on it.

Hard constraints:
  * Citations cannot be combined with structured outputs: a request with citations enabled on any document or
    search_result block AND `output_config.format` returns HTTP 400. Never add a JSON schema to the cited call. If a
    downstream step needs JSON, run a SECOND call with no citations that receives the already-verified claims as text
    (and carries their cite_ids through unchanged); never ask that call to generate citations or quotes.
  * Citations must be enabled on all or none of the documents in a request.
  * cache_control goes on the last search_result block, which caches every block before it (Anthropic caches the
    prefix up to the breakpoint). Reuse the same page list and order to hit the cache across questions.
  * The API's cited_text is not trusted: it is re-verified against the local page text (a model cannot "cite" a
    page that was not sent, and the page number comes from our own source link, never from model output).
"""

import re
from urllib.parse import parse_qs, urlsplit

from agent.findings import _norm, _numbers

from .deeplink import build_viewer_link
from .index import load_index
from .locator import Citation, Claim
from .verify import verify

try:
    from agent.llm import MODEL as DEFAULT_MODEL
except Exception:  # pragma: no cover
    DEFAULT_MODEL = "claude-opus-5-5"

CITATION_SYSTEM_RULE = """CITATION RULE (hard requirement).
Every number and every quotation in your answer must carry a citation to one of the provided source blocks. Quote
figures exactly as they appear in the source (same digits, same units). Write one claim per sentence and cite each
sentence that contains a number or a factual assertion. If the sources do not contain the fact, write "not found in
the provided sources" instead of guessing. Never compute or round a figure that is not printed on a source page
unless you show the calculation with each operand cited. Never invent, infer, or state page numbers or document
names yourself; page references come only from the citations. Any sentence containing a number or quote that has no
citation will be deleted before the reader sees it."""

_YEAR = re.compile(r"^(19|20)\d\d$")
_NUMTOK = re.compile(r"(?<![\w.])[$(]?\d[\d,]*(?:\.\d+)?%?")


def _blocks(text):
    """One text block per paragraph so cited_text is a paragraph, not the whole page. If the API joins the blocks of
    a multi-block citation without whitespace, the substring rung can miss and the fuzzy rung (partial_ratio) catches it."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return [{"type": "text", "text": p} for p in paras] or [{"type": "text", "text": text or " "}]


def build_cited_request(system, question, pages, model=None, max_tokens=2048, cache=True, link="viewer"):
    """Messages API body. pages: list of (canonical_id, page, text, source_url). `link`: 'viewer' (default,
    decodable) or 'deep' (the EDGAR/PDF/DailyMed link, which parse_cited_response cannot decode on its own)."""
    idx = load_index()
    blocks = []
    for cid, page, text, source_url in pages:
        rec = idx.resolve(cid)
        folio = (idx.get_page(cid, page) or (page, "?", ""))[1] if rec else "?"
        stub = Citation(canonical_id=rec.canonical_id if rec else cid, page=page, quote="", source_url=source_url)
        source = build_viewer_link(stub) if link == "viewer" else (source_url or build_viewer_link(stub))
        title = f"{rec.doc_title if rec else cid} {idx.location(cid, page) or page}"
        blocks.append({"type": "search_result", "source": source, "title": title,
                       "content": _blocks(text), "citations": {"enabled": True}})
    if blocks and cache:
        blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return {
        "model": model or DEFAULT_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0,
        "system": [{"type": "text", "text": f"{system}\n\n{CITATION_SYSTEM_RULE}".strip()}],
        "messages": [{"role": "user", "content": blocks + [{"type": "text", "text": question}]}],
    }


def _doc_page_from_source(source):
    q = parse_qs(urlsplit(source or "").query)
    if "doc" in q:
        try:
            return q["doc"][0], int(q.get("page", ["1"])[0])
        except ValueError:
            return q["doc"][0], None
    return None, None


def _find_page(idx, cid, quote):
    nq = _norm(quote)
    for n, (_, t) in idx.pages(cid).items():
        if nq and nq in _norm(t):
            return n
    return None


def _claim_numbers(text):
    return [t for t in _NUMTOK.findall(text or "") if not _YEAR.match(t.strip("$(%,"))]


def parse_cited_response(response_json, index=None, pages=None, documents=None, strict_numbers=True):
    """Response JSON (dict with `content`) -> list[Claim], every Citation already verified.

    pages: the list given to build_cited_request (fallback to map search_result_index when `source` carries no
    doc/page). documents: list of canonical ids or (canonical_id, page) by document_index, for char_location and
    page_location citations from `document` blocks. strict_numbers: a claim whose text has a number that appears in
    none of its cited texts has all its citations downgraded to unverified (the 'every number is cited' rule).
    Whitespace-only text blocks are dropped; uncited text blocks become Claims with no citations (gate rejects them).
    """
    idx = index or load_index()
    claims = []
    for block in response_json.get("content", []):
        if block.get("type") != "text" or not (block.get("text") or "").strip():
            continue
        cites = []
        for raw in block.get("citations") or []:
            c = _to_citation(raw, idx, pages, documents)
            if c is not None:
                cites.append(verify(c, idx))
        claim = Claim(text=block["text"], citations=cites)
        if strict_numbers and cites:
            _enforce_numbers(claim, raw_texts=[r.get("cited_text", "") for r in block["citations"]])
        claims.append(claim)
    return claims


def _enforce_numbers(claim, raw_texts):
    pool = set()
    for t in raw_texts:
        pool |= _numbers(t)
    missing = [t for t in _claim_numbers(claim.text) if _numbers(t) and not _numbers(t) <= pool]
    if missing:
        for c in claim.citations:
            c.verification.status = "unverified"
            c.verification.score = 0.0
            c.verification.detail = f"claim number(s) {missing} not in cited text"
            c.confidence_note = c.verification.detail


def _to_citation(raw, idx, pages, documents):
    typ, quote = raw.get("type"), raw.get("cited_text", "")
    cid = page = None
    if typ == "search_result_location":
        cid, page = _doc_page_from_source(raw.get("source"))
        if cid is None and pages:
            i = raw.get("search_result_index")
            if isinstance(i, int) and 0 <= i < len(pages):
                cid, page = pages[i][0], pages[i][1]
    elif typ in ("char_location", "page_location", "content_block_location"):
        d = raw.get("document_index")
        ref = documents[d] if documents and isinstance(d, int) and 0 <= d < len(documents) else None
        if isinstance(ref, (tuple, list)):
            cid, page = ref[0], ref[1]
        else:
            cid = ref
        if cid is None:
            title = raw.get("document_title") or ""
            cid = next((r.canonical_id for r in idx.records.values() if r.doc_title == title), None)
        if page is None and typ == "page_location":
            page = raw.get("start_page_number")
        if page is None and cid:
            page = _find_page(idx, cid, quote)
    if not cid:
        return Citation(canonical_id="", page=page, quote=quote, confidence_note=f"unresolvable {typ} citation")
    return Citation(canonical_id=cid, page=page, quote=quote, claim_type="quote")
