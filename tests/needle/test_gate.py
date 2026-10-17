"""Per-number citation gate (agent/needle/cite/gate.py): review C6, C1-C3/C5 mechanism, D2. Offline, synthetic index."""

import sqlite3

import pytest

from agent.moat import cite as moat
from agent.needle.cite import gate as G, verify as V
from agent.needle.cite.index import load_index
from agent.needle.cite.locator import Citation, Claim
from tests.needle.test_cite import ADV_DOC, ADV_P2, EDGAR, SCHEMA, _doc

KEYS = {"status", "checked", "total", "verified", "derived", "assumed", "unsupported"}
DOC = "AAA:10k_FY2025.md"


@pytest.fixture(scope="module", autouse=True)
def _restore_moat_db():
    old = moat.DB
    yield
    moat.DB = old
    moat.db.cache_clear()


@pytest.fixture(scope="module")
def idx(tmp_path_factory):
    f = tmp_path_factory.mktemp("gate") / "citations.sqlite"
    con = sqlite3.connect(f)
    con.executescript(SCHEMA)
    _doc(con, DOC, "annual_report", EDGAR, "data/corpus/companies/AAA/10k_FY2025.md", ADV_DOC, "10-K", "2025-12-31", "2026-02-20")
    con.commit()
    con.close()
    return load_index(f)


@pytest.fixture(scope="module")
def good(idx):
    return V.verify(Citation(DOC, 2, ADV_P2[:90]), idx)          # exact: "... $29,482 million in 2025, an increase of 18 percent ..."


@pytest.fixture(scope="module")
def full_year(idx):
    return V.verify(Citation(DOC, 2, "$64,168 million for the full year."), idx)


@pytest.fixture(scope="module")
def bad(idx):
    return V.verify(Citation(DOC, 2, "Invented sentence about revenue doubling to 99 billion dollars this year."), idx)


def _shape(chk):
    assert set(chk) == KEYS and chk["status"] in ("passed", "no_numbers", "failed", "unchecked")
    assert chk["verified"] + chk["derived"] + chk["assumed"] + len(chk["unsupported"]) == chk["total"]
    for u in chk["unsupported"]:
        assert set(u) == {"value", "where", "reason"} and u["reason"]
    assert (chk["status"] in G.OK_STATUSES) == (not chk["unsupported"] and chk["status"] != "unchecked")
    assert (chk["status"] == "no_numbers") == (chk["status"] != "unchecked" and chk["total"] == 0 and not chk["unsupported"])


def test_g1_one_verified_citation_no_longer_clears_invented_numbers(idx, good, bad):
    text = "Keytruda sales were $29,482 million; revenue will double to $99 billion; margin 95%; 4,000 layoffs."
    r = G.numeric_gate(text, [Claim(text, [good, bad, bad])], index=idx)
    chk = r.numeric_check
    _shape(chk)
    assert chk["status"] == "failed" and not r.passed
    assert chk["total"] == 4 and chk["verified"] == 1
    assert [u["value"] for u in chk["unsupported"]] == ["$99 billion", "95%", "4,000"]
    assert V.gate([Claim(text, [good, bad])])[0]                 # the old per-claim gate still lets it through


def test_g2_fabricated_quote_number_match_does_not_cover_other_units(idx):
    nm = V.verify(Citation(DOC, 3, "Totally fabricated quote that is not on any page at all", claim_type="number",
                           value="18", unit="percent"), idx)
    assert nm.verification.status == "number_match" and "18 percent" in nm.quote     # footnote shows the page text
    assert not G.numeric_gate("Margin rose 18 points.", [nm], index=idx).passed      # pts is not percent
    assert G.numeric_gate("Sales rose 18%.", [nm], index=idx).passed


