"""The numeric gate is wired into every output path (docs/gate_wiring.md; reviews C1-C5, D1-D13).

Synthetic tests always run; tests that need the shared citation index or the drug packs skip when those are absent."""

import json
import sys
from types import SimpleNamespace

import pytest

from agent.needle.cite.gate import gate_document, gate_record
from agent.needle.cite.locator import Citation, Verification
from agent.needle.quant import data as DATA
from agent.needle.quant import decide as D
from agent.needle.quant import find as F
from agent.needle.quant import impact as IM
from agent.needle.quant import league
from agent.needle.quant import product as P
from agent.needle.quant import run

REAL = P.default_db().exists() and (P.REPO / "data" / "corpus" / "drugs" / "zepbound" / "label_sections.md").exists() \
    and P.moat_root() is not None
needs_real = pytest.mark.skipif(not REAL, reason="real citation index / drug packs not present")


def _cite(quote, value=None, status="exact", cid="DOC:x.md", page=3):
    return Citation(canonical_id=cid, page=page, quote=quote, claim_type="number" if value else "quote", value=value,
                    verification=Verification(status, 1.0, "2026-10-17", "test"))


def _scored(fid, sentence, cites, S=0.05):
    fam = F.FAM["receivables"]
    imp = IM.Impact("anchor", formula="0.03 x Rev_TTM 100.0", quantified=True)
    imp.d_eps = {"bull": 0.1, "base": 0.1, "bear": 0.1}
    vec = {"M": 1.0, "O": 0.5, "D": 0.6, "E": 1.0, "pi": 0.1, "c": 0.0, "z": 0}
    sc = F.Scored("TST", fid, "receivables_outpace_revenue", sentence, fam, "anchor", "adverse", imp, {}, vec, S,
                  "MEDIUM", [], [], list(cites), [[c] for c in cites], fact_key=fid)
    sc.assumptions = {"ANCHOR": {"value": "0.03", "label": "constant: ANCHOR"},
                      "rev": {"value": "100", "label": "constant: test revenue"}}
    return sc


def test_finding_with_one_unsupported_number_is_rejected_and_absent_from_league(tmp_path, monkeypatch):
    good = _scored("good", "Receivables 10,227 at quarter end.", [_cite("Receivables 10,227 9,570", "10,227")], S=0.04)
    bad = _scored("bad", "Receivables 10,227 at quarter end, up 99.9% on a peer z of +4.2.",
                  [_cite("Receivables 10,227 9,570", "10,227")], S=0.9)
    co = SimpleNamespace(ticker="TST")
    monkeypatch.setattr(run, "OUT", tmp_path)
    monkeypatch.setattr(run.data, "company", lambda t: co)
    monkeypatch.setattr(run.find, "ira_findings", lambda t, c: [bad, good])
    monkeypatch.setattr(run.find, "mfn_findings", lambda t, c: [])
    _, shown, withheld = run.score_ticker("TST", write=True)
    assert [f.id for f in shown] == ["good"]
    assert "bad" in [f.id for f in withheld]
    rej = [json.loads(x) for x in (tmp_path / "TST" / "rejected_v3.jsonl").read_text().splitlines()]
    r = next(x for x in rej if x["id"] == "bad")
    assert r["rejected_by"] == "numeric_gate" and r["numeric_check"]["status"] == "failed"
    assert {u["value"] for u in r["numeric_check"]["unsupported"]} >= {"99.9%", "+4.2"}
    shown_rows = [json.loads(x) for x in (tmp_path / "TST" / "findings_v3.jsonl").read_text().splitlines()]
    assert [x["id"] for x in shown_rows] == ["good"] and shown_rows[0]["numeric_check"]["status"] == "passed"
    L, top, _, _ = league.league_score(shown)
    assert [f.id for f in top] == ["good"]                       # the S = 0.9 row never reaches the league


def test_derived_citation_with_missing_operand_is_unsupported():
    op = _cite("Receivables 10,227", "10,227")
    der = DATA.derived_citation("a / 2", 5113.5, [op], expr="a / 2", names=["a"])
    assert der.operands == [op.cite_id]
    rec = {"sentence": "Half of receivables.", "citations": [der.to_dict()]}          # operand not inline
    out, ok = gate_record(rec, ["sentence"], "citations")
    assert not ok and any(u["reason"].startswith("operand not in record") for u in out["numeric_check"]["unsupported"])
    rec["citations"].append(op.to_dict())
    out, ok = gate_record(rec, ["sentence"], "citations")
    assert ok
    # the Scored writer puts operands inline
    sc = _scored("x", "Receivables 10,227.", [op, der])
    ids = {c["cite_id"] for c in sc.to_dict()["citations"]}
    assert op.cite_id in ids and der.cite_id in ids


def test_decide_forged_exact_status_is_discarded():
    forged = {"canonical_id": "NOPE:not_a_doc.md", "page": 1, "quote": "cash 99,999", "verification":
              {"status": "exact", "score": 1.0}, "cite_id": "c_forged"}
    c = D.citation_from_dict(forged, 99999, "USD millions")
    assert c.verification.status == "unverified" and not c.verification.ok and c.cite_id != "c_forged"
    # a gated document refuses the number the forged citation was meant to carry
    s = gate_document({"budget": [{"where": "cash", "text": "cash 99,999", "citations": [c]}]})
    assert not s["passed"]


