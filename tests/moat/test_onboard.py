"""Offline checks for the onboarding commands (no network, no R2): CIK resolution, aliases, product member names,
manifest schema, and that `index --add` is idempotent and keeps existing ids stable on a tiny fixture."""

import csv
import json
import sqlite3

import pytest

from agent.moat import common
from agent.moat import index as I
from agent.moat import onboard_lib as L
from agent.moat.onboard_company import member_name, parse_subsidiaries

TICKERS = [
    {"cik": 872589, "name": "REGENERON PHARMACEUTICALS, INC.", "ticker": "REGN", "exchange": "Nasdaq"},
    {"cik": 1114448, "name": "NOVARTIS AG", "ticker": "NVS", "exchange": "NYSE"},
    {"cik": 875320, "name": "VERTEX PHARMACEUTICALS INC / MA", "ticker": "VRTX", "exchange": "Nasdaq"},
    {"cik": 1067983, "name": "BERKSHIRE HATHAWAY INC", "ticker": "BRK-B", "exchange": "NYSE"},
]


def test_resolve_cik_exact_and_share_class():
    assert L.resolve_cik("regn", TICKERS) == {"ticker": "REGN", "cik": 872589,
                                              "name": "REGENERON PHARMACEUTICALS, INC.", "exchange": "Nasdaq"}
    assert L.resolve_cik("BRK.B", TICKERS)["cik"] == 1067983
    assert L.resolve_cik("ZZZZ", TICKERS) is None


def test_company_key_and_aliases():
    assert L.company_key("REGENERON PHARMACEUTICALS, INC.") == "regeneron"
    assert L.company_key("VERTEX PHARMACEUTICALS INC / MA") == "vertex"
    assert L.company_key("NOVARTIS AG") == "novartis"
    subs = ["Regeneron Ireland DAC", "Checkmate Pharmaceuticals, Inc.", "Decibel Therapeutics, Inc.",
            "Regeneron UK Limited", "Global Holdings LLC", "BV 12 Ltd", "Alnara Pharmaceuticals Inc.",
            "Document and Entity Information", "Alpine Immune Sciences"]
    al = L.aliases("VERTEX PHARMACEUTICALS INC / MA", ["VERTEX PHARMACEUTICALS INC"], subs)
    assert al[0] == "vertex"
    assert "checkmate" in al and "decibel" in al and "alnara" in al
    assert "document" not in al and "alpine" not in al  # no corporate suffix: not trusted as an entity row
    assert al.count("vertex") == 1 and "global" not in al and "holdings" not in al
    rx = L.alias_regex(al)
    assert rx.search("VERTEX PHARMS INC") and not rx.search("VERTEXA")


def test_member_name():
    assert member_name("regn:EyleaHDMember") == "Eylea HD"
    assert member_name("vrtx:TrikaftaKaftrioMember") == "Trikafta Kaftrio"
    assert member_name("us-gaap:ProductMember") == ""
    assert member_name("regn:CollaborationRevenueMember") == ""


def test_subsidiary_exhibit_names():
    import re
    from agent.moat.onboard_company import SUBS_PATTERNS
    k = SUBS_PATTERNS["10-K"][1]
    assert all(re.search(k, n, re.I) for n in ["regn-ex_211x12312025x10k.htm", "ex21.htm", "exhibit21-1.htm",
                                               "vrtx-20251231xex21.htm"])
    assert not re.search(k, "regn-ex_2310x.htm", re.I) and not re.search(k, "ex2101.htm", re.I)
    f = SUBS_PATTERNS["20-F"][1]
    assert re.search(f, "nvs-ex8.htm", re.I) and re.search(f, "ex8-1.htm", re.I) and re.search(f, "a-ex_81x.htm", re.I)
    assert not re.search(f, "ex81500.htm", re.I)


