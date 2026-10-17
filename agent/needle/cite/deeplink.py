"""Deep links: a clickable URL for (document, page, quote). Rules follow the scraper's index contract
(agent/moat, commit 704741d) and branch on source_url, raw doc_type, page_scheme and license.

  SEC filings (annual/quarterly report, 8-K, 6-K, earnings release, EDGAR press release): source_url is the EDGAR
      primary .htm. No page anchors exist, so url + "#:~:text=" + a run of 4 to 8 consecutive quote words,
      percent-encoded (WICG text fragment: every term encodes '-', ',' and '&'). Chrome and Edge honor it; Safari
      lands at the top. The run is validated against the stored page text (review D5): it must appear, word for
      word, inside ONE text block of the page (a line, split again at markdown table pipes), because the browser
      matches within a DOM block and a run that crosses table cells or a heading never matches. A line that reads
      like a flattened table row (two numeric cells side by side) is split at every numeric cell, since each td is its
      own block. Leading bullets and lone punctuation are skipped. No page text, no quote, or no run found -> plain URL, with a note.
  sec_comment_letter: .htm -> text fragment; .pdf -> "#page=N".
  any other .pdf (CMS, White House, Federal Register fact sheets, IR PDFs): url + "#page=N".
  PDF page basis: "#page=" uses the index's page_no (the [[page N]] marker). For page_scheme "pdf_page" that is the
      PDF page by construction. For page_scheme "marker" on a PDF source the converter writes one marker per PDF page,
      and excerpts keep the original numbering (BMY pricing_report_2025.md carries pages 35-39 of the BMS Impact
      Report PDF), so page_no is still the PDF page. page_scheme "section" or "none" (e.g. the ASPE clinical trial
      costs excerpt, one "page" per section) has no PDF page: plain URL, note "no PDF page in the index".
  fda_label: the DailyMed setid page, plain. Section anchors are not stable across label versions, so no "#section-N";
      the section title is in the footnote (pages.printed, shown by the location string).
  fda_label_version (getFile.cfm zip URL, not browsable): the DailyMed history page for the setid.
  transcript: third-party page (fool.com, marketbeat, ...) with no anchors: plain page; the footnote shows speaker + quote.
  license == bloomberg_licensed, or no http source_url (LSEG Grade A PDFs under verified/calls/src/, R2 keys, local
      files): NO deep link, viewer route only. Licensed text must never leave the team (see render's public flag).
  anything else: plain source_url.
The viewer link <VIEWER_BASE>/viewer?doc=<canonical_id>&page=<n>&q=<quote> is always produced. VIEWER_BASE comes from
env VIEWER_BASE (default http://127.0.0.1:8765, the port of `python -m agent.needle.cite.viewer_server`), so the
footnote link is absolute and clickable from a .md file; set VIEWER_BASE="" for the old relative "/viewer?..." form.

Validation is against the converted page text, not the live EDGAR HTML: a run that survives inside one block of the
markdown is very likely inside one DOM block, but the viewer link stays the guaranteed route.
"""

import os
import re
from urllib.parse import parse_qs, quote as _q, urlencode, urlsplit

from .numbers import strip_zw

HEAD_WORDS = 8
MIN_RUN_WORDS = 4
LICENSED = ("bloomberg_licensed",)
DEFAULT_VIEWER_BASE = "http://127.0.0.1:8765"


def _enc(s):
    return _q(s, safe="").replace("-", "%2D")


def _words(quote):
    return strip_zw(quote).split()


def text_fragment(quote, head=HEAD_WORDS):
    """'#:~:text=<first ~8 words>' or '' when there is no quote. Unvalidated: use fragment_for_page for links."""
    w = _words(quote)
    return "#:~:text=" + _enc(" ".join(w[:head])) if w else ""


_ADJ_NUMS = re.compile(r"\d[\d,.]*\)?%?\s+[($]*\$?\s?[-\u2212]?\d")     # two numeric cells side by side
_NUMCELL = re.compile(r"(?:^|\s)[($]*\s?[-\u2212+]?\$?\s?\d[\d,.]*\)?%?(?=\s|$)")


