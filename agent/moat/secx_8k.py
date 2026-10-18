import re, sys
from agent.moat.secx_lib import *

EX = re.compile(r"ex-?99|ex99|exhibit99|ex-?10|ex-?2[._-]|ex-?2\d?\.", re.I)


def main():
    done = corpus_urls()
    mine = set()
    man = OUT / "manifests" / "secx.jsonl"
    if man.exists():
        for ln in man.read_text().splitlines():
            try:
                mine.add(json.loads(ln)["source_url"])
            except Exception:
                pass
    only = sys.argv[1:] or list(ciks())
    for t, cik in ciks().items():
        if t not in only:
            continue
        form = "6-K" if t in ("AZN", "NVO") else "8-K"
        sub = "6k" if form == "6-K" else "8k"
        _, fs = filings(cik, "2023-01-01")
        fs = [f for f in fs if f["form"] == form]
        n = skipped = 0
        for f in fs:
            try:
                docs = folder_docs(cik, f["accession"])
            except Exception as e:
                note_gap("secx", t, f"{form} {f['accession']}", repr(e))
                continue
            keep = [(nm, u) for nm, u in docs if nm.lower().endswith((".htm", ".html", ".txt"))
                    and (nm == f["primary_doc"] or EX.search(nm)) and "index" not in nm.lower()]
            for nm, u in keep:
                if u in done or u in mine:
                    skipped += 1
                    continue
                try:
                    raw = sec_get(u)
                except Exception as e:
                    note_gap("secx", t, f"{form} doc {u}", repr(e))
                    continue
                stem = re.sub(r"\.[a-z]+$", "", nm)
                f2 = dict(f)
                save_doc(f"companies/{t}/{sub}/{f['filed']}_{f['accession']}_{stem}.md", u, raw, t,
                         "current_report_8k" if form == "8-K" else "foreign_current_report", f2)
                n += 1
            if n % 25 == 0:
                print(t, f["filed"], n, flush=True)
        print("DONE", t, form, "filings", len(fs), "docs written", n, "skipped", skipped, flush=True)


main()
