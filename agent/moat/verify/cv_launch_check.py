"""Costs verifier item 2 (mechanical half): for each call quote in launch_and_marketing_benchmarks.csv, re-find it on
its page, find the speaker turn that contains it, and compare speaker, company and quarter. Writes /tmp/cv/launch_q.csv
and prints each quote for hand grading."""
import re

import pandas as pd

from agent.moat.verify.pe_lib import PAGE_RE, ROOT, norm

TURN = re.compile(r"\*\*([^*]+?):\*\*")


def main():
    d = pd.read_csv(ROOT / "data/moat/tables/launch_and_marketing_benchmarks.csv")
    q = d[d.datum_type.str.startswith("earnings-call")]
    out = []
    for i, r in q.iterrows():
        txt = (ROOT / r.file).read_text(errors="replace")
        flat = PAGE_RE.sub(" ", txt)
        nq = norm(r.quote_or_note, loose=True)
        # page check
        ms = list(PAGE_RE.finditer(txt))
        pg_txt = ""
        for j, m in enumerate(ms):
            if m.group(1) == str(r.page):
                end = ms[j + 1].start() if j + 1 < len(ms) else len(txt)
                pg_txt = txt[m.end():end]
                nxt = txt[end:ms[j + 2].start()] if j + 2 < len(ms) else txt[end:]
                pg_txt2 = pg_txt + " " + PAGE_RE.sub(" ", nxt)
        on_page = nq in norm(pg_txt, loose=True) or (nq in norm(pg_txt2, loose=True) if pg_txt else False)
        pos = norm(flat, loose=False).find(norm(r.quote_or_note)[:80])
        in_file = nq in norm(flat, loose=True)
        # speaker: last turn header before the quote in the raw text
        k = flat.find(r.quote_or_note[:60])
        spk = None
        if k >= 0:
            heads = list(TURN.finditer(flat[:k]))
            spk = heads[-1].group(1).strip() if heads else None
        spk_ok = spk is not None and str(r.speaker).split(" (")[0].strip().lower() == spk.split(" (")[0].strip().lower()
        qtr = r.period.split(" ")[0]
        q_ok = qtr in r.file
        tk_ok = f"/{r.ticker}/" in r.file
        out.append({"idx": i, "on_page": on_page, "in_file": in_file, "found_speaker": spk, "speaker_ok": spk_ok,
                    "quarter_ok": q_ok, "ticker_ok": tk_ok})
    o = pd.DataFrame(out).set_index("idx")
    o.to_csv("/tmp/cv/launch_q.csv")
    print(o[["on_page", "in_file", "speaker_ok", "quarter_ok", "ticker_ok"]].apply(pd.Series.value_counts).to_string())
    print(o[~o.speaker_ok | ~o.on_page].join(q[["ticker", "period", "speaker", "page"]]).to_string())
    for i, r in q.iterrows():
        print(i, r.ticker, r.period.split(" ")[0], "|", r.quote_or_note[:330])


if __name__ == "__main__":
    main()
