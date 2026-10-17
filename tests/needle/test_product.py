"""Product fine print tests: appendix data, five-row table, citations, gate, growth limiter, CLI.

Synthetic tests (a fake citation index and a one-drug pack) always run. Real-data tests run when the shared
citations.sqlite and the drug packs are present (they are gitignored)."""

import json
import re
import sqlite3

import pytest

from agent.moat import cite as moat
from agent.needle.cite.index import load_index
from agent.needle.cite.verify import gate
from agent.needle.quant import product as P
from agent.needle.quant import product_cli

REAL = P.default_db().exists() and (P.REPO / "data" / "corpus" / "drugs" / "zepbound" / "label_sections.md").exists() \
    and P.moat_root() is not None
needs_real = pytest.mark.skipif(not REAL, reason="real citation index / drug packs not present")

LABEL = """<!-- source: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc-123 setid=abc-123 -->
## WARNING: RISK OF THYROID C-CELL TUMORS

- Fooxin causes thyroid C-cell tumors in rodents at clinically relevant exposures in animal studies.

## 1 INDICATIONS AND USAGE

Fooxin is indicated as an adjunct to diet and exercise to improve glycemic control in adults with type 2 diabetes.

## 2 DOSAGE AND ADMINISTRATION

Administer Fooxin subcutaneously once weekly, on the same day each week, at any time of day with or without meals.

## 4 CONTRAINDICATIONS

Fooxin is contraindicated in patients with a personal history of medullary thyroid carcinoma or hypersensitivity.

## 5 WARNINGS AND PRECAUTIONS

### 5.1 Pancreatitis

Pancreatitis has been reported in patients treated with Fooxin and the drug should be stopped if suspected.
"""


