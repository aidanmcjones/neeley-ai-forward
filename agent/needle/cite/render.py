"""Render claims with in-text markers and a Sources list.

render_markdown(claims) / render_html(claims) take list[Claim] (see locator.Claim). Each claim's text gets a marker
per citation ([n], or <sup><a href="#fn-n">[n]</a></sup>), numbered in order of first appearance. Identical
citations (same canonical_id, page, quote) share one footnote number.

Footnote line (markdown):
  [n] <doc_title>, p. <folio> (file page <page>) -- "<quote>" -- [open](deep_link) · [viewer](viewer_link) · verified: <status>
The page text comes from agent.moat.cite.where() (via Citation.location): "p. 58", "Item 1A", "section <title>", "PDF p. 3", or "file page N (no printed page number)"; "(file page N)" is appended when absent.
public=True withholds quote text and the viewer link of licensed (Bloomberg) citations.
"""

import html


def _number(claims):
    """(per-claim marker lists, ordered unique citations)."""
    seen, order, marks = {}, [], []
    for cl in claims:
        row = []
        for c in cl.citations:
            key = (c.canonical_id, c.page, " ".join((c.quote or "").split()).lower())
            if key not in seen:
                seen[key] = len(order) + 1
                order.append(c)
            row.append(seen[key])
        marks.append(sorted(set(row)))
    return marks, order


def _where(c):
    loc = c.location or (f"p. {c.folio}" if c.folio not in ("", "?") else "")
    if not loc:
        return f"file page {c.page}"
    return loc if "file page" in loc else f"{loc} (file page {c.page})"


def _quote(c, public):
    if public and c.license:
        return "[licensed text withheld]"
    q = " ".join((c.quote or "").split()).replace('"', "'")
    return f"{c.speaker}: {q}" if c.speaker else q


def _md_url(u):
    return u.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def render_markdown(claims, public=False):
    marks, cites = _number(claims)
    body = " ".join((cl.text.rstrip() + "".join(f"[{n}]" for n in m)) for cl, m in zip(claims, marks))
    if not cites:
        return body
    lines = ["", "**Sources**", ""]
    for n, c in enumerate(cites, 1):
        links = []
        if c.deep_link:
            links.append(f"[open]({_md_url(c.deep_link)})")
        if c.viewer_link and not (public and c.license):
            links.append(f"[viewer]({_md_url(c.viewer_link)})")
        tail = " · ".join(links + [f"verified: {c.verification.status}"])
        lines.append(f'[{n}] {c.doc_title}, {_where(c)} -- "{_quote(c, public)}" -- {tail}')
        lines.append("")
    return body + "\n" + "\n".join(lines).rstrip() + "\n"


def render_html(claims, public=False):
    marks, cites = _number(claims)
    esc = html.escape
    parts = []
    for cl, m in zip(claims, marks):
        sup = "".join(f'<sup><a href="#fn-{n}">[{n}]</a></sup>' for n in m)
        parts.append(esc(cl.text.rstrip()) + sup)
    out = ['<p>' + " ".join(parts) + '</p>']
    if cites:
        out.append('<ol class="sources">')
        for n, c in enumerate(cites, 1):
            links = []
            if c.deep_link:
                links.append(f'<a href="{esc(c.deep_link, quote=True)}">open</a>')
            if c.viewer_link and not (public and c.license):
                links.append(f'<a href="{esc(c.viewer_link, quote=True)}">viewer</a>')
            tail = " &middot; ".join(links + [f"verified: {esc(c.verification.status)}"])
            out.append(f'<li id="fn-{n}">[{n}] {esc(c.doc_title)}, {esc(_where(c))} -- '
                       f'&ldquo;{esc(_quote(c, public))}&rdquo; -- {tail}</li>')
        out.append("</ol>")
    return "\n".join(out)
