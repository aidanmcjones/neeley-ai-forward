"""Score the golden-path prompt on 10 to 20 fixed inputs.

cases.jsonl: one JSON object per line:
  {"id": "c1", "question": "...", "must_include": ["phrase", "number"]}

Run:  python eval/run_eval.py
Prints pass rate; that number goes on the architecture slide.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.llm import call  # noqa: E402

CASES = ROOT / "eval" / "cases.jsonl"
DATA_DIR = ROOT / "data"


def load_context():
    ctx = {}
    for f in sorted(DATA_DIR.glob("*")):
        if f.suffix.lower() in {".txt", ".md", ".csv", ".json"}:
            ctx[f.name] = f.read_text(errors="ignore")[:200_000]
    return ctx or None


def main():
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    ctx = load_context()
    passed = 0
    for c in cases:
        text = call(c["question"], context=ctx)["text"].lower()
        missing = [m for m in c.get("must_include", []) if m.lower() not in text]
        ok = not missing
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'} {c['id']}" + (f"  missing: {missing}" if missing else ""))
    print(f"\n{passed}/{len(cases)} passed ({100 * passed / max(len(cases), 1):.0f}%)")


if __name__ == "__main__":
    main()
