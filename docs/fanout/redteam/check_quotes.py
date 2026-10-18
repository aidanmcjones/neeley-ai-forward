"""Usage: python docs/fanout/redteam/check_quotes.py MRK-nugget-001 [--file other.jsonl]
   or:  python docs/fanout/redteam/check_quotes.py --quote "TICKER" "doc_id" PAGE "quote text"
Runs agent.needle.pages.check on every evidence quote of one nugget row. Read-only."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from agent.needle import pages
from agent.needle.schema import Evidence

def run(ev):
    tk = ev.doc_id.split(":")[0]
    st, why = pages.check(ev, pages.docs(tk))
    print(f"[{st}] {ev.doc_id} p{ev.page} printed={ev.printed} cite={ev.citation} :: {why} :: {ev.quote[:90]}")

if sys.argv[1] == "--quote":
    run(Evidence(doc_id=sys.argv[3], page=int(sys.argv[4]), quote=sys.argv[5], speaker=sys.argv[6] if len(sys.argv) > 6 else ""))
else:
    f = ROOT / "docs/nuggets/MRK.jsonl"
    if "--file" in sys.argv: f = Path(sys.argv[sys.argv.index("--file") + 1])
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["id"] == sys.argv[1]:
            for e in r["evidence"]:
                run(Evidence(doc_id=e["doc_id"], page=e["page"], quote=e["quote"], speaker=e.get("speaker", ""), figures=e.get("figures", [])))
