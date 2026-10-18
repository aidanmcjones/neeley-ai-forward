"""Regression: orphan exclusivity is not product protection, and biologics get patents from the 10-K.

Bugs fixed (docs/red_team_v2_company_pick.md section 9 #3): Keytruda "protection ends 2031-01-25" (orphan) with no
patents, Enbrel "2010-11-02" (approval + 12y), DARZALEX "intravenous" and "2027-11-16".
"""

import json

import pytest

from agent.needle.detect import labels as L

PB_HEAD = ("Proprietary Name,Ref. Product Proprietary Name,Submission Type,Approval Date,Route of Administration,"
           "Marketing Status,Exclusivity Expiration Date,Ref. Product Exclusivity Exp. Date,"
           "Orphan Exclusivity Exp. Date,First Interchangeable Exclusivity Exp. Date\n")


def _clear():
    for f in (L._profile, L._parse, L._label_text, L._tenk_table):
        f.cache_clear()


@pytest.fixture
def fake(tmp_path, monkeypatch):
    drugs = tmp_path / "drugs"
    drugs.mkdir()
    tenk = tmp_path / "tenk_patents.json"
    tenk.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(L, "DRUGS", drugs)
    monkeypatch.setattr(L, "TENK_PATENTS", tenk)
    _clear()
    yield drugs, tenk
    _clear()


def _pack(drugs, slug, files):
    d = drugs / slug
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")


def test_purple_orphan_date_is_not_protection(fake):
    drugs, tenk = fake
    _pack(drugs, "mab", {"purple_book.csv": PB_HEAD +
                         "Mab,,Original,\"September 4, 2014\",Intravenous,Rx,,,\"January 25, 2031\",\n"})
    P = L.profile("mab")
    assert P["orphan_exclusivity"]["value"] == "2031-01-25"
    assert P["protection_end"]["value"] == "2026-09-04"  # 12y from first licensure, not the orphan date
    assert "derived" in P["protection_end"]["basis"]


def test_biologic_gets_10k_patent(fake):
    drugs, tenk = fake
    _pack(drugs, "mab", {"purple_book.csv": PB_HEAD +
                         "Mab,,Original,\"November 2, 1998\",Subcutaneous,Rx,,,\"May 27, 2006\",\n"})
    tenk.write_text(json.dumps({"mab": {"ticker": "X", "doc": "data/x.md", "patents": [
        {"expiry": "2028-11-22", "subject": "compound", "page": "1", "quote": "q1"},
        {"expiry": "2029", "subject": "DNA", "page": "1", "quote": "q2"}]}}), encoding="utf-8")
    P = L.profile("mab")
    assert P["latest_patent_expiry"]["value"] == "2029"
    assert "10-K" in P["latest_patent_expiry"]["source"]
    assert P["protection_end"]["value"] == "2029"
    assert P["protection_end"]["date_for_compare"] == "2029-12-31"
    assert P["orphan_exclusivity"]["value"] == "2006-05-27"


def test_orange_book_ode_code_excluded(fake):
    drugs, tenk = fake
    _pack(drugs, "pill", {
        "orange_book_patents.csv": "Patent_No,Patent_Expire_Date_Text,Delist_Flag\n123,\"Jan 1, 2030\",\n",
        "orange_book_exclusivity.csv": "Exclusivity_Code,Exclusivity_Date\nODE-111,\"Jun 1, 2033\"\nNCE,\"Jan 1, 2027\"\n"})
    P = L.profile("pill")
    assert P["protection_end"]["value"] == "2030-01-01"
    assert P["orphan_exclusivity"]["value"] == "2033-06-01"


def test_new_form_does_not_restart_12y_clock(fake):
    drugs, tenk = fake
    rows = (PB_HEAD + "Mab,,Original,\"November 16, 2015\",Intravenous,Rx,,,,\n"
            "Mab Sc,,Original,\"May 1, 2020\",Subcutaneous,Rx,,,\"January 15, 2028\",\n")
    _pack(drugs, "mab-sc", {"purple_book.csv": rows})
    P = L.profile("mab-sc")
    assert P["route"]["value"] == "subcutaneous"
    assert P["protection_end"]["value"] == "2027-11-16"  # first licensure 2015 + 12, orphan 2028 excluded


# ---------------------------------------------------------------- real corpus
def test_tenk_quotes_verify_on_their_pages():
    _clear()
    table = L._tenk_table()
    n = 0
    for slug, e in table.items():
        if slug.startswith("_"):
            continue
        for it in e["patents"] + ([e["stated_us_loe"]] if "stated_us_loe" in e else []):
            assert L.verify_tenk(e, it), (slug, it["quote"])
            n += 1
    assert n >= 15


def test_case_products_match_10k():
    _clear()
    k = L.profile("keytruda")
    assert k["protection_end"]["value"] != "2031-01-25"
    assert k["orphan_exclusivity"]["value"] == "2031-01-25"
    assert k["latest_patent_expiry"]["value"] == "2029-11"
    assert k["stated_us_loe"]["value"] == "2028-12"
    assert L.profile("enbrel")["protection_end"]["value"] == "2038-02-22"
    dz = L.profile("darzalex")
    assert dz["protection_end"]["value"] == "2029"
    assert dz["route"]["subcutaneous_form"] == "darzalex-faspro"
    assert L.profile("darzalex-faspro")["route"]["value"] == "subcutaneous"
    rows = {r["field"]: r for r in L.compare("JNJ")["darzalex-faspro"]["table"]}
    assert rows["Protection ends (latest patent or non-orphan exclusivity)"]["product"].startswith("2029")
    assert "keytruda-qlex" in L.compare("MRK")