@pytest.fixture()
def fake(tmp_path_factory):
    """Fake index with one label doc (page = section) plus a one-drug pack, wired in through monkeypatching."""
    from agent.needle.detect import labels
    tmp = tmp_path_factory.mktemp("prod")
    db = tmp / "citations.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""CREATE TABLE docs (doc_id TEXT PRIMARY KEY, ticker TEXT, company TEXT, "group" TEXT, doc_type TEXT, form TEXT,
      period TEXT, filed TEXT, source_quality TEXT, source_url TEXT, path TEXT, stream TEXT, quote_grade TEXT,
      superseded_by TEXT, license TEXT, drug TEXT, n_pages INTEGER, page_scheme TEXT, notes TEXT);
      CREATE TABLE pages (id INTEGER PRIMARY KEY, doc_id TEXT, page_no INTEGER, printed TEXT, char_start INTEGER,
      char_end INTEGER, speakers TEXT, text TEXT);""")
    secs = re.split(r"(?m)^(?=## )", LABEL)[1:]
    con.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("drug:foo:label_sections.md", "TST", "TST", "drugs", "fda_label", "", "", "", "official",
                 "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=abc-123", "data/corpus/drugs/foo/label_sections.md", "", "", "",
                 "", "foo", len(secs), "section", ""))
    for n, t in enumerate(secs, 1):
        con.execute("INSERT INTO pages (doc_id,page_no,printed,text) VALUES (?,?,?,?)",
                    ("drug:foo:label_sections.md", n, t.splitlines()[0].lstrip("# ").strip(), t))
    con.commit()
    con.close()
    pack = tmp / "drugs" / "foo"
    pack.mkdir(parents=True)
    (pack / "label_sections.md").write_text(LABEL, encoding="utf-8")
    (tmp / "moat" / "tables").mkdir(parents=True)
    old_drugs, old_db = labels.DRUGS, moat.DB
    labels.DRUGS = tmp / "drugs"
    labels._profile.cache_clear()
    labels._parse.cache_clear()
    labels._label_text.cache_clear()
    idx = load_index(db)
    app = {"company": "Test", "starter": "Fooxin faces generic pressure.",
           "products": {"foo": {"self": P.E("Fooxin", "foo", "Test", "fooxide"), "rivals": [P.E("Generic fooxide", None, "generic makers")]}}}
    P.APPENDIX["TST"] = app
    yield {"idx": idx, "root": tmp / "moat"}
    P.APPENDIX.pop("TST", None)
    labels.DRUGS = old_drugs
    labels._profile.cache_clear()
    labels._parse.cache_clear()
    labels._label_text.cache_clear()
    moat.DB = old_db
    moat.db.cache_clear()


# ---------------------------------------------------------------- appendix as data
def test_appendix_rival_sets_spot_check():
    a = P.APPENDIX
    lly = a["LLY"]["products"]["zepbound"]["rivals"]
    assert [r["name"] for r in lly] == ["Ozempic", "Wegovy injection", "Wegovy pill"]
    assert lly[2]["slug"] == "wegovy" and lly[2]["variant"] == "tablet"
    assert set(a["LLY"]["products"]) == {"zepbound", "mounjaro", "trulicity"}
    assert [r["slug"] for r in a["MRK"]["products"]["keytruda"]["rivals"]] == ["opdivo", "imfinzi", "tecentriq"]
    assert [r["slug"] for r in a["AZN"]["products"]["tagrisso"]["rivals"]] == ["rybrevant", "lazcluze"]
    assert a["AZN"]["products"]["farxiga"]["rivals"][0]["slug"] is None        # generic dapagliflozin has no label
    assert [r["slug"] for r in a["NVO"]["products"]["ozempic"]["rivals"]] == ["mounjaro", "zepbound", "foundayo"]
    assert [r["slug"] for r in a["GILD"]["products"]["biktarvy"]["rivals"]] == ["dovato", "cabenuva"]
    assert set(a) == {"MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"}
    assert [k for k, _ in P.ROWS] == ["approved_uses", "safety", "dosing", "timeline", "pricing"]


def test_unknown_product_is_a_clear_error():
    with pytest.raises(KeyError):
        P.compare("LLY", "keytruda")


# ---------------------------------------------------------------- synthetic comparison
def test_synthetic_table_five_rows_and_label_citations(fake):
    c = P.compare("TST", "foo", data_root=fake["root"], index=fake["idx"])
    assert list(c.rows) == [k for k, _ in P.ROWS] and len(c.rows) == 5
    for row, cells in c.rows.items():
        assert set(cells) == {"Fooxin", "Generic fooxide"}
    me = {r: c.rows[r]["Fooxin"] for r in ("approved_uses", "safety", "dosing")}
    for cell in me.values():
        assert not cell.empty and cell.citations
        for ct in cell.citations:
            assert ct.page and ct.verification.status != "unverified" and ct.verification.ok
    assert me["safety"].citations[0].page == 1                       # boxed warning page
    assert me["dosing"].detail["frequency"] == "once weekly"
    # generic rival: every cell empty with a reason, nothing invented
    assert all(c.rows[r]["Generic fooxide"].empty and c.rows[r]["Generic fooxide"].empty_reason for r in c.rows)
    gl = P.growth_limiter(c)
    assert gl[1] is False and gl[0].count(".") == 1                  # no revenue: honest non-answer, still one sentence
    assert gate(me["safety"].citations and [__import__("agent.needle.cite.locator", fromlist=["Claim"]).Claim("x", me["safety"].citations)])[0]


# ---------------------------------------------------------------- real data
@pytest.fixture(scope="module")
def lly():
    return P.compare("LLY", "zepbound")


@needs_real
def test_real_table_has_five_rows_and_cited_label_cells(lly):
    assert list(lly.rows) == [k for k, _ in P.ROWS]
    assert [e["name"] for e in lly.entities] == ["Zepbound", "Ozempic", "Wegovy injection", "Wegovy pill"]
    for row in ("approved_uses", "safety", "dosing"):
        for name, cell in lly.rows[row].items():
            assert not cell.empty, (row, name, cell.empty_reason)
            assert cell.citations, (row, name)
            for ct in cell.citations:
                assert ct.page and ct.verification.status != "unverified"
                assert ct.doc_type == "label" and "dailymed.nlm.nih.gov" in ct.deep_link and "#section" not in ct.deep_link
    assert lly.rows["dosing"]["Wegovy pill"].detail["route"] == "oral"
    assert lly.rows["timeline"]["Zepbound"].detail["company_stated"]["us_loe"] == "2036"
    assert "discrepancy" in lly.rows["timeline"]["Zepbound"].detail


@needs_real
def test_real_tied_finding_passes_gate_and_has_the_find_shape(lly):
    claims = P.tie_to_financials(lly)
    assert claims
    passed, rejected = gate(claims)
    assert len(passed) == len(claims) and not rejected
    c = claims[0]
    assert c.signal_family == "product" and c.obscurity_note and "consequence" in c.obscurity_note
    assert set(c.impact["dRev"]) == {"bull", "base", "bear"} and c.impact["formula"]
    assert c.impact["dRev"]["bear"] <= c.impact["dRev"]["base"] <= c.impact["dRev"]["bull"] <= 0
    assert c.confidence in ("high", "medium", "low") and c.peer.get("named_peer_row")
    rec = c.record()
    assert rec["sentence"] and rec["citations"] and rec["signal_family"] == "product"
    label_tie = [x for x in claims if x.channel == "label_breadth_medicare"]
    assert label_tie and label_tie[0].impact["inputs"]["rival"].startswith("Wegovy")


@needs_real
def test_real_growth_limiter_is_one_sentence(lly):
    claims = P.tie_to_financials(lly)
    s, priced, reasons, cites = P.growth_limiter(lly, claims)
    assert isinstance(priced, bool) and reasons and cites
    assert s.endswith(".") and "\n" not in s and len(re.findall(r"[.!?](?:\s|$)", s)) == 1
    assert any("analysts asked" in r for r in reasons)


@needs_real
def test_cli_runs_and_writes_json_and_markdown(tmp_path):
    data = product_cli.main(["--ticker", "MRK", "--product", "keytruda", "--out", str(tmp_path)])
    j = tmp_path / "MRK" / "product_keytruda.json"
    m = tmp_path / "MRK" / "product_keytruda.md"
    assert j.exists() and m.exists()
    d = json.loads(j.read_text())
    assert list(d["comparison"]["rows"]) == [k for k, _ in P.ROWS]
    assert d["growth_limiter"]["sentence"] and data["findings"]
    md = m.read_text()
    assert "| Row |" in md and "**Sources**" in md and "verified:" in md and "—" not in md
