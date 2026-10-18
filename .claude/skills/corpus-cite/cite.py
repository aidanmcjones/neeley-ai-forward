"""Find and verify cited text in data/corpus. Read-only. Run from the repo root with python -I.

  find   TICKER "regex" [--types 10k,transcript] [--max 20]   page hits: doc_id, file page N, printed P, snippet
  page   TICKER DOC_ID N                                       print one file page
  quote  DOC_ID N "exact quote" [--figures 1,234;5.6] [--speaker NAME]
  row    NUGGET_ID [--file docs/nuggets/X.jsonl]               verify every evidence quote of one nugget row
  file   docs/nuggets/X.jsonl                                  verify every row in a nugget file
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from agent.needle import pages  # noqa: E402
from agent.needle.schema import Evidence  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def verify(e):
    ev = Evidence(doc_id=e["doc_id"], page=e.get("page"), quote=e.get("quote", ""), speaker=e.get("speaker", ""),
                  figures=e.get("figures", []))
    status, why = pages.check(ev, pages.docs(ev.doc_id.split(":")[0]))
    print(f"[{status}] {ev.doc_id} p{ev.page} printed={ev.printed} | {ev.citation} | {why} | {ev.quote[:80]}")
    return status == "verified"


def rows(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find"); f.add_argument("ticker"); f.add_argument("pattern")
    f.add_argument("--types", default=""); f.add_argument("--max", type=int, default=20)
    p = sub.add_parser("page"); p.add_argument("ticker"); p.add_argument("doc_id"); p.add_argument("n", type=int)
    q = sub.add_parser("quote"); q.add_argument("doc_id"); q.add_argument("n", type=int); q.add_argument("quote")
    q.add_argument("--figures", default=""); q.add_argument("--speaker", default="")
    r = sub.add_parser("row"); r.add_argument("id"); r.add_argument("--file", default="")
    fl = sub.add_parser("file"); fl.add_argument("path")
    a = ap.parse_args()

    if a.cmd == "find":
        types = tuple(a.types.split(",")) if a.types else None
        rx, hits = re.compile(a.pattern, re.I), 0
        for doc_id, d in pages.docs(a.ticker, types).items():
            for n, (printed, text) in d["pages"].items():
                for m in rx.finditer(text):
                    s = re.sub(r"\s+", " ", text[max(0, m.start() - 140):m.end() + 140])
                    print(f"{doc_id} N={n} printed={printed} :: {s}")
                    hits += 1
                    if hits >= a.max:
                        return print(f"(stopped at --max {a.max})")
        print(f"{hits} hits")
    elif a.cmd == "page":
        printed, text = pages.docs(a.ticker)[a.doc_id]["pages"][a.n]
        print(f"[{a.doc_id} file page {a.n} | printed {printed}]\n{text}")
    elif a.cmd == "quote":
        figs = [x for x in a.figures.split(";") if x]
        sys.exit(0 if verify({"doc_id": a.doc_id, "page": a.n, "quote": a.quote, "speaker": a.speaker,
                              "figures": figs}) else 1)
    elif a.cmd == "row":
        tk = a.id.split("-")[0]
        path = a.file or f"docs/nuggets/{tk}.jsonl"
        row = next((x for x in rows(path) if x["id"] == a.id), None)
        if not row:
            sys.exit(f"{a.id} not in {path}")
        sys.exit(0 if all([verify(e) for e in row["evidence"]]) else 1)
    elif a.cmd == "file":
        bad = 0
        for row in rows(a.path):
            print(f"-- {row['id']}")
            bad += not all([verify(e) for e in row["evidence"]])
        print(f"{bad} rows with an unverified quote")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
