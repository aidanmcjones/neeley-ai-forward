"""facts.locator (agent/needle/cite/facts.py apply_locator): page, fact and url locators, label-section rows, and the
older sqlite without the column. Offline, synthetic index."""

import json
import sqlite3

import pytest

from agent.moat import cite as moat
from agent.needle.cite import facts as F
from agent.needle.cite.index import load_index
from agent.needle.cite.locator import Citation, Verification
from tests.needle.test_cite import DM, EDGAR, EXACT, K10, SCHEMA, _doc

LABEL_IND = """<!-- source: x -->
[[page 1 | printed WARNING]]
Boxed warning text that is long enough to be a line.

[[page 2 | printed 1 INDICATIONS AND USAGE]]
## 1 INDICATIONS AND USAGE

DRUGX is indicated in combination with a reduced-calorie diet and increased physical activity:

- to reduce excess body weight and maintain weight reduction long term in adults with obesity.

- to treat moderate to severe obstructive sleep apnea (OSA) in adults with obesity.
"""
FACTS = """CREATE TABLE facts (id INTEGER PRIMARY KEY, "table" TEXT, doc_id TEXT, row_key TEXT, ticker TEXT, drug TEXT,
  period TEXT, field TEXT, value TEXT, unit TEXT, source TEXT, source_row TEXT, verify_status TEXT,
  row_json TEXT, text TEXT{loc});"""


def _db(path, with_locator):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executescript(FACTS.format(loc=", locator TEXT" if with_locator else ""))
    _doc(con, "AAA:10k_FY2025.md", "annual_report", EDGAR, "data/corpus/companies/AAA/10k_FY2025.md", K10, "10-K")
    _doc(con, "drug:drugx:label_sections.md", "fda_label", DM, "data/corpus/drugs/drugx/label_sections.md", LABEL_IND,
         scheme="section", drug="drugx")
    rows = [
        ("pipeline/loe_calendar.csv", "pipeline/loe_calendar.csv#1", "company_stated_loe", "29,482", "pass",
         {"quote": "Net sales of Keytruda were $29,482 million in 2025"}, "AAA:10k_FY2025.md#p2", ""),
        ("calls/cross_source.csv", "calls/cross_source.csv#2", "value", "7", "verified", {}, "fact:calls/cross_source.csv#2", ""),
        ("rx/partd.csv", "rx/partd.csv#3", "claims", "211575", "no_verified_copy", {},
         "url:https://data.cms.gov/api/1/x#3", "https://data.cms.gov/api/1/x"),
        ("rx/partd.csv", "rx/partd.csv#4", "claims", "5", "unchecked", {}, "url:https://data.cms.gov/api/1/x#4", ""),
        ("epi/indication_map.csv", "epi/indication_map.csv#83", "label_section", "1", "unchecked",
         {"drug": "drugx", "indication": "obstructive sleep apnea (with obesity)", "sub_indication": "moderate to severe OSA"},
         "url:https://dailymed.nlm.nih.gov/x#83", "https://dailymed.nlm.nih.gov/x"),
    ]
    for i, (t, rk, fld, v, vs, rj, loc, src) in enumerate(rows):
        srow = ("data/corpus/drugs/drugx/label_sections.md#1 INDICATIONS AND USAGE|osa" if t.startswith("epi/") else str(i))
        vals = [i + 1, t, "", rk, "AAA", "", "", fld, v, "", src, srow, vs, json.dumps(rj), ""]
        if with_locator:
            vals.append(loc)
        con.execute(f"INSERT INTO facts VALUES ({','.join('?' * len(vals))})", vals)
    con.commit()
    con.row_factory = sqlite3.Row
    return con


@pytest.fixture(scope="module", autouse=True)
def _restore_moat_db():
    old = moat.DB
    yield
    moat.DB = old
    moat.db.cache_clear()


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    d = tmp_path_factory.mktemp("loc")
    new, old = _db(d / "new.sqlite", True), _db(d / "old.sqlite", False)
    return new, load_index(d / "new.sqlite"), old, load_index(d / "old.sqlite")


