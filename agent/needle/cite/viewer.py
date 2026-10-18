"""Local viewer: the page text with the quote wrapped in <mark>.

Streamlit usage (the UI agent owns styling; this is only the call shape). With the viewer_link
'/viewer?doc=..&page=..&q=..' the app reads st.query_params and renders:

    import streamlit as st
    from agent.needle.cite.viewer import render_viewer
    qp = st.query_params
    if qp.get("doc"):
        html_out = render_viewer(qp["doc"], int(qp.get("page", 1)), qp.get("q", ""))
        st.markdown(html_out, unsafe_allow_html=True)

Streamlit has no path routing, so serve it as a query-param page: '?doc=...&page=...&q=...'. The link builder emits
'<VIEWER_BASE>/viewer?...' (default http://127.0.0.1:8765), which agent.needle.cite.viewer_server serves with the
standard library; the UI can mount viewer_server.viewer_response instead.
"""

import html
import re

from .index import load_index

ZW = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")


def _span(text, quote):
    words = [w for w in ZW.sub("", quote or "").split() if w]
    for k in (len(words), min(len(words), 12), min(len(words), 6)):
        if k == 0:
            break
        pat = r"\s+".join(re.escape(w) for w in words[:k])
        m = re.search(pat, text, flags=re.I)
        if m:
            if k < len(words):
                tail = r"\s+".join(re.escape(w) for w in words[-4:])
                m2 = re.search(pat + r".{0,%d}?" % (len(quote) * 2) + tail, text, flags=re.I | re.S)
                if m2:
                    return m2.span()
            return m.span()
    return None


def render_viewer(doc, page, q="", db_path=None, public=False):
    """HTML string: header line plus the escaped page text with the quote in <mark>. Unknown doc/page -> message."""
    idx = load_index(db_path)
    got = idx.get_page(doc, page)
    if got is None:
        return f'<div class="srcpage">Source text unavailable: {html.escape(str(doc))} page {html.escape(str(page))}</div>'
    n, folio, text = got
    rec = idx.resolve(doc)
    if public and rec.license:
        return '<div class="srcpage">Licensed source: team only.</div>'
    head = f"{html.escape(rec.doc_title)}, {html.escape(idx.location(doc, n))} (file page {n})"
    span = _span(text, q) if q else None
    if span:
        s, e = span
        body = html.escape(text[:s]) + "<mark>" + html.escape(text[s:e]) + "</mark>" + html.escape(text[e:])
    else:
        body = html.escape(text)
    return f'<div class="srcpage"><p><b>{head}</b></p><pre style="white-space:pre-wrap">{body}</pre></div>'
