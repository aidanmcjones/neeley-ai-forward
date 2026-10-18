"""Spot-check roles. No args: anomaly counts per call. Args TICKER QUARTER: compact dump of that call."""
import re
import sys
from agent.moat.verify.m_qa import classify, roster_for, INTRO
from agent.moat.verify.m_topics import pick_files, RANK

ANSWERISH = re.compile(r"^\s*(thanks?( you)?,? (for|so much for) (the|your) question|yes,? (thank|good)|so let me|i'?ll take|let me (start|take)|great question)", re.I)


def best(tk, fs, ros, q):
    cs = []
    for f in fs:
        if f.name.startswith(q):
            lay, k0, turns = classify(f.read_text(), tk, ros)
            n = sum(1 for t in turns if t[2] == "A")
            cs.append((RANK[lay] if n >= 4 else 9, -n, f, lay, turns))
    return sorted(cs, key=lambda c: (c[0], c[1]))[0] if cs else None


def main():
    by = pick_files()
    ros = {tk: roster_for(fs, tk) for tk, fs in by.items()}
    gA = set().union(*[r["A"] for r in ros.values()])
    for r in ros.values():
        r["E"] -= gA
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            tk, q = arg.split(":")
            c = best(tk, by[tk], ros[tk], q)
            ops = sum(1 for t in c[4] if t[2] == "O" and INTRO.search(t[3]))
            print("##", tk, q, c[2].name, c[3], "intros", ops)
            for t in c[4]:
                if t[2] == "A":
                    print(f"  {t[0]:5} {t[1][:34]:34} | {re.sub(chr(10), ' ', t[3])[:80]}")
        return
    tot = {"calls": 0, "answerish_A": 0, "missed_after_intro": 0}
    for tk, fs in sorted(by.items()):
        qs = sorted({f.name.split("_")[0] for f in fs})
        for q in qs:
            c = best(tk, fs, ros[tk], q)
            turns = c[4]
            a1 = [t for t in turns if t[2] == "A" and ANSWERISH.search(t[3])]
            miss = [turns[i + 1] for i in range(len(turns) - 1) if turns[i][2] == "O" and INTRO.search(turns[i][3])
                    and turns[i + 1][2] == "E" and "?" in turns[i + 1][3][:600]]
            tot["calls"] += 1
            tot["answerish_A"] += len(a1)
            tot["missed_after_intro"] += len(miss)
            if a1 or miss:
                print(tk, q, c[3], "answerish_A:", [(t[0], t[1][:20], t[3][:50]) for t in a1][:3], "| missed:",
                      [(t[0], t[1][:20], t[3][:50]) for t in miss][:3])
    print(tot)


main()