def _base(r, status="exact"):
    return Citation(canonical_id=r["table"], quote=f"{r['row_key']} {r['field']} = {r['value']}", claim_type="number",
                    value=r["value"], location=f"row {r['row_key']}", page_scheme="none",
                    verification=Verification(status, 1.0 if status == "exact" else 0.0, "", "facts row"),
                    confidence_note="facts row")


def _row(con, rk):
    return con.execute("SELECT * FROM facts WHERE row_key = ?", (rk,)).fetchone()


def test_parse_locator_forms():
    assert F.parse_locator("LLY:10k_FY2025.md#p12") == {"kind": "page", "doc_id": "LLY:10k_FY2025.md", "page": 12}
    assert F.parse_locator("fact:calls/cross_source.csv#2")["kind"] == "fact"
    u = F.parse_locator("url:https://x.org/a?b=1#c#17")
    assert u == {"kind": "url", "url": "https://x.org/a?b=1#c", "row_key": "17"}
    assert F.parse_locator("") is None and F.parse_locator(None) is None


def test_page_locator_gives_a_verified_page_citation(env):
    con, idx, _, _ = env
    r = _row(con, "pipeline/loe_calendar.csv#1")
    c = F.apply_locator(r, _base(r), json.loads(r["row_json"]), idx)
    assert c.canonical_id == "AAA:10k_FY2025.md" and c.page == 2 and c.verification.ok
    assert c.deep_link.startswith(EDGAR) and "#:~:text=" in c.deep_link and "page=2" in c.viewer_link
    assert "pipeline/loe_calendar.csv#1" in c.confidence_note and "facts.locator" in c.confidence_note
    # a cited value that differs from the row is never upgraded to a page citation
    assert F.apply_locator(r, _base(r, "unverified"), json.loads(r["row_json"]), idx, value_mismatch=True).page is None


def test_fact_locator_keeps_the_facts_citation_with_the_row_key(env):
    con, idx, _, _ = env
    r = _row(con, "calls/cross_source.csv#2")
    c = F.apply_locator(r, _base(r), {}, idx)
    assert c.canonical_id == "calls/cross_source.csv" and c.page is None and c.verification.status == "exact"
    assert c.location == "row calls/cross_source.csv#2" and "calls/cross_source.csv#2" in c.quote


def test_url_locator_is_machine_data_with_the_url_as_deep_link_and_keeps_the_whitelist(env):
    con, idx, _, _ = env
    r = _row(con, "rx/partd.csv#3")
    c = F.apply_locator(r, _base(r, "machine_data"), {}, idx)
    assert c.source_url == "https://data.cms.gov/api/1/x" and c.raw_doc_type == "machine_data"
    assert c.deep_link == ""                  # an API endpoint does not show the row: the row key is the citation
    assert c.verification.status == "machine_data" and "machine data" in c.confidence_note
    r4 = _row(con, "rx/partd.csv#4")                         # unchecked row: a URL is not a check (fail closed)
    c4 = F.apply_locator(r4, _base(r4, "unverified"), {}, idx)
    assert c4.verification.status == "unverified"
    page = dict(r)
    page["locator"] = "url:https://www.cms.gov/medicare/drug-list.html#3"
    assert F.apply_locator(page, _base(r, "machine_data"), {}, idx).deep_link == "https://www.cms.gov/medicare/drug-list.html"


def test_label_section_row_resolves_to_the_label_page_line(env):
    con, idx, _, _ = env
    r = _row(con, "epi/indication_map.csv#83")
    c = F.apply_locator(r, _base(r, "unverified"), json.loads(r["row_json"]), idx)
    assert c.canonical_id == "drug:drugx:label_sections.md" and c.page == 2
    assert c.verification.status == "exact" and "obstructive sleep apnea" in c.quote
    assert c.deep_link == DM


def test_older_sqlite_without_the_column_is_unchanged(env):
    _, _, old, idx_old = env
    assert F.row_locator(_row(old, "pipeline/loe_calendar.csv#1")) == ""
    for rk in ("pipeline/loe_calendar.csv#1", "calls/cross_source.csv#2", "rx/partd.csv#3"):
        r = _row(old, rk)
        b = _base(r)
        assert F.apply_locator(r, b, json.loads(r["row_json"]), idx_old) == b