def test_unverified_citation_supports_nothing(idx, bad):
    c = Citation(DOC, 2, "Keytruda sales were $31,000 million overall", claim_type="quote")
    c = V.verify(c, idx)
    assert c.verification.status == "unverified"
    r = G.numeric_gate("Keytruda sales were $31,000 million.", [c], index=idx)
    assert r.numeric_check["unsupported"][0]["value"] == "$31,000 million"


def test_scale_and_sign_and_rounding(idx, good):
    t4 = V.verify(Citation(DOC, 4, "Revenue 15,144 12,000 Inventory 183", claim_type="quote"), idx)
    assert t4.verification.ok
    assert G.numeric_gate("Revenue was $15.144 billion.", [t4], index=idx).passed      # "(in millions)" header
    assert G.numeric_gate("Revenue was 15,144.", [t4], index=idx).passed               # restates the cell
    bad_scale = G.numeric_gate("Revenue was $15,144 thousand.", [t4], index=idx)
    assert not bad_scale.passed
    other = V.verify(Citation(DOC, 2, "Other income was ($183) million lower."), idx)
    r = G.numeric_gate("Other income was $183 million higher.", [other], index=idx)
    assert not r.passed and "sign differs" in r.numeric_check["unsupported"][0]["reason"]
    assert G.numeric_gate("Other income fell by ($183) million.", [other], index=idx).passed
    assert G.numeric_gate("Keytruda sold about $29.5 billion.", [good], index=idx).passed  # rounds 29,482 million
    assert not G.numeric_gate("Keytruda sold $29.6 billion.", [good], index=idx).passed


def test_years_dates_and_ids_are_not_counted(idx, good):
    r = G.numeric_gate("In 2025 (10-K p. 41, Item 7, Q4 2025, filed 2026-02-20) Keytruda sales were $29,482 million.[1]",
                       [good], index=idx)
    assert r.passed and r.numeric_check["total"] == 1


def test_derived_recomputes_from_verified_operands(idx, good, full_year, bad):
    a = Citation.from_dict({**good.to_dict(), "value": "29,482", "unit": "USD millions"})
    der = {"share": G.derived_entry(45.9, "a / b * 100", {"a": a, "b": (64168, full_year)}, unit="%")}
    r = G.numeric_gate("Keytruda was 45.9% of revenue.", [], derived=der, index=idx)
    assert r.passed and r.numeric_check["derived"] == 1
    assert set(r.numbers[0]["operands"]) == {good.cite_id, full_year.cite_id}
    wrong = {"share": G.derived_entry(46.9, "a / b * 100", {"a": a, "b": (64168, full_year)}, unit="%")}
    w = G.numeric_gate("Keytruda was 46.9% of revenue.", [], derived=wrong, index=idx)
    assert not w.passed and "re-computes to" in w.numeric_check["unsupported"][0]["reason"]
    unv = {"share": G.derived_entry(45.9, "a / b * 100", {"a": a, "b": (64168, bad)}, unit="%")}
    u = G.numeric_gate("Keytruda was 45.9% of revenue.", [], derived=unv, index=idx)
    assert not u.passed and "did not pass verification" in u.numeric_check["unsupported"][0]["reason"]
    off = {"share": G.derived_entry(45.9, "a / b * 100", {"a": a, "b": (64000, full_year)}, unit="%")}
    assert not G.numeric_gate("Keytruda was 45.9% of revenue.", [], derived=off, index=idx).passed  # 64,000 not cited


def test_assumptions_and_formula_constants(idx, good):
    ass = {"0.65%": "Pfizer MFN base rate (weights constant)", "0.15": "tax rate t (assumed)"}
    assert G.numeric_gate("at the base rate of 0.65% of US revenue", [], assumptions=ass, index=idx).passed
    assert not G.numeric_gate("at the base rate of 0.65% of US revenue", [], assumptions={"0.65%": ""}, index=idx).passed
    f = "0.65% x Rev 29,482 x (1 - t 0.15) / 100"
    ok = G.numeric_gate([("impact.formula", f)], [good], assumptions=ass, index=idx)
    assert ok.passed and ok.numeric_check["assumed"] == 4 and ok.numeric_check["verified"] == 1
    assert not G.numeric_gate([("sentence", f)], [good], assumptions=ass, index=idx).passed   # 1 and 100 need a source


