"""Marker grammar of rendered records: square brackets are reserved for [n], [derived: ...], [assumption] and
[constant: NAME]; every [n] resolves to a footnote of the same record whose quote matches one of the record's
exported citations (the UI's marker_map rule, ui_export.marker_map)."""

import json
import re
from pathlib import Path

import pytest

from agent.needle.cite import render
from agent.needle.cite.locator import Citation, Claim

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[(open|viewer)\]\([^)]*\)")


def lookalikes(text):
    """Bracketed tokens in a rendered body (footnote list and markdown links removed) that are not marker forms."""
    body = LINK.sub("", (text or "").partition("**Sources**")[0])
    return [m.group(0) for m in re.finditer(r"\[[^\[\]]*\]", body) if not render.is_marker(m.group(0))]


def footnotes(md):
    out = {}
    for line in (md or "").partition("**Sources**")[2].splitlines():
        m = re.match(r"^\[(\d+)\] (.*)$", line.strip())
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def markers(text):
    body = LINK.sub("", (text or "").partition("**Sources**")[0])
    ns = [int(x) for x in re.findall(r"\[(\d+)\]", body)]
    ns += [int(y) for m in re.findall(r"\[derived: ([^\]]*)\]", body) for y in m.split(", ") if y.isdigit()]
    return ns


def unresolved(rec):
    """[n] markers in sentence_md / formula_md with no footnote, or whose footnote matches no exported citation of
    the record by doc_title, location and (whitespace-exact) quote."""
    notes = footnotes(rec.get("sentence_md"))
    cits = rec.get("citations") or []
    bad = []
    for n in markers(rec.get("sentence_md")) + markers(rec.get("formula_md")):
        line = notes.get(n)
        if line is None:
            bad.append(n)
            continue
        head = line.split(" -- ")[0]
        qm = re.search(r' -- "(.*)" -- ', line + " -- ")
        cand = [c for c in cits if head.startswith(f"{c.get('doc_title')}, {c.get('location')}")]
        q = qm.group(1) if qm else None
        if not (any(q is not None and (c.get("quote") or "") == q for c in cand) or len(cand) == 1
                or (cand and q is None)):
            bad.append(n)
    return bad


def test_unresolved_catches_a_quote_the_footnote_reflowed():
    """The BMY Orencia / PFE Xeljanz case: a cited quote stored with newlines prints whitespace-collapsed in the
    footnote, so among several citations on the same page the UI could not match it and showed [3] unresolved twice."""
    def cit(q):
        return {"doc_title": "CMS fact sheet", "location": "p. 2", "quote": q}
    md = ('d 0.65[derived: 1] x 0.66[1]\n\n**Sources**\n\n[1] CMS fact sheet, p. 2 (file page 2) -- '
          '"Psoriatic arthritis $1,650 $4,722 65%" -- verified: exact\n')
    rec = {"sentence_md": md, "citations": [cit("Psoriatic \narthritis\n$1,650 $4,722 65%"), cit("$4,695.00 66%")]}
    assert unresolved(rec) == [1, 1]
    rec["citations"][0]["quote"] = "Psoriatic arthritis $1,650 $4,722 65%"
    assert unresolved(rec) == []


def test_non_marker_brackets_render_in_parentheses():
    c = Citation("AAA:10k_FY2025.md", 3, "Enbrel US sales 2,199", doc_title="AAA 10-K", location="p. 3")
    c.verification.status = "exact"
    md = render.render_markdown([Claim("Rev_pre 2,199.0 x 0.65 [biologic; LOE 2031-01-01]", [c])])
    assert "(biologic; LOE 2031-01-01)" in md and "[biologic" not in md
    assert not lookalikes(md)
    assert render.unbracket("a [1] b [x; y] [derived: 1, 2] [constant: K_NET] [assumption]") == \
        "a [1] b (x; y) [derived: 1, 2] [constant: K_NET] [assumption]"


def test_loe_formula_label_is_not_bracketed():
    from datetime import date
    from agent.needle.quant import data, impact
    try:
        co = data.company("AMGN")
    except Exception:
        pytest.skip("company data not available")
    imp = impact.loe(co, "Enbrel", 2199.0, date(2028, 11, 22), True)
    assert "(biologic; LOE 2028-11-22)" in imp.formula and "[" not in imp.formula


@pytest.mark.parametrize("t", ["AMGN", "MRK", "BMY", "PFE"])
def test_rendered_records_use_only_marker_brackets_and_every_marker_resolves(t):
    f = ROOT / "out" / t / "findings_v3.jsonl"
    if not f.exists():
        pytest.skip("out/<T>/findings_v3.jsonl not generated (gitignored)")
    for line in f.read_text().splitlines():
        rec = json.loads(line)
        for fld in ("sentence_md", "formula_md"):
            assert not lookalikes(rec.get(fld)), (rec["id"], fld, lookalikes(rec.get(fld)))
        assert not unresolved(rec), (rec["id"], unresolved(rec))