@needs_real
def test_decide_forged_exact_on_a_real_page_is_reverified():
    c = D.citation_from_dict({"canonical_id": "LLY:10k_FY2025.md", "page": 49, "quote": "Zepbound (1) 77,777 fabricated",
                              "verification": {"status": "exact"}}, 77777, "USD millions")
    assert c.verification.status == "unverified"


def _cmp_with_cell(text, cites):
    ent = {"name": "Foo", "slug": "", "maker": "", "variant": "", "ingredient": "", "note": ""}
    rows = {k: {"Foo": P.Cell()} for k, _ in P.ROWS}
    rows["pricing"]["Foo"] = P.Cell(text, {}, cites, [], "")
    return P.ProductComparison("TST", "foo", "2026-10-17", [ent], rows)


def test_product_cell_number_missing_from_its_citations_is_uncited():
    c = _cmp_with_cell("list price $1,234 per month", [_cite("list price $9,999 per month", "9,999")])
    assert ("pricing", "Foo") in c.uncited()
    res = P.cell_gate(c, "pricing", "Foo")
    assert not res.passed and res.numeric_check["unsupported"][0]["value"] == "$1,234"
    ok = _cmp_with_cell("list price $9,999 per month", [_cite("list price $9,999 per month", "9,999")])
    assert ok.uncited() == [] and P.cell_gate(ok, "pricing", "Foo").passed


@needs_real
def test_amgn_product_no_longer_crashes(tmp_path):
    from agent.needle.quant import product_cli
    for prod in ("repatha", "enbrel"):
        d = product_cli.main(["--ticker", "AMGN", "--product", prod, "--out", str(tmp_path)])
        assert d["numeric_check"]["status"] == "passed"
        tl = d["comparison"]["rows"]["timeline"]
        assert tl                                                   # the timeline row parsed "8/27/2029"-style dates


def test_every_cli_accepts_public(monkeypatch, tmp_path):
    from agent.needle.quant import decide_cli, product_cli
    seen = {}
    monkeypatch.setattr(product_cli, "build", lambda t, p, root=None, public=False: (seen.setdefault("product", public),
                                                                                    ({"findings": [], "empty_cells": []}, ""))[1])
    product_cli.main(["--ticker", "LLY", "--product", "zepbound", "--out", str(tmp_path), "--public"])
    assert seen["product"] is True
    monkeypatch.setattr(run, "score_ticker", lambda t, extra_signals=None: (None, [], []))
    monkeypatch.setattr(sys, "argv", ["run", "--ticker", "TST", "--public"])
    run.main()
    assert run.PUBLIC is True
    run.PUBLIC = False
    import argparse
    calls = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        ns = real(self, args, namespace)
        calls["public"] = getattr(ns, "public", None)
        raise SystemExit(0)
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    with pytest.raises(SystemExit):
        decide_cli.main(["--ticker", "LLY", "--findings", "x", "--moves", "y", "--public"])
    assert calls["public"] is True


# ---------------------------------------------------------------- phase 2: DECIDE and FIND on the verified tables
@needs_real
def test_verified_tables_cite_by_row_with_status_in_the_note():
    from agent.needle.quant import verified_tables as V
    acq = V.acquisition_value("ph3")
    assert acq.value == 2650.0 and acq.citations[0].verification.status == "exact"
    assert "verified" in acq.citations[0].verification.detail                 # verify_status carried into the note
    assert V.acquisition_value("all").value == 1675.0 and V.acquisition_value("approved").value == 1800.0
    assert V.royalty("ph2").value == 0.15 and V.royalty("ph2").derived              # cell n = 5, used
    lm = V.loe_month("LLY", "trulicity")
    assert lm.value == 3 and lm.derived and lm.citations[0].verification.ok   # company_stated_loe 2027, 10-K page
    comps = V.deal_comps()
    assert comps and all(r.get("verify_status") in ("verified", "corrected") for r in comps)


@needs_real
def test_decide_uses_table_rows_and_keeps_research_fallback_labelled():
    from agent.needle.quant import moves as M
    r = D.evaluate_move("M3", {}, [], context={"ta": "metabolic"})
    inp = {i.name: i for i in r.inputs}
    assert inp["trial_cost_each"].kind == "table" and inp["trial_cost_each"].value == 35.1      # moore2018|controlled
    assert inp["p_ph3"].kind == "benchmark"                                                    # BIO non-NME: no row
    labels = D.input_assumptions(inp["p_ph3"], [c for c in r.citations if c.cite_id in inp["p_ph3"].citation_ids])
    assert all(v["label"].startswith("research-note fallback") for v in labels.values())
    r5 = D.evaluate_move("M5", {"loe_month": {"value": 3, "kind": "company"}}, [],
                         context={"ticker": "LLY", "product": "trulicity"})
    lm = {i.name: i for i in r5.inputs}["loe_month"]
    assert lm.kind == "table" and lm.derived and M.get_template("M5")


@needs_real
def test_kill_table_baselines_from_rx_tables():
    from agent.needle.quant import decide_cli
    r = D.evaluate_move("M3", {}, [])
    rows = decide_cli.kill_table(r, {"product": "zepbound"})
    ctx = next(x for x in rows if x["id"] == "rx_context")
    assert any("Part D prescribers" in t for _, _, t in ctx["context"])
    assert all(c.verification.ok for _, c, _ in ctx["context"] if c is not None)