def _blocks(page_text):
    """Text blocks a browser matches a fragment inside. A line is a block, split at markdown table pipes. A line that
    reads like a flattened table row (two numeric cells side by side; the converter drops the cell borders) is split at
    every numeric cell too, so a run can only come from one label cell (review verify2: 9 of 15 table-row fragments
    crossed td cells and failed in the browser)."""
    out = []
    for line in strip_zw(page_text).splitlines():
        for cell in line.split("|"):
            b = " ".join(cell.split())
            if not b:
                continue
            if _ADJ_NUMS.search(b):
                out += [p.strip() for p in _NUMCELL.split(b) if p and p.strip()]
            else:
                out.append(b)
    return out


def _wordy(w):
    return any(ch.isalnum() for ch in w)


def fragment_run(quote, page_text, head=HEAD_WORDS, min_words=MIN_RUN_WORDS):
    """The longest run (head down to min_words words) of consecutive quote words that appears inside one block of
    page_text, earliest first, or ''. Runs never start or end on a word with no letter or digit (bullets, '$', '-')."""
    w = _words(quote)
    blocks = _blocks(page_text)
    if not w or not blocks:
        return ""
    for k in range(min(head, len(w)), min_words - 1, -1):
        for i in range(0, len(w) - k + 1):
            run = w[i:i + k]
            if not (_wordy(run[0]) and _wordy(run[-1])):
                continue
            s = " ".join(run)
            if any(s in b for b in blocks):
                return s
    return ""


def fragment_for_page(quote, page_text):
    """('#:~:text=...', '') when a validated run exists, else ('', reason)."""
    if not (quote or "").strip():
        return "", ""
    if not (page_text or "").strip():
        return "", "no page text to validate a text fragment; plain URL"
    run = fragment_run(quote, page_text)
    if not run:
        return "", "no run of 4+ quote words sits inside one block of the page text; text fragment dropped, plain URL"
    return "#:~:text=" + _enc(run), ""


def source_kind(url):
    u = urlsplit((url or "").lower())
    if u.path.endswith(".pdf"):
        return "pdf"
    if "dailymed.nlm.nih.gov" in u.netloc:
        return "dailymed"
    if u.netloc.endswith("sec.gov") and u.path.endswith((".htm", ".html")):
        return "edgar"
    return "other"


def dailymed_history_url(source_url):
    q = parse_qs(urlsplit(source_url).query)
    return f"https://dailymed.nlm.nih.gov/dailymed/history.cfm?setid={q['setid'][0]}" if "setid" in q else source_url


PDF_PAGE_SCHEMES = ("pdf_page", "marker", "")     # "" = a Citation built by hand, scheme not set


def build_deep_link_with_note(citation, page_text=""):
    """(public deep link or '' (viewer only), note). page_text is the stored page the quote was verified on; EDGAR
    text fragments are built only from a run found in it."""
    url = citation.source_url or ""
    if citation.license in LICENSED or not url.startswith("http"):
        return "", ""
    base, kind, raw = url.split("#")[0], source_kind(url), citation.raw_doc_type
    if raw == "fda_label_version":
        return dailymed_history_url(base), ""
    if raw == "fda_label" or kind == "dailymed":
        return base, ""
    if kind == "pdf" or citation.page_scheme == "pdf_page":
        if not citation.page:
            return base, ""
        if citation.page_scheme not in PDF_PAGE_SCHEMES:
            return base, f"no PDF page in the index (page_scheme {citation.page_scheme}); plain URL"
        return f"{base}#page={citation.page}", ""
    if kind == "edgar":
        q = citation.quote
        cs, ce = citation.char_start, citation.char_end
        if page_text and cs is not None and ce and ce <= len(page_text):
            q = page_text[cs:ce]                          # the verified span, verbatim from the page
        frag, note = fragment_for_page(q, page_text)
        return base + frag, note
    return base, ""


def build_deep_link(citation, page_text=""):
    """Public deep link or '' (viewer only). See build_deep_link_with_note."""
    return build_deep_link_with_note(citation, page_text)[0]


def fact_link(source, source_row=""):
    """Link for a facts-table row: cms.gov / data.medicaid.gov / any http source directly; R2 keys and WRDS-style ids
    (no http) have no public link and use the local route."""
    return source if (source or "").startswith("http") else ""


def viewer_base():
    return os.environ.get("VIEWER_BASE", DEFAULT_VIEWER_BASE).rstrip("/")


def build_viewer_link(citation, base=None):
    q = urlencode({"doc": citation.canonical_id, "page": citation.page or 1, "q": " ".join((citation.quote or "").split())[:400]})
    return f"{viewer_base() if base is None else base.rstrip('/')}/viewer?" + q.replace("+", "%20")
