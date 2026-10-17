"""Deep links: a clickable URL for (document, page, quote). Rules follow the scraper's index contract
(agent/moat, commit 704741d) and branch on source_url, raw doc_type, page_scheme and license.

  SEC filings (annual/quarterly report, 8-K, 6-K, earnings release, EDGAR press release): source_url is the EDGAR
      primary .htm. No page anchors exist, so url + "#:~:text=" + first 8 words of the quote, percent-encoded
      (WICG text fragment: every term encodes '-', ',' and '&'). Chrome and Edge honor it; Safari lands at the top.
      No quote -> plain URL.
  sec_comment_letter: .htm -> text fragment; .pdf -> "#page=N" (page_no is the PDF page).
  any other .pdf (CMS, White House, Federal Register fact sheets, IR PDFs): url + "#page=N".
  fda_label: the DailyMed setid page, plain. Section anchors are not stable across label versions, so no "#section-N";
      the section title is in the footnote (pages.printed, shown by the location string).
  fda_label_version (getFile.cfm zip URL, not browsable): the DailyMed history page for the setid.
  transcript: third-party page (fool.com, marketbeat, ...) with no anchors: plain page; the footnote shows speaker + quote.
  license == bloomberg_licensed, or no http source_url (LSEG Grade A PDFs under verified/calls/src/, R2 keys, local
      files): NO deep link, viewer route only. Licensed text must never leave the team (see render's public flag).
  anything else: plain source_url.
The viewer link /viewer?doc=<canonical_id>&page=<n>&q=<quote> is always produced.

Text fragments cannot be validated server side: the browser matches them and silently skips the highlight on a
miss (SEC HTML tables may differ from the converted markdown). The viewer link is the reliable route.
"""

import re
from urllib.parse import parse_qs, quote as _q, urlencode, urlsplit

HEAD_WORDS = 8
LICENSED = ("bloomberg_licensed",)


def _enc(s):
    return _q(s, safe="").replace("-", "%2D")


def _words(quote):
    return re.sub(r"[​­]", "", quote or "").split()


def text_fragment(quote, head=HEAD_WORDS):
    """'#:~:text=<first ~8 words>' or '' when there is no quote."""
    w = _words(quote)
    return "#:~:text=" + _enc(" ".join(w[:head])) if w else ""


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


def build_deep_link(citation, page_text=""):
    """Public deep link or '' (viewer only). page_text is accepted for API stability and unused."""
    url = citation.source_url or ""
    if citation.license in LICENSED or not url.startswith("http"):
        return ""
    base, kind, raw = url.split("#")[0], source_kind(url), citation.raw_doc_type
    if raw == "fda_label_version":
        return dailymed_history_url(base)
    if raw == "fda_label" or kind == "dailymed":
        return base
    if kind == "pdf" or citation.page_scheme == "pdf_page":
        return f"{base}#page={citation.page}" if citation.page else base
    if kind == "edgar":
        return base + text_fragment(citation.quote)
    return base


def fact_link(source, source_row=""):
    """Link for a facts-table row: cms.gov / data.medicaid.gov / any http source directly; R2 keys and WRDS-style ids
    (no http) have no public link and use the local route."""
    return source if (source or "").startswith("http") else ""


def build_viewer_link(citation):
    q = urlencode({"doc": citation.canonical_id, "page": citation.page or 1, "q": " ".join((citation.quote or "").split())[:400]})
    return "/viewer?" + q.replace("+", "%20")
