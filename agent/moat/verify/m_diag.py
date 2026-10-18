"""Diagnostics for m_qa over every transcript; optional arg: ticker quarter to dump turns."""
import sys
from collections import defaultdict
from pathlib import Path
from agent.moat.verify.m_qa import ROOT, classify, roster_for, INTRO


def files():
    by = defaultdict(list)
    for base in ("data/corpus/companies", "data/moat/companies"):
        for f in sorted((ROOT / base).glob("*/transcripts/*_transcript.md")):
            by[f.parts[-3]].append(f)
    return by


def main():
    by = files()
    want = sys.argv[1:]
    for tk, fs in sorted(by.items()):
        if want and tk != want[0]:
            continue
        ros = roster_for(fs, tk)
        if not want:
            print(tk, "rosterE", sorted(ros["E"])[:40])
        for f in fs:
            q = f.name.split("_")[0]
            if len(want) > 1 and q != want[1]:
                continue
            lay, k0, turns = classify(f.read_text(), tk, ros)
            an = [t for t in turns if t[2] == "A"]
            intros = sum(1 for t in turns if t[2] in "OE" and INTRO.search(t[3]))
            names = sorted({t[1] for t in an})
            src = "corpus" if "corpus" in str(f) else "moat"
            print(f"{tk} {q} {src:6} {lay:8} turns={len(turns):3} an={len(an):3} intros={intros:3} names={len(names)} {names[:14]}")
            if len(want) > 1:
                for t in turns:
                    print("   ", t[0], t[2], t[1][:40], "|", t[3][:150])


main()
