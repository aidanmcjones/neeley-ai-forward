"""Detector contract. Every detector module in this package:

  def run(ticker: str) -> list[Signal]     # pure, deterministic; no network; reads data/corpus only
  python -m agent.needle.detect.<name> --ticker AZN   # writes out/<TICKER>/signals_<name>.jsonl via save()

Rules shared by all detectors:
- Every Signal carries at least one Evidence whose quote is copied verbatim from a page-marked corpus file and
  passes agent.needle.pages.check() (labels are the one exception: they cite label_sections.md by section).
- Quotes are 15 to 60 words, taken from the page text itself, never paraphrased.
- Earnings-call evidence names the speaker; transcripts in SKIP_DOCS are never quoted.
- LLM use is optional and goes through agent.llm.call (cached); a detector must still run without an API key.
"""

import argparse
from pathlib import Path

from agent.needle.schema import write_jsonl

ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT = ROOT / "out"

SHORTLIST = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]

# flagged as unquotable in data/corpus/README.md and GAPS.md
SKIP_DOCS = {
    "AZN:transcripts/2026Q1_transcript.md",   # actually the Q2 2026 call (duplicate)
    "AZN:transcripts/2025Q3_transcript.md",   # no speaker names
    "GILD:transcripts/2025Q3_transcript.md",  # garbled
}

# case appendix: each company's products and the rival products they are compared with (drug_pack slugs)
CASE_SETS = {
    "MRK": {"keytruda": ["opdivo", "imfinzi", "tecentriq"], "januvia": ["ozempic", "jardiance"]},
    "BMY": {"eliquis": ["xarelto"], "opdivo": ["keytruda", "tecentriq"]},
    "PFE": {"ibrance": ["verzenio", "kisqali"], "vyndamax": ["attruby", "amvuttra"]},
    "LLY": {"zepbound": ["wegovy"], "mounjaro": ["ozempic"], "trulicity": ["ozempic"]},
    "NVO": {"wegovy": ["zepbound", "foundayo"], "ozempic": ["mounjaro"]},
    "ABBV": {"skyrizi": ["tremfya", "stelara", "cosentyx", "entyvio"], "rinvoq": ["tremfya", "cosentyx", "entyvio"]},
    "JNJ": {"tremfya": ["skyrizi", "rinvoq", "wezlana"], "darzalex": ["sarclisa"]},
    "AZN": {"tagrisso": ["rybrevant", "lazcluze"], "farxiga": ["jardiance"], "imfinzi": ["keytruda"]},
    "AMGN": {"repatha": ["praluent", "leqvio", "lipfendra"], "enbrel": ["skyrizi", "rinvoq", "humira"]},
    "GILD": {"biktarvy": ["dovato", "cabenuva"], "yeztugo": ["apretude"]},
}


def save(ticker, name, signals):
    path = OUT / ticker.upper() / f"signals_{name}.jsonl"
    write_jsonl(path, signals)
    return path


def cli(name, run):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", help="one ticker; default is all 10 shortlist companies")
    a = ap.parse_args()
    for t in ([a.ticker.upper()] if a.ticker else SHORTLIST):
        try:
            sigs = run(t)
            print(f"{t}: {len(sigs)} signals -> {save(t, name, sigs)}")
        except Exception as e:  # one company failing must not stop the sweep
            print(f"{t}: FAILED {type(e).__name__}: {e}")
