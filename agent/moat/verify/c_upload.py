"""Upload verified calls files via common.write and append AI-was-wrong entries."""
import csv
import json
from collections import Counter

from agent.moat.common import OUT, ROOT, now, write

V = OUT / "verified" / "calls"
FILES = ["transcript_grades.csv", "qa_turns.csv", "cross_source.csv", "cross_source_diffs.csv", "roster_check.csv", "fix_counts.csv"]


def main():
    for fn in FILES:
        write("verify_calls", f"verified/calls/{fn}", (V / fn).read_text(), group="calls", doc_type="table", quality="verified")
    for p in sorted((V / "src").iterdir()):
        url = ""
        write("verify_calls", f"verified/calls/src/{p.name}", p.read_bytes(), ticker=p.name.split("_")[0], doc_type="transcript_source",
              period=p.name.split("_")[1], quality="official" if "official" in p.name else "third_party", source_url=url or None)
    fc = dict(csv.reader((V / "fix_counts.csv").open()))
    diffs = list(csv.DictReader((V / "cross_source_diffs.csv").open()))
    ndiff = sum(1 for d in diffs if d["ticker"] in ("MRK", "PFE", "JNJ") and d["quarter"] != "2026Q2" and "official" in d["source_a"])
    E = [
        ("qa_turns", "executive (e.g. Adam Lenkowsky, Cindy Perettie, Ilya Yuffa, Roopal Thakkar) tagged role=analyst",
         "these are named officers of the company on its own call", "roster match against EXEC list + 10-K/proxy name check",
         int(fc.get("executive tagged as analyst", 0)), "tables/qa_turns.csv BMY Adam Lenkowsky rows"),
        ("qa_turns", "sell-side analysts tagged role=executive (Courtney Breen at MRK, Chris Schott at LLY, Simon Baker / James Gordon at AZN)",
         "they are Bernstein / J.P. Morgan / Redburn / Barclays analysts", "name seen as analyst on other calls",
         int(fc.get("analyst tagged as executive", 0)), "tables/qa_turns.csv MRK Courtney Breen 'Merck & Co.'"),
        ("qa_turns", "speaker = timestamp ('00:50:04'), answer sentence, or Motley Fool headline ('AbbVie vs. Eli Lilly', 'Forget High-Yield Traps')",
         "no such speaker; text is an answer fragment or page furniture", "speaker-label sanity regex",
         int(fc.get("unattributable speaker label", 0)), "tables/qa_turns.csv ABBV 2025Q3 'Forget High-Yield Traps'"),
        ("qa_turns", "ASR/parser misspelled names: 'Michael Szapary'/'Mike Savar' (Mike Czapar), 'Patrick Johnson' (Patrik Jonsson), 'Michael Novart' (Michael Novod), 'Steve Scholar | TD Collin' (Steve Scala, TD Cowen), 'Romeo Devon' (Vamil Divan), 'Chung Wen' (Trung Huynh), mojibake 'JÃ¸rgensen'",
         "correct spellings per company filings and analyst rosters", "alias map + roster",
         int(fc.get("executive name variant or misspelling", 0)) + int(fc.get("analyst name variant or ASR misspelling", 0)), "tables/qa_turns.csv LLY 'Michael Szapary'"),
        ("qa_turns", "analyst firm blank, 'Analyst'/'Equity Analyst', the company's own name, or a spilled answer sentence",
         "the analyst's bank, from the operator intro or the same analyst on adjacent calls", "firm placeholder check + inference",
         int(fc.get("missing or placeholder analyst firm filled", 0)), "tables/qa_turns.csv MRK Daina Graybosch firm='that and also steer...'"),
        ("transcripts", "MarketBeat/Quartr ASR text presented as the transcript (third_party) with exact executive wording",
         f"official LSEG copies differ on 2-5% of executive words and 40-60% of sentences are not verbatim; {ndiff} substantive diffs incl. MRK 2025Q3 Litchfield '$6.6' vs '$3.6', JNJ 2025Q3 Wolk '$93.7' vs '$90', JNJ 2025Q2 Duato '17-year' vs '70-year', PFE 2024Q3 Bourla '50' vs '15', MRK 2025Q2 PADCEV->'PET/CEF', LAGEVRIO->'Librio'",
         "word alignment against official LSEG PDFs fetched from merck.com / pfizer and jnj q4cdn", ndiff, "data/moat/verified/calls/cross_source_diffs.csv"),
        ("transcripts", "corpus AZN 2026Q1 transcript (roic.ai) is the Q1 2026 call",
         "its text is the Q2/H1 2026 call of July 27, 2026 (matches only 15% of the MarketBeat Q1 copy; figures differ throughout)",
         "cross-source alignment + date string in body", 1, "data/corpus/companies/AZN/transcripts/2026Q1_transcript.md"),
        ("transcripts_index", "call_date for BMY 2025Q3 = 2025-11-27 and NVO 2025Q3 = 2025-12-11",
         "calls were 2025-10-30 and 2025-11-05; collector took the fool.com article date", "MarketBeat event date vs index", 2,
         "tables/transcripts_index.csv"),
        ("transcripts_index", "tables written to data/moat/tables/", "calls_tables.py writes ROOT/tables/ (repo root), not data/moat/tables/",
         "file not found at documented path", 2, "agent/moat/calls_tables.py tdir = ROOT / 'tables'"),
        ("transcripts", "JNJ 2026Q2 official PDF text marked usable for search only",
         "re-extraction still spaceless; a MarketBeat copy matches 72% of its sentences verbatim (spaces stripped), so it is repairable sentence by sentence",
         "spaceless substring check", 1, "data/moat/verified/calls/src/JNJ_2026Q2_mb.html"),
    ]
    p = OUT / "verify" / "ai_wrong.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for table, said, src, how, n, ex in E:
            f.write(json.dumps({"stream": "calls", "table": table, "what_the_ai_said": said, "what_the_source_says": src,
                                "how_caught": how, "count": n, "example_source": ex, "at": now()}) + "\n")
    print("uploaded", len(FILES), "tables +", len(list((V / "src").iterdir())), "sources; ai_wrong +", len(E))


if __name__ == "__main__":
    main()
