"""Render claims with per-number in-text markers and a Sources list.

render_markdown(claims, public=False, index=None) / render_html(claims, public=False, index=None) take list[Claim]
(see locator.Claim; optional .derived and .assumptions maps, as in agent.needle.cite.gate). Markers (review D2, D15,
C18) follow agent.needle.cite.gate.numeric_gate's per-number classification of the claim text:
  * each number gets its own marker right after it (after its unit or scale word): "$29,482 million[1]", "18%[2]";
  * when every number in the claim is carried by one shared citation, a single [n] goes after the clause instead;
  * a derived number gets "[derived: a, b]" (a, b = footnotes of its operand citations; "assumption" for an assumed
    operand), an assumed number gets "[assumption]";
  * citations not used by any number (context quotes) and claims with no numbers keep their markers at the end;
  * an unsupported number gets no marker: the gate must stop it before rendering.
Numbering is by first appearance; identical citations (same canonical_id, page, quote) share one footnote number.

Footnote line (markdown):
  [n] <doc_title>, <location> (file page <page>) -- "<quote>" -- [open](deep_link) · [viewer](viewer_link) · verified: <status>
The location is agent.moat.cite.where() (via Citation.location): "p. 58", "Item 1A", "section <title>", "PDF p. 3",
"file page N (no printed page number)". "(file page N)" is appended only when the page is known; a citation with no
page (facts rows, XBRL, derived) prints its location alone, never "file page None". Quotes are verbatim: double
quotes inside the quote are kept (markdown) or escaped (HTML).
public=True (every entry point takes it) withholds the quote text and the viewer link of licensed citations.
"""

import html
import re

from . import gate as _gate

# Square brackets are reserved for markers: [n], [derived], [derived: ...], [assumption], [constant: NAME]. Any other
# bracketed text in a claim (a label such as "[biologic; LOE 2031-01-01]") would read as a citation marker, so it is
# rendered in parentheses. The swap keeps string length, so the gate's number offsets stay valid.
MARKER_RE = re.compile(r"\[(?:\d+|derived(?:: [^\[\]]*)?|assumption|constant: [^\[\]]+)\]")
_BRACKET_RE = re.compile(r"\[([^\[\]]*)\]")


def is_marker(s):
    return bool(MARKER_RE.fullmatch(s))


def unbracket(text):
    """Non-marker [x] -> (x), same length; marker forms are left alone."""
    return _BRACKET_RE.sub(lambda m: m.group(0) if is_marker(m.group(0)) else f"({m.group(1)})", text)

_SEP = " "


def _key(c):
    return (c.canonical_id, c.page, " ".join((c.quote or "").split()).lower())


def _operand_cites(cl):
    out = []
    for e in (getattr(cl, "derived", None) or {}).values():
        if not isinstance(e, dict):
            continue
        for o in (e.get("operands") or {}).values():
            c = _gate.as_citation(o) or (_gate.as_citation(o.get("citation")) if isinstance(o, dict) else None)
            if c is not None:
                out.append(c)
    return out


def _number(claims):
    """(per-claim marker lists, ordered unique citations). Operand citations of derived numbers are numbered too."""
    seen, order, marks = {}, [], []
    for cl in claims:
        row = []
        for c in list(cl.citations) + _operand_cites(cl):
            k = _key(c)
            if k not in seen:
                seen[k] = len(order) + 1
                order.append(c)
            row.append(seen[k])
        marks.append(sorted(set(row)))
    return marks, order


def _plan(cl, num_of, index=None):
    """(inserts [(pos, [('cite', n) | ('derived', [labels]) | ('assumption',)])], end markers [n])."""
    by_id = {}
    for c in list(cl.citations) + _operand_cites(cl):
        by_id.setdefault(c.cite_id, num_of[_key(c)])
    own = sorted({num_of[_key(c)] for c in cl.citations})
    text = cl.text.rstrip()
    try:
        res = _gate.numeric_gate([(getattr(cl, "where", None) or "claim", text)], cl.citations, getattr(cl, "derived", None),
                                 getattr(cl, "assumptions", None), index=index)
        nums = res.numbers
    except Exception:
        nums = []
    dmode = getattr(cl, "dates", "")
    if dmode:                                 # dates in a fact cell are claims too (gate.date_check)
        try:
            nums = list(nums) + _gate.date_check("claim", text, cl.citations, getattr(cl, "assumptions", None),
                                                 years=dmode == "all")["numbers"]
        except Exception:
            pass
    if not nums:
        return [], own
    for r in nums:                            # prefer citations whose quote or value carries the number over page text
        if r["kind"] == "verified":
            direct = [i for i, b in zip(r["cites"], r.get("basis", [])) if b in ("quote", "value")]
            r["cites"] = direct or r["cites"]
    used, inserts = set(), []
    cite_sets = [sorted({by_id[i] for i in r["cites"] if i in by_id}) for r in nums if r["kind"] == "verified"]
    shared = set(cite_sets[0]).intersection(*map(set, cite_sets[1:])) if cite_sets else set()
    if shared and len(cite_sets) == len(nums):
        one = min(shared)
        return [], sorted({one} | (set(own) - {n for s in cite_sets for n in s}))
    for r in nums:
        if r["kind"] == "verified":
            ns = sorted({by_id[i] for i in r["cites"] if i in by_id})
            used |= set(ns)
            inserts.append((r["end"], [("cite", n) for n in ns]))
        elif r["kind"] == "derived":
            labels = []
            for ref in r.get("operands", []):
                if ref in by_id:
                    labels.append(str(by_id[ref]))
                    used.add(by_id[ref])
                elif str(ref).startswith("assumption:"):
                    labels.append("assumption")
            labels = list(dict.fromkeys(labels))
            inserts.append((r["end"], [("derived", labels)]))
        elif r["kind"] == "assumed":
            if r.get("label") == "arithmetic constant":
                continue                      # documented rule: bare 0, 1, 100 in a formula carry no marker
            inserts.append((r["end"], [("assumption", r.get("label") or "")]))
    return inserts, sorted(set(own) - used)