def test_fail_closed_on_errors(idx, good, monkeypatch):
    monkeypatch.setattr(G, "same_number", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = G.numeric_gate("Keytruda sales were $29,482 million.", [good], index=idx)
    assert not r.passed and r.numeric_check["unsupported"][0]["reason"].startswith("gate error")
    assert r.numeric_check["checked"] == 0 and r.numeric_check["total"] == 1
    monkeypatch.undo()
    monkeypatch.setattr(G, "tokenize", lambda *a, **k: 1 / 0)
    r2 = G.numeric_gate("Keytruda sales were $29,482 million.", [good], index=idx)
    assert r2.numeric_check["status"] == "failed" and "gate error" in r2.numeric_check["unsupported"][0]["reason"]


def test_gate_record_findings_shape(idx, good):
    rec = {"id": "x1", "sentence": "Keytruda sales were $29,482 million, up 18%.",
           "impact": {"formula": "0.03 x Rev 29,482 x (1 - t 0.15)"},
           "citations": [good.to_dict()], "assumptions": {"0.03": "anchor placeholder (3% margin event)", "0.15": "t"}}
    out, passed = G.gate_record(rec, ["sentence", "impact.formula"], "citations", index=idx)
    _shape(out["numeric_check"])
    assert passed and out["numeric_check"]["total"] == 6 and "numeric_check" not in rec
    out2, passed2 = G.gate_record({**rec, "sentence": "Sales were $31,000 million."}, ["sentence"], "citations", index=idx)
    assert not passed2 and out2["numeric_check"]["unsupported"][0]["where"].startswith("sentence@")
    out3, passed3 = G.gate_record({"citations": []}, ["sentence"], "citations", index=idx)
    assert out3["numeric_check"]["status"] == "unchecked" and not passed3


def test_gate_document_per_item_and_document_level(idx, good, bad):
    doc = {"five numbers": [{"where": "EV", "text": "EV 1,551.3", "citations": []},
                            {"where": "cash", "text": "cash 29,482", "citations": [good.to_dict()], "unit": "USD millions"}],
           "inputs": [Claim("Keytruda sales were $29,482 million.", [good]), ("bad", "revenue 99 billion", [bad])]}
    s = G.gate_document(doc, index=idx)
    _shape(s["numeric_check"])
    assert not s["passed"] and s["failed"] == ["EV", "bad"]
    assert [x["passed"] for x in s["items"]] == [False, True, True, False]
    assert s["numeric_check"]["total"] == 4 and s["numeric_check"]["verified"] == 2
    ok = G.gate_document([Claim("Keytruda sales were $29,482 million.", [good])], index=idx)
    assert ok["passed"] and ok["numeric_check"]["status"] == "passed"
    assert G.gate_document([], index=idx)["numeric_check"]["status"] == "unchecked"


def test_safe_eval_rejects_code():
    assert G.safe_eval("max(a, b) / 2 - -1", {"a": 4, "b": 6}) == 4.0
    with pytest.raises(ValueError):
        G.safe_eval("__import__('os').getcwd()", {})


# ---------------------------------------------------------------- per-number markers (review D2, D15, C18)
def test_render_per_number_markers(idx, good, full_year):
    from agent.needle.cite import render
    other = V.verify(Citation(DOC, 2, "Gross margin was 71.5% in 2025."), idx)
    cl = Claim("Keytruda sales were $29,482 million and gross margin was 71.5%; total $64,168 million.",
               [good, other, full_year])
    md = render.render_markdown([cl], index=idx)
    assert "$29,482 million[1] and gross margin was 71.5%[2]; total $64,168 million[3]." in md
    h = render.render_html([cl], index=idx)
    assert '$29,482 million<sup><a href="#fn-1">[1]</a></sup>' in h
    # all numbers share one citation -> a single marker after the clause
    one = render.render_markdown([Claim("Sales were $29,482 million, up 18%.", [good])], index=idx)
    assert "Sales were $29,482 million, up 18%.[1]" in one


def test_render_derived_and_assumption_markers(idx, good, full_year):
    from agent.needle.cite import render
    a = Citation.from_dict({**good.to_dict(), "value": "29,482", "unit": "USD millions"})
    der = {"share": G.derived_entry(45.9, "a / b * 100", {"a": a, "b": (64168, full_year)}, unit="%")}
    cl = Claim("Keytruda was 45.9% of revenue at a base rate of 0.65%.", [], derived=der,
               assumptions={"0.65%": "Pfizer MFN base rate"})
    md = render.render_markdown([cl], index=idx)
    assert "45.9%[derived: 1, 2] of revenue at a base rate of 0.65%[assumption]." in md
    assert md.count("**Sources**") == 1 and "[1] AAA 10-K FY2025" in md and "[2] AAA 10-K FY2025" in md
    assert G.gate_document([cl], index=idx)["passed"]


def test_render_footnote_page_and_quotes_and_public(idx):
    from agent.needle.cite import render
    fact = Citation("tables/x.csv", None, 'Keytruda "US" sales = 29,482', claim_type="number", value="29,482",
                    doc_title="moat table x", location="row MRK-2025", license="wrds_licensed")
    fact.verification.status = "exact"
    md = render.render_markdown([Claim("Keytruda US sales 29,482.", [fact])])
    assert "file page None" not in md and "moat table x, row MRK-2025 --" in md
    assert '"Keytruda "US" sales = 29,482"' in md                      # double quotes kept verbatim
    pub = render.render_markdown([Claim("Keytruda US sales 29,482.", [fact])], public=True)
    assert "licensed text withheld" in pub and "Keytruda \"US\"" not in pub
    assert "licensed text withheld" in render.render_html([Claim("x", [fact])], public=True)


def test_no_numbers_status_is_not_passed_but_is_not_a_failure(idx, good):
    r = G.numeric_gate("Management reworded the pricing risk factor.", [good], index=idx)
    _shape(r.numeric_check)
    assert r.numeric_check["status"] == "no_numbers" and r.numeric_check["total"] == 0 and r.passed
    out, ok = G.gate_record({"sentence": "paragraph dropped from MD&A", "citations": []}, ["sentence"], "citations",
                            index=idx)
    assert out["numeric_check"]["status"] == "no_numbers" and ok
    s = G.gate_document({"notes": [("n1", "no figures here", []), ("n2", "none here either", [])]}, index=idx)
    assert s["passed"] and s["numeric_check"]["status"] == "no_numbers"
    assert [x["numeric_check"]["status"] for x in s["items"]] == ["no_numbers", "no_numbers"]
    mixed = G.gate_document([("n", "no figures", []), Claim("Keytruda sales were $29,482 million.", [good])], index=idx)
    assert mixed["passed"] and mixed["numeric_check"]["status"] == "passed"
    bad = G.gate_document([("n", "no figures", []), ("x", "revenue 99 billion", [])], index=idx)
    assert not bad["passed"] and bad["numeric_check"]["status"] == "failed" and bad["failed"] == ["x"]


def test_verify2_page_numerals_outside_the_quote_support_nothing(idx, good):
    # good quotes "...$29,482 million in 2025, an increase of 18 percent..."; 71.5% and ($183) sit on the same page
    # outside the quote. Review verify2: a footer "- 3 -" or an EPS "1.18" on the page verified a z-score.
    r = G.numeric_gate("Gross margin was 71.5%; other income ($183) million; sales $29,482 million.", [good], index=idx)
    assert [u["value"] for u in r.numeric_check["unsupported"]] == ["71.5%", "($183) million"]
    assert r.numeric_check["verified"] == 1
    n = [x for x in r.numbers if x["kind"] == "verified"][0]
    assert set(n["basis"]) <= {"quote", "value"}


def test_verify2_record_maps_win_over_a_coincidental_citation(idx):
    # the AMGN case: "z +1.2" is a code-computed peer statistic; a passing citation quoting "$ 1.18" must not verify it
    eps = V.verify(Citation(DOC, 2, "Net sales of Keytruda were $29,482 million in 2025"), idx)
    from dataclasses import replace
    eps = replace(eps, quote="basic EPS $ 1.18")                 # a passing citation whose quote holds 1.18
    peer = {"peer_z": {"value": "1.2", "label": "shortlist peer panel statistic (not page-cited)"}}
    r = G.numeric_gate("DSO 93 days; z +1.2", [eps], assumptions=dict(peer, d={"value": "93", "label": "x"}), index=idx)
    z = [x for x in r.numbers if x["value"].endswith("1.2")][0]
    assert z["kind"] == "assumed" and "peer panel" in z["label"]


def test_verify2_constants_are_labelled_where_the_reader_sees_them(idx):
    from agent.needle.cite.render import render_markdown
    cl = Claim("0.03 x Rev 29,482 x (1 - t 0.15)", [],
               derived={"rev": {"value": 29482, "expr": "a", "operands": {"a": {"value": 29482, "assumption": "rev"}}}},
               assumptions={"0.03": {"value": "0.03", "label": "constant: ANCHOR (3% margin event)"},
                            "t": {"value": "0.15", "label": "effective tax rate t (assumption)"}}, where="impact.formula")
    md = render_markdown([cl], index=idx)
    assert "0.03[constant: ANCHOR]" in md and "0.15)[assumption]" in md
    assert "(1 - t" in md and "(1[" not in md                    # bare arithmetic 1 is excluded by the documented rule


def test_verify2_assumption_label_follows_the_printed_symbol(idx):
    am = {"t": {"value": "0.2", "label": "effective tax rate t"},
          "m": {"value": "0.2", "label": "constant: M_MDP_AVOIDED (m_avoided)"}}
    r = G.numeric_gate([("impact.formula", "t 0.2 and m_avoided (0.3, 0.2, 0.1)")], [],
                       assumptions=dict(am, x={"value": "0.3", "label": "x"}, y={"value": "0.1", "label": "y"}), index=idx)
    lab = {(n["value"], n["start"]): n["label"] for n in r.numbers}
    assert lab[("0.2", 2)] == "effective tax rate t" and lab[("0.2", 26)].startswith("constant: M_MDP_AVOIDED")


def test_count_operands_and_median(idx, good, full_year, bad):
    two = G.derived_entry(2, "a + b", {"a": {"value": 1, "citation": good, "count": True},
                                       "b": {"value": 1, "citation": full_year, "count": True}})
    r = G.numeric_gate("lists 2 indications", [], derived={"n": two}, index=idx)
    assert r.passed and r.numeric_check["derived"] == 1
    dup = G.derived_entry(2, "a + b", {"a": {"value": 1, "citation": good, "count": True},
                                       "b": {"value": 1, "citation": good, "count": True}})
    assert not G.numeric_gate("lists 2 indications", [], derived={"n": dup}, index=idx).passed
    unv = G.derived_entry(1, "a", {"a": {"value": 1, "citation": bad, "count": True}})
    assert not G.numeric_gate("lists 1 indication", [], derived={"n": unv}, index=idx).passed
    med = G.derived_entry(1.5, "median(x, y)", {"x": {"derived": "n"}, "y": {"value": 1, "citation": good, "count": True}})
    assert G.numeric_gate("rival median 1.5", [], derived={"n": two, "m": med}, index=idx).passed