def test_parse_subsidiaries_table():
    raw = ("<table><tr><td>Name</td><td>Jurisdiction</td></tr><tr><td>Regeneron Ireland DAC</td><td>Ireland</td></tr>"
           "<tr><td>Checkmate Pharmaceuticals, Inc.</td><td>Delaware</td></tr></table>")
    assert parse_subsidiaries(raw) == [{"entity": "Regeneron Ireland DAC", "country": "Ireland"},
                                       {"entity": "Checkmate Pharmaceuticals, Inc.", "country": "Delaware"}]


class _NoStore:
    kind = "none"


@pytest.fixture
def moat_tmp(tmp_path, monkeypatch):
    out = tmp_path / "data" / "moat"
    monkeypatch.setattr(common, "OUT", out)
    monkeypatch.setattr(common, "_store", _NoStore())
    monkeypatch.setattr(L, "OUT", out)
    return out


def test_manifest_schema(moat_tmp):
    run = L.Run("ZZZ", 1)
    run.doc("companies/ZZZ/10k_FY2025.md", "<!-- x -->\n[[page 1 | printed 1]]\nhello", ticker="ZZZ",
            group="companies", doc_type="annual_report", form="10-K", period="2025-12-31", pages=1)
    run.table("products", [{"brand": "A", "source": "s", "source_row": "r1"}, {"brand": "B"}], ticker="ZZZ")
    rows = [json.loads(l) for l in (moat_tmp / "manifests" / "onboard_ZZZ.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    for r in rows:
        assert L.check_manifest_row(r) == "", r
    assert rows[1]["path"] == "data/moat/onboard/ZZZ/products.csv"
    with open(moat_tmp / "onboard" / "ZZZ" / "products.csv") as f:
        hdr = next(csv.reader(f))
    assert "source" in hdr and "source_row" in hdr
    assert run.counts == {"docs": 1, "pages": 1, "tables": 1, "rows": 2}
    run.step("boom", lambda: 1 / 0)
    gaps = (moat_tmp / "gaps" / "onboard.jsonl").read_text()
    assert "boom" in gaps and "ZeroDivisionError" in gaps
    assert L.check_manifest_row(dict(rows[0], doc_id="X:wrong")) != ""


@pytest.fixture
def tiny_index(tmp_path, monkeypatch):
    root = tmp_path
    corpus, moat = root / "data" / "corpus", root / "data" / "moat"
    (corpus / "companies" / "AAA").mkdir(parents=True)
    (corpus / "companies" / "AAA" / "10k.md").write_text(
        "<!-- source: https://sec.example/a -->\n[[page 1 | printed 1]]\nAlpha revenue rose\n"
        "[[page 2 | printed 2]]\nBeta royalty fell\n")
    with open(corpus / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["doc_id", "ticker", "group", "doc_type", "path", "source_url"])
        w.writeheader()
        w.writerow({"doc_id": "AAA:10k.md", "ticker": "AAA", "group": "companies", "doc_type": "annual_report",
                    "path": "data/corpus/companies/AAA/10k.md", "source_url": "https://sec.example/a"})
    (moat / "manifests").mkdir(parents=True)
    (moat / "tables").mkdir()
    (moat / "tables" / "prices_daily.csv").write_text("ticker,date,adj_close,source,source_row\nAAA,2026-01-02,10,x,1\n")
    (moat / "verified" / "calls").mkdir(parents=True)
    (moat / "verified" / "calls" / "transcript_grades.csv").write_text("path,grade,quote_from\n")
    monkeypatch.setattr(I, "ROOT", root)
    monkeypatch.setattr(I, "CORPUS", corpus)
    monkeypatch.setattr(I, "MOAT", moat)
    monkeypatch.setattr(I, "OUT", moat / "index" / "citations.sqlite")
    monkeypatch.setattr(I, "BBG", corpus / "_inbox" / "bloomberg")
    monkeypatch.setattr(I, "GRADES", moat / "verified" / "calls" / "transcript_grades.csv")
    return root, moat


def _snapshot(db):
    return {"pages": db.execute("SELECT id, doc_id, page_no FROM pages ORDER BY id").fetchall(),
            "facts": db.execute('SELECT id, "table", row_key FROM facts ORDER BY id').fetchall(),
            "docs": db.execute("SELECT doc_id FROM docs ORDER BY doc_id").fetchall()}


def test_index_add_idempotent_and_ids_stable(tiny_index):
    root, moat = tiny_index
    out = moat / "index" / "citations.sqlite"
    meta = I.build(out)
    assert meta["n_docs"] == 1 and meta["n_pages"] == 2
    db = sqlite3.connect(out)
    before = _snapshot(db)
    db.close()

    # nothing new: add is a no-op
    r0 = I.add(out)
    assert r0["new_docs"] == 0 and r0["new_facts"] == 0

    # onboard a doc and a table, then add twice
    (moat / "companies" / "BBB").mkdir(parents=True)
    (moat / "companies" / "BBB" / "10q_2026Q1.md").write_text(
        "<!-- source: https://sec.example/b -->\n[[page 1 | printed 7]]\nGamma inventory build\n")
    (moat / "onboard" / "BBB").mkdir(parents=True)
    (moat / "onboard" / "BBB" / "products.csv").write_text("ticker,brand,partd_spend_2024,source,source_row\n"
                                                         "BBB,ZEPHYR,123,cms,line=2\n")
    (moat / "onboard" / "BBB" / "profile.json").write_text(json.dumps({"ticker": "BBB", "name": "BBB Pharma"}))
    with open(moat / "manifests" / "onboard_BBB.jsonl", "w") as f:
        for rel, dt in (("companies/BBB/10q_2026Q1.md", "quarterly_report"), ("onboard/BBB/products.csv", "table")):
            f.write(json.dumps({"doc_id": f"BBB:{rel}", "ticker": "BBB", "group": "companies", "doc_type": dt,
                                "path": f"data/moat/{rel}", "source_url": "https://sec.example/b",
                                "stream": "onboard_BBB"}) + "\n")
    r1 = I.add(out)
    assert r1["new_docs"] == 2 and r1["new_pages"] == 1 and r1["new_facts"] == 1
    assert r1["new_tables"] == ["onboard/BBB/products.csv"]
    r2 = I.add(out)
    assert r2["new_docs"] == 0 and r2["new_pages"] == 0 and r2["new_facts"] == 0

    db = sqlite3.connect(out)
    after = _snapshot(db)
    assert after["pages"][:len(before["pages"])] == before["pages"]
    assert after["facts"][:len(before["facts"])] == before["facts"]
    hit = db.execute("SELECT p.doc_id, p.page_no, p.printed FROM pages_fts f JOIN pages p ON p.id = f.rowid "
                     "WHERE pages_fts MATCH 'inventory'").fetchall()
    assert hit == [("BBB:companies/BBB/10q_2026Q1.md", 1, "7")]
    fact = db.execute("SELECT f.ticker, f.verify_status, f.source_row FROM facts_fts x JOIN facts f ON f.id = x.rowid "
                      "WHERE facts_fts MATCH 'ZEPHYR'").fetchall()
    assert fact == [("BBB", "unverified_onboard", "line=2")]
    assert db.execute("SELECT company FROM docs WHERE doc_id = 'BBB:companies/BBB/10q_2026Q1.md'").fetchone()[0] == "BBB Pharma"
    db.close()


def test_progress_scans_onboard_manifests(tmp_path, monkeypatch):
    from agent.moat import progress as P
    (tmp_path / "data/moat/manifests").mkdir(parents=True)
    for n in ("onboard_REGN", "onboard_VRTX", "onboard_drug_dupixent", "filings"):
        (tmp_path / "data/moat/manifests" / f"{n}.jsonl").write_text("")
    monkeypatch.setattr(P, "ROOT", tmp_path)
    assert P.onboarded_tickers() == ["REGN", "VRTX"]
    assert P.onboarded_drugs() == ["dupixent"]