def _apply(text, inserts, fmt):
    out = text
    for pos, ms in sorted(inserts, key=lambda x: -x[0]):
        out = out[:pos] + "".join(fmt(m) for m in ms) + out[pos:]
    return out


CONSTANT = "constant: "


def _assumption_tag(label):
    """'[constant: <name>]' for a model constant (gatewire label 'constant: <name> (...)'), else 'assumption'."""
    label = str(label or "")
    if label.startswith(CONSTANT):
        return "constant: " + label[len(CONSTANT):].split(" (")[0].strip()
    return "assumption"


def _md_mark(m):
    if m[0] == "cite":
        return f"[{m[1]}]"
    if m[0] == "derived":
        return f"[derived: {', '.join(m[1])}]" if m[1] else "[derived]"
    return f"[{_assumption_tag(m[1] if len(m) > 1 else '')}]"


def _html_mark(m):
    if m[0] == "cite":
        return f'<sup><a href="#fn-{m[1]}">[{m[1]}]</a></sup>'
    if m[0] == "derived":
        refs = ", ".join(f'<a href="#fn-{x}">{x}</a>' if x.isdigit() else x for x in m[1])
        return f"<sup>[derived{': ' + refs if refs else ''}]</sup>"
    return f"<sup>[{html.escape(_assumption_tag(m[1] if len(m) > 1 else ''))}]</sup>"


def claim_markup(claims, fmt="md", index=None):
    """(list of marked-up claim texts, ordered unique citations)."""
    _, order = _number(claims)
    num_of = {_key(c): i for i, c in enumerate(order, 1)}
    out = []
    for cl in claims:
        inserts, end = _plan(cl, num_of, index)
        text = unbracket(cl.text.rstrip())
        if fmt == "html":                     # escape segment by segment so the offsets stay valid
            pieces, last = [], 0
            for pos, ms in sorted(inserts, key=lambda x: x[0]):
                pieces.append(html.escape(text[last:pos]) + "".join(_html_mark(m) for m in ms))
                last = pos
            body = "".join(pieces) + html.escape(text[last:])
            out.append(body + "".join(_html_mark(("cite", n)) for n in end))
        else:
            out.append(_apply(text, inserts, _md_mark) + "".join(f"[{n}]" for n in end))
    return out, order


def _where(c):
    loc = c.location or (f"p. {c.folio}" if c.folio not in ("", "?", None) else "")
    if c.page is None:
        return loc
    if not loc:
        return f"file page {c.page}"
    return loc if "file page" in loc else f"{loc} (file page {c.page})"


def _quote(c, public):
    if public and c.license:
        return "(licensed text withheld)"
    q = " ".join((c.quote or "").split())
    return f"{c.speaker}: {q}" if c.speaker else q


def _md_url(u):
    return u.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def _status(c):
    v = c.verification
    return getattr(v, "status", None) or (v.get("status") if isinstance(v, dict) else "") or "unverified"


def render_footnotes_md(cites, public=False):
    lines = ["", "**Sources**", ""]
    for n, c in enumerate(cites, 1):
        links = []
        if c.deep_link:
            links.append(f"[open]({_md_url(c.deep_link)})")
        if c.viewer_link and not (public and c.license):
            links.append(f"[viewer]({_md_url(c.viewer_link)})")
        tail = " · ".join(links + [f"verified: {_status(c)}"])
        where = _where(c)
        head = f"{c.doc_title}, {where}" if where else f"{c.doc_title}"
        lines.append(f'[{n}] {head} -- "{_quote(c, public)}" -- {tail}')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(claims, public=False, index=None):
    texts, cites = claim_markup(claims, "md", index)
    body = _SEP.join(texts)
    if not cites:
        return body
    return body + "\n" + render_footnotes_md(cites, public)


def render_html(claims, public=False, index=None):
    texts, cites = claim_markup(claims, "html", index)
    esc = html.escape
    out = ['<p>' + _SEP.join(texts) + '</p>']
    if cites:
        out.append('<ol class="sources">')
        for n, c in enumerate(cites, 1):
            links = []
            if c.deep_link:
                links.append(f'<a href="{esc(c.deep_link, quote=True)}">open</a>')
            if c.viewer_link and not (public and c.license):
                links.append(f'<a href="{esc(c.viewer_link, quote=True)}">viewer</a>')
            tail = " &middot; ".join(links + [f"verified: {esc(_status(c))}"])
            where = _where(c)
            head = esc(c.doc_title) + (f", {esc(where)}" if where else "")
            out.append(f'<li id="fn-{n}">[{n}] {head} -- &ldquo;{esc(_quote(c, public))}&rdquo; -- {tail}</li>')
        out.append("</ol>")
    return "\n".join(out)
