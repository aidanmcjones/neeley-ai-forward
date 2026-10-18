import csv
import io
import re
from agent.moat.common import write, note_gap
from agent.moat.market_topics import CORP, TOPIC_RE, ROOT
from agent.moat.market_topics2 import parse_qa2 as parse_qa

COLS = ["ticker", "quarter", "topic", "analyst_turns", "turns_with_topic", "mentions", "example_quote",
        "example_speaker", "example_file", "source", "source_row"]


def quote(text, rx):
    m = rx.search(text)
    a = max(0, m.start() - 160)
    return re.sub(r"\s+", " ", text[a:m.end() + 200]).strip()


def main():
    rows = []
    for f in sorted(CORP.glob("*/transcripts/*_transcript.md")):
        tk = f.parts[-3]
        q = f.name.split("_")[0]
        rel = str(f.relative_to(ROOT))
        text = f.read_text()
        start, turns = parse_qa(text)
        merged = []
        for t in turns:
            if merged and merged[-1][1] == t[1] and merged[-1][2] == t[2]:
                merged[-1] = (merged[-1][0], t[1], t[2], merged[-1][3] + " " + t[3])
            else:
                merged.append(t)
        turns = merged
        an = [t for t in turns if t[2]]
        print(tk, q, "qa_start_line", start, "turns", len(turns), "analyst_turns", len(an), flush=True)
        if len(an) < 3:
            note_gap("market", tk, f"analyst_topics {q}", f"only {len(an)} analyst turns parsed (qa_start line {start})")
        for topic, rx in TOPIC_RE.items():
            hit = [t for t in an if rx.search(t[3])]
            ex = max(hit, key=lambda t: len(rx.findall(t[3])), default=None)
            rows.append([tk, q, topic, len(an), len(hit), sum(len(rx.findall(t[3])) for t in an),
                         quote(ex[3], rx) if ex else "", ex[1] if ex else "", rel if ex else "", rel,
                         ex[0] if ex else start])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    w.writerows(rows)
    write("market", "tables/analyst_topics.csv", buf.getvalue(), group="market", doc_type="table",
          source_url="data/corpus/companies/*/transcripts")
    print(len(rows))


main()
