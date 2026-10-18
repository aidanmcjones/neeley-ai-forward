"""Check Q&A start: count operator introductions that fall before the detected Q&A start (should be 0)."""
from agent.moat.verify.m_qa import layout, raw_turns, qa_start, INTRO
from agent.moat.verify.m_topics import pick_files

bad = 0
for tk, fs in sorted(pick_files().items()):
    for f in fs:
        text = f.read_text()
        lay = layout(text)
        turns = raw_turns(text, lay)
        k0 = qa_start(turns, text)
        pre = [t for t in turns[:k0] if t[1].lower() == "operator" and INTRO.search(t[3]) and "question" in t[3].lower()]
        if len(pre) > 0 or k0 == len(turns) // 2:
            bad += 1
            print(tk, f.parent.parent.parent.name, f.name[:6], lay, "k0", k0, "of", len(turns), "operator intros before k0:", len(pre),
                  [t[3][:60] for t in pre[:2]])
print("flagged", bad)
