"""Peers wave 3 item 2: label and grade check of the three new transcripts (BBIO 2025Q2, 2025Q3 Motley Fool;
NVS 2026Q1 MarketBeat/Quartr), drop publisher summary blocks, append rows to verified/peers/transcript_labels.csv.

Call date: from the header and confirmed against the same-day SEC filing (BBIO 10-Q, NVS results 6-K); quarter:
from the opening remarks. The Fool Q3 page opens with a publisher summary turn ('**BridgeBio Pharma:** (BBIO -1.10%)
reported ...'); it is removed and the cleaned file rewritten through common.write (the stale peers.jsonl row for
that path is replaced by the new one).

Usage: PYTHONPATH=. python agent/moat/verify/pe_w3_transcripts.py
"""
import io
import json
import re

import pandas as pd

from agent.moat.common import OUT, write
from agent.moat.verify.pe_lib import ROOT, log_wrong

LAB = ROOT / "data/moat/verified/peers/transcript_labels.csv"
T = {"BBIO|2025Q2": ("data/moat/companies/BBIO/transcripts/2025Q2_transcript.md", "data/moat/companies/BBIO/10q_2025Q2.md", "Second Quarter 2025"),
     "BBIO|2025Q3": ("data/moat/companies/BBIO/transcripts/2025Q3_transcript.md", "data/moat/companies/BBIO/10q_2025Q3.md", "Third Quarter 2025"),
     "NVS|2026Q1": ("data/moat/companies/NVS/transcripts/2026Q1_transcript.md", "data/moat/companies/NVS/6k/2026-04-28_0001114448-26-000010.md", "Q1 2026")}
PUB = re.compile(r"^\*\*(BridgeBio Pharma|Novartis)[^*]*:\*\* \((BBIO|NVS) [+-]?[\d.]+%\).*?\n\n", re.M | re.S)


def main():
    lab = pd.read_csv(LAB)
    rows = []
    for key, (path, filing, qtext) in T.items():
        tk, q = key.split("|")
        txt = (ROOT / path).read_text()
        call = re.search(r"call_date=(\S+)", txt[:600]).group(1)
        url = re.search(r"source: (\S+)", txt[:600]).group(1)
        fhdr = (ROOT / filing).read_text()[:400]
        fdate = re.search(r"filed: (\S+)", fhdr).group(1) if "filed:" in fhdr else re.search(r"/(\d{4}-\d{2}-\d{2})_", "/" + filing.split("/")[-1]).group(1)
        q_in_text = qtext.lower() in txt[:3000].lower()
        blocks = PUB.findall(txt)
        dropped = len(blocks)
        if dropped:
            clean = PUB.sub("", txt, count=dropped)
            rel = path.replace("data/moat/", "")
            m = json.loads([l for l in (OUT / "manifests/peers.jsonl").read_text().splitlines() if f'"{path}"' in l][-1])
            write("peers", rel, clean, ticker=m["ticker"], group=m["group"], doc_type=m["doc_type"], period=m["period"],
                  filed=m["filed"], source_url=m["source_url"], quality=m["source_quality"], pages=m["pages"])
            man = OUT / "manifests/peers.jsonl"
            ls = man.read_text().splitlines()
            hits = [i for i, l in enumerate(ls) if f'"path": "{path}"' in l]
            ls = [l for i, l in enumerate(ls) if i not in hits[:-1]]
            man.write_text("\n".join(ls) + "\n")
            log_wrong([dict(stream="peers", table="companies/BBIO/transcripts/2025Q3_transcript.md", row_key="page 1 first turn",
                            what_the_ai_wrote="'**BridgeBio Pharma:** (BBIO -1.10%) reported a material acceleration in revenue ...' kept as a speaker turn",
                            what_the_source_says="Motley Fool publisher summary with a stock ticker quote, not said on the call",
                            error_type="publisher_text_as_speaker", severity="medium", how_caught="ticker-quote pattern in a speaker turn",
                            count=1, example_cite=url)])
        sp = re.findall(r"^\*\*([^*]+):\*\*", (ROOT / path).read_text(), re.M)
        roles = sum("(" in s for s in sp)
        rows.append(dict(ticker=tk, file=path, label=q, call_date=call, date_from=f"header; same-day filing {filing} filed {fdate}",
                         expected_label=q, label_ok=bool(q_in_text and call == fdate), quarters_named_in_text=f"'{qtext}' in opening remarks: {q_in_text}",
                         top_named=q, source_url=url, convention="calendar", grade="C",
                         grade_reason=("single third-party copy (Motley Fool), speaker names without roles" if tk == "BBIO" else
                                       "single third-party copy (MarketBeat/Quartr), speakers named with roles; Novartis publishes no transcript"),
                         publisher_blocks_dropped=dropped, speaker_turns=len(sp), turns_with_role=roles, wave=3))
        print(rows[-1])
    lab = lab[~lab.file.isin([r["file"] for r in rows])]  # NVS 2026Q1 row was for the earlier MarketBeat copy (2026-04-29 url)
    out = pd.concat([lab, pd.DataFrame(rows)], ignore_index=True)
    buf = io.StringIO()
    out.to_csv(buf, index=False)
    write("verify_peers", "verified/peers/transcript_labels.csv", buf.getvalue(), group="peers", doc_type="table",
          quality="verified")
    print(len(out))


if __name__ == "__main__":
    main()
